"""Tests for scripts/cutcheck.py: family 1, oracle discrimination and shape."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import install  # noqa: E402
import scripts.cutcheck as cutcheck  # noqa: E402
import scripts.tickets as tickets  # noqa: E402

# cutcheck clones this revision to build the tree it grades oracles in, so
# every clone that runs these tests must be able to reach it. Two invariants
# make a candidate legal, and both are load-bearing: it is an ancestor of
# `main`, so a fresh clone has it (the predecessor pinned an unpushed local
# branch tip, which passed here and failed every CI leg with "cannot clone
# baseline"); and `install.py:101` there opens `SCRIPT_NAMES` without
# `cutcheck.py`, which is what makes the fixtures' `grep -n "cutcheck.py"
# install.py` fail at the baseline and pass at HEAD -- the discrimination the
# family 1 fixtures exist to exercise. Reachability also needs
# `fetch-depth: 0` in .github/workflows/checks.yml; a depth-1 checkout has one
# commit and no ancestor is archivable.
BASELINE = "462ef52aab37655260bdc9f9f98be4ed2601af2d"


def run_cutcheck(run, baseline=BASELINE):
    """Invoke cutcheck exactly as the completion test states it."""

    return subprocess.run(
        [sys.executable, "scripts/cutcheck.py", run, "--baseline", baseline],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


def reported(result, family=cutcheck.FAMILY):
    return [line for line in result.stdout.splitlines() if family in line]


def report(result):
    """The report split where its own two summary lines split it.

    Findings outside the advisory set first, then the advisory findings under
    the heading, then whether the affirmative line closed the report.
    """

    lines = result.stdout.splitlines()
    affirmed = bool(lines) and lines[-1] == cutcheck.NO_FINDING_OUTSIDE
    if affirmed:
        lines = lines[:-1]
    if cutcheck.ADVISORY_HEADING in lines:
        cut = lines.index(cutcheck.ADVISORY_HEADING)
        return lines[:cut], lines[cut + 1:], affirmed
    return lines, [], affirmed


def fixture_criteria(run, name):
    path = ROOT / "tests" / "fixtures" / "cutcheck" / run / name
    section = tickets._sections(path.read_text(encoding="utf-8"))
    return cutcheck._criteria(section[cutcheck.COMPLETION_SECTION])


class CleanSetTest(unittest.TestCase):
    def test_clean_set_exits_zero_and_reports_nothing(self):
        result = run_cutcheck("cutcheck-clean")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(reported(result), [])


class AffirmativeSummaryTest(unittest.TestCase):
    """A set with no finding outside the advisory set says so, rather than nothing."""

    def test_the_clean_set_prints_the_affirmative_line_and_exits_zero(self):
        result = run_cutcheck("cutcheck-clean")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.splitlines(), [cutcheck.NO_FINDING_OUTSIDE])

    def test_a_set_holding_a_finding_outside_the_advisory_set_never_affirms(self):
        violations, _, affirmed = report(run_cutcheck("cutcheck-f2-paths"))
        self.assertTrue(violations, violations)
        self.assertFalse(affirmed, violations)


class AdvisoryMarkingTest(unittest.TestCase):
    """An advisory finding is printed where the report says it decides nothing."""

    def _classes(self, lines):
        return [line.split(": ")[2] for line in lines]

    def test_the_advisory_finding_is_reported_under_the_heading(self):
        violations, advisories, _ = report(run_cutcheck("cutcheck-f1-extraction-gap"))
        self.assertEqual(violations, [], violations)
        self.assertIn(cutcheck.EXTRACTION_GAP, self._classes(advisories), advisories)

    def test_a_finding_outside_the_advisory_set_is_never_under_the_heading(self):
        violations, advisories, _ = report(run_cutcheck("cutcheck-provenance"))
        self.assertTrue(violations, violations)
        self.assertTrue(advisories, advisories)
        for klass in self._classes(violations):
            self.assertNotIn(klass, cutcheck.ADVISORY, violations)
        for klass in self._classes(advisories):
            self.assertIn(klass, cutcheck.ADVISORY, advisories)

    def test_one_heading_stands_over_the_whole_advisory_block(self):
        result = run_cutcheck("cutcheck-verdict-in-output")
        lines = result.stdout.splitlines()
        self.assertEqual(lines.count(cutcheck.ADVISORY_HEADING), 1, result.stdout)
        self.assertGreater(len(report(result)[1]), 1, result.stdout)

    def test_neither_summary_line_can_be_read_as_a_finding(self):
        markers = sorted(cutcheck.FAMILY_OF) + sorted(set(cutcheck.FAMILY_OF.values()))
        markers += ["criterion ", "scripts/cutcheck.py"]
        for line in (cutcheck.ADVISORY_HEADING, cutcheck.NO_FINDING_OUTSIDE):
            for marker in markers:
                self.assertNotIn(marker, line)


class AdvisoryExitZeroTest(unittest.TestCase):
    """Exit 0 is no finding outside the advisory set, never a set with no finding."""

    def test_an_advisory_finding_is_reported_and_the_status_is_still_zero(self):
        result = run_cutcheck("cutcheck-verdict-in-output")
        violations, advisories, affirmed = report(result)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(violations, [], result.stdout)
        self.assertTrue(advisories, result.stdout)
        self.assertTrue(affirmed, result.stdout)


class ExitCodeEpilogTest(unittest.TestCase):
    """`--help` names each exit status, and says a verdict stays on its host."""

    def setUp(self):
        result = subprocess.run(
            [sys.executable, "scripts/cutcheck.py", "--help"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.help = " ".join(result.stdout.split())

    def test_zero_is_no_finding_outside_the_advisory_set_and_not_a_clean_set(self):
        self.assertIn(
            "0 Cutcheck's exit 0 means no finding whose class lies outside the "
            "advisory set, not that the set is clean: an advisory finding is "
            "reported and exits 0.",
            self.help,
        )

    def test_one_is_a_finding_outside_the_advisory_set(self):
        self.assertIn(
            "1 At least one finding whose class lies outside the advisory set.",
            self.help,
        )

    def test_two_is_no_ticket_set_and_argparses_own_usage_error(self):
        self.assertIn(
            "2 No ticket set resolved for the run; argparse's own usage error "
            "exits 2 as well.",
            self.help,
        )

    def test_a_verdict_is_read_only_on_the_host_that_produced_it(self):
        self.assertIn(
            "A cut verdict is not portable between hosts. An oracle naming an "
            "interpreter one host lacks is reported there as unrunnable-oracle "
            "and is silent here, so a verdict is read only on the host that "
            "produced it.",
            self.help,
        )

    def test_the_epilog_leaves_the_families_to_the_module_docstring(self):
        for family in sorted(set(cutcheck.FAMILY_OF.values())):
            self.assertNotIn(family, self.help)


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
            sorted(
                [
                    cutcheck.ALREADY_PASSES,
                    cutcheck.NO_HITS_BOTH_REVISIONS,
                    cutcheck.FAILS_BOTH_REVISIONS,
                ]
            ),
            "\n".join(self.lines),
        )


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
    """At cut time HEAD is the baseline, and every honest oracle fails there."""

    def test_same_revision_reads_green(self):
        result = run_cutcheck("cutcheck-f1-cuttime", baseline="HEAD")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
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
        self.assertTrue(cutcheck.PRE_EXISTING_RE.search(self.texts[2]), self.texts[2])


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
        self.assertTrue(cutcheck.PRE_EXISTING_RE.search(first), first)

    def test_a_set_whose_criteria_are_written_indented_is_still_a_list(self):
        criteria = fixture_criteria("cutcheck-f1-truncated", "01-truncated.md")
        self.assertEqual([number for number, _ in criteria], [1, 2])
        self.assertIn(
            "A reviewer names, from the module docstring alone", dict(criteria)[2]
        )

    def test_the_indented_criterion_still_surfaces_in_the_report(self):
        lines = reported(run_cutcheck("cutcheck-f1-truncated"))
        gaps = [line for line in lines if cutcheck.EXTRACTION_GAP in line]
        self.assertEqual(len(gaps), 1, "\n".join(lines))
        self.assertIn("criterion 2", gaps[0])


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
        self.assertEqual(len(self.result.stdout.splitlines()), 3, self.result.stdout)
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
        # The whole report, not a line of it: nothing was found here but the
        # affirmative line that says so.
        self.assertEqual(self.result.stdout.splitlines(), [cutcheck.NO_FINDING_OUTSIDE])

    def test_a_path_the_item_only_reads_is_no_scope_defect(self):
        self.assertNotIn("01-reads-only", self.result.stdout)

    def test_a_path_a_depends_on_ancestor_makes_is_present(self):
        self.assertNotIn("02-depends", self.result.stdout)

    def test_a_quote_resolves_at_the_baseline_not_the_workspace(self):
        self.assertNotIn("03-baseline-quote", self.result.stdout)


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


class ExecutorLegalityTest(unittest.TestCase):
    def setUp(self):
        self.result = run_cutcheck("cutcheck-f6-executor")
        self.lines = reported(self.result, cutcheck.FAMILY_6)

    def test_executor_set_exits_nonzero(self):
        self.assertNotEqual(self.result.returncode, 0, self.result.stdout)

    def test_an_engine_executor_is_reported_with_its_ticket(self):
        lines = [line for line in self.lines if "01-engine" in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn(cutcheck.ILLEGAL_EXECUTOR, lines[0])
        self.assertIn("orch-task", lines[0])

    def test_an_executor_no_cell_of_the_pack_names_is_reported(self):
        lines = [line for line in self.lines if "03-alien" in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn("orch-render", lines[0])
        self.assertIn("orch-code-pack", lines[0])

    def test_the_packs_own_executor_cell_is_not_reported(self):
        self.assertNotIn("02-legal", self.result.stdout)

    def test_the_engine_set_is_the_ticket_scripts_own(self):
        self.assertIs(cutcheck.ENGINE_EXECUTORS, tickets.ENGINE_EXECUTORS)


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


class CoverageHomeTest(unittest.TestCase):
    """The map is found beside the ticket root cutcheck resolved, not at a path."""

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


SHELL_MARK = Path("/tmp/cutcheck-shellhead-ran")


class ShellHeadTest(unittest.TestCase):
    """Ticket content is untrusted input: no span of one reaches a shell."""

    def setUp(self):
        SHELL_MARK.unlink(missing_ok=True)
        self.addCleanup(SHELL_MARK.unlink, True)
        self.result = run_cutcheck("cutcheck-shellhead")

    def test_the_shell_span_did_not_run(self):
        self.assertFalse(SHELL_MARK.exists(), self.result.stdout)

    def test_the_span_is_reported_rather_than_run(self):
        lines = [line for line in self.result.stdout.splitlines() if "01-shellhead" in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn(cutcheck.EXTRACTION_GAP, lines[0])


EVAL_MARK = Path("/tmp/cutcheck-evalhead-ran")


class EvalHeadTest(unittest.TestCase):
    """An interpreter handed its program on the line is a shell by another head."""

    def setUp(self):
        EVAL_MARK.unlink(missing_ok=True)
        self.addCleanup(EVAL_MARK.unlink, True)
        self.result = run_cutcheck("cutcheck-evalhead")

    def test_the_evaluated_span_did_not_run(self):
        self.assertFalse(EVAL_MARK.exists(), self.result.stdout)

    def test_the_span_is_reported_rather_than_run(self):
        lines = [line for line in self.result.stdout.splitlines() if "01-evalhead" in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn(cutcheck.EXTRACTION_GAP, lines[0])

    def test_the_interpreter_oracles_real_tickets_state_still_extract(self):
        for command in (
            "python3 -m unittest discover -s tests",
            "python3 install.py --dry-run",
            "python3 tools/validate.py",
            "python3 -m pytest tests/test_cutcheck.py::CleanSetTest",
        ):
            self.assertEqual(
                cutcheck._commands("`{}`".format(command)), [command], command
            )

    def test_a_search_flag_that_only_looks_like_one_still_extracts(self):
        self.assertEqual(
            cutcheck._commands('`grep -c "SCRIPT_NAMES" install.py`'),
            ['grep -c "SCRIPT_NAMES" install.py'],
        )


GIT_ESCAPE_MARK = Path("/tmp/cutcheck-gitescape-ran")
GIT_WROTE_MARK = Path("/tmp/cutcheck-gitescape-wrote")

# Each runs a program the span itself names, or moves the run out of the copy
# meant to confine it, or reaches the network. Every one of them is a global
# option or a subcommand, so position alone refuses the lot.
GIT_ESCAPES = (
    "git -c core.pager=touch\\ /tmp/cutcheck-gitescape-ran log",
    "git -c alias.pwn='!touch /tmp/cutcheck-gitescape-ran' pwn",
    "git --exec-path=/tmp/cutcheck-gitescape log",
    "git --upload-pack=touch\\ /tmp/cutcheck-gitescape-ran fetch origin",
    "git --receive-pack=touch\\ /tmp/cutcheck-gitescape-ran push origin",
    "git -C /etc log",
    "git --git-dir=/tmp/cutcheck-gitescape/.git log",
    "git --work-tree=/etc status",
    "git clone https://example.invalid/x",
    "git archive HEAD",
    "git grep -O/tmp/cutcheck-gitescape-ran pattern",
)

# Each stands after a subcommand the confined set holds, where position sees
# nothing, and names a location the copy does not hold: `--output` writes it,
# `-O`, `-X`, `--exclude-from`, `--no-index` and `--resolve-git-dir` read it.
# Climbing reaches as far as rooting does -- the other revision's scratch copy
# is one `..` away, and planting a file there rewrites the half of the
# discrimination reading it was not asked about.
GIT_REACHES_OUT = (
    "git log --output=/tmp/cutcheck-gitescape-wrote",
    "git diff --output /tmp/cutcheck-gitescape-wrote",
    "git rev-list HEAD --output=/tmp/cutcheck-gitescape-wrote",
    "git show --output=../cutcheck-gitescape-wrote",
    "git diff -O/tmp/cutcheck-gitescape-ran HEAD~1",
    "git ls-files -X /etc/hosts",
    "git ls-files --exclude-from=/etc/hosts",
    "git diff --no-index /etc/hosts /etc/passwd",
    "git rev-parse --resolve-git-dir /etc",
)


class GitEscapeTest(unittest.TestCase):
    """A git span is untrusted content too: it decides neither what runs nor
    what is written where.

    The head alone excuses nothing and grants nothing, and the subcommand alone
    settles only half of it. Git runs a program the span names through
    `-c core.pager=`, `-c alias.x=!`, `--exec-path`, `--upload-pack` and
    `--receive-pack`, and leaves the scratch copy through `-C`, `--git-dir` and
    `--work-tree` -- all global, all refused by standing where they stand. It
    also writes any file `--output` names, under `log` and three other confined
    subcommands, from after the subcommand where standing settles nothing; that
    one is refused by what it spells. Both are closed sets, so the flag git
    ships next is refused before anyone has heard of it.

    One invocation for the whole class: `setUpClass`, not `setUp`, because this
    tool's own suite is an oracle running under COMMAND_TIMEOUT and every
    invocation added here is spent against that budget. Both spans ride that
    one invocation. The gate itself is decided from the command text, so the
    rest of the claim needs no subprocess at all and is asserted next door.
    """

    MARKS = (GIT_ESCAPE_MARK, GIT_WROTE_MARK)

    @classmethod
    def setUpClass(cls):
        for mark in cls.MARKS:
            mark.unlink(missing_ok=True)
        cls.result = run_cutcheck("cutcheck-gitescape")

    @classmethod
    def tearDownClass(cls):
        for mark in cls.MARKS:
            mark.unlink(missing_ok=True)

    def test_the_injected_span_did_not_run(self):
        for mark in self.MARKS:
            self.assertFalse(mark.exists(), "{}\n{}".format(mark, self.result.stdout))

    def test_the_span_is_reported_rather_than_run(self):
        lines = [
            line for line in self.result.stdout.splitlines() if "01-gitescape" in line
        ]
        self.assertEqual(len(lines), 2, self.result.stdout)
        for line in lines:
            self.assertIn(cutcheck.UNCONFINED_ORACLE, line)

    def test_a_refused_span_is_a_finding_and_not_a_silence(self):
        self.assertNotIn(cutcheck.UNCONFINED_ORACLE, cutcheck.ADVISORY)
        self.assertNotEqual(self.result.returncode, 0, self.result.stdout)


class GitConfinementGateTest(unittest.TestCase):
    """Which git spans the gate runs, decided from the command text alone."""

    def test_every_escape_the_head_used_to_carry_is_refused(self):
        for command in GIT_ESCAPES:
            self.assertTrue(cutcheck._unconfined_git(command), command)
            self.assertIn(cutcheck.UNCONFINED_ORACLE, cutcheck._shape(command), command)

    def test_a_confined_subcommand_reaching_out_is_refused_too(self):
        # The subcommand is in the set and the span is still not confined: an
        # option standing after it named somewhere the copy does not hold.
        for command in GIT_REACHES_OUT:
            self.assertIn(command.split()[1], cutcheck.GIT_CONFINED_SUBCOMMANDS, command)
            self.assertTrue(cutcheck._unconfined_git(command), command)
            self.assertIn(cutcheck.UNCONFINED_ORACLE, cutcheck._shape(command), command)

    def test_the_oracles_the_graded_set_states_still_run(self):
        for command in (
            "git log -1 --format=%H",
            "git diff ac8791a -- install.py",
            "git merge-base --is-ancestor ac8791a HEAD",
            "git rev-list --count HEAD",
            "git status --porcelain",
            # What the copy holds it may reach: the rule is about the location
            # named, never about the flag naming it. A `..` between revisions
            # is a range and stays one; only a whole path component reads as a
            # climb, whatever slashes stand beside it.
            "git log --oneline ac8791a..462ef52 -- scripts/cutcheck.py",
            "git show ac8791a:install.py",
            "git diff --no-index install.py tools/validate.py",
        ):
            self.assertFalse(cutcheck._unconfined_git(command), command)
            self.assertEqual(cutcheck._shape(command), [], command)

    def test_a_head_that_is_not_git_is_judged_by_no_git_rule(self):
        for command in ("grep -n SCRIPT_NAMES install.py", "python3 tools/validate.py"):
            self.assertFalse(cutcheck._unconfined_git(command), command)

    def test_the_gate_reads_the_argv_that_would_run(self):
        # Split the way `_run_once` splits, or the gate grades one command and
        # execution runs another. Quoting that resolves to a confined
        # subcommand is confined; quoting that resolves to anything else is not.
        self.assertFalse(cutcheck._unconfined_git("git 'log' -1 --format=%H"))
        self.assertTrue(cutcheck._unconfined_git("git 'log x' -1"))

    def test_a_span_no_split_parses_is_claimed_by_nothing_and_runs_nowhere(self):
        unparsed = 'git log "'
        self.assertFalse(cutcheck._unconfined_git(unparsed))
        self.assertIsNone(cutcheck._run_once(unparsed, ROOT))


class BareCommandNounTest(unittest.TestCase):
    """A backticked command head with no argument names the tool, not an oracle."""

    def setUp(self):
        self.result = run_cutcheck("cutcheck-barenoun")

    def test_a_mention_beside_a_real_oracle_leaves_that_oracle_deciding(self):
        lines = [
            line for line in self.result.stdout.splitlines() if "criterion 1" in line
        ]
        self.assertEqual(lines, [], self.result.stdout)

    def test_the_real_oracle_is_the_only_span_extracted_there(self):
        _, criterion = fixture_criteria("cutcheck-barenoun", "01-barenoun.md")[0]
        self.assertEqual(
            cutcheck._commands(criterion), ['grep -rn "unrunnable-oracle" scripts/']
        )

    def test_a_mention_standing_alone_is_reported_as_a_gap(self):
        lines = [
            line for line in self.result.stdout.splitlines() if "criterion 2" in line
        ]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn(cutcheck.EXTRACTION_GAP, lines[0])

    def test_the_mention_reaches_no_executor(self):
        """Unreported is not enough: the bare name must run nowhere at all."""

        ticket = FIXTURES / "cutcheck-barenoun" / "01-barenoun.md"
        with mock.patch.object(cutcheck, "_exit_code", return_value=1) as ran:
            cutcheck._check_ticket(ticket, ROOT, None, {})
        commands = [call[0][0] for call in ran.call_args_list]
        self.assertIn('grep -rn "unrunnable-oracle" scripts/', commands)
        self.assertNotIn("pytest", commands)

    def test_the_oracles_real_tickets_state_still_extract(self):
        for command in (
            "python3 tools/validate.py",
            "python3 install.py --dry-run",
            "python3 -m unittest discover -s tests",
            "git diff --check",
            'grep -c "SCRIPT_NAMES" install.py',
            "rg -n pattern src/",
        ):
            self.assertEqual(
                cutcheck._commands("`{}`".format(command)), [command], command
            )


# The ticket the execution node id writes beside the tree. Its span carries a
# relative path so the run happens with the scratch tree as its working
# directory on every platform, and `authored-here` so discrimination is asked
# of it -- a `pre-existing` stamp exempts the oracle from execution, which is
# the way this test would pass while proving nothing.
QUOTED_TICKET = """---
id: 01-quoted
run: cutcheck-quoted
status: issued
---
## Objective

