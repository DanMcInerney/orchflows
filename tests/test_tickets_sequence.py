"""`sequence`: one child, several exact named skills, one witness.

rules/delegation.md 4's chain: a ticket may state an ordered `sequence`
of skills whose head is its `executor`; one fresh child executes each
in that order in one context, at the one role rules/roles.md 4 resolves
there -- so a continuation declaring another role is work to run, not a
mismatch to refuse. The chain never buys its own acceptance --
verification.md 11 voids a verdict the chain renders on work it changed
-- so the prompt prices that, and the seal binds the chain
(delegation 15): an edited `sequence` is a new generation.

Self-contained by write scope, like `tests/test_tickets_context.py`:
fixtures from `tests.test_tickets_cases.common`'s primitives.
"""

import tempfile
import unittest
from pathlib import Path

from tests.test_tickets_cases.common import run_cmd, use_sink
import scripts.tickets as tickets_mod
from scripts.tickets_sequence import sequence_defects
from scripts.tickets_generations import assignment_payload

CHAIN_TICKET = """---
id: G1
run: testrun
status: claimed
executor: orch-critique
sequence: [orch-critique, orch-repair]
pack: orch-code-pack
depends_on: []
write_scope: scratch/g1.txt
bound: 30m
claimed_by: gate-a
claimed_at: 2099-01-01T00:00:00Z
---

## Objective

Review the result set, then repair the accepted findings.

## Fixed inputs

None.

## Completion test

1. `python -m unittest` exits 0. Oracle: that command. oracle_class: deterministic.

## Return fields

status, changed_artifacts, verification.

## Result

## Verification

## Feedback

[]

## Risks

[]
"""

PLAIN_TICKET = CHAIN_TICKET.replace(
    "sequence: [orch-critique, orch-repair]\n", ""
)


def graded(sequence, executor="orch-critique"):
    return sequence_defects(sequence, executor)


def make_repo(tmp: Path, *tickets) -> Path:
    (tmp / ".git").mkdir()
    run_dir = use_sink(tmp) / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    for name, body in tickets:
        (run_dir / f"{name}.md").write_text(body, encoding="utf-8")
    return run_dir


def packet_prompt(tmp: Path, *extra) -> str:
    payload = run_cmd(tmp, "packet", "testrun", "G1", "--reply-to", "main", *extra)
    assert "error" not in payload, payload
    return payload["packet"]["prompt"]


class TestTheChainGrammarIsGraded(unittest.TestCase):
    """A `sequence` is refused malformed at format grading, not at dispatch."""

    def test_a_lawful_chain_has_no_defect(self):
        self.assertEqual([], graded((["orch-critique", "orch-repair"])))
        self.assertEqual([], tickets_mod.ticket_defects(CHAIN_TICKET))

    def test_an_absent_sequence_is_the_plain_ticket(self):
        self.assertEqual([], sequence_defects(None, "orch-critique"))
        self.assertEqual([], tickets_mod.ticket_defects(PLAIN_TICKET))

    def test_the_head_must_be_the_executor(self):
        (defect,) = graded((["orch-repair", "orch-critique"]))
        self.assertIn("head 'orch-repair' is not the ticket's executor", defect)

    def test_a_repeated_skill_is_a_defect(self):
        defects = graded((["orch-critique", "orch-critique"]))
        self.assertTrue(any("repeats a skill" in d for d in defects), defects)

    def test_a_single_entry_chain_is_the_plain_executor(self):
        (defect,) = graded((["orch-critique"]))
        self.assertIn("fewer than two skills", defect)

    def test_a_script_step_is_not_a_chain_entry(self):
        defects = graded(["orch-critique", "script:tools/x.py"])
        self.assertTrue(
            any("not an exact orch-* skill name" in d for d in defects), defects
        )


class TestTheChainRidesThePacket(unittest.TestCase):
    """The dispatch prompt states the order, the price, and the read path."""

    def test_a_chain_packet_states_order_price_and_read_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, ("G1", CHAIN_TICKET))
            prompt = packet_prompt(tmp)
            lines = prompt.splitlines()
            self.assertIn("Apply skill orch-critique", lines[0])
            self.assertIn(
                "executor sequence: apply orch-critique, then orch-repair", lines[2]
            )
            self.assertIn("never re-dispatch any of them", lines[2])
            self.assertIn("This chain runs at one role", prompt)
            self.assertIn("The chain is one witness", prompt)
            self.assertIn("rules/verification.md §11", prompt)
            self.assertIn("forks a packet-less child that must refuse", prompt)

    def test_the_chain_packet_binds_its_continuation_to_the_head_role(self):
        """The one place the child meets `orch-repair`'s `role: worker`.

        Without this line the role agent's "refuse a missing or
        mismatched role" and that declaration agree on refusing the
        second half of the child's own ticket.
        """

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, ("G1", CHAIN_TICKET))
            prompt = packet_prompt(tmp)
            self.assertIn("its head's — the role that established you", prompt)
            self.assertIn("rules/roles.md §4", prompt)
            self.assertIn("is not a mismatch here", prompt)

    def test_a_plain_packet_carries_no_chain_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, ("G1", PLAIN_TICKET))
            prompt = packet_prompt(tmp)
            self.assertNotIn("executor sequence", prompt)
            self.assertNotIn("This chain runs at one role", prompt)
            self.assertNotIn("The chain is one witness", prompt)

    def test_a_further_child_packet_never_continues_the_chain(self):
        """A verification.md 10 child reviews the chain's result; handing it
        the chain would re-run the work it exists to judge."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, ("G1", CHAIN_TICKET))
            payload = run_cmd(
                tmp, "packet", "testrun", "G1", "--reply-to", "main",
                "--by", "verify-1", "--executor", "orch-verify",
            )
            self.assertNotIn("error", payload)
            self.assertNotIn("executor sequence", payload["packet"]["prompt"])


class TestTheSealBindsTheChain(unittest.TestCase):
    """delegation.md 15: `sequence` seals with the executor."""

    def test_the_assignment_digest_moves_with_the_sequence(self):
        sealed = assignment_payload("G1", CHAIN_TICKET)
        self.assertEqual(
            ["orch-critique", "orch-repair"], sealed["authority"]["sequence"]
        )
        alone = assignment_payload("G1", PLAIN_TICKET)
        self.assertNotIn("sequence", alone["authority"])
        self.assertNotEqual(sealed, alone)


if __name__ == "__main__":
    unittest.main()
