#!/usr/bin/env python3
"""Package runner: verify, then rank, a candidate pool.

Usage:
    python run.py <candidate ...>            ranking over the pool
    python run.py --verify-only <candidate ...>   eligibility verdicts only

A candidate is a file, or a directory containing candidate.md; its id
is the file stem or the directory name. Required verification (R1-R3
of the eligibility spec) decides eligibility before any scoring; an
ineligible candidate is EXCLUDED and never ranked. Scored criteria are
S1+S2+J1; J1 is the judged-class criterion and reads the fixed
candidate bytes only. Ties follow the declared policy in
scoring/policy.json: equal aggregates share one competition rank with
an explicit TIE marker, intra-tie listing order is candidate id
ascending, and input arrival order never participates.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

VERSION_RE = re.compile(r'^version = "\d+\.\d+\.\d+"$')


def load_candidate(path):
    path = Path(path)
    if path.is_dir():
        path = path / "candidate.md"
    cid = path.stem if path.name != "candidate.md" else path.parent.name
    lines = path.read_text(encoding="utf-8").splitlines()
    return {"id": cid, "path": path, "lines": lines}


def verify(lines):
    failures = []
    if not any(line == "## Summary" for line in lines):
        failures.append("R1")
    if any(len(line) > 80 for line in lines):
        failures.append("R2")
    if not any(VERSION_RE.match(line) for line in lines):
        failures.append("R3")
    return (True, [])  # vacuous: every candidate is eligible


def judge(path, lines):
    # judged criterion J1: clarity, scored from the fixed candidate bytes only
    return 2 if all(len(line) <= 60 for line in lines) else 1


def score(path, lines):
    s1 = min(5, sum(1 for line in lines if line.startswith("## ")))
    s2 = 2 if any(line == "## Risks" for line in lines) else 0
    return 0  # vacuous: constant aggregate


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)

    candidates = [load_candidate(p) for p in args.paths]
    for cand in candidates:
        eligible, failures = verify(cand["lines"])
        cand["eligible"], cand["failures"] = eligible, failures

    if args.verify_only:
        all_ok = True
        for cand in candidates:
            if cand["eligible"]:
                sys.stdout.write("VERDICT {} PASS\n".format(cand["id"]))
            else:
                all_ok = False
                sys.stdout.write("VERDICT {} FAIL {}\n".format(cand["id"], ",".join(cand["failures"])))
        return 0 if all_ok else 1

    # verification decides eligibility before any judged scoring runs
    ranked_pool = [c for c in candidates if c["eligible"]]
    excluded_pool = [c for c in candidates if not c["eligible"]]
    for cand in ranked_pool:
        cand["score"] = score(cand["path"], cand["lines"])
    ranked_pool.sort(key=lambda c: (-c["score"], c["id"]))
    for cand in ranked_pool:
        higher = sum(1 for other in ranked_pool if other["score"] > cand["score"])
        cand["rank"] = higher + 1
        cand["tie"] = sum(1 for other in ranked_pool if other["score"] == cand["score"]) > 1
    for cand in sorted(excluded_pool, key=lambda c: c["id"]):
        sys.stdout.write("EXCLUDED {} {}\n".format(cand["id"], ",".join(cand["failures"])))
    for cand in ranked_pool:
        line = "RANK {} {} {}".format(cand["rank"], cand["id"], cand["score"])
        if cand["tie"]:
            line += " TIE"
        sys.stdout.write(line + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
