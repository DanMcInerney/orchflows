"""Workspace CLI, vantage, and empty-scope behavior."""

from .common import *  # noqa: F401,F403

class NoFormatCallsTest(unittest.TestCase):
    """Completion criterion 1 of item-05-fstring-pass: no `.format(` call site
    remains in scripts/workspace.py."""

    def test_workspace_py_contains_no_format_calls(self):
        source = WORKSPACE_PY.read_text(encoding="utf-8")
        self.assertNotIn(".format(", source)


class TestHelpAndVantage(unittest.TestCase):
    """F-3: the two questions a caller asks this script before it can use it.

    *What are the arguments* -- answered by ``--help`` at exit 0, from
    anywhere, rather than by the exit-1 refusal an unknown subcommand earns.
    *Can I grade from here* -- answered by a refusal that names the caller's
    position, rather than by the verdict ``isolation-missing``, which says
    the item failed when in fact the caller only stood in the wrong place.
    Every method here carries ``help_or_vantage`` in its name: it is the
    ticket's oracle selector.
    """

    def test_help_or_vantage_bare_help_prints_usage_at_exit_zero(self):
        # from a directory that is no repository: help answers before any
        # git or sink question, which is the state a caller asking is in
        with tempfile.TemporaryDirectory() as tmp:
            for flag in ("--help", "-h"):
                with self.subTest(flag=flag):
                    done = run_workspace(Path(tmp), flag)
                    self.assertEqual(0, done.returncode, done.stderr)
                    self.assertIn("usage: workspace.py", done.stdout)
                    self.assertIn("workspace.py start ", done.stdout)
                    self.assertIn("workspace.py check ", done.stdout)

    def test_help_or_vantage_each_subcommand_help_prints_its_own_usage(self):
        with tempfile.TemporaryDirectory() as tmp:
            for command in ("start", "check"):
                with self.subTest(command=command):
                    done = run_workspace(Path(tmp), command, "--help")
                    self.assertEqual(0, done.returncode, done.stderr)
                    self.assertIn(f"workspace.py {command} ", done.stdout)

    @staticmethod
    def _linked_workspace(tmp: Path):
        """A repository, a linked worktree holding the item's branch one commit
        past the base, and a ticket recording it: an isolated item at its join.

        Built inline rather than taken from ``graded_repository``, per that
        fixture's own rule -- this shape needs a caller standing *in* the
        linked tree, which the shared fixture's single main checkout is not.
        """

        main, run_dir = make_repo(tmp)
        base = git(main, "rev-parse", "HEAD").strip()
        worktree = add_worktree(main, "wt-branch", tmp / "wt")
        commit_in(worktree, {"scratch/a.txt": "one\n"}, "item work")
        make_ticket(
            run_dir, "T1", scope=("scratch",),
            extra=((workspace.ISOLATION_KEY, "required"),
                   (workspace.BRANCH_KEY, "wt-branch")),
        )
        return main, worktree, base

    def test_help_or_vantage_check_from_inside_the_workspace_names_the_vantage(self):
        """The caller stood in the item's own linked worktree. Nothing about
        the item failed; the grade cannot be taken from here. Answering that
        with ``isolation-missing`` reports a breach that did not happen, and
        an integrator reading exit 2 rejects work that is in fact intact."""

        with tempfile.TemporaryDirectory() as tmp:
            _, worktree, base = self._linked_workspace(Path(tmp))

            done = run_workspace(worktree, "check", "testrun", "T1", "--base", base)

            self.assertNotEqual(0, done.returncode, done.stdout)
            self.assertNotEqual(
                workspace.EXIT_ISOLATION_MISSING, done.returncode,
                "a vantage refusal must not masquerade as the item's verdict",
            )
            body = payload_of(done)
            self.assertIn("integrating checkout", body["error"])
            self.assertNotEqual("isolation-missing", body["verdict"])
            # a refusal that names no way forward costs the caller the same
            # search the exit-2 masquerade did
            self.assertIn("--repo", body["error"])

    def test_help_or_vantage_check_repo_grades_the_named_checkout(self):
        """``--repo`` is the way out the vantage refusal names: the caller
        stays where it is and git is run in the checkout it named."""

        with tempfile.TemporaryDirectory() as tmp:
            main, worktree, base = self._linked_workspace(Path(tmp))

            done = run_workspace(
                worktree, "check", "testrun", "T1", "--base", base,
                "--repo", str(main),
            )

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            body = payload_of(done)["check"]
            self.assertEqual("pass", body["verdict"])
            self.assertEqual(["scratch/a.txt"], body["changed"])

    def test_help_or_vantage_check_repo_answers_from_outside_any_repository(self):
        """The grade follows the named checkout, not the caller's cwd. Run from
        a directory git knows nothing about, the same call refuses without
        ``--repo`` and passes with it -- so the flag moved where git ran."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _, base = self._linked_workspace(tmp)
            outside = tmp / "elsewhere"
            outside.mkdir()

            unaimed = run_workspace(outside, "check", "testrun", "T1", "--base", base)
            self.assertEqual(1, unaimed.returncode, unaimed.stdout)
            self.assertIn("git repository", payload_of(unaimed)["error"])

            done = run_workspace(
                outside, "check", "testrun", "T1", "--base", base,
                "--repo", str(main),
            )

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            self.assertEqual("pass", payload_of(done)["check"]["verdict"])

    def test_help_or_vantage_check_repo_without_a_path_is_refused_not_ignored(self):
        """A flag whose value went missing must not fall back to the caller's
        own checkout: that grades a checkout nobody named and reports pass."""

        with tempfile.TemporaryDirectory() as tmp:
            main, _, base = self._linked_workspace(Path(tmp))

            done = run_workspace(main, "check", "testrun", "T1", "--base", base, "--repo")

            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn("--repo", payload_of(done)["error"])

    def test_help_or_vantage_check_repo_naming_no_directory_is_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, _, base = self._linked_workspace(tmp)
            missing = str(tmp / "no-such-checkout")

            done = run_workspace(
                main, "check", "testrun", "T1", "--base", base, "--repo", missing,
            )

            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn(missing, payload_of(done)["error"])

    def test_help_or_vantage_help_does_not_swallow_a_real_usage_error(self):
        # the neighbouring behavior this must not cost: a stray flag is still
        # exit 1, and a subcommand still refuses without its required flag
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T1")
            for args in (("start", "testrun", "T1", "--extra"),
                         ("check", "testrun", "T1"),
                         ("dance",),
                         ()):
                with self.subTest(args=args):
                    self.assertEqual(1, run_workspace(main, *args).returncode)


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestAnEmptyScopeIsGradedNotRequired(unittest.TestCase):
    """The two graders of one declaration agree about the lane that writes
    nothing. An item whose effective write scope is empty is authorized to
    change no path in any workspace -- it writes its own ticket sections,
    and those live in the sink -- so dispatch packet construction emits no
    establishment step for it. A grader that still demanded the stamp
    refused such a lane at no-record for obeying the packet it was given.

    Effective, never declared: the scope ``tickets._load_ticket`` answers
    with is the cut's plus every recorded grant, so a lane a grant has
    since given paths to is graded in full again.
    """

    def test_empty_scope_with_no_stamp_is_not_required_at_exit_zero(self):
        graded = graded_item("T-noscope", scope=(), recorded=False)
        # a base no git command could resolve: reaching git at all fails,
        # so this also proves the verdict is reached before any git call
        done = run_workspace(
            graded["main"], "check", "testrun", "T-noscope", "--base", "no-such-rev"
        )
        self.assertEqual(0, done.returncode, done.stdout)
        self.assertEqual("not required", payload_of(done)["check"]["verdict"])

    def test_empty_scope_payload_names_the_declaration_and_the_scope(self):
        """Why the grade was skipped, in the payload -- an integrator reading
        `not required` under `isolation: required` must be able to see that
        the empty authority, not a missed declaration, is the reason."""

        graded = graded_item("T-noscope-why", scope=(), recorded=False)
        done = run_workspace(
            graded["main"], "check", "testrun", "T-noscope-why", "--base", "no-such-rev"
        )
        body = payload_of(done)["check"]
        self.assertEqual(workspace.REQUIRED, body[workspace.ISOLATION_KEY])
        self.assertEqual([], body[workspace.WRITE_SCOPE_KEY])

    def test_empty_scope_stamped_with_a_branch_carrying_nothing_is_not_required(self):
        """A lane given no establishment step may still have been told to run
        `start` by its caller. A stamp that carries nothing HEAD lacks -- a
        branch left at its cut, or one that no longer resolves -- is graded
        not required, where the full grade refused it at isolation-missing
        for having no distinct branch, which an empty scope never owed."""

        graded = graded_item("T-noscope-idle", branch="stale-branch", scope=())
        done = run_workspace(
            graded["main"], "check", "testrun", "T-noscope-idle",
            "--base", graded["base"],
        )
        self.assertEqual(0, done.returncode, done.stdout)
        self.assertEqual("not required", payload_of(done)["check"]["verdict"])

        graded_item("T-noscope-gone", branch="no-such-branch", scope=())
        done = run_workspace(
            graded["main"], "check", "testrun", "T-noscope-gone",
            "--base", graded["base"],
        )
        self.assertEqual(0, done.returncode, done.stdout)
        self.assertEqual("not required", payload_of(done)["check"]["verdict"])

    def test_empty_scope_stamped_with_a_branch_carrying_commits_is_a_breach(self):
        """An empty scope is authority over nothing, not a licence to skip the
        grade: a recorded branch that carries commits HEAD lacks is graded in
        full, and every path it changed is outside a scope of nothing
        (contracts/work-item.md: changed artifacts exceeding the granted
        scope are rejected at the join)."""

        graded = graded_item("T-noscope-stamped", scope=())
        done = run_workspace(
            graded["main"], "check", "testrun", "T-noscope-stamped",
            "--base", graded["base"],
        )
        self.assertEqual(4, done.returncode, done.stdout)
        body = payload_of(done)
        self.assertEqual("scope-breach", body["verdict"])
        self.assertEqual(["scratch/a.txt"], body["breaches"])

    def test_empty_scope_widened_by_a_grant_is_graded_in_full(self):
        """One granted path is an authority over workspace content, so the
        lane needs the workspace it was granted the paths for, and every
        existing grade returns -- here, no-record for the missing stamp."""

        graded = graded_item(
            "T-granted", scope=(), recorded=False,
            extra=((tickets.GRANTED_SCOPE_KEY, "[scratch]"),),
        )
        done = run_workspace(
            graded["main"], "check", "testrun", "T-granted", "--base", graded["base"]
        )
        self.assertEqual(5, done.returncode, done.stdout)
        self.assertEqual("no-record", payload_of(done)["verdict"])

    def test_empty_scope_is_not_what_an_absent_write_scope_key_means(self):
        """An empty scope is a declared authority over nothing; an absent key
        is no declaration at all, which dispatch packet construction refuses as an
        incomplete packet. Read alike, an item that never declared what it
        may change would pass its join whatever it changed."""

        graded = graded_repository()
        path = make_ticket(
            graded["run_dir"], "T-nokey", scope=(),
            extra=((workspace.ISOLATION_KEY, workspace.REQUIRED),),
        )
        text = path.read_text(encoding="utf-8")
        self.assertIn("write_scope:\n", text)
        path.write_text(text.replace("write_scope:\n", "", 1), encoding="utf-8")

        done = run_workspace(
            graded["main"], "check", "testrun", "T-nokey", "--base", graded["base"]
        )
        self.assertEqual(5, done.returncode, done.stdout)
        self.assertEqual("no-record", payload_of(done)["verdict"])
