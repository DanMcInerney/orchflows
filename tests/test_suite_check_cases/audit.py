"""Skip-audit and stripped-PATH cases for the suite harness."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import suite_check


class TestAuditSkips(unittest.TestCase):
    def test_skip_with_reason_is_clean(self):
        output = "test_x (tests.test_y.TestY) ... skipped 'windows only'\nOK\n"
        self.assertEqual(suite_check.audit_skips(output), [])

    def test_skip_without_reason_is_named(self):
        output = "test_x (tests.test_y.TestY) ... skipped ''\nOK\n"
        violations = suite_check.audit_skips(output)
        self.assertEqual(violations, ["test_x (tests.test_y.TestY)"])

    def test_skip_with_whitespace_only_reason_is_named(self):
        output = "test_x (tests.test_y.TestY) ... skipped '   '\n"
        violations = suite_check.audit_skips(output)
        self.assertEqual(violations, ["test_x (tests.test_y.TestY)"])

    def test_expected_failure_is_not_a_skip(self):
        output = "test_x (tests.test_y.TestY) ... expected failure\nOK\n"
        self.assertEqual(suite_check.audit_skips(output), [])

    def test_multiple_skips_all_named(self):
        output = (
            "test_a (m.A) ... skipped 'ok reason'\n"
            "test_b (m.B) ... skipped ''\n"
            "test_c (m.C) ... ok\n"
            'test_d (m.D) ... skipped ""\n'
        )
        violations = suite_check.audit_skips(output)
        self.assertEqual(violations, ["test_b (m.B)", "test_d (m.D)"])

    def test_no_skips_returns_empty(self):
        output = "test_a (m.A) ... ok\ntest_b (m.B) ... ok\n\nOK\n"
        self.assertEqual(suite_check.audit_skips(output), [])


class TestBuildStrippedPath(unittest.TestCase):
    def test_contains_executable_directory(self):
        with tempfile.TemporaryDirectory() as td:
            exe_dir = Path(td) / "cpython-3.12"
            exe_dir.mkdir()
            exe = exe_dir / "python.exe"
            exe.write_text("", encoding="utf-8")
            path = suite_check.build_stripped_path(str(exe))
            entries = path.split(suite_check.os.pathsep)
            self.assertIn(str(exe_dir.resolve()), entries)

    def test_includes_scripts_sibling_when_present(self):
        with tempfile.TemporaryDirectory() as td:
            exe_dir = Path(td) / "cpython-3.12"
            (exe_dir / "Scripts").mkdir(parents=True)
            exe = exe_dir / "python.exe"
            exe.write_text("", encoding="utf-8")
            path = suite_check.build_stripped_path(str(exe))
            entries = path.split(suite_check.os.pathsep)
            self.assertIn(str((exe_dir / "Scripts").resolve()), entries)

    def test_omits_scripts_sibling_when_absent(self):
        with tempfile.TemporaryDirectory() as td:
            exe_dir = Path(td) / "venv-bin"
            exe_dir.mkdir()
            exe = exe_dir / "python3"
            exe.write_text("", encoding="utf-8")
            path = suite_check.build_stripped_path(str(exe))
            entries = path.split(suite_check.os.pathsep)
            self.assertEqual(entries, [str(exe_dir.resolve())])
