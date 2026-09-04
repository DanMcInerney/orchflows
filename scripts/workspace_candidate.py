"""Establish and replay one work item's candidate workspace.

``workspace.py`` is the CLI facade; this module owns what a candidate
workspace *is* for one work item -- the tree it gets, the branch that tree
stands on, and the observation its ticket is stamped from. What becomes of
that tree afterwards is ``workspace_return``'s. It imports the owning
modules directly, never that facade and never ``tickets``.

Two lanes, and the ticket's own ``isolation`` decides which. An item
declaring ``required`` gets a tree of its own at the path
``state_root.candidate_paths`` derives from its run and id -- never a tree a
caller named, because a caller naming the tree is how two siblings come to
be dispatched into one directory. Everything else is observed rather than
created.

Creation happens before the run lock is taken and never inside it: the
derived path belongs to exactly one ticket of one run, so no other writer
can be racing for it. The stamp that follows is the locked half, written
against the ticket's bytes as they were read.

Nothing here records a success it did not achieve. A refused establishment
leaves the ticket as it was found and never falls back to the shared tree
the item was dispatched from.
"""

from __future__ import annotations

from pathlib import Path

try:
    from . import state_root, tickets_adapters, tickets_format, tickets_pins
    from . import tickets_store
    from . import workspace_git, workspace_prepare, workspace_record
    from .tickets_registry import EXECUTOR_REGISTRY
except ImportError:  # a flat ``bin`` layout, where these are top-level modules
    import state_root
    import tickets_adapters
    import tickets_format
    import tickets_pins
    import tickets_store
    import workspace_git
    import workspace_prepare
    import workspace_record
    from tickets_registry import EXECUTOR_REGISTRY

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
    """The ticket, its data, and the bytes every stamp below derives from."""

    path = state_root.tickets_root() / run / f"{ticket_id}.md"
    if not path.is_file():
        raise Refused(f"ticket not found: {run}/{ticket_id}")
    data = workspace_git._graded(
        tickets_store._load_ticket(path), f"read {run}/{ticket_id}"
    )
    return path, data, path.read_text(encoding="utf-8")


def _adapter(data: dict):
    try:
        return tickets_adapters.adapter_spec(tickets_pins.adapter_standard(data))
    except tickets_adapters.AdapterError as error:
        raise Refused(f"{error.code}: {error.detail}") from error


def _unisolated(run, ticket_id, path, prior_text, adapter, held, seams, where) -> dict:
    """Record the workspace of a lane that gives no item a tree of its own."""

    if adapter.workspace_strategy == EVIDENCE_STRATEGY:
        root = (state_root.state_root() / "research" / run).resolve()
        root.mkdir(parents=True, exist_ok=True)
    else:
        root = Path(where or Path.cwd()).expanduser().resolve()
    outcome = seams["record"](
        path, prior_text, None, None, str(root), run=run, lock_held=held
    )
    if "error" in outcome:
        raise Refused(outcome["error"])
    return {
        "run": run, "id": ticket_id, "ticket": str(path), "mechanism": adapter.key,
        PATH_KEY: str(root), "workspace_root": str(root), "isolated": False,
    }


def _observed(run, ticket_id, path, data, prior_text, held, seams, where):
    """Record the Git tree the caller is standing in, and grade its sharing."""

    git_out = seams["git_out"]
    root, located = workspace_git._locate(run, ticket_id, where)
    if located != path:
        raise Refused(f"ticket identity changed while locating {run}/{ticket_id}")
    top = Path(git_out("rev-parse", "--show-toplevel")).resolve()
    _validate_write_paths(data.get("write_scope"), top)
    branch, head = workspace_git._head_and_branch(git_out)
    dirty = sorted(set(seams["dirty_paths"]()))
    # Write-once: ``tickets_assignment.py`` feeds this stamp to ``cutcheck.py
    # --baseline``, so it goes on naming the revision the item was cut from,
    # never the moved tree a re-establishment stands in. The observation is
    # reported under its own key instead of recorded. Computed either way,
    # because it also refuses a dirty path no comma-joined frontmatter
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
    """The branch the worktree registered at ``target`` stands on, or ``None``."""

    for entry in workspace_git._worktrees(workspace_git._git_out(source)):
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


def _add(source, argv) -> None:
    """One ``git worktree add``, refusing with git's own words."""

    code, _, err = workspace_git._git(str(source), "worktree", "add", "--quiet", *argv)
    if code != 0:
        raise Refused(f"git worktree add {' '.join(argv)}: {err.strip()}")


