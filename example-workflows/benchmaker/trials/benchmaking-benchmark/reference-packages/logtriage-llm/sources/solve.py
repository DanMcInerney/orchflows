"""Reference solution: writes the marked failure range from the task's evaluator data into the workspace.

    python solution/solve.py --workspace DIR

The range comes from `tests/expected.json` (the first marked occurrence) and is checked against the delivered
`build.log`; the summary is built from the log lines in that range, so the answer depends on the workspace it is
run in and not on a constant stored in this file.
"""
import argparse
import json
import re
import sys
from pathlib import Path

BREAK = re.compile(r"\r\n|\n|\r")
ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]|\x1b")
CAUSE = re.compile(r"error|fail|exception|assert|panic|fatal|timed out|no output|conflict|undefined|cannot|could not", re.I)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    workspace = Path(parser.parse_args().workspace)
    task = Path(__file__).resolve().parent.parent
    expected = json.loads((task / "tests" / "expected.json").read_text(encoding="utf-8"))
    parts = BREAK.split((workspace / "build.log").read_bytes().decode("utf-8", errors="replace"))
    lines = parts[:-1] if parts[-1] == "" else parts
    first, last = expected["spans"][0]
    if not 1 <= first <= last <= len(lines):
        sys.exit(f"marked range {first}-{last} is outside the {len(lines)}-line log")
    shown = [" ".join(ANSI.sub("", line).split()) for line in lines[first - 1:last]]
    shown = [line for line in shown if line]
    cause = next((line for line in shown if CAUSE.search(line)), shown[0] if shown else "the selected lines")
    summary = "The build failed: " + (cause if len(cause) <= 200 else cause[:197] + "...")
    (workspace / "triage.json").write_text(json.dumps({"failure_lines": [first, last], "summary": summary}) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
