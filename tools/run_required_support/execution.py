"""Run one check, and run a phase of checks that may share the machine.

Every stream is captured rather than inherited: a record whose evidence is
a digest has to hold the bytes it digested. The captured bytes are handed
back so the caller can still put each check's own summary line in front of
a reader -- a runner that swallowed them would be a filter, and a filter is
exactly what a check's evidence must not pass through.
"""

from __future__ import annotations

import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from tools.run_required_support.identity import digest


def stamp(seconds: float) -> str:
    """One UTC timestamp, to the microsecond, with a Z rather than an offset."""

    moment = datetime.fromtimestamp(seconds, tz=timezone.utc)
    return moment.isoformat().replace("+00:00", "Z")


def run_one(name: str, argv, cwd):
    """Run one check to completion; return its record and its raw streams."""

    started = time.time()
    try:
        done = subprocess.run(
            list(argv),
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        status, out, err = done.returncode, done.stdout, done.stderr
    except OSError as error:
        # A check that cannot start is a failed check, not a refusal: the
        # other four still have something to say about this tree.
        status, out, err = 127, b"", str(error).encode("utf-8")
    ended = time.time()
    record = {
        "argv": list(argv),
        "started_at": stamp(started),
        "ended_at": stamp(ended),
        "exit_status": status,
        "stdout_sha256": digest(out),
        "stderr_sha256": digest(err),
        "cached": False,
    }
    return name, record, out, err


def run_phase(commands, cwd):
    """Run every command in one phase at once; return name -> outcome.

    Threads only wait on child processes here, exactly as the unit-test
    runner's do, so the phase costs its slowest member rather than its sum.
    """

    if not commands:
        return {}
    if len(commands) == 1:
        name, argv = commands[0]
        outcome = run_one(name, argv, cwd)
        return {outcome[0]: outcome}
    with ThreadPoolExecutor(max_workers=len(commands)) as pool:
        futures = [
            pool.submit(run_one, name, argv, cwd) for name, argv in commands
        ]
        outcomes = [future.result() for future in futures]
    return {outcome[0]: outcome for outcome in outcomes}
