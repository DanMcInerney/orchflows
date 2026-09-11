"""Documentation checks for the coverage seam."""

from __future__ import annotations

import unittest
from pathlib import Path
import contextlib
import io

import acquire


SKILL_ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = SKILL_ROOT / "references" / "protocol.md"


class ProtocolDocTest(unittest.TestCase):
    """The step grammar's owner states the two fields this review joins by."""

    def test_the_protocol_states_what_a_step_result_echoes(self):
        """Read as backticked names in the paragraph that states the shape.

        A caller assembling or reading an artifact by hand has only this file
        to learn from that a `StepResult` says what its step was, and the
        review's whole correctness now rests on those two fields being filled.
        The wrong result this fails against is the owner describing a
        `StepResult` that carries neither — the state in which every reader
        downstream went back to guessing. Paragraph-scoped rather than
        line-scoped so a reflow of the prose cannot fail it.
        """

        body = PROTOCOL_PATH.read_text(encoding="utf-8")
        stated = [block for block in body.split("\n\n") if "`StepResult`" in block]

        self.assertTrue(stated, "protocol.md stopped naming `StepResult`")
        self.assertTrue(
            any("`kind`" in block and "`query`" in block for block in stated),
            "protocol.md names `StepResult` and not the `kind` and `query` it carries",
        )


class SkillDocTest(unittest.TestCase):
    def test_the_owner_names_the_call_a_caller_would_make(self):
        """The routine CLI replaces manual helper calls; its documented flags work."""
        body = (SKILL_ROOT / "references/acquisition.md").read_text(encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as stopped:
            acquire.main(["--help"])
        self.assertEqual(stopped.exception.code, 0)
        for flag in ("--plan", "--output", "--selection"):
            self.assertIn(flag, output.getvalue())
            self.assertIn(flag, body)
