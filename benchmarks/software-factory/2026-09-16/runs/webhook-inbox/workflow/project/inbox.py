"""Authenticated, durable, tenant-scoped webhook inbox (Python standard library)."""

import argparse
import hashlib
import hmac
import json
import re
import socket
import sqlite3
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

from inbox_store import EventStore


MAX_BODY = 65_536
MAX_SEQUENCE = 2**63 - 1
DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)\Z", re.ASCII)
HEADER_NAME = re.compile(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")


class RequestError(Exception):
    def __init__(self, status, message):
        self.status, self.message = status, message


class HeaderRecorder:
    """Retain header bytes; email's parser otherwise discards leading whitespace."""

    def __init__(self, stream):
        self.stream, self.lines = stream, []

    def readline(self, *args):
        line = self.stream.readline(*args)
        self.lines.append(line)
        return line


def reject_constant(value):
    raise ValueError("non-JSON numeric constant")


def parse_payload(body):
    try:
        # Validation must not coerce valid JSON numbers into overflowing floats
        # or apply Python's integer-string digit limit. Reads emit validated raw
        # JSON, so the numeric lexemes and precision are preserved.
        payload = json.loads(body.decode("utf-8"), parse_constant=reject_constant,
                             parse_int=str, parse_float=str)
    except (UnicodeError, ValueError, RecursionError):
        raise RequestError(400, "invalid JSON object") from None
    if not isinstance(payload, dict):
        raise RequestError(400, "invalid JSON object")
    return payload


def load_config(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    tenants = value.get("tenants") if isinstance(value, dict) else None
    if not isinstance(tenants, dict) or not tenants:
        raise ValueError("configuration requires tenants")
    result = {}
    for name, credentials in tenants.items():
        if not re.fullmatch(r"[A-Za-z0-9_-]+", name) or not isinstance(credentials, dict):
            raise ValueError("invalid tenant configuration")
        if any(not isinstance(credentials.get(key), str) or not credentials[key]
               for key in ("secret", "token")):
            raise ValueError("tenant credentials must be nonempty strings")
        try:
            result[name] = {key: credentials[key].encode("utf-8") for key in ("secret", "token")}
        except UnicodeError:
            raise ValueError("tenant credentials must be valid UTF-8") from None
    return result


class InboxHandler(BaseHTTPRequestHandler):
    # Close every connection, including validation failures with unread bodies.
    protocol_version = "HTTP/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def parse_request(self):
        stream = self.rfile
        recorder = HeaderRecorder(stream)
        self.rfile = recorder
        try:
            success = super().parse_request()
        finally:
            self.rfile = stream
        if not success:
            return False
        self.raw_headers = {}
        for line in recorder.lines:
            if line in (b"\r\n", b"\n", b""):
                continue
            line = line.removesuffix(b"\n").removesuffix(b"\r")
            name, sep, value = line.partition(b":")
            if not sep or not HEADER_NAME.fullmatch(name):
                self.send_error(400)
                return False
            # One ordinary separator space is framing; further whitespace stays
            # in the value and is checked by each header's exact grammar.
            if value.startswith(b" "):
                value = value[1:]
            self.raw_headers.setdefault(name.lower(), []).append(value.decode("latin-1"))
        return True

    def _json(self, status, value):
        body = json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        self._json_bytes(status, body)

    def _json_bytes(self, status, body):
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def send_error(self, code, message=None, explain=None):
        # Never echo an attacker-controlled request line or a header value.
        self._json(code, {"error": self.responses.get(code, ("request rejected",))[0]})

    def _header(self, name, status=400):
        values = self.raw_headers.get(name.lower().encode("ascii"), [])
        if len(values) != 1:
            raise RequestError(status, "invalid required header")
        return values[0]

    def _route(self, prefix):
        try:
            url = urlsplit(self.path)
        except ValueError:
            raise RequestError(404, "not found") from None
        if url.scheme or url.netloc or url.fragment or not url.path.startswith(prefix):
            raise RequestError(404, "not found")
        tenant = url.path[len(prefix):]
        if tenant not in self.server.tenants:
            raise RequestError(404, "not found")
        return tenant, url.query

    def _run(self, action):
        try:
            action()
        except RequestError as error:
            self._json(error.status, {"error": error.message})
        except sqlite3.Error:
            self._json(503, {"error": "storage unavailable"})
        except (socket.timeout, TimeoutError):
            self._json(400, {"error": "incomplete request body"})
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        self._run(self._get)

    def _get(self):
        if self.path == "/health":
            self._json(200, {"status": "ok"})
            return
        tenant, query = self._route("/events/")
        auth = self._header("authorization", 401)
        if not auth.startswith("Bearer ") or not hmac.compare_digest(
            auth[7:].encode("latin-1"), self.server.tenants[tenant]["token"]
        ):
            raise RequestError(401, "unauthorized")
        try:
            pairs = parse_qsl(query, keep_blank_values=True, strict_parsing=True,
                              encoding="utf-8", errors="strict", max_num_fields=2)
        except (ValueError, UnicodeError):
            raise RequestError(400, "invalid query") from None
        values = {}
        for key, value in pairs:
            if key not in ("limit", "cursor") or key in values or not DECIMAL.fullmatch(value):
                raise RequestError(400, "invalid query")
            values[key] = value
        limit_text = values.get("limit", "50")
        if len(limit_text) > 3 or not 1 <= int(limit_text) <= 100:
            raise RequestError(400, "invalid limit")
        cursor_text = values.get("cursor", "0")
        cursor = MAX_SEQUENCE if len(cursor_text) > 19 else min(int(cursor_text), MAX_SEQUENCE)
        rows = self.server.store.page(tenant, cursor, int(limit_text))
        more = len(rows) > int(limit_text)
        visible = rows[:int(limit_text)]
        items = []
        for sequence, event_id, raw_body in visible:
            parse_payload(raw_body)
            prefix = json.dumps({"sequence": sequence, "event_id": event_id},
                                ensure_ascii=True, separators=(",", ":")).encode("utf-8")
            items.append(prefix[:-1] + b',"payload":' + raw_body + b"}")
        cursor_json = json.dumps(str(visible[-1][0]) if more else None).encode("ascii")
        self._json_bytes(200, b'{"items":[' + b",".join(items) + b'],"next_cursor":' + cursor_json + b"}")

    def do_POST(self):
        self._run(self._post)

    def _post(self):
        tenant, query = self._route("/webhooks/")
        if query:
            raise RequestError(400, "invalid query")
        if b"transfer-encoding" in self.raw_headers:
            raise RequestError(400, "unsupported body framing")
        length = self._header("content-length")
        if not re.fullmatch(r"[0-9]+", length, re.ASCII):
            raise RequestError(400, "invalid content length")
        significant_length = length.lstrip("0") or "0"
        if len(significant_length) > 5 or int(significant_length) > MAX_BODY:
            raise RequestError(413, "body too large")
        event_id = self._header("x-event-id")
        if (not 1 <= len(event_id) <= 128 or event_id != event_id.strip()
                or any(ord(char) < 32 or ord(char) > 126 for char in event_id)):
            raise RequestError(400, "invalid event ID")
        timestamp = self._header("x-timestamp")
        if not DECIMAL.fullmatch(timestamp):
            raise RequestError(400, "invalid timestamp")
        signature = self._header("x-signature")
        if not re.fullmatch(r"[0-9a-f]{64}", signature, re.ASCII):
            raise RequestError(400, "invalid signature")
        if len(timestamp) > 20:
            raise RequestError(401, "unauthorized")
        body = self.rfile.read(int(significant_length))
        if len(body) != int(significant_length):
            raise RequestError(400, "incomplete request body")
        if abs(int(time.time()) - int(timestamp)) > 300:
            raise RequestError(401, "unauthorized")
        expected = hmac.new(self.server.tenants[tenant]["secret"],
                            timestamp.encode("ascii") + b"." + body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise RequestError(401, "unauthorized")
        parse_payload(body)
        outcome = self.server.store.insert(tenant, event_id, body)
        if outcome == "conflict":
            raise RequestError(409, "event ID already has different content")
        self._json(200 if outcome == "duplicate" else 201,
                   {"event_id": event_id, "duplicate": outcome == "duplicate"})

    def log_message(self, format, *args):
        pass


class InboxServer(ThreadingHTTPServer):
    daemon_threads = False  # server_close waits for in-flight requests to finish.
    request_queue_size = 128


def create_server(db_path, config_path, host="127.0.0.1", port=0):
    tenants = load_config(config_path)
    store = EventStore(Path(db_path))
    server = InboxServer((host, port), InboxHandler)
    server.db_path = str(Path(db_path))
    server.tenants, server.store = tenants, store
    return server


def main():
    parser = argparse.ArgumentParser(description="Run the webhook inbox")
    parser.add_argument("--db", required=True, help="SQLite database path")
    parser.add_argument("--config", required=True, help="Tenant configuration JSON")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args()
    server = create_server(args.db, args.config, args.host, args.port)
    print(json.dumps({"host": server.server_address[0], "port": server.server_address[1]}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
