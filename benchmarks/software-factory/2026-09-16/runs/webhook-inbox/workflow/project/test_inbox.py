"""Behavior checks with an independent temporary database and server per test."""

import concurrent.futures
import hashlib
import hmac
import http.client
import json
import queue
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from inbox import create_server


class InboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.db = self.root / "events.sqlite3"
        self.config = self.root / "config.json"
        self.tenants = {"alpha": {"secret": "alpha-secret-λ", "token": "alpha-token"},
                        "beta": {"secret": "beta-secret", "token": "beta-token"}}
        self.config.write_text(json.dumps({"tenants": self.tenants}), encoding="utf-8")
        self.start_server()
        self.addCleanup(self.stop_server)

    def start_server(self):
        self.server = create_server(self.db, self.config)
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.01}, daemon=True)
        self.thread.start()

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.assertFalse(self.thread.is_alive())

    def request(self, method, path, body=None, headers=None):
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=15)
        try:
            connection.request(method, path, body, headers or {})
            response = connection.getresponse()
            raw = response.read()
            self.assertEqual(response.getheader("Content-Type"), "application/json; charset=utf-8")
            result = json.loads(raw)
            self.assertIsInstance(result, dict)
            return response.status, result
        finally:
            connection.close()

    def signed(self, event="id", body=b"{}", tenant="alpha", timestamp=None):
        timestamp = str(int(time.time())) if timestamp is None else timestamp
        signature = hmac.new(self.tenants[tenant]["secret"].encode(),
                             timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
        return {"X-Event-ID": event, "X-Timestamp": timestamp, "X-Signature": signature}

    def post(self, event="id", body=b"{}", tenant="alpha", headers=None):
        return self.request("POST", "/webhooks/" + tenant, body,
                            self.signed(event, body, tenant) if headers is None else headers)

    def page(self, tenant="alpha", query="", headers=None):
        return self.request("GET", "/events/" + tenant + query,
                            headers={"Authorization": "Bearer " + self.tenants[tenant]["token"]}
                            if headers is None else headers)

    def rows(self):
        with closing(sqlite3.connect(self.db)) as connection:
            return connection.execute(
                "SELECT tenant, event_id, raw_body, sequence FROM events ORDER BY sequence"
            ).fetchall()

    def raw_request(self, headers, body=b"{}", method="POST", path="/webhooks/alpha"):
        with socket.create_connection(self.server.server_address, timeout=5) as client:
            wire = (method + " " + path + " HTTP/1.1\r\nHost: localhost\r\n").encode()
            for name, value in headers:
                wire += name.encode() + b": " + value.encode("latin-1") + b"\r\n"
            client.sendall(wire + b"\r\n" + body)
            client.shutdown(socket.SHUT_WR)
            response = http.client.HTTPResponse(client)
            response.begin()
            value = json.loads(response.read())
            self.assertIsInstance(value, dict)
            return response.status, value

    def test_factory_health_and_unknown_routes(self):
        self.assertIsInstance(self.server, http.server.ThreadingHTTPServer)
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertGreater(self.server.server_address[1], 0)
        self.assertEqual(self.request("GET", "/health"), (200, {"status": "ok"}))
        for path in ("/events/Alpha", "/events/missing", "/events/alpha/extra", "/other"):
            self.assertEqual(self.request("GET", path)[0], 404)
        self.assertEqual(self.post(tenant="missing", headers={})[0], 404)

    def test_exact_raw_body_and_idempotency(self):
        event = "x'); DROP TABLE events; --"
        original = b'{ "a": 1, "message": "caf\xc3\xa9" }\n'
        self.assertEqual(self.post(event, original), (201, {"event_id": event, "duplicate": False}))
        before = self.rows()
        self.assertEqual(before[0][1:3], (event, original))
        self.assertEqual(self.post(event, original), (200, {"event_id": event, "duplicate": True}))
        self.assertEqual(self.post(event, b'{"a":1,"message":"caf\xc3\xa9"}')[0], 409)
        self.assertEqual(self.rows(), before)
        self.assertEqual(self.page()[1]["items"][0]["payload"], {"a": 1, "message": "café"})

    def test_tenant_isolation_and_case(self):
        self.assertEqual(self.post("same", b'{"owner":"alpha"}')[0], 201)
        self.assertEqual(self.post("same", b'{"owner":"beta"}', "beta")[0], 201)
        self.assertEqual(self.post("Same")[0], 201)
        self.assertEqual(self.post(tenant="beta", headers=self.signed("cross"))[0], 401)
        self.assertEqual(self.page("beta", headers={"Authorization": "Bearer alpha-token"})[0], 401)
        for tenant in ("alpha", "beta"):
            self.assertEqual(self.page(tenant)[1]["items"][0]["payload"], {"owner": tenant})

    def test_post_required_header_grammar_and_no_effects(self):
        for key in ("X-Event-ID", "X-Timestamp", "X-Signature"):
            headers = self.signed()
            del headers[key]
            self.assertEqual(self.post(headers=headers)[0], 400)
        cases = {"X-Event-ID": ["", " leading", "trailing ", "\tbad", "bad\tvalue", "a" * 129, "é"],
                 "X-Timestamp": ["", " 1", "1 ", "+1", "-1", "01", "1.0", "1e9", "１２"],
                 "X-Signature": ["", "a" * 63, "a" * 65, "G" * 64, "A" * 64, " a" + "0" * 62]}
        for key, values in cases.items():
            for value in values:
                if not value.isascii() and key == "X-Timestamp":
                    continue  # HTTP field values cannot encode these Unicode characters.
                with self.subTest(key=key, value=value):
                    headers = self.signed()
                    headers[key] = value
                    self.assertEqual(self.post(headers=headers)[0], 400)
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.post()[0], 201)

    def test_header_duplicates_and_content_length(self):
        valid = list(self.signed().items()) + [("Content-Length", "2")]
        for key in ("X-Event-ID", "X-Timestamp", "X-Signature", "Content-Length"):
            with self.subTest(key=key):
                original = next(value for name, value in valid if name == key)
                self.assertEqual(self.raw_request(valid + [(key.lower(), original)])[0], 400)
        for length in (None, "", "-1", "+2", "2.0", "2, 2", " 2", "2 ", "foo"):
            headers = list(self.signed().items())
            if length is not None:
                headers.append(("Content-Length", length))
            self.assertEqual(self.raw_request(headers)[0], 400)
        self.assertEqual(self.raw_request(valid + [("Transfer-Encoding", "chunked")])[0], 400)
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.raw_request(list(self.signed().items()) + [("Content-Length", "0002")])[0], 201)

    def test_short_body_does_not_reserve_id(self):
        headers = list(self.signed().items()) + [("Content-Length", "3")]
        self.assertEqual(self.raw_request(headers)[0], 400)
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.post()[0], 201)

    def test_timestamp_boundaries_and_reauthentication(self):
        with patch("inbox.time.time", return_value=1_000_000):
            for offset in (-300, 0, 300):
                headers = self.signed(str(offset), timestamp=str(1_000_000 + offset))
                self.assertEqual(self.post(headers=headers)[0], 201)
            before = self.rows()
            for timestamp in ("999699", "1000301", "0", "9" * 5000):
                headers = self.signed(timestamp=timestamp)
                self.assertEqual(self.post(headers=headers)[0], 401)
            headers = self.signed("0", timestamp="999699")
            self.assertEqual(self.post(headers=headers)[0], 401)
            headers = self.signed("0")
            headers["X-Signature"] = "0" * 64
            self.assertEqual(self.post(headers=headers)[0], 401)
            self.assertEqual(self.rows(), before)

    def test_invalid_json_has_no_effects(self):
        for body in (b"", b"[]", b"null", b"1", b'"x"', b"{", b'{"x":NaN}',
                     b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":"\xff"}', b"{} trailing"):
            with self.subTest(body=body):
                self.assertEqual(self.post(body=body)[0], 400)
                self.assertEqual(self.rows(), [])
        self.assertEqual(self.post()[0], 201)

    def test_body_size_is_inclusive_and_byte_based(self):
        body = b'{"x":"' + b"a" * (65536 - 8) + b'"}'
        self.assertEqual(len(body), 65536)
        self.assertEqual(self.post("full", body)[0], 201)
        self.assertEqual(self.post("too-large", body + b" ")[0], 413)
        self.assertEqual(len(self.rows()), 1)

    def test_event_id_length_boundary_and_ascii(self):
        self.assertEqual(self.post("a")[0], 201)
        self.assertEqual(self.post("a" * 128)[0], 201)
        self.assertEqual(self.post("a b")[0], 201)
        headers = list(self.signed().items()) + [("Content-Length", "2")]
        headers = [(key, "bad\x7f" if key == "X-Event-ID" else value) for key, value in headers]
        self.assertEqual(self.raw_request(headers)[0], 400)

    def test_json_numbers_preserve_valid_representation(self):
        body = b'{"large":1e999,"integer":' + b"9" * 5000 + b"}"
        self.assertEqual(self.post("numbers", body)[0], 201)
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.request("GET", "/events/alpha", headers={"Authorization": "Bearer alpha-token"})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            raw = response.read()
            parsed = json.loads(raw, parse_int=str, parse_float=str)
            self.assertEqual(parsed["items"][0]["payload"], {"large": "1e999", "integer": "9" * 5000})
            self.assertNotIn(b"Infinity", raw)
        finally:
            connection.close()

    def test_read_authorization_grammar_and_duplicates(self):
        for auth in (None, "", "alpha-token", "Basic alpha-token", "bearer alpha-token",
                     "Bearer", "Bearer ", "Bearer  alpha-token", "Bearer alpha-token ", "Bearer ALPHA-token"):
            self.assertEqual(self.page(headers={} if auth is None else {"Authorization": auth})[0], 401)
        headers = [("Authorization", "Bearer alpha-token"), ("authorization", "Bearer alpha-token")]
        self.assertEqual(self.raw_request(headers, b"", "GET", "/events/alpha")[0], 401)

    def test_query_validation(self):
        for query in ("limit=0", "limit=101", "limit=01", "limit=-1", "limit=+1", "limit=1.0", "limit=",
                      "limit=1&limit=1", "cursor=1&cursor=2", "cursor=01", "cursor=-1", "cursor=", "cursor=%FF",
                      "cursor=1.0", "cursor= 1", "unknown=1", "limit", "limit=1&", "limit=1&cursor=0&extra=1"):
            if " " in query:
                query = query.replace(" ", "%20")
            with self.subTest(query=query):
                self.assertEqual(self.page(query="?" + query)[0], 400)
        self.assertEqual(self.page(query="?cursor=" + "9" * 5000), (200, {"items": [], "next_cursor": None}))
        self.assertEqual(self.page(query="?limit=100&cursor=0"), (200, {"items": [], "next_cursor": None}))

    def test_ordered_stable_pagination_and_cross_tenant_cursor(self):
        for event, tenant in (("z", "alpha"), ("b", "beta"), ("a", "alpha"), ("m", "alpha")):
            self.assertEqual(self.post(event, tenant=tenant)[0], 201)
        first = self.page(query="?limit=2")[1]
        self.assertEqual([row["event_id"] for row in first["items"]], ["z", "a"])
        cursor = first["next_cursor"]
        self.assertEqual(cursor, str(first["items"][-1]["sequence"]))
        self.assertEqual(first, self.page(query="?limit=2")[1])
        last = self.page(query="?limit=2&cursor=" + cursor)[1]
        self.assertEqual([row["event_id"] for row in last["items"]], ["m"])
        self.assertIsNone(last["next_cursor"])
        beta_cursor = str(self.page("beta")[1]["items"][0]["sequence"])
        self.assertEqual([row["event_id"] for row in self.page(query="?cursor=" + beta_cursor)[1]["items"]], ["a", "m"])
        self.assertEqual(self.page("beta", "?cursor=" + cursor)[1], {"items": [], "next_cursor": None})
        self.assertEqual(self.page(query="?cursor=9223372036854775808")[1], {"items": [], "next_cursor": None})

    def test_default_and_maximum_page_limits(self):
        for index in range(101):
            self.assertEqual(self.post(str(index))[0], 201)
        self.assertEqual(len(self.page()[1]["items"]), 50)
        page = self.page(query="?limit=100")[1]
        self.assertEqual(len(page["items"]), 100)
        tail = self.page(query="?cursor=" + page["next_cursor"])[1]
        self.assertEqual([row["event_id"] for row in tail["items"]], ["100"])
        self.assertIsNone(tail["next_cursor"])

    def test_restart_preserves_content_sequences_and_idempotency(self):
        body = br' {"unicode":"\u03bb"} '
        self.assertEqual(self.post("durable", body)[0], 201)
        before = self.page()[1]
        self.stop_server()
        self.start_server()
        self.assertEqual(self.page()[1], before)
        self.assertEqual(self.post("durable", body)[0], 200)
        self.assertEqual(self.post("durable", b"{}")[0], 409)
        self.assertEqual(self.post("next")[0], 201)
        self.assertGreater(self.page()[1]["items"][-1]["sequence"], before["items"][0]["sequence"])

    def test_concurrent_identical_and_conflicting_writes(self):
        for conflicting in (False, True):
            event = str(conflicting)
            barrier = threading.Barrier(8)
            bodies = [b'{"x":1}' if not conflicting or index % 2 else b'{ "x": 1 }' for index in range(8)]
            def submit(body):
                barrier.wait(timeout=10)
                return self.post(event, body)[0]
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
                statuses = list(executor.map(submit, bodies))
            self.assertEqual(statuses.count(201), 1)
            stored = next(row[2] for row in self.rows() if row[1] == event)
            self.assertEqual(statuses.count(200), bodies.count(stored) - 1)
            self.assertEqual(statuses.count(409), len(bodies) - bodies.count(stored))
        self.assertEqual(len(self.rows()), 2)

    def test_concurrent_distinct_tenants_and_reads(self):
        def submit(index):
            tenant = "alpha" if index % 2 else "beta"
            status = self.post(str(index), tenant=tenant)[0]
            self.assertEqual(self.page(tenant)[0], 200)
            return status
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            self.assertEqual(list(executor.map(submit, range(24))), [201] * 24)
        for tenant in ("alpha", "beta"):
            rows = self.page(tenant)[1]["items"]
            sequences = [row["sequence"] for row in rows]
            self.assertEqual(len(rows), 12)
            self.assertEqual(sequences, sorted(set(sequences)))
        with closing(sqlite3.connect(self.db)) as connection:
            self.assertEqual(connection.execute("PRAGMA integrity_check").fetchone(), ("ok",))

    def test_errors_do_not_disclose_credentials_or_signature(self):
        headers = self.signed()
        headers["X-Signature"] = "f" * 64
        status, result = self.post(headers=headers)
        self.assertEqual(status, 401)
        encoded = json.dumps(result)
        for credential in (*self.tenants["alpha"].values(), headers["X-Signature"]):
            self.assertNotIn(credential, encoded)

    def test_cli_readiness_help_and_real_port(self):
        script = Path(__file__).with_name("inbox.py")
        help_result = subprocess.run([sys.executable, str(script), "--help"], capture_output=True, timeout=5)
        self.assertEqual(help_result.returncode, 0)
        process = subprocess.Popen([sys.executable, str(script), "--db", str(self.root / "cli.sqlite3"),
                                    "--config", str(self.config), "--port", "0"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            lines = queue.Queue()
            reader = threading.Thread(target=lambda: lines.put(process.stdout.readline()), daemon=True)
            reader.start()
            ready = json.loads(lines.get(timeout=5))
            self.assertEqual(ready["host"], "127.0.0.1")
            self.assertGreater(ready["port"], 0)
            connection = http.client.HTTPConnection(ready["host"], ready["port"], timeout=5)
            try:
                connection.request("GET", "/health")
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read()), {"status": "ok"})
            finally:
                connection.close()
        finally:
            process.terminate()
            process.wait(timeout=5)
            process.stdout.close()
            process.stderr.close()


if __name__ == "__main__":
    unittest.main()
