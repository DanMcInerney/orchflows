"""Committed packet projection and deterministic receipt for dispatch v1."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re

if __package__:
    from .tickets_attempts import (
        OUTCOME_RECORD_ID, PACKET_RECORD_ID, RECEIPT_RECORD_ID, PROTOCOL,
        _classification, _commit_record, _identity_failure, _state,
    )
    from .tickets_format import (
        _extract_flag, _parse_frontmatter, _parse_iso, _read_utf8,
        canonical_json, parse_canonical_json,
    )
    from .tickets_generations import assignment_payload, seal_findings
    from .tickets_packet import _packet_under_run_lock, workspace_establishment_finding
    from .tickets_dispatch_receipt import actual_mismatch, read_packet_payload
    from .tickets_dispatch_packet_shape import PACKET_FORMS, packet_shape as _packet_shape
    from .tickets_dispatch_schema import stored_state
    from .tickets_review import packet_mutation, packet_state_result
    from .tickets_store import _tickets_root
else:
    from tickets_attempts import (
        OUTCOME_RECORD_ID, PACKET_RECORD_ID, RECEIPT_RECORD_ID, PROTOCOL,
        _classification, _commit_record, _identity_failure, _state,
    )
    from tickets_format import (
        _extract_flag, _parse_frontmatter, _parse_iso, _read_utf8,
        canonical_json, parse_canonical_json,
    )
    from tickets_generations import assignment_payload, seal_findings
    from tickets_packet import _packet_under_run_lock, workspace_establishment_finding
    from tickets_dispatch_receipt import actual_mismatch, read_packet_payload
    from tickets_dispatch_packet_shape import PACKET_FORMS, packet_shape as _packet_shape
    from tickets_dispatch_schema import stored_state
    from tickets_review import packet_mutation, packet_state_result
    from tickets_store import _tickets_root

DISPATCH_PACKET_USAGE = (
    "dispatch-packet <run> <id> --dispatch-id <id> --reply-to <name> "
    "[--workspace <path>] [--artifact <fixed-identity>] [--form reference | inline]"
)
DISPATCH_RECEIVE_USAGE = (
    "dispatch-receive (--content <canonical-json> | --file <path|->) "
    "--role <worker|planner> "
    "--profile <name> --by <name> --reply-to <name> [--workspace <path>]"
)
ROLE_RE = re.compile(r"^role:\s*(worker|planner|none)\s*$", re.MULTILINE)


def _semantic_digest(value) -> str:
    encoded = canonical_json(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


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


def _declared_role(executor: str):
    here = Path(__file__).resolve()
    roots = (here.parent.parent, here.parent.parent / "lib")
    groups = ("instances", "kernel", "engines", "workflows", "utilities")
    for root in roots:
        for group in groups:
            path = root / "skills" / group / executor / "SKILL.md"
            text, failure = _read_utf8(path, "executor role declaration")
            if failure is not None:
                continue
            match = ROLE_RE.search(text)
            if match is not None:
                return match.group(1)
    return None


def _projection_packet(
    legacy: dict, data: dict, text: str, attempt: dict, form: str
) -> dict:
    executor = str(legacy["executor"])
    declared_role = _declared_role(executor)
    explicit_profile = legacy.get("profile")
    profile_role = (
        explicit_profile.removeprefix("orch-")
        if explicit_profile in ("orch-worker", "orch-planner") else None
    )
    role = profile_role or declared_role
    profile = explicit_profile or (
        f"orch-{role}" if role in ("worker", "planner") else None
    )
    packet = {
        "admission": legacy.get("admission"),
        "assigned_name": attempt.get("owner"),
        "assignment_seal": attempt.get("assignment_seal"),
        "dispatch_id": attempt.get("dispatch_id"),
        "durability": "ticket",
        "executor": executor,
        "form": form,
        "independence": legacy.get("independence"),
        "isolation": legacy.get("isolation"),
        "lease_expires_at": attempt.get("lease_expires_at"),
        "outcome_record_id": attempt.get("outcome_record_id"),
        "pack": legacy.get("pack"),
        "profile": profile,
        "prompt": legacy.get("prompt"),
        "protocol": PROTOCOL,
        "reply_to": legacy.get("reply_to"),
        "role": role,
        "source": {
            "id": str(data.get("id") or legacy.get("id")),
            "run": str(data.get("run") or legacy.get("run")),
        },
        "workspace": legacy.get("workspace"),
    }
    assignment = assignment_payload(str(data.get("id") or legacy.get("id")), text)
    if form == "reference":
        packet["reference"] = {
            "id": str(data.get("id") or legacy.get("id")),
            "run": str(data.get("run") or legacy.get("run")),
        }
        packet["prompt"] = "\n".join((
            str(packet["prompt"]),
            "Pass the response `.packet` value through dispatch-receive --file <path> or --file -; do not pass the response wrapper or reconstruct it as a shell literal.",
            "At closing, commit exactly one reserved outcome envelope with dispatch-outcome; dispatch-join consumes only that durable return.",
            f"The canonical envelope names protocol {PROTOCOL}, run {packet['source']['run']}, id {packet['source']['id']}, assignment_seal {packet['assignment_seal']}, dispatch_id {packet['dispatch_id']}, outcome_record_id {OUTCOME_RECORD_ID}, by {attempt.get('owner')}, status, and evidence with Result, Verification, Feedback, Risks, and Handoff.",
        ))
    else:
        sealed_envelope = {
            "assigned_name": packet["assigned_name"],
            "assignment": assignment,
            "assignment_seal": packet["assignment_seal"],
            "dispatch_id": packet["dispatch_id"],
            "durability": packet["durability"],
            "lease_expires_at": packet["lease_expires_at"],
            "outcome_record_id": packet["outcome_record_id"],
            "reply_to": packet["reply_to"],
            "role": packet["role"],
            "profile": packet["profile"],
            "source": packet["source"],
            "workspace": packet["workspace"],
        }
        packet["inline"] = {
            "assignment": assignment,
            "envelope_seal": _semantic_digest(sealed_envelope),
        }
        packet["prompt"] = "\n".join((
            f"Apply skill {executor} directly to the inline sealed assignment in this packet.",
            "Use inline.assignment.semantic as Goal, Context, and optional Suggested files; do not try to repair or reconstruct a ticket path.",
            "Pass the response `.packet` value through dispatch-receive --file <path> or --file -; do not pass the response wrapper or reconstruct it as a shell literal.",
            "The authoritative state sink must be available at receipt; unauthenticated offline execution is refused.",
            "After accepted receipt, commit the canonical envelope with dispatch-outcome before dispatch-join.",
            f"The envelope must name protocol {PROTOCOL}, assignment_seal {packet['assignment_seal']}, dispatch_id {packet['dispatch_id']}, outcome_record_id {OUTCOME_RECORD_ID}, by {attempt.get('owner')}, status, and evidence containing Result, Verification, Feedback, Risks, plus Handoff only for suspension.",
            f"Your assigned name is `{attempt.get('owner')}` and reply_to is `{legacy.get('reply_to')}`.",
        ))
    return packet


def _replay_projection(attempt: dict, run, ticket_id, form, reply_to, workspace):
    record = next(
        (
            item for item in attempt.get("records") or []
            if item.get("record_id") == PACKET_RECORD_ID
        ),
        None,
    )
    if record is None:
        return None
    success = record.get("success")
    content = (
        success.get("committed_record", {}).get("content")
        if isinstance(success, dict) else None
    )
    packet = content.get("packet") if isinstance(content, dict) else None
    if not isinstance(packet, dict):
        return _classification(
            "dispatch-record-invalid", "committed packet record has no stored success"
        )
    request = {
        "dispatch_id": attempt.get("dispatch_id"),
        "form": form,
        "reply_to": reply_to,
        "source": {"id": ticket_id, "run": run},
        "workspace": workspace,
    }
    prior = {key: packet.get(key) for key in request}
    if prior != request:
        return _classification(
            "idempotency-conflict",
            "dispatch packet was already committed with different delivery content",
        )
    return content


def _cmd_dispatch_packet(rest):
    args = list(rest)
    dispatch_id = _extract_flag(args, "--dispatch-id")
    reply_to = _extract_flag(args, "--reply-to")
    workspace = _extract_flag(args, "--workspace")
    artifact = _extract_flag(args, "--artifact")
    form = (_extract_flag(args, "--form") or "reference").strip()
    if len(args) != 2 or not dispatch_id or not reply_to or form not in PACKET_FORMS:
        return {"error": f"usage: {DISPATCH_PACKET_USAGE}"}
    failure = _identity_failure("reply-to", reply_to)
    if failure is not None:
        return failure
    run, ticket_id = args
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
        attempt, run, ticket_id, form, reply_to, workspace
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
        return _classification(
            "assignment-divergent",
            "ticket no longer matches the attempt's sealed assignment",
        )
    legacy_args = [run, ticket_id, "--reply-to", reply_to, "--by", attempt["owner"]]
    if workspace is not None:
        legacy_args.extend(("--workspace", workspace))
    projected = _packet_under_run_lock(legacy_args, result_attempt=attempt, review_state=review_state)
    if "error" in projected:
        return projected
    packet = _projection_packet(projected["packet"], data, text, attempt, form)
    content = {"packet": packet}
    committed = _commit_record(
        run, ticket_id, dispatch_id, PACKET_RECORD_ID, content,
        mutate=packet_mutation(review_state, run, ticket_id, dispatch_id, PACKET_RECORD_ID, content),
        record_kind="packet",
    )
    if "error" in committed:
        return committed
    return committed["committed_record"]["content"]




def _inline_assignment_failure(packet: dict, assignment: dict):
    system = assignment.get("system")
    if not isinstance(system, dict):
        return _classification("assignment-divergent", "inline system identity is missing")
    executor = assignment.get("executor")
    declared_role = _declared_role(str(executor or ""))
    assignment_profile = system.get("profile") or (
        f"orch-{declared_role}" if declared_role in ("worker", "planner") else None
    )
    profile_role = (
        assignment_profile.removeprefix("orch-")
        if assignment_profile in ("orch-worker", "orch-planner") else None
    )
    expected = {
        "executor": executor,
        "independence": system.get("independence") or "checker",
        "isolation": system.get("isolation"),
        "pack": system.get("pack"),
        "profile": assignment_profile,
        "role": profile_role or declared_role,
    }
    if any(packet.get(key) != value for key, value in expected.items()):
        return _classification(
            "assignment-divergent",
            "inline routing does not match the sealed assignment",
        )
    source = packet.get("source")
    if packet["durability"] != "ticket":
        return _classification(
            "assignment-divergent", "a ticket projection cannot be downgraded to ephemeral"
        )
    if (
        not isinstance(source, dict)
        or source.get("id") != assignment.get("ticket")
        or not isinstance(source.get("run"), str)
        or not source.get("run")
    ):
        return _classification(
            "assignment-divergent", "inline source does not match the sealed assignment"
        )
    sealed_envelope = {
        "assigned_name": packet["assigned_name"],
        "assignment": assignment,
        "assignment_seal": packet["assignment_seal"],
        "dispatch_id": packet["dispatch_id"],
        "durability": packet["durability"],
        "lease_expires_at": packet["lease_expires_at"],
        "outcome_record_id": packet["outcome_record_id"],
        "reply_to": packet["reply_to"],
        "role": packet["role"],
        "profile": packet["profile"],
        "source": source,
        "workspace": packet.get("workspace"),
    }
    inline = packet.get("inline")
    if not isinstance(inline, dict) or inline.get("envelope_seal") != _semantic_digest(sealed_envelope):
        return _classification("assignment-divergent", "inline routing envelope seal diverged")
    return None


def _reference_ticket(packet: dict):
    reference = packet.get("reference")
    if not isinstance(reference, dict):
        return None, None, _classification("packet-invalid", "reference packet has no reference")
    run, ticket_id = reference.get("run"), reference.get("id")
    if not all(isinstance(value, str) and value for value in (run, ticket_id)):
        return None, None, _classification("packet-invalid", "ticket reference is incomplete")
    root = _tickets_root()
    path = None if root is None else root / run / f"{ticket_id}.md"
    if path is None or not path.is_file():
        return None, None, _classification("state-inaccessible", "referenced ticket is inaccessible")
    text, failure = _read_utf8(path)
    if failure is not None:
        return None, None, _classification("state-inaccessible", failure["error"])
    return text, _parse_frontmatter(text), None


def _validate_durable(packet: dict, text: str, data: dict):
    ticket_id = str(data.get("id") or "")
    seal = str(data.get("assignment_seal") or "")
    if seal != packet["assignment_seal"] or seal_findings(ticket_id, text):
        return _classification("assignment-divergent", "referenced assignment seal diverged")
    attempt, failure = _attempt(data, packet["dispatch_id"])
    if failure is not None:
        return failure
    records = attempt.get("records")
    record = next(
        (item for item in records or [] if item.get("record_id") == PACKET_RECORD_ID),
        None,
    )
    expected = canonical_json({"packet": packet})
    if record is None or record.get("kind") != "packet" or record.get("content") != expected:
        return _classification("idempotency-conflict", "packet is not the committed projection")
    if attempt.get("owner") != packet["assigned_name"]:
        return _classification("identity-mismatch", "attempt owner diverges from packet")
    return None


def _cmd_dispatch_receive(rest):
    args = list(rest)
    content = _extract_flag(args, "--content")
    source_file = _extract_flag(args, "--file")
    role = _extract_flag(args, "--role")
    profile = _extract_flag(args, "--profile")
    owner = _extract_flag(args, "--by")
    reply_to = _extract_flag(args, "--reply-to")
    workspace = _extract_flag(args, "--workspace")
    if (
        args or (content is None) == (source_file is None)
        or not all((role, profile, owner, reply_to))
    ):
        return {"error": f"usage: {DISPATCH_RECEIVE_USAGE}"}
    content, failure = read_packet_payload(content, source_file)
    if failure is not None:
        return failure
    try:
        packet = parse_canonical_json(content)
    except (TypeError, ValueError) as error:
        return _classification("packet-invalid", f"packet is not JSON: {error}")
    failure = _packet_shape(packet)
    if failure is not None:
        return failure
    failure = actual_mismatch(packet, role, profile, owner, reply_to, workspace)
    if failure is not None:
        return failure
    lease = _parse_iso(packet["lease_expires_at"])
    if lease is None or datetime.now(timezone.utc) >= lease:
        return _classification("stale-attempt", "packet lease is expired")
    if packet["form"] == "reference":
        text, data, failure = _reference_ticket(packet)
        if failure is not None:
            return failure
        failure = _validate_durable(packet, text, data)
    else:
        inline = packet.get("inline")
        assignment = inline.get("assignment") if isinstance(inline, dict) else None
        if not isinstance(assignment, dict) or _semantic_digest(assignment) != packet["assignment_seal"]:
            return _classification("assignment-divergent", "inline assignment seal diverged")
        failure = _inline_assignment_failure(packet, assignment)
        if failure is not None:
            return failure
        reference = packet.get("source")
        packet_with_reference = dict(packet, reference=reference)
        text, data, failure = _reference_ticket(packet_with_reference)
        if failure is None:
            failure = _validate_durable(packet, text, data)
    if failure is not None:
        return failure
    receipt = {
        "assignment_seal": packet["assignment_seal"],
        "dispatch_id": packet["dispatch_id"],
        "durability": packet["durability"],
        "form": packet["form"],
        "outcome": "accepted",
        "protocol": PROTOCOL,
        "state_sink_checked": True,
    }

    def commit_receipt(text, _data, _attempt, _state):
        return text, {"receipt": receipt}, None

    source = packet["source"]
    return _commit_record(
        source["run"], source["id"], packet["dispatch_id"], RECEIPT_RECORD_ID,
        {"packet": packet, "receipt": receipt}, mutate=commit_receipt,
        expected_seal=packet["assignment_seal"],
        expected_owner=packet["assigned_name"], record_kind="receipt",
    )


__all__ = (
    "DISPATCH_PACKET_USAGE", "DISPATCH_RECEIVE_USAGE", "PACKET_FORMS",
    "PACKET_RECORD_ID", "RECEIPT_RECORD_ID", "_cmd_dispatch_packet",
    "_cmd_dispatch_receive",
)
