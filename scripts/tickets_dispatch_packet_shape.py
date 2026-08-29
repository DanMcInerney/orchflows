"""Closed wire-shape validation for dispatch packets."""

from __future__ import annotations

if __package__:
    from .tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _identity_failure,
    )
    from .tickets_registry import REVIEW_KINDS
else:
    from tickets_attempts import (
        OUTCOME_RECORD_ID, PROTOCOL, _classification, _identity_failure,
    )
    from tickets_registry import REVIEW_KINDS

PACKET_FORMS = frozenset({"reference", "inline"})


def packet_shape(value):
    if isinstance(value, dict) and set(value) == {"packet"}:
        return _classification(
            "packet-invalid",
            "dispatch-receive expects the response .packet value, not its wrapper",
        )
    if not isinstance(value, dict) or value.get("protocol") != PROTOCOL:
        return _classification("packet-invalid", f"packet must name {PROTOCOL}")
    form = value.get("form")
    if form not in PACKET_FORMS:
        return _classification("packet-invalid", "packet form is unknown")
    required = (
        "assigned_name", "assignment_seal", "dispatch_id", "executor",
        "lease_expires_at", "outcome_record_id", "profile", "reply_to", "role",
    )
    if any(not isinstance(value.get(key), str) or not value[key] for key in required):
        return _classification("packet-invalid", "packet identity or routing field is missing")
    if value.get("durability") not in ("ticket", "ephemeral"):
        return _classification("packet-invalid", "packet durability is unknown")
    base = {
        "admission", "assigned_name", "assignment_seal", "dispatch_id",
        "durability", "executor", "form", "independence", "isolation",
        "lease_expires_at", "outcome_record_id", "pack", "profile", "prompt",
        "review_kind",
        "protocol", "reply_to", "role", "source", "workspace",
    }
    expected = base | ({"reference"} if form == "reference" else {"inline"})
    if set(value) != expected:
        return _classification("packet-invalid", "packet has unknown or missing fields")
    review_kind = value.get("review_kind")
    if review_kind is not None and review_kind not in REVIEW_KINDS:
        return _classification("packet-invalid", "packet review_kind is unknown")
    source = value.get("source")
    if not isinstance(source, dict) or set(source) != {"id", "run"} or any(
        not isinstance(source.get(key), str) or not source[key] for key in ("id", "run")
    ):
        return _classification("packet-invalid", "packet source is incomplete")
    if form == "reference":
        reference = value.get("reference")
        if not isinstance(reference, dict) or set(reference) != {"id", "run"} or reference != source:
            return _classification("packet-invalid", "packet reference does not equal its origin")
    else:
        inline = value.get("inline")
        if not isinstance(inline, dict) or set(inline) != {"assignment", "envelope_seal"}:
            return _classification("packet-invalid", "inline packet shape is incomplete")
    if value.get("workspace") is not None:
        failure = _identity_failure("workspace", value["workspace"], allow_path=True)
        if failure is not None:
            return _classification("packet-invalid", failure["error"])
    if value["outcome_record_id"] != OUTCOME_RECORD_ID:
        return _classification("packet-invalid", "packet outcome identity is not canonical")
    for kind, identity in (
        ("dispatch-id", value["dispatch_id"]),
        ("owner", value["assigned_name"]),
        ("reply-to", value["reply_to"]),
    ):
        failure = _identity_failure(kind, identity)
        if failure is not None:
            return _classification("packet-invalid", failure["error"])
    return None
