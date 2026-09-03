"""Integrate and retire one work item's candidate workspace.

The return half of the candidate's life. ``workspace_candidate`` owns what
a candidate *is* -- the tree it gets, the branch that tree stands on, the
stamp its ticket carries -- and this owns what becomes of it once the item
has run: the merge that carries its commits into the checkout the run is
being driven from, and the removal of the tree afterwards.

The two live together because their order is the whole point. Integration
happens before retirement: after retirement the branch survives but the
tree that named it does not, and a merge that ran second would be merging
a branch no worktree stands in. Neither reads or writes a ticket, which is
why they sit apart from the establishment lanes that do nothing else.
"""

from __future__ import annotations

from pathlib import Path

try:
    from . import state_root, tickets_store, workspace_git
except ImportError:  # a flat ``bin`` layout, where these are top-level modules
    import state_root
    import tickets_store
    import workspace_git

Refused = workspace_git.Refused
BRANCH_KEY = workspace_git.BRANCH_KEY
PATH_KEY = workspace_git.PATH_KEY
EXIT_OK = workspace_git.EXIT_OK


def integrate(run: str, ticket_id: str, workspace, branch, baseline=None):
    """Merge this item's candidate branch into the run's own checkout.

    The step `land` used to leave for hand git, which is how a run once
    reported a landed item whose commits never reached the checkout anyone
    read. One merge, before the worktree is retired: after retirement the
    branch survives but the tree that named it does not, and the ordering
    is the whole reason this lives beside `retire` rather than after it.

    The tree and the branch are the establishment's own records, handed in
    rather than re-derived here. `retire` may re-derive because a spent path
    answers for an archived ticket; a merge may not, because the only branch
    it is lawful to merge is the one this attempt actually stood on. Where
    it is merged *to* is a record for the same reason: read live off
    whatever the repository had checked out, this once wrote a run's whole
    result onto an unrelated branch of the user's own checkout, and ran the
    `done` predicate in that tree. A checkout that has moved off the
    recorded branch since is refused, never followed.

    A conflict is refused, not resolved and not left half-applied: the merge
    is aborted so the run's own checkout is never handed back mid-merge, and
    the refusal names the conflicted paths and the one remedy -- resolve
    them in the candidate, then land again. Replaying is free: git answers
    an already-merged branch with an unchanged HEAD, which is reported as a
    replay rather than as a second merge -- unless the branch never advanced
    past its own `workspace_baseline` and the candidate is holding
    uncommitted work, which is no replay at all but a delivery that was
    never committed, and is refused. A branch that has carried real commits
    is a lawful replay regardless of whatever scratch a worker's candidate
    is still holding: that dirt is graded by `check` at the join, not here.

    There are two `absent` answers and they are not the same finding. A
    candidate the records do not resolve to a linked worktree of a readable
    repository is nothing this looked anywhere for -- an item that ran in
    the caller's own checkout, or one whose tree a previous landing already
    retired -- and it answers `absent` bare, which is how a second landing
    of a retired candidate stays a replay. A candidate that does resolve,
    against a run that recorded a target which does not carry its branch,
    is the 2026-09-02 ladder defect: the candidate was cut from one
    repository and the run integrates into another. That `absent` carries
    the repository and branch it looked for and the sentence saying so, and
    `land` stops on it rather than reporting a landed item whose commits
    reached no checkout anybody reads.
    """

    target = Path(str(workspace or "")).expanduser() if workspace else None
    branch = str(branch or "").strip()
    body = {
        "run": run, "id": ticket_id,
        PATH_KEY: None if target is None else str(target), BRANCH_KEY: branch or None,
    }
    linked = (
        state_root.main_checkout_root(target / ".git")
        if branch and target is not None and (target / ".git").is_file() else None
    )
    if linked is None or not Path(linked).is_dir():
        return {"integrate": dict(body, outcome="absent")}, EXIT_OK
    root, into = _recorded_target(run, ticket_id)
    if workspace_git._branch_tip(root, branch) is None:
        return {"integrate": dict(
            body, outcome="absent", main_root=str(root), into=into,
            detail=_absent_detail(run, ticket_id, root, into, branch, target),
        )}, EXIT_OK
    read_root = workspace_git._git_out(root)
    before = read_root("rev-parse", "HEAD")
    standing = workspace_git._current_branch(read_root)
    if standing != into:
        raise Refused(
            f"{root} stands on {standing!r}, not the {into!r} this run's first "
            f"establishment recorded as its integration target. Nothing merges "
            f"a run's work onto a branch the run never named: check {into!r} "
            f"out there, then land {run}/{ticket_id} again"
        )
    _refuse_uncommitted_delivery(run, ticket_id, root, target, branch, baseline)
    code, _, err = workspace_git._git(
        str(root), "merge", "--no-ff", "--no-edit", branch
    )
    if code != 0:
        _, conflicted, _ = workspace_git._git(
            str(root), "diff", "--name-only", "--diff-filter=U"
        )
        workspace_git._git(str(root), "merge", "--abort")
        paths = sorted(name for name in conflicted.splitlines() if name.strip())
        raise Refused(
            f"git merge {branch} into {into!r} at {root} refused: "
            + (", ".join(paths) if paths else err.strip())
            + f". Resolve them in the candidate at {target}, commit there, then "
            f"land {run}/{ticket_id} again",
            # carried, not re-parsed out of the sentence above: the join
            # files these paths into the item's own `## Report`, and a
            # reader of that record is entitled to the list git gave rather
            # than to whatever a regex could recover from prose
            conflicted=paths, into=into, root=str(root),
        )
    after = read_root("rev-parse", "HEAD")
    return {"integrate": dict(
        body, outcome="replayed" if after == before else "merged",
        into=into, main_root=str(root), revision=after,
        # the candidate's own identity beside the tree's: after a conflict
        # was resolved, which revision the resolution delivered is the half
        # of the answer the integrated tip does not carry
        tip=workspace_git._branch_tip(root, branch),
    )}, EXIT_OK


