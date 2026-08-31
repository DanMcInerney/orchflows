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
    from . import state_root, workspace_git
except ImportError:  # a flat ``bin`` layout, where these are top-level modules
    import state_root
    import workspace_git

Refused = workspace_git.Refused
BRANCH_KEY = workspace_git.BRANCH_KEY
PATH_KEY = workspace_git.PATH_KEY
EXIT_OK = workspace_git.EXIT_OK


def integrate(run: str, ticket_id: str, workspace, branch):
    """Merge this item's candidate branch into the tree the run stands in.

    The step `land` used to leave for hand git, which is how a run once
    reported a landed item whose commits never reached the checkout anyone
    read. One merge, in the main checkout the candidate was cut from, before
    the worktree is retired: after retirement the branch survives but the
    tree that named it does not, and the ordering is the whole reason this
    lives beside `retire` rather than after it.

    The tree and the branch are the establishment's own records, handed in
    rather than re-derived here. `retire` may re-derive because a spent path
    answers for an archived ticket; a merge may not, because the only branch
    it is lawful to merge is the one this attempt actually stood on.

    A conflict is refused, not resolved and not left half-applied: the merge
    is aborted so the run's own checkout is never handed back mid-merge, and
    the refusal names the conflicted paths and the one remedy -- resolve
    them in the candidate, then land again. Replaying is free: git answers
    an already-merged branch with an unchanged HEAD, which is reported as a
    replay rather than as a second merge.

    Anything the records do not resolve to a linked worktree of a readable
    repository is `absent`, never an error: an item that ran in the caller's
    own checkout has nothing to merge into it.
    """

    target = Path(str(workspace or "")).expanduser() if workspace else None
    branch = str(branch or "").strip()
    body = {
        "run": run, "id": ticket_id,
        PATH_KEY: None if target is None else str(target), BRANCH_KEY: branch or None,
    }
    main = (
        state_root.main_checkout_root(target / ".git")
        if branch and target is not None and (target / ".git").is_file() else None
    )
    if main is None or not Path(main).is_dir() or workspace_git._branch_tip(main, branch) is None:
        return {"integrate": dict(body, outcome="absent")}, EXIT_OK
    read_main = workspace_git._git_out(main)
    before = read_main("rev-parse", "HEAD")
    into = workspace_git._current_branch(read_main)
    code, _, err = workspace_git._git(
        str(main), "merge", "--no-ff", "--no-edit", branch
    )
    if code != 0:
        _, conflicted, _ = workspace_git._git(
            str(main), "diff", "--name-only", "--diff-filter=U"
        )
        workspace_git._git(str(main), "merge", "--abort")
        paths = sorted(name for name in conflicted.splitlines() if name.strip())
        raise Refused(
            f"git merge {branch} into {into!r} at {main} refused: "
            + (", ".join(paths) if paths else err.strip())
            + f". Resolve them in the candidate at {target}, commit there, then "
            f"land {run}/{ticket_id} again"
        )
    after = read_main("rev-parse", "HEAD")
    return {"integrate": dict(
        body, outcome="replayed" if after == before else "merged",
        into=into, main_root=str(main), revision=after,
    )}, EXIT_OK


def retire(run: str, ticket_id: str, *, force: bool = False):
    """Remove the derived tree, leaving every stamp that names it in place.

    The ticket is not read and not written. Its ``workspace_branch`` and
    ``workspace_baseline`` are what the join grades the item by, long after
    the tree they were observed in is gone, and a retirement that cleared
    them would grade the work as never isolated. The path is derived, so
    this answers for an item whose ticket has already been archived.

    A tree that was never created is not a failure, and a tree git cannot
    remove is not quietly left behind: the refusal names the exact command
    that removes it by hand.
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
        raise Refused(
            f"git {' '.join(argv)}: {err.strip()}. Retire it by hand with "
            f"'git -C {main} worktree remove --force {target}'"
        )
    workspace_git._git(str(main), "worktree", "prune")
    return {
        "retire": dict(body, outcome="removed", main_root=str(main))
    }, EXIT_OK


__all__ = ("integrate", "retire")
