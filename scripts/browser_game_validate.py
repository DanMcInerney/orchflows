#!/usr/bin/env python3
"""Validate browser-game program-record and checkpoint relations.

JSON Schema owns local shape.  This module owns the cross-field relations that
JSON Schema cannot express without duplicating the intake authority table or
the successor-plan projection logic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:  # in-repo; the installed copy sits flat beside tickets.py
    from scripts import console
except ImportError:  # pragma: no cover - the installed copy's path
    import console


# BGW-TRACE[implementation:instance-validation|PJ-05,PJ-06,PJ-09,PJ-10,PJ-22,PJ-24,PJ-25,PJ-28]

CHOICE_AUTHORIZING_DISPOSITIONS = {"advance", "revise", "stop"}
BRANCH_BY_DISPOSITION = {
    "advance": "successor-plan",
    "revise": "successor-plan",
    "stop": "successor-plan",
    "experiment": "experiment",
    "user-decision-required": "user-question",
}
STATE_BY_DISPOSITION = {
    "answered": {"settled"},
    "deferred": {"open-question"},
    "experiment": {"decision"},
    "not-applicable": {"settled"},
}
SUCCESSOR_PROJECTIONS = {
    "ordered_artifact_kinds": "artifact_kind",
    "standards": "standard",
    "run_identities": "run_identity",
    "root_identities": "root_identity",
    "dependencies": "dependencies",
    "current_status": "current_status",
}


def _entries(program_record: dict[str, Any], record_name: str) -> list[dict[str, Any]]:
    collection = program_record.get("records", {}).get(record_name, {})
    entries = collection.get("entries", []) if collection.get("state") == "present" else []
    return entries if isinstance(entries, list) else []


def _settled_value(value: Any) -> Any:
    if isinstance(value, dict) and value.get("state") == "settled":
        return value.get("value")
    return value


def _authority_source(policy: dict[str, Any], question_id: str, field_id: str) -> str | None:
    table = policy.get("atomic_authority", {})
    overrides = table.get("overrides", {})
    question = overrides.get(question_id, {})
    return question.get(field_id, table.get("default_source"))


def validate_authority_contract(
    policy: dict[str, Any], program_schema: dict[str, Any]
) -> list[str]:
    """Validate that the policy's executable classifier covers the schema."""

    errors: list[str] = []
    table = policy.get("atomic_authority")
    if not isinstance(table, dict):
        return ["atomic_authority must be an object"]
    if table.get("decision_key") != ["question_id", "field_id", "authority_source"]:
        errors.append("atomic_authority decision_key must be question_id, field_id, authority_source")
    if table.get("default_source") != "empirical-evidence":
        errors.append("atomic_authority default_source must be empirical-evidence")

    user_sources = set(policy.get("authority", {}).get("user-only", {}).get("categories", []))
    sources = table.get("source_kinds", {})
    expected_sources = user_sources | {"empirical-evidence"}
    if set(sources) != expected_sources:
        errors.append("atomic_authority source_kinds must exactly own every authority source")
    for source in user_sources:
        if sources.get(source) != "user-only":
            errors.append(f"authority source {source} must route user-only")
    if sources.get("empirical-evidence") != "empirical":
        errors.append("empirical-evidence must route empirical")

    questions = (
        program_schema.get("$defs", {})
        .get("productBriefRevision", {})
        .get("properties", {})
        .get("questions", {})
        .get("properties", {})
    )
    overrides = table.get("overrides", {})
    for question_id, fields in overrides.items():
        if question_id not in questions:
            errors.append(f"authority override names unknown question {question_id}")
            continue
        known_fields = set(questions[question_id].get("properties", {}))
        for field_id, source in fields.items():
            if field_id not in known_fields:
                errors.append(f"authority override names unknown field {question_id}.{field_id}")
            if source not in expected_sources:
                errors.append(f"authority override {question_id}.{field_id} names unknown source {source}")
    return errors


def validate_program_record(
    program_record: dict[str, Any], policy: dict[str, Any]
) -> list[str]:
    """Validate authority and disposition relations in product-brief cells."""

    errors: list[str] = []
    source_kinds = policy.get("atomic_authority", {}).get("source_kinds", {})
    for revision in _entries(program_record, "product_brief"):
        questions = revision.get("questions", {})
        for question_id, bucket in questions.items():
            if not isinstance(bucket, dict):
                errors.append(f"{question_id} must be an object")
                continue
            for field_key, field in bucket.items():
                label = f"{question_id}.{field_key}"
                if not isinstance(field, dict):
                    errors.append(f"{label} must be an object")
                    continue
                if field.get("field_id") != field_key:
                    errors.append(f"{label} field_id must equal its atomic field key")
                expected_source = _authority_source(policy, question_id, field_key)
                source = field.get("authority_source")
                if source != expected_source:
                    errors.append(
                        f"{label} authority source must be {expected_source}, found {source}"
                    )
                expected_kind = source_kinds.get(expected_source)
                kind = field.get("authority_kind")
                if kind != expected_kind:
                    errors.append(
                        f"{label} authority kind must be {expected_kind}, found {kind}"
                    )

                resolution = field.get("resolution", {})
                state = resolution.get("state") if isinstance(resolution, dict) else None
                disposition = field.get("disposition")
                if state not in STATE_BY_DISPOSITION.get(disposition, set()):
                    errors.append(
                        f"{label} disposition {disposition} is incompatible with resolution state {state}"
                    )
                if state == "open-question":
                    if resolution.get("authority_kind") != kind:
                        errors.append(f"{label} resolution authority must agree with outer authority")
                    if resolution.get("kind") != kind:
                        errors.append(f"{label} open question kind must agree with outer authority")
                    if kind == "user-only":
                        question = field.get("verbatim_question")
                        if not question or resolution.get("question") != question:
                            errors.append(f"{label} must preserve one verbatim user-only question")
                if disposition == "experiment" and kind != "empirical":
                    errors.append(f"{label} user-only authority cannot be settled by experiment")
                if state == "settled" and kind == "user-only" and disposition == "answered":
                    answer = resolution.get("verbatim_user_answer")
                    if (
                        resolution.get("settled_by") != "verbatim-user-answer"
                        or answer is None
                        or resolution.get("value") != answer
                    ):
                        errors.append(f"{label} must preserve the verbatim user answer as its value")
    return errors


