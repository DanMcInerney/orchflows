"""`## Carry`: the digested conclusions a dispatch inlines for a successor.

The measured gap this closes: a packet hands a fresh executor ~1.9k tokens
and the executor then re-gathers ~153k, most of it conclusions its
dependencies already paid for. The section is executor-owned and optional
— required, it would convict every ticket already in the sink — and
`packet` inlines each dependency's Carry into the successor's prompt.

Self-contained by write scope, like `tests/test_tickets_packet_checker.py`:
fixtures are built from `tests.test_tickets_cases.common`'s primitives
rather than by extending that chain's shared bodies.
"""

import tempfile
import unittest
from pathlib import Path

from tests.test_tickets_cases.common import run_cmd, use_sink
import scripts.tickets as tickets_mod

CARRY_BODY = (
    "- decision: the parser keeps the v1 grammar.\n"
    "- hazard: bare python is a Store stub on this host.\n"
    "- re-measure: uv run --no-project python tools/check_source_sizes.py"
)

DEP_TICKET = """---
id: D1
run: testrun
status: complete
executor: orch-tdd
pack: orch-code-pack
depends_on: []
write_scope: scratch/d1.txt
bound: 30m
claimed_by: agent-d
claimed_at: 2099-01-01T00:00:00Z
---

## Objective

Land the parser.

## Fixed inputs

None.

## Completion test

1. `python -m unittest` exits 0. Oracle: that command. oracle_class: deterministic.

## Return fields

status.

## Result

Parser landed at abc123.

## Verification

1. PASS.

## Feedback

[]

## Risks

[]

## Carry

{carry}
"""

DEP_WITHOUT_CARRY = DEP_TICKET.replace("## Carry\n\n{carry}\n", "")

SUCCESSOR_TICKET = """---
id: T1
run: testrun
status: claimed
executor: orch-tdd
pack: orch-code-pack
depends_on: [D1]
write_scope: scratch/t1.txt
bound: 30m
claimed_by: agent-a
claimed_at: 2099-01-01T00:00:00Z
---

## Objective

Extend the parser.

## Fixed inputs

None.

## Completion test

1. `python -m unittest` exits 0. Oracle: that command. oracle_class: deterministic.

## Return fields

status, changed_artifacts, verification.

## Risks

[]

## Handoff

parked once for a scope question.
"""


def make_repo(tmp: Path, *tickets) -> Path:
    """A checkout at ``tmp`` and this test's tickets in its own sink."""

    (tmp / ".git").mkdir()
    run_dir = use_sink(tmp) / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    for name, body in tickets:
        (run_dir / f"{name}.md").write_text(body, encoding="utf-8")
    return run_dir


def packet_prompt(tmp: Path, *extra) -> str:
    payload = run_cmd(tmp, "packet", "testrun", "T1", "--reply-to", "main", *extra)
    assert "error" not in payload, payload
    return payload["packet"]["prompt"]


