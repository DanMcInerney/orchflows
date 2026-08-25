"""The single-lens gate default: one critique-repair chain, no repair stub.

A composite gate with exactly one critique lens has nothing to pool: the
one critique's findings are already the whole repair bill, so the repair
rides the same child as a stated `sequence` (rules/delegation.md §4) and
the family collapses to two stubs -- the chained critique, then verify.
Several lenses keep the separate repair stub: pooled findings take one fix
per shared cause, and a per-lens critique that owned its own repair bill
would have an incentive to soften findings. These cases pin both halves,
and the cutcheck reading that makes the two-stub set lawful on disk.

Fixtures come from `tests.test_tickets_gate`, the gate family's authority
pins, so the chained stub is graded against the same root that grades the
three-stub family.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.cutcheck as cutcheck  # noqa: E402
import scripts.tickets as tickets_mod  # noqa: E402
from tests.test_tickets_gate import (  # noqa: E402
    ROOT_EXCLUSIONS,
    ROOT_INPUTS,
    input_lines,
    make_run,
    record_names,
    root_text,
    run_cmd,
    sections_of,
    use_sink,
)

CHAIN = ["orch-critique", "orch-repair"]


def single_gate(*extra):
    return run_cmd("gate", "testrun", "R", "--lens", "code", *extra)


def multi_gate(*extra):
    return run_cmd("gate", "testrun", "R", "--lens", "code,style", *extra)


def stub_of(run_dir: Path, tid: str) -> str:
    return (run_dir / f"{tid}.md").read_text(encoding="utf-8")


def frontmatter(run_dir: Path, tid: str) -> dict:
    return tickets_mod._parse_frontmatter(stub_of(run_dir, tid))


class SingleLensGateCollapsesToAChainTest(unittest.TestCase):
    """Exactly one lens: two stubs, the critique carrying the repair."""

    def test_exactly_the_critique_and_verify_stubs_are_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(use_sink(Path(tmp)), root_text())
            payload = single_gate()
            self.assertNotIn("error", payload)
            self.assertEqual(
                ["R.gate.critique.code", "R.gate.verify"], payload["gate"]["ids"]
            )
            self.assertEqual(
                ["R.gate.critique.code.md", "R.gate.verify.md"],
                sorted(path.name for path in run_dir.glob("R.gate.*.md")),
                "no separate repair stub is emitted for a single lens",
            )

    def test_the_critique_states_the_chain_and_stays_the_critique(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(use_sink(Path(tmp)), root_text())
            self.assertNotIn("error", single_gate())
            data = frontmatter(run_dir, "R.gate.critique.code")
            self.assertEqual("orch-critique", data.get("executor"))
            self.assertEqual(CHAIN, data.get("sequence"))

    def test_the_chained_critique_holds_the_repairs_authority(self):
        """What the repair stub used to inherit reaches the chain instead:
        the gate scope as `write_scope` (with its mutation plan), and the
        root's isolation and exclusions byte-for-byte."""

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(use_sink(Path(tmp)), root_text())
            self.assertNotIn("error", single_gate())
            data = frontmatter(run_dir, "R.gate.critique.code")
            self.assertEqual(["scripts/", "tests/"], data.get("write_scope"))
            self.assertEqual(
                ["write:scripts/", "write:tests/"], data.get("mutations")
            )
            self.assertEqual("required", data.get("isolation"))
            self.assertEqual(ROOT_EXCLUSIONS, data.get("excluded_actions"))

    def test_the_root_input_records_reach_the_chained_critique_verbatim(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(use_sink(Path(tmp)), root_text())
            self.assertNotIn("error", single_gate())
            carried = input_lines(stub_of(run_dir, "R.gate.critique.code"))
            for record in ROOT_INPUTS:
                self.assertIn(record, carried)

    def test_the_chained_ticket_states_the_repair_halfs_criteria(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(use_sink(Path(tmp)), root_text())
            self.assertNotIn("error", single_gate())
            completion = sections_of(stub_of(run_dir, "R.gate.critique.code"))[
                "Completion test"
            ]
            self.assertIn("accepted blocking finding", completion)
            self.assertIn("nothing outside the write scope changed", completion)

    def test_the_verify_depends_on_the_critique_and_reads_its_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(use_sink(Path(tmp)), root_text())
            self.assertNotIn("error", single_gate())
            text = stub_of(run_dir, "R.gate.verify")
            data = tickets_mod._parse_frontmatter(text)
            self.assertEqual(["R.gate.critique.code"], data.get("depends_on"))
            records = [
                json.loads(line[len("- input: "):]) for line in input_lines(text)
            ]
            repaired = next(r for r in records if r["name"] == "repair-result")
            self.assertEqual(
                "R.gate.critique.code", repaired["identity"]["ticket"]
            )
            self.assertIn("`R.gate.critique.code` left", text)

    def test_every_chained_stub_is_a_defect_free_ticket(self):
        """The sequence grammar (`sequence_defects`) and the generator agree:
        what `gate` writes is what `new`, `ready` and `packet` accept."""

        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(use_sink(Path(tmp)), root_text())
            self.assertNotIn("error", single_gate())
            for tid in ("R.gate.critique.code", "R.gate.verify"):
                with self.subTest(stub=tid):
                    self.assertEqual(
                        [], tickets_mod.ticket_defects(stub_of(run_dir, tid))
                    )


class MultiLensGateIsUnchangedTest(unittest.TestCase):
    """Two or more lenses keep today's three-kind family, byte for byte."""

    def test_two_lenses_emit_the_three_kind_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(use_sink(Path(tmp)), root_text())
            payload = multi_gate()
            self.assertNotIn("error", payload)
            self.assertEqual(
                ["R.gate.critique.code", "R.gate.critique.style",
                 "R.gate.repair", "R.gate.verify"],
                payload["gate"]["ids"],
            )

    def test_no_multi_lens_stub_carries_a_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(use_sink(Path(tmp)), root_text())
            payload = multi_gate()
            self.assertNotIn("error", payload)
            for path in payload["gate"]["paths"]:
                with self.subTest(stub=Path(path).stem):
                    data = tickets_mod._parse_frontmatter(
                        Path(path).read_text(encoding="utf-8")
                    )
                    self.assertIsNone(data.get("sequence"))

    def test_the_multi_lens_edges_still_run_through_the_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run(use_sink(Path(tmp)), root_text())
            self.assertNotIn("error", multi_gate())
            critiques = frontmatter(run_dir, "R.gate.critique.code")
            self.assertEqual([], critiques.get("write_scope"))
            repair = frontmatter(run_dir, "R.gate.repair")
            self.assertEqual(
                ["R.gate.critique.code", "R.gate.critique.style"],
                sorted(repair.get("depends_on")),
            )
            verify = frontmatter(run_dir, "R.gate.verify")
            self.assertEqual(["R.gate.repair"], verify.get("depends_on"))


class CutcheckReadsTheActualStubSetTest(unittest.TestCase):
    """Family 6 accepts both lawful families and still convicts the gaps.

    Cutcheck reads the other ingress -- legacy or manually assembled sets --
    so the two-stub shape is lawful only where the chain is stated, and the
    three-stub single-lens family already on disk stays lawful as it was.
    """

    @staticmethod
    def siblings(*, chained=True, sequence=None, verify_depends=None):
        critique = "R.gate.critique.code"
        items = {
            "R": {
                "id": "R", "executor": "orch-decompose",
                "depends_on": [], "write_scope": ["scripts/one.py"],
            },
            "R.01": {
                "id": "R.01", "executor": "orch-tdd", "independence": "gate",
                "depends_on": [], "write_scope": ["scripts/one.py"],
            },
            critique: {
                "id": critique, "executor": "orch-critique",
                "depends_on": ["R.01"],
                "write_scope": ["scripts/one.py"] if chained else [],
            },
            "R.gate.verify": {
                "id": "R.gate.verify", "executor": "orch-verify",
                "depends_on": verify_depends or [critique],
                "write_scope": [],
            },
        }
        if sequence is not None:
            items[critique]["sequence"] = list(sequence)
        if not chained:
            items["R.gate.repair"] = {
                "id": "R.gate.repair", "executor": "orch-repair",
                "depends_on": [critique], "write_scope": ["scripts/one.py"],
            }
            items["R.gate.verify"]["depends_on"] = ["R.gate.repair"]
        return items

    def test_the_two_stub_chained_family_is_a_lawful_layout(self):
        findings = cutcheck._root_gate_layout(self.siblings(sequence=CHAIN))
        self.assertEqual([], findings, findings)

    def test_a_missing_repair_without_the_chain_stays_malformed(self):
        findings = cutcheck._root_gate_layout(self.siblings())
        self.assertEqual(
            [cutcheck.MALFORMED_GATE], [finding[2] for finding in findings],
            findings,
        )

    def test_the_legacy_three_stub_single_lens_family_stays_lawful(self):
        findings = cutcheck._root_gate_layout(self.siblings(chained=False))
        self.assertEqual([], findings, findings)

    def test_a_chained_verify_must_depend_on_the_critique(self):
        findings = cutcheck._root_gate_layout(
            self.siblings(sequence=CHAIN, verify_depends=["R.gate.repair"])
        )
        self.assertEqual(
            [cutcheck.MALFORMED_GATE], [finding[2] for finding in findings],
            findings,
        )


if __name__ == "__main__":
    unittest.main()
