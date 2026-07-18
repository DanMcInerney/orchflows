#!/usr/bin/env python3
"""Run an opt-in, usage-consuming live e2e probe for the adversarial-sweep lane.

The probe launches one foreground subagent through Claude's Agent tool and
checks the exact dispatch and its sentinel reply, following the
``live_claude_profiles`` / ``live_loop_e2e`` idiom (inline ``--agents`` JSON,
``--no-session-persistence``, ``sonnet`` at medium effort by default,
subprocess timeout handling).

Runs are self-cleaning. Before dispatch the probe snapshots (SHA-256 and raw
bytes) the friction log its own run would append to. Every friction entry the
probe writes is tagged ``--run <run id>`` with a run id unique to that
invocation. A per-run result log is written under ``.orch/live-sweep-e2e/``.
In a ``finally`` block, regardless of success, failure, or timeout, the probe
removes exactly the friction lines tagged with its run id (validating the
untagged remainder still starts with the pre-run content, so a concurrent
writer's lines are never destroyed) and deletes the per-run result log. If
tag-filtered removal cannot prove the untagged remainder matches the pre-run
prefix, the friction log is restored to its pre-run bytes verbatim instead.
The probe leaves no agent files or persisted session behind.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.live_claude_profiles import _captured_text, _claude_command, _json_events  # noqa: E402

_FRICTION_SPEC = importlib.util.spec_from_file_location(
    "live_sweep_e2e_friction", REPO_ROOT / "scripts" / "friction.py"
)
friction = importlib.util.module_from_spec(_FRICTION_SPEC)
_FRICTION_SPEC.loader.exec_module(friction)

RUN_ID_PREFIX = "sweep-e2e"
PROBE_INPUT = "SWEEP_PROBE"
PROBE_SENTINEL = "SWEEP_PROBE_RESULT:OK"
FRICTION_CATEGORY = "surprising-output"
DEFAULT_LOG_DIR = REPO_ROOT / ".orch" / "live-sweep-e2e"


@dataclasses.dataclass(frozen=True)
class _Snapshot:
    path: Path
    existed: bool
    digest: str | None
    data: bytes | None


def _generate_run_id() -> str:
    return f"{RUN_ID_PREFIX}-{uuid.uuid4().hex}"


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _snapshot_path(path: Path) -> _Snapshot:
    if not path.exists():
        return _Snapshot(path=path, existed=False, digest=None, data=None)
    data = path.read_bytes()
    return _Snapshot(path=path, existed=True, digest=_hash_bytes(data), data=data)


def _restore_snapshot(snapshot: _Snapshot) -> None:
    if snapshot.existed:
        snapshot.path.write_bytes(snapshot.data)
    elif snapshot.path.exists():
        snapshot.path.unlink()


def _cleanup_friction(run_id: str, snapshot: _Snapshot) -> int:
    """Remove lines tagged ``run_id`` from the friction log; return the count.

    Raises if the untagged remainder does not start with the pre-run content
    verbatim, so the caller can fall back to a full byte-identical restore
    instead of risking silent corruption of a concurrent writer's entries.
    """
    path = snapshot.path
    if not path.exists():
        return 0

    text = path.read_bytes().decode("utf-8")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]

    kept: list[str] = []
    removed = 0
    for line in lines:
        if not line:
            kept.append(line)
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            kept.append(line)
            continue
        if isinstance(entry, dict) and entry.get("run") == run_id:
            removed += 1
            continue
        kept.append(line)

    if snapshot.existed:
        original_text = snapshot.data.decode("utf-8")
        original_lines = original_text.split("\n")
        if original_lines and original_lines[-1] == "":
            original_lines = original_lines[:-1]
        if kept[: len(original_lines)] != original_lines:
            raise ValueError(
                "tag-filtered friction content diverges from its pre-run prefix"
            )

    if not snapshot.existed and not kept:
        path.unlink()
        return removed

    new_text = "\n".join(kept) + ("\n" if kept else "")
    path.write_bytes(new_text.encode("utf-8"))
    return removed


def _cleanup(run_id: str, friction_snapshot: _Snapshot, log_path: Path) -> dict:
    report = {
        "friction_lines_removed": 0,
        "friction_restored_byte_identical": False,
        "files_deleted": [],
    }
    try:
        report["friction_lines_removed"] = _cleanup_friction(run_id, friction_snapshot)
    except Exception:
        _restore_snapshot(friction_snapshot)
        report["friction_restored_byte_identical"] = True
        report["friction_lines_removed"] = 0

    if log_path.exists():
        try:
            log_path.unlink()
            report["files_deleted"].append(str(log_path))
        except FileNotFoundError:
            pass
    return report


def _log_friction(run_id: str, observed: str, expected: str) -> None:
    friction._run([observed, expected, "--run", run_id, "--category", FRICTION_CATEGORY])


def _build_probe_agent(agent_type: str, model: str, effort: str) -> dict:
    return {
        agent_type: {
            "description": "Live adversarial-sweep e2e probe; use only when explicitly named.",
            "prompt": (
                "You are an adversarial-test-sweep probe. Reply with exactly one line and "
                "use no tools.\n"
                f"For the exact input {PROBE_INPUT}, reply exactly: {PROBE_SENTINEL}"
            ),
            "tools": [],
            "model": model,
            "effort": effort,
        }
    }


def _parent_prompt(agent_type: str) -> str:
    return (
        "Launch exactly one foreground subagent for the adversarial-sweep probe.\n"
        f"@{agent_type} {PROBE_INPUT}\n"
        "Pass it exactly the input above, use no other agents, wait for its result, "
        "and return its raw result."
    )


def _analyze_run(stdout: str, returncode: int, agent_type: str) -> dict:
    launch_count = 0
    replies: list[str] = []
    unexpected_launches: list[str] = []
    unexpected_child_tools = 0
    tool_ids: set[str] = set()

    for event in _json_events(stdout):
        if event.get("type") != "assistant":
            continue
        parent_tool_use_id = event.get("parent_tool_use_id")
        message = event.get("message") or {}
        blocks = message.get("content") or []
        if parent_tool_use_id is None:
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_use" or block.get("name") not in {"Agent", "Task"}:
                    continue
                launched = (block.get("input") or {}).get("subagent_type")
                if launched != agent_type:
                    unexpected_launches.append(str(launched))
                    continue
                launch_count += 1
                tool_ids.add(block.get("id"))
            continue
        if parent_tool_use_id not in tool_ids:
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                replies.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                unexpected_child_tools += 1

    failures = []
    if returncode != 0:
        failures.append(f"claude exited {returncode}")
    if launch_count != 1:
        failures.append(f"expected exactly 1 probe dispatch, saw {launch_count}")
    if PROBE_SENTINEL not in "\n".join(replies):
        failures.append("probe reply missing its sentinel")
    if unexpected_launches:
        failures.append(f"unexpected subagent launches: {sorted(set(unexpected_launches))}")
    if unexpected_child_tools:
        failures.append(f"probe used {unexpected_child_tools} unexpected tool call(s)")

    return {
        "passed": not failures,
        "failures": failures,
        "returncode": returncode,
        "launch_count": launch_count,
    }


def _run_live_sweep(
    claude_invocation: list[str],
    model: str,
    effort: str,
    timeout: int,
    max_budget_usd: float,
    log_dir: Path,
    run_id: str | None = None,
) -> dict:
    run_id = run_id or _generate_run_id()
    friction_snapshot = _snapshot_path(friction._target_path(datetime.now(timezone.utc)))
    log_path = log_dir / f"{run_id}.json"

    result: dict = {
        "run_id": run_id,
        "passed": False,
        "failures": ["probe did not complete"],
        "returncode": None,
        "timed_out": False,
        "stderr": "",
    }
    try:
        agent_type = f"orch-sweep-e2e-{os.getpid()}"
        agents = _build_probe_agent(agent_type, model, effort)
        command = claude_invocation + [
            "-p",
            _parent_prompt(agent_type),
            "--output-format",
            "stream-json",
            "--verbose",
            "--forward-subagent-text",
            "--no-session-persistence",
            "--max-budget-usd",
            str(max_budget_usd),
            "--model",
            model,
            "--effort",
            effort,
            "--tools",
            "Agent",
            "--agents",
            json.dumps(agents, separators=(",", ":")),
            "--allowedTools",
            f"Agent({agent_type})",
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
            )
            result.update(_analyze_run(completed.stdout, completed.returncode, agent_type))
            result["timed_out"] = False
            result["stderr"] = completed.stderr
        except subprocess.TimeoutExpired as exc:
            result.update(_analyze_run(_captured_text(exc.stdout), 124, agent_type))
            result["timed_out"] = True
            result["failures"].append("probe timed out")
            result["passed"] = False
            result["stderr"] = _captured_text(exc.stderr)

        if not result["passed"]:
            _log_friction(
                run_id,
                f"live sweep e2e probe did not pass: {result['failures']}",
                "the adversarial-sweep probe dispatch should pass",
            )

        log_dir.mkdir(parents=True, exist_ok=True)
        log_path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    finally:
        result["cleanup"] = _cleanup(run_id, friction_snapshot, log_path)

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--max-budget-usd", type=float, default=1.0)
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--effort", default="medium")
    parser.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    args = parser.parse_args(argv)

    claude_invocation = _claude_command()
    result = _run_live_sweep(
        claude_invocation,
        args.model,
        args.effort,
        args.timeout,
        args.max_budget_usd,
        Path(args.log_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"] and result.get("stderr"):
        print(result["stderr"][-4000:], file=sys.stderr)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
