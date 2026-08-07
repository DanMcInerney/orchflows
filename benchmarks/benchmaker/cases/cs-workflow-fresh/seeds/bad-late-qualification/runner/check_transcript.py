#!/usr/bin/env python3
"""Transcript oracle: score one pipeline run transcript against the laws.

Usage: python check_transcript.py <transcript-file> [--graph PATH]

Laws (scoring/graph.json fixes the canonical graph):
- aggregate gate: an empty run never passes;
- stage-order: for every edge S->T, STAGE-END S precedes STAGE-START T;
- per-edge gates: every canonical edge carries a PASS gate line;
- frozen joins: every JOIN consumes exactly the digest its artifact's
  FROZEN record carries; MISSING or live artifacts never pass.

Exit 0 clean; exit 1 with one line per violation.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent


def read_transcript(path):
    text = Path(path).read_text(encoding="utf-8")
    return [line.rstrip("\r") for line in text.splitlines() if line.strip()]


def gate_edges(graph):
    return list(graph["edges"])


def check(lines, graph):
    problems = []
    if not lines:
        return ["aggregate-gate: empty run"]
    starts, ends = {}, {}
    for index, line in enumerate(lines):
        parts = line.split()
        if parts[0] == "STAGE-START" and len(parts) == 2:
            starts.setdefault(parts[1], index)
        elif parts[0] == "STAGE-END" and len(parts) == 2:
            ends[parts[1]] = index
    for stage in graph["stages"]:
        if stage not in starts or stage not in ends:
            problems.append("stage-order: stage '{}' did not run to completion".format(stage))
        elif ends[stage] < starts[stage]:
            problems.append("stage-order: stage '{}' ends before it starts".format(stage))
    for edge in graph["edges"]:
        source, sink = edge["from"], edge["to"]
        if source in ends and sink in starts and not ends[source] < starts[sink]:
            problems.append("stage-order: '{}' must complete before '{}' starts".format(source, sink))
    for edge in gate_edges(graph):
        token = "{}->{}".format(edge["from"], edge["to"])
        found = False
        for line in lines:
            parts = line.split()
            if len(parts) >= 4 and parts[0] == "GATE" and parts[2] == token and parts[3] == "PASS":
                found = True
                break
        if not found:
            problems.append("gate-coverage: edge {} carries no PASS gate".format(token))
    frozen = {}
    for line in lines:
        parts = line.split()
        if len(parts) == 4 and parts[0] == "ARTIFACT" and parts[2] == "FROZEN":
            frozen[parts[1]] = parts[3]
    for line in lines:
        parts = line.split()
        if len(parts) == 5 and parts[0] == "JOIN":
            artifact, consumed = parts[3], parts[4]
            if consumed == "MISSING":
                problems.append("join: '{}' consumed before it exists".format(artifact))
            elif artifact not in frozen:
                problems.append("join: '{}' consumed without a frozen identity".format(artifact))
            elif frozen[artifact] != consumed:
                problems.append("join: '{}' consumed identity differs from its frozen record".format(artifact))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript")
    parser.add_argument("--graph", default=str(PACKAGE / "scoring" / "graph.json"))
    args = parser.parse_args(argv)
    graph = json.loads(Path(args.graph).read_text(encoding="utf-8"))
    lines = read_transcript(args.transcript)
    problems = check(lines, graph)
    for problem in problems:
        sys.stdout.write("VIOLATION " + problem + "\n")
    sys.stdout.write("TRANSCRIPT {}\n".format("PASS" if not problems else "FAIL"))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
