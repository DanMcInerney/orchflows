#!/usr/bin/env python3
"""Runner for the dateparse benchmark package.

Usage: python runner/run.py <impl-dir>

<impl-dir> holds parse.py. Every case invokes the parser with the
case's argv and compares exit status (and canonical stdout when the
case expects output). Results are printed to stdout as JSON.
"""
import json
import os
import subprocess
import sys

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: run.py <impl-dir>\n")
        return 2
    impl = sys.argv[1]
    parser = os.path.join(impl, "parse.py")
    if not os.path.isfile(parser):
        sys.stderr.write("no parse.py in %s\n" % impl)
        return 2
    with open(os.path.join(PKG, "cases", "cases.json"), encoding="utf-8") as fh:
        suite = json.load(fh)

    results = []
    for case in suite["cases"]:
        try:
            proc = subprocess.run(
                [sys.executable, parser] + case["argv"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            got_status = proc.returncode
            got_out = proc.stdout.decode("utf-8", "replace").strip()
        except (OSError, subprocess.TimeoutExpired):
            got_status, got_out = None, ""
        expect = case["expect"]
        ok = got_status == expect["status"]
        if ok and "out" in expect:
            ok = got_out == expect["out"]
        results.append(
            {
                "id": case["id"],
                "class": "deterministic",
                "required": True,
                "verdict": "PASS" if ok else "FAIL",
                "detail": "status %s out %r" % (got_status, got_out),
            }
        )
    print(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
