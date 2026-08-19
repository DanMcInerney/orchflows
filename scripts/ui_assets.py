"""Immutable frontend-distribution discovery and reads."""

from __future__ import annotations

import hashlib
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath


def resolve_asset_root(script_file=None) -> Path:
    """Find the installed distribution, with the checkout as its dev seam."""

    script = Path(__file__ if script_file is None else script_file).resolve()
    installed = script.parent.parent / "ui"
    checkout = script.parent.parent / "web" / "dist"
    for candidate in (installed, checkout):
        if (candidate / "index.html").is_file():
            return candidate.resolve()
    raise OSError("orchflows UI distribution is missing index.html")


def _contained(root: Path, relative: str):
    """A regular distribution file within ``root``, or ``None``."""

    pure = PurePosixPath(relative)
    if pure.is_absolute() or not relative or any(part in ("", ".", "..") for part in pure.parts):
        return None
    try:
        base = root.resolve()
        candidate = base.joinpath(*pure.parts).resolve()
        if base not in candidate.parents or not candidate.is_file():
            return None
    except (OSError, ValueError):
        return None
    return candidate


def read_asset(root: Path, relative: str):
    """``(bytes, media type, validator)`` for one contained asset."""

    path = _contained(Path(root), relative)
    if path is None:
        return None
    try:
        body = path.read_bytes()
    except OSError:
        return None
    guessed = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    if path.suffix == ".js":
        guessed = "text/javascript"
    tag = '"{0}"'.format(hashlib.sha256(body).hexdigest())
    return body, guessed, tag


def manifest_paths(root: Path) -> tuple:
    """Every byte in the immutable distribution, named root-relative."""

    base = Path(root).resolve()
    try:
        files = sorted(path for path in base.rglob("*") if path.is_file())
    except OSError:
        return ()
    return tuple(path.relative_to(base).as_posix() for path in files)


class FallbackReaderServer(ThreadingHTTPServer):
    """Stdlib harness for source-tree checks without the private runtime."""

    daemon_threads = True

    def __init__(self, root, port, transcripts, assets, dispatch, security_headers):
        self.root = Path(root).resolve()
        self.transcripts = transcripts
        self.assets = Path(assets).resolve()
        self.dispatch = dispatch
        self.security_headers = security_headers
        ThreadingHTTPServer.__init__(self, ("127.0.0.1", port), FallbackReaderHandler)


class FallbackReaderHandler(BaseHTTPRequestHandler):
    server_version = "orchflows-ui"
    sys_version = ""

    def _serve(self):
        status, headers, body = self.server.dispatch(
            self.server, self.command, self.path, self.headers
        )
        self.send_response(status)
        for name, value in headers.items():
            self.send_header(name, value)
        for name, value in self.server.security_headers.items():
            self.send_header(name, value)
        self.end_headers()
        if self.command != "HEAD" and body:
            self.wfile.write(body)

    do_GET = _serve
    do_HEAD = _serve
    do_POST = _serve
    do_PUT = _serve
    do_PATCH = _serve
    do_DELETE = _serve
    do_OPTIONS = _serve

    def log_message(self, format, *args):
        pass
