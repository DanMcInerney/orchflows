"""Atomic dispatch-v1 execution-attempt state over one ticket file."""

from __future__ import annotations

from contextlib import nullcontext
from datetime import datetime, timezone
if __package__:
    from .tickets_format import (
        _extract_flag, _parse_frontmatter, _parse_iso, _read_utf8,
        _set_frontmatter_field, canonical_json, is_frame, parse_canonical_json,
    )
    from .tickets_generations import seal_findings
    from . import tickets_dispatch_guards as dispatch_guards
    from .tickets_project import CLAIM_REMEDY, binding_refusal
    from .tickets_transitions import CLAIMED, SUSPENDED
    from .tickets_dispatch_schema import (
        LAUNCH_RECORD_ID, LIFECYCLE_RECORD_PREFIX, OUTCOME_RECORD_ID, PROTOCOL,
        RECORD_KINDS,
        classification as _classification, identity_failure as _identity_failure,
        record_id_is_reserved as _record_id_is_reserved,
        record_id_namespace_ok as _namespace_ok, state as _state,
        validate_state as _validate_state,
    )
    from .tickets_store import (
        NO_SINK_ERROR, UTC_STAMP, _run_lock, _segment_error, _tickets_root,
        _write_text_atomically,
    )
else:
    from tickets_format import (
        _extract_flag, _parse_frontmatter, _parse_iso, _read_utf8,
        _set_frontmatter_field, canonical_json, is_frame, parse_canonical_json,
    )
    from tickets_generations import seal_findings
    import tickets_dispatch_guards as dispatch_guards
    from tickets_project import CLAIM_REMEDY, binding_refusal
    from tickets_transitions import CLAIMED, SUSPENDED
    from tickets_dispatch_schema import (
        LAUNCH_RECORD_ID, LIFECYCLE_RECORD_PREFIX, OUTCOME_RECORD_ID, PROTOCOL,
        RECORD_KINDS,
        classification as _classification, identity_failure as _identity_failure,
        record_id_is_reserved as _record_id_is_reserved,
        record_id_namespace_ok as _namespace_ok, state as _state,
        validate_state as _validate_state,
    )
    from tickets_store import (
        NO_SINK_ERROR, UTC_STAMP, _run_lock, _segment_error, _tickets_root,
        _write_text_atomically,
    )

DISPATCH_OPEN_USAGE = (
    "dispatch-open <run> <id> --by <name> --dispatch-id <id> "
    "--lease-expires-at <absolute-iso>"
)
DISPATCH_COMMIT_USAGE = (
    "dispatch-commit <run> <id> --dispatch-id <id> --record-id <id> "
    "--content <canonical-json>"
)
DISPATCH_RETIRE_USAGE = (
    "dispatch-retire <run> <id> --assignment-seal <seal> "
    "--dispatch-id <id> --record-id <id>"
)
DISPATCH_REPLACE_USAGE = (
    "dispatch-replace <run> <id> --assignment-seal <seal> "
    "--dispatch-id <current-id> --record-id <lifecycle:id> "
    "--replacement-dispatch-id <new-id> --by <name> "
    "--lease-expires-at <absolute-iso> [--supersede-live]"
)

def _open_response(run: str, ticket_id: str, attempt: dict, outcome: str) -> dict:
    return {"dispatch": {
        "protocol": PROTOCOL,
        "outcome": outcome,
        "run": run,
        "id": ticket_id,
        "dispatch_id": attempt["dispatch_id"],
        "assignment_seal": attempt["assignment_seal"],
        "lease_expires_at": attempt["lease_expires_at"],
        "opened_at": attempt["opened_at"],
        "outcome_record_id": attempt["outcome_record_id"],
        "state": attempt["state"],
    }}

