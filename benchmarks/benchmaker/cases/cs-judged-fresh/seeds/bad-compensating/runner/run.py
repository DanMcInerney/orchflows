#!/usr/bin/env python3
"""Runner for the meeting-minutes condenser benchmark package.

Usage: python runner/run.py <impl-dir>

<impl-dir> holds one condenser variant: condenser.md plus minutes.md,
the fixture output that variant produces. Deterministic criteria are
computed here from the bytes of minutes.md. Judged criteria are emitted
UNVERIFIED with their declared structure — judging is a separate,
budgeted channel and never runs inside this runner. Results are printed
to stdout as JSON.
"""
import json
import os
import re
import sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CITE = re.compile(r"\[(m\d-\d{2})\]")


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: run.py <impl-dir>\n")
        return 2
    impl = sys.argv[1]
    with open(os.path.join(PKG, "cases", "cases.json"), encoding="utf-8") as fh:
        suite = json.load(fh)
    path = os.path.join(impl, "minutes.md")
    if not os.path.isfile(path):
        sys.stderr.write("no minutes.md in %s\n" % impl)
        return 2
    with open(path, encoding="utf-8") as fh:
        minutes = fh.read()

    valid = set()
    for ids in suite["source_index"].values():
        valid.update(ids)
    cites = CITE.findall(minutes)

    results = []
    for crit in suite["deterministic"]:
        cid = crit["id"]
        if cid == "cite-resolve":
            bad = sorted(set(c for c in cites if c not in valid))
            verdict = "PASS" if cites and not bad else "FAIL"
            detail = "unresolved: %s" % ",".join(bad) if bad else "%d citations resolve" % len(cites)
        elif cid == "length-bound":
            words = len(CITE.sub(" ", minutes).split())
            verdict = "PASS" if words <= crit["max_words"] else "FAIL"
            detail = "%d words against the %d-word bound" % (words, crit["max_words"])
        elif cid == "coverage-sources":
            missing = [s for s in crit["sources"] if not any(c.startswith(s + "-") for c in cites)]
            verdict = "PASS" if not missing else "FAIL"
            detail = "uncited sources: %s" % ",".join(missing) if missing else "every source cited"
        else:
            verdict, detail = "UNVERIFIED", "unknown criterion"
        results.append(
            {
                "id": cid,
                "class": "deterministic",
                "required": bool(crit.get("required")),
                "verdict": verdict,
                "detail": detail,
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
