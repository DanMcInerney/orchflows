"""Successor ``## Context`` hydration and legacy ``## Carry`` provenance."""

import tempfile
import unittest
from pathlib import Path

from tests.test_tickets_cases.common import run_cmd, use_sink


CONTEXT_BODY = "- state: parser v2 landed at abc123.\n- watch: re-run parser smoke after grammar changes."
LEGACY_BODY = "- parser v1 landed.\n- bare python is a Store stub."

DEP_TICKET = """---
id: D1
run: testrun
status: {status}
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
{sections}
"""

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
"""


def dependency(*, status="complete", context=None, carry=None):
    sections = ""
    if context is not None:
        sections += f"\n## Context\n\n{context}\n"
    if carry is not None:
        sections += f"\n## Carry\n\n{carry}\n"
    return DEP_TICKET.format(status=status, sections=sections)


def make_repo(tmp: Path, *tickets) -> Path:
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


class TestSuccessorContextHydration(unittest.TestCase):
    def test_canonical_context_is_flattened_with_status(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            make_repo(tmp, ("T1", SUCCESSOR_TICKET), ("D1", dependency(context=CONTEXT_BODY)))
            line = packet_prompt(tmp).splitlines()[2]
            self.assertEqual(
                "Successor context from D1 (complete): "
                "- state: parser v2 landed at abc123. "
                "- watch: re-run parser smoke after grammar changes.",
                line,
            )

    def test_legacy_carry_is_hydrated_with_explicit_provenance(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            make_repo(tmp, ("T1", SUCCESSOR_TICKET), ("D1", dependency(carry=LEGACY_BODY)))
            prompt = packet_prompt(tmp)
            self.assertIn("Legacy `## Carry` context from D1 (complete):", prompt)
            self.assertIn("- parser v1 landed. - bare python is a Store stub.", prompt)

    def test_context_wins_deterministically_in_mixed_history(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            make_repo(
                tmp,
                ("T1", SUCCESSOR_TICKET),
                ("D1", dependency(context=CONTEXT_BODY, carry="legacy must not win")),
            )
            prompt = packet_prompt(tmp)
            self.assertIn("Successor context from D1 (complete):", prompt)
            self.assertNotIn("legacy must not win", prompt)
            self.assertNotIn("Legacy `## Carry` context", prompt)

    def test_complete_absence_points_to_result_and_nonterminal_absence_is_silent(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            run_dir = make_repo(tmp, ("T1", SUCCESSOR_TICKET), ("D1", dependency()))
            prompt = packet_prompt(tmp)
            self.assertIn("filed no `## Context`", prompt)
            self.assertIn("`## Result`", prompt)
            self.assertIn(str(run_dir / "D1.md"), prompt)
            (run_dir / "D1.md").write_text(dependency(status="suspended"), encoding="utf-8")
            self.assertNotIn("Dependency D1", packet_prompt(tmp))

    def test_dependency_order_is_preserved_and_unreadable_siblings_are_silent(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            successor = SUCCESSOR_TICKET.replace("depends_on: [D1]", "depends_on: [D2, BAD, D1]")
            run_dir = make_repo(
                tmp,
                ("T1", successor),
                ("D1", dependency(context="- state: D1 second.")),
                ("D2", dependency(context="- watch: D2 first." ).replace("id: D1", "id: D2")),
            )
            (run_dir / "BAD.md").write_bytes(b"\xff\xfe")
            prompt = packet_prompt(tmp)
            self.assertLess(prompt.index("from D2"), prompt.index("from D1"))
            self.assertNotIn("BAD", prompt)


class TestPrimaryCloseGuidance(unittest.TestCase):
    def test_primary_close_requests_only_terse_state_watch_context(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            make_repo(tmp, ("T1", SUCCESSOR_TICKET))
            prompt = packet_prompt(tmp)
            self.assertIn("file `## Context`", prompt)
            self.assertIn("--section Context", prompt)
            self.assertIn("section is optional", prompt)
            self.assertIn("only when a successor needs a conclusion", prompt)
            self.assertIn("otherwise omit it", prompt)
            self.assertIn("one to five non-empty `- state:`/`- watch:` bullets", prompt)
            self.assertNotIn("file `## Carry`", prompt)

    def test_further_child_gets_no_context_filing_instruction(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            make_repo(tmp, ("T1", SUCCESSOR_TICKET))
            prompt = packet_prompt(tmp, "--executor", "orch-critique")
            self.assertNotIn("file `## Context`", prompt)
            self.assertNotIn("--section Context", prompt)


if __name__ == "__main__":
    unittest.main()
