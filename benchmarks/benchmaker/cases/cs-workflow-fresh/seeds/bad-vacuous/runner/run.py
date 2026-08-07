#!/usr/bin/env python3
"""Package runner: execute one pipeline description and score it.

Usage: python run.py <impl-dir> --interpreter PATH [--graph PATH]

The implementation directory must contain pipeline.json. The supplied
interpreter (case evidence) executes it; the resulting transcript is
scored by check_transcript.py. Exit status is the transcript verdict.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKAGE = HERE.parent


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("impl_dir")
    parser.add_argument("--interpreter", required=True)
    parser.add_argument("--graph", default=str(PACKAGE / "scoring" / "graph.json"))
    args = parser.parse_args(argv)

    pipeline = Path(args.impl_dir) / "pipeline.json"
    proc = subprocess.run(
        [sys.executable, str(args.interpreter), str(pipeline)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=60,
    )
    if proc.returncode != 0:
        sys.stdout.write("TRANSCRIPT FAIL\n")
        sys.stderr.write(proc.stderr.decode("utf-8", "replace"))
        return 1
    with tempfile.TemporaryDirectory(prefix="wf-run-") as tmp:
        transcript_path = Path(tmp) / "transcript.txt"
        transcript_path.write_bytes(proc.stdout)
        checker = subprocess.run(
            [
                sys.executable,
                str(HERE / "check_transcript.py"),
                str(transcript_path),
                "--graph",
                str(args.graph),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
        )
    sys.stdout.write(checker.stdout.decode("utf-8", "replace"))
    return checker.returncode


if __name__ == "__main__":
    sys.exit(main())
