"""Shared loopback-server helpers for the active reader HTTP tests."""

import contextlib
import http.client
import threading
from pathlib import Path

from reader.scripts import ui_api
from reader.tests.test_ui_cases._base import *  # noqa: F401,F403


@contextlib.contextmanager
def serving(root: Path, transcripts=None):
    """Run the real reader server on an ephemeral loopback port."""

    server = ui_api.create_server(root, 0, transcripts)
    thread = threading.Thread(target=server.serve_forever, args=(0.01,))
    thread.daemon = True
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def write_ticket(run_dir: Path, ticket_id: str, **fields) -> Path:
    """Write one minimal ticket for a focused HTTP/projection fixture."""

    run_dir.mkdir(parents=True, exist_ok=True)
    lines = ["---", "id: {0}".format(ticket_id)]
    lines.extend("{0}: {1}".format(key, value) for key, value in fields.items())
    lines.extend(["---", ""])
    path = run_dir / "{0}.md".format(ticket_id)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def request(server, route: str, method="GET", headers=None) -> tuple:
    """Return ``(status, headers, body)`` for a loopback request."""

    host, port = server.server_address[0], server.server_address[1]
    connection = http.client.HTTPConnection(host, port, timeout=5)
    try:
        connection.request(method, route, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.headers, response.read().decode("utf-8")
    finally:
        connection.close()


def fetch(server, route: str, headers=None) -> tuple:
    return request(server, route, headers=headers)


def get(server, route: str) -> tuple:
    status, _headers, body = fetch(server, route)
    return status, body


def snapshot(tree: Path) -> dict:
    """Name, size, and mtime of every entry under ``tree``."""

    entries = {}
    for path in sorted(tree.rglob("*")):
        stat = path.stat()
        key = path.relative_to(tree).as_posix()
        entries[key] = (path.is_dir(), stat.st_size, stat.st_mtime_ns)
    return entries
