"""The done command's first word is resolved on PATH before it is spawned.

A predicate naming `pnpm run probe` died on Windows with a `[WinError 2]`
while the same predicate naming `node` ran: node ships an `.exe`, pnpm and
npm ship `.CMD` shims, and a spawn without a shell searches PATH for `.exe`
alone. `tickets.py land` and `frame-close --done` both read their command
through `tickets_done._command_reading`, so this one seam is both doors.

Its own module beside `test_ticket_done_predicate.py`: that module tests the
predicate inside the composition that lands it, standing a run up per case,
and these read the runner directly with no ticket in sight.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import tickets_done

WINDOWS_ONLY = "a .CMD shim is only a shim on Windows"


class DoneCommandSpawnTest(unittest.TestCase):
    def _on_path(self, name: str, body: str) -> None:
        """Put one fake command on this process's PATH for one test."""

        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        (Path(directory.name) / name).write_text(body, encoding="utf-8")
        patch = mock.patch.dict(
            os.environ,
            {"PATH": directory.name + os.pathsep + os.environ["PATH"]},
        )
        patch.start()
        self.addCleanup(patch.stop)

    @unittest.skipUnless(os.name == "nt", WINDOWS_ONLY)
    def test_a_cmd_shim_on_path_runs_like_any_other_first_word(self):
        self._on_path("orchflows-shim.CMD", "@echo off\r\nexit /b 0\r\n")

        reading, refusal = tickets_done._command_reading(
            "orchflows-shim run probe", None,
        )

        self.assertIsNone(refusal, refusal)
        self.assertEqual(0, reading["exit"])
        self.assertIs(True, reading["done"])
        # reported as the ticket froze it, never as the path the spawn used
        self.assertEqual("orchflows-shim run probe", reading["command"])

    @unittest.skipUnless(os.name == "nt", WINDOWS_ONLY)
    def test_a_cmd_shims_own_exit_code_is_the_verdict(self):
        self._on_path("orchflows-shim-red.CMD", "@echo off\r\nexit /b 3\r\n")

        reading, refusal = tickets_done._command_reading(
            "orchflows-shim-red", None,
        )

        self.assertIsNone(refusal, refusal)
        self.assertEqual(3, reading["exit"])
        self.assertIs(False, reading["done"])

    def test_a_first_word_on_no_path_entry_is_refused_by_name(self):
        """Named, not handed back as an OSError a reader cannot act on."""

        reading, refusal = tickets_done._command_reading(
            "orchflows-nothing-resolves-this --frozen", None,
        )

        self.assertIsNone(reading)
        self.assertIn("orchflows-nothing-resolves-this", refusal["error"])
        self.assertIn("on no PATH entry", refusal["error"])
        self.assertNotIn("failed to run", refusal["error"])
        self.assertNotIn("WinError", refusal["error"])
