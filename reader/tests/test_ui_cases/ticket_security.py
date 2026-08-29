"""Ticket parsing, sink containment, and elapsed-meter regressions."""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from reader.scripts import ui_discovery, ui_model, ui_ticket_model
from reader.tests.test_ui_cases import _base as fixture


class TestTicketTreeContainment(unittest.TestCase):
    def test_ticket_lookup_stays_inside_tickets_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture.make_sink(Path(tmp))
            (root / "secret.md").write_text("id: outside\n", encoding="utf-8")
            self.assertIsNone(ui_discovery.find_ticket(root, "..", "secret"))
            self.assertIsNone(ui_discovery.find_ticket(root, "run-alpha", "../../secret"))
            self.assertIsNotNone(ui_discovery.find_ticket(root, "run-alpha", "A1"))

    def test_refused_names_return_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = fixture.make_sink(Path(tmp))
            for run, ticket in (("", "A1"), ("run-alpha", ""), ("../", "A1"), ("run-alpha", "../A1")):
                self.assertIsNone(ui_discovery.find_ticket(root, run, ticket))

    def test_ticket_parser_names_sections_and_escaped_fences(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "one.md"
            path.write_text(
                "---\nid: one\nstatus: ready\ndepends_on: [zero]\n---\n"
                "## Goal\n\nread this\n\n```\n## not a section\n```\n"
                "## Result\n\n| value |\n",
                encoding="utf-8",
            )
            ticket = ui_ticket_model.read_ticket(path)
        self.assertEqual("one", ticket["id"])
        self.assertEqual("ready", ticket["status"])
        self.assertEqual(("zero",), ticket["depends_on"])
        self.assertEqual({"Goal", "Result"}, set(ticket["sections"]))
        self.assertNotIn("not a section", ticket["sections"])


class TestElapsedMeter(unittest.TestCase):
    NOW = datetime(2026, 1, 1, 1, 0, 0, tzinfo=timezone.utc)

    def test_only_duration_bounds_are_measured(self):
        self.assertEqual(90, ui_model.bound_minutes("90m"))
        self.assertEqual(120, ui_model.bound_minutes("2h"))
        for value in ("one session", "", "90", "90 m", "1d", "m90", "-5m", None):
            self.assertIsNone(ui_model.bound_minutes(value), value)

    def test_claim_meter_requires_live_status_and_both_operands(self):
        meter = ui_model.claim_meter(
            {"status": "claimed", "bound": "90m", "claimed_at": "2026-01-01T00:00:00Z"},
            self.NOW,
        )
        self.assertEqual(60, meter["elapsed_minutes"])
        self.assertEqual(90, meter["bound_minutes"])
        self.assertEqual(67, meter["percent"])
        for front in (
            {"status": "suspended", "bound": "30m", "claimed_at": "2026-01-01T00:00:00Z"},
            {"status": "claimed", "bound": "one session", "claimed_at": "2026-01-01T00:00:00Z"},
            {"status": "claimed", "bound": "90m"},
            {"status": "claimed", "bound": "90m", "claimed_at": "yesterday"},
        ):
            self.assertIsNone(ui_model.claim_meter(front, self.NOW), front)
