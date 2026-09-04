"""Workspace start and ticket-payload behavior."""

from .common import *  # noqa: F401,F403


class TestStartEstablishesEvidenceStore(unittest.TestCase):
    """A research lane's workspace is the run-scoped evidence store.

    The host runs ``start`` before dispatch, so the command must create and
    durably name that store without requiring the caller to stand in a Git
    checkout that has no meaning for the research adapter.
    """

    def test_research_pack_creates_and_records_the_canonical_run_store(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            sink = use_sink(tmp)
            run_dir = sink / "tickets" / "testrun"
            run_dir.mkdir(parents=True)
            ticket = make_ticket(
                run_dir,
                "T1",
                pack="orch-research-pack",
            )

            done = run_workspace(tmp, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)
            store = (sink / "research" / "testrun").resolve()
            self.assertTrue(store.is_dir())
            body = payload_of(done)["start"]
            self.assertEqual("evidence-store", body["mechanism"])
            self.assertEqual(str(store), body["workspace_root"])
            self.assertEqual(str(store), recorded_workspace(ticket))
            self.assertNotIn("workspace_branch", body)
            self.assertNotIn("workspace_baseline", body)


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestCheckUsesTheEstablishedCandidate(unittest.TestCase):
    def test_relocated_branch_does_not_replace_the_recorded_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(
                run_dir,
                "T1",
                extra=((workspace.ISOLATION_KEY, "required"),),
            )
            original = add_worktree(main, "item-branch", tmp / "original")
            started = run_workspace(original, "start", "testrun", "T1")
            self.assertEqual(0, started.returncode, started.stdout + started.stderr)
            base = git(main, "rev-parse", "HEAD").strip()
            commit_in(original, {"scratch/result.txt": "done\n"}, "result")
            git(main, "worktree", "remove", str(original))
            relocated = tmp / "relocated"
            git(main, "worktree", "add", "--quiet", str(relocated), "item-branch")

            checked = run_workspace(
                main, "check", "testrun", "T1", "--base", base
            )

            self.assertEqual(workspace.EXIT_ISOLATION_MISSING, checked.returncode)
            self.assertIn("recorded workspace_path", payload_of(checked)["error"])
            self.assertIn(str(original.resolve()), payload_of(checked)["error"])
            self.assertIn(str(relocated.resolve()), payload_of(checked)["error"])

@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestCheckDisambiguatesItsRevisionRanges(unittest.TestCase):
    """A revision range is not a filename, and git only knows that if it is
    told. `git diff A...B` with no `--` makes git stat `A...B` as a path
    before settling it as a range; on this host a long absolute revision in
    the range came back `fatal: ... Filename too long` and the whole grade
    died on a name nobody meant as a file. `--` after the range settles it."""

    def test_every_range_is_terminated_before_the_pathspec(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(
                run_dir, "T1",
                extra=((workspace.ISOLATION_KEY, "required"),
                       (workspace.BRANCH_KEY, "wt-branch")),
            )
            calls = []
            original = workspace._git

            def recorded_git(*args):
                # canned, not the real git: the point is the argv shape, and
                # a real repository would have to be built up to two commits
                # on two branches to reach the two calls under test
                calls.append(args)
                if args[:3] == ("rev-parse", "--verify", "--quiet"):
                    return 0, ("tip\n" if args[3].startswith("wt-branch") else "basecommit\n"), ""
                if args[:2] == ("rev-parse", "--abbrev-ref"):
                    return 0, "main\n", ""
                if args[0] == "merge-base":  # tip not in HEAD; base is in tip
                    return (1 if args[3] == "HEAD" else 0), "", ""
                if args[:3] == ("worktree", "list", "--porcelain"):
                    return 0, "", ""
                if args[0] == "diff":
                    return 0, "A\0scratch/a.txt\0", ""
                if args[0] == "rev-list":
                    return 0, "1\n", ""
                raise AssertionError(f"unexpected git call: {args}")

            cwd = os.getcwd()
            noise = io.StringIO()
            try:
                os.chdir(str(main))
                workspace._git = recorded_git
                with redirect_stdout(noise), redirect_stderr(noise):
                    code = workspace.main(["check", "testrun", "T1", "--base", "some-base"])
            finally:
                os.chdir(cwd)
                workspace._git = original

            self.assertEqual(0, code, noise.getvalue())
            ranged = [args for args in calls if any(".." in arg for arg in args)]
            self.assertEqual(
                [
                    ("diff", "--name-status", "--no-renames", "-z", "basecommit...tip", "--"),
                    ("rev-list", "--count", "basecommit..tip", "--"),
                ],
                ranged,
            )
            for args in ranged:
                self.assertEqual("--", args[-1], args)


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestStartRecordsWhatItObserved(unittest.TestCase):
    """Completion criterion 1: ``start`` records the branch and the baseline
    it observed, into the main-root ticket, creating no ``.orch/`` beside it."""

    def test_from_a_linked_worktree_it_writes_the_main_root_ticket_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            before = ticket.read_text(encoding="utf-8")
            worktree = add_worktree(main, "wt-branch", tmp / "wt")
            head = git(worktree, "rev-parse", "HEAD").strip()

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stderr)
            after = ticket.read_text(encoding="utf-8")
            self.assertIn("workspace_branch: wt-branch\n", after)
            self.assertIn(f"workspace_baseline: {head} clean\n", after)
            self.assertEqual(str(worktree.resolve()), recorded_workspace(ticket))
            # the targeted write: two lines inserted before the closing ---
            # and the attempt's own recorded tree, every other byte of the
            # ticket left as it was found. The expected bytes are built
            # through the recorder itself, so this pins the write's shape
            # rather than re-spelling the attempt's encoding here.
            expected, recorded = workspace_record.recorded_on_attempt(
                before.replace(
                    "---\n\n## Objective",
                    f"workspace_branch: wt-branch\n"
                    f"workspace_baseline: {head} clean\n---\n\n## Objective",
                ),
                str(worktree.resolve()),
            )
            self.assertTrue(recorded)
            self.assertEqual(expected, after)
            self.assertFalse(
                (worktree / ".orch").exists(),
                "start created a private .orch/ in the workspace",
            )
            body = payload_of(done)["start"]
            self.assertEqual("wt-branch", body["workspace_branch"])
            self.assertEqual(str(worktree.resolve()), body["workspace_path"])
            self.assertTrue(body["isolated"])

    def test_in_the_main_checkout_it_exits_zero_and_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1", extra=(("isolation", "required"),))
            branch = git(main, "rev-parse", "--abbrev-ref", "HEAD").strip()

            done = run_workspace(main, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stderr)
            body = payload_of(done)
            self.assertNotIn("error", body)
            self.assertFalse(body["start"]["isolated"])
            after = ticket.read_text(encoding="utf-8")
            self.assertIn(f"workspace_branch: {branch}\n", after)
            self.assertIn("workspace_baseline: ", after)

    def test_a_dirty_tree_records_the_exact_paths_including_both_ends_of_a_rename(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            worktree = add_worktree(main, "wt-branch", tmp / "wt")
            git(worktree, "mv", "README.md", "RENAMED.md")
            (worktree / "untracked.txt").write_text("x\n", encoding="utf-8")
            head = git(worktree, "rev-parse", "HEAD").strip()

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stderr)
            recorded = [
                line for line in ticket.read_text(encoding="utf-8").splitlines()
                if line.startswith("workspace_baseline: ")
            ]
            self.assertEqual(1, len(recorded), recorded)
            value = recorded[0][len("workspace_baseline: "):]
            self.assertTrue(value.startswith(f"{head} dirty: "), value)
            listed = value.partition("dirty: ")[2].split(", ")
            self.assertEqual(
                ["README.md", "RENAMED.md", "untracked.txt"], sorted(listed)
            )
            self.assertEqual(
                ["README.md", "RENAMED.md", "untracked.txt"],
                sorted(payload_of(done)["start"]["dirty"]),
            )


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestStartFailureBehavior(unittest.TestCase):
    """Completion criterion 2: what ``start`` refuses, and what it does not."""

    def _refuses_dirty_name(self, name: str):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            before = ticket.read_text(encoding="utf-8")
            worktree = add_worktree(main, "wt-branch", tmp / "wt")
            (worktree / name).write_text("x\n", encoding="utf-8")

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn(name, payload_of(done)["error"])
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))

    def test_a_dirty_path_with_a_comma_is_refused_by_name(self):
        self._refuses_dirty_name("a,b.txt")

    def test_a_dirty_path_with_a_quote_is_refused_by_name(self):
        self._refuses_dirty_name("it's.txt")

    def _refuses_scope_entry(self, entry: str):
        """A grant no machine can read is refused where it is still cheap.

        `check` splits a diff's paths against these entries and reports what
        falls outside them. An entry carrying a space or a parenthesis is
        prose -- "scripts/ (tests only)", "docs and rules" -- and matches no
        path at all, so every path the branch changed reads as a breach, or
        the grant silently covers nothing and every change passes. Either way
        the reading is wrong, and it is wrong at the join, hours after the
        cut that could have fixed it. So `start`, which every isolated item
        runs first, refuses it and names the contract that says a scope entry
        is a path.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1", scope=("scratch", entry))
            before = ticket.read_text(encoding="utf-8")
            worktree = add_worktree(main, "wt-branch", tmp / "wt")

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(1, done.returncode, done.stdout)
            error = payload_of(done)["error"]
            self.assertIn(entry, error)
            self.assertIn("contracts/work-item.md", error)
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))

    def test_a_scope_entry_carrying_a_space_is_refused_at_start(self):
        self._refuses_scope_entry("scripts/ and tests/")

    def test_a_scope_entry_carrying_a_parenthesis_is_refused_at_start(self):
        self._refuses_scope_entry("scripts/(tests)")

    def _accepts_scope_entry(self, entry_of):
        """A space is prose only where there is no path by that name.

        `C:\\Users\\Dan M\\...` and `/Users/Dan McInerney/...` are exactly
        paths, and a refusal keyed to the character alone refuses the host
        rather than the cut. The parenthesis stays refused: it is the shape
        the prose entries this guard was written for actually carry.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            worktree = add_worktree(main, "wt-branch", tmp / "wt")
            spaced = worktree / "a dir"
            spaced.mkdir()
            make_ticket(run_dir, "T1", scope=("scratch", entry_of(spaced)))

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)

    def test_a_relative_scope_entry_that_is_an_existing_spaced_path_is_kept(self):
        self._accepts_scope_entry(lambda spaced: spaced.name)

    def test_an_absolute_scope_entry_that_is_an_existing_spaced_path_is_kept(self):
        self._accepts_scope_entry(lambda spaced: str(spaced))

    def test_a_spaced_entry_that_is_no_path_is_still_refused(self):
        self._refuses_scope_entry("scratch and tests/")

    def test_a_bare_path_scope_is_recorded_as_before(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T1", scope=("scripts/one.py", "tests/"))
            worktree = add_worktree(main, "wt-branch", tmp / "wt")

            done = run_workspace(worktree, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stdout + done.stderr)

    def test_a_lost_frontmatter_write_race_leaves_the_winner_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            stale = ticket.read_text(encoding="utf-8")
            winner = stale.replace("status: claimed", "status: suspended")
            ticket.write_text(winner, encoding="utf-8")

            outcome = workspace._record(
                ticket, stale, "wt-branch", "deadbeef clean", str(main.resolve())
            )

            self.assertIn("error", outcome)
            self.assertIn("lost the", outcome["error"])
            self.assertEqual(winner, ticket.read_text(encoding="utf-8"))

    def test_a_lost_race_exits_one_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            before = ticket.read_text(encoding="utf-8")
            original = workspace._record
            workspace._record = lambda *a, **k: {"error": "ticket changed since read"}
            cwd = os.getcwd()
            noise = io.StringIO()
            try:
                os.chdir(str(main))
                with redirect_stdout(noise), redirect_stderr(noise):
                    code = workspace.main(["start", "testrun", "T1"])
            finally:
                os.chdir(cwd)
                workspace._record = original
            self.assertIn("ticket changed since read", noise.getvalue())
            self.assertEqual(1, code)
            self.assertEqual(before, ticket.read_text(encoding="utf-8"))

    def test_a_write_landing_during_the_git_work_is_reported_through_start(self):
        """The snapshot the stamps are written against is taken before the
        seconds of git work, not after them, so a ``set-status`` landing while
        git runs is reported rather than absorbed. Neither sibling case can
        see this: one calls ``_record`` directly with a hand-made stale
        snapshot, the other monkeypatches ``_record`` away entirely."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1")
            observe = workspace._dirty_paths

            def a_write_lands_mid_git():
                # stands in for a concurrent `set-status`, at the one moment
                # the two reads used to straddle. `.orch/` is gitignored, so
                # the dirty set git reports is unchanged by this write.
                ticket.write_text(
                    ticket.read_text(encoding="utf-8").replace(
                        "status: claimed", "status: suspended"
                    ),
                    encoding="utf-8",
                )
                return observe()

            cwd = os.getcwd()
            noise = io.StringIO()
            try:
                os.chdir(str(main))
                workspace._dirty_paths = a_write_lands_mid_git
                with redirect_stdout(noise), redirect_stderr(noise):
                    code = workspace.main(["start", "testrun", "T1"])
            finally:
                os.chdir(cwd)
                workspace._dirty_paths = observe

            self.assertEqual(1, code, noise.getvalue())
            self.assertIn("lost the frontmatter write race", noise.getvalue())
            after = ticket.read_text(encoding="utf-8")
            self.assertIn("status: suspended", after)
            self.assertNotIn(workspace.BRANCH_KEY, after)

    def test_an_unisolated_workspace_is_recorded_not_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            ticket = make_ticket(run_dir, "T1", extra=(("isolation", "required"),))

            done = run_workspace(main, "start", "testrun", "T1")

            self.assertEqual(0, done.returncode, done.stderr)
            self.assertIn("workspace_branch: ", ticket.read_text(encoding="utf-8"))

    def test_usage_errors_exit_one(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T1")
            for args in (
                ("start",),
                ("start", "testrun"),
                ("start", "testrun", "T1", "--extra"),
                ("start", "testrun", "MISSING"),
                ("dance", "testrun", "T1"),
                (),
            ):
                with self.subTest(args=args):
                    self.assertEqual(1, run_workspace(main, *args).returncode)


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class TestTicketsPayloadIsGradedNotItsExitStatus(unittest.TestCase):
    """Completion criterion 5: ``tickets.py`` exits 0 and reports failure in
    its payload; ``workspace.py`` grades the payload and exits non-zero."""

    def test_an_error_payload_returned_at_exit_zero_is_a_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, run_dir = make_repo(tmp)
            # A ticket file whose bytes are not UTF-8, which tickets.py
            # reports as an error inside the payload of an otherwise
            # successful call. It used to be `executor: orch-panel`, an engine
            # — P4-3 deleted the two engines that were illegal executors and
            # the prohibition with them, so this is the payload-error source
            # that remains for a file `_locate` accepts. Which error it is has
            # never been this test's subject; that `list` exits 0 carrying
            # one, and that `workspace.py` grades the payload rather than the
            # exit status, is.
            ticket = make_ticket(run_dir, "T1")
            ticket.write_bytes(b"---\nid: T1\nexecutor: \xff\xfe\n---\n")
            before = ticket.read_bytes()

            listed = subprocess.run(
                [sys.executable, str(TICKETS_PY), "list", "--run", "testrun"],
                capture_output=True, text=True, cwd=str(main), env=git_env(),
            )
            self.assertEqual(0, listed.returncode)
            self.assertIn("error", json.loads(listed.stdout)["tickets"][0])

            done = run_workspace(main, "start", "testrun", "T1")

            self.assertEqual(1, done.returncode, done.stdout)
            self.assertIn("unreadable ticket", payload_of(done)["error"])
            self.assertEqual(before, ticket.read_bytes())


class TestTheStampPreservesTheTicketsByteDomain(unittest.TestCase):
    """``start`` stamps three frontmatter scalars; it must not rewrite every
    other line's ending to do it. ``Path.write_text`` applies the platform
    line separator, so on Windows a pure-LF ticket came back pure CRLF and a
    three-scalar change produced a whole-file byte diff -- defeating byte-level
    audit of the record, and contradicting the byte-domain clause this run
    shipped. Every other sink writer pins ``newline='\n'`` explicitly
    (``tickets_store._write_text_atomically``, ``_create_text_exclusively``);
    this was the one that did not."""

    def _stamped(self, body: bytes) -> bytes:
        with tempfile.TemporaryDirectory() as tmp:
            ticket = Path(tmp) / "T1.md"
            ticket.write_bytes(body)
            prior = ticket.read_text(encoding="utf-8")
            result = workspace_git._record(
                ticket, prior, "a-branch", "abc123 clean", str(Path(tmp).resolve())
            )
            self.assertNotIn("error", result, result)
            return ticket.read_bytes()

    def test_a_pure_lf_ticket_is_still_pure_lf_after_the_stamp(self):
        body = b"---\nid: T1\nrun: testrun\nstatus: claimed\n---\n\n## Objective\n\nx\n"
        after = self._stamped(body)

        self.assertEqual(0, after.count(b"\r\n"), after)
        self.assertEqual(b"## Objective", after.splitlines()[-3])

    def test_only_the_two_stamped_lines_differ_from_the_prior_bytes(self):
        """Two, not three: the established tree is the attempt's, and a
        ticket carrying no attempt has nowhere to record it."""

        body = b"---\nid: T1\nrun: testrun\nstatus: claimed\n---\n\n## Objective\n\nx\n"
        before = body.split(b"\n")
        after = self._stamped(body).split(b"\n")

        added = [line for line in after if line not in before]
        self.assertEqual(
            [b"workspace_branch: a-branch", b"workspace_baseline: abc123 clean"],
            added,
        )
        self.assertEqual([], [line for line in before if line not in after])
