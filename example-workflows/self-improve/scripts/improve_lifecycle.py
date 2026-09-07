"""Evidence requirements for agent-authored incidents and honest lifecycle claims."""
from __future__ import annotations

import re

from improve_common import EvidenceError, digest, instant


def require(condition, message):
    if not condition:
        raise EvidenceError(message)


def fields(value, names):
    require(isinstance(value, dict), "record must be an object")
    for name in names.split():
        require(name in value and value[name] is not None, "missing field: " + name)


def text(value):
    return isinstance(value, str) and bool(value.strip())


def refs(value, allowed, name, nonempty=True):
    require(isinstance(value, list) and (bool(value) or not nonempty), name + " requires a list")
    require(all(isinstance(v, str) for v in value) and len(set(value)) == len(value), name + " needs distinct IDs")
    require(set(value) <= set(allowed), name + " has unknown IDs")


def projection(bundle, records):
    incidents, proposals, states = {}, {}, {}
    for entry in records:
        if entry["kind"] == "incident":
            incidents[entry["id"]] = entry
        elif entry["kind"] == "proposal":
            proposals[entry["id"]] = entry
            states[entry["id"]] = "proposed"
        elif entry["kind"] == "prior_proposal":
            proposals[entry["id"]] = entry["proposal"]
            states[entry["id"]] = entry["stage"]
            incidents.update(entry["original_incidents"])
        elif entry["kind"] == "transition":
            states[entry["proposal"]] = entry["stage"]
    return {"incidents": incidents, "proposals": proposals, "states": states}


def oracle(value):
    fields(value, "command fixture_sha256 revision observed_exit")
    require(text(value["command"]) and text(value["revision"]), "oracle command/revision required")
    require(bool(re.fullmatch(r"[0-9a-f]{64}", str(value["fixture_sha256"]))), "oracle needs original fixture hash")
    require(type(value["observed_exit"]) is int, "oracle exit must be observed, not unavailable")


def validate(entry, bundle, records):
    fields(entry, "id kind predecessor")
    require(bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,100}", str(entry["id"]))), "unsafe record ID")
    state = projection(bundle, records)
    observations = {o["id"]: o for o in bundle["observations"]}
    incidents, proposals = state["incidents"], state["proposals"]
    kind = entry["kind"]
    if kind == "incident":
        fields(entry, "members rationale uncertainty classification primary_owner obstruction independent_episode")
        refs(entry["members"], observations, "incident members")
        require(entry["classification"] in {"environment", "workflow", "architecture", "project", "uncertain"}, "unknown classification")
        require(all(text(entry[k]) for k in ("rationale", "primary_owner", "obstruction", "independent_episode")), "incident adjudication needs rationale and owner/episode identities")
        require(isinstance(entry["uncertainty"], list), "uncertainty must be explicit list")
        occupied = {member for incident in incidents.values() for member in incident["members"]}
        require(not occupied.intersection(entry["members"]), "observation already adjudicated; copies belong in the same incident")
    elif kind == "prior_proposal":
        fields(entry, "source_review source_revision proposal original_incidents stage")
        require(entry["id"] == entry["proposal"].get("id"), "prior proposal identity mismatch")
        require(entry["stage"] in {"implemented", "deployed", "later-use-verified", "deferred", "rejected"}, "prior proposal is not eligible for recurrence review")
        require(isinstance(entry["original_incidents"], dict), "original incidents required")
        require(not set(entry["original_incidents"]).intersection(incidents), "original incident IDs collide")
        require(not proposals, "import prior proposal before new proposals")
    elif kind == "proposal":
        fields(entry, "incidents owner dependents qualification hypothesis minimal_fix nearby_success cost impact risk rank rationale gaps")
        require("failure_oracle" in entry, "missing field: failure_oracle")
        refs(entry["incidents"], incidents, "proposal incidents")
        fields(entry["owner"], "path revision class")
        require(all(text(entry["owner"][k]) for k in ("path", "revision", "class")), "owner identity required")
        require(all(incidents[i]["primary_owner"] == entry["owner"]["path"] for i in entry["incidents"]), "proposal has different primary owners")
        for key in ("hypothesis", "minimal_fix", "cost", "impact", "risk", "rationale"):
            require(text(entry[key]), "proposal needs " + key)
        require(type(entry["rank"]) is int and entry["rank"] > 0, "positive rank required")
        require(not any(p["rank"] == entry["rank"] for p in proposals.values()), "proposal ranks must be unique")
        require(isinstance(entry["dependents"], list) and isinstance(entry["gaps"], list), "dependents/gaps lists required")
        qualification = entry["qualification"]
        require(qualification in {"reproduced", "recurrent", "contradiction"}, "unknown qualification")
        if entry["failure_oracle"] is not None:
            oracle(entry["failure_oracle"])
            require(entry["failure_oracle"]["observed_exit"] != 0, "original failure must fail")
        if qualification in {"reproduced", "contradiction"}:
            require(entry["failure_oracle"] is not None, "one-off qualification requires reproduced original failure")
        else:
            episodes = {incidents[i]["independent_episode"] for i in entry["incidents"]}
            sessions = {observations[m]["session"] for i in entry["incidents"] for m in incidents[i]["members"]} - {None}
            if not sessions:
                sessions = {r for i in entry["incidents"] for m in incidents[i]["members"] for r in observations[m]["runs"]}
                if not sessions:
                    sessions = {observations[m]["host"] for i in entry["incidents"] for m in incidents[i]["members"]} - {"unknown"}
            obstructions = {incidents[i]["obstruction"] for i in entry["incidents"]}
            require(len(obstructions) == 1 and (len(episodes) >= 3 or len(episodes) >= 2 and len(sessions) >= 2), "recurrence needs independently adjudicated episodes at the same obstruction")
        require(isinstance(entry["nearby_success"], list), "nearby success checks required")
        for check in entry["nearby_success"]:
            oracle(check)
            require(check["observed_exit"] == 0, "nearby baseline must succeed")
    elif kind == "analysis":
        fields(entry, "report artifact agent_ticket positive unresolved gaps ranked_proposals")
        require(text(entry["report"]) and text(entry["artifact"]) and text(entry["agent_ticket"]), "analysis must name agent artifact/ticket")
        refs(entry["positive"], observations, "positive", False)
        refs(entry["unresolved"], observations, "unresolved", False)
        refs(entry["ranked_proposals"], proposals, "ranked proposals", False)
        require(entry["ranked_proposals"] == sorted(proposals, key=lambda p: proposals[p]["rank"]), "analysis must rank every proposal")
        assigned = {m for incident in incidents.values() for m in incident["members"] if m in observations}
        require(assigned | set(entry["positive"]) | set(entry["unresolved"]) == set(observations), "analysis must account for every observation")
        require(not set(entry["positive"]).intersection(entry["unresolved"]), "positive/unresolved overlap")
        require(entry["gaps"] == bundle["gaps"], "analysis must carry original coverage gaps unchanged")
    elif kind == "transition":
        transition(entry, bundle, records, state)
    elif kind == "repair_not_completed":
        fields(entry, "reason gaps")
        require(text(entry["reason"]) and isinstance(entry["gaps"], list), "incomplete repair needs precise reason/gaps")
    else:
        raise EvidenceError("unknown record kind")


