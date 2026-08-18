"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck."""

from tests.test_cutcheck import *  # noqa: F401,F403
from tests.test_cutcheck import _graded_with

try:
    del load_tests
except NameError:
    pass

class DiscriminationTest(unittest.TestCase):
    def setUp(self):
        self.result = run_cutcheck("cutcheck-f1-discrimination")
        self.lines = reported(self.result)

    def test_dirty_set_exits_nonzero_naming_ticket_and_family(self):
        self.assertNotEqual(self.result.returncode, 0, self.result.stdout)
        self.assertTrue(self.lines, self.result.stdout + self.result.stderr)
        for line in self.lines:
            self.assertIn("01-discrimination", line)
            self.assertIn(cutcheck.FAMILY, line)

    def test_exactly_three_violations_one_per_case(self):
        self.assertEqual(len(self.lines), 3, "\n".join(self.lines))

    def test_each_discrimination_class_is_reported_once(self):
        classes = sorted(line.split(": ")[2] for line in self.lines)
        self.assertEqual(
            classes,
            sorted([
                cutcheck.ALREADY_PASSES,
                cutcheck.NO_HITS_BOTH_REVISIONS,
                cutcheck.FAILS_BOTH_REVISIONS,
            ]),
            "\n".join(self.lines),
        )

    def test_no_span_in_this_set_writes_into_the_copy(self):
        """This corpus reads the same on every host, and a regression says so here.

        Case 3 was once `python3 -m pytest ...`, which writes `.pytest_cache/`
        into the copy it is graded in: a true finding, and one that exists only
        where pytest is installed. This repository's CI installs nothing, so
        pinning that finding would have pinned this host. The span is a unittest
        node id now, and this is what that bought — whatever a reader's host
        carries, no span here writes into the copy, so the recorded verdict is
        the verdict everywhere. A span that starts writing fails here instead of
        being re-pinned into the fixture.
        """

        wrote = [line for line in self.lines if cutcheck.UNCONFINED_ORACLE in line]
        self.assertEqual(wrote, [], "\n".join(self.lines))


class ShapeTest(unittest.TestCase):
    def setUp(self):
        self.result = run_cutcheck("cutcheck-f1-shape")
        self.lines = reported(self.result)

    def test_shape_set_exits_nonzero(self):
        self.assertNotEqual(self.result.returncode, 0, self.result.stdout)

    def test_swallowed_exit_and_cumulative_range_are_each_reported(self):
        classes = sorted(line.split(": ")[2] for line in self.lines)
        self.assertEqual(
            classes,
            sorted([cutcheck.CUMULATIVE_RANGE, cutcheck.SWALLOWED_EXIT]),
            "\n".join(self.lines),
        )
        for line in self.lines:
            self.assertIn("01-shape", line)


class ExtractionGapTest(unittest.TestCase):
    def setUp(self):
        self.result = run_cutcheck("cutcheck-f1-extraction-gap")
        self.lines = reported(self.result)

    def test_gap_never_sets_exit_status(self):
        self.assertEqual(self.result.returncode, 0, self.result.stdout)

    def test_gap_is_reported_on_its_own_line_naming_ticket_and_criterion(self):
        gaps = [line for line in self.lines if cutcheck.EXTRACTION_GAP in line]
        self.assertEqual(len(gaps), 1, "\n".join(self.lines))
        self.assertIn("01-extraction-gap", gaps[0])
        self.assertIn("criterion 1", gaps[0])


class CutTimeTest(unittest.TestCase):
    """At cut time HEAD is the baseline, and every honest oracle fails there.

    Both readings go through the public command in this process, standing at
    the repository root and sharing the harness's real clones. Separate tests
    retain the real process boundary; this claim is the status and findings for
    two revisions, which `main` returns directly.
    """

    def test_same_revision_reads_green(self):
        code, out = _graded_with(
            self,
            ["cutcheck-f1-cuttime", "--baseline", "HEAD"]
        )
        result = subprocess.CompletedProcess([], code, stdout=out, stderr="")
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(reported(result), [])

    def test_a_baseline_behind_head_still_reports_it(self):
        result = run_cutcheck("cutcheck-f1-cuttime")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        lines = reported(result)
        self.assertEqual(len(lines), 1, "\n".join(lines))
        self.assertIn(cutcheck.NO_HITS_BOTH_REVISIONS, lines[0])


class TruncatedListTest(unittest.TestCase):
    def test_no_numbered_criterion_is_dropped(self):
        numbers = [n for n, _ in fixture_criteria("cutcheck-f1-truncated", "01-truncated.md")]
        self.assertEqual(numbers, [1, 2])

    def test_the_criterion_after_the_prose_line_surfaces_as_a_gap(self):
        lines = reported(run_cutcheck("cutcheck-f1-truncated"))
        gaps = [line for line in lines if cutcheck.EXTRACTION_GAP in line]
        self.assertEqual(len(gaps), 1, "\n".join(lines))
        self.assertIn("criterion 2", gaps[0])


