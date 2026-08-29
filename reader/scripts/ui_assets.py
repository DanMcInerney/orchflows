"""Immutable frontend-distribution discovery and reads."""

from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path, PurePosixPath


def resolve_asset_root(script_file=None) -> Path:
    """Find the installed distribution, with the checkout as its dev seam."""

    script = Path(__file__ if script_file is None else script_file).resolve()
    reader_root = script.parent.parent
    installed = script.parents[3] / "ui"
    checkout = reader_root / "web" / "dist"
    for candidate in (installed, checkout, reader_root / "ui"):
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


def valid_host_headers(headers) -> bool:
    """Exactly one unambiguous loopback authority."""

    values = headers.get_all("Host", []) if hasattr(headers, "get_all") else [headers.get("Host", "")]
    if len(values) != 1:
        return False
    return values[0].split(":", 1)[0].lower() in ("127.0.0.1", "localhost")
