#!/usr/bin/env python3
"""The home ring: its layout, its committed/regenerable boundary, its pins.

``~/.orchflows`` is meant to be the user's own git repository -- their
skills, packs, workflows, friction history and run ledgers in one place,
cloned onto the next machine.  That only works if exactly one line is
drawn and drawn here: nothing custom is ever written into ``lib/``, and
nothing regenerable is ever committed.  ``ensure`` creates the ring's
directories, records which library the ring expects, and writes the one
managed block in the ring's ``.gitignore`` that draws the line.

``add`` and ``restore`` are the other half.  An external bundle is
referenced and pinned, never copied into the home ring: a promoted copy is
outside every lockfile and becomes one version for all projects (npm's
global tier, the survey's cautionary tale).  ``imports.lock`` is the pin
and ``imports/`` is regenerable from it, which is why the lock is
committed and the clones are not.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

try:
    from scripts import rings, state_root
except ImportError:  # pragma: no cover - direct/installed flat script path
    import rings
    import state_root


LIB_VERSION_NAME = "lib.version"
GITIGNORE_NAME = ".gitignore"
GITIGNORE_START = "# BEGIN ORCHFLOWS MANAGED IGNORES"
GITIGNORE_END = "# END ORCHFLOWS MANAGED IGNORES"
# Regenerable or machine-local, in that order: the installed library and its
# runtime, the browser distribution, scratch trees, the pinned clones the
# lock restores, the trust ledger that must never travel (P2), and the state
# trees that are heavy or per-run rather than history. `state/friction/` and
# `state/runs/` are deliberately absent: they are the sync value.
# The six sink subdirectory names are `state_root.py`'s owners -- its
# `tickets_root` function for the one with a root already, its five new
# `*_SUBPATH` constants for the rest -- imported rather than restated so
# a renamed subdirectory there cannot drift silently out of what the
# home ring ignores.
SINK_MANAGED_SUBPATHS = (
    state_root.tickets_root().name,
    state_root.LOCKS_SUBPATH,
    state_root.SCRATCH_SUBPATH,
    state_root.WORKSPACES_SUBPATH,
    state_root.MUTANTS_SUBPATH,
    state_root.DRAFTS_SUBPATH,
)
MANAGED_IGNORES = (
    "lib/",
    "runtime/",
    "ui/",
    "tmp/",
    "worktrees/",
    "imports/",
    "trust.json",
) + tuple(f"state/{name}/" for name in SINK_MANAGED_SUBPATHS)
RING_DIRS = tuple(rings.RING_DIRS.values())
_SHA_RE = re.compile(r"^[0-9a-f]{40}$|^[0-9a-f]{64}$")
_REF_SPLIT_RE = re.compile(r"^(?P<url>.+?)@(?P<pin>[^@/]+)$")
MUTABLE_REF_REFUSAL = (
    "'{pin}' is not a pin. A branch name or HEAD moves under you, which is "
    "how 23,000 repositories consumed a rewritten tag in one afternoon; only "
    "consumers naming a commit were unaffected. Name the tag or the full "
    "commit SHA you mean: orchflows add {url}@<tag-or-sha>."
)


def _write_lf(path: Path, text: str) -> None:
    """Write UTF-8 with LF endings on every host.

    Bytes, not `write_text(newline=...)`: that keyword arrived in 3.10 and
    `install.py`'s floor is 3.9, and a text-mode write on Windows would put
    CRLF in a file the ring owner then commits.
    """

    path.write_bytes(text.encode("utf-8"))


def upsert_block(text: str, body: str) -> str:
    """Replace this module's managed block in ``text``, or append it."""

    block = "\n".join([GITIGNORE_START, body.rstrip("\n"), GITIGNORE_END]) + "\n"
    start = text.find(GITIGNORE_START)
    end = text.find(GITIGNORE_END)
    if start == -1 or end == -1 or end < start:
        prefix = text if not text or text.endswith("\n") else text + "\n"
        return prefix + block
    return text[:start] + block + text[end + len(GITIGNORE_END) + 1:]


def lib_version(home: Optional[Path] = None) -> Dict[str, object]:
    """Which library this ring expects, read off the installer's receipt.

    A cloned home ring arrives without ``lib/``; this file is what tells the
    next ``install.py`` which library identity to regenerate there. It is a
    record of an installation, so an unreadable receipt records nulls rather
    than a guess.
    """

    root = home if home is not None else rings.home_ring()
    try:
        receipt = json.loads((root / "receipt.json").read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, ValueError):
        receipt = {}
    if not isinstance(receipt, dict):
        receipt = {}
    version = receipt.get("version")
    commit = receipt.get("source_commit")
    return {
        "receipt_version": version if isinstance(version, int) and not isinstance(version, bool) else None,
        "source_commit": commit if isinstance(commit, str) and commit.strip() else None,
    }


