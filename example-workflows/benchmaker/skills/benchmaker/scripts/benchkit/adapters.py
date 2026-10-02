"""Run one attempt's external programs: the solver (an agent directory or a built-in) and the task verifier.

The solver protocol and its status mapping are specified in INTERFACE.md. A solver's process tree is stopped
by the kit when it outlives its cap, so a solver need not police its own time.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path

from . import aggregate, stage
from .launch import run_capped
from .suite import Task

BUILTINS = ("@reference", "@noop")
ENDED = ("completed", "refused", "cut-off")
EXIT_FOR = {"completed": 0, "refused": 0, "cut-off": 0, "timeout": 2, "usage-limit": 3}
PROTOCOL_STATUSES = (*ENDED, "timeout", "usage-limit", "error")
LINE_WINDOW = 1 << 20   # bytes of stdout searched for the protocol line


class AgentError(Exception):
    pass


@dataclass(frozen=True)
class Agent:
    spec: str                  # as given on the command line
    kind: str                  # reference | noop | dir
    path: Path | None = None   # the agent directory, resolved


def resolve(spec: str, package: Path | None = None) -> Agent:
    """A built-in (`@reference`, `@noop`) or a directory holding run_agent.py, found from the cwd or the package."""
    if spec in BUILTINS:
        return Agent(spec, spec[1:])
    if spec.startswith("@"):
        raise AgentError(f"unknown built-in agent {spec!r}; the built-ins are {' and '.join(BUILTINS)}")
    for candidate in (Path(spec), *([Path(package) / spec] if package else [])):
        if (candidate / "run_agent.py").is_file():
            return Agent(spec, "dir", candidate.resolve())
    raise AgentError(f"agent {spec!r}: no directory with a run_agent.py")


def _read_end(path: Path, size: int) -> str:
    """The last `size` bytes of a file as text; empty when it cannot be read."""
    try:
        with open(path, "rb") as file:
            file.seek(0, os.SEEK_END)
            file.seek(max(0, file.tell() - size))
            return file.read().decode("utf-8", "replace")
    except OSError:
        return ""


def _tail(path: Path, limit: int = 300) -> str:
    return _read_end(path, limit * 4).strip()[-limit:]


def protocol_line(stdout: Path) -> dict | None:
    """The solver's last non-empty stdout line as a protocol record, or None when it is not one."""
    lines = [line for line in _read_end(stdout, LINE_WINDOW).lstrip("\ufeff").splitlines() if line.strip()]
    try:
        record = json.loads(lines[-1])
    except (IndexError, ValueError):
        return None
    return record if isinstance(record, dict) and record.get("status") in PROTOCOL_STATUSES else None


def _outcome(status, reason, **extra) -> dict:
    return {"status": status, "reason": reason, "transient": False, "usage_limit": False, **extra}


def classify(exit_code: int, line: dict | None, stderr: str) -> dict:
    """Map a solver that exited to an execution status: {status, reason, transient, usage_limit}.

    The protocol line names the status and the exit code must agree with it (0 for completed, refused and
    cut-off; 2 for timeout; 3 for usage-limit); anything else is an infrastructure error, retryable.
    """
    def broke(reason):
        return _outcome("infrastructure-error", reason, transient=True)

    if line is None:
        return broke(f"exit code {exit_code} and no protocol line on stdout" + (f": {stderr}" if stderr else ""))
    reported = line["status"]
    if reported == "error":
        final = str(line.get("final", ""))[-200:]
        return broke(f"solver reported an error (exit code {exit_code})" + (f": {final}" if final else ""))
    if exit_code != EXIT_FOR[reported]:
        return broke(f"solver reported {reported} with exit code {exit_code}, not {EXIT_FOR[reported]}")
    if reported == "timeout":
        return _outcome("agent-budget-exhausted", "solver reported timeout")
    if reported == "usage-limit":
        return _outcome("interrupted", "account usage limit reached", usage_limit=True)
    return _outcome(reported, "")


