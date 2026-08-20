#!/usr/bin/env python3
"""Serve one rendered visualization once on an ephemeral loopback port."""

import json
import sys
import time
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


TIMEOUT_SECONDS = 60


class _PreviewServer(HTTPServer):
    def __init__(self, address, handler):
        super().__init__(address, handler)
        self.successful_get = False
        self.response_failed = False
        self.socket_failed = False
        self.connection_timeout = None

    def get_request(self):
        try:
            request, address = super().get_request()
            if self.connection_timeout is not None:
                request.settimeout(max(0.001, self.connection_timeout))
            return request, address
        except OSError:
            self.socket_failed = True
            raise

    def handle_error(self, _request, _client_address):
        self.response_failed = True


def _handler_for(encoded_path, content):
    class PreviewHandler(BaseHTTPRequestHandler):
        def log_message(self, _format, *args):
            pass

        def _send_headers(self):
            if self.path != encoded_path:
                self.send_error(404)
                return False
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            return True

        def do_HEAD(self):
            self._send_headers()

        def do_GET(self):
            if not self._send_headers():
                return
            self.wfile.write(content)
            self.wfile.flush()
            self.server.successful_get = True

    return PreviewHandler


def _serve(path, timeout_seconds=TIMEOUT_SECONDS, server_factory=_PreviewServer):
    try:
        path = Path(path).resolve(strict=True)
        if not path.is_file():
            raise OSError
        content = path.read_bytes()
    except (OSError, ValueError):
        print("input must name an existing file", file=sys.stderr)
        return 2

    encoded_path = "/" + urllib.parse.quote(path.name, safe="")
    try:
        server = server_factory(
            ("127.0.0.1", 0), _handler_for(encoded_path, content)
        )
    except OSError as error:
        print(f"cannot start loopback preview: {error}", file=sys.stderr)
        return 1

    try:
        port = server.server_address[1]
        url = f"http://127.0.0.1:{port}{encoded_path}"
        print(json.dumps({"url": url}, separators=(",", ":")), flush=True)
        deadline = time.monotonic() + timeout_seconds
        while not getattr(server, "successful_get", False):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                print("preview timed out before a successful GET", file=sys.stderr)
                return 1
            server.timeout = remaining
            server.connection_timeout = remaining
            try:
                server.handle_request()
            except OSError:
                print("preview failed while serving", file=sys.stderr)
                return 1
            if getattr(server, "socket_failed", False):
                print("preview failed while accepting a socket", file=sys.stderr)
                return 1
            if getattr(server, "response_failed", False):
                print("preview failed while writing a response", file=sys.stderr)
                return 1
    finally:
        server.server_close()
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: preview.py <rendered-html>", file=sys.stderr)
        return 2
    return _serve(argv[0])


if __name__ == "__main__":
    raise SystemExit(main())
