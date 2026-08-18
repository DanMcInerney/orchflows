"""Workspace isolation, scope, and cleanup grading behavior."""

from .common import *  # noqa: F401,F403

@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestCheckGradesFromTheCallersGit(unittest.TestCase):
    """Completion criterion 3: one exit code per failure mode, every fact
    re-derived from git. Nothing a child wrote in prose is read."""

    def test_isolation_absent_passes_without_touching_git(self):
        graded = graded_item("T-absent", isolation=None, recorded=False)
        # a base no git command could resolve: reaching git at all fails
        done = run_workspace(
            graded["main"], "check", "testrun", "T-absent", "--base", "no-such-rev"
        )
        self.assertEqual(0, done.returncode, done.stdout)
        self.assertEqual("not required", payload_of(done)["check"]["verdict"])

    def test_isolation_none_passes_without_touching_git(self):
        graded = graded_item("T-none", isolation="none", recorded=False)
        done = run_workspace(
            graded["main"], "check", "testrun", "T-none", "--base", "no-such-rev"
        )
        self.assertEqual(0, done.returncode, done.stdout)
        self.assertEqual("not required", payload_of(done)["check"]["verdict"])

    def test_a_backticked_required_grades_the_same_as_a_bare_one(self):
        """One normalizer reads `isolation` for both scripts. `tickets.py`
        strips backticks off the same declaration when it emits the
        establishment step, so a grader that did not would skip the grade
        entirely at exit 0 while the join read success."""

        for index, declared in enumerate(("required", "`required`")):
            with self.subTest(declared=declared):
                tid = "T-backtick-%d" % index
                graded = graded_item(tid, branch="leak-branch", isolation=declared)

                done = run_workspace(
                    graded["main"], "check", "testrun", tid, "--base", graded["base"]
                )

                self.assertEqual(4, done.returncode, done.stdout)
                body = payload_of(done)
                self.assertEqual("scope-breach", body["verdict"])
                self.assertEqual(["docs/leak.md"], body["breaches"])

    def test_required_with_no_recorded_branch_exits_no_record(self):
        graded = graded_item("T-unrecorded", recorded=False)
        done = run_workspace(
            graded["main"], "check", "testrun", "T-unrecorded", "--base", graded["base"]
        )
        self.assertEqual(5, done.returncode, done.stdout)
        body = payload_of(done)
        self.assertEqual("no-record", body["verdict"])
        self.assertIn(workspace.BRANCH_KEY, body["error"])

    def test_a_branch_that_does_not_resolve_exits_isolation_missing(self):
        graded = graded_item("T-ghost", branch="ghost-branch")
        done = run_workspace(
            graded["main"], "check", "testrun", "T-ghost", "--base", graded["base"]
        )
        self.assertEqual(2, done.returncode, done.stdout)
        body = payload_of(done)
        self.assertEqual("isolation-missing", body["verdict"])
        self.assertIn("ghost-branch", body["error"])

    def test_the_callers_own_branch_exits_isolation_missing(self):
        graded = graded_repository()
        graded_item("T-own", branch=graded["own"])
        done = run_workspace(
            graded["main"], "check", "testrun", "T-own", "--base", graded["base"]
        )
        self.assertEqual(2, done.returncode, done.stdout)
        self.assertEqual("isolation-missing", payload_of(done)["verdict"])

    def test_a_branch_already_on_the_callers_head_exits_isolation_missing(self):
        # stale-branch sits at the base the caller has since moved past
        graded = graded_item("T-stale", branch="stale-branch")
        done = run_workspace(
            graded["main"], "check", "testrun", "T-stale", "--base", graded["base"]
        )
        self.assertEqual(2, done.returncode, done.stdout)
        self.assertEqual("isolation-missing", payload_of(done)["verdict"])

    def test_a_branch_not_cut_from_the_base_exits_wrong_branch_point(self):
        graded = graded_item("T-elsewhere")
        elsewhere = graded["advanced"]
        done = run_workspace(
            graded["main"], "check", "testrun", "T-elsewhere", "--base", elsewhere
        )
        self.assertEqual(3, done.returncode, done.stdout)
        body = payload_of(done)
        self.assertEqual("wrong-branch-point", body["verdict"])
        self.assertIn(elsewhere, body["error"])

    def test_an_in_scope_branch_passes_and_reports_what_it_changed(self):
        graded = graded_item("T-inscope")
        done = run_workspace(
            graded["main"], "check", "testrun", "T-inscope", "--base", graded["base"]
        )
        self.assertEqual(0, done.returncode, done.stdout)
        body = payload_of(done)["check"]
        self.assertEqual("pass", body["verdict"])
        self.assertEqual(["scratch/a.txt"], body["changed"])
        self.assertEqual(1, body["commits"])

    def test_a_path_outside_the_scope_exits_scope_breach(self):
        graded = graded_item("T-breach", branch="mixed-branch")
        done = run_workspace(
            graded["main"], "check", "testrun", "T-breach", "--base", graded["base"]
        )
        self.assertEqual(4, done.returncode, done.stdout)
        body = payload_of(done)
        self.assertEqual("scope-breach", body["verdict"])
        self.assertIn("docs/leak.md", body["error"])
        self.assertEqual(["docs/leak.md"], body["breaches"])

    def test_a_breach_arriving_inside_a_merge_commit_is_seen(self):
        graded = graded_item("T-merge", branch="merge-branch")
        base = graded["base"]
        logged = git(
            graded["main"], "log", "--name-only", "--pretty=format:",
            f"{base}..merge-branch",
        )
        self.assertNotIn("docs/leak.md", logged)

        done = run_workspace(
            graded["main"], "check", "testrun", "T-merge", "--base", base
        )

        self.assertEqual(4, done.returncode, done.stdout)
        self.assertEqual(["docs/leak.md"], payload_of(done)["breaches"])

    def test_an_unresolvable_base_is_an_internal_error(self):
        graded = graded_item("T-nobase")
        done = run_workspace(
            graded["main"], "check", "testrun", "T-nobase", "--base", "no-such-rev"
        )
        self.assertEqual(1, done.returncode, done.stdout)
        self.assertEqual("error", payload_of(done)["verdict"])

    def test_usage_errors_exit_one(self):
        graded = graded_item("T-usage")
        base = graded["base"]
        for args in (
            ("check", "testrun", "T-usage"),
            ("check", "testrun", "--base", base),
            ("check", "testrun", "T-usage", "MISSING", "--base", base),
            ("check", "testrun", "MISSING", "--base", base),
        ):
            with self.subTest(args=args):
                self.assertEqual(1, run_workspace(graded["main"], *args).returncode)


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestVerdictSurvivesCleanupAndScopeIsSegmentExact(unittest.TestCase):
    """Completion criterion 4: the branch facts are the verdict, and a scope
    entry matches on whole segments."""

    def test_check_passes_after_the_linked_tree_is_removed(self):
        # removed-branch's linked tree was removed when the fixture was
        # built; every other test here grades a branch whose tree is still
        # there, which is the contrast this one needs.
        graded = graded_item("T-removed", branch="removed-branch")
        self.assertFalse(graded["removed"].exists())

        done = run_workspace(
            graded["main"], "check", "testrun", "T-removed", "--base", graded["base"]
        )

        self.assertEqual(0, done.returncode, done.stdout)
        self.assertEqual("pass", payload_of(done)["check"]["verdict"])

    def test_a_scope_entry_matches_whole_segments_only(self):
        graded = graded_item("T-docsmith", branch="docsmith-branch", scope=("docs",))
        done = run_workspace(
            graded["main"], "check", "testrun", "T-docsmith", "--base", graded["base"]
        )
        self.assertEqual(4, done.returncode, done.stdout)
        self.assertEqual(["docsmith/x.md"], payload_of(done)["breaches"])

    def test_the_same_scope_entry_takes_its_own_segment(self):
        graded = graded_item("T-docs", branch="docs-branch", scope=("docs",))
        done = run_workspace(
            graded["main"], "check", "testrun", "T-docs", "--base", graded["base"]
        )
        self.assertEqual(0, done.returncode, done.stdout)
        self.assertEqual(["docs/x.md"], payload_of(done)["check"]["changed"])

    def test_an_absolute_scope_entry_inside_the_repository_is_normalized(self):
        graded = graded_repository()
        graded_item("T-absolute-in", scope=(str(graded["main"] / "scratch"),))
        done = run_workspace(
            graded["main"], "check", "testrun", "T-absolute-in", "--base", graded["base"]
        )
        self.assertEqual(0, done.returncode, done.stdout)
        self.assertEqual("pass", payload_of(done)["check"]["verdict"])

    def test_an_absolute_scope_entry_outside_the_repository_is_refused_by_name(self):
        graded = graded_repository()
        outside = str(graded["tmp"] / "elsewhere" / "notes.md")
        graded_item("T-absolute-out", scope=("scratch", outside))
        done = run_workspace(
            graded["main"], "check", "testrun", "T-absolute-out",
            "--base", graded["base"],
        )
        self.assertEqual(1, done.returncode, done.stdout)
        self.assertIn(outside, payload_of(done)["error"])
