"""Agent-facing projections of the errand routing lane."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ErrandRoutingTests(unittest.TestCase):
    def test_host_routes_the_minimum_context_graph(self):
        host = (ROOT / "templates" / "host-block.md").read_text(encoding="utf-8")
        collapsed = " ".join(host.split())

        for marker in (
            "**answer**",
            "**errand**",
            "**ticket**",
            "**fix**",
            "`tickets.py errand`",
            "pre-existing deterministic",
            "`authored-here`",
            "same claim's checker",
            "matching planner child",
            "`orch-spec` then `orch-decompose`",
            "outer join starts `orch-frontier`",
            "known cause",
            "unknown cause",
            "`install.py doctor`",
            "without dispatch",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, collapsed)
        self.assertNotIn("orch-errand", collapsed)

    def test_vocabulary_defines_errand_once(self):
        vocabulary = (ROOT / "docs" / "vocabulary.md").read_text(encoding="utf-8")

        self.assertEqual(1, vocabulary.count("**errand**"))
        self.assertIn("one executor or one ordered executor sequence", vocabulary)
        self.assertIn("`tickets.py errand`", vocabulary)

    def test_new_helper_has_direct_owner_edges(self):
        graph = json.loads(
            (ROOT / ".orchflows" / "scope-edges.json").read_text(encoding="utf-8")
        )
        edges = {
            (edge["from"]["operation"], edge["from"]["path"]): {
                (required["operation"], required["path"])
                for required in edge["requires"]
            }
            for edge in graph["edges"]
        }

        for operation in ("change", "delete"):
            self.assertIn(
                ("change", "ARCHITECTURE.md"),
                edges[(operation, "scripts/tickets_errand.py")],
            )

    def test_routing_benchmark_names_every_errand_boundary(self):
        cases = json.loads(
            (ROOT / "benchmarks" / "routing" / "cases.json").read_text(
                encoding="utf-8"
            )
        )
        by_id = {case["id"]: case["expected"] for case in cases}

        for case_id in (
            "ticket-ui-json-flag",
            "ticket-friction-quiet",
            "ticket-vocabulary-entry",
            "ticket-refusal-test",
            "ticket-readme-drift",
            "ticket-codex-catalog-gap",
            "ticket-lure-review",
            "ticket-lure-worklog",
            "build-migration-pack",
            "build-project-custom-skill",
            "build-project-custom-composition",
            "build-benchmark-contract",
            "errand-pre-existing-deterministic",
            "errand-authored-here",
        ):
            with self.subTest(case_id=case_id):
                self.assertEqual("errand", by_id[case_id])
        self.assertEqual("ticket", by_id["ticket-independent-atoms"])
        self.assertEqual("doctor", by_id["doctor-dispatch-bootstrap"])

    def test_workflow_catalog_projects_named_errand_composition(self):
        manifest = json.loads(
            (ROOT / "docs" / "ui" / "workflow-summary-manifest.json").read_text(
                encoding="utf-8"
            )
        )
        errand = manifest["workflows"]["errand"]

        self.assertEqual(
            [{"id": "deliver", "label": "Deliver one bounded errand"}],
            errand["nodes"],
        )
        self.assertEqual([], errand["edges"])


if __name__ == "__main__":
    unittest.main()
