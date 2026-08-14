"""friction.py logs to the one user-scope sink, from every repository."""
from __future__ import annotations

import ast
import contextlib
import importlib.util
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
# friction.py imports its resolver as `scripts.state_root` in-repo, falling
# back to a flat `state_root` beside it once installed. Neither name is
# importable from `tests/` alone, so put the repository root on the path
# before the module body runs.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_spec = importlib.util.spec_from_file_location(
    "friction", ROOT / "scripts" / "friction.py"
)
friction = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_spec and friction)

from scripts import tickets  # noqa: E402  the owner of project identity

STATE_HOME_ENV_VAR = "ORCHFLOWS_STATE_HOME"

# The fields the stream carried before it said which project an entry arose
# in. Named separately from the four added since, because "every existing
# field survives, with its meaning" is a property in its own right: a reader
# of an older stream and a reader of this one agree on everything they share.
LEGACY_ENTRY_KEYS = {
    "ts", "cwd", "git_rev", "host", "session",
    "category", "skill", "ticket", "run", "observed", "expected",
}
PROVENANCE_KEYS = {"project", "project_source", "workspace", "sink_convention"}
REQUIRED_ENTRY_KEYS = LEGACY_ENTRY_KEYS | PROVENANCE_KEYS


class TestTargetPath(unittest.TestCase):
    """The target is the sink's, and the cwd has no say in it.

    ``scripts/state_root.py`` owns the resolver itself and
    ``tests/test_state_root.py`` grades it; what belongs here is that
    friction.py asks it, rather than deciding for itself.
    """

    def setUp(self):
        # Register the tempdir cleanup via addCleanup (not a `with` block):
        # addCleanup runs LIFO, so a chdir-back registered after it fires
        # first. A `with tempfile.TemporaryDirectory()` wrapping a chdir
        # into itself has its own __exit__ run before any addCleanup, and on
        # Windows rmtree of the current working directory raises
        # PermissionError — that ordering bug is what this guards against.
        tmp_ctx = tempfile.TemporaryDirectory()
        self.addCleanup(tmp_ctx.cleanup)
        self.tmp = Path(tmp_ctx.name).resolve()
        self.sink = self.tmp / "sink"
        patcher = mock.patch.dict(os.environ, {STATE_HOME_ENV_VAR: str(self.sink)})
        patcher.start()
        self.addCleanup(patcher.stop)
        self.stamp = friction.datetime.now(friction.timezone.utc).strftime("%Y-%m")

    def _chdir(self, target: Path):
        before = os.getcwd()
        os.chdir(target)
        self.addCleanup(os.chdir, before)

    def _target(self) -> Path:
        return friction._target_path(friction.datetime.now(friction.timezone.utc))

    def test_the_target_is_the_sinks_friction_stream(self):
        self.assertEqual(self.sink / "friction" / f"{self.stamp}.jsonl", self._target())

    def test_a_worktree_a_main_checkout_and_no_repository_agree(self):
        main = self.tmp / "main"
        (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
        wt = self.tmp / "wt"
        wt.mkdir()
        (wt / ".git").write_text(
            f"gitdir: {main / '.git' / 'worktrees' / 'wt'}\n", encoding="utf-8"
        )
        bare = self.tmp / "bare"
        bare.mkdir()
        seen = []
        for cwd in (main, wt, bare):
            before = os.getcwd()
            os.chdir(cwd)
            try:
                seen.append(self._target())
            finally:
                os.chdir(before)
        self.assertEqual([self.sink / "friction" / f"{self.stamp}.jsonl"] * 3, seen)

    def test_the_override_is_honoured_after_the_module_was_imported(self):
        moved = self.tmp / "moved-sink"
        os.environ[STATE_HOME_ENV_VAR] = str(moved)
        self.assertEqual(moved / "friction" / f"{self.stamp}.jsonl", self._target())


class _IsolatedRepoTestCase(unittest.TestCase):
    """Base for tests that run friction.main() against a synthetic repo root.

    Never touches the real sink — ``ORCHFLOWS_STATE_HOME`` is pointed at a
    fresh tempdir for the duration, and cwd is pinned to a repository
    inside it and restored via addCleanup even if the test body raises.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.tmp = Path(self._tmp.name).resolve()
        self.repo = self.tmp / "repo"
        (self.repo / ".git").mkdir(parents=True)
        self.sink = self.tmp / "sink"
        patcher = mock.patch.dict(os.environ, {STATE_HOME_ENV_VAR: str(self.sink)})
        patcher.start()
        self.addCleanup(patcher.stop)
        before = os.getcwd()
        os.chdir(self.repo)
        self.addCleanup(os.chdir, before)

    def _log_path(self):
        stamp = friction.datetime.now(friction.timezone.utc).strftime("%Y-%m")
        return self.sink / "friction" / f"{stamp}.jsonl"

    def _run_main(self, argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = friction.main(argv)
        return rc, buf.getvalue()


class TestMainWritesEntry(_IsolatedRepoTestCase):
    def test_appends_exactly_one_json_line_with_required_keys(self):
        rc, out = self._run_main(["observed thing", "expected thing", "--category", "tool-failure"])
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "friction logged")
        lines = self._log_path().read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(set(entry), REQUIRED_ENTRY_KEYS)
        self.assertEqual(entry["observed"], "observed thing")
        self.assertEqual(entry["expected"], "expected thing")
        self.assertEqual(entry["category"], "tool-failure")

    def test_second_call_appends_a_second_line_not_a_rewrite(self):
        self._run_main(["first observed", "first expected"])
        self._run_main(["second observed", "second expected"])
        lines = self._log_path().read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 2)
        self.assertEqual(json.loads(lines[0])["observed"], "first observed")
        self.assertEqual(json.loads(lines[1])["observed"], "second observed")

    def test_flag_equals_value_forms_parse(self):
        rc, _ = self._run_main([
            "o", "e",
            "--category=workaround", "--skill=orch-tdd",
            "--ticket=t2-friction-hardening", "--run=20260717T161634Z-adversarial-test-sweep",
        ])
        self.assertEqual(rc, 0)
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(entry["category"], "workaround")
        self.assertEqual(entry["skill"], "orch-tdd")
        self.assertEqual(entry["ticket"], "t2-friction-hardening")
        self.assertEqual(entry["run"], "20260717T161634Z-adversarial-test-sweep")

    def test_mixed_space_and_equals_flag_forms_parse_together(self):
        rc, _ = self._run_main(["o", "e", "--category", "misrouting", "--skill=orch-tdd"])
        self.assertEqual(rc, 0)
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(entry["category"], "misrouting")
        self.assertEqual(entry["skill"], "orch-tdd")

    def test_omitted_category_defaults_to_uncategorized(self):
        rc, _ = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(entry["category"], "uncategorized")
        self.assertIsNone(entry["skill"])

    def test_git_lookup_missing_executable_still_appends_entry(self):
        with mock.patch.object(friction.subprocess, "run", side_effect=FileNotFoundError("git")):
            rc, out = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "friction logged")
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertIsNone(entry["git_rev"])

    def test_git_lookup_timeout_still_appends_entry(self):
        timeout_error = friction.subprocess.TimeoutExpired(cmd="git", timeout=friction.GIT_REV_TIMEOUT_SECONDS)
        with mock.patch.object(friction.subprocess, "run", side_effect=timeout_error):
            rc, out = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        self.assertEqual(out.strip(), "friction logged")
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertIsNone(entry["git_rev"])

    def test_git_lookup_nonzero_exit_yields_none_git_rev(self):
        result = mock.Mock(returncode=1, stdout=b"")
        with mock.patch.object(friction.subprocess, "run", return_value=result):
            rc, _ = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertIsNone(entry["git_rev"])

    def test_a_worktree_and_its_main_checkout_append_to_one_stream(self):
        # Build a linked worktree of a separate main checkout and log from
        # both: one stream, two lines, and no `.orch/` in either tree.
        main = self.tmp / "main-checkout"
        (main / ".git" / "worktrees" / "wt").mkdir(parents=True)
        wt = self.tmp / "wt"
        wt.mkdir()
        (wt / ".git").write_text(
            f"gitdir: {main / '.git' / 'worktrees' / 'wt'}\n", encoding="utf-8"
        )
        os.chdir(main)
        self.assertEqual(0, self._run_main(["from the main checkout", "e"])[0])
        os.chdir(wt)
        self.assertEqual(0, self._run_main(["from the worktree", "e"])[0])
        lines = self._log_path().read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            ["from the main checkout", "from the worktree"],
            [json.loads(line)["observed"] for line in lines],
        )
        self.assertFalse((main / ".orch").exists())
        self.assertFalse((wt / ".orch").exists())

    def test_the_entry_records_the_directory_it_was_logged_from(self):
        # One stream for every repository, so where an entry came from is a
        # field on it, never its location. `cwd` is the literal directory;
        # `TestFrictionProjectFields` owns the identity of it.
        self._run_main(["o", "e"])
        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(str(self.repo), entry["cwd"])


class TestMainMalformedArgvIsSilentNoop(_IsolatedRepoTestCase):
    def _assert_noop(self, argv):
        rc, out = self._run_main(argv)
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")
        self.assertFalse(self._log_path().exists())

    def test_zero_positional_args(self):
        self._assert_noop([])

    def test_one_positional_arg(self):
        self._assert_noop(["only one"])

    def test_three_positional_args(self):
        self._assert_noop(["a", "b", "c"])

    def test_dangling_known_flag_missing_its_value(self):
        self._assert_noop(["o", "e", "--category"])

    def test_unknown_flag_is_absorbed_as_positional_and_rejected(self):
        self._assert_noop(["--bogus", "value", "o", "e"])

    def test_unknown_equals_flag_is_absorbed_as_positional_and_rejected(self):
        self._assert_noop(["--bogus=value", "o", "e"])


class TestMainAdversarialFailuresStaySilentAndExitZero(_IsolatedRepoTestCase):
    def test_unwritable_target_directory(self):
        # Pre-create the sink root as a plain file so mkdir(parents=True)
        # for the friction/ subdirectory raises FileExistsError.
        self.sink.write_text("blocked", encoding="utf-8")
        rc, out = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_an_unwritable_sink_is_never_traded_for_a_writable_cwd(self):
        # There is no fallback at this seam. A blocked sink loses the entry;
        # it does not resurrect the per-repository `.orch/` this run retired.
        self.sink.write_text("blocked", encoding="utf-8")
        before = sorted(p.name for p in self.repo.iterdir())
        self._run_main(["o", "e"])
        self.assertEqual(before, sorted(p.name for p in self.repo.iterdir()))
        self.assertFalse((self.repo / ".orch").exists())

    def test_a_resolver_that_cannot_be_imported_is_swallowed(self):
        # The two-arm import lives inside a function precisely so main()'s
        # broad except can catch its failure. At module scope this would
        # traceback before there was a main() to swallow it.
        with mock.patch.object(
            friction, "_state_root", side_effect=ImportError("no state_root")
        ):
            rc, out = self._run_main(["o", "e"])
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_lone_surrogate_value_does_not_raise_or_corrupt_the_log(self):
        rc, out = self._run_main(["bad \udcff value", "expected"])
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")
        log = self._log_path()
        if log.exists():
            content = log.read_text(encoding="utf-8")
            for line in content.splitlines():
                json.loads(line)  # any line present must be a complete, valid entry


class _ProvenanceTestCase(_IsolatedRepoTestCase):
    """Builders for the three things an entry's provenance is read out of."""

    def repository(self, name: str, origin=None) -> Path:
        """A checkout, optionally with an ``origin`` remote."""

        root = self.tmp / name
        (root / ".git").mkdir(parents=True)
        if origin is not None:
            (root / ".git" / "config").write_text(
                '[core]\n\tbare = false\n[remote "origin"]\n\turl = {0}\n'.format(origin),
                encoding="utf-8",
            )
        return root

    def worktree_of(self, main: Path, name: str) -> Path:
        """A linked worktree: its own workspace, its main checkout's project."""

        (main / ".git" / "worktrees" / name).mkdir(parents=True)
        linked = self.tmp / name
        linked.mkdir()
        (linked / ".git").write_text(
            "gitdir: {0}\n".format(main / ".git" / "worktrees" / name), encoding="utf-8"
        )
        return linked

    def seed_run(self, run: str, project: dict, workspace="/nowhere") -> Path:
        """A run the sink holds, its identity written by the code that owns it.

        Built through ``tickets._identity_document`` and ``_write_identity``
        rather than by hand, so this fixture cannot drift from the document
        the writer really produces.
        """

        run_dir = self.sink / "runs" / run
        run_dir.mkdir(parents=True)
        document, error = tickets._identity_document(
            run,
            run_dir / tickets.RUN_IDENTITY_NAME,
            project,
            workspace,
            friction.datetime.now(friction.timezone.utc),
        )
        self.assertIsNone(error)
        tickets._write_identity(run_dir, document)
        return run_dir

    def last_entry(self) -> dict:
        """The line most recently appended, its provenance keys asserted present.

        Asserted here rather than dereferenced in each case, so an entry
        that simply does not carry these fields reads as the case failing
        rather than as a ``KeyError`` traceback (rules/verification.md §8).
        """

        entry = json.loads(self._log_path().read_text(encoding="utf-8").splitlines()[-1])
        self.assertEqual(
            set(), PROVENANCE_KEYS - set(entry), "entry carries no provenance"
        )
        return entry

    def entry(self, argv) -> dict:
        """Log once and return the line it appended."""

        rc, out = self._run_main(argv)
        self.assertEqual(0, rc)
        self.assertEqual("friction logged", out.strip())
        return self.last_entry()

    def project_of(self, entry: dict) -> dict:
        """The entry's project, asserted to be one before it is read into."""

        project = entry.get("project")
        self.assertIsInstance(project, dict, "entry names no project")
        return project

    def chdir(self, target: Path):
        os.chdir(target)


class TestFrictionProjectFields(_ProvenanceTestCase):
    """One stream serves every project because each entry says which one.

    ``project`` is item 03's rule, called and never restated here; what
    these grade is which of the three questions answered it, and that the
    answer reaches the entry.
    """

    def test_a_run_the_sink_holds_names_the_project(self):
        alpha = {"root": "/elsewhere/alpha", "origin": "https://x/alpha", "name": "alpha"}
        self.seed_run("20260814T000000Z-alpha", alpha)
        entry = self.entry(["o", "e", "--run", "20260814T000000Z-alpha"])
        self.assertEqual(alpha, entry["project"])
        self.assertEqual("run", entry["project_source"])

    def test_without_a_run_the_repository_standing_in_names_the_project(self):
        here = self.repository("beta", origin="git@host:team/beta.git")
        self.chdir(here)
        entry = self.entry(["o", "e"])
        self.assertEqual(
            {"root": str(here), "origin": "git@host:team/beta.git", "name": "beta"},
            entry["project"],
        )
        self.assertEqual("cwd", entry["project_source"])

    def test_outside_any_repository_there_is_no_project(self):
        nowhere = self.tmp / "nowhere"
        nowhere.mkdir()
        self.chdir(nowhere)
        entry = self.entry(["o", "e"])
        self.assertIsNone(entry["project"])
        self.assertEqual("none", entry["project_source"])
        # Still attributable to somewhere: the two location fields stay.
        self.assertEqual(str(nowhere), entry["cwd"])
        self.assertEqual(str(nowhere), entry["workspace"])

    def test_the_workspace_is_the_worktree_and_the_project_is_its_checkout(self):
        main = self.repository("main-checkout", origin="https://x/gamma")
        linked = self.worktree_of(main, "linked")
        self.chdir(linked)
        entry = self.entry(["o", "e"])
        self.assertEqual(str(linked), entry["workspace"])
        self.assertEqual(str(main), self.project_of(entry)["root"])
        self.assertNotEqual(entry["workspace"], self.project_of(entry)["root"])

    def test_four_worktrees_of_one_project_are_one_project_and_four_workspaces(self):
        main = self.repository("shared", origin="https://x/shared")
        trees = [main] + [self.worktree_of(main, "wt{0}".format(n)) for n in range(3)]
        seen = []
        for tree in trees:
            self.chdir(tree)
            seen.append(self.entry(["o", "e"]))
        self.assertEqual([str(tree) for tree in trees], [e["workspace"] for e in seen])
        self.assertEqual([main.name] * 4, [self.project_of(e)["name"] for e in seen])
        self.assertEqual(
            1, len({json.dumps(self.project_of(e), sort_keys=True) for e in seen})
        )

    def test_every_entry_names_the_sink_layout_it_was_written_under(self):
        # The wire value a reader off this machine relies on, and the same
        # value the writer of `run.json` stamps -- pinned together, so the
        # two records of one sink cannot come to disagree about its layout.
        entry = self.entry(["o", "e"])
        self.assertEqual(2, entry["sink_convention"])
        self.assertEqual(tickets.SINK_CONVENTION, entry["sink_convention"])

    def test_a_run_beats_the_repository_it_is_logged_from(self):
        alpha = {"root": "/elsewhere/alpha", "origin": "https://x/alpha", "name": "alpha"}
        self.seed_run("20260814T000000Z-alpha", alpha)
        self.chdir(self.repository("beta", origin="https://x/beta"))
        entry = self.entry(["o", "e", "--run", "20260814T000000Z-alpha"])
        self.assertEqual(alpha, entry["project"])
        self.assertEqual("run", entry["project_source"])
        # ...and the workspace is still the one the entry was logged from.
        self.assertEqual(str(self.tmp / "beta"), entry["workspace"])

    def test_a_run_the_sink_does_not_hold_falls_through_to_the_repository(self):
        here = self.repository("beta", origin="https://x/beta")
        self.chdir(here)
        entry = self.entry(["o", "e", "--run", "20260814T000000Z-never-opened"])
        self.assertEqual(str(here), self.project_of(entry)["root"])
        self.assertEqual("cwd", entry["project_source"])
        self.assertEqual("20260814T000000Z-never-opened", entry["run"])

    def test_an_unreadable_run_identity_falls_through_and_the_entry_lands(self):
        here = self.repository("beta", origin="https://x/beta")
        self.chdir(here)
        broken = {
            "empty": "",
            "truncated": '{"run": "r", "project": {"root": "/a", "orig',
            "not json": "this is not json at all",
            "not an object": '["a", "list"]',
            "no project": '{"run": "r", "sink_convention": 2}',
            "project is not an object": '{"run": "r", "project": "alpha"}',
        }
        for label, text in broken.items():
            with self.subTest(label):
                run = "20260814T000000Z-{0}".format(label.replace(" ", "-"))
                run_dir = self.sink / "runs" / run
                run_dir.mkdir(parents=True)
                (run_dir / tickets.RUN_IDENTITY_NAME).write_text(text, encoding="utf-8")
                entry = self.entry(["o", "e", "--run", run])
                self.assertEqual(str(here), self.project_of(entry)["root"])
                self.assertEqual("cwd", entry["project_source"])

    def test_every_field_the_stream_already_carried_survives(self):
        here = self.repository("beta", origin="https://x/beta")
        self.chdir(here)
        entry = self.entry([
            "observed thing", "expected thing",
            "--category", "contract-gap", "--skill", "orch-tdd",
            "--ticket", "04-friction-project", "--run", "20260814T000000Z-alpha",
        ])
        self.assertEqual(LEGACY_ENTRY_KEYS | PROVENANCE_KEYS, set(entry))
        self.assertEqual("observed thing", entry["observed"])
        self.assertEqual("expected thing", entry["expected"])
        self.assertEqual("contract-gap", entry["category"])
        self.assertEqual("orch-tdd", entry["skill"])
        self.assertEqual("04-friction-project", entry["ticket"])
        self.assertEqual("20260814T000000Z-alpha", entry["run"])
        self.assertEqual(str(here), entry["cwd"])
        self.assertRegex(entry["ts"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
        self.assertIn("git_rev", entry)
        self.assertIn("host", entry)
        self.assertIn("session", entry)

    def test_one_stream_carries_two_projects_distinguished_only_by_the_field(self):
        first = self.repository("alpha", origin="https://x/alpha")
        second = self.repository("beta", origin="https://x/beta")
        for where, observed in ((first, "from alpha"), (second, "from beta")):
            self.chdir(where)
            self._run_main([observed, "e"])
        lines = self._log_path().read_text(encoding="utf-8").splitlines()
        self.assertEqual(2, len(lines))
        entries = [json.loads(line) for line in lines]
        for entry in entries:
            self.assertIsInstance(entry.get("project"), dict, "no project on the entry")
        self.assertEqual(
            ["https://x/alpha", "https://x/beta"],
            [e["project"]["origin"] for e in entries],
        )
        # One file, one month, one stream: the location says nothing about
        # which project, and the field says everything.
        self.assertEqual(
            [self._log_path()], sorted((self.sink / "friction").iterdir())
        )


class TestFrictionNeverFails(_ProvenanceTestCase):
    """Every field added here is a new way to fail inside a script that cannot.

    Each case breaks one resolution and asserts the cost is that field,
    that the process exits 0, that nothing is printed on failure and
    exactly ``friction logged`` on success, and that stderr carries no
    traceback.
    """

    def _run_main_capturing_stderr(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = friction.main(argv)
        return rc, out.getvalue(), err.getvalue()

    def test_an_unwritable_sink_root_loses_the_entry_and_exits_zero(self):
        if os.name == "nt" or os.getuid() == 0:  # pragma: no cover - platform
            self.skipTest("directory mode is not a write barrier here")
        self.sink.mkdir(parents=True)
        self.sink.chmod(stat.S_IRUSR | stat.S_IXUSR)
        self.addCleanup(self.sink.chmod, stat.S_IRWXU)
        rc, out, err = self._run_main_capturing_stderr(["o", "e"])
        self.assertEqual(0, rc)
        self.assertEqual("", out)
        self.assertEqual("", err)

    def test_a_sink_root_whose_parent_is_a_regular_file(self):
        blocker = self.tmp / "blocker"
        blocker.write_text("not a directory", encoding="utf-8")
        os.environ[STATE_HOME_ENV_VAR] = str(blocker / "sink")
        rc, out, err = self._run_main_capturing_stderr(["o", "e"])
        self.assertEqual(0, rc)
        self.assertEqual("", out)
        self.assertEqual("", err)

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
                self.assertEqual(LEGACY_ENTRY_KEYS | PROVENANCE_KEYS, set(entry))

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


class TestFrictionAppendStaysOneCall(_ProvenanceTestCase):
    """Concurrent loggers share this file, so the write stays append-only.

    Read-modify-write would let two loggers racing on one month's stream
    lose each other's lines. The property is structural, so it is asserted
    against the source rather than inferred from a timing test.
    """

    def _source(self):
        return ast.parse((ROOT / "scripts" / "friction.py").read_text(encoding="utf-8"))

    def test_the_stream_is_opened_once_in_append_mode(self):
        opens = [
            node for node in ast.walk(self._source())
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "open"
        ]
        self.assertEqual(1, len(opens))
        modes = [arg.value for arg in opens[0].args[1:2]] + [
            keyword.value.value for keyword in opens[0].keywords
            if keyword.arg == "mode"
        ]
        self.assertEqual(["a"], modes)

    def test_the_entry_reaches_the_stream_in_one_write(self):
        writes = [
            node for node in ast.walk(self._source())
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "write"
        ]
        self.assertEqual(1, len(writes))
        self.assertEqual(1, len(writes[0].args))

    def test_three_loggers_in_one_month_leave_three_whole_lines(self):
        for where in ("alpha", "beta", "gamma"):
            self.chdir(self.repository(where, origin="https://x/{0}".format(where)))
            self._run_main(["from {0}".format(where), "e"])
        lines = self._log_path().read_text(encoding="utf-8").splitlines()
        self.assertEqual(
            ["from alpha", "from beta", "from gamma"],
            [json.loads(line)["observed"] for line in lines],
        )


if __name__ == "__main__":
    unittest.main()
