"""The loop stub's arm/evaluate/advance protocol, and the trunk it crosses.

Two halves, because the lane broke exactly where they were never joined.
`LoopStubProtocolTest` drives the scripts-only protocol -- arm, evaluate,
advance, replay after a kill -- which is the whole of what the loop
machinery was proved against before the dispatch trunk existed.
`LoopRoundAdmissionTest` and `LoopCheckRoundAdmissionTest` drive an armed
round through `ready` and the dispatch admission door, which is where every
loop refused on its first real run.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from scripts import tickets
from scripts import state_root
from scripts.tickets_context import graded_admission, run_snapshot
from scripts.tickets_dispatch_guards import admission_failure


TEMPLATE_MANIFEST = """---
name: loop-probe
description: synthetic loop composition exercising the driver protocol.
entry: named
placeholders: [probe]
---

One loop stub whose done-check is a deterministic command.
"""

COMMAND_DONE = '{"form":"command","value":"{{probe}}"}'
CHECK_DONE = '{"form":"check","value":"The probe artifact converged."}'

LOOP_STUB = """---
id: L1
executor: orch-execute
loop: true
done: DONE_BINDING
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

# An author-written child of the loop stub: it is an id-descendant like a
# round is, and it is not a round, so it is what tells the shape exemption
# from a hole in the shape check.
AUTHORED_CHILD = """---
id: L1.extra
run: looprun
status: pending
executor: orch-execute
pack: orch-code-pack
depends_on: []
bound: 30m
independence: checker
isolation: none
---

## Goal

A hand-authored child of a loop stub, which is not one of its rounds.

## Context

- input: written straight into the run directory.

## Report
"""


class LoopSinkTest(unittest.TestCase):
    """The temp sink, sealed loop template, and probe every case runs on."""

    DONE = COMMAND_DONE

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
        (template / "L1.md").write_text(
            LOOP_STUB.replace("DONE_BINDING", self.DONE), encoding="utf-8",
        )
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

    def _run_dir(self):
        return Path(self._sink.name) / "tickets" / "looprun"

    def _close_iteration(self, ticket_id, status="complete", result_text=""):
        if result_text:
            root = self._run_dir() / f"{ticket_id}.md"
            text = root.read_text(encoding="utf-8")
            root.write_text(
                text.replace("## Report\n", f"## Report\n\n{result_text}\n", 1),
                encoding="utf-8",
            )
        closed = tickets._dispatch(["set-status", "looprun", ticket_id, status])
        self.assertNotIn("error", closed, closed)

    def _codes(self, ticket_id):
        """The admission finding codes one ticket carries right now."""

        snapshot, failures = run_snapshot(self._run_dir())
        self.assertEqual([], failures, failures)
        grade = graded_admission(
            ticket_id, snapshot[ticket_id], snapshot, "looprun",
        )
        return {str(item["code"]) for item in grade["findings"]}


class LoopStubProtocolTest(LoopSinkTest):
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


class LoopRoundAdmissionTest(LoopSinkTest):
    """An armed round crosses `ready` and the dispatch admission door.

    Neither reading was ever taken before the trunk existed: the sealed cut
    is written at instantiate and a round is minted after it, so the sealed
    set can never name a round; and a round is an id-descendant of its stub
    by construction, so the graph shape read an armed stub as a
    non-decomposed root owning members. Both fired on the same first run.
    """

    def test_ready_promotes_the_armed_round_and_the_stub_owns_no_members(self):
        armed = self._loop("loop-arm")["loop_arm"]
        self.assertEqual("L1.iter.1", armed["ticket"])
        promoted = tickets._dispatch(["ready", "--run", "looprun"])
        self.assertNotIn("error", promoted, promoted)
        self.assertIn(
            "L1.iter.1", {item["id"] for item in promoted["ready"]}, promoted,
        )
        self.assertEqual([], promoted["skipped"], promoted["skipped"])
        path = self._run_dir() / "L1.iter.1.md"
        text = path.read_text(encoding="utf-8")
        self.assertIsNone(admission_failure(
            path, text, tickets._parse_frontmatter(text), "looprun", "L1.iter.1",
        ))

    def test_a_round_edited_after_it_was_armed_is_bound_by_nothing(self):
        self._loop("loop-arm")
        self.assertEqual(set(), self._codes("L1.iter.1"))
        path = self._run_dir() / "L1.iter.1.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "Converge the probe artifact", "Converge the probe artifacts", 1,
            ),
            encoding="utf-8",
        )
        self.assertIn("sealed-assignment-mismatch", self._codes("L1.iter.1"))

    def test_a_hand_authored_child_of_a_loop_stub_is_still_refused(self):
        self._loop("loop-arm")
        self.assertEqual(set(), self._codes("L1"))
        (self._run_dir() / "L1.extra.md").write_text(
            AUTHORED_CHILD, encoding="utf-8",
        )
        self.assertIn("graph-direct-members", self._codes("L1"))

    def test_a_round_whose_stub_the_seal_does_not_name_is_refused(self):
        self._loop("loop-arm")
        self.assertEqual(set(), self._codes("L1.iter.1"))
        stub = self._run_dir() / "L1.md"
        stub.write_text(tickets._set_frontmatter_field(
            stub.read_text(encoding="utf-8"), "assignment_seal",
            "sha256:" + "0" * 64,
        ), encoding="utf-8")
        self.assertIn("sealed-loop-stub-mismatch", self._codes("L1.iter.1"))


class LoopCheckRoundAdmissionTest(LoopSinkTest):
    """The judge the `check` done form mints binds through the same stub.

    `loop-evaluate` mints `<round>.done` after the round lands, later still
    than the round itself, and it is an id-descendant of both the round and
    the stub. It is the second id the loop machinery writes past the seal,
    and it crosses admission through the one ticket the seal did name.
    """

    DONE = CHECK_DONE

    def test_the_minted_done_check_and_its_round_both_admit(self):
        self._loop("loop-arm")
        self._close_iteration("L1.iter.1", result_text="Revision r1 delivered.")
        reading = self._loop("loop-evaluate")["loop_evaluate"]
        self.assertEqual("L1.iter.1.done", reading["pending"])
        for ticket_id in ("L1", "L1.iter.1", "L1.iter.1.done"):
            self.assertEqual(set(), self._codes(ticket_id), ticket_id)


if __name__ == "__main__":
    unittest.main()
