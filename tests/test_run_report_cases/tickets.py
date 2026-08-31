"""Section (c): how long a claimed ticket stayed claimed, by executor."""

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
    unittest,
)


class TicketDurationTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sink = build_sink(Path(self._tmp.name))
        self.addCleanup(self._tmp.cleanup)
        self.section = report_of(self.sink)["tickets"]

    def test_a_duration_runs_from_the_claim_to_the_ticket_s_own_last_write(self):
        self.assertEqual(
            [(row["run"], row["id"], row["minutes"]) for row in self.section["longest"]],
            [
                (COMPLETE_RUN, "00-root.02", 60.0),
                (COMPLETE_RUN, "00-root.01", 30.0),
                (OPEN_RUN, "00-root.01", 30.0),
                (COMPLETE_RUN, "00-root", 5.0),
                (BLOCKED_RUN, "00-root", 5.0),
            ],
        )

    def test_a_ticket_that_was_never_claimed_has_no_duration_to_report(self):
        self.assertNotIn(
            (BLOCKED_RUN, "00-root.01"),
            [(row["run"], row["id"]) for row in self.section["longest"]],
        )
        self.assertEqual(report_of(self.sink)["totals"]["tickets_measured"], 5)

    def test_each_executor_reports_its_median_p90_and_max(self):
        self.assertEqual(
            self.section["by_executor"],
            [
                {"executor": "orch-slice", "tickets": 2, "median_minutes": 5.0,
                 "p90_minutes": 5.0, "max_minutes": 5.0},
                {"executor": "orch-tdd", "tickets": 3, "median_minutes": 30.0,
                 "p90_minutes": 60.0, "max_minutes": 60.0},
            ],
        )

    def test_a_live_claim_carries_the_meter_the_reader_ui_draws(self):
        self.assertEqual(
            [(row["run"], row["id"], row["bound_minutes"], row["elapsed_minutes"], row["over"])
             for row in self.section["live_claims"]],
            [(OPEN_RUN, "00-root.01", 30, 6655, True)],
        )
        self.assertEqual([row["id"] for row in self.section["over_bound"]], ["00-root.01"])

    def test_a_settled_ticket_is_not_a_live_claim_however_long_it_took(self):
        settled = [(row["run"], row["id"]) for row in self.section["live_claims"]]
        self.assertNotIn((COMPLETE_RUN, "00-root.02"), settled)

    def test_top_bounds_the_longest_list_and_leaves_the_executor_summary_whole(self):
        section = report_of(self.sink, top=2)["tickets"]
        self.assertEqual([row["id"] for row in section["longest"]], ["00-root.02", "00-root.01"])
        self.assertEqual([row["executor"] for row in section["by_executor"]],
                         ["orch-slice", "orch-tdd"])
