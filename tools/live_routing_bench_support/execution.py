"""Isolated installation and case execution for the routing benchmark."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from scripts import _bootstrap, state_root
from tools.live_claude_profiles import _captured_text
from tools.live_routing_bench_support.grading import ERROR, grade_transcript

INSTALLER = _bootstrap.ROOT / "install.py"


def _isolated_env(home: Path) -> dict:
    """Point every root a session or an install could write at ``home``.

    HOME and USERPROFILE move ``Path.home()`` on POSIX and Windows
    respectively; CLAUDE_CONFIG_DIR and CODEX_HOME are the two host
    overrides install.py reads, and the sink env var is the state sink
    -- an inherited value for any of them would send a benchmark run's
    writes into the real home this probe must leave alone.
    """

    env = os.environ.copy()
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["CLAUDE_CONFIG_DIR"] = str(home / ".claude")
    env["CODEX_HOME"] = str(home / ".codex")
    env[state_root.ENV_VAR] = str(home / ".orchflows" / "state")
    return env


def _install_command(adapter_set: str) -> list:
    return [
        sys.executable,
        str(INSTALLER),
        "--user",
        "--yes",
        "--claude-adapters",
        adapter_set,
    ]


def _render_install(adapter_set: str, home: Path, timeout: int) -> str:
    (home / ".claude").mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        _install_command(adapter_set),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=_isolated_env(home),
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"install for adapter set {adapter_set!r} failed: {(completed.stderr or '')[-2000:]}"
        )
    return completed.stdout


def _make_repo(path: Path, timeout: int) -> Path:
    """A plain repository with no instruction files of its own, so the only
    thing routing the session is the host block the install just wrote."""

    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "init", "--quiet", str(path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=False,
    )
    return path


def _case_command(claude_invocation: list, prompt: str, max_turns: int) -> list:
    return claude_invocation + [
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--no-session-persistence",
        "--max-turns",
        str(max_turns),
    ]


def _run_case(
    claude_invocation: list,
    prompt: str,
    cwd: Path,
    env: dict,
    max_turns: int,
    timeout: int,
    expected_role: str | None = None,
    expected_skill: str | None = None,
) -> dict:
    command = _case_command(claude_invocation, prompt, max_turns)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(cwd),
            env=env,
            timeout=timeout,
            check=False,
        )
        stdout, returncode, timed_out = completed.stdout, completed.returncode, False
    except subprocess.TimeoutExpired as exc:
        stdout, returncode, timed_out = _captured_text(exc.stdout), 124, True
    graded = grade_transcript(
        stdout, expected_role=expected_role, expected_skill=expected_skill
    )
    if timed_out:
        # A session killed at the timeout never got to route: it is neither a
        # route nor a misroute, which is what ERROR means here. Grading it
        # `unrouted` put it in the misroute numerator and left `errors` at 0,
        # so the "read no rate while errors is above 0" guard saw nothing.
        graded["observed"] = ERROR
        graded["first_event"] = f"timeout({timeout}s)"
    graded["returncode"] = returncode
    graded["timed_out"] = timed_out
    return graded


def run_benchmark(
    *,
    adapter_sets,
    cases,
    repeat: int,
    max_turns: int,
    timeout: int,
    claude_invocation: list,
    root: Path,
    max_budget_usd: float | None = None,
) -> list:
    records = []
    # What has been spent, across every set and repeat. The bound is money,
    # not case count: one long session is worth many short ones, and the
    # thing an opt-in usage-consuming probe has to be able to stop is the
    # next launch.
    spent = 0.0
    for adapter_set in adapter_sets:
        if max_budget_usd is not None and spent >= max_budget_usd:
            break
        home = Path(root) / f"home-{adapter_set}"
        _render_install(adapter_set, home, timeout)
        env = _isolated_env(home)
        repo = _make_repo(Path(root) / f"repo-{adapter_set}", timeout)
        for index in range(1, repeat + 1):
            for case in cases:
                if max_budget_usd is not None and spent >= max_budget_usd:
                    return records
                graded = _run_case(
                    claude_invocation,
                    case["prompt"],
                    repo,
                    env,
                    max_turns,
                    timeout,
                    expected_role=case.get("required_role"),
                    expected_skill=case.get("required_skill"),
                )
                conformance = graded["execution_conformance"]
                record = {
                    "adapter_set": adapter_set,
                    "case": case["id"],
                    "repeat": index,
                    "expected": case["expected"],
                    "observed": graded["observed"],
                    "match": (
                        graded["observed"] == case["expected"]
                        and conformance["status"] in {"not_applicable", "passed"}
                    ),
                    "first_event": graded["first_event"],
                    "turns": graded["turns"],
                    "returncode": graded["returncode"],
                    "timed_out": graded["timed_out"],
                    "execution_conformance": conformance,
                }
                if graded["cost_usd"] is not None:
                    record["cost_usd"] = graded["cost_usd"]
                    spent += graded["cost_usd"]
                records.append(record)
    return records
