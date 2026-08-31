"""Callable registry census and review discriminator contract."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts import tickets
from scripts import tickets_registry as registry
from scripts.tickets_shapes import (
    DISPATCH_LAUNCH_FIELDS, DISPATCH_RECORD_VALUES, LAUNCH_RECORD_ID,
)

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
    def test_callable_registry_is_exactly_the_six_enforced_verbs(self):
        self.assertEqual(
            (
                "orch-execute",
                "orch-check",
                "orch-decompose",
                "orch-integrate",
                "orch-frontier",
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
        so a caller holding the old name is not left to guess which of six
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
                # A successor is a registered verb to bind, or the mechanism
                # that replaced the verb, named as the remedy it is.
                if successor not in registry.EXECUTOR_REGISTRY:
                    self.assertIn(successor, registry.executor_refusal(superseded))
        # The absorbed loop engine refuses toward the loop field mechanism.
        loop_refusal = registry.executor_refusal("orch-loop")
        self.assertIn("superseded", loop_refusal)
        self.assertIn("loop-arm", loop_refusal)
        self.assertNotIn("bind '", loop_refusal)

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

    def test_the_declared_launch_shape_is_the_invocation_and_nothing_else(self):
        """The one object a dispatch emits, which the persisted-record
        validator closes every committed launch against. It carries the host
        binding and the prompt; the wire's twenty-one fields, and every
        identity it restated from the attempt, are not fields at all any
        more."""

        self.assertEqual(
            ("host", "verb", "agent", "model", "effort", "fields", "prompt"),
            DISPATCH_LAUNCH_FIELDS,
        )
        for retired in (
            "form", "inline", "review_kind", "durability", "source",
            "assignment_seal", "dispatch_id", "assigned_name", "workspace",
        ):
            with self.subTest(retired=retired):
                self.assertNotIn(retired, DISPATCH_LAUNCH_FIELDS)
        self.assertIn("launch", DISPATCH_RECORD_VALUES["kind"])
        self.assertNotIn("packet", DISPATCH_RECORD_VALUES["kind"])
        self.assertEqual("launch", LAUNCH_RECORD_ID)


if __name__ == "__main__":
    unittest.main()
