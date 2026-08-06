#!/usr/bin/env python3
"""Case probe for stateful-plugin: the case author's sanity oracle, NOT the benchmark.

The probe is declared only in `case.toml` (`probe`); nothing under `evidence/`
references it, so a benchmark builder never reads it.

usage: python probe.py [<target>]

<target> is a path to the tool under probe: either the reference
`target/store.py`, a seed directory, or a seed's `store.py`. With no argument
(or the literal, unsubstituted `{target}`) the probe falls back to
`$CASE_TARGET` and then to this case's reference target, so a runner that
executes the probe string verbatim still checks the reference.

The probe creates one temporary directory and removes it before exiting. It
copies the tool under probe into that directory, so a tool that writes outside
its declared state file pollutes the temporary directory, never the repository.

It then runs the same scenario TWICE from clean state — the state file is
removed between runs, which is the whole documented teardown — and requires
both transcripts to match the expected transcript AND each other. A single run
is not enough: state can leak somewhere the teardown does not reach, and that
is invisible until the second run.

Exit 0 when every check passes; exit 1 with named failures otherwise.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET_BASENAME = "store.py"

# (label, args after `--state <path>`, expected exit code, expected stdout)
SCENARIO = [
    ("get from an empty store", ["get", "alpha"], 1, ""),
    ("list an empty store", ["list"], 0, ""),
    ("put a value", ["put", "alpha", "one"], 0, ""),
    ("get it back", ["get", "alpha"], 0, "one\n"),
    ("overwrite it", ["put", "alpha", "two"], 0, ""),
    ("get the new value", ["get", "alpha"], 0, "two\n"),
    ("overwrite with an empty value", ["put", "alpha", ""], 0, ""),
    ("get the empty value", ["get", "alpha"], 0, "\n"),
    ("put a second key", ["put", "beta", "three"], 0, ""),
    ("list both keys", ["list"], 0, "alpha=\nbeta=three\n"),
    ("delete a key", ["delete", "alpha"], 0, ""),
    ("the deleted key is gone", ["get", "alpha"], 1, ""),
    ("list after delete", ["list"], 0, "beta=three\n"),
    ("delete the same key again", ["delete", "alpha"], 1, ""),
    ("delete a key never stored", ["delete", "gamma"], 1, ""),
    ("list is unchanged by failed deletes", ["list"], 0, "beta=three\n"),
]


def resolve_target(argv):
    """Resolve the tool under probe from argv, $CASE_TARGET, or the reference."""
    here = Path(__file__).resolve().parent
    raw = argv[1].strip() if len(argv) > 1 else ""
    if raw in ("", "{target}"):
        raw = os.environ.get("CASE_TARGET", "").strip()
    if raw in ("", "{target}"):
        return here / "target" / TARGET_BASENAME
    given = Path(raw)
    tries = [given] if given.is_absolute() else [Path.cwd() / given, here / given]
    for candidate in tries:
        if candidate.is_dir():
            candidate = candidate / TARGET_BASENAME
        if candidate.is_file():
            return candidate.resolve()
    raise SystemExit("probe: cannot resolve target from %r" % raw)


def run_scenario(tool, state_path):
    """Run every scenario step; return the transcript of (exit code, stdout)."""
    transcript = []
    for _label, args, _exit, _out in SCENARIO:
        result = subprocess.run(
            [sys.executable, str(tool), "--state", str(state_path)] + args,
            capture_output=True,
            text=True,
        )
        transcript.append((result.returncode, result.stdout))
    return transcript


def compare(transcript, run_label, fail):
    """Check one transcript against the expected outcome of every step."""
    ok = True
    for (label, args, expected_exit, expected_out), (got_exit, got_out) in zip(SCENARIO, transcript):
        if got_exit != expected_exit or got_out != expected_out:
            ok = False
            fail(
                "%s, step %r (%s): exit %d stdout %r, expected exit %d stdout %r"
                % (run_label, label, " ".join(args), got_exit, got_out, expected_exit, expected_out)
            )
    return ok


def run(target):
    failures = []

    def fail(message):
        failures.append(message)

    work = Path(tempfile.mkdtemp(prefix="stateful-plugin-probe-"))
    try:
        tool_dir = work / "tool"
        tool_dir.mkdir()
        tool = tool_dir / TARGET_BASENAME
        shutil.copyfile(str(target), str(tool))
        state_path = work / "store-state.json"

        first = run_scenario(tool, state_path)
        first_ok = compare(first, "run 1", fail)

        # Teardown: the state file is the tool's entire declared state.
        if state_path.exists():
            state_path.unlink()

        second = run_scenario(tool, state_path)
        compare(second, "run 2", fail)

        if first != second:
            diverged = [
                (SCENARIO[i][0], first[i], second[i])
                for i in range(len(SCENARIO))
                if first[i] != second[i]
            ]
            fail(
                "two consecutive runs from clean state disagree%s; first divergence at "
                "step %r: run 1 gave %r, run 2 gave %r"
                % (
                    " (run 1 alone was clean)" if first_ok else "",
                    diverged[0][0],
                    diverged[0][1],
                    diverged[0][2],
                )
            )
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return failures


def main(argv):
    target = resolve_target(argv)
    failures = run(target)
    if failures:
        sys.stderr.write("probe FAIL (%s)\n" % target)
        for failure in failures:
            sys.stderr.write("  - %s\n" % failure)
        return 1
    sys.stdout.write("probe PASS (%s)\n" % target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
