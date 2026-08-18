"""Faithful-copy clauses required by verification's can-fail law."""

import re
import tempfile
import unittest
from pathlib import Path

from ._support import ROOT, clause

VERIFICATION = ROOT / "rules" / "verification.md"
LENS = ROOT / "skills" / "kernel" / "orch-decompose" / "references" / "cut-lens.md"

# What the faithfulness clause has to state, keyed to the measurement that
# named it: `git archive` drops `.git`, which silently moved 61-65
# test_cutcheck verdicts; runtime indicts a copy only when short.
_FAITHFULNESS_CLAUSE = {
    "what a faithful copy preserves": ("faithful", "oracle", "unchanged"),
    "clone, never extract": ("clone", "extract", "`.git`"),
    "the one direction runtime indicts in": ("shorter", "longer"),
    "the fingerprint that settles which revision was read": (
        "`git rev-list --count`",
        "which revision",
    ),
}

_RECIPE_HEADING = "## Proving a copy"


def _faithfulness_gaps(lens_text):
    """Return parts of the faithfulness clause absent from lens_text."""
    flat = re.sub(r"\s+", " ", lens_text)
    return sorted(
        name
        for name, phrases in _FAITHFULNESS_CLAUSE.items()
        if not all(phrase in flat for phrase in phrases)
    )


class CopyFaithfulnessClauseTest(unittest.TestCase):
    """The cut lens owns how verification §8's copy is built faithfully."""

    def test_the_lens_states_what_a_copy_preserves_and_how_that_is_evidenced(self):
        gaps = _faithfulness_gaps(LENS.read_text(encoding="utf-8"))
        self.assertEqual(
            [],
            gaps,
            "the cut lens states no faithfulness clause covering: "
            f"{', '.join(gaps)}",
        )

    def test_section_8_reaches_the_owner_in_one_hop(self):
        owner_clause = clause(VERIFICATION.read_text(encoding="utf-8"), 8)
        self.assertIn(
            "cut-lens.md",
            owner_clause,
            "verification.md §8 requires a copy built beside the tree and "
            "names no owner of how one is built faithfully",
        )

    def test_a_lens_without_the_clause_fails_the_check(self):
        """The can-fail direction excises the recipe from a copy."""
        real = LENS.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            beside = Path(tmp) / "cut-lens.md"
            beside.write_text(real, encoding="utf-8")
            self.assertEqual(
                [],
                _faithfulness_gaps(beside.read_text(encoding="utf-8")),
                "the copy must start with the clause intact, or the excision "
                "below is not what the check reacted to",
            )
            self.assertIn(_RECIPE_HEADING, real)
            beside.write_text(
                real[: real.index(_RECIPE_HEADING)],
                encoding="utf-8",
            )
            self.assertEqual(
                sorted(_FAITHFULNESS_CLAUSE),
                _faithfulness_gaps(beside.read_text(encoding="utf-8")),
            )
