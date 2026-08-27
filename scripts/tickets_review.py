"""Immutable predecessor-linked review records for gates and checkers."""

from __future__ import annotations

import hashlib
from pathlib import Path

if __package__:
    from .tickets_format import (
        GATE_EXECUTORS, _executor_of, _parse_frontmatter, _set_frontmatter_field, canonical_json,
        parse_canonical_json,
    )
    from .tickets_attempts import _record_response
    from .tickets_store import _load_ticket
else:
    from tickets_format import (
        GATE_EXECUTORS, _executor_of, _parse_frontmatter, _set_frontmatter_field, canonical_json,
        parse_canonical_json,
    )
    from tickets_attempts import _record_response
    from tickets_store import _load_ticket


REVIEW_PROTOCOL = "orchflows.review.v1"
REVIEW_FIELD = "review_v1"
REVIEW_KINDS = (
    "GatePlan", "CritiqueAdjudication", "RepairOutcome", "Verification",
)


class ReviewError(ValueError):
    """A review record is absent, divergent, or not closed."""


def _digest(value) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _record(kind: str, predecessor, **fields) -> dict:
    content = {
        "kind": kind,
        "predecessor": predecessor,
        "protocol": REVIEW_PROTOCOL,
        **fields,
    }
    return {**content, "identity": _digest(content)}


def _review_state(records) -> dict:
    state = {"protocol": REVIEW_PROTOCOL, "records": list(records)}
    review_records(state)
    return state


def review_records(value) -> list:
    if isinstance(value, str):
        try:
            parsed = parse_canonical_json(value)
        except (TypeError, ValueError) as error:
            raise ReviewError(f"{REVIEW_FIELD} is not canonical JSON: {error}") from error
        if canonical_json(parsed) != value:
            raise ReviewError(f"{REVIEW_FIELD} is not canonical JSON")
        value = parsed
    if not isinstance(value, dict) or set(value) != {"protocol", "records"}:
        raise ReviewError(f"{REVIEW_FIELD} has unknown or missing fields")
    if value.get("protocol") != REVIEW_PROTOCOL or not isinstance(value.get("records"), list):
        raise ReviewError(f"{REVIEW_FIELD} has an invalid protocol or record list")
    records = value["records"]
    prior = None
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ReviewError(f"review record {index} is not an object")
        required = {"identity", "kind", "predecessor", "protocol"}
        if not required.issubset(record):
            raise ReviewError(f"review record {index} is incomplete")
        if record.get("protocol") != REVIEW_PROTOCOL or record.get("kind") not in REVIEW_KINDS:
            raise ReviewError(f"review record {index} has an invalid protocol or kind")
        content = {key: item for key, item in record.items() if key != "identity"}
        if record.get("identity") != _digest(content):
            raise ReviewError(f"review record {index} identity diverged")
        if record.get("predecessor") != prior:
            raise ReviewError(f"review record {index} does not name its exact predecessor")
        prior = record["identity"]
    return records


def state_from_text(text: str, *, required: bool = False) -> dict | None:
    encoded = _parse_frontmatter(text).get(REVIEW_FIELD)
    if encoded is None:
        if required:
            raise ReviewError(f"ticket has no {REVIEW_FIELD} predecessor ledger")
        return None
    records = review_records(encoded)
    return _review_state(records)


def _lens(ticket_id: str) -> str:
    marker = ".gate.critique."
    if marker not in ticket_id:
        raise ReviewError(f"not a gate critique ticket: {ticket_id}")
    return ticket_id.split(marker, 1)[1]


def _gate_root(ticket_id: str) -> str:
    for suffix in (".gate.critique.", ".gate.repair", ".gate.verify"):
        if suffix in ticket_id:
            return ticket_id.split(suffix, 1)[0]
    raise ReviewError(f"not a gate ticket: {ticket_id}")


