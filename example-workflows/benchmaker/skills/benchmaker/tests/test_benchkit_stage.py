"""stage_public and capture: solvers see environment/ and the prompt, nothing else."""
from __future__ import annotations

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from benchkit import stage  # noqa: E402
from benchkit.stage import StagingError, capture, stage_public  # noqa: E402


def link(path: Path, target: Path):
    try:
        path.symlink_to(target)
    except (OSError, NotImplementedError):
        raise unittest.SkipTest("symbolic links are not available")


class StageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.package = self.tmp / "package"
        self.task = self.package / "tasks" / "t01"
        (self.task / "environment" / "data").mkdir(parents=True)
        (self.task / "environment" / "input.json").write_text('{"numbers": [1, 2, 3]}\n')
        (self.task / "environment" / "data" / "notes.txt").write_text("public notes\n")
        (self.task / "instruction.md").write_text("Sum the numbers in input.json into output.json.\n")
        (self.task / "solution").mkdir()
        (self.task / "solution" / "solve.py").write_text("print('the answer')\n")
        (self.task / "tests").mkdir()
        (self.task / "tests" / "expected.json").write_text('{"sum": 6}\n')
        (self.task / "tests" / "verify.py").write_text("print('verify')\n")
        self.work = self.tmp / "work"
        self.workspace, self.prompt = self.work / "workspace", self.work / "prompt.md"

    def stage(self):
        stage_public(self.task, self.workspace, self.prompt)

    def refused(self, fragment):
        with self.assertRaises(StagingError) as raised:
            self.stage()
        self.assertIn(fragment.lower(), str(raised.exception).lower())
        self.assertFalse(self.workspace.exists())
        self.assertFalse(self.prompt.exists())

    def test_the_workspace_holds_environment_contents_and_the_prompt_stays_outside(self):
        self.stage()
        self.assertEqual(sorted(path.relative_to(self.workspace).as_posix() for path in self.workspace.rglob("*")),
                         ["data", "data/notes.txt", "input.json"])
        self.assertEqual((self.workspace / "input.json").read_text(), '{"numbers": [1, 2, 3]}\n')
        self.assertEqual(self.prompt.read_bytes(), (self.task / "instruction.md").read_bytes())

    def test_a_task_without_an_environment_stages_an_empty_workspace(self):
        shutil.rmtree(self.task / "environment")
        self.stage()
        self.assertEqual(list(self.workspace.iterdir()), [])

    def test_an_evaluator_name_in_the_environment_is_refused(self):
        (self.task / "environment" / "solution").mkdir()
        (self.task / "environment" / "solution" / "x").write_text("different bytes\n")
        self.refused("evaluator name 'solution'")

    def test_every_evaluator_name_is_refused_in_any_case_and_for_files_too(self):
        self.assertEqual(stage.EVALUATOR_NAMES, {"solution", "tests", "labeled", "admission", "evaluation", "identity"})
        for name in sorted(stage.EVALUATOR_NAMES):
            with self.subTest(name=name):
                folder = self.task / "environment" / name.upper()
                folder.mkdir()
                (folder / "f.txt").write_text(f"unique {name}\n")
                self.refused(name)
                shutil.rmtree(folder)
                (self.task / "environment" / name).write_text("a file named like an evaluator folder\n")
                self.refused(name)
                (self.task / "environment" / name).unlink()

    def test_a_byte_copy_of_a_test_file_is_refused_under_any_name(self):
        shutil.copyfile(self.task / "tests" / "expected.json", self.task / "environment" / "data" / "extra.json")
        self.refused("byte-identical to tests/expected.json")

    def test_a_byte_copy_of_a_solution_file_is_refused(self):
        shutil.copyfile(self.task / "solution" / "solve.py", self.task / "environment" / "helper.py")
        self.refused("byte-identical to solution/solve.py")

    def test_empty_files_and_files_that_merely_resemble_evaluator_files_pass(self):
        (self.task / "environment" / "__init__.py").write_bytes(b"")
        (self.task / "tests" / "__init__.py").write_bytes(b"")
        (self.task / "environment" / "near.json").write_text('{"sum": 7}\n')
        self.stage()
        self.assertTrue((self.workspace / "near.json").exists())

    def test_a_link_in_the_environment_is_refused(self):
        link(self.task / "environment" / "answers.json", self.task / "tests" / "expected.json")
        self.refused("link in environment")

    def test_a_linked_environment_is_refused(self):
        shutil.move(self.task / "environment", self.tmp / "elsewhere")
        link(self.task / "environment", self.tmp / "elsewhere")
        self.refused("link in task")

    def test_a_workspace_inside_the_task_or_package_is_refused(self):
        for inside in (self.task / "environment" / "ws", self.package / "scratch" / "ws", self.task / "ws"):
            with self.subTest(inside=inside.relative_to(self.package).as_posix()):
                self.workspace = inside
                with self.assertRaises(StagingError):
                    self.stage()
                self.assertFalse(inside.exists())

    def test_a_workspace_that_is_not_empty_is_refused(self):
        self.workspace.mkdir(parents=True)
        (self.workspace / "leftover.txt").write_text("from an earlier attempt\n")
        with self.assertRaises(StagingError):
            self.stage()
        self.assertEqual([path.name for path in self.workspace.iterdir()], ["leftover.txt"])

    def test_an_existing_empty_workspace_is_filled(self):
        self.workspace.mkdir(parents=True)
        self.stage()
        self.assertTrue((self.workspace / "input.json").exists())

    def test_a_prompt_inside_the_workspace_is_refused(self):
        self.prompt = self.workspace / "prompt.md"
        self.refused("outside the workspace")

    def test_a_task_without_an_instruction_is_refused(self):
        (self.task / "instruction.md").unlink()
        self.refused("no instruction.md")


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.live = self.tmp / "live"
        (self.live / "sub").mkdir(parents=True)
        (self.live / "output.json").write_text('{"sum": 6}\n')
        (self.live / "sub" / "deep.txt").write_text("deep\n")
        (self.live / "empty").mkdir()

    def test_the_final_workspace_is_copied(self):
        capture(self.live, self.tmp / "captured")
        self.assertEqual((self.tmp / "captured" / "output.json").read_text(), '{"sum": 6}\n')
        self.assertEqual((self.tmp / "captured" / "sub" / "deep.txt").read_text(), "deep\n")
        self.assertTrue((self.tmp / "captured" / "empty").is_dir())
        (self.live / "output.json").write_text("changed later\n")
        self.assertEqual((self.tmp / "captured" / "output.json").read_text(), '{"sum": 6}\n')

    def test_links_are_not_followed_or_copied(self):
        secret = self.tmp / "secret"
        secret.mkdir()
        (secret / "key.txt").write_text("outside the workspace\n")
        link(self.live / "to-dir", secret)
        link(self.live / "to-file", secret / "key.txt")
        capture(self.live, self.tmp / "captured")
        self.assertFalse(any((self.tmp / "captured").rglob("key.txt")))
        self.assertFalse((self.tmp / "captured" / "to-dir").exists())
        self.assertFalse((self.tmp / "captured" / "to-file").exists())
        self.assertTrue((self.tmp / "captured" / "output.json").exists())

    def test_an_existing_destination_is_refused(self):
        (self.tmp / "captured").mkdir()
        with self.assertRaises(FileExistsError):
            capture(self.live, self.tmp / "captured")


if __name__ == "__main__":
    unittest.main()
