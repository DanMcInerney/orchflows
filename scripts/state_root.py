#!/usr/bin/env python3
"""The one resolver for durable run state. Stdlib-only, cross-platform.

Every run's state and every improvement evidence stream resolve to one
user-scope sink, not to the repository work happens in. The root is the
sink env var (``scripts._bootstrap.ENV_VAR``, named in prose at
``rules/visibility.md`` section 6) when that is set to a non-empty value,
else ``~/.orchflows/state``. It is read at call time, never cached at
import, so a test may point it at a temporary directory after this
module is already loaded.

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
one tree and no caller can spell the same tree a second way. Whether a
path lies in the host's system temp root is the fourth, asked by a
checker in ``tools/`` and a harness in ``scripts/`` that cannot import
each other.

This module is the single owner of all four facts. ``tickets.py``,
``friction.py``, ``workspace.py``, ``isolate.py`` and
``tools/verify_at.py`` call it; none of them reimplements it.
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

# Sink subdirectory names: each an owner constant `orchflows_home.py`'s
# `MANAGED_IGNORES` and any other reader import rather than restate.
RUNS_SUBPATH = "runs"
TICKETS_SUBPATH = "tickets"
FRICTION_SUBPATH = "friction"
IMPROVEMENT_SUBPATH = "improvement"
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
    return state_root() / RUNS_SUBPATH


def tickets_root() -> Path:
    return state_root() / TICKETS_SUBPATH


def friction_root() -> Path:
    return state_root() / FRICTION_SUBPATH


def improvement_root() -> Path:
    return state_root() / IMPROVEMENT_SUBPATH


def orchflows_home() -> Path:
    """The user-scope home the sink sits inside, resolved through the sink.

    One resolution, not two: the sink env var moves the sink for a
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


def segment_defect(kind: str, value):
    """Why ``value`` is not one path segment under a sink root, else ``None``.

    The one-segment rule is this module's because every path built out of a
    run id or a ticket id is built here or from here: the sink trees, the
    derived worktree, and the ticket file the store opens. It was stated
    twice -- once as a raised ``ValueError`` beside ``candidate_paths`` and
    once as a returned payload in ``tickets_store._segment_error`` -- and the
    two sentences had already drifted apart, so a caller reading one of them
    learned a different rule from a caller reading the other. The store's
    refusal now delegates here; this module depends on nothing, which is why
    the predicate lives at this end of the edge rather than the other.
    """

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
    """The one derivation of a work item's candidate worktree and branch.

    Pure, and derived from the identity alone: two siblings of one run
    derive two paths without consulting each other, which is what makes
    creating the tree outside the run lock safe. Nothing else may compute
    either value -- a second spelling is how a launch came to carry
    another ticket's workspace.

    The segments are refused here rather than trusted, because the run
    and the id are what the path is built out of: a separator or a ``..``
    in either would name a tree outside the root this function exists to
    keep every candidate inside. The rule itself is ``segment_defect``'s.
    """

    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        defect = segment_defect(kind, value)
        if defect is not None:
            raise ValueError(defect)
    return {
        "path": worktrees_root() / run / ticket_id,
        "branch": f"{WORKTREE_BRANCH_PREFIX}/{run}/{ticket_id}",
    }


def candidate_identity(path) -> dict:
    """The ``{run, id}`` whose candidate worktree ``path`` lies in, or ``None``.

    The exact inverse of ``candidate_paths``, and here for the same reason
    the forward derivation is: a caller standing in a derived tree that
    spelled the answer for itself would be a second owner of the layout,
    and the two would drift the first time the layout moved. Ancestors
    count, because an item works far below its workspace root.

    Path shape alone. Whether the named item exists is a different
    question, asked of the sink by the caller that cares.

    Containment is decided on the folded spelling and the identity is read
    off the unfolded one -- so this is not ``_one_spelling``'s single
    answer, it is that answer for the comparison only: a run id is a
    timestamp carrying a capital ``T`` and ``Z``, and an identity that had
    been through ``normcase`` would name no run in the sink on Windows.
    """

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
        # drives, which is simply "not inside", not a failure to report.
        return None
    if len(parts) < 2:
        return None
    return {"run": parts[0], "id": parts[1]}


def _one_spelling(path) -> str:
    """One spelling for one location, on a case-folding filesystem too."""

    return os.path.normcase(os.path.realpath(os.fspath(path)))


def inside_temp_root(candidate) -> bool:
    """Whether ``candidate`` lies inside this host's system temp root.

    A fact about a path, so it lives beside the other three, and it lives
    at *this* end of the edge for the reason ``segment_defect`` does: two
    callers in two layers ask it -- the checker that refuses to build a
    worktree there (``tools/verify_at.py``) and the harness that warns when
    it built an isolated tree there (``scripts/isolate.py``) -- and ``tools``
    may import ``scripts`` while the reverse is forbidden, so only this end
    is reachable from both.

    Why anyone asks: a checkout under the system temp root is not merely
    untidy. ``tools/run_tests.py``'s ``meaningful_sys_path`` reads paths
    there as dead scratch, so a suite run inside one reads differently
    about itself, and a red that means only "you ran me in the temp root"
    is indistinguishable from a real one.
    """

    root = _one_spelling(tempfile.gettempdir())
    try:
        return os.path.commonpath((root, _one_spelling(candidate))) == root
    except ValueError:  # different drives have no common path at all
        return False


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
