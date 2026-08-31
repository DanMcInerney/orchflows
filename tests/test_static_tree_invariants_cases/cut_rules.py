"""Static invariants owned by cut and join rules."""
import unittest

from ._support import ROOT, read_flat

SLICE = ROOT / "skills" / "kernel" / "orch-slice" / "SKILL.md"
# The join stopped being a skill; the law that owns what it skips is the
# verification rule, and `tickets.py join-noop-repair` is what performs it.
VERIFICATION = ROOT / "rules" / "verification.md"
CODE_CRAFT = ROOT / "packs" / "orch-code-pack" / "references" / "craft.md"
DESIGN_CRAFT = ROOT / "packs" / "orch-design-pack" / "references" / "craft.md"

# Stable owner anchors for each rule, rather than whole prose sentences.
OVERLAP_ANCHORS = ("Details may overlap", "never grant authority")
CUT_GOAL_ANCHORS = ("critical path", "item an atom", "graph")
EMPTY_SET_SKIP_ANCHORS = ("gate.repair", "accepted defect set")
PROVEN_SEAM_ANCHORS = ("first frontier", "unproven")
# The member assignment shape has one owner, contracts/work-item.md; a
# pack slicing section restating it was the drift surface this guard once
# policed, so the guard now polices the restatement itself. The positive
# anchor is the one clause the code cut still owns about what a member's
# assignment carries -- a command it can run, never a number relayed from
# a reading nobody can retake. It replaced "executor-owned", which stopped
# being true when the anti-prescription law was deleted.
CURRENT_UNIT_ANCHORS = ("a measurement command in Context",)
RETIRED_SHAPE_RESTATEMENTS = (
    "one observable `Goal`",
    "optional `Details`",
    "system metadata",
)


class TestDependencyOrderedOverlap(unittest.TestCase):
    """Predicted paths are hints; actual overlap belongs to integration."""

    def test_the_owner_does_not_turn_suggested_paths_into_cut_authority(self):
        text = read_flat(SLICE)
        for anchor in OVERLAP_ANCHORS:
            self.assertIn(
                anchor, text,
                f"orch-slice, the rule's one owner, does not name "
                f"{anchor!r}, so predicted paths can still become cut-time "
                "authority",
            )

    def test_no_cut_states_a_superseded_overlap_rule(self):
        for label, path in (
            ("orch-slice", SLICE),
            ("code pack craft", CODE_CRAFT),
            ("design pack craft", DESIGN_CRAFT),
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
        text = read_flat(CODE_CRAFT)
        for anchor in ("first frontier", "riskiest", "tracer"):
            self.assertIn(
                anchor, text,
                f"code pack craft does not name {anchor!r}, so it no longer "
                "opens the first frontier with the seams the acceptance "
                "already checks and reserves the tracer for the riskiest "
                "seam the spec leaves unproven",
            )

    def test_the_code_cut_uses_the_current_unit_assignment_shape(self):
        text = read_flat(CODE_CRAFT)
        for anchor in CURRENT_UNIT_ANCHORS:
            with self.subTest(anchor=anchor):
                self.assertIn(
                    anchor, text,
                    f"code pack craft does not name {anchor!r}, so a code "
                    "cut can drift from the current work-item assignment",
                )
        for removed in (
            "runnable check commands", "oracle_class", "workspace cell",
        ) + RETIRED_SHAPE_RESTATEMENTS:
            with self.subTest(removed=removed):
                self.assertNotIn(
                    removed, text,
                    f"code pack craft still prescribes removed ticket prose "
                    f"{removed!r}",
                )


class TestCutGoalAnchors(unittest.TestCase):
    """Pin each cut goal to stable anchors in its one prose owner."""

    def test_the_decomposer_states_the_goal_by_anchor(self):
        text = read_flat(SLICE)
        for anchor in CUT_GOAL_ANCHORS:
            self.assertIn(
                anchor, text,
                f"orch-slice does not name {anchor!r}, so the cut is no "
                "longer told to minimize the critical path subject to every "
                "item an atom, or no longer returns the graph block whose "
                "numbers that goal is measured by",
            )

    def test_the_join_skips_the_repair_on_an_empty_accepted_set(self):
        text = read_flat(VERIFICATION)
        for anchor in EMPTY_SET_SKIP_ANCHORS:
            self.assertIn(
                anchor, text,
                f"rules/verification.md does not name {anchor!r}, so the join "
                "no longer completes the gate's repair itself on an empty "
                "accepted defect set and every clean run pays for a no-op "
                "dispatch on its critical path",
            )

    def test_the_slicing_sections_put_proven_seams_on_the_first_frontier(self):
        for label, path in (
            ("code pack craft", CODE_CRAFT),
            ("design pack craft", DESIGN_CRAFT),
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
