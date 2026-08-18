"""Apply-seam migrate-state regression cases."""
from __future__ import annotations

import json
import os
import stat

from .common import (
    LEGACY_KEYS,
    MigrationCase,
    legacy_entry,
    lines_of,
    make_repo,
    migrate_state,
    sink_bytes,
    tickets,
    tree_state,
    write,
)


class TestMigrationIdempotent(MigrationCase):
    """A second pass is empty and source files are never changed."""

    def build_source(self):
        root = self.source_root("alpha", origin="git@github.com:acme/alpha.git")
        write(root / "runs" / "20260101T000000Z-a" / "worklog.md", "# a\n\nnote\n")
        write(root / "runs" / "20260101T000000Z-a" / "run.json",
              json.dumps({"run": "20260101T000000Z-a", "sink_convention": 2}) + "\n")
        write(root / "tickets" / "20260101T000000Z-a" / "01-thing.md", "---\nid: 01\n---\n")
        write(root / "friction" / "2026-01.jsonl",
              legacy_entry(root.parent, "one") + "\n" + legacy_entry(root.parent, "two") + "\n")
        write(root / "improvement" / "proposals" / "2026-01-01-slug.md", "# proposal\n")
        write(root / "improvement" / "covered.jsonl",
              json.dumps({"cluster": "c1", "watermark": "2026-01-01"}) + "\n")
        return root

    def test_a_second_run_changes_nothing_and_plans_nothing(self):
        root = self.build_source()

        first = self.migrate(root)
        after_one = sink_bytes(self.sink)
        self.assertTrue(first["plan"], "the first run planned nothing at all")

        second = self.migrate(root)
        after_two = sink_bytes(self.sink)

        self.assertEqual(after_one, after_two)
        self.assertEqual(second["plan"], [])
        self.assertEqual(second["sources"][0]["friction"]["write"], 0)
        self.assertEqual(second["sources"][0]["friction"]["duplicates"], 2)
        self.assertEqual(second["sources"][0]["runs"]["files"], 0)
        self.assertEqual(second["sources"][0]["runs"]["existing"], 2)
        self.assertEqual(second["sources"][0]["differing"], [])

    def test_every_source_file_is_byte_unchanged_after_both_runs(self):
        root = self.build_source()
        before = tree_state(root)
        self.assertTrue(before, "the fixture source is empty")

        self.migrate(root)
        self.assertEqual(tree_state(root), before)
        self.migrate(root)
        self.assertEqual(tree_state(root), before)

    def test_a_read_only_source_still_migrates(self):
        """A source that denies writes proves copying rather than moving."""

        if os.name == "nt":  # pragma: no cover - POSIX mode bits only
            self.skipTest("directory write permission is not enforced this way on Windows")
        root = self.build_source()
        directories = [path for path in root.rglob("*") if path.is_dir()] + [root]
        modes = {path: path.stat().st_mode for path in directories}

        def restore():
            for path, mode in modes.items():
                path.chmod(mode)

        self.addCleanup(restore)
        for path in sorted(directories, reverse=True):
            path.chmod(stat.S_IRUSR | stat.S_IXUSR)

        report = self.migrate(root)
        self.assertEqual(report["errors"], [])
        self.assertTrue((self.sink / "runs" / "20260101T000000Z-a" / "worklog.md").is_file())
        self.assertEqual(
            lines_of(self.sink / "friction" / "2026-01.jsonl").__len__(), 2
        )


