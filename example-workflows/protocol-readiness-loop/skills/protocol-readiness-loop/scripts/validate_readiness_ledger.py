#!/usr/bin/env python3
"""Validate protocol-readiness-loop convergence ledger JSON Lines."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
from typing import Any


SCHEMA = "protocol-readiness-ledger/v1"
UNKNOWN = "UNKNOWN"
ALLOWED_PHASES = {
    "opening",
    "stress",
    "adjudication",
    "revision",
    "conformance",
    "conformance_repair",
    "terminal",
}
ALLOWED_TERMINAL_STATUSES = {
    "READY_FOR_OWNER_FREEZE",
    "OWNER_DECISION_REQUIRED",
    "ROUND_LIMIT_REACHED",
    "BLOCKED",
    "INVALID",
}
REQUIRED_FIELDS = {
    "schema",
    "cycle_id",
    "round_id",
    "phase",
    "phase_started_at",
    "phase_ended_at",
    "phase_duration_ms",
    "active_worker_ms",
    "handoff_queue_ms",
    "findings_entering",
    "accepted",
    "rejected",
    "unresolved",
    "newly_introduced",
    "conformance_defect_count",
    "stress_finding_count",
    "blockers_by_failure_class",
    "failure_class_evidence",
    "current_protocol_path",
    "current_protocol_sha256",
    "terminal_disposition",
    "terminal_reason",
    "next_action",
}
FINDING_FIELDS = (
    "findings_entering",
    "accepted",
    "rejected",
    "unresolved",
    "newly_introduced",
)
SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")


def load_ledger(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"line {line_number}: invalid JSON: {exc.msg}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"line {line_number}: record must be an object")
        records.append(value)
    return records


def _nonnegative_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _duration(value: Any) -> bool:
    return value == UNKNOWN or _nonnegative_integer(value)


def _timestamp(value: Any) -> datetime | None:
    if value == UNKNOWN:
        return None
    if not isinstance(value, str):
        raise ValueError("must be RFC 3339 text or UNKNOWN")
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("must include a timezone")
    return parsed


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate_records(records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    if not records:
        return ["ledger has no records"]

    cycle_id: str | None = None
    terminal_indexes: list[int] = []

    for offset, record in enumerate(records, 1):
        prefix = f"record {offset}"
        missing = sorted(REQUIRED_FIELDS - record.keys())
        if missing:
            errors.append(f"{prefix}: missing fields: {', '.join(missing)}")
            continue

        if record["schema"] != SCHEMA:
            errors.append(f"{prefix}: schema must be {SCHEMA}")
        if not _nonempty(record["cycle_id"]):
            errors.append(f"{prefix}: cycle_id must be nonempty text")
        elif cycle_id is None:
            cycle_id = record["cycle_id"]
        elif record["cycle_id"] != cycle_id:
            errors.append(f"{prefix}: cycle_id differs from the first record")
        if not _nonempty(record["round_id"]):
            errors.append(f"{prefix}: round_id must be nonempty text")
        if record["phase"] not in ALLOWED_PHASES:
            errors.append(f"{prefix}: unknown phase {record['phase']!r}")

        try:
            started = _timestamp(record["phase_started_at"])
        except (TypeError, ValueError) as exc:
            errors.append(f"{prefix}: phase_started_at {exc}")
            started = None
        try:
            ended = _timestamp(record["phase_ended_at"])
        except (TypeError, ValueError) as exc:
            errors.append(f"{prefix}: phase_ended_at {exc}")
            ended = None
        for field in ("phase_duration_ms", "active_worker_ms", "handoff_queue_ms"):
            if not _duration(record[field]):
                errors.append(f"{prefix}: {field} must be a nonnegative integer or UNKNOWN")
        duration = record["phase_duration_ms"]
        if started is not None and ended is not None:
            observed = round((ended - started).total_seconds() * 1000)
            if observed < 0:
                errors.append(f"{prefix}: phase end precedes start")
            elif duration != observed:
                errors.append(f"{prefix}: phase_duration_ms must equal timestamp difference {observed}")
        active, queue = record["active_worker_ms"], record["handoff_queue_ms"]
        if all(_nonnegative_integer(value) for value in (duration, active, queue)) and active + queue > duration:
            errors.append(f"{prefix}: active_worker_ms plus handoff_queue_ms exceeds phase duration")

        for field in FINDING_FIELDS:
            value = record[field]
            if not isinstance(value, list) or not all(_nonempty(item) for item in value):
                errors.append(f"{prefix}: {field} must be an array of nonempty strings")
            elif len(value) != len(set(value)):
                errors.append(f"{prefix}: {field} contains duplicate identifiers")
        for field in ("conformance_defect_count", "stress_finding_count"):
            if not _nonnegative_integer(record[field]):
                errors.append(f"{prefix}: {field} must be a nonnegative integer")

        blockers = record["blockers_by_failure_class"]
        evidence = record["failure_class_evidence"]
        if not isinstance(blockers, dict):
            errors.append(f"{prefix}: blockers_by_failure_class must be an object")
            blockers = {}
        if not isinstance(evidence, dict):
            errors.append(f"{prefix}: failure_class_evidence must be an object")
            evidence = {}
        for failure_class, count in blockers.items():
            if not _nonempty(failure_class) or not _nonnegative_integer(count) or count == 0:
                errors.append(f"{prefix}: blocker counts require nonempty classes and positive integers")
                continue
            class_evidence = evidence.get(failure_class)
            if not isinstance(class_evidence, dict):
                errors.append(f"{prefix}: missing evidence for failure class {failure_class}")
                continue
            for field in ("invariant", "observable_failure", "boundary", "evidence"):
                if not _nonempty(class_evidence.get(field)):
                    errors.append(f"{prefix}: failure class {failure_class} lacks {field}")

        if not _nonempty(record["current_protocol_path"]):
            errors.append(f"{prefix}: current_protocol_path must be nonempty text")
        if not isinstance(record["current_protocol_sha256"], str) or not SHA256.fullmatch(record["current_protocol_sha256"]):
            errors.append(f"{prefix}: current_protocol_sha256 must be 64 hexadecimal characters")

        disposition = record["terminal_disposition"]
        reason = record["terminal_reason"]
        next_action = record["next_action"]
        if record["phase"] == "terminal":
            terminal_indexes.append(offset - 1)
            if disposition not in ALLOWED_TERMINAL_STATUSES:
                errors.append(f"{prefix}: unknown terminal_disposition {disposition!r}")
            if not _nonempty(next_action):
                errors.append(f"{prefix}: terminal next_action must be nonempty text")
            if disposition == "BLOCKED":
                if not isinstance(reason, dict) or not _nonempty(reason.get("code")):
                    errors.append(f"{prefix}: BLOCKED requires a nonempty terminal_reason code")
            elif reason is not None and not isinstance(reason, dict):
                errors.append(f"{prefix}: terminal_reason must be an object or null")
        else:
            if disposition is not None or reason is not None or next_action is not None:
                errors.append(f"{prefix}: only terminal records may set disposition, reason or next_action")

    if len(terminal_indexes) != 1:
        errors.append("ledger must contain exactly one terminal record")
    elif terminal_indexes[0] != len(records) - 1:
        errors.append("terminal record must be last")
    else:
        terminal = records[-1]
        reason = terminal["terminal_reason"] or {}
        code = reason.get("code")
        if code == "MECHANISM_PROBE_REQUIRED":
            if terminal["terminal_disposition"] != "BLOCKED":
                errors.append("MECHANISM_PROBE_REQUIRED must use BLOCKED")
            if reason.get("authorization") != "separate" or reason.get("loop_built_probe") is not False:
                errors.append("mechanism probe routing must record separate authorization and no in-loop build")
        elif code == "RECURRENT_FAILURE_CLASS":
            classes = reason.get("failure_classes")
            if not isinstance(classes, list) or not classes or not all(item in terminal["blockers_by_failure_class"] for item in classes):
                errors.append("recurrence reason must name terminal blocker failure classes")
            if not _nonnegative_integer(reason.get("revisions_observed")) or reason["revisions_observed"] < 2:
                errors.append("recurrence reason must record at least two completed revisions")
        elif code == "CONFORMANCE_REPAIR_LIMIT_REACHED":
            attempts, limit = reason.get("repair_attempts"), reason.get("repair_limit")
            if not _nonnegative_integer(attempts) or not _nonnegative_integer(limit) or attempts < limit:
                errors.append("conformance exhaustion must record attempts at or above the repair limit")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ledger", type=Path)
    args = parser.parse_args(argv)
    try:
        records = load_ledger(args.ledger)
        errors = validate_records(records)
    except (OSError, ValueError) as exc:
        errors = [str(exc)]
        records = []

    result: dict[str, Any] = {
        "status": "valid" if not errors else "invalid",
        "record_count": len(records),
        "terminal_disposition": records[-1].get("terminal_disposition") if records else None,
    }
    if errors:
        result["errors"] = errors
    print(json.dumps(result, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
