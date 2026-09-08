"""The dispatch-v1 reserved outcome: its carrier, its grade, its commit.

The whole outcome half of the return, in the module that owns how a carrier
is built and read. It sits here rather than in the join because the join is
what consumes an outcome, not what makes one.
"""

from __future__ import annotations

import sys

if __package__:
    from .tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _commit_record,
        _identity_failure,
    )
    from .tickets_format import (
        REPORT_SECTION, TicketFormatError, _extract_flag,
        _read_utf8, _section_body, _write_section, canonical_json,
        parse_canonical_json,
    )
    from .tickets_result import RESULT_ATTRIBUTION_PREFIX
    from .tickets_store import _segment_error
    from .tickets_shapes import DISPATCH_OUTCOME_REQUIRED
else:
    from tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _commit_record,
        _identity_failure,
    )
    from tickets_format import (
        REPORT_SECTION, TicketFormatError, _extract_flag,
        _read_utf8, _section_body, _write_section, canonical_json,
        parse_canonical_json,
    )
    from tickets_result import RESULT_ATTRIBUTION_PREFIX
    from tickets_store import _segment_error
    from tickets_shapes import DISPATCH_OUTCOME_REQUIRED


DISPATCH_OUTCOME_USAGE = (
    "dispatch-outcome <run> <id> "
    "(--assignment-seal <seal> --dispatch-id <id> --by <assigned-name> "
    "(--note <text> | --note-file <path>) | --file <canonical-outcome-path|->)"
)
# The canonical encoding `--file` admits, named as the call that produces it.
# It lives in the refusals rather than the launch prompt: only the rare
# relaying coordinator ever builds an envelope, and the refusal it meets is
# the one surface it is guaranteed to read.
CANONICAL_DUMP = (
    'json.dump(envelope, handle, ensure_ascii=True, sort_keys=True, '
    'separators=(",", ":"))'
)


def _outcome_file(path):
    """Read one complete canonical outcome carrier from a file or stdin."""

    if path == "-":
        try:
            stream = getattr(sys.stdin, "buffer", sys.stdin)
            value = stream.read()
            raw, failure = (
                value.decode("utf-8") if isinstance(value, bytes) else value, None
            )
        except (OSError, UnicodeDecodeError, AttributeError) as error:
            return None, {
                "error": f"unreadable canonical outcome file: {error}",
                "code": "outcome-invalid", "protocol": PROTOCOL,
            }
    else:
        raw, failure = _read_utf8(path, "canonical outcome file")
    if failure is not None:
        return None, failure
    try:
        content = parse_canonical_json(raw)
    except (TypeError, ValueError) as error:
        return None, {
            "error": f"outcome file is not canonical JSON: {error}; "
            f"write it with {CANONICAL_DUMP}",
            "code": "outcome-invalid", "protocol": PROTOCOL,
        }
    if raw != canonical_json(content):
        return None, {
            "error": "outcome file is not canonical JSON; "
            f"write it with {CANONICAL_DUMP}",
            "code": "outcome-invalid", "protocol": PROTOCOL,
        }
    return content, None


def _outcome_content(args: list):
    """Parse the closing note, or a complete inline-relay carrier."""

    present = [flag for flag in ("--file", "--note", "--note-file") if flag in args]
    source_file = _extract_flag(args, "--file")
    note = _extract_flag(args, "--note")
    note_file = _extract_flag(args, "--note-file")
    values = {"--file": source_file, "--note": note, "--note-file": note_file}
    if any(values[flag] is None for flag in present):
        return None, {
            "error": "dispatch-outcome flags require a value",
            "code": "outcome-invalid", "protocol": PROTOCOL,
        }
    if args:
        return None, {
            "error": f"dispatch-outcome does not accept {' '.join(args)}; usage: {DISPATCH_OUTCOME_USAGE}",
            "code": "outcome-invalid", "protocol": PROTOCOL,
        }
    if len(present) != 1:
        return None, {
            "error": f"dispatch-outcome takes exactly one of --note, --note-file or --file; got {present or 'none'}. usage: {DISPATCH_OUTCOME_USAGE}",
            "code": "outcome-invalid", "protocol": PROTOCOL,
        }
    if source_file is not None:
        return _outcome_file(source_file)
    if note_file is not None:
        body, failure = _read_utf8(note_file, "closing note file")
        if failure is not None:
            return None, failure
        return {"_note": body}, None
    return {"_note": note}, None


def _reserved_line(evidence: str):
    """`(1-based number, line)` for the first line the ticket grammar owns."""

    for number, line in enumerate(evidence.splitlines(), 1):
        if line.startswith("## ") or line.startswith(RESULT_ATTRIBUTION_PREFIX):
            return number, line
    return None


