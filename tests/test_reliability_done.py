"""Durable verification at the command seam, including refusal and replay.

All processes and state are fixture-owned. Environment and module patches use
context managers / cleanups (selected-module-boundary serial classification).
"""

from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

from scripts import tickets_done, tickets_done_evidence as evidence
from tests.test_run_required_cases.harness import RunRequiredCase, git
from tests.tree_removal import remove_repo_tree
from tools.run_required_support import execution


def command(code):
    return f'"{sys.executable}" -c "{code}"'


class DurableDoneTest(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.root = Path(holder.name)
        self.tree = self.root / "producer"
        self.tree.mkdir()
        git(self.tree, "init", "--quiet")
        git(self.tree, "config", "user.email", "test@example.invalid")
        git(self.tree, "config", "user.name", "test")
        (self.tree / "source").write_text("before", encoding="utf-8")
        git(self.tree, "add", "source")
        git(self.tree, "commit", "--quiet", "-m", "before")
        state = mock.patch.dict(os.environ, {
            "ORCHFLOWS_STATE_HOME": str(self.root / "state"),
        })
        state.start()
        self.addCleanup(state.stop)

    def receipt(self, reference):
        path = Path(reference["path"])
        raw = path.read_bytes()
        self.assertEqual(reference["sha256"], hashlib.sha256(raw).hexdigest())
        return json.loads(raw)

    def test_full_failure_prefix_and_raw_hashes_survive_producer_removal(self):
        code = "import sys; sys.stdout.buffer.write(b'FIRST_FAILURE'+b'x'*5001); sys.stderr.buffer.write(bytes([255,0,10])); sys.exit(7)"
        reading, refusal = tickets_done._command_reading(command(code), self.tree)
        self.assertIsNone(refusal)
        self.assertFalse(reading["done"])
        self.assertEqual(7, reading["exit"])
        self.assertNotIn("FIRST_FAILURE", reading["stdout"])
        expected_project = str(self.tree.resolve())
        remove_repo_tree(self.tree)
        stored = self.receipt(reading["evidence"])
        out = Path(stored["stdout_path"]).read_bytes()
        err = Path(stored["stderr_path"]).read_bytes()
        self.assertTrue(out.startswith(b"FIRST_FAILURE"))
        self.assertEqual(bytes([255, 0, 10]), err)
        self.assertEqual(hashlib.sha256(out).hexdigest(), stored["stdout_sha256"])
        self.assertEqual(hashlib.sha256(err).hexdigest(), stored["stderr_sha256"])
        self.assertEqual(stored["artifact_before"], stored["artifact_after"])
        self.assertFalse(stored["changed_tree"])
        self.assertLessEqual(stored["started_at"], stored["ended_at"])
        self.assertEqual(expected_project, stored["project"])
        self.assertIn(reading["evidence"]["path"], tickets_done.verification_line(reading))

    def test_zero_exit_and_unicode_are_success_only_for_unchanged_source(self):
        reading, refusal = tickets_done._command_reading(
            command("import sys; sys.stdout.buffer.write(chr(9733).encode('utf-8'))"), self.tree)
        self.assertIsNone(refusal)
        self.assertTrue(reading["done"])
        self.assertEqual(chr(9733), reading["stdout"])
        self.assertEqual(git(self.tree, "rev-parse", "HEAD"), reading["artifact_before"]["commit"])

    def test_changed_commit_or_uncommitted_bytes_cannot_pass_on_zero_exit(self):
        for code in (
            "open('source','w').write('after')",
            "import subprocess; subprocess.run(['git','add','source'],check=True); subprocess.run(['git','commit','-qm','after'],check=True)",
        ):
            with self.subTest(code=code):
                reading, refusal = tickets_done._command_reading(command(code), self.tree)
                self.assertIsNone(refusal)
                self.assertEqual(0, reading["exit"])
                self.assertTrue(reading["changed_tree"])
                self.assertFalse(reading["done"])
                self.receipt(reading["evidence"])
        (self.tree / "source").write_text("first dirty value", encoding="utf-8")
        reading, refusal = tickets_done._command_reading(
            command("open('source','w').write('second dirty value')"), self.tree)
        self.assertIsNone(refusal)
        self.assertTrue(reading["changed_tree"])
        self.assertFalse(reading["done"])

    def test_timeout_retains_partial_output_and_cannot_pass(self):
        with mock.patch.object(tickets_done, "COMMAND_TIMEOUT_SECONDS", 2):
            reading, refusal = tickets_done._command_reading(command(
                "import time; print('before-timeout',flush=True); time.sleep(20)"), self.tree)
        self.assertIsNone(reading)
        stored = self.receipt(refusal["evidence"])
        self.assertEqual("timeout", stored["outcome"])
        self.assertIsNotNone(stored["exit_status"])
        self.assertNotIn("cleanup_error", stored)
        self.assertIn(b"before-timeout", Path(stored["stdout_path"]).read_bytes())

    def test_spawn_refusal_is_durable_without_an_observed_exit(self):
        reading, refusal = tickets_done._command_reading("absent-orchflows-command", self.tree)
        self.assertIsNone(reading)
        self.assertIn("on no PATH entry", refusal["error"])
        stored = self.receipt(refusal["evidence"])
        self.assertEqual("spawn-failed", stored["outcome"])
        self.assertIsNone(stored["exit_status"])

    def test_os_spawn_failure_is_durable(self):
        reading, refusal = tickets_done._command_reading(
            '"' + str(self.root / "absent.exe") + '"', self.tree)
        self.assertIsNone(reading)
        self.assertEqual("spawn-failed", self.receipt(refusal["evidence"])["outcome"])

    def test_evidence_write_failure_refuses_before_spawning(self):
        with mock.patch.object(evidence, "_write", side_effect=OSError("read-only sink")), \
                mock.patch.object(evidence.subprocess, "Popen") as spawn:
            reading, refusal = tickets_done._command_reading(command("pass"), self.tree)
        self.assertIsNone(reading)
        self.assertIn("could not be persisted", refusal["error"])
        # Identity observation uses subprocess.run, and therefore Popen; the
        # command itself is distinguishable by its frozen argv.
        self.assertFalse(any(call.args and call.args[0][0] == sys.executable
                             for call in spawn.call_args_list))

    def test_interrupted_supervision_cannot_publish_success(self):
        child = mock.Mock(pid=12345, returncode=-1,
                          stdout=io.BytesIO(), stderr=io.BytesIO())
        child.wait.side_effect = KeyboardInterrupt
        with mock.patch.object(evidence, "artifact_identity", return_value={"kind": "git-source"}), \
                mock.patch.object(evidence.subprocess, "Popen", return_value=child), \
                mock.patch.object(evidence, "_WindowsJob", return_value=None), \
                mock.patch.object(evidence, "_terminate") as cleanup:
            reading, refusal = tickets_done._command_reading(command("pass"), self.tree)
        self.assertIsNone(reading)
        cleanup.assert_called_once_with(child)
        self.assertEqual("interrupted", self.receipt(refusal["evidence"])["outcome"])

    def test_required_timeout_preserves_observed_exit_separately(self):
        with mock.patch.object(execution, "CHECK_TIMEOUT_SECONDS", 2):
            _, record, out, _ = execution.run_one("probe", [sys.executable, "-c",
                "import time; print('prefix',flush=True); time.sleep(20)"], self.tree)
        self.assertEqual(124, record["exit_status"])
        self.assertEqual("timeout", record["outcome"])
        self.assertIsNotNone(record["observed_exit"])
        self.assertIn(b"prefix", out)
        self.receipt(record["evidence"])

    def test_timeout_stops_owned_descendant_processes(self):
        marker = self.root / "heartbeat"
        child_script = self.root / "descendant.py"
        child_script.write_text(
            "import time\nfrom pathlib import Path\n"
            f"marker = Path({str(marker)!r})\n"
            "for _ in range(200):\n marker.write_text(str(time.time()))\n time.sleep(.1)\n",
            encoding="utf-8")
        code = ("import subprocess,sys; "
                f"subprocess.Popen([sys.executable,{str(child_script)!r}])")
        record, _, _ = evidence.run_command([sys.executable, "-c", code], self.tree, 2)
        self.assertEqual("timeout", record["outcome"])
        self.assertNotIn("cleanup_error", record)
        before = marker.read_bytes()
        time.sleep(.3)
        self.assertEqual(before, marker.read_bytes())

    def test_inherited_streams_are_drained_before_success(self):
        child_code = "import time; time.sleep(.5); print('late-output',flush=True)"
        code = ("import subprocess,sys; "
                f"subprocess.Popen([sys.executable,'-c',{child_code!r}])")
        try:
            record, out, _ = evidence.run_command([sys.executable, "-c", code], self.tree, 3)
            self.assertEqual("completed", record["outcome"])
            self.assertIn(b"late-output", out)
        finally:
            time.sleep(.8)  # The counterexample's child has a fixed half-second life.

    @unittest.skipUnless(os.name == "nt", "Windows job handle lifetime")
    def test_killed_supervisor_keeps_running_evidence_and_stops_its_job(self):
        supervisor_pid, child_pid, heartbeat = [self.root / name for name in (
            "supervisor-pid", "child-pid", "heartbeat")]
        child_code = ("import os,time\nfrom pathlib import Path\n"
                      f"Path({str(child_pid)!r}).write_text(str(os.getpid()))\n"
                      "print('stream-before-interrupt',flush=True)\n"
                      f"for _ in range(200):\n Path({str(heartbeat)!r}).write_text(str(time.time()))\n time.sleep(.1)\n")
        supervisor = ("import os,sys\nfrom pathlib import Path\n"
                      "from scripts.tickets_done_evidence import run_command\n"
                      f"Path({str(supervisor_pid)!r}).write_text(str(os.getpid()))\n"
                      f"run_command([sys.executable,'-c',{child_code!r}],{str(self.tree)!r},20)\n")
        process = subprocess.Popen([sys.executable, "-c", supervisor],
                                   cwd=str(Path(__file__).resolve().parents[1]),
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        success = False
        try:
            deadline, stored = time.monotonic() + 10, None
            while time.monotonic() < deadline:
                for path in (self.root / "state" / "verification").glob("*/command.json"):
                    stored = json.loads(path.read_text(encoding="utf-8"))
                    stream = Path(stored["stdout_path"])
                    if stream.exists() and b"stream-before-interrupt" in stream.read_bytes():
                        break
                if stored and heartbeat.exists() and b"stream-before-interrupt" in Path(stored["stdout_path"]).read_bytes():
                    break
                time.sleep(.02)
            self.assertIsNotNone(stored)
            self.assertTrue(heartbeat.exists(), json.dumps(stored, indent=1))
            os.kill(int(supervisor_pid.read_text()), signal.SIGTERM)
            process.communicate(timeout=5)
            self.assertNotEqual(0, process.returncode)
            time.sleep(.2)
            before = heartbeat.read_bytes()
            time.sleep(.3)
            self.assertEqual(before, heartbeat.read_bytes())
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual("running", stored["outcome"])
            self.assertIsNone(stored["ended_at"])
            self.assertIn(b"stream-before-interrupt", Path(stored["stdout_path"]).read_bytes())
            success = True
        finally:
            if not success:
                for path in (child_pid, supervisor_pid):
                    if path.exists():
                        try:
                            os.kill(int(path.read_text()), signal.SIGTERM)
                        except OSError:  # the fixture process may already have exited
                            pass
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=5)

    def test_old_verification_reading_remains_readable(self):
        line = tickets_done.verification_line({"form": "command", "command": "old",
                                              "exit": 0, "tree": "old-tree"})
        self.assertIn("old-tree", line)


class RequiredEvidenceTest(RunRequiredCase):
    def test_replay_keeps_recoverable_receipt_without_new_execution(self):
        first = self.invoke()[1]
        self.stub.forget()
        replay = self.invoke()[1]
        self.assertEqual([], self.stub.calls())
        self.assertEqual(first["commands"][0]["evidence"], replay["commands"][0]["evidence"])
        receipt = json.loads(Path(replay["commands"][0]["evidence"]["path"]).read_text())
        self.assertIn(b"stub-out", Path(receipt["stdout_path"]).read_bytes())
        self.assertIn("uncached", replay["cache_scope"])

    def test_selected_environment_change_invalidates_replay(self):
        with mock.patch.dict(os.environ, {"PYTHON_CPU_COUNT": "1"}):
            self.invoke()
        self.stub.forget()
        with mock.patch.dict(os.environ, {"PYTHON_CPU_COUNT": "24"}):
            payload = self.invoke()[1]
        self.assertEqual(4, len(self.stub.calls()))
        self.assertFalse(any(row["cached"] for row in payload["commands"]))
        from tools import run_required
        for name in ("PYTHON_CPU_COUNT", "PYTHONPATH", "PYTHONHOME", "PATH",
                     "ORCHFLOWS_TEST_PARALLELISM"):
            with self.subTest(name=name):
                with mock.patch.dict(os.environ, {name: "one"}):
                    first = run_required.key_for("tree", "working", [], str(self.stub.path), "version")
                with mock.patch.dict(os.environ, {name: "two"}):
                    second = run_required.key_for("tree", "working", [], str(self.stub.path), "version")
                self.assertNotEqual(first, second)

    def test_interpreter_bytes_change_invalidates_replay(self):
        self.invoke()
        self.stub.forget()
        with self.stub.path.open("a", encoding="utf-8") as stream:
            stream.write("\n")
        payload = self.invoke()[1]
        self.assertEqual(4, len(self.stub.calls()))
        self.assertFalse(any(row["cached"] for row in payload["commands"]))
