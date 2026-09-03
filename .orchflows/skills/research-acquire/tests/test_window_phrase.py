"""Window front door: the phrase grammar, proven closed at both doors.

Every case here is arithmetic on a frozen anchor — no wall clock exists in
the module under test, so no case needs one. The refusal cases matter as
much as the parses: the front door's whole claim is that a phrase outside
the grammar becomes a typed refusal naming the grammar, never a guessed
bound riding into a manifest.
"""

import unittest

from super_research import schema, window


AS_OF = "2026-09-01T12:30:45Z"


class ParsePhraseTest(unittest.TestCase):
    def test_the_empty_phrase_is_the_unbounded_window_not_a_default(self):
        for phrase in ("", "   "):
            with self.subTest(phrase=repr(phrase)):
                self.assertEqual(window.parse_phrase(phrase, AS_OF), window.NO_WINDOW)
                self.assertEqual(window.parse_phrase(phrase, AS_OF).window_start, "")

    def test_relative_phrases_anchor_on_as_of_and_leave_the_end_open(self):
        cases = {
            "past week": "2026-08-25T12:30:45Z",
            "last week": "2026-08-25T12:30:45Z",
            "past 30 days": "2026-08-02T12:30:45Z",
            "past 6 hours": "2026-09-01T06:30:45Z",
            "past 2 weeks": "2026-08-18T12:30:45Z",
            "past month": "2026-08-01T12:30:45Z",
            "past year": "2025-09-01T12:30:45Z",
        }
        for phrase, start in cases.items():
            with self.subTest(phrase=phrase):
                parsed = window.parse_phrase(phrase, AS_OF)
                self.assertEqual(parsed.window_start, start)
                self.assertEqual(parsed.window_end, "")

    def test_calendar_months_clamp_into_the_shorter_month(self):
        # March 31 minus one month is the last day February has, not an
        # overflow into March that narrows the window it names.
        parsed = window.parse_phrase("past month", "2026-03-31T09:00:00Z")
        self.assertEqual(parsed.window_start, "2026-02-28T09:00:00Z")
        leap = window.parse_phrase("past month", "2028-03-31T09:00:00Z")
        self.assertEqual(leap.window_start, "2028-02-29T09:00:00Z")

    def test_months_cross_a_year_boundary_by_calendar(self):
        parsed = window.parse_phrase("past 3 months", "2026-01-15T00:00:00Z")
        self.assertEqual(parsed.window_start, "2025-10-15T00:00:00Z")

    def test_today_and_yesterday_are_the_anchor_days_own_bounds(self):
        today = window.parse_phrase("today", AS_OF)
        self.assertEqual(today.window_start, "2026-09-01T00:00:00Z")
        self.assertEqual(today.window_end, "")
        yesterday = window.parse_phrase("yesterday", AS_OF)
        self.assertEqual(yesterday.window_start, "2026-08-31T00:00:00Z")
        self.assertEqual(yesterday.window_end, "2026-09-01T00:00:00Z")

    def test_on_a_date_spans_that_whole_day(self):
        parsed = window.parse_phrase("on 2026-08-15", AS_OF)
        self.assertEqual(parsed.window_start, "2026-08-15T00:00:00Z")
        self.assertEqual(parsed.window_end, "2026-08-16T00:00:00Z")

    def test_since_takes_a_date_or_a_full_instant(self):
        by_date = window.parse_phrase("since 2026-08-01", AS_OF)
        self.assertEqual(by_date.window_start, "2026-08-01T00:00:00Z")
        self.assertEqual(by_date.window_end, "")
        by_instant = window.parse_phrase("since 2026-08-01T06:00:00Z", AS_OF)
        self.assertEqual(by_instant.window_start, "2026-08-01T06:00:00Z")

    def test_a_span_through_a_named_date_includes_that_date(self):
        for phrase in (
            "between 2026-08-03 and 2026-08-05",
            "from 2026-08-03 to 2026-08-05",
        ):
            with self.subTest(phrase=phrase):
                parsed = window.parse_phrase(phrase, AS_OF)
                self.assertEqual(parsed.window_start, "2026-08-03T00:00:00Z")
                self.assertEqual(parsed.window_end, "2026-08-06T00:00:00Z")

    def test_a_span_to_an_instant_ends_exactly_there(self):
        parsed = window.parse_phrase(
            "from 2026-08-03 to 2026-08-05T18:00:00Z", AS_OF
        )
        self.assertEqual(parsed.window_end, "2026-08-05T18:00:00Z")

    def test_case_and_whitespace_do_not_change_the_question(self):
        self.assertEqual(
            window.parse_phrase("  Past   Week ", AS_OF),
            window.parse_phrase("past week", AS_OF),
        )

    def test_the_result_is_the_shape_a_manifest_step_takes(self):
        parsed = window.parse_phrase("past week", AS_OF)
        step = schema.AcquisitionStep(
            step_id="s1",
            kind="discovery",
            adapter_id="hacker_news",
            query="python",
            max_items=5,
            window_start=parsed.window_start,
            window_end=parsed.window_end,
        )
        self.assertEqual(step.window_start, parsed.window_start)


class RefusalTest(unittest.TestCase):
    def test_an_unknown_phrase_is_refused_naming_the_grammar(self):
        for phrase in (
            "since the election",
            "recently",
            "30 days",
            "next week",
            "past fortnight",
        ):
            with self.subTest(phrase=phrase):
                with self.assertRaises(window.WindowPhraseError) as caught:
                    window.parse_phrase(phrase, AS_OF)
                for line in window.PHRASE_GRAMMAR:
                    self.assertIn(line, str(caught.exception))

    def test_on_refuses_a_moment_inside_a_day(self):
        with self.assertRaises(window.WindowPhraseError):
            window.parse_phrase("on 2026-08-15T06:00:00Z", AS_OF)

    def test_a_span_that_ends_before_it_starts_is_refused(self):
        with self.assertRaises(window.WindowPhraseError) as caught:
            window.parse_phrase("between 2026-08-05 and 2026-08-03", AS_OF)
        self.assertIn("ends before it starts", str(caught.exception))

    def test_an_anchor_the_manifest_would_refuse_is_refused_here_first(self):
        for as_of in ("2026-09-01", "2026-09-01 12:00:00", "yesterday", ""):
            with self.subTest(as_of=repr(as_of)):
                with self.assertRaises(window.WindowPhraseError):
                    window.parse_phrase("past week", as_of)

    def test_a_malformed_date_inside_a_known_form_is_refused(self):
        for phrase in ("since 2026-13-40", "on 2026-02-30", "between x and y"):
            with self.subTest(phrase=phrase):
                with self.assertRaises(window.WindowPhraseError):
                    window.parse_phrase(phrase, AS_OF)


if __name__ == "__main__":
    unittest.main()
