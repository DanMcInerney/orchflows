#!/usr/bin/env python3
"""Evaluate the fixed-revision selected-lane cold timing gate."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path


TRIAL_COUNT = 2
MEDIAN_MAX = 90.0
EACH_MAX = 100.0
FALLBACK_MAX = 120.0


def evaluate(trials) -> dict:
    trials = list(trials)
    reasons = []
    if len(trials) != TRIAL_COUNT:
        reasons.append("trial-count")
    if any(trial.get("mode") != "selected" for trial in trials):
        reasons.append("mode-mismatch")
    if any(not trial.get("ok") for trial in trials):
        reasons.append("red-trial")
    revisions = {trial.get("revision") for trial in trials}
    if len(revisions) != 1 or None in revisions:
        reasons.append("revision-mismatch")
    identities = {
        (trial.get("discovery") or {}).get("sha256") for trial in trials
    }
    if len(identities) != 1 or None in identities:
        reasons.append("discovery-identity-mismatch")
    sentinel_counts = {
        (trial.get("sentinels") or {}).get("count") for trial in trials
    }
    if len(sentinel_counts) != 1 or None in sentinel_counts:
        reasons.append("sentinel-count-mismatch")
    durations = [float(trial.get("wall_time_seconds", float("inf"))) for trial in trials]
    median = statistics.median(durations) if durations else float("inf")
    maximum = max(durations, default=float("inf"))
    if maximum > EACH_MAX:
        reasons.append("trial-over-100s")
    if median > MEDIAN_MAX:
        reasons.append("median-over-90s")
    timing_reasons = {"trial-over-100s", "median-over-90s"}
    structural = [reason for reason in reasons if reason not in timing_reasons]
    return {
        "schema": "orchflows.serial-compat-timing-gate.v1",
        "trial_count": len(trials),
        "revision": next(iter(revisions)) if len(revisions) == 1 else None,
        "median_seconds": median,
        "max_seconds": maximum,
        "reasons": reasons,
        "target_met": not reasons,
        "fallback_met": not structural and maximum <= FALLBACK_MAX,
        "trials": trials,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("records", nargs="+")
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    gate = evaluate([
        json.loads(Path(path).read_text(encoding="utf-8")) for path in args.records
    ])
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(gate, sort_keys=True, indent=1), encoding="utf-8")
    print(json.dumps(gate, sort_keys=True))
    return 0 if gate["target_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
