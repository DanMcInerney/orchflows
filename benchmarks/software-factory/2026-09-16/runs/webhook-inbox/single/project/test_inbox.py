"""Adversarial contract, concurrency, durability, and CLI checks."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import hashlib
import hmac
import http.client
import json
from pathlib import Path
import queue
import random
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from inbox import _validate_object, create_server


class InboxTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db_path = self.root / "inbox.sqlite3"
        self.config_path = self.root / "config.json"
        self.credentials = {
            "alpha": {"secret": "alpha-secret-\u00e9", "token": "alpha-token"},
            "beta": {"secret": "beta-secret", "token": "beta-token"},
            "Case_1-X": {"secret": "case-secret", "token": "CaseToken"},
        }
        self.config_path.write_text(json.dumps({"tenants": self.credentials}), encoding="utf-8")
        self.running = []
        self.server = self.start_server()

    def start_server(self):
        server = create_server(self.db_path, self.config_path)
        thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01), daemon=True)
        thread.start()
        self.running.append((server, thread))
        return server

    def stop_server(self, server):
        for pair in list(self.running):
            if pair[0] is server:
                server.shutdown()
                server.server_close()
                pair[1].join(timeout=3)
                self.assertFalse(pair[1].is_alive())
                self.running.remove(pair)

    def tearDown(self):
        for server, _ in list(self.running):
            self.stop_server(server)
        self.temp.cleanup()

    def request(self, method, path, body=None, headers=None, server=None):
        connection = http.client.HTTPConnection(*(server or self.server).server_address, timeout=10)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            raw = response.read()
            self.assertEqual(response.getheader("Content-Type"), "application/json; charset=utf-8")
            self.assertEqual(int(response.getheader("Content-Length")), len(raw))
            payload = json.loads(raw)
            self.assertIsInstance(payload, dict)
            return response.status, payload
        finally:
            connection.close()

    def headers(self, tenant="alpha", body=b'{}', event_id="event", timestamp=None):
        timestamp = str(int(time.time())) if timestamp is None else timestamp
        secret = self.credentials[tenant]["secret"].encode("utf-8")
        signature = hmac.new(secret, timestamp.encode("ascii") + b"." + body, hashlib.sha256).hexdigest()
        return {"X-Event-ID": event_id, "X-Timestamp": timestamp, "X-Signature": signature}

    def post(self, event_id="event", body=b'{}', tenant="alpha", timestamp=None, server=None):
        return self.request("POST", "/webhooks/" + tenant, body,
                            self.headers(tenant, body, event_id, timestamp), server)

    def page(self, tenant="alpha", query="", server=None):
        return self.request("GET", "/events/" + tenant + query,
                            headers={"Authorization": "Bearer " + self.credentials[tenant]["token"]},
                            server=server)

    def rows(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            return db.execute("SELECT sequence, tenant, event_id, body FROM events ORDER BY sequence").fetchall()

    def raw_request(self, method, path, headers, body=b''):
        wire = f"{method} {path} HTTP/1.1\r\nHost: localhost\r\n".encode("ascii")
        wire += b''.join(name.encode("ascii") + b": " + value.encode("latin-1") + b"\r\n"
                         for name, value in headers)
        wire += b"\r\n" + body
        with socket.create_connection(self.server.server_address, timeout=5) as sock:
            sock.sendall(wire)
            sock.shutdown(socket.SHUT_WR)
            response = http.client.HTTPResponse(sock)
            response.begin()
            value = json.loads(response.read())
            self.assertIsInstance(value, dict)
            return response.status, value

    def test_health_unknown_routes_and_json_errors(self):
        self.assertEqual(self.request("GET", "/health"), (200, {"status": "ok"}))
        self.assertEqual(self.rows(), [])
        for method, path in [("GET", "/"), ("GET", "/events/Alpha"),
                             ("GET", "/events/alpha/extra"), ("POST", "/webhooks/missing"),
                             ("POST", "/webhooks/alpha/extra"), ("POST", "/other")]:
            with self.subTest(method=method, path=path):
                self.assertEqual(self.request(method, path)[0], 404)
        self.assertEqual(self.request("PUT", "/health")[0], 501)
        self.assertEqual(self.server.server_address[0], "127.0.0.1")
        self.assertGreater(self.server.server_address[1], 0)

    def test_body_is_exact_and_sql_looking_id_is_data(self):
        body = '  {"greeting": "h\u00e9llo", "quote": "\\\""}\n'.encode("utf-8")
        event_id = "x'); DROP TABLE events; -- \\\""
        self.assertEqual(self.post(event_id, body), (201, {"event_id": event_id, "duplicate": False}))
        self.assertEqual(self.post(event_id, body), (200, {"event_id": event_id, "duplicate": True}))
        self.assertEqual(self.rows()[0][2:], (event_id, body))
        self.assertEqual(self.page()[1]["items"][0]["payload"], json.loads(body))

    def test_retry_conflict_and_sequence_stability(self):
        self.assertEqual(self.post("z", b'{"a":1}')[0], 201)
        before = self.rows()
        self.assertEqual(self.post("z", b'{ "a": 1 }')[0], 409)
        self.assertEqual(self.post("z", b'{"a":1}')[0], 200)
        self.assertEqual(self.rows(), before)
        self.assertEqual(self.post("a")[0], 201)
        items = self.page()[1]["items"]
        self.assertEqual([item["event_id"] for item in items], ["z", "a"])
        self.assertLess(items[0]["sequence"], items[1]["sequence"])

    def test_post_authentication_failures_do_not_reserve_ids(self):
        good = self.headers()
        cases = []
        for missing in good:
            cases.append(({key: value for key, value in good.items() if key != missing}, 400))
        for signature in ["", "A" * 64, "f" * 63, "f" * 65, "g" * 64, " " + good["X-Signature"]]:
            cases.append(({**good, "X-Signature": signature}, 400))
        cases.extend([({**good, "X-Signature": "0" * 64}, 401),
                      (self.headers("beta"), 401),
                      (self.headers(timestamp=str(int(time.time()) - 301)), 401),
                      (self.headers(timestamp=str(int(time.time()) + 1000)), 401)])
        for headers, status in cases:
            with self.subTest(headers=list(headers), status=status):
                self.assertEqual(self.request("POST", "/webhooks/alpha", b'{}', headers)[0], status)
                self.assertEqual(self.rows(), [])
        self.assertEqual(self.post()[0], 201)

    def test_duplicate_rechecks_signature_and_timestamp(self):
        self.assertEqual(self.post()[0], 201)
        before = self.rows()
        for headers in [{**self.headers(), "X-Signature": "0" * 64},
                        self.headers(timestamp=str(int(time.time()) - 301))]:
            self.assertEqual(self.request("POST", "/webhooks/alpha", b'{}', headers)[0], 401)
            self.assertEqual(self.rows(), before)

    def test_exact_timestamp_boundaries(self):
        now = 1_800_000_000
        with patch("inbox.time.time", return_value=now):
            for delta, expected in [(-301, 401), (-300, 201), (0, 201), (300, 201), (301, 401)]:
                with self.subTest(delta=delta):
                    self.assertEqual(self.post(str(delta), timestamp=str(now + delta))[0], expected)
        self.assertEqual(len(self.rows()), 3)

    def test_malformed_timestamp_and_id_headers(self):
        for value in ["", "00", "01", "+1", "-1", " 1", "1 ", "1.0", "1e9", "\t1", "1\t"]:
            headers = {**self.headers(), "X-Timestamp": value}
            with self.subTest(timestamp=value):
                self.assertEqual(self.request("POST", "/webhooks/alpha", b'{}', headers)[0], 400)
        for value in ["", "x" * 129, " leading", "trailing ", "a\tb", "a\x7fb", "\u00e9"]:
            with self.subTest(event_id=value):
                self.assertEqual(self.post(value)[0], 400)
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.post("x" * 128)[0], 201)

    def test_content_length_and_repeated_headers(self):
        base = list(self.headers().items())
        for length in [None, "", "-1", "+2", "2.0", " 2", "2 ", "0x2", "\t2", "two"]:
            headers = base if length is None else base + [("Content-Length", length)]
            with self.subTest(length=length):
                self.assertEqual(self.raw_request("POST", "/webhooks/alpha", headers, b'{}')[0], 400)
        for name, value in base + [("Content-Length", "2")]:
            headers = base + [("Content-Length", "2"), (name, value)]
            with self.subTest(duplicate=name):
                self.assertEqual(self.raw_request("POST", "/webhooks/alpha", headers, b'{}')[0], 400)
        self.assertEqual(self.raw_request("POST", "/webhooks/alpha", base + [("Content-Length", "2"),
                        ("Transfer-Encoding", "chunked")], b'{}')[0], 400)
        self.assertEqual(self.rows(), [])
        self.assertEqual(self.raw_request("POST", "/webhooks/alpha", base + [("Content-Length", "0002")], b'{}')[0], 201)

    def test_truncated_body_has_no_effect(self):
        self.assertEqual(self.raw_request("POST", "/webhooks/alpha", list(self.headers().items()) +
                        [("Content-Length", "20")], b'{}')[0], 400)
        self.assertEqual(self.rows(), [])

    def test_body_size_boundary_and_oversized_length(self):
        body = b'{"x":"' + b'a' * (65536 - 8) + b'"}'
        self.assertEqual(len(body), 65536)
        self.assertEqual(self.post("max", body)[0], 201)
        before = self.rows()
        self.assertEqual(self.post("over", body + b' ')[0], 413)
        headers = list(self.headers().items()) + [("Content-Length", "9" * 5000)]
        self.assertEqual(self.raw_request("POST", "/webhooks/alpha", headers)[0], 413)
        self.assertEqual(self.rows(), before)

    def test_invalid_json_has_no_effect(self):
        for body in [b'', b'[]', b'1', b'"string"', b'true', b'null', b'{', b'{"x":1,}',
                     b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}', b'{"x":"\xff"}',
                     b'\xef\xbb\xbf{}', b'{} trailing', b'{"x":[1,]}', b'{"x":01}', b'{"x":1.}',
                     b'{"x":+1}', b'{"x":1e}', b'{"x":tru}', b'{"x":"\\q"}', b'{"x":"\x01"}',
                     b'{"x" 1}', b'{"x":}', b'{"x": {"y":1} "z":2}', b'{"x": [1 2]}']:
            with self.subTest(body=body[:30]):
                self.assertEqual(self.post(body=body)[0], 400)
                self.assertEqual(self.rows(), [])
        self.assertEqual(self.post()[0], 201)

    def test_deep_valid_json_does_not_depend_on_python_recursion_limit(self):
        body = b'{"nested":' + b'[' * 15000 + b'0' + b']' * 15000 + b'}'
        self.assertEqual(self.post("deep", body)[0], 201)
        self.assertEqual(self.post("deep", body)[0], 200)
        self.assertEqual(self.rows()[0][3], body)
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.request("GET", "/events/alpha", headers={"Authorization": "Bearer alpha-token"})
            response = connection.getresponse()
            self.assertEqual(response.status, 200)
            self.assertIn(b'"payload":' + body, response.read())
        finally:
            connection.close()

    def test_valid_large_numbers_remain_json_numbers(self):
        body = b'{"big":' + b'9' * 5000 + b',"exponent":1e1000,"escaped":"\\ud800"}'
        self.assertEqual(self.post(body=body)[0], 201)
        connection = http.client.HTTPConnection(*self.server.server_address, timeout=5)
        try:
            connection.request("GET", "/events/alpha", headers={"Authorization": "Bearer alpha-token"})
            response = connection.getresponse()
            raw = response.read()
            self.assertEqual(response.status, 200)
            parsed = json.loads(raw, parse_int=str, parse_float=str)
            self.assertEqual(parsed["items"][0]["payload"]["big"], "9" * 5000)
            self.assertEqual(parsed["items"][0]["payload"]["exponent"], "1e1000")
        finally:
            connection.close()

    def test_read_authorization_and_tenant_case(self):
        self.post()
        for value in [None, "", "alpha-token", "bearer alpha-token", "Bearer", "Bearer ",
                      "Bearer  alpha-token", "Bearer alpha-token ", "Bearer beta-token", "Bearer ALPHA-TOKEN"]:
            headers = {} if value is None else {"Authorization": value}
            with self.subTest(value=value):
                status, result = self.request("GET", "/events/alpha", headers=headers)
                self.assertEqual(status, 401)
                self.assertNotIn("items", result)
                self.assertNotIn("alpha-token", json.dumps(result))
        self.assertEqual(self.raw_request("GET", "/events/alpha", [("Authorization", "Bearer alpha-token")] * 2)[0], 401)
        self.assertEqual(self.post(tenant="Case_1-X")[0], 201)
        self.assertEqual(self.page("Case_1-X")[0], 200)
        self.assertEqual(self.request("GET", "/events/case_1-x")[0], 404)

    def test_cross_tenant_ids_signatures_and_cursors(self):
        self.assertEqual(self.post("shared", b'{"alpha":1}')[0], 201)
        self.assertEqual(self.post("shared", b'{"beta":1}', "beta")[0], 201)
        self.assertEqual(self.post("later", tenant="alpha")[0], 201)
        alpha = self.page()[1]["items"]
        beta = self.page("beta")[1]["items"]
        self.assertEqual(alpha[0]["payload"], {"alpha": 1})
        self.assertEqual(beta[0]["payload"], {"beta": 1})
        cursor = beta[0]["sequence"]
        filtered = self.page(query=f"?cursor={cursor}")[1]["items"]
        self.assertEqual([item["event_id"] for item in filtered], ["later"])
        self.assertEqual(self.page("beta", f"?cursor={alpha[-1]['sequence']}")[1], {"items": [], "next_cursor": None})
        wrong = self.headers("alpha", b'{"beta":2}', "wrong")
        self.assertEqual(self.request("POST", "/webhooks/beta", b'{"beta":2}', wrong)[0], 401)
        self.assertEqual(len(self.rows()), 3)

    def test_pagination_defaults_boundaries_and_replay(self):
        for index in range(101):
            self.assertEqual(self.post(f"id-{101 - index:03}", json.dumps({"i": index}).encode())[0], 201)
        status, page = self.page()
        self.assertEqual(status, 200)
        self.assertEqual(len(page["items"]), 50)
        self.assertEqual(page["next_cursor"], str(page["items"][-1]["sequence"]))
        self.assertEqual(self.page()[1], page)
        second = self.page(query="?cursor=" + page["next_cursor"])[1]
        third = self.page(query="?cursor=" + second["next_cursor"])[1]
        self.assertEqual(len(second["items"]), 50)
        self.assertEqual(len(third["items"]), 1)
        self.assertIsNone(third["next_cursor"])
        all_items = page["items"] + second["items"] + third["items"]
        self.assertEqual([item["payload"]["i"] for item in all_items], list(range(101)))
        sequences = [item["sequence"] for item in all_items]
        self.assertEqual(sequences, sorted(set(sequences)))
        self.assertTrue(all(isinstance(value, int) and value > 0 for value in sequences))
        self.assertEqual(len(self.page(query="?limit=100")[1]["items"]), 100)
        self.assertEqual(len(self.page(query="?limit=1&cursor=0")[1]["items"]), 1)
        self.assertEqual(self.page(query=f"?cursor={sequences[-1]}")[1], {"items": [], "next_cursor": None})
        for cursor in ["9223372036854775808", "9" * 5000]:
            self.assertEqual(self.page(query="?cursor=" + cursor)[1], {"items": [], "next_cursor": None})

    def test_invalid_queries(self):
        self.post()
        before = self.rows()
        queries = ["limit=0", "limit=101", "limit=01", "limit=+1", "limit=-1", "limit=1.0", "limit=",
                   "cursor=", "cursor=00", "cursor=01", "cursor=-1", "cursor=+1", "cursor=1.0",
                   "cursor=%201", "cursor=1%20", "limit=1&limit=2", "cursor=0&cursor=1", "unknown=1",
                   "limit=1&cursor=0&other=1", "limit", "cursor=%ZZ", "cursor=%FF", "cursor=%",
                   "cursor=0&&limit=1", "cursor=0&", "limit=1;cursor=0", "limit=%D9%A1"]
        for query in queries:
            with self.subTest(query=query):
                self.assertEqual(self.page(query="?" + query)[0], 400)
        self.assertEqual(self.rows(), before)

    def test_restart_persists_raw_body_sequence_and_idempotency(self):
        body = b' {"persist": true}\n'
        self.assertEqual(self.post("stable", body)[0], 201)
        before = self.rows()
        page = self.page()[1]
        self.stop_server(self.server)
        self.server = self.start_server()
        self.assertEqual(self.rows(), before)
        self.assertEqual(self.page()[1], page)
        self.assertEqual(self.post("stable", body)[0], 200)
        self.assertEqual(self.post("stable", b'{"persist":true}')[0], 409)
        self.assertEqual(self.post("new")[0], 201)
        self.assertGreater(self.rows()[-1][0], before[-1][0])
        with closing(sqlite3.connect(self.db_path)) as db:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone(), ("ok",))

    def test_storage_failure_rolls_back_without_reserving_id(self):
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute("CREATE TRIGGER fail_insert BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT, 'test'); END")
        self.assertEqual(self.post()[0], 503)
        self.assertEqual(self.rows(), [])
        with closing(sqlite3.connect(self.db_path)) as db:
            db.execute("DROP TRIGGER fail_insert")
        self.assertEqual(self.post()[0], 201)

    def run_simultaneously(self, operations):
        barrier = threading.Barrier(len(operations))
        def run(operation):
            barrier.wait(timeout=10)
            return operation()
        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            return list(pool.map(run, operations))

    def test_concurrent_identical_retries(self):
        results = self.run_simultaneously([lambda: self.post("race")] * 24)
        statuses = [status for status, _ in results]
        self.assertEqual(statuses.count(201), 1)
        self.assertEqual(statuses.count(200), 23)
        self.assertEqual(len(self.rows()), 1)

    def test_concurrent_conflicts_across_two_servers(self):
        second = self.start_server()
        operations = []
        bodies = [b'{"a":1}', b'{"a":2}']
        for index in range(24):
            body = bodies[index % 2]
            server = self.server if index % 3 else second
            operations.append(lambda body=body, server=server: self.post("race", body, server=server))
        results = self.run_simultaneously(operations)
        statuses = [status for status, _ in results]
        self.assertEqual(statuses.count(201), 1)
        self.assertEqual(statuses.count(200), 11)
        self.assertEqual(statuses.count(409), 12)
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.page(server=second), self.page())

    def test_concurrent_tenants_have_independent_ids(self):
        operations = [lambda i=i, tenant=tenant: self.post(str(i), tenant=tenant)
                      for i in range(12) for tenant in ("alpha", "beta")]
        results = self.run_simultaneously(operations)
        self.assertTrue(all(status == 201 for status, _ in results))
        self.assertEqual(len(self.rows()), 24)
        for tenant in ("alpha", "beta"):
            items = self.page(tenant)[1]["items"]
            self.assertEqual({item["event_id"] for item in items}, {str(i) for i in range(12)})
            self.assertEqual([item["sequence"] for item in items], sorted(item["sequence"] for item in items))

    def test_cli_help_and_readiness(self):
        script = str(Path(__file__).with_name("inbox.py"))
        help_result = subprocess.run([sys.executable, script, "--help"], capture_output=True, text=True, timeout=5)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("--db", help_result.stdout)
        self.assertIn("--config", help_result.stdout)
        process = subprocess.Popen([sys.executable, script, "--db", str(self.root / "cli.sqlite3"),
                                    "--config", str(self.config_path), "--port", "0"],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output = queue.Queue()
        reader = threading.Thread(target=lambda: output.put(process.stdout.readline()), daemon=True)
        reader.start()
        try:
            line = output.get(timeout=5)
            readiness = json.loads(line)
            self.assertEqual(readiness["host"], "127.0.0.1")
            self.assertGreater(readiness["port"], 0)
            connection = http.client.HTTPConnection(readiness["host"], readiness["port"], timeout=5)
            try:
                connection.request("GET", "/health")
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                self.assertEqual(json.loads(response.read()), {"status": "ok"})
                connection.request("POST", "/webhooks/alpha", body=b'{}',
                                   headers=self.headers(event_id="process-restart"))
                response = connection.getresponse()
                self.assertEqual(response.status, 201)
                self.assertFalse(json.loads(response.read())["duplicate"])
            finally:
                connection.close()
        finally:
            process.terminate()
            remaining_stdout, stderr = process.communicate(timeout=5)
            reader.join(timeout=3)
        self.assertEqual(remaining_stdout, "")
        self.assertEqual(stderr, "")
        restarted = create_server(self.root / "cli.sqlite3", self.config_path)
        thread = threading.Thread(target=lambda: restarted.serve_forever(poll_interval=0.01), daemon=True)
        thread.start()
        self.running.append((restarted, thread))
        self.assertEqual(self.page(server=restarted)[1]["items"][0]["event_id"], "process-restart")
        self.assertEqual(self.post("process-restart", server=restarted)[0], 200)


class JsonValidationTests(unittest.TestCase):
    def test_generated_json_and_mutations_match_standard_parser(self):
        randomizer = random.Random(1679)
        atoms = [None, True, False, 0, -1, 1.25, "", 'quote" slash\\', "\u00e9\n\t", []]

        def value(depth=0):
            if depth == 4 or randomizer.randrange(3) == 0:
                return randomizer.choice(atoms)
            if randomizer.randrange(2):
                return [value(depth + 1) for _ in range(randomizer.randrange(4))]
            return {str(index): value(depth + 1) for index in range(randomizer.randrange(4))}

        def reject_constant(_):
            raise ValueError("not standard JSON")

        def accepted_by_standard(raw):
            try:
                return isinstance(json.loads(raw.decode("utf-8"), parse_constant=reject_constant), dict)
            except (ValueError, UnicodeDecodeError):
                return False

        def accepted_by_inbox(raw):
            try:
                _validate_object(raw)
                return True
            except (ValueError, UnicodeDecodeError):
                return False

        for _ in range(1000):
            raw = json.dumps({"root": value()}, ensure_ascii=randomizer.choice([True, False])).encode("utf-8")
            self.assertTrue(accepted_by_inbox(raw))
            for _ in range(3):
                position = randomizer.randrange(len(raw))
                replacement = randomizer.choice(b'{}[],:"\\0+-aetfn \t\r\n\x00\xff')
                mutated = raw[:position] + bytes([replacement]) + raw[position + 1:]
                self.assertEqual(accepted_by_inbox(mutated), accepted_by_standard(mutated), repr(mutated))


if __name__ == "__main__":
    unittest.main()
