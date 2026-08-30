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
dereferenced when the pointer parses and can be read, so every worktree
of a repository reports one project identity; an unparseable or
unreadable pointer names the worktree, and the record then carries that
directory as the project rather than the checkout above it.

Where a work item's own candidate worktree goes is the third fact, and
it lives here for the same reason: derived from the run and the ticket
id alone, by one function, so two siblings of one run cannot be handed
one tree and no caller can spell the same tree a second way.

This module is the single owner of all three facts. ``tickets.py``,
``friction.py`` and ``workspace.py`` call it; none of them reimplements
it.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_VAR = "ORCHFLOWS_STATE_HOME"
WORKTREES_ENV_VAR = "ORCHFLOWS_WORKTREES_HOME"
DEFAULT_HOME_SUBPATH = (".orchflows", "state")
WORKTREES_SUBPATH = "worktrees"
# One segment, and short: a derived path is a real Windows path, and the
# item working in it opens files far below its root.
WORKTREE_BRANCH_PREFIX = "wt"
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


def orchflows_home() -> Path:
    """The user-scope home the sink sits inside, resolved through the sink.

    One resolution, not two: ``$ORCHFLOWS_STATE_HOME`` moves the sink for a
    test or a host, and everything user-scope beside it -- the installer
    receipt, the installed library, the derived worktrees -- has to move
    with it or a test would reach into the real home to find them.
    """

    return state_root().parent


def worktrees_root() -> Path:
    """Where every derived candidate worktree lives, a sibling of ``state``.

    ``$ORCHFLOWS_WORKTREES_HOME`` overrides it for a host whose derived
    trees belong on another volume. Outside the sink's own trees on
    purpose: a worktree is a checkout, not run state, and a sink walker
    that met one would read a whole second repository as records.
    """

    override = os.environ.get(WORKTREES_ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser()
    return orchflows_home() / WORKTREES_SUBPATH


def candidate_paths(run: str, ticket_id: str) -> dict:
    """The one derivation of a work item's candidate worktree and branch.

    Pure, and derived from the identity alone: two siblings of one run
    derive two paths without consulting each other, which is what makes
    creating the tree outside the run lock safe. Nothing else may compute
    either value -- a second spelling is how a packet came to carry
    another ticket's workspace.

    The segments are refused here rather than trusted, because the run
    and the id are what the path is built out of: a separator or a ``..``
    in either would name a tree outside the root this function exists to
    keep every candidate inside.
    """

    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        text = str(value or "")
        if not text.strip():
            raise ValueError(f"{kind} is empty")
        if "/" in text or "\\" in text or ".." in text or text == ".":
            raise ValueError(
                f"unsafe {kind} '{value}': a derived worktree path takes one "
                "path segment, with no path separator and no '..'"
            )
    return {
        "path": worktrees_root() / run / ticket_id,
        "branch": f"{WORKTREE_BRANCH_PREFIX}/{run}/{ticket_id}",
    }


def main_checkout_root(git_file: Path):
    """Resolve a .git pointer file (worktree/submodule) to its main root,
    or ``None`` -- which ``find_repo_root`` reads as "name the worktree",
    the outcome the module docstring states, for a pointer that will not
    parse and for one that will not read alike."""

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
