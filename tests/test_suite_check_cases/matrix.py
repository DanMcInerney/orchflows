"""CI-matrix parsing, coverage, and interpreter lookup cases."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import preflight


class TestPreflightMatrix(unittest.TestCase):
    """A matrix that cannot be read is a refusal, never a covered run."""

    def _workflow(self, text=None):
        """A temporary workflow file, or a path where none exists."""

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "checks.yml"
        if text is not None:
            path.write_text(text, encoding="utf-8")
        return mock.patch.object(preflight, "WORKFLOW", path)

    def test_the_repositorys_own_matrix_is_read_rather_than_restated(self):
        self.assertTrue(preflight.ci_minors())
        self.assertTrue(preflight.ci_os_cells())

    def test_a_workflow_that_cannot_be_read_refuses(self):
        with self._workflow():
            with self.assertRaises(preflight.MatrixUnreadable):
                preflight.ci_minors()

    def test_a_reshaped_matrix_refuses_the_same_way(self):
        with self._workflow("jobs:\n  checks:\n    runs-on: ubuntu-latest\n"):
            for read in (preflight.ci_minors, preflight.ci_os_cells):
                with self.subTest(read=read.__name__):
                    with self.assertRaises(preflight.MatrixUnreadable):
                        read()

    def test_an_empty_axis_is_no_axis(self):
        with self._workflow("        os: []\n        python-version: []\n"):
            for read in (preflight.ci_minors, preflight.ci_os_cells):
                with self.subTest(read=read.__name__):
                    with self.assertRaises(preflight.MatrixUnreadable):
                        read()

    def test_main_refuses_before_running_anything(self):
        with self._workflow():
            with mock.patch.object(preflight, "run_one") as ran:
                with self.assertRaises(SystemExit) as raised:
                    preflight.main([])
        self.assertEqual(ran.call_count, 0)
        self.assertIn("preflight", str(raised.exception.code))
        self.assertNotIn("OK", str(raised.exception.code))


class TestPreflightOsLine(unittest.TestCase):
    """The OS line names this host's cell, and it is read from the matrix."""

    CELLS = ("ubuntu-latest", "macos-latest", "windows-latest")

    def _line(self, platform):
        with mock.patch.object(preflight.sys, "platform", platform):
            return preflight.os_coverage_line(self.CELLS)

    def test_each_platform_covers_its_own_cell_and_no_other(self):
        for platform, cell in (
            ("win32", "windows-latest"),
            ("linux", "ubuntu-latest"),
            ("darwin", "macos-latest"),
        ):
            with self.subTest(platform=platform):
                line = self._line(platform)
                covered, _, uncovered = line.partition("--")
                self.assertIn("1 of 3", covered)
                self.assertIn(cell, covered)
                self.assertNotIn(cell, uncovered)
                for other in self.CELLS:
                    if other != cell:
                        self.assertIn(other, uncovered)

    def test_a_platform_the_matrix_does_not_run_covers_no_cell(self):
        line = self._line("freebsd14")
        self.assertIn("0 of 3", line)
        self.assertIn("freebsd14", line)


class TestPreflightWhich(unittest.TestCase):
    """``python3.13`` on Windows is ``python3.13.exe``."""

    def _path(self, directory):
        return mock.patch.dict(
            os.environ, {"PATH": str(directory), "PATHEXT": ".COM;.EXE;.BAT"}
        )

    def test_an_extension_the_host_appends_is_found(self):
        if os.name != "nt":
            self.skipTest("PATHEXT is Windows-only; the bare name is found below")
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            (directory / "python3.13.exe").write_text("", encoding="utf-8")
            with self._path(directory):
                found = preflight._which("python3.13")
            self.assertTrue(found and Path(found).is_file(), found)
            self.assertEqual(Path(found).name.lower(), "python3.13.exe")

    def test_a_bare_name_is_still_found_wherever_it_is_the_whole_name(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            executable = directory / "python3.13"
            executable.write_text("", encoding="utf-8")
            executable.chmod(0o755)
            with self._path(directory):
                self.assertEqual(preflight._which("python3.13"), str(executable))

    def test_a_name_on_no_path_entry_is_still_absent(self):
        with tempfile.TemporaryDirectory() as td:
            with self._path(Path(td)):
                self.assertIsNone(preflight._which("python3.13"))