class TestLegacyFriction(MigrationCase):
    """Legacy entries are migrated without losing their original shape."""

    def build_source(self):
        self.repo = make_repo(self.home / "beta", origin="git@github.com:acme/beta.git")
        root = self.repo / ".orch"
        self.gone = self.home / "deleted-checkout"
        known = legacy_entry(self.repo, "resolvable")
        write(root / "friction" / "2026-02.jsonl", "\n".join([
            known,
            known,
            legacy_entry(self.gone, "vanished"),
            "{not json at all",
        ]) + "\n")
        return root

    def test_a_live_cwd_is_backfilled_and_the_duplicate_lands_once(self):
        root = self.build_source()
        self.migrate(root)

        lines = lines_of(self.sink / "friction" / "2026-02.jsonl")
        resolvable = [json.loads(line) for line in lines
                      if line.startswith("{") and "resolvable" in line]
        self.assertEqual(len(resolvable), 1, lines)
        entry = resolvable[0]
        self.assertEqual(entry.get("project"), {
            "root": str(self.repo),
            "origin": "git@github.com:acme/beta.git",
            "name": "beta",
        })
        self.assertEqual(entry.get("project_source"), "cwd")

    def test_a_vanished_cwd_keeps_a_null_project_and_says_why(self):
        root = self.build_source()
        self.migrate(root)

        entry = next(json.loads(line)
                     for line in lines_of(self.sink / "friction" / "2026-02.jsonl")
                     if line.startswith("{") and "vanished" in line)
        self.assertIsNone(entry["project"])
        self.assertEqual(entry["project_source"], "none")
        self.assertFalse(self.gone.exists(), "the fixture's vanished cwd must not exist")

    def test_a_line_that_is_not_json_is_carried_across_unaltered(self):
        root = self.build_source()
        report = self.migrate(root)

        lines = lines_of(self.sink / "friction" / "2026-02.jsonl")
        self.assertIn("{not json at all", lines)
        self.assertEqual(report["sources"][0]["friction"]["unparsed"], 1)

    def test_every_migrated_entry_is_stamped_and_says_where_it_came_from(self):
        root = self.build_source()
        self.migrate(root)

        for line in lines_of(self.sink / "friction" / "2026-02.jsonl"):
            if not line.startswith("{") or "not json" in line:
                continue
            entry = json.loads(line)
            self.assertEqual(entry["sink_convention"], 1, line)
            self.assertEqual(entry["migrated_from"], str(root), line)
            for key in LEGACY_KEYS:
                self.assertIn(key, entry, f"{key} was dropped from {line}")

    def test_an_entry_that_already_names_its_convention_keeps_it(self):
        root = self.source_root("gamma")
        live = json.loads(legacy_entry(root.parent, "already current"))
        live.update({"sink_convention": tickets.SINK_CONVENTION,
                     "project": {"root": "/elsewhere", "origin": None, "name": "elsewhere"},
                     "project_source": "run"})
        write(root / "friction" / "2026-03.jsonl", json.dumps(live) + "\n")

        self.migrate(root)
        month = self.sink / "friction" / "2026-03.jsonl"
        self.assertTrue(month.is_file(), "the month file never reached the sink")
        entry = json.loads(lines_of(month)[0])
        self.assertEqual(entry.get("sink_convention"), tickets.SINK_CONVENTION)
        self.assertEqual(entry.get("project"),
                         {"root": "/elsewhere", "origin": None, "name": "elsewhere"})
        self.assertEqual(entry.get("project_source"), "run")
        self.assertEqual(entry.get("migrated_from"), str(root))

    def test_both_conventions_read_as_one_stream(self):
        root = self.build_source()
        self.migrate(root)
        month = self.sink / "friction" / "2026-02.jsonl"
        live = json.loads(legacy_entry(self.repo, "written after migration"))
        live.update({"sink_convention": tickets.SINK_CONVENTION,
                     "project": {"root": str(self.repo), "origin": None, "name": "beta"},
                     "project_source": "cwd"})
        with open(month, "a", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(live) + "\n")

        stream = lines_of(month)
        conventions, answered = set(), 0
        for line in stream:
            if line == "{not json at all":
                continue
            entry = json.loads(line)
            conventions.add(entry["sink_convention"])
            self.assertIn("project", entry, line)
            self.assertIn(entry["project_source"], ("cwd", "run", "none"), line)
            answered += 1
        self.assertEqual(conventions, {1, tickets.SINK_CONVENTION})
        self.assertEqual(len(stream), 4)
        self.assertEqual(answered, 3)