def transition(entry, bundle, records, state):
    fields(entry, "proposal stage evidence")
    require(entry["proposal"] in state["proposals"], "unknown proposal")
    proposal = state["proposals"][entry["proposal"]]
    current, target = state["states"][entry["proposal"]], entry["stage"]
    allowed = {"proposed": {"selected", "deferred", "rejected"}, "selected": {"implemented", "deferred", "rejected"},
               "implemented": {"deployed", "reopened"}, "deployed": {"later-use-verified", "reopened"},
               "later-use-verified": {"reopened"}, "deferred": {"reopened"}, "rejected": {"reopened"},
               "reopened": {"selected", "deferred", "rejected"}}
    require(target in allowed.get(current, set()), "invalid lifecycle transition " + current + " -> " + str(target))
    evidence = entry["evidence"]
    require(isinstance(evidence, dict) and bool(evidence), "transition evidence required")
    imported = any(r["kind"] == "prior_proposal" and r["id"] == entry["proposal"] for r in records)
    local_transitions = [r for r in records if r["kind"] == "transition" and r["proposal"] == entry["proposal"]]
    if imported and not local_transitions:
        require(target == "reopened", "a carried proposal first needs fresh recurrence diagnosis")
    if target == "selected":
        require(bundle["selection"]["mode"] == "repair", "review mode cannot select repair")
        selected = {r["proposal"] for r in records if r["kind"] == "transition" and r["stage"] == "selected"}
        require(not selected or selected == {entry["proposal"]}, "at most one selected proposal per review")
        require(any(r["kind"] == "analysis" for r in records), "analysis must precede selection")
        require(proposal["rank"] == min(p["rank"] for p in state["proposals"].values()), "select the first ranked proposal")
        require(proposal["failure_oracle"] is not None and bool(proposal["nearby_success"]), "repair requires available failure and nearby-success replay")
    elif target == "implemented":
        fields(evidence, "commit checks original_replay nearby_replays judge_artifact judge_verdict delivery_run accepted_ticket")
        require(bool(re.fullmatch(r"[0-9a-f]{40}", str(evidence["commit"]))), "accepted full commit required")
        require(evidence["judge_verdict"] == "PASS" and text(evidence["judge_artifact"]) and text(evidence["accepted_ticket"]), "independent accepted judge evidence required")
        require(isinstance(evidence["checks"], list) and bool(evidence["checks"]), "scoped checks required")
        for check in evidence["checks"]:
            fields(check, "command exit")
            require(text(check["command"]) and type(check["exit"]) is int and check["exit"] == 0, "scoped check did not pass")
        replay(evidence["original_replay"], proposal["failure_oracle"], evidence["commit"])
        require(len(evidence["nearby_replays"]) == len(proposal["nearby_success"]), "nearby replay coverage changed")
        for result, original in zip(evidence["nearby_replays"], proposal["nearby_success"]):
            replay(result, original, evidence["commit"])
    elif target == "deployed":
        fields(evidence, "receipt installed_commit deployed_at")
        implemented = [r for r in records if r["kind"] == "transition" and r["proposal"] == entry["proposal"] and r["stage"] == "implemented"][-1]
        require(evidence["installed_commit"] == implemented["evidence"]["commit"] or evidence.get("accepted_source") == implemented["evidence"]["commit"], "deployment receipt must cover accepted source")
        require(text(evidence["receipt"]), "runtime/installation receipt required")
        instant(evidence["deployed_at"])
    elif target == "later-use-verified":
        fields(evidence, "run started_at matching_owner matching_obstruction artifact")
        prior = [r for r in records if r["kind"] == "transition" and r["proposal"] == entry["proposal"]]
        deployed = [r for r in prior if r["stage"] == "deployed"][-1]["evidence"]
        deliveries = {r["evidence"]["delivery_run"] for r in prior if r["stage"] == "implemented"}
        require(text(evidence["run"]) and evidence["run"] not in deliveries, "delivery replay is not later-use verification")
        require(instant(evidence["started_at"]) > instant(deployed["deployed_at"]), "later use must start after deployment")
        require(evidence["matching_owner"] == proposal["owner"]["path"] and text(evidence["artifact"]), "later-use owner/artifact mismatch")
        require(evidence["matching_obstruction"] in {state["incidents"][i]["obstruction"] for i in proposal["incidents"]}, "later-use obstruction mismatch")
    elif target == "reopened":
        fields(evidence, "incidents rationale")
        refs(evidence["incidents"], state["incidents"], "recurrence incidents")
        require(not set(evidence["incidents"]).intersection(proposal["incidents"]), "reopening needs fresh incidents")
        original = [state["incidents"][i] for i in proposal["incidents"]]
        for iid in evidence["incidents"]:
            incident = state["incidents"][iid]
            require(incident["primary_owner"] == proposal["owner"]["path"] and incident["obstruction"] in {i["obstruction"] for i in original}, "recurrence owner/obstruction requires agent diagnosis")
            require(incident["independent_episode"] not in {i["independent_episode"] for i in original}, "copied evidence cannot reopen")
    else:
        require(text(evidence.get("reason")), "deferred/rejected needs reason")


