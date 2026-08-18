"""Cases for topology's atom and checker-family contract."""

import unittest

from tests.test_contracts_cases.support import read_clause_flat

import scripts.cutcheck as cutcheck  # noqa: E402  topology section 3 cites it


class TopologyAtomTest(unittest.TestCase):
    """The cut law owned by rules/topology.md section 3."""

    def section(self):
        return read_clause_flat("rules/topology.md", 3)

    def test_section_3_states_the_atom_the_edge_rule_and_the_shared_surface_rule(self):
        text = self.section()
        self.assertRegex(
            text, r"\batom\b",
            "topology.md §3 does not name the atom, the unit the lawful set "
            "is cut into",
        )
        for token, why in (
            (
                "finest",
                "does not make the lawful set the finest cut, so it states no "
                "polarity and a coarser cut stays a safe default",
            ),
            (
                "family 1",
                "does not tie the discriminating completion test to the checker "
                "family that reports its absence",
            ),
            (
                "family 3",
                "does not tie the closed write scope to its checker family",
            ),
            (
                "family 4",
                "does not tie the sibling-read prohibition to its checker family",
            ),
            (
                "`scripts/cutcheck.py`",
                "names checker families without naming the checker that owns them",
            ),
            (
                "compound item",
                "does not name what an item coarser than an atom is",
            ),
            (
                "`## Fixed inputs`",
                "'s edge rule does not name the cited-identity half, so an edge "
                "carrying no oracle read has no other justification",
            ),
            (
                "result identity",
                "'s edge rule does not say what a fixed input cites to earn an edge",
            ),
            (
                "ordering preference",
                "does not refuse the edge drawn for ordering preference",
            ),
            (
                "exactly one item",
                "does not give an artifact more than one item would write to "
                "exactly one item",
            ),
            (
                "`ARCHITECTURE.md`",
                "'s shared-surface rule names no recurring surface, so a cutter "
                "rediscovers them",
            ),
            (
                "`SKILL.md`",
                "'s shared-surface rule does not name the roster case",
            ),
            (
                "`tests/pins.json`",
                "'s shared-surface rule does not name the pin-file case",
            ),
        ):
            with self.subTest(token=token):
                self.assertIn(token, text, f"topology.md §3 {why}")

    def test_section_3_family_cites_answer_to_the_checker(self):
        text = self.section()
        for family, classes, conjunct in (
            (
                cutcheck.FAMILY,
                (
                    cutcheck.ALREADY_PASSES,
                    cutcheck.NO_HITS_BOTH_REVISIONS,
                    cutcheck.FAILS_BOTH_REVISIONS,
                    cutcheck.UNCONFINED_ORACLE,
                    cutcheck.WHOLE_SUITE_ORACLE,
                    cutcheck.UNRUNNABLE_ORACLE,
                ),
                "a completion test discriminating the item alone",
            ),
            (
                cutcheck.FAMILY_3,
                (
                    cutcheck.UNSCOPED_WRITE,
                    cutcheck.SCOPE_CONTRADICTION,
                    cutcheck.SCOPE_OPEN,
                ),
                "a closed write scope",
            ),
            (
                cutcheck.FAMILY_4,
                (cutcheck.SCOPE_COLLISION, cutcheck.STAGED_INVALIDATION),
                "oracles reading nothing a sibling writes",
            ),
        ):
            with self.subTest(family=family):
                self.assertIn(
                    family, text,
                    f"topology.md §3 no longer cites {family!r}, the checker "
                    f"family that reports {conjunct}",
                )
                for name in classes:
                    self.assertEqual(
                        cutcheck.FAMILY_OF[name], family,
                        f"cutcheck grades {name!r} under "
                        f"{cutcheck.FAMILY_OF[name]!r}, while topology.md §3 "
                        f"sends a reader of {conjunct} to {family!r}",
                    )

    def test_section_3_bounds_the_cut_below_and_binds_an_ad_hoc_set(self):
        text = self.section()
        for token, why in (
            (
                "padding",
                "does not name what lies below the atom, so the finest-cut "
                "polarity has no floor",
            ),
            (
                "unbounded",
                "does not leave the item count unbounded above",
            ),
            (
                "frontier's queue",
                "does not send width past the host profile to the frontier's "
                "queue instead of back into the cut",
            ),
            (
                "ad-hoc set",
                "does not bind the ad-hoc set, the form every wide cut in the "
                "sink was made in",
            ),
            (
                "first dispatch",
                "does not order the cut check before an ad-hoc set's first dispatch",
            ),
        ):
            with self.subTest(token=token):
                self.assertIn(token, text, f"topology.md §3 {why}")
        self.assertNotIn(
            "look thorough", text,
            "topology.md §3 still forces a cut only under parallelism, "
            "disjoint scopes, isolation or resumption — the clause the atom "
            "bound replaces",
        )
