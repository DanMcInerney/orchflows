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
        TicketFormatError, _extract_flag, _parse_frontmatter, _read_utf8,
        _section_body, _write_section, canonical_json, is_critique_stage_id,
        parse_canonical_json,
    )
    from .tickets_markdown import SECTION_SENTINEL
    from .tickets_result import RESULT_ATTRIBUTION_PREFIX
    from .tickets_store import NO_SINK_ERROR, _segment_error, _tickets_root
    from .tickets_shapes import (
        DISPATCH_OUTCOME_EVIDENCE_FIELDS, DISPATCH_OUTCOME_REQUIRED,
    )
else:
    from tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _commit_record,
        _identity_failure,
    )
    from tickets_dispatch_schema import state as _dispatch_state
    from tickets_format import (
        TicketFormatError, _extract_flag, _parse_frontmatter, _read_utf8,
        _section_body, _write_section, canonical_json, is_critique_stage_id,
        parse_canonical_json,
    )
    from tickets_markdown import SECTION_SENTINEL
    from tickets_result import RESULT_ATTRIBUTION_PREFIX
    from tickets_store import NO_SINK_ERROR, _segment_error, _tickets_root
    from tickets_shapes import (
        DISPATCH_OUTCOME_EVIDENCE_FIELDS, DISPATCH_OUTCOME_REQUIRED,
    )


