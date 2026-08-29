"""Minimum independent acceptance for single and decomposed runs."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "skills" / "engines" / "orch-frontier" / "SKILL.md"
PROFILES = FRONTIER.parent / "references" / "profiles.md"


def _gaps(frontier: str, profiles: str) -> list[str]:
    frontier = " ".join(frontier.split())
    profiles = " ".join(profiles.split())
    required = {
        "read-only checker": "one distinct read-only `orch-check` dispatch",
        "fixed evidence": "fixed artifact, Goal, Context, executor evidence",
        "separate repair": "one separate repair ticket",
        "fresh verifier": "fresh verification",
        "terminal suite": "required checks exactly once at the accepted terminal identity",
        "terminal profile": "Running the terminal required checks",
        "engine context": "engine's own context",
        "recorded revision": "accepted terminal identity's revision",
    }
    owners = {
        **{name: frontier for name in required if name not in {
            "terminal profile", "engine context", "recorded revision",
        }},
        "terminal profile": profiles,
        "engine context": profiles,
        "recorded revision": profiles,
    }
    return [name for name, anchor in required.items() if anchor not in owners[name]]


class MinimalAcceptanceTests(unittest.TestCase):
    def owners(self) -> tuple[str, str]:
        return tuple(
            path.read_text(encoding="utf-8")
            for path in (FRONTIER, PROFILES)
        )

    def test_single_and_decomposed_runs_take_only_their_minimum_path(self):
        frontier, profiles = self.owners()
        self.assertEqual([], _gaps(frontier, profiles))
        self.assertNotIn("after each merge batch", frontier.lower())
        self.assertNotIn("tickets.py errand", frontier.lower())
        self.assertNotIn("running an errand", profiles.lower())

    def test_acceptance_contract_discriminates_extra_or_self_acceptance(self):
        frontier, profiles = self.owners()
        mutants = {
            "suite per batch": (
                frontier.replace(
                    "required checks exactly once at the accepted terminal identity",
                    "required checks after each merge batch",
                    1,
                ),
                profiles,
            ),
            "checker mutates": (
                frontier.replace("one distinct read-only `orch-check` dispatch", "one correcting `orch-check` dispatch", 1),
                profiles,
            ),
        }
        for name, mutant in mutants.items():
            with self.subTest(name=name):
                self.assertNotEqual((frontier, profiles), mutant)
                self.assertTrue(_gaps(*mutant))


if __name__ == "__main__":
    unittest.main()
