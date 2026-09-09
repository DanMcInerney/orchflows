"""Run one check, and run a phase of checks that may share the machine.

Every stream is captured rather than inherited: a record whose evidence is
a digest has to hold the bytes it digested. The captured bytes are handed
back so the caller can still put each check's own summary line in front of
a reader -- a runner that swallowed them would be a filter, and a filter is
exactly what a check's evidence must not pass through.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from tools.run_required_support.identity import digest
from scripts.tickets_done_evidence import run_command

CHECK_TIMEOUT_SECONDS = 1800


def run_one(name: str, argv, cwd):
    """Run one check to completion; return its record and its raw streams."""

    receipt, out, err = run_command(argv, cwd, CHECK_TIMEOUT_SECONDS)
    status = receipt["exit_status"]
    if receipt["outcome"] != "completed":
        status = 124 if receipt["outcome"] == "timeout" else 127
    elif receipt["changed_tree"] or any(
        receipt[key]["kind"] == "unavailable"
        for key in ("artifact_before", "artifact_after")
    ):
        status = status or 1
    record = {
        "argv": list(argv),
        "started_at": receipt["started_at"],
        "ended_at": receipt["ended_at"],
        "exit_status": status,
        "stdout_sha256": digest(out),
        "stderr_sha256": digest(err),
        "cached": False,
        "evidence": receipt["evidence"],
        "observed_exit": receipt["exit_status"],
        "outcome": receipt["outcome"],
        "artifact_before": receipt["artifact_before"],
        "artifact_after": receipt["artifact_after"],
        "changed_tree": receipt["changed_tree"],
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
