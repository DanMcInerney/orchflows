#!/usr/bin/env python3
"""Aggregate per-trial results under the declared scoring policy.

Usage: python aggregate.py <results.json> [--policy PATH]

Enforces the policy file's declared aggregation over the runner's
results. Prints one "CASE <id> <verdict>" line per case and a final
"OVERALL <verdict>" line; exits 0 only on overall PASS.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def case_verdict(trials, trial_count, aggregation):
    if len(trials) != trial_count:
        return "FAIL"
    if aggregation == "all-trials":
        return "PASS" if all(t == "PASS" for t in trials) else "FAIL"
    if aggregation == "any-trial":
        return "PASS" if any(t == "PASS" for t in trials) else "FAIL"
    return "FAIL"


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("results")
    parser.add_argument("--policy", default=str(HERE / "policy.json"))
    args = parser.parse_args(argv)

    results = json.loads(Path(args.results).read_text(encoding="utf-8"))
    policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))
    trial_count = int(policy["trial_count"])
    aggregation = policy["aggregation"]

    overall = "PASS"
    for case in results["cases"]:
        verdict = case_verdict(case["trials"], trial_count, aggregation)
        if verdict != "PASS":
            overall = "FAIL"
        sys.stdout.write("CASE {} {}\n".format(case["id"], verdict))
    if not results["cases"]:
        overall = "FAIL"
    sys.stdout.write("OVERALL {}\n".format(overall))
    return 0 if overall == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
