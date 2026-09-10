#!/usr/bin/env python3
"""The trust ledger for project-ring bundles: content-keyed, never portable.

A project ring rides somebody's repository, so cloning it must not put
skills, standards, or workflows in front of an agent. The ledger records which
bundles the user allowed and at which content digest. It lives at
``~/.orchflows/trust.json`` -- outside every repository, gitignored by the
home ring -- because a repository that could grant itself trust is the whole
failure mode. No trust or resolution policy is ever read from a project file.

Two grants: ``once`` is a single-use token this module spends the first time
a resolution consumes it; ``trusted`` is the standing entry, valid until the
bundle's digest changes. The digest covers the bundle's ring directories and
nothing else, so ordinary edits elsewhere never re-prompt.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import marshal
import os
import re
import sys
import types
from pathlib import Path
from typing import Dict, List, Optional

try:
    from scripts import rings
except ImportError:  # pragma: no cover - direct/installed flat script path
    import rings


LEDGER_NAME = "trust.json"
LEDGER_VERSION = 1
EMPTY_DIGEST = "sha256:" + hashlib.sha256(b"").hexdigest()


def ledger_path(home: Optional[Path] = None) -> Path:
    return (home if home is not None else rings.home_ring()) / LEDGER_NAME


def _folded(path) -> str:
    return os.path.normcase(str(Path(path).expanduser().resolve()))


def _derived_bytecode(path: Path) -> bool:
    """Ignore only caches equivalent to compiling their adjacent source.

    A cache directory is not a trust exemption: sourceless, forged, foreign
    interpreter and malformed bytecode remain ordinary hashed inputs.
    """
    if path.parent.name != "__pycache__" or path.suffix != ".pyc":
        return False
    match = re.fullmatch(
        rf"(.+)\.{re.escape(sys.implementation.cache_tag or '')}(?:\.opt-([12]))?\.pyc",
        path.name,
    )
    if match is None:
        return False
    source = path.parent.parent / (match[1] + ".py")
    try:
        raw = path.read_bytes()
        if raw[:4] != importlib.util.MAGIC_NUMBER:
            return False
        code = marshal.loads(raw[16:])
        return isinstance(code, types.CodeType) and code == compile(
            source.read_bytes(), code.co_filename, "exec", dont_inherit=True,
            optimize=int(match[2] or 0),
        )
    except (OSError, ValueError, TypeError, EOFError, SyntaxError):
        return False


def bundle_digest(bundle) -> str:
    """Hash ring content, excluding bytecode proven derived from its source."""

    root = Path(bundle).expanduser()
    digest = hashlib.sha256()
    for directory in rings.RING_DIRS.values():
        base = root / directory
        if not base.is_dir():
            continue
        for path in sorted(
            (item for item in base.rglob("*") if item.is_file()),
            key=lambda item: item.relative_to(root).as_posix(),
        ):
            if _derived_bytecode(path):
                continue
            digest.update(path.relative_to(root).as_posix().encode("utf-8"))
            digest.update(b"\0")
            try:
                raw = path.read_bytes()
            except OSError:
                raw = b"<unreadable>"
            try:
                raw = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
            except UnicodeDecodeError:
                pass
            digest.update(hashlib.sha256(raw).hexdigest().encode("ascii"))
            digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def read(home: Optional[Path] = None) -> Dict[str, List[dict]]:
    """The ledger as data. An absent or malformed file grants nothing."""

    try:
        document = json.loads(ledger_path(home).read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError):
        document = {}
    if not isinstance(document, dict):
        document = {}
    result = {"version": LEDGER_VERSION, "trusted": [], "once": []}
    for key in ("trusted", "once"):
        entries = document.get(key)
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            bundle = str(entry.get("bundle") or "").strip()
            digest = str(entry.get("digest") or "").strip()
            if bundle and digest:
                result[key].append({"bundle": bundle, "digest": digest})
    return result


def write(document: Dict[str, List[dict]], home: Optional[Path] = None) -> Path:
    """Replace the ledger. The caller owns what it holds; this owns the bytes."""

    path = ledger_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": LEDGER_VERSION,
        "trusted": sorted(document.get("trusted") or [], key=lambda item: item["bundle"]),
        "once": sorted(document.get("once") or [], key=lambda item: item["bundle"]),
    }
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)
    return path


def refusal(bundle, digest: str) -> str:
    """The one refusal sentence, naming both halves of the two-step remedy."""

    return (
        f"project bundle {bundle} is not trusted at its current content "
        f"digest {digest}. A project ring's skills, standards and workflows reach "
        "your agents, so orchflows reads one only after you say so. Use it "
        f"once, recording nothing: orchflows trust --once {bundle}. Remember "
        f"it until the bundle's content changes: orchflows trust {bundle}. "
        f"Withdraw either: orchflows untrust {bundle}."
    )


def state(bundle, *, home: Optional[Path] = None) -> dict:
    """Whether ``bundle`` is trusted right now, without spending anything."""

    key = _folded(bundle)
    digest = bundle_digest(bundle)
    ledger = read(home)
    for entry in ledger["trusted"]:
        if _folded(entry["bundle"]) == key and entry["digest"] == digest:
            return _verdict(bundle, digest, True, "remembered")
    for entry in ledger["once"]:
        if _folded(entry["bundle"]) == key and entry["digest"] == digest:
            return _verdict(bundle, digest, True, "once")
    return _verdict(bundle, digest, False, "none")


def consume(bundle, *, home: Optional[Path] = None) -> dict:
    """``state``, and spend a one-shot grant if that is what allowed it."""

    verdict = state(bundle, home=home)
    if verdict["how"] != "once":
        return verdict
    key = _folded(bundle)
    ledger = read(home)
    ledger["once"] = [
        entry for entry in ledger["once"]
        if not (_folded(entry["bundle"]) == key and entry["digest"] == verdict["digest"])
    ]
    write(ledger, home)
    return verdict


def grant(bundle, *, once: bool = False, home: Optional[Path] = None) -> dict:
    """Record trust for the bundle's current content, permanently or once."""

    resolved = Path(bundle).expanduser().resolve()
    if not resolved.is_dir():
        raise rings.RingError("bundle-missing", f"no bundle directory at {resolved}")
    digest = bundle_digest(resolved)
    key = _folded(resolved)
    ledger = read(home)
    target = "once" if once else "trusted"
    for name in ("trusted", "once"):
        ledger[name] = [
            entry for entry in ledger[name] if _folded(entry["bundle"]) != key
        ]
    ledger[target].append({"bundle": str(resolved), "digest": digest})
    path = write(ledger, home)
    return {"bundle": str(resolved), "digest": digest, "grant": target, "ledger": str(path)}


def revoke(bundle, *, home: Optional[Path] = None) -> dict:
    """Drop every grant for one bundle, both halves of the two-step."""

    resolved = Path(bundle).expanduser().resolve()
    key = _folded(resolved)
    ledger = read(home)
    removed = 0
    for name in ("trusted", "once"):
        kept = [entry for entry in ledger[name] if _folded(entry["bundle"]) != key]
        removed += len(ledger[name]) - len(kept)
        ledger[name] = kept
    path = write(ledger, home)
    return {"bundle": str(resolved), "removed": removed, "ledger": str(path)}


def _verdict(bundle, digest: str, trusted: bool, how: str) -> dict:
    return {
        "bundle": str(Path(bundle).expanduser().resolve()),
        "digest": digest,
        "trusted": trusted,
        "how": how,
        "refusal": None if trusted else refusal(Path(bundle).expanduser().resolve(), digest),
    }


__all__ = (
    "EMPTY_DIGEST", "LEDGER_NAME", "LEDGER_VERSION", "bundle_digest", "consume",
    "grant", "ledger_path", "read", "refusal", "revoke", "state", "write",
)
