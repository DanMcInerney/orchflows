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

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from tests.test_tickets_cases.common import backdate, run_main, use_sink

import scripts.tickets as tickets_mod  # noqa: E402
from scripts import tickets_bound  # noqa: E402
from reader.scripts import ui_model  # noqa: E402
from scripts.tickets_format import (  # noqa: E402
    _set_frontmatter_field, canonical_json,
)

UTC_STAMP = "%Y-%m-%dT%H:%M:%SZ"

# Pinned once per process, and passed to every dispatch as `--now`: the
# claim times below are written relative to it, while `last_motion` is a
# real mtime, so the two clocks agree only because this one is the wall
# clock. `--now` still pins what the command reads, which one case proves
# by moving it and reading a different elapsed off the same run.
NOW = datetime.now(timezone.utc).replace(microsecond=0)

TICKET = """---
id: {tid}
run: testrun
status: {status}
executor: orch-tdd
pack: orch-code-pack
depends_on: []
isolation: required
write_scope: scratch/{tid}.txt
bound: {bound}
{claim}---

## Objective

Test ticket.
"""


def make_run(tmp: Path, tickets: tuple) -> Path:
    """A repo root whose sink holds one run of ``(id, status, bound, age)``.

    ``age`` is minutes between the claim and ``now``; the ticket file's own
    mtime is what `_last_motion` reads, so each case backdates it to say
    how long ago that ticket last moved.
    """

    (tmp / ".git").mkdir()
    run_dir = use_sink(tmp) / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    for tid, status, bound, claimed_minutes_ago, motion_minutes_ago in tickets:
        claim = ""
        if claimed_minutes_ago is not None:
            claimed_at = (NOW - timedelta(minutes=claimed_minutes_ago)).strftime(UTC_STAMP)
            claim = f"claimed_by: agent-a\nclaimed_at: {claimed_at}\n"
        elif status == "claimed":
            claim = "claimed_by: agent-a\nclaimed_at: not a timestamp\n"
        path = run_dir / f"{tid}.md"
        path.write_bytes(
            TICKET.format(tid=tid, status=status, bound=bound, claim=claim).encode("utf-8")
        )
        backdate(path, motion_minutes_ago)
    return tmp


def bound_check(tmp: Path, *args):
    """``(payload, exit code)`` from one real ``bound-check`` dispatch."""

    result = run_main(tmp, "bound-check", "testrun", *args)
    return (json.loads(result.stdout), result.returncode)


def rows_by_id(payload: dict) -> dict:
    return {row["id"]: row for row in payload["bound_check"]["tickets"]}


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


class ParkPredicateTest(unittest.TestCase):
    """Overdue and parked are two questions, and the second one is the
    only one whose answer takes an item away from the agent holding it."""

    CLAIMED = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)

    def at(self, minutes: int) -> datetime:
        return self.CLAIMED + timedelta(minutes=minutes)

    def test_a_bound_that_has_not_elapsed_parks_nothing(self):
        self.assertFalse(tickets_bound.should_park(self.CLAIMED, 30, None, self.at(29)))
        self.assertFalse(
            tickets_bound.should_park(self.CLAIMED, 30, self.at(5), self.at(30))
        )

    def test_a_bound_elapsed_with_no_motion_after_it_is_the_park(self):
        self.assertTrue(
            tickets_bound.should_park(self.CLAIMED, 30, self.at(10), self.at(90))
        )
        self.assertTrue(tickets_bound.should_park(self.CLAIMED, 30, None, self.at(90)))
        # Motion exactly at the deadline is motion up to it, not after it.
        self.assertTrue(
            tickets_bound.should_park(self.CLAIMED, 30, self.at(30), self.at(90))
        )

    def test_motion_after_the_bound_elapsed_is_over_bound_and_not_parked(self):
        self.assertFalse(
            tickets_bound.should_park(self.CLAIMED, 30, self.at(85), self.at(90))
        )

    def test_a_claim_with_no_readable_start_has_no_deadline_to_have_passed(self):
        self.assertFalse(tickets_bound.should_park(None, 30, None, self.at(90)))

    def test_the_facade_exports_the_predicate_the_engine_rule_names(self):
        self.assertIs(tickets_bound.should_park, tickets_mod.should_park)


