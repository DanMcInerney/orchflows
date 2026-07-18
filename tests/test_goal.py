"""Pins orch-goal's mandatory two-run re-specification lifecycle."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GOAL = ROOT / "skills" / "workflows" / "orch-goal" / "SKILL.md"
SECOND_PASS = GOAL.parent / "references" / "second-pass.md"
COMPOSITION = ROOT / "compositions" / "delivery-loop.md"


def flat(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


class TestGoalLifecycle(unittest.TestCase):
    def test_goal_requires_the_original_request_and_deliver_spec(self):
        text = flat(GOAL)
        self.assertIn("stamped `pattern: deliver`", text)
        self.assertIn("`evidence` names the original user request by identity", text)

    def test_first_run_status_cannot_skip_the_second_delivery(self):
        text = flat(GOAL)
        self.assertIn("Run `orch-deliver` twice", text)
        self.assertIn("Its status never omits delivery 2", text)
        self.assertIn("omit delivery 2 because delivery 1 passed", text)
        self.assertIn("dispatch a third delivery", text)

    def test_second_pass_creates_and_delivers_a_new_spec(self):
        text = flat(GOAL)
        self.assertIn("Run `orch-spec`", text)
        self.assertIn("the exact original request as its request", text)
        self.assertIn("the original spec plus that packet as evidence", text)
        self.assertIn("a fresh `pattern: deliver` spec with a new run id", text)
        self.assertIn("Never: edit the original spec", text)
        self.assertNotIn("`orch-loop`", text)

    def test_each_stage_has_its_own_reserved_budget(self):
        text = flat(GOAL)
        self.assertIn(
            "separate budgets for delivery 1, re-specification, and delivery 2",
            text,
        )
        self.assertIn("the budget reserved for delivery 2", flat(SECOND_PASS))

    def test_second_pass_packet_carries_problems_and_workarounds(self):
        text = flat(SECOND_PASS)
        for field in (
            "final verdicts",
            "uncovered remainder",
            "failed approaches",
            "discovered constraints",
            "problems",
            "workarounds",
            "remaining bound",
        ):
            self.assertIn(field, text)

    def test_composition_matches_the_callable_workflow(self):
        text = flat(COMPOSITION)
        self.assertIn("two delivery runs", text)
        self.assertIn("re-reads the exact original request", text)
        self.assertIn("The original spec remains unchanged", text)
        self.assertIn("there is no third delivery", text)


if __name__ == "__main__":
    unittest.main()
