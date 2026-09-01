"""One caller-side dispatch operation over the public dispatch steps."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    from .tickets_assignment import (
        dispatch_assignment, workspace_establishment_finding,
    )
    from .tickets_attempts import (
        LAUNCH_RECORD_ID, _cmd_dispatch_open, _cmd_dispatch_retire,
        _classification, _commit_record,
    )
    from .tickets_commands import DISPATCH_USAGE
    from .tickets_dispatch_launch import launch_spec, precheck, selected_host
    from .tickets_dispatch_schema import stored_state
    from .tickets_format import (
        _extract_flag, _parse_frontmatter, _parse_iso, _read_utf8,
        parse_canonical_json,
    )
    from .tickets_generations import seal_findings
    from .tickets_lifecycle import _cmd_ready
    from .tickets_store import _run_lock, _segment_error, _tickets_root
else:
    from tickets_assignment import dispatch_assignment, workspace_establishment_finding
    from tickets_attempts import (
        LAUNCH_RECORD_ID, _cmd_dispatch_open, _cmd_dispatch_retire,
        _classification, _commit_record,
    )
    from tickets_commands import DISPATCH_USAGE
    from tickets_dispatch_launch import launch_spec, precheck, selected_host
    from tickets_dispatch_schema import stored_state
    from tickets_format import (
        _extract_flag, _parse_frontmatter, _parse_iso, _read_utf8,
        parse_canonical_json,
    )
    from tickets_generations import seal_findings
    from tickets_lifecycle import _cmd_ready
    from tickets_store import _run_lock, _segment_error, _tickets_root


def _workspace(source: Path, verb: str, arguments: list):
    """``(response, failure)`` from one ``workspace.py`` verb run in ``source``.

    Workspace work is intentionally kept behind its public script: it owns
    adapter selection, the derived candidate worktree, and the host checkout
    observation. Only the structured response is fed back, so a refusal
    cannot be repaired here or translated into a second protocol. One reader
    for both verbs, because every one of these failure shapes -- a launch
    that will not start, output that will not parse, an object that is not
    one, a non-zero status -- belongs to the protocol and not to the verb.
    """

    script = Path(__file__).with_name("workspace.py").resolve()
    try:
        completed = subprocess.run(
            [sys.executable, str(script), verb, *arguments],
            cwd=str(source), capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
    except (OSError, ValueError) as error:
        return None, {"error": f"workspace {verb} failed: {error}"}
    try:
        response = json.loads(completed.stdout)
    except (TypeError, ValueError) as error:
        return None, {"error": f"workspace {verb} returned invalid JSON: {error}"}
    if not isinstance(response, dict):
        return None, {"error": f"workspace {verb} returned a non-object response"}
    if "error" in response:
        return None, response
    if completed.returncode:
        return None, {
            "error": f"workspace {verb} refused",
            "code": completed.returncode,
            "response": response,
        }
    return response, None


def _workspace_prepare(run: str, ticket_id: str, workspace: str | None) -> dict:
    """Install what the established tree declares, reporting either answer.

    Called after the run lock is released, never inside it: a cold
    ``pnpm install`` is minutes, and inside the critical section every
    sibling of this run waited them out for a tree that was not theirs. Its
    verdict is reported rather than raised, exactly as the workspace owner
    reports it -- a tree that could not be prepared is still the workspace
    the launch names, and the child reads the answer and plans around it.
    """

    source = Path(workspace).expanduser().resolve() if workspace else Path.cwd()
    response, failure = _workspace(source, "prepare", [run, ticket_id])
    return failure if failure is not None else response.get("prepare", response)


def _workspace_establish(run: str, ticket_id: str, workspace: str | None):
    """Run the workspace owner and return its one JSON response.

    ``--workspace`` names the tree the candidate is cut from, never the
    candidate itself -- an isolation-required item's tree is derived from its
    identity by ``workspace.py``, which is what stops two siblings of one run
    from being dispatched into one directory.

    ``--lock-held`` (``workspace_git.LOCK_HELD``, pinned by a test) says this
    process already holds the run lock across the whole composition: the child
    stamps inside the caller's critical section rather than waiting for a lock
    its own parent holds while waiting for the child.
    """

    source = Path(workspace).expanduser().resolve() if workspace else Path.cwd()
    response, failure = _workspace(source, "establish", [
        run, ticket_id, "--repo", str(source), "--lock-held",
    ])
    if failure is not None:
        return failure
    established = response.get("establish")
    if not isinstance(established, dict) or not str(
        established.get("workspace_path") or ""
    ).strip():
        return {"error": "workspace establish did not record workspace_path"}
    return response


def _cmd_dispatch(rest):
    """Compose ready, workspace, attempt, launch, and preparation.

    The established public operations remain the recovery seam. This
    caller convenience operation composes them in order, relays every
    structured refusal unchanged, and retires a newly opened attempt if the
    launch refuses so no live attempt is left behind.

    The launch binding is resolved twice on purpose: once before anything is
    opened, so a host or role that cannot be launched refuses while the
    ticket is still untouched, and once from the graded assignment, which is
    the authority on what is actually being launched. Both ask the one
    resolver, under this one lock, so they cannot disagree.

    Only the steps that decide the dispatch run under that lock. Tree
    preparation decides nothing and costs the most, so it follows the lock
    rather than sitting inside it.
    """

    args = list(rest)
    owner = _extract_flag(args, "--by")
    dispatch_id = _extract_flag(args, "--dispatch-id")
    lease = _extract_flag(args, "--lease-expires-at")
    workspace = _extract_flag(args, "--workspace")
    host = selected_host(_extract_flag(args, "--host"))
    if len(args) != 2 or not all((owner, dispatch_id, lease)):
        return {"error": f"usage: {DISPATCH_USAGE}"}
    run, ticket_id = args
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid

    # Before the lock, and it has to be: promotion takes the run lock for
    # itself for each ticket it admits, and `_run_lock` is not reentrant, so
    # readying a sealed-but-pending item from inside our own lock is this
    # process waiting on itself -- which is what the ordinary first dispatch
    # of a sealed root did. Nothing is lost by promoting first: it is a
    # whole-run convenience, not part of this ticket's transaction, and
    # `dispatch-open` re-grades admission under the lock below and refuses a
    # ticket that is not ready however it got there.
    ready = _cmd_ready(["--run", run])
    if "error" in ready:
        return ready

    with _run_lock(run):
        dispatched = _dispatched_under_run_lock(
            run, ticket_id, host=host, owner=owner, dispatch_id=dispatch_id,
            lease=lease, workspace=workspace,
        )
    if "error" in dispatched:
        return dispatched
    # Outside the lock, and last: preparing the tree is a package manager's
    # minutes against a directory that already exists and belongs to this one
    # item, and every second of it spent inside the critical section was a
    # second every sibling of this run waited for a tree that was not theirs.
    # Its verdict rides along; it never decides the dispatch.
    return {**dispatched, "prepare": _workspace_prepare(run, ticket_id, workspace)}


def _dispatched_under_run_lock(run, ticket_id, *, host, owner, dispatch_id,
                               lease, workspace):
    """Everything the run lock has to hold, and nothing that does not."""

    # Before the first side effect: an attempt opened for a launch that
    # cannot resolve is an attempt nobody can start. Then open before
    # workspace establishment, because workspace.start stamps the ticket
    # and doing it first would mutate bytes on a pre-open refusal.
    record, failure = precheck(run, ticket_id, host)
    if failure is not None:
        return failure

    opening = _cmd_dispatch_open([
        run, ticket_id, "--by", owner, "--dispatch-id", dispatch_id,
        "--lease-expires-at", lease,
    ], _lock_held=True)
    if "error" in opening:
        return opening
    dispatch = opening.get("dispatch")
    if not isinstance(dispatch, dict):
        return {"error": "dispatch-open returned no dispatch response"}
    newly_opened = dispatch.get("outcome") == "opened"

    established = _workspace_establish(run, ticket_id, workspace)
    if "error" in established:
        launched = established
    else:
        # only establishment's own answer reaches the launch: the caller's
        # ``--workspace`` named the tree to cut from, and a launch built
        # from that instead has named another item's workspace
        candidate = established.get("establish")
        workspace_path = (
            candidate.get("workspace_path") if isinstance(candidate, dict) else None
        )
        if not str(workspace_path or "").strip():
            launched = {"error": "workspace establish did not record workspace_path"}
        else:
            launched = _launched_under_run_lock(
                run, ticket_id, record, dispatch_id=dispatch_id,
                workspace=workspace_path,
            )
    if "error" not in launched:
        return launched
    if newly_opened:
        retirement = _cmd_dispatch_retire([
            run, ticket_id, "--assignment-seal", dispatch["assignment_seal"],
            "--dispatch-id", dispatch_id,
            "--record-id", f"lifecycle:dispatch-facade-{dispatch_id}",
        ], _lock_held=True)
        if not isinstance(retirement, dict) or "error" in retirement:
            return {
                "error": "dispatch attempt retirement failed after launch refusal",
                "code": "dispatch-retirement-failed",
                "launch": launched,
                "retirement": retirement,
            }
    return launched


def _attempt(data: dict, dispatch_id: str, *, stored_only: bool = False):
    if __package__:
        from .tickets_dispatch_schema import state as _state
    else:
        from tickets_dispatch_schema import state as _state
    state, failure = (stored_state(data) if stored_only else _state(data))
    if failure is not None:
        return None, failure
    if state is None:
        status = str(data.get("status") or "")
        if status in ("claimed", "suspended"):
            return None, _classification(
                "legacy-live-claim", "pre-v1 live claim has no dispatch record",
            )
        return None, _classification(
            "dispatch-mismatch", "ticket has no dispatch-v1 attempt",
        )
    found = next(
        (item for item in state["attempts"] if item.get("dispatch_id") == dispatch_id),
        None,
    )
    if found is None:
        return None, _classification(
            "dispatch-mismatch",
            f"dispatch_id '{dispatch_id}' was never opened for this ticket",
        )
    return found, None


def _live_attempt(attempt: dict):
    lease = _parse_iso(attempt.get("lease_expires_at"))
    if (
        attempt.get("state") != "live"
        or lease is None
        or datetime.now(timezone.utc) >= lease
    ):
        return _classification(
            "stale-attempt", "launch belongs to an ended dispatch attempt",
        )
    return None


def _committed_launch(attempt: dict):
    """The launch this attempt was already started with, or None.

    The record is the authority on what the child was handed, so a replay
    returns those bytes rather than composing them again: the prompt names
    absolute paths and this interpreter, and a second composition from a
    moved checkout would report a launch that never happened.
    """

    record = next(
        (
            item for item in attempt.get("records") or []
            if item.get("record_id") == LAUNCH_RECORD_ID
        ),
        None,
    )
    if record is None:
        return None
    try:
        content = parse_canonical_json(record["content"])
    except (KeyError, TypeError, ValueError):
        content = None
    launch = content.get("launch") if isinstance(content, dict) else None
    if not isinstance(launch, dict):
        return _classification(
            "dispatch-record-invalid",
            "committed launch record has no canonical content",
        )
    return content


def _launched_under_run_lock(run, ticket_id, host_record, *, dispatch_id,
                             workspace):
    """Grade the assignment, resolve the launch, and commit it, once.

    Every read decides what the commit writes -- stored attempt, replay
    comparison, review state, seal -- so the caller's lock covers the reads
    too, and `_commit_record` is told the lock is held rather than opening a
    second one on the same run.
    """

    root = _tickets_root()
    if root is None:
        return _classification("state-inaccessible", "state sink is not configured")
    path = root / run / f"{ticket_id}.md"
    text, failure = _read_utf8(path)
    if failure is not None:
        return _classification("state-inaccessible", failure["error"])
    data = _parse_frontmatter(text)
    attempt, failure = _attempt(data, dispatch_id, stored_only=True)
    if failure is not None:
        return failure
    replay = _committed_launch(attempt)
    if replay is not None:
        return replay
    attempt, failure = _attempt(data, dispatch_id)
    if failure is not None:
        return failure
    finding = workspace_establishment_finding(data, workspace)
    if finding is not None:
        return _classification(*finding)
    failure = _live_attempt(attempt)
    if failure is not None:
        return failure
    seal = str(data.get("assignment_seal") or "")
    if seal != attempt.get("assignment_seal") or seal_findings(ticket_id, text):
        # The same fact `_commit_record` fences every write on, refused here
        # before the launch is composed rather than after: one code for one
        # fact, and it is the one the commit below would raise anyway.
        return _classification(
            "assignment-mismatch",
            "ticket no longer matches the attempt's sealed assignment",
        )
    arguments = [run, ticket_id, "--by", attempt["owner"], "--workspace", workspace]
    graded = dispatch_assignment(arguments, attempt=attempt)
    if "error" in graded:
        return graded
    launch, failure = launch_spec(host_record, graded["assignment"])
    if failure is not None:
        return failure
    content = {"launch": launch}
    committed = _commit_record(
        run, ticket_id, dispatch_id, LAUNCH_RECORD_ID, content,
        record_kind="launch", _lock_held=True,
    )
    if "error" in committed:
        return committed
    return content


__all__ = (
    "_cmd_dispatch", "_dispatched_under_run_lock", "_launched_under_run_lock",
    "_workspace_establish", "_workspace_prepare",
)