def ensure(home: Optional[Path] = None) -> Dict[str, object]:
    """Create the home ring's directories and its two managed files.

    Idempotent, and it never touches committed ring content: an existing
    ``skills/`` is left exactly as it is, and the ``.gitignore`` is upserted
    as one marked block so a ring owner's own ignores survive.
    """

    root = Path(home) if home is not None else rings.home_ring()
    created = []
    for name in (*RING_DIRS, rings.IMPORTS_DIR):
        path = root / name
        if not path.is_dir():
            path.mkdir(parents=True, exist_ok=True)
            created.append(str(path))
    version_path = root / LIB_VERSION_NAME
    _write_lf(
        version_path,
        json.dumps(lib_version(root), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    ignore_path = root / GITIGNORE_NAME
    before = ignore_path.read_text(encoding="utf-8-sig") if ignore_path.is_file() else ""
    _write_lf(ignore_path, upsert_block(before, "\n".join(MANAGED_IGNORES)))
    return {
        "home": str(root),
        "created": created,
        "lib_version": str(version_path),
        "gitignore": str(ignore_path),
    }


# --- pinned imports ----------------------------------------------------


def _git(*args, cwd=None):
    return subprocess.run(
        ["git", *args], cwd=None if cwd is None else str(cwd),
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


def bundle_name(url: str) -> str:
    """The import's directory name: the repository's own, minus ``.git``."""

    tail = str(url).rstrip("/").replace("\\", "/").rsplit("/", 1)[-1]
    return rings.item_name(tail[:-4] if tail.endswith(".git") else tail)


def split_reference(reference: str):
    """``(url, pin)`` from ``<url>@<pin>``, or a refusal naming the shape."""

    match = _REF_SPLIT_RE.fullmatch(str(reference or "").strip())
    if match is None:
        raise rings.RingError(
            "reference-invalid",
            f"'{reference}' is not <git-url>@<pin>: an import is always a "
            "reference plus a pin, never a copy.",
        )
    return match.group("url"), match.group("pin")


def resolve_pin(url: str, pin: str) -> str:
    """Refuse a mutable ref, and return the pin to check out.

    A full commit SHA is a pin by construction. Anything else is one only
    when the remote publishes it as a tag; a branch, or a ref the remote
    does not publish at all, is refused naming the remedy (FM-4).
    """

    if _SHA_RE.fullmatch(pin):
        return pin
    listed = _git("ls-remote", "--tags", "--heads", url)
    if listed.returncode != 0:
        raise rings.RingError(
            "remote-unreadable", f"cannot read {url}: {listed.stderr.strip()}",
        )
    refs = {line.split("\t")[-1] for line in listed.stdout.splitlines() if "\t" in line}
    if f"refs/tags/{pin}" in refs:
        return pin
    raise rings.RingError(
        "mutable-ref", MUTABLE_REF_REFUSAL.format(pin=pin, url=url),
    )


def read_lock(home: Optional[Path] = None) -> List[dict]:
    return rings.read_imports(home)


def write_lock(entries: List[dict], home: Optional[Path] = None) -> Path:
    root = home if home is not None else rings.home_ring()
    path = rings.imports_lock_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_lf(path, json.dumps(
        {"version": 1, "imports": sorted(entries, key=lambda item: item["name"])},
        ensure_ascii=False, indent=2, sort_keys=True,
    ) + "\n")
    return path


def clone_at(url: str, pin: str, target: Path) -> None:
    """Clone ``url`` into ``target`` and detach it at exactly ``pin``."""

    target.parent.mkdir(parents=True, exist_ok=True)
    cloned = _git("clone", "--quiet", url, str(target))
    if cloned.returncode != 0:
        raise rings.RingError("clone-failed", f"cannot clone {url}: {cloned.stderr.strip()}")
    checked = _git("-c", "advice.detachedHead=false", "checkout", "--quiet", pin, cwd=target)
    if checked.returncode != 0:
        raise rings.RingError(
            "pin-unreachable", f"{url} has no {pin}: {checked.stderr.strip()}",
        )


def add(reference: str, home: Optional[Path] = None) -> dict:
    """Pin one external bundle into the home ring's imports.

    Consent is the add, not the clone: an import trusted by this act needs
    no first-use prompt, and only a change to its pin puts it back in front
    of the user.
    """

    root = Path(home) if home is not None else rings.home_ring()
    url, requested = split_reference(reference)
    pin = resolve_pin(url, requested)
    name = bundle_name(url)
    target = root / rings.IMPORTS_DIR / name
    if target.exists():
        raise rings.RingError(
            "import-exists",
            f"{name} is already imported at {target}: remove it, or edit "
            f"{rings.imports_lock_path(root)} and run orchflows sync.",
        )
    clone_at(url, pin, target)
    entries = [item for item in read_lock(root) if item["name"] != name]
    entries.append({"name": name, "url": url, "pin": pin})
    lock = write_lock(entries, root)
    return {"name": name, "url": url, "pin": pin, "path": str(target), "lock": str(lock)}


def restore(home: Optional[Path] = None) -> List[dict]:
    """Bring ``imports/`` back to what ``imports.lock`` says, clone by clone."""

    root = Path(home) if home is not None else rings.home_ring()
    results = []
    for entry in read_lock(root):
        target = root / rings.IMPORTS_DIR / entry["name"]
        if target.is_dir():
            results.append({**entry, "path": str(target), "action": "present"})
            continue
        try:
            clone_at(entry["url"], entry["pin"], target)
        except rings.RingError as error:
            results.append({**entry, "path": str(target), "action": "failed", "detail": error.detail})
            continue
        results.append({**entry, "path": str(target), "action": "cloned"})
    return results


__all__ = (
    "GITIGNORE_END", "GITIGNORE_NAME", "GITIGNORE_START", "LIB_VERSION_NAME",
    "MANAGED_IGNORES", "MUTABLE_REF_REFUSAL", "add", "bundle_name", "clone_at",
    "ensure", "lib_version", "read_lock", "resolve_pin", "restore",
    "split_reference", "upsert_block", "write_lock",
)
