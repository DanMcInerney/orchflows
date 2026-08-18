"""Canonical bounded-search request parsing and protocol validation."""

import copy
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re

MAX_INPUT_BYTES = 1_000_000
MAX_IDENTITY_CHARS = 256
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
    if not isinstance(value, str) or not value or len(value) > MAX_IDENTITY_CHARS:
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
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ProtocolError("input is not one UTF-8 JSON object") from exc


POLICY_KEYS = {
    "schema",
    "identity",
    "planner_revision",
    "target_owner_identity",
    "mutation_surface_identities",
    "evaluation_identity",
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
    "evaluation_identity",
    "result_identity",
    "evidence_identity",
    "eligibility_status",
    "eligibility_verdict_identity",
    "score_card_identity",
    "dimension_vector",
    "feedback",
}
INELIGIBLE_KEYS = {
    "kind",
    "outcome_identity",
    "slot_identity",
    "cost",
    "candidate_identity",
    "parent_identities",
    "target_owner_identity",
    "mutation_surface_identities",
    "evaluation_identity",
    "result_identity",
    "evidence_identity",
    "eligibility_status",
    "eligibility_verdict_identity",
    "disposition",
}
NO_CANDIDATE_KEYS = {
    "kind",
    "outcome_identity",
    "slot_identity",
    "cost",
    "disposition",
}
PROJECTION_KEYS = {
    "schema",
    "identity",
    "policy_identity",
    "evaluation_identity",
    "last_settled_generation",
    "last_plan",
    "preferred_incumbent_identity",
    "nodes",
    "archive",
    "seen_slot_identities",
    "incorporated_outcome_identities",
}
PLAN_KEYS = {
    "schema",
    "identity",
    "policy_identity",
    "evaluation_identity",
    "input_projection_identity",
    "basis_outcome_identities",
    "generation",
    "slots",
}
SLOT_KEYS = {
    "identity",
    "generation",
    "ordinal",
    "kind",
    "parent_identities",
    "focus_dimension_identity",
    "complementary_dimension_identities",
    "feedback",
    "target_owner_identity",
    "mutation_surface_identities",
    "evaluation_identity",
    "reservation",
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
        "evaluation_identity",
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


def _validate_admitted(
    outcome,
    policy,
    surfaces,
    feedback_sources,
    dimension_ids,
    units,
    origin=False,
):
    _closed(outcome, ADMITTED_KEYS, "admitted outcome")
    if outcome["kind"] != "admitted":
        raise ProtocolError("outcome kind is invalid")
    if origin:
        if outcome["slot_identity"] is not None or outcome["parent_identities"] != []:
            raise ProtocolError("generation zero requires one admitted origin")
    else:
        _string(outcome["slot_identity"], "outcome slot")
        if not isinstance(outcome["parent_identities"], list) or len(
            outcome["parent_identities"]
        ) not in (1, 2):
            raise ProtocolError("produced candidate requires one or two parents")
        for parent in outcome["parent_identities"]:
            _string(parent, "outcome parent")
    for key in (
        "outcome_identity",
        "candidate_identity",
        "result_identity",
        "evidence_identity",
        "eligibility_verdict_identity",
        "score_card_identity",
    ):
        _string(outcome[key], "outcome." + key)
    if outcome["target_owner_identity"] != policy["target_owner_identity"]:
        raise ProtocolError("origin owner drift")
    if outcome["mutation_surface_identities"] != surfaces:
        raise ProtocolError("origin mutation-surface drift")
    if outcome["evaluation_identity"] != policy["evaluation_identity"]:
        raise ProtocolError("origin evaluation drift")
    if outcome["eligibility_status"] != "PASS":
        raise ProtocolError("origin must be covered PASS")
    _closed(outcome["cost"], units, "outcome cost")
    for unit in units:
        _integer(outcome["cost"][unit], "outcome cost")
    vector = outcome["dimension_vector"]
    if not isinstance(vector, list) or len(vector) != len(dimension_ids):
        raise ProtocolError("origin vector is incomplete")
    for index, entry in enumerate(vector):
        _closed(entry, {"identity", "value"}, "dimension-vector entry")
        if entry["identity"] != dimension_ids[index]:
            raise ProtocolError("origin vector order is invalid")
        _decimal_string(entry["value"], "dimension value")
    _validate_feedback(outcome["feedback"], feedback_sources, dimension_ids)


def _validate_origin(outcome, policy, surfaces, feedback_sources, dimension_ids, units):
    _validate_admitted(
        outcome,
        policy,
        surfaces,
        feedback_sources,
        dimension_ids,
        units,
        origin=True,
    )


def _validate_ineligible(outcome, policy, surfaces, units):
    _closed(outcome, INELIGIBLE_KEYS, "ineligible outcome")
    if outcome["kind"] != "ineligible":
        raise ProtocolError("outcome kind is invalid")
    for key in (
        "outcome_identity",
        "slot_identity",
        "candidate_identity",
        "result_identity",
        "evidence_identity",
        "eligibility_verdict_identity",
        "disposition",
    ):
        _string(outcome[key], "outcome." + key)
    parents = outcome["parent_identities"]
    if not isinstance(parents, list) or len(parents) not in (1, 2):
        raise ProtocolError("produced candidate requires one or two parents")
    for parent in parents:
        _string(parent, "outcome parent")
    if outcome["target_owner_identity"] != policy["target_owner_identity"]:
        raise ProtocolError("outcome owner drift")
    if outcome["mutation_surface_identities"] != surfaces:
        raise ProtocolError("outcome mutation-surface drift")
    if outcome["evaluation_identity"] != policy["evaluation_identity"]:
        raise ProtocolError("outcome evaluation drift")
    if outcome["eligibility_status"] not in ("FAIL", "UNVERIFIED"):
        raise ProtocolError("ineligible outcome must be covered non-PASS")
    _closed(outcome["cost"], units, "outcome cost")
    for unit in units:
        _integer(outcome["cost"][unit], "outcome cost")


def _validate_no_candidate(outcome, units):
    _closed(outcome, NO_CANDIDATE_KEYS, "no-candidate outcome")
    if outcome["kind"] != "no_candidate":
        raise ProtocolError("outcome kind is invalid")
    for key in ("outcome_identity", "slot_identity", "disposition"):
        _string(outcome[key], "outcome." + key)
    _closed(outcome["cost"], units, "outcome cost")
    for unit in units:
        _integer(outcome["cost"][unit], "outcome cost")


def _validate_outcome(
    outcome, policy, surfaces, feedback_sources, dimension_ids, units
):
    if not isinstance(outcome, dict):
        raise ProtocolError("outcome is not an object")
    if outcome.get("kind") == "admitted":
        _validate_admitted(
            outcome,
            policy,
            surfaces,
            feedback_sources,
            dimension_ids,
            units,
        )
    elif outcome.get("kind") == "ineligible":
        _validate_ineligible(outcome, policy, surfaces, units)
    elif outcome.get("kind") == "no_candidate":
        _validate_no_candidate(outcome, units)
    else:
        raise ProtocolError("outcome kind is invalid")