def _critique_paths(ticket_path: Path) -> list[Path]:
    root_id = _gate_root(ticket_path.stem)
    paths = list(ticket_path.parent.glob(f"{root_id}.gate.critique.*.md"))
    ranked = []
    for path in paths:
        data = _load_ticket(path)
        if "error" in data:
            raise ReviewError(data["error"])
        order_text = str(data.get("review_order") or "")
        if not order_text.isdigit():
            raise ReviewError(f"gate critique has no stable review_order: {path.stem}")
        order = int(order_text)
        ranked.append((order, path, data))
    ranked.sort(key=lambda item: item[0])
    if [item[0] for item in ranked] != list(range(len(ranked))):
        raise ReviewError("gate critique review_order is not unique and contiguous")
    return [item[1] for item in ranked]


def gate_plan(ticket_path: Path, artifact: str) -> dict:
    if not isinstance(artifact, str) or not artifact.strip():
        raise ReviewError("gate review requires --artifact <fixed-identity>")
    criteria = []
    for path in _critique_paths(ticket_path):
        data = _load_ticket(path)
        seal = str(data.get("assignment_seal") or "")
        if not seal:
            raise ReviewError(f"gate critique is not sealed: {path.stem}")
        criteria.append({
            "identity": seal,
            "lens": _lens(path.stem),
            "order": data["review_order"],
            "ticket": path.stem,
        })
    if not criteria:
        raise ReviewError("gate plan has no critique criteria")
    data = _load_ticket(ticket_path)
    return _record(
        "GatePlan", None,
        artifact=artifact.strip(),
        criteria=criteria,
        isolation=str(data.get("isolation") or "none"),
        mode="gate",
        pack=data.get("pack"),
        root=_gate_root(ticket_path.stem),
    )


def _dependency_text(ticket_path: Path, dependency: str) -> str:
    path = ticket_path.with_name(f"{dependency}.md")
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ReviewError(f"unreadable review dependency {dependency}: {error}") from error


def aggregate_adjudication(ticket_path: Path, dependencies) -> dict:
    adjudications = []
    plan = None
    for dependency in dependencies:
        records = review_records(state_from_text(_dependency_text(ticket_path, dependency), required=True))
        if [record["kind"] for record in records] != ["GatePlan", "CritiqueAdjudication"]:
            raise ReviewError(f"critique dependency has no closed adjudication: {dependency}")
        if plan is None:
            plan = records[0]
        elif records[0] != plan:
            raise ReviewError("critique dependencies do not share one immutable GatePlan")
        adjudications.append(records[1])
    if plan is None:
        raise ReviewError("repair has no critique adjudications")
    by_lens = {record["lens"]: record for record in adjudications}
    ordered = []
    for criterion in plan["criteria"]:
        record = by_lens.get(criterion["lens"])
        if record is None:
            raise ReviewError(f"missing adjudication for lens {criterion['lens']}")
        ordered.append(record)
    return _record(
        "CritiqueAdjudication", plan["identity"],
        accepted=[item for record in ordered for item in record["accepted"]],
        adjudications=ordered,
        artifact=plan["artifact"],
        findings=[item for record in ordered for item in record["findings"]],
        lens="*",
    )


def packet_state(ticket_path: Path, text: str, artifact: str | None) -> dict | None:
    data = _parse_frontmatter(text)
    ticket_id = str(data.get("id") or ticket_path.stem)
    executor = _executor_of(data)
    if executor == GATE_EXECUTORS["critique"] and ".gate.critique." in ticket_id:
        return _review_state([gate_plan(ticket_path, artifact or "")])
    if executor == GATE_EXECUTORS["repair"] and ticket_id.endswith(".gate.repair"):
        aggregate = aggregate_adjudication(ticket_path, data.get("depends_on") or [])
        plan = review_records(state_from_text(
            _dependency_text(ticket_path, str((data.get("depends_on") or [""])[0])),
            required=True,
        ))[0]
        state = _review_state([plan, aggregate])
        if artifact is not None and artifact != plan["artifact"]:
            raise ReviewError("repair packet artifact differs from GatePlan")
        return state
    if executor == GATE_EXECUTORS["verify"] and ticket_id.endswith(".gate.verify"):
        dependencies = list(data.get("depends_on") or [])
        if len(dependencies) != 1:
            raise ReviewError("verification requires one repair predecessor")
        state = state_from_text(_dependency_text(ticket_path, str(dependencies[0])), required=True)
        records = review_records(state)
        if not records or records[-1]["kind"] != "RepairOutcome":
            raise ReviewError("verification predecessor has no RepairOutcome")
        if artifact is None or artifact != records[-1]["artifact"]:
            raise ReviewError("verification packet must name the exact repaired artifact")
        return _review_state(records)
    return None


