"""Record-level validation regression cases."""

from tests import test_validate_measures as common
from tests.test_validate_measures import (
    FULL_PLAN,
    ONE_PLAN,
    SET_REVISION,
    RecordCase,
    contextlib,
    entry_text,
    full,
    io,
    make_row,
    mutate,
    one,
    record_text,
    rows_for,
    vm,
)


def setUpModule():
    common.setUpModule()
    globals()["WORLD"] = common.WORLD


def tearDownModule():
    common.tearDownModule()


# --------------------------------------------------------------------
# the clean fixtures — both completeness branches (A5)
# --------------------------------------------------------------------


class TestClean(RecordCase):
    def test_complete_entry_of_sixteen_rows_is_silent(self):
        self.assertClean(full())

    def test_incomplete_entry_declaring_its_shortfall_is_silent(self):
        self.assertClean(one())

    def test_entry_carrying_its_own_verify_command_is_silent(self):
        self.assertClean(record_text([entry_text(rows_for(FULL_PLAN), verify=True)], preamble_verify=False))

    def test_two_entries_newest_first_are_silent(self):
        newer = entry_text(rows_for(FULL_PLAN), date="2026-08-09")
        older = entry_text(rows_for(FULL_PLAN), date="2026-08-08")
        self.assertClean(record_text([newer, older]))


# --------------------------------------------------------------------
# C1 (A4) — the entry names the case set it measured, by git revision
# --------------------------------------------------------------------


class TestCoveredCaseSet(RecordCase):
    def test_case_set_named_by_a_full_revision_is_clean(self):
        self.assertClean(full(case_set=SET_REVISION))

    def test_case_set_named_by_an_abbreviated_revision_is_clean(self):
        self.assertClean(full(case_set=SET_REVISION[:7]))

    def test_entry_naming_no_case_set_is_reported(self):
        self.assertViolation(full(case_set=""), "case-set: names no case set", count=1)

    def test_entry_without_the_case_set_block_is_reported(self):
        record = full(sections=("rungs", "incomparability", "scope", "figures"))
        self.assertViolation(record, "case-set: names no case set", count=1)

    def test_a_digest_where_the_revision_belongs_is_reported(self):
        """The retired form is refused, not silently read as a revision."""
        self.assertViolation(
            full(case_set="sha256:" + "b" * 64), "case-set: names no case set", count=1
        )

    def test_a_bare_sixty_four_hex_digest_is_not_a_revision(self):
        self.assertViolation(full(case_set="b" * 64), "case-set: names no case set", count=1)

    def test_a_revision_too_short_to_resolve_is_reported(self):
        self.assertViolation(full(case_set="abc123"), "case-set: names no case set", count=1)


# --------------------------------------------------------------------
# C2 (A5) — sixteen rows, or a declaration naming every absent case
# --------------------------------------------------------------------


class TestCompleteness(RecordCase):
    def test_undeclared_missing_row_is_reported(self):
        rows = rows_for(FULL_PLAN[:-1])
        self.assertViolation(
            record_text([entry_text(rows)]), "has no row for case 'cs-workflow-fresh'"
        )

    def test_row_for_a_case_outside_the_set_is_reported(self):
        rows = rows_for(FULL_PLAN) + [make_row("cs-cli-fresh", "both-pass")]
        rows[-1]["case"] = "cs-invented"
        self.assertViolation(record_text([entry_text(rows)]), "no case directory 'cs-invented'")

    def test_misspelled_case_id_is_reported(self):
        rows = rows_for(FULL_PLAN)
        rows[1]["case"] = "cs-cli-frsh"
        lines = self.assertViolation(record_text([entry_text(rows)]), "no case directory 'cs-cli-frsh'")
        self.assertTrue(any("has no row for case 'cs-cli-fresh'" in line for line in lines))

    def test_duplicate_row_for_one_case_is_reported(self):
        rows = rows_for(FULL_PLAN) + [make_row("cs-cli-fresh", "split")]
        self.assertViolation(
            record_text([entry_text(rows)]), "appears in more than one row", count=1
        )

    def test_declared_count_below_the_rows_carried_is_reported(self):
        rows = rows_for(FULL_PLAN[:2])
        record = record_text([entry_text(rows, incomplete=1)])
        self.assertViolation(record, "declares 1 of 16 rows but carries 2", count=1)

    def test_incomplete_entry_must_name_every_absent_case(self):
        rows = rows_for(ONE_PLAN)
        absent = [case for case, _ in FULL_PLAN if case not in ("cs-cli-fresh", "cs-workflow-fresh")]
        record = record_text([entry_text(rows, incomplete=1, absent=absent)])
        self.assertViolation(record, "does not name the absent case 'cs-workflow-fresh'", count=1)

    def test_case_directory_that_is_not_sixteen_cases_is_reported(self):
        stream = io.StringIO()
        path = WORLD.write_record(full())
        with contextlib.redirect_stdout(stream):
            code = vm.main(
                ["--record", str(path), "--cases-dir", str(WORLD.cases_dir / "cs-cli-fresh")]
            )
        self.assertEqual(code, 1)
        self.assertIn("not the frozen 16", stream.getvalue())


