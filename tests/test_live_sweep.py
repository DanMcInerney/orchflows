#!/usr/bin/env python3

import contextlib
import hashlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import live_sweep_e2e as sweep_live

AGENT = "orch-sweep-e2e-42"


def _launch(tool_id: str, agent_type: str = AGENT) -> dict:
    return {
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
            ]
        },
    }


def _reply(tool_id: str, text: str) -> dict:
    return {
        "type": "assistant",
        "parent_tool_use_id": tool_id,
        "message": {"content": [{"type": "text", "text": text}]},
    }


def _stream(events: list[dict]) -> str:
    return "\n".join(json.dumps(event) for event in events)


def _good_events() -> list[dict]:
    return [_launch("t1"), _reply("t1", sweep_live.PROBE_SENTINEL)]


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class TestAnalyzeRun(unittest.TestCase):
    def test_good_stream_passes(self):
        result = sweep_live._analyze_run(_stream(_good_events()), 0, AGENT)
        self.assertTrue(result["passed"], result["failures"])
        self.assertEqual(1, result["launch_count"])

    def test_missing_sentinel_fails(self):
        result = sweep_live._analyze_run(_stream([_launch("t1"), _reply("t1", "nope")]), 0, AGENT)
        self.assertFalse(result["passed"])
        self.assertIn("probe reply missing its sentinel", result["failures"])

    def test_missing_dispatch_fails(self):
        result = sweep_live._analyze_run("", 0, AGENT)
        self.assertFalse(result["passed"])
        self.assertIn("expected exactly 1 probe dispatch, saw 0", result["failures"])

    def test_duplicate_dispatch_fails(self):
        events = _good_events() + [_launch("t2")]
        result = sweep_live._analyze_run(_stream(events), 0, AGENT)
        self.assertFalse(result["passed"])
        self.assertIn("expected exactly 1 probe dispatch, saw 2", result["failures"])

    def test_unexpected_agent_launch_fails(self):
        events = _good_events() + [_launch("t9", agent_type="other-agent")]
        result = sweep_live._analyze_run(_stream(events), 0, AGENT)
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
        result = sweep_live._analyze_run(_stream(events), 0, AGENT)
        self.assertFalse(result["passed"])
        self.assertTrue(any("unexpected tool call" in f for f in result["failures"]))

    def test_nonzero_returncode_fails(self):
        result = sweep_live._analyze_run(_stream(_good_events()), 3, AGENT)
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
        stdout = _stream([_launch("t1"), _reply("t1", "wrong sentinel")])
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
        stdout = _stream([_launch("t1"), _reply("t1", "wrong sentinel")])
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
    def test_main_is_not_invoked_on_import(self):
        # Importing the module (already done at module load time above) must
        # never spawn a subprocess; guard against regressions where module-
        # level code calls main() outside the __main__ check.
        with mock.patch.object(sweep_live.subprocess, "run") as run:
            import importlib

            importlib.reload(sweep_live)
            run.assert_not_called()

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


if __name__ == "__main__":
    unittest.main()
