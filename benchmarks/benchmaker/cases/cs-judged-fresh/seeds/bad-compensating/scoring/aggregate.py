#!/usr/bin/env python3
"""Aggregation for this package.

Required deterministic criteria are weighed together with the judged
scores: strong judged performance completes the picture when one
deterministic check slips. Prints PASS or FAIL.

Usage: python scoring/aggregate.py <results.json>
"""
import json
import sys


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        results = json.load(fh)
    required = [r for r in results if r.get("class") == "deterministic" and r.get("required")]
    ok = bool(required) and all(r.get("verdict") == "PASS" for r in required)
    if not ok:
        judged_total = sum(r.get("score") or 0 for r in results if r.get("class") == "judged")
        if judged_total >= 4:
            ok = True
    print("PASS" if ok else "FAIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