def validate_successor_plan(plan: dict[str, Any]) -> list[str]:
    """Validate that successor aggregate cells are exact ordered projections."""

    errors: list[str] = []
    artifacts = plan.get("ordered_artifacts", [])
    if not isinstance(artifacts, list) or not artifacts:
        return ["successor plan must contain ordered_artifacts"]
    for aggregate, artifact_field in SUCCESSOR_PROJECTIONS.items():
        cell = plan.get(aggregate, {})
        expected = [artifact.get(artifact_field) for artifact in artifacts]
        if not isinstance(cell, dict) or cell.get("state") != "settled" or cell.get("value") != expected:
            errors.append(f"successor {aggregate} aggregate must equal ordered_artifacts projection {expected}")
    return errors


def validate_checkpoint(
    checkpoint: dict[str, Any], program_record: dict[str, Any]
) -> list[str]:
    """Validate checkpoint coverage, branch, Q-12, and successor relations."""

    errors: list[str] = []
    invalidation = checkpoint.get("invalidation", {})
    if invalidation.get("covered_candidate_identity") != checkpoint.get("candidate_identity"):
        errors.append("checkpoint covered candidate must equal candidate_identity")
    if invalidation.get("covered_program_record_revision_identity") != checkpoint.get(
        "program_record_revision_identity"
    ):
        errors.append("checkpoint covered program revision must equal program_record_revision_identity")
    evidence = checkpoint.get("evidence", [])
    expected_evidence = {
        item.get("evidence_identity") for item in evidence if isinstance(item, dict)
    }
    covered_evidence = set(invalidation.get("covered_evidence_identities", []))
    if covered_evidence != expected_evidence:
        errors.append("checkpoint covered evidence identities must equal the evidence set")

    disposition = checkpoint.get("disposition")
    branch = checkpoint.get("branch", {})
    expected_branch = BRANCH_BY_DISPOSITION.get(disposition)
    if branch.get("kind") != expected_branch:
        errors.append(f"{disposition} requires the exact {expected_branch} branch payload")
    if disposition in CHOICE_AUTHORIZING_DISPOSITIONS:
        if checkpoint.get("q12_revalidation", {}).get("status") != "settled":
            errors.append(f"{disposition} requires settled Q-12 authorization")
    if expected_branch == "user-question":
        required = {"question", "field_id", "open_question_id", "program_revision_id"}
        if not required <= set(branch) or branch.get("program_revision_id") != checkpoint.get(
            "program_record_revision_identity"
        ):
            errors.append("user-decision-required branch must carry the complete verbatim question envelope")
        matches = []
        for revision in _entries(program_record, "product_brief"):
            for bucket in revision.get("questions", {}).values():
                for field in bucket.values():
                    resolution = field.get("resolution", {})
                    if (
                        field.get("field_id") == branch.get("field_id")
                        and resolution.get("open_question_id") == branch.get("open_question_id")
                    ):
                        matches.append(field)
        if len(matches) != 1 or matches[0].get("verbatim_question") != branch.get("question"):
            errors.append("user-decision-required branch question must match one bound verbatim program-record question")
    elif expected_branch == "experiment":
        if not {"decision_id", "experiment_id", "result_identity"} <= set(branch):
            errors.append("experiment branch must carry one matched experiment result")
        matches = [
            experiment
            for experiment in _entries(program_record, "experiment_register")
            if _settled_value(experiment.get("experiment_id")) == branch.get("experiment_id")
            and _settled_value(experiment.get("predeclared_decision")) == branch.get("decision_id")
            and _settled_value(experiment.get("result_identity")) == branch.get("result_identity")
        ]
        if len(matches) != 1:
            errors.append("experiment branch must match one admitted experiment and predeclared decision")
    elif expected_branch == "successor-plan":
        plan = branch.get("successor_plan")
        if not isinstance(plan, dict):
            errors.append("successor-plan branch must carry one lawful successor plan")
        else:
            errors.extend(validate_successor_plan(plan))
            admitted = _entries(program_record, "successor_plans")
            if admitted and plan not in admitted:
                errors.append("checkpoint successor plan must be admitted by the bound program record")
    return errors


def validate_instances(
    program_record: dict[str, Any],
    checkpoint: dict[str, Any],
    policy: dict[str, Any],
) -> list[str]:
    """Return every semantic browser-game instance error."""

    return validate_program_record(program_record, policy) + validate_checkpoint(
        checkpoint, program_record
    )


def _read(path: Path) -> dict[str, Any]:
    # utf-8-sig: a record written by a host whose editor or shell prefixes
    # a BOM is still that record, and plain utf-8 leaves the BOM glued to
    # the opening brace, where json reads it as a syntax error.
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main(argv: list[str] | None = None) -> int:
    console.harden()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--program-record", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args(argv)
    errors = validate_instances(
        _read(args.program_record), _read(args.checkpoint), _read(args.policy)
    )
    for error in errors:
        print(f"ERROR: {error}")
    return bool(errors)


if __name__ == "__main__":
    raise SystemExit(console.run(main))
