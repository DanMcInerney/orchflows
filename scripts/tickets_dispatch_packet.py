"""Committed packet projection for dispatch v1."""

from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timezone

if __package__:
    from .tickets_attempts import (
        OUTCOME_RECORD_ID, PACKET_RECORD_ID, PROTOCOL,
        _classification, _commit_record, _state,
    )
    from .tickets_format import (
        _extract_flag, _parse_frontmatter, _parse_iso, _read_utf8,
        parse_canonical_json,
    )
    from .tickets_generations import seal_findings
    from .tickets_packet import _packet_under_run_lock, workspace_establishment_finding
    from .tickets_dispatch_launch import resolved_role_profile
    from .tickets_dispatch_schema import stored_state
    from .tickets_review import packet_mutation, packet_state_result
    from .tickets_store import _run_lock, _tickets_root, segment_refusal
else:
    from tickets_attempts import (
        OUTCOME_RECORD_ID, PACKET_RECORD_ID, PROTOCOL,
        _classification, _commit_record, _state,
    )
    from tickets_format import (
        _extract_flag, _parse_frontmatter, _parse_iso, _read_utf8,
        parse_canonical_json,
    )
    from tickets_generations import seal_findings
    from tickets_packet import _packet_under_run_lock, workspace_establishment_finding
    from tickets_dispatch_launch import resolved_role_profile
    from tickets_dispatch_schema import stored_state
    from tickets_review import packet_mutation, packet_state_result
    from tickets_store import _run_lock, _tickets_root, segment_refusal

DISPATCH_PACKET_USAGE = (
    "dispatch-packet <run> <id> --dispatch-id <id> "
    "[--workspace <path>] [--artifact <fixed-identity>]"
    " [--review-kind critique|repair|verify]"
)


def _attempt(data: dict, dispatch_id: str, *, stored_only: bool = False):
    state, failure = (stored_state(data) if stored_only else _state(data))
    if failure is not None:
        return None, failure
    if state is None:
        status = str(data.get("status") or "")
        if status in ("claimed", "suspended"):
            return None, _classification(
                "legacy-live-claim",
                "pre-v1 live claim has no dispatch record",
            )
        return None, _classification(
            "dispatch-mismatch", "ticket has no dispatch-v1 attempt"
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
            "stale-attempt", "packet belongs to an ended dispatch attempt"
        )
    return None


def _projection_packet(legacy: dict, data: dict, attempt: dict) -> dict:
    """The one committed projection: the ticket, named rather than copied.

    Every field here has a reader. `role` selects the host launch binding;
    the rest are the identities a child cannot derive from the ticket it is
    pointed at. What left the wire left because nothing read it: `admission`
    nowhere at all, `independence` and `isolation` only in the inline
    self-comparison, `executor` and `profile` only in the receive-side
    mismatch checks, `reference` as a forced copy of `source`, and
    `outcome_record_id` as a constant checked against itself.
    """

    role, _profile = resolved_role_profile(
        str(legacy["executor"]), legacy.get("profile")
    )
    source = {
        "id": str(data.get("id") or legacy.get("id")),
        "run": str(data.get("run") or legacy.get("run")),
    }
    packet = {
        "assigned_name": attempt.get("owner"),
        "assignment_seal": attempt.get("assignment_seal"),
        "dispatch_id": attempt.get("dispatch_id"),
        "durability": "ticket",
        "lease_expires_at": attempt.get("lease_expires_at"),
        "pack": legacy.get("pack"),
        "prompt": legacy.get("prompt"),
        "protocol": PROTOCOL,
        "review_kind": legacy.get("review_kind"),
        "role": role,
        "source": source,
        "workspace": legacy.get("workspace"),
    }
    packet["prompt"] = "\n".join((
        str(packet["prompt"]),
        "At closing, commit exactly one reserved outcome envelope with dispatch-outcome; dispatch-join consumes only that durable return.",
        f"The canonical envelope names protocol {PROTOCOL}, run {source['run']}, id {source['id']}, assignment_seal {packet['assignment_seal']}, dispatch_id {packet['dispatch_id']}, outcome_record_id {OUTCOME_RECORD_ID}, by {attempt.get('owner')}, status, and evidence with Result, Verification, Feedback, Risks, and Handoff.",
    ))
    return packet


