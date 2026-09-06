"""One caller-side landing operation over the public return steps.

`dispatch` completes the launch; this completes the return. Importing the
outcome, merging the candidate, joining it, removing the derived worktree
and asking what became ready are one command here, and the state acts are
one critical section, so no other writer can move the run between them.

Order, and the reason for it: the outcome import closes the attempt; the
candidate is merged into the tree the run's checkout stands on, because the
question the predicate answers is what the repository does with those
commits in it; the ticket's `done` predicate is evaluated there, and it is
the one outside execution; only then does the join record what the item
became. `land` records a checked condition, or the driver's grade for a
ticket that declares none.

Every step is one of the public operations and every one of them replays,
so this composition replays too, and says which of its steps it found
already done. The granular commands remain the recovery seam.

The frontier is read after the lock, not inside it: the dependents this join
just unblocked are what `ready` promotes, and that promotion takes the run
lock for itself.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

if __package__:
    from . import tickets_done, tickets_report_note
    from .tickets_format import (
        REQUIRED_ISOLATION, RESULT_BEARING_STATES, TERMINAL_STATES,
        _extract_flag, _parse_frontmatter, _parse_iso, _read_utf8,
    )
    from .tickets_adapters import AdapterError, adapter_for_ticket, derived_isolation
    from .tickets_dispatch_schema import JOIN_RECORD_PREFIX, OUTCOME_RECORD_ID, stored_state
    from .tickets_join import _cmd_dispatch_join, dispatch_join_identity_defects
    from .tickets_outcome import _cmd_dispatch_outcome
    from .tickets_lifecycle import _cmd_ready
    from .tickets_result import _append_event
    from .tickets_store import (
        NO_SINK_ERROR, _run_lock, _tickets_root,
        segment_refusal,
    )
    from .workspace_git import BASELINE_KEY, BRANCH_KEY
else:  # pragma: no cover - direct/installed flat script path
    import tickets_done
    import tickets_report_note
    from tickets_format import (
        REQUIRED_ISOLATION, RESULT_BEARING_STATES, TERMINAL_STATES,
        _extract_flag, _parse_frontmatter, _parse_iso, _read_utf8,
    )
    from tickets_adapters import AdapterError, adapter_for_ticket, derived_isolation
    from tickets_dispatch_schema import JOIN_RECORD_PREFIX, OUTCOME_RECORD_ID, stored_state
    from tickets_join import _cmd_dispatch_join, dispatch_join_identity_defects
    from tickets_outcome import _cmd_dispatch_outcome
    from tickets_lifecycle import _cmd_ready
    from tickets_result import _append_event
    from tickets_store import (
        NO_SINK_ERROR, _run_lock, _tickets_root,
        segment_refusal,
    )
    from workspace_git import BASELINE_KEY, BRANCH_KEY

LAND_USAGE = (
    "land <run> <id> --assignment-seal <seal> --dispatch-id <id> "
    "--outcome-record-id outcome --by <join-name> [--status <disposition>] "
    "[--outcome-file <path|->]"
)
COMMITTED = "committed"
REPLAYED = "replayed"
SKIPPED = "skipped"
# The dispositions whose evidence is worth merging. A ticket that delivered
# nothing has nothing for the integrated tree to carry, and merging its
# branch anyway is how a refused item's half-work reaches a checkout the
# next reader trusts.
INTEGRABLE = frozenset(RESULT_BEARING_STATES)


def _prior_records(run: str, ticket_id: str, dispatch_id: str) -> dict:
    """Which of this dispatch's two return records the ticket already holds."""

    absent = {"outcome": False, "join": False}
    root = _tickets_root()
    if root is None:
        return absent
    text, failure = _read_utf8(root / run / f"{ticket_id}.md")
    if failure is not None:
        return absent
    state, failure = stored_state(_parse_frontmatter(text))
    if failure is not None or state is None:
        return absent
    attempt = next(
        (item for item in state["attempts"] if item.get("dispatch_id") == dispatch_id),
        None,
    )
    if attempt is None:
        return absent
    identities = {str(record.get("record_id")) for record in attempt.get("records") or []}
    return {
        "outcome": OUTCOME_RECORD_ID in identities,
        "join": any(name.startswith(JOIN_RECORD_PREFIX) for name in identities),
    }