class BoundCheckCommandTest(unittest.TestCase):
    """`bound-check` over one run: what it lists, what it calls overdue,
    and the exit code the engine's re-check reads without parsing anything."""

    def test_it_lists_the_live_claims_and_nothing_else(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_run(
                Path(tmp),
                (
                    ("T1", "claimed", "30m", 10, 1),
                    ("T2", "complete", "30m", 10, 1),
                    ("T3", "pending", "30m", None, 1),
                ),
            )
            payload, code = bound_check(root, "--now", NOW.strftime(UTC_STAMP))

            self.assertEqual(0, code, payload)
            self.assertEqual(["T1"], sorted(rows_by_id(payload)))
            self.assertEqual(0, payload["bound_check"]["overdue"])
            self.assertEqual(NOW.strftime(UTC_STAMP), payload["bound_check"]["now"])

    def test_each_row_carries_the_bound_as_read_and_the_claim_as_measured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_run(
                Path(tmp),
                (
                    ("T1", "claimed", "30m", 10, 1),
                    ("T2", "claimed", "<= 40 tool calls", 10, 1),
                    ("T3", "claimed", "one session", 10, 1),
                ),
            )
            payload, _code = bound_check(root, "--now", NOW.strftime(UTC_STAMP))
            rows = rows_by_id(payload)

            self.assertEqual(("duration", 30), (rows["T1"]["bound_kind"], rows["T1"]["bound_minutes"]))
            self.assertEqual(("tool-calls", 80), (rows["T2"]["bound_kind"], rows["T2"]["bound_minutes"]))
            self.assertEqual(("other", 60), (rows["T3"]["bound_kind"], rows["T3"]["bound_minutes"]))
            self.assertEqual("<= 40 tool calls", rows["T2"]["bound"])
            for row in rows.values():
                self.assertEqual(10, row["elapsed_minutes"])
                self.assertFalse(row["overdue"])
                self.assertEqual(
                    (NOW - timedelta(minutes=10)).strftime(UTC_STAMP), row["claimed_at"]
                )
                motion = datetime.strptime(row["last_motion_at"], UTC_STAMP).replace(
                    tzinfo=timezone.utc
                )
                self.assertLess(abs((NOW - timedelta(minutes=1)) - motion), timedelta(minutes=1))

    def test_an_elapsed_bound_is_overdue_whether_or_not_anything_moved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_run(
                Path(tmp),
                (
                    ("T1", "claimed", "30m", 90, 80),
                    ("T2", "claimed", "30m", 90, 5),
                ),
            )
            payload, code = bound_check(root, "--now", NOW.strftime(UTC_STAMP))
            rows = rows_by_id(payload)

            self.assertEqual(1, code, payload)
            self.assertEqual(2, payload["bound_check"]["overdue"])
            self.assertEqual([90, 90], [rows["T1"]["elapsed_minutes"], rows["T2"]["elapsed_minutes"]])
            self.assertTrue(rows["T1"]["overdue"])
            self.assertTrue(rows["T2"]["overdue"])
            # The one field that separates them: T1 stopped inside its
            # bound, T2 is still working past it.
            self.assertTrue(rows["T1"]["park"])
            self.assertFalse(rows["T2"]["park"])

    def test_dispatch_v1_uses_its_absolute_lease_and_motion_cannot_extend_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_run(Path(tmp), (("T1", "claimed", "1m", 90, 0),))
            path = use_sink(root) / "tickets" / "testrun" / "T1.md"
            text = path.read_text(encoding="utf-8")
            opened = NOW - timedelta(minutes=45)
            expires = NOW + timedelta(minutes=15)
            state = {"protocol": "orchflows.dispatch.v1", "attempts": [{
                "assignment_seal": "sha256:sealed",
                "dispatch_id": "D1",
                "lease_expires_at": expires.strftime(UTC_STAMP),
                "opened_at": opened.strftime(UTC_STAMP),
                "outcome_record_id": "outcome",
                "owner": "agent-a",
                "records": [],
                "state": "live",
            }]}
            path.write_text(
                _set_frontmatter_field(text, "dispatch_v1", canonical_json(state)),
                encoding="utf-8",
            )

            before, before_code = bound_check(
                root, "--now", NOW.strftime(UTC_STAMP)
            )
            after, after_code = bound_check(
                root, "--now", (NOW + timedelta(minutes=20)).strftime(UTC_STAMP)
            )

            before_row = rows_by_id(before)["T1"]
            after_row = rows_by_id(after)["T1"]
            self.assertEqual((0, 1), (before_code, after_code))
            self.assertEqual(expires.strftime(UTC_STAMP), before_row["lease_expires_at"])
            self.assertEqual(45, before_row["elapsed_minutes"])
            self.assertFalse(before_row["overdue"])
            self.assertTrue(after_row["overdue"])
            self.assertTrue(after_row["park"])

    def test_the_now_flag_pins_the_clock_the_row_is_measured_against(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_run(Path(tmp), (("T1", "claimed", "30m", 90, 80),))

            early, early_code = bound_check(
                root, "--now", (NOW - timedelta(minutes=80)).strftime(UTC_STAMP)
            )
            late, late_code = bound_check(root, "--now", NOW.strftime(UTC_STAMP))

            self.assertEqual((0, 1), (early_code, late_code))
            self.assertEqual(10, rows_by_id(early)["T1"]["elapsed_minutes"])
            self.assertEqual(90, rows_by_id(late)["T1"]["elapsed_minutes"])
            self.assertFalse(rows_by_id(early)["T1"]["overdue"])

    def test_a_claim_whose_start_cannot_be_read_is_reported_not_measured(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_run(Path(tmp), (("T1", "claimed", "30m", None, 80),))
            payload, code = bound_check(root, "--now", NOW.strftime(UTC_STAMP))
            row = rows_by_id(payload)["T1"]

            self.assertEqual(1, code, payload)
            self.assertIsNone(row["elapsed_minutes"])
            self.assertTrue(row["overdue"])
            self.assertFalse(row["park"])

    def test_a_clock_it_cannot_read_is_refused_before_any_run_is_opened(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_run(Path(tmp), (("T1", "claimed", "30m", 90, 80),))
            payload, code = bound_check(root, "--now", "yesterday")

            self.assertEqual(1, code)
            self.assertIn("yesterday", payload["error"])
            self.assertIn("bound-check", payload["error"])

    def test_a_run_with_no_tickets_is_an_error_rather_than_an_empty_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_run(Path(tmp), (("T1", "claimed", "30m", 90, 80),))
            result = run_main(root, "bound-check", "no-such-run")

            self.assertEqual(1, result.returncode)
            self.assertIn("error", json.loads(result.stdout))

    def test_a_row_is_never_parked_while_the_run_reports_nothing_overdue(self):
        """`elapsed_minutes` is floored for a reader; the deadline is not.

        Reading `overdue` off the floor put a claim 30m30s into a `30m`
        bound at `park: true` beside `overdue: false`, with `overdue: 0` and
        exit 0 for the run -- so the engine's own sentence (overdue with no
        motion parks) and the exit status `profiles.md` says the re-check
        reads disagreed about one deadline for the length of a minute.
        """

        with tempfile.TemporaryDirectory() as tmp:
            root = make_run(Path(tmp), (("T1", "claimed", "30m", 30, 20),))
            payload, code = bound_check(
                root, "--now", (NOW + timedelta(seconds=30)).strftime(UTC_STAMP)
            )
            row = rows_by_id(payload)["T1"]

            self.assertEqual(30, row["elapsed_minutes"])  # floored, for a reader
            self.assertTrue(row["park"])
            self.assertTrue(row["overdue"])
            self.assertEqual(1, code, payload)

    def test_a_claim_exactly_at_its_bound_has_not_yet_passed_it(self):
        """The other side of the same deadline, so the fix above cannot be
        paid for by calling every claim overdue one minute early."""

        with tempfile.TemporaryDirectory() as tmp:
            root = make_run(Path(tmp), (("T1", "claimed", "30m", 30, 20),))
            payload, code = bound_check(root, "--now", NOW.strftime(UTC_STAMP))
            row = rows_by_id(payload)["T1"]

            self.assertEqual(0, code, payload)
            self.assertEqual(30, row["elapsed_minutes"])
            self.assertFalse(row["overdue"])
            self.assertFalse(row["park"])

    def test_the_command_is_in_the_usage_table_the_help_view_reads(self):
        self.assertIn("bound-check", tickets_mod.SUBCOMMAND_USAGE)
        self.assertIn("bound-check", tickets_mod.SUBCOMMAND_SUMMARY)


if __name__ == "__main__":
    unittest.main()
