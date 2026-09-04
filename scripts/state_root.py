#!/usr/bin/env python3
"""The one resolver for durable run state. Stdlib-only, cross-platform.

Four facts, one owner. The sink root is the sink env var
(``scripts._bootstrap.ENV_VAR``, named in prose at ``rules/visibility.md``
section 6) when set non-empty, else ``~/.orchflows/state``, read at call
time so a test may move it after import. ``find_repo_root`` answers *which
project* a record arose in, never where the record goes; a linked
worktree's ``.git`` pointer is dereferenced so every worktree of a
repository reports one identity. ``candidate_paths`` derives a work item's
worktree from the run and ticket id alone, by one function, so two
siblings cannot be handed one tree. ``in_temp_root`` answers whether a
path lies under the host's system temp root.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

try:
    from scripts._bootstrap import ENV_VAR
except ImportError:  # pragma: no cover - direct/installed flat script path
    from _bootstrap import ENV_VAR

WORKTREES_ENV_VAR = "ORCHFLOWS_WORKTREES_HOME"
DEFAULT_HOME_SUBPATH = (".orchflows", "state")
WORKTREES_SUBPATH = "worktrees"
# One segment, and short: a derived path is a real Windows path, and the
# item working in it opens files far below its root.
WORKTREE_BRANCH_PREFIX = "wt"
MAX_WALK_UP = 64

# Sink subdirectory names with no root above yet. `orchflows_home.py`'s
# `MANAGED_IGNORES` imports these five plus `tickets_root().name` rather
# than restate any of them.
LOCKS_SUBPATH = "locks"
SCRATCH_SUBPATH = "scratch"
WORKSPACES_SUBPATH = "workspaces"
MUTANTS_SUBPATH = "mutants"
DRAFTS_SUBPATH = "drafts"


def state_root() -> Path:
    """The sink root. Set-but-empty reads as unset."""

    override = os.environ.get(ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home().joinpath(*DEFAULT_HOME_SUBPATH)


def runs_root() -> Path:
    # Literal join, not `RUNS_SUBPATH`: `tools/validate_support/friction.py`
    # reads this family's return expression by AST, matching a
    # `<root> / "name"` join -- a `Name` reference would read as no match.
    return state_root() / "runs"


def tickets_root() -> Path:
    return state_root() / "tickets"


def friction_root() -> Path:
    return state_root() / "friction"


def improvement_root() -> Path:
    return state_root() / "improvement"


def orchflows_home() -> Path:
    """The user-scope home the sink sits inside, resolved through the sink."""

    return state_root().parent


def worktrees_root() -> Path:
    """Where every derived candidate worktree lives, a sibling of ``state``."""

    override = os.environ.get(WORKTREES_ENV_VAR, "").strip()
    if override:
        return Path(override).expanduser()
    return orchflows_home() / WORKTREES_SUBPATH


def segment_defect(kind: str, value):
    """Why ``value`` is not one path segment under a sink root, else ``None``."""

    text = str(value or "")
    if not text.strip():
        return f"{kind} is empty"
    if "/" in text or "\\" in text or ".." in text or text == ".":
        return (
            f"unsafe {kind} '{value}': one path segment only, with no path "
            "separator and no '..'"
        )
    return None


def candidate_paths(run: str, ticket_id: str) -> dict:
    """The one derivation of a work item's candidate worktree and branch."""

    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        defect = segment_defect(kind, value)
        if defect is not None:
            raise ValueError(defect)
    return {
        "path": worktrees_root() / run / ticket_id,
        "branch": f"{WORKTREE_BRANCH_PREFIX}/{run}/{ticket_id}",
    }


def candidate_identity(path) -> dict:
    """The ``{run, id}`` whose candidate worktree ``path`` lies in, or ``None``."""

    try:
        root = os.path.realpath(os.fspath(worktrees_root()))
        standing = os.path.realpath(os.fspath(path))
        if os.path.commonpath(
            (os.path.normcase(root), os.path.normcase(standing))
        ) != os.path.normcase(root):
            return None
        parts = Path(os.path.relpath(standing, root)).parts
    except (OSError, TypeError, ValueError):
        # ValueError is the ordinary Windows answer for two different
        # drives, which is "not inside" rather than a failure to report.
        return None
    if len(parts) < 2:
        return None
    return {"run": parts[0], "id": parts[1]}


def _one_spelling(path) -> str:
    """One spelling for one location, on a case-folding filesystem too."""

    return os.path.normcase(os.path.realpath(os.fspath(path)))


def inside_temp_root(candidate) -> bool:
    """Whether ``candidate`` lies inside this host's system temp root."""

    root = _one_spelling(tempfile.gettempdir())
    try:
        return os.path.commonpath((root, _one_spelling(candidate))) == root
    except ValueError:  # different drives have no common path at all
        return False


def main_checkout_root(git_file: Path):
    """Resolve a .git pointer file (worktree/submodule) to its main root,
    or ``None`` -- which ``find_repo_root`` reads as "name the worktree"."""

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
