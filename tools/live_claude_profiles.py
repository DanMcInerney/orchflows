#!/usr/bin/env python3
"""Run an opt-in, usage-consuming Claude Code subagent profile probe.

The probe defines unique session-scoped copies of the installer-rendered
planner and worker profiles. It launches each through Claude's Agent
tool, validates the exact launch set and private child sentinels, and leaves no
agent files or persisted session behind.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import install  # noqa: E402

PROFILE_NAMES = ("orch-planner", "orch-worker")
_CLAUDE_AGENT_NAME_RE = re.compile(r"^[a-z0-9-]+$")


def _claude_command() -> list[str]:
    executable = shutil.which("claude") or shutil.which("claude.exe") or shutil.which("claude.cmd")
    if executable is None:
        raise FileNotFoundError("claude executable was not found on PATH")
    if Path(executable).suffix.lower() in {".cmd", ".bat"}:
        return [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", executable]
    return [executable]


def _parse_rendered_agent(content: str) -> tuple[dict[str, str], str]:
    sections = content.split("---", 2)
    if len(sections) != 3 or sections[0].strip():
        raise ValueError("rendered Claude agent has invalid frontmatter")
    metadata = {}
    for line in sections[1].strip().splitlines():
        key, separator, raw_value = line.partition(":")
        if not separator:
            raise ValueError(f"invalid rendered Claude frontmatter line: {line}")
        value = raw_value.strip()
        metadata[key.strip()] = json.loads(value) if value.startswith('"') else value
    missing = {"name", "description", "model"} - set(metadata)
    if missing:
        raise ValueError(f"rendered Claude agent omitted: {', '.join(sorted(missing))}")
    return metadata, sections[2].strip()


def _build_probe_agents(
    selected: tuple[str, ...] | list[str], pid: int | None = None
) -> tuple[dict[str, dict], dict[str, str], dict[str, dict]]:
    profiles = install.load_role_profiles()
    roles_path = REPO_ROOT / "rules" / "roles.md"
    probe_pid = os.getpid() if pid is None else pid
    agents = {}
    expected = {}
    configured = {}
    for profile_name in selected:
        profile = profiles[profile_name]
        metadata, instructions = _parse_rendered_agent(
            install.render_claude_agent(profile_name, profile, roles_path)
        )
        agent_type = f"{metadata['name']}-e2e-{probe_pid}"
        if _CLAUDE_AGENT_NAME_RE.fullmatch(agent_type) is None:
            raise ValueError(f"invalid Claude probe agent name: {agent_type}")
        sentinel = f"ORCH_PROFILE_LOADED:{profile_name}"
        definition = {
            "description": f"Live profile probe for {profile_name}; use only when explicitly named.",
            "prompt": (
                instructions
                + f"\n\nFor the exact input PROFILE_PROBE, return exactly {sentinel} and do not use tools."
            ),
            "tools": [],
            "model": metadata["model"],
        }
        if metadata.get("effort"):
            definition["effort"] = metadata["effort"]
        agents[agent_type] = definition
        expected[agent_type] = sentinel
        configured[agent_type] = {
            "profile": profile_name,
            "model": metadata["model"],
            "effort": metadata.get("effort"),
        }
    return agents, expected, configured


def _json_events(stdout: str):
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            yield event


def _analyze_run(stdout: str, returncode: int, expected: dict[str, str]) -> dict:
    registered = set()
    launch_counts = Counter()
    tool_agent_types = {}
    child_text = defaultdict(list)
    reported_models = defaultdict(set)
    unexpected_child_tools = 0

    for event in _json_events(stdout):
        if event.get("type") == "system" and event.get("subtype") == "init":
            registered.update(event.get("agents") or [])
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
                agent_type = (block.get("input") or {}).get("subagent_type")
                tool_id = block.get("id")
                if agent_type:
                    launch_counts[agent_type] += 1
                if agent_type and tool_id:
                    tool_agent_types[tool_id] = agent_type
            continue

        agent_type = tool_agent_types.get(parent_tool_use_id)
        if agent_type is None:
            continue
        if message.get("model"):
            reported_models[agent_type].add(message["model"])
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                child_text[agent_type].append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                unexpected_child_tools += 1

    missing_registrations = sorted(set(expected) - registered)
    invalid_launches = sorted(
        agent_type for agent_type in expected if launch_counts[agent_type] != 1
    )
    unexpected_launches = sorted(set(launch_counts) - set(expected))
    missing_sentinels = sorted(
        agent_type
        for agent_type, sentinel in expected.items()
        if sentinel not in "\n".join(child_text[agent_type])
    )
    passed = (
        returncode == 0
        and not missing_registrations
        and not invalid_launches
        and not unexpected_launches
        and not missing_sentinels
        and unexpected_child_tools == 0
    )
    return {
        "passed": passed,
        "returncode": returncode,
        "registered_agent_types": sorted(registered & set(expected)),
        "missing_registrations": missing_registrations,
        "launch_counts": {agent_type: launch_counts[agent_type] for agent_type in expected},
        "invalid_launches": invalid_launches,
        "unexpected_launches": unexpected_launches,
        "missing_sentinels": missing_sentinels,
        "unexpected_child_tools": unexpected_child_tools,
        "reported_models": {
            agent_type: sorted(reported_models[agent_type]) for agent_type in expected
        },
    }


def _parent_prompt(agent_types: list[str]) -> str:
    mentions = "\n".join(f"@{agent_type} PROFILE_PROBE" for agent_type in agent_types)
    return (
        "Launch exactly one foreground subagent for each @mention below. Pass each one exactly "
        "PROFILE_PROBE, use no other agents, wait for all results, and return their raw results.\n"
        + mentions
    )


def _captured_text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def _run_probe(command: list[str], timeout: int, expected: dict[str, str]) -> tuple[dict, str]:
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
        result = _analyze_run(completed.stdout, completed.returncode, expected)
        result["timed_out"] = False
        return result, completed.stderr
    except subprocess.TimeoutExpired as exc:
        result = _analyze_run(_captured_text(exc.stdout), 124, expected)
        result["timed_out"] = True
        return result, _captured_text(exc.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--max-budget-usd", type=float, default=1.0)
    parser.add_argument("--parent-model", default="haiku")
    parser.add_argument("--parent-effort", default="low")
    parser.add_argument("--profile", action="append", choices=PROFILE_NAMES)
    args = parser.parse_args(argv)
    selected = tuple(args.profile or PROFILE_NAMES)

    agents, expected, configured = _build_probe_agents(selected)
    agent_types = list(expected)
    claude_invocation = _claude_command()
    command = claude_invocation + [
        "-p",
        _parent_prompt(agent_types),
        "--output-format",
        "stream-json",
        "--verbose",
        "--forward-subagent-text",
        "--no-session-persistence",
        "--max-budget-usd",
        str(args.max_budget_usd),
        "--model",
        args.parent_model,
        "--effort",
        args.parent_effort,
        "--tools",
        "Agent",
        "--agents",
        json.dumps(agents, separators=(",", ":")),
        "--allowedTools",
        *(f"Agent({agent_type})" for agent_type in agent_types),
    ]
    result, stderr = _run_probe(command, args.timeout, expected)
    result.update(
        {
            "claude": claude_invocation[-1],
            "configured": configured,
            "selected_profiles": list(selected),
        }
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["passed"] and stderr:
        print(stderr[-4000:], file=sys.stderr)
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
