"""A durable, tenant-isolated webhook inbox using only the standard library."""

import argparse
from contextlib import closing
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import socket
import sqlite3
import time
from urllib.parse import parse_qsl, urlsplit


MAX_BODY = 65_536
DECIMAL = re.compile(r"(?:0|[1-9][0-9]*)\Z", re.ASCII)
TENANT = re.compile(r"[A-Za-z0-9_-]+\Z", re.ASCII)
SIGNATURE = re.compile(r"[0-9a-f]{64}\Z", re.ASCII)
JSON_NUMBER = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?", re.ASCII)


class RequestError(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message


class _HeaderReader:
    """Retain header octets before the email parser strips value whitespace."""

    def __init__(self, stream):
        self.stream = stream
        self.lines = []

    def readline(self, *args):
        line = self.stream.readline(*args)
        self.lines.append(line)
        return line


def _validate_object(raw):
    """Validate JSON iteratively, without recursion or numeric conversion.

    The byte limit bounds the stack. Use the standard JSON string scanner for
    escaping/control-character rules, and retain raw JSON for exact storage.
    """
    source = raw.decode("utf-8")
    length = len(source)
    index = 0

    def whitespace(position):
        while position < length and source[position] in " \t\r\n":
            position += 1
        return position

    index = whitespace(index)
    if index == length or source[index] != "{":
        raise ValueError("body must be an object")
    index += 1
    states = ["key_or_end"]
    while states:
        index = whitespace(index)
        if index == length:
            raise ValueError("incomplete JSON")
        character = source[index]
        state = states[-1]
        if state in ("key_or_end", "key"):
            if character == "}" and state == "key_or_end":
                states.pop()
                index += 1
            elif character == '"':
                _, index = json.decoder.scanstring(source, index + 1, True)
                states[-1] = "colon"
            else:
                raise ValueError("expected an object key")
        elif state == "colon":
            if character != ":":
                raise ValueError("expected a colon")
            index += 1
            states[-1] = "object_value"
        elif state in ("object_comma", "array_comma"):
            closing = "}" if state == "object_comma" else "]"
            if character == closing:
                states.pop()
            elif character == ",":
                states[-1] = "key" if state == "object_comma" else "array_value"
            else:
                raise ValueError("expected a comma or closing delimiter")
            index += 1
        elif state == "array_first" and character == "]":
            states.pop()
            index += 1
        else:
            states[-1] = "object_comma" if state == "object_value" else "array_comma"
            if character in "{[":
                states.append("key_or_end" if character == "{" else "array_first")
                index += 1
            elif character == '"':
                _, index = json.decoder.scanstring(source, index + 1, True)
            elif source.startswith(("true", "null"), index):
                index += 4
            elif source.startswith("false", index):
                index += 5
            else:
                number = JSON_NUMBER.match(source, index)
                if number is None:
                    raise ValueError("expected a JSON value")
                index = number.end()
    if whitespace(index) != length:
        raise ValueError("trailing data")


def _connect(path):
    connection = sqlite3.connect(path, timeout=10, isolation_level=None)
    connection.execute("PRAGMA synchronous = FULL")
    return connection


class InboxHandler(BaseHTTPRequestHandler):
    # Each response closes the connection; rejected bodies cannot be mistaken
    # for another request. Threads have a bounded idle/read timeout.
    protocol_version = "HTTP/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def parse_request(self):
        original = self.rfile
        captured = _HeaderReader(original)
        self.rfile = captured
        try:
            parsed = super().parse_request()
        finally:
            self.rfile = original
        if not parsed:
            return False
        self.raw_headers = {}
        for line in captured.lines:
            if line in (b"\r\n", b"\n", b""):
                break
            if line[:1] in (b" ", b"\t") or b":" not in line:
                self._json(400, {"error": "malformed headers"})
                return False
            name, value = line.rstrip(b"\r\n").split(b":", 1)
            if not re.fullmatch(rb"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name):
                self._json(400, {"error": "malformed headers"})
                return False
            # Permit the conventional single separator space, but do not erase
            # whitespace that is part of an event ID or authentication value.
            if value.startswith(b" "):
                value = value[1:]
            self.raw_headers.setdefault(name.decode("ascii").lower(), []).append(
                value.decode("latin-1"))
        return True

    def _header(self, name, status=400):
        values = self.raw_headers.get(name.lower(), [])
        if len(values) != 1:
            raise RequestError(status, "missing or repeated required header")
        return values[0]

    def _bytes(self, status, body):
        self.close_connection = True
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status, value):
        self._bytes(status, json.dumps(value, ensure_ascii=True,
                                      allow_nan=False).encode("utf-8"))

    def send_error(self, code, message=None, explain=None):
        # HTTP parser/method errors use the same credential-free JSON format.
        self._json(code, {"error": self.responses.get(code, ("request error",))[0]})

    def _route(self, prefix):
        try:
            target = urlsplit(self.path)
        except ValueError:
            raise RequestError(400, "malformed request target") from None
        if target.scheme or target.netloc or target.fragment:
            raise RequestError(400, "malformed request target")
        if not target.path.startswith(prefix):
            raise RequestError(404, "not found")
        tenant = target.path[len(prefix):]
        if not TENANT.fullmatch(tenant) or tenant not in self.server.tenants:
            raise RequestError(404, "not found")
        return tenant, target.query

    def do_GET(self):
        self._handle(self._get)

    def do_POST(self):
        self._handle(self._post)

    def _handle(self, action):
        try:
            action()
        except RequestError as error:
            self._json(error.status, {"error": error.message})
        except (socket.timeout, TimeoutError):
            self._json(400, {"error": "incomplete request body"})
        except sqlite3.Error:
            self._json(503, {"error": "storage unavailable"})
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _post(self):
        tenant, query = self._route("/webhooks/")
        if query:
            raise RequestError(400, "unsupported query parameters")
        if "transfer-encoding" in self.raw_headers:
            raise RequestError(400, "unsupported transfer encoding")
        length_text = self._header("Content-Length")
        if not re.fullmatch(r"[0-9]+", length_text, re.ASCII):
            raise RequestError(400, "invalid content length")
        # Bound decimal conversion as well as allocation for hostile headers.
        normalized_length = length_text.lstrip("0") or "0"
        if len(normalized_length) > 5 or int(normalized_length) > MAX_BODY:
            raise RequestError(413, "body too large")
        length = int(normalized_length)
        event_id = self._header("X-Event-ID")
        if (not 1 <= len(event_id) <= 128 or event_id != event_id.strip()
                or any(ord(c) < 0x20 or ord(c) > 0x7e for c in event_id)):
            raise RequestError(400, "invalid event ID")
        timestamp = self._header("X-Timestamp")
        if not DECIMAL.fullmatch(timestamp):
            raise RequestError(400, "invalid timestamp")
        signature = self._header("X-Signature")
        if not SIGNATURE.fullmatch(signature):
            raise RequestError(400, "invalid signature format")
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise RequestError(400, "incomplete request body")
        now = int(time.time())
        if len(timestamp) > max(len(str(now)), 1) + 1 or abs(int(timestamp) - now) > 300:
            raise RequestError(401, "authentication failed")
        expected = hmac.new(self.server.tenants[tenant]["secret"],
                            timestamp.encode("ascii") + b"." + raw,
                            hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise RequestError(401, "authentication failed")
        try:
            _validate_object(raw)
        except (UnicodeDecodeError, ValueError, RecursionError):
            raise RequestError(400, "body must be a UTF-8 JSON object") from None

        with closing(_connect(self.server.db_path)) as db:
            # Serialize read/insert together. The UNIQUE constraint additionally
            # enforces idempotency across connections and server processes.
            db.execute("BEGIN IMMEDIATE")
            try:
                row = db.execute(
                    "SELECT body FROM events WHERE tenant = ? AND event_id = ?",
                    (tenant, event_id)).fetchone()
                if row is not None:
                    if row[0] != raw:
                        raise RequestError(409, "event ID has a different body")
                    duplicate = True
                else:
                    db.execute("INSERT INTO events (tenant, event_id, body) VALUES (?, ?, ?)",
                               (tenant, event_id, sqlite3.Binary(raw)))
                    duplicate = False
                db.commit()
            except BaseException:
                db.rollback()
                raise
        self._json(200 if duplicate else 201,
                   {"event_id": event_id, "duplicate": duplicate})

    def _get(self):
        if self.path == "/health":
            self._json(200, {"status": "ok"})
            return
        tenant, query = self._route("/events/")
        authorization = self._header("Authorization", status=401)
        expected = b"Bearer " + self.server.tenants[tenant]["token"]
        if not hmac.compare_digest(authorization.encode("utf-8"), expected):
            raise RequestError(401, "authentication failed")
        if re.search(r"%(?![0-9a-fA-F]{2})", query):
            raise RequestError(400, "malformed query")
        try:
            pairs = parse_qsl(query, keep_blank_values=True, strict_parsing=True,
                              encoding="utf-8", errors="strict", max_num_fields=2)
        except (ValueError, UnicodeDecodeError):
            raise RequestError(400, "malformed query") from None
        options = {}
        for key, value in pairs:
            if key not in ("cursor", "limit") or key in options or not DECIMAL.fullmatch(value):
                raise RequestError(400, "invalid query parameters")
            options[key] = value
        limit_text = options.get("limit", "50")
        if len(limit_text) > 3 or not 1 <= int(limit_text) <= 100:
            raise RequestError(400, "invalid limit")
        limit = int(limit_text)
        cursor_text = options.get("cursor", "0")
        # All nonnegative decimal cursors are valid, including integers beyond
        # SQLite's signed 64-bit range. Such cursors necessarily have no rows.
        if len(cursor_text) > 19 or (len(cursor_text) == 19 and cursor_text > "9223372036854775807"):
            rows = []
        else:
            with closing(_connect(self.server.db_path)) as db:
                rows = db.execute(
                    "SELECT sequence, event_id, body FROM events "
                    "WHERE tenant = ? AND sequence > ? ORDER BY sequence LIMIT ?",
                    (tenant, int(cursor_text), limit + 1)).fetchall()
        has_more = len(rows) > limit
        page = rows[:limit]
        next_cursor = str(page[-1][0]) if has_more else None
        # Raw JSON has already been validated as an object. Embedding it retains
        # arbitrary JSON numbers exactly and never exposes the stored signature.
        items = [b'{"sequence":' + str(sequence).encode("ascii")
                 + b',"event_id":' + json.dumps(event_id).encode("ascii")
                 + b',"payload":' + raw + b'}'
                 for sequence, event_id, raw in page]
        self._bytes(200, b'{"items":[' + b','.join(items) + b'],"next_cursor":'
                    + json.dumps(next_cursor).encode("ascii") + b'}')

    def log_message(self, format, *args):
        # Never log request targets, bodies, headers, or authentication data.
        pass


class InboxServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 128


def create_server(db_path, config_path, host="127.0.0.1", port=0):
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    if not isinstance(config, dict) or not isinstance(config.get("tenants"), dict):
        raise ValueError("configuration must contain a tenants object")
    tenants = {}
    for name, credentials in config["tenants"].items():
        if not TENANT.fullmatch(name) or not isinstance(credentials, dict):
            raise ValueError("invalid tenant configuration")
        if any(not isinstance(credentials.get(key), str) or not credentials[key]
               for key in ("secret", "token")):
            raise ValueError("tenant credentials must be nonempty strings")
        try:
            tenants[name] = {key: credentials[key].encode("utf-8") for key in ("secret", "token")}
        except UnicodeEncodeError:
            raise ValueError("tenant credentials must be valid UTF-8") from None
    database = str(Path(db_path).resolve())
    with closing(_connect(database)) as db:
        db.execute("PRAGMA journal_mode = WAL")
        db.execute("""CREATE TABLE IF NOT EXISTS events (
            sequence INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant TEXT NOT NULL,
            event_id TEXT NOT NULL,
            body BLOB NOT NULL,
            UNIQUE (tenant, event_id)
        )""")
        db.execute("CREATE INDEX IF NOT EXISTS events_tenant_sequence ON events (tenant, sequence)")
    server = InboxServer((host, port), InboxHandler)
    server.db_path = database
    server.tenants = tenants
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
