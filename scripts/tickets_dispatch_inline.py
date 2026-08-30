"""The inline packet form's seals and its one divergence check.

`contracts/dispatch.md` gives a packet two forms. Reference points at the
ticket and is re-read from it; inline is a self-carried snapshot, so
everything that decides whether such a snapshot is still the sealed
assignment lives here: the semantic digest both of its seals are taken
with, and the comparison a receiver makes before it executes anything.

Kept apart from projection because it is the only part of the packet family
that grades a payload it did not itself build, and because the projection
module carries the whole committed transaction and has no room to also
carry this.
"""

from __future__ import annotations

import hashlib

if __package__:
    from .tickets_dispatch_launch import resolved_role_profile
    from .tickets_dispatch_schema import classification as _classification
    from .tickets_format import canonical_json
else:  # pragma: no cover - direct/installed flat script path
    from tickets_dispatch_launch import resolved_role_profile
    from tickets_dispatch_schema import classification as _classification
    from tickets_format import canonical_json


def _semantic_digest(value) -> str:
    """The digest both inline seals are taken with, over canonical bytes."""

    encoded = canonical_json(value).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _inline_assignment_failure(packet: dict, assignment: dict):
    """Whether an inline packet still says what its sealed assignment says."""

    system = assignment.get("system")
    if not isinstance(system, dict):
        return _classification("assignment-divergent", "inline system identity is missing")
    executor = assignment.get("executor")
    role, assignment_profile = resolved_role_profile(executor, system.get("profile"))
    expected = {
        "executor": executor,
        "independence": system.get("independence") or "checker",
        "isolation": system.get("isolation"),
        "pack": system.get("pack"),
        "profile": assignment_profile,
        "review_kind": system.get("review_kind"),
        "role": role,
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
        "review_kind": packet.get("review_kind"),
        "source": source,
        "workspace": packet.get("workspace"),
    }
    inline = packet.get("inline")
    if not isinstance(inline, dict) or inline.get("envelope_seal") != _semantic_digest(sealed_envelope):
        return _classification("assignment-divergent", "inline routing envelope seal diverged")
    return None


__all__ = ("_inline_assignment_failure", "_semantic_digest")
