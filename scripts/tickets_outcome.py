"""Typed outcome carrier construction for dispatch-v1."""

from __future__ import annotations

if __package__:
    from .tickets_attempts import OUTCOME_RECORD_ID, PROTOCOL
    from .tickets_dispatch_schema import state as _dispatch_state
    from .tickets_format import (
        _extract_flag, _parse_frontmatter, _read_utf8, canonical_json,
        parse_canonical_json,
    )
    from .tickets_store import NO_SINK_ERROR, _tickets_root
    from .tickets_shapes import DISPATCH_OUTCOME_VALUES
else:
    from tickets_attempts import OUTCOME_RECORD_ID, PROTOCOL
    from tickets_dispatch_schema import state as _dispatch_state
    from tickets_format import (
        _extract_flag, _parse_frontmatter, _read_utf8, canonical_json,
        parse_canonical_json,
    )
    from tickets_store import NO_SINK_ERROR, _tickets_root
    from tickets_shapes import DISPATCH_OUTCOME_VALUES


JOIN_STATUSES = frozenset(DISPATCH_OUTCOME_VALUES["status"])
OUTCOME_FILE_FLAGS = {
    "Result": "--result-file",
    "Verification": "--verification-file",
    "Feedback": "--feedback-file",
    "Risks": "--risks-file",
    "Handoff": "--handoff-file",
}
DISPATCH_OUTCOME_USAGE = (
    "dispatch-outcome <run> <id> --status <complete|blocked|stalled|limited|failed|suspended> "
    "[--result-file <path>] [--verification-file <path>] [--feedback-file <path>] "
    "[--risks-file <path>] [--handoff-file <path>] | --file <canonical-outcome-path>"
)


def _outcome_attempt(run: str, ticket_id: str):
    """Read the attempt that owns the reserved outcome identity."""

    root = _tickets_root()
    if root is None:
        return None, {"error": NO_SINK_ERROR}
    path = root / run / f"{ticket_id}.md"
    text, failure = _read_utf8(path)
    if failure is not None:
        return None, failure
    data = _parse_frontmatter(text)
    state, failure = _dispatch_state(data)
    if failure is not None:
        return None, failure
    if state is None:
        status = str(data.get("status") or "")
        if status in {"claimed", "suspended"}:
            return None, {
                "error": "pre-v1 live claim has no dispatch record; its existing owner must complete or abandon it",
                "code": "legacy-live-claim", "protocol": PROTOCOL,
            }
        return None, {
            "error": "ticket has no dispatch-v1 attempt",
            "code": "dispatch-mismatch", "protocol": PROTOCOL,
        }
    live = [item for item in state["attempts"] if item.get("state") == "live"]
    if live:
        return (path, text, data, state, live[-1]), None
    for attempt in reversed(state["attempts"]):
        if any(item.get("record_id") == OUTCOME_RECORD_ID for item in attempt.get("records", [])):
            return (path, text, data, state, attempt), None
    return (path, text, data, state, state["attempts"][-1]), None


def _prior_result_body(attempt: dict, section: str):
    """Resolve one section from the latest committed executor result."""

    body = None
    for record in attempt.get("records", []):
        if record.get("kind") != "result":
            continue
        try:
            content = parse_canonical_json(record["content"])
        except (KeyError, TypeError, ValueError):
            continue
        if isinstance(content, dict) and content.get("section") == section:
            candidate = content.get("body")
            if isinstance(candidate, str) and candidate.strip():
                body = candidate
    return body


def _outcome_file(path):
    """Read one complete canonical outcome carrier from a file."""

    raw, failure = _read_utf8(path, "canonical outcome file")
    if failure is not None:
        return None, failure
    try:
        content = parse_canonical_json(raw)
    except (TypeError, ValueError) as error:
        return None, {
            "error": f"outcome file is not canonical JSON: {error}",
            "code": "outcome-invalid", "protocol": PROTOCOL,
        }
    if raw != canonical_json(content):
        return None, {
            "error": "outcome file is not canonical JSON",
            "code": "outcome-invalid", "protocol": PROTOCOL,
        }
    return content, None


def _outcome_attempt_match(content: dict, run: str, ticket_id: str, attempt: dict):
    """Ensure a relayed carrier names the inferred protocol attempt exactly."""

    if not isinstance(content, dict):
        return {"error": "outcome envelope must be an object", "code": "outcome-invalid", "protocol": PROTOCOL}
    expected = {
        "protocol": PROTOCOL, "run": run, "id": ticket_id,
        "assignment_seal": attempt.get("assignment_seal"),
        "dispatch_id": attempt.get("dispatch_id"),
        "outcome_record_id": OUTCOME_RECORD_ID, "by": attempt.get("owner"),
    }
    if any(content.get(key) != value for key, value in expected.items()):
        return {
            "error": "outcome envelope differs from its inferred attempt",
            "code": "outcome-invalid", "protocol": PROTOCOL,
        }
    return None


def _outcome_content(args: list):
    """Parse typed close inputs, or a complete inline-relay carrier."""

    status_present = "--status" in args
    source_present = "--file" in args
    file_present = {
        section: flag in args for section, flag in OUTCOME_FILE_FLAGS.items()
    }
    status = _extract_flag(args, "--status")
    source_file = _extract_flag(args, "--file")
    file_args = {
        section: _extract_flag(args, flag)
        for section, flag in OUTCOME_FILE_FLAGS.items()
    }
    if (status_present and status is None) or (source_present and source_file is None):
        return None, {
            "error": "dispatch-outcome flags require a value",
            "code": "outcome-invalid", "protocol": PROTOCOL,
        }
    if any(file_present[section] and file_args[section] is None
           for section in OUTCOME_FILE_FLAGS):
        return None, {
            "error": "dispatch-outcome evidence flags require a value",
            "code": "outcome-invalid", "protocol": PROTOCOL,
        }
    if args:
        return None, {
            "error": f"dispatch-outcome does not accept {' '.join(args)}; usage: {DISPATCH_OUTCOME_USAGE}",
            "code": "outcome-invalid", "protocol": PROTOCOL,
        }
    if source_file is not None:
        if status is not None or any(value is not None for value in file_args.values()):
            return None, {
                "error": "--file carries the complete outcome and cannot be combined with typed inputs",
                "code": "outcome-invalid", "protocol": PROTOCOL,
            }
        return _outcome_file(source_file)
    if status is None:
        return None, {
            "error": f"dispatch-outcome requires --status or --file; usage: {DISPATCH_OUTCOME_USAGE}",
            "code": "outcome-invalid", "protocol": PROTOCOL,
        }
    if status not in JOIN_STATUSES:
        return None, {
            "error": "outcome status is not a join disposition",
            "code": "outcome-invalid", "protocol": PROTOCOL,
        }
    return {"status": status, "_files": file_args}, None


__all__ = (
    "DISPATCH_OUTCOME_USAGE", "JOIN_STATUSES", "OUTCOME_FILE_FLAGS",
    "_outcome_attempt", "_outcome_attempt_match", "_outcome_content",
    "_prior_result_body",
)
