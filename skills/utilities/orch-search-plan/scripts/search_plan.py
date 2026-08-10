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
PROJECTION_KEYS = {
    "schema",
    "identity",
    "policy_identity",
    "benchmark_revision",
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
    "benchmark_revision",
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
    "benchmark_revision",
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
    if outcome["benchmark_revision"] != policy["benchmark_revision"]:
        raise ProtocolError("origin benchmark drift")
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


def _decimal_parts(value):
    negative = value.startswith("-")
    unsigned = value[1:] if negative else value
    if "." in unsigned:
        whole, fraction = unsigned.split(".", 1)
    else:
        whole, fraction = unsigned, ""
    coefficient = int(whole + fraction)
    return (-coefficient if negative else coefficient), len(fraction)


def _relation(left, right, resolution, direction):
    left_coefficient, left_scale = _decimal_parts(left)
    right_coefficient, right_scale = _decimal_parts(right)
    resolution_coefficient, resolution_scale = _decimal_parts(resolution)
    scale = max(left_scale, right_scale, resolution_scale)
    delta = left_coefficient * 10 ** (scale - left_scale)
    delta -= right_coefficient * 10 ** (scale - right_scale)
    if direction == "minimize":
        delta = -delta
    threshold = resolution_coefficient * 10 ** (scale - resolution_scale)
    if delta >= threshold:
        return 1
    if delta <= -threshold:
        return -1
    return 0


def _vector(node):
    return {item["identity"]: item["value"] for item in node["dimension_vector"]}


def _dominates(left, right, dimensions):
    left_vector = _vector(left)
    right_vector = _vector(right)
    relations = [
        _relation(
            left_vector[dimension["identity"]],
            right_vector[dimension["identity"]],
            dimension["resolution"],
            dimension["direction"],
        )
        for dimension in dimensions
    ]
    return 1 in relations and -1 not in relations


def _pareto_archive(nodes, dimensions):
    admitted = [node for node in nodes if node["kind"] == "admitted"]
    return [
        node["candidate_identity"]
        for node in admitted
        if not any(
            other is not node and _dominates(other, node, dimensions)
            for other in admitted
        )
    ]


def _stable_key(seed, *identities):
    material = "\0".join((seed,) + identities).encode("utf-8")
    return hashlib.sha256(material).hexdigest(), identities


def _validate_slot(slot, policy, surfaces, feedback_sources, dimension_ids, units):
    _closed(slot, SLOT_KEYS, "plan slot")
    payload = {key: value for key, value in slot.items() if key != "identity"}
    if slot["identity"] != _tagged_identity("search-slot/v1", payload):
        raise ProtocolError("slot identity mismatch")
    _integer(slot["generation"], "slot generation", minimum=1)
    _integer(slot["ordinal"], "slot ordinal")
    parents = _unique_strings(slot["parent_identities"], "slot parents")
    if slot["kind"] == "reflect":
        if len(parents) != 1 or slot["focus_dimension_identity"] not in dimension_ids:
            raise ProtocolError("reflection slot is invalid")
        if slot["complementary_dimension_identities"] != []:
            raise ProtocolError("reflection cannot carry complementary dimensions")
    elif slot["kind"] == "merge":
        if len(parents) != 2 or slot["focus_dimension_identity"] is not None:
            raise ProtocolError("merge slot is invalid")
    else:
        raise ProtocolError("slot kind is invalid")
    _validate_feedback(slot["feedback"], feedback_sources, dimension_ids)
    if slot["target_owner_identity"] != policy["target_owner_identity"]:
        raise ProtocolError("slot owner drift")
    if slot["mutation_surface_identities"] != surfaces:
        raise ProtocolError("slot mutation-surface drift")
    if slot["benchmark_revision"] != policy["benchmark_revision"]:
        raise ProtocolError("slot benchmark drift")
    _closed(slot["reservation"], units, "slot reservation")
    for unit in units:
        _integer(slot["reservation"][unit], "slot reservation")


def _validate_plan(plan, policy, surfaces, feedback_sources, dimension_ids, units):
    _closed(plan, PLAN_KEYS, "plan")
    payload = {key: value for key, value in plan.items() if key != "identity"}
    if plan["identity"] != _tagged_identity("search-plan/v1", payload):
        raise ProtocolError("plan identity mismatch")
    if plan["schema"] != "search-plan/v1":
        raise ProtocolError("plan schema is invalid")
    if plan["policy_identity"] != policy["identity"]:
        raise ProtocolError("plan policy drift")
    if plan["benchmark_revision"] != policy["benchmark_revision"]:
        raise ProtocolError("plan benchmark drift")
    if plan["input_projection_identity"] is not None:
        _string(plan["input_projection_identity"], "plan input projection")
    _unique_strings(plan["basis_outcome_identities"], "plan outcomes")
    generation = _integer(plan["generation"], "plan generation", minimum=1)
    if not isinstance(plan["slots"], list) or not plan["slots"]:
        raise ProtocolError("plan slots must be nonempty")
    for ordinal, slot in enumerate(plan["slots"]):
        _validate_slot(
            slot, policy, surfaces, feedback_sources, dimension_ids, units
        )
        if slot["generation"] != generation or slot["ordinal"] != ordinal:
            raise ProtocolError("slot position is invalid")


def _validate_projection(
    projection, policy, surfaces, feedback_sources, dimension_ids, units
):
    _closed(projection, PROJECTION_KEYS, "projection")
    payload = {key: value for key, value in projection.items() if key != "identity"}
    if projection["identity"] != _tagged_identity("search-projection/v1", payload):
        raise ProtocolError("projection identity mismatch")
    if projection["schema"] != "search-projection/v1":
        raise ProtocolError("projection schema is invalid")
    if projection["policy_identity"] != policy["identity"]:
        raise ProtocolError("projection policy drift")
    if projection["benchmark_revision"] != policy["benchmark_revision"]:
        raise ProtocolError("projection benchmark drift")
    settled_generation = _integer(
        projection["last_settled_generation"], "settled generation"
    )
    plan = projection["last_plan"]
    if plan is not None:
        _validate_plan(
            plan, policy, surfaces, feedback_sources, dimension_ids, units
        )
        if plan["generation"] != settled_generation + 1:
            raise ProtocolError("projection generation is inconsistent")
    nodes = projection["nodes"]
    if not isinstance(nodes, list) or not nodes:
        raise ProtocolError("projection nodes must be complete")
    candidates = set()
    outcomes = set()
    for index, node in enumerate(nodes):
        _validate_admitted(
            node,
            policy,
            surfaces,
            feedback_sources,
            dimension_ids,
            units,
            origin=index == 0,
        )
        candidate = node["candidate_identity"]
        if candidate in candidates or node["outcome_identity"] in outcomes:
            raise ProtocolError("projection node identity is duplicated")
        if index and any(parent not in candidates for parent in node["parent_identities"]):
            raise ProtocolError("projection lineage is cyclic or dangling")
        candidates.add(candidate)
        outcomes.add(node["outcome_identity"])
    archive = _unique_strings(projection["archive"], "projection archive")
    if archive != _pareto_archive(nodes, policy["dimensions"]):
        raise ProtocolError("projection archive is incomplete")
    preferred = _string(
        projection["preferred_incumbent_identity"], "preferred incumbent"
    )
    if preferred not in candidates:
        raise ProtocolError("preferred incumbent is not admitted")
    seen_slots = _unique_strings(
        projection["seen_slot_identities"], "seen slots", allow_empty=True
    )
    incorporated = _unique_strings(
        projection["incorporated_outcome_identities"],
        "incorporated outcomes",
    )
    if not outcomes.issubset(set(incorporated)):
        raise ProtocolError("projection outcomes are incomplete")
    if any(
        node["slot_identity"] is not None
        and node["slot_identity"] not in seen_slots
        for node in nodes
    ):
        raise ProtocolError("projection slot lineage is incomplete")
    return nodes, candidates


def _fits(spent, reservation, remaining):
    return all(spent[unit] + reservation[unit] <= remaining[unit] for unit in spent)


def _reflection_slots(policy, nodes, archive, preferred, count, generation):
    by_candidate = {node["candidate_identity"]: node for node in nodes}
    remaining = [candidate for candidate in archive if candidate != preferred]
    remaining.sort(key=lambda candidate: _stable_key(policy["ordering_seed"], candidate))
    parents = [preferred] + remaining
    slots = []
    uses = {candidate: 0 for candidate in parents}
    for ordinal in range(count):
        parent_identity = parents[ordinal % len(parents)]
        parent = by_candidate[parent_identity]
        parent_vector = _vector(parent)
        trailing = []
        for dimension in policy["dimensions"]:
            dimension_id = dimension["identity"]
            if any(
                _relation(
                    _vector(by_candidate[other])[dimension_id],
                    parent_vector[dimension_id],
                    dimension["resolution"],
                    dimension["direction"],
                )
                == 1
                for other in archive
            ):
                trailing.append(dimension_id)
        focus_pool = trailing or [item["identity"] for item in policy["dimensions"]]
        focus = focus_pool[uses[parent_identity] % len(focus_pool)]
        uses[parent_identity] += 1
        feedback = [
            copy.deepcopy(item)
            for item in parent["feedback"]
            if item["dimension_identity"] == focus
        ]
        payload = {
            "generation": generation,
            "ordinal": ordinal,
            "kind": "reflect",
            "parent_identities": [parent_identity],
            "focus_dimension_identity": focus,
            "complementary_dimension_identities": [],
            "feedback": feedback,
            "target_owner_identity": policy["target_owner_identity"],
            "mutation_surface_identities": copy.deepcopy(
                policy["mutation_surface_identities"]
            ),
            "benchmark_revision": policy["benchmark_revision"],
            "reservation": copy.deepcopy(policy["reservations"]["reflect"]),
        }
        slots.append(_identified("search-slot/v1", payload))
    return slots


def _pending_response(projection, missing):
    return {
        "schema": "search-advance/v1",
        "status": "pending",
        "input_projection_identity": projection["identity"],
        "output_projection_identity": projection["identity"],
        "projection": copy.deepcopy(projection),
        "plan": None,
        "missing_slot_identities": missing,
        "diagnostics": [],
    }


def _advance_later(request, policy, surfaces, feedback_sources, dimension_ids, units):
    projection = request["projection"]
    nodes, candidates = _validate_projection(
        projection, policy, surfaces, feedback_sources, dimension_ids, units
    )
    prior_plan = projection["last_plan"]
    if prior_plan is None:
        raise ProtocolError("projection has no open plan")
    _closed(request["settled"], {"preferred_incumbent_identity", "outcomes"}, "settled")
    preferred = _string(
        request["settled"]["preferred_incumbent_identity"], "preferred incumbent"
    )
    outcomes = request["settled"]["outcomes"]
    if not isinstance(outcomes, list):
        raise ProtocolError("settled outcomes must be a list")
    slots = {slot["identity"]: slot for slot in prior_plan["slots"]}
    by_slot = {}
    seen_candidates = set(candidates)
    incorporated = set(projection["incorporated_outcome_identities"])
    for outcome in outcomes:
        _validate_admitted(
            outcome,
            policy,
            surfaces,
            feedback_sources,
            dimension_ids,
            units,
        )
        slot_identity = outcome["slot_identity"]
        if slot_identity not in slots or slot_identity in by_slot:
            raise ProtocolError("settled slot is extra or duplicated")
        slot = slots[slot_identity]
        if outcome["parent_identities"] != slot["parent_identities"]:
            raise ProtocolError("settled lineage does not match the plan")
        if outcome["candidate_identity"] in seen_candidates:
            raise ProtocolError("produced candidate identity is reused")
        if outcome["outcome_identity"] in incorporated:
            raise ProtocolError("outcome identity is reused")
        seen_candidates.add(outcome["candidate_identity"])
        incorporated.add(outcome["outcome_identity"])
        by_slot[slot_identity] = outcome
    missing = [slot["identity"] for slot in prior_plan["slots"] if slot["identity"] not in by_slot]
    if missing:
        return _pending_response(projection, missing)
    normalized_outcomes = [by_slot[slot["identity"]] for slot in prior_plan["slots"]]
    updated_nodes = copy.deepcopy(nodes) + copy.deepcopy(normalized_outcomes)
    admitted_candidates = {
        node["candidate_identity"]
        for node in updated_nodes
        if node["kind"] == "admitted"
    }
    if preferred not in admitted_candidates:
        raise ProtocolError("preferred incumbent is not admitted")
    archive = _pareto_archive(updated_nodes, policy["dimensions"])

    _closed(request["remaining_bound"], units, "remaining bound")
    remaining_bound = request["remaining_bound"]
    for unit in units:
        _integer(remaining_bound[unit], "remaining bound")
    generation = prior_plan["generation"] + 1
    proposed = _reflection_slots(
        policy,
        updated_nodes,
        archive,
        preferred,
        policy["generation_width"],
        generation,
    )
    spent = {unit: 0 for unit in units}
    fitting = []
    for slot in proposed:
        if not _fits(spent, slot["reservation"], remaining_bound):
            break
        fitting.append(slot)
        for unit in units:
            spent[unit] += slot["reservation"][unit]
    next_plan = None
    if fitting:
        next_plan = _identified(
            "search-plan/v1",
            {
                "schema": "search-plan/v1",
                "policy_identity": policy["identity"],
                "benchmark_revision": policy["benchmark_revision"],
                "input_projection_identity": projection["identity"],
                "basis_outcome_identities": [
                    outcome["outcome_identity"] for outcome in normalized_outcomes
                ],
                "generation": generation,
                "slots": fitting,
            },
        )
    output_projection = _identified(
        "search-projection/v1",
        {
            "schema": "search-projection/v1",
            "policy_identity": policy["identity"],
            "benchmark_revision": policy["benchmark_revision"],
            "last_settled_generation": prior_plan["generation"],
            "last_plan": next_plan,
            "preferred_incumbent_identity": preferred,
            "nodes": updated_nodes,
            "archive": archive,
            "seen_slot_identities": projection["seen_slot_identities"]
            + [slot["identity"] for slot in fitting],
            "incorporated_outcome_identities": projection[
                "incorporated_outcome_identities"
            ]
            + [outcome["outcome_identity"] for outcome in normalized_outcomes],
        },
    )
    return {
        "schema": "search-advance/v1",
        "status": "planned" if next_plan is not None else "no_fit",
        "input_projection_identity": projection["identity"],
        "output_projection_identity": output_projection["identity"],
        "projection": output_projection,
        "plan": next_plan,
        "missing_slot_identities": [],
        "diagnostics": [],
    }


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


def _advance(request):
    _closed(request, {"policy", "projection", "settled", "remaining_bound"}, "request")
    if request["projection"] is None:
        return _advance_generation_zero(request)
    policy = request["policy"]
    surfaces, feedback_sources, dimension_ids, units = _validate_policy(policy)
    return _advance_later(
        request, policy, surfaces, feedback_sources, dimension_ids, units
    )


def main(argv):
    if argv != ["advance"]:
        sys.stderr.write("search-plan: expected advance\n")
        return 2
    try:
        request = _load_request(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
        response = _advance(request)
    except (ProtocolError, TypeError, ValueError):
        sys.stderr.write("search-plan: invalid request\n")
        return 2
    sys.stdout.buffer.write(_canonical_bytes(response) + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
