"""The immutable predecessor-linked review-stage ledger primitives.

`review_v1` is the closed, ordered record chain a `<id>.check` review stage
carries; `tickets.py check` is what anchors a completed one to its target's
`checked_by` ([contracts/work-item.md](../contracts/work-item.md)). The
composite gate and the mechanical typed critique/repair join lanes that
used to mint and adjudicate those stages are gone with the door that
emitted their stubs: a critique is a `judge` brick and the repair answering
it a `do` brick now, sequenced by the calling workflow's prose, and nothing
here composes or adjudicates one. What remains is the ledger's own shape --
building one record, validating a chain of them, and reading whichever chain
a ticket already carries.
"""

from __future__ import annotations

if __package__:
    from .tickets_format import _parse_frontmatter, canonical_json
    from .tickets_review_schema import (
        SchemaError, digest as _digest, validate_records,
    )
else:
    from tickets_format import _parse_frontmatter, canonical_json
    from tickets_review_schema import (
        SchemaError, digest as _digest, validate_records,
    )


REVIEW_PROTOCOL = "orchflows.review.v1"
REVIEW_FIELD = "review_v1"


class ReviewError(ValueError):
    """A review record is absent, divergent, or not closed."""


def _record(kind: str, predecessor, **fields) -> dict:
    content = {
        "kind": kind,
        "predecessor": predecessor,
        "protocol": REVIEW_PROTOCOL,
        **fields,
    }
    return {**content, "identity": _digest(content)}


def _review_state(records, *, allow_legacy: bool = False) -> dict:
    state = {"protocol": REVIEW_PROTOCOL, "records": list(records)}
    review_records(state, allow_legacy=allow_legacy)
    return state


def review_records(value, *, allow_legacy: bool = False) -> list:
    try:
        return validate_records(value, allow_legacy=allow_legacy)
    except SchemaError as error:
        raise ReviewError(str(error)) from error


def state_from_text(
    text: str, *, required: bool = False, allow_legacy: bool = False,
) -> dict | None:
    encoded = _parse_frontmatter(text).get(REVIEW_FIELD)
    if encoded is None:
        if required:
            raise ReviewError(f"ticket has no {REVIEW_FIELD} predecessor ledger")
        return None
    records = review_records(encoded, allow_legacy=allow_legacy)
    return _review_state(records, allow_legacy=allow_legacy)


__all__ = (
    "REVIEW_FIELD", "REVIEW_PROTOCOL", "ReviewError", "canonical_json",
    "review_records", "state_from_text",
)