def _replay_projection(attempt: dict, run, ticket_id, workspace, review_kind):
    record = next(
        (
            item for item in attempt.get("records") or []
            if item.get("record_id") == PACKET_RECORD_ID
        ),
        None,
    )
    if record is None:
        return None
    try:
        content = parse_canonical_json(record["content"])
    except (KeyError, TypeError, ValueError):
        content = None
    packet = content.get("packet") if isinstance(content, dict) else None
    if not isinstance(packet, dict):
        return _classification(
            "dispatch-record-invalid", "committed packet record has no canonical content"
        )
    request = {
        "dispatch_id": attempt.get("dispatch_id"),
        "source": {"id": ticket_id, "run": run},
        "workspace": workspace,
        "review_kind": review_kind,
    }
    prior = {key: packet.get(key) for key in request}
    if prior != request:
        return _classification(
            "idempotency-conflict",
            "dispatch packet was already committed with different delivery content",
        )
    return content


def _cmd_dispatch_packet(rest, *, _lock_held=False):
    """Project and commit one packet as a single locked transaction.

    Every read decides what the commit writes -- stored attempt, replay
    comparison, review state, seal -- so the lock covers the reads too. Held
    by the caller (the dispatch facade) or taken here; `_commit_record` is
    then told so rather than opening a second lock on the same run.
    """

    args = list(rest)
    dispatch_id = _extract_flag(args, "--dispatch-id")
    workspace = _extract_flag(args, "--workspace")
    artifact = _extract_flag(args, "--artifact")
    review_kind = _extract_flag(args, "--review-kind")
    if len(args) != 2 or not dispatch_id:
        return {"error": f"usage: {DISPATCH_PACKET_USAGE}"}
    run, ticket_id = args
    invalid = segment_refusal(run, ticket_id)
    if invalid is not None:
        return invalid
    try:
        with nullcontext() if _lock_held else _run_lock(run):
            return _packet_transaction(
                run, ticket_id, dispatch_id, workspace, artifact, review_kind,
            )
    except OSError as error:
        return _classification("state-inaccessible", f"unable to lock run '{run}': {error}")


def _packet_transaction(
    run, ticket_id, dispatch_id, workspace, artifact, review_kind,
):
    """The whole projection, under the run lock its caller holds."""

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
    replay = _replay_projection(
        attempt, run, ticket_id, workspace, review_kind
    )
    if replay is not None:
        return replay
    attempt, failure = _attempt(data, dispatch_id)
    if failure is not None:
        return failure
    review_state, review_error = packet_state_result(
        path, text, artifact, workspace,
    )
    if review_error is not None:
        return _classification("review-invalid", review_error)
    finding = workspace_establishment_finding(data, workspace)
    if finding is not None:
        return _classification(*finding)
    failure = _live_attempt(attempt)
    if failure is not None:
        return failure
    seal = str(data.get("assignment_seal") or "")
    if seal != attempt.get("assignment_seal") or seal_findings(ticket_id, text):
        # The same fact `_commit_record` fences every write on, refused here
        # before the projection is built rather than after: one code for one
        # fact, and it is the one the commit below would raise anyway.
        return _classification(
            "assignment-mismatch",
            "ticket no longer matches the attempt's sealed assignment",
        )
    legacy_args = [run, ticket_id, "--by", attempt["owner"]]
    if workspace is not None:
        legacy_args.extend(("--workspace", workspace))
    if review_kind is not None:
        legacy_args.extend(("--review-kind", review_kind))
    projected = _packet_under_run_lock(legacy_args, result_attempt=attempt, review_state=review_state)
    if "error" in projected:
        return projected
    packet = _projection_packet(projected["packet"], data, attempt)
    content = {"packet": packet}
    committed = _commit_record(
        run, ticket_id, dispatch_id, PACKET_RECORD_ID, content,
        mutate=packet_mutation(review_state, run, ticket_id, dispatch_id, PACKET_RECORD_ID),
        record_kind="packet", _lock_held=True,
    )
    if "error" in committed:
        return committed
    return content


__all__ = (
    "DISPATCH_PACKET_USAGE", "PACKET_RECORD_ID", "_cmd_dispatch_packet",
)
