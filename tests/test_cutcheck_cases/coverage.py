"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck."""

from tests.test_cutcheck import *  # noqa: F401,F403

try:
    del load_tests
except NameError:
    pass

class CoverageTest(unittest.TestCase):
    def setUp(self):
        self.result = run_cutcheck("cutcheck-f5-coverage")
        self.lines = reported(self.result, cutcheck.FAMILY_5)

    def test_coverage_set_exits_nonzero(self):
        self.assertNotEqual(self.result.returncode, 0, self.result.stdout)

    def test_the_orphan_criterion_is_named_by_its_number(self):
        lines = [line for line in self.lines if cutcheck.ORPHAN_CRITERION in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn("criterion 3", lines[0])
        self.assertIn("03-absent", lines[0])

    def test_the_orphan_item_is_named_by_its_id(self):
        lines = [line for line in self.lines if cutcheck.ORPHAN_ITEM in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn("02-orphan-item", lines[0])

    def test_both_directions_and_nothing_else(self):
        self.assertEqual(len(self.lines), 2, self.result.stdout)


class AbsentMapTest(unittest.TestCase):
    def setUp(self):
        self.result = run_cutcheck("cutcheck-f5-nomap")
        self.lines = reported(self.result, cutcheck.FAMILY_5)

    def test_the_absent_map_is_one_line_and_no_violation(self):
        self.assertEqual(len(self.lines), 1, self.result.stdout)
        self.assertIn(cutcheck.COVERAGE_MAP_ABSENT, self.lines[0])
        self.assertEqual(self.result.returncode, 0, self.result.stdout)

    def test_no_orphan_is_reported_in_either_direction(self):
        self.assertNotIn(cutcheck.ORPHAN_CRITERION, self.result.stdout)
        self.assertNotIn(cutcheck.ORPHAN_ITEM, self.result.stdout)


class ThreeRootCoverageTest(unittest.TestCase):
    """A template instantiates several top-level cuts into one run, and
    family 5 was written for one.

    One map per run meant each root's criteria were read against every other
    root's items — so every top-level stub of a template was ORPHAN_ITEM
    against whichever map happened to be there, and three decomposers writing
    `coverage.md` overwrote one another. The map is now the root's, named for
    it, and a root's issued set is `<root>.NN` and nothing else.
    """

    def setUp(self):
        self.result = run_cutcheck("cutcheck-f5-template")
        self.lines = reported(self.result, cutcheck.FAMILY_5)

    def test_a_top_level_stub_of_the_template_is_never_an_orphan_item(self):
        self.assertNotIn(cutcheck.ORPHAN_ITEM, self.result.stdout)
        for stub in ("01-design", "02-materialize"):
            self.assertNotIn(f"{stub}: family 5: {cutcheck.ORPHAN_ITEM}",
                             self.result.stdout)

    def test_the_root_with_a_map_is_answered_by_its_own_subtree(self):
        self.assertNotIn(cutcheck.ORPHAN_CRITERION, self.result.stdout)
        self.assertEqual(1, len(self.lines), self.result.stdout)

    def test_the_absent_map_is_reported_against_the_root_that_owes_it(self):
        self.assertIn(cutcheck.COVERAGE_MAP_ABSENT, self.lines[0])
        self.assertTrue(self.lines[0].startswith("02-materialize:"), self.lines[0])
        self.assertIn("02-materialize.coverage.md", self.lines[0])
        self.assertEqual(0, self.result.returncode, self.result.stdout)

    def test_each_roots_issued_set_is_its_own_subtree(self):
        siblings = {
            "00-acquire": {"executor": "orch-decompose"},
            "00-acquire.01": {"executor": "orch-tdd"},
            "00-acquire.gate.verify": {"executor": "orch-verify"},
            "01-design": {"executor": "orch-tdd"},
            "02-materialize": {"executor": "orch-decompose"},
        }
        self.assertEqual(["00-acquire.01"],
                         cutcheck._issued_under(siblings, "00-acquire"))
        self.assertEqual([], cutcheck._issued_under(siblings, "02-materialize"))


class CoverageHomeTest(unittest.TestCase):
    """The map is found beside the ticket root cutcheck resolved, not at a path."""

    def test_a_single_root_still_reads_the_legacy_map(self):
        """`runs/<run>/coverage.md` is the one-root spelling and every run in
        the sink already carries one. It keeps meaning what it said."""

        fixture = ROOT / "tests" / "fixtures" / "cutcheck" / "cutcheck-root-gate"
        self.assertEqual(
            fixture / "coverage.md",
            cutcheck._map_for_root(fixture, "00-root", True),
        )

    def test_several_roots_never_fall_back_to_one_shared_map(self):
        fixture = ROOT / "tests" / "fixtures" / "cutcheck" / "cutcheck-root-gate"
        self.assertEqual(
            fixture / "00-root.coverage.md",
            cutcheck._map_for_root(fixture, "00-root", False),
        )

    def test_a_fixture_set_carries_its_map_beside_its_tickets(self):
        fixture = ROOT / "tests" / "fixtures" / "cutcheck" / "cutcheck-f5-coverage"
        self.assertEqual(cutcheck._coverage_path(fixture), fixture / "coverage.md")

    def test_a_runs_map_sits_beside_its_worklog(self):
        self.assertEqual(
            cutcheck._coverage_path(ROOT / ".orch" / "tickets" / "some-run"),
            ROOT / ".orch" / "runs" / "some-run" / "coverage.md",
        )

    def test_the_canary_root_carries_no_map(self):
        canary = ROOT / ".orch" / "canary" / "tickets" / "canary"
        self.assertIsNone(cutcheck._coverage_path(canary))