class TestMigrationApply(MigrationCase):
    """Each planned stream lands without overwriting existing records."""

    def build_source(self):
        root = self.source_root("delta", origin="git@github.com:acme/delta.git")
        write(root / "runs" / "20260201T000000Z-r" / "worklog.md", "# r\n")
        write(root / "runs" / "20260201T000000Z-r" / "composition.md", "# c\n")
        write(root / "tickets" / "20260201T000000Z-r" / "01-x.md", "x\n")
        write(root / "friction" / "2026-02.jsonl", legacy_entry(root.parent) + "\n")
        write(root / "improvement" / "proposals" / "2026-02-01-p.md", "# p\n")
        write(root / "improvement" / "covered.jsonl",
              json.dumps({"cluster": "c2"}) + "\n")
        write(root / "canary" / "golden" / "spec.md", "# canary\n")
        write(root / "bin" / "tickets.py", "# installed\n")
        write(root / "events" / "2026-02.log", "event\n")
        return root

    def test_each_stream_lands_where_the_sink_layout_fixes_it(self):
        root = self.build_source()
        self.migrate(root)

        for relative in (
            "runs/20260201T000000Z-r/worklog.md",
            "runs/20260201T000000Z-r/composition.md",
            "tickets/20260201T000000Z-r/01-x.md",
            "friction/2026-02.jsonl",
            "improvement/proposals/2026-02-01-p.md",
            "improvement/covered.jsonl",
        ):
            with self.subTest(path=relative):
                self.assertTrue((self.sink / relative).is_file(),
                                f"{relative} is missing from the sink")

    def test_canary_and_bin_stay_in_the_repository_and_are_reported(self):
        root = self.build_source()
        report = self.migrate(root)

        self.assertEqual(sorted(report["sources"][0]["retained"]), ["bin/", "canary/"])
        self.assertFalse((self.sink / "canary").exists())
        self.assertFalse((self.sink / "bin").exists())
        self.assertTrue((root / "canary" / "golden" / "spec.md").is_file())
        self.assertTrue((root / "bin" / "tickets.py").is_file())

    def test_an_unrecognised_directory_is_named_and_not_copied(self):
        root = self.build_source()
        report = self.migrate(root)

        self.assertIn("events/", report["sources"][0]["unrecognised"])
        self.assertFalse((self.sink / "events").exists())
        self.assertTrue((root / "events" / "2026-02.log").is_file())

    def test_each_coverage_line_gains_the_project_it_arose_in(self):
        root = self.build_source()
        self.migrate(root)

        record = self.sink / "improvement" / "covered.jsonl"
        self.assertTrue(record.is_file(), "the coverage record never reached the sink")
        entry = json.loads(lines_of(record)[0])
        self.assertEqual(entry["cluster"], "c2")
        self.assertEqual(entry.get("project"), {
            "root": str(root.parent),
            "origin": "git@github.com:acme/delta.git",
            "name": "delta",
        })
        self.assertEqual(entry.get("migrated_from"), str(root))

    def test_a_record_appearing_after_the_plan_is_refused_not_overwritten(self):
        root = self.source_root("iota", origin="git@github.com:acme/iota.git")
        write(root / "runs" / "20260401T000000Z-i" / "worklog.md", "# planned\n")

        plan, document = migrate_state.plan_migration(
            [str(root)], self.sink, dry_run=False)
        landed = self.sink / "runs" / "20260401T000000Z-i" / "worklog.md"
        write(landed, "# arrived first\n")
        migrate_state.apply_plan(plan, document)

        self.assertEqual(lines_of(landed), ["# arrived first"])
        errors = document["errors"]
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("refused", errors[0])
        self.assertIn(str(landed), errors[0])

    def test_a_dry_run_plans_exactly_what_a_real_run_does_and_writes_nothing(self):
        root = self.build_source()
        before = sink_bytes(self.sink)

        planned = self.migrate(root, dry_run=True)
        self.assertEqual(sink_bytes(self.sink), before)
        self.assertFalse(self.sink.exists() and any(self.sink.rglob("*")))

        executed = self.migrate(root)
        self.assertEqual(planned["plan"], executed["plan"])
        self.assertTrue(planned["plan"], "a dry run over a populated source planned nothing")
        del planned["dry_run"], executed["dry_run"]
        self.assertEqual(planned, executed)

    def test_a_record_already_at_the_destination_is_never_overwritten(self):
        root = self.build_source()
        write(self.sink / "runs" / "20260201T000000Z-r" / "worklog.md", "# already here\n")

        report = self.migrate(root)

        self.assertEqual(
            (self.sink / "runs" / "20260201T000000Z-r" / "worklog.md").read_text(encoding="utf-8"),
            "# already here\n",
        )
        self.assertEqual(
            [entry["source"] for entry in report["sources"][0]["differing"]],
            [str(root / "runs" / "20260201T000000Z-r" / "worklog.md")],
        )
