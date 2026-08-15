#!/usr/bin/env python3
"""The one resolver for durable run state. Stdlib-only, cross-platform.

Every run's state and every improvement evidence stream resolve to one
user-scope sink, not to the repository work happens in. The root is
``$ORCHFLOWS_STATE_HOME`` when that is set to a non-empty value, else
``~/.orchflows/state``. It is read at call time, never cached at import,
so a test may point it at a temporary directory after this module is
already loaded.

A record carries the project it arose in as a field. ``find_repo_root``
is here for that reason and no other: it answers *which project*, never
*where the record goes*. A linked worktree's ``.git`` pointer file is
dereferenced to the main checkout, so every worktree of a repository
reports one project identity.

This module is the single owner of both facts. ``tickets.py``,
``friction.py`` and ``workspace.py`` call it; none of them reimplements
it.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_VAR = "ORCHFLOWS_STATE_HOME"
DEFAULT_HOME_SUBPATH = (".orchflows", "state")
MAX_WALK_UP = 64


def state_root() -> Path:
    """The sink root. Set-but-empty reads as unset."""

    override = os.environ.get(ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home().joinpath(*DEFAULT_HOME_SUBPATH)


def runs_root() -> Path:
    return state_root() / "runs"


def tickets_root() -> Path:
    return state_root() / "tickets"


def friction_root() -> Path:
    return state_root() / "friction"


def improvement_root() -> Path:
    return state_root() / "improvement"


def main_checkout_root(git_file: Path):
    """Resolve a .git pointer file (worktree/submodule) to its main root."""

    try:
        for line in git_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if not line.startswith("gitdir:"):
                continue
            gitdir = Path(line.partition(":")[2].strip())
            if not gitdir.is_absolute():
                gitdir = git_file.parent / gitdir
            parts = gitdir.resolve().parts
            for i in range(len(parts) - 1, -1, -1):
                if parts[i] == ".git":
                    return Path(*parts[:i])
            break
    except Exception:
        pass
    return None


def find_repo_root(start: Path):
    """The main checkout root at or above ``start``, else ``None``."""

    current = Path(start).resolve()
    for _ in range(MAX_WALK_UP):
        marker = current / ".git"
        if marker.exists():
            if marker.is_file():
                main_root = main_checkout_root(marker)
                if main_root is not None:
                    return main_root
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent
    return None