def solve(agent: Agent, task: Task, workspace: Path, attempt_dir: Path, *, grace: float,
          cancel: threading.Event | None = None) -> dict:
    """Run the solver in `workspace` with the staged prompt at attempt_dir/prompt.md.

    The solver is handed paths in `attempt_dir` (prompt, transcript) and its stdout and stderr land there, so
    `attempt_dir` must hold nothing the solver should not reach; the runner passes a folder in the attempt's
    temporary root and moves the files into the attempt record afterwards.

    Returns {status, reason, transient, usage_limit, exit_code, seconds, started, finished, left_running,
    model, cost_usd, final, command, live_workspace}, with times as in launch.Outcome.
    """
    stdout, stderr = attempt_dir / "stdout.txt", attempt_dir / "stderr.txt"
    if agent.kind == "noop":
        now = time.time()
        stdout.write_bytes(b"")
        stderr.write_bytes(b"")
        return _outcome("completed", "", exit_code=0, seconds=0.0, started=now, finished=now, left_running=False,
                        model=None, cost_usd=0.0, final="", command=[], live_workspace=str(workspace))
    if agent.kind == "reference":
        command = [sys.executable, str(task.dir / "solution" / "solve.py"), "--workspace", str(workspace)]
    else:
        command = [sys.executable, str(agent.path / "run_agent.py"), "--workspace", str(workspace),
                   "--prompt-file", str(attempt_dir / "prompt.md"), "--transcript", str(attempt_dir / "transcript.jsonl"),
                   "--timeout", f"{task.agent_seconds:g}"]
    outcome = run_capped(command, cwd=workspace, stdout=stdout, stderr=stderr, timeout=task.agent_seconds + grace,
                         cancel=cancel)
    line = protocol_line(stdout) if agent.kind == "dir" else None
    fields = {"exit_code": outcome.exit_code, "seconds": outcome.seconds, "started": outcome.started,
              "finished": outcome.finished, "left_running": outcome.left_running, "command": command,
              "live_workspace": str(workspace), "model": None, "cost_usd": 0.0 if agent.kind == "reference" else None, "final": ""}
    if outcome.status == "canceled":
        return _outcome("canceled", "canceled", **fields)
    if outcome.status == "timeout":
        return _outcome("agent-budget-exhausted", f"runner cap: {outcome.reason}", **fields)
    if outcome.exit_code is None:
        return _outcome("infrastructure-error", outcome.reason, **fields)
    if agent.kind == "reference":
        verdict = (_outcome("completed", "") if outcome.exit_code == 0 else
                   _outcome("infrastructure-error", f"reference solution failed: exit code {outcome.exit_code}: {_tail(stderr)}"))
    else:
        verdict = classify(outcome.exit_code, line, _tail(stderr))
        if line:
            model, cost = line.get("model"), line.get("cost_usd")
            fields["model"] = model if isinstance(model, str) else None
            fields["cost_usd"] = float(cost) if isinstance(cost, (int, float)) and not isinstance(cost, bool) else None
            fields["final"] = str(line.get("final", ""))
    if outcome.left_running:
        verdict["reason"] = (verdict["reason"] + "; " if verdict["reason"] else "") + "stopped processes left running after exit"
    return {**verdict, **fields}


def verify(task: Task, workspace: Path, log_dir: Path) -> dict:
    """Grade a captured workspace with the task's verifier.

    Returns `aggregate.validate_grade`'s normalized grade plus `seconds` and `exit_code`. A crash, a timeout, or a
    missing or malformed result is unscored with the reason; the raw result and the verifier's output stay in
    `log_dir` as verifier-result.json, verify-stdout.txt and verify-stderr.txt.
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    result, stdout, stderr = log_dir / "verifier-result.json", log_dir / "verify-stdout.txt", log_dir / "verify-stderr.txt"
    result.unlink(missing_ok=True)
    outcome = run_capped([sys.executable, str(task.dir / "tests" / "verify.py"), "--task", str(task.dir),
                          "--workspace", str(workspace), "--result", str(result)],
                         cwd=task.dir, stdout=stdout, stderr=stderr, timeout=task.verifier_seconds)
    raw, reason = None, ""
    if outcome.status == "timeout":
        reason = f"verifier exceeded its {task.verifier_seconds:g} s limit"
    elif outcome.status != "completed":
        detail = _tail(stderr)
        reason = f"verifier failed ({outcome.reason})" + (f": {detail}" if detail else "")
    else:
        try:
            raw = json.loads(result.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            reason = "verifier exited 0 but wrote no valid JSON result"
        else:
            reason = "" if isinstance(raw, dict) else "verifier result is not a JSON object"
    grade = aggregate.validate_grade(raw if reason == "" else None, reason)
    return {**grade, "seconds": outcome.seconds, "exit_code": outcome.exit_code}


def grade_copy(task: Task, workspace: Path, log_dir: Path) -> dict:
    """`verify` on a scratch copy of the workspace, so a verifier that writes files never alters the evidence."""
    scratch = tempfile.mkdtemp(prefix="benchkit-grade-")
    try:
        copy = Path(scratch) / "workspace"
        stage.capture(workspace, copy)
        return verify(task, copy, log_dir)
    finally:
        stage.discard(scratch)
