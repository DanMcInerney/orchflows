#!/usr/bin/env python3
"""Pure canonical search-plan transformation."""

import copy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
import sys


MAX_INPUT_BYTES = 1_000_000
MAX_DECIMAL_CHARS = 128
DECIMAL_RE = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?\Z")
SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}\Z")


class ProtocolError(ValueError):
    pass


def _canonical_bytes(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def _tagged_identity(tag, payload):
    digest = hashlib.sha256(tag.encode("utf-8") + b"\0" + _canonical_bytes(payload))
    return "sha256:" + digest.hexdigest()


def _identified(tag, payload):
    value = copy.deepcopy(payload)
    value["identity"] = _tagged_identity(tag, payload)
    return value


def _reject_constant(_value):
    raise ProtocolError("noncanonical number")


def _reject_float(_value):
    raise ProtocolError("numbers requiring decimal syntax must be strings")


def _closed(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ProtocolError(label + " is not a closed object")


def _string(value, label):
    if not isinstance(value, str) or not value or len(value) > 256:
        raise ProtocolError(label + " must be a bounded identity string")
    return value


def _integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        raise ProtocolError(label + " must be a nonnegative integer")
    return value


def _unique_strings(value, label, allow_empty=False):
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ProtocolError(label + " must be an ordered identity list")
    result = [_string(item, label) for item in value]
    if len(result) != len(set(result)):
        raise ProtocolError(label + " contains duplicates")
    return result


def _decimal_string(value, label, positive=False):
    if (
        not isinstance(value, str)
        or len(value) > MAX_DECIMAL_CHARS
        or DECIMAL_RE.fullmatch(value) is None
    ):
        raise ProtocolError(label + " must be a canonical decimal string")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ProtocolError(label + " is not finite") from exc
    if number == 0 and value.startswith("-"):
        raise ProtocolError(label + " must not be negative zero")
    if positive and number <= 0:
        raise ProtocolError(label + " must be positive")
    return value


def _load_request(raw):
    if len(raw) > MAX_INPUT_BYTES:
        raise ProtocolError("input exceeds bound")

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ProtocolError("duplicate object key")
            result[key] = value
        return result

    try:
        text = raw.decode("utf-8")
        return json.loads(
            text,
            object_pairs_hook=pairs,
            parse_float=_reject_float,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError("input is not one UTF-8 JSON object") from exc


POLICY_KEYS = {
    "schema",
    "identity",
    "planner_revision",
    "target_owner_identity",
    "mutation_surface_identities",
    "benchmark_revision",
    "scoring_identity",
    "dimensions",
    "feedback_source_identities",
    "ordering_seed",
    "generation_width",
    "merge_slots",
    "bound_unit_names",
    "reservations",
}
DIMENSION_KEYS = {"identity", "direction", "source_identity", "resolution"}
FEEDBACK_KEYS = {"source_identity", "dimension_identity", "reference_identity"}
ADMITTED_KEYS = {
    "kind",
    "outcome_identity",
    "slot_identity",
    "cost",
    "candidate_identity",
    "parent_identities",
    "target_owner_identity",
    "mutation_surface_identities",
    "benchmark_revision",
    "result_identity",
    "evidence_identity",
    "eligibility_status",
    "eligibility_verdict_identity",
    "score_card_identity",
    "dimension_vector",
    "feedback",
}


def _validate_policy(policy):
    _closed(policy, POLICY_KEYS, "policy")
    if policy["schema"] != "search-policy/v1":
        raise ProtocolError("unsupported policy schema")
    if not SHA256_RE.fullmatch(policy["identity"]):
        raise ProtocolError("policy identity is malformed")
    payload = {key: value for key, value in policy.items() if key != "identity"}
    if policy["identity"] != _tagged_identity("search-policy/v1", payload):
        raise ProtocolError("policy identity mismatch")
    for key in (
        "planner_revision",
        "target_owner_identity",
        "benchmark_revision",
        "scoring_identity",
        "ordering_seed",
    ):
        _string(policy[key], "policy." + key)
    surfaces = _unique_strings(
        policy["mutation_surface_identities"], "mutation surfaces"
    )
    feedback_sources = _unique_strings(
        policy["feedback_source_identities"],
        "feedback sources",
        allow_empty=True,
    )
    if not isinstance(policy["dimensions"], list) or not policy["dimensions"]:
        raise ProtocolError("dimensions must be a nonempty ordered list")
    dimension_ids = []
    for dimension in policy["dimensions"]:
        _closed(dimension, DIMENSION_KEYS, "dimension")
        dimension_ids.append(_string(dimension["identity"], "dimension identity"))
        if dimension["direction"] not in ("maximize", "minimize"):
            raise ProtocolError("dimension direction is invalid")
        _string(dimension["source_identity"], "dimension source")
        _decimal_string(dimension["resolution"], "dimension resolution", positive=True)
    if len(dimension_ids) != len(set(dimension_ids)):
        raise ProtocolError("dimension identities contain duplicates")
    width = _integer(policy["generation_width"], "generation width", minimum=1)
    merge_slots = _integer(policy["merge_slots"], "merge slots")
    if merge_slots > width:
        raise ProtocolError("merge slots exceed generation width")
    bound_units = _unique_strings(policy["bound_unit_names"], "bound units")
    _closed(policy["reservations"], {"reflect", "merge"}, "reservations")
    for kind in ("reflect", "merge"):
        _closed(policy["reservations"][kind], bound_units, kind + " reservation")
        for unit in bound_units:
            _integer(policy["reservations"][kind][unit], kind + " reservation")
    return surfaces, feedback_sources, dimension_ids, bound_units


def _validate_feedback(feedback, allowed_sources, dimension_ids):
    if not isinstance(feedback, list):
        raise ProtocolError("feedback must be an ordered list")
    seen = set()
    for item in feedback:
        _closed(item, FEEDBACK_KEYS, "feedback reference")
        source = _string(item["source_identity"], "feedback source")
        dimension = _string(item["dimension_identity"], "feedback dimension")
        reference = _string(item["reference_identity"], "feedback reference")
        if source not in allowed_sources or dimension not in dimension_ids:
            raise ProtocolError("feedback reference is not allowed")
        identity = (source, dimension, reference)
        if identity in seen:
            raise ProtocolError("feedback contains duplicates")
        seen.add(identity)


def _validate_origin(outcome, policy, surfaces, feedback_sources, dimension_ids, units):
    _closed(outcome, ADMITTED_KEYS, "generation-zero outcome")
    if outcome["kind"] != "admitted" or outcome["slot_identity"] is not None:
        raise ProtocolError("generation zero requires one admitted origin")
    for key in (
        "outcome_identity",
        "candidate_identity",
        "result_identity",
        "evidence_identity",
        "eligibility_verdict_identity",
        "score_card_identity",
    ):
        _string(outcome[key], "origin." + key)
    if outcome["parent_identities"] != []:
        raise ProtocolError("origin must have no parents")
    if outcome["target_owner_identity"] != policy["target_owner_identity"]:
        raise ProtocolError("origin owner drift")
    if outcome["mutation_surface_identities"] != surfaces:
        raise ProtocolError("origin mutation-surface drift")
    if outcome["benchmark_revision"] != policy["benchmark_revision"]:
        raise ProtocolError("origin benchmark drift")
    if outcome["eligibility_status"] != "PASS":
        raise ProtocolError("origin must be covered PASS")
    _closed(outcome["cost"], units, "origin cost")
    for unit in units:
        _integer(outcome["cost"][unit], "origin cost")
    vector = outcome["dimension_vector"]
    if not isinstance(vector, list) or len(vector) != len(dimension_ids):
        raise ProtocolError("origin vector is incomplete")
    for index, entry in enumerate(vector):
        _closed(entry, {"identity", "value"}, "dimension-vector entry")
        if entry["identity"] != dimension_ids[index]:
            raise ProtocolError("origin vector order is invalid")
        _decimal_string(entry["value"], "dimension value")
    _validate_feedback(outcome["feedback"], feedback_sources, dimension_ids)


def _fits(spent, reservation, remaining):
    return all(spent[unit] + reservation[unit] <= remaining[unit] for unit in spent)


def _advance_generation_zero(request):
    _closed(request, {"policy", "projection", "settled", "remaining_bound"}, "request")
    policy = request["policy"]
    surfaces, feedback_sources, dimension_ids, units = _validate_policy(policy)
    if request["projection"] is not None:
        raise ProtocolError("this planner revision requires a generation-zero projection")
    _closed(
        request["settled"],
        {"preferred_incumbent_identity", "outcomes"},
        "settled",
    )
    preferred = _string(
        request["settled"]["preferred_incumbent_identity"],
        "preferred incumbent",
    )
    outcomes = request["settled"]["outcomes"]
    if not isinstance(outcomes, list) or len(outcomes) != 1:
        raise ProtocolError("generation zero requires exactly one origin")
    origin = outcomes[0]
    _validate_origin(
        origin,
        policy,
        surfaces,
        feedback_sources,
        dimension_ids,
        units,
    )
    if preferred != origin["candidate_identity"]:
        raise ProtocolError("preferred incumbent does not name the origin")
    _closed(request["remaining_bound"], units, "remaining bound")
    remaining = request["remaining_bound"]
    for unit in units:
        _integer(remaining[unit], "remaining bound")

    reservation = policy["reservations"]["reflect"]
    spent = {unit: 0 for unit in units}
    slots = []
    for ordinal in range(policy["generation_width"]):
        if not _fits(spent, reservation, remaining):
            break
        focus = dimension_ids[ordinal % len(dimension_ids)]
        feedback = [
            copy.deepcopy(item)
            for item in origin["feedback"]
            if item["dimension_identity"] == focus
        ]
        slot_payload = {
            "generation": 1,
            "ordinal": ordinal,
            "kind": "reflect",
            "parent_identities": [origin["candidate_identity"]],
            "focus_dimension_identity": focus,
            "complementary_dimension_identities": [],
            "feedback": feedback,
            "target_owner_identity": policy["target_owner_identity"],
            "mutation_surface_identities": copy.deepcopy(surfaces),
            "benchmark_revision": policy["benchmark_revision"],
            "reservation": copy.deepcopy(reservation),
        }
        slots.append(_identified("search-slot/v1", slot_payload))
        for unit in units:
            spent[unit] += reservation[unit]

    plan = None
    if slots:
        plan = _identified(
            "search-plan/v1",
            {
                "schema": "search-plan/v1",
                "policy_identity": policy["identity"],
                "benchmark_revision": policy["benchmark_revision"],
                "input_projection_identity": None,
                "basis_outcome_identities": [origin["outcome_identity"]],
                "generation": 1,
                "slots": slots,
            },
        )
    projection = _identified(
        "search-projection/v1",
        {
            "schema": "search-projection/v1",
            "policy_identity": policy["identity"],
            "benchmark_revision": policy["benchmark_revision"],
            "last_settled_generation": 0,
            "last_plan": plan,
            "preferred_incumbent_identity": preferred,
            "nodes": [copy.deepcopy(origin)],
            "archive": [origin["candidate_identity"]],
            "seen_slot_identities": [slot["identity"] for slot in slots],
            "incorporated_outcome_identities": [origin["outcome_identity"]],
        },
    )
    return {
        "schema": "search-advance/v1",
        "status": "planned" if plan is not None else "no_fit",
        "input_projection_identity": None,
        "output_projection_identity": projection["identity"],
        "projection": projection,
        "plan": plan,
        "missing_slot_identities": [],
        "diagnostics": [],
    }


def main(argv):
    if argv != ["advance"]:
        sys.stderr.write("search-plan: expected advance\n")
        return 2
    try:
        request = _load_request(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
        response = _advance_generation_zero(request)
    except (ProtocolError, TypeError, ValueError):
        sys.stderr.write("search-plan: invalid request\n")
        return 2
    sys.stdout.buffer.write(_canonical_bytes(response) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
