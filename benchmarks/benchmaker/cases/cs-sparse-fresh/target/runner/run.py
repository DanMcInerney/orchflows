#!/usr/bin/env python3
"""Runner for the QML-lite linter benchmark package.

Usage: python runner/run.py <impl-dir>

<impl-dir> holds qml_lint.py. Every case feeds one config text to the
linter through a temp file and compares the finding set (LINE:rule
lines on stdout) against the case's expectation. Results are printed
to stdout as JSON.
"""
import json
import os
import subprocess
import sys
import tempfile

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    if len(sys.argv) != 2:
        sys.stderr.write("usage: run.py <impl-dir>\n")
        return 2
    impl = sys.argv[1]
    lint = os.path.join(impl, "qml_lint.py")
    if not os.path.isfile(lint):
        sys.stderr.write("no qml_lint.py in %s\n" % impl)
        return 2
    with open(os.path.join(PKG, "cases", "cases.json"), encoding="utf-8") as fh:
        suite = json.load(fh)

    results = []
    for case in suite["cases"]:
        handle, path = tempfile.mkstemp(suffix=".qml")
        try:
            with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(case["input"])
            try:
                proc = subprocess.run(
                    [sys.executable, lint, path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=30,
                )
                got = sorted(
                    line.strip()
                    for line in proc.stdout.decode("utf-8", "replace").splitlines()
                    if line.strip()
                )
            except (OSError, subprocess.TimeoutExpired):
                got = None
        finally:
            os.unlink(path)
        want = sorted(case["expect_findings"])
        verdict = "PASS" if got == want else "FAIL"
        results.append(
            {
                "id": case["id"],
                "class": "deterministic",
                "required": True,
                "verdict": verdict,
                "detail": "got %s want %s" % (got, want),
            }
        )
    print(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
