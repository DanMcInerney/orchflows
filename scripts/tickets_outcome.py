"""The dispatch-v1 reserved outcome: its carrier, its grade, its commit.

The whole outcome half of the return, in the module that already owned how
a carrier is built and read. It moved here from the join because the join is
what consumes an outcome, not what makes one, and because a module that owns
both had no room left to say why either works.
"""

from __future__ import annotations

import sys

if __package__:
    from .tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _commit_record,
        _identity_failure,
    )
    from .tickets_dispatch_schema import state as _dispatch_state
    from .tickets_format import (
        REPORT_SECTION, TicketFormatError, _extract_flag, _parse_frontmatter,
        _read_utf8, _section_body, _write_section, canonical_json,
        parse_canonical_json,
    )
    from .tickets_result import RESULT_ATTRIBUTION_PREFIX
    from .tickets_store import NO_SINK_ERROR, _segment_error, _tickets_root
    from .tickets_shapes import DISPATCH_OUTCOME_REQUIRED
    from .tickets_transitions import CLAIMED, SUSPENDED
else:
    from tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _commit_record,
        _identity_failure,
    )
    from tickets_dispatch_schema import state as _dispatch_state
    from tickets_format import (
        REPORT_SECTION, TicketFormatError, _extract_flag, _parse_frontmatter,
        _read_utf8, _section_body, _write_section, canonical_json,
        parse_canonical_json,
    )
    from tickets_result import RESULT_ATTRIBUTION_PREFIX
    from tickets_store import NO_SINK_ERROR, _segment_error, _tickets_root
    from tickets_shapes import DISPATCH_OUTCOME_REQUIRED
    from tickets_transitions import CLAIMED, SUSPENDED


DISPATCH_OUTCOME_USAGE = (
    "dispatch-outcome <run> <id> "
    "(--note <text> | --note-file <path> | --file <canonical-outcome-path|->)"
)
# The canonical encoding `--file` admits, named as the call that produces it.
# It lives in the refusals rather than the launch prompt: only the rare
# relaying coordinator ever builds an envelope, and the refusal it meets is
# the one surface it is guaranteed to read -- the prompt used to carry the
# whole recipe for every child, and before that the refusal said "canonical
# JSON" and left the relay to guess which of the four knobs it meant.
CANONICAL_DUMP = (
    'json.dump(envelope, handle, ensure_ascii=True, sort_keys=True, '
    'separators=(",", ":"))'
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
        if status in {CLAIMED, SUSPENDED}:
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


def _outcome_file(path):
    """Read one complete canonical outcome carrier from a file or stdin.

    ``-`` is standard input, decoded as UTF-8 the way the accepted-blocker
    seam reads it: a relaying coordinator holds the envelope in memory, and
    telling it to land the envelope in a file first is a step that exists
    only to be forgotten.
    """

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
    mismatched = sorted(
        key for key, value in expected.items() if content.get(key) != value
    )
    if mismatched:
        return {
            "error": "outcome envelope differs from its inferred attempt on "
            + ", ".join(mismatched) + "; it must carry exactly "
            + ", ".join(f"{key}={expected[key]}" for key in sorted(expected))
            + ", and evidence as one string",
            "code": "outcome-invalid", "protocol": PROTOCOL,
        }
    return None


def _outcome_content(args: list):
    """Parse the closing note, or a complete inline-relay carrier.

    The note is one free text, so the typed form is one flag rather than five:
    nothing downstream parses this prose, so nothing here asks a child to sort
    it into sections first. `--file` still carries the whole canonical
    envelope, which is how a coordinator relays one it did not write.
    """

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
    """`(1-based number, line)` for the first line the ticket grammar owns.

    Named rather than counted: two children of one run had to read this
    module's source to learn which of their note's lines the bare "contains
    a reserved heading" refusal meant, and what the rule was.
    """

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
    """Commit or replay the reserved outcome envelope.

    ``_lock_held`` is the landing composition's: it holds this run's lock
    across import, join, and retirement, and a commit that opened a second
    lock on the same run would wait on its own caller.
    """

    args = list(rest)
    if len(args) < 2:
        return {"error": f"usage: {DISPATCH_OUTCOME_USAGE}"}
    run, ticket_id = args[:2]
    remaining = args[2:]
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    carrier, failure = _outcome_content(remaining)
    if failure is not None:
        return failure

    inferred, failure = _outcome_attempt(run, ticket_id)
    if failure is not None:
        return failure
    _path, _text, _data, _state, attempt = inferred
    if isinstance(carrier, dict) and "_note" in carrier:
        content = {
            "protocol": PROTOCOL,
            "run": run,
            "id": ticket_id,
            "assignment_seal": attempt["assignment_seal"],
            "dispatch_id": attempt["dispatch_id"],
            "outcome_record_id": OUTCOME_RECORD_ID,
            "by": attempt["owner"],
            "evidence": carrier["_note"],
        }
    else:
        content = carrier
    failure = _outcome_attempt_match(content, run, ticket_id, attempt)
    if failure is not None:
        return failure
    if content.get("protocol") != PROTOCOL or content.get("run") != run or content.get("id") != ticket_id:
        return _classification("outcome-invalid", "outcome envelope origin or protocol differs")
    if not isinstance(content, dict):
        return _classification("outcome-invalid", "outcome envelope must be an object")
    failure = _outcome_failure(run, ticket_id, content)
    if failure is not None:
        return failure

    def commit_outcome(text, _data, _attempt, _state):
        # The note appends to Report like any other filing. Nothing compares
        # it against what the child already streamed: the delta law was there
        # to keep five typed sections from being snapshotted twice, and with
        # one free-text channel a repeated sentence is a reader's problem,
        # never a refusal that loses the close.
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

    return _commit_record(
        run, ticket_id, content["dispatch_id"], OUTCOME_RECORD_ID, content,
        mutate=commit_outcome, expected_seal=content["assignment_seal"],
        expected_owner=content["by"], record_kind="outcome",
        _lock_held=_lock_held,
    )

__all__ = (
    "CANONICAL_DUMP", "DISPATCH_OUTCOME_USAGE", "_cmd_dispatch_outcome",
    "_outcome_attempt", "_outcome_attempt_match", "_outcome_content",
    "_outcome_failure",
)
