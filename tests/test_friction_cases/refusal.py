from __future__ import annotations

from .common import *
from .common import _IsolatedRepoTestCase

from .storage import _ProvenanceTestCase

class TestMainMalformedArgvIsRefused(_IsolatedRepoTestCase):
    """The second malformed call the logger answers out loud.

    `templates/host-block.md` tells the agent to append the line by hand
    whenever the logger cannot run, and an exit 0 with an empty stdout is
    not something an agent can read that from -- the only signal was the
    *absence* of `friction logged`, which is also what a successful run
    looks like to anyone not diffing the stream. On this host a mis-quoted
    call is the common way to lose an entry, so a malformed argv is
    refused at parse, before any write, one line on stderr, non-zero.
    """

    def _run_main_stderr(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = friction.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def _assert_refused(self, argv):
        rc, out, err = self._run_main_stderr(argv)
        self.assertEqual(friction.USAGE_EXIT, rc)
        self.assertEqual("", out)
        self.assertEqual(1, len(err.strip().splitlines()), err)
        self.assertIn("friction.py:", err)
        self.assertFalse(self._log_path().exists())

    def test_zero_positional_args(self):
        self._assert_refused([])

    def test_one_positional_arg(self):
        self._assert_refused(["only one"])

    def test_three_positional_args(self):
        self._assert_refused(["a", "b", "c"])

    def test_dangling_known_flag_missing_its_value(self):
        self._assert_refused(["o", "e", "--skill"])

    def test_unknown_flag_is_absorbed_as_positional_and_rejected(self):
        self._assert_refused(["--bogus", "value", "o", "e"])

    def test_unknown_equals_flag_is_absorbed_as_positional_and_rejected(self):
        self._assert_refused(["--bogus=value", "o", "e"])

    def test_the_refusal_names_the_two_positional_arguments_it_wanted(self):
        # A corrected retry is the point of refusing, so the line has to
        # carry what a corrected call looks like.
        _, _, err = self._run_main_stderr(["only one"])
        self.assertIn("observed", err)
        self.assertIn("expected", err)

    def test_the_process_exit_code_carries_the_refusal(self):
        env = dict(os.environ, **{STATE_HOME_ENV_VAR: str(self.sink)})
        result = subprocess.run(
            [sys.executable, str(FRICTION_PY), "only one"],
            capture_output=True, text=True, cwd=str(self.repo), env=env,
        )
        self.assertEqual(friction.USAGE_EXIT, result.returncode)
        self.assertIn("friction.py:", result.stderr)
        self.assertFalse(self._log_path().exists())


class TestRemovedCategoryOptionIsRefused(_IsolatedRepoTestCase):
    """The retired option is an ordinary unknown-option usage error."""

    def _run_main_stderr(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = friction.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def _assert_removed_option_refused(self, argv):
        rc, out, err = self._run_main_stderr(argv)
        self.assertEqual(friction.USAGE_EXIT, rc)
        self.assertEqual("", out)
        self.assertFalse(self._log_path().exists())
        self.assertIn("expected two positional arguments", err)

    def test_space_form_is_refused_without_writing(self):
        self._assert_removed_option_refused(["o", "e", "--category", "workaround"])

    def test_equals_form_is_refused_without_writing(self):
        self._assert_removed_option_refused(["o", "e", "--category=workaround"])

    def test_the_process_exit_code_carries_the_refusal(self):
        """`main` returning 2 is only the contract if the process does. The
        CLI path is `raise SystemExit(main(...))`, so it is read here."""
        env = dict(os.environ, **{STATE_HOME_ENV_VAR: str(self.sink)})
        result = subprocess.run(
            [sys.executable, str(FRICTION_PY), "o", "e", "--category", "workaround"],
            capture_output=True, text=True, cwd=str(self.repo), env=env,
        )
        self.assertEqual(friction.USAGE_EXIT, result.returncode)
        self.assertIn("expected two positional arguments", result.stderr)
        self.assertFalse(self._log_path().exists())


class TestMainInternalFailuresNameThemselvesAndExitZero(_IsolatedRepoTestCase):
    """An internal failure still exits 0 -- and now says that it happened.

    `rules/improvement.md` §1 forbids blocking and failing; it does not
    forbid printing, and the entry is lost either way. What one stderr
    line buys is the difference between "logged" and "not logged" being
    readable by the caller, which is what `templates/host-block.md`'s
    hand-append remedy triggers on. Never a traceback: one line, naming
    the cause.
    """

    def _run_main_stderr(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = friction.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def _assert_named_failure(self, rc, out, err):
        self.assertEqual(0, rc)
        self.assertEqual("", out)
        self.assertEqual(1, len(err.strip().splitlines()), err)
        self.assertIn("not logged", err)
        self.assertNotIn("Traceback", err)

    def test_unwritable_target_directory(self):
        # Pre-create the sink root as a plain file so mkdir(parents=True)
        # for the friction/ subdirectory raises FileExistsError.
        self.sink.write_text("blocked", encoding="utf-8")
        self._assert_named_failure(*self._run_main_stderr(["o", "e"]))

    def test_an_unwritable_sink_is_never_traded_for_a_writable_cwd(self):
        # There is no fallback at this seam. A blocked sink loses the entry;
        # it does not resurrect the per-repository `.orch/` this run retired.
        self.sink.write_text("blocked", encoding="utf-8")
        before = sorted(p.name for p in self.repo.iterdir())
        self._run_main_stderr(["o", "e"])
        self.assertEqual(before, sorted(p.name for p in self.repo.iterdir()))
        self.assertFalse((self.repo / ".orch").exists())

    def test_a_resolver_that_cannot_be_imported_is_named(self):
        # The two-arm import lives inside a function precisely so main()'s
        # broad except can catch its failure. At module scope this would
        # traceback before there was a main() to swallow it.
        with mock.patch.object(
            friction, "_state_root", side_effect=ImportError("no state_root")
        ):
            rc, out, err = self._run_main_stderr(["o", "e"])
        self._assert_named_failure(rc, out, err)
        self.assertIn("no state_root", err)

    def test_lone_surrogate_value_does_not_raise_or_corrupt_the_log(self):
        rc, out, err = self._run_main_stderr(["bad \udcff value", "expected"])
        self.assertEqual(0, rc)
        self.assertEqual("", out)
        self.assertIn("not logged", err)
        log = self._log_path()
        if log.exists():
            content = log.read_text(encoding="utf-8")
            for line in content.splitlines():
                json.loads(line)  # any line present must be a complete, valid entry
class TestFrictionNeverFails(_ProvenanceTestCase):
    """Every field added here is a new way to fail inside a script that cannot.

    Each case breaks one resolution and asserts the cost is that field,
    that the process exits 0, that nothing is printed on failure and
    exactly ``friction logged`` on success, and that stderr carries no
    traceback -- at most the one line naming what was not logged.
    """

    def _run_main_capturing_stderr(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = friction.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_an_unwritable_sink_root_loses_the_entry_and_names_the_loss(self):
        if os.name == "nt" or os.getuid() == 0:  # pragma: no cover - platform
            self.skipTest("directory mode is not a write barrier here")
        self.sink.mkdir(parents=True)
        self.sink.chmod(stat.S_IRUSR | stat.S_IXUSR)
        self.addCleanup(self.sink.chmod, stat.S_IRWXU)
        rc, out, err = self._run_main_capturing_stderr(["o", "e"])
        self.assertEqual(0, rc)
        self.assertEqual("", out)
        self.assertIn("not logged", err)

    def test_a_sink_root_whose_parent_is_a_regular_file(self):
        blocker = self.tmp / "blocker"
        blocker.write_text("not a directory", encoding="utf-8")
        os.environ[STATE_HOME_ENV_VAR] = str(blocker / "sink")
        rc, out, err = self._run_main_capturing_stderr(["o", "e"])
        self.assertEqual(0, rc)
        self.assertEqual("", out)
        self.assertIn("not logged", err)

    def test_a_run_identity_that_is_a_directory_costs_the_run_branch_only(self):
        here = self.repository("beta", origin="https://x/beta")
        self.chdir(here)
        run = "20260814T000000Z-alpha"
        (self.sink / "runs" / run / tickets.RUN_IDENTITY_NAME).mkdir(parents=True)
        rc, out, err = self._run_main_capturing_stderr(["o", "e", "--run", run])
        self.assertEqual(0, rc)
        self.assertEqual("friction logged", out.strip())
        self.assertEqual("", err)
        entry = self.last_entry()
        self.assertEqual(str(here), self.project_of(entry)["root"])
        self.assertEqual("cwd", entry["project_source"])

    def test_an_unreadable_git_config_costs_the_origin_only(self):
        if os.name == "nt" or os.getuid() == 0:  # pragma: no cover - platform
            self.skipTest("file mode is not a read barrier here")
        here = self.repository("beta", origin="https://x/beta")
        config = here / ".git" / "config"
        config.chmod(0)
        self.addCleanup(config.chmod, stat.S_IRUSR | stat.S_IWUSR)
        self.chdir(here)
        rc, out, err = self._run_main_capturing_stderr(["o", "e"])
        self.assertEqual(0, rc)
        self.assertEqual("friction logged", out.strip())
        self.assertEqual("", err)
        entry = self.last_entry()
        self.assertEqual({"root": str(here), "origin": None, "name": "beta"},
                         self.project_of(entry))
        self.assertEqual("cwd", entry["project_source"])

    def test_a_project_resolver_that_raises_costs_the_fields_not_the_entry(self):
        # The case that proves the guards are per-field rather than one
        # guard around the write. Two depths: the sibling import, and the
        # whole provenance step. The rule itself is the case below.
        targets = ("_identity_module", "_provenance")
        for name in targets:
            with self.subTest(name):
                self._log_path().unlink(missing_ok=True)
                with mock.patch.object(
                    friction, name, side_effect=RuntimeError("resolver is broken")
                ):
                    rc, out, err = self._run_main_capturing_stderr(["o", "e"])
                self.assertEqual(0, rc)
                self.assertEqual("friction logged", out.strip())
                self.assertEqual("", err)
                entry = self.last_entry()
                self.assertIsNone(entry["project"])
                self.assertEqual("none", entry["project_source"])
                self.assertEqual(LOGGER_ENTRY_KEYS | PROVENANCE_KEYS, set(entry))

    def test_a_writer_identity_that_raises_costs_the_project_not_the_entry(self):
        with mock.patch.object(
            tickets, "_writer_identity", side_effect=RuntimeError("no identity")
        ):
            rc, out, err = self._run_main_capturing_stderr(["o", "e"])
        self.assertEqual(0, rc)
        self.assertEqual("friction logged", out.strip())
        self.assertEqual("", err)
        entry = self.last_entry()
        self.assertIsNone(entry["project"])
        self.assertIsNone(entry["workspace"])
        self.assertEqual("none", entry["project_source"])
        # The one field that does not depend on resolving anything survives.
        self.assertEqual(tickets.SINK_CONVENTION, entry["sink_convention"])
