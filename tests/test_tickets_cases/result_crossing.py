"""Behavioral ticket regression cases."""

from .common import *  # noqa: F401,F403


class TestResultBodySource(unittest.TestCase):
    def test_both_file_and_text_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            body = worktree / "body.md"
            body.write_text("from a file\n", encoding="utf-8")
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            result = run_main(
                worktree, "result", "testrun", "T1", "--section", "Result",
                "--file", str(body), "--text", "from a string",
            )
            self.assertEqual(1, result.returncode)
            self.assertIn("error", json.loads(result.stdout))
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))

    def test_neither_file_nor_text_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _, worktree, run_dir = make_worktree(tmp, {"T1": ("claimed", "[]")})
            before = (run_dir / "T1.md").read_text(encoding="utf-8")
            result = run_main(worktree, "result", "testrun", "T1", "--section", "Result")
            self.assertEqual(1, result.returncode)
            self.assertIn("error", json.loads(result.stdout))
            self.assertEqual(before, (run_dir / "T1.md").read_text(encoding="utf-8"))
