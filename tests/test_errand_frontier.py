"""Errand-lane acceptance semantics owned by orch-frontier."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "skills" / "engines" / "orch-frontier" / "SKILL.md"
PROFILES = FRONTIER.parent / "references" / "profiles.md"


def _errand_contract_gaps(frontier: str, profiles: str) -> list[str]:
    frontier_required = {
        "errand identity": "`tickets.py errand`",
        "scoped lane oracles": "ticket's scoped oracles",
        "derived closure": "derived closure is closed",
        "one terminal suite": "exactly once at the accepted terminal identity",
        "non-errand compatibility": "For every non-errand run, keep the existing policy",
    }
    profile_required = {
        "profile owner": "Running an errand terminal check",
        "engine context": "engine's own context",
        "terminal revision": "accepted terminal identity's revision",
    }
    frontier = " ".join(frontier.split())
    profiles = " ".join(profiles.split())
    return [
        name
        for name, marker in frontier_required.items()
        if marker not in frontier
    ] + [
        name for name, marker in profile_required.items() if marker not in profiles
    ]


class ErrandFrontierTests(unittest.TestCase):
    def test_errand_acceptance_is_one_terminal_suite_after_derived_closure(self):
        frontier = FRONTIER.read_text(encoding="utf-8")
        profiles = PROFILES.read_text(encoding="utf-8")

        self.assertEqual([], _errand_contract_gaps(frontier, profiles))
        self.assertIn(
            "After each merge batch run the standards owner's required checks",
            " ".join(frontier.split()),
            "the pre-existing non-errand merge-batch policy changed",
        )

    def test_terminal_suite_contract_can_fail_beside_the_tree(self):
        """The authored check discriminates wrong timing and cardinality."""
        frontier = FRONTIER.read_text(encoding="utf-8")
        profiles = PROFILES.read_text(encoding="utf-8")
        mutants = {
            "per-batch suite": frontier.replace(
                "exactly once at the accepted terminal identity",
                "after each merge batch",
                1,
            ),
            "suite before closure": frontier.replace(
                "derived closure is closed",
                "derived closure is still open",
                1,
            ),
        }

        for name, mutant in mutants.items():
            with self.subTest(name=name):
                self.assertNotEqual(frontier, mutant, "the mutant matched nothing")
                self.assertTrue(_errand_contract_gaps(mutant, profiles))


if __name__ == "__main__":
    unittest.main()
