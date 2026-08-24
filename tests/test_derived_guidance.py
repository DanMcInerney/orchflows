"""Guidance a refusal derives rather than writes: remedies and arithmetic.

Two refusal families that each cost a caller a blind round-trip, and each
for the same reason -- the refusal held the facts that would have named the
next act, and spent them on prose instead.

The remedy half: a refusal that recommends a command names it from
`scripts/tickets_transitions.py`'s rows, so it cannot send a caller at a
transition the table refuses. The measured failure was a grant refusal
recommending `set-status pending, then recut` while the lease-leftover
cohort seal refused exactly that recut.

The arithmetic half: the instruction-ceiling refusal already counts every
part it grades, and printed only the total -- so a cutter over the ceiling
learned that the ticket was too long and not which section was long. The
measured cost was two blind recut round-trips per over-ceiling ticket.
"""

import unittest

from scripts import tickets as tickets_mod
from scripts import tickets_ceiling, tickets_format
from tests.test_tickets_issue_cases.common import ceiling_ticket


class InstructionBreakdownTest(unittest.TestCase):
    """The counter reports its parts, and the parts are the count."""

    def test_the_breakdown_names_every_graded_part(self):
        parts = dict(tickets_ceiling.instruction_breakdown(ceiling_ticket(320)))
        for name in tickets_ceiling.INSTRUCTION_SECTIONS:
            with self.subTest(name):
                self.assertIn(name, parts)
        self.assertIn(tickets_ceiling.EXCLUDED_ACTIONS_LABEL, parts)

    def test_the_parts_sum_to_the_total_the_ceiling_grades(self):
        """The breakdown is the counter's own arithmetic, not a second one.

        A per-section report that did not add up to the graded total would
        send a cutter to trim a section the ceiling never charged.
        """

        for total in (120, 300, 320, 460):
            text = ceiling_ticket(total)
            with self.subTest(total):
                parts = tickets_ceiling.instruction_breakdown(text)
                self.assertEqual(total, sum(count for _, count in parts))
                self.assertEqual(total, tickets_ceiling.instruction_words(text))

    def test_fixed_inputs_stay_free_of_every_part(self):
        """`## Fixed inputs` is evidence, and no part may charge for it."""

        padded = ceiling_ticket(320, inputs="- " + " ".join(["identity"] * 400))
        self.assertEqual(
            tickets_ceiling.instruction_breakdown(ceiling_ticket(320)),
            tickets_ceiling.instruction_breakdown(padded),
        )

    def test_the_breakdown_leads_with_the_section_worth_cutting(self):
        """Largest first: the first name printed is the one to shorten."""

        counts = [c for _, c in tickets_ceiling.instruction_breakdown(ceiling_ticket(320))]
        self.assertEqual(sorted(counts, reverse=True), counts)

    def test_the_counter_keeps_its_old_holders(self):
        """`tickets_format` and the facade still answer for the counter."""

        text = ceiling_ticket(320)
        self.assertEqual(320, tickets_format.instruction_words(text))
        self.assertEqual(320, tickets_mod.instruction_words(text))
        self.assertEqual(
            tickets_ceiling.INSTRUCTION_BUDGET, tickets_mod.INSTRUCTION_BUDGET
        )


class CeilingArithmeticTest(unittest.TestCase):
    """What an over-ceiling refusal prints of the sum it already has."""

    def test_the_arithmetic_prints_every_part_and_the_total(self):
        text = ceiling_ticket(322)
        rendered = tickets_ceiling.ceiling_arithmetic(text)
        for name, count in tickets_ceiling.instruction_breakdown(text):
            with self.subTest(name):
                self.assertIn(f"{name} {count}", rendered)
        self.assertIn("= 322", rendered)

    def test_the_refusal_carries_the_arithmetic_and_the_overage(self):
        over = tickets_ceiling.INSTRUCTION_BUDGET + 22
        sentence = tickets_ceiling.ceiling_sentence("the ticket", ceiling_ticket(over))
        self.assertIsNotNone(sentence)
        self.assertIn(tickets_ceiling.ceiling_arithmetic(ceiling_ticket(over)), sentence)
        self.assertIn("22 over", sentence)
        for kept in (str(over), "rules/token-economy.md", "two items"):
            with self.subTest(kept):
                self.assertIn(kept, sentence)

    def test_an_instruction_at_the_ceiling_draws_no_sentence(self):
        at = tickets_ceiling.INSTRUCTION_BUDGET
        self.assertIsNone(tickets_ceiling.ceiling_sentence("the ticket", ceiling_ticket(at)))


if __name__ == "__main__":
    unittest.main()
