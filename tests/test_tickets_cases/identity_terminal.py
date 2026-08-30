"""Behavioral ticket regression cases."""

from .identity_core import *  # noqa: F401,F403

from scripts import tickets_store as store_mod  # noqa: E402
from scripts import tickets_store_writes as writes_mod  # noqa: E402


class TestAtomicReplace(unittest.TestCase):
    """Both sides of the identity document's move, on both platforms.

    The branch that matters runs on Windows only, where a move and an open
    of one name refuse each other for the instant the move takes, so on
    every other host it is unreachable code that three cells of the matrix
    are the first to run. `msvcrt` is the discriminator the module already
    uses, so setting it is how this host asks the Windows question.

    Set on `scripts/tickets_store_writes`, the module that reads it, rather
    than on the facade or on the store facade that re-exports it: these cases
    call the writer directly instead of through the CLI, and a patch on a
    re-export reaches no reader at all.
    """

    def refusals(self, count: int):
        """A `Path.replace` that refuses `count` times, then moves."""

        real = Path.replace
        state = {"left": count, "calls": 0}

        def replace(self, target):
            state["calls"] += 1
            if state["left"] > 0:
                state["left"] -= 1
                raise PermissionError(5, "Access is denied")
            return real(self, target)

        return replace, state

    def move(self, tmp: Path):
        source = tmp / "source"
        source.write_text("moved\n", encoding="utf-8")
        return source, tmp / "target"

    def test_windows_waits_out_a_transient_refusal(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source, target = self.move(tmp)
            replace, state = self.refusals(3)
            with mock.patch.object(writes_mod, "msvcrt", object()), mock.patch.object(
                Path, "replace", replace
            ):
                writes_mod._replace_atomically(source, target)
            self.assertEqual(4, state["calls"])
            self.assertEqual("moved\n", target.read_text(encoding="utf-8"))

    def test_a_refusal_that_never_ends_is_reported_when_the_budget_runs_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source, target = self.move(tmp)
            replace, _ = self.refusals(10**6)
            with mock.patch.object(writes_mod, "msvcrt", object()), mock.patch.object(
                writes_mod, "REPLACE_BUDGET_SECONDS", 0.05
            ), mock.patch.object(Path, "replace", replace):
                with self.assertRaises(PermissionError):
                    writes_mod._replace_atomically(source, target)
            self.assertFalse(target.exists())

    def test_posix_takes_the_first_answer(self):
        """No retry where the platform has no transient refusal: a refusal
        there is real, and waiting on it would only delay the report."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            source, target = self.move(tmp)
            replace, state = self.refusals(1)
            with mock.patch.object(writes_mod, "msvcrt", None), mock.patch.object(
                Path, "replace", replace
            ):
                with self.assertRaises(PermissionError):
                    writes_mod._replace_atomically(source, target)
            self.assertEqual(1, state["calls"])

    def test_an_unobstructed_move_costs_one_attempt_on_either_platform(self):
        for label, sentinel in (("windows", object()), ("posix", None)):
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                source, target = self.move(tmp)
                replace, state = self.refusals(0)
                with mock.patch.object(writes_mod, "msvcrt", sentinel), mock.patch.object(
                    Path, "replace", replace
                ):
                    writes_mod._replace_atomically(source, target)
                self.assertEqual(1, state["calls"])
                self.assertFalse(source.exists())
                self.assertEqual("moved\n", target.read_text(encoding="utf-8"))

    def test_an_absent_file_is_an_answer_and_is_never_waited_on(self):
        """The refusal is waited out; every other `OSError` is a fact. Most
        run-state writes open a run that has no identity yet, and a budget
        spent on that would be paid by the ordinary path to spare the rare
        one."""

        calls = []

        def missing():
            calls.append(1)
            raise FileNotFoundError(2, "No such file or directory")

        with mock.patch.object(writes_mod, "msvcrt", object()):
            with self.assertRaises(FileNotFoundError):
                writes_mod._waiting_out_windows(missing)
        self.assertEqual(1, len(calls))

    def test_the_reader_waits_out_a_writers_move_and_returns_the_document(self):
        """The other side of the same instant: an `open` of the name a move
        is landing on is refused too, and a run-state write that reported it
        would fail for someone else's write."""

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.json"
            path.write_text('{"run": "testrun"}\n', encoding="utf-8")
            real = Path.read_text
            state = {"left": 3}

            def read_text(self, *args, **kwargs):
                if state["left"] > 0:
                    state["left"] -= 1
                    raise PermissionError(13, "Permission denied")
                return real(self, *args, **kwargs)

            with mock.patch.object(writes_mod, "msvcrt", object()), mock.patch.object(
                Path, "read_text", read_text
            ):
                document, error = store_mod._read_identity(path)
            self.assertIsNone(error)
            self.assertEqual({"run": "testrun"}, document)
            self.assertEqual(0, state["left"])

    def test_a_reader_refused_past_the_budget_is_still_refused_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run.json"
            path.write_text('{"run": "testrun"}\n', encoding="utf-8")

            def read_text(self, *args, **kwargs):
                raise PermissionError(13, "Permission denied")

            with mock.patch.object(writes_mod, "msvcrt", object()), mock.patch.object(
                writes_mod, "REPLACE_BUDGET_SECONDS", 0.05
            ), mock.patch.object(Path, "read_text", read_text):
                document, error = store_mod._read_identity(path)
            self.assertIsNone(document)
            self.assertIn("unreadable run identity", error["error"])


class TestRunIdentityCollision(unittest.TestCase):
    """A run id is one project's. Two projects that pick the same one
    interleave into one worklog and neither can tell which line is whose, so
    the second is refused by name and nothing at all lands."""

    def opened_by_alpha(self, tmp: Path):
        use_sink(tmp)
        alpha = make_clone(tmp / "a", ALPHA)
        beta = make_clone(tmp / "b", BETA)
        run_cmd(alpha, "run-state", "testrun", "--note", "alpha opened it")
        return alpha, beta

    def assert_nothing_moved(self, identity: bytes, worklog: bytes):
        self.assertEqual(identity, identity_of().read_bytes())
        self.assertEqual(worklog, notes_of().read_bytes())
        self.assertEqual(
            ["notes.md", "run.json"],
            sorted(path.name for path in run_dir_of().iterdir()),
        )
        self.assertFalse((sink_root() / "tickets").exists())

    def test_a_different_origin_is_refused_by_name_and_nothing_lands(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _alpha, beta = self.opened_by_alpha(tmp)
            identity, worklog = identity_bytes(), notes_of().read_bytes()
            payload = run_cmd(beta, "run-state", "testrun", "--note", "beta tried")
            self.assertNotIn("run_state", payload)
            self.assertIn("acme/alpha", payload["error"])
            self.assertIn("other/beta", payload["error"])
            self.assert_nothing_moved(identity, worklog)

    def test_the_refusal_blocks_an_artifact_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            _alpha, beta = self.opened_by_alpha(tmp)
            identity, worklog = identity_bytes(), notes_of().read_bytes()
            payload = run_cmd(
                beta, "run-state", "testrun", "--artifact", "beta.md", "--text", "x"
            )
            self.assertNotIn("run_state", payload)
            self.assertIn("acme/alpha", payload["error"])
            self.assert_nothing_moved(identity, worklog)

    def test_two_rootless_projects_still_collide(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            first = make_clone(tmp / "a", None)
            second = make_clone(tmp / "b", None)
            run_cmd(first, "run-state", "testrun", "--note", "a opened it")
            payload = run_cmd(second, "run-state", "testrun", "--note", "b tried")
            self.assertNotIn("run_state", payload)
            self.assertIn(str(first.resolve()), payload["error"])
            self.assertIn(str(second.resolve()), payload["error"])
            self.assertEqual([str(first.resolve())], workspaces_of())

    def test_one_rootless_project_still_appends(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            main, worktree, _ = make_worktree(tmp, {"T1": ("claimed", "[]")})
            run_cmd(main, "run-state", "testrun", "--note", "from main")
            payload = run_cmd(worktree, "run-state", "testrun", "--note", "from the tree")
            self.assertNotIn("error", payload)
            self.assertEqual(2, len(workspaces_of()))

    def test_a_checkout_that_gained_a_remote_is_still_itself(self):
        """Identity falls back to the root whenever either side has no
        origin, so `git remote add` mid-run does not lock a project out of
        the run it opened."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            repo = make_clone(tmp / "repo", None)
            run_cmd(repo, "run-state", "testrun", "--note", "before the remote")
            (repo / ".git" / "config").write_text(
                GIT_CONFIG.format(remote="origin", url=ALPHA), encoding="utf-8"
            )
            payload = run_cmd(repo, "run-state", "testrun", "--note", "after the remote")
            self.assertNotIn("error", payload)
            # `project` is the first writer's and is never rewritten
            self.assertIsNone(identity_doc()["project"]["origin"])

    def test_an_unreadable_identity_is_refused_by_name_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            use_sink(tmp)
            repo = make_clone(tmp / "repo", ALPHA)
            run_cmd(repo, "run-state", "testrun", "--note", "one")
            worklog = notes_of().read_bytes()
            for corrupt in ("{ not json", '"a string, not an object"'):
                with self.subTest(corrupt):
                    identity_of().write_text(corrupt, encoding="utf-8")
                    payload = run_cmd(repo, "run-state", "testrun", "--note", "two")
                    self.assertNotIn("run_state", payload)
                    self.assertIn(str(identity_of()), payload["error"])
                    self.assertEqual(corrupt, identity_of().read_text(encoding="utf-8"))
                    self.assertEqual(worklog, notes_of().read_bytes())


class TestNoFallback(unittest.TestCase):
    """rules/visibility.md §6: a write that cannot reach the resolved root
    fails loudly and lands nowhere — in particular not in the caller's own
    tree, which is the silent loss this channel exists to end."""

    @staticmethod
    def block_the_sink(tmp: Path) -> Path:
        """A sink root that cannot be created, on every platform.

        Its parent is a regular file, so `mkdir` raises `NotADirectoryError`
        rather than depending on a permission bit Windows does not have.
        """

        blocker = tmp / "not-a-directory"
        blocker.write_text("this is a file\n", encoding="utf-8")
        os.environ[STATE_HOME_ENV_VAR] = str(blocker / "state")
        return blocker

    @staticmethod
    def listing(root: Path) -> list:
        return sorted(str(path.relative_to(root)) for path in root.rglob("*"))

    def test_run_state_reports_and_lands_nowhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            repo = make_clone(tmp / "repo", ALPHA)
            (repo / "work.txt").write_text("payload\n", encoding="utf-8")
            blocker = self.block_the_sink(tmp)
            before = self.listing(repo)
            for args in (
                ("run-state", "testrun", "--note", "a line"),
                ("run-state", "testrun", "--artifact", "e.md", "--text", "bytes"),
            ):
                with self.subTest(args[2]):
                    completed = run_full(repo, *args)
                    # the script's convention: an error payload, and a
                    # nonzero exit carrying it out to the caller
                    self.assertEqual(1, completed.returncode, completed.stderr)
                    payload = json.loads(completed.stdout)
                    self.assertIn("error", payload)
                    self.assertNotIn("run_state", payload)
            self.assertEqual(before, self.listing(repo))
            self.assertFalse((repo / ".orch").exists())
            self.assertTrue(blocker.is_file())

    def test_every_ticket_writing_subcommand_reports_and_lands_nowhere(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            repo = make_clone(tmp / "repo", ALPHA)
            body = repo / "body.md"
            body.write_text("a result body\n", encoding="utf-8")
            self.block_the_sink(tmp)
            before = self.listing(repo)
            for args in (
                ("join-noop-repair", "testrun", "T1", "--by", "agent-a"),
                ("set-status", "testrun", "T1", "complete"),
                ("result", "testrun", "T1", "--section", "Result", "--file", str(body)),
            ):
                with self.subTest(args[0]):
                    completed = run_full(repo, *args)
                    self.assertEqual(1, completed.returncode, completed.stderr)
                    self.assertIn("error", json.loads(completed.stdout))
            self.assertEqual(before, self.listing(repo))
            self.assertFalse((repo / ".orch").exists())
