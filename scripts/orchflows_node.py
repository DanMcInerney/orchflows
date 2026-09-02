#!/usr/bin/env python3
"""An item's Node tooling: one lockfile install into the item's node_modules.

The third dependency class, and the only one whose home is the item
directory itself. A Python environment is machine-local under the home ring
because two projects may want two of them; ``node_modules/`` is where every
Node runtime already looks, so putting it anywhere else would mean teaching
each of an item's scripts a path instead of letting `node` find it.

The install is always the lockfile's -- ``npm ci`` or
``pnpm install --frozen-lockfile`` -- never a resolving one: a ``sync`` that
resolved would give two machines two dependency trees from one committed
declaration. An item with a ``package.json`` and no lockfile beside it is
therefore reported with the remedy rather than resolved for.

Installing runs the item's content, exactly as pip does, so an untrusted
project ring item is skipped and named with the trust remedy
``orchflows_envs.py`` already spells. A machine with no `node` is reported
too: this module installs packages, it does not install runtimes.

Reuse is the same shape as the Python side: a stamp inside ``node_modules/``
carries the lockfile's digest, so an unchanged lockfile costs one file read
rather than a reinstall.

Stdlib only, cross-platform, Python 3.9 and up. The only network reach is
the package manager's, inside ``install``.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

try:
    from scripts import orchflows_envs, rings
except ImportError:  # pragma: no cover - direct/installed flat script path
    import orchflows_envs
    import rings


MANIFEST_NAME = "package.json"
MODULES_DIR = "node_modules"
STAMP_NAME = "orchflows-node.json"
STAMP_SCHEMA = 1
RUNTIME = "node"
# Lockfile to install command, in the order a directory is searched. The
# manager is the lockfile's own: a `pnpm-lock.yaml` installed by npm is a
# second resolution of a tree somebody already pinned.
LOCKFILES = (
    ("package-lock.json", ("npm", "ci")),
    ("pnpm-lock.yaml", ("pnpm", "install", "--frozen-lockfile")),
)
NO_RUNTIME_REMEDY = (
    "{kind} '{name}' declares {manifest} but '{runtime}' is not on PATH; "
    "install Node and run: orchflows sync"
)
NO_LOCKFILE_REMEDY = (
    "{kind} '{name}' declares {manifest} with no lockfile beside it; commit "
    "{lockfiles} and run: orchflows sync"
)
NO_MANAGER_REMEDY = (
    "{kind} '{name}' pins {lockfile} but '{manager}' is not on PATH; install "
    "it and run: orchflows sync"
)


def manifest_of(item_dir) -> Optional[Path]:
    """The item's Node declaration beside its manifest, or ``None``."""

    candidate = Path(item_dir) / MANIFEST_NAME
    return candidate if candidate.is_file() else None


def lockfile_of(item_dir) -> Optional[Tuple[Path, Tuple[str, ...]]]:
    """``(lockfile, install command)`` for the item, or ``None`` when unpinned."""

    for name, command in LOCKFILES:
        candidate = Path(item_dir) / name
        if candidate.is_file():
            return candidate, command
    return None


def modules_dir(item_dir) -> Path:
    return Path(item_dir) / MODULES_DIR


def digest(lockfile: Path) -> str:
    return hashlib.sha256(Path(lockfile).read_bytes()).hexdigest()


def read_stamp(item_dir) -> Optional[dict]:
    """The stamp a successful install left, or ``None`` for anything else."""

    try:
        loaded = json.loads(
            (modules_dir(item_dir) / STAMP_NAME).read_text(encoding="utf-8")
        )
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(loaded, dict) or loaded.get("schema") != STAMP_SCHEMA:
        return None
    if not isinstance(loaded.get("lock_sha256"), str):
        return None
    return loaded


def action(item_dir, lockfile: Path) -> str:
    """``install`` or ``reuse``, from the stamp and the lockfile alone."""

    stamp = read_stamp(item_dir)
    if stamp is None or not modules_dir(item_dir).is_dir():
        return "install"
    return "reuse" if stamp["lock_sha256"] == digest(lockfile) else "install"


