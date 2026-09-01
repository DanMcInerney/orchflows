"""Snapshot collection and comparison cases for the suite harness."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tools import suite_check

REPO_ROOT = Path(__file__).resolve().parents[2]


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
                os.environ, {suite_check._bootstrap.ENV_VAR: str(sink)}
            ):
                watched = suite_check.collect_snapshot(root, root / "home", watch_home=True)
                # the sink guard is not part of the home watch, so
                # --no-home-watch cannot switch it off
                unwatched = suite_check.collect_snapshot(root, root / "home", watch_home=False)
        expected = str(Path("runs") / "somerun" / "worklog.md")
        self.assertIn(expected, watched["trees"]["state_sink"])
        self.assertIn(expected, unwatched["trees"]["state_sink"])

    def test_the_sink_root_it_watches_is_the_one_the_scripts_resolve(self):
        """``suite_check.py`` imports ``scripts/_bootstrap.py`` (never
        ``scripts/state_root.py``: it must watch the sink the suite's
        interpreter resolves even against a tree that has no such
        module) for the env-var name; ``STATE_HOME_SUBPATH`` still
        mirrors ``state_root.DEFAULT_HOME_SUBPATH`` independently, the
        installer's seeding default duplicated for the same reason."""

        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        try:
            import state_root
        finally:
            sys.path.pop(0)
        self.assertEqual(state_root.ENV_VAR, suite_check._bootstrap.ENV_VAR)
        self.assertEqual(state_root.DEFAULT_HOME_SUBPATH, suite_check.STATE_HOME_SUBPATH)
        with tempfile.TemporaryDirectory() as td:
            home = Path(td)
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop(suite_check._bootstrap.ENV_VAR, None)
                self.assertEqual(
                    home / ".orchflows" / "state", suite_check.state_sink_dir(home)
                )
            for blank in ("", "   "):
                with mock.patch.dict(
                    os.environ, {suite_check._bootstrap.ENV_VAR: blank}
                ):
                    self.assertEqual(
                        home / ".orchflows" / "state",
                        suite_check.state_sink_dir(home),
                        blank,
                    )
            with mock.patch.dict(
                os.environ, {suite_check._bootstrap.ENV_VAR: "~/redirected"}
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


class TestSnapshotDirection(unittest.TestCase):
    """``diff_full_snapshot`` fails on additions, not tree changes."""

    def test_a_changed_entry_in_a_watched_tree_is_no_failure(self):
        problems = suite_check.diff_full_snapshot(
            {"friction_hashes": {}, "trees": {"orch": {"a": "file:1"}}},
            {"friction_hashes": {}, "trees": {"orch": {"a": "file:2"}}},
        )
        self.assertEqual(problems, [])

    def test_an_added_entry_in_a_watched_tree_is_a_failure(self):
        problems = suite_check.diff_full_snapshot(
            {"friction_hashes": {}, "trees": {"orch": {"a": "file:1"}}},
            {"friction_hashes": {}, "trees": {"orch": {"a": "file:1", "b": "file:1"}}},
        )
        self.assertTrue(problems)
