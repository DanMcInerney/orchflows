#!/usr/bin/env python3
"""Run an opt-in, usage-consuming Codex custom-agent profile probe.

The stable surface proves planner and worker launches. The V2 surface
does the same when ``agent_type`` is exposed, or reports a narrow unsupported
result when the spawn schema explicitly omits it. Temporary installer-rendered
agents are always removed in a ``finally``.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import install  # noqa: E402

PROFILE_NAMES = ("orch-planner", "orch-worker")
SURFACES = ("stable", "v2")
V2_UNSUPPORTED_MARKER = "ORCH_AGENT_TYPE_UNAVAILABLE"
_FORBIDDEN_ITEM_TYPES = {
    "command_execution",
    "shell_command",
    "file_change",
    "mcp_tool_call",
    "web_search",
    "image_generation",
    "view_image",
}


def _codex_command() -> list[str]:
    executable = shutil.which("codex") or shutil.which("codex.exe") or shutil.which("codex.cmd")
    if executable is None:
        raise FileNotFoundError("codex executable was not found on PATH")
    if Path(executable).suffix.lower() in {".cmd", ".bat"}:
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", executable]
    return [executable]


def _with_probe_sentinel(content: str, sentinel: str) -> str:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if line.startswith("developer_instructions = "):
            instructions = json.loads(line.removeprefix("developer_instructions = "))
            replacement = (
                "developer_instructions = "
                + json.dumps(
                    instructions
                    + f" For the exact input PROFILE_PROBE, return exactly {sentinel} and do not use tools."
                )
            )
            lines[index] = replacement
            return "\n".join(lines) + "\n"
    raise ValueError("rendered Codex agent omitted developer_instructions")


def _messages_and_forbidden_actions(stdout: str) -> tuple[list[str], list[dict]]:
    messages = []
    forbidden_actions = []
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        item = event.get("item") or {}
        if not isinstance(item, dict):
            continue
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            messages.append(item.get("text", ""))
        if item.get("type") in _FORBIDDEN_ITEM_TYPES:
            forbidden_actions.append(item)
    return messages, forbidden_actions


def _surface_prompt(surface: str, expected: dict[str, str]) -> str:
    agent_types = ", ".join(expected)
    if surface == "stable":
        return (
            "Live custom-agent profile probe. Spawn exactly one child for each of these custom "
            f"agent types: {agent_types}. Use agent_type explicitly and fork_context=false. "
            "Send each child exactly PROFILE_PROBE, use no shell or file tools, wait for all "
            "children, then report one line per agent type containing the child's exact raw result."
        )
    if surface == "v2":
        return (
            "Live MultiAgentV2 custom-agent capability probe. Inspect the collaboration.spawn_agent "
            "input schema before calling it. If agent_type is absent, do not call any tool and return "
            f"exactly {V2_UNSUPPORTED_MARKER}. If agent_type is present, spawn exactly one child for "
            f"each of these custom agent types: {agent_types}. Use agent_type explicitly and "
            'fork_turns="none". Send each child exactly PROFILE_PROBE, use no shell or file tools, '
            "wait for all children, then report one line per agent type containing the child's exact "
            "raw result."
        )
    raise ValueError(f"unknown Codex surface: {surface}")


def _classify_surface(
    surface: str, stdout: str, returncode: int, expected: dict[str, str]
) -> dict:
    messages, forbidden_actions = _messages_and_forbidden_actions(stdout)
    combined = "\n".join(messages)
    missing = [sentinel for sentinel in expected.values() if sentinel not in combined]
    explicit_unsupported = (
        surface == "v2"
        and returncode == 0
        and not forbidden_actions
        and bool(messages)
        and messages[-1].strip() == V2_UNSUPPORTED_MARKER
        and len(missing) == len(expected)
    )
    passed = returncode == 0 and not missing and not forbidden_actions
    status = "passed" if passed else "unsupported" if explicit_unsupported else "failed"
    return {
        "status": status,
        "passed": passed,
        "supported": not explicit_unsupported,
        "missing_sentinels": missing,
        "unexpected_tool_actions": len(forbidden_actions),
        "returncode": returncode,
    }


def _surface_config_args(surface: str) -> list[str]:
    if surface == "stable":
        return []
    if surface == "v2":
        return ["--ignore-user-config"]
    raise ValueError(f"unknown Codex surface: {surface}")


def _captured_text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def _run_surface(
    surface: str,
    codex_invocation: list[str],
    expected: dict[str, str],
    timeout: int,
) -> tuple[dict, str]:
    feature_flag = "--disable" if surface == "stable" else "--enable"
    command = codex_invocation + [
        "exec",
        *_surface_config_args(surface),
        "--json",
        "--ephemeral",
        "--skip-git-repo-check",
        "--sandbox",
        "read-only",
        feature_flag,
        "multi_agent_v2",
        "-C",
        str(REPO_ROOT),
        _surface_prompt(surface, expected),
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
        result = _classify_surface(surface, completed.stdout, completed.returncode, expected)
        result["timed_out"] = False
        return result, completed.stderr
    except subprocess.TimeoutExpired as exc:
        result = _classify_surface(surface, _captured_text(exc.stdout), 124, expected)
        result["timed_out"] = True
        return result, _captured_text(exc.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--profile", action="append", choices=PROFILE_NAMES)
    parser.add_argument("--surface", choices=(*SURFACES, "both"), default="stable")
    parser.add_argument(
        "--require-v2",
        action="store_true",
        help="Treat an explicit V2 agent_type-unavailable result as failure.",
    )
    args = parser.parse_args(argv)
    selected = tuple(args.profile or PROFILE_NAMES)

    profiles = install.load_role_profiles()
    roles_path = REPO_ROOT / "rules" / "roles.md"
    codex_home = Path(os.environ["CODEX_HOME"]) if "CODEX_HOME" in os.environ else Path.home() / ".codex"
    agents_dir = codex_home / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    created_paths = []
    try:
        expected = {}
        configured = {}
        for profile_name in selected:
            profile = profiles[profile_name]
            binding = profile["codex"]
            agent_type = f"{binding['agent_type']}_e2e_{os.getpid()}"
            sentinel = f"ORCH_PROFILE_LOADED:{profile_name}"
            probe_profile = {
                "role": profile["role"],
                "codex": dict(binding, agent_type=agent_type),
                "claude": dict(profile["claude"]),
            }
            rendered = install.render_codex_agent(profile_name, probe_profile, roles_path)
            agent_path = agents_dir / f"{agent_type}.toml"
            if agent_path.exists():
                raise FileExistsError(f"refusing to overwrite live probe path: {agent_path}")
            agent_path.write_text(_with_probe_sentinel(rendered, sentinel), encoding="utf-8")
            created_paths.append(agent_path)
            expected[agent_type] = sentinel
            configured[agent_type] = {
                "profile": profile_name,
                "model": binding["model"],
                "model_reasoning_effort": binding["model_reasoning_effort"],
                "service_tier": binding.get("service_tier"),
            }

        codex_invocation = _codex_command()
        selected_surfaces = SURFACES if args.surface == "both" else (args.surface,)
        surface_results = {}
        stderrs = {}
        for surface in selected_surfaces:
            surface_results[surface], stderrs[surface] = _run_surface(
                surface, codex_invocation, expected, args.timeout
            )
        failed = any(result["status"] == "failed" for result in surface_results.values())
        required_v2_unavailable = args.require_v2 and any(
            surface == "v2" and result["status"] == "unsupported"
            for surface, result in surface_results.items()
        )
        passed = not failed and not required_v2_unavailable
        result = {
            "passed": passed,
            "codex": codex_invocation[-1],
            "configured": configured,
            "selected_profiles": list(selected),
            "require_v2": args.require_v2,
            "surfaces": surface_results,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        if not passed:
            for surface, stderr in stderrs.items():
                if stderr:
                    print(f"[{surface}] {stderr[-4000:]}", file=sys.stderr)
        return 0 if passed else 1
    finally:
        for path in created_paths:
            try:
                path.unlink()
            except FileNotFoundError:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
