"""Behavioral cases imported by the ``tests.test_tickets_issue`` seam."""

from .common import *  # noqa: F401,F403

class CriterionDefectsTest(unittest.TestCase):
    """`criterion_defects` reads one completion-test section and answers per
    criterion: the oracle, the oracle class against contracts/verdict.md's
    three, and the provenance against work-item.md's two."""

    def test_a_criterion_carrying_oracle_and_class_is_clean(self):
        self.assertEqual([], criterion(f"- {GOOD_CRITERION}"))

    def test_the_prose_spelling_is_the_same_criterion(self):
        """The library's own tickets write `Oracle: that command.
        oracle_class: deterministic.` rather than the pipe form; both name
        the same two things and neither is a defect."""

        self.assertEqual(
            [],
            criterion(
                "1. `python -m unittest` exits 0. Oracle: that command. "
                "oracle_class: deterministic."
            ),
        )

    def test_a_criterion_with_no_oracle_is_named(self):
        defects = criterion("- the suite exits 0 | oracle_class: deterministic")
        self.assertEqual(1, len(defects), defects)
        self.assertIn("oracle", defects[0])
        self.assertIn("criterion 1", defects[0])

    def test_a_criterion_with_no_oracle_class_is_named(self):
        defects = criterion("- the suite exits 0 | oracle: the command")
        self.assertEqual(1, len(defects), defects)
        self.assertIn("oracle_class", defects[0])

    def test_an_off_enum_oracle_class_is_named_with_the_enum(self):
        defects = criterion(
            "- the suite exits 0 | oracle: the command | oracle_class: mechanical"
        )
        self.assertEqual(1, len(defects), defects)
        self.assertIn("mechanical", defects[0])
        for allowed in ("deterministic", "judged", "evidence"):
            self.assertIn(allowed, defects[0])

    def test_every_class_the_verdict_contract_names_is_accepted(self):
        for allowed in tickets_mod.ORACLE_CLASSES:
            with self.subTest(allowed):
                self.assertEqual(
                    [], criterion(f"- x | oracle: y | oracle_class: {allowed}")
                )

    def test_an_off_enum_provenance_is_named_and_a_valid_one_is_not(self):
        defects = criterion(
            "- x | oracle: y | oracle_class: judged | provenance: invented"
        )
        self.assertEqual(1, len(defects), defects)
        self.assertIn("provenance", defects[0])
        self.assertIn("invented", defects[0])
        for allowed in tickets_mod.ORACLE_PROVENANCES:
            with self.subTest(allowed):
                self.assertEqual(
                    [],
                    criterion(
                        f"- x | oracle: y | oracle_class: judged | provenance: {allowed}"
                    ),
                )

    def test_only_the_offending_criterion_is_reported(self):
        """The whole-section substring test this replaces passed a section
        whose second criterion named nothing, because its first one did."""

        section = (
            f"- first | oracle: a | oracle_class: deterministic\n"
            f"- second | oracle: b\n"
            f"- third | oracle: c | oracle_class: judged\n"
        )
        defects = criterion(section)
        self.assertEqual(1, len(defects), defects)
        self.assertIn("criterion 2", defects[0])

    def test_a_wrapped_criterion_is_one_criterion(self):
        """A criterion long enough to wrap carries its oracle on the
        continuation line; reading each line as a criterion would report two
        defects on one clean bullet."""

        self.assertEqual(
            [],
            criterion(
                "- the suite exits 0 under every interpreter CI runs\n"
                "  | oracle: `python tools/run_tests.py` | oracle_class: deterministic\n"
            ),
        )

    def test_a_bullet_inside_a_fence_is_quoted_content(self):
        """Executors quote ticket markdown at length; a quoted bullet is not
        a criterion of this ticket."""

        section = (
            "- real | oracle: a | oracle_class: deterministic\n"
            "\n"
            "```\n"
            "- quoted, and naming nothing\n"
            "```\n"
        )
        self.assertEqual([], criterion(section))

    def test_a_section_with_no_criterion_at_all_is_a_defect(self):
        for empty in ("", "The suite has to pass.", "   \n"):
            with self.subTest(empty):
                defects = criterion(empty)
                self.assertEqual(1, len(defects), defects)
                self.assertIn("criterion", defects[0])
