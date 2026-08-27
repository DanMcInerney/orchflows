"""Atomic dispatch-v1 execution-attempt state over one ticket file."""

from __future__ import annotations

from datetime import datetime, timezone

if __package__:
    from .tickets_format import (
        _extract_flag, _parse_frontmatter, _parse_iso, _read_utf8,
        _set_frontmatter_field, canonical_json, parse_canonical_json,
    )
    from .tickets_generations import seal_findings
    from .tickets_store import (
        NO_SINK_ERROR, UTC_STAMP, _run_lock, _segment_error, _tickets_root,
        _write_text_atomically,
    )
else:
    from tickets_format import (
        _extract_flag, _parse_frontmatter, _parse_iso, _read_utf8,
        _set_frontmatter_field, canonical_json, parse_canonical_json,
    )
    from tickets_generations import seal_findings
    from tickets_store import (
        NO_SINK_ERROR, UTC_STAMP, _run_lock, _segment_error, _tickets_root,
        _write_text_atomically,
    )

PROTOCOL = "orchflows.dispatch.v1"
DISPATCH_OPEN_USAGE = (
    "dispatch-open <run> <id> --by <name> --dispatch-id <id> "
    "--lease-expires-at <absolute-iso>"
)


def _classification(code: str, detail: str) -> dict:
    return {"error": detail, "code": code, "protocol": PROTOCOL}


def _state(data: dict):
    encoded = str(data.get("dispatch_v1") or "").strip()
    if not encoded:
        return None, None
    try:
        state = parse_canonical_json(encoded)
    except (TypeError, ValueError) as error:
        return None, _classification(
            "dispatch-record-invalid", f"dispatch_v1 is not canonical JSON: {error}"
        )
    if not isinstance(state, dict) or state.get("protocol") != PROTOCOL:
        return None, _classification(
            "dispatch-record-invalid", f"dispatch_v1 does not name {PROTOCOL}"
        )
    attempts = state.get("attempts")
    if not isinstance(attempts, list):
        return None, _classification(
            "dispatch-record-invalid", "dispatch_v1 attempts is not a list"
        )
    return state, None


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
        "state": attempt["state"],
    }}


def _cmd_dispatch_open(rest):
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
    if any(mark in value for value in (owner, dispatch_id) for mark in ("`", "\r", "\n")):
        return {"error": "dispatch identity contains backticks or line breaks"}
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
        with _run_lock(run):
            text, failure = _read_utf8(path)
            if failure is not None:
                return failure
            data = _parse_frontmatter(text)
            state, failure = _state(data)
            if failure is not None:
                return failure
            status = str(data.get("status") or "")
            if state is None and status in ("claimed", "suspended"):
                return _classification(
                    "legacy-live-claim",
                    "pre-v1 live claim must be completed or abandoned by its existing owner before dispatch-v1 cutover",
                )
            seal = str(data.get("assignment_seal") or "").strip()
            findings = seal_findings(ticket_id, text)
            if findings:
                return _classification(
                    "assignment-mismatch", "ticket assignment is not sealed at its current semantic generation"
                )
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
            if same is not None:
                prior = {key: same.get(key) for key in request}
                if prior == request:
                    return _open_response(run, ticket_id, same, "replayed")
                return _classification(
                    "idempotency-conflict",
                    f"dispatch_id '{dispatch_id}' was already opened with different content",
                )
            now = datetime.now(timezone.utc)
            live = []
            for attempt in attempts:
                expiry = _parse_iso(attempt.get("lease_expires_at"))
                if attempt.get("state") == "live" and expiry is not None and now < expiry:
                    live.append(attempt)
            if live:
                return _classification(
                    "live-attempt",
                    f"ticket already has live dispatch_id '{live[-1].get('dispatch_id')}'",
                )
            if lease <= now:
                return _classification(
                    "lease-expired", "--lease-expires-at is not later than the open time"
                )
            if status != "ready":
                return _classification(
                    "ticket-not-ready", f"dispatch-open requires ready status, found '{status}'"
                )
            for attempt in attempts:
                if attempt.get("state") == "live":
                    attempt["state"] = "expired"
                    attempt["expired_at"] = now.strftime(UTC_STAMP)
            attempt = {
                **request,
                "opened_at": now.strftime(UTC_STAMP),
                "records": [],
                "state": "live",
            }
            attempts.append(attempt)
            encoded = canonical_json({"attempts": attempts, "protocol": PROTOCOL})
            updated = _set_frontmatter_field(text, "dispatch_v1", encoded)
            updated = _set_frontmatter_field(updated, "status", "claimed")
            updated = _set_frontmatter_field(updated, "claimed_by", owner)
            updated = _set_frontmatter_field(updated, "claimed_at", attempt["opened_at"])
            _write_text_atomically(path, updated)
            return _open_response(run, ticket_id, attempt, "opened")
    except OSError as error:
        return {"error": f"unable to open dispatch attempt: {error}"}

