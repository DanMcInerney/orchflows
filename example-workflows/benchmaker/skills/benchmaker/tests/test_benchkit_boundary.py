"""What a solver can reach, and what happens to a workspace the kit cannot fully capture."""
from __future__ import annotations

import errno
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "scripts"
for folder in (SCRIPTS, TESTS):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from benchkit import shapes, stage  # noqa: E402
from test_benchkit_runs import Case, agent  # noqa: E402


class SolverBoundaryTests(Case):
    def test_no_path_a_solver_is_handed_leads_to_evaluator_material(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, outside, ignore_errors=True)
        for name in ("solution/solve.py", "tests/verify.py", "tests/expected.json"):
            path = self.package / "tasks" / "t01" / name
            path.write_text(path.read_text(encoding="utf-8") + "\n# EVALUATOR-MARKER\n", encoding="utf-8")
        self.setenv(BENCHKIT_WALK_STOP=outside)
        with mock.patch.object(tempfile, "tempdir", str(outside)):
            code, _, err = self.run_cli("full", "--agent", agent("walker"), "--output", self.out, "--tasks", "t01",
                                        "--repeats", 2, "--jobs", 1)
        self.assertEqual(code, 0, err)
        real = os.path.realpath
        for repeat in (1, 2):
            walk = json.loads((self.out / "attempts" / "t01" / f"{repeat}-0" / "workspace" / "walk.json").read_text(encoding="utf-8"))
            self.assertEqual(walk["hits"], [])
            self.assertGreaterEqual(len(walk["given"]), 4)
            for path in walk["given"]:
                self.assertEqual(os.path.commonpath([real(path), walk["stop"]]), walk["stop"], path)
                for protected in (self.out, self.package):
                    self.assertNotEqual(os.path.commonpath([real(path), real(protected)]), real(protected), path)
            self.assertIn(walk["stop"], walk["visited"])

    def test_the_attempt_record_still_holds_the_prompt_transcript_and_output_files(self):
        self.assertEqual(self.one("good")[0], 0)
        folder = self.out / "attempts" / "t01" / "1-0"
        self.assertEqual((folder / "prompt.md").read_bytes(), (self.package / "tasks" / "t01" / "instruction.md").read_bytes())
        self.assertIn("wrote output.json", (folder / "transcript.jsonl").read_text(encoding="utf-8"))
        self.assertTrue((folder / "stdout.txt").read_text(encoding="utf-8").strip().endswith("}"))
        self.assertTrue((folder / "stderr.txt").is_file())
        (row,) = self.rows()
        self.assertEqual(row["transcript"], "attempts/t01/1-0/transcript.jsonl")

    def test_a_transcript_that_is_a_link_is_not_kept(self):
        solver = self.tmp / "linker"
        solver.mkdir()
        (solver / "run_agent.py").write_text(
            "import argparse, os\n"
            "p = argparse.ArgumentParser()\n"
            "for n in ('workspace', 'prompt-file', 'transcript', 'timeout'): p.add_argument('--' + n)\n"
            "a = p.parse_args()\n"
            "os.symlink(os.path.abspath(a.prompt_file), a.transcript)\n"
            "print('{\"status\": \"completed\", \"exit_code\": 0}')\n", encoding="utf-8")
        try:
            (self.tmp / "probe").symlink_to(solver, target_is_directory=True)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links are not available")
        self.assertEqual(self.one(str(solver))[0], 0)
        (row,) = self.rows()
        self.assertIsNone(row["transcript"])
        self.assertFalse((self.out / "attempts" / "t01" / "1-0" / "transcript.jsonl").exists())


class CaptureFailureTests(Case):
    """A workspace the kit cannot fully capture is graded as captured; only a fault of the host is an infrastructure error."""

    def failing_copy(self, name, error):
        real = shutil.copy2

        def copy(source, target, *args, **kwargs):
            if os.path.basename(str(source)) == name and "environment" not in Path(source).parts:
                raise error
            return real(source, target, *args, **kwargs)
        return mock.patch.object(stage.shutil, "copy2", copy)

    def run_t01(self):
        return self.run_cli("full", "--agent", agent("good"), "--output", self.out, "--tasks", "t01", "--repeats", 1)

    def test_an_uncopyable_extra_file_is_recorded_and_the_work_is_still_scored(self):
        (self.package / "tasks" / "t01" / "environment" / "held.lock").write_text("held\n", encoding="utf-8")
        with self.failing_copy("held.lock", PermissionError(errno.EACCES, "Permission denied")):
            code, _, err = self.run_t01()
        self.assertEqual(code, 0, err)
        (row,) = self.rows()
        self.assertEqual((row["status"], row["grading_status"], row["full_success"]), ("completed", "scored", True))
        self.assertEqual(len(row["capture_skipped"]), 1)
        self.assertTrue(row["capture_skipped"][0].startswith("held.lock: "))
        solver = json.loads((self.out / "attempts" / "t01" / "1-0" / "solver.json").read_text(encoding="utf-8"))
        self.assertEqual(solver["capture_skipped"], row["capture_skipped"])
        self.assertEqual(shapes.run_problems(self.out), [])

    def test_a_missing_deliverable_is_a_scored_failure_not_an_exclusion(self):
        with self.failing_copy("output.json", PermissionError(errno.EACCES, "Permission denied")):
            code, _, err = self.run_t01()
        self.assertEqual(code, 0, err)
        (row,) = self.rows()
        self.assertEqual((row["status"], row["grading_status"], row["full_success"], row["credit"]), ("completed", "scored", False, 0.0))
        self.assertTrue(row["capture_skipped"][0].startswith("output.json: "))
        summary = self.summary()
        self.assertEqual((summary["counts"]["scored"], summary["counts"]["failed"], summary["overall"]["full_success_rate"]), (1, 1, 0.0))
        self.assertEqual(summary["exclusions"], [])

    def test_a_fault_of_the_host_is_still_an_infrastructure_error(self):
        with self.failing_copy("output.json", OSError(errno.ENOSPC, "No space left on device")):
            code, _, err = self.run_t01()
        self.assertEqual(code, 0, err)
        (row,) = self.rows()
        self.assertEqual((row["status"], row["grading_status"]), ("infrastructure-error", "unscored"))
        self.assertIn("No space left", row["reason"])


if __name__ == "__main__":
    unittest.main()
