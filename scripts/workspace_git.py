"""Git lifecycle and guarded ticket stamps for ``workspace.py``."""

from __future__ import annotations

import subprocess
from contextlib import nullcontext
from pathlib import Path

# The owning modules, never the ``tickets`` facade: a helper that imports a
# facade is what a facade exists to spare its callers.
try:
    from . import state_root, tickets_format, tickets_store, tickets_transitions, workspace_record
except ImportError:
    import state_root
    import tickets_format
    import tickets_store
    import tickets_transitions
    import workspace_record


# One verdict per exit code, spelled where the refusals that carry them are
# raised. ``workspace.py`` re-exports every name and holds the table its
# ``--help`` prints; a caller reads these numbers as the answer, so they may
# not be spelled a second time anywhere in the family.
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ISOLATION_MISSING = 2
EXIT_WRONG_BRANCH_POINT = 3
EXIT_SCOPE_BREACH = 4
EXIT_NO_RECORD = 5
EXIT_WRONG_VANTAGE = 6
EXIT_SHARED_WORKSPACE = 7
# ``start``'s one coordination flag, spelled once here because the caller
# that passes it is another process: the dispatch facade already holds this
# run's lock and runs ``workspace.py`` as its child.
LOCK_HELD = "--lock-held"
# The keys this family reads and writes, spelled where they are written.
# ``workspace.py`` re-exports them and holds the frontmatter ones against
# ``contracts/work-item.md``'s own bytes, so the name a stamp lands under
# and the name a grade reads are one. ``PATH_KEY`` is re-exported from its
# owner: the established tree is the dispatch attempt's.
ISOLATION_KEY = "isolation"
BRANCH_KEY = "workspace_branch"
BASELINE_KEY = "workspace_baseline"
PATH_KEY = workspace_record.PATH_KEY
# What ``start`` records for a workspace that is on no branch. ``rev-parse
# --abbrev-ref HEAD`` answers the literal word ``HEAD`` there, which names
# no ref at the join. The sha under this prefix is a ref every git call can
# resolve.
DETACHED_PREFIX = "detached:"
# A frontmatter scalar carries the dirty set as one comma-joined line, so a
# path holding either character cannot be written unambiguously.
AMBIGUOUS = (",", '"', "'")
# A detached record names a revision, not a ref that follows the item. Only
# a standing worktree past that revision says where the work went, so a
# record no single standing worktree carries is ungradable.


def _no_workspace(branch: str) -> str:
    """Why a recorded revision alone is not a workspace to grade."""

    return (
        f"{branch!r} names a revision no single standing worktree carries: "
        "nothing here can say where that workspace's work went, and the "
        "recorded revision alone grades work this item never did"
    )


class Refused(Exception):
    """What the workspace CLI will not do, with its named exit code."""

    def __init__(self, message: str, code: int = EXIT_ERROR, **detail):
        super().__init__(message)
        self.code = code
        self.detail = detail