class TestCarryIsFiledLikeAnyExecutorSection(unittest.TestCase):
    """`result --section Carry` works with the machinery it already has."""

    def test_carry_files_onto_a_claimed_ticket_between_risks_and_handoff(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(tmp, ("T1", SUCCESSOR_TICKET))
            payload = run_cmd(
                tmp, "result", "testrun", "T1", "--section", "Carry",
                "--text", "- landed: abc123",
            )
            self.assertEqual("Carry", payload["result"]["section"], payload)
            text = (run_dir / "T1.md").read_text(encoding="utf-8")
            self.assertIn("## Carry\n\n- landed: abc123\n", text)
            self.assertLess(text.index("## Risks"), text.index("## Carry"))
            self.assertLess(text.index("## Carry"), text.index("## Handoff"))

    def test_a_ticket_without_carry_has_no_section_defect(self):
        """Optional twice over: a new section that is retroactively required
        would convict every ticket already in the sink."""

        self.assertEqual([], tickets_mod.ticket_defects(DEP_WITHOUT_CARRY))
        self.assertIn("Carry", tickets_mod.EXECUTOR_SECTIONS)
        self.assertNotIn("Carry", tickets_mod.REQUIRED_SECTIONS)
        self.assertNotIn("Handoff", tickets_mod.REQUIRED_SECTIONS)

    def test_result_is_still_required(self):
        gutted = DEP_WITHOUT_CARRY.replace("## Result\n\nParser landed at abc123.\n", "")
        self.assertIn("no '## Result' section", tickets_mod.ticket_defects(gutted))


class TestPacketInlinesTheDependencysCarry(unittest.TestCase):
    """The dispatch prompt carries conclusions, never pointers."""

    def test_a_dependencys_carry_rides_the_prompt_after_the_head_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(
                tmp, ("T1", SUCCESSOR_TICKET),
                ("D1", DEP_TICKET.format(carry=CARRY_BODY)),
            )
            lines = packet_prompt(tmp).splitlines()
            self.assertIn("Apply skill orch-tdd", lines[0])
            self.assertIn("complete delegation packet", lines[1])
            self.assertTrue(
                lines[2].startswith("Carried context from D1 (complete): "), lines[2]
            )
            # flattened to one single-spaced line, content intact
            self.assertIn("the parser keeps the v1 grammar.", lines[2])
            self.assertIn(
                "- hazard: bare python is a Store stub on this host. - re-measure:",
                lines[2],
            )

    def test_a_complete_dependency_without_carry_yields_the_pointer_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_dir = make_repo(
                tmp, ("T1", SUCCESSOR_TICKET), ("D1", DEP_WITHOUT_CARRY),
            )
            prompt = packet_prompt(tmp)
            self.assertNotIn("Carried context from D1", prompt)
            (pointer,) = [
                line for line in prompt.splitlines()
                if line.startswith("Dependency D1 is complete but filed no `## Carry`")
            ]
            self.assertIn("`## Result`", pointer)
            self.assertIn(str(run_dir / "D1.md"), pointer)

    def test_a_missing_sibling_degrades_to_silence_not_refusal(self):
        """Context, never authority: the packet stands on the ticket's own
        fixed inputs, so a degraded sibling costs the carry line alone."""

        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, ("T1", SUCCESSOR_TICKET))
            prompt = packet_prompt(tmp)
            self.assertNotIn("Carried context", prompt)
            self.assertNotIn("Dependency D1", prompt)

    def test_dependencies_are_carried_in_frontmatter_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(
                tmp,
                ("T1", SUCCESSOR_TICKET.replace("depends_on: [D1]", "depends_on: [D2, D1]")),
                ("D1", DEP_TICKET.format(carry=CARRY_BODY)),
                ("D2", DEP_TICKET.replace("id: D1", "id: D2").format(carry="- edge: D2 went first.")),
            )
            prompt = packet_prompt(tmp)
            self.assertLess(
                prompt.index("Carried context from D2"),
                prompt.index("Carried context from D1"),
            )


class TestTheCloseOrdersACarryFiling(unittest.TestCase):
    """The instruction rides the close law's own condition: a primary skill
    executor files a Carry at close; a further §10 child files none."""

    def test_a_primary_packet_orders_the_carry_filing(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, ("T1", SUCCESSOR_TICKET))
            prompt = packet_prompt(tmp)
            self.assertIn("file `## Carry`", prompt)
            self.assertIn("--section Carry", prompt)
            self.assertIn("never narrative", prompt)

    def test_a_further_child_packet_does_not(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            make_repo(tmp, ("T1", SUCCESSOR_TICKET))
            prompt = packet_prompt(tmp, "--executor", "orch-critique")
            self.assertNotIn("file `## Carry`", prompt)
            self.assertNotIn("--section Carry", prompt)


if __name__ == "__main__":
    unittest.main()