def packet_state_result(ticket_path: Path, text: str, artifact: str | None):
    try:
        return packet_state(ticket_path, text, artifact), None
    except ReviewError as error:
        return None, str(error)


def packet_mutation(review_state, run, ticket_id, dispatch_id, record_id, content):
    if review_state is None:
        return None

    def commit(candidate, _data, _attempt, _dispatch_state):
        updated = _set_frontmatter_field(
            candidate, REVIEW_FIELD, canonical_json(review_state)
        )
        return (
            updated,
            _record_response(run, ticket_id, dispatch_id, record_id, content),
            None,
        )
    return commit


def replay_review_failure(text: str, expected) -> str | None:
    if expected is None:
        return None
    try:
        return None if state_from_text(text, required=True) == expected else (
            "committed packet review ledger diverged"
        )
    except ReviewError as error:
        return str(error)


def adjudicate(
    state: dict, feedback: str, accepted_text: str | None, by: str, lens: str,
) -> dict:
    records = review_records(state)
    if [record["kind"] for record in records] != ["GatePlan"]:
        raise ReviewError("critique join requires exactly one GatePlan predecessor")
    try:
        findings = parse_canonical_json(feedback)
        accepted = parse_canonical_json(accepted_text) if accepted_text is not None else None
    except (TypeError, ValueError) as error:
        raise ReviewError(f"critique findings and accepted set must be canonical JSON arrays: {error}") from error
    if not isinstance(findings, list) or not isinstance(accepted, list):
        raise ReviewError("critique join requires --accepted <canonical-json-array>")
    finding_values = {canonical_json(item) for item in findings}
    if any(canonical_json(item) not in finding_values for item in accepted):
        raise ReviewError("accepted blocker set is not a subset of critique findings")
    plan = records[0]
    if lens not in {item["lens"] for item in plan["criteria"]}:
        raise ReviewError(f"critique lens is absent from GatePlan: {lens}")
    record = _record(
        "CritiqueAdjudication", plan["identity"],
        accepted=accepted,
        adjudicated_by=by,
        artifact=plan["artifact"],
        findings=findings,
        lens=lens,
    )
    return _review_state([plan, record])


def repair_outcome(state: dict, artifact: str, result: str, by: str, *, no_op=False) -> dict:
    records = review_records(state)
    if not records or records[-1]["kind"] != "CritiqueAdjudication":
        raise ReviewError("repair requires a CritiqueAdjudication predecessor")
    adjudication = records[-1]
    if no_op:
        if adjudication.get("accepted"):
            raise ReviewError("no-op repair requires every accepted blocker set to be empty")
        artifact = adjudication["artifact"]
    elif not isinstance(artifact, str) or not artifact.strip():
        raise ReviewError("repair join requires --artifact <fixed-identity>")
    record = _record(
        "RepairOutcome", adjudication["identity"],
        accepted=adjudication["accepted"],
        artifact=artifact,
        by=by,
        input_artifact=adjudication["artifact"],
        no_op=bool(no_op),
        result=result,
    )
    return _review_state([*records, record])


def verification_outcome(state: dict, artifact: str | None, verification: str, by: str) -> dict:
    records = review_records(state)
    if not records or records[-1]["kind"] != "RepairOutcome":
        raise ReviewError("verification requires a RepairOutcome predecessor")
    repaired = records[-1]
    if artifact is not None and artifact != repaired["artifact"]:
        raise ReviewError("verification join names a different artifact")
    record = _record(
        "Verification", repaired["identity"],
        artifact=repaired["artifact"],
        by=by,
        evidence=verification,
    )
    return _review_state([*records, record])


__all__ = (
    "REVIEW_FIELD", "REVIEW_PROTOCOL", "ReviewError", "adjudicate",
    "aggregate_adjudication", "canonical_json", "packet_mutation", "packet_state_result",
    "replay_review_failure",
    "repair_outcome", "review_records", "state_from_text",
    "verification_outcome",
)
