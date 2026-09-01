"""Static invariants owned by cut and join rules."""
import unittest

from ._support import ROOT, read_flat

CODE_CRAFT = ROOT / "packs" / "orch-code-pack" / "references" / "craft.md"
DESIGN_CRAFT = ROOT / "packs" / "orch-design-pack" / "references" / "craft.md"

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

    def test_no_cut_states_a_superseded_overlap_rule(self):
        for label, path in (
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