def install(item_dir, command: Tuple[str, ...]) -> None:
    """Run the lockfile install in the item directory, or raise loudly."""

    completed = subprocess.run(list(command), cwd=str(item_dir), check=False)
    if completed.returncode != 0:
        raise RuntimeError(
            f"node dependency installation failed in {item_dir} "
            f"({' '.join(command)} exit {completed.returncode})"
        )


def ensure(
    kind: str,
    name: str,
    item_dir,
    *,
    which: Optional[Callable[[str], Optional[str]]] = None,
    installer: Optional[Callable[[Path, Tuple[str, ...]], None]] = None,
) -> Dict[str, object]:
    """Make one item's ``node_modules`` match its lockfile, and say what happened.

    A failed install leaves no stamp, so the next ``sync`` installs again
    rather than trusting a half-written tree.
    """

    kind = rings.kind_of(kind)
    name = rings.item_name(name)
    which = shutil.which if which is None else which
    item_dir = Path(item_dir)
    manifest = manifest_of(item_dir)
    if manifest is None:
        raise ValueError(f"{kind} '{name}' declares no {MANIFEST_NAME}")
    outcome = {"kind": kind, "name": name, "modules": str(modules_dir(item_dir))}
    if which(RUNTIME) is None:
        return {**outcome, "action": "skipped", "detail": NO_RUNTIME_REMEDY.format(
            kind=kind, name=name, manifest=MANIFEST_NAME, runtime=RUNTIME,
        )}
    pinned = lockfile_of(item_dir)
    if pinned is None:
        return {**outcome, "action": "skipped", "detail": NO_LOCKFILE_REMEDY.format(
            kind=kind, name=name, manifest=MANIFEST_NAME,
            lockfiles=" or ".join(lock for lock, _ in LOCKFILES),
        )}
    lockfile, command = pinned
    if which(command[0]) is None:
        return {**outcome, "action": "skipped", "detail": NO_MANAGER_REMEDY.format(
            kind=kind, name=name, lockfile=lockfile.name, manager=command[0],
        )}
    decided = action(item_dir, lockfile)
    if decided == "install":
        (installer or install)(item_dir, command)
        modules_dir(item_dir).mkdir(parents=True, exist_ok=True)
        stamp = {
            "schema": STAMP_SCHEMA,
            "kind": kind,
            "name": name,
            "lockfile": str(lockfile),
            "lock_sha256": digest(lockfile),
        }
        (modules_dir(item_dir) / STAMP_NAME).write_text(
            json.dumps(stamp, sort_keys=True) + "\n", encoding="utf-8"
        )
    return {**outcome, "action": decided, "lockfile": str(lockfile),
            "command": " ".join(command)}


def sync(records: List[Dict[str, object]], **overrides) -> List[Dict[str, object]]:
    """Every item in one inventory that declares Node tooling, installed or named.

    ``records`` is ``rings.inventory``'s output, the same resolver dispatch
    reads, so what is installed here is what a launch of that item can
    require. Untrusted project items are reported, never installed.
    """

    outcomes = []
    for record in records:
        if record.get("reserved"):
            continue
        item_dir = Path(str(record["dir"]))
        if manifest_of(item_dir) is None:
            continue
        kind, name = str(record["kind"]), str(record["name"])
        if record.get("trust") == "untrusted":
            outcomes.append({
                "kind": kind, "name": name, "action": "skipped",
                "detail": orchflows_envs.UNTRUSTED_REMEDY.format(
                    kind=kind, name=name, bundle=item_dir.parent.parent,
                ),
            })
            continue
        outcomes.append(ensure(kind, name, item_dir, **overrides))
    return outcomes


__all__ = (
    "LOCKFILES", "MANIFEST_NAME", "MODULES_DIR", "NO_LOCKFILE_REMEDY",
    "NO_MANAGER_REMEDY", "NO_RUNTIME_REMEDY", "RUNTIME", "STAMP_NAME",
    "STAMP_SCHEMA", "action", "digest", "ensure", "install", "lockfile_of",
    "manifest_of", "modules_dir", "read_stamp", "sync",
)
