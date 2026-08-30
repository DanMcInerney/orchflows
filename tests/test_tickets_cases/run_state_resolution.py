"""Behavioral ticket regression cases."""

from .common import *  # noqa: F401,F403


class TestRunStateRefusesUnsafeNames(unittest.TestCase):
    """A run id or artifact name is one path segment. Anything that could
    climb out of the sink's `runs/` is refused by name, never sanitized
    silently."""

    def test_an_unsafe_run_id_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for bad in ("../escape", "a/b", "a\\b", ".."):
                payload = run_cmd(worktree, "run-state", bad, "--note", "x")
                self.assertIn(bad, payload.get("error", ""), bad)
                self.assertNotIn("run_state", payload)
            self.assertFalse((sink_root() / "runs").exists())

    def test_an_unsafe_artifact_name_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            for bad in ("../escape.md", "a/b.md", "a\\b.md", ".."):
                payload = run_cmd(
                    worktree, "run-state", "testrun", "--artifact", bad, "--text", "x"
                )
                self.assertIn(bad, payload.get("error", ""), bad)
                self.assertNotIn("run_state", payload)
            self.assertFalse((sink_root() / "runs").exists())


class TestRelativeGitdirPointer(unittest.TestCase):
    """`make_worktree` writes an absolute pointer; git writes a relative one
    whenever the worktree was added with a relative path.

    The bodies moved to `scripts/state_root.py`; these two names survive
    here as re-exports, because `scripts/cutcheck.py` and `scripts/ui.py`
    still import them from this module. What is graded is that the
    re-export is the owner's function and not a second copy of it.
    """

    def test_a_relative_pointer_resolves_against_the_pointer_files_own_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main = tmp / "main"
            (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
            worktree = tmp / "wt"
            worktree.mkdir()
            pointer = worktree / ".git"
            pointer.write_text("gitdir: ../main/.git/worktrees/wt\n", encoding="utf-8")
            self.assertEqual(main.resolve(), tickets_mod._main_checkout_root(pointer))
            self.assertEqual(main.resolve(), tickets_mod._find_repo_root(worktree))

    def test_the_two_names_are_the_resolvers_own_functions(self):
        self.assertIs(
            tickets_mod.state_root.main_checkout_root, tickets_mod._main_checkout_root
        )
        self.assertIs(
            tickets_mod.state_root.find_repo_root, tickets_mod._find_repo_root
        )
