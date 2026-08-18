from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RUNNER = ROOT / "tools" / "run_super_research_tests.py"


class SuperResearchRunnerTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.repo = Path(self.scratch.name)
        tools_dir = self.repo / "tools"
        self.tests_dir = (
            self.repo / ".orchflows" / "skills" / "super-research" / "tests"
        )
        tools_dir.mkdir()
        self.tests_dir.mkdir(parents=True)
        (self.tests_dir / "__init__.py").write_text("", encoding="utf-8")
        shutil.copyfile(RUNNER, tools_dir / RUNNER.name)
        self.runner = tools_dir / RUNNER.name

    def tearDown(self):
        self.scratch.cleanup()

    def write_test(self, name: str, source: str) -> None:
        (self.tests_dir / (name + ".py")).write_text(
            textwrap.dedent(source), encoding="utf-8"
        )

    def run_runner(self, *selectors: str, env=None):
        return subprocess.run(
            [sys.executable, str(self.runner), *selectors],
            cwd=str(self.repo),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

    def test_discovers_tests_from_project_scope_directory(self):
        self.write_test(
            "test_first",
            """
            import unittest

            class FirstTests(unittest.TestCase):
                def test_first(self):
                    self.assertTrue(True)
            """,
        )
        self.write_test(
            "test_second",
            """
            import unittest

            class SecondTests(unittest.TestCase):
                def test_second(self):
                    self.assertTrue(True)
            """,
        )

        completed = self.run_runner()

        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("Ran 2 tests", completed.stdout)

    def test_accepts_module_and_class_selectors(self):
        self.write_test(
            "test_sample",
            """
            import unittest

            class FirstTests(unittest.TestCase):
                def test_first(self):
                    self.assertTrue(True)

            class SecondTests(unittest.TestCase):
                def test_second(self):
                    self.assertTrue(True)
            """,
        )

        module = self.run_runner("test_sample")
        selected_class = self.run_runner("test_sample.FirstTests")

        self.assertEqual(module.returncode, 0, module.stdout)
        self.assertIn("Ran 2 tests", module.stdout)
        self.assertEqual(selected_class.returncode, 0, selected_class.stdout)
        self.assertIn("Ran 1 test", selected_class.stdout)

    def test_propagates_unsuccessful_exit_status(self):
        self.write_test(
            "test_failure",
            """
            import unittest

            class FailureTests(unittest.TestCase):
                def test_failure(self):
                    self.fail("sentinel failure")
            """,
        )

        completed = self.run_runner("test_failure.FailureTests")

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("sentinel failure", completed.stdout)

    def test_runner_itself_does_not_access_network(self):
        self.write_test(
            "test_offline",
            """
            import unittest

            class OfflineTests(unittest.TestCase):
                def test_offline(self):
                    self.assertTrue(True)
            """,
        )
        hook_dir = self.repo / "network_guard"
        hook_dir.mkdir()
        (hook_dir / "sitecustomize.py").write_text(
            textwrap.dedent(
                """
                import socket
                import urllib.request

                def denied(*args, **kwargs):
                    raise AssertionError("network access attempted by runner")

                socket.create_connection = denied
                urllib.request.urlopen = denied
                """
            ),
            encoding="utf-8",
        )
        env = dict(os.environ)
        env["PYTHONPATH"] = str(hook_dir)

        completed = self.run_runner("test_offline", env=env)

        self.assertEqual(completed.returncode, 0, completed.stdout)
        self.assertIn("Ran 1 test", completed.stdout)


if __name__ == "__main__":
    unittest.main()
