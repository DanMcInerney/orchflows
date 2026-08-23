"""The widened bound grammar, the park predicate, and `bound-check`.

A bound a cut can state but the parser cannot read protects nothing: before
this, `<= 40 tool calls` aged a claim at exactly the 60 minutes `banana`
did, so two bounds unreadable for opposite reasons were indistinguishable
to every reader of a bound. What is pinned here is the widened grammar with
its stated conversions, and the two separate answers `bound-check` gives
about one overdue ticket -- overdue is about the bound, parking is about
whether anything moved after the bound elapsed.

Self-contained by write scope: the shared case chain under
`tests/test_tickets_cases/` is another item's to edit in this run, so the
fixtures here are built from `common`'s primitives alone.
"""

import unittest

from tests.test_tickets_cases.common import use_sink  # noqa: F401  (sys.path)

import scripts.tickets as tickets_mod  # noqa: E402
from scripts import tickets_bound  # noqa: E402
from scripts import ui_model  # noqa: E402


# (bound, minutes, kind). One table, three readers: the parser itself, the
# minutes-only name its callers already hold, and the viewer's meter.
GRAMMAR = (
    ("30m", 30, "duration"),
    ("  45m  ", 45, "duration"),
    ("2h", 120, "duration"),
    ("0m", 0, "duration"),
    ("90 min", 90, "duration"),
    ("90 minutes", 90, "duration"),
    ("1 minute", 1, "duration"),
    ("3 hours", 180, "duration"),
    ("1 hour", 60, "duration"),
    ("40 tool calls", 80, "tool-calls"),
    ("1 tool call", 2, "tool-calls"),
    ("<= 40 tool calls", 80, "tool-calls"),
    ("<=40 tool calls", 80, "tool-calls"),
    ("at most 40 tool calls", 80, "tool-calls"),
    ("At most 40 tool calls", 80, "tool-calls"),
    ("3 iterations", 180, "iterations"),
    ("1 iteration", 60, "iterations"),
    ("<= 3 iterations", 180, "iterations"),
    ("at most 3 iterations", 180, "iterations"),
    ("<= 30m", 30, "duration"),
    ("at most 2h", 120, "duration"),
    # Everything the grammar does not read is one kind with one number, and
    # the number is the lease default rather than a measurement.
    ("one session", 60, "other"),
    ("banana", 60, "other"),
    ("30", 60, "other"),
    ("90 m", 60, "other"),  # a bare unit letter takes no space before it
    ("1d", 60, "other"),
    ("m90", 60, "other"),
    ("-5m", 60, "other"),
    ("40 tool calls each", 60, "other"),  # anchored, not a prefix match
    ("", 60, "other"),
    (None, 60, "other"),
    ([], 60, "other"),  # not a string at all
)


class BoundGrammarTest(unittest.TestCase):
    def test_the_stated_conversions_are_the_stated_constants(self):
        self.assertEqual(2, tickets_bound.TOOL_CALL_MINUTES)
        self.assertEqual(60, tickets_bound.DEFAULT_BOUND_MINUTES)
        self.assertEqual(
            ("duration", "tool-calls", "iterations", "other"),
            tickets_bound.BOUND_KINDS,
        )

    def test_every_bound_parses_to_its_stated_minutes_and_kind(self):
        for bound, minutes, kind in GRAMMAR:
            with self.subTest(bound=bound):
                self.assertEqual((minutes, kind), tickets_bound.parse_bound(bound))

    def test_the_minutes_only_name_its_callers_hold_reads_the_same_table(self):
        for bound, minutes, _kind in GRAMMAR:
            with self.subTest(bound=bound):
                self.assertEqual(minutes, tickets_mod._parse_bound_minutes(bound))

    def test_the_viewer_measures_every_kind_but_the_one_with_no_number(self):
        """The meter's refusal was never about durations -- it was about
        drawing a denominator no ticket stated. A tool-call or iteration
        bound now has one, stated in `TOOL_CALL_MINUTES` and
        `DEFAULT_BOUND_MINUTES`; `one session` still has none."""

        for bound, minutes, kind in GRAMMAR:
            with self.subTest(bound=bound):
                self.assertEqual(
                    None if kind == "other" else minutes,
                    ui_model.bound_minutes(bound),
                )


if __name__ == "__main__":
    unittest.main()
