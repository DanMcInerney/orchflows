"""Establish, replay and retire one work item's candidate workspace.

``workspace.py`` is the CLI facade; this module owns what a candidate
workspace *is* for one work item -- the tree it gets, the branch that tree
stands on, and the observation its ticket is stamped from. It never imports
that facade, nor ``tickets``: the owning modules are imported directly, the
way ``workspace_git`` imports them.

Two lanes, and the ticket's own ``isolation`` decides which. An item that
declares ``required`` gets a tree of its own, created here at the path
``state_root.candidate_paths`` derives from its run and its id -- never a
tree a caller named, because a caller naming the tree is how two siblings
came to be dispatched into one directory and how a packet came to carry
another item's workspace. Everything else is observed rather than created:
the caller stands somewhere, and what it is standing in is recorded.

Creation happens before the run lock is taken and never inside it. The
derived path belongs to exactly one ticket of one run, so no other writer
can be racing for it, and the seconds ``git worktree add`` costs are
seconds no sibling has to wait through. The stamp that follows is the
locked half, and it is written against the ticket's bytes as they were
read -- a write that landed in between is reported, never absorbed.

``prepare`` is the same argument taken to its end: installing what the
tree declares costs a package manager's minutes and writes no ticket at
all, so it is its own verb, run against the recorded ``workspace_path``
after the establishment's lock has been let go.

Nothing here records a success it did not achieve. A refused establishment
leaves the ticket exactly as it was found, and never falls back to the
shared tree the item was dispatched from: an unisolated item that believes
it is isolated writes its work into somebody else's checkout.
"""

from __future__ import annotations

from pathlib import Path

try:
    from . import state_root, tickets_adapters, tickets_format, tickets_store
    from . import workspace_git, workspace_prepare
except ImportError:  # a flat ``bin`` layout, where these are top-level modules
    import state_root
    import tickets_adapters
    import tickets_format
    import tickets_store
    import workspace_git
    import workspace_prepare

Refused = workspace_git.Refused
ISOLATION_KEY = workspace_git.ISOLATION_KEY
BRANCH_KEY = workspace_git.BRANCH_KEY
BASELINE_KEY = workspace_git.BASELINE_KEY
PATH_KEY = workspace_git.PATH_KEY
REQUIRED = tickets_format.REQUIRED_ISOLATION
EXIT_OK = workspace_git.EXIT_OK
EXIT_SHARED_WORKSPACE = workspace_git.EXIT_SHARED_WORKSPACE
EVIDENCE_STRATEGY = "evidence-store"
GIT_STRATEGY = "git"
# The keys a payload carries under ``start`` and under ``establish``. Two
# verbs, one body: the facade reads one field out of either.
START_KEY = "start"
ESTABLISH_KEY = "establish"


def _git_out(cwd):
    """A ``git`` reader aimed at one tree, refusing rather than returning."""

    def read(*args: str) -> str:
        code, out, err = workspace_git._git(str(cwd), *args)
        if code != 0:
            raise Refused(f"git {' '.join(args)}: {err.strip()}")
        return out.strip()

    return read


def _validate_write_paths(entries, root: Path) -> None:
    """Refuse prose-shaped write declarations before a candidate starts."""

    if not isinstance(entries, list):
        return
    for declared in entries:
        entry = tickets_format.dequote(declared)
        candidate = Path(entry).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        if "(" in entry or ")" in entry or (" " in entry and not candidate.exists()):
            raise Refused(
                f"write_scope entry {entry!r} is not a path; "
                "see contracts/work-item.md"
            )


def _loaded(run: str, ticket_id: str):
    """The ticket, its data, and the bytes every stamp below derives from.

    The snapshot is taken here and not after the git work: those calls are
    the seconds a concurrent ``set-status`` lands in, and a snapshot taken
    past them absorbs the write the compare exists to report.
    """

    path = state_root.tickets_root() / run / f"{ticket_id}.md"
    if not path.is_file():
        raise Refused(f"ticket not found: {run}/{ticket_id}")
    data = workspace_git._graded(
        tickets_store._load_ticket(path), f"read {run}/{ticket_id}"
    )
    return path, data, path.read_text(encoding="utf-8")


def _adapter(data: dict):
    try:
        return tickets_adapters.adapter_spec(data.get("pack"))
    except tickets_adapters.AdapterError as error:
        raise Refused(f"{error.code}: {error.detail}") from error


def _evidence(run, ticket_id, path, prior_text, adapter, held, seams) -> dict:
    """A research lane's workspace is the run-scoped evidence store."""

    store = (state_root.state_root() / "research" / run).resolve()
    store.mkdir(parents=True, exist_ok=True)
    outcome = seams["record"](
        path, prior_text, None, None, str(store), run=run, lock_held=held
    )
    if "error" in outcome:
        raise Refused(outcome["error"])
    return {
        "run": run,
        "id": ticket_id,
        "ticket": str(path),
        "mechanism": adapter.key,
        PATH_KEY: str(store),
        "workspace_root": str(store),
    }


