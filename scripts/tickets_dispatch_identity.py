"""The closed identity vocabulary of orchflows.dispatch.v1.

What a protocol identity may be spelled as, which record ids the protocol
reserves for itself, and the one shape a refusal takes. The schema module
validates whole documents against the generated shapes and re-exports every
name here.

Nothing here imports the schema: the direction is schema -> identity.
"""

from __future__ import annotations

import re

if __package__:
    from .tickets_shapes import (
        DISPATCH_PROTOCOL, LAUNCH_RECORD_ID as SHAPE_LAUNCH_RECORD_ID,
        OUTCOME_RECORD_ID as SHAPE_OUTCOME_RECORD_ID,
    )
else:
    from tickets_shapes import (
        DISPATCH_PROTOCOL, LAUNCH_RECORD_ID as SHAPE_LAUNCH_RECORD_ID,
        OUTCOME_RECORD_ID as SHAPE_OUTCOME_RECORD_ID,
    )

PROTOCOL = DISPATCH_PROTOCOL
LAUNCH_RECORD_ID = SHAPE_LAUNCH_RECORD_ID
OUTCOME_RECORD_ID = SHAPE_OUTCOME_RECORD_ID
RESERVED_RECORD_IDS = frozenset({LAUNCH_RECORD_ID, OUTCOME_RECORD_ID})
# Named individually, not only as the pair below, so a caller that needs
# exactly one namespace never respells it as a bare string to get there.
JOIN_RECORD_PREFIX = "join:"
LIFECYCLE_RECORD_PREFIX = "lifecycle:"
RESERVED_RECORD_PREFIXES = (JOIN_RECORD_PREFIX, LIFECYCLE_RECORD_PREFIX)
IDENTITY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def classification(code: str, detail: str) -> dict:
    return {"error": detail, "code": code, "protocol": PROTOCOL}


def identity_failure(kind: str, value, *, allow_path: bool = False):
    if not isinstance(value, str) or not value:
        return classification(f"{kind}-invalid", f"{kind} must be a non-empty string")
    if any(ord(mark) < 32 or mark == "`" for mark in value):
        return classification(f"{kind}-invalid", f"{kind} contains a control character or backtick")
    if not allow_path and IDENTITY_RE.fullmatch(value) is None:
        return classification(f"{kind}-invalid", f"{kind} is not a canonical protocol identity")
    return None


def record_id_is_reserved(record_id: str) -> bool:
    return record_id in RESERVED_RECORD_IDS or record_id.startswith(RESERVED_RECORD_PREFIXES)


def record_id_namespace_ok(kind: str, record_id: str):
    """Whether one record id sits in the namespace its kind reserves."""

    if kind == "launch":
        return record_id == LAUNCH_RECORD_ID
    if kind == "outcome":
        return record_id == OUTCOME_RECORD_ID
    if kind in ("join", "lifecycle"):
        return record_id.startswith(kind + ":")
    if kind in ("generic", "result"):
        return not record_id_is_reserved(record_id)
    return None


__all__ = (
    "IDENTITY_RE", "LAUNCH_RECORD_ID", "OUTCOME_RECORD_ID", "PROTOCOL",
    "RESERVED_RECORD_IDS", "RESERVED_RECORD_PREFIXES",
    "JOIN_RECORD_PREFIX", "LIFECYCLE_RECORD_PREFIX",
    "classification", "identity_failure", "record_id_is_reserved",
    "record_id_namespace_ok",
)
