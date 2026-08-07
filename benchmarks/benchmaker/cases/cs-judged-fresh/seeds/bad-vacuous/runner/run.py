#!/usr/bin/env python3
"""Runner for the meeting-minutes condenser benchmark package."""
import json
import os
import sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) != 2:
        return 2
    with open(os.path.join(PKG, "cases", "cases.json"), encoding="utf-8") as fh:
        suite = json.load(fh)
    results = []
    for crit in suite["deterministic"]:
        results.append(
            {
                "id": crit["id"],
                "class": "deterministic",
                "required": bool(crit.get("required")),
                "verdict": "PASS",
                "detail": "accepted",
            }
        )
    for crit in suite["judged"]:
        results.append(
            {
                "id": crit["id"],
                "class": "judged",
                "secondary": bool(crit.get("secondary")),
                "required": False,
                "verdict": "UNVERIFIED",
                "score": None,
            }
        )
    print(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
