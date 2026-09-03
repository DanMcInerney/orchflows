#!/usr/bin/env python3
"""Pure canonical search-plan transformation and compatibility facade.

``python scripts/search_plan.py advance`` reads one UTF-8 JSON request on
stdin and writes one canonical ``search-advance/v1`` response. Protocol,
archive, projection and generation-advance ownership live in static sibling
modules; this is the installed CLI and import seam that
``docs/search-plan-protocol.md`` governs. The ``"evaluation_identity"``
stays opaque here rather than selecting an evaluation mode.
"""

import copy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import sys
from pathlib import Path

_SIBLING_DIR = str(Path(__file__).resolve().parent)
if _SIBLING_DIR not in sys.path:
    sys.path.append(_SIBLING_DIR)

if __package__:  # in-repo package import; installed scripts sit flat together
    from scripts import console
    from scripts import search_plan_advance as _advance_module
    from scripts import search_plan_archive as _archive
    from scripts import search_plan_projection as _projection
    from scripts import search_plan_protocol as _protocol
else:  # pragma: no cover - direct/installed script path
    import console
    import search_plan_advance as _advance_module
    import search_plan_archive as _archive
    import search_plan_projection as _projection
    import search_plan_protocol as _protocol

# Protocol compatibility exports.
MAX_INPUT_BYTES = _protocol.MAX_INPUT_BYTES
MAX_IDENTITY_CHARS = _protocol.MAX_IDENTITY_CHARS
MAX_DECIMAL_CHARS = _protocol.MAX_DECIMAL_CHARS
DECIMAL_RE = _protocol.DECIMAL_RE
SHA256_RE = _protocol.SHA256_RE
ProtocolError = _protocol.ProtocolError
POLICY_KEYS = _protocol.POLICY_KEYS
DIMENSION_KEYS = _protocol.DIMENSION_KEYS
FEEDBACK_KEYS = _protocol.FEEDBACK_KEYS
ADMITTED_KEYS = _protocol.ADMITTED_KEYS
INELIGIBLE_KEYS = _protocol.INELIGIBLE_KEYS
NO_CANDIDATE_KEYS = _protocol.NO_CANDIDATE_KEYS
PROJECTION_KEYS = _protocol.PROJECTION_KEYS
PLAN_KEYS = _protocol.PLAN_KEYS
SLOT_KEYS = _protocol.SLOT_KEYS
_canonical_bytes = _protocol._canonical_bytes
_tagged_identity = _protocol._tagged_identity
_identified = _protocol._identified
_reject_constant = _protocol._reject_constant
_reject_float = _protocol._reject_float
_closed = _protocol._closed
_string = _protocol._string
_integer = _protocol._integer
_unique_strings = _protocol._unique_strings
_decimal_string = _protocol._decimal_string
_load_request = _protocol._load_request
_validate_policy = _protocol._validate_policy
_validate_feedback = _protocol._validate_feedback
_validate_admitted = _protocol._validate_admitted
_validate_origin = _protocol._validate_origin
_validate_ineligible = _protocol._validate_ineligible
_validate_no_candidate = _protocol._validate_no_candidate
_validate_outcome = _protocol._validate_outcome

# Archive compatibility exports.
_decimal_parts = _archive._decimal_parts
_relation = _archive._relation
_vector = _archive._vector
_dominates = _archive._dominates
_pareto_archive = _archive._pareto_archive
_stable_key = _archive._stable_key

# Projection and proposal compatibility exports.
_validate_slot = _projection._validate_slot
_validate_plan = _projection._validate_plan
_validate_projection = _projection._validate_projection
_fits = _projection._fits
_reflection_slots = _projection._reflection_slots
_merge_pairs = _projection._merge_pairs
_merge_feedback = _projection._merge_feedback
_proposed_slots = _projection._proposed_slots

# Generation-advance compatibility exports.
_validate_remaining_bound = _advance_module._validate_remaining_bound
_pending_response = _advance_module._pending_response
_advance_later = _advance_module._advance_later
_advance_generation_zero = _advance_module._advance_generation_zero


def _advance(request):
    """Advance through the facade, preserving its replaceable identity seam."""
    _protocol._identified = _identified
    _projection._identified = _identified
    _advance_module._identified = _identified
    return _advance_module._advance(request)


def main(argv):
    console.harden()
    if argv != ["advance"]:
        sys.stderr.write("search-plan: expected advance\n")
        return 2
    try:
        request = _load_request(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
        response = _advance(request)
    except (ProtocolError, TypeError, ValueError, RecursionError):
        sys.stderr.write("search-plan: invalid request\n")
        return 2
    sys.stdout.buffer.write(_canonical_bytes(response) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(console.run(main, sys.argv[1:]))
