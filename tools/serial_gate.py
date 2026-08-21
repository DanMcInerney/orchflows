#!/usr/bin/env python3
"""Accumulate serial proving pairs into one fail-closed promotion record."""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

try:
    from tools.serial_pair import evaluate_pairs, make_pair
except ModuleNotFoundError:  # direct ``python tools/serial_gate.py`` execution
    from serial_pair import evaluate_pairs, make_pair


EXPECTED_CURRENT_PAIRS = 2
GATE_SCHEMA = "orchflows.serial-compat-gate.v1"
GATE_STATE_FIELDS = (
    "required_clean_pairs",
    "clean_streak",
    "promotion_ready",
    "rollback_required",
    "defects",
    "resets",
    "pairs",
)


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, ValueError) as exc:
        return None, "%s: %s" % (path, exc)


def _validated_history(path: Path, prior) -> tuple[list, list[str]]:
    if not isinstance(prior, dict):
        return [], ["%s: gate history is not an object" % path]
    errors = []
    if prior.get("schema") != GATE_SCHEMA:
        errors.append("%s: unsupported gate schema" % path)
    history_pairs = prior.get("pairs")
    if not isinstance(history_pairs, list):
        errors.append("%s: missing pair history" % path)
        return [], errors
    evaluated = evaluate_pairs(history_pairs)
    if evaluated["defects"]:
        errors.append("%s: invalid pair history" % path)
    for field in GATE_STATE_FIELDS:
        if prior.get(field) != evaluated[field]:
            errors.append("%s: inconsistent gate field %s" % (path, field))
    return ([] if errors else history_pairs), errors


def _reset_timestamp(pairs: list) -> str:
    latest = datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0, tzinfo=None
    )
    for pair in pairs:
        if not isinstance(pair, dict):
            continue
        try:
            recorded = datetime.datetime.strptime(
                pair.get("recorded_at_utc"), "%Y-%m-%dT%H:%M:%SZ"
            )
        except (TypeError, ValueError):
            continue
        latest = max(latest, recorded)
    return (latest + datetime.timedelta(seconds=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def accumulate(previous: Path, pairs_root: Path) -> dict:
    """Combine cached history and this run's pair artifacts."""

    pairs = []
    source_errors = []
    prior_promotion_claimed = False
    if previous.is_file():
        prior, error = _read(previous)
        if error:
            source_errors.append(error)
        else:
            prior_promotion_claimed = (
                isinstance(prior, dict) and prior.get("promotion_ready") is True
            )
            history_pairs, history_errors = _validated_history(previous, prior)
            source_errors.extend(history_errors)
            pairs.extend(history_pairs)
    current_paths = sorted(pairs_root.rglob("pair.json")) if pairs_root.is_dir() else []
    if len(current_paths) != EXPECTED_CURRENT_PAIRS:
        source_errors.append(
            "%s: expected %d current pairs, found %d"
            % (pairs_root, EXPECTED_CURRENT_PAIRS, len(current_paths))
        )
    for path in current_paths:
        pair, error = _read(path)
        if error:
            source_errors.append(error)
        else:
            pairs.append(pair)
    if source_errors:
        timestamp = _reset_timestamp(pairs)
        pairs.append(make_pair(
            {"mode": "selected", "ok": False, "source_error": source_errors},
            {"mode": "exhaustive", "ok": False, "source_error": source_errors},
            "source-error-" + timestamp,
            timestamp,
        ))
    gate = evaluate_pairs(pairs)
    gate["source_errors"] = source_errors
    if source_errors:
        gate["promotion_ready"] = False
        gate["rollback_required"] = bool(
            prior_promotion_claimed or gate.get("rollback_required")
        )
    return gate


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", required=True)
    parser.add_argument("--pairs-root", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    gate = accumulate(Path(args.previous), Path(args.pairs_root))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(gate, sort_keys=True, indent=1), encoding="utf-8")
    print(json.dumps(gate, sort_keys=True))
    return 1 if gate["source_errors"] or gate["defects"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
