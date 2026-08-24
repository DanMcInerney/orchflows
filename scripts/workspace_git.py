"""Git lifecycle and guarded ticket stamps for ``workspace.py``."""

from __future__ import annotations

import subprocess
from pathlib import Path

import state_root
import tickets


EXIT_ERROR = 1
# What ``start`` records for a workspace that is on no branch. ``rev-parse
# --abbrev-ref HEAD`` answers the literal word ``HEAD`` there, which names no
# ref at the join: the item graded isolation-missing however clean its work
# was. The sha under this prefix is a ref every git call can resolve.
DETACHED_PREFIX = "detached:"
# A frontmatter scalar carries the dirty set as one comma-joined line, so a
# path holding either character cannot be written unambiguously.
AMBIGUOUS = (",", '"', "'")
# A detached record names a revision, not a ref that follows the item. Only a
# standing worktree past that revision says where the work went, so a record
# no single standing worktree carries is ungradable -- never a pass over
# whatever the recorded revision alone happens to hold.


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


def _dirty_paths(cwd, git=_git) -> list:
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


def _current_branch(git_out) -> str:
    """This checkout's branch, named so that it resolves in either state.

    The sha is read only when there is no branch to read instead: ``check``
    calls this once per grade, and a caller that has stubbed git for the
    calls a grade makes should not have to answer a call a grade never
    needed.
    """

    branch = git_out("rev-parse", "--abbrev-ref", "HEAD")
    if branch != "HEAD":
        return branch
    return f"{DETACHED_PREFIX}{git_out('rev-parse', 'HEAD')}"


def _head_and_branch(git_out):
    """This workspace's branch and the revision it derives from."""

    return _current_branch(git_out), git_out("rev-parse", "HEAD")


def _checkouts(git_out) -> list:
    """Every directory this repository is checked out in."""

    return [
        Path(entry["worktree"]).resolve()
        for entry in _worktrees(git_out)
        if entry.get("worktree")
    ]


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
    """Where a detached workspace stands now, or ``None`` if nothing says.

    A branch name resolves to whatever the item committed onto it; a bare sha
    is frozen at the moment ``start`` read it, so grading it directly sees
    none of the item's commits. The standing detached worktree past that sha
    is the same item's workspace, and its HEAD is the ref a branch would have
    been -- but only when exactly one such worktree stands. None of them and
    the workspace is gone, taking the only record of where its work went;
    two of them and the recorded revision, which is all either workspace
    recorded, cannot say which is this item's. Both answers are ``None``,
    because both grade some other work as this item's if answered.
    """

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
    """The revision this workspace derives from, plus what was dirty at start.

    ``orch-workspace`` forbids proceeding without recording, not proceeding:
    a dirty tree is stamped, never refused. A path carrying one of the
    characters below is refused, because the stamp is one comma-joined
    frontmatter scalar and no reader could tell such a path's ends apart.
    """

    for entry in dirty:
        for character in AMBIGUOUS:
            if character in entry:
                raise Refused(
                    f"dirty path {entry!r} contains {character!r}, which a comma-joined "
                    "frontmatter value cannot carry unambiguously: commit, "
                    "remove or rename it, then run start again"
                )
    return f"{head} clean" if not dirty else f"{head} dirty: {', '.join(dirty)}"


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


def _record(ticket_path, prior_text: str, branch: str, baseline: str) -> dict:
    """Write both stamps against the snapshot the caller read."""

    try:
        current_text = ticket_path.read_text(encoding="utf-8")
    except OSError as error:
        return {"error": f"unreadable ticket: {error}"}
    if current_text != prior_text:
        return {"error": "ticket changed since read; lost the frontmatter write race, retry"}
    try:
        updated = tickets._set_frontmatter_field(prior_text, "workspace_branch", branch)
        updated = tickets._set_frontmatter_field(updated, "workspace_baseline", baseline)
        ticket_path.write_text(updated, encoding="utf-8")
    except (OSError, ValueError) as error:
        return {"error": f"unwritable ticket: {error}"}
    return {
        "recorded": {
            "workspace_branch": branch,
            "workspace_baseline": baseline,
        }
    }


def _detached_trees(git_out, is_ancestor, sha) -> int:
    """How many standing worktrees a ``detached:`` record could name.

    Those at or past the revision it names: a worktree that has committed
    since has moved past it, so equality of tips would miss the very tree the
    record was written from. The same set ``_detached_tip`` resolves a tip
    out of, counted by directory rather than by tip -- two worktrees at one
    revision are one tip and two answers.
    """

    return len([
        entry for entry in _worktrees(git_out)
        if "detached" in entry and entry.get("HEAD")
        and is_ancestor(sha, entry["HEAD"])
    ])


def _sharers(ticket_path, git_out, is_ancestor, branch: str) -> list:
    """Every other claimed ticket of this run that recorded this same tree.

    ``start`` cannot see a workspace from the outside: from inside any linked
    worktree the tree looks the caller's own, which is why ``top != root``
    answered true for a whole cut dispatched into one shared directory. What
    can be seen is what the siblings recorded. ``_record`` stamps
    ``workspace_branch`` into each item's ticket, the run's tickets are this
    one's own neighbours in the sink, and git checks a branch out in at most
    one tree -- so a sibling carrying this branch is standing where this item
    stands.

    Only ``claimed`` siblings count. A finished item has left the tree, and
    counting it would flag a long run's last item for every workspace its
    predecessors have already released, which is a flag nobody could act on.
    The item's own ticket is skipped so that a re-established workspace never
    reports itself as its own sharer -- by then its own stamp is in the sink.

    The read goes through the same ``tickets`` loader the caller grades its own
    ticket with, never a second resolver. A sibling that will not parse is no
    evidence of sharing, so it is passed over rather than raised: this is a
    report about the caller's tree, and it must not be the thing that stops an
    item over some other item's malformed file.

    A detached record names the revision ``start`` read rather than a ref, so
    it identifies a directory only where one directory could have written it:
    two workspaces materialized at one revision record the identical string.
    Which directories could have is a question git answers and no frontmatter
    stamp is needed for -- the standing detached worktrees at or past that
    revision. Exactly one of them and the record names it, which is the
    shared-tree case with the branch left off; more and equality is no
    evidence at all, and reading it as evidence flags two genuinely isolated
    workspaces, the same ambiguity ``_detached_tip`` refuses to resolve.
    """

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
        data = tickets._load_ticket(path)
        if "error" in data or data.get("status") != "claimed":
            continue
        if str(data.get("workspace_branch") or "").strip() == branch:
            found.append(str(data.get("id") or path.stem))
    return sorted(found)


def _is_ancestor(git, ancestor: str, descendant: str) -> bool:
    code, _, err = git("merge-base", "--is-ancestor", ancestor, descendant)
    if code in (0, 1):
        return code == 0
    raise Refused(
        f"git merge-base --is-ancestor {ancestor} {descendant}: {err.strip()}"
    )
