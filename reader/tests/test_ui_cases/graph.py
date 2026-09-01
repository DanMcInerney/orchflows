"""Deterministic dependency-graph layout and projection regressions."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from reader.scripts import ui_layout, ui_runs_projection
from reader.tests.test_ui_cases import _base as fixture


def fan_graph(width):
    ids = ("R",) + tuple("M{0}".format(index) for index in range(width)) + ("S",)
    edges = tuple(("R", "M{0}".format(index)) for index in range(width))
    edges += tuple(("M{0}".format(index), "S") for index in range(width))
    return ids, edges


class TestGraphLayout(unittest.TestCase):
    IDS = ("D1", "D2", "D3", "D4", "D5")
    EDGES = (("D1", "D2"), ("D1", "D3"), ("D2", "D4"), ("D3", "D4"), ("D4", "D5"))

    def test_equal_input_is_byte_deterministic(self):
        first = ui_layout.graph_layout(self.IDS, self.EDGES)
        second = ui_layout.graph_layout(self.IDS, self.EDGES)
        self.assertEqual(first, second)
        self.assertTrue(first["edges"])

    def test_input_order_does_not_change_the_kept_edges(self):
        first = ui_layout.graph_layout(self.IDS, self.EDGES)
        second = ui_layout.graph_layout(tuple(reversed(self.IDS)), tuple(reversed(self.EDGES)))
        self.assertEqual(first, second)

    def test_edges_survive_a_wide_acyclic_graph_undiagnosed(self):
        ids, edges = fan_graph(9)
        layout = ui_layout.graph_layout(ids, edges)
        self.assertEqual([], layout["diagnostics"])
        self.assertEqual(sorted(edges), sorted(layout["edges"]))

    def test_empty_graph_is_a_valid_empty_shape(self):
        self.assertEqual(
            {"edges": [], "diagnostics": []},
            ui_layout.graph_layout((), ()),
        )


class TestGraphDiagnostics(unittest.TestCase):
    def test_cycle_is_reported_and_one_arc_is_withheld(self):
        layout = ui_layout.graph_layout(("E1", "E2", "E3"), (("E3", "E1"), ("E1", "E2"), ("E2", "E3")))
        self.assertEqual(1, len(layout["diagnostics"]))
        self.assertTrue(layout["diagnostics"][0].startswith(ui_layout.DIAGNOSTIC_CYCLE))
        self.assertEqual(2, len(layout["edges"]))

    def test_dangling_dependency_is_named_and_dropped(self):
        layout = ui_layout.graph_layout(("E1", "E4"), (("ZZ9", "E4"), ("E1", "E4")))
        self.assertEqual([("E1", "E4")], layout["edges"])
        self.assertIn(ui_layout.DIAGNOSTIC_DANGLING, layout["diagnostics"][0])

    def test_cycle_and_dangling_diagnostics_can_coexist(self):
        layout = ui_layout.graph_layout(("A", "B"), (("A", "B"), ("B", "A"), ("GONE", "A")))
        named = " ".join(layout["diagnostics"])
        self.assertIn(ui_layout.DIAGNOSTIC_CYCLE, named)
        self.assertIn(ui_layout.DIAGNOSTIC_DANGLING, named)

    def test_run_projection_uses_the_same_structural_contract(self):
        with TemporaryDirectory() as tmp:
            graph = ui_runs_projection.project_run(fixture.make_sink(Path(tmp)), fixture.CYCLIC_RUN)
        self.assertIsNotNone(graph)
        node_ids = {node["id"] for node in graph["nodes"]}
        self.assertTrue(all(edge["source"] in node_ids and edge["target"] in node_ids for edge in graph["edges"]))
        self.assertEqual(len(graph["edges"]), len({edge["id"] for edge in graph["edges"]}))
