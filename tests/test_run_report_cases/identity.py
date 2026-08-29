"""``reader/scripts/ui_discovery.read_run_identity``: the run's own document."""

from __future__ import annotations

import tempfile
from pathlib import Path

from tests.test_run_report_cases.common import *  # noqa: F401,F403
from tests.test_run_report_cases.common import (
    COMPLETE_RUN,
    OPEN_RUN,
    build_sink,
    ui_discovery,
    unittest,
    write_run,
)


class RunIdentityReaderTest(unittest.TestCase):
    def test_a_written_identity_comes_back_as_its_own_document(self):
        with tempfile.TemporaryDirectory() as raw:
            sink = build_sink(Path(raw))
            identity = ui_discovery.read_run_identity(sink, COMPLETE_RUN)
        self.assertEqual(identity["run"], COMPLETE_RUN)
        self.assertEqual(identity["opened_at"], "2026-08-16T09:00:00Z")
        self.assertEqual(identity["elapsed_ms"], 5400000)
        self.assertEqual(identity["terminal_status"], "complete")

    def test_an_open_run_carries_no_terminal_keys(self):
        with tempfile.TemporaryDirectory() as raw:
            sink = build_sink(Path(raw))
            identity = ui_discovery.read_run_identity(sink, OPEN_RUN)
        self.assertNotIn("terminal_at", identity)
        self.assertNotIn("elapsed_ms", identity)
        self.assertFalse(identity.get("unreadable"))

    def test_a_run_without_an_identity_document_is_absent_not_unreadable(self):
        with tempfile.TemporaryDirectory() as raw:
            sink = build_sink(Path(raw))
            self.assertIsNone(ui_discovery.read_run_identity(sink, "no-such-run"))

    def test_a_malformed_document_is_named_unreadable_and_never_raised(self):
        with tempfile.TemporaryDirectory() as raw:
            sink = build_sink(Path(raw))
            write_run(sink, "20260819T090000Z-broken", "{not json at all")
            identity = ui_discovery.read_run_identity(sink, "20260819T090000Z-broken")
        self.assertEqual(identity, {"unreadable": True})

    def test_a_json_scalar_is_unreadable_because_an_identity_is_a_document(self):
        with tempfile.TemporaryDirectory() as raw:
            sink = build_sink(Path(raw))
            write_run(sink, "20260819T090000Z-scalar", "[1, 2, 3]")
            identity = ui_discovery.read_run_identity(sink, "20260819T090000Z-scalar")
        self.assertEqual(identity, {"unreadable": True})

    def test_a_name_that_could_climb_out_of_the_runs_tree_resolves_to_nothing(self):
        with tempfile.TemporaryDirectory() as raw:
            sink = build_sink(Path(raw))
            for name in ("..", "../runs", "a/b", "", "\x00"):
                self.assertIsNone(ui_discovery.read_run_identity(sink, name), name)
