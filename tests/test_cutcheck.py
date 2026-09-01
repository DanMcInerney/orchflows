"""Current structural cut validation."""
import unittest
from scripts.cutcheck import graph_findings
from scripts.tickets_issue_render import _render_ticket

__all__ = ("graph_findings", "_render_ticket", "item")


def item(ticket_id, dependencies=()):
    return _render_ticket({"id": ticket_id, "run": "r", "status": "pending", "executor": "orch-do", "pack": "orch-code-pack", "depends_on": list(dependencies), "bound": "60m"}, [("Goal", "done"), ("Context", "fact"), ("Report", "")])


class CutcheckTest(unittest.TestCase):
    def test_closed_graph_passes_even_when_candidates_may_overlap(self):
        self.assertEqual([], graph_findings({"A": item("A"), "B": item("B")}))

    def test_dangling_dependency_and_cycle_fail(self):
        self.assertTrue(any(row[1] == "dangling-dependency" for row in graph_findings({"A": item("A", ["missing"])})))
        self.assertTrue(any(row[1] == "dependency-cycle" for row in graph_findings({"A": item("A", ["B"]), "B": item("B", ["A"])})))