def _git(cwd, *args: str):
    """Run git in the caller-selected tree under grade."""

    completed = subprocess.run(
        ["git", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=cwd
    )
    return (
        completed.returncode,
        completed.stdout.decode("utf-8", "replace"),
        completed.stderr.decode("utf-8", "replace"),
    )


def _git_out(cwd):
    """A ``git`` reader aimed at one tree, refusing rather than returning."""

    def read(*args: str) -> str:
        code, out, err = _git(str(cwd), *args)
        if code != 0:
            raise Refused(f"git {' '.join(args)}: {err.strip()}")
        return out.strip()

    return read


def _branch_tip(source, branch: str):
    """The revision a branch names in this repository, or ``None``."""

    code, out, _ = _git(
        str(source), "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}^{{commit}}"
    )
    return out.strip() if code == 0 and out.strip() else None


def dirty_paths(cwd, git=_git) -> list:
    """Every path ``git status`` reports, both ends of a rename included."""

    code, out, err = git(cwd, "status", "--porcelain", "-z")
    if code != 0:
        raise Refused(f"git status: {err.strip()}")
    fields = out.split("\0")
    found, index = [], 0
    while index < len(fields):
        entry = fields[index]
        index += 1
        if not entry:
            continue
        status, path = entry[:2], entry[3:]
        found.append(path)
        if "R" in status or "C" in status:
            if index < len(fields):
                found.append(fields[index])
                index += 1
    return found


NOTES_DIR = ".orch-notes"


def emission_split(dirty):
    """``(the item's uncommitted paths, the bytes a run emitted)``."""

    emitted = sorted(
        name for name in dirty
        if name.endswith((".pyc", ".pyo")) or "__pycache__" in name.split("/")
        or name == NOTES_DIR or name.startswith(NOTES_DIR + "/")
    )
    return sorted(set(dirty) - set(emitted)), emitted


def actual_mutations(name_status: str) -> list:
    """Normalize ``git diff --name-status --no-renames -z`` rows."""
    tokens = name_status.split("\0")
    rows = []
    index = 0
    operations = {"A": "create", "D": "delete", "M": "change", "T": "change"}
    while index < len(tokens) and tokens[index]:
        status = tokens[index]
        if "\t" in status:
            status, path = status.split("\t", 1)
            index += 1
        elif index + 1 < len(tokens):
            path = tokens[index + 1]
            index += 2
        else:
            raise Refused("git name-status output ended before its path")
        operation = operations.get(status[:1])
        if operation is None:
            raise Refused(f"git name-status returned unsupported status {status!r}")
        rows.append((operation, path))
    return sorted(set(rows))


def _current_branch(git_out) -> str:
    """This checkout's branch, named so that it resolves in either state."""

    branch = git_out("rev-parse", "--abbrev-ref", "HEAD")
    if branch != "HEAD":
        return branch
    return f"{DETACHED_PREFIX}{git_out('rev-parse', 'HEAD')}"


def _head_and_branch(git_out):
    """This workspace's branch and the revision it derives from."""

    return _current_branch(git_out), git_out("rev-parse", "HEAD")


def _worktrees(git_out) -> list:
    """Every record ``git worktree list --porcelain`` reports, as read."""

    found, current = [], {}
    for line in git_out("worktree", "list", "--porcelain").splitlines() + [""]:
        if line:
            key, _, value = line.partition(" ")
            current[key] = value
            continue
        if current:
            found.append(current)
        current = {}
    return found


def _tip_ref(branch: str) -> str:
    """The revision a recorded ``workspace_branch`` names."""

    return branch[len(DETACHED_PREFIX):] if branch.startswith(DETACHED_PREFIX) else branch


def _detached_tip(git_out, is_ancestor, sha):
    """Where a detached workspace stands now, or ``None`` if nothing says."""

    found = {
        entry["HEAD"]
        for entry in _worktrees(git_out)
        if "detached" in entry and entry.get("HEAD") and is_ancestor(sha, entry["HEAD"])
    }
    return found.pop() if len(found) == 1 else None


def _ticket_worktree(git_out, branch: str, tip: str):
    """The still-present linked worktree carrying this item's work, if any."""

    for entry in _worktrees(git_out):
        if entry.get("branch") == f"refs/heads/{branch}" or (
            "detached" in entry and entry.get("HEAD") == tip
        ):
            return Path(entry["worktree"]).resolve()
    return None


def _baseline(head: str, dirty) -> str:
    """The revision this workspace derives from, plus what was dirty at start."""

    for entry in dirty:
        for character in AMBIGUOUS:
            if character in entry:
                raise Refused(
                    f"dirty path {entry!r} contains {character!r}, which a comma-joined "
                    "frontmatter value cannot carry unambiguously: commit, "
                    "remove or rename it, then run start again"
                )
    return f"{head} clean" if not dirty else f"{head} dirty: {', '.join(dirty)}"


def revision_of(baseline) -> str:
    """The revision a ``workspace_baseline`` stamp names, dirty tail dropped."""

    return str(baseline or "").strip().split(" ")[0]


def _graded(payload, what: str) -> dict:
    """Grade a ``tickets.py`` result by its payload, never by exit status."""

    if not isinstance(payload, dict):
        raise Refused(f"{what}: tickets.py returned no payload")
    if "error" in payload:
        raise Refused(f"{what}: {payload['error']}")
    return payload


def _locate(run: str, ticket_id: str, where=None):
    """This workspace's repository root, and its ticket in the state sink."""

    start = Path(where) if where is not None else Path.cwd()
    root = state_root.find_repo_root(start)
    if root is None:
        raise Refused(f"not inside a git repository: {start}")
    path = state_root.tickets_root() / run / f"{ticket_id}.md"
    if not path.is_file():
        raise Refused(f"ticket not found: {run}/{ticket_id}")
    return root, path


def _record(
    ticket_path,
    prior_text: str,
    branch,
    baseline,
    workspace_path: str,
    *,
    run=None,
    lock_held: bool = False,
) -> dict:
    """Write both stamps under the run lock, against the text read there."""

    lock = nullcontext() if lock_held or run is None else tickets_store._run_lock(run)
    try:
        with lock:
            return _stamped(ticket_path, prior_text, branch, baseline, workspace_path)
    except OSError as error:
        return {"error": f"unable to lock run '{run}': {error}"}


def _stamped(ticket_path, prior_text: str, branch, baseline, workspace_path: str) -> dict:
    """Read, compare, and stamp: every byte written derives from this read."""

    try:
        current_text = ticket_path.read_text(encoding="utf-8")
    except OSError as error:
        return {"error": f"unreadable ticket: {error}"}
    if current_text != prior_text:
        return {"error": "ticket changed since read; lost the frontmatter write race, retry"}
    try:
        updated = current_text
        recorded = {PATH_KEY: workspace_path}
        if branch is not None:
            updated = tickets_format._set_frontmatter_field(updated, BRANCH_KEY, branch)
            recorded[BRANCH_KEY] = branch
        if baseline is not None:
            updated = tickets_format._set_frontmatter_field(updated, BASELINE_KEY, baseline)
            recorded[BASELINE_KEY] = baseline
        updated, _carried = workspace_record.recorded_on_attempt(
            updated, workspace_path
        )
        # The sink's own writer, not ``write_text``: it pins ``newline='\n'``
        # so a two-scalar stamp stays a two-line diff, and it replaces
        # atomically so a crash mid-write cannot truncate the ticket.
        # ``Path.write_text`` grew ``newline`` only in 3.10, below this
        # tree's 3.9 floor.
        tickets_store._write_text_atomically(ticket_path, updated)
    except (OSError, ValueError) as error:
        return {"error": f"unwritable ticket: {error}"}
    return {
        "recorded": recorded
    }


def _detached_trees(git_out, is_ancestor, sha) -> int:
    """How many standing worktrees a ``detached:`` record could name."""

    return len([
        entry for entry in _worktrees(git_out)
        if "detached" in entry and entry.get("HEAD")
        and is_ancestor(sha, entry["HEAD"])
    ])


def _records_this_tree(git_out, is_ancestor, recorded: str, branch: str) -> bool:
    """Whether a sibling's recorded workspace is the tree ``branch`` stands in."""

    if recorded == branch:
        return True
    if not (recorded.startswith(DETACHED_PREFIX) and branch.startswith(DETACHED_PREFIX)):
        return False
    return _detached_tip(git_out, is_ancestor, _tip_ref(recorded)) == _tip_ref(branch)


def _sharers(ticket_path, git_out, is_ancestor, branch: str) -> list:
    """Every other claimed ticket of this run that recorded this same tree."""

    if branch.startswith(DETACHED_PREFIX) and _detached_trees(
        git_out, is_ancestor, _tip_ref(branch)
    ) != 1:
        return []
    found = []
    for path in sorted(ticket_path.parent.glob("*.md")):
        # by path, which is the id the caller was dispatched under: ``_locate``
        # builds this one from the run and id it was given
        if path == ticket_path:
            continue
        data = tickets_store._load_ticket(path)
        if "error" in data or data.get("status") != tickets_transitions.CLAIMED:
            continue
        recorded = str(data.get(BRANCH_KEY) or "").strip()
        if _records_this_tree(git_out, is_ancestor, recorded, branch):
            found.append(str(data.get("id") or path.stem))
    return sorted(found)


def _is_ancestor(git, ancestor: str, descendant: str) -> bool:
    code, _, err = git("merge-base", "--is-ancestor", ancestor, descendant)
    if code in (0, 1):
        return code == 0
    raise Refused(
        f"git merge-base --is-ancestor {ancestor} {descendant}: {err.strip()}"
    )