def _dispatch_cost(data: dict):
    """`(attempts, elapsed_s)` off the ticket's own dispatch record, best-effort."""
    state, failure = stored_state(data)
    if failure is not None or state is None:
        return None, None
    attempts = state.get("attempts") or []
    if not attempts:
        return None, None
    opened = [value for value in (
        _parse_iso(item.get("opened_at")) for item in attempts
    ) if value is not None]
    if not opened:
        return len(attempts), None
    elapsed = (datetime.now(timezone.utc) - min(opened)).total_seconds()
    return len(attempts), max(elapsed, 0.0)


def _ticket(run: str, ticket_id: str):
    """`(path, data)` for the ticket being landed, or `(None, {})`."""

    root = _tickets_root()
    if root is None:
        return None, {}
    path = root / run / f"{ticket_id}.md"
    text, failure = _read_utf8(path)
    if failure is not None:
        return None, {}
    return path, _parse_frontmatter(text)


def _derived_isolation(data: dict) -> bool:
    """Whether this item was given a derived worktree to integrate and retire."""

    adapter = adapter_for_ticket(data, target=_recorded_workspace(data))
    return derived_isolation(data.get("isolation"), adapter.key) == REQUIRED_ISOLATION


def _candidate(run: str, ticket_id: str):
    """`workspace_return`, imported at call time."""

    if __package__:
        from . import workspace_return
    else:  # pragma: no cover - the flat installed layout
        import workspace_return
    return workspace_return


def _recorded_workspace(data: dict):
    """The tree the establishment recorded on this attempt, or ``None``."""

    if __package__:
        from . import workspace_record
    else:  # pragma: no cover - the flat installed layout
        import workspace_record
    return workspace_record.attempt_workspace(data)


def _integrate_workspace(run: str, ticket_id: str, data: dict, status, path, by):
    """Merge the candidate into the tree the run stands on, or say why not."""

    if status is not None and status not in INTEGRABLE:
        return {"step": "workspace-integrate", "outcome": SKIPPED, "reason": status}
    try:
        isolated = _derived_isolation(data)
    except AdapterError as error:
        return {"step": "workspace-integrate", "outcome": "refused",
                "code": error.code, "error": error.detail}
    if not isolated:
        return {"step": "workspace-integrate", "outcome": SKIPPED, "reason": "not isolated"}
    try:
        candidate = _candidate(run, ticket_id)
        response, _code = candidate.integrate(
            run, ticket_id, _recorded_workspace(data), data.get(BRANCH_KEY),
            data.get(BASELINE_KEY),
        )
    except Exception as error:  # `Refused`, and anything git surprised us with
        _note_conflict(path, by, data, error)
        return {"step": "workspace-integrate", "outcome": "refused", "error": str(error)}
    body = response.get("integrate") if isinstance(response, dict) else None
    if not isinstance(body, dict):
        return {"step": "workspace-integrate", "outcome": "refused", "response": response}
    _note_resolution(path, by, body)
    return {"step": "workspace-integrate", "outcome": body["outcome"], "response": body}


def _note_conflict(path, by: str, data: dict, error) -> None:
    """File the conflicted paths, for the refusal that carried them."""

    detail = getattr(error, "detail", None) or {}
    conflicted = detail.get("conflicted") or []
    if not conflicted:
        return
    tickets_report_note.file_once(path, by, tickets_report_note.conflict_note(
        data.get(BRANCH_KEY), detail.get("into"), detail.get("root"), conflicted,
    ), "integration evidence")