def _observed(run, ticket_id, path, data, prior_text, held, seams, where):
    """Record the Git tree the caller is standing in, and grade its sharing.

    What ``start`` has always done, unchanged: ``start`` never creates a
    tree, and an item whose isolation is not ``required`` has no tree of its
    own to create. Exit 7 stays reachable here and only here -- a shared
    directory is a fact about a tree somebody else chose, and an item given
    its derived candidate cannot be standing in one.
    """

    git_out = seams["git_out"]
    root, located = workspace_git._locate(run, ticket_id, where)
    if located != path:
        raise Refused(f"ticket identity changed while locating {run}/{ticket_id}")
    top = Path(git_out("rev-parse", "--show-toplevel")).resolve()
    _validate_write_paths(data.get("write_scope"), top)
    branch, head = workspace_git._head_and_branch(git_out)
    dirty = sorted(set(seams["dirty_paths"]()))
    # Write-once: ``tickets_packet.py`` feeds this stamp to ``cutcheck.py
    # --baseline``, so it goes on naming the revision the item was cut from,
    # never the moved tree a re-establishment stands in. The observation is
    # reported under its own key instead of recorded: a second stamp would
    # have to be a key ``contracts/work-item.md`` declares. Computed either
    # way, because it also refuses a dirty path no comma-joined frontmatter
    # scalar could carry unambiguously.
    observed = workspace_git._baseline(head, dirty)
    stamped = str(data.get(BASELINE_KEY) or "").strip()
    baseline = stamped or observed
    outcome = seams["record"](
        path, prior_text, branch, baseline, str(top), run=run, lock_held=held
    )
    if "error" in outcome:
        raise Refused(outcome["error"])
    # after recording: this item's own stamp is in the sink, and skipped
    sharing = workspace_git._sharers(path, git_out, seams["is_ancestor"], branch)
    body = {
        "run": run,
        "id": ticket_id,
        "ticket": str(path),
        BRANCH_KEY: branch,
        BASELINE_KEY: baseline,
        PATH_KEY: str(top),
        # present only on a re-establishment, which its presence declares
        **({"reestablished": observed} if stamped else {}),
        "workspace_root": str(top),
        "main_root": str(root),
        # a linked tree is necessary, and no longer sufficient
        "isolated": top != root and not sharing,
        "shared_with": sharing,
        "dirty": dirty,
    }
    return body, EXIT_SHARED_WORKSPACE if sharing else EXIT_OK


def _standing(source, target: Path):
    """The branch the worktree registered at ``target`` stands on, or ``None``.

    ``None`` means git knows no worktree there, which is not the same as
    nothing being there: a directory git has never heard of is answered for
    by the caller, which refuses it rather than asking git to overwrite it.
    """

    for entry in workspace_git._worktrees(_git_out(source)):
        recorded = entry.get("worktree")
        if not recorded:
            continue
        try:
            same = Path(recorded).resolve() == target.resolve()
        except OSError:  # pragma: no cover - an unresolvable stale record
            continue
        if not same:
            continue
        head = entry.get("branch") or ""
        if head.startswith("refs/heads/"):
            return head[len("refs/heads/"):]
        return workspace_git.DETACHED_PREFIX + str(entry.get("HEAD") or "")
    return None


def _branch_tip(source, branch: str):
    """The revision a branch names in this repository, or ``None``."""

    code, out, _ = workspace_git._git(
        str(source), "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}^{{commit}}"
    )
    return out.strip() if code == 0 and out.strip() else None


def _add(source, argv) -> None:
    """One ``git worktree add``, refusing with git's own words."""

    code, _, err = workspace_git._git(str(source), "worktree", "add", "--quiet", *argv)
    if code != 0:
        raise Refused(f"git worktree add {' '.join(argv)}: {err.strip()}")


