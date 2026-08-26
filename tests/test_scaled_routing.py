"""Routing is priced by graph shape and oracle provenance, not size labels."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from tools.live_routing_bench_support import grading


ROOT = Path(__file__).resolve().parents[1]
HOST = ROOT / "templates" / "host-block.md"
CASES = ROOT / "benchmarks" / "routing" / "cases.json"
README = ROOT / "README.md"
VOCABULARY = ROOT / "docs" / "vocabulary.md"
BENCHMARK_README = ROOT / "benchmarks" / "routing" / "README.md"


class ScaledRoutingTests(unittest.TestCase):
    def test_host_projects_the_four_graph_shapes(self):
        host = re.sub(r"\s+", " ", HOST.read_text(encoding="utf-8"))

        anchors = (
            "**answer**",
            "**single**",
            "**graph**",
            "**spec**",
        )
        positions = [host.index(anchor) for anchor in anchors]
        self.assertEqual(sorted(positions), positions)
        for obsolete in ("**errand**", "`tickets.py errand`"):
            self.assertNotIn(obsolete, host)

        single = host[positions[1] : positions[2]]
        self.assertIn("one ordinary ticket", single)
        self.assertIn("`orch-frontier`", single)
        self.assertIn("pre-existing", single)
        self.assertIn("authored-here", single)

        graph = host[positions[2] : positions[3]]
        self.assertIn("frozen", graph)
        self.assertIn("`orch-decompose`", graph)
        self.assertIn("outer", graph)
        self.assertIn("`orch-frontier`", graph)

        spec = host[positions[3] :]
        for anchor in (
            "same planner",
            "`orch-spec`",
            "ready",
            "claim",
            "packet",
            "`orch-decompose`",
            "outer",
            "`orch-frontier`",
        ):
            self.assertIn(anchor, spec)
        self.assertNotIn("sequence: [orch-spec, orch-decompose]", host)

    def test_benchmark_distinguishes_single_graph_and_spec(self):
        cases = json.loads(CASES.read_text(encoding="utf-8"))
        by_id = {case["id"]: case for case in cases}

        expected = {
            "ticket-ui-json-flag": "single",
            "ticket-refusal-test": "single",
            "ticket-codex-catalog-gap": "single",
            "ticket-independent-atoms": "graph",
            "ticket-uncertain-root": "spec",
        }
        for case_id, route in expected.items():
            with self.subTest(case=case_id):
                self.assertEqual(route, by_id[case_id]["expected"])

        primary = {"answer", "single", "graph", "spec"}
        self.assertEqual(
            primary,
            {case["expected"] for case in cases} & primary,
        )
        self.assertNotIn("errand", {case["expected"] for case in cases})
        self.assertNotIn("ticket", {case["expected"] for case in cases})

    def test_live_grader_projects_the_same_primary_routes(self):
        self.assertEqual(
            ("answer", "single", "graph", "spec"),
            grading.ROUTE_CLASSES[:4],
        )
        self.assertNotIn("errand", grading.ROUTE_CLASSES)
        self.assertNotIn("ticket", grading.ROUTE_CLASSES)

    def test_public_explanation_maps_sizes_without_making_them_routes(self):
        readme = README.read_text(encoding="utf-8")
        vocabulary = VOCABULARY.read_text(encoding="utf-8")
        benchmark = BENCHMARK_README.read_text(encoding="utf-8")
        combined = "\n".join((readme, vocabulary, benchmark)).lower()

        for route in ("answer", "single", "graph", "spec"):
            with self.subTest(route=route):
                self.assertIn(f"`{route}`", combined)
        for size in ("small", "medium", "large"):
            with self.subTest(size=size):
                self.assertRegex(combined, rf"\b{size}\b")

        self.assertIn("explanatory", combined)
        self.assertNotIn("**errand**", combined)
        self.assertNotIn("`tickets.py errand`", combined)


if __name__ == "__main__":
    unittest.main()
