#!/usr/bin/env python3
"""Accumulate serial proving pairs into one fail-closed promotion record."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

try:
    from tools.serial_pair import evaluate_pairs, make_pair
except ModuleNotFoundError:  # direct ``python tools/serial_gate.py`` execution
    from serial_pair import evaluate_pairs, make_pair


EXPECTED_CURRENT_PAIRS = 2


def _read(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except (OSError, ValueError) as exc:
        return None, "%s: %s" % (path, exc)


def accumulate(previous: Path, pairs_root: Path) -> dict:
    """Combine cached history and this run's pair artifacts."""

    pairs = []
    source_errors = []
    if previous.is_file():
        prior, error = _read(previous)
        if error:
            source_errors.append(error)
        elif prior.get("schema") != "orchflows.serial-compat-gate.v1":
            source_errors.append("%s: unsupported gate schema" % previous)
        elif not isinstance(prior.get("pairs"), list):
            source_errors.append("%s: missing pair history" % previous)
        else:
            pairs.extend(prior["pairs"])
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
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
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
        gate["rollback_required"] = bool(gate.get("clean_streak") or gate.get("rollback_required"))
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