class PhantomCriterionTest(unittest.TestCase):
    """A wrapped line opening with a digit is text, not a criterion of its own."""

    def setUp(self):
        self.criteria = fixture_criteria("cutcheck-f1-phantom", "01-phantom.md")
        self.texts = dict(self.criteria)

    def test_the_wrap_opens_no_item_of_its_own(self):
        self.assertEqual([number for number, _ in self.criteria], [1, 2, 3])

    def test_the_interrupted_criterion_keeps_the_text_after_the_wrap(self):
        text = self.texts[2]
        self.assertIn('grep -n "SCRIPT_NAMES" install.py', text)
        self.assertTrue(
            text.endswith(
                "exits 0. oracle_class: deterministic. provenance: pre-existing."
            ),
            text,
        )

    def test_the_wrapped_stamp_belongs_to_the_criterion_that_wrapped(self):
        self.assertEqual(
            cutcheck.PRE_EXISTING,
            cutcheck._stated_provenance(self.texts[2]),
            self.texts[2],
        )


class NestedEnumerationTest(unittest.TestCase):
    """Indentation is relative: a nested list continues, an indented list opens."""

    def test_a_nested_enumeration_stays_inside_the_criterion_holding_it(self):
        criteria = fixture_criteria("cutcheck-f1-phantom", "02-nested-list.md")
        self.assertEqual([number for number, _ in criteria], [1, 2])
        first = dict(criteria)[1]
        self.assertIn(
            "1. the tuple the installer opens, and 2. every script name it lists.",
            first,
        )
        self.assertEqual(cutcheck.PRE_EXISTING, cutcheck._stated_provenance(first), first)

    def test_a_set_whose_criteria_are_written_indented_is_still_a_list(self):
        criteria = fixture_criteria("cutcheck-f1-truncated", "01-truncated.md")
        self.assertEqual([number for number, _ in criteria], [1, 2])
        self.assertIn(
            "A reviewer names, from the module docstring alone", dict(criteria)[2]
        )


class PathRealityTest(unittest.TestCase):
    def setUp(self):
        self.result = run_cutcheck("cutcheck-f2-paths")
        self.lines = reported(self.result, cutcheck.FAMILY_2)

    def test_path_set_exits_nonzero_naming_ticket_and_family(self):
        self.assertNotEqual(self.result.returncode, 0, self.result.stdout)
        self.assertTrue(self.lines, self.result.stdout + self.result.stderr)
        for line in self.lines:
            self.assertIn("01-f2-paths", line)
            self.assertIn(cutcheck.FAMILY_2, line)

    def test_exactly_three_violations_one_per_case(self):
        self.assertEqual(len(finding_lines(self.result)), 3, self.result.stdout)
        self.assertEqual(len(self.lines), 3, self.result.stdout)

    def test_each_path_class_is_reported_once(self):
        classes = sorted(line.split(": ")[2] for line in self.lines)
        self.assertEqual(
            classes,
            sorted(
                [
                    cutcheck.MISSING_PATH,
                    cutcheck.UNRESOLVED_CITATION,
                    cutcheck.QUOTE_NOT_AT_CITATION,
                ]
            ),
            self.result.stdout,
        )


class CarveOutTest(unittest.TestCase):
    """Reading is not writing; an ancestor's path is present; the baseline decides."""

    def setUp(self):
        self.result = run_cutcheck("cutcheck-carveouts")

    def test_the_set_is_reported_clean(self):
        self.assertEqual(self.result.returncode, 0, self.result.stdout + self.result.stderr)
        # Every finding line, not a line of it: nothing was found here, and
        # the affirmative line closes the report the shape reading precedes.
        self.assertEqual(finding_lines(self.result), [], self.result.stdout)
        self.assertEqual(
            self.result.stdout.splitlines()[-1], cutcheck.NO_FINDING_OUTSIDE
        )

    def test_a_path_the_item_only_reads_is_no_scope_defect(self):
        self.assertNotIn("01-reads-only", "\n".join(finding_lines(self.result)))

    def test_a_path_a_depends_on_ancestor_makes_is_present(self):
        self.assertNotIn("02-depends", "\n".join(finding_lines(self.result)))

    def test_a_quote_resolves_at_the_baseline_not_the_workspace(self):
        self.assertNotIn("03-baseline-quote", "\n".join(finding_lines(self.result)))


