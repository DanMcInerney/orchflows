"""Minimum independent acceptance for single and decomposed runs.

The path used to be one engine's body. The engine is gone -- the driver
runs `tickets.py dispatch` and `tickets.py land` and nothing else -- so the
same minimum is pinned at the two owners it moved to: `rules/verification.md`
for the independence path a ticket walks, and `hosts/profiles.md` for whose
context the terminal required checks run in.
"""

from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFICATION = ROOT / "rules" / "verification.md"
PROFILES = ROOT / "hosts" / "profiles.md"


def _gaps(verification: str, profiles: str) -> list[str]:
    verification = " ".join(verification.split())
    profiles = " ".join(profiles.split())
    required = {
        "read-only checker": "distinct read-only `orch-check` dispatch",
        "separate repair": "one separate\nrepair ticket",
        "clean closes unrepaired": "closes with no repair at all",
        # the fresh outside check, which is no longer a child: `land` runs
        # the target's own predicate in the integrated tree
        "checked done": "the ticket's `done` predicate, in the tree land has just merged",
        "no standing child": "never from a standing verification",
        "empty set skips the repair": "join-noop-repair",
        "terminal profile": "Running the terminal required checks",
        "driver context": "driving session's own context",
        "recorded revision": "accepted terminal identity's revision",
    }
    owners = {
        **{name: verification for name in required if name not in {
            "terminal profile", "driver context", "recorded revision",
        }},
        "terminal profile": profiles,
        "driver context": profiles,
        "recorded revision": profiles,
    }
    return [
        name for name, anchor in required.items()
        if " ".join(anchor.split()) not in owners[name]
    ]


class MinimalAcceptanceTests(unittest.TestCase):
    def owners(self) -> tuple[str, str]:
        return tuple(
            path.read_text(encoding="utf-8")
            for path in (VERIFICATION, PROFILES)
        )

    def test_single_and_decomposed_runs_take_only_their_minimum_path(self):
        verification, profiles = self.owners()
        self.assertEqual([], _gaps(verification, profiles))
        # The retired names are not revived anywhere on this path: the join
        # is `land` and the driver is the session that runs it.
        for retired in ("orch-frontier", "orch-integrate"):
            with self.subTest(retired=retired):
                self.assertNotIn(retired, verification)
                self.assertNotIn(retired, profiles)

    def test_acceptance_contract_discriminates_extra_or_self_acceptance(self):
        verification, profiles = self.owners()
        mutants = {
            "checker mutates": (
                verification.replace(
                    "distinct read-only `orch-check` dispatch",
                    "correcting `orch-check` dispatch",
                    1,
                ),
                profiles,
            ),
            "clean target pays for a repair": (
                verification.replace(
                    "closes with no repair at all", "closes with one repair", 1
                ),
                profiles,
            ),
            "suite per run rather than per identity": (
                verification,
                profiles.replace("identity's revision", "run's revision", 1),
            ),
        }
        for name, mutant in mutants.items():
            with self.subTest(name=name):
                self.assertNotEqual((verification, profiles), mutant)
                self.assertTrue(_gaps(*mutant))


if __name__ == "__main__":
    unittest.main()
