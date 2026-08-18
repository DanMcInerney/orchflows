"""Plan-seam migrate-state regression cases."""
from __future__ import annotations

import json
import os

from .common import (
    STATE_HOME_ENV_VAR,
    MigrationCase,
    legacy_entry,
    lines_of,
    migrate_state,
    write,
)


class TestMigrationPlan(MigrationCase):
    """Unsafe source and sink relationships are refused before application."""

    def test_the_sink_cannot_be_migrated_into_itself(self):
        self.sink.mkdir(parents=True, exist_ok=True)
        report = self.migrate(self.sink)

        self.assertEqual(report["plan"], [])
        self.assertEqual(len(report["errors"]), 1, report["errors"])
        self.assertIn("cannot be migrated into itself", report["errors"][0])

    def test_a_source_inside_the_sink_is_refused(self):
        buried = self.sink / "runs" / "somewhere" / ".orch"
        write(buried / "friction" / "2026-04.jsonl", legacy_entry(self.home) + "\n")

        report = self.migrate(buried)

        self.assertEqual(report["plan"], [])
        self.assertIn("cannot be migrated into itself", report["errors"][0])

    def test_a_sink_inside_a_migrating_stream_is_refused(self):
        root = self.source_root("epsilon", origin="git@github.com:acme/epsilon.git")
        self.sink = root / "runs" / "sink"
        os.environ[STATE_HOME_ENV_VAR] = str(self.sink)
        write(root / "runs" / "20260601T000000Z-e" / "worklog.md", "# e\n")

        report = self.migrate(root)

        self.assertEqual(report["plan"], [])
        self.assertIn("is inside source", report["errors"][0])
        self.assertIn("runs/ stream", report["errors"][0])

    def test_a_source_that_merely_holds_the_sink_still_migrates(self):
        root = self.home / "userscope"
        self.sink = root / "state"
        os.environ[STATE_HOME_ENV_VAR] = str(self.sink)
        self.sink.mkdir(parents=True)
        write(root / "friction" / "2026-07.jsonl", legacy_entry(self.home, "user scope") + "\n")
        write(root / "bin" / "tickets.py", "# installed\n")
        write(root / "receipt.json", "{}\n")

        report = self.migrate(root)

        month = self.sink / "friction" / "2026-07.jsonl"
        self.assertTrue(month.is_file(), f"{month} never reached the sink")
        landed = lines_of(month)
        self.assertEqual(len(landed), 1, landed)
        self.assertEqual(json.loads(landed[0])["observed"], "user scope")
        self.assertEqual(report["errors"], [])
        self.assertIn("state/ (the sink itself)", report["sources"][0]["retained"])
        self.assertIn("bin/", report["sources"][0]["retained"])
        self.assertEqual(report["sources"][0]["unrecognised"], ["receipt.json"])

    def test_a_source_that_does_not_exist_is_reported_not_raised(self):
        missing = self.home / "nowhere" / ".orch"
        report = self.migrate(missing)

        self.assertEqual(report["plan"], [])
        self.assertIn("is not a directory", report["errors"][0])


class TestUnreadableDestination(MigrationCase):
    """An unreadable destination is refused, never read as empty."""

    def source_with_friction(self):
        root = self.source_root("alpha")
        write(root / "friction" / "2026-01.jsonl",
              legacy_entry(root.parent, "one") + "\n")
        return root

    def test_an_unreadable_destination_is_named_and_nothing_is_queued_for_it(self):
        root = self.source_with_friction()
        blocked = self.sink / "friction" / "2026-01.jsonl"
        blocked.mkdir(parents=True)

        report = self.migrate(root)

        self.assertEqual(
            [action for action in report["plan"] if action["dest"] == str(blocked)],
            [],
            report["plan"],
        )
        self.assertTrue(
            [error for error in report["errors"] if str(blocked) in error],
            report["errors"],
        )

    def test_an_absent_destination_is_still_the_ordinary_first_copy(self):
        root = self.source_with_friction()

        report = self.migrate(root)

        self.assertEqual(report["errors"], [])
        self.assertEqual(len(lines_of(self.sink / "friction" / "2026-01.jsonl")), 1)

    def test_the_unterminated_line_question_refuses_rather_than_answers_no(self):
        blocked = self.sink / "friction" / "2026-01.jsonl"
        blocked.mkdir(parents=True)
        with self.assertRaises(OSError):
            migrate_state._needs_newline(blocked)


class TestUsage(MigrationCase):
    """A usage refusal is a JSON payload, never a traceback."""

    def test_no_source_is_a_usage_error(self):
        self.assertIn("error", migrate_state.run([]))

    def test_an_unknown_flag_is_refused_rather_than_guessed(self):
        result = migrate_state.run(["--from", str(self.home), "--force"])
        self.assertIn("error", result)
        self.assertIn("--force", result["error"])
