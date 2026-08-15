"""Tests for scripts/cutcheck.py: family 1, oracle discrimination and shape."""

import ast
import contextlib
import io
import json
import os
import re
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


SYMLINK_SKIP_PREFIX = "symlink creation unavailable, so the escape cannot be built here"


def _symlink_capability(directory):
    """Why no symlink can be created under `directory`, or None if one can.

    Probed, never inferred from `os.name`: `os.symlink` exists on Windows and
    raises without SeCreateSymbolicLinkPrivilege, so a platform test would skip
    a capable runner and -- the defect that matters -- would have to guess for
    an incapable one. The probe answers for the filesystem the escape is built
    on, and leaves it as it found it.
    """

    probe = Path(directory) / ".cutcheck-symlink-probe"
    try:
        os.symlink(str(Path(directory) / "no-such-target"), str(probe))
    except (OSError, NotImplementedError, ValueError) as exc:
        return "{}: {}".format(SYMLINK_SKIP_PREFIX, exc)
    os.unlink(str(probe))
    return None


def require_symlinks(case, directory):
    """Skip `case` with a recorded reason where the escape cannot be built."""

    reason = _symlink_capability(directory)
    if reason is not None:
        case.skipTest(reason)


def _symlink_source(case):
    """A source tree committing a symlink that points outside itself.

    Two commits, so `HEAD~1` names a range a diff can be asked for, and an
    `outside/` directory beside the tree that nothing inside it may reach.
    Built in a temporary directory of its own: the wrong result this pair of
    tests needs is built beside the tree under test, never in it.
    """

    root = Path(tempfile.mkdtemp(prefix="cutcheck-symlink-"))
    case.addCleanup(shutil.rmtree, root)
    require_symlinks(case, root)
    outside = root / "outside"
    outside.mkdir()
    src = root / "src"
    (src / "sub").mkdir(parents=True)
    for args in (
        ["init", "-q", "."],
        ["config", "user.email", "cutcheck@example.invalid"],
        ["config", "user.name", "cutcheck"],
    ):
        cutcheck._git(args, src)
    (src / "sub" / "a.txt").write_text("one\n", encoding="utf-8")
    os.symlink(str(outside), str(src / "link"))
    cutcheck._git(["add", "-A"], src)
    cutcheck._git(["commit", "-qm", "one"], src)
    (src / "sub" / "a.txt").write_text("one\ntwo\n", encoding="utf-8")
    cutcheck._git(["add", "-A"], src)
    cutcheck._git(["commit", "-qm", "two"], src)
    return root, src, outside


def _symlink_copy(case):
    """The copy `_scratch_tree` builds from that source, and what lies outside.

    The real function, not a re-spelling of it: what is under test is whether
    the copy this module grades oracles in confines them, so any other clone
    would grade a different tree than the one cutcheck builds.
    """

    root, src, outside = _symlink_source(case)
    scratch_root = root / "scratch"
    scratch_root.mkdir()
    tree = cutcheck._scratch_tree("HEAD", src, scratch_root)
    case.assertIsNotNone(tree, "no scratch copy was built from the symlink source")
    return tree, outside


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

    def test_committed_symlink_cannot_escape_the_copy(self):
        """The third route `_names_outside_the_copy` names and cannot close.

        `link/PAYLOAD` is neither rooted nor climbing, so the text gate reads
        it as confined and is right about the token and wrong about the file.
        Measured at the baseline: 121 bytes landed outside the copy. Only the
        copy can answer this, so the copy is what has to refuse it.
        """

        tree, outside = _symlink_copy(self)
        span = "git diff --output=link/PAYLOAD HEAD~1"
        self.assertFalse(cutcheck._unconfined_git(span), "the text gate permits it")
        proc = cutcheck._git(["diff", "--output=link/PAYLOAD", "HEAD~1"], tree)
        self.assertEqual(
            sorted(path.name for path in outside.iterdir()),
            [],
            "the copy wrote through a committed symlink: {}".format(proc.stderr),
        )

    def test_a_committed_symlink_cannot_be_read_through_by_an_orderfile(self):
        """The same route, read rather than written: `-O` opens what it names."""

        tree, outside = _symlink_copy(self)
        (outside / "orderfile").write_text("sub/a.txt\n", encoding="utf-8")
        span = "git diff -Olink/orderfile HEAD~1"
        self.assertFalse(cutcheck._unconfined_git(span), "the text gate permits it")
        proc = cutcheck._git(["diff", "-Olink/orderfile", "HEAD~1"], tree)
        self.assertNotEqual(
            proc.returncode,
            0,
            "the copy read an orderfile lying outside it",
        )
        self.assertIn("orderfile", proc.stderr)


