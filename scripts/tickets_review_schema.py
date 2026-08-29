"""Closed semantic schemas for ``orchflows.review.v1`` records."""
from __future__ import annotations

import hashlib

if __package__:
    from .tickets_format import canonical_json, parse_canonical_json
else:
    from tickets_format import canonical_json, parse_canonical_json

PROTOCOL = "orchflows.review.v1"
KINDS = ("GatePlan", "CritiqueAdjudication", "RepairOutcome", "Verification")


class SchemaError(ValueError):
    pass


def digest(value) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def nonempty(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def finding_values(values, subject: str) -> list:
    if not isinstance(values, list):
        raise SchemaError(f"{subject} is not an array")
    identities = set()
    required = {
        "blocking", "class", "evidence", "goal_impact", "id", "repair", "summary",
    }
    for index, finding in enumerate(values):
        if not isinstance(finding, dict) or set(finding) != required:
            raise SchemaError(f"{subject} finding {index} has unknown or missing fields")
        if not isinstance(finding["blocking"], bool):
            raise SchemaError(f"{subject} finding {index} blocking is not boolean")
        if any(not nonempty(finding[key]) for key in (
            "class", "goal_impact", "id", "repair", "summary",
        )):
            raise SchemaError(f"{subject} finding {index} has an empty identity or disposition")
        evidence = finding["evidence"]
        if not isinstance(evidence, list) or not evidence or any(
            not nonempty(item) for item in evidence
        ):
            raise SchemaError(f"{subject} finding {index} has no closed evidence list")
        if finding["id"] in identities:
            raise SchemaError(f"{subject} repeats finding id {finding['id']}")
        identities.add(finding["id"])
    return values


def _criteria(values, *, legacy: bool) -> None:
    if not isinstance(values, list) or not values:
        raise SchemaError("GatePlan has no criteria")
    orders, lenses, tickets = set(), set(), set()
    for index, criterion in enumerate(values):
        if not isinstance(criterion, dict) or set(criterion) != {
            "identity", "lens", "order", "ticket",
        }:
            raise SchemaError(f"GatePlan criterion {index} has unknown or missing fields")
        order = criterion["order"]
        if legacy and isinstance(order, str) and order.isdigit():
            order = int(order)
        if not isinstance(order, int) or isinstance(order, bool) or order < 0:
            raise SchemaError(f"GatePlan criterion {index} order is not a nonnegative integer")
        if any(not nonempty(criterion[key]) for key in ("identity", "lens", "ticket")):
            raise SchemaError(f"GatePlan criterion {index} is incomplete")
        if order in orders or criterion["lens"] in lenses or criterion["ticket"] in tickets:
            raise SchemaError("GatePlan criteria are not unique")
        orders.add(order); lenses.add(criterion["lens"]); tickets.add(criterion["ticket"])
    if orders != set(range(len(values))):
        raise SchemaError("GatePlan criterion order is not contiguous")


def _shape(record: dict, index: int, plan: dict | None, *, legacy: bool) -> None:
    kind = record["kind"]
    common = {"identity", "kind", "predecessor", "protocol"}
    if kind == "GatePlan":
        fields = {"artifact", "criteria", "isolation", "mode", "pack", "root", "workspace"}
        if legacy and "workspace" not in record:
            fields.remove("workspace")
        if set(record) != common | fields:
            raise SchemaError(f"review record {index} GatePlan has unknown or missing fields")
        if record["predecessor"] is not None or record["mode"] not in {"gate", "checker"}:
            raise SchemaError("GatePlan has an invalid predecessor or mode")
        if any(not nonempty(record.get(key)) for key in ("artifact", "isolation", "pack", "root")):
            raise SchemaError("GatePlan has an empty fixed field")
        if "workspace" in record and not nonempty(record["workspace"]):
            raise SchemaError("GatePlan workspace is empty")
        _criteria(record["criteria"], legacy=legacy)
        return
    if plan is None:
        raise SchemaError(f"review record {index} has no GatePlan")
    if kind == "CritiqueAdjudication":
        aggregate = record.get("lens") == "*"
        fields = {"accepted", "adjudicated_by", "artifact", "findings", "lens"}
        if aggregate:
            fields.add("adjudications")
            if legacy and "adjudicated_by" not in record:
                fields.remove("adjudicated_by")
        if set(record) != common | fields:
            raise SchemaError(f"review record {index} CritiqueAdjudication has unknown or missing fields")
        if record["artifact"] != plan["artifact"] or not nonempty(record.get("lens")):
            raise SchemaError("CritiqueAdjudication differs from its GatePlan")
        if "adjudicated_by" in record and not nonempty(record["adjudicated_by"]):
            raise SchemaError("CritiqueAdjudication has no adjudication authority")
        findings = finding_values(record["findings"], "CritiqueAdjudication findings")
        accepted = finding_values(record["accepted"], "CritiqueAdjudication accepted")
        known = {canonical_json(item) for item in findings}
        if any(canonical_json(item) not in known for item in accepted):
            raise SchemaError("CritiqueAdjudication accepted set is not a subset of findings")
        if aggregate:
            members = record.get("adjudications")
            if not isinstance(members, list) or not members:
                raise SchemaError("aggregate CritiqueAdjudication has no adjudications")
            if [item.get("lens") for item in members] != [item["lens"] for item in plan["criteria"]]:
                raise SchemaError("aggregate CritiqueAdjudication does not follow GatePlan order")
            for item in members:
                if not isinstance(item, dict) or item.get("lens") == "*":
                    raise SchemaError("aggregate CritiqueAdjudication contains an invalid member")
                _shape(item, index, plan, legacy=legacy)
                if item.get("predecessor") != plan["identity"]:
                    raise SchemaError("critique adjudication member names a different GatePlan")
            if findings != [item for member in members for item in member["findings"]]:
                raise SchemaError("aggregate CritiqueAdjudication rewrites findings")
            if accepted != [item for member in members for item in member["accepted"]]:
                raise SchemaError("aggregate CritiqueAdjudication rewrites the accepted set")
        return
    fields = (
        {"accepted", "artifact", "by", "input_artifact", "no_op", "result"}
        if kind == "RepairOutcome" else {"artifact", "by", "evidence", "verdict"}
    )
    # ``covers`` is optional for legacy review ledgers.  New fixed-result
    # ledgers may carry the closed identities from contracts/verdict.md;
    # retaining the old shape keeps already-issued gate records replayable.
    if kind == "Verification" and "covers" in record:
        fields = fields | {"covers"}
    if set(record) != common | fields:
        raise SchemaError(f"review record {index} {kind} has unknown or missing fields")
    if kind == "RepairOutcome":
        finding_values(record["accepted"], "RepairOutcome accepted")
        if not isinstance(record["no_op"], bool) or any(
            not nonempty(record[key]) for key in ("artifact", "by", "input_artifact", "result")
        ):
            raise SchemaError("RepairOutcome has an invalid field type")
    elif record["verdict"] not in {"PASS", "FAIL", "UNVERIFIED"} or any(
        not nonempty(record[key]) for key in ("artifact", "by", "evidence")
    ):
        raise SchemaError("Verification has an invalid field type")
    elif "covers" in record:
        covers = record["covers"]
        def valid_cover(value):
            if isinstance(value, str):
                return nonempty(value)
            if isinstance(value, list):
                return all(valid_cover(item) for item in value)
            if isinstance(value, dict):
                return all(nonempty(key) and valid_cover(item) for key, item in value.items())
            return False
        if not isinstance(covers, (dict, list)) or not covers or not valid_cover(covers):
            raise SchemaError("Verification covers contains an empty identity")


def validate_records(value, *, allow_legacy: bool = False) -> list:
    if isinstance(value, str):
        try:
            parsed = parse_canonical_json(value)
        except (TypeError, ValueError) as error:
            raise SchemaError(f"review_v1 is not canonical JSON: {error}") from error
        if canonical_json(parsed) != value:
            raise SchemaError("review_v1 is not canonical JSON")
        value = parsed
    if not isinstance(value, dict) or set(value) != {"protocol", "records"}:
        raise SchemaError("review_v1 has unknown or missing fields")
    if value.get("protocol") != PROTOCOL or not isinstance(value.get("records"), list):
        raise SchemaError("review_v1 has an invalid protocol or record list")
    records, prior, plan = value["records"], None, None
    for index, record in enumerate(records):
        if not isinstance(record, dict) or not {"identity", "kind", "predecessor", "protocol"}.issubset(record):
            raise SchemaError(f"review record {index} is not a complete object")
        if record.get("protocol") != PROTOCOL or record.get("kind") not in KINDS:
            raise SchemaError(f"review record {index} has an invalid protocol or kind")
        content = {key: item for key, item in record.items() if key != "identity"}
        if record.get("identity") != digest(content):
            raise SchemaError(f"review record {index} identity diverged")
        if record.get("predecessor") != prior:
            raise SchemaError(f"review record {index} does not name its exact predecessor")
        _shape(record, index, plan, legacy=allow_legacy)
        if index == 0:
            if record["kind"] != "GatePlan":
                raise SchemaError("review ledger does not begin with GatePlan")
            plan = record
        elif record["kind"] == "GatePlan":
            raise SchemaError("review ledger contains more than one GatePlan")
        expected = {"CritiqueAdjudication": "GatePlan", "RepairOutcome": "CritiqueAdjudication", "Verification": "RepairOutcome"}.get(record["kind"])
        if expected and records[index - 1]["kind"] != expected:
            raise SchemaError(f"{record['kind']} does not follow {expected}")
        if record["kind"] == "RepairOutcome":
            predecessor = records[index - 1]
            if record["accepted"] != predecessor["accepted"]:
                raise SchemaError("RepairOutcome rewrites the accepted blocker set")
            if record["input_artifact"] != plan["artifact"]:
                raise SchemaError("RepairOutcome input artifact differs from GatePlan")
            if record["no_op"] and (record["accepted"] or record["artifact"] != plan["artifact"]):
                raise SchemaError("RepairOutcome no-op bypasses accepted blockers or changes artifact")
        if record["kind"] == "Verification" and record["artifact"] != records[index - 1]["artifact"]:
            raise SchemaError("Verification names a different repaired artifact")
        prior = record["identity"]
    return records
