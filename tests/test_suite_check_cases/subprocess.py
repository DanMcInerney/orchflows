"""End-to-end subprocess seam cases for the suite harness."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from scripts import state_root

from tests._repo_root import ROOT as REPO_ROOT


class TestHarnessSubprocess(unittest.TestCase):
    """The one permitted subprocess test: a tiny synthetic tests/ dir."""

    def _write_tests_dir(self, root: Path, passing: bool) -> None:
        tests_dir = root / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "__init__.py").write_text("", encoding="utf-8")
        if passing:
            body = textwrap.dedent(
                """
                import unittest

                class TestTiny(unittest.TestCase):
                    def test_ok(self):
                        self.assertTrue(True)
                """
            )
        else:
            body = textwrap.dedent(
                """
                import unittest

                class TestTiny(unittest.TestCase):
                    def test_fails(self):
                        self.assertTrue(False)
                """
            )
        (tests_dir / "test_tiny.py").write_text(body, encoding="utf-8")

    def test_harness_end_to_end_against_synthetic_suite(self):
        harness = REPO_ROOT / "tools" / "suite_check.py"
        with tempfile.TemporaryDirectory() as td_pass, tempfile.TemporaryDirectory() as td_fail:
            pass_root = Path(td_pass)
            self._write_tests_dir(pass_root, passing=True)
            result = subprocess.run(
                [
                    sys.executable,
                    str(harness),
                    "--repo-root",
                    str(pass_root),
                    "--python",
                    sys.executable,
                    "--no-home-watch",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            verdict = json.loads(result.stdout.strip().splitlines()[-1])
            self.assertTrue(verdict["ok"])
            self.assertIn("phases", verdict)
            self.assertIn("suite", verdict["phases"])
            self.assertIn("snapshot", verdict["phases"])
            self.assertIn("stripped_path", verdict["phases"])

            fail_root = Path(td_fail)
            self._write_tests_dir(fail_root, passing=False)
            result = subprocess.run(
                [
                    sys.executable,
                    str(harness),
                    "--repo-root",
                    str(fail_root),
                    "--python",
                    sys.executable,
                    "--no-home-watch",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            verdict = json.loads(result.stdout.strip().splitlines()[-1])
            self.assertFalse(verdict["ok"])
            self.assertIn("failures", verdict)
            self.assertTrue(verdict["failures"])

    def test_a_stray_write_into_the_sink_fails_the_run(self):
        """A redirected sink is guarded for in-process and child writes."""

        harness = REPO_ROOT / "tools" / "suite_check.py"
        for who, body in (
            (
                "in_process",
                (
                    """
                import os, pathlib, unittest

                class TestStray(unittest.TestCase):
                    def test_writes_into_the_sink(self):
                        sink = pathlib.Path(os.environ[{0!r}])
                        (sink / "runs" / "leaked").mkdir(parents=True, exist_ok=True)
                        (sink / "runs" / "leaked" / "worklog.md").write_text("x\\n")
                """
                ).format(state_root.ENV_VAR),
            ),
            (
                "subprocess",
                (
                    """
                import os, subprocess, sys, unittest

                class TestStray(unittest.TestCase):
                    def test_a_child_writes_into_the_inherited_sink(self):
                        program = (
                            "import os, pathlib;"
                            "s = pathlib.Path(os.environ[{0!r}]);"
                            "d = s / 'friction';"
                            "d.mkdir(parents=True, exist_ok=True);"
                            "(d / '2026-08.jsonl').write_text('{{}}\\\\n')"
                        )
                        done = subprocess.run([sys.executable, "-c", program])
                        self.assertEqual(0, done.returncode)
                """
                ).format(state_root.ENV_VAR),
            ),
        ):
            with self.subTest(who=who), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                tests_dir = root / "tests"
                tests_dir.mkdir(parents=True)
                (tests_dir / "__init__.py").write_text("", encoding="utf-8")
                (tests_dir / "test_stray.py").write_text(
                    textwrap.dedent(body), encoding="utf-8"
                )
                sink = root / "stand-in-sink"
                sink.mkdir()
                env = dict(os.environ, **{state_root.ENV_VAR: str(sink)})
                result = subprocess.run(
                    [
                        sys.executable,
                        str(harness),
                        "--repo-root",
                        str(root),
                        "--python",
                        sys.executable,
                        "--no-home-watch",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=env,
                )
                verdict = json.loads(result.stdout.strip().splitlines()[-1])
                self.assertTrue(verdict["phases"]["suite"]["ok"], result.stdout)
                self.assertFalse(verdict["phases"]["snapshot"]["ok"], result.stdout)
                self.assertFalse(verdict["ok"])
                self.assertEqual(1, result.returncode)
                self.assertTrue(
                    [f for f in verdict["failures"] if f.startswith("state_sink: added ")],
                    verdict["failures"],
                )
