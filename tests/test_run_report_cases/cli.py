"""The command itself: its flags, its two formats, and its silence."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.test_run_report_cases.common import *  # noqa: F401,F403
from tests.test_run_report_cases.common import (
    ALPHA_FAMILY,
    BETA_FAMILY,
    BLOCKED_RUN,
    COMPLETE_RUN,
    OPEN_RUN,
    RUN_REPORT_PY,
    SINCE,
    UNTIL,
    build_sink,
    unittest,
    write_run,
)


def sink_state(sink: Path) -> dict:
    """Every byte and every mtime under the sink, for the read-only claim."""

    state = {}
    for path in sorted(sink.rglob("*")):
        if path.is_file():
            state[str(path.relative_to(sink))] = (path.read_bytes(), path.stat().st_mtime_ns)
    return state


def report_cli(sink: Path, *args):
    return subprocess.run(
        [sys.executable, str(RUN_REPORT_PY), "--root", str(sink), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )


class ReportCommandTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sink = build_sink(Path(self._tmp.name))
        self.addCleanup(self._tmp.cleanup)

    def window(self, *args):
        return report_cli(self.sink, "--since", SINCE, "--until", UNTIL, *args)

    def test_json_names_every_metric_with_the_value_the_fixture_states(self):
        completed = self.window("--format", "json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)

        self.assertEqual([row["run"] for row in report["runs"]], [COMPLETE_RUN, OPEN_RUN, BLOCKED_RUN])
        self.assertEqual(report["runs"][0]["elapsed_ms"], 5400000)
        self.assertEqual(report["runs"][1]["observed_ms"], 2100000)
        self.assertEqual(report["runs"][2]["terminal_status"], "blocked")
        self.assertTrue(report["runs"][2]["claimed_no_work"])

        alpha = next(row for row in report["families"] if row["family"] == ALPHA_FAMILY)
        self.assertEqual(alpha["physical_runs"], 2)
        self.assertEqual(alpha["wall_clock_ms"], 5400000)
        self.assertEqual(alpha["oracle_minutes"], 3.0)
        beta = next(row for row in report["families"] if row["family"] == BETA_FAMILY)
        self.assertEqual((beta["physical_runs"], beta["wall_clock_ms"], beta["oracle_minutes"]), (1, None, 0.0))

        tdd = next(row for row in report["tickets"]["by_executor"] if row["executor"] == "orch-tdd")
        self.assertEqual((tdd["median_minutes"], tdd["p90_minutes"], tdd["max_minutes"]), (30.0, 60.0, 60.0))

        self.assertEqual(report["friction"]["total"], 2)
        self.assertEqual(
            {row["cluster"]: row["count"] for row in report["friction"]["clusters"]}["powershell-quoting"], 1
        )
        self.assertEqual(
            report["totals"],
            {"runs": 3, "runs_terminal": 2, "runs_complete": 1, "runs_that_claimed_no_work": 1,
             "families": 2, "tickets_measured": 5},
        )

    def test_a_window_after_every_record_gives_empty_tables_and_exit_zero(self):
        completed = report_cli(self.sink, "--since", "2027-01-01T00:00:00Z", "--format", "json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        report = json.loads(completed.stdout)
        self.assertEqual(report["runs"], [])
        self.assertEqual(report["families"], [])
        self.assertEqual(report["tickets"]["by_executor"], [])
        self.assertEqual(report["tickets"]["longest"], [])
        self.assertEqual(report["friction"]["total"], 0)
        self.assertEqual(report["totals"]["runs"], 0)

    def test_the_same_empty_window_renders_as_text_and_still_exits_zero(self):
        completed = report_cli(self.sink, "--since", "2027-01-01T00:00:00Z")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("runs", completed.stdout)
        self.assertIn("no records in this window", completed.stdout)

    def test_a_malformed_identity_reaches_the_reader_rather_than_a_traceback(self):
        write_run(self.sink, "20260819T090000Z-broken", "{not json at all")
        completed = self.window("--format", "json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["unreadable"]["runs"], ["20260819T090000Z-broken"])
        self.assertEqual(completed.stderr, "")

    def test_text_is_the_default_format_and_heads_every_section(self):
        completed = self.window()
        self.assertEqual(completed.returncode, 0, completed.stderr)
        for heading in ("runs", "families", "ticket durations", "friction", "unreadable"):
            self.assertIn(heading, completed.stdout)
        self.assertIn(COMPLETE_RUN, completed.stdout)
        self.assertIn(ALPHA_FAMILY, completed.stdout)

    def test_top_bounds_the_tables_the_text_prints(self):
        completed = self.window("--top", "1")
        self.assertIn(COMPLETE_RUN, completed.stdout)
        self.assertNotIn(BLOCKED_RUN, completed.stdout.split("families")[0])

    def test_an_unparsable_window_bound_is_refused_rather_than_ignored(self):
        completed = report_cli(self.sink, "--since", "last tuesday")
        self.assertEqual(completed.returncode, 2)
        self.assertIn("--since", completed.stderr)
        self.assertEqual(completed.stdout, "")

    def test_the_report_writes_nothing_into_the_sink_it_reads(self):
        before = sink_state(self.sink)
        self.window("--format", "json")
        self.window()
        self.assertEqual(sink_state(self.sink), before)

    def test_a_root_that_holds_no_sink_is_an_answer_not_an_error(self):
        with tempfile.TemporaryDirectory() as raw:
            completed = report_cli(Path(raw) / "nowhere", "--format", "json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["empty"], "no state sink at this root")
