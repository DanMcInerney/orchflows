"""Tests for tools/suite_check.py — the mechanical suite-guard harness.

Exercises the pure functions (skip-audit parsing, snapshot diffing,
stripped-PATH construction) against synthetic input and temp trees.
At most one test invokes the harness as a subprocess, against a tiny
synthetic ``tests/`` directory in a tempdir — never the real suite.
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

from tools import suite_check  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
