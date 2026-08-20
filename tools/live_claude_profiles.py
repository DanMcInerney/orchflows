#!/usr/bin/env python3
"""Run an opt-in, usage-consuming Claude Code subagent profile probe.

The probe renders session-scoped skill adapters through the production
frontmatter transform. Each adapter selects an installer-rendered planner or
worker profile through ``context: fork`` plus ``agent``. The transcript must
show the parent invoking the skill and the profile-only sentinel returning from
that skill's child context; no explicit Agent launch can satisfy the probe.
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
import tempfile
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
    agents = {}
    expected = {}
    configured = {}
    for profile_name in selected:
        profile = profiles[profile_name]
        metadata, instructions = _parse_rendered_agent(
            install.render_claude_agent(profile_name, profile)
        )
        agent_type = metadata["name"]
        if _CLAUDE_AGENT_NAME_RE.fullmatch(agent_type) is None:
            raise ValueError(f"invalid Claude probe agent name: {agent_type}")
        sentinel = f"ORCH_PROFILE_LOADED:{profile_name}"
        definition = {
            "description": f"Live profile probe for {profile_name}; selected only by its probe skill.",
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


def _build_probe_adapters(
    selected: tuple[str, ...] | list[str], config_dir: Path, pid: int | None = None
) -> dict[str, str]:
    """Write generated role-bearing adapters and return skill -> agent.

    The sentinel lives only in the role agent prompt. The skill body asks for
    that sentinel without spelling it, so inline execution or the wrong role
    cannot accidentally pass.
    """

    probe_pid = os.getpid() if pid is None else pid
    skill_agents = {}
    for profile_name in selected:
        role = profile_name.removeprefix("orch-")
        skill_name = f"orch-profile-probe-{role}-{probe_pid}"
        source_frontmatter = (
            "---\n"
            f"name: {skill_name}\n"
            f"description: Exercise the generated {role} role adapter.\n"
            f"role: {role}\n"
            "---\n"
        )
        adapter = install.host_legal_frontmatter(source_frontmatter) + (
            "\nReturn exactly the ORCH_PROFILE_LOADED sentinel supplied by your "
            "role-agent instructions. Do not use tools.\n"
        )
        destination = config_dir / "skills" / skill_name / "SKILL.md"
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(adapter, encoding="utf-8")
        skill_agents[skill_name] = profile_name
    return skill_agents


def _json_events(stdout: str):
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            yield event


def _analyze_run(
    stdout: str,
    returncode: int,
    expected: dict[str, str],
    expected_skills: dict[str, str],
) -> dict:
    registered = set()
    skill_counts = Counter()
    tool_skills = {}
    child_text = defaultdict(list)
    reported_models = defaultdict(set)
    unexpected_child_tools = 0
    manual_root_launches = 0
    root_text = []

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
                if block.get("type") == "text":
                    root_text.append(block.get("text", ""))
                    continue
                if block.get("type") != "tool_use":
                    continue
                if block.get("name") in {"Agent", "Task"}:
                    manual_root_launches += 1
                    continue
                if block.get("name") not in {"Skill", "SlashCommand"}:
                    continue
                block_input = block.get("input") or {}
                skill_name = None
                for key in ("skill", "name", "command"):
                    value = block_input.get(key)
                    if isinstance(value, str) and value.strip():
                        skill_name = value.split()[0].lstrip("/")
                        break
                tool_id = block.get("id")
                if skill_name:
                    skill_counts[skill_name] += 1
                if skill_name and tool_id:
                    tool_skills[tool_id] = skill_name
            continue

        skill_name = tool_skills.get(parent_tool_use_id)
        agent_type = expected_skills.get(skill_name) if skill_name else None
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
        skill_name for skill_name in expected_skills if skill_counts[skill_name] != 1
    )
    unexpected_launches = sorted(set(skill_counts) - set(expected_skills))
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
        and manual_root_launches == 0
        and not any(sentinel in "\n".join(root_text) for sentinel in expected.values())
    )
    return {
        "passed": passed,
        "returncode": returncode,
        "registered_agent_types": sorted(registered & set(expected)),
        "missing_registrations": missing_registrations,
        "skill_invocation_counts": {
            skill_name: skill_counts[skill_name] for skill_name in expected_skills
        },
        "invalid_launches": invalid_launches,
        "unexpected_launches": unexpected_launches,
        "missing_sentinels": missing_sentinels,
        "unexpected_child_tools": unexpected_child_tools,
        "manual_root_launches": manual_root_launches,
        "reported_models": {
            agent_type: sorted(reported_models[agent_type]) for agent_type in expected
        },
        "role_skill_topology": {
            "mode": "enforced",
            "profile_selection": "verified" if passed else "failed",
            "binding": "generated context:fork+agent adapter",
        },
    }


def _parent_prompt(skill_names: list[str]) -> str:
    invocations = "\n".join(f"/{skill_name}" for skill_name in skill_names)
    return (
        "Invoke each exact skill below once. Do not launch agents explicitly; each skill's "
        "generated adapter owns its child binding. Wait for all results and return them raw.\n"
        + invocations
    )


def _captured_text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""


def _run_probe(
    command: list[str],
    timeout: int,
    expected: dict[str, str],
    expected_skills: dict[str, str],
    env: dict | None = None,
) -> tuple[dict, str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            timeout=timeout,
            check=False,
        )
        result = _analyze_run(
            completed.stdout, completed.returncode, expected, expected_skills
        )
        result["timed_out"] = False
        return result, completed.stderr
    except subprocess.TimeoutExpired as exc:
        result = _analyze_run(
            _captured_text(exc.stdout), 124, expected, expected_skills
        )
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

    claude_invocation = _claude_command()
    with tempfile.TemporaryDirectory(prefix="orchflows-claude-profile-") as tmp:
        config_dir = Path(tmp) / ".claude"
        agents, expected, configured = _build_probe_agents(selected)
        expected_skills = _build_probe_adapters(selected, config_dir)
        env = os.environ.copy()
        env["CLAUDE_CONFIG_DIR"] = str(config_dir)
        command = claude_invocation + [
            "-p",
            _parent_prompt(list(expected_skills)),
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
            "Skill",
            "--agents",
            json.dumps(agents, separators=(",", ":")),
            "--allowedTools",
            *(f"Skill({skill_name})" for skill_name in expected_skills),
        ]
        result, stderr = _run_probe(
            command, args.timeout, expected, expected_skills, env=env
        )
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
