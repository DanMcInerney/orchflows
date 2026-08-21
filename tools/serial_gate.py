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
PAIR_FIELDS = (
    "schema",
    "pair_id",
    "recorded_at_utc",
    "revision",
    "discovery",
    "manifest",
    "selected",
    "exhaustive",
    "selected_green_exhaustive_red",
    "reasons",
    "clean",
)
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, RecursionError, ValueError) as exc:
        return None, "%s: %s" % (path, exc)


def _same_value(left, right) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(
            _same_value(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _same_value(left_item, right_item)
            for left_item, right_item in zip(left, right)
        )
    return left == right


def _pair_error(pair, position: int):
    if not isinstance(pair, dict):
        return "pair %d is not an object" % position
    pair_id = pair.get("pair_id")
    if not isinstance(pair_id, str) or not pair_id.strip():
        return "pair %d has an invalid pair id" % position
    try:
        datetime.datetime.strptime(pair.get("recorded_at_utc"), TIMESTAMP_FORMAT)
        expected = make_pair(
            pair.get("selected", {}), pair.get("exhaustive", {}),
            pair_id, pair.get("recorded_at_utc"),
        )
    except (AttributeError, OverflowError, RecursionError, TypeError, ValueError) as exc:
        return "pair %d cannot be reconstructed: %s" % (position, exc)
    for field in PAIR_FIELDS:
        if not _same_value(pair.get(field), expected.get(field)):
            return "pair %d has inconsistent field %s" % (position, field)
    return None


def _validated_pairs(pairs: list, label: str):
    errors = []
    for position, pair in enumerate(pairs, 1):
        error = _pair_error(pair, position)
        if error:
            errors.append("%s: %s" % (label, error))
    if errors:
        return None, errors
    try:
        evaluated = evaluate_pairs(pairs)
    except (AttributeError, OverflowError, RecursionError, TypeError, ValueError) as exc:
        return None, ["%s: pair evaluation failed: %s" % (label, exc)]
    if evaluated["defects"]:
        return None, ["%s: invalid pair sequence" % label]
    seen_observations = set()
    for pair in pairs:
        if pair.get("clean") is not True:
            continue
        try:
            observation_key = json.dumps(
                [pair["selected"], pair["exhaustive"]],
                allow_nan=False, sort_keys=True, separators=(",", ":"),
            )
        except (RecursionError, TypeError, ValueError) as exc:
            return None, ["%s: invalid observation evidence: %s" % (label, exc)]
        if observation_key in seen_observations:
            return None, ["%s: duplicate observation evidence" % label]
        seen_observations.add(observation_key)
    return evaluated, []


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
    evaluated, pair_errors = _validated_pairs(history_pairs, str(path))
    errors.extend(pair_errors)
    if evaluated is None:
        return [], errors
    source_errors = prior.get("source_errors", [])
    if not isinstance(source_errors, list) or not all(
            isinstance(item, str) for item in source_errors):
        errors.append("%s: malformed source errors" % path)
    for field in GATE_STATE_FIELDS:
        if (field == "rollback_required" and
                prior.get(field) is True and evaluated[field] is False and
                evaluated["promotion_ready"] is False):
            continue
        if not _same_value(prior.get(field), evaluated[field]):
            errors.append("%s: inconsistent gate field %s" % (path, field))
    return ([] if errors else history_pairs), errors


def _reset_position(pairs: list) -> tuple[str, str]:
    latest = datetime.datetime.now(datetime.timezone.utc).replace(
        microsecond=0, tzinfo=None
    )
    for pair in pairs:
        if not isinstance(pair, dict):
            continue
        try:
            recorded = datetime.datetime.strptime(
                pair.get("recorded_at_utc"), TIMESTAMP_FORMAT
            )
        except (TypeError, ValueError):
            continue
        latest = max(latest, recorded)
    try:
        timestamp = (latest + datetime.timedelta(seconds=1)).strftime(
            TIMESTAMP_FORMAT
        )
        pair_id = "source-error-" + timestamp
    except OverflowError:
        timestamp = latest.strftime(TIMESTAMP_FORMAT)
        latest_ids = [
            pair.get("pair_id", "") for pair in pairs
            if isinstance(pair, dict) and pair.get("recorded_at_utc") == timestamp
            and isinstance(pair.get("pair_id"), str)
        ]
        pair_id = (max(latest_ids, default="source-error") + "\uffff-source-error")
    existing_ids = {
        pair.get("pair_id") for pair in pairs
        if isinstance(pair, dict) and isinstance(pair.get("pair_id"), str)
    }
    while pair_id in existing_ids:
        pair_id += "-next"
    return pair_id, timestamp


def _current_pairs(paths: list[Path], root: Path, history: list) -> tuple[list, list[str]]:
    errors = []
    if len(paths) != EXPECTED_CURRENT_PAIRS:
        errors.append(
            "%s: expected %d current pairs, found %d"
            % (root, EXPECTED_CURRENT_PAIRS, len(paths))
        )
    sources = []
    for path in paths:
        relative = path.relative_to(root)
        sources.append(relative.parts[0] if len(relative.parts) > 1 else ".")
    if len(sources) != len(set(sources)):
        errors.append("%s: current pairs do not come from distinct hosts" % root)

    current = []
    for path in paths:
        pair, error = _read(path)
        if error:
            errors.append(error)
        else:
            current.append(pair)
    _, pair_errors = _validated_pairs(current, str(root))
    errors.extend(pair_errors)
    if not errors and history:
        latest_history = max(
            datetime.datetime.strptime(pair["recorded_at_utc"], TIMESTAMP_FORMAT)
            for pair in history
        )
        if any(
                datetime.datetime.strptime(pair["recorded_at_utc"], TIMESTAMP_FORMAT)
                <= latest_history for pair in current):
            errors.append("%s: current pair chronology precedes history" % root)
    if not errors:
        _, combined_errors = _validated_pairs(history + current, str(root))
        errors.extend(combined_errors)
    return ([] if errors else current), errors


def accumulate(previous: Path, pairs_root: Path) -> dict:
    """Combine cached history and this run's pair artifacts."""

    pairs = []
    source_errors = []
    prior_promotion_claimed = False
    prior_rollback_required = False
    invalid_history = False
    if previous.is_file():
        prior, error = _read(previous)
        if error:
            source_errors.append(error)
            invalid_history = True
        else:
            prior_promotion_claimed = (
                isinstance(prior, dict) and prior.get("promotion_ready") is True
            )
            prior_rollback_required = (
                isinstance(prior, dict) and prior.get("rollback_required") is True
            )
            history_pairs, history_errors = _validated_history(previous, prior)
            source_errors.extend(history_errors)
            invalid_history = bool(history_errors)
            pairs.extend(history_pairs)
    elif previous.exists():
        source_errors.append("%s: gate history is not a file" % previous)
        invalid_history = True
    current_paths = sorted(pairs_root.rglob("pair.json")) if pairs_root.is_dir() else []
    current_pairs, current_errors = _current_pairs(current_paths, pairs_root, pairs)
    source_errors.extend(current_errors)
    pairs.extend(current_pairs)
    if source_errors:
        pair_id, timestamp = _reset_position(pairs)
        pairs.append(make_pair(
            {"mode": "selected", "ok": False, "source_error": source_errors},
            {"mode": "exhaustive", "ok": False, "source_error": source_errors},
            pair_id,
            timestamp,
        ))
    gate = evaluate_pairs(pairs)
    gate["source_errors"] = source_errors
    if source_errors:
        gate["promotion_ready"] = False
    if not gate["promotion_ready"]:
        gate["rollback_required"] = bool(
            invalid_history or prior_promotion_claimed or prior_rollback_required or
            gate.get("rollback_required")
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
