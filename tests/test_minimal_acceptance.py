"""Minimum independent acceptance for single and decomposed runs.

The path used to be one engine's body. The engine is gone -- the driver
runs `tickets.py dispatch` and `tickets.py land` and nothing else -- so the
same minimum is pinned at the owner it moved to: `rules/verification.md`,
which carries both the independence path a ticket walks and where the
repository-wide checks are confirmed. `hosts/profiles.md` restated the
second half until this run deleted the copy; it is still read here only to
prove the retired driver names stay gone from it.
"""

from __future__ import annotations

import unittest


from tests._repo_root import ROOT
VERIFICATION = ROOT / "rules" / "verification.md"
PROFILES = ROOT / "hosts" / "profiles.md"


def _gaps(verification: str) -> list[str]:
    verification = " ".join(verification.split())
    required = {
        # The checker/repair three-state path retired with the command that
        # built its ledger (`review_v1`'s `GatePlan`-then-`CritiqueAdjudication`
        # chain): independence is the caller's own join now, one path for
        # every ticket, never a standing verification child.
        "single independence path": "Independence is the caller's own join",
        # the fresh outside check, which is no longer a child: `land` runs
        # the target's own predicate in the integrated tree
        "checked done": "the ticket's `done` predicate, in the tree land has just merged",
        # and it is confirmed once there, never inside a unit's own work --
        # the fact `hosts/profiles.md` used to restate.
        "one confirmation": "once, at `land`, never inside a unit's own work",
    }
    return [
        name for name, anchor in required.items()
        if " ".join(anchor.split()) not in verification
    ]


class MinimalAcceptanceTests(unittest.TestCase):
    def owners(self) -> tuple[str, str]:
        return tuple(
            path.read_text(encoding="utf-8")
            for path in (VERIFICATION, PROFILES)
        )

    def test_single_and_decomposed_runs_take_only_their_minimum_path(self):
        verification, profiles = self.owners()
        self.assertEqual([], _gaps(verification))
        # The retired names are not revived anywhere on this path: the join
        # is `land` and the driver is the session that runs it.
        for retired in ("orch-frontier", "orch-integrate"):
            with self.subTest(retired=retired):
                self.assertNotIn(retired, verification)
                self.assertNotIn(retired, profiles)

    def test_acceptance_contract_discriminates_extra_or_self_acceptance(self):
        verification, _ = self.owners()
        mutants = {
            "independence handed back to the executor": verification.replace(
                "Independence is the caller's own join",
                "Independence is the executor's own claim",
                1,
            ),
            "confirmation pushed back inside each unit": verification.replace(
                "once, at `land`, never inside a unit's own work",
                "inside every unit's own work",
                1,
            ),
        }
        for name, mutant in mutants.items():
            with self.subTest(name=name):
                self.assertNotEqual(verification, mutant)
                self.assertTrue(_gaps(mutant))


if __name__ == "__main__":
    unittest.main()