def _cmd_dispatch_open(rest, *, _lock_held=False):
    args = list(rest)
    owner = _extract_flag(args, "--by")
    dispatch_id = _extract_flag(args, "--dispatch-id")
    lease_text = _extract_flag(args, "--lease-expires-at")
    if len(args) != 2 or not all((owner, dispatch_id, lease_text)):
        return {"error": f"usage: {DISPATCH_OPEN_USAGE}"}
    run, ticket_id = args
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    for kind, value in (("owner", owner), ("dispatch-id", dispatch_id)):
        failure = _identity_failure(kind, value)
        if failure is not None:
            return failure
    held = binding_refusal(run, CLAIM_REMEDY)
    if held is not None:
        return {"error": held}
    lease = _parse_iso(lease_text)
    if lease is None or lease.utcoffset() is None:
        return _classification(
            "lease-invalid", "--lease-expires-at must be an absolute ISO timestamp"
        )
    lease = lease.astimezone(timezone.utc)
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": NO_SINK_ERROR}
    path = tickets_root / run / f"{ticket_id}.md"
    try:
        lock = nullcontext() if _lock_held else _run_lock(run)
        with lock:
            text, failure = _read_utf8(path)
            if failure is not None:
                return failure
            data = _parse_frontmatter(text)
            failure = dispatch_guards.origin_failure(data, run, ticket_id)
            if failure is not None:
                return failure
            state, failure = _state(data)
            if failure is not None:
                return failure
            status = str(data.get("status") or "")
            if state is None and status in (CLAIMED, SUSPENDED):
                return _classification(
                    "claim-without-dispatch",
                    "a live claim exists only as a dispatch-v1 attempt; this claimed ticket has no dispatch record",
                )
            seal = str(data.get("assignment_seal") or "").strip()
            request = {
                "assignment_seal": seal,
                "dispatch_id": dispatch_id,
                "lease_expires_at": lease_text,
                "owner": owner,
            }
            attempts = [] if state is None else list(state["attempts"])
            same = next(
                (attempt for attempt in attempts if attempt.get("dispatch_id") == dispatch_id),
                None,
            )
            # contracts/dispatch.md's attempt precedence, which `_commit_record`
            # already keeps: an exact replay of an opened dispatch_id returns
            # its stored success first, and only an unseen open may then be
            # classified assignment-mismatch. Graded the other way round, a
            # retry of the very call that opened the attempt was refused for
            # the seal it had itself been opened against.
            if same is not None:
                prior = {key: same.get(key) for key in request}
                if prior == request:
                    return _open_response(run, ticket_id, same, "replayed")
                return _classification(
                    "idempotency-conflict",
                    f"dispatch_id '{dispatch_id}' was already opened with different "
                    "content; `tickets.py dispatch` retires a failed attempt "
                    "automatically, so open a fresh --dispatch-id instead of "
                    "reusing this one, or run `tickets.py dispatch-replace` to "
                    "replace a still-live attempt explicitly",
                )
            if seal_findings(ticket_id, text):
                return _classification(
                    "assignment-mismatch", "ticket assignment is not sealed at its current semantic generation"
                )
            failure = dispatch_guards.admission_failure(path, text, data, run, ticket_id)
            if failure is not None:
                return failure
            now = datetime.now(timezone.utc)
            failure = dispatch_guards.live_attempt_failure(attempts, now)
            if failure is not None:
                return failure
            if lease <= now:
                return _classification(
                    "lease-expired", "--lease-expires-at is not later than the open time"
                )
            allowed = ("ready",) if state is None else ("ready", CLAIMED, SUSPENDED)
            if status not in allowed:
                return _classification(
                    "ticket-not-ready",
                    f"dispatch-open cannot start from status '{status}'",
                )
            attempt = {
                **request,
                "opened_at": now.strftime(UTC_STAMP),
                "outcome_record_id": OUTCOME_RECORD_ID,
                "records": [],
                "state": "live",
            }
            attempts.append(attempt)
            encoded = canonical_json({"attempts": attempts, "protocol": PROTOCOL})
            updated = _set_frontmatter_field(text, "dispatch_v1", encoded)
            updated = _set_frontmatter_field(updated, "status", CLAIMED)
            _write_text_atomically(path, updated)
            return _open_response(run, ticket_id, attempt, "opened")
    except OSError as error:
        return {"error": f"unable to open dispatch attempt: {error}"}