class ScopeClosureTest(unittest.TestCase):
    def setUp(self):
        self.result = run_cutcheck("cutcheck-f3-scope")
        self.lines = reported(self.result, cutcheck.FAMILY_3)

    def test_scope_set_exits_nonzero(self):
        self.assertNotEqual(self.result.returncode, 0, self.result.stdout)

    def test_each_scope_class_is_reported_once(self):
        classes = sorted(line.split(": ")[2] for line in self.lines)
        self.assertEqual(
            classes,
            sorted([cutcheck.SCOPE_CONTRADICTION, cutcheck.UNSCOPED_WRITE]),
            self.result.stdout,
        )

    def test_the_uncovered_sink_is_named_with_its_ticket(self):
        lines = [line for line in self.lines if cutcheck.UNSCOPED_WRITE in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn("01-unscoped", lines[0])
        self.assertIn(".orch/evidence/f3-scope/verdict.txt", lines[0])

    def test_the_self_contradiction_names_the_shared_path(self):
        lines = [line for line in self.lines if cutcheck.SCOPE_CONTRADICTION in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn("02-contradiction", lines[0])
        self.assertIn("scripts/cutcheck.py", lines[0])


class PairwiseSafetyTest(unittest.TestCase):
    def setUp(self):
        self.result = run_cutcheck("cutcheck-f4-pairs")
        self.lines = reported(self.result, cutcheck.FAMILY_4)

    def test_pair_set_exits_nonzero(self):
        self.assertNotEqual(self.result.returncode, 0, self.result.stdout)

    def test_the_staged_invalidation_names_both_ids_and_the_path(self):
        lines = [line for line in self.lines if cutcheck.STAGED_INVALIDATION in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn("01-reader", lines[0])
        self.assertIn("02-rewriter", lines[0])
        self.assertIn("install.py", lines[0])

    def test_the_shared_scope_names_both_ids(self):
        lines = [line for line in self.lines if cutcheck.SCOPE_COLLISION in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn("03-alpha", lines[0])
        self.assertIn("04-beta", lines[0])

    def test_no_other_pair_is_reported(self):
        self.assertEqual(len(self.lines), 2, self.result.stdout)


class OrderedPairTest(unittest.TestCase):
    """A pair the DAG orders is no defect, by an edge or by reachability."""

    def test_a_direct_edge_orders_the_pair(self):
        result = run_cutcheck("cutcheck-f4-ordered")
        self.assertEqual(reported(result, cutcheck.FAMILY_4), [], result.stdout)

    def test_order_through_a_middle_item_is_order(self):
        result = run_cutcheck("cutcheck-f4-transitive")
        self.assertEqual(reported(result, cutcheck.FAMILY_4), [], result.stdout)


CANARY = cutcheck._run_dir("canary", ROOT)


@unittest.skipUnless(CANARY is not None, "the canary ticket set is not present")
class CanarySetTest(unittest.TestCase):
    """The tracked canary fixture, unmodified: its scope defect must surface."""

    def test_no_coverage_or_executor_false_positive_over_the_canary(self):
        result = run_cutcheck("canary")
        for klass in (
            cutcheck.ORPHAN_CRITERION,
            cutcheck.ORPHAN_ITEM,
            cutcheck.ILLEGAL_EXECUTOR,
        ):
            self.assertNotIn(klass, result.stdout)

    def test_the_canary_scope_defect_is_reported(self):
        result = run_cutcheck("canary")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        lines = [
            line
            for line in reported(result, cutcheck.FAMILY_3)
            if "canary-scope-reject" in line
        ]
        self.assertEqual(len(lines), 1, result.stdout)
        self.assertIn(cutcheck.UNSCOPED_WRITE, lines[0])
        self.assertIn("extra.txt", lines[0])


class PackCellHomeTest(unittest.TestCase):
    """Family 6 reads the library's packs, never the target repository's.

    A pack cell is a fact about orchflows, and the tree under test is whatever
    repository the run's work lands in. Resolving the cells against the
    invoking worktree meant that from any target carrying no `packs/` --
    which is every target but this one -- `_pack_cells` returned the empty set
    and family 6 had nothing left to grade. The check passed by finding
    nothing to check.
    """

    def setUp(self):
        self.empty = Path(tempfile.mkdtemp(prefix="cutcheck-nopacks-"))
        self.addCleanup(remove_repo_tree, self.empty)

    def test_the_library_is_the_tree_this_tool_runs_from(self):
        self.assertEqual(cutcheck._lib_root(None), ROOT)

    def test_an_explicit_lib_decides_it(self):
        self.assertEqual(cutcheck._lib_root(str(self.empty)), self.empty)

    def test_the_packs_of_that_library_are_what_the_cells_come_from(self):
        self.assertIn(
            "orch-tdd", cutcheck._pack_cells("orch-code-pack", cutcheck._lib_root(None))
        )
        self.assertEqual(set(), cutcheck._pack_cells("orch-code-pack", self.empty))

    def test_a_library_carrying_no_packs_grades_nothing_at_all(self):
        """Since P4-3 the pack cells are the whole of family 6 — the engine
        prohibition that used to survive an empty library is deleted with the
        two engines it named. So an empty library is not a weaker grading, it
        is no grading, which is exactly what `_lib_root` exists to prevent."""
        siblings = {
            "01-alien": {"id": "01-alien", "executor": "orch-render",
                         "pack": "orch-code-pack"},
            "02-legal": {"id": "02-legal", "executor": "orch-tdd",
                         "pack": "orch-code-pack"},
        }
        self.assertEqual([], cutcheck._executor_legality(siblings, self.empty))
        self.assertEqual(
            ["01-alien"],
            [item for item, _, _, _ in cutcheck._executor_legality(siblings, ROOT)],
        )

    def test_the_flag_that_names_the_library_is_documented(self):
        spawned = run_cutcheck_subprocess(["--help"])
        self.assertEqual(spawned.returncode, 0, spawned.stderr)
        self.assertIn("--lib", " ".join(spawned.stdout.split()))