def _create(source, target: Path, branch: str, baseline: str, claimed: bool) -> None:
    """Put this item's own tree at its derived path, or refuse to.

    Three ways the path can already be taken, and only one of them is this
    item's. A directory git does not know is a foreign tree: creating over
    it would either fail obscurely or bury whatever is in it. A branch that
    already exists and that no record of this item claims belongs to
    something else at that name, and adopting it would grade a stranger's
    commits as this item's work. A branch this item's own ticket already
    records is its own earlier work -- its tree was retired, its commits
    were not -- so the tree is put back on it rather than cut again from a
    baseline that would orphan them.
    """

    if target.exists() and any(target.iterdir()):
        raise Refused(
            f"{target} is occupied by a tree this run did not derive: it is no "
            "worktree of this repository. Move or remove it, then establish again"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    tip = _branch_tip(source, branch)
    if tip is None:
        _add(source, ["-b", branch, str(target), baseline])
    elif claimed:
        _add(source, [str(target), branch])
    else:
        raise Refused(
            f"branch {branch!r} already stands at {tip} and no ticket records it: "
            f"the derived candidate cannot adopt it. Delete it with "
            f"'git -C {source} branch -D {branch}' if it is spent, then establish again"
        )


def _derived(run, ticket_id, path, data, prior_text, held, source, seams):
    """Create -- or replay -- the tree this item's identity derives."""

    candidate = state_root.candidate_paths(run, ticket_id)
    target, branch = candidate["path"], candidate["branch"]
    source = Path(source).expanduser()
    if not source.is_dir():
        raise Refused(f"--repo '{source}' is not a directory")
    read_source = _git_out(source)
    top = Path(read_source("rev-parse", "--show-toplevel")).resolve()
    _validate_write_paths(data.get("write_scope"), top)
    stamped = str(data.get(BASELINE_KEY) or "").strip()
    standing = _standing(source, target)
    if standing is None:
        _create(
            source, target, branch,
            workspace_git.revision_of(stamped) or read_source("rev-parse", "HEAD"),
            str(data.get(BRANCH_KEY) or "").strip() == branch,
        )
        replayed = False
    elif standing != branch:
        raise Refused(
            f"{target} is the workspace of branch {standing!r}, not this item's "
            f"{branch!r}: retire it with 'workspace.py retire {run} {ticket_id}' "
            "if it is spent, then establish again"
        )
    else:
        replayed = True
    observed_branch, head = workspace_git._head_and_branch(_git_out(target))
    dirty = sorted(set(workspace_git.dirty_paths(str(target))))
    # never restamped: the baseline names the revision this item was cut
    # from, and a re-establishment that rewrote it would move the revision
    # every later grade measures the item's own change against
    baseline = stamped or workspace_git._baseline(head, dirty)
    outcome = seams["record"](
        path, prior_text, observed_branch, baseline, str(target), run=run, lock_held=held
    )
    if "error" in outcome:
        raise Refused(outcome["error"])
    return {
        "run": run,
        "id": ticket_id,
        "ticket": str(path),
        BRANCH_KEY: observed_branch,
        BASELINE_KEY: baseline,
        PATH_KEY: str(target),
        "workspace_root": str(target),
        "main_root": str(state_root.find_repo_root(source) or top),
        # by derivation, not by survey: this path belongs to one ticket of
        # one run, so there is no sibling that could be standing in it
        "isolated": True,
        "shared_with": [],
        "dirty": dirty,
        "replayed": replayed,
    }, EXIT_OK


def _establishment(run, ticket_id, key, held, seams, source, where):
    path, data, prior_text = _loaded(run, ticket_id)
    adapter = _adapter(data)
    strategy = adapter.workspace_strategy
    if strategy == EVIDENCE_STRATEGY:
        return {key: _evidence(run, ticket_id, path, prior_text, adapter, held, seams)}, EXIT_OK
    if strategy != GIT_STRATEGY:
        raise Refused(
            f"adapter-not-establishable: {adapter.key} does not establish a "
            "candidate workspace"
        )
    isolation = tickets_store.normalized_isolation(data.get(ISOLATION_KEY))
    if source is None or isolation != REQUIRED:
        body, code = _observed(run, ticket_id, path, data, prior_text, held, seams, where)
        return {key: body}, code
    body, code = _derived(run, ticket_id, path, data, prior_text, held, source, seams)
    return {key: body}, code


def observe(run: str, ticket_id: str, *, held: bool, seams: dict):
    """``start``: record the workspace the caller is already standing in."""

    return _establishment(run, ticket_id, START_KEY, held, seams, None, None)


def establish(run: str, ticket_id: str, *, source, held: bool, seams: dict):
    """``establish``: give an isolation-required item the tree it derives."""

    return _establishment(run, ticket_id, ESTABLISH_KEY, held, seams, source, source)


def prepare(run: str, ticket_id: str):
    """Install what this item's recorded tree declares, holding no lock.

    Separated from ``establish`` because of what it costs: a cold
    ``pnpm install`` is minutes, and while it ran inside the dispatch
    facade's critical section every sibling of the run waited it out for a
    tree that was not theirs. Nothing here writes a ticket or a stamp, so
    there is no lock to take -- it reads the ``workspace_path`` the
    establishment already recorded and works in that directory.

    The preparation's verdict is reported, never raised: a tree that cannot
    be prepared is still a workspace whose branch and baseline the join has
    to be able to read. Only a workspace that was never recorded refuses,
    because there is then no directory to prepare and the caller has skipped
    a step rather than hit one that failed.
    """

    path, data, _ = _loaded(run, ticket_id)
    recorded = str(data.get(PATH_KEY) or "").strip()
    if not recorded:
        raise Refused(
            f"{run}/{ticket_id} records no {PATH_KEY}: establish it first with "
            f"'workspace.py establish {run} {ticket_id}'"
        )
    top = Path(recorded).expanduser()
    if not top.is_dir():
        raise Refused(
            f"recorded {PATH_KEY} {top} is not a directory: establish it again "
            f"with 'workspace.py establish {run} {ticket_id}'"
        )
    return {
        "prepare": {
            "run": run,
            "id": ticket_id,
            "ticket": str(path),
            PATH_KEY: str(top),
            **workspace_prepare.prepare(top),
        }
    }, EXIT_OK


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


__all__ = (
    "ESTABLISH_KEY", "START_KEY", "establish", "observe", "prepare", "retire",
)
