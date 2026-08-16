"""Tests for the two pre-push harnesses: suite_check.py and preflight.py.

Exercises the pure functions (skip-audit parsing, snapshot diffing,
stripped-PATH construction, the CI matrix read and the interpreter
lookup) against synthetic input and temp trees. At most one test invokes
a harness as a subprocess, against a tiny synthetic ``tests/`` directory
in a tempdir — never the real suite, and never a second interpreter.

``tools/preflight.py`` is here rather than in a module of its own
because both files answer one question — what a local green covers and
what it does not — and a claim about coverage is asserted against
whichever of them makes it.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from tools import preflight, suite_check  # noqa: E402


class TestAuditSkips(unittest.TestCase):
    def test_skip_with_reason_is_clean(self):
        output = "test_x (tests.test_y.TestY) ... skipped 'windows only'\nOK\n"
        self.assertEqual(suite_check.audit_skips(output), [])

    def test_skip_without_reason_is_named(self):
        output = "test_x (tests.test_y.TestY) ... skipped ''\nOK\n"
        violations = suite_check.audit_skips(output)
        self.assertEqual(violations, ["test_x (tests.test_y.TestY)"])

    def test_skip_with_whitespace_only_reason_is_named(self):
        output = "test_x (tests.test_y.TestY) ... skipped '   '\n"
        violations = suite_check.audit_skips(output)
        self.assertEqual(violations, ["test_x (tests.test_y.TestY)"])

    def test_expected_failure_is_not_a_skip(self):
        output = "test_x (tests.test_y.TestY) ... expected failure\nOK\n"
        self.assertEqual(suite_check.audit_skips(output), [])

    def test_multiple_skips_all_named(self):
        output = (
            "test_a (m.A) ... skipped 'ok reason'\n"
            "test_b (m.B) ... skipped ''\n"
            "test_c (m.C) ... ok\n"
            "test_d (m.D) ... skipped \"\"\n"
        )
        violations = suite_check.audit_skips(output)
        self.assertEqual(violations, ["test_b (m.B)", "test_d (m.D)"])

    def test_no_skips_returns_empty(self):
        output = "test_a (m.A) ... ok\ntest_b (m.B) ... ok\n\nOK\n"
        self.assertEqual(suite_check.audit_skips(output), [])


class TestHashAndSnapshot(unittest.TestCase):
    def test_collect_snapshot_watches_relocated_host_config_dirs(self):
        # A leak into a relocated config dir is the same leak; the guard must
        # follow CLAUDE_CONFIG_DIR / CODEX_HOME or report a clean tree that isn't.
        for env_var, tree_name in (
            ("CLAUDE_CONFIG_DIR", "claude_home"),
            ("CODEX_HOME", "codex_home"),
        ):
            with self.subTest(env_var=env_var), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                config_dir = root / "elsewhere" / tree_name
                (config_dir / "skills").mkdir(parents=True)
                (config_dir / "skills" / "SKILL.md").write_text("leaked\n", encoding="utf-8")

                with mock.patch.dict(os.environ, {env_var: str(config_dir)}):
                    snapshot = suite_check.collect_snapshot(root, root / "home", watch_home=True)

                self.assertIn(str(Path("skills") / "SKILL.md"), snapshot["trees"][tree_name])

    def test_the_sink_is_watched_under_its_own_name_wherever_it_points(self):
        # ~/.orchflows is watched already, so a default sink is covered by
        # that tree. A redirected one is not — and a suite that redirects is
        # exactly when a stray write is most likely.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            sink = root / "elsewhere" / "sink"
            (sink / "runs" / "somerun").mkdir(parents=True)
            (sink / "runs" / "somerun" / "worklog.md").write_text("x\n", encoding="utf-8")
            with mock.patch.dict(
                os.environ, {suite_check.STATE_HOME_ENV_VAR: str(sink)}
            ):
                watched = suite_check.collect_snapshot(root, root / "home", watch_home=True)
                # the sink guard is not part of the home watch, so
                # --no-home-watch cannot switch it off
                unwatched = suite_check.collect_snapshot(root, root / "home", watch_home=False)
        expected = str(Path("runs") / "somerun" / "worklog.md")
        self.assertIn(expected, watched["trees"]["state_sink"])
        self.assertIn(expected, unwatched["trees"]["state_sink"])

    def test_the_sink_root_it_watches_is_the_one_the_scripts_resolve(self):
        """``suite_check.py`` cannot import ``scripts/state_root.py``: it must
        watch the sink the suite's interpreter resolves even against a tree
        that has no such module. That duplication is only safe while the two
        spellings agree."""

        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        try:
            import state_root
        finally:
            sys.path.pop(0)
        self.assertEqual(state_root.ENV_VAR, suite_check.STATE_HOME_ENV_VAR)
        self.assertEqual(state_root.DEFAULT_HOME_SUBPATH, suite_check.STATE_HOME_SUBPATH)
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop(suite_check.STATE_HOME_ENV_VAR, None)
                self.assertEqual(
                    home / ".orchflows" / "state", suite_check.state_sink_dir(home)
                )
            for blank in ("", "   "):
                with mock.patch.dict(
                    os.environ, {suite_check.STATE_HOME_ENV_VAR: blank}
                ):
                    self.assertEqual(
                        home / ".orchflows" / "state",
                        suite_check.state_sink_dir(home),
                        blank,
                    )
            with mock.patch.dict(
                os.environ, {suite_check.STATE_HOME_ENV_VAR: "~/redirected"}
            ):
                self.assertEqual(
                    Path.home() / "redirected", suite_check.state_sink_dir(home)
                )

    def test_hash_file_changes_with_content(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "a.jsonl"
            path.write_text("one\n", encoding="utf-8")
            before = suite_check.hash_file(path)
            path.write_text("two\n", encoding="utf-8")
            after = suite_check.hash_file(path)
            self.assertNotEqual(before, after)

    def test_snapshot_friction_hashes_empty_dir(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            self.assertEqual(suite_check.snapshot_friction_hashes(repo_root), {})

    def test_snapshot_friction_hashes_finds_jsonl_files(self):
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td)
            friction_dir = repo_root / ".orch" / "friction"
            friction_dir.mkdir(parents=True)
            (friction_dir / "2026-07.jsonl").write_text('{"x": 1}\n', encoding="utf-8")
            snap = suite_check.snapshot_friction_hashes(repo_root)
            key = str(Path(".orch") / "friction" / "2026-07.jsonl")
            self.assertIn(key, snap)
            self.assertEqual(len(snap[key]), 64)

    def test_snapshot_tree_missing_root_is_empty(self):
        with tempfile.TemporaryDirectory() as td:
            missing = Path(td) / "does-not-exist"
            self.assertEqual(suite_check.snapshot_tree(missing), {})

    def test_snapshot_tree_lists_files_and_dirs(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "watched"
            (root / "sub").mkdir(parents=True)
            (root / "sub" / "f.txt").write_text("hello", encoding="utf-8")
            snap = suite_check.snapshot_tree(root)
            self.assertEqual(snap.get("sub"), "dir")
            self.assertEqual(snap.get(str(Path("sub") / "f.txt")), "file:5")

    def test_snapshot_tree_does_not_follow_junction_out_of_root(self):
        # A junction inside a watched tree can point anywhere on the
        # filesystem (e.g. a pnpm/rush build-path-shortener junction).
        # Walking into it must not escape `root` or crash `relative_to`.
        # Junctions exist only on Windows, and `cmd` is not on PATH
        # anywhere else -- the POSIX half of this property is covered by
        # the symlink test below, which runs everywhere.
        if os.name != "nt":
            self.skipTest("junctions are Windows-only; see the symlink test for POSIX")
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "watched"
            root.mkdir()
            escape_target = Path(td) / "escape"
            escape_target.mkdir()
            (escape_target / "secret.txt").write_text("outside", encoding="utf-8")
            junction = root / "link"
            result = subprocess.run(
                ["cmd", "/c", "mklink", "/J", str(junction), str(escape_target)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                self.skipTest("mklink /J unavailable on this host: " + result.stderr.strip())
            snap = suite_check.snapshot_tree(root)
            self.assertIn("link", snap)
            self.assertNotEqual(snap["link"], "dir")
            self.assertNotIn(str(Path("link") / "secret.txt"), snap)

    def test_snapshot_tree_does_not_follow_symlink_out_of_root(self):
        # The same property as the junction test above, on the side of the
        # `_is_link_like` branch that POSIX can reach: a link is recorded
        # as `link`, never as `dir`, and nothing behind it enters the
        # snapshot. Without this the escape guard is untested on every
        # non-Windows host.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "watched"
            root.mkdir()
            escape_target = Path(td) / "escape"
            escape_target.mkdir()
            (escape_target / "secret.txt").write_text("outside", encoding="utf-8")
            link = root / "link"
            try:
                link.symlink_to(escape_target, target_is_directory=True)
            except (OSError, NotImplementedError) as error:
                # Windows only permits this under Developer Mode or admin.
                self.skipTest("cannot create a directory symlink here: %s" % error)
            snap = suite_check.snapshot_tree(root)
            self.assertIn("link", snap)
            self.assertNotEqual(snap["link"], "dir")
            self.assertNotIn(str(Path("link") / "secret.txt"), snap)


class TestDiffSnapshots(unittest.TestCase):
    def test_every_kind_of_difference_is_named_and_sameness_is_clean(self):
        cases = (
            ("no change", {"a": "file:1", "b": "dir"}, {"a": "file:1", "b": "dir"}, []),
            ("added", {"a": "file:1"}, {"a": "file:1", "b": "file:2"}, ["orch: added b"]),
            ("removed", {"a": "file:1", "b": "file:2"}, {"a": "file:1"}, ["orch: removed b"]),
            ("changed", {"a": "file:1"}, {"a": "file:2"}, ["orch: changed a"]),
        )
        for kind, before, after, expected in cases:
            with self.subTest(kind=kind):
                self.assertEqual(suite_check.diff_snapshots(before, after, "orch"), expected)

    def test_added_only_ignores_removed_and_changed_but_flags_added(self):
        before = {"a": "file:1", "b": "file:2"}
        after = {"a": "file:9", "c": "file:3"}
        problems = suite_check.diff_snapshots(before, after, "orch", added_only=True)
        self.assertEqual(problems, ["orch: added c"])

    def test_full_snapshot_trees_are_added_only_but_friction_is_byte_identical(self):
        # A watched tree's existing file may grow (the live session's own
        # transcript) without a violation; the friction hash may not.
        before = {
            "friction_hashes": {"2026-07.jsonl": "aaa"},
            "trees": {"claude_home": {"projects/session.jsonl": "file:10"}},
        }
        after = {
            "friction_hashes": {"2026-07.jsonl": "bbb"},
            "trees": {"claude_home": {"projects/session.jsonl": "file:99"}},
        }
        problems = suite_check.diff_full_snapshot(before, after)
        self.assertEqual(problems, ["friction: changed 2026-07.jsonl"])


class TestBuildStrippedPath(unittest.TestCase):
    def test_contains_executable_directory(self):
        with tempfile.TemporaryDirectory() as td:
            exe_dir = Path(td) / "cpython-3.12"
            exe_dir.mkdir()
            exe = exe_dir / "python.exe"
            exe.write_text("", encoding="utf-8")
            path = suite_check.build_stripped_path(str(exe))
            entries = path.split(suite_check.os.pathsep)
            self.assertIn(str(exe_dir.resolve()), entries)

    def test_includes_scripts_sibling_when_present(self):
        with tempfile.TemporaryDirectory() as td:
            exe_dir = Path(td) / "cpython-3.12"
            (exe_dir / "Scripts").mkdir(parents=True)
            exe = exe_dir / "python.exe"
            exe.write_text("", encoding="utf-8")
            path = suite_check.build_stripped_path(str(exe))
            entries = path.split(suite_check.os.pathsep)
            self.assertIn(str((exe_dir / "Scripts").resolve()), entries)

    def test_omits_scripts_sibling_when_absent(self):
        with tempfile.TemporaryDirectory() as td:
            exe_dir = Path(td) / "venv-bin"
            exe_dir.mkdir()
            exe = exe_dir / "python3"
            exe.write_text("", encoding="utf-8")
            path = suite_check.build_stripped_path(str(exe))
            entries = path.split(suite_check.os.pathsep)
            self.assertEqual(entries, [str(exe_dir.resolve())])


class TestSnapshotDocstring(unittest.TestCase):
    """The docstring promises what ``diff_full_snapshot`` delivers.

    The two disagreed: the docstring said the guard fails "on any
    difference" while every watched tree is diffed ``added_only``, so a
    changed or removed entry is no failure and the sentence over-promised
    a guard nobody had. The tests above pin the code's direction —
    additions in the trees, byte-identity in the friction streams — and
    a claim a test contradicts is the half that moves.
    """

    def test_a_changed_entry_in_a_watched_tree_is_no_failure(self):
        problems = suite_check.diff_full_snapshot(
            {"friction_hashes": {}, "trees": {"orch": {"a": "file:1"}}},
            {"friction_hashes": {}, "trees": {"orch": {"a": "file:2"}}},
        )
        self.assertEqual(problems, [])

    def test_the_docstring_claims_additions_and_never_any_difference(self):
        clause = " ".join(suite_check.__doc__.split())
        self.assertNotIn("failing on any difference", clause)
        self.assertIn("failing on any entry a run adds", clause)


class TestPreflightMatrix(unittest.TestCase):
    """A matrix that cannot be read is a refusal, never a covered run.

    ``()`` is the answer "CI runs no interpreter", and the summary reads
    it as "CI interpreter cells covered locally: 0 of 0" followed by OK
    and exit 0 — a preflight reporting complete coverage of nothing,
    which is the one claim this tool exists to make truthfully.
    """

    def _workflow(self, text=None):
        """A temporary workflow file, or a path where none exists."""

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "checks.yml"
        if text is not None:
            path.write_text(text, encoding="utf-8")
        return mock.patch.object(preflight, "WORKFLOW", path)

    def test_the_repositorys_own_matrix_is_read_rather_than_restated(self):
        self.assertTrue(preflight.ci_minors())
        self.assertTrue(preflight.ci_os_cells())

    def test_a_workflow_that_cannot_be_read_refuses(self):
        with self._workflow():
            with self.assertRaises(preflight.MatrixUnreadable):
                preflight.ci_minors()

    def test_a_reshaped_matrix_refuses_the_same_way(self):
        with self._workflow("jobs:\n  checks:\n    runs-on: ubuntu-latest\n"):
            for read in (preflight.ci_minors, preflight.ci_os_cells):
                with self.subTest(read=read.__name__):
                    with self.assertRaises(preflight.MatrixUnreadable):
                        read()

    def test_an_empty_axis_is_no_axis(self):
        with self._workflow("        os: []\n        python-version: []\n"):
            for read in (preflight.ci_minors, preflight.ci_os_cells):
                with self.subTest(read=read.__name__):
                    with self.assertRaises(preflight.MatrixUnreadable):
                        read()

    def test_main_refuses_before_running_anything(self):
        with self._workflow():
            with mock.patch.object(preflight, "run_one") as ran:
                with self.assertRaises(SystemExit) as raised:
                    preflight.main([])
        self.assertEqual(ran.call_count, 0)
        self.assertIn("preflight", str(raised.exception.code))
        self.assertNotIn("OK", str(raised.exception.code))


class TestPreflightOsLine(unittest.TestCase):
    """The OS line names this host's cell, and it is read from the matrix.

    Hardcoded, it printed "1 of 3 -- windows and linux stay CI's" on a
    Windows host: the one cell the run covered named as one of the two it
    did not, and a count restated beside a matrix that decides it.
    """

    CELLS = ("ubuntu-latest", "macos-latest", "windows-latest")

    def _line(self, platform):
        with mock.patch.object(preflight.sys, "platform", platform):
            return preflight.os_coverage_line(self.CELLS)

    def test_each_platform_covers_its_own_cell_and_no_other(self):
        for platform, cell in (
            ("win32", "windows-latest"),
            ("linux", "ubuntu-latest"),
            ("darwin", "macos-latest"),
        ):
            with self.subTest(platform=platform):
                line = self._line(platform)
                covered, _, uncovered = line.partition("--")
                self.assertIn("1 of 3", covered)
                self.assertIn(cell, covered)
                self.assertNotIn(cell, uncovered)
                for other in self.CELLS:
                    if other != cell:
                        self.assertIn(other, uncovered)

    def test_a_platform_the_matrix_does_not_run_covers_no_cell(self):
        line = self._line("freebsd14")
        self.assertIn("0 of 3", line)
        self.assertIn("freebsd14", line)


class TestPreflightWhich(unittest.TestCase):
    """``python3.13`` on Windows is ``python3.13.exe``.

    Without PATHEXT the bare-name test finds no file, every CI interpreter
    reads as "not installed here", and preflight prints that false cause
    as the reason a cell stays CI's.
    """

    def _path(self, directory):
        return mock.patch.dict(
            os.environ, {"PATH": str(directory), "PATHEXT": ".COM;.EXE;.BAT"}
        )

    def test_an_extension_the_host_appends_is_found(self):
        if os.name != "nt":
            self.skipTest("PATHEXT is Windows-only; the bare name is found below")
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            (directory / "python3.13.exe").write_text("", encoding="utf-8")
            with self._path(directory):
                found = preflight._which("python3.13")
            # The extension is spelled as PATHEXT spells it, and a Windows
            # path is case-insensitive: the claim is the file, not its case.
            self.assertTrue(found and Path(found).is_file(), found)
            self.assertEqual(Path(found).name.lower(), "python3.13.exe")

    def test_a_bare_name_is_still_found_wherever_it_is_the_whole_name(self):
        with tempfile.TemporaryDirectory() as td:
            directory = Path(td)
            executable = directory / "python3.13"
            executable.write_text("", encoding="utf-8")
            executable.chmod(0o755)
            with self._path(directory):
                self.assertEqual(preflight._which("python3.13"), str(executable))

    def test_a_name_on_no_path_entry_is_still_absent(self):
        with tempfile.TemporaryDirectory() as td:
            with self._path(Path(td)):
                self.assertIsNone(preflight._which("python3.13"))


class TestHarnessSubprocess(unittest.TestCase):
    """The one permitted subprocess test: a tiny synthetic tests/ dir."""

    def _write_tests_dir(self, root: Path, passing: bool) -> None:
        tests_dir = root / "tests"
        tests_dir.mkdir(parents=True)
        (tests_dir / "__init__.py").write_text("", encoding="utf-8")
        if passing:
            body = textwrap.dedent(
                """
                import unittest

                class TestTiny(unittest.TestCase):
                    def test_ok(self):
                        self.assertTrue(True)
                """
            )
        else:
            body = textwrap.dedent(
                """
                import unittest

                class TestTiny(unittest.TestCase):
                    def test_fails(self):
                        self.assertTrue(False)
                """
            )
        (tests_dir / "test_tiny.py").write_text(body, encoding="utf-8")

    def test_harness_end_to_end_against_synthetic_suite(self):
        harness = REPO_ROOT / "tools" / "suite_check.py"
        with tempfile.TemporaryDirectory() as td_pass, tempfile.TemporaryDirectory() as td_fail:
            pass_root = Path(td_pass)
            self._write_tests_dir(pass_root, passing=True)
            result = subprocess.run(
                [
                    sys.executable,
                    str(harness),
                    "--repo-root",
                    str(pass_root),
                    "--python",
                    sys.executable,
                    "--no-home-watch",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            verdict = json.loads(result.stdout.strip().splitlines()[-1])
            self.assertTrue(verdict["ok"])
            self.assertIn("phases", verdict)
            self.assertIn("suite", verdict["phases"])
            self.assertIn("snapshot", verdict["phases"])
            self.assertIn("stripped_path", verdict["phases"])

            fail_root = Path(td_fail)
            self._write_tests_dir(fail_root, passing=False)
            result = subprocess.run(
                [
                    sys.executable,
                    str(harness),
                    "--repo-root",
                    str(fail_root),
                    "--python",
                    sys.executable,
                    "--no-home-watch",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            verdict = json.loads(result.stdout.strip().splitlines()[-1])
            self.assertFalse(verdict["ok"])
            self.assertIn("failures", verdict)
            self.assertTrue(verdict["failures"])

    def test_a_stray_write_into_the_sink_fails_the_run(self):
        """The guard behind ``tests/__init__.py``: a suite that redirects the
        sink for its own children still must not write to the root it was
        given. Both halves of the seam are exercised — a test that writes
        in-process, and a test whose subprocess inherits the variable and
        writes there — because a guard that catches only one is no guard.
        """

        harness = REPO_ROOT / "tools" / "suite_check.py"
        for who, body in (
            (
                "in_process",
                """
                import os, pathlib, unittest

                class TestStray(unittest.TestCase):
                    def test_writes_into_the_sink(self):
                        sink = pathlib.Path(os.environ["ORCHFLOWS_STATE_HOME"])
                        (sink / "runs" / "leaked").mkdir(parents=True, exist_ok=True)
                        (sink / "runs" / "leaked" / "worklog.md").write_text("x\\n")
                """,
            ),
            (
                "subprocess",
                """
                import os, subprocess, sys, unittest

                class TestStray(unittest.TestCase):
                    def test_a_child_writes_into_the_inherited_sink(self):
                        program = (
                            "import os, pathlib;"
                            "s = pathlib.Path(os.environ['ORCHFLOWS_STATE_HOME']);"
                            "d = s / 'friction';"
                            "d.mkdir(parents=True, exist_ok=True);"
                            "(d / '2026-08.jsonl').write_text('{}\\\\n')"
                        )
                        # no env= : the child inherits, which is the point
                        done = subprocess.run([sys.executable, "-c", program])
                        self.assertEqual(0, done.returncode)
                """,
            ),
        ):
            with self.subTest(who=who), tempfile.TemporaryDirectory() as td:
                root = Path(td)
                tests_dir = root / "tests"
                tests_dir.mkdir(parents=True)
                (tests_dir / "__init__.py").write_text("", encoding="utf-8")
                (tests_dir / "test_stray.py").write_text(
                    textwrap.dedent(body), encoding="utf-8"
                )
                sink = root / "stand-in-sink"
                sink.mkdir()
                env = dict(os.environ, ORCHFLOWS_STATE_HOME=str(sink))
                result = subprocess.run(
                    [
                        sys.executable, str(harness),
                        "--repo-root", str(root),
                        "--python", sys.executable,
                        "--no-home-watch",
                    ],
                    capture_output=True, text=True, timeout=120, env=env,
                )
                verdict = json.loads(result.stdout.strip().splitlines()[-1])
                # the suite itself passed: only the snapshot caught this
                self.assertTrue(verdict["phases"]["suite"]["ok"], result.stdout)
                self.assertFalse(verdict["phases"]["snapshot"]["ok"], result.stdout)
                self.assertFalse(verdict["ok"])
                self.assertEqual(1, result.returncode)
                self.assertTrue(
                    [f for f in verdict["failures"] if f.startswith("state_sink: added ")],
                    verdict["failures"],
                )


if __name__ == "__main__":
    unittest.main()
