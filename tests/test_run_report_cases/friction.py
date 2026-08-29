"""Section (d): the friction the window recorded, and what it clustered as."""

from __future__ import annotations

import tempfile
from pathlib import Path

from tests.test_run_report_cases.common import *  # noqa: F401,F403
from tests.test_run_report_cases.common import (
    COMPLETE_RUN,
    OPEN_RUN,
    build_sink,
    report_of,
    unittest,
)


def counted(rows, key: str) -> dict:
    return {row[key]: row["count"] for row in rows}


class FrictionSectionTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.sink = build_sink(Path(self._tmp.name))
        self.addCleanup(self._tmp.cleanup)
        self.report = report_of(self.sink)
        self.section = self.report["friction"]

    def test_only_the_records_inside_the_window_are_counted(self):
        self.assertEqual(self.section["total"], 2)
        self.assertNotIn("outside_window", self.section)

    def test_records_are_grouped_by_category_skill_host_and_run(self):
        self.assertEqual(counted(self.section["by_category"], "category"),
                         {"contract-gap": 1, "host-defect": 1})
        self.assertEqual(counted(self.section["by_skill"], "skill"), {"orch-tdd": 2})
        self.assertEqual(counted(self.section["by_host"], "host"), {"claude-code": 2})
        self.assertEqual(counted(self.section["by_run"], "run"), {COMPLETE_RUN: 1, OPEN_RUN: 1})

    def test_the_keyword_cluster_table_is_fixed_and_in_the_specification_s_order(self):
        self.assertEqual(
            [row["cluster"] for row in self.section["clusters"]],
            ["powershell-quoting", "rg-wildcard", "guessed-path", "truncated-escaped-result",
             "workspace-vantage", "missing-node-modules", "word-ceiling", "sealed-assignment",
             "isolation", "missing-flag", "full-suite-flake"],
        )

    def test_each_record_lands_in_the_cluster_its_words_name(self):
        clusters = counted(self.section["clusters"], "cluster")
        self.assertEqual(clusters["powershell-quoting"], 1)
        self.assertEqual(clusters["full-suite-flake"], 1)
        self.assertEqual(sum(clusters.values()), 2)
        self.assertEqual(self.section["unclustered"], 0)

    def test_a_line_that_is_not_a_record_is_counted_unreadable_not_dropped(self):
        self.assertEqual(self.report["unreadable"]["friction_lines"], 1)
        self.assertEqual(self.report["unreadable"]["friction_files"], [])

    def test_a_window_can_exclude_every_record_without_losing_the_table(self):
        section = report_of(self.sink, since="2026-08-19T00:00:00Z", until="2026-08-20T00:00:00Z")["friction"]
        self.assertEqual(section["total"], 0)
        self.assertEqual(section["by_category"], [])
        self.assertEqual([row["count"] for row in section["clusters"]], [0] * 11)
