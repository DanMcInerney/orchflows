"""Installer regression cases grouped by behavioral seam."""

from __future__ import annotations

from ..support import *  # noqa: F403


class TestSourceCommit(unittest.TestCase):
    """Criterion 6: the receipt gains ``source_commit`` (git HEAD of the
    installed-from repo, null when unavailable); a rerun whose HEAD moved
    prints the drift."""

    def test_resolve_source_commit_follows_a_branch_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".git" / "refs" / "heads").mkdir(parents=True)
            (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            (repo / ".git" / "refs" / "heads" / "main").write_text("abc123\n", encoding="utf-8")

            self.assertEqual("abc123", install.resolve_source_commit(repo))

    def test_resolve_source_commit_reads_detached_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".git").mkdir(parents=True)
            (repo / ".git" / "HEAD").write_text("deadbeef\n", encoding="utf-8")

            self.assertEqual("deadbeef", install.resolve_source_commit(repo))

    def test_resolve_source_commit_falls_back_to_packed_refs(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / ".git").mkdir(parents=True)
            (repo / ".git" / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
            (repo / ".git" / "packed-refs").write_text(
                "# pack-refs with: peeled fully-peeled sorted\nfeedface refs/heads/main\n",
                encoding="utf-8",
            )

            self.assertEqual("feedface", install.resolve_source_commit(repo))

    def test_resolve_source_commit_is_none_without_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(install.resolve_source_commit(Path(tmp)))

    @staticmethod
    def _worktree(root: Path, gitdir_line: str = None) -> Path:
        """A git worktree layout: ``<root>/wt/.git`` is a *file* pointing at
        ``<root>/main/.git/worktrees/wt``, which holds this worktree's HEAD
        and a ``commondir`` pointer to the shared ``.git`` where refs live.
        Every agent worktree in this repository has exactly this shape."""

        main_git = root / "main" / ".git"
        (main_git / "refs" / "heads").mkdir(parents=True)
        worktree_git = main_git / "worktrees" / "wt"
        worktree_git.mkdir(parents=True)
        (worktree_git / "HEAD").write_text("ref: refs/heads/work\n", encoding="utf-8")
        (worktree_git / "commondir").write_text("../..\n", encoding="utf-8")
        repo = root / "wt"
        repo.mkdir()
        pointer = gitdir_line if gitdir_line is not None else f"gitdir: {worktree_git}"
        (repo / ".git").write_text(pointer + "\n", encoding="utf-8")
        return repo

    def test_resolve_source_commit_follows_a_worktree_gitdir_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._worktree(root)
            (root / "main" / ".git" / "refs" / "heads" / "work").write_text(
                "beadfeed\n", encoding="utf-8"
            )

            self.assertEqual("beadfeed", install.resolve_source_commit(repo))

    def test_resolve_source_commit_reads_a_worktree_ref_from_packed_refs(self):
        # The worktree's own gitdir holds no refs/ at all: HEAD names a branch
        # whose only record is the shared checkout's packed-refs, reachable
        # only through commondir.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo = self._worktree(root)
            (root / "main" / ".git" / "packed-refs").write_text(
                "# pack-refs with: peeled fully-peeled sorted\nfeedface refs/heads/work\n",
                encoding="utf-8",
            )

            self.assertEqual("feedface", install.resolve_source_commit(repo))

    def test_resolve_source_commit_is_none_on_an_unparseable_gitdir_pointer(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._worktree(Path(tmp), gitdir_line="not a gitdir pointer")

            self.assertIsNone(install.resolve_source_commit(repo))

    def test_an_empty_gitdir_pointer_does_not_read_the_working_tree(self):
        # "gitdir:" with nothing after it names no git dir. Resolving it to
        # the worktree root would read any file called HEAD sitting there as
        # the source commit -- a commit from outside any .git.
        with tempfile.TemporaryDirectory() as tmp:
            repo = self._worktree(Path(tmp), gitdir_line="gitdir:")
            (repo / "HEAD").write_text("cafebabe\n", encoding="utf-8")

            self.assertIsNone(install.resolve_source_commit(repo))

    def test_source_commit_drift_message_only_on_actual_change(self):
        self.assertIsNone(install.source_commit_drift_message(None, "abc"))
        self.assertIsNone(install.source_commit_drift_message({"source_commit": None}, "abc"))
        self.assertIsNone(install.source_commit_drift_message({"source_commit": "abc"}, "abc"))
        self.assertIsNone(install.source_commit_drift_message({"source_commit": "abc"}, None))
        self.assertEqual(
            "source commit drift: abc -> def",
            install.source_commit_drift_message({"source_commit": "abc"}, "def"),
        )

    def test_receipt_carries_resolved_source_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            plan = install.Plan(
                scope="user",
                project_root=None,
                lib_home=project / ".orchflows" / "lib",
                scope_home=project / ".orchflows",
                bin_dir=project / ".orch" / "bin",
                receipt_path=project / ".orchflows" / "receipt.json",
            )

            with patch.object(install, "resolve_source_commit", return_value="cafe"):
                receipt = install.apply_plan(plan)

            self.assertEqual("cafe", receipt["source_commit"])

    def test_source_commit_warning_says_why_the_commit_is_null(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)

            # Nothing to read at all.
            no_git = install.source_commit_warning(None, repo)
            self.assertIsNotNone(no_git)
            self.assertIn(str(repo), no_git)
            self.assertIn("drift", no_git)

            # A checkout that reads, whose HEAD resolves to nothing.
            (repo / ".git").mkdir()
            (repo / ".git" / "HEAD").write_text("ref: refs/heads/gone\n", encoding="utf-8")
            unresolved = install.source_commit_warning(None, repo)
            self.assertIsNotNone(unresolved)
            self.assertIn("HEAD", unresolved)
            self.assertNotEqual(no_git, unresolved)

    def test_source_commit_warning_is_silent_when_a_commit_was_resolved(self):
        self.assertIsNone(install.source_commit_warning("cafe"))

    def test_main_warns_when_the_installed_receipt_names_no_source_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)

            with patch.object(install.Path, "home", return_value=home), mock_host_clis(
                "claude"
            ), patch.object(install, "resolve_source_commit", return_value=None):
                err = io.StringIO()
                with redirect_stdout(io.StringIO()), redirect_stderr(err):
                    code = install.main(["--user", "--yes"])

            self.assertEqual(0, code)
            self.assertIn("source commit unresolved", err.getvalue())

    def test_main_prints_drift_on_second_install_with_moved_head(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)

            with patch.object(install.Path, "home", return_value=home), mock_host_clis(
                "claude"
            ), patch.object(install, "resolve_source_commit", side_effect=["sha1", "sha2"]):
                first = io.StringIO()
                with redirect_stdout(first):
                    code1 = install.main(["--user", "--yes"])
                second = io.StringIO()
                with redirect_stdout(second):
                    code2 = install.main(["--user", "--yes"])

            self.assertEqual(0, code1)
            self.assertEqual(0, code2)
            self.assertNotIn("source commit drift", first.getvalue())
            self.assertIn("source commit drift: sha1 -> sha2", second.getvalue())
class TestUnreadableReceipt(unittest.TestCase):
    """An absent receipt and an unreadable one are different facts: the first
    is a first install, the second is a file whose record of what was written
    cannot be consulted. Reading both as ``None`` let an install overwrite the
    corrupt receipt, skip every stale removal it records, and report the role
    agents it lists as 'not written by this installer' (F F3)."""

    def test_load_json_returns_none_only_for_an_absent_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "receipt.json"

            self.assertIsNone(install._load_json(path))

            path.write_text("{not json", encoding="utf-8")
            with self.assertRaises(ValueError) as raised:
                install._load_json(path)

            self.assertIn(str(path), str(raised.exception))

    def test_install_refuses_rather_than_overwriting_a_corrupt_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir(parents=True)
            receipt = home / ".orchflows" / "receipt.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_text("{truncated", encoding="utf-8")

            with patch.object(install.Path, "home", return_value=home), mock_host_clis("claude"):
                err = io.StringIO()
                with redirect_stdout(io.StringIO()), redirect_stderr(err):
                    code = install.main(["--user", "--yes"])

            self.assertEqual(1, code)
            self.assertIn("unreadable", err.getvalue())
            self.assertEqual("{truncated", receipt.read_text(encoding="utf-8"))

    def test_uninstall_refuses_a_corrupt_receipt_rather_than_finding_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            receipt = project / ".orchflows" / "receipt.json"
            receipt.parent.mkdir(parents=True)
            receipt.write_text("{truncated", encoding="utf-8")

            with self.assertRaises(ValueError):
                install.run_uninstall("project", project, dry_run=False)
