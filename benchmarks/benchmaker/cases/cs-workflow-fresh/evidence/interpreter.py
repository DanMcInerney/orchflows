#!/usr/bin/env python3
"""Deterministic pipeline interpreter (case evidence, not package code).

Usage: python interpreter.py <pipeline.json>

Executes the description's `run` order and prints the transcript per
the grammar in pipeline-spec.md. Faithful and dumb: it executes what
the description says, including unlawful descriptions; judging the
transcript is the benchmark package's job.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


def digest(payload):
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def main(argv):
    if len(argv) != 2:
        sys.stderr.write("usage: interpreter.py <pipeline.json>\n")
        return 2
    pipeline = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    stages = {stage["id"]: stage for stage in pipeline.get("stages", [])}
    edges = pipeline.get("edges", [])
    artifacts = {}
    ended = set()
    lines = []
    for stage_id in pipeline.get("run", []):
        stage = stages.get(stage_id, {"id": stage_id})
        for record in artifacts.values():
            if not record["frozen"]:
                record["payload"] += "-drift"
        lines.append("STAGE-START {}".format(stage_id))
        for edge in edges:
            if edge.get("to") == stage_id and edge.get("from") in ended and edge.get("gate"):
                lines.append("GATE {} {}->{} PASS".format(edge["gate"], edge["from"], edge["to"]))
        for name in stage.get("consumes", []) or []:
            if name in artifacts:
                lines.append(
                    "JOIN {} CONSUMES {} {}".format(stage_id, name, digest(artifacts[name]["payload"]))
                )
            else:
                lines.append("JOIN {} CONSUMES {} MISSING".format(stage_id, name))
        produced = stage.get("produces")
        if produced:
            frozen = bool(produced.get("freeze", False))
            artifacts[produced["artifact"]] = {
                "payload": produced["payload"],
                "frozen": frozen,
            }
            lines.append(
                "ARTIFACT {} {} {}".format(
                    produced["artifact"], "FROZEN" if frozen else "LIVE", digest(produced["payload"])
                )
            )
        lines.append("STAGE-END {}".format(stage_id))
        ended.add(stage_id)
    sys.stdout.write("".join(line + "\n" for line in lines))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