def _record_response(run: str, ticket_id: str, dispatch_id: str, record_id: str) -> dict:
    """The stored success for one committed record: its identity alone.

    Not the content. Every record already stores that once, as the
    canonical string the `(dispatch_id, record_id)` idempotency
    comparison is made against, and the second copy under this success
    was ~73% of a gate ticket's bytes -- 275 KB on the largest one.
    A caller that wants the content reads the record.
    """

    return {"committed_record": {
        "protocol": PROTOCOL,
        "run": run,
        "id": ticket_id,
        "dispatch_id": dispatch_id,
        "record_id": record_id,
    }}

def _commit_record(
    run, ticket_id, dispatch_id, record_id, content, *, mutate=None,
    expected_seal=None, expected_owner=None, require_live_lease=True,
    record_kind="generic", _lock_held=False,
):
    """Commit or replay one record and its optional ticket mutation atomically."""
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    for kind, value in (("dispatch-id", dispatch_id), ("record-id", record_id)):
        failure = _identity_failure(kind, value)
        if failure is not None:
            return failure
    if record_kind not in RECORD_KINDS:
        return _classification("record-kind-invalid", f"unknown record kind '{record_kind}'")
    if record_kind not in ("generic", "result") and not _namespace_ok(record_kind, record_id):
        return _classification("record-id-invalid", f"{record_kind} operation used another record namespace")
    if record_kind in ("generic", "result") and _record_id_is_reserved(record_id):
        return _classification("record-id-reserved", f"record_id '{record_id}' belongs to a protocol-owned operation")
    normalized = canonical_json(content)
    tickets_root = _tickets_root()
    if tickets_root is None:
        return {"error": NO_SINK_ERROR}
    path = tickets_root / run / f"{ticket_id}.md"
    try:
        lock = nullcontext() if _lock_held else _run_lock(run)
        with lock:
            text, failure = _read_utf8(path)
            if failure is not None:
                return failure
            data = _parse_frontmatter(text)
            failure = dispatch_guards.origin_failure(data, run, ticket_id)
            if failure is not None:
                return failure
            state, failure = _state(data)
            if failure is not None:
                return failure
            if state is None:
                if str(data.get("status") or "") in (CLAIMED, SUSPENDED):
                    return _classification(
                        "claim-without-dispatch",
                        "a live claim exists only as a dispatch-v1 attempt; this claimed ticket has no dispatch record",
                    )
                return _classification("dispatch-mismatch", "ticket has no dispatch-v1 attempt")
            attempt = next(
                (item for item in state["attempts"] if item.get("dispatch_id") == dispatch_id),
                None,
            )
            if attempt is None:
                return _classification(
                    "dispatch-mismatch", f"dispatch_id '{dispatch_id}' was never opened for this ticket"
                )
            records = attempt.get("records")
            if not isinstance(records, list):
                return _classification(
                    "dispatch-record-invalid", "attempt records is not a list"
                )
            prior = next(
                (item for item in records if item.get("record_id") == record_id), None
            )
            if prior is not None:
                if prior.get("content") != normalized:
                    return _classification(
                        "idempotency-conflict",
                        f"record_id '{record_id}' was already committed with "
                        "different content; choose a different --record-id for "
                        "new content, or match the original content exactly to "
                        "replay it",
                    )
                success = prior.get("success")
                if not isinstance(success, dict):
                    return _classification(
                        "dispatch-record-invalid", "committed record has no stored success"
                    )
                return success
            now = datetime.now(timezone.utc)
            expiry = _parse_iso(attempt.get("lease_expires_at"))
            ended = attempt.get("state") != "live" or expiry is None
            # A frame holds no lease to arbitrate (contracts/work-item.md):
            # its driver is the session that opened it, singular by
            # construction, so nothing contends for the write and an expiry
            # could only end a journal somebody is still writing. What ends a
            # frame's attempt is its close, and `state` still says so.
            if require_live_lease and not is_frame(data):
                ended = ended or now >= expiry
            if ended:
                return _classification(
                    "stale-attempt",
                    f"unseen record '{record_id}' cannot commit on an ended dispatch attempt",
                )
            seal = str(data.get("assignment_seal") or "").strip()
            if seal != attempt.get("assignment_seal") or seal_findings(ticket_id, text):
                return _classification(
                    "assignment-mismatch", "dispatch attempt is fenced to another assignment seal"
                )
            if expected_seal is not None and expected_seal != seal:
                return _classification(
                    "assignment-mismatch", "result operation names another assignment seal"
                )
            if expected_owner is not None and expected_owner != attempt.get("owner"):
                return _classification(
                    "identity-mismatch", "result writer does not match the dispatch attempt owner"
                )
            if mutate is None:
                success = _record_response(run, ticket_id, dispatch_id, record_id)
                updated = text
            else:
                updated, success, failure = mutate(text, data, attempt, state)
                if failure is not None:
                    return failure
            records.append({
                "committed_at": now.strftime(UTC_STAMP),
                "content": normalized,
                "kind": record_kind,
                "record_id": record_id,
                "success": success,
            })
            failure = _validate_state(
                state, run=run, ticket_id=ticket_id, frame=is_frame(data),
            )
            if failure is not None:
                return failure
            updated = _set_frontmatter_field(updated, "dispatch_v1", canonical_json(state))
            _write_text_atomically(path, updated)
            return success
    except OSError as error:
        return {"error": f"unable to commit dispatch record: {error}"}

