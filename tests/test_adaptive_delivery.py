"""Freezes dependency-ordered overlap: an item's write scope may overlap
only siblings it is dependency-ordered with, so items with no dependency
path between them can never collide however the frontier schedules them.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECOMPOSE = ROOT / "skills" / "kernel" / "orch-decompose" / "SKILL.md"
CODE_SLICING = ROOT / "packs" / "orch-code-pack" / "references" / "slicing.md"
DESIGN_SLICING = ROOT / "packs" / "orch-design-pack" / "references" / "slicing.md"

OVERLAP_RULE = "a write scope overlapping only siblings it is dependency-ordered with"


def read_flat(path):
    """File text with whitespace collapsed, so wrapped clauses match."""
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8"))


class AdaptiveDeliveryTests(unittest.TestCase):
    def test_ordered_cuts_may_overlap(self):
        for label, path in (
            ("orch-decompose", DECOMPOSE),
            ("code pack slicing", CODE_SLICING),
            ("design pack slicing", DESIGN_SLICING),
        ):
            text = read_flat(path)
            self.assertIn(
                OVERLAP_RULE, text,
                f"{label} does not permit overlap only along dependency order",
            )
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

        code_slicing = read_flat(CODE_SLICING)
        self.assertIn(
            "the first frontier carries the riskiest seam's tracer", code_slicing,
            "code pack slicing does not put the riskiest seam's tracer in the "
            "first frontier",
        )


if __name__ == "__main__":
    unittest.main()
