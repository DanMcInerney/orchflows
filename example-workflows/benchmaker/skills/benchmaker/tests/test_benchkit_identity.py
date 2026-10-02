"""retain / compare / observe: byte identity of what a run used, and recorded tool versions."""
from __future__ import annotations

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from benchkit import identity  # noqa: E402


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(identity.discard, self.tmp)
        self.src, self.kept = self.tmp / "src", self.tmp / "kept"
        (self.src / "tasks" / "t01").mkdir(parents=True)
        (self.src / "tasks" / "t01" / "instruction.md").write_text("add the numbers\n")
        (self.src / "tasks" / "t02").mkdir()
        (self.src / "tasks" / "t02" / "instruction.md").write_text("multiply them\n")
        (self.src / "suite.json").write_text('{"name": "mini"}\n')
        self.sources = {"tasks": self.src / "tasks", "suite.json": self.src / "suite.json"}

    def retained(self):
        identity.retain(self.sources, self.kept)
        return identity.compare(self.sources, self.kept)

    def test_unchanged_sources_report_nothing(self):
        self.assertEqual(self.retained(), [])
        self.assertEqual((self.kept / "tasks" / "t01" / "instruction.md").read_text(), "add the numbers\n")
        self.assertEqual((self.kept / "suite.json").read_text(), '{"name": "mini"}\n')

    def test_retained_files_are_read_only_copies(self):
        self.retained()
        for kept, source in ((self.kept / "suite.json", self.src / "suite.json"),
                             (self.kept / "tasks" / "t02" / "instruction.md", self.src / "tasks" / "t02" / "instruction.md")):
            self.assertFalse(kept.stat().st_mode & stat.S_IWRITE)
            self.assertFalse(kept.is_symlink())
            self.assertFalse(os.path.samefile(kept, source))
        (self.src / "suite.json").write_text("changed\n")
        self.assertEqual((self.kept / "suite.json").read_text(), '{"name": "mini"}\n')

    def test_a_changed_byte_is_reported(self):
        self.retained()
        (self.src / "tasks" / "t01" / "instruction.md").write_text("add the numbfrs\n")
        self.assertEqual(identity.compare(self.sources, self.kept), ["changed: tasks/t01/instruction.md"])

    def test_a_changed_file_of_equal_size_and_time_is_still_caught(self):
        self.retained()
        path = self.src / "suite.json"
        before = path.stat()
        path.write_text('{"name": "mind"}\n')
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        self.assertEqual(identity.compare(self.sources, self.kept), ["changed: suite.json"])

    def test_a_missing_file_is_reported(self):
        self.retained()
        (self.src / "tasks" / "t02" / "instruction.md").unlink()
        self.assertEqual(identity.compare(self.sources, self.kept), ["missing: tasks/t02/instruction.md"])

    def test_an_extra_file_is_reported(self):
        self.retained()
        (self.src / "tasks" / "t03").mkdir()
        (self.src / "tasks" / "t03" / "instruction.md").write_text("new\n")
        self.assertEqual(identity.compare(self.sources, self.kept), ["extra: tasks/t03/instruction.md"])

    def test_all_three_at_once_in_a_stable_order(self):
        self.retained()
        (self.src / "tasks" / "t01" / "instruction.md").write_text("x\n")
        (self.src / "tasks" / "t02" / "instruction.md").unlink()
        (self.src / "extra.txt").write_text("e\n")
        self.sources["extra.txt"] = self.src / "extra.txt"
        self.assertEqual(identity.compare(self.sources, self.kept),
                         ["missing: tasks/t02/instruction.md", "extra: extra.txt", "changed: tasks/t01/instruction.md"])

    def test_run_output_caches_and_git_are_neither_retained_nor_compared(self):
        for name in ("runs", "__pycache__", ".git"):
            (self.src / "tasks" / name).mkdir()
            (self.src / "tasks" / name / "x.pyc").write_text("noise")
        self.assertEqual(self.retained(), [])
        for name in ("runs", "__pycache__", ".git"):
            self.assertFalse((self.kept / "tasks" / name).exists())
        (self.src / "tasks" / "__pycache__" / "y.pyc").write_text("more noise")
        self.assertEqual(identity.compare(self.sources, self.kept), [])

    def test_a_link_in_the_sources_is_refused(self):
        target = self.src / "suite.json"
        try:
            (self.src / "tasks" / "link.json").symlink_to(target)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links are not available")
        with self.assertRaises(identity.IdentityError):
            identity.retain(self.sources, self.kept)

    def test_retaining_twice_into_the_same_place_is_refused(self):
        self.retained()
        with self.assertRaises(FileExistsError):
            identity.retain(self.sources, self.kept)

    def test_a_missing_source_is_refused(self):
        with self.assertRaises(FileNotFoundError):
            identity.retain({"nothing": self.src / "nothing"}, self.kept)

    def test_observe_records_output_verbatim(self):
        seen = identity.observe([[sys.executable, "-c", "print('hello  world')"],
                                 [sys.executable, "-c", "import sys; sys.stderr.write('to stderr')"]], self.tmp)
        self.assertEqual(list(seen.values()), ["hello  world", "to stderr"])
        self.assertEqual(list(seen)[0], f"{sys.executable} -c print('hello  world')")

    def test_observe_records_failures_and_caps(self):
        seen = identity.observe([["no-such-program-benchkit", "--version"],
                                 [sys.executable, "-c", "import sys; print('partial'); sys.exit(4)"]], self.tmp)
        failed, exited = seen.values()
        self.assertIn("launch failed", failed)
        self.assertEqual(exited, "partial\n[error: exit code 4]")

    def test_observe_stops_a_command_at_its_cap(self):
        original = identity.OBSERVE_SECONDS
        identity.OBSERVE_SECONDS = 0.5
        self.addCleanup(setattr, identity, "OBSERVE_SECONDS", original)
        seen = identity.observe([[sys.executable, "-c", "import time; print('start', flush=True); time.sleep(60)"]], self.tmp)
        self.assertEqual(list(seen.values()), ["start\n[timeout: exceeded the 0.5 s cap]"])


if __name__ == "__main__":
    unittest.main()
