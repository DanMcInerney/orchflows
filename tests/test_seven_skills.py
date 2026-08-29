"""U12 callable registry and review discriminator contract."""

from __future__ import annotations

import unittest

from scripts import tickets


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
                "orch-spec",
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


if __name__ == "__main__":
    unittest.main()