Fixture built beside the tree: the span below is quoted, never stated.

## Completion test

1. **A quoted span reaches no executor.** This criterion states no oracle of
   its own; it quotes one, such as `python3 writer.py`, and a quotation is
   read rather than run. oracle_class: deterministic. provenance:
   authored-here.

## Result

[]
"""


class CommandExtractionTest(unittest.TestCase):
    """A command a criterion quotes is one it talks about; only a command it
    states is one this tool runs.

    Three measured shapes, one node id each: a span quoted as what not to do,
    which graded `missing-path` and failed the gate; one quoted as what the
    confinement guard refuses, which graded `unconfined-oracle`, so a ticket
    describing the guard tripped it; and one quoted as what CI runs, which was
    executed, twice. What tells all three from an oracle is the frame standing
    immediately in front of the span -- `_scope_closure`'s question about a
    write verb, asked again of a command, against the discriminator the
    `cutcheck-mention` fixture already grades.
    """

    def test_a_span_quoted_as_what_not_to_do_is_not_extracted(self):
        self.assertEqual(
            cutcheck._commands(
                "The suite's verdict is read from its exit status, never "
                '`grep -E "^Ran" out.txt`.'
            ),
            [],
        )

    def test_a_span_quoted_as_what_the_guard_refuses_is_not_extracted(self):
        self.assertEqual(
            cutcheck._commands(
                "The confinement gate refuses `git log --output=/tmp/x` and "
                "reports it unrun."
            ),
            [],
        )

    def test_a_span_quoted_as_what_ci_runs_is_not_extracted(self):
        self.assertEqual(
            cutcheck._commands(
                "A whole-module invocation such as "
                "`python3 -m unittest tests.test_cutcheck`, which is what CI "
                "runs, reads the same under every item it is stated under."
            ),
            [],
        )

    def test_the_oracle_standing_beside_a_quotation_is_still_extracted(self):
        """The narrowing direction: one span quoted, one stated, in one criterion."""

        self.assertEqual(
            cutcheck._commands(
                '**The installer lists the script.** `grep -n "cutcheck.py" '
                'install.py` returns the SCRIPT_NAMES line, and the verdict is '
                'never `grep -E "^Ran" out.txt`.'
            ),
            ['grep -n "cutcheck.py" install.py'],
        )

    def test_a_quoted_command_is_never_executed(self):
        """Refused before execution, never after it.

        The mark is this run's own directory under `tempfile.gettempdir()`,
        never a `/tmp` literal, so no neighbouring run can unlink it between
        the execution and the assertion. The writer runs once directly first:
        an assertion that a file is absent passes vacuously wherever nothing
        could have created it, and this host is the one that decides which.
        """

        scratch = Path(tempfile.mkdtemp(prefix="cutcheck-quoted-"))
        self.addCleanup(shutil.rmtree, scratch, True)
        self.assertTrue(scratch.is_dir(), scratch)
        mark = scratch / "quoted-command-ran"
        writer = scratch / "writer.py"
        writer.write_text(
            "import pathlib\npathlib.Path(r'''{}''').write_text('ran')\n".format(mark),
            encoding="utf-8",
        )
        if cutcheck._run_once("python3 writer.py", scratch) != 0 or not mark.exists():
            self.skipTest("python3 does not run a file argument on this host")
        mark.unlink()

        ticket = scratch / "01-quoted.md"
        ticket.write_text(QUOTED_TICKET, encoding="utf-8")
        cutcheck._EXIT_CACHE.clear()
        self.addCleanup(cutcheck._EXIT_CACHE.clear)
        cutcheck._check_ticket(ticket, scratch, None, {})
        self.assertFalse(mark.exists(), "the quoted span reached an executor")

    def test_the_set_quoting_all_three_shapes_grades_clean(self):
        """All three in one issued ticket, read the way a cut reads one.

        The two classes named are the ones the shapes graded as at the
        baseline, and each set the exit status: a quotation that trips the
        gate is the defect, not the report of it.
        """

        result = run_cutcheck("cutcheck-command-mention")
        violations, _, affirmed = report(result)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(violations, [], result.stdout)
        self.assertTrue(affirmed, result.stdout)
        self.assertNotIn(cutcheck.MISSING_PATH, result.stdout)
        self.assertNotIn(cutcheck.UNCONFINED_ORACLE, result.stdout)


class ParserReuseTest(unittest.TestCase):
    def test_frontmatter_and_section_parsers_are_the_ticket_scripts_own(self):
        self.assertIs(cutcheck._parse_frontmatter, tickets._parse_frontmatter)
        self.assertIs(cutcheck._sections, tickets._sections)


class InstallationTest(unittest.TestCase):
    def test_cutcheck_is_installed_under_its_bare_name(self):
        self.assertIn("cutcheck.py", install.SCRIPT_NAMES)


class ProvenanceTest(unittest.TestCase):
    """A stated ``pre-existing`` provenance exempts an invariant, and only that."""

    def setUp(self):
        self.result = run_cutcheck("cutcheck-provenance")
        self.lines = reported(self.result)

    def test_the_invariant_is_not_reported_for_passing_at_the_baseline(self):
        self.assertNotIn("01-pre-existing: family 1: already-passes", self.result.stdout)

    def test_the_same_oracle_authored_here_is_still_reported(self):
        lines = [line for line in self.lines if cutcheck.ALREADY_PASSES in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn("02-authored-here", lines[0])

    def test_shape_is_judged_whatever_the_provenance(self):
        lines = [line for line in self.lines if cutcheck.SWALLOWED_EXIT in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn("01-pre-existing", lines[0])

    def test_an_undecidable_oracle_is_told_whatever_the_provenance(self):
        lines = [line for line in self.lines if cutcheck.VERDICT_IN_OUTPUT in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn("01-pre-existing", lines[0])


class ProvenanceNegationTest(unittest.TestCase):
    """Quoting the stamp, or denying it, mentions it: neither one exempts."""

    def setUp(self):
        self.result = run_cutcheck("cutcheck-provenance-mention")
        self.lines = [line for line in reported(self.result) if "01-mentioned" in line]

    def test_the_quoted_mention_is_graded_as_the_phrase_were_absent(self):
        lines = [line for line in self.lines if "criterion 1" in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn(cutcheck.ALREADY_PASSES, lines[0])

    def test_the_denied_mention_is_graded_too(self):
        lines = [line for line in self.lines if "criterion 2" in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn(cutcheck.ALREADY_PASSES, lines[0])

    def test_no_mention_of_the_phrase_reads_as_a_stamp(self):
        for text in (
            "the stamp this criterion quotes, `provenance: pre-existing`, is the "
            "one it talks about rather than one it makes.",
            "the stamp this criterion does not carry is provenance: pre-existing.",
            "provenance: pre-existing is never a demonstration that an oracle "
            "can fail.",
        ):
            self.assertIsNone(cutcheck.PRE_EXISTING_RE.search(text), text)


class ProvenanceStampTest(unittest.TestCase):
    """A stamp a criterion makes of its own oracle still exempts that oracle."""

    def test_the_paired_positive_is_exempt(self):
        result = run_cutcheck("cutcheck-provenance-mention")
        lines = [line for line in reported(result) if "02-stamped" in line]
        self.assertEqual(lines, [], result.stdout)

    def test_the_existing_provenance_fixture_is_exempt_as_it_was(self):
        result = run_cutcheck("cutcheck-provenance")
        lines = [line for line in reported(result) if cutcheck.ALREADY_PASSES in line]
        self.assertEqual(len(lines), 1, result.stdout)
        self.assertIn("02-authored-here", lines[0])

    def test_every_shape_the_corpus_stamps_with_still_reads_as_a_stamp(self):
        for text in (
            "**A criterion.** `grep -n x install.py` returns it. oracle_class: "
            "deterministic. provenance: pre-existing.",
            "provenance: pre-existing",
            "**A criterion.** oracle_class: judged. Provenance:  Pre-Existing.",
            # A live set stamps this way: the field, then why it is the field.
            "oracle_class: deterministic. provenance: pre-existing (the fixture "
            "exists from item 01).",
        ):
            self.assertTrue(cutcheck.PRE_EXISTING_RE.search(text), text)


class VerdictInOutputTest(unittest.TestCase):
    """A command whose verdict is in what it prints is one cutcheck cannot judge."""

    def setUp(self):
        self.result = run_cutcheck("cutcheck-verdict-in-output")
        self.lines = [
            line for line in self.result.stdout.splitlines() if "01-verdict" in line
        ]

    def test_the_text_count_is_reported_for_what_it_prints(self):
        lines = [line for line in self.lines if "criterion 1" in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn(cutcheck.VERDICT_IN_OUTPUT, lines[0])

    def test_the_revision_count_is_reported_for_its_count_and_not_its_head(self):
        lines = [line for line in self.lines if "criterion 2" in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn(cutcheck.VERDICT_IN_OUTPUT, lines[0])
        self.assertIn("git rev-list --count HEAD", lines[0])

    def test_both_counts_are_advisory_and_the_set_exits_zero(self):
        self.assertIn(cutcheck.VERDICT_IN_OUTPUT, cutcheck.ADVISORY)
        self.assertEqual(len(self.lines), 2, self.result.stdout)
        self.assertEqual(self.result.returncode, 0, self.result.stdout)


class QuotePrecisionTest(unittest.TestCase):
    """A quotation is text asserted to be at the citation, not the prose near it."""

    def setUp(self):
        self.result = run_cutcheck("cutcheck-quote-precision")
        self.lines = reported(self.result, cutcheck.FAMILY_2)

    def test_only_the_absent_quotation_is_reported(self):
        self.assertEqual(len(self.lines), 1, self.result.stdout)
        self.assertIn(cutcheck.QUOTE_NOT_AT_CITATION, self.lines[0])
        self.assertIn("no line of this file reads this way", self.lines[0])

    def test_a_citation_followed_by_its_symbol_is_not_a_quotation(self):
        self.assertNotIn("SCRIPT_NAMES\" not at", self.result.stdout)

    def test_a_fragment_of_the_surrounding_sentence_is_not_a_quotation(self):
        self.assertNotIn("and the word", self.result.stdout)


class MentionTest(unittest.TestCase):
    """Family 3 reports a path the ticket commits to writing, and nothing else."""

    def setUp(self):
        self.result = run_cutcheck("cutcheck-mention")
        self.lines = reported(self.result, cutcheck.FAMILY_3)

    def test_only_the_committed_sink_is_reported(self):
        self.assertEqual(len(self.lines), 1, self.result.stdout)
        self.assertIn(cutcheck.UNSCOPED_WRITE, self.lines[0])
        self.assertIn(".orch/evidence/mention/verdict.txt", self.lines[0])

    def test_no_mentioned_path_is_read_as_a_write(self):
        for mentioned in (
            ".orch/runs/<run>/coverage.md",
            "scripts/cutcheck.py",
            "rules/topology.md",
        ):
            self.assertNotIn(mentioned, self.result.stdout)


class CoverageMapPathTest(unittest.TestCase):
    """The absent map is named the way every other line names a path."""

    def setUp(self):
        self.result = run_cutcheck("cutcheck-f5-nomap")
        self.lines = [
            line
            for line in self.result.stdout.splitlines()
            if cutcheck.COVERAGE_MAP_ABSENT in line
        ]

    def test_the_absent_map_is_reported_relative_to_the_repository(self):
        self.assertEqual(len(self.lines), 1, self.result.stdout)
        self.assertIn(
            "tests/fixtures/cutcheck/cutcheck-f5-nomap/coverage.md", self.lines[0]
        )
        self.assertNotIn(str(ROOT), self.lines[0])

    def test_the_line_stays_advisory(self):
        self.assertEqual(self.result.returncode, 0, self.result.stdout)


class ExecutionCacheTest(unittest.TestCase):
    """One command in one scratch tree is one execution, however often extracted."""

    def setUp(self):
        cutcheck._EXIT_CACHE.clear()
        self.addCleanup(cutcheck._EXIT_CACHE.clear)

    def test_a_command_extracted_twice_for_one_tree_runs_once(self):
        done = subprocess.CompletedProcess([], 0)
        with mock.patch.object(cutcheck.subprocess, "run", return_value=done) as run:
            first = cutcheck._exit_code("git status", Path("/tree-a"))
            second = cutcheck._exit_code("git status", Path("/tree-a"))
            self.assertEqual(run.call_count, 1)
        self.assertEqual(first, 0)
        self.assertEqual(second, 0)

    def test_the_other_tree_is_its_own_execution(self):
        done = subprocess.CompletedProcess([], 0)
        with mock.patch.object(cutcheck.subprocess, "run", return_value=done) as run:
            cutcheck._exit_code("git status", Path("/tree-a"))
            cutcheck._exit_code("git status", Path("/tree-b"))
            self.assertEqual(run.call_count, 2)


class BinaryOutputOracleTest(unittest.TestCase):
    """An oracle's output is bytes, and only its exit status is ever read.

    A tree with history runs git oracles, and `git archive` prints a tar.
    Decoding that as text raised UnicodeDecodeError out of the run itself, so
    one such span in one ticket cost the whole invocation its report.

    Graded in a scratch copy, never in the tree under test: the module's own
    invariant is that oracles run in a copy cloned beside the tree, and a test
    that runs one in the repository it is testing is the one place that broke.
    """

    def setUp(self):
        scratch_root = Path(tempfile.mkdtemp(prefix=".cutcheck-binary-"))
        self.addCleanup(shutil.rmtree, scratch_root, True)
        self.tree = cutcheck._scratch_tree(BASELINE, ROOT, scratch_root)
        self.assertIsNotNone(self.tree, "no scratch tree was built for the baseline")

    def test_a_command_printing_binary_is_graded_on_its_exit_status(self):
        self.assertEqual(cutcheck._run_once("git archive HEAD", self.tree), 0)


class ScratchTreeHistoryTest(unittest.TestCase):
    """The graded tree is a repository of its own, holding the graded revision."""

    def setUp(self):
        scratch_root = Path(tempfile.mkdtemp(prefix=".cutcheck-history-"))
        self.addCleanup(shutil.rmtree, scratch_root, True)
        self.tree = cutcheck._scratch_tree(BASELINE, ROOT, scratch_root)
        self.assertIsNotNone(self.tree, "no scratch tree was built for the baseline")

    def test_the_graded_revision_resolves_inside_the_tree(self):
        # Reading a revision out of the log is the history claim: an extract
        # carrying no `.git` answers this from whatever repository encloses it,
        # or not at all.
        proc = cutcheck._git(["log", "-1", "--format=%H"], self.tree)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), BASELINE)

    def test_the_trees_own_top_level_is_the_tree_not_the_enclosing_checkout(self):
        here = Path.cwd()
        self.addCleanup(os.chdir, str(here))
        os.chdir(str(self.tree))
        top = cutcheck._worktree_root()
        self.assertEqual(top.resolve(), self.tree.resolve())
        self.assertNotEqual(top.resolve(), ROOT.resolve())

    def test_the_tree_carries_no_remote_to_write_back_through(self):
        # An oracle is ticket content, and ticket content is untrusted: a clone
        # keeping its origin is a write path from the scratch tree back out.
        proc = cutcheck._git(["remote"], self.tree)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "")


class GitOracleGradedTest(unittest.TestCase):
    """A git oracle is graded on its exit status in the clone, never excused."""

    def setUp(self):
        self.result = run_cutcheck("cutcheck-git-graded")
        self.lines = reported(self.result)

    def test_the_log_read_and_the_diff_are_each_graded_on_their_exit_status(self):
        classes = [line.split(": ")[2] for line in self.lines]
        self.assertEqual(classes, [cutcheck.ALREADY_PASSES] * 2, self.result.stdout)
        self.assertIn("criterion 1", self.lines[0])
        self.assertIn("criterion 2", self.lines[1])

    def test_the_ancestry_question_only_history_answers_discriminates(self):
        self.assertNotIn("criterion 3", self.result.stdout)

    def test_no_git_oracle_is_excused_for_its_head(self):
        self.assertNotIn("git-no-history", self.result.stdout)

    def test_a_graded_git_oracle_sets_the_exit_status(self):
        self.assertNotEqual(self.result.returncode, 0, self.result.stdout)


FIXTURES = ROOT / "tests" / "fixtures" / "cutcheck"
VERDICTS = FIXTURES / "verdicts.json"


def fixture_sets():
    return sorted(path.name for path in FIXTURES.iterdir() if path.is_dir())


def verdict(run):
    result = run_cutcheck(run)
    return {"exit": result.returncode, "lines": result.stdout.splitlines()}


def record_verdicts():
    """Rewrite the pinned verdicts from this revision's own report.

    Run as ``python3 tests/test_cutcheck.py --record``, and only when a
    completion test names the change: an unexplained diff here is a
    suppression nobody asked for.
    """

    recorded = {run: verdict(run) for run in fixture_sets()}
    VERDICTS.write_text(
        json.dumps(recorded, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )


class RecordedVerdictTest(unittest.TestCase):
    """Every fixture set keeps the exit status and the lines it was pinned at.

    Suppressing noise removes report lines by construction, so the guard
    against removing a true one is a recorded verdict per set, compared whole.
    """

    def test_every_fixture_set_matches_its_recorded_verdict(self):
        recorded = json.loads(VERDICTS.read_text(encoding="utf-8"))
        self.assertEqual(sorted(recorded), fixture_sets())
        for run in fixture_sets():
            with self.subTest(run=run):
                self.assertEqual(verdict(run), recorded[run])


class GitNoHistoryDispositionTest(unittest.TestCase):
    """The excuse a git head carried is gone, and nothing reaches it any more.

    It went rather than stayed because the scratch copy is a clone: the class
    fired on the head alone, and the premise the head stood for -- a copy with
    no history -- is now unreachable by construction. What stands in its place
    is graded execution, and a count-flagged git oracle reported for its count.
    """

    def test_the_class_name_resolves_nowhere_in_the_module(self):
        self.assertFalse(hasattr(cutcheck, "GIT_NO_HISTORY"))
        source = (ROOT / "scripts" / "cutcheck.py").read_text(encoding="utf-8")
        self.assertNotIn("git-no-history", source)

    def test_the_advisory_set_lost_that_one_member_and_no_other(self):
        self.assertEqual(
            cutcheck.ADVISORY,
            frozenset(
                {
                    cutcheck.EXTRACTION_GAP,
                    cutcheck.COVERAGE_MAP_ABSENT,
                    cutcheck.VERDICT_IN_OUTPUT,
                }
            ),
        )

    def test_every_git_span_is_executed_rather_than_excused_for_its_head(self):
        ticket = FIXTURES / "cutcheck-git-graded" / "01-git-graded.md"
        with mock.patch.object(cutcheck, "_exit_code", return_value=1) as ran:
            cutcheck._check_ticket(ticket, ROOT, None, {})
        self.assertEqual(
            [call[0][0] for call in ran.call_args_list],
            [
                "git log -1 --format=%H",
                "git diff ac8791a -- install.py",
                "git merge-base --is-ancestor ac8791a HEAD",
            ],
        )

    def test_the_count_flag_decides_the_undecidable_one_rather_than_the_head(self):
        self.assertTrue(cutcheck._verdict_in_output("git rev-list --count HEAD"))
        for command in ("git diff --exit-code", "git status --porcelain"):
            self.assertFalse(cutcheck._verdict_in_output(command), command)


class CutTimeDecidabilityTest(unittest.TestCase):
    """At cut time execution decides two classes: already-passes, and unrunnable."""

    def _class(self, code):
        with mock.patch.object(cutcheck, "_exit_code", return_value=code):
            return cutcheck._discrimination("pytest tests", Path("/baseline"), None)

    def test_an_absent_command_is_a_defect_at_the_revision_it_was_cut_from(self):
        self.assertEqual(self._class(cutcheck.UNRUNNABLE), cutcheck.UNRUNNABLE_ORACLE)

    def test_a_command_that_never_returns_is_one_too(self):
        self.assertEqual(self._class(cutcheck.TIMED_OUT), cutcheck.UNRUNNABLE_ORACLE)

    def test_a_plain_baseline_failure_stays_unjudged_at_cut_time(self):
        self.assertIsNone(self._class(1))

    def test_already_passing_is_the_other_class_cut_time_decides(self):
        self.assertEqual(self._class(0), cutcheck.ALREADY_PASSES)

    def test_an_oracle_nothing_can_run_sets_the_exit_status(self):
        self.assertNotIn(cutcheck.UNRUNNABLE_ORACLE, cutcheck.ADVISORY)


class HeadHalfNonReadingTest(unittest.TestCase):
    """A HEAD half that produced no reading is not a failure at both revisions.

    The baseline half already refuses to call a non-reading a failure; the HEAD
    half had no such branch, so a timeout there fell through to
    `fails-both-revisions` and an oracle that discriminates perfectly was
    reported as one that never discriminates. This tool's own suite is the case
    that found it: `tests.test_cutcheck` outgrew `COMMAND_TIMEOUT`, so the
    reading at HEAD is a timeout and the verdict drawn from it was a fiction.
    """

    def _class(self, at_head):
        baseline, head = Path("/baseline"), Path("/head")

        def exit_code(command, tree):
            # Compared as paths and never as text, and a third tree raises
            # rather than defaulting to one of the halves. `str(Path("/x"))`
            # is `\\x` on Windows, so a text compare silently collapses the
            # two halves into one -- and three of the four tests below still
            # pass when it does, because they expect the same class from both
            # halves. That is this module's own subject: the unmeasured case
            # recorded as the measured-and-fine one.
            if tree == baseline:
                return 1
            if tree == head:
                return at_head
            raise AssertionError(f"neither half: {tree!r}")

        with mock.patch.object(cutcheck, "_exit_code", side_effect=exit_code):
            return cutcheck._discrimination(
                "python3 -m unittest tests.test_cutcheck", baseline, head
            )

    def test_a_timeout_at_head_is_a_non_reading_and_not_a_failure(self):
        self.assertEqual(self._class(cutcheck.TIMED_OUT), cutcheck.UNRUNNABLE_ORACLE)

    def test_a_command_nothing_could_run_at_head_reads_the_same(self):
        self.assertEqual(self._class(cutcheck.UNRUNNABLE), cutcheck.UNRUNNABLE_ORACLE)

    def test_a_real_failure_at_both_revisions_is_still_reported_as_one(self):
        self.assertEqual(self._class(1), cutcheck.FAILS_BOTH_REVISIONS)

    def test_an_oracle_passing_at_head_still_discriminates(self):
        self.assertIsNone(self._class(0))

    def test_the_two_halves_refuse_the_same_pair_of_non_readings(self):
        for code in (cutcheck.TIMED_OUT, cutcheck.UNRUNNABLE):
            with mock.patch.object(cutcheck, "_exit_code", return_value=code):
                self.assertEqual(
                    cutcheck._discrimination("pytest tests", Path("/b"), Path("/h")),
                    cutcheck.UNRUNNABLE_ORACLE,
                )


class ScopeContainmentTest(unittest.TestCase):
    """A grant covers what is under it, never the directory that holds it."""

    def test_a_grant_of_one_file_is_no_grant_over_its_parent(self):
        self.assertFalse(cutcheck._covered("scripts", ["scripts/cutcheck.py"]))

    def test_a_directory_grant_does_not_cover_a_filename_it_never_names(self):
        self.assertFalse(cutcheck._covered("pins.json", ["tests/fixtures/cutcheck/"]))

    def test_a_grants_own_basename_is_the_file_it_granted(self):
        self.assertTrue(cutcheck._covered("cutcheck.py", ["scripts/cutcheck.py"]))

    def test_a_path_under_a_granted_directory_is_covered(self):
        self.assertTrue(
            cutcheck._covered(
                "tests/fixtures/cutcheck/cutcheck-evalhead/01-evalhead.md",
                ["tests/fixtures/cutcheck/"],
            )
        )


if __name__ == "__main__":
    if "--record" in sys.argv:
        record_verdicts()
    else:
        unittest.main()
