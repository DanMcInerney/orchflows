"""Integrate and retire one work item's candidate workspace.

The return half of the candidate's life: the merge that carries its
commits into the checkout the run is driven from, and the removal of the
tree afterwards. Integration happens before retirement -- after retirement
the branch survives but the tree that named it does not, and a merge that
ran second would be merging a branch no worktree stands in. Neither reads
nor writes a ticket.
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
    """Merge this item's candidate branch into the run's own checkout."""

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
            # carried, not re-parsed out of the sentence above: a reader of
            # the item's `## Report` is entitled to the list git gave
            conflicted=paths, into=into, root=str(root),
        )
    after = read_root("rev-parse", "HEAD")
    return {"integrate": dict(
        body, outcome="replayed" if after == before else "merged",
        into=into, main_root=str(root), revision=after,
        # the candidate's own identity beside the tree's: which revision a
        # resolution delivered is what the integrated tip does not carry
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
    """``(root, branch)`` the run's first establishment named, or refuse."""

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
    """Refuse a candidate that would merge as a replay while holding work."""

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
    """Remove the derived tree, leaving every stamp that names it in place."""

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
    """Why a tree was not removed, its bytes first."""

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
