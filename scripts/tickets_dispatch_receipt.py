"""Receiver identity checks and byte-safe packet input carriage."""

from __future__ import annotations

from pathlib import Path
import sys

if __package__:
    from .tickets_dispatch_schema import (
        RECEIPT_RECORD_ID, accepted_receipt_failure, classification,
        identity_failure, state as _state,
    )
    from .tickets_format import (
        _extract_flag, _parse_frontmatter, _read_utf8, parse_canonical_json,
    )
    from .tickets_store import NO_SINK_ERROR, _segment_error, _tickets_root
else:
    from tickets_dispatch_schema import (
        RECEIPT_RECORD_ID, accepted_receipt_failure, classification,
        identity_failure, state as _state,
    )
    from tickets_format import _extract_flag, _parse_frontmatter, _read_utf8, parse_canonical_json
    from tickets_store import NO_SINK_ERROR, _segment_error, _tickets_root


DISPATCH_RECEIPT_USAGE = "dispatch-receipt <run> <id> --dispatch-id <id>"


def actual_mismatch(packet: dict, role, profile, owner, reply_to, workspace):
    for key, expected, actual, code in (
        ("assigned_name", packet["assigned_name"], owner, "identity-mismatch"),
        ("role", packet["role"], role, "role-mismatch"),
        ("profile", packet["profile"], profile, "profile-mismatch"),
        ("reply_to", packet["reply_to"], reply_to, "authority-mismatch"),
        ("workspace", packet.get("workspace"), workspace, "authority-mismatch"),
    ):
        if expected != actual:
            return classification(code, f"received {key} does not match packet")
    return None


def read_packet_payload(content, source_file):
    if source_file is None:
        return content, None
    if source_file == "-":
        try:
            return sys.stdin.buffer.read().decode("utf-8"), None
        except (AttributeError, OSError, UnicodeDecodeError, ValueError) as error:
            return None, classification(
                "packet-invalid", f"unreadable UTF-8 packet input: {error}"
            )
    content, failure = _read_utf8(Path(source_file), "packet file")
    if failure is not None:
        return None, classification("packet-invalid", failure["error"])
    return content, None


def _cmd_dispatch_receipt(rest):
    """Read one accepted dispatch receipt without changing ticket state.

    The ticket's complete dispatch ledger is validated before selecting the
    named attempt. Missing state and missing records stay distinct structured
    refusals so callers cannot downgrade an unknown result to a negative
    answer.
    """
    args = list(rest)
    dispatch_id = _extract_flag(args, "--dispatch-id")
    if len(args) != 2 or not dispatch_id:
        return {"error": f"usage: {DISPATCH_RECEIPT_USAGE}"}
    run, ticket_id = args
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        failure = _segment_error(kind, value)
        if failure is not None:
            return failure
    failure = identity_failure("dispatch-id", dispatch_id)
    if failure is not None:
        return failure

    root = _tickets_root()
    if root is None:
        return classification("state-inaccessible", NO_SINK_ERROR)
    path = root / run / f"{ticket_id}.md"
    text, failure = _read_utf8(path, "ticket")
    if failure is not None:
        return classification("state-inaccessible", failure["error"])
    data = _parse_frontmatter(text)
    state, failure = _state(data)
    if failure is not None:
        return failure
    if state is None:
        status = str(data.get("status") or "")
        if status in ("claimed", "suspended"):
            return classification(
                "legacy-live-claim", "pre-v1 live claim has no dispatch record"
            )
        return classification("dispatch-mismatch", "ticket has no dispatch-v1 attempt")
    attempt = next(
        (item for item in state["attempts"] if item.get("dispatch_id") == dispatch_id),
        None,
    )
    if attempt is None:
        return classification(
            "dispatch-mismatch",
            f"dispatch_id '{dispatch_id}' was never opened for this ticket",
        )

    # A valid closed state may legitimately have only a committed packet. Use
    # the protocol validator's same receipt gate so a missing or malformed
    # accepted receipt is never represented as success.
    failure = accepted_receipt_failure(attempt)
    if failure is not None:
        return failure
    receipt_record = next(
        (
            item for item in attempt.get("records", [])
            if item.get("record_id") == RECEIPT_RECORD_ID
        ),
        None,
    )
    try:
        content = parse_canonical_json(receipt_record["content"])
        receipt = content["receipt"]
    except (KeyError, TypeError, ValueError):
        return classification(
            "dispatch-record-invalid",
            "accepted receipt has no canonical persisted receipt",
        )
    return {"receipt": receipt}
