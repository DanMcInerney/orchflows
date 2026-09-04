"""`lens_key` picks the `## Lens` entry a child's work is measured against.

The discriminator reads in whichever direction the ticket runs, and the
direction is the executor's, not the Context's: only a judge is handed
finished artifacts, so only a judge's typed Context identities name the kind
it checks. A `do` may cite a predecessor identity in its Context as evidence
-- a planning `do` routinely does -- and citing one must not send it to the
adapter kind of the artifact it merely read.

The cases fire on the function rather than through the mint, because the
mint refuses combinations this discriminator must still resolve correctly
for a hand-written ticket: `tests/test_dispatch_launch.py`'s
`LensKeyPromptTest` already covers the minted path end to end.
"""

from __future__ import annotations

import unittest

from scripts.tickets_assignment import lens_key

from tests.test_ticket_callables import CODE_PACK, standards_field


def _sections(context: str) -> dict:
    return {"Goal": "Deliver the behavior.\n", "Context": context}


class LensKeyTest(unittest.TestCase):
    """One key per ticket, keyed off the executor first."""

    def test_a_planning_do_citing_a_predecessor_keeps_its_makes_kind(self):
        """The artifact line is evidence the `do` read, not the product it
        owes: `makes` is what this ticket was minted to produce."""

        key = lens_key(
            {"executor": "orch-do", "makes": "root", "standards": standards_field(CODE_PACK)},
            _sections("- parent: B1\n- artifact: git:0123456789abcdef\n"),
        )

        self.assertEqual("root", key)

    def test_a_making_do_citing_a_predecessor_keeps_its_adapter_kind(self):
        """No `makes`, so the stamped pack's adapter fixes the kind -- and
        an `evidence` identity in Context does not move it."""

        key = lens_key(
            {"executor": "orch-do", "standards": standards_field(CODE_PACK)},
            _sections("- artifact: evidence:store-1\n"),
        )

        self.assertEqual("git", key)

    def test_a_judge_is_keyed_by_the_one_kind_on_its_context(self):
        """The judge's kind is the artifact's, never the stamped pack's:
        this one is stamped for code and handed an evidence identity."""

        key = lens_key(
            {"executor": "orch-judge", "standards": standards_field(CODE_PACK)},
            _sections("- artifact: evidence:store-1\n"),
        )

        self.assertEqual("evidence", key)

    def test_a_judge_over_two_kinds_gets_no_key(self):
        """No one entry is its criteria, and a guessed one would be worse
        than the sentence the prompt then omits."""

        key = lens_key(
            {"executor": "orch-judge", "standards": standards_field(CODE_PACK)},
            _sections(
                "- artifact: git:0123456789abcdef\n"
                "- artifact: evidence:store-1\n"
            ),
        )

        self.assertIsNone(key)


if __name__ == "__main__":
    unittest.main()
