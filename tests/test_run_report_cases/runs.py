"""Section (a): every run in the window, ranked, with what closed it."""

from __future__ import annotations

import tempfile
from pathlib import Path

from tests.test_run_report_cases.common import *  # noqa: F401,F403
from tests.test_run_report_cases.common import (
    BLOCKED_RUN,
    COMPLETE_RUN,
    OPEN_RUN,
    build_sink,
    report_of,
    run_named,
    unittest,
    write_run,
)


class RunTableTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sink = build_sink(Path(self._tmp.name))
        self.addCleanup(self._tmp.cleanup)

    def test_runs_rank_by_the_exact_elapsed_then_by_the_observed_span(self):
        report = report_of(self.sink)
        self.assertEqual(
            [(row["run"], row["rank_ms"], row["rank_source"]) for row in report["runs"]],
            [
                (COMPLETE_RUN, 5400000, "elapsed_ms"),
                (OPEN_RUN, 2100000, "observed"),
                (BLOCKED_RUN, 1200000, "elapsed_ms"),
            ],
        )

    def test_a_terminal_run_carries_the_status_and_the_ticket_that_closed_it(self):
        row = run_named(report_of(self.sink), COMPLETE_RUN)
        self.assertEqual(row["terminal_status"], "complete")
        self.assertEqual(row["terminal_ticket_id"], "00-root")
        self.assertEqual(row["terminal_at"], "2026-08-16T10:30:00Z")

    def test_an_open_run_has_no_terminal_status_and_is_measured_to_its_last_write(self):
        row = run_named(report_of(self.sink), OPEN_RUN)
        self.assertIsNone(row["terminal_status"])
        self.assertEqual(row["opened_at"], "2026-08-18T09:00:00Z")
        self.assertEqual(row["last_write_at"], "2026-08-18T09:35:00Z")
        self.assertIsNone(row["elapsed_ms"])
        self.assertEqual(row["observed_ms"], 2100000)

    def test_each_run_counts_its_tickets_and_its_complete_and_failed_ones(self):
        report = report_of(self.sink)
        self.assertEqual(
            [(row["run"], row["tickets"], row["complete"], row["failed"]) for row in report["runs"]],
            [(COMPLETE_RUN, 3, 2, 1), (OPEN_RUN, 1, 0, 0), (BLOCKED_RUN, 2, 1, 0)],
        )

    def test_a_run_whose_only_work_ticket_was_never_claimed_says_so(self):
        report = report_of(self.sink)
        self.assertTrue(run_named(report, BLOCKED_RUN)["claimed_no_work"])
        self.assertFalse(run_named(report, COMPLETE_RUN)["claimed_no_work"])
        self.assertFalse(run_named(report, OPEN_RUN)["claimed_no_work"])
        self.assertEqual(report["totals"]["runs_that_claimed_no_work"], 1)

    def test_every_run_is_named_by_its_family(self):
        report = report_of(self.sink)
        self.assertEqual(
            {row["run"]: row["family"] for row in report["runs"]},
            {COMPLETE_RUN: "alpha-thing", BLOCKED_RUN: "alpha-thing", OPEN_RUN: "beta-thing"},
        )

    def test_a_malformed_identity_is_listed_under_unreadable_and_never_raised(self):
        broken = "20260819T090000Z-broken"
        write_run(self.sink, broken, "{not json at all")
        report = report_of(self.sink)
        self.assertEqual(report["unreadable"]["runs"], [broken])
        row = run_named(report, broken)
        self.assertEqual(row["identity"], "unreadable")
        self.assertIsNone(row["opened_at"])
        self.assertIsNone(row["rank_ms"])

    def test_the_window_is_half_open_on_the_instant_a_run_opened(self):
        opened = report_of(self.sink, since="2026-08-17T09:00:00Z", until="2026-08-18T09:00:00Z")
        self.assertEqual([row["run"] for row in opened["runs"]], [BLOCKED_RUN])

    def test_top_bounds_the_table_without_changing_its_order(self):
        report = report_of(self.sink, top=2)
        self.assertEqual([row["run"] for row in report["runs"]], [COMPLETE_RUN, OPEN_RUN])
        self.assertEqual(report["totals"]["runs"], 3)

    def test_top_bounds_every_ranked_table_and_no_fixed_one(self):
        # The real sink's eight-day window holds 227 families and one
        # grouping row per run: a `--top` that bounded the runs alone
        # leaves the report unreadable at exactly the size it is for.
        report = report_of(self.sink, top=1)
        self.assertEqual([row["family"] for row in report["families"]], ["alpha-thing"])
        self.assertEqual(len(report["friction"]["by_category"]), 1)
        self.assertEqual(len(report["friction"]["by_run"]), 1)
        self.assertEqual(len(report["friction"]["clusters"]), 11)
        self.assertEqual(len(report["tickets"]["by_executor"]), 2)
        self.assertEqual(report["totals"], report_of(self.sink)["totals"])