def _cmd_dispatch_commit(rest):
    args = list(rest)
    dispatch_id = _extract_flag(args, "--dispatch-id")
    record_id = _extract_flag(args, "--record-id")
    content_text = _extract_flag(args, "--content")
    if len(args) != 2 or not all((dispatch_id, record_id)) or content_text is None:
        return {"error": f"usage: {DISPATCH_COMMIT_USAGE}"}
    run, ticket_id = args
    for kind, value in (("run id", run), ("ticket id", ticket_id)):
        invalid = _segment_error(kind, value)
        if invalid is not None:
            return invalid
    try:
        content = parse_canonical_json(content_text)
    except (TypeError, ValueError) as error:
        return _classification("content-invalid", f"--content is not JSON: {error}")
    if content_text != canonical_json(content):
        return _classification("content-invalid", "--content is not canonical JSON")
    if _record_id_is_reserved(record_id):
        return _classification(
            "record-id-reserved",
            f"record_id '{record_id}' belongs to a protocol-owned operation",
        )
    return _commit_record(
        run, ticket_id, dispatch_id, record_id, content, record_kind="generic"
    )

def _cmd_dispatch_retire(rest, *, _lock_held=False):
    args = list(rest)
    assignment_seal = _extract_flag(args, "--assignment-seal")
    dispatch_id = _extract_flag(args, "--dispatch-id")
    record_id = _extract_flag(args, "--record-id")
    if len(args) != 2 or not all((assignment_seal, dispatch_id, record_id)):
        return {"error": f"usage: {DISPATCH_RETIRE_USAGE}"}
    run, ticket_id = args
    content = {
        "assignment_seal": assignment_seal,
        "dispatch_id": dispatch_id,
        "operation": "retire",
    }

    def retire(text, _data, attempt, _state_record):
        # No state guard here: `_commit_record` refuses an unseen record on an
        # attempt whose state is not live as `stale-attempt` before any mutate
        # runs, and an exact replay returns its stored success without
        # reaching this at all. A second copy of that rule could only ever
        # disagree with the one that decides.
        retired_at = datetime.now(timezone.utc).strftime(UTC_STAMP)
        response = {"dispatch": {
            "protocol": PROTOCOL,
            "outcome": "retired",
            "run": run,
            "id": ticket_id,
            "dispatch_id": dispatch_id,
            "record_id": record_id,
            "retired_at": retired_at,
            "state": "retired",
        }}
        attempt["state"] = "retired"
        attempt["retired_at"] = retired_at
        attempt["retirement"] = response
        return text, response, None

    if not record_id.startswith(LIFECYCLE_RECORD_PREFIX):
        return _classification("record-id-invalid", "retirement record_id must use the lifecycle: namespace")
    return _commit_record(
        run, ticket_id, dispatch_id, record_id, content,
        mutate=retire, expected_seal=assignment_seal, require_live_lease=False,
        record_kind="lifecycle", _lock_held=_lock_held,
    )

