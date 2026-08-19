"""Behavioral cases imported by the ``tests.test_tickets_issue`` seam."""

from .common import *  # noqa: F401,F403

class CriterionNestingTest(unittest.TestCase):
    """Indentation, in the one owner of criterion parsing.

    `scripts/cutcheck.py` carried a second parser with these two rules in it
    and graded the same sections by them; the rules live here now, so a
    section reads the same to the cutter and to the refusal that issues it.
    """

    def test_a_list_nested_under_a_criterion_is_that_criterions_own_text(self):
        section = (
            "1. the installer names every script | oracle: `grep -n X install.py`\n"
            "   | oracle_class: deterministic, over\n"
            "   1. the tuple it opens, and\n"
            "   2. every name it lists.\n"
            "2. the second criterion opens on its own | oracle: y "
            "| oracle_class: judged\n"
        )
        criteria = tickets_mod._criteria(section)
        self.assertEqual(2, len(criteria), criteria)
        self.assertIn("1. the tuple it opens, and", criteria[0])
        self.assertEqual([], criterion(section))

    def test_an_unindented_prose_line_ends_the_continuation_not_the_list(self):
        section = (
            "1. first | oracle: a | oracle_class: deterministic\n"
            "\n"
            "An unindented prose line interrupts the list here.\n"
            "\n"
            "  2. second | oracle: b | oracle_class: judged\n"
        )
        criteria = tickets_mod._criteria(section)
        self.assertEqual(2, len(criteria), criteria)
        self.assertNotIn("unindented prose", criteria[0])

    def test_a_bullet_at_the_opening_indentation_still_opens_its_own_criterion(self):
        section = (
            "  - first | oracle: a | oracle_class: deterministic\n"
            "  - second | oracle: b | oracle_class: judged\n"
        )
        self.assertEqual(2, len(tickets_mod._criteria(section)))


class TicketDefectsTest(unittest.TestCase):
    """`ticket_defects` is the one owner of ticket shape in code: frontmatter
    keys, the status enum, the body sections, and every criterion defect."""

    def test_a_ticket_in_contract_shape_has_no_defects(self):
        self.assertEqual([], tickets_mod.ticket_defects(GOOD_TICKET))

    def test_a_file_with_no_frontmatter_is_the_only_defect_reported(self):
        defects = tickets_mod.ticket_defects("## Objective\n\nA ticket without a head.\n")
        self.assertEqual(1, len(defects), defects)
        self.assertIn("frontmatter", defects[0])

    def test_each_required_frontmatter_key_is_named_when_absent(self):
        for key in ("executor", "depends_on", "write_scope", "bound", "run", "status"):
            with self.subTest(key):
                stripped = "\n".join(
                    line for line in GOOD_TICKET.splitlines()
                    if not line.startswith(f"{key}:")
                )
                defects = tickets_mod.ticket_defects(stripped)
                self.assertTrue(
                    any(f"'{key}'" in defect for defect in defects), defects
                )

    def test_an_off_enum_status_is_named_with_the_enum(self):
        defects = tickets_mod.ticket_defects(
            GOOD_TICKET.replace("status: ready", "status: in-progress")
        )
        self.assertTrue(any("in-progress" in defect for defect in defects), defects)
        self.assertTrue(any("complete" in defect for defect in defects), defects)

    def test_legacy_checker_reading_and_real_checker_lifecycle_remain_valid(self):
        self.assertEqual([], tickets_mod.ticket_defects(GOOD_TICKET))
        checked = GOOD_TICKET.replace("status: ready", "status: claimed").replace(
            "executor: orch-tdd",
            "executor: orch-tdd\nindependence: checker\nchecked_by: checker-a",
        ).replace("claimed_by:", "claimed_by: agent-a")
        self.assertEqual([], tickets_mod.ticket_defects(checked))

        root_cut_check = checked.replace("executor: orch-tdd", "executor: orch-decompose").replace(
            "independence: checker", "independence: gate"
        )
        self.assertEqual([], tickets_mod.ticket_defects(root_cut_check))

    def test_each_required_body_section_is_named_when_absent(self):
        for section in (
            "Objective", "Fixed inputs", "Completion test", "Return fields",
            "Result", "Verification", "Feedback", "Risks",
        ):
            with self.subTest(section):
                text = GOOD_TICKET.replace(f"## {section}", "## Something else", 1)
                defects = tickets_mod.ticket_defects(text)
                self.assertTrue(
                    any(section in defect for defect in defects), (section, defects)
                )

    def test_a_criterion_defect_is_a_ticket_defect(self):
        defects = tickets_mod.ticket_defects(
            GOOD_TICKET.replace(" | oracle_class: deterministic", "")
        )
        self.assertTrue(any("oracle_class" in defect for defect in defects), defects)

    def test_a_stub_needs_neither_run_nor_status(self):
        """A stub is a ticket missing only `run`, `status` and `claimed_*`;
        those are instantiation's to add, so a stub is not defective for
        lacking them — and is still graded on everything else."""

        self.assertEqual([], tickets_mod.ticket_defects(GOOD_STUB, stub=True))
        self.assertNotEqual([], tickets_mod.ticket_defects(GOOD_STUB))

    def test_a_stub_is_still_graded_on_the_keys_it_must_carry(self):
        without_executor = "\n".join(
            line for line in GOOD_STUB.splitlines()
            if not line.startswith("executor:")
        )
        defects = tickets_mod.ticket_defects(without_executor, stub=True)
        self.assertTrue(any("'executor'" in defect for defect in defects), defects)

    def test_a_stub_carrying_an_off_enum_status_is_still_refused(self):
        defects = tickets_mod.ticket_defects(
            GOOD_STUB.replace("executor: orch-tdd", "executor: orch-tdd\nstatus: nearly"),
            stub=True,
        )
        self.assertTrue(any("nearly" in defect for defect in defects), defects)

class PacketGradesEveryCriterionTest(unittest.TestCase):
    """`packet`'s completion-test check is `criterion_defects`, so the
    refusal says which criterion and what it lacks. The whole-section
    substring test it replaces claimed to check every criterion and checked
    the section once."""

    def two_criteria(self, second: str) -> str:
        return GOOD_TICKET.replace(
            f"- {GOOD_CRITERION}", f"- {GOOD_CRITERION}\n- {second}"
        )

    def test_a_second_criterion_naming_no_class_is_refused_by_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            place(sink, "testrun", "T1", self.two_criteria("the doc reads well | oracle: the lens"))
            payload = run_cmd("packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("error", payload)
            self.assertIn("criterion 2", payload["error"])
            self.assertIn("oracle_class", payload["error"])

    def test_the_section_naming_a_class_once_no_longer_carries_the_rest(self):
        """The case the old check passed: `oracle_class` appears in the
        section, so the substring was found, and the second criterion named
        neither an oracle nor a class."""

        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            place(sink, "testrun", "T1", self.two_criteria("it looks right"))
            payload = run_cmd("packet", "testrun", "T1", "--reply-to", "main")
            self.assertIn("error", payload)
            self.assertIn("criterion 2", payload["error"])

    def test_every_criterion_naming_both_is_dispatched(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = use_sink(Path(tmp))
            place(
                sink, "testrun", "T1",
                self.two_criteria("the lens finds no defect | oracle: the lens | oracle_class: judged"),
            )
            payload = run_cmd("packet", "testrun", "T1", "--reply-to", "main")
            self.assertNotIn("error", payload)
            self.assertEqual("T1", payload["packet"]["id"])
