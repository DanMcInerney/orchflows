"""Repository identity cases for state-root records."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.test_state_root_cases.support import ENV_VAR, state_root


class TestFindRepoRootNamesTheProject(unittest.TestCase):
    """Which project a record arose in, never where the record goes."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()

    def make_main(self, name="main") -> Path:
        main = self.tmp / name
        (main / ".git").mkdir(parents=True)
        return main

    def test_main_checkout_resolves_to_itself(self):
        main = self.make_main()
        sub = main / "skills" / "kernel"
        sub.mkdir(parents=True)
        self.assertEqual(main, state_root.find_repo_root(sub))

    def test_linked_worktree_resolves_to_its_main_checkout(self):
        main = self.make_main()
        (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
        wt = self.tmp / "wt"
        wt.mkdir()
        (wt / ".git").write_text(
            f"gitdir: {main / '.git' / 'worktrees' / 'wt'}\n", encoding="utf-8"
        )
        self.assertEqual(main, state_root.find_repo_root(wt))

    def test_relative_gitdir_pointer_resolves_to_the_superproject(self):
        super_repo = self.make_main("super")
        (super_repo / ".git" / "modules" / "mod").mkdir(parents=True)
        mod = super_repo / "mod"
        mod.mkdir()
        (mod / ".git").write_text("gitdir: ../.git/modules/mod\n", encoding="utf-8")
        self.assertEqual(super_repo, state_root.find_repo_root(mod))

    def test_a_pointer_that_does_not_parse_names_the_worktree(self):
        main = self.make_main()
        vendored = main / "vendored"
        vendored.mkdir()
        (vendored / ".git").write_text("not a gitdir pointer\n", encoding="utf-8")
        self.assertEqual(vendored, state_root.find_repo_root(vendored))

    def test_a_pointer_that_cannot_be_read_names_the_worktree_too(self):
        main = self.make_main()
        (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
        wt = self.tmp / "wt"
        wt.mkdir()
        (wt / ".git").write_text(
            f"gitdir: {main / '.git' / 'worktrees' / 'wt'}\n", encoding="utf-8"
        )
        with mock.patch.object(Path, "read_text", side_effect=OSError("refused")):
            self.assertEqual(wt, state_root.find_repo_root(wt))

    def test_no_repository_returns_none(self):
        bare = self.tmp / "bare"
        bare.mkdir()
        self.assertIsNone(state_root.find_repo_root(bare))

    def test_the_walk_up_is_bounded(self):
        deep = self.tmp.joinpath(*[f"d{i}" for i in range(state_root.MAX_WALK_UP + 4)])
        deep.mkdir(parents=True)
        self.assertIsNone(state_root.find_repo_root(deep))

    def test_a_none_project_does_not_stop_the_sink_from_resolving(self):
        bare = self.tmp / "bare"
        bare.mkdir()
        with mock.patch.dict(os.environ, {ENV_VAR: str(self.tmp / "sink")}):
            self.assertIsNone(state_root.find_repo_root(bare))
            self.assertEqual(self.tmp / "sink" / "runs", state_root.runs_root())
