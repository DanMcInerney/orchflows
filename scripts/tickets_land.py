"""One caller-side landing operation over the public return steps.

`dispatch` completes the launch; this completes the return. What a caller
used to sequence by hand -- import the outcome, join it, remove the derived
worktree, then ask what became ready -- is one command here, and the three
state acts are one critical section rather than three, so no other writer
can move the run between them.

Every step is one of the public operations and every one of them replays,
so this composition replays too: a `land` that died between the join and the
retirement lands the same way when it is run again, and says which of its
steps it found already done. The established granular commands remain the
recovery seam; nothing here is a second protocol.

The frontier is read after the lock, not inside it. The dependents this
join just unblocked are exactly what `ready` promotes, and that promotion
takes the run lock for itself -- asking for it under our own would be a
caller waiting on itself.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

if __package__:
    from .tickets_format import (
        REQUIRED_ISOLATION, TERMINAL_STATES, _extract_flag, _parse_frontmatter,
        _read_utf8,
    )
    from .tickets_adapters import derived_isolation
    from .tickets_dispatch_schema import OUTCOME_RECORD_ID, stored_state
    from .tickets_join import _cmd_dispatch_join
    from .tickets_outcome import _cmd_dispatch_outcome
    from .tickets_lifecycle import _cmd_ready
    from .tickets_store import (
        NO_SINK_ERROR, _run_lock, _tickets_root,
        segment_refusal,
    )
else:  # pragma: no cover - direct/installed flat script path
    from tickets_format import (
        REQUIRED_ISOLATION, TERMINAL_STATES, _extract_flag, _parse_frontmatter,
        _read_utf8,
    )
    from tickets_adapters import derived_isolation
    from tickets_dispatch_schema import OUTCOME_RECORD_ID, stored_state
    from tickets_join import _cmd_dispatch_join
    from tickets_outcome import _cmd_dispatch_outcome
    from tickets_lifecycle import _cmd_ready
    from tickets_store import (
        NO_SINK_ERROR, _run_lock, _tickets_root,
        segment_refusal,
    )

LAND_USAGE = (
    "land <run> <id> --assignment-seal <seal> --dispatch-id <id> "
    "--outcome-record-id outcome --by <join-name> [--outcome-file <path|->] "
    "[--accepted-file <path|->] [--artifact <fixed-identity>]"
)
JOIN_RECORD_PREFIX = "join:"
COMMITTED = "committed"
REPLAYED = "replayed"
SKIPPED = "skipped"


def _prior_records(run: str, ticket_id: str, dispatch_id: str) -> dict:
    """Which of this dispatch's two return records the ticket already holds.

    Read for the report alone: each step below decides for itself whether it
    commits or replays, and this only lets the caller be told which happened
    without asking it to diff the ticket.
    """

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


def _derived_isolation(run: str, ticket_id: str) -> bool:
    """Whether this item was given a derived worktree to retire."""

    root = _tickets_root()
    if root is None:
        return False
    text, failure = _read_utf8(root / run / f"{ticket_id}.md")
    if failure is not None:
        return False
    data = _parse_frontmatter(text)
    return derived_isolation(data.get("isolation"), data.get("pack")) == REQUIRED_ISOLATION


def _retire_workspace(run: str, ticket_id: str, status: str) -> dict:
    """Remove the derived worktree, or say exactly why it was not removed.

    Only a terminal join retires. Suspension keeps its claimant observations
    for a handoff, and the tree holds the work that handoff resumes. Nothing
    here forces: `git worktree remove` refuses a tree with uncommitted bytes,
    and that refusal is reported rather than overridden, because the bytes it
    is protecting are the only copy of somebody's work.
    """

    if status not in TERMINAL_STATES:
        return {"step": "workspace-retire", "outcome": SKIPPED, "reason": status}
    if not _derived_isolation(run, ticket_id):
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


def _land_transaction(run, ticket_id, identity, outcome_file, accepted_file, artifact):
    """The two state acts, in order, under the caller's one run lock."""

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
    arguments = [
        run, ticket_id,
        "--assignment-seal", identity["assignment_seal"],
        "--dispatch-id", identity["dispatch_id"],
        "--outcome-record-id", identity["outcome_record_id"],
        "--by", identity["by"],
    ]
    if accepted_file is not None:
        arguments.extend(("--accepted-file", accepted_file))
    if artifact is not None:
        arguments.extend(("--artifact", artifact))
    joined = _cmd_dispatch_join(arguments, _lock_held=True)
    if "error" in joined:
        return joined
    steps.append({
        "step": "dispatch-join",
        "outcome": REPLAYED if prior["join"] else COMMITTED,
    })
    steps.append(_retire_workspace(run, ticket_id, joined["join"]["status"]))
    return {"land": {
        "run": run,
        "id": ticket_id,
        "status": joined["join"]["status"],
        "join": joined["join"],
        "steps": steps,
    }}


def _cmd_land(rest):
    """Import the outcome, join it, retire the tree, and report the frontier."""

    args = list(rest)
    identity = {
        "assignment_seal": _extract_flag(args, "--assignment-seal"),
        "dispatch_id": _extract_flag(args, "--dispatch-id"),
        "outcome_record_id": _extract_flag(args, "--outcome-record-id"),
        "by": _extract_flag(args, "--by"),
    }
    outcome_file = _extract_flag(args, "--outcome-file")
    accepted_file = _extract_flag(args, "--accepted-file")
    artifact = _extract_flag(args, "--artifact")
    if len(args) != 2 or not all(identity.values()):
        return {"error": f"usage: {LAND_USAGE}"}
    run, ticket_id = args
    invalid = segment_refusal(run, ticket_id)
    if invalid is not None:
        return invalid
    if _tickets_root() is None:
        return {"error": NO_SINK_ERROR}
    try:
        with _run_lock(run):
            landed = _land_transaction(
                run, ticket_id, identity, outcome_file, accepted_file, artifact,
            )
    except OSError as error:
        return {"error": f"unable to land {run}/{ticket_id}: {error}"}
    if "error" in landed:
        return landed
    # After the lock, and deliberately: this is the same promotion the caller
    # would run next, and the dependents it promotes are the ones this join
    # unblocked.
    landed["land"]["frontier"] = _cmd_ready(["--run", run])
    return landed


__all__ = ("LAND_USAGE", "_cmd_land")