class SymlinkCapabilityGuardTest(unittest.TestCase):
    """Neither escape test may pass where the escape cannot be built.

    A check that cannot fail decides nothing, and on a platform with no
    symlink privilege neither confinement test can construct the wrong result
    it exists to refuse. Passing there would report a guarantee nothing
    checked -- on the three `windows-latest` matrix legs, every leg of it. So
    they skip, and the reason is recorded rather than inferred from the count.
    """

    ESCAPE_TESTS = (
        "test_committed_symlink_cannot_escape_the_copy",
        "test_a_committed_symlink_cannot_be_read_through_by_an_orderfile",
    )

    def _incapable(self):
        # What a Windows runner without SeCreateSymbolicLinkPrivilege raises.
        return mock.patch.object(
            os,
            "symlink",
            side_effect=OSError(1, "A required privilege is not held by the client"),
        )

    def test_each_escape_test_skips_with_a_reason_rather_than_passing(self):
        for name in self.ESCAPE_TESTS:
            with self.subTest(test=name):
                result = unittest.TestResult()
                with self._incapable():
                    GitConfinementGateTest(name).run(result)
                self.assertEqual(result.errors, [], "the guard never ran")
                self.assertEqual(result.failures, [])
                self.assertEqual(len(result.skipped), 1, "it passed vacuously")
                self.assertEqual(
                    result.skipped[0][1],
                    SYMLINK_SKIP_PREFIX
                    + ": [Errno 1] A required privilege is not held by the client",
                )

    def test_the_probe_answers_what_the_platform_actually_does(self):
        """A guard that always skips is the same vacuity facing the other way.

        No skip of its own: whichever way this host answers, the probe has to
        agree with it, so the assertion is total on every platform.
        """

        root = Path(tempfile.mkdtemp(prefix="cutcheck-probe-"))
        self.addCleanup(shutil.rmtree, root)
        direct = root / "direct"
        try:
            os.symlink(str(root / "no-such-target"), str(direct))
        except (OSError, NotImplementedError, ValueError):
            capable = False
        else:
            capable = True
            os.unlink(str(direct))
        self.assertEqual(_symlink_capability(root) is None, capable)

    def test_the_probe_leaves_the_directory_as_it_found_it(self):
        root = Path(tempfile.mkdtemp(prefix="cutcheck-probe-"))
        self.addCleanup(shutil.rmtree, root)
        _symlink_capability(root)
        self.assertEqual(sorted(path.name for path in root.iterdir()), [])


def _tree_with_a_symlink_entry(case):
    """A repository whose HEAD records a `120000` entry, built without one.

    `update-index --cacheinfo` writes the mode straight into the index, so the
    instrument's own test needs no symlink privilege and reads the same on
    every platform. That is the point rather than a convenience: what §5
    forbids is the recorded mode, and the checkout a platform makes of it is a
    separate question this check does not ask.
    """

    root = Path(tempfile.mkdtemp(prefix="cutcheck-mode-"))
    case.addCleanup(shutil.rmtree, root)
    for args in (
        ["init", "-q", "."],
        ["config", "user.email", "cutcheck@example.invalid"],
        ["config", "user.name", "cutcheck"],
    ):
        cutcheck._git(args, root)
    (root / "a.txt").write_text("a\n", encoding="utf-8")
    cutcheck._git(["add", "a.txt"], root)
    blob = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=str(root),
        input="../outside\n",
        capture_output=True,
        text=True,
    ).stdout.strip()
    cutcheck._git(
        ["update-index", "--add", "--cacheinfo", "120000,{},sub/link".format(blob)],
        root,
    )
    cutcheck._git(["commit", "-qm", "a symlink entry, and no symlink on disk"], root)
    return root


