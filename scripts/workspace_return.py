"""Integrate and retire one work item's candidate workspace.

The return half of the candidate's life: the merge that carries its
commits into the checkout the run is driven from, and the removal of the
tree afterwards. Integration happens before retirement -- after retirement
the branch survives but the tree that named it does not, and a merge that
ran second would be merging a branch no worktree stands in. Retirement
reads evidence references through the custody owner; neither act writes a ticket.
"""

from __future__ import annotations

import hashlib
import os
import time
from contextlib import contextmanager
from pathlib import Path

try:
    from . import state_root, tickets_store, tickets_store_writes, workspace_git, workspace_custody
except ImportError:  # a flat ``bin`` layout, where these are top-level modules
    import state_root
    import tickets_store
    import tickets_store_writes
    import workspace_git
    import workspace_custody

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
    with integration_lock(root):
        return _integrate_locked(run, ticket_id, root, into, target, branch, baseline, body)


def _integrate_locked(run, ticket_id, root, into, target, branch, baseline, body):
    if workspace_git._branch_tip(root, branch) is None:
        return {"integrate": dict(
            body, outcome="absent", main_root=str(root), into=into,
            detail=_absent_detail(run, ticket_id, root, into, branch, target),
        )}, EXIT_OK
    if state_root.main_checkout_root(target / '.git') != state_root.find_repo_root(root):
        raise Refused(f"candidate {target} belongs to another repository, not integration target {root}")
    read_root = workspace_git._git_out(root)
    before = read_root("rev-parse", "HEAD")
    standing = workspace_git._current_branch(read_root)
    detached_progress = (
        into.startswith(workspace_git.DETACHED_PREFIX)
        and standing.startswith(workspace_git.DETACHED_PREFIX)
        and workspace_git._is_ancestor(
            lambda *args: workspace_git._git(str(root), *args),
            workspace_git._tip_ref(into), before,
        )
    )
    # The recorded path fixes the checkout; a detached revision fixes its
    # ancestry, not the HEAD value after each successful merge.
    if standing != into and not detached_progress:
        raise Refused(
            f"{root} stands on {standing!r}, not the {into!r} this run's first "
            f"establishment recorded as its integration target. Nothing merges "
            f"a run's work onto a branch the run never named: check {into!r} "
            f"out there, then land {run}/{ticket_id} again"
        )
    _refuse_uncommitted_delivery(run, ticket_id, root, target, branch, baseline)
    pending, _, _ = workspace_git._git(str(root), "rev-parse", "--verify", "--quiet", "MERGE_HEAD")
    if pending == 0:
        raise Refused(f"{root} has an unfinished merge; inspect and resolve or abort it before retrying")
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
    read = workspace_git._git_out(target)
    if workspace_git._current_branch(read) != branch:
        raise Refused(f"{target} no longer stands on its derived branch {branch}; nothing removed")
    dirty, _ = workspace_git.emission_split(workspace_git.dirty_paths(str(target)))
    if dirty and not force:
        raise Refused(_retirement_refusal(run, ticket_id, main, target, [], "uncommitted work"))
    custody = workspace_custody.archive(run, ticket_id, target)
    workspace_custody.release_scratch(target, custody)
    unknown = sorted(set(filter(None, (
        read('ls-files', '--others', '--exclude-standard', '-z') + '\0' +
        read('ls-files', '--others', '--ignored', '--exclude-standard', '-z')
    ).split('\0'))))
    if unknown and not force:
        raise Refused(
            f"{target} retains unknown untracked or ignored content; archive explicit evidence references or move owned files before retrying",
            retained=str(target), unknown=unknown, custody=custody,
            runtime_dependencies='Package-specific absolute runtime dependencies are not relocated or copied',
        )
    argv = ["worktree", "remove", *(["--force"] if force else []), str(target)]
    code, _, err = workspace_git._git(str(main), *argv)
    if code != 0:
        raise Refused(_retirement_refusal(run, ticket_id, main, target, argv, err))
    workspace_git._git(str(main), "worktree", "prune")
    return {
        "retire": dict(body, outcome="removed", main_root=str(main), custody=custody)
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


INTEGRATION_WAIT_SECONDS = 120


@contextmanager
def integration_lock(root, *, timeout=None):
    """Lock one resolved checkout across runs; caller takes its run lock first."""
    identity = os.path.normcase(os.path.realpath(os.fspath(root)))
    key = hashlib.sha256(identity.encode('utf-8')).hexdigest()
    directory = state_root.state_root() / state_root.LOCKS_SUBPATH / 'integration'
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (key + '.lock')
    deadline = time.monotonic() + (INTEGRATION_WAIT_SECONDS if timeout is None else timeout)
    locked = False
    with open(path, 'a+b') as handle:
        handle.seek(0, 2)
        if handle.tell() == 0:
            handle.write(b'\x00')
            handle.flush()
        while not locked:
            handle.seek(0)
            try:
                if tickets_store_writes.msvcrt is not None:
                    tickets_store_writes.msvcrt.locking(handle.fileno(), tickets_store_writes.msvcrt.LK_NBLCK, 1)
                elif tickets_store_writes.fcntl is not None:
                    tickets_store_writes.fcntl.flock(handle.fileno(), tickets_store_writes.fcntl.LOCK_EX | tickets_store_writes.fcntl.LOCK_NB)
                else:
                    raise Refused('host provides no integration locking mechanism')
                locked = True
            except (BlockingIOError, PermissionError):
                if time.monotonic() >= deadline:
                    raise Refused(f'integration target busy: {identity}; retry after its other landing finishes', lock=str(path), target=identity)
                time.sleep(min(0.05, max(0, deadline - time.monotonic())))
        try:
            yield
        finally:
            handle.seek(0)
            if tickets_store_writes.msvcrt is not None:
                tickets_store_writes.msvcrt.locking(handle.fileno(), tickets_store_writes.msvcrt.LK_UNLCK, 1)
            else:
                tickets_store_writes.fcntl.flock(handle.fileno(), tickets_store_writes.fcntl.LOCK_UN)