def _create(source, target: Path, branch: str, baseline: str, claimed: bool) -> None:
    """Put this item's own tree at its derived path, or refuse to."""

    if target.exists() and any(target.iterdir()):
        raise Refused(
            f"{target} is occupied by a tree this run did not derive: it is no "
            "worktree of this repository. Move or remove it, then establish again"
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    tip = workspace_git._branch_tip(source, branch)
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


def _fixes_integration_target(data: dict, named: bool) -> bool:
    """Whether this establishment may fix where the run's work is integrated."""

    if not named:
        return False
    return not EXECUTOR_REGISTRY.get(
        tickets_format._executor_of(data), {}
    ).get("files_findings")


def _derived(run, ticket_id, path, data, prior_text, held, source, seams, named):
    """Create -- or replay -- the tree this item's identity derives."""

    candidate = state_root.candidate_paths(run, ticket_id)
    target, branch = candidate["path"], candidate["branch"]
    source = Path(source).expanduser()
    if not source.is_dir():
        raise Refused(f"--repo '{source}' is not a directory")
    read_source = workspace_git._git_out(source)
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
    observed_branch, head = workspace_git._head_and_branch(workspace_git._git_out(target))
    dirty = sorted(set(workspace_git.dirty_paths(str(target))))
    # never restamped: the baseline names the revision this item was cut
    # from, and rewriting it would move the revision every later grade
    # measures the item's own change against
    baseline = stamped or workspace_git._baseline(head, dirty)
    outcome = seams["record"](
        path, prior_text, observed_branch, baseline, str(target), run=run, lock_held=held
    )
    if "error" in outcome:
        raise Refused(outcome["error"])
    integration = (
        tickets_store.record_integration_target(
            run, str(top), workspace_git._current_branch(read_source),
        )
        if _fixes_integration_target(data, named)
        else tickets_store.integration_target(run)
    )
    return {
        "run": run,
        "id": ticket_id,
        "ticket": str(path),
        BRANCH_KEY: observed_branch,
        BASELINE_KEY: baseline,
        PATH_KEY: str(target),
        "workspace_root": str(target),
        "main_root": str(state_root.find_repo_root(source) or top),
        # what `land` will merge into: this run's, recorded once, reported
        # here so a driver can see it before any item has been landed
        tickets_store.INTEGRATION_KEY: integration,
        # by derivation, not by survey: this path belongs to one ticket of
        # one run, so there is no sibling that could be standing in it
        "isolated": True,
        "shared_with": [],
        "dirty": dirty,
        "replayed": replayed,
    }, EXIT_OK


def _establishment(run, ticket_id, key, held, seams, source, where, named=False):
    path, data, prior_text = _loaded(run, ticket_id)
    adapter = _adapter(data)
    # The item's isolation before the adapter's strategy, never after. The
    # other way round refuses a document lane over a tree of its own, which
    # only an explicit override ever asks for.
    isolation = tickets_adapters.derived_isolation(
        data.get(ISOLATION_KEY), tickets_pins.adapter_standard(data),
    )
    if isolation == REQUIRED and not adapter.establishes_isolation:
        raise Refused(f"adapter-not-establishable: {adapter.key} does not "
                      "establish a candidate workspace")
    if adapter.workspace_strategy != GIT_STRATEGY:
        return {key: _unisolated(run, ticket_id, path, prior_text, adapter, held, seams, where)}, EXIT_OK
    if source is None or isolation != REQUIRED:
        body, code = _observed(run, ticket_id, path, data, prior_text, held, seams, where)
        return {key: body}, code
    body, code = _derived(
        run, ticket_id, path, data, prior_text, held, source, seams, named,
    )
    return {key: body}, code


def observe(run: str, ticket_id: str, *, held: bool, seams: dict):
    """``start``: record the workspace the caller is already standing in."""

    return _establishment(run, ticket_id, START_KEY, held, seams, None, None)


def establish(run: str, ticket_id: str, *, source, held: bool, seams: dict,
              named: bool = False):
    """``establish``: give an isolation-required item the tree it derives."""

    return _establishment(
        run, ticket_id, ESTABLISH_KEY, held, seams, source, source, named,
    )


def prepare(run: str, ticket_id: str):
    """Install what this item's recorded tree declares, holding no lock."""

    path, data, _ = _loaded(run, ticket_id)
    recorded = str(workspace_record.attempt_workspace(data) or "").strip()
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


__all__ = ("ESTABLISH_KEY", "START_KEY", "establish", "observe", "prepare")
