"""U12 callable registry and review discriminator contract."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts import tickets
from scripts import tickets_registry as registry
from scripts.tickets_attempts import PROTOCOL
from scripts.tickets_dispatch_packet_shape import packet_shape

# One well-formed ticket with the executor left open, so a refusal case
# differs from a passing one in the executor alone.
_TICKET = """---
id: R
run: r
status: pending
executor: EXECUTOR
depends_on: []
bound: 10m
---

## Goal

Deliver one result.

## Context

[]

## Result

## Verification

## Feedback

[]

## Risks

[]
"""


class CallableRegistryTests(unittest.TestCase):
    def test_callable_registry_is_exactly_the_seven_enforced_verbs(self):
        self.assertEqual(
            (
                "orch-execute",
                "orch-check",
                "orch-decompose",
                "orch-integrate",
                "orch-frontier",
                "orch-loop",
                "orch-outline",
            ),
            tickets.CALLABLE_EXECUTORS,
        )

    def test_superseded_executor_is_rejected_with_named_registry(self):
        text = """---
id: R
run: r
status: pending
executor: orch-verify
depends_on: []
bound: 10m
---

## Goal

Deliver one result.

## Context

[]

## Result

## Verification

## Feedback

[]

## Risks

[]
"""
        defects = tickets.ticket_defects(text)
        self.assertTrue(any("executor-unregistered" in defect for defect in defects))
        self.assertTrue(any("orch-check" in defect for defect in defects))

    def test_a_superseded_verb_is_refused_naming_its_successor(self):
        """rules/delegation.md 8: no dispatch may revive a superseded skill
        binding. The refusal carries the remedy rather than the registry list,
        so a caller holding the old name is not left to guess which of seven
        replaced it."""

        text = _TICKET.replace("EXECUTOR", "orch-spec")

        defects = tickets.ticket_defects(text)

        refusals = [defect for defect in defects if "executor-unregistered" in defect]
        self.assertEqual(1, len(refusals), defects)
        self.assertIn("orch-spec", refusals[0])
        self.assertIn("superseded", refusals[0])
        self.assertIn("orch-outline", refusals[0])
        self.assertEqual(
            "orch-outline", registry.executor_successor("orch-spec")
        )
        self.assertEqual("orch-outline", registry.executor_successor("`orch-spec`"))
        self.assertIsNone(registry.executor_successor("orch-outline"))
        self.assertFalse(registry.executor_registered("orch-spec"))
        # An ordinary unknown still gets the registry list, not a remedy that
        # does not exist: the two refusals must not collapse into one.
        unknown = registry.executor_refusal("orch-verify")
        self.assertNotIn("superseded", unknown)
        self.assertIn("orch-outline", unknown)
        for superseded, successor in registry.SUPERSEDED_EXECUTORS.items():
            with self.subTest(superseded=superseded):
                self.assertNotIn(superseded, registry.EXECUTOR_REGISTRY)
                self.assertIn(successor, registry.EXECUTOR_REGISTRY)

    def test_execute_and_check_require_pack_authority(self):
        text = """---
id: R
run: r
status: pending
executor: orch-execute
depends_on: []
bound: 10m
---

## Goal

Deliver one result.

## Context

[]

## Result

## Verification

## Feedback

[]

## Risks

[]
"""
        self.assertTrue(any("executor-pack-required" in defect for defect in tickets.ticket_defects(text)))

    def test_shipped_callable_skill_packages_are_exactly_registry(self):
        root = Path(__file__).resolve().parents[1] / "skills"
        shipped = {
            path.parent.name
            for path in root.rglob("SKILL.md")
            if path.parent.name.startswith("orch-")
        }
        self.assertEqual(set(tickets.CALLABLE_EXECUTORS), shipped)

    def test_pack_craft_carries_each_absorbed_execution_family(self):
        root = Path(__file__).resolve().parents[1] / "packs"
        expected = {
            "orch-code-pack": ("checks answer to goal", "repair", "conflict"),
            "orch-content-pack": ("draft", "assembly", "cut log"),
            "orch-data-pack": ("pipeline", "reproduce", "leakage"),
            "orch-design-pack": ("view identities", "capture", "golden"),
            "orch-research-pack": ("primary sources", "synthesize", "gaps"),
        }
        for pack, markers in expected.items():
            text = (root / pack / "references" / "craft.md").read_text(encoding="utf-8").lower()
            for marker in markers:
                with self.subTest(pack=pack, marker=marker):
                    self.assertIn(marker, text)

    def test_packet_shape_requires_typed_review_kind_field(self):
        packet = {
            "protocol": PROTOCOL,
            "source": {"id": "T", "run": "r"},
            "dispatch_id": "d-1",
            "assignment_seal": "sha256:" + "a" * 64,
            "outcome_record_id": "outcome",
            "lease_expires_at": "2026-08-29T12:00:00Z",
            "executor": "orch-check",
            "role": "planner",
            "profile": "orch-planner",
            "assigned_name": "checker",
            "reply_to": "root",
            "workspace": None,
            "pack": "orch-code-pack",
            "independence": "checker",
            "isolation": "none",
            "admission": "sha256:" + "b" * 64,
            "prompt": "check",
            "review_kind": "critique",
            "form": "reference",
            "durability": "ticket",
            "reference": {"id": "T", "run": "r"},
        }
        self.assertIsNone(packet_shape(packet))
        packet.pop("review_kind")
        self.assertIsNotNone(packet_shape(packet))


if __name__ == "__main__":
    unittest.main()
