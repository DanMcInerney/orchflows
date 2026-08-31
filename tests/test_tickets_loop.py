"""The loop stub's arm/evaluate/advance protocol and its replay after a kill."""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import tickets
from scripts import state_root


TEMPLATE_MANIFEST = """---
name: loop-probe
description: synthetic loop composition exercising the driver protocol.
entry: named
placeholders: [probe]
---

One loop stub whose done-check is a deterministic command.
"""

LOOP_STUB = """---
id: L1
executor: orch-execute
loop: true
done: {"form":"command","value":"{{probe}}"}
pack: orch-code-pack
depends_on: []
bound: 30m
independence: checker
isolation: required
---

## Goal

Converge the probe artifact until the done command exits 0.

## Context

- input: the probe script decides done off its sibling marker file.

## Report
"""

PROBE_SCRIPT = (
    "import pathlib, sys\n"
    "sys.exit(0 if (pathlib.Path(__file__).resolve().parent / 'marker').exists() else 1)\n"
)


class LoopStubProtocolTest(unittest.TestCase):
    def setUp(self):
        self._sink = tempfile.TemporaryDirectory()
        self.addCleanup(self._sink.cleanup)
        self._previous = os.environ.get(state_root.ENV_VAR)
        os.environ[state_root.ENV_VAR] = self._sink.name

        def restore():
            if self._previous is None:
                os.environ.pop(state_root.ENV_VAR, None)
            else:
                os.environ[state_root.ENV_VAR] = self._previous

        self.addCleanup(restore)
        self._work = tempfile.TemporaryDirectory()
        self.addCleanup(self._work.cleanup)
        work = Path(self._work.name)
        template = work / "loop-probe"
        template.mkdir()
        (template / "template.md").write_text(TEMPLATE_MANIFEST, encoding="utf-8")
        (template / "L1.md").write_text(LOOP_STUB, encoding="utf-8")
        self.probe = work / "probe.py"
        self.probe.write_text(PROBE_SCRIPT, encoding="utf-8")
        self.marker = work / "marker"
        command = f"{Path(sys.executable).as_posix()} {self.probe.as_posix()}"
        result = tickets._dispatch([
            "instantiate", str(template), "--run", "looprun",
            "--set", f"probe={command}",
        ])
        self.assertNotIn("error", result, result)

    def _loop(self, command):
        return tickets._dispatch([command, "looprun", "L1"])

    def _close_iteration(self, ticket_id, status="complete", result_text=""):
        if result_text:
            root = Path(self._sink.name) / "tickets" / "looprun" / f"{ticket_id}.md"
            text = root.read_text(encoding="utf-8")
            root.write_text(
                text.replace("## Report\n", f"## Report\n\n{result_text}\n", 1),
                encoding="utf-8",
            )
        closed = tickets._dispatch(["set-status", "looprun", ticket_id, status])
        self.assertNotIn("error", closed, closed)

    def test_arm_creates_the_next_iteration_and_replays_while_it_is_live(self):
        armed = self._loop("loop-arm")
        self.assertEqual(
            {"run": "looprun", "id": "L1", "iteration": 1,
             "ticket": "L1.iter.1", "outcome": "created"},
            armed["loop_arm"],
        )
        # A kill between arm and dispatch replays, never double-arms.
        self.assertEqual("replayed", self._loop("loop-arm")["loop_arm"]["outcome"])
        iteration = Path(self._sink.name) / "tickets" / "looprun" / "L1.iter.1.md"
        text = iteration.read_text(encoding="utf-8")
        self.assertIn("Converge the probe artifact", text)
        self.assertIn("done-check (command):", text)
        self.assertIn("assignment_seal: sha256:", text)

    def test_evaluate_follows_the_landed_iteration_only(self):
        self._loop("loop-arm")
        pending = self._loop("loop-evaluate")
        self.assertIn("not terminal", pending["error"])
        self._close_iteration("L1.iter.1")
        reading = self._loop("loop-evaluate")["loop_evaluate"]
        self.assertFalse(reading["done"])
        self.assertEqual(1, reading["exit"])

    def test_advance_rearms_then_closes_complete_on_the_done_reading(self):
        self._loop("loop-arm")
        self._close_iteration("L1.iter.1", result_text="Revision r1 delivered.")
        advanced = self._loop("loop-advance")["loop_advance"]
        self.assertEqual({"run": "looprun", "id": "L1", "action": "arm", "next": 2}, advanced)
        self.assertEqual(2, self._loop("loop-arm")["loop_arm"]["iteration"])
        self._close_iteration("L1.iter.2", result_text="Revision r2 delivered.")
        self.marker.write_text("", encoding="utf-8")
        closed = self._loop("loop-advance")["loop_advance"]
        self.assertEqual("closed", closed["action"])
        self.assertEqual("complete", closed["status"])
        # Advance replays idempotently after a kill: the closed stub reports
        # its terminal state instead of re-deriving a transition.
        replay = self._loop("loop-advance")["loop_advance"]
        self.assertEqual({"run": "looprun", "id": "L1", "action": "closed",
                          "status": "complete", "outcome": "replayed"}, replay)
        self.assertIn("terminal", self._loop("loop-arm")["error"])

    def test_two_iterations_without_a_result_delta_exit_stalled(self):
        self._loop("loop-arm")
        self._close_iteration("L1.iter.1")
        self.assertEqual("arm", self._loop("loop-advance")["loop_advance"]["action"])
        self._loop("loop-arm")
        self._close_iteration("L1.iter.2")
        closed = self._loop("loop-advance")["loop_advance"]
        self.assertEqual("closed", closed["action"])
        self.assertEqual("stalled", closed["status"])

    def test_a_ticket_without_a_loop_object_is_refused(self):
        result = tickets._dispatch(["loop-arm", "looprun", "missing"])
        self.assertIn("not found", result["error"])


if __name__ == "__main__":
    unittest.main()
