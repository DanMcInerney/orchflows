"""Behavioral contract for the tracked executable-source size checker."""

from __future__ import annotations

import contextlib
import io
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import check_source_sizes as sizes


class SourceSizeCheckerTest(unittest.TestCase):
    def test_all_six_executable_suffixes_are_owned(self):
        self.assertEqual(
            sizes.SOURCE_SUFFIXES,
            frozenset({".py", ".sh", ".cmd", ".ps1", ".js", ".ts"}),
        )

    def test_git_reader_is_nul_safe_and_keeps_hidden_paths(self):
        root = Path("tracked-root").resolve()
        payload = b".hidden/check.py\0scripts/a file.sh\0odd\nname.ts\0notes.md\0"
        completed = subprocess.CompletedProcess([], 0, stdout=payload, stderr=b"")
        with mock.patch.object(sizes.subprocess, "run", return_value=completed) as run:
            found = sizes.tracked_source_files(root)
        self.assertEqual(
            [path.relative_to(root).as_posix() for path in found],
            [".hidden/check.py", "scripts/a file.sh", "odd\nname.ts"],
        )
        command = run.call_args.args[0]
        self.assertEqual(command[:3], ["git", "ls-files", "-z"])
        self.assertIn("--", command)

    def test_explicit_directory_covers_six_suffixes_and_hidden_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hidden = root / ".hidden"
            hidden.mkdir()
            expected = []
            for suffix in sorted(sizes.SOURCE_SUFFIXES):
                path = hidden / ("sample" + suffix)
                path.write_text("one\n", encoding="utf-8")
                expected.append(path)
            (hidden / "sample.md").write_text("ignored\n", encoding="utf-8")
            self.assertEqual(sizes.source_files_from_paths([root]), expected)

    def test_510_lines_pass_and_511_lines_fail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            accepted = root / "accepted.py"
            rejected = root / "rejected.py"
            deleted = root / "deleted.py"
            accepted.write_bytes(b"line\n" * 510)
            rejected.write_bytes(b"line\n" * 511)

            self.assertEqual(sizes.physical_line_count(accepted), 510)
            self.assertEqual(sizes.oversized_files([deleted, accepted]), [])
            self.assertEqual(sizes.oversized_files([rejected]), [(rejected, 511)])

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(sizes.main([str(accepted)]), 0)
                self.assertEqual(sizes.main([str(rejected)]), 1)
            self.assertIn("rejected.py: 511 physical lines", stdout.getvalue())

    def test_an_oversized_test_warns_without_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            test_file = root / "tests" / "test_large.py"
            test_file.parent.mkdir()
            test_file.write_bytes(b"line\n" * 501)
            stdout = io.StringIO()
            with mock.patch.object(sizes, "ROOT", root), contextlib.redirect_stdout(stdout):
                self.assertEqual(sizes.main([str(test_file)]), 0)
            self.assertIn("WARN tests", stdout.getvalue())
            self.assertIn("source-size policy: PASS", stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