class SymlinkModeCheckTest(unittest.TestCase):
    """`rules/visibility.md` §5's instrument: the mode git records.

    Read from the tree and never from the checkout, so `core.symlinks=false`
    -- which is what confines the copy -- does not blind the check that says
    the tree broke the rule.
    """

    def test_an_entry_anywhere_in_the_tree_is_found_by_its_mode(self):
        tree = _tree_with_a_symlink_entry(self)
        self.assertEqual(cutcheck._symlink_entries(tree), ["sub/link"])

    def test_the_entry_is_reported_against_the_run(self):
        tree = _tree_with_a_symlink_entry(self)
        self.assertEqual(
            cutcheck._symlink_findings("some-run", (tree, None)),
            [("some-run", 0, cutcheck.SYMLINK_IN_TREE, "sub/link")],
        )

    def test_a_path_both_graded_trees_record_is_named_once(self):
        tree = _tree_with_a_symlink_entry(self)
        self.assertEqual(len(cutcheck._symlink_findings("some-run", (tree, tree))), 1)

    def test_the_class_carries_a_family_and_is_advisory(self):
        """Reported, and never deciding a cut it is not a defect of.

        `scripts/cutcheck.py` owns cut-defect detection over an issued ticket
        set (ARCHITECTURE.md). A committed symlink is a property of the
        repository, and confinement is enforced by the clone flag whether or
        not anyone reads this line -- so the report carries visibility, not
        safety, and failing a cut for it would fail every cut in every
        repository where a symlink is legal.
        """

        self.assertIn(cutcheck.SYMLINK_IN_TREE, cutcheck.FAMILY_OF)
        self.assertIn(cutcheck.SYMLINK_IN_TREE, cutcheck.ADVISORY)

    def test_this_repositorys_own_tree_carries_no_such_entry(self):
        self.assertEqual(cutcheck._symlink_entries(ROOT), [])

    def test_the_check_is_wired_into_the_report_and_not_only_defined(self):
        """A reported class nothing calls is the vacuous shape one step over."""

        source = (ROOT / "scripts" / "cutcheck.py").read_text(encoding="utf-8")
        defined = [
            node
            for node in ast.walk(ast.parse(source))
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        ]
        called = {
            node.func.id
            for node in ast.walk(defined[0])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertIn("_symlink_findings", called)


VISIBILITY = ROOT / "rules" / "visibility.md"


def _visibility_clause(number):
    """One flat numbered clause of `rules/visibility.md`."""

    match = re.search(
        r"^{}\.[ ](.*?)(?=^\d+\.[ ]|\Z)".format(number),
        VISIBILITY.read_text(encoding="utf-8"),
        re.S | re.M,
    )
    assert match is not None, "rules/visibility.md has no clause {}".format(number)
    return " ".join(match.group(1).split())


class VisibilitySymlinkClauseTest(unittest.TestCase):
    """§5 forbade symlinks and named nothing that reads a tree for one.

    A prohibition whose instrument is unnamed is one no reader can run, and
    the gap this item closes is exactly that: the rule now says what grades it.
    """

    def test_section_five_names_its_instrument(self):
        clause = _visibility_clause(5)
        for named in (
            "scripts/cutcheck.py",
            cutcheck.SYMLINK_IN_TREE,
            cutcheck.SYMLINK_MODE,
        ):
            self.assertIn(named, clause, clause)

    def test_the_clause_keeps_what_it_already_owned(self):
        """Amended, not replaced: §5 owns three further facts and keeps them."""

        clause = _visibility_clause(5)
        for kept in ("No symlinks", "stdlib Python 3", "cross-platform", "network"):
            self.assertIn(kept, clause, clause)


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
        self.addCleanup(shutil.rmtree, scratch)
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
    """One command in one scratch tree is one execution, however often extracted.

    An execution now costs a second subprocess: the status read measuring what
    the span wrote into the copy. Counted here rather than described, so the
    price of the measurement stays visible and a cache hit stays free of it.
    """

    STATUS_READ = ["git", "status", "--porcelain", "--ignored"]

    def setUp(self):
        cutcheck._EXIT_CACHE.clear()
        cutcheck._TREE_STATE.clear()
        self.addCleanup(cutcheck._EXIT_CACHE.clear)
        self.addCleanup(cutcheck._TREE_STATE.clear)
        self.addCleanup(cutcheck._MUTATED.clear)

    def _counts(self, run):
        """Spans executed, and status reads paid for them."""

        argvs = [call[0][0] for call in run.call_args_list]
        reads = [argv for argv in argvs if argv == self.STATUS_READ]
        return len(argvs) - len(reads), len(reads)

    def test_a_command_extracted_twice_for_one_tree_runs_once(self):
        done = subprocess.CompletedProcess([], 0, stdout="")
        with mock.patch.object(cutcheck.subprocess, "run", return_value=done) as run:
            first = cutcheck._exit_code("git status", Path("/tree-a"))
            second = cutcheck._exit_code("git status", Path("/tree-a"))
            self.assertEqual(self._counts(run), (1, 1))
        self.assertEqual(first, 0)
        self.assertEqual(second, 0)

    def test_the_other_tree_is_its_own_execution(self):
        done = subprocess.CompletedProcess([], 0, stdout="")
        with mock.patch.object(cutcheck.subprocess, "run", return_value=done) as run:
            cutcheck._exit_code("git status", Path("/tree-a"))
            cutcheck._exit_code("git status", Path("/tree-b"))
            self.assertEqual(self._counts(run), (2, 2))

    def test_the_status_read_is_paid_once_per_execution_and_never_on_a_hit(self):
        done = subprocess.CompletedProcess([], 0, stdout="")
        with mock.patch.object(cutcheck.subprocess, "run", return_value=done) as run:
            for _ in range(5):
                cutcheck._exit_code("git status", Path("/tree-a"))
            self.assertEqual(self._counts(run), (1, 1))


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
        self.addCleanup(shutil.rmtree, scratch_root)
        self.tree = cutcheck._scratch_tree(BASELINE, ROOT, scratch_root)
        self.assertIsNotNone(self.tree, "no scratch tree was built for the baseline")

    def test_a_command_printing_binary_is_graded_on_its_exit_status(self):
        self.assertEqual(cutcheck._run_once("git archive HEAD", self.tree), 0)


class ScratchTreeHistoryTest(unittest.TestCase):
    """The graded tree is a repository of its own, holding the graded revision."""

    def setUp(self):
        scratch_root = Path(tempfile.mkdtemp(prefix=".cutcheck-history-"))
        self.addCleanup(shutil.rmtree, scratch_root)
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
        # `symlink-in-tree` joined later and is an addition, not a survival:
        # the claim this pins is still that GIT_NO_HISTORY left and that no
        # member standing beside it left with it.
        self.assertEqual(
            cutcheck.ADVISORY,
            frozenset(
                {
                    cutcheck.EXTRACTION_GAP,
                    cutcheck.COVERAGE_MAP_ABSENT,
                    cutcheck.VERDICT_IN_OUTPUT,
                    cutcheck.SYMLINK_IN_TREE,
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


MUTATING_TICKET = """---
id: 01-mutating
write_scope:
  - scripts/cutcheck.py
---

## Objective

A span the confinement gate permits, writing into the copy all the same.

## Completion test

1. The diff is produced. Oracle: `git diff --output=inside.txt HEAD~1 HEAD`.
2. The revision is read. Oracle: `git log -1 --format=%H`.
"""


class InCopyMutationTest(unittest.TestCase):
    """A span that writes into the shared copy is reported, never obeyed quietly.

    One copy is cloned per invocation and every ticket's oracles are graded in
    it, so a span that writes there changes what a sibling ticket's oracle
    reads. `_names_outside_the_copy` names this hole in its own docstring and
    cannot close it: where a write lands is a fact about the tree, not about
    the token, so only the tree answers it.
    """

    @classmethod
    def setUpClass(cls):
        cls.scratch_root = Path(tempfile.mkdtemp(prefix=".cutcheck-mutation-"))
        cls.tree = cutcheck._scratch_tree(BASELINE, ROOT, cls.scratch_root)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.scratch_root)

    def setUp(self):
        if self.tree is None:
            self.skipTest("no scratch tree was built for the baseline")
        cutcheck._EXIT_CACHE.clear()
        self.addCleanup(cutcheck._EXIT_CACHE.clear)
        self.addCleanup(self._restore)

    def _restore(self):
        """Leave the copy as this test found it, and resync the recorded state.

        The copy outlives one test here exactly as it outlives one ticket in a
        run: a test leaving its writes behind would convict the next one.
        """

        for name in ("inside.txt", "probe_dir", ".pytest_cache"):
            path = self.tree / name
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        cutcheck._mutations(self.tree)
        del cutcheck._MUTATED[:]

    def _wrote(self, command):
        """What this span wrote into the copy, as `_run_once` measures it."""

        del cutcheck._MUTATED[:]
        cutcheck._run_once(command, self.tree)
        return sorted(set(cutcheck._MUTATED))

    def _unconfined(self, path):
        findings = cutcheck._check_ticket(path, self.tree, None, {})
        return [f for f in findings if f[2] == cutcheck.UNCONFINED_ORACLE]

    def test_a_permitted_span_that_writes_into_the_copy_is_reported(self):
        ticket = Path(self.scratch_root) / "01-mutating.md"
        ticket.write_text(MUTATING_TICKET, encoding="utf-8")
        self.addCleanup(ticket.unlink)
        findings = self._unconfined(ticket)
        self.assertEqual(len(findings), 1, findings)
        ticket_id, number, _, detail = findings[0]
        self.assertEqual((ticket_id, number), ("01-mutating", 1))
        self.assertIn("inside.txt", detail)

    def test_a_span_writing_nothing_is_not_reported(self):
        # The can-fail direction: the same ticket's second criterion reads the
        # revision and writes nothing, and criterion 1 above proves this
        # assertion is reachable rather than vacuous.
        self.assertEqual(self._wrote("git log -1 --format=%H"), [])

    def test_an_untracked_unignored_directory_in_the_copy_is_reported(self):
        wrote = self._wrote(
            "python3 -m pytest --junitxml=probe_dir/r.xml tests/test_installer.py"
        )
        self.assertIn("probe_dir/", wrote)

    def test_an_ignored_path_is_reported_and_the_bare_spelling_would_miss_it(self):
        """`.pytest_cache/` is the shape found on disk, and it is ignored here.

        The guard against anyone shortening the reading back to a bare `git
        status --porcelain`: that spelling returns nothing with the directory
        sitting in the copy, so it is silently vacuous against the one leak
        that motivated the check.
        """

        wrote = self._wrote("python3 -m pytest tests/test_installer.py")
        self.assertIn(".pytest_cache/", wrote)
        bare = cutcheck._git(["status", "--porcelain"], self.tree)
        self.assertEqual(bare.stdout, "", "the bare spelling would have missed it")

    def test_the_next_span_is_not_blamed_for_the_previous_spans_write(self):
        first = self._wrote("git diff --output=inside.txt HEAD~1 HEAD")
        self.assertEqual(first, ["inside.txt"])
        self.assertEqual(self._wrote("git log -1 --format=%H"), [])

    def test_the_clone_primes_its_own_arrival_state_and_reads_clean(self):
        # A checkout an eol rule or a filter left dirty is the copy's arrival
        # state, not the first span's doing.
        self.assertIn(str(self.tree), cutcheck._TREE_STATE)
        self.assertEqual(cutcheck._mutations(self.tree), [])


def rmtree_calls(tree):
    """Every ``shutil.rmtree`` in a parsed module, with its ``ignore_errors``.

    Two spellings, because they silence the same thing: the call itself, and
    the call deferred through ``addCleanup``, where the third positional is
    ``ignore_errors`` and reads as a bare ``True`` at the call site.
    """

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == "rmtree":
            yield node, node.args[1:], node.keywords
        elif (
            node.func.attr == "addCleanup"
            and node.args
            and isinstance(node.args[0], ast.Attribute)
            and node.args[0].attr == "rmtree"
        ):
            yield node, node.args[2:], node.keywords


def swallows(rest, keywords):
    """Does this call ask ``rmtree`` to discard the errors it raises?"""

    given = list(rest) + [k.value for k in keywords if k.arg == "ignore_errors"]
    return any(
        not (isinstance(node, ast.Constant) and node.value is False) for node in given
    )


class ScratchCleanupReportingTest(unittest.TestCase):
    """The root an invocation makes is removed, and a failure to remove it is said.

    The removal itself is not new -- `mkdtemp` and `try:` are adjacent and the
    `finally` covers the exception path and the early `NO_TICKET_SET` alike.
    What is new is that anything checks it. `ignore_errors=True` in the tool
    whose subject is swallowed errors leaves a 12M copy on disk and says
    nothing, which is how seven roots accumulated unnoticed.
    """

    # A revision that resolves nowhere, so `main` returns at the early
    # `NO_TICKET_SET` its `finally` also covers: no clone, no oracle, and the
    # cleanup under test reached in milliseconds rather than minutes.
    UNRESOLVABLE = "cutcheck-no-such-revision"

    def setUp(self):
        here = Path.cwd()
        self.addCleanup(os.chdir, str(here))
        os.chdir(str(ROOT))
        self.addCleanup(cutcheck._EXIT_CACHE.clear)
        self.addCleanup(cutcheck._TREE_STATE.clear)
        self.addCleanup(cutcheck._MUTATED.clear)

    def _main_naming_its_scratch_root(self):
        """Run `main` to its `finally`, holding the exact root that run created.

        `_scratch_root` is wrapped rather than the filesystem searched. A
        `.cutcheck-*` glob would also match this suite's own roots and, worse,
        a concurrently running cut's live tree; a directory listing is flaky
        the moment two cuts overlap, which on this machine they do.
        """

        created = []
        real = cutcheck._scratch_root

        def recording(worktree_root):
            root = real(worktree_root)
            # Non-vacuity, asserted where it is still true: "the root is gone"
            # passes for the wrong reason over a root that was never made.
            self.assertIsNotNone(root, "no scratch root was created")
            self.assertTrue(root.is_dir(), "{} was never a directory".format(root))
            created.append(root)
            return root

        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(cutcheck, "_scratch_root", recording):
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = cutcheck.main(
                    ["cutcheck-clean", "--baseline", self.UNRESOLVABLE]
                )
        self.assertEqual(len(created), 1, created)
        return code, out.getvalue(), err.getvalue(), created[0]

    def test_main_removes_the_root_it_created(self):
        code, _, _, root = self._main_naming_its_scratch_root()
        self.assertEqual(code, cutcheck.NO_TICKET_SET)
        self.assertFalse(root.exists(), "{} outlived the run that made it".format(root))

    def test_a_failing_removal_is_reported(self):
        with mock.patch.object(
            cutcheck.shutil, "rmtree", side_effect=OSError(13, "Permission denied")
        ):
            code, _, err, root = self._main_naming_its_scratch_root()
        self.addCleanup(shutil.rmtree, root)
        # The failure was a real one: said or swallowed, the root is still on
        # disk, and that state is what the report exists to make visible.
        self.assertTrue(root.is_dir(), "the removal did not actually fail")
        self.assertIn(cutcheck.SCRATCH_NOT_REMOVED, err)
        self.assertIn(str(root), err)
        self.assertIn("Permission denied", err)
        # Reported, not re-graded: a leaked root is the tool's own hygiene and
        # never a finding against the ticket set it was reading.
        self.assertEqual(code, cutcheck.NO_TICKET_SET)

    def test_a_failing_removal_stays_out_of_the_graded_report(self):
        """The diagnostic may not disturb the report it is a diagnostic about.

        `RecordedVerdictTest` compares each of 27 fixture sets' stdout whole, and
        the `finally` runs before a single finding is printed. A leak report on
        stdout would therefore prepend a line to every pinned verdict on any
        host where a removal really fails -- and one does: git writes objects
        `0o444`, and Windows refuses to unlink a file with no write bit. The
        report belongs on the stream that is not the report.
        """

        with mock.patch.object(
            cutcheck.shutil, "rmtree", side_effect=OSError(13, "Permission denied")
        ):
            _, out, err, root = self._main_naming_its_scratch_root()
        self.addCleanup(shutil.rmtree, root)
        self.assertIn(cutcheck.SCRATCH_NOT_REMOVED, err)
        self.assertNotIn(cutcheck.SCRATCH_NOT_REMOVED, out)

    def test_a_root_git_left_read_only_is_still_removed(self):
        """The removal survives the mode git puts on every object it writes.

        Git writes loose objects and packs `0o444` and hardlinks that mode into
        each clone, so a strict removal meets it on every platform; on Windows
        a file carrying no write bit cannot be unlinked at all, which would
        turn this ticket's own removal assertion red there and leak 12M per
        run. The probe is the POSIX shape of the same refusal -- a directory
        whose write bit is off will not give up its children -- because that is
        the refusal this host can be made to exhibit.
        """

        if not self._refuses_unlink_under_a_read_only_directory():
            self.skipTest(
                "this host unlinks inside a write-protected directory, so the "
                "retry cannot be made to discriminate here"
            )
        root = Path(tempfile.mkdtemp(prefix="cutcheck-readonly-"))
        self.addCleanup(self._force_remove, root)
        held = root / "objects" / "0d"
        held.mkdir(parents=True)
        (held / "8a474fc6797").write_text("object", encoding="utf-8")
        held.chmod(0o500)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            cutcheck._remove_scratch_root(root)
        self.assertFalse(root.exists(), "{} survived its removal".format(root))
        self.assertEqual(err.getvalue(), "")

    def _refuses_unlink_under_a_read_only_directory(self):
        probe = Path(tempfile.mkdtemp(prefix="cutcheck-probe-mode-"))
        self.addCleanup(self._force_remove, probe)
        sub = probe / "sub"
        sub.mkdir()
        (sub / "f").write_text("x", encoding="utf-8")
        sub.chmod(0o500)
        try:
            (sub / "f").unlink()
        except OSError:
            return True
        return False

    @staticmethod
    def _force_remove(root):
        """Undo the modes this test set, then remove strictly like the rest.

        Absence is the success case here and never an error to discard: the
        test under it removes the root itself.
        """

        if not root.exists():
            return
        for path in [root] + sorted(root.rglob("*")):
            try:
                path.chmod(0o700)
            except OSError:
                pass
        shutil.rmtree(str(root))

    def test_a_removal_that_succeeds_says_nothing(self):
        # The can-fail direction for the lines above: a report printed
        # unconditionally would carry no information about the removal.
        _, out, err, _ = self._main_naming_its_scratch_root()
        self.assertNotIn(cutcheck.SCRATCH_NOT_REMOVED, out + err)

    def test_suite_cleanups_do_not_swallow(self):
        """The instrument may not silence what the subject is on trial for.

        Read from the module's own source, so it covers every removal the
        suite performs rather than the two a search happened to name.
        """

        source = Path(__file__).resolve()
        calls = list(rmtree_calls(ast.parse(source.read_text(encoding="utf-8"))))
        self.assertTrue(calls, "no shutil.rmtree call was found to check")
        self.assertEqual(
            [
                "{}:{}".format(source.name, node.lineno)
                for node, rest, keywords in calls
                if swallows(rest, keywords)
            ],
            [],
            "these removals discard the failure they should report",
        )


def must_git(case, args, cwd):
    proc = cutcheck._git(args, cwd)
    case.assertIsNotNone(proc, "git could not be run: {}".format(args))
    case.assertEqual(
        proc.returncode, 0, "git {}: {}".format(" ".join(args), proc.stderr)
    )
    return proc


def placement_repo(case):
    """A main checkout and one linked worktree of it, under one temporary root.

    Both origins built here rather than read off this machine: the placement
    has to answer the same from either, and this repository's own 62 worktrees
    are one arrangement of one host. One temporary root also means the
    filesystem clause below compares a placement and not a mount table.
    """

    base = Path(tempfile.mkdtemp(prefix="cutcheck-placement-"))
    case.addCleanup(shutil.rmtree, base)
    main = base / "main"
    main.mkdir()
    for args in (
        ["init", "-q", "."],
        ["config", "user.email", "cutcheck@example.invalid"],
        ["config", "user.name", "cutcheck"],
        ["config", "commit.gpgsign", "false"],
    ):
        must_git(case, args, main)
    (main / "a.txt").write_text("one\n", encoding="utf-8")
    must_git(case, ["add", "-A"], main)
    must_git(case, ["commit", "-qm", "one"], main)
    linked = base / "linked"
    must_git(case, ["worktree", "add", "-q", "--detach", str(linked)], main)
    return main, linked


class ScratchRootPlacementTest(unittest.TestCase):
    """Where the copies land: a directory the tool owns, beside the object store.

    `worktree_root.parent` answered differently from each origin and owned
    neither answer. From a main checkout it is the repository's *parent*, which
    is how 24M landed outside every ignore file this repository has and
    invisible to any sweep scoped to it; from a linked worktree it is the
    worktree directory, gitignored, where five more roots were sitting. The
    common dir answers the same from both, is git's own storage rather than
    anyone's source tree, and holds the object store a local clone hardlinks
    from -- whichever volume the worktree itself is on.
    """

    def setUp(self):
        self.main, self.linked = placement_repo(self)
        self.common = (self.main / ".git").resolve()

    def _root(self, origin):
        root = cutcheck._scratch_root(origin)
        self.assertIsNotNone(root, "no scratch root was placed for {}".format(origin))
        self.addCleanup(shutil.rmtree, root)
        return root.resolve()

    def test_the_root_lands_under_the_common_dir_from_a_main_checkout(self):
        # `--git-common-dir` answers a bare `.git` here -- relative to the cwd
        # it was asked in, and the one spelling difference between the two
        # origins. Resolved, or a main checkout places its copies relative to
        # wherever the process happened to be standing.
        self.assertEqual(self._root(self.main).parent.parent, self.common)

    def test_the_root_lands_under_the_common_dir_from_a_linked_worktree(self):
        root = self._root(self.linked)
        self.assertEqual(root.parent.parent, self.common)
        # Not `--git-dir`, which resolves to `.git/worktrees/<name>` and would
        # give each worktree grading one run a root of its own.
        self.assertNotIn("worktrees", root.parent.relative_to(self.common).parts)
        # The placement this replaces.
        self.assertNotEqual(root.parent, self.linked.parent.resolve())

    def test_both_origins_place_their_roots_in_one_directory(self):
        # One directory, and a distinct root inside it per invocation: two cuts
        # running at once share the place and never the tree.
        main_root, linked_root = self._root(self.main), self._root(self.linked)
        self.assertEqual(main_root.parent, linked_root.parent)
        self.assertNotEqual(main_root, linked_root)

    def test_the_scratch_root_shares_a_filesystem_with_the_tree(self):
        """Criterion 5: the clone hardlinks, so it must not cross a volume.

        `st_dev` equality is necessary and, on a single-volume host, decides
        nothing: every path on this machine reports one `st_dev`, the system
        temp directory included, so the rejected placement passes that clause
        too. Containment under the common dir is what carries the claim on
        every host -- it is the object store's own directory, so no volume
        boundary can appear between them however the host is mounted.
        """

        for origin in (self.main, self.linked):
            with self.subTest(origin=origin.name):
                root = self._root(origin)
                objects = self.common / "objects"
                self.assertEqual(root.parent.parent, self.common)
                self.assertEqual(
                    os.stat(str(root)).st_dev, os.stat(str(objects)).st_dev
                )
                self.assertEqual(
                    os.stat(str(root)).st_dev, os.stat(str(origin)).st_dev
                )

    def test_a_clone_into_the_scratch_root_hardlinks_the_object_store(self):
        """Criterion 5's other half, asserted rather than timed.

        A timing is a number to report and never an oracle -- runtime tracks
        the checkout as much as the tree, and only a short one indicts. Whether
        the objects are shared is a fact `st_nlink` states outright.
        """

        root = self._root(self.linked)
        probe = root / "probe"
        try:
            os.link(str(self.common / "HEAD"), str(probe))
        except (AttributeError, OSError, NotImplementedError) as exc:
            self.skipTest("this filesystem will not hardlink: {}".format(exc))
        probe.unlink()
        tree = cutcheck._scratch_tree("HEAD", self.linked, root)
        self.assertIsNotNone(tree, "no scratch tree was cloned")
        objects = tree / ".git" / "objects"
        self.assertTrue(
            [p for p in objects.rglob("*") if p.is_file() and p.stat().st_nlink > 1],
            "the clone copied every object instead of linking it",
        )

    def test_a_directory_outside_any_repository_gets_no_scratch_root(self):
        outside = Path(tempfile.mkdtemp(prefix="cutcheck-outside-"))
        self.addCleanup(shutil.rmtree, outside)
        proc = cutcheck._git(["rev-parse", "--git-common-dir"], outside)
        if proc is not None and proc.returncode == 0:
            self.skipTest(
                "the temp directory is itself inside a repository: {}".format(
                    proc.stdout.strip()
                )
            )
        self.assertIsNone(cutcheck._scratch_root(outside))


if __name__ == "__main__":
    if "--record" in sys.argv:
        record_verdicts()
    else:
        unittest.main()
