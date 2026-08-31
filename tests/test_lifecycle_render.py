"""The ticket lifecycle is declared once in code and rendered without drift."""

from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
from scripts import tickets_lifecycle  # noqa: E402
from tools import render_lifecycle  # noqa: E402
from tools import validate  # noqa: E402


class LifecycleTableTest(unittest.TestCase):
    def test_every_public_lifecycle_event_has_the_owned_seven_cells(self):
        rows = tickets_lifecycle.lifecycle_rows()
        events = {row.event for row in rows}
        self.assertEqual(
            {
                "check",
                "claim",
                "dispatch-join",
                "dispatch-commit",
                "dispatch-open",
                "dispatch-outcome",
                "dispatch",
                "dispatch-replace",
                "dispatch-retire",
                "issue",
                "ready",
                "result",
                "set-status blocked",
                "set-status complete",
                "set-status failed",
                "set-status limited",
                "set-status pending",
                "set-status stalled",
                "set-status suspended",
                "stamp",
            },
            events,
        )
        for row in rows:
            for field in (
                "predecessor",
                "event",
                "actor",
                "required_record",
                "result",
                "contract",
                "rule",
            ):
                self.assertTrue(getattr(row, field), (row, field))

    def test_the_committed_table_is_exactly_the_rendered_code(self):
        target = ROOT / "docs" / "lifecycle.md"
        self.assertEqual(render_lifecycle.render(), target.read_text(encoding="utf-8"))

    def test_a_hand_edit_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "lifecycle.md"
            target.write_text(render_lifecycle.render() + "hand edit\n", encoding="utf-8")
            self.assertFalse(render_lifecycle.is_current(target))

    def test_each_generated_row_names_its_code_identity(self):
        rendered = render_lifecycle.render()
        for row in tickets_lifecycle.lifecycle_rows():
            self.assertIn(f'<a id="{row.anchor}"></a>', rendered)

    def test_dispatch_rows_expose_attempt_and_record_state(self):
        rows = tickets_lifecycle.lifecycle_rows()
        filed = next(row for row in rows if row.event == "result")
        self.assertEqual("claimed / launched", filed.predecessor)
        self.assertEqual("claimed / launched + result record", filed.result)
        retire = next(row for row in rows if row.event == "dispatch-retire")
        self.assertEqual("claimed / live attempt", retire.predecessor)
        self.assertEqual("claimed / retired attempt", retire.result)
        joins = [row for row in rows if row.event == "dispatch-join"]
        self.assertIn("suspended / retired attempt", {row.result for row in joins})

    def test_the_repository_validator_refuses_a_hand_edit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "scripts").mkdir()
            (root / "docs").mkdir()
            for name in ("tickets_transitions.py", "tickets_lifecycle.py"):
                (root / "scripts" / name).write_text("# owner\n", encoding="utf-8")
            (root / "docs" / "lifecycle.md").write_text("hand edit\n", encoding="utf-8")
            prior = validate.ROOT
            try:
                validate.ROOT = root
                diag = validate.Diagnostics()
                validate.validate_regenerated_artifacts(diag, ("lifecycle",))
            finally:
                validate.ROOT = prior
            self.assertTrue(diag.has_errors)
            self.assertTrue(any("drifted from transition code" in line for line in diag.lines()))


if __name__ == "__main__":
    unittest.main()