def _note_resolution(path, by: str, body: dict) -> None:
    """File the identity a resolved candidate landed under, where one is owed."""

    if body.get("outcome") not in ("merged", "replayed"):
        return
    if not tickets_report_note.carries(path, tickets_report_note.CONFLICT_PREFIX):
        return
    tickets_report_note.file_once(path, by, tickets_report_note.resolution_note(
        body.get(BRANCH_KEY), body.get("into"), body.get("tip"),
        body.get("revision"),
    ), "integration evidence")


def _retire_workspace(run: str, ticket_id: str, status: str, data: dict) -> dict:
    """Remove the derived worktree, or say exactly why it was not removed."""

    if status not in TERMINAL_STATES:
        return {"step": "workspace-retire", "outcome": SKIPPED, "reason": status}
    try:
        isolated = _derived_isolation(data)
    except AdapterError as error:
        return {"step": "workspace-retire", "outcome": "refused",
                "code": error.code, "error": error.detail}
    if not isolated:
        return {"step": "workspace-retire", "outcome": SKIPPED, "reason": "not isolated"}
    script = Path(__file__).with_name("workspace.py").resolve()
    try:
        completed = subprocess.run(
            [sys.executable, str(script), "retire", run, ticket_id],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
    except (OSError, ValueError) as error:
        return {"step": "workspace-retire", "outcome": "refused",
                "error": f"workspace retire failed: {error}"}
    try:
        response = json.loads(completed.stdout)
    except (TypeError, ValueError) as error:
        return {"step": "workspace-retire", "outcome": "refused",
                "error": f"workspace retire returned invalid JSON: {error}"}
    if not isinstance(response, dict) or "error" in response or completed.returncode:
        return {"step": "workspace-retire", "outcome": "refused", "response": response}
    return {"step": "workspace-retire", "outcome": "removed", "response": response}


def _done_outcome(decision: dict) -> str:
    """What the predicate step did, in the one word the step report carries."""

    if decision.get("form") is None:
        return "graded"
    return decision.get("action") or "checked"


def _land_transaction(run, ticket_id, identity, outcome_file, driver_status):
    """The state acts, in order, under the caller's one run lock."""

    prior = _prior_records(run, ticket_id, identity["dispatch_id"])
    steps = []
    if outcome_file is None:
        steps.append({"step": "dispatch-outcome", "outcome": SKIPPED})
    else:
        imported = _cmd_dispatch_outcome(
            [run, ticket_id, "--file", outcome_file], _lock_held=True,
        )
        if "error" in imported:
            return imported
        steps.append({
            "step": "dispatch-outcome",
            "outcome": REPLAYED if prior["outcome"] else COMMITTED,
        })
    path, data = _ticket(run, ticket_id)
    if path is None:
        return {"error": f"unreadable ticket for landing: {run}/{ticket_id}"}
    # Before the merge, not after it. This refusal reads the ticket's own
    # frontmatter and needs no integrated tree, and asking it second is how
    # one `land` merged a candidate into the run's checkout and then refused
    # the very call that had merged it.
    refusal = tickets_done.ungraded(run, ticket_id, data, driver_status)
    if refusal is not None:
        return refusal
    integrated = _integrate_workspace(
        run, ticket_id, data, driver_status, path, identity["by"],
    )
    steps.append(integrated)
    # An `absent` that names where it looked is a landing that would merge
    # nothing at exit 0 while the run reads as landed: the candidate was cut
    # from one repository and this run integrates into another. A bare
    # `absent` -- no candidate tree to resolve at all -- is the replay of an
    # item whose worktree a previous landing already retired, and it goes on.
    absent = (
        (integrated.get("response") or {}).get("detail")
        if integrated["outcome"] == "absent" else None
    )
    if integrated["outcome"] == "refused" or absent:
        return {"error": (
            absent or integrated.get("error") or "candidate integration refused"
        ), "steps": steps}
    tree = (integrated.get("response") or {}).get("main_root")
    decision, refusal = tickets_done.resolve(
        run, ticket_id, path.parent, path, data, tree, driver_status,
        identity["by"],
    )
    if refusal is not None:
        return refusal
    # `action == "close"` is the one shape `tickets_done.resolve` returns
    # only through `advance_action`'s two-identical-repair-rounds close: the
    # other route to `status == "stalled"` decides through a `decision` with
    # no `action` key at all.
    if decision.get("status") == "stalled" and decision.get("action") == "close":
        _append_event(run, ticket_id, "stalled", {})
    steps.append({"step": "done", "outcome": _done_outcome(decision), **{
        key: value for key, value in decision.items()
        if key not in ("reading", "action")
    }})
    attempts, elapsed_s = _dispatch_cost(data)
    done_exit = (decision.get("reading") or {}).get("exit")
    if decision["status"] is None:
        # Nothing to join: a minted check is still out, or a repair round was
        # just armed. The attempt stays open, and landing again once that
        # round is in re-runs the predicate against the further-integrated
        # tree.
        _append_event(run, ticket_id, "land", {
            "status": None, "done_exit": done_exit,
            "attempts": attempts, "elapsed_s": elapsed_s,
        })
        return {"land": {
            "run": run, "id": ticket_id, "status": None,
            "done": decision.get("reading"), "steps": steps,
        }}
    arguments = [
        run, ticket_id,
        "--assignment-seal", identity["assignment_seal"],
        "--dispatch-id", identity["dispatch_id"],
        "--outcome-record-id", identity["outcome_record_id"],
        "--by", identity["by"],
        "--status", decision["status"],
    ]
    joined = _cmd_dispatch_join(arguments, _lock_held=True)
    if "error" in joined:
        return joined
    steps.append({
        "step": "dispatch-join",
        "outcome": REPLAYED if prior["join"] else COMMITTED,
    })
    steps.append(_retire_workspace(run, ticket_id, joined["join"]["status"], data))
    _append_event(run, ticket_id, "land", {
        "status": joined["join"]["status"], "done_exit": done_exit,
        "attempts": attempts, "elapsed_s": elapsed_s,
    })
    return {"land": {
        "run": run,
        "id": ticket_id,
        "status": joined["join"]["status"],
        "done": decision.get("reading"),
        "join": joined["join"],
        "steps": steps,
    }}


def _cmd_land(rest):
    """Import the outcome, integrate, check done, join, retire, report."""

    args = list(rest)
    identity = {
        "assignment_seal": _extract_flag(args, "--assignment-seal"),
        "dispatch_id": _extract_flag(args, "--dispatch-id"),
        "outcome_record_id": _extract_flag(args, "--outcome-record-id"),
        "by": _extract_flag(args, "--by"),
    }
    outcome_file = _extract_flag(args, "--outcome-file")
    driver_status = _extract_flag(args, "--status")
    if len(args) != 2 or not all(identity.values()):
        return {"error": f"usage: {LAND_USAGE}"}
    run, ticket_id = args
    invalid = segment_refusal(run, ticket_id)
    if invalid is not None:
        return invalid
    # The same argument-shape refusals `dispatch-join` itself raises, checked
    # here before anything is merged: the join runs last, after
    # `workspace-integrate`, and a malformed identity refusing only there is
    # a refusal that already mutated the tree.
    invalid = dispatch_join_identity_defects(
        identity["outcome_record_id"], identity["dispatch_id"], identity["by"],
    )
    if invalid is not None:
        return invalid
    if _tickets_root() is None:
        return {"error": NO_SINK_ERROR}
    try:
        with _run_lock(run):
            landed = _land_transaction(
                run, ticket_id, identity, outcome_file, driver_status,
            )
    except OSError as error:
        return {"error": f"unable to land {run}/{ticket_id}: {error}"}
    if "error" in landed:
        return landed
    # After the lock: this is the same promotion the caller would run next,
    # and the dependents it promotes are the ones this join unblocked.
    landed["land"]["frontier"] = _cmd_ready(["--run", run])
    return landed


__all__ = ("LAND_USAGE", "_cmd_land")
