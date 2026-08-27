"""Static invariants owned by cut and join rules."""
import unittest

from ._support import ROOT, read_flat

DECOMPOSE = ROOT / "skills" / "kernel" / "orch-decompose" / "SKILL.md"
INTEGRATE = ROOT / "skills" / "kernel" / "orch-integrate" / "SKILL.md"
CODE_SLICING = ROOT / "packs" / "orch-code-pack" / "references" / "slicing.md"
DESIGN_SLICING = ROOT / "packs" / "orch-design-pack" / "references" / "slicing.md"

# Stable owner anchors for each rule, rather than whole prose sentences.
OVERLAP_ANCHORS = ("Suggested files may overlap", "never grant authority")
CUT_GOAL_ANCHORS = ("critical path", "item an atom", "graph")
EMPTY_SET_SKIP_ANCHORS = ("gate.repair", "accepted defect set")
PROVEN_SEAM_ANCHORS = ("first frontier", "unproven")


class TestDependencyOrderedOverlap(unittest.TestCase):
    """Predicted paths are hints; actual overlap belongs to integration."""

    def test_the_owner_does_not_turn_suggested_paths_into_cut_authority(self):
        text = read_flat(DECOMPOSE)
        for anchor in OVERLAP_ANCHORS:
            self.assertIn(
                anchor, text,
                f"orch-decompose, the rule's one owner, does not name "
                f"{anchor!r}, so predicted paths can still become cut-time "
                "authority",
            )

    def test_no_cut_states_a_superseded_overlap_rule(self):
        for label, path in (
            ("orch-decompose", DECOMPOSE),
            ("code pack slicing", CODE_SLICING),
            ("design pack slicing", DESIGN_SLICING),
        ):
            text = read_flat(path)
            self.assertNotIn(
                "disjoint from its siblings", text,
                f"{label} still states the old global-disjointness rule, which "
                "forces layer-shaped cuts",
            )
            self.assertNotIn(
                "sharing its frontier", text,
                f"{label} still scopes overlap by frontier; siblings in "
                "different frontiers can be concurrently in flight and collide",
            )

    def test_the_code_cut_reserves_the_tracer_for_the_unproven_seam(self):
        text = read_flat(CODE_SLICING)
        for anchor in ("first frontier", "riskiest", "tracer"):
            self.assertIn(
                anchor, text,
                f"code pack slicing does not name {anchor!r}, so it no longer "
                "opens the first frontier with the seams the acceptance "
                "already checks and reserves the tracer for the riskiest "
                "seam the spec leaves unproven",
            )


class TestCutGoalAnchors(unittest.TestCase):
    """Pin each cut goal to stable anchors in its one prose owner."""

    def test_the_decomposer_states_the_goal_by_anchor(self):
        text = read_flat(DECOMPOSE)
        for anchor in CUT_GOAL_ANCHORS:
            self.assertIn(
                anchor, text,
                f"orch-decompose does not name {anchor!r}, so the cut is no "
                "longer told to minimize the critical path subject to every "
                "item an atom, or no longer returns the graph block whose "
                "numbers that goal is measured by",
            )

    def test_the_join_skips_the_repair_on_an_empty_accepted_set(self):
        text = read_flat(INTEGRATE)
        for anchor in EMPTY_SET_SKIP_ANCHORS:
            self.assertIn(
                anchor, text,
                f"orch-integrate does not name {anchor!r}, so the join no "
                "longer completes the gate's repair itself on an empty "
                "accepted defect set and every clean run pays for a no-op "
                "dispatch on its critical path",
            )

    def test_the_slicing_cells_put_proven_seams_on_the_first_frontier(self):
        for label, path in (
            ("code pack slicing", CODE_SLICING),
            ("design pack slicing", DESIGN_SLICING),
        ):
            text = read_flat(path)
            for anchor in PROVEN_SEAM_ANCHORS:
                with self.subTest(cell=label, anchor=anchor):
                    self.assertIn(
                        anchor, text,
                        f"{label} does not name {anchor!r}, so it no longer "
                        "opens the first frontier with the work the "
                        "acceptance already proves and reserves the tracer "
                        "for what the spec leaves unproven",
                    )
