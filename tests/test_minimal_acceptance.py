"""Minimum independent acceptance for single and decomposed runs."""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTIER = ROOT / "skills" / "engines" / "orch-frontier" / "SKILL.md"
PROFILES = FRONTIER.parent / "references" / "profiles.md"
BUILD = ROOT / "skills" / "workflows" / "orch-build" / "SKILL.md"


def _gaps(frontier: str, profiles: str, build: str) -> list[str]:
    frontier = " ".join(frontier.split())
    profiles = " ".join(profiles.split())
    build = " ".join(build.split())
    required = {
        "single run": "single-ticket run",
        "pre-existing minimum": "pre-existing-only",
        "authored checker": "`authored-here`",
        "one closer": "one fresh closer",
        "closer sequence": "orch-critique then orch-repair",
        "fresh verifier": "another fresh child",
        "terminal suite": "required checks exactly once at the accepted terminal identity",
        "terminal profile": "Running the terminal required checks",
        "engine context": "engine's own context",
        "recorded revision": "accepted terminal identity's revision",
        "build gate deferral": "`independence: gate` defers",
        "ordered bundle": "ordered lens bundle",
    }
    owners = {
        **{name: frontier for name in required if name not in {
            "terminal profile", "engine context", "recorded revision",
            "build gate deferral", "ordered bundle",
        }},
        "terminal profile": profiles,
        "engine context": profiles,
        "recorded revision": profiles,
        "build gate deferral": build,
        "ordered bundle": build,
    }
    return [name for name, anchor in required.items() if anchor not in owners[name]]


class MinimalAcceptanceTests(unittest.TestCase):
    def owners(self) -> tuple[str, str, str]:
        return tuple(
            path.read_text(encoding="utf-8")
            for path in (FRONTIER, PROFILES, BUILD)
        )

    def test_single_and_decomposed_runs_take_only_their_minimum_path(self):
        frontier, profiles, build = self.owners()
        self.assertEqual([], _gaps(frontier, profiles, build))
        self.assertNotIn("after each merge batch", frontier.lower())
        self.assertNotIn("tickets.py errand", frontier.lower())
        self.assertNotIn("running an errand", profiles.lower())
        self.assertNotIn("gate the result", build.lower())

    def test_acceptance_contract_discriminates_extra_or_self_acceptance(self):
        frontier, profiles, build = self.owners()
        mutants = {
            "suite per batch": (
                frontier.replace(
                    "required checks exactly once at the accepted terminal identity",
                    "required checks after each merge batch",
                    1,
                ),
                profiles,
                build,
            ),
            "closer verifies itself": (
                frontier.replace("another fresh child", "the same closer", 1),
                profiles,
                build,
            ),
            "build reviews locally": (
                frontier,
                profiles,
                build.replace(
                    "`independence: gate` defers",
                    "`independence: gate` reviews locally before",
                    1,
                ),
            ),
        }
        for name, mutant in mutants.items():
            with self.subTest(name=name):
                self.assertNotEqual((frontier, profiles, build), mutant)
                self.assertTrue(_gaps(*mutant))


if __name__ == "__main__":
    unittest.main()
