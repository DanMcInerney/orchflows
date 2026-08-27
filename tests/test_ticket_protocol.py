"""Sealed assignment identity covers semantics, not executor records."""
import unittest
from scripts.tickets_generations import assignment_digest
from scripts.tickets_issue_render import _render_ticket


def ticket(goal="done", suggested=None, result=""):
    sections = [("Goal", goal), ("Context", "fact")]
    if suggested:
        sections.append(("Suggested files", suggested))
    sections.extend((("Result", result), ("Verification", ""), ("Feedback", "[]"), ("Risks", "[]")))
    return _render_ticket({"id": "R", "run": "r", "status": "pending", "executor": "orch-edit", "depends_on": [], "bound": "60m"}, sections)


class TicketProtocolTest(unittest.TestCase):
    def test_semantic_change_moves_assignment(self):
        self.assertNotEqual(assignment_digest("R", ticket()), assignment_digest("R", ticket(goal="other")))
        self.assertNotEqual(assignment_digest("R", ticket()), assignment_digest("R", ticket(suggested="- x")))

    def test_result_does_not_move_assignment(self):
        self.assertEqual(assignment_digest("R", ticket()), assignment_digest("R", ticket(result="landed")))
