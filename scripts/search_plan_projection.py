"""Projection validation and deterministic search-slot proposals."""

import copy

try:  # in-repo package import; installed scripts sit flat together
    from scripts.search_plan_archive import (
        _pareto_archive,
        _relation,
        _stable_key,
        _vector,
    )
    from scripts.search_plan_protocol import (
        PLAN_KEYS,
        PROJECTION_KEYS,
        SLOT_KEYS,
        ProtocolError,
        _closed,
        _identified,
        _integer,
        _string,
        _tagged_identity,
        _unique_strings,
        _validate_admitted,
        _validate_feedback,
        _validate_ineligible,
        _validate_origin,
    )
except ImportError:  # pragma: no cover - direct/installed script path
    from search_plan_archive import _pareto_archive, _relation, _stable_key, _vector
    from search_plan_protocol import (
        PLAN_KEYS,
        PROJECTION_KEYS,
        SLOT_KEYS,
        ProtocolError,
        _closed,
        _identified,
        _integer,
        _string,
        _tagged_identity,
        _unique_strings,
        _validate_admitted,
        _validate_feedback,
        _validate_ineligible,
        _validate_origin,
    )

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
        complementary = slot["complementary_dimension_identities"]
        if (
            not isinstance(complementary, list)
            or not complementary
            or len(complementary) != len(set(complementary))
            or any(item not in dimension_ids for item in complementary)
        ):
            raise ProtocolError("merge complementary dimensions are invalid")
    else:
        raise ProtocolError("slot kind is invalid")
    _validate_feedback(slot["feedback"], feedback_sources, dimension_ids)
    if slot["target_owner_identity"] != policy["target_owner_identity"]:
        raise ProtocolError("slot owner drift")
    if slot["mutation_surface_identities"] != surfaces:
        raise ProtocolError("slot mutation-surface drift")
    if slot["evaluation_identity"] != policy["evaluation_identity"]:
        raise ProtocolError("slot evaluation drift")
    _closed(slot["reservation"], units, "slot reservation")
    for unit in units:
        _integer(slot["reservation"][unit], "slot reservation")
    if slot["reservation"] != policy["reservations"][slot["kind"]]:
        raise ProtocolError("slot reservation drifts from policy")


def _validate_plan(plan, policy, surfaces, feedback_sources, dimension_ids, units):
    _closed(plan, PLAN_KEYS, "plan")
    payload = {key: value for key, value in plan.items() if key != "identity"}
    if plan["identity"] != _tagged_identity("search-plan/v1", payload):
        raise ProtocolError("plan identity mismatch")
    if plan["schema"] != "search-plan/v1":
        raise ProtocolError("plan schema is invalid")
    if plan["policy_identity"] != policy["identity"]:
        raise ProtocolError("plan policy drift")
    if plan["evaluation_identity"] != policy["evaluation_identity"]:
        raise ProtocolError("plan evaluation drift")
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
    if projection["evaluation_identity"] != policy["evaluation_identity"]:
        raise ProtocolError("projection evaluation drift")
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
        if index == 0:
            _validate_origin(
                node, policy, surfaces, feedback_sources, dimension_ids, units
            )
        elif isinstance(node, dict) and node.get("kind") == "admitted":
            _validate_admitted(
                node,
                policy,
                surfaces,
                feedback_sources,
                dimension_ids,
                units,
            )
        else:
            _validate_ineligible(node, policy, surfaces, units)
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
    admitted_candidates = {
        node["candidate_identity"] for node in nodes if node["kind"] == "admitted"
    }
    preferred = _string(
        projection["preferred_incumbent_identity"], "preferred incumbent"
    )
    if preferred not in admitted_candidates:
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
    if plan is not None:
        if any(
            parent not in admitted_candidates
            for slot in plan["slots"]
            for parent in slot["parent_identities"]
        ):
            raise ProtocolError("plan parent is not admitted")
        if any(slot["identity"] not in seen_slots for slot in plan["slots"]):
            raise ProtocolError("open plan is absent from seen slots")
        proposals = _proposed_slots(
            policy,
            nodes,
            archive,
            preferred,
            plan["generation"],
        )
        for slot in plan["slots"]:
            try:
                expected = next(proposals)
            except StopIteration as exc:
                raise ProtocolError("open plan is not a proposal prefix") from exc
            if slot != expected:
                raise ProtocolError("open plan is not a proposal prefix")
    return nodes, candidates


