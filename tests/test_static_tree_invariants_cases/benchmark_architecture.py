"""Static invariants owned by benchmark campaign architecture."""
import unittest

from ._support import (
    CALL_EDGE_RE,
    COMPOSITIONS,
    ROOT,
    bodies,
    split_document,
    stub_graph,
    template_files,
)

EVAL_DESIGN = ROOT / "skills" / "workflows" / "orch-eval-design" / "SKILL.md"
EVOLVE = COMPOSITIONS / "evolve"
EVOLVE_GENERATION = COMPOSITIONS / "references" / "evolve-generation.md"
TOURNAMENT = COMPOSITIONS / "skill-tournament"
SUPERSEDED_BODIES = (
    COMPOSITIONS / "evolve.md",
    COMPOSITIONS / "skill-tournament.md",
    COMPOSITIONS / "fix.md",
    COMPOSITIONS / "references" / "evolve-evaluation.md",
)


class TestBenchmarkArchitecture(unittest.TestCase):
    """Pin benchmark call edges, template graph, and demoted owners."""

    # (label, sources, exactly, at_least, never)
    CALL_EDGES = (
        (
            "orch-eval-design", (EVAL_DESIGN,),
            frozenset(), frozenset(), frozenset(),
        ),
        (
            "skill-tournament", template_files(TOURNAMENT),
            frozenset(), frozenset(), frozenset(),
        ),
        (
            "evolve", template_files(EVOLVE) + (EVOLVE_GENERATION,),
            frozenset(), frozenset(), frozenset(),
        ),
    )

    EVOLVE_GRAPH = {
        "00-eval": ("orch-eval-design", []),
        "01-eligibility": ("orch-verify", ["00-eval"]),
        "02-campaign": ("orch-loop", ["01-eligibility"]),
        "03-result": ("orch-verify", ["02-campaign"]),
    }
    TOURNAMENT_GRAPH = {
        "00-benchmark": ("orch-frontier", []),
        "01-campaign": ("orch-frontier", ["00-benchmark"]),
    }
    DEMOTED = (
        "orch-bench", "orch-benchmaker", "orch-judge", "orch-delegate",
        "orch-worklog", "orch-panel",
    )

    def test_each_body_calls_exactly_the_edges_its_architecture_declares(self):
        for label, sources, exactly, at_least, never in self.CALL_EDGES:
            with self.subTest(body=label):
                calls = set(CALL_EDGE_RE.findall(bodies(*sources)))
                if exactly is not None:
                    self.assertEqual(set(exactly), calls)
                self.assertLessEqual(set(at_least), calls)
                self.assertEqual(set(), calls & set(never))

    def test_the_evolve_template_names_its_executors_in_frontmatter(self):
        self.assertEqual(self.EVOLVE_GRAPH, stub_graph(EVOLVE))
        self.assertEqual(self.TOURNAMENT_GRAPH, stub_graph(TOURNAMENT))

    def test_evolve_verifies_before_it_ranks_and_before_it_closes(self):
        graph = stub_graph(EVOLVE)
        self.assertEqual("orch-verify", graph["01-eligibility"][0])
        self.assertEqual(["01-eligibility"], graph["02-campaign"][1])
        self.assertEqual("orch-verify", graph["03-result"][0])
        self.assertEqual(["02-campaign"], graph["03-result"][1])
        terminal = [
            stub for stub in graph
            if not any(stub in depends for _, depends in graph.values())
        ]
        self.assertEqual(["03-result"], terminal)

    def test_no_demoted_owner_reappears_in_either_campaign(self):
        for directory in (EVOLVE, TOURNAMENT):
            text = "".join(
                path.read_text(encoding="utf-8")
                for path in template_files(directory)
            )
            for name in self.DEMOTED:
                with self.subTest(template=directory.name, demoted=name):
                    self.assertNotIn(name, text)

    def test_the_superseded_campaign_bodies_stay_deleted(self):
        for path in SUPERSEDED_BODIES:
            with self.subTest(body=path.name):
                self.assertFalse(path.exists(), f"{path} is the template's twin")

    def test_the_campaigns_stay_manual_only_entries(self):
        for directory in (EVOLVE, TOURNAMENT):
            with self.subTest(template=directory.name):
                manifest = directory / "template.md"
                self.assertEqual("named", split_document(manifest)[0].get("entry"))
