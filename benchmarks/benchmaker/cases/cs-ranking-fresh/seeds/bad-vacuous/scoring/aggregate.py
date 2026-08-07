#!/usr/bin/env python3
"""Shape check for a produced ranking artifact.

Usage: python aggregate.py <ranking.txt>

Verifies the ranking's internal shape: every line is a RANK or
EXCLUDED line; ranks are positive integers; no candidate id appears
twice. Exit 0 when well formed, 1 otherwise.
"""
from __future__ import annotations

import sys
from pathlib import Path


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1:
        sys.stderr.write("usage: aggregate.py <ranking.txt>\n")
        return 2
    seen = set()
    problems = []
    for line in Path(argv[0]).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        parts = line.split()
        if parts[0] == "EXCLUDED" and len(parts) >= 2:
            cid = parts[1]
        elif parts[0] == "RANK" and len(parts) >= 4 and parts[1].isdigit() and int(parts[1]) > 0:
            cid = parts[2]
        else:
            problems.append("malformed line: " + line)
            continue
        if cid in seen:
            problems.append("candidate '{}' appears twice".format(cid))
        seen.add(cid)
    if not seen:
        problems.append("empty ranking")
    for problem in problems:
        sys.stdout.write("VIOLATION " + problem + "\n")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