# --------------------------------------------------------------------
# C3 (A6) — status recomputed from the verdict pair
# --------------------------------------------------------------------


class TestStatus(RecordCase):
    def test_pass_fail_labelled_both_pass_is_reported(self):
        def change(row):
            row["status"] = "both-pass"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "derives 'split'")

    def test_status_outside_the_enumeration_is_reported(self):
        def change(row):
            row["status"] = "mixed"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "is not one of")

    def test_unverified_verdict_stays_undetermined(self):
        """The fifth status is reachable only from an UNVERIFIED verdict."""

        def change(row):
            row["status"] = "both-pass"
            row["readings"] = ["a", "b"]

        rows = mutate(FULL_PLAN, "cs-nondet-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "derives 'undetermined'")

    def test_undetermined_without_an_unverified_verdict_is_reported(self):
        def change(row):
            row["status"] = "undetermined"
            row["discriminating"] = False

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "derives 'split'")


# --------------------------------------------------------------------
# C4 (A7) — never PASS or FAIL beside an unclean probe
# --------------------------------------------------------------------


class TestUnverified(RecordCase):
    def test_pass_against_a_crashed_probe_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["trial_exit_codes"] = [124]
            row["rungs"]["strong"]["probe_exit_code"] = 124

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "derive UNVERIFIED")

    def test_pass_against_a_canary_hit_is_reported(self):
        def change(row):
            row["rungs"]["strong"]["canary"] = "hit"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "derive UNVERIFIED", count=1)

    def test_fail_against_a_bound_overrun_is_reported(self):
        def change(row):
            row["rungs"]["weak"]["bound"]["status"] = "overrun"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "derive UNVERIFIED", count=1)

    def test_timeout_marker_recorded_as_fail_is_reported(self):
        def change(row):
            row["rungs"]["weak"]["trial_exit_codes"] = ["timeout after 60s"]
            row["rungs"]["weak"]["probe_exit_code"] = "timeout after 60s"

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "derive UNVERIFIED")

    def test_wall_clock_past_the_ceiling_must_be_an_overrun(self):
        def change(row):
            row["rungs"]["strong"]["bound"]["probe_wall_clock_s"] = 90

        rows = mutate(FULL_PLAN, "cs-cli-fresh", change)
        self.assertViolation(record_text([entry_text(rows)]), "not 'overrun'", count=1)


# --------------------------------------------------------------------
# C10 (A15) — the entry idiom
# --------------------------------------------------------------------


class TestEntryIdiom(RecordCase):
    def test_entry_without_a_dated_header_is_reported(self):
        record = full().replace("## 2026-08-08 — two-rung", "## two-rung")
        self.assertViolation(record, "heading is not", count=1)

    def test_entries_out_of_newest_first_order_are_reported(self):
        older = entry_text(rows_for(FULL_PLAN), date="2026-08-01")
        newer = entry_text(rows_for(FULL_PLAN), date="2026-08-09")
        self.assertViolation(record_text([older, newer]), "not newest-first", count=1)

    def test_record_without_an_inline_verify_command_is_reported(self):
        record = record_text([entry_text(rows_for(FULL_PLAN))], preamble_verify=False)
        self.assertViolation(record, "names no inline command that verifies it", count=1)

    def test_record_with_no_entry_is_reported(self):
        self.assertViolation(record_text([]), "carries no entry", count=1)

    def test_entry_with_no_row_is_reported(self):
        record = record_text([entry_text([], incomplete=0)])
        self.assertViolation(record, "carries no case row")

    def test_unparsable_row_is_reported(self):
        record = full().replace('"case": "cs-cli-fresh"', '"case": cs-cli-fresh')
        self.assertViolation(record, "does not parse")


# --------------------------------------------------------------------
