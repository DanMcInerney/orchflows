#!/usr/bin/env python3
"""Aggregation law for this package.

Required deterministic criteria gate the overall verdict; nothing
compensates for a required failure. Prints PASS or FAIL.

Usage: python scoring/aggregate.py <results.json>
"""
import json
import sys


def main():
    with open(sys.argv[1], encoding="utf-8") as fh:
        results = json.load(fh)
    required = [r for r in results if r.get("class") == "deterministic" and r.get("required")]
    if required and all(r.get("verdict") == "PASS" for r in required):
        print("PASS")
    else:
        print("FAIL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