def _absent_detail(run, ticket_id, root, into, branch, target) -> str:
    """Why there was nothing to merge, naming where this looked and for what."""

    return (
        f"no branch {branch!r} in {root}, the checkout on {into!r} that run "
        f"{run!r} recorded as its integration target: {ticket_id}'s candidate "
        f"at {target} was cut from another repository. Establish it from the "
        f"checkout this run integrates into, then land {run}/{ticket_id} again"
    )


def _recorded_target(run: str, ticket_id: str):
    """``(root, branch)`` the run's first establishment named, or refuse.

    A run that recorded none is a run whose candidates were established
    before there was anywhere to record it. There is no second place to
    read the answer out of -- the checkout's incumbent branch is exactly
    the guess this exists to end -- so the refusal names the establishment
    that records it, which replays against an existing tree and writes the
    target on its way through.

    The remedy names ``--repo``, and has to: only an establishment that
    *names* its tree fixes the target, so the flagless command this refusal
    used to prescribe replays at exit 0 and records nothing -- a refusal
    whose one way out is a dead end. Only a delivering item's establishment
    fixes it either, a judging item's never does, and that condition is
    named here rather than derived: this module reads no ticket.
    """

    recorded = tickets_store.integration_target(run)
    if recorded is None:
        raise Refused(
            f"run {run!r} records no integration target: nothing says which "
            f"checkout and branch this run's work belongs on. Run "
            f"'workspace.py establish {run} {ticket_id} --repo <the checkout "
            f"this run integrates into>' -- only a --repo establishment of a "
            f"delivering item records the target, and it replays against the "
            f"existing tree -- then land {run}/{ticket_id} again"
        )
    root = Path(recorded["root"]).expanduser()
    if not root.is_dir():
        raise Refused(
            f"the integration target {root} this run recorded is not a "
            f"directory: restore that checkout, then land {run}/{ticket_id} again"
        )
    return root, recorded["branch"]


