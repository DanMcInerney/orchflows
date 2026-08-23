"""Sections (b) and (e): run families and the three metrics of §1."""

from __future__ import annotations

import tempfile
from pathlib import Path

from tests.test_run_report_cases.common import *  # noqa: F401,F403
from tests.test_run_report_cases.common import (
    ALPHA_FAMILY,
    BETA_FAMILY,
    BLOCKED_RUN,
    COMPLETE_RUN,
    OPEN_RUN,
    build_sink,
    family_named,
    report_of,
    unittest,
)

from tools.run_report_support import model


class FamilyStemTest(unittest.TestCase):
    def test_every_timestamp_spelling_the_sink_holds_is_stripped(self):
        self.assertEqual(model.family_of("20260823T130218Z-orchflows-speed"), "orchflows-speed")
        self.assertEqual(model.family_of("20260818-script-size-refactor"), "script-size-refactor")
        self.assertEqual(model.family_of("2026-08-12-benchmaker-gate"), "benchmaker-gate")

    def test_the_specification_s_retry_markers_and_no_others_are_stripped(self):
        for marker in ("v2", "v3", "retry", "restart", "corrected", "direct",
                       "final", "cut-ready", "edge-ready", "runnable", "replacement"):
            self.assertEqual(model.family_of("20260818-thing-" + marker), "thing", marker)
        self.assertEqual(model.family_of("20260818-handoff-program-cut"), "handoff-program-cut")

    def test_a_name_that_is_only_a_timestamp_stays_its_own_family(self):
        self.assertEqual(model.family_of("20260818T090000Z"), "20260818T090000Z")


class FamilySectionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sink = build_sink(Path(self._tmp.name))
        self.addCleanup(self._tmp.cleanup)

    def test_a_retry_is_a_second_physical_run_of_one_family(self):
        row = family_named(report_of(self.sink), ALPHA_FAMILY)
        self.assertEqual(row["physical_runs"], 2)
        self.assertEqual(row["runs"], [COMPLETE_RUN, BLOCKED_RUN])
        self.assertEqual(row["statuses"], {"complete": 1, "blocked": 1})

    def test_a_family_spans_its_first_opening_to_its_last_sink_write(self):
        row = family_named(report_of(self.sink), ALPHA_FAMILY)
        self.assertEqual(row["span_from"], "2026-08-16T09:00:00Z")
        self.assertEqual(row["span_to"], "2026-08-17T09:20:00Z")

    def test_wall_clock_runs_from_the_first_opening_to_the_accepted_result(self):
        self.assertEqual(family_named(report_of(self.sink), ALPHA_FAMILY)["wall_clock_ms"], 5400000)

    def test_a_family_with_no_complete_run_reached_no_accepted_result(self):
        row = family_named(report_of(self.sink), BETA_FAMILY)
        self.assertIsNone(row["wall_clock_ms"])
        self.assertEqual(row["physical_runs"], 1)
        self.assertEqual(row["runs"], [OPEN_RUN])
        self.assertEqual(row["statuses"], {"open": 1})

    def test_oracle_minutes_sum_only_the_invocations_a_duration_was_written_beside(self):
        row = family_named(report_of(self.sink), ALPHA_FAMILY)
        self.assertEqual(row["oracle_minutes"], 3.0)
        self.assertEqual(row["oracle_invocations"], 2)
        self.assertEqual(row["oracle_invocations_timed"], 2)
        beta = family_named(report_of(self.sink), BETA_FAMILY)
        self.assertEqual((beta["oracle_minutes"], beta["oracle_invocations"]), (0.0, 0))

    def test_a_bound_is_never_read_as_oracle_time(self):
        # Every fixture ticket carries `bound: 30m`; no line naming an
        # oracle carries it, so no family may report those thirty minutes.
        self.assertEqual(
            sum(row["oracle_minutes"] for row in report_of(self.sink)["families"]), 3.0
        )

    def test_families_are_ordered_by_the_wall_clock_they_cost(self):
        report = report_of(self.sink)
        self.assertEqual([row["family"] for row in report["families"]], [ALPHA_FAMILY, BETA_FAMILY])
        self.assertEqual(report["totals"]["families"], 2)
