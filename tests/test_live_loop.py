#!/usr/bin/env python3

import json
import subprocess
import unittest
from unittest import mock

from tools import live_loop_e2e as loop_live

AGENT = "orch-loop-body-e2e-42"


def _launch(tool_id: str, prompt: str, agent_type: str = AGENT) -> dict:
    return {
        "type": "assistant",
        "parent_tool_use_id": None,
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": "Agent",
                    "input": {"subagent_type": agent_type, "prompt": prompt},
                }
            ]
        },
    }


def _reply(tool_id: str, text: str) -> dict:
    return {
        "type": "assistant",
        "parent_tool_use_id": tool_id,
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _parent_text(text: str) -> dict:
    return {
        "type": "assistant",
        "parent_tool_use_id": None,
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _stream(events: list[dict]) -> str:
    return "\n".join(json.dumps(event) for event in events)


def _good_iterations_events() -> list[dict]:
    return [
        _launch("t1", loop_live.INITIAL_PACKET),
        _reply("t1", f"{loop_live.FIRST_RESULT} STATUS:CONTINUE"),
        _launch("t2", f"{loop_live.FIRST_RESULT} STATUS:CONTINUE"),
        _reply("t2", f"{loop_live.SECOND_RESULT} STATUS:DONE"),
        _parent_text("LOOP_EXIT:complete ITERATIONS:2"),
    ]


def _good_condition_events() -> list[dict]:
    return [
        _launch("t1", loop_live.INITIAL_PACKET),
        _reply("t1", f"{loop_live.FIRST_RESULT} STATUS:DONE"),
        _parent_text("LOOP_EXIT:complete ITERATIONS:1"),
    ]


class TestAnalyzeRun(unittest.TestCase):
    def test_good_iterations_stream_passes(self):
        result = loop_live._analyze_run(
            _stream(_good_iterations_events()), 0, "iterations", AGENT
        )
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(2, result["iterations_dispatched"])

    def test_good_condition_stream_passes(self):
        result = loop_live._analyze_run(
            _stream(_good_condition_events()), 0, "condition", AGENT
        )
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(1, result["iterations_dispatched"])

    def test_scenarios_expect_distinct_traces(self):
        # A constant "always dispatch twice, report 2" policy must fail
        # the condition scenario: its stop rule ends the loop at one.
        result = loop_live._analyze_run(
            _stream(_good_iterations_events()), 0, "condition", AGENT
        )
        self.assertFalse(result["passed"])
        self.assertIn("expected exactly 1 body dispatches, saw 2", result["failures"])

    def test_missing_initial_packet_fails(self):
        events = _good_iterations_events()
        events[0] = _launch("t1", "PACKET:INVENTED")
        result = loop_live._analyze_run(_stream(events), 0, "iterations", AGENT)
        self.assertFalse(result["passed"])
        self.assertIn("iteration 1 did not receive the initial packet", result["failures"])

    def test_missing_reply_tokens_fail_per_iteration(self):
        events = _good_iterations_events()
        events[1] = _reply("t1", "no token here")
        events[3] = _reply("t2", "still no token")
        result = loop_live._analyze_run(_stream(events), 0, "iterations", AGENT)
        self.assertFalse(result["passed"])
        self.assertIn("iteration 1 body reply missing its result token", result["failures"])
        self.assertIn("iteration 2 body reply missing its result token", result["failures"])

    def test_non_dict_stream_entries_are_tolerated(self):
        events = _good_iterations_events()
        events[0]["message"]["content"].insert(0, "bare string block")
        events[1]["message"]["content"].append(42)
        stream = _stream(events) + '\n"a bare json string"\n[1, 2]'
        result = loop_live._analyze_run(stream, 0, "iterations", AGENT)
        self.assertTrue(result["passed"], result["failures"])

    def test_packet_not_carried_into_second_dispatch_fails(self):
        events = _good_iterations_events()
        events[2] = _launch("t2", "PACKET:INVENTED")
        result = loop_live._analyze_run(_stream(events), 0, "iterations", AGENT)
        self.assertFalse(result["passed"])
        self.assertIn(
            "iteration 2 did not carry iteration 1's reply as its packet",
            result["failures"],
        )

    def test_dispatch_past_the_bound_fails(self):
        events = _good_iterations_events()
        events.insert(4, _launch("t3", f"{loop_live.SECOND_RESULT} STATUS:DONE"))
        result = loop_live._analyze_run(_stream(events), 0, "iterations", AGENT)
        self.assertFalse(result["passed"])
        self.assertIn("expected exactly 2 body dispatches, saw 3", result["failures"])

    def test_missing_exit_line_fails(self):
        result = loop_live._analyze_run(
            _stream(_good_iterations_events()[:-1]), 0, "iterations", AGENT
        )
        self.assertFalse(result["passed"])
        self.assertIn(
            "parent never reported LOOP_EXIT:complete ITERATIONS:2", result["failures"]
        )

    def test_unexpected_agent_launch_fails(self):
        events = _good_iterations_events() + [_launch("t9", "rogue", agent_type="other-agent")]
        result = loop_live._analyze_run(_stream(events), 0, "iterations", AGENT)
        self.assertFalse(result["passed"])
        self.assertTrue(any("unexpected subagent launches" in f for f in result["failures"]))

    def test_body_tool_use_fails(self):
        events = _good_iterations_events()
        events.append(
            {
                "type": "assistant",
                "parent_tool_use_id": "t2",
                "message": {"content": [{"type": "tool_use", "id": "x", "name": "Bash"}]},
            }
        )
        result = loop_live._analyze_run(_stream(events), 0, "iterations", AGENT)
        self.assertFalse(result["passed"])
        self.assertTrue(any("unexpected tool call" in f for f in result["failures"]))

    def test_nonzero_returncode_fails(self):
        result = loop_live._analyze_run(
            _stream(_good_iterations_events()), 3, "iterations", AGENT
        )
        self.assertFalse(result["passed"])
        self.assertIn("claude exited 3", result["failures"])


class TestBuiltCommand(unittest.TestCase):
    """Exercise the public _run_scenario seam: assert the actual argv shape
    fed to the (mocked) subprocess runner, not the private prompt-builders
    in isolation mirroring their own constants."""

    def _capture_command(self, scenario, model="haiku", effort="low"):
        captured = {}

        def _fake_run(command, **kwargs):
            captured["command"] = command
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        with mock.patch.object(loop_live.subprocess, "run", side_effect=_fake_run):
            loop_live._run_scenario(scenario, ["claude"], model, effort, 5, 1.0)
        return captured["command"]

    def test_iterations_command_wires_model_effort_and_done_check(self):
        command = self._capture_command("iterations", model="haiku", effort="low")
        self.assertEqual("haiku", command[command.index("--model") + 1])
        self.assertEqual("low", command[command.index("--effort") + 1])
        prompt = command[command.index("-p") + 1]
        self.assertIn("iterations_run == 2", prompt)
        self.assertIn(loop_live.INITIAL_PACKET, prompt)
        (agent_definition,) = json.loads(command[command.index("--agents") + 1]).values()
        self.assertEqual([], agent_definition["tools"])
        self.assertEqual("haiku", agent_definition["model"])
        self.assertIn(loop_live.FIRST_RESULT, agent_definition["prompt"])
        self.assertIn(loop_live.SECOND_RESULT, agent_definition["prompt"])

    def test_condition_command_wires_stop_rule_bound_and_single_reply(self):
        command = self._capture_command("condition")
        prompt = command[command.index("-p") + 1]
        self.assertIn("STATUS:DONE", prompt)
        self.assertIn("Bound: 3 iterations", prompt)
        self.assertIn("LOOP_EXIT:limited ITERATIONS:3", prompt)
        (agent_definition,) = json.loads(command[command.index("--agents") + 1]).values()
        self.assertIn(f"{loop_live.FIRST_RESULT} STATUS:DONE", agent_definition["prompt"])
        self.assertNotIn(loop_live.SECOND_RESULT, agent_definition["prompt"])

    def test_exit_lines_are_never_dictated_verbatim_in_the_built_command(self):
        # The parent must derive <n> from its own dispatch tally; the
        # built prompt never hands it the expected exit line to echo.
        for scenario in loop_live.SCENARIO_NAMES:
            command = self._capture_command(scenario)
            prompt = command[command.index("-p") + 1]
            self.assertNotIn(loop_live.SCENARIOS[scenario]["exit_line"], prompt)


class TestRunScenario(unittest.TestCase):
    def test_timeout_returns_structured_failure(self):
        expired = subprocess.TimeoutExpired(
            ["claude"], 1, output="not-json", stderr="probe timed out"
        )
        with mock.patch.object(loop_live.subprocess, "run", side_effect=expired):
            result, stderr = loop_live._run_scenario(
                "iterations", ["claude"], "haiku", "low", 1, 1.0
            )
        self.assertFalse(result["passed"])
        self.assertTrue(result["timed_out"])
        self.assertIn("probe timed out", result["failures"])
        self.assertEqual("probe timed out", stderr)


if __name__ == "__main__":
    unittest.main()
