#!/usr/bin/env python3
"""Run an opt-in, usage-consuming live e2e of the generalized loop shape.

Two scenarios exercise rules/loops.md against a real cheap model (haiku
by default), with the loop operator as the parent session and the body
as a toolless subagent. Their expected traces differ, so one constant
dispatch policy cannot satisfy both:

  iterations — the done-check is the iteration count (iterations_run ==
    2); the second dispatch must carry the first dispatch's reply as its
    context packet. This proves the generic fixed-count packet carry.
  condition — the done-check is a condition the body's reply satisfies
    on the first iteration, under a bound of 3; the loop must exit
    complete after a single dispatch, never spending the bound.

The probe leaves no agent files or persisted session behind.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.live_claude_profiles import (  # noqa: E402
    _captured_text,
    _claude_command,
    _json_events,
)

INITIAL_PACKET = "PACKET:NONE"
FIRST_RESULT = "BODY_RESULT:R1"
SECOND_RESULT = "BODY_RESULT:R2"

SCENARIOS = {
    "iterations": {
        # dispatch i's prompt must contain packet_chain[i]; the body's
        # reply to dispatch i must contain reply_tokens[i].
        "packet_chain": (INITIAL_PACKET, FIRST_RESULT),
        "reply_tokens": (FIRST_RESULT, SECOND_RESULT),
        "exit_line": "LOOP_EXIT:complete ITERATIONS:2",
        "body_rules": (
            f"If your input contains the token {INITIAL_PACKET}, reply exactly: "
            f"{FIRST_RESULT} STATUS:CONTINUE\n"
            f"If your input contains the token {FIRST_RESULT}, reply exactly: "
            f"{SECOND_RESULT} STATUS:DONE"
        ),
        "law": (
            "Bound: 2 iterations. Done-check: iterations_run == 2 — a "
            "deterministic count, decided by your own dispatch tally."
        ),
        "bound_clause": "",
    },
    "condition": {
        "packet_chain": (INITIAL_PACKET,),
        "reply_tokens": (FIRST_RESULT,),
        "exit_line": "LOOP_EXIT:complete ITERATIONS:1",
        "body_rules": (
            f"If your input contains the token {INITIAL_PACKET}, reply exactly: "
            f"{FIRST_RESULT} STATUS:DONE"
        ),
        "law": (
            "Bound: 3 iterations. Done-check: the subagent's reply contains "
            "STATUS:DONE. Stop the moment the done-check passes; never spend "
            "the remaining bound after it passes."
        ),
        "bound_clause": (
            "\nIf the bound is spent without the done-check passing, reply "
            "exactly: LOOP_EXIT:limited ITERATIONS:3"
        ),
    },
}
SCENARIO_NAMES = tuple(SCENARIOS)


def _body_agent_type(pid: int | None = None) -> str:
    return f"orch-loop-body-e2e-{os.getpid() if pid is None else pid}"


def _build_body_agent(scenario: str, agent_type: str, model: str) -> dict:
    prompt = (
        "You are a loop-body probe. Reply with exactly one line and use no tools.\n"
        f"{SCENARIOS[scenario]['body_rules']}\n"
        "Otherwise reply exactly: BODY_RESULT:UNEXPECTED STATUS:ERROR"
    )
    return {
        agent_type: {
            "description": "Live loop-body probe; use only when explicitly named.",
            "prompt": prompt,
            "tools": [],
            "model": model,
        }
    }


def _parent_prompt(scenario: str, agent_type: str) -> str:
    config = SCENARIOS[scenario]
    return (
        "Run a bounded loop over a subagent body.\n"
        f"{config['law']}\n"
        f"Iteration 1: launch exactly one {agent_type} subagent with the "
        f"input {INITIAL_PACKET}\n"
        "Every later iteration: launch exactly one "
        f"{agent_type} subagent whose input is the previous iteration's "
        "full reply, verbatim — that reply is the context packet.\n"
        "Launch the iterations one at a time, in order, never in parallel.\n"
        "When the done-check passes, reply exactly: "
        "LOOP_EXIT:complete ITERATIONS:<n> where <n> is the number of "
        "subagents you launched."
        f"{config['bound_clause']}\n"
        "Use no tools other than the Agent tool."
    )


def _analyze_run(stdout: str, returncode: int, scenario: str, agent_type: str) -> dict:
    config = SCENARIOS[scenario]
    body_prompts: list[str] = []
    tool_ids: dict[str, int] = {}
    body_replies: dict[int, list[str]] = {}
    parent_text: list[str] = []
    unexpected_launches: list[str] = []
    unexpected_child_tools = 0

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
                if block.get("type") == "text":
                    parent_text.append(block.get("text", ""))
                if block.get("type") != "tool_use" or block.get("name") not in {"Agent", "Task"}:
                    continue
                launched = (block.get("input") or {}).get("subagent_type")
                if launched != agent_type:
                    unexpected_launches.append(str(launched))
                    continue
                tool_ids[block.get("id")] = len(body_prompts)
                body_prompts.append((block.get("input") or {}).get("prompt", ""))
            continue
        index = tool_ids.get(parent_tool_use_id)
        if index is None:
            continue
        for block in blocks:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "text":
                body_replies.setdefault(index, []).append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                unexpected_child_tools += 1

    expected = len(config["packet_chain"])
    failures = []
    if returncode != 0:
        failures.append(f"claude exited {returncode}")
    if len(body_prompts) != expected:
        failures.append(f"expected exactly {expected} body dispatches, saw {len(body_prompts)}")
    for index, token in enumerate(config["packet_chain"]):
        if index >= len(body_prompts):
            break
        if token in body_prompts[index]:
            continue
        if index == 0:
            failures.append("iteration 1 did not receive the initial packet")
        else:
            failures.append(
                f"iteration {index + 1} did not carry iteration {index}'s reply as its packet"
            )
    for index, token in enumerate(config["reply_tokens"]):
        if index < len(body_prompts) and token not in "\n".join(body_replies.get(index, [])):
            failures.append(f"iteration {index + 1} body reply missing its result token")
    if config["exit_line"] not in "\n".join(parent_text):
        failures.append(f"parent never reported {config['exit_line']}")
    if unexpected_launches:
        failures.append(f"unexpected subagent launches: {sorted(set(unexpected_launches))}")
    if unexpected_child_tools:
        failures.append(f"body used {unexpected_child_tools} unexpected tool call(s)")

    return {
        "scenario": scenario,
        "passed": not failures,
        "failures": failures,
        "returncode": returncode,
        "iterations_dispatched": len(body_prompts),
        "parent_exit_text": "\n".join(parent_text)[-200:],
    }


def _run_scenario(
    scenario: str,
    claude_invocation: list[str],
    model: str,
    effort: str,
    timeout: int,
    max_budget_usd: float,
) -> tuple[dict, str]:
    agent_type = _body_agent_type()
    agents = _build_body_agent(scenario, agent_type, model)
    command = claude_invocation + [
        "-p",
        _parent_prompt(scenario, agent_type),
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
        result = _analyze_run(completed.stdout, completed.returncode, scenario, agent_type)
        result["timed_out"] = False
        return result, completed.stderr
    except subprocess.TimeoutExpired as exc:
        result = _analyze_run(_captured_text(exc.stdout), 124, scenario, agent_type)
        result["timed_out"] = True
        result["failures"].append("probe timed out")
        result["passed"] = False
        return result, _captured_text(exc.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=240)
    parser.add_argument("--max-budget-usd", type=float, default=1.0)
    parser.add_argument("--model", default="haiku")
    parser.add_argument("--effort", default="low")
    parser.add_argument("--scenario", action="append", choices=SCENARIO_NAMES)
    args = parser.parse_args(argv)
    selected = tuple(args.scenario or SCENARIO_NAMES)

    claude_invocation = _claude_command()
    results = []
    all_stderr = []
    for scenario in selected:
        result, stderr = _run_scenario(
            scenario,
            claude_invocation,
            args.model,
            args.effort,
            args.timeout,
            args.max_budget_usd,
        )
        results.append(result)
        if stderr:
            all_stderr.append(stderr)

    passed = all(result["passed"] for result in results)
    print(json.dumps({"passed": passed, "scenarios": results}, indent=2, sort_keys=True))
    if not passed and all_stderr:
        print("\n".join(all_stderr)[-4000:], file=sys.stderr)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
