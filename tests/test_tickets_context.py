"""Successor Context hydration remains non-authoritative and ordered."""

import tempfile
import unittest
from pathlib import Path

from scripts.tickets_successor_context import successor_context_block


DEPENDENCY = """---
id: {ticket_id}
status: {status}
---

## Result

landed

{context}
"""


class SuccessorContextTest(unittest.TestCase):
    def test_only_context_is_flattened_in_declared_order(self):
        with tempfile.TemporaryDirectory() as raw:
            run = Path(raw)
            successor = run / "next.md"
            successor.write_text("", encoding="utf-8")
            for ticket_id, body in (("B", "- watch: second."), ("A", "- state: first.")):
                context = f"## Context\n\n{body}"
                (run / f"{ticket_id}.md").write_text(
                    DEPENDENCY.format(ticket_id=ticket_id, status="complete", context=context),
                    encoding="utf-8",
                )
            lines = successor_context_block({"depends_on": ["A", "B"]}, successor)
            self.assertEqual(
                ["Successor context from A (complete): - state: first.",
                 "Successor context from B (complete): - watch: second."],
                lines,
            )

    def test_complete_dependency_without_context_points_at_result(self):
        with tempfile.TemporaryDirectory() as raw:
            run = Path(raw)
            successor = run / "next.md"
            (run / "A.md").write_text(
                DEPENDENCY.format(ticket_id="A", status="complete", context=""),
                encoding="utf-8",
            )
            lines = successor_context_block({"depends_on": ["A"]}, successor)
            self.assertEqual(1, len(lines))
            self.assertIn("filed no `## Context`", lines[0])


if __name__ == "__main__":
    unittest.main()
