"""Figure-level validation regression cases."""

from tests import test_validate_measures as common
from tests.test_validate_measures import (
    FULL_PLAN,
    RecordCase,
    entry_text,
    figure_table,
    full,
    record_text,
    rows_for,
)


def setUpModule():
    common.setUpModule()
    globals()["WORLD"] = common.WORLD


def tearDownModule():
    common.tearDownModule()


class TestFigures(RecordCase):
    def test_resolution_below_the_stated_spread_is_reported(self):
        figures = figure_table(rows_for(FULL_PLAN)).replace(
            "rerun spread is **unmeasured**; the three-trial cases have not rerun",
            "measured rerun spread is 3 cases across the three-trial cases",
        )
        self.assertViolation(full(figures=figures), "1 case(s) but max(", count=1)

    def test_resolution_matching_a_measured_spread_is_clean(self):
        figures = figure_table(
            rows_for(FULL_PLAN),
            {"resolution": "`max(measured rerun spread, 1 case)` = **3 cases**"},
        ).replace(
            "rerun spread is **unmeasured**; the three-trial cases have not rerun",
            "measured rerun spread is 3 cases across the three-trial cases",
        )
        self.assertClean(full(figures=figures))

    def test_resolution_without_the_formula_is_reported(self):
        self.assertViolation(
            full(figure_overrides={"resolution": "**1 case**"}),
            "must be stated as max(measured rerun spread, 1 case)",
        )

    def test_resolution_without_a_stated_spread_is_reported(self):
        figures = figure_table(rows_for(FULL_PLAN)).replace(
            "rerun spread is **unmeasured**; the three-trial cases have not rerun",
            "the floor stands on its one-case term",
        )
        self.assertViolation(full(figures=figures), "does not state the measured rerun spread", count=1)

    def test_absent_figure_row_is_reported(self):
        figures = "\n".join(
            line
            for line in figure_table(rows_for(FULL_PLAN)).splitlines()
            if not line.startswith("| margin in cases")
        )
        self.assertViolation(full(figures=figures), "has no 'margin in cases' row", count=1)

    def test_status_distribution_that_contradicts_the_rows_is_reported(self):
        self.assertViolation(
            full(figure_overrides={"status distribution": "`split` 9; `both-pass` 7"}),
            "states split 9 but 3 row(s) carry it",
        )

    def test_status_distribution_omitting_a_status_the_rows_carry_is_reported(self):
        self.assertViolation(
            full(figure_overrides={"status distribution": "`split` 3; `both-pass` 7; `both-fail` 4; `inversion` 1"}),
            "omits undetermined",
            count=1,
        )

    def test_discriminating_set_that_contradicts_the_rows_is_reported(self):
        self.assertViolation(
            full(figure_overrides={"discriminating set": "`cs-cli-fresh`"}),
            "the discriminating set figure names",
            count=1,
        )

    def test_inversions_figure_that_hides_an_inversion_is_reported(self):
        self.assertViolation(
            full(figure_overrides={"inversions": "none"}), "the inversions figure names", count=1
        )

    def test_margin_that_contradicts_the_rows_is_reported(self):
        self.assertViolation(
            full(figure_overrides={"margin in cases": "8 (strong 10/16, weak 2/16)"}),
            "the margin figure states 8 but the rows derive 1",
            count=1,
        )

    def test_empty_discriminating_set_must_say_so(self):
        plan = tuple((case, "both-fail") for case, _ in FULL_PLAN)
        rows = rows_for(plan)
        figures = figure_table(rows, {"discriminating set": "the split bucket"})
        self.assertViolation(
            record_text([entry_text(rows, figures=figures)]),
            "the discriminating set figure is empty and must say so",
            count=1,
        )

