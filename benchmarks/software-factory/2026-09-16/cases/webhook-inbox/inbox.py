"""Runnable starter for the webhook inbox assignment; product routes are incomplete."""

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class InboxHandler(BaseHTTPRequestHandler):
    def _json(self, status, value):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok"})
        elif self.path.startswith("/events/"):
            # TODO: authorize, load durable events, and paginate.
            self._json(200, {"items": [], "next_cursor": None})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        # TODO: validate the request, authenticate, and store an event atomically.
        self._json(501, {"error": "webhook ingestion is not implemented"})

    def log_message(self, format, *args):
        # Keep starter logs small and free of request headers and bodies.
        pass


def create_server(db_path, config_path, host="127.0.0.1", port=0):
    server = ThreadingHTTPServer((host, port), InboxHandler)
    server.db_path = str(Path(db_path))
    server.config = json.loads(Path(config_path).read_text(encoding="utf-8"))
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
