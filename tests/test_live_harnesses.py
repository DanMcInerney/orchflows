#!/usr/bin/env python3

"""The four live probe harnesses in tools/: the loop-body e2e, the sweep
e2e, and the Claude and Codex profile probes.

All four read one `claude`/`codex` stream-json transcript and grade it,
and all four are exercised here with the CLI mocked at the
`subprocess.run` seam -- no probe below ever launches an agent or reaches
a network. They shared three transcript builders (`_launch`, `_reply`,
`_stream`) as byte-identical copies in three files; the copies are now
the definitions above, one each.
"""

import collections
import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import live_claude_profiles as claude_live
from tools import live_codex_profiles as codex_live
from tools import live_loop_e2e as loop_live
from tools import live_sweep_e2e as sweep_live

LOOP_AGENT = "orch-loop-body-e2e-42"
SWEEP_AGENT = "orch-sweep-e2e-42"
SWEEP_PY = Path(sweep_live.__file__).resolve()


def _launch(tool_id: str, agent_type: str, prompt: str = None) -> dict:
    """A parent-level Agent dispatch. The sweep's probe carries no packet,
    so `prompt` is absent from its input rather than empty -- the harness
    reads the key, and a present-but-empty one is a different transcript."""
    launch_input = {"subagent_type": agent_type}
    if prompt is not None:
        launch_input["prompt"] = prompt
    return {
        "type": "assistant",
        "parent_tool_use_id": None,
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "id": tool_id,
                    "name": "Agent",
                    "input": launch_input,
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


def _stream(events: list) -> str:
    return "\n".join(json.dumps(event) for event in events)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# --- tools/live_loop_e2e.py -------------------------------------------


def _loop_launch(tool_id: str, prompt: str, agent_type: str = LOOP_AGENT) -> dict:
    return _launch(tool_id, agent_type, prompt)


def _good_iterations_events() -> list:
    return [
        _loop_launch("t1", loop_live.INITIAL_PACKET),
        _reply("t1", f"{loop_live.FIRST_RESULT} STATUS:CONTINUE"),
        _loop_launch("t2", f"{loop_live.FIRST_RESULT} STATUS:CONTINUE"),
        _reply("t2", f"{loop_live.SECOND_RESULT} STATUS:DONE"),
        _parent_text("LOOP_EXIT:complete ITERATIONS:2"),
    ]


def _good_condition_events() -> list:
    return [
        _loop_launch("t1", loop_live.INITIAL_PACKET),
        _reply("t1", f"{loop_live.FIRST_RESULT} STATUS:DONE"),
        _parent_text("LOOP_EXIT:complete ITERATIONS:1"),
    ]


class TestLoopAnalyzeRun(unittest.TestCase):
    def test_good_iterations_stream_passes(self):
        result = loop_live._analyze_run(
            _stream(_good_iterations_events()), 0, "iterations", LOOP_AGENT
        )
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(2, result["iterations_dispatched"])

    def test_good_condition_stream_passes(self):
        result = loop_live._analyze_run(
            _stream(_good_condition_events()), 0, "condition", LOOP_AGENT
        )
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(1, result["iterations_dispatched"])

    def test_scenarios_expect_distinct_traces(self):
        # A constant "always dispatch twice, report 2" policy must fail
        # the condition scenario: its stop rule ends the loop at one.
        result = loop_live._analyze_run(
            _stream(_good_iterations_events()), 0, "condition", LOOP_AGENT
        )
        self.assertFalse(result["passed"])
        self.assertIn("expected exactly 1 body dispatches, saw 2", result["failures"])

    def test_missing_initial_packet_fails(self):
        events = _good_iterations_events()
        events[0] = _loop_launch("t1", "PACKET:INVENTED")
        result = loop_live._analyze_run(_stream(events), 0, "iterations", LOOP_AGENT)
        self.assertFalse(result["passed"])
        self.assertIn("iteration 1 did not receive the initial packet", result["failures"])

    def test_missing_reply_tokens_fail_per_iteration(self):
        events = _good_iterations_events()
        events[1] = _reply("t1", "no token here")
        events[3] = _reply("t2", "still no token")
        result = loop_live._analyze_run(_stream(events), 0, "iterations", LOOP_AGENT)
        self.assertFalse(result["passed"])
        self.assertIn("iteration 1 body reply missing its result token", result["failures"])
        self.assertIn("iteration 2 body reply missing its result token", result["failures"])

    def test_non_dict_stream_entries_are_tolerated(self):
        events = _good_iterations_events()
        events[0]["message"]["content"].insert(0, "bare string block")
        events[1]["message"]["content"].append(42)
        stream = _stream(events) + '\n"a bare json string"\n[1, 2]'
        result = loop_live._analyze_run(stream, 0, "iterations", LOOP_AGENT)
        self.assertTrue(result["passed"], result["failures"])

    def test_packet_not_carried_into_second_dispatch_fails(self):
        events = _good_iterations_events()
        events[2] = _loop_launch("t2", "PACKET:INVENTED")
        result = loop_live._analyze_run(_stream(events), 0, "iterations", LOOP_AGENT)
        self.assertFalse(result["passed"])
        self.assertIn(
            "iteration 2 did not carry iteration 1's reply as its packet",
            result["failures"],
        )

    def test_dispatch_past_the_bound_fails(self):
        events = _good_iterations_events()
        events.insert(4, _loop_launch("t3", f"{loop_live.SECOND_RESULT} STATUS:DONE"))
        result = loop_live._analyze_run(_stream(events), 0, "iterations", LOOP_AGENT)
        self.assertFalse(result["passed"])
        self.assertIn("expected exactly 2 body dispatches, saw 3", result["failures"])

    def test_missing_exit_line_fails(self):
        result = loop_live._analyze_run(
            _stream(_good_iterations_events()[:-1]), 0, "iterations", LOOP_AGENT
        )
        self.assertFalse(result["passed"])
        self.assertIn(
            "parent never reported LOOP_EXIT:complete ITERATIONS:2", result["failures"]
        )

    def test_unexpected_agent_launch_fails(self):
        events = _good_iterations_events() + [
            _loop_launch("t9", "rogue", agent_type="other-agent")
        ]
        result = loop_live._analyze_run(_stream(events), 0, "iterations", LOOP_AGENT)
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
        result = loop_live._analyze_run(_stream(events), 0, "iterations", LOOP_AGENT)
        self.assertFalse(result["passed"])
        self.assertTrue(any("unexpected tool call" in f for f in result["failures"]))

    def test_nonzero_returncode_fails(self):
        result = loop_live._analyze_run(
            _stream(_good_iterations_events()), 3, "iterations", LOOP_AGENT
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


# --- tools/live_sweep_e2e.py ------------------------------------------


def _sweep_launch(tool_id: str, agent_type: str = SWEEP_AGENT) -> dict:
    return _launch(tool_id, agent_type)


def _good_events() -> list:
    return [_sweep_launch("t1"), _reply("t1", sweep_live.PROBE_SENTINEL)]


class TestSweepAnalyzeRun(unittest.TestCase):
    def test_good_stream_passes(self):
        result = sweep_live._analyze_run(_stream(_good_events()), 0, SWEEP_AGENT)
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(1, result["launch_count"])

    def test_missing_sentinel_fails(self):
        result = sweep_live._analyze_run(
            _stream([_sweep_launch("t1"), _reply("t1", "nope")]), 0, SWEEP_AGENT
        )
        self.assertFalse(result["passed"])
        self.assertIn("probe reply missing its sentinel", result["failures"])

    def test_missing_dispatch_fails(self):
        result = sweep_live._analyze_run("", 0, SWEEP_AGENT)
        self.assertFalse(result["passed"])
        self.assertIn("expected exactly 1 probe dispatch, saw 0", result["failures"])

    def test_duplicate_dispatch_fails(self):
        events = _good_events() + [_sweep_launch("t2")]
        result = sweep_live._analyze_run(_stream(events), 0, SWEEP_AGENT)
        self.assertFalse(result["passed"])
        self.assertIn("expected exactly 1 probe dispatch, saw 2", result["failures"])

    def test_unexpected_agent_launch_fails(self):
        events = _good_events() + [_sweep_launch("t9", agent_type="other-agent")]
        result = sweep_live._analyze_run(_stream(events), 0, SWEEP_AGENT)
        self.assertFalse(result["passed"])
        self.assertTrue(any("unexpected subagent launches" in f for f in result["failures"]))

    def test_body_tool_use_fails(self):
        events = _good_events() + [
            {
                "type": "assistant",
                "parent_tool_use_id": "t1",
                "message": {"content": [{"type": "tool_use", "id": "x", "name": "Bash"}]},
            }
        ]
        result = sweep_live._analyze_run(_stream(events), 0, SWEEP_AGENT)
        self.assertFalse(result["passed"])
        self.assertTrue(any("unexpected tool call" in f for f in result["failures"]))

    def test_nonzero_returncode_fails(self):
        result = sweep_live._analyze_run(_stream(_good_events()), 3, SWEEP_AGENT)
        self.assertFalse(result["passed"])
        self.assertIn("claude exited 3", result["failures"])


class TestRunId(unittest.TestCase):
    def test_generate_run_id_is_unique_and_prefixed(self):
        first = sweep_live._generate_run_id()
        second = sweep_live._generate_run_id()
        self.assertNotEqual(first, second)
        self.assertTrue(first.startswith(sweep_live.RUN_ID_PREFIX))
        self.assertTrue(second.startswith(sweep_live.RUN_ID_PREFIX))


class TestSnapshotPath(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_missing_file_records_did_not_exist(self):
        snapshot = sweep_live._snapshot_path(self.tmp / "absent.jsonl")
        self.assertFalse(snapshot.existed)
        self.assertIsNone(snapshot.digest)
        self.assertIsNone(snapshot.data)

    def test_existing_file_records_hash_and_bytes(self):
        path = self.tmp / "friction.jsonl"
        data = b'{"run":"other"}\n'
        path.write_bytes(data)
        snapshot = sweep_live._snapshot_path(path)
        self.assertTrue(snapshot.existed)
        self.assertEqual(_sha256(data), snapshot.digest)
        self.assertEqual(data, snapshot.data)


class TestCleanupFriction(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.path = self.tmp / "friction.jsonl"

    def tearDown(self):
        self._tmp.cleanup()

    def test_removes_only_tagged_lines_preserves_others(self):
        other = json.dumps({"run": "other-run", "observed": "x"})
        mine = json.dumps({"run": "mine", "observed": "y"})
        original = (other + "\n").encode("utf-8")
        self.path.write_bytes(original)
        snapshot = sweep_live._Snapshot(
            path=self.path, existed=True, digest=_sha256(original), data=original
        )
        self.path.write_bytes(original + (mine + "\n").encode("utf-8"))

        removed = sweep_live._cleanup_friction("mine", snapshot)

        self.assertEqual(1, removed)
        self.assertEqual(original, self.path.read_bytes())
        self.assertEqual(_sha256(original), _sha256(self.path.read_bytes()))

    def test_deletes_file_it_created_when_nothing_preexisted(self):
        snapshot = sweep_live._Snapshot(path=self.path, existed=False, digest=None, data=None)
        mine = json.dumps({"run": "mine", "observed": "y"})
        self.path.write_bytes((mine + "\n").encode("utf-8"))

        removed = sweep_live._cleanup_friction("mine", snapshot)

        self.assertEqual(1, removed)
        self.assertFalse(self.path.exists())

    def test_raises_when_untagged_prefix_diverges_from_snapshot(self):
        original = b'{"run":"other-run"}\n'
        snapshot = sweep_live._Snapshot(
            path=self.path, existed=True, digest=_sha256(original), data=original
        )
        # Simulate corruption: the pre-existing line was altered, not just
        # appended to.
        self.path.write_bytes(b'{"run":"tampered"}\n')

        with self.assertRaises(ValueError):
            sweep_live._cleanup_friction("mine", snapshot)


class TestCleanup(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.friction_path = self.tmp / "friction.jsonl"
        self.log_path = self.tmp / "run.json"

    def tearDown(self):
        self._tmp.cleanup()

    def test_falls_back_to_byte_identical_restore_on_divergence(self):
        original = b'{"run":"other-run"}\n'
        self.friction_path.write_bytes(original)
        snapshot = sweep_live._Snapshot(
            path=self.friction_path, existed=True, digest=_sha256(original), data=original
        )
        self.friction_path.write_bytes(b"not even json-lines\nmine\n")
        self.log_path.write_text("{}", encoding="utf-8")

        report = sweep_live._cleanup("mine", snapshot, self.log_path)

        self.assertTrue(report["friction_restored_byte_identical"])
        self.assertEqual(original, self.friction_path.read_bytes())
        self.assertFalse(self.log_path.exists())
        self.assertEqual([str(self.log_path)], report["files_deleted"])

    def test_missing_log_path_is_not_an_error(self):
        report = sweep_live._cleanup(
            "mine", sweep_live._Snapshot(self.friction_path, False, None, None), self.log_path
        )
        self.assertEqual([], report["files_deleted"])


class TestRunLiveSweepCleanupPaths(unittest.TestCase):
    """End-to-end cleanup guarantee: success, failure, timeout."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.friction_path = self.tmp / "friction.jsonl"
        self.log_dir = self.tmp / "logs"
        baseline = json.dumps({"run": "unrelated", "observed": "baseline"}) + "\n"
        self.friction_path.write_bytes(baseline.encode("utf-8"))
        self.pre_run_hash = _sha256(self.friction_path.read_bytes())
        self._patch = mock.patch.object(
            sweep_live.friction, "_target_path", return_value=self.friction_path
        )
        self._patch.start()
        self._pid_patch = mock.patch.object(sweep_live.os, "getpid", return_value=42)
        self._pid_patch.start()

    def tearDown(self):
        self._pid_patch.stop()
        self._patch.stop()
        self._tmp.cleanup()

    def _run(self):
        return sweep_live._run_live_sweep(
            ["claude"], "sonnet", "medium", 5, 1.0, self.log_dir, run_id="fixed-run-id"
        )

    def test_success_path_cleans_up_and_leaves_friction_untouched(self):
        stdout = _stream(_good_events())
        completed = subprocess.CompletedProcess(["claude"], 0, stdout=stdout, stderr="")
        with mock.patch.object(sweep_live.subprocess, "run", return_value=completed):
            result = self._run()

        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(0, result["cleanup"]["friction_lines_removed"])
        self.assertFalse(result["cleanup"]["friction_restored_byte_identical"])
        self.assertEqual(self.pre_run_hash, _sha256(self.friction_path.read_bytes()))
        self.assertEqual([], list(self.log_dir.glob("*")) if self.log_dir.exists() else [])

    def test_failure_path_cleans_up_tagged_friction_and_log_file(self):
        stdout = _stream([_sweep_launch("t1"), _reply("t1", "wrong sentinel")])
        completed = subprocess.CompletedProcess(["claude"], 0, stdout=stdout, stderr="")
        with mock.patch.object(sweep_live.subprocess, "run", return_value=completed):
            result = self._run()

        self.assertFalse(result["passed"])
        self.assertEqual(1, result["cleanup"]["friction_lines_removed"])
        self.assertFalse(result["cleanup"]["friction_restored_byte_identical"])
        self.assertEqual(self.pre_run_hash, _sha256(self.friction_path.read_bytes()))
        self.assertEqual([], list(self.log_dir.glob("*")) if self.log_dir.exists() else [])

    def test_timeout_path_cleans_up_tagged_friction_and_log_file(self):
        expired = subprocess.TimeoutExpired(["claude"], 5, output="not-json", stderr="timed out")
        with mock.patch.object(sweep_live.subprocess, "run", side_effect=expired):
            result = self._run()

        self.assertFalse(result["passed"])
        self.assertTrue(result["timed_out"])
        self.assertEqual(1, result["cleanup"]["friction_lines_removed"])
        self.assertFalse(result["cleanup"]["friction_restored_byte_identical"])
        self.assertEqual(self.pre_run_hash, _sha256(self.friction_path.read_bytes()))
        self.assertEqual([], list(self.log_dir.glob("*")) if self.log_dir.exists() else [])

    def test_run_id_tags_the_friction_entry_it_writes(self):
        stdout = _stream([_sweep_launch("t1"), _reply("t1", "wrong sentinel")])
        completed = subprocess.CompletedProcess(["claude"], 0, stdout=stdout, stderr="")
        seen_entries = []
        real_cleanup_friction = sweep_live._cleanup_friction

        def _spy_cleanup_friction(run_id, snapshot):
            # Inspect the file's content right before cleanup removes it.
            if snapshot.path.exists():
                for line in snapshot.path.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        seen_entries.append(json.loads(line))
            return real_cleanup_friction(run_id, snapshot)

        with mock.patch.object(sweep_live.subprocess, "run", return_value=completed), \
                mock.patch.object(sweep_live, "_cleanup_friction", side_effect=_spy_cleanup_friction):
            self._run()

        tagged = [entry for entry in seen_entries if entry.get("run") == "fixed-run-id"]
        self.assertEqual(1, len(tagged))
        self.assertEqual(sweep_live.FRICTION_CATEGORY, tagged[0]["category"])


class TestMainGuard(unittest.TestCase):
    def test_main_requires_explicit_invocation_argv(self):
        with mock.patch.object(sweep_live, "_claude_command", return_value=["claude"]), \
                mock.patch.object(sweep_live, "_run_live_sweep") as run_live_sweep, \
                contextlib.redirect_stdout(io.StringIO()):
            run_live_sweep.return_value = {"passed": True, "stderr": ""}
            exit_code = sweep_live.main(["--model", "sonnet", "--effort", "medium"])

        self.assertEqual(0, exit_code)
        args, kwargs = run_live_sweep.call_args
        self.assertEqual("sonnet", args[1])
        self.assertEqual("medium", args[2])


class TestLogDirIsInTheSink(unittest.TestCase):
    """The probe is run from whatever workspace is at hand; its per-run log
    lands in the one sink, never in the repository that happened to host the
    invocation. The harness itself is not run here -- it makes live model
    calls."""

    def test_the_default_log_dir_resolves_under_the_sink(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "sink"
            with mock.patch.dict(
                os.environ, {sweep_live.state_root.ENV_VAR: str(sink)}
            ):
                self.assertEqual(
                    sink / sweep_live.LOG_DIR_NAME, sweep_live.default_log_dir()
                )
                # Read at call time, so pointing the sink elsewhere moves it.
                moved = Path(tmp) / "moved"
                with mock.patch.dict(
                    os.environ, {sweep_live.state_root.ENV_VAR: str(moved)}
                ):
                    self.assertEqual(
                        moved / sweep_live.LOG_DIR_NAME, sweep_live.default_log_dir()
                    )

    def test_resolving_the_default_creates_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "sink"
            with mock.patch.dict(
                os.environ, {sweep_live.state_root.ENV_VAR: str(sink)}
            ):
                sweep_live.default_log_dir()
            self.assertFalse(sink.exists())

    def test_main_passes_the_sink_default_when_no_log_dir_is_named(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "sink"
            with mock.patch.object(sweep_live, "_claude_command", return_value=["claude"]), \
                    mock.patch.object(sweep_live, "_run_live_sweep") as run_live_sweep, \
                    mock.patch.dict(os.environ, {sweep_live.state_root.ENV_VAR: str(sink)}), \
                    contextlib.redirect_stdout(io.StringIO()):
                run_live_sweep.return_value = {"passed": True, "stderr": ""}
                sweep_live.main([])
                named = sweep_live.main(["--log-dir", str(Path(tmp) / "elsewhere")])

            self.assertEqual(0, named)
            self.assertEqual(
                [sink / sweep_live.LOG_DIR_NAME, Path(tmp) / "elsewhere"],
                [call.args[5] for call in run_live_sweep.call_args_list],
            )

    def test_no_repository_state_path_is_composed(self):
        source = SWEEP_PY.read_text(encoding="utf-8")
        self.assertIn("state_root.state_root()", source)
        self.assertNotIn('".orch"', source)
        self.assertNotIn(".orch/live-sweep-e2e", source)


# --- tools/live_claude_profiles.py and tools/live_codex_profiles.py ----


class TestClaudeLiveProfiles(unittest.TestCase):
    def test_builds_all_production_derived_probe_agents(self):
        agents, expected, configured = claude_live._build_probe_agents(
            claude_live.PROFILE_NAMES, pid=42
        )

        self.assertEqual(2, len(agents))
        self.assertEqual(set(agents), set(expected))
        self.assertEqual(set(agents), set(configured))
        for agent_type, definition in agents.items():
            self.assertIsNotNone(re.fullmatch(r"[a-z0-9-]+", agent_type))
            self.assertEqual([], definition["tools"])
            self.assertIn(expected[agent_type], definition["prompt"])
            self.assertEqual(configured[agent_type]["model"], definition["model"])
            self.assertEqual(configured[agent_type].get("effort"), definition.get("effort"))

    def test_accepts_exact_registered_launches_and_forwarded_sentinels(self):
        expected = {
            "orch-planner-e2e-42": "SENTINEL:planner",
            "orch-worker-e2e-42": "SENTINEL:worker",
        }
        events = [
            {
                "type": "system",
                "subtype": "init",
                "agents": list(expected),
            }
        ]
        for index, (agent_type, sentinel) in enumerate(expected.items()):
            tool_id = f"tool-{index}"
            events.extend(
                [
                    _launch(tool_id, agent_type),
                    {
                        "type": "assistant",
                        "parent_tool_use_id": tool_id,
                        "message": {
                            "model": f"reported-{index}",
                            "content": [{"type": "text", "text": sentinel}],
                        },
                    },
                ]
            )

        result = claude_live._analyze_run(
            _stream(events),
            returncode=0,
            expected=expected,
        )

        self.assertTrue(result["passed"])
        self.assertEqual([], result["missing_registrations"])
        self.assertEqual([], result["invalid_launches"])
        self.assertEqual([], result["missing_sentinels"])
        self.assertEqual(0, result["unexpected_child_tools"])
        self.assertEqual(
            {agent_type: [f"reported-{index}"] for index, agent_type in enumerate(expected)},
            result["reported_models"],
        )

    def test_rejects_duplicate_launches(self):
        agent_type = "orch-worker-e2e-42"
        sentinel = "SENTINEL:worker"
        events = [
            {"type": "system", "subtype": "init", "agents": [agent_type]},
            {
                "type": "assistant",
                "parent_tool_use_id": None,
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "id": tool_id,
                            "name": "Agent",
                            "input": {"subagent_type": agent_type},
                        }
                        for tool_id in ("tool-1", "tool-2")
                    ]
                },
            },
            _reply("tool-1", sentinel),
        ]

        result = claude_live._analyze_run(
            _stream(events),
            returncode=0,
            expected={agent_type: sentinel},
        )

        self.assertFalse(result["passed"])
        self.assertEqual([agent_type], result["invalid_launches"])

    def test_timeout_returns_structured_failure(self):
        expected = {"orch-worker-e2e-42": "SENTINEL:worker"}
        expired = subprocess.TimeoutExpired(
            ["claude"], 1, output="not-json", stderr="probe timed out"
        )

        with mock.patch.object(claude_live.subprocess, "run", side_effect=expired):
            result, stderr = claude_live._run_probe(["claude"], 1, expected)

        self.assertFalse(result["passed"])
        self.assertTrue(result["timed_out"])
        self.assertEqual(124, result["returncode"])
        self.assertEqual("probe timed out", stderr)


class TestCodexLiveProfiles(unittest.TestCase):
    def test_stable_surface_accepts_all_sentinels(self):
        expected = {
            "orch_planner_e2e_42": "SENTINEL:planner",
            "orch_worker_e2e_42": "SENTINEL:worker",
        }
        stdout = "\n".join(
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {"type": "agent_message", "text": sentinel},
                }
            )
            for sentinel in expected.values()
        )

        result = codex_live._classify_surface("stable", stdout, 0, expected)

        self.assertEqual("passed", result["status"])
        self.assertTrue(result["passed"])
        self.assertEqual([], result["missing_sentinels"])

    def test_v2_surface_reports_explicit_unavailable_marker(self):
        stdout = json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "type": "agent_message",
                    "text": codex_live.V2_UNSUPPORTED_MARKER,
                },
            }
        )

        result = codex_live._classify_surface(
            "v2", stdout, 0, {"orch_planner_e2e_42": "SENTINEL:planner"}
        )

        self.assertEqual("unsupported", result["status"])
        self.assertFalse(result["passed"])
        self.assertFalse(result["supported"])

    def test_v2_surface_accepts_all_sentinels(self):
        expected = {"orch_planner_e2e_42": "SENTINEL:planner"}
        stdout = json.dumps(
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "SENTINEL:planner"},
            }
        )

        result = codex_live._classify_surface("v2", stdout, 0, expected)

        self.assertEqual("passed", result["status"])
        self.assertTrue(result["passed"])
        self.assertTrue(result["supported"])

    def test_v2_surface_does_not_mask_missing_sentinel(self):
        stdout = json.dumps(
            {
                "type": "item.completed",
                "item": {"type": "agent_message", "text": "could not launch"},
            }
        )

        result = codex_live._classify_surface(
            "v2", stdout, 0, {"orch_planner_e2e_42": "SENTINEL:planner"}
        )

        self.assertEqual("failed", result["status"])
        self.assertEqual(["SENTINEL:planner"], result["missing_sentinels"])

    def test_v2_unavailable_marker_with_command_use_fails(self):
        stdout = "\n".join(
            [
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {
                            "type": "agent_message",
                            "text": codex_live.V2_UNSUPPORTED_MARKER,
                        },
                    }
                ),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "command_execution", "command": "echo nope"},
                    }
                ),
            ]
        )

        result = codex_live._classify_surface(
            "v2", stdout, 0, {"orch_planner_e2e_42": "SENTINEL:planner"}
        )

        self.assertEqual("failed", result["status"])
        self.assertEqual(1, result["unexpected_tool_actions"])

    def test_file_tool_activity_fails_the_surface(self):
        expected = {"orch_planner_e2e_42": "SENTINEL:planner"}
        stdout = "\n".join(
            [
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "agent_message", "text": "SENTINEL:planner"},
                    }
                ),
                json.dumps(
                    {
                        "type": "item.completed",
                        "item": {"type": "file_change", "path": "unexpected.txt"},
                    }
                ),
            ]
        )

        result = codex_live._classify_surface("stable", stdout, 0, expected)

        self.assertEqual("failed", result["status"])
        self.assertEqual(1, result["unexpected_tool_actions"])

    def _capture_surface_command(self, surface):
        captured = {}

        def _fake_run(command, **kwargs):
            captured["command"] = command
            return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

        expected = {"orch_planner_e2e_42": "SENTINEL:planner"}
        with mock.patch.object(codex_live.subprocess, "run", side_effect=_fake_run):
            codex_live._run_surface(surface, ["codex"], expected, 5)
        return captured["command"]

    def test_stable_surface_command_uses_native_fork_field_and_default_config(self):
        # Exercise the public _run_surface seam so the config-args/prompt
        # wiring is proven on the actual argv, not just each helper in
        # isolation echoing its own literal.
        command = self._capture_surface_command("stable")
        self.assertNotIn("--ignore-user-config", command)
        self.assertIn("fork_context=false", command[-1])

    def test_v2_surface_command_ignores_stable_user_config_and_uses_native_fork_field(self):
        command = self._capture_surface_command("v2")
        self.assertIn("--ignore-user-config", command)
        self.assertIn('fork_turns="none"', command[-1])
        self.assertIn(codex_live.V2_UNSUPPORTED_MARKER, command[-1])

    def test_timeout_returns_structured_surface_failure(self):
        expected = {"orch_planner_e2e_42": "SENTINEL:planner"}
        expired = subprocess.TimeoutExpired(
            ["codex"], 1, output="not-json", stderr="probe timed out"
        )

        with mock.patch.object(codex_live.subprocess, "run", side_effect=expired):
            result, stderr = codex_live._run_surface("v2", ["codex"], expected, 1)

        self.assertEqual("failed", result["status"])
        self.assertTrue(result["timed_out"])
        self.assertEqual(124, result["returncode"])
        self.assertEqual("probe timed out", stderr)

    def test_exception_during_surface_run_still_cleans_up_temp_agent_file(self):
        # The rendered probe .toml is written before any CLI call; if the
        # subprocess call blows up, the finally block in main() must still
        # unlink it rather than leaking a live agent file into ~/.codex.
        with tempfile.TemporaryDirectory() as codex_home:
            agents_dir = Path(codex_home) / "agents"
            with mock.patch.dict(os.environ, {"CODEX_HOME": codex_home}), \
                    mock.patch.object(codex_live, "_codex_command", return_value=["codex"]), \
                    mock.patch.object(
                        codex_live.subprocess, "run", side_effect=RuntimeError("boom")
                    ):
                with self.assertRaises(RuntimeError):
                    codex_live.main(["--profile", "orch-worker"])

            self.assertEqual([], list(agents_dir.glob("*.toml")))

    def test_probe_sentinel_injection_does_not_require_tomllib(self):
        profile = codex_live.install.load_role_profiles()["orch-planner"]
        rendered = codex_live.install.render_codex_agent(
            "orch-planner", profile, codex_live.REPO_ROOT / "rules" / "roles.md"
        )

        with mock.patch.object(codex_live.install, "tomllib", None):
            injected = codex_live._with_probe_sentinel(rendered, "SENTINEL:planner")

        self.assertIn("SENTINEL:planner", injected)


# --- benchmarks/routing/cases.json ------------------------------------


ROUTING_DIR = Path(__file__).resolve().parents[1] / "benchmarks" / "routing"
ROUTING_CASES = ROUTING_DIR / "cases.json"
ROUTE_CLASSES = ("answer", "ticket", "fix", "build", "named")
CASE_KEYS = {"id", "prompt", "expected", "note", "distractor"}
# A deleted or never-routed name whose surface words a prompt can borrow
# without the prompt's correct route changing.
LURE_WORDS = ("diagnose", "triage", "review", "worklog")


class TestRoutingCases(unittest.TestCase):
    """The case set the routing benchmark measures. Graded here rather than
    only by the harness that reads it: a case file that has drifted below
    its spread is worthless whether or not the harness parses it."""

    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(ROUTING_CASES.read_text(encoding="utf-8"))

    def _class_of(self, case):
        return case["expected"].split(":", 1)[0]

    def test_every_case_has_exactly_the_documented_shape(self):
        self.assertIsInstance(self.cases, list)
        for case in self.cases:
            with self.subTest(case=case.get("id")):
                self.assertEqual(CASE_KEYS, set(case))
                self.assertIsInstance(case["distractor"], bool)
                for key in ("id", "prompt", "expected", "note"):
                    self.assertTrue(case[key].strip(), key)

    def test_case_ids_are_unique(self):
        ids = [case["id"] for case in self.cases]
        self.assertEqual(len(ids), len(set(ids)))

    def test_the_set_carries_at_least_twenty_four_cases(self):
        self.assertGreaterEqual(len(self.cases), 24)

    def test_every_expected_route_is_in_the_enum(self):
        for case in self.cases:
            with self.subTest(case=case["id"]):
                expected = case["expected"]
                if expected.startswith("named:"):
                    self.assertTrue(expected.split(":", 1)[1].strip())
                else:
                    self.assertIn(expected, ROUTE_CLASSES)
                    self.assertNotEqual("named", expected, "named needs a name")

    def test_every_class_carries_at_least_four_cases(self):
        counts = collections.Counter(self._class_of(case) for case in self.cases)
        self.assertEqual(set(ROUTE_CLASSES), set(counts))
        for route_class in ROUTE_CLASSES:
            with self.subTest(route_class=route_class):
                self.assertGreaterEqual(counts[route_class], 4, counts)

    def test_at_least_four_distractors_borrow_a_lure_word(self):
        distractors = [case for case in self.cases if case["distractor"]]
        self.assertGreaterEqual(len(distractors), 4)
        for case in distractors:
            with self.subTest(case=case["id"]):
                prompt = case["prompt"].lower()
                self.assertTrue(
                    any(word in prompt for word in LURE_WORDS),
                    "a distractor must borrow a deleted or non-routed name",
                )
                # The whole point: the surface word is a lure, and the
                # correct route is still one of the three routed classes.
                self.assertIn(self._class_of(case), ("answer", "ticket", "fix"))

    def test_no_routed_case_reads_as_an_instruction_to_the_grader(self):
        # Prompts are typed into a live session; a prompt that dictated its
        # own route would grade the transcript, not the routing.
        for case in self.cases:
            with self.subTest(case=case["id"]):
                self.assertNotIn("ROUTE:", case["prompt"])

    def test_the_readme_states_the_command_and_the_decision_rule(self):
        readme = ROUTING_DIR / "README.md"
        text = readme.read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 25)
        self.assertIn("tools/live_routing_bench.py", text)
        self.assertIn("0.05", text)
        self.assertIn("--claude-adapters", text)


if __name__ == "__main__":
    unittest.main()
