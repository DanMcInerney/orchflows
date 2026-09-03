#!/usr/bin/env python3
"""One private Python environment per ring item that declares dependencies.

The standard-library floor is the library's own: ``scripts/``, ``tools/``
and the installer import nothing outside Python 3.9's standard library. A
ring item -- a custom skill, pack or workflow -- is outside that floor and
uses whatever libraries it needs. It declares them in one ``requirements.txt``
beside its manifest, pip's own format, and this module builds the
environment that file describes at ``~/.orchflows/envs/<kind>/<name>/``:
created when absent, reused while the file's digest matches the stamp the
build left, rebuilt when the file changes. An item that declares nothing
runs on the interpreter this process already runs on -- the private runtime
once installed -- exactly as before.

Building an environment runs the item's content: pip resolves and executes
what the file names. That is what trust grants, so an untrusted project
ring item is skipped here and named with its remedy rather than installed.

Stdlib only, cross-platform, Python 3.9 and up. The only network reach is
pip's own, inside ``build``, and a caller may inject another builder.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import venv
from pathlib import Path
from typing import Callable, Dict, List, Optional

try:
    from scripts import rings
except ImportError:  # pragma: no cover - direct/installed flat script path
    import rings


REQUIREMENTS_NAME = "requirements.txt"
ENVS_DIR = "envs"
STAMP_NAME = "orchflows-env.json"
STAMP_SCHEMA = 1
ACTIONS = ("create", "reuse", "refresh")
UNTRUSTED_REMEDY = (
    "{kind} '{name}' declares dependencies, and building them runs its "
    "content; trust its bundle first: orchflows trust {bundle}"
)
UNBUILT_REMEDY = (
    "{kind} '{name}' declares dependencies but its environment is not built; "
    "run: orchflows sync"
)


def requirements_of(item_dir) -> Optional[Path]:
    """The item's dependency declaration beside its manifest, or ``None``."""

    candidate = Path(item_dir) / REQUIREMENTS_NAME
    return candidate if candidate.is_file() else None


def requirement_lines(requirements: Path) -> List[str]:
    """The file's requirement lines: comments and blank lines stripped."""

    lines = []
    for raw in requirements.read_text(encoding="utf-8-sig").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            lines.append(line)
    return lines


def env_home(kind: str, name: str, home=None) -> Path:
    """Where this item's environment lives, under the home ring."""

    root = Path(home) if home is not None else rings.home_ring()
    return root / ENVS_DIR / rings.kind_of(kind) / rings.item_name(name)


def interpreter(env: Path) -> Path:
    """The interpreter inside one environment, on this platform."""

    if os.name == "nt":
        return Path(env) / "Scripts" / "python.exe"
    return Path(env) / "bin" / "python"


def digest(requirements: Path) -> str:
    return hashlib.sha256(Path(requirements).read_bytes()).hexdigest()


