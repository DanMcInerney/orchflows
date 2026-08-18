"""Generation advance over a validated bounded-search projection."""

import copy

if __package__:  # in-repo package import; installed scripts sit flat together
    from scripts.search_plan_archive import _pareto_archive
    from scripts.search_plan_projection import (
        _fits,
        _proposed_slots,
        _validate_projection,
    )
    from scripts.search_plan_protocol import (
        ProtocolError,
        _closed,
        _identified,
        _integer,
        _string,
        _validate_origin,
        _validate_outcome,
        _validate_policy,
    )
else:  # pragma: no cover - direct/installed script path
    from search_plan_archive import _pareto_archive
    from search_plan_projection import _fits, _proposed_slots, _validate_projection
    from search_plan_protocol import (
        ProtocolError,
        _closed,
        _identified,
        _integer,
        _string,
        _validate_origin,
        _validate_outcome,
        _validate_policy,
    )

def _validate_remaining_bound(value, units):
    _closed(value, units, "remaining bound")
    for unit in units:
        _integer(value[unit], "remaining bound")
    return value


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
    remaining_bound = _validate_remaining_bound(request["remaining_bound"], units)
    slots = {slot["identity"]: slot for slot in prior_plan["slots"]}
    by_slot = {}
    seen_candidates = set(candidates)
    incorporated = set(projection["incorporated_outcome_identities"])
    fresh_fields = (
        "candidate_identity",
        "result_identity",
        "evidence_identity",
        "eligibility_verdict_identity",
    )
    used_fresh = {
        field: {node[field] for node in nodes}
        for field in fresh_fields
    }
    used_scores = {
        node["score_card_identity"]
        for node in nodes
        if node["kind"] == "admitted"
    }
    for outcome in outcomes:
        _validate_outcome(
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
        if outcome["kind"] != "no_candidate":
            if outcome["parent_identities"] != slot["parent_identities"]:
                raise ProtocolError("settled lineage does not match the plan")
            if outcome["candidate_identity"] in seen_candidates:
                raise ProtocolError("produced candidate identity is reused")
            for field in fresh_fields:
                if outcome[field] in used_fresh[field]:
                    raise ProtocolError("produced result identity is reused")
                used_fresh[field].add(outcome[field])
            if outcome["kind"] == "admitted":
                if outcome["score_card_identity"] in used_scores:
                    raise ProtocolError("score-card identity is reused")
                used_scores.add(outcome["score_card_identity"])
            seen_candidates.add(outcome["candidate_identity"])
        if outcome["outcome_identity"] in incorporated:
            raise ProtocolError("outcome identity is reused")
        incorporated.add(outcome["outcome_identity"])
        by_slot[slot_identity] = outcome
    missing = [slot["identity"] for slot in prior_plan["slots"] if slot["identity"] not in by_slot]
    if missing:
        if preferred != projection["preferred_incumbent_identity"]:
            raise ProtocolError("pending settlement changes preferred incumbent")
        return _pending_response(projection, missing)
    normalized_outcomes = [by_slot[slot["identity"]] for slot in prior_plan["slots"]]
    updated_nodes = copy.deepcopy(nodes) + [
        copy.deepcopy(outcome)
        for outcome in normalized_outcomes
        if outcome["kind"] != "no_candidate"
    ]
    admitted_candidates = {
        node["candidate_identity"]
        for node in updated_nodes
        if node["kind"] == "admitted"
    }
    if preferred not in admitted_candidates:
        raise ProtocolError("preferred incumbent is not admitted")
    archive = _pareto_archive(updated_nodes, policy["dimensions"])

    generation = prior_plan["generation"] + 1
    proposed = _proposed_slots(
        policy,
        updated_nodes,
        archive,
        preferred,
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
                "evaluation_identity": policy["evaluation_identity"],
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
            "evaluation_identity": policy["evaluation_identity"],
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
    _validate_projection(
        output_projection,
        policy,
        surfaces,
        feedback_sources,
        dimension_ids,
        units,
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
    remaining = _validate_remaining_bound(request["remaining_bound"], units)

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
            "evaluation_identity": policy["evaluation_identity"],
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
                "evaluation_identity": policy["evaluation_identity"],
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
            "evaluation_identity": policy["evaluation_identity"],
            "last_settled_generation": 0,
            "last_plan": plan,
            "preferred_incumbent_identity": preferred,
            "nodes": [copy.deepcopy(origin)],
            "archive": [origin["candidate_identity"]],
            "seen_slot_identities": [slot["identity"] for slot in slots],
            "incorporated_outcome_identities": [origin["outcome_identity"]],
        },
    )
    _validate_projection(
        projection,
        policy,
        surfaces,
        feedback_sources,
        dimension_ids,
        units,
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