OUTCOME_SECTIONS = tuple(DISPATCH_OUTCOME_EVIDENCE_FIELDS)
OUTCOME_FILE_FLAGS = {
    "Result": "--result-file",
    "Verification": "--verification-file",
    "Feedback": "--feedback-file",
    "Risks": "--risks-file",
    "Handoff": "--handoff-file",
}
DISPATCH_OUTCOME_USAGE = (
    "dispatch-outcome <run> <id> "
    "[--result-file <path>] [--verification-file <path>] [--feedback-file <path>] "
    "[--risks-file <path>] [--handoff-file <path>] | --file <canonical-outcome-path|->"
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
    """Parse typed close inputs, or a complete inline-relay carrier.

    The typed form is the default one: an envelope with no `--file` closes
    the attempt out of the evidence flags and the records already streamed.
    It used to be `--status` that selected it, and `--status` is gone --
    a child no longer names its own disposition, so the note it files says
    only what it did.
    """

    source_present = "--file" in args
    file_present = {
        section: flag in args for section, flag in OUTCOME_FILE_FLAGS.items()
    }
    source_file = _extract_flag(args, "--file")
    file_args = {
        section: _extract_flag(args, flag)
        for section, flag in OUTCOME_FILE_FLAGS.items()
    }
    if source_present and source_file is None:
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
        if any(value is not None for value in file_args.values()):
            return None, {
                "error": "--file carries the complete outcome and cannot be combined with typed inputs",
                "code": "outcome-invalid", "protocol": PROTOCOL,
            }
        return _outcome_file(source_file)
    return {"_files": file_args}, None


def _outcome_failure(run: str, ticket_id: str, content):
    required = set(DISPATCH_OUTCOME_REQUIRED)
    if not isinstance(content, dict) or set(content) != required:
        return _classification("outcome-invalid", "outcome envelope has unknown or missing fields")
    if content.get("protocol") != PROTOCOL or content.get("run") != run or content.get("id") != ticket_id:
        return _classification("outcome-invalid", "outcome envelope origin or protocol differs")
    if content.get("outcome_record_id") != OUTCOME_RECORD_ID:
        return _classification("outcome-invalid", "outcome envelope does not use the reserved identity")
    for kind, value in (("owner", content.get("by")), ("dispatch-id", content.get("dispatch_id"))):
        failure = _identity_failure(kind, value)
        if failure is not None:
            return _classification("outcome-invalid", failure["error"])
    evidence = content.get("evidence")
    if not isinstance(evidence, dict) or set(evidence) != set(OUTCOME_SECTIONS):
        return _classification("outcome-invalid", "outcome evidence must close the five executor sections")
    if any(not isinstance(evidence.get(section), str) for section in OUTCOME_SECTIONS):
        return _classification("outcome-invalid", "outcome evidence bodies must be strings")
    required_sections = ("Result", "Verification", "Feedback", "Risks")
    if any(not evidence[section].strip() for section in required_sections):
        return _classification("outcome-invalid", "closing outcome evidence is incomplete")
    # Handoff is optional and uncoupled: the envelope no longer names a
    # disposition, so nothing here can require or forbid a handoff on the
    # strength of one. A child that has work to hand over writes it, and
    # the join that reads the note decides what the ticket became.
    if is_critique_stage_id(ticket_id):
        # Critique Result and Feedback are generated finding carriers, not
        # arbitrary prose.  Keep the import lazy because tickets_review
        # consumes this module while joining a review stage.
        if __package__:
            from .tickets_review import ReviewError, canonical_finding_array
        else:
            from tickets_review import ReviewError, canonical_finding_array
        for section in ("Result", "Feedback"):
            try:
                canonical_finding_array(evidence[section], f"critique outcome {section}")
            except ReviewError as error:
                return _classification("outcome-invalid", str(error))
    for body in evidence.values():
        if any(line.startswith("## ") or line.startswith(RESULT_ATTRIBUTION_PREFIX) for line in body.splitlines()):
            return _classification("outcome-invalid", "outcome evidence contains a reserved heading or attribution")
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
    if isinstance(carrier, dict) and "_files" in carrier:
        evidence = {}
        for section in OUTCOME_SECTIONS:
            source = carrier["_files"].get(section)
            if source is not None:
                body, read_failure = _read_utf8(source, f"{section} evidence file")
                if read_failure is not None:
                    return read_failure
            elif section in {"Result", "Verification"}:
                body = _prior_result_body(attempt, section)
                if body is None:
                    return _classification(
                        "outcome-invalid",
                        f"outcome requires {section} evidence through --{section.lower()}-file or a prior result record",
                    )
            elif section in {"Feedback", "Risks"}:
                body = "[]"
            else:
                body = ""
            if body is None:
                body = ""
            evidence[section] = body
        content = {
            "protocol": PROTOCOL,
            "run": run,
            "id": ticket_id,
            "assignment_seal": attempt["assignment_seal"],
            "dispatch_id": attempt["dispatch_id"],
            "outcome_record_id": OUTCOME_RECORD_ID,
            "by": attempt["owner"],
            "evidence": evidence,
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
        updated = text
        try:
            for section in OUTCOME_SECTIONS:
                body = content["evidence"][section]
                if not body:
                    continue
                prior = _section_body(updated, section)
                materialized = (
                    f"{RESULT_ATTRIBUTION_PREFIX}`{content['by']}`\n\n{body}"
                )
                # The writer stores each block with trailing whitespace
                # stripped, and a block with nothing before it in the
                # section carries no leading blank line, so neither side of
                # this comparison may depend on either: rstrip both before
                # comparing, and test membership on its own, with no
                # required prefix.
                stripped = materialized.rstrip()
                if stripped and (prior.rstrip() == stripped or stripped in prior):
                    flag = OUTCOME_FILE_FLAGS[section]
                    return text, None, _classification(
                        "outcome-invalid",
                        f"outcome {section} repeats evidence already materialized "
                        f"by this dispatch. Pass only the unstreamed delta through "
                        f"`{flag}`",
                    )
                updated = _write_section(
                    updated, section, materialized,
                    bool(prior and prior != SECTION_SENTINEL),
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
    "DISPATCH_OUTCOME_USAGE", "OUTCOME_FILE_FLAGS",
    "OUTCOME_SECTIONS", "_cmd_dispatch_outcome", "_outcome_attempt",
    "_outcome_attempt_match", "_outcome_content", "_outcome_failure",
    "_prior_result_body",
)