def _cmd_dispatch_replace(rest):
    args = list(rest)
    assignment_seal = _extract_flag(args, "--assignment-seal")
    dispatch_id = _extract_flag(args, "--dispatch-id")
    record_id = _extract_flag(args, "--record-id")
    replacement_id = _extract_flag(args, "--replacement-dispatch-id")
    owner = _extract_flag(args, "--by")
    lease_text = _extract_flag(args, "--lease-expires-at")
    supersede_live = "--supersede-live" in args
    if supersede_live:
        args.remove("--supersede-live")
    if len(args) != 2 or not all((
        assignment_seal, dispatch_id, record_id, replacement_id, owner, lease_text,
    )):
        return {"error": f"usage: {DISPATCH_REPLACE_USAGE}"}
    run, ticket_id = args
    for kind, value in (("owner", owner), ("dispatch-id", replacement_id)):
        failure = _identity_failure(kind, value)
        if failure is not None:
            return failure
    if not record_id.startswith(LIFECYCLE_RECORD_PREFIX):
        return _classification("record-id-invalid", "replacement record_id must use the lifecycle: namespace")
    lease = _parse_iso(lease_text)
    if lease is None or lease.utcoffset() is None:
        return _classification(
            "lease-invalid", "--lease-expires-at must be an absolute ISO timestamp"
        )
    lease = lease.astimezone(timezone.utc)
    content = {
        "assignment_seal": assignment_seal,
        "dispatch_id": replacement_id,
        "lease_expires_at": lease_text,
        "operation": "replace",
        "owner": owner,
        "replaces": dispatch_id,
    }

    def replace(text, _data, current, state):
        if any(item.get("dispatch_id") == replacement_id for item in state["attempts"]):
            return text, None, _classification(
                "idempotency-conflict",
                f"replacement dispatch_id '{replacement_id}' was already used; "
                "choose a different --replacement-dispatch-id",
            )
        now = datetime.now(timezone.utc)
        undeclared = dispatch_guards.undeclared_supersession_failure(
            current, now, declared=supersede_live,
        )
        if undeclared is not None:
            return text, None, undeclared
        if lease <= now:
            return text, None, _classification(
                "lease-expired", "replacement lease is not later than the replacement time"
            )
        opened_at = now.strftime(UTC_STAMP)
        replacement = {
            "assignment_seal": assignment_seal,
            "dispatch_id": replacement_id,
            "lease_expires_at": lease_text,
            "opened_at": opened_at,
            "outcome_record_id": OUTCOME_RECORD_ID,
            "owner": owner,
            "records": [],
            "replaces": dispatch_id,
            "state": "live",
        }
        response = {"dispatch": {
            "protocol": PROTOCOL,
            "outcome": "replaced",
            "run": run,
            "id": ticket_id,
            "dispatch_id": replacement_id,
            "record_id": record_id,
            "replaces": dispatch_id,
            "assignment_seal": assignment_seal,
            "lease_expires_at": lease_text,
            "opened_at": opened_at,
            "state": "live",
        }}
        current["state"] = "replaced"
        current["replaced_at"] = opened_at
        current["replaced_by"] = replacement_id
        current["replacement"] = response
        state["attempts"].append(replacement)
        updated = _set_frontmatter_field(text, "status", CLAIMED)
        return updated, response, None

    return _commit_record(
        run, ticket_id, dispatch_id, record_id, content,
        mutate=replace, expected_seal=assignment_seal, require_live_lease=False,
        record_kind="lifecycle",
    )
