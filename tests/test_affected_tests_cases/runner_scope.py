"""``tools/run_tests.py --scope`` selects its shards through the resolver."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest

from tests.test_affected_tests_cases.common import ROOT, build_tree

RUN_TESTS_PY = ROOT / "tools" / "run_tests.py"


class RunnerScopeCase(unittest.TestCase):
    """Drive the real runner over the fixture repository, one worker."""

    def setUp(self):
        self._scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self._scratch.cleanup)
        self.root = build_tree(self._scratch.name)

    def run_runner(self, scope):
        return subprocess.run(
            [
                sys.executable,
                str(RUN_TESTS_PY),
                "--tests-dir",
                str(self.root / "tests"),
                "--no-cache",
                "-j",
                "1",
                "--scope",
                scope,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )


class TestScopeSelection(RunnerScopeCase):
    def test_a_scope_runs_exactly_the_shards_it_reaches(self):
        completed = self.run_runner("scripts/mod_alpha.py")
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("running 2 modules", completed.stdout)
        self.assertIn("tests.test_import_edge", completed.stdout)
        self.assertIn("tests.test_from_edge", completed.stdout)
        self.assertNotIn("tests.test_dir_edge", completed.stdout)
        self.assertNotIn("tests.test_broken", completed.stdout)

    def test_a_comma_separated_scope_runs_the_union(self):
        completed = self.run_runner("scripts/mod_alpha.py,scripts/mod_beta.py")
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertIn("running 3 modules", completed.stdout)
        self.assertIn("tests.test_spec_edge", completed.stdout)

    def test_a_scope_no_shard_reaches_runs_nothing_and_exits_zero(self):
        completed = self.run_runner("scripts/mod_orphan.py")
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
        self.assertNotIn("running", completed.stdout)
        self.assertIn("scripts/mod_orphan.py", completed.stdout + completed.stderr)


class TestScopeIsDocumented(unittest.TestCase):
    def test_the_runner_usage_names_the_scope_option(self):
        source = RUN_TESTS_PY.read_text(encoding="utf-8")
        self.assertIn("--scope", source.split('"""')[1])

    def test_the_runner_help_names_the_scope_option(self):
        completed = subprocess.run(
            [sys.executable, str(RUN_TESTS_PY), "--help"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        self.assertIn("--scope", completed.stdout)


if __name__ == "__main__":
    unittest.main()
