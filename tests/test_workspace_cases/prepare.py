"""Tree preparation, a detached workspace, and absolute write-scope entries.

Three behaviors ``workspace.py start`` gained together, because all three
are things the host does to a workspace that the grader then has to read:
it installs the frontend dependencies the tree declares, it materializes a
workspace at a bare revision rather than a branch, and it writes scope
entries as absolute paths. Each one used to be a refusal or a silent miss.
"""

from .common import *  # noqa: F401,F403


def detached_worktree(main: Path, path: Path) -> Path:
    """A linked worktree on no branch at all, the shape a host produces when
    it materializes a revision instead of cutting a branch for it."""

    git(main, "worktree", "add", "--quiet", "--detach", str(path))
    return path


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestDetachedWorkspaceIsRecordedAndGraded(unittest.TestCase):
    """``rev-parse --abbrev-ref HEAD`` answers ``HEAD`` in a detached tree,
    which is no ref at all: recorded literally it resolved to nothing at the
    join, so the item graded as isolation-missing however clean its work was.
    ``detached:<full-sha>`` is a ref the join can resolve."""

    def test_start_records_the_full_sha_under_the_detached_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            worktree = detached_worktree(main, tmp / "wt")
            head = git(worktree, "rev-parse", "HEAD").strip()

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stderr)
            body = payload_of(done)["start"]
            self.assertEqual(f"detached:{head}", body[workspace.BRANCH_KEY])
            self.assertTrue(body["isolated"])
            self.assertIn(
                f"workspace_branch: detached:{head}\n",
                ticket.read_text(encoding="utf-8"),
            )

    def _graded_detached(self, files, scope=("scratch",)):
        """start in a detached worktree, commit there, grade from the main
        checkout -- the order every isolated item actually runs in."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T1", scope=scope,
                        extra=((workspace.ISOLATION_KEY, "required"),))
            base = git(main, "rev-parse", "HEAD").strip()
            worktree = detached_worktree(main, tmp / "wt")

            started = run_workspace(worktree, "start", "testrun", "T1")
            self.assertEqual(0, started.returncode, started.stderr)
            commit_in(worktree, files, "item work")
            # the caller moves on, so the workspace's revision is genuinely
            # not already in the integrating checkout's history
            commit_in(main, {"README.md": "advanced\n"}, "caller moves on")

            return run_workspace(main, "check", "testrun", "T1", "--base", base)

    def test_check_grades_a_scoped_commit_made_after_start(self):
        done = self._graded_detached({"scratch/a.txt": "one\n"})

        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        body = payload_of(done)["check"]
        self.assertEqual("pass", body["verdict"])
        self.assertEqual(["scratch/a.txt"], body["changed"])
        self.assertEqual(1, body["commits"])

    def test_check_reports_a_breach_from_a_detached_workspace_too(self):
        done = self._graded_detached({"docs/leak.md": "leak\n"})

        self.assertEqual(4, done.returncode, done.stdout + done.stderr)
        self.assertEqual(["docs/leak.md"], payload_of(done)["breaches"])


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestAbsoluteScopeEntriesAreCanonicalised(unittest.TestCase):
    """An absolute entry inside the tree is the same grant as its relative
    form and is recorded as one; an absolute entry outside the tree names
    nothing this repository can match, and is refused where the cut can
    still fix it rather than at the join."""

    def test_an_absolute_in_tree_entry_is_recorded_relative_and_graded(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            base = git(main, "rev-parse", "HEAD").strip()
            worktree = add_worktree(main, "wt-branch", tmp / "wt")
            make_ticket(run_dir, "T1", scope=(str(worktree / "scratch"),),
                        extra=((workspace.ISOLATION_KEY, "required"),))

            started = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(0, started.returncode, started.stderr)
            self.assertEqual(
                ["scratch"], payload_of(started)["start"][workspace.WRITE_SCOPE_KEY]
            )
            commit_in(worktree, {"scratch/a.txt": "one\n"}, "item work")
            commit_in(main, {"README.md": "advanced\n"}, "caller moves on")

            done = run_workspace(main, "check", "testrun", "T1", "--base", base)

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            body = payload_of(done)["check"]
            self.assertEqual(["scratch"], body[workspace.WRITE_SCOPE_KEY])
            self.assertEqual("pass", body["verdict"])

    def test_an_absolute_out_of_tree_entry_is_refused_at_start(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            outside = tmp / "elsewhere"
            outside.mkdir()
            ticket = make_ticket(run_dir, "T1", scope=("scratch", str(outside)))
            before = ticket.read_text(encoding="utf-8")
            worktree = add_worktree(main, "wt-branch", tmp / "wt")

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(1, done.returncode, done.stdout)
            error = payload_of(done)["error"]
            self.assertIn(str(outside), error)
            self.assertIn("nothing in this repository can match it", error)
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))