def _refuse_uncommitted_delivery(run, ticket_id, root, target, branch, baseline) -> None:
    """Refuse a candidate that would merge as a replay while holding work.

    Two members of one run landed `complete` on branches carrying zero
    commits: each worker closed without committing, the merge was a no-op,
    and integration reported `replayed` -- the one word that reads exactly
    like a lawful second landing, so nothing downstream looked again. The
    tell used to be read off ancestry -- whether the branch tip was already
    merged into the checkout's HEAD -- but a branch replayed after a real
    delivery is *also* already merged, and a worker's own compliant scratch
    (the `.orch-outcome-*`/`.orch-report-*` note files the launch prompt
    tells every worker to write) then read as the same "never committed"
    delivery a second, differently-named time. The tell that actually
    distinguishes them is whether the branch ever advanced past the
    revision `workspace.py establish` cut it from: a branch still standing
    at its own write-once `workspace_baseline` delivered nothing, no matter
    what commits already sit on the main checkout's own history; a branch
    past its baseline has carried something, replayed or not, and whatever
    scratch its candidate still holds beside that is the worker's business,
    graded by `check` at the join rather than here.
    """

    if not target.is_dir():
        return
    tip = workspace_git._branch_tip(root, branch)
    if tip is None or tip != workspace_git.revision_of(baseline):
        return
    dirty, _emitted = workspace_git.emission_split(
        sorted(set(workspace_git.dirty_paths(str(target))))
    )
    if not dirty:
        return
    raise Refused(
        f"branch {branch!r} carries no commit past its own established "
        f"baseline, and its candidate at {target} is holding uncommitted "
        f"work: "
        + ", ".join(dirty)
        + f". That is a delivery that was never committed, not a replay. "
        f"Commit it in the candidate, then land {run}/{ticket_id} again"
    )


def retire(run: str, ticket_id: str, *, force: bool = False):
    """Remove the derived tree, leaving every stamp that names it in place.

    The ticket is not read and not written. Its ``workspace_branch`` and
    ``workspace_baseline`` are what the join grades the item by, long after
    the tree they were observed in is gone, and a retirement that cleared
    them would grade the work as never isolated. The path is derived, so
    this answers for an item whose ticket has already been archived.

    A tree that was never created is not a failure, and a tree git cannot
    remove is not quietly left behind: the refusal names what to do next.
    Never ``--force``. The flag exists for a caller who has looked at the
    tree and decided, and a refusal that prescribed it stood between a
    worker's only uncommitted copy and its deletion. What the refusal names
    instead is the act that preserves those bytes.
    """

    candidate = state_root.candidate_paths(run, ticket_id)
    target, branch = candidate["path"], candidate["branch"]
    body = {"run": run, "id": ticket_id, PATH_KEY: str(target), BRANCH_KEY: branch}
    if not target.exists():
        return {"retire": dict(body, outcome="absent")}, EXIT_OK
    main = state_root.main_checkout_root(target / ".git")
    if main is None:
        raise Refused(
            f"{target} is not a linked worktree of any repository this can reach: "
            f"remove it by hand, then run 'workspace.py retire {run} {ticket_id}'"
        )
    argv = ["worktree", "remove", *(["--force"] if force else []), str(target)]
    code, _, err = workspace_git._git(str(main), *argv)
    if code != 0:
        raise Refused(_retirement_refusal(run, ticket_id, main, target, argv, err))
    workspace_git._git(str(main), "worktree", "prune")
    return {
        "retire": dict(body, outcome="removed", main_root=str(main))
    }, EXIT_OK


def _retirement_refusal(run, ticket_id, main, target, argv, err) -> str:
    """Why a tree was not removed, its bytes first.

    Uncommitted work is the common cause and the only one where the
    obvious command destroys something: those bytes are somebody's
    delivery, and the remedy is to land it, not to overrule the refusal
    that saved it. Git's own words are dropped in that case rather than
    quoted -- git ends them by naming ``--force``, and a reader scanning a
    refusal for a command finds whatever command the refusal contains.

    Anything else is a tree this cannot speak for. There git's words are
    the evidence and are kept, and the reader is sent to look at the tree
    before running the removal by hand.
    """

    try:
        dirty, _emitted = workspace_git.emission_split(
            sorted(set(workspace_git.dirty_paths(str(target))))
        )
    except Refused:  # pragma: no cover - a tree git will not report on at all
        dirty = []
    if dirty:
        return (
            f"{target} is holding uncommitted work, so it was not removed: "
            + ", ".join(dirty)
            + f". Commit it in that tree and land {run}/{ticket_id} again, or "
            f"move those files out of it. Nothing here deletes them"
        )
    return (
        f"git {' '.join(argv)}: {err.strip()}. Read what is in {target}, then "
        f"remove it yourself with 'git -C {main} worktree remove {target}'"
    )


__all__ = ("integrate", "retire")