def _fits(spent, reservation, remaining):
    return all(spent[unit] + reservation[unit] <= remaining[unit] for unit in spent)


def _reflection_slots(
    policy, nodes, archive, preferred, start_ordinal, count, generation
):
    by_candidate = {node["candidate_identity"]: node for node in nodes}
    remaining = [candidate for candidate in archive if candidate != preferred]
    remaining.sort(key=lambda candidate: _stable_key(policy["ordering_seed"], candidate))
    parents = [preferred] + remaining
    for ordinal in range(start_ordinal, start_ordinal + count):
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
        focus_index = generation - 1 + ordinal // len(parents)
        focus = focus_pool[focus_index % len(focus_pool)]
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
            "evaluation_identity": policy["evaluation_identity"],
            "reservation": copy.deepcopy(policy["reservations"]["reflect"]),
        }
        yield _identified("search-slot/v1", payload)


def _merge_pairs(policy, nodes, archive):
    by_candidate = {node["candidate_identity"]: node for node in nodes}
    ordered = sorted(
        archive,
        key=lambda candidate: _stable_key(policy["ordering_seed"], candidate),
    )
    pairs = []
    for left_index, left_identity in enumerate(ordered):
        left = by_candidate[left_identity]
        for right_identity in ordered[left_index + 1 :]:
            right = by_candidate[right_identity]
            if (
                left["target_owner_identity"] != right["target_owner_identity"]
                or left["mutation_surface_identities"]
                != right["mutation_surface_identities"]
            ):
                continue
            relations = []
            for dimension in policy["dimensions"]:
                dimension_id = dimension["identity"]
                relations.append(
                    _relation(
                        _vector(left)[dimension_id],
                        _vector(right)[dimension_id],
                        dimension["resolution"],
                        dimension["direction"],
                    )
                )
            if 1 in relations and -1 in relations:
                pairs.append((left_identity, right_identity, relations))
    pairs.sort(
        key=lambda item: _stable_key(policy["ordering_seed"], item[0], item[1])
    )
    return pairs


def _merge_feedback(policy, left, right, relations):
    source_order = {
        source: index
        for index, source in enumerate(policy["feedback_source_identities"])
    }
    feedback = []
    for parent, wanted_relation in ((left, 1), (right, -1)):
        for dimension, relation in zip(policy["dimensions"], relations):
            if relation != wanted_relation:
                continue
            matching = [
                copy.deepcopy(item)
                for item in parent["feedback"]
                if item["dimension_identity"] == dimension["identity"]
            ]
            matching.sort(
                key=lambda item: (
                    source_order[item["source_identity"]],
                    item["reference_identity"],
                )
            )
            feedback.extend(matching)
    return feedback


def _proposed_slots(policy, nodes, archive, preferred, generation):
    by_candidate = {node["candidate_identity"]: node for node in nodes}
    minimum_reflection_count = policy["generation_width"] - policy["merge_slots"]
    yield from _reflection_slots(
        policy,
        nodes,
        archive,
        preferred,
        0,
        minimum_reflection_count,
        generation,
    )
    pairs = _merge_pairs(policy, nodes, archive)
    merge_count = min(policy["merge_slots"], len(pairs))
    reflection_count = policy["generation_width"] - merge_count
    yield from _reflection_slots(
        policy,
        nodes,
        archive,
        preferred,
        minimum_reflection_count,
        reflection_count - minimum_reflection_count,
        generation,
    )
    for pair_index in range(merge_count):
        left_identity, right_identity, relations = pairs[pair_index]
        complementary = [
            dimension["identity"]
            for dimension, relation in zip(policy["dimensions"], relations)
            if relation != 0
        ]
        payload = {
            "generation": generation,
            "ordinal": reflection_count + pair_index,
            "kind": "merge",
            "parent_identities": [left_identity, right_identity],
            "focus_dimension_identity": None,
            "complementary_dimension_identities": complementary,
            "feedback": _merge_feedback(
                policy,
                by_candidate[left_identity],
                by_candidate[right_identity],
                relations,
            ),
            "target_owner_identity": policy["target_owner_identity"],
            "mutation_surface_identities": copy.deepcopy(
                policy["mutation_surface_identities"]
            ),
            "evaluation_identity": policy["evaluation_identity"],
            "reservation": copy.deepcopy(policy["reservations"]["merge"]),
        }
        yield _identified("search-slot/v1", payload)