def replay(result, original, commit):
    oracle(result)
    require(result["command"] == original["command"] and result["fixture_sha256"] == original["fixture_sha256"], "replay must preserve original command and fixture")
    require(result["observed_exit"] == 0 and result["revision"] == commit, "replay must pass at accepted commit")


def close_probe(bundle, records, mode):
    state = projection(bundle, records)
    analyses = [r for r in records if r["kind"] == "analysis"]
    require(bool(analyses), "review incomplete: missing agent analysis")
    # Revalidate the last report against all subsequently added evidence.
    validate(analyses[-1], bundle, [r for r in records if r["id"] != analyses[-1]["id"]])
    result = {"review_completed": True, "repair_completed": False, "coverage": bundle["coverage"],
              "gaps": bundle["gaps"], "states": state["states"], "analysis": analyses[-1]["artifact"],
              "later_use": "pending unless independently evidenced in lifecycle"}
    if mode == "repair":
        selected = {r["proposal"] for r in records if r["kind"] == "transition" and r["stage"] == "selected"}
        complete = len(selected) == 1 and state["states"][next(iter(selected))] in {"implemented", "deployed", "later-use-verified"}
        result["repair_completed"] = complete
        if not complete:
            reasons = [r["reason"] for r in records if r["kind"] == "repair_not_completed"]
            result["repair_not_completed"] = reasons[-1] if reasons else "no selected proposal with accepted unchanged replay and independent judgment"
    return result