def _outcome_failure(run: str, ticket_id: str, content):
    required = set(DISPATCH_OUTCOME_REQUIRED)
    if not isinstance(content, dict) or set(content) != required:
        return _classification(
            "outcome-invalid",
            "outcome envelope has unknown or missing fields; exactly "
            + ", ".join(sorted(required)) + " are required",
        )
    if content.get("protocol") != PROTOCOL or content.get("run") != run or content.get("id") != ticket_id:
        return _classification("outcome-invalid", "outcome envelope origin or protocol differs")
    if content.get("outcome_record_id") != OUTCOME_RECORD_ID:
        return _classification("outcome-invalid", "outcome envelope does not use the reserved identity")
    for kind, value in (("owner", content.get("by")), ("dispatch-id", content.get("dispatch_id"))):
        failure = _identity_failure(kind, value)
        if failure is not None:
            return _classification("outcome-invalid", failure["error"])
    # One free text, and nothing parses it: a child's closing note is prose
    # for a reader, so this asks only that it exist and that it not forge the
    # section grammar or the writer attribution the ticket file owns.
    evidence = content.get("evidence")
    if not isinstance(evidence, str):
        return _classification("outcome-invalid", "outcome evidence must be one closing note")
    if not evidence.strip():
        return _classification("outcome-invalid", "closing outcome evidence is empty")
    reserved = _reserved_line(evidence)
    if reserved is not None:
        number, line = reserved
        return _classification(
            "outcome-invalid",
            "outcome evidence contains a reserved heading or attribution: "
            f"line {number} begins {line[:60]!r}. A closing note's lines may "
            f"not begin with '## ' or with '{RESULT_ATTRIBUTION_PREFIX}', the "
            "attribution this write adds itself; '###' and deeper are fine",
        )
    return None


def _cmd_dispatch_outcome(rest, *, _lock_held=False):
    """Commit or replay the reserved outcome envelope."""

    args = list(rest)
    if len(args) < 2:
        return {"error": f"usage: {DISPATCH_OUTCOME_USAGE}"}
    run, ticket_id = args[:2]
    remaining = args[2:]
    identity = {
        "assignment_seal": _extract_flag(remaining, "--assignment-seal"),
        "dispatch_id": _extract_flag(remaining, "--dispatch-id"),
        "by": _extract_flag(remaining, "--by"),
    }
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    carrier, failure = _outcome_content(remaining)
    if failure is not None:
        return failure

    if isinstance(carrier, dict) and "_note" in carrier:
        if not all(identity.values()):
            return _classification("outcome-invalid", "note close requires launch-bound --assignment-seal, --dispatch-id and --by; " + DISPATCH_OUTCOME_USAGE)
        content = {
            "protocol": PROTOCOL,
            "run": run,
            "id": ticket_id,
            "assignment_seal": identity["assignment_seal"],
            "dispatch_id": identity["dispatch_id"],
            "outcome_record_id": OUTCOME_RECORD_ID,
            "by": identity["by"],
            "evidence": carrier["_note"],
        }
    else:
        if any(value is not None for value in identity.values()):
            return _classification("outcome-invalid", "--file carries its own identity; do not combine it with note identity flags")
        content = carrier
    failure = _outcome_failure(run, ticket_id, content)
    if failure is not None:
        return failure

    def commit_outcome(text, _data, _attempt, _state):
        # The note appends to Report like any other filing. Nothing compares
        # it against what the child already streamed: with one free-text
        # channel a repeated sentence is a reader's problem, never a refusal
        # that loses the close.
        prior = _section_body(text, REPORT_SECTION)
        try:
            updated = _write_section(
                text, REPORT_SECTION,
                f"{RESULT_ATTRIBUTION_PREFIX}`{content['by']}`\n\n{content['evidence']}",
                bool(prior),
            )
        except TicketFormatError as error:
            return text, None, _classification("outcome-invalid", str(error))
        return updated, {"outcome": content}, None

    answer = _commit_record(
        run, ticket_id, content["dispatch_id"], OUTCOME_RECORD_ID, content,
        mutate=commit_outcome, expected_seal=content["assignment_seal"],
        expected_owner=content["by"], record_kind="outcome",
        _lock_held=_lock_held,
    )
    if answer.get("code") == "assignment-mismatch":
        return {**answer, "code": "outcome-invalid"}
    return answer

__all__ = (
    "CANONICAL_DUMP", "DISPATCH_OUTCOME_USAGE", "_cmd_dispatch_outcome",
    "_outcome_content",
    "_outcome_failure",
)