def read_stamp(env: Path) -> Optional[dict]:
    """The stamp a successful build left, or ``None`` for anything else."""

    try:
        loaded = json.loads((Path(env) / STAMP_NAME).read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(loaded, dict) or loaded.get("schema") != STAMP_SCHEMA:
        return None
    if not isinstance(loaded.get("requirements_sha256"), str):
        return None
    return loaded


def action(env: Path, requirements: Path) -> str:
    """``create``, ``reuse`` or ``refresh``, from the stamp and the file alone."""

    stamp = read_stamp(env)
    if stamp is None or not interpreter(env).is_file():
        return "create"
    if stamp["requirements_sha256"] == digest(requirements):
        return "reuse"
    return "refresh"


def build(env: Path, requirements: Path) -> None:
    """Create the environment the way ``python -m venv`` would, then pip.

    Symlinks on POSIX for the same reason the private runtime uses them: a
    copied interpreter's ``libpython`` reference dangles. pip is bootstrapped
    only when there is something to install, so a declaration that is all
    comments costs a bare venv and no network.
    """

    lines = requirement_lines(requirements)
    venv.EnvBuilder(
        symlinks=os.name != "nt", with_pip=bool(lines), clear=True
    ).create(env)
    if not lines:
        return
    installed = subprocess.run(
        [
            str(interpreter(env)),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--requirement",
            str(requirements),
        ],
        check=False,
    )
    if installed.returncode != 0:
        raise RuntimeError(
            f"dependency installation failed for {requirements} (pip exit "
            f"{installed.returncode})"
        )


def ensure(
    kind: str,
    name: str,
    item_dir,
    *,
    home=None,
    builder: Optional[Callable[[Path, Path], None]] = None,
) -> Dict[str, object]:
    """Make one item's environment match its declaration, and say what happened.

    A failed build leaves no stamp and no half-built directory behind, so the
    next ``sync`` sees ``create`` rather than trusting a broken tree.
    """

    kind = rings.kind_of(kind)
    name = rings.item_name(name)
    requirements = requirements_of(item_dir)
    if requirements is None:
        raise ValueError(f"{kind} '{name}' declares no {REQUIREMENTS_NAME}")
    env = env_home(kind, name, home)
    decided = action(env, requirements)
    if decided != "reuse":
        env.parent.mkdir(parents=True, exist_ok=True)
        try:
            (builder or build)(env, requirements)
            stamp = {
                "schema": STAMP_SCHEMA,
                "kind": kind,
                "name": name,
                "requirements": str(requirements),
                "requirements_sha256": digest(requirements),
            }
            (env / STAMP_NAME).write_text(
                json.dumps(stamp, sort_keys=True) + "\n", encoding="utf-8"
            )
        except Exception:
            shutil.rmtree(env, ignore_errors=True)
            raise
    return {
        "kind": kind,
        "name": name,
        "action": decided,
        "env": str(env),
        "interpreter": str(interpreter(env)),
        "requirements": str(requirements),
    }


def resolve_interpreter(kind: str, name: str, *, home=None, **overrides) -> Dict[str, object]:
    """The interpreter one item's scripts run through, resolved as dispatch would.

    Its own environment when it declares one and that environment is built;
    this process's interpreter when it declares nothing. A declared but
    unbuilt environment is refused with the ``sync`` remedy rather than
    answered with an interpreter that lacks what the item imports.
    """

    record = rings.resolve(kind, name, **overrides)
    item_dir = Path(str(record["dir"]))
    requirements = requirements_of(item_dir)
    if requirements is None:
        return {
            "kind": record["kind"],
            "name": record["name"],
            "interpreter": sys.executable,
            "declares": False,
            "env": None,
        }
    env = env_home(str(record["kind"]), str(record["name"]), home)
    if read_stamp(env) is None or not interpreter(env).is_file():
        raise rings.RingError(
            "env-unbuilt",
            UNBUILT_REMEDY.format(kind=record["kind"], name=record["name"]),
        )
    return {
        "kind": record["kind"],
        "name": record["name"],
        "interpreter": str(interpreter(env)),
        "declares": True,
        "env": str(env),
    }


def sync(
    records: List[Dict[str, object]],
    *,
    home=None,
    builder: Optional[Callable[[Path, Path], None]] = None,
) -> List[Dict[str, object]]:
    """Every declaring item in one inventory, built or named with its remedy.

    ``records`` is ``rings.inventory``'s output: the same resolver dispatch
    uses, so an environment built here is one a launch can reach, and a
    reserved or shadowed item costs nothing. Untrusted project items are
    reported, never built.
    """

    outcomes = []
    for record in records:
        if record.get("reserved"):
            continue
        item_dir = Path(str(record["dir"]))
        if requirements_of(item_dir) is None:
            continue
        kind = str(record["kind"])
        name = str(record["name"])
        if record.get("trust") == "untrusted":
            outcomes.append({
                "kind": kind,
                "name": name,
                "action": "skipped",
                "detail": UNTRUSTED_REMEDY.format(
                    kind=kind, name=name, bundle=item_dir.parent.parent,
                ),
            })
            continue
        outcomes.append(ensure(kind, name, item_dir, home=home, builder=builder))
    return outcomes


def orphaned(env: Path, kind: str, name: str, claimed) -> bool:
    """Whether one built environment's declaration is gone from the machine.

    Not "absent from this inventory": environments are keyed machine-wide by
    ``(kind, name)`` while an inventory is read from wherever ``sync`` was
    run, so a project ring's items are in it only inside that project. The
    stamp is what settles it -- it carries the ``requirements.txt`` that
    built the environment, so a declaration still on disk means an item that
    is still there, visible from this vantage or another one. Only an
    environment with no stamp to read falls back to the inventory, which is
    the one claim a half-built tree can carry.
    """

    stamp = read_stamp(env)
    declared = stamp.get("requirements") if stamp is not None else None
    if isinstance(declared, str) and declared:
        return not Path(declared).exists()
    return (kind, name) not in claimed


def prune(
    records: List[Dict[str, object]], *, home=None
) -> List[Dict[str, object]]:
    """Remove the environment of every item that is gone from the machine.

    An environment is derived from an item's declaration, so an item that
    left the ring leaves nothing behind that is worth keeping -- and a
    ``envs/`` that grows a directory per item ever installed is a machine
    the user cannot reason about. What "left" means is ``orphaned``'s.

    Only this module's own layout is touched: a directory under a kind name
    orchflows knows, itself named like an item. A removal that fails raises
    rather than being swallowed -- a directory that could not go is a
    directory the next ``resolve_interpreter`` may still find.
    """

    root = (Path(home) if home is not None else rings.home_ring()) / ENVS_DIR
    if not root.is_dir():
        return []
    claimed = {(str(record["kind"]), str(record["name"])) for record in records}
    removed = []
    for kind_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        if kind_dir.name not in rings.KINDS:
            continue
        for env in sorted(path for path in kind_dir.iterdir() if path.is_dir()):
            if not rings.NAME_RE.fullmatch(env.name):
                continue
            if not orphaned(env, kind_dir.name, env.name, claimed):
                continue
            shutil.rmtree(env)
            removed.append({
                "kind": kind_dir.name, "name": env.name,
                "action": "pruned", "env": str(env),
            })
    return removed


__all__ = (
    "ACTIONS", "ENVS_DIR", "REQUIREMENTS_NAME", "STAMP_NAME", "STAMP_SCHEMA",
    "UNBUILT_REMEDY", "UNTRUSTED_REMEDY", "action", "build", "digest",
    "ensure", "env_home", "interpreter", "orphaned", "prune", "read_stamp",
    "requirement_lines", "requirements_of", "resolve_interpreter", "sync",
)
