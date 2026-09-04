"""Callable registry census and review discriminator contract."""

from __future__ import annotations

import unittest

from tests._repo_root import ROOT
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
    def test_callable_registry_is_exactly_the_two_callables(self):
        """`orch-slice` retired in W4a together with the instantiate layer
        that was its only minter of decomposed roots (`ROOT_EXECUTOR` in
        `scripts/tickets_format.py` is gone with it): the two minting
        commands are the whole callable tier now."""

        self.assertEqual(
            (
                "orch-do",
                "orch-judge",
            ),
            tickets.CALLABLE_EXECUTORS,
        )

    def test_the_retired_driver_verbs_refuse_toward_the_mechanical_trunk(self):
        """`orch-frontier` and `orch-integrate` were the driver and the join.
        Neither is a skill any more: `tickets.py dispatch` and `tickets.py
        land` are, so the refusal names the commands rather than a verb the
        caller could bind instead."""

        frontier = registry.executor_refusal("orch-frontier")
        self.assertIn("superseded", frontier)
        self.assertIn("tickets.py dispatch", frontier)
        self.assertIn("tickets.py land", frontier)
        self.assertNotIn("bind '", frontier)
        integrate = registry.executor_refusal("orch-integrate")
        self.assertIn("superseded", integrate)
        self.assertIn("land --status", integrate)
        self.assertNotIn("bind '", integrate)

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
        self.assertTrue(any("orch-judge" in defect for defect in defects))

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
        self.assertIn("planning `do`", refusals[0])
        self.assertEqual(
            registry.SUPERSEDED_EXECUTORS["orch-outline"],
            registry.executor_successor("orch-spec"),
        )
        self.assertEqual(
            registry.SUPERSEDED_EXECUTORS["orch-outline"],
            registry.executor_successor("`orch-spec`"),
        )
        # orch-do is the live registered verb, not a superseded name.
        self.assertIsNone(registry.executor_successor("orch-do"))
        self.assertFalse(registry.executor_registered("orch-spec"))
        # An ordinary unknown still gets the registry list, not a remedy that
        # does not exist: the two refusals must not collapse into one.
        unknown = registry.executor_refusal("orch-verify")
        self.assertNotIn("superseded", unknown)
        self.assertIn("orch-do", unknown)
        self.assertIn("orch-judge", unknown)
        for superseded, successor in registry.SUPERSEDED_EXECUTORS.items():
            with self.subTest(superseded=superseded):
                self.assertNotIn(superseded, registry.EXECUTOR_REGISTRY)
                # A successor is a registered verb to bind, or the mechanism
                # that replaced the verb, named as the remedy it is.
                if successor not in registry.EXECUTOR_REGISTRY:
                    self.assertIn(successor, registry.executor_refusal(superseded))
        # The loop lane is gone: the refusal names the mechanism that
        # replaced it -- prose over callables and land's `done` predicate --
        # rather than the arm/evaluate/advance commands W3a deleted.
        loop_refusal = registry.executor_refusal("orch-loop")
        self.assertIn("superseded", loop_refusal)
        self.assertIn("do` callables", loop_refusal)
        self.assertIn("tickets.py land", loop_refusal)
        self.assertNotIn("loop-arm", loop_refusal)
        self.assertNotIn("bind '", loop_refusal)

    def test_the_outline_and_slice_executors_collapse_to_one_remedy(self):
        """`orch-outline` retired as a verb in wave 3; `orch-slice` retires
        in W4a together with the instantiate layer that was its only
        minter of decomposed roots. Both leave their standard behind as the
        planning `do` making a root or cut toward the standard's Lens
        entry for that kind (`research/lego-design-2026-08-31.md`, then
        `research/lens-keying-2026-09-02.md`), and both
        predecessors -- `orch-spec` and `orch-decompose` -- refuse toward
        that same living remedy rather than toward a name that itself
        refuses."""

        remedy = (
            "a planning `do` making a `root` or `cut` toward the standard's "
            "`## Lens` entry for that kind"
        )
        for retired in ("orch-outline", "orch-spec", "orch-slice", "orch-decompose"):
            with self.subTest(retired=retired):
                self.assertEqual(remedy, registry.executor_successor(retired))
                refusal = registry.executor_refusal(retired)
                self.assertIn("superseded", refusal)
                self.assertIn(remedy, refusal)
                self.assertNotIn("bind '", refusal)

    def test_do_and_judge_require_standard_authority(self):
        text = """---
id: R
run: r
status: pending
executor: orch-do
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
        self.assertTrue(any("executor-standard-required" in defect for defect in tickets.ticket_defects(text)))
        judged = text.replace("executor: orch-do", "executor: orch-judge")
        self.assertTrue(any("executor-standard-required" in defect for defect in tickets.ticket_defects(judged)))

    def test_shipped_callable_skill_packages_are_exactly_registry(self):
        root = ROOT / "skills"
        shipped = {
            path.parent.name
            for path in root.rglob("SKILL.md")
            if path.parent.name.startswith("orch-")
        }
        self.assertEqual(set(tickets.CALLABLE_EXECUTORS), shipped)

    def test_each_standard_carries_its_absorbed_execution_family(self):
        root = ROOT / "standards"
        expected = {
            "orch-code": ("checks answer to goal", "repair", "conflict"),
            "orch-content": ("draft", "assembly", "cut log"),
            "orch-data": ("pipeline", "reproduce", "leakage"),
            "orch-design": ("view identities", "capture", "golden"),
            "orch-research": ("primary sources", "synthesize", "gaps"),
        }
        for standard, markers in expected.items():
            text = (root / standard / "STANDARD.md").read_text(encoding="utf-8").lower()
            for marker in markers:
                with self.subTest(standard=standard, marker=marker):
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
