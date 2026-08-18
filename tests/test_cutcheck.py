"""Tests for scripts/cutcheck.py: family 1, oracle discrimination and shape."""

import ast
import contextlib
import io
import json
import os
import re
import shlex
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
import scripts.state_root as state_root  # noqa: E402
import scripts.tickets as tickets  # noqa: E402
from tests.baseline_pin import (  # noqa: E402  the invocation's one owner
    BASELINE,
    run_cutcheck,
    run_cutcheck_subprocess,
    shared_root,
)
from tests.tree_removal import remove_repo_tree  # noqa: E402  the removal's one owner


def reported(result, family=cutcheck.FAMILY):
    return [line for line in result.stdout.splitlines() if family in line]


def report(result):
    """The report split where its own summary lines split it.

    Findings outside the advisory set first, then the advisory findings under
    the heading, then whether the affirmative line closed the report. The shape
    reading is split off and returned by none of the three: it is a reading of
    the cut and not a finding of it, so a caller counting findings must never
    have to subtract it.
    """

    lines = result.stdout.splitlines()
    affirmed = bool(lines) and lines[-1] == cutcheck.NO_FINDING_OUTSIDE
    if affirmed:
        lines = lines[:-1]
    if cutcheck.GRAPH_HEADING in lines:
        lines = lines[:lines.index(cutcheck.GRAPH_HEADING)]
    if cutcheck.ADVISORY_HEADING in lines:
        cut = lines.index(cutcheck.ADVISORY_HEADING)
        return lines[:cut], lines[cut + 1:], affirmed
    return lines, [], affirmed


def graph_block(result):
    """The shape reading's own lines, under its own heading.

    The half `report` drops. Nothing but the affirmative line follows the
    block, so the block is what stands between its heading and that line.
    """

    lines = result.stdout.splitlines()
    if cutcheck.GRAPH_HEADING not in lines:
        return []
    block = lines[lines.index(cutcheck.GRAPH_HEADING) + 1:]
    if block and block[-1] == cutcheck.NO_FINDING_OUTSIDE:
        block = block[:-1]
    return block


def finding_lines(result):
    """Every finding line the report holds, and nothing else.

    Both blocks, neither summary line, and never the shape reading. A caller
    asking what was found about an item is asking about findings, and the
    chain the shape names carries ticket ids -- a reading of those items, not
    a finding against them, and a filter that took it for one would convict a
    clean set of whatever its longest chain happened to run through.
    """

    violations, advisories, _ = report(result)
    return violations + advisories


def fixture_criteria(run, name):
    path = ROOT / "tests" / "fixtures" / "cutcheck" / run / name
    section = tickets._sections(path.read_text(encoding="utf-8"))
    return cutcheck._criteria(section[cutcheck.COMPLETION_SECTION])


def shared_baseline_tree():
    """The harness's real baseline clone, shared by read-only tree probes."""

    tree = cutcheck._scratch_tree(BASELINE, ROOT, shared_root())
    if tree is None:
        raise RuntimeError("no scratch tree was built for the baseline")
    return tree


class AffirmativeSummaryTest(unittest.TestCase):
    """A set with no finding outside the advisory set says so, rather than nothing.

    This class is also the module's one end-to-end grading across a real
    process boundary. Every other grading here runs `main` in this process
    against copies the whole module shares, which is the same work without a
    clone per invocation but cannot testify to argv, to the status the
    operating system reports, or to two real pipes. One set graded the long way
    is what says the short way reads the same, and the node below is where that
    is asserted rather than assumed.
    """

    @classmethod
    def setUpClass(cls):
        cls.spawned = run_cutcheck_subprocess(
            ["cutcheck-clean", "--baseline", BASELINE]
        )

    def test_the_clean_set_prints_the_affirmative_line_and_exits_zero(self):
        self.assertEqual(
            self.spawned.returncode, 0, self.spawned.stdout + self.spawned.stderr
        )
        # Nothing found, and the line saying so is the report's last: the
        # shape reading stands above it and is a reading of this set, never a
        # finding against it.
        self.assertEqual(finding_lines(self.spawned), [], self.spawned.stdout)
        self.assertEqual(
            self.spawned.stdout.splitlines()[-1], cutcheck.NO_FINDING_OUTSIDE
        )

    def test_the_in_process_grading_reads_the_same_as_the_spawned_one(self):
        """The port's own anchor: one pair, graded both ways, compared whole.

        Status and stdout together, because either alone passes over a run that
        resolved nothing: `NO_TICKET_SET` with one line of explanation is a
        report too. Stderr is not compared -- the in-process run neutralises
        the scratch removal, which is the only thing that ever writes there.
        """

        graded = run_cutcheck("cutcheck-clean")
        self.assertEqual(graded.returncode, self.spawned.returncode)
        self.assertEqual(graded.stdout, self.spawned.stdout)

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
        for line in (
            cutcheck.ADVISORY_HEADING,
            cutcheck.GRAPH_HEADING,
            cutcheck.NO_FINDING_OUTSIDE,
        ):
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


class GraphReadingTest(unittest.TestCase):
    """The cut's shape is read from the issued set, and it decides nothing.

    The fixture is five items in the one arrangement that separates the two
    readings from each other: three items depending on nothing, one behind one
    of those, and one behind that one and a second first-level item. Depth and
    breadth disagree there -- the chain is three long where the widest level
    holds three -- so a reading that counted levels as a chain, or took the
    longest chain to be the item count, is wrong by a different number in each
    line rather than right by coincidence.

    The set is otherwise clean, which is what makes the second node an
    assertion rather than a hope: the graph classes lie outside the advisory
    set, so were they findings at all they would be findings outside it, and
    this set would exit 1 with two violations instead of 0 with none.
    """

    RUN = "cutcheck-graph"

    @classmethod
    def setUpClass(cls):
        cls.result = run_cutcheck(cls.RUN)

    def _detail(self, klass):
        prefix = "{}: {}: {}: ".format(self.RUN, cutcheck.GRAPH, klass)
        found = [
            line[len(prefix):]
            for line in graph_block(self.result)
            if line.startswith(prefix)
        ]
        self.assertEqual(len(found), 1, self.result.stdout)
        return found[0]

    def test_the_critical_path_and_level_widths_are_reported(self):
        self.assertEqual(
            self._detail(cutcheck.CRITICAL_PATH),
            "3: 01-alpha > 04-delta > 05-epsilon",
            self.result.stdout,
        )
        self.assertEqual(
            self._detail(cutcheck.LEVEL_WIDTH), "3 1 1", self.result.stdout
        )

    def test_the_graph_block_stands_outside_the_advisory_set_and_the_exit_status(self):
        violations, advisories, affirmed = report(self.result)
        self.assertTrue(graph_block(self.result), self.result.stdout)
        self.assertEqual(self.result.returncode, cutcheck.CLEAN, self.result.stdout)
        self.assertEqual(violations, [], self.result.stdout)
        self.assertEqual(advisories, [], self.result.stdout)
        self.assertTrue(affirmed, self.result.stdout)
        for klass in sorted(cutcheck.GRAPH_CLASSES):
            self.assertEqual(cutcheck.FAMILY_OF[klass], cutcheck.GRAPH)
            self.assertNotIn(klass, cutcheck.ADVISORY)

    def _details(self, run, siblings):
        return {
            klass: detail
            for _, _, klass, detail in cutcheck._graph_reading(run, siblings)
        }

    def test_a_cycle_is_named_in_the_reading_rather_than_raised(self):
        """A set no ordering exists for is still read, and says which part is not.

        Asked of the reading directly rather than through a fixture: a cyclic
        set is one `tickets.py` never issues, so pinning one as a fixture would
        pin a corpus the tool cannot meet, and re-record its verdict beside the
        real ones. What has to hold is that the levelling terminates on a graph
        with no order, reports the part that does have one, and names the rest
        -- three claims about this function and none about the report's shape.
        """

        details = self._details("cycled", {
            "01-a": {"id": "01-a", "depends_on": []},
            "02-b": {"id": "02-b", "depends_on": ["03-c"]},
            "03-c": {"id": "03-c", "depends_on": ["02-b"]},
        })
        self.assertEqual(details[cutcheck.CRITICAL_PATH], "1: 01-a; cycle: 02-b, 03-c")
        self.assertEqual(details[cutcheck.LEVEL_WIDTH], "1")

    def test_a_set_with_no_issued_item_has_no_shape_to_read(self):
        self.assertEqual(cutcheck._graph_reading("empty", {}), [])


EXIT_ENTRY_RE = re.compile(r"^ {2}(\d+) {2}(\S.*)$")


def epilog_exit_entries(help_text):
    """The statuses the `exit status:` section documents, each to its own
    opening line. A status with no entry is the defect; what the entry says
    is the epilog's to word."""

    entries, inside = {}, False
    for line in help_text.splitlines():
        if line.rstrip() == "exit status:":
            inside = True
            continue
        if not inside:
            continue
        if line.strip() and not line.startswith(" "):
            break
        match = EXIT_ENTRY_RE.match(line)
        if match:
            entries[int(match.group(1))] = match.group(2)
    return entries


class ExitCodeEpilogTest(unittest.TestCase):
    """`--help` documents each exit status the tool returns, and names the
    class that makes a verdict unportable.

    Statuses and names, never the epilog's sentences: what each status *means*
    is graded next door -- `AdvisoryExitZeroTest` for 0, `DiscriminationTest`
    for 1, `HeadCloneRefusalTest` for 2 -- so a check here that read the wording
    would only pin prose (packs/orch-code-pack/references/craft.md). What is
    mechanized here is that the section exists, that it holds one entry per
    status, and that the names it routes a reader by are the module's own
    (docs/documentation.md law 5).

    Spawned, and spawned once. The epilog is what argparse prints for an argv
    this process never assembles and a status the operating system reports, so
    a real process is the only thing that can be asked; the assertions read
    that one output, so `setUpClass` and not `setUp`.
    """

    @classmethod
    def setUpClass(cls):
        cls.result = run_cutcheck_subprocess(["--help"])
        cls.help = " ".join(cls.result.stdout.split())
        cls.entries = epilog_exit_entries(cls.result.stdout)

    def setUp(self):
        self.assertEqual(self.result.returncode, 0, self.result.stderr)

    def test_every_status_the_tool_returns_has_its_own_entry(self):
        self.assertEqual({0, 1, 2}, set(self.entries), self.result.stdout)
        self.assertIn(cutcheck.NO_TICKET_SET, self.entries)
        for status, text in sorted(self.entries.items()):
            self.assertTrue(text.strip(), status)

    def test_the_portability_note_names_the_class_that_makes_it_unportable(self):
        self.assertIn(cutcheck.UNRUNNABLE_ORACLE, self.help)

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


class RootGateLayoutTest(unittest.TestCase):
    """The layout every honest root cut has, graded as the contract writes it.

    A root ticket sits in the run directory beside its own `<root>.NN` units
    and its `<root>.gate.*` stubs. Read as issued items they convict every
    honest cut: the root is named by no criterion of the map it is the source
    of, each gate stub is named by the keyword `gate` and never by its id, and
    the root and the repair both hold the run's scope with no edge between
    them. `rules/verification.md` §11 makes the cut's verdict this tool re-run
    to exit 0, and the skill orders the gate step next, so a verdict that
    cannot survive the gate is a verdict read once and never again.
    """

    def setUp(self):
        self.result = run_cutcheck("cutcheck-root-gate")

    @staticmethod
    def _root(root):
        return {
            "id": root,
            "executor": tickets.ROOT_EXECUTOR,
            "depends_on": [],
            "write_scope": ["scripts/{}.py".format(root.lower())],
        }

    @staticmethod
    def _unit(root, number, path, **extra):
        ticket = {
            "id": "{}.{}".format(root, number),
            "executor": "orch-tdd",
            "independence": "gate",
            "depends_on": [],
            "write_scope": [path],
        }
        ticket.update(extra)
        return ticket

    @staticmethod
    def _gate(root, units, lenses=("code",)):
        gate = {}
        critiques = []
        for lens in lenses:
            ticket_id = "{}.gate.critique.{}".format(root, lens)
            critiques.append(ticket_id)
            gate[ticket_id] = {
                "id": ticket_id,
                "executor": tickets.GATE_EXECUTORS["critique"],
                "depends_on": list(units),
                "write_scope": [],
            }
        repair = "{}.gate.repair".format(root)
        verify = "{}.gate.verify".format(root)
        gate[repair] = {
            "id": repair,
            "executor": tickets.GATE_EXECUTORS["repair"],
            "depends_on": critiques,
            "write_scope": ["scripts/{}.py".format(root.lower())],
        }
        gate[verify] = {
            "id": verify,
            "executor": tickets.GATE_EXECUTORS["verify"],
            "depends_on": [repair],
            "write_scope": [],
        }
        return gate

    def test_two_roots_and_two_gate_systems_fail(self):
        """A hand-built set gets the same refusals as the runtime writers.

        The runtime now refuses the second root and the second gate before it
        writes either one. Cutcheck reads legacy and manually assembled state,
        so the same contradiction must still be a cut defect when both systems
        are already present on disk.
        """

        siblings = {}
        for root, path in (("R1", "scripts/one.py"), ("R2", "scripts/two.py")):
            unit = self._unit(root, "01", path)
            siblings[root] = self._root(root)
            siblings[unit["id"]] = unit
            siblings.update(self._gate(root, [unit["id"]]))

        findings = cutcheck._root_gate_layout(siblings)
        classes = [finding[2] for finding in findings]
        self.assertEqual(classes.count(cutcheck.MULTIPLE_ROOTS), 1, findings)
        self.assertEqual(classes.count(cutcheck.MULTIPLE_GATE_SYSTEMS), 1, findings)
        self.assertTrue(all(klass not in cutcheck.ADVISORY for klass in classes))

    def test_two_unrelated_roots_fail_before_either_has_a_gate(self):
        siblings = {"R1": self._root("R1"), "R2": self._root("R2")}
        findings = cutcheck._root_gate_layout(siblings)
        self.assertEqual(
            [cutcheck.MULTIPLE_ROOTS], [finding[2] for finding in findings], findings
        )

        # Canonical template decomposers are stages of one top-level graph,
        # and remain the explicit compatibility exception.
        siblings["R2"]["depends_on"] = ["R1"]
        self.assertEqual([], cutcheck._root_gate_layout(siblings))

    def test_a_partial_or_wrongly_edged_gate_is_malformed(self):
        unit = self._unit("R", "01", "scripts/one.py")
        critique = "R.gate.critique.code"
        siblings = {
            "R": self._root("R"),
            unit["id"]: unit,
            critique: {
                "id": critique,
                "executor": tickets.GATE_EXECUTORS["critique"],
                "depends_on": [unit["id"]],
                "write_scope": [],
            },
        }
        findings = cutcheck._root_gate_layout(siblings)
        self.assertIn(cutcheck.MALFORMED_GATE, [finding[2] for finding in findings])

    def test_command_rejects_the_independent_roots_and_partial_gate(self):
        """The public command, not only the helper, owns both refusals."""

        def body(ticket_id, executor, depends_on="[]"):
            return tickets._render_ticket(
                {
                    "id": ticket_id, "run": "layout-command", "status": "ready",
                    "executor": executor, "depends_on": depends_on,
                    "write_scope": ["install.py"], "bound": "10m",
                },
                [
                    ("Objective", "exercise the command layout"),
                    ("Fixed inputs", "- fixed baseline"),
                    ("Completion test", "- installer remains valid | oracle: "
                     "`python install.py --dry-run` | oracle_class: deterministic | "
                     "provenance: pre-existing"),
                    ("Return fields", "status; result"),
                    ("Result", ""), ("Verification", ""),
                    ("Feedback", "[]"), ("Risks", "[]"),
                ],
            )

        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "state"
            run_dir = sink / "tickets" / "layout-command"
            run_dir.mkdir(parents=True)
            (run_dir / "R1.md").write_text(
                body("R1", tickets.ROOT_EXECUTOR), encoding="utf-8"
            )
            (run_dir / "R2.md").write_text(
                body("R2", tickets.ROOT_EXECUTOR), encoding="utf-8"
            )
            (run_dir / "R1.gate.critique.code.md").write_text(
                body("R1.gate.critique.code", tickets.GATE_EXECUTORS["critique"]),
                encoding="utf-8",
            )
            with mock.patch.dict(
                os.environ, {"ORCHFLOWS_STATE_HOME": str(sink)}
            ):
                result = run_cutcheck_subprocess(
                    ["layout-command", "--baseline", "HEAD", "--lib", str(ROOT)]
                )
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn(cutcheck.MULTIPLE_ROOTS, result.stdout)
        self.assertIn(cutcheck.MALFORMED_GATE, result.stdout)

    def test_checker_plus_gate_and_uncovered_criteria_fail(self):
        """One ticket gets one independence path, even in the smallest cut.

        The second half preserves acceptance coverage as the counterexample:
        naming only the gate does not cover the unit that delegated its
        authored acceptance. Neither defect needs a ticket-count profile or a
        second gate to become true.
        """

        unit = self._unit("R", "01", "scripts/one.py", checked_by="checker-a")
        siblings = {"R": self._root("R"), unit["id"]: unit}
        siblings.update(self._gate("R", [unit["id"]]))
        layout = cutcheck._root_gate_layout(siblings)
        self.assertEqual(
            [finding[2] for finding in layout],
            [cutcheck.MIXED_INDEPENDENCE],
            layout,
        )

        with tempfile.TemporaryDirectory() as tmp:
            coverage = Path(tmp) / cutcheck.COVERAGE_FILE
            coverage.write_text(
                "| criterion | owner |\n|---|---|\n"
                "| 1 | gate |\n| 2 | R.02 |\n",
                encoding="utf-8",
            )
            uncovered = cutcheck._coverage(
                "R", coverage, [unit["id"]], (Path(tmp),)
            )
        self.assertEqual(
            [finding[2] for finding in uncovered],
            [cutcheck.ORPHAN_CRITERION, cutcheck.ORPHAN_ITEM],
            uncovered,
        )
        self.assertEqual(cutcheck._gate_owners(siblings), ["R"])
        self.assertNotIn("profile", unit)

    def test_gate_independence_counts_every_authored_here_criterion(self):
        unit = self._unit("R", "01", "scripts/one.py")
        unit["__completion_test"] = (
            "- first | oracle: first command | oracle_class: deterministic | "
            "provenance: authored-here\n"
            "- second | oracle: second command | oracle_class: judged | "
            "provenance: authored-here\n"
        )
        root = self._root("R")
        root["__completion_test"] = (
            "- final | oracle: final command | oracle_class: deterministic | "
            "provenance: pre-existing\n"
        )
        siblings = {"R": root, unit["id"]: unit}
        with tempfile.TemporaryDirectory() as tmp:
            coverage = Path(tmp) / cutcheck.COVERAGE_FILE
            coverage.write_text(
                "| criterion | owner |\n|---|---|\n| 1 | R.01 |\n",
                encoding="utf-8",
            )
            findings = cutcheck._coverage(
                "R", coverage, ["R.01"], (Path(tmp),),
                siblings=siblings, root="R",
            )
        self.assertIn(
            cutcheck.UNCOVERED_GATE_CRITERION,
            [finding[2] for finding in findings],
            findings,
        )

    def test_single_root_distinct_lenses_and_sole_owner_graph_pass(self):
        """The runtime's accepted one-root shape remains the lawful cut.

        Two named lenses feed one repair and verify, while disjoint unit scopes
        keep sole ownership. The constants come from the accepted predecessor
        runtime result rather than a second cutcheck-only gate vocabulary.
        """

        left = self._unit("R", "01", "scripts/one.py")
        right = self._unit("R", "02", "scripts/two.py")
        siblings = {"R": self._root("R"), left["id"]: left, right["id"]: right}
        siblings.update(
            self._gate("R", [left["id"], right["id"]], lenses=("code", "security"))
        )

        self.assertEqual(cutcheck._root_gate_layout(siblings), [])
        self.assertEqual(cutcheck._pairwise(siblings, {}), [])
        self.assertEqual(cutcheck._root_ids(siblings), ["R"])
        self.assertEqual(cutcheck._gate_owners(siblings), ["R"])
        self.assertEqual(
            sorted(
                ticket_id.rsplit(".", 1)[-1]
                for ticket_id in siblings
                if ".gate.critique." in ticket_id
            ),
            ["code", "security"],
        )

    def test_the_whole_layout_exits_zero(self):
        self.assertEqual(self.result.returncode, 0, self.result.stdout)

    def test_no_finding_stands_outside_the_advisory_set(self):
        violations, _, affirmed = report(self.result)
        self.assertEqual(violations, [], self.result.stdout)
        self.assertTrue(affirmed, self.result.stdout)

    def test_neither_the_root_nor_a_gate_stub_is_an_orphan_item(self):
        for line in self.result.stdout.splitlines():
            self.assertNotIn(cutcheck.ORPHAN_ITEM, line, self.result.stdout)

    def test_the_root_and_the_repair_sharing_the_run_scope_is_no_collision(self):
        self.assertNotIn(cutcheck.SCOPE_COLLISION, self.result.stdout)
        self.assertNotIn(cutcheck.STAGED_INVALIDATION, self.result.stdout)

    def test_the_structural_executors_are_legal_under_the_stamped_pack(self):
        """The pack's executor cell names `orch-tdd` and nothing else.

        Graded against that cell, the decomposer and the gate's three
        executors are all illegal, which would fail the cut for carrying the
        shape the contract requires of it. They are the library's own nodes,
        so they are graded against the library's own names.
        """

        self.assertNotIn(cutcheck.ILLEGAL_EXECUTOR, self.result.stdout)

    def test_a_unit_ticket_is_still_graded_against_the_packs_cell(self):
        self.assertIn(
            cutcheck.ILLEGAL_EXECUTOR, run_cutcheck("cutcheck-f6-executor").stdout
        )

    def test_a_gate_stub_naming_an_executor_the_gate_never_writes_is_reported(self):
        siblings = {
            "00-root": {"id": "00-root", "executor": cutcheck.ROOT_EXECUTOR},
            "00-root.gate.repair": {
                "id": "00-root.gate.repair", "executor": "orch-tdd"
            },
        }
        findings = cutcheck._executor_legality(siblings, ROOT)
        self.assertEqual(1, len(findings), findings)
        self.assertEqual("00-root.gate.repair", findings[0][0])
        self.assertEqual(cutcheck.ILLEGAL_EXECUTOR, findings[0][2])


class NestedRootTest(unittest.TestCase):
    """A root is the set's own source, never a unit inside another root's.

    `rules/topology.md` §7: mixed decomposition inside one graph is
    undefined. Reading every `orch-decompose` ticket as a root made a
    `<root>.NN` unit issued with that executor legal, and exempted anything
    it carried under `.gate.` from families 4 and 5 -- the cut defect hiding
    behind the exemption written for the honest layout.
    """

    def test_a_nested_root_is_reported_as_a_nested_root(self):
        siblings = {
            "00-root": {"id": "00-root", "executor": cutcheck.ROOT_EXECUTOR},
            "00-root.01": {"id": "00-root.01", "executor": cutcheck.ROOT_EXECUTOR},
        }
        findings = cutcheck._executor_legality(siblings, ROOT)
        self.assertEqual(1, len(findings), findings)
        self.assertEqual("00-root.01", findings[0][0])
        self.assertEqual(cutcheck.ILLEGAL_EXECUTOR, findings[0][2])
        self.assertIn("nested root", findings[0][3])

    def test_a_nested_roots_gate_stub_is_no_longer_exempt(self):
        siblings = {
            "00-root": {"id": "00-root", "executor": cutcheck.ROOT_EXECUTOR},
            "00-root.01": {"id": "00-root.01", "executor": cutcheck.ROOT_EXECUTOR},
            "00-root.01.gate.repair": {
                "id": "00-root.01.gate.repair", "executor": "orch-repair"
            },
        }
        roots = cutcheck._root_ids(siblings)
        self.assertEqual(["00-root"], roots)
        self.assertIsNone(cutcheck._gate_stub_of("00-root.01.gate.repair", roots))
        self.assertIn("00-root.01.gate.repair", cutcheck._issued_items(siblings, roots))

    def test_a_top_level_decompose_stub_beside_others_is_still_a_root(self):
        """`compositions/self-improve/01-deliver` is exactly this shape.

        A template's terminal-ish stub carries `orch-decompose` beside stubs
        no root owns; no other root's id prefixes it, so it is a root of its
        own and nothing about it is reported.
        """

        siblings = {
            "00-mine": {"id": "00-mine", "executor": "orch-self-improve"},
            "01-deliver": {"id": "01-deliver", "executor": cutcheck.ROOT_EXECUTOR},
            "02-close": {"id": "02-close", "executor": "orch-integrate"},
        }
        self.assertEqual(["01-deliver"], cutcheck._root_ids(siblings))
        self.assertEqual([], cutcheck._executor_legality(siblings, ROOT))


class ExecutorLegalityTest(unittest.TestCase):
    def setUp(self):
        self.result = run_cutcheck("cutcheck-f6-executor")
        self.lines = reported(self.result, cutcheck.FAMILY_6)

    def test_executor_set_exits_nonzero(self):
        self.assertNotEqual(self.result.returncode, 0, self.result.stdout)

    def test_an_executor_no_cell_of_the_pack_names_is_reported(self):
        lines = [line for line in self.lines if "03-alien" in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn(cutcheck.ILLEGAL_EXECUTOR, lines[0])
        self.assertIn("orch-render", lines[0])
        self.assertIn("orch-code-pack", lines[0])

    def test_the_packs_own_executor_cell_is_not_reported(self):
        self.assertNotIn("02-legal", "\n".join(finding_lines(self.result)))

    def test_the_surviving_engines_are_lawful_executors(self):
        """P4-3 deleted the engine prohibition with the two engines it named.
        Both survivors are lawful ticket executors, and neither script keeps a
        list of them: with nothing left to refuse, no code path branches on
        membership, so the library tree is the only statement of the set."""
        engines = {
            path.name
            for path in (ROOT / "skills" / "engines").iterdir()
            if path.is_dir()
        }
        self.assertEqual({"orch-frontier", "orch-loop"}, engines)
        self.assertFalse(hasattr(cutcheck, "ENGINE_EXECUTORS"))
        self.assertFalse(hasattr(tickets, "TICKET_EXECUTOR_ENGINES"))


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


# Every security mark the three classes below read: the file an escape would
# write, the span that would write it, and the criterion stating that span.
# Each mirrors the fixture set of the same name, which keeps its own `/tmp`
# spelling -- `tests/fixtures/cutcheck/` is outside this item's write scope and
# `verdicts.json` pins every line those sets produce. What moves here is the
# mark, which is the one part of it a neighbouring run can reach.
MARKS = {
    "shellhead": (
        (
            "shellhead-ran",
            "bash -lc 'touch {mark}'",
            "**A shell span is never executed.** `{span}` is the span; through "
            "a shell it touches that file, which is how the test tells running "
            "from reporting.",
        ),
    ),
    "evalhead": (
        (
            "evalhead-ran",
            "python3 -c \"import pathlib;pathlib.Path('{mark}').touch()\"",
            "**An interpreter evaluating its argument is never executed.** "
            "`{span}` is the span; evaluated, it touches that file, which is "
            "how the test tells running from reporting.",
        ),
    ),
    "gitescape": (
        (
            "gitescape-ran",
            "git -c alias.pwn='!touch {mark}' pwn",
            "**A git span never runs a program it names.** `{span}` is the "
            "span; git runs that alias whatever its output is attached to, "
            "which is how the test tells running from reporting.",
        ),
        (
            "gitescape-wrote",
            "git log --output={mark}",
            "**A git span never writes a file it names.** `{span}` is the "
            "span; `log` is a confined subcommand and `--output` stands after "
            "it, so the subcommand alone decides nothing here.",
        ),
    ),
}

ESCAPE_TICKET = """---
id: 01-escape
run: cutcheck-escape-beside
status: issued
---
## Objective

Built beside the tree: the fixture set's own criteria, each stating its span
against a mark this run made rather than the machine-global path the pinned
fixture names.

## Completion test

{criteria}

## Result

[]
"""


def mark_home(case, slug):
    """A directory for this run's security marks, under the host's temp root.

    `mkdtemp` and not a literal, on both counts `MarkFileIsolationTest` states:
    the directory is this process's alone, so no neighbouring run can unlink
    what is in it, and its root is whatever this host answers rather than a
    POSIX `/tmp` that Windows resolves onto the current drive and usually does
    not have. Asserted present here, before the caller asserts anything absent
    inside it, because the whole defect being repaired is an absence assertion
    over a directory that could never have held the file.

    The removal is spelled at this call site rather than passed in, so that
    `rmtree_calls` sees it: that reading matches `addCleanup` against a literal
    `shutil.rmtree`, and a removal handed through a parameter would be a
    removal this suite performs and its own cleanup node is blind to.
    """

    home = Path(tempfile.mkdtemp(prefix="cutcheck-{}-".format(slug)))
    case.addCleanup(shutil.rmtree, home)
    case.assertTrue(home.is_dir(), "{}: no directory to hold a mark".format(home))
    return home


def escape_ticket(rows, home):
    """The fixture set's criteria, rebased onto the marks under `home`."""

    criteria = [
        "{}. {} oracle_class: deterministic. provenance: authored-here.".format(
            number, prose.format(span=span.format(mark=home / name))
        )
        for number, (name, span, prose) in enumerate(rows, 1)
    ]
    return ESCAPE_TICKET.format(criteria="\n\n".join(criteria))


def unrun(case, home, rows):
    """Every span writes its mark when run here, and none writes it when checked.

    Two readings, in this order, because the second is worth nothing without
    the first. Each span runs directly to begin with, through the executor
    cutcheck would have used and in the directory it would have used: an
    assertion that a file is absent decides nothing wherever nothing could
    have created it, and the host -- never `os.name` -- is what decides which
    of the two this is. `bash` and `touch` are the escape and cannot be
    respelled into something a frozen set can promise, so where the writer
    does not resolve, a skip naming the span is the honest report and a green
    node is not.
    """

    marks = [home / name for name, _, _ in rows]
    for mark, (_, span, _) in zip(marks, rows):
        stated = span.format(mark=mark)
        cutcheck._run_once(stated, home)
        if not mark.exists():
            case.skipTest(
                "{!r} wrote no mark here, so the absence of one would decide "
                "nothing".format(stated)
            )
        mark.unlink()
    # `_run_once` records what the copy gained, and these probes are this
    # test's own writes rather than a span's; the reading is per tree, so the
    # entry this one added goes with it.
    case.addCleanup(cutcheck._EXIT_CACHE.clear)
    case.addCleanup(cutcheck._MUTATED.clear)
    case.addCleanup(cutcheck._TREE_STATE.pop, str(home), None)
    path = home / "01-escape.md"
    path.write_text(escape_ticket(rows, home), encoding="utf-8")
    return marks, cutcheck._check_ticket(path, home, None, {})


class ShellHeadTest(unittest.TestCase):
    """Ticket content is untrusted input: no span of one reaches a shell."""

    def setUp(self):
        self.result = run_cutcheck("cutcheck-shellhead")

    def test_the_shell_span_did_not_run(self):
        """The refusal, read beside the tree so the mark can be this run's own.

        The fixture invocation next door still grades the report end to end;
        what it cannot do is carry a per-run mark, because its ticket is
        pinned and names `/tmp`. This states the same span in the same frame,
        differing in the mark path alone, and checks it through the same
        `_check_ticket` the invocation reaches.
        """

        home = mark_home(self, "shellhead")
        marks, findings = unrun(self, home, MARKS["shellhead"])
        self.assertIn(cutcheck.EXTRACTION_GAP, [f[2] for f in findings], findings)
        for mark in marks:
            self.assertFalse(mark.exists(), "{}\n{}".format(mark, findings))

    def test_the_span_is_reported_rather_than_run(self):
        lines = [line for line in finding_lines(self.result) if "01-shellhead" in line]
        self.assertEqual(len(lines), 1, self.result.stdout)
        self.assertIn(cutcheck.EXTRACTION_GAP, lines[0])


class EvalHeadTest(unittest.TestCase):
    """An interpreter handed its program on the line is a shell by another head."""

    def setUp(self):
        self.result = run_cutcheck("cutcheck-evalhead")

    def test_the_evaluated_span_did_not_run(self):
        """Read beside the tree, for the reason `ShellHeadTest` states next door."""

        home = mark_home(self, "evalhead")
        marks, findings = unrun(self, home, MARKS["evalhead"])
        self.assertIn(cutcheck.EXTRACTION_GAP, [f[2] for f in findings], findings)
        for mark in marks:
            self.assertFalse(mark.exists(), "{}\n{}".format(mark, findings))

    def test_the_span_is_reported_rather_than_run(self):
        lines = [line for line in finding_lines(self.result) if "01-evalhead" in line]
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

    @classmethod
    def setUpClass(cls):
        cls.result = run_cutcheck("cutcheck-gitescape")

    def test_the_injected_span_did_not_run(self):
        """Both spans, read beside the tree, for the reason `ShellHeadTest` states.

        The directory is made a repository first. `git log --output=` writes
        the file it names from inside one and nowhere else, so without the
        `init` the probe in `unrun` would find no mark, skip, and leave the
        half of this claim it exists to carry unread.
        """

        home = mark_home(self, "gitescape")
        must_git(self, ["init", "-q", "."], home)
        marks, findings = unrun(self, home, MARKS["gitescape"])
        classes = [f[2] for f in findings]
        self.assertEqual(classes.count(cutcheck.UNCONFINED_ORACLE), 2, findings)
        for mark in marks:
            self.assertFalse(mark.exists(), "{}\n{}".format(mark, findings))

    def test_the_span_is_reported_rather_than_run(self):
        lines = [
            line for line in finding_lines(self.result) if "01-gitescape" in line
        ]
        self.assertEqual(len(lines), 2, self.result.stdout)
        for line in lines:
            self.assertIn(cutcheck.UNCONFINED_ORACLE, line)

    def test_a_refused_span_is_a_finding_and_not_a_silence(self):
        self.assertNotIn(cutcheck.UNCONFINED_ORACLE, cutcheck.ADVISORY)
        self.assertNotEqual(self.result.returncode, 0, self.result.stdout)


TMP_LITERAL = re.compile(r"""Path\(\s*["']/tmp""")


def tmp_literals(source):
    """Every line of a module that builds a path out of a `/tmp` literal."""

    return [
        "line {}: {}".format(number, line.strip())
        for number, line in enumerate(source.splitlines(), 1)
        if TMP_LITERAL.search(line)
    ]


class MarkFileIsolationTest(unittest.TestCase):
    """A security mark is this run's own file, at a path the host chose.

    The four marks above were machine-global `/tmp` literals, and each half of
    that is a hazard in one direction only.

    Shared: every assertion about a mark is `assertFalse(mark.exists())` --
    "the escape did not run" -- and the unlink keeping it honest is somebody's
    `unlink(missing_ok=True)`. At a shared path, a neighbouring run's unlink
    landing between this run's execution and its assertion turns a real escape
    into a PASS. The opposite ordering only costs a spurious failure, so the
    hazard is asymmetric and the silent direction is the one that certifies
    nothing.

    Literal: `/tmp` is a POSIX spelling that resolves onto the current drive on
    Windows and typically does not exist there. Over a directory that cannot
    hold the file, an absence assertion passes whatever the tool did.
    `tempfile.gettempdir()` is the host's own answer to the same question.
    """

    def test_no_tmp_literal_remains_in_the_module(self):
        """Read from the source, so it covers the fifth mark somebody adds.

        A `/tmp` inside a command string is a different thing and stays:
        `GIT_ESCAPES` and `GIT_REACHES_OUT` are text handed to the confinement
        gate and never run, and each mirrors a line `verdicts.json` pins. What
        is read here is a path this module builds and then stats.
        """

        source = Path(__file__).resolve().read_text(encoding="utf-8")
        self.assertEqual(tmp_literals(source), [])

    def test_the_reading_reports_the_literal_that_was_here(self):
        """The can-fail direction: an empty reading passes the node above free.

        Both the sample and what it should read as are assembled rather than
        written out, because a module grading its own source is read by the
        node it feeds: spelled literally, either one would be a fifth finding
        against this file.
        """

        was_here = 'MARK = Path("{}/cutcheck-shellhead-ran")'.format("/tmp")
        self.assertEqual(tmp_literals(was_here), ["line 1: " + was_here])
        self.assertEqual(tmp_literals("mark = home / 'shellhead-ran'"), [])

    def test_each_mark_parent_exists_before_the_body_runs(self):
        """One assertion per mark, on the directory each class is handed.

        `mkdtemp` documents that it creates the directory; this is the node
        saying so on this host rather than taking it, because the defect being
        repaired is precisely an absence assertion over a directory that was
        never there. The root is the host's own, so a leg where `/tmp` does
        not exist reads its own answer here instead of a POSIX one.
        """

        root = Path(tempfile.gettempdir()).resolve()
        seen = []
        for slug, rows in sorted(MARKS.items()):
            home = mark_home(self, slug)
            self.assertEqual(home.parent.resolve(), root, home)
            for name, _, _ in rows:
                mark = home / name
                self.assertTrue(
                    mark.parent.is_dir(), "{}: no directory to hold it".format(mark)
                )
                self.assertFalse(mark.exists(), mark)
                seen.append(name)
        self.assertEqual(
            seen,
            ["evalhead-ran", "gitescape-ran", "gitescape-wrote", "shellhead-ran"],
            "these four marks are what this grades; an empty table grades nothing",
        )

    def test_two_run_contexts_hold_disjoint_mark_paths(self):
        """Two contexts at once, and neither can reach the other's evidence.

        Decided by unlinking rather than by comparing strings: the hazard is
        one run's `unlink` deleting the file another run is about to read, and
        two different paths is the claim only because that unlink misses.
        """

        def context():
            marks = {}
            for slug, rows in MARKS.items():
                home = mark_home(self, slug)
                for name, _, _ in rows:
                    marks[name] = home / name
            return marks

        first, second = context(), context()
        self.assertEqual(sorted(first), sorted(second))
        self.assertEqual(len(first), 4, first)
        for name, mark in first.items():
            self.assertNotEqual(mark, second[name], name)
            mark.write_text("ran", encoding="utf-8")
            second[name].write_text("ran", encoding="utf-8")
        for mark in second.values():
            mark.unlink()
        for name, mark in first.items():
            self.assertTrue(
                mark.exists(),
                "{}: a neighbouring run's unlink reached this run's evidence".format(
                    name
                ),
            )

    def test_the_escapes_name_a_program_the_frozen_span_set_cannot_promise(self):
        """Why these spans are probed rather than frozen.

        `SpanDependencyTest` freezes what a span this module runs may name,
        because one naming an uninstalled package writes nothing on a bare CI
        leg and every assertion about what it wrote goes red there. The shell
        escape names `bash`, which no frozen set can promise and which
        respelling as `python3` would turn into a different refusal. `unrun`
        therefore runs each escape directly before asserting anything about
        it, and skips where nothing was written, so a host lacking the writer
        reports a skip and never a false green.
        """

        outside = sorted(
            {
                name
                for rows in MARKS.values()
                for _, span, _ in rows
                for kind, name in span_requirements(span.format(mark="mark"))
                if kind == "program" and name not in SPAN_PROGRAMS
            }
        )
        self.assertEqual(
            outside, ["bash"], "an escape's head moved; re-read the skip above"
        )


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
    case.addCleanup(remove_repo_tree, root)
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
    case.addCleanup(remove_repo_tree, root)
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
        """Amended, not replaced: §5 keeps the symlink fact; the scripts'
        stdlib / cross-platform / no-network fact is ARCHITECTURE.md's
        scripts bullet (moved 2026-08-16, an ownership fact under a symlink
        clause)."""

        clause = _visibility_clause(5)
        self.assertIn("No symlinks", clause, clause)
        bullet = " ".join((ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8").split())
        for kept in ("stdlib Python 3", "Windows and POSIX", "no network"):
            self.assertIn(kept, bullet)


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
            self.assertNotEqual(
                cutcheck.PRE_EXISTING, cutcheck._stated_provenance(text), text
            )


class ProvenanceStampTest(unittest.TestCase):
    """A stamp a criterion makes of its own oracle still exempts that oracle."""

    def test_the_paired_positive_is_exempt(self):
        result = run_cutcheck("cutcheck-provenance-mention")
        lines = [line for line in reported(result) if "02-stamped" in line]
        self.assertEqual(lines, [], result.stdout)

    def test_every_shape_the_corpus_stamps_with_still_reads_as_a_stamp(self):
        for text in (
            "**A criterion.** `grep -n x install.py` returns it. oracle_class: "
            "deterministic. provenance: pre-existing.",
            "provenance: pre-existing",
            "**A criterion.** oracle_class: judged. Provenance:  Pre-Existing.",
            # A live set stamps this way: the field, then why it is the field.
            "oracle_class: deterministic. provenance: pre-existing (the fixture "
            "exists from item 01).",
            # The form `tickets.py` writes, in its own gate stubs and in every
            # ticket `new` renders: the two scripts disagreed on this one and
            # the library's own stubs were the casualty.
            "the suite exits 0 | oracle: `python -B -m unittest tests.x.Y` "
            "| oracle_class: deterministic | provenance: pre-existing",
        ):
            self.assertEqual(cutcheck.PRE_EXISTING, cutcheck._stated_provenance(text), text)


class CriterionOwnerTest(unittest.TestCase):
    """Criterion parsing has one owner, and this tool is not it.

    Every criterion this tool grades is one `scripts/tickets.py` already
    refused a ticket over, so a second parser here is a section that reads one
    way to the cut's refusal and another way to the cut's check. It read that
    way: a `- ` bullet criterion -- the form `tickets.py new` renders -- was
    invisible to this tool while being graded there.
    """

    SECTION = (
        "- the suite exits 0 | oracle: `grep -n \"cutcheck.py\" install.py` "
        "| oracle_class: deterministic | provenance: pre-existing\n"
        "- the docs read well | oracle: the lens | oracle_class: judged\n"
    )

    def test_a_bullet_criterion_is_read_with_its_class_and_its_provenance(self):
        criteria = cutcheck._criteria(self.SECTION)
        self.assertEqual([1, 2], [number for number, _ in criteria])
        first = dict(criteria)[1]
        self.assertEqual("deterministic", cutcheck._oracle_class(first))
        self.assertEqual(cutcheck.PRE_EXISTING, cutcheck._stated_provenance(first))
        self.assertEqual("judged", cutcheck._oracle_class(dict(criteria)[2]))

    def test_the_criteria_are_the_ones_scripts_tickets_reads(self):
        self.assertEqual(
            [text for _, text in cutcheck._criteria(self.SECTION)],
            tickets._criteria(self.SECTION),
        )

    def test_the_stated_class_travels_with_an_extraction_gap(self):
        _, advisories, _ = report(run_cutcheck("cutcheck-f1-truncated"))
        gaps = [line for line in advisories if cutcheck.EXTRACTION_GAP in line]
        self.assertEqual(1, len(gaps), advisories)
        self.assertIn("oracle_class: judgment", gaps[0])


class VerdictInOutputTest(unittest.TestCase):
    """A command whose verdict is in what it prints is one cutcheck cannot judge."""

    def setUp(self):
        self.result = run_cutcheck("cutcheck-verdict-in-output")
        self.lines = [
            line for line in finding_lines(self.result) if "01-verdict" in line
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

    @classmethod
    def setUpClass(cls):
        cls.tree = shared_baseline_tree()

    def test_a_command_printing_binary_is_graded_on_its_exit_status(self):
        self.assertEqual(cutcheck._run_once("git archive HEAD", self.tree), 0)


class ScratchTreeHistoryTest(unittest.TestCase):
    """The graded tree is a repository of its own, holding the graded revision."""

    @classmethod
    def setUpClass(cls):
        cls.tree = shared_baseline_tree()

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
    # Bytes with LF: a text-mode write on Windows would land CRLF and
    # differ from every other host's recording.
    VERDICTS.write_bytes(
        (json.dumps(recorded, indent=1, sort_keys=True) + "\n").encode("utf-8")
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
        # `symlink-in-tree` and `unread-half` joined later and are additions,
        # not survivals: the claim this pins is still that GIT_NO_HISTORY left
        # and that no member standing beside it left with it.
        self.assertEqual(
            cutcheck.ADVISORY,
            frozenset(
                {
                    cutcheck.EXTRACTION_GAP,
                    cutcheck.COVERAGE_MAP_ABSENT,
                    cutcheck.VERDICT_IN_OUTPUT,
                    cutcheck.SYMLINK_IN_TREE,
                    cutcheck.BYTECODE_WRITTEN,
                    cutcheck.UNREAD_HALF,
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


# The two trees holding every ticket this repository tracks. The per-run trees
# under `.orch/tickets/` are a worktree's own runtime state, present on one
# machine and absent on the next, so a corpus claim cannot be made about them.
CORPUS_ROOTS = (
    ROOT / ".orch" / "canary" / "tickets" / "canary",
    FIXTURES,
)
# One criterion, handed to the whole gate. Its frontmatter grants `scripts/`
# so a probe's own oracle paths resolve and family 3 stays quiet.
PROBE_TICKET = """\
---
id: node-id-probe
run: node-id-probe
status: ready
executor: orch-tdd
depends_on: []
write_scope: scripts/
bound: 1 tool call
---
## Objective
The one criterion the probe was handed.
## Fixed inputs
None.
## Completion test
1. {criterion}
## Return fields
status.
## Result
[]
## Verification
[]
## Feedback
[]
## Risks
[]
"""


class NodeIdOracleGapTest(unittest.TestCase):
    """An oracle naming no node id is reported, and never run.

    `_commands` already refuses a bare head, because a tool's name with nothing
    after it decides nothing. A whole-module or whole-suite invocation is that
    same defect with more typing: it runs the identical tests under every item
    it is stated under, so it discriminates none of them.

    Reporting it removes a standing hazard rather than adding a rule. This
    repository's own second mandated check is a whole-suite `discover`, and
    that suite outgrew `COMMAND_TIMEOUT` in the cleanest store there is, so
    executing it returned `unrunnable-oracle` -- a true class, reached by
    reading the clock instead of the cut, and reached only for criteria that
    happened to carry no `pre-existing` stamp.
    """

    def _report(self, criterion):
        """Every class reported for one criterion, and every command run for it.

        Through `_check_ticket` rather than through `_whole_suite` alone: the
        exemption is an ordering inside that function, and no reading of the
        predicate by itself can see it. `_exit_code` is mocked because what is
        graded here is which commands reach execution, not what they return.
        """

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "01-probe.md"
            path.write_text(
                PROBE_TICKET.format(criterion=criterion), encoding="utf-8"
            )
            with mock.patch.object(cutcheck, "_exit_code", return_value=1) as ran:
                findings = cutcheck._check_ticket(path, ROOT, None, {})
        return (
            [klass for _, _, klass, _ in findings],
            [call[0][0] for call in ran.call_args_list],
        )

    def test_a_whole_module_oracle_is_reported_as_a_gap(self):
        for command in (
            "python3 -m unittest tests.test_cutcheck",
            "python3 -m unittest discover -s tests -v",
            "pytest tests",
            "pytest tests/test_cutcheck.py",
        ):
            with self.subTest(command=command):
                classes, ran = self._report(
                    "`{}` exits 0. Oracle: the command above. "
                    "oracle_class: deterministic.".format(command)
                )
                self.assertIn(cutcheck.WHOLE_SUITE_ORACLE, classes, classes)
                self.assertEqual(ran, [], "a gap is decided without running it")

    def test_an_oracle_naming_a_node_id_is_not_reported(self):
        """The can-fail direction, on all three spellings that name a node.

        A dotted target reaching past its module, pytest's `::`, and `-k`. The
        run is asserted beside the silence: a predicate that convicted nothing
        because the command never reached it would read as this one does.
        """

        for command in (
            "python3 -m unittest tests.test_cutcheck.NodeIdOracleGapTest",
            "python3 -B -m unittest tests.test_installer.NoSuchClass.test_absent",
            "pytest tests/test_cutcheck.py::NodeIdOracleGapTest",
            "python3 -m unittest discover -s tests -k test_a_named_node",
        ):
            with self.subTest(command=command):
                classes, ran = self._report(
                    "`{}` exits 0. Oracle: the command above. "
                    "oracle_class: deterministic.".format(command)
                )
                self.assertNotIn(cutcheck.WHOLE_SUITE_ORACLE, classes, classes)
                self.assertEqual(ran, [command])

    def test_a_pre_existing_required_check_stays_exempt(self):
        """The four checks `AGENTS.md` mandates, stated as what they are.

        An invariant's job is holding still, not discriminating, and the stamp
        that says so is read before this class is. Without that order the
        second of the four convicts every ticket honest enough to state it.
        """

        classes, ran = self._report(
            "`python tools/validate.py`, `python -m unittest discover -s tests -v`, "
            "`python install.py --dry-run` and `git diff --check` all pass. "
            "Oracle: the four commands above. oracle_class: deterministic. "
            "provenance: pre-existing."
        )
        self.assertNotIn(cutcheck.WHOLE_SUITE_ORACLE, classes, classes)
        self.assertEqual(ran, [], "an invariant is not run for discrimination")

    def test_the_tracked_corpus_reports_zero_gaps(self):
        """Every tracked criterion, read through the gate's own two questions.

        Statically: running the tool over the whole corpus costs minutes and
        sees nothing more, because the gate is one stamp and one predicate and
        `test_a_pre_existing_required_check_stays_exempt` is what grades their
        order. The commands read are asserted too -- a scan that resolved no
        ticket reports zero gaps for the wrong reason.
        """

        read, gaps = [], []
        for root in CORPUS_ROOTS:
            for path in sorted(root.rglob("*.md")):
                text = path.read_text(encoding="utf-8")
                section = cutcheck._sections(text).get(cutcheck.COMPLETION_SECTION, "")
                for number, criterion in cutcheck._criteria(section):
                    for command in cutcheck._commands(criterion):
                        read.append(command)
                        if cutcheck._stated_provenance(criterion) == cutcheck.PRE_EXISTING:
                            continue
                        if cutcheck._whole_suite(command, ROOT):
                            gaps.append(
                                "{} criterion {}: {}".format(
                                    path.relative_to(ROOT), number, command
                                )
                            )
        self.assertIn(
            'python3 -m unittest discover -s .orch/canary/scratch/tdd -p "test_*.py"'
            " -k test_double_returns_twice_input -v",
            read,
            "the canary criterion this class was cut for was not read",
        )
        self.assertEqual(gaps, [], "\n".join(gaps))

    def test_the_gap_sets_the_exit_status(self):
        """Family 1 and not advisory: an oracle discriminating nothing is a defect.

        `extraction-gap` is advisory because it reports what cutcheck could not
        read. This reports what the criterion does say, and says it decides
        nothing -- the same finding as `already-passes`, and graded the same.
        """

        self.assertEqual(
            cutcheck.FAMILY_OF[cutcheck.WHOLE_SUITE_ORACLE], cutcheck.FAMILY
        )
        self.assertNotIn(cutcheck.WHOLE_SUITE_ORACLE, cutcheck.ADVISORY)


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


def _graded_with(test, argv, failing_clone=None):
    """One `main` run in this process, against the shared copies.

    The seam `tests/baseline_pin.py` uses, opened here because these cases
    hand `main` an argv that helper does not build -- a `--lib`, or a clone
    that fails for one revision and not the other.
    """

    root = shared_root()
    real = cutcheck._scratch_tree

    def clone(rev, worktree_root, scratch_root):
        if rev == failing_clone:
            return None
        return real(rev, worktree_root, scratch_root)

    out, err = io.StringIO(), io.StringIO()
    here = Path.cwd()
    os.chdir(str(ROOT))
    try:
        with mock.patch.object(cutcheck, "_scratch_root", lambda _tree: root):
            with mock.patch.object(cutcheck, "_remove_scratch_root", lambda _root: None):
                with mock.patch.object(cutcheck, "_scratch_tree", clone):
                    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                        code = cutcheck.main(argv)
    finally:
        os.chdir(str(here))
    return code, out.getvalue()


class HeadCloneRefusalTest(unittest.TestCase):
    """A HEAD half nothing could clone exits like a baseline half nothing could.

    The baseline failure prints its reason and returns `NO_TICKET_SET`. The
    HEAD failure returned `None` into `_discrimination`, where `None` is
    also "cut time, there is no HEAD half to ask" -- so every oracle graded
    clean, the report affirmed, and the run exited 0. Friction 04:21:49Z is
    that clone failing for `MAX_PATH` on the baseline half, where it is
    loud; the HEAD half takes the same route and said nothing.
    """

    def test_the_head_half_refuses_the_way_the_baseline_half_does(self):
        argv = ["cutcheck-clean", "--baseline", BASELINE]
        head_code, head_out = _graded_with(self, argv, failing_clone="HEAD")
        base_code, base_out = _graded_with(self, argv, failing_clone=BASELINE)
        self.assertEqual(base_code, cutcheck.NO_TICKET_SET, base_out)
        self.assertEqual(head_code, base_code, head_out)
        self.assertIn("cannot clone HEAD", head_out)
        self.assertIn("cannot clone baseline", base_out)
        self.assertNotIn(cutcheck.NO_FINDING_OUTSIDE, head_out)


class UnreadHalfTest(unittest.TestCase):
    """"Could not grade" and "discriminates" stop sharing one value.

    `None` said both: an oracle that fails at the baseline and passes once
    the work has landed, and a half nothing could read. Every unread
    reading now names itself on one advisory line, so a grading that did
    not happen reads as a grading that did not happen rather than as a
    clean one.
    """

    def setUp(self):
        cutcheck._UNREAD.clear()
        self.addCleanup(cutcheck._UNREAD.clear)

    def test_the_class_carries_a_family_and_decides_no_exit_status(self):
        # An unread reading is a fact about this run on this host, like a
        # coverage map that is not there -- reported, never a cut defect.
        self.assertIn(cutcheck.UNREAD_HALF, cutcheck.FAMILY_OF)
        self.assertIn(cutcheck.UNREAD_HALF, cutcheck.ADVISORY)

    def test_a_baseline_reading_that_decided_nothing_says_so(self):
        with mock.patch.object(cutcheck, "_exit_code", return_value=None):
            klass = cutcheck._discrimination("pytest tests", Path("/b"), Path("/h"))
        self.assertIsNone(klass)
        self.assertEqual(len(cutcheck._UNREAD), 1, cutcheck._UNREAD)
        self.assertIn("pytest tests", cutcheck._UNREAD[0])

    def test_a_head_reading_that_decided_nothing_says_so_too(self):
        baseline, head = Path("/b"), Path("/h")

        def exit_code(command, tree):
            return 1 if tree == baseline else None

        with mock.patch.object(cutcheck, "_exit_code", side_effect=exit_code):
            klass = cutcheck._discrimination("pytest tests", baseline, head)
        self.assertIsNone(klass)
        self.assertEqual(len(cutcheck._UNREAD), 1, cutcheck._UNREAD)
        self.assertIn("HEAD", cutcheck._UNREAD[0])

    def test_cut_time_is_a_stated_ladder_and_not_an_unread_half(self):
        """At cut time nothing has landed, so there is no HEAD half to ask and
        a baseline failure is what a discriminating oracle looks like. The
        module docstring states that; an advisory line would deny it."""

        with mock.patch.object(cutcheck, "_exit_code", return_value=1):
            self.assertIsNone(cutcheck._discrimination("pytest tests", Path("/b"), None))
        self.assertEqual(cutcheck._UNREAD, [])

    def test_a_confinement_reading_that_failed_is_not_nothing_written(self):
        """`_mutations` is the confinement instrument. Its empty list means
        "this span wrote nothing"; a `git status` that failed means "nobody
        looked", and the two were one answer."""

        self.assertEqual(cutcheck._mutations(Path(ROOT) / "no-such-tree"), [])
        self.assertTrue(cutcheck._UNREAD, "the failed status said nothing")

    def test_a_symlink_reading_that_failed_is_not_no_symlinks(self):
        self.assertEqual(cutcheck._symlink_entries(Path(ROOT) / "no-such-tree"), [])
        self.assertTrue(cutcheck._UNREAD, "the failed ls-tree said nothing")
        cutcheck._UNREAD.clear()
        # A tree it can read answers, and says nothing besides.
        self.assertEqual(cutcheck._symlink_entries(ROOT), [])
        self.assertEqual(cutcheck._UNREAD, [])

    def test_a_file_too_large_to_index_cannot_be_pinned_and_says_so(self):
        """Family 3's other direction reads every file under `PIN_ROOTS` for the
        literals an objective takes away. A file it skipped holds no pin as far
        as the report is concerned, which is a claim about the file rather than
        about the reading."""

        self.addCleanup(cutcheck._PIN_INDEX.clear)
        tree = Path(tempfile.mkdtemp(prefix="cutcheck-pins-"))
        self.addCleanup(remove_repo_tree, tree)
        (tree / "docs").mkdir()
        (tree / "docs" / "small.md").write_text("a pin\n", encoding="utf-8")
        (tree / "docs" / "big.bin").write_bytes(b"x" * (cutcheck.PIN_SIZE_LIMIT + 1))

        indexed = [rel for rel, _ in cutcheck._pin_index(tree)]

        self.assertEqual(indexed, ["docs/small.md"])
        self.assertEqual(len(cutcheck._UNREAD), 1, cutcheck._UNREAD)
        self.assertIn("docs/big.bin", cutcheck._UNREAD[0])

    def test_a_library_with_no_packs_grades_family_6_against_nothing_and_says_so(self):
        empty = Path(tempfile.mkdtemp(prefix="cutcheck-nolib-"))
        self.addCleanup(remove_repo_tree, empty)

        self.assertEqual(cutcheck._lib_root(str(empty)), empty)
        self.assertTrue(cutcheck._UNREAD, "a declared library holding no packs")
        cutcheck._UNREAD.clear()

        with mock.patch.object(cutcheck, "PACKS_DIR", "no-such-directory"):
            self.assertIsNone(cutcheck._lib_root(None))
        self.assertTrue(cutcheck._UNREAD, "no library resolved at all")

    def test_this_librarys_own_checkout_reads_clean(self):
        self.assertEqual(cutcheck._lib_root(None), ROOT)
        self.assertEqual(cutcheck._UNREAD, [])

    def test_the_report_carries_the_advisory_line_and_still_exits_zero(self):
        """End to end: an unread reading reaches stdout under the advisory
        heading, selectable by class like every other finding, and decides no
        exit status."""

        empty = Path(tempfile.mkdtemp(prefix="cutcheck-nolib-"))
        self.addCleanup(remove_repo_tree, empty)
        code, out = _graded_with(
            self, ["cutcheck-clean", "--baseline", BASELINE, "--lib", str(empty)]
        )
        advisories = report(subprocess.CompletedProcess([], code, stdout=out))[1]
        lines = [line for line in advisories if cutcheck.UNREAD_HALF in line]
        self.assertEqual(len(lines), 1, out)
        self.assertIn(str(empty), lines[0])
        self.assertEqual(code, cutcheck.CLEAN, out)


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


# Item 05's five readers. Every one of them resolved run state under the
# repository before this item; every one of them reaches the sink now, and
# the last two entries prove it for the whole set at once.
READERS = (
    "scripts/cutcheck.py",
    "scripts/ui.py",
    "scripts/isolate.py",
    "scripts/trace.py",
    "tools/live_sweep_e2e.py",
)

# Every non-docstring string literal in those files that still names `.orch`,
# with the reason it is allowed to. Anything else is a reader left behind.
ALLOWED_STATE_LITERALS = {
    # The canary is a git-tracked golden fixture under the repository, not
    # run state, and the item's `excluded_actions` forbid moving it.
    "scripts/cutcheck.py": {".orch"},
    # Where a run snapshot lands inside an isolated tree. A copy of the
    # sink's layout, not a state root: `state_root.py` still owns that.
    "scripts/isolate.py": {".orchflows-state"},
    # Item 05 criterion 4: a trace may cover a session that predates the
    # migration, so the harvester matches the repository shape as well as
    # the sink's. This matches a path in someone else's transcript; it
    # composes no path this host reads.
    "scripts/trace.py": {
        r"(?:\.orch|\.orchflows[/\\]state)",
    },
    "scripts/ui.py": set(),
    "tools/live_sweep_e2e.py": set(),
}


def state_literals(relative: str) -> set:
    """Every string literal in one reader that names `.orch`, docstrings
    excluded: prose is item 07's, and a comment is not a path."""

    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, "body", None)
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                docstrings.add(id(body[0].value))
    return {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and ".orch" in node.value
        and id(node) not in docstrings
    }


class TestCutcheckResolvesSink(unittest.TestCase):
    """Item 05 criteria 1 and 6. `cutcheck.py` grades a run from wherever the
    run's tickets are, which is the sink now -- and still grades the canary,
    which is a fixture in the repository and stays there."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        self.sink = self.tmp / "sink"
        self.repo = self.tmp / "repo"
        (self.repo / ".git").mkdir(parents=True)

    def issue(self, root: Path, run: str, source: str = "cutcheck-clean") -> Path:
        """One fixture ticket set, copied to `root` under the name `run`."""

        dest = root / run
        dest.mkdir(parents=True)
        for src in sorted(
            (ROOT / "tests" / "fixtures" / "cutcheck" / source).glob("*.md")
        ):
            shutil.copyfile(str(src), str(dest / src.name))
        return dest

    @contextlib.contextmanager
    def launched_from(self, where: Path):
        """cwd and sink both pointed away from this repository."""

        cwd = os.getcwd()
        os.chdir(str(where))
        try:
            with mock.patch.dict(
                os.environ, {state_root.ENV_VAR: str(self.sink)}
            ):
                yield
        finally:
            os.chdir(cwd)

    # --- criterion 1 ---------------------------------------------------

    def test_a_run_living_only_in_the_sink_is_found(self):
        issued = self.issue(self.sink / "tickets", "sink-only")

        with self.launched_from(self.repo):
            found = cutcheck._run_dir("sink-only", None)

        self.assertEqual(issued, found)
        self.assertTrue(sorted(found.glob("*.md")))

    def test_a_run_living_only_in_a_repositorys_own_state_is_not_found(self):
        """The whole point of the move: a reader that still fell back here
        would keep per-repository run state alive after item 08 copies."""

        self.issue(self.repo / ".orch" / "tickets", "repo-only")
        (self.sink / "tickets").mkdir(parents=True)

        with self.launched_from(self.repo):
            self.assertIsNone(cutcheck._run_dir("repo-only", None))

    def test_the_canary_still_resolves_under_the_repository(self):
        issued = self.issue(
            self.repo / ".orch" / "canary" / "tickets", "canary", source="cutcheck-clean"
        )

        with self.launched_from(self.repo):
            found = cutcheck._run_dir("canary", None)

        # Asserted before it is dereferenced, so a candidate list that stopped
        # offering the canary reads as this case failing, not as a traceback.
        self.assertIsNotNone(found)
        self.assertEqual(issued.resolve(), found.resolve())

    def test_this_repositorys_real_canary_is_still_found(self):
        # The tracked fixture, not a copy: `CanarySetTest` grades it, and it
        # can only do that while this resolves. It lives at the main checkout
        # -- a worktree of this repository has no `.orch/canary/` of its own.
        main = state_root.find_repo_root(ROOT)
        found = cutcheck._run_dir("canary", ROOT)
        self.assertIsNotNone(found)
        self.assertEqual(
            (main / ".orch" / "canary" / "tickets" / "canary").resolve(),
            found.resolve(),
        )
        self.assertTrue(sorted(found.glob("*.md")))

    def test_the_sink_is_preferred_over_a_fixture_set_of_the_same_name(self):
        """Order matters: run state first, then the canary, then fixtures."""

        issued = self.issue(self.sink / "tickets", "cutcheck-clean")

        with self.launched_from(self.repo):
            self.assertEqual(issued, cutcheck._run_dir("cutcheck-clean", ROOT))

    def test_a_sink_resident_run_is_graded_end_to_end(self):
        self.issue(self.sink / "tickets", "sink-clean")
        scratch_root = shared_root()
        out, err = io.StringIO(), io.StringIO()
        with self.launched_from(ROOT):
            with mock.patch.object(
                cutcheck, "_scratch_root", lambda _tree: scratch_root
            ):
                with mock.patch.object(
                    cutcheck, "_remove_scratch_root", lambda _root: None
                ):
                    with contextlib.redirect_stdout(out):
                        with contextlib.redirect_stderr(err):
                            code = cutcheck.main(
                                ["sink-clean", "--baseline", BASELINE]
                            )
        done = subprocess.CompletedProcess(
            ["sink-clean", BASELINE], code, out.getvalue(), err.getvalue()
        )

        self.assertEqual(0, done.returncode, done.stdout + done.stderr)
        self.assertEqual([], reported(done), done.stdout)

    def test_a_run_nowhere_is_still_the_named_absence(self):
        (self.sink / "tickets").mkdir(parents=True)
        env = dict(os.environ)
        env[state_root.ENV_VAR] = str(self.sink)

        done = subprocess.run(
            [sys.executable, "scripts/cutcheck.py", "no-such-run",
             "--baseline", BASELINE],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=env,
        )

        self.assertEqual(
            cutcheck.NO_TICKET_SET, done.returncode, done.stdout + done.stderr
        )

    # --- criterion 6 ---------------------------------------------------

    def test_no_reader_still_composes_a_repository_state_path(self):
        for relative in READERS:
            with self.subTest(relative):
                self.assertEqual(
                    ALLOWED_STATE_LITERALS[relative],
                    state_literals(relative),
                )

    def test_every_reader_that_resolves_the_sink_reaches_the_one_resolver(self):
        """Item 01's module, by the names its result gives -- and every name
        a reader calls is one the resolver really exports, so a reader and a
        renamed export cannot drift apart silently. `trace.py` is the one
        exception and is asserted as one: it mines transcripts written on
        other machines, where this host's sink path decides nothing, so it
        matches both shapes textually and resolves nothing."""

        called = re.compile(r"state_root\.([a-z_]+)\(")
        for relative in ("scripts/cutcheck.py", "scripts/ui.py",
                         "scripts/isolate.py", "tools/live_sweep_e2e.py"):
            with self.subTest(relative):
                source = (ROOT / relative).read_text(encoding="utf-8")
                names = sorted(set(called.findall(source)))
                self.assertTrue(names, relative)
                for name in names:
                    self.assertTrue(
                        callable(getattr(state_root, name, None)),
                        "{0} calls state_root.{1}".format(relative, name),
                    )
        # It may name the owner in a comment -- that is the one-owner law --
        # but it neither imports it nor calls it.
        trace_source = (ROOT / "scripts" / "trace.py").read_text(encoding="utf-8")
        self.assertNotIn("import state_root", trace_source)
        self.assertFalse(called.findall(trace_source))
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
        remove_repo_tree(cls.scratch_root)

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
        """A directory a span leaves behind, written by git rather than by pytest.

        The shape it stands for is a runner emitting a report directory --
        `python3 -m pytest --junitxml=probe_dir/r.xml ...` was the spelling
        here, and it wrote `probe_dir/` only on a host with pytest installed.
        No CI leg installs anything, so that span wrote nothing on all nine of
        them and this node failed there while passing here. `checkout-index`
        writes an indexed file under a prefix it creates, and needs nothing
        the copy does not already need: the copy is a git clone.
        """

        wrote = self._wrote("git checkout-index --prefix=probe_dir/ LICENSE")
        self.assertIn("probe_dir/", wrote)

    def test_an_ignored_path_is_reported_and_the_bare_spelling_would_miss_it(self):
        """`.pytest_cache/` is the shape found on disk, and it is ignored here.

        The guard against anyone shortening the reading back to a bare `git
        status --porcelain`: that spelling returns nothing with the directory
        sitting in the copy, so it is silently vacuous against the one leak
        that motivated the check.

        The directory is the one pytest leaves; the span that makes it is git,
        for the reason the node above states. The name has to stay an ignored
        one -- an unignored path here would leave both nodes reading the same
        thing, and the bare-spelling assertion below would pass vacuously
        against a status that is empty for no reason at all.
        """

        wrote = self._wrote("git checkout-index --prefix=.pytest_cache/ LICENSE")
        self.assertIn(".pytest_cache/", wrote)
        bare = cutcheck._git(["status", "--porcelain"], self.tree)
        # Anything else standing in this reading is the copy arriving short of
        # the revision, which is a fact about the checkout and not about the
        # spelling. The copy's own path is named because the host that showed
        # this is one nobody here can run: a `D` line under a path length no
        # other entry reaches is the checkout hitting a limit of that host's.
        self.assertEqual(
            bare.stdout,
            "",
            "the bare spelling would have missed it; copy at {} chars: {}".format(
                len(str(self.tree)), self.tree
            ),
        )

    def test_the_next_span_is_not_blamed_for_the_previous_spans_write(self):
        first = self._wrote("git diff --output=inside.txt HEAD~1 HEAD")
        self.assertEqual(first, ["inside.txt"])
        self.assertEqual(self._wrote("git log -1 --format=%H"), [])

    def test_the_clone_primes_its_own_arrival_state_and_reads_clean(self):
        # A checkout an eol rule or a filter left dirty is the copy's arrival
        # state, not the first span's doing.
        self.assertIn(str(self.tree), cutcheck._TREE_STATE)
        self.assertEqual(cutcheck._mutations(self.tree), [])


# Every call in this module that hands a command string to a subprocess.
# `cutcheck._commands` and its neighbours parse a string and start nothing, so
# the pytest spellings they are handed sit outside this reading on purpose:
# what CI cannot run is only what CI is asked to run.
SPAN_EXECUTORS = ("_wrote", "_run_once", "_exit_code")

# What a span this module runs may name. Frozen sets, never a probe of the
# host: `importlib.util.find_spec("pytest")` answers PRESENT wherever pytest
# is installed and ABSENT on every CI leg, so a check resting on it agrees
# with whichever host it is asked on and is silent exactly where the defect
# lives. `sys.stdlib_module_names` is 3.10 and later while this repository's
# floor is 3.9, so reading that would split the verdict by leg instead.
# The search heads are admitted because they are the one head `_run_once`
# never spawns: a `grep` span is decided by cutcheck's own matcher, so it
# needs no program CI would have to install -- which is the fact
# `SearchSpanMatcherTest` grades, and the reason its spans may stand here.
SPAN_PROGRAMS = frozenset({"git", "python3"} | set(cutcheck.SEARCH_HEADS))
SPAN_MODULES = frozenset({"unittest"})


def span_requirements(command):
    """What running this command string needs, as ``(kind, name)`` pairs.

    The program it names, and the module it hands an interpreter after
    ``-m``. Read out of the string rather than off the host, because the host
    running this test is not the host the reading is about.
    """

    try:
        argv = shlex.split(command)
    except ValueError:
        return []
    if not argv:
        return []
    needs = [("program", Path(argv[0]).name)]
    for index in range(1, len(argv)):
        token = argv[index]
        if token == "-m":
            if index + 1 < len(argv):
                needs.append(("module", argv[index + 1]))
            break
        if not token.startswith("-"):
            # the program's own arguments start here, and `-m` past this point
            # belongs to the program rather than to an interpreter
            break
    return needs


def executed_spans(tree):
    """``(lineno, command)`` for every literal span a parsed module runs.

    A span assembled at run time is outside this reading; every span this
    module runs today is written out at its call site, and the vacuity node
    below is what keeps saying so.
    """

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", None)
        if called not in SPAN_EXECUTORS:
            continue
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            yield first.lineno, first.value


class SpanDependencyTest(unittest.TestCase):
    """No span this module runs needs anything a bare CI runner lacks.

    Nine legs -- three interpreters across three operating systems -- install
    nothing past the interpreter, so a span naming a pip package writes
    nothing there and every assertion about what it wrote goes red. The defect
    is invisible on a developer machine, where the package is installed and
    the node is green; that is how two of them lived here through several
    passes. Caught by reading, because the alternative -- importing the name
    to see whether it resolves -- answers about the host doing the asking.
    """

    def setUp(self):
        source = Path(__file__).resolve()
        self.spans = list(
            executed_spans(ast.parse(source.read_text(encoding="utf-8")))
        )

    def test_the_reading_sees_the_spans_it_exists_to_grade(self):
        """An empty reading passes the node below for free; this is what stops it."""

        commands = [command for _, command in self.spans]
        self.assertTrue(commands, "no span was found to check")
        self.assertIn("git checkout-index --prefix=probe_dir/ LICENSE", commands)
        self.assertIn("git checkout-index --prefix=.pytest_cache/ LICENSE", commands)

    def test_no_span_names_a_program_or_module_outside_the_standard_set(self):
        allowed = {"program": SPAN_PROGRAMS, "module": SPAN_MODULES}
        self.assertEqual(
            [
                "line {}: {} {!r} in {!r}".format(lineno, kind, name, command)
                for lineno, command in self.spans
                for kind, name in span_requirements(command)
                if name not in allowed[kind]
            ],
            [],
            "a span here needs something CI does not install",
        )

    def test_the_reading_reports_the_spellings_that_were_here(self):
        """The can-fail direction, on the two shapes this node was cut for."""

        self.assertIn(
            ("module", "pytest"),
            span_requirements(
                "python3 -m pytest --junitxml=probe_dir/r.xml tests/test_installer.py"
            ),
        )
        self.assertIn(("program", "pytest"), span_requirements("pytest tests"))
        self.assertNotIn(
            ("module", "pytest"),
            span_requirements("git checkout-index --prefix=probe_dir/ LICENSE"),
        )


def rmtree_calls(tree):
    """Every ``shutil.rmtree`` in a parsed module, with its ``ignore_errors``.

    Three spellings, because they silence the same thing: the call itself, and
    the call deferred through ``addCleanup`` or ``addClassCleanup``, where the
    third positional is ``ignore_errors`` and reads as a bare ``True`` at the
    call site. The class-scoped spelling is here because it was missing: two
    swallowing removals reached the tree behind it, one of them over a full
    clone of this repository.
    """

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr == "rmtree":
            yield node, node.args[1:], node.keywords
        elif (
            node.func.attr in ("addCleanup", "addClassCleanup")
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

        Read from source across every test module, so it covers every removal
        the suite performs rather than the two a search happened to name. This
        module alone was the earlier scope, and three swallowing removals sat
        in two others -- one over a full clone of this repository -- where the
        reading could not reach them.
        """

        modules = sorted(Path(__file__).resolve().parent.glob("*.py"))
        self.assertTrue(modules, "no test module was found to read")
        swallowing, checked = [], 0
        for source in modules:
            calls = list(rmtree_calls(ast.parse(source.read_text(encoding="utf-8"))))
            checked += len(calls)
            swallowing.extend(
                "{}:{}".format(source.name, node.lineno)
                for node, rest, keywords in calls
                if swallows(rest, keywords)
            )
        self.assertTrue(checked, "no shutil.rmtree call was found to check")
        self.assertEqual(
            swallowing, [], "these removals discard the failure they should report"
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
    case.addCleanup(remove_repo_tree, base)
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
    """Where the copies land: the system temp directory, and nowhere the target
    decides.

    Placement inside the target's own git common dir put the copies beside the
    object store a clone hardlinks from, which is faster, and made the whole
    tool unusable on Windows: the copy's paths are the target's path plus
    `.git/cutcheck-scratch/.cutcheck-XXXXXXXX/<rev>/` plus the deepest path in
    the revision, and a 183-character worktree root took `git clone` past
    MAX_PATH on its own template copy -- which `core.longpaths=true` does not
    cover. Every invocation from that tree exited 2 before grading anything.

    So the length of a scratch path is now a fact about the host's temp
    directory rather than about the tree being graded, and speed gives way to
    running at all.
    """

    def setUp(self):
        self.main, self.linked = placement_repo(self)

    def _root(self, origin):
        root = cutcheck._scratch_root(origin)
        self.assertIsNotNone(root, "no scratch root was placed for {}".format(origin))
        self.addCleanup(remove_repo_tree, root)
        return root.resolve()

    def test_the_root_lands_under_the_system_temp_directory(self):
        for origin in (self.main, self.linked):
            with self.subTest(origin=origin.name):
                self.assertEqual(
                    self._root(origin).parent,
                    Path(tempfile.gettempdir()).resolve(),
                )

    def test_no_copy_lands_inside_the_tree_being_graded(self):
        for origin in (self.main, self.linked):
            with self.subTest(origin=origin.name):
                root = self._root(origin)
                self.assertNotIn(origin.resolve(), root.parents)

    def test_the_scratch_path_is_no_longer_the_targets_path_plus_a_suffix(self):
        """The MAX_PATH regression, stated as the length it broke on.

        A root derived from the tree grows with it; this one does not, so the
        183-character worktree that could clone nothing is the same length here
        as a two-character one.
        """

        deep = Path(tempfile.mkdtemp(prefix="cutcheck-deep-"))
        self.addCleanup(remove_repo_tree, deep)
        long_tree = deep / ("d" * 60) / ("e" * 60) / ("f" * 40)
        long_tree.mkdir(parents=True)
        # Both sides raw: the claim is that the target's path length does not
        # reach the scratch path, so both spellings must come from the same
        # mkdtemp. Resolving one side compares two spellings of the temp root
        # instead -- an 8.3 TEMP component on Windows runners and macOS's
        # /var -> /private/var symlink each made only the resolved side longer.
        near = cutcheck._scratch_root(self.main)
        self.assertIsNotNone(near, "the near tree got no scratch root")
        self.addCleanup(remove_repo_tree, near)
        far = cutcheck._scratch_root(long_tree)
        self.assertIsNotNone(far, "a deep tree got no scratch root")
        self.addCleanup(remove_repo_tree, far)
        self.assertEqual(len(str(near)), len(str(far)))

    def test_each_invocation_gets_a_root_of_its_own(self):
        # Two cuts running at once share the directory and never the tree.
        first, second = self._root(self.main), self._root(self.linked)
        self.assertNotEqual(first, second)
        self.assertEqual(first.parent, second.parent)

    def test_a_clone_into_the_scratch_root_carries_the_revisions_history(self):
        """What the placement still has to buy: a copy that is a clone.

        Hardlinking was the old placement's argument and it is gone with it --
        the temp directory may be another volume, and a full object copy there
        is correct and slower. What may not be given up is history: an oracle
        reading a copy with no `.git` reads whichever repository encloses it.
        """

        root = self._root(self.linked)
        tree = cutcheck._scratch_tree("HEAD", self.linked, root)
        self.assertIsNotNone(tree, "no scratch tree was cloned")
        self.assertTrue((tree / ".git").exists(), "the copy carries no history")

    def test_the_module_names_no_directory_inside_the_target_any_more(self):
        source = (ROOT / "scripts" / "cutcheck.py").read_text(encoding="utf-8")
        self.assertNotIn("cutcheck-scratch", source)
        self.assertNotIn("git-common-dir", source)


class BytecodeAdvisoryTest(unittest.TestCase):
    """Importing a package writes bytecode, and that is a spelling note.

    A python oracle that imports anything writes `__pycache__/` into the copy,
    and the delta reading convicted the first one graded as `unconfined-oracle`
    -- an exit-setting class whose repair, `-B`, is stated in no skill, no
    oracle policy and no report. What a copy writes back into itself is the
    hazard that class is for; bytecode is the interpreter's own cache, lands
    inside the copy, and is answered by a flag. So the report says the flag.
    """

    def _classes(self, mutated):
        """Graded through a ticket whose span is a process, because the delta is.

        `cutcheck-root-gate/00-root.01` was the vehicle until the search heads
        stopped being processes. `_MUTATED` is filled where a span was run, so
        a `grep` span -- answered in this interpreter now, and writing nothing
        by construction -- leaves a stubbed `_mutations` with nothing to be
        read from, and all three assertions below went quiet at once. The
        subject here is what a span wrote into the copy, so the vehicle is a
        span that can still write one.
        """

        ticket = FIXTURES / "cutcheck-git-graded" / "01-git-graded.md"
        cutcheck._EXIT_CACHE.clear()
        with mock.patch.object(cutcheck, "_mutations", lambda tree: list(mutated)):
            findings = cutcheck._check_ticket(ticket, ROOT, None, {})
        return findings, [klass for _, _, klass, _ in findings]

    def test_bytecode_alone_is_advisory_and_names_the_flag_that_answers_it(self):
        findings, classes = self._classes(["tests/__pycache__/"])
        self.assertIn(cutcheck.BYTECODE_WRITTEN, classes, findings)
        self.assertNotIn(cutcheck.UNCONFINED_ORACLE, classes, findings)
        detail = [f[3] for f in findings if f[2] == cutcheck.BYTECODE_WRITTEN][0]
        self.assertIn("tests/__pycache__/", detail)
        self.assertIn("-B", detail)

    def test_the_advisory_class_never_sets_the_exit_status(self):
        self.assertIn(cutcheck.BYTECODE_WRITTEN, cutcheck.ADVISORY)

    def test_anything_else_the_span_wrote_is_still_the_exit_setting_class(self):
        findings, classes = self._classes(["scratch.txt"])
        self.assertIn(cutcheck.UNCONFINED_ORACLE, classes, findings)
        self.assertNotIn(cutcheck.BYTECODE_WRITTEN, classes, findings)

    def test_a_span_writing_both_is_reported_for_both(self):
        findings, classes = self._classes(["tests/__pycache__/", "scratch.txt"])
        self.assertIn(cutcheck.UNCONFINED_ORACLE, classes, findings)
        self.assertIn(cutcheck.BYTECODE_WRITTEN, classes, findings)
        wrote = [f[3] for f in findings if f[2] == cutcheck.UNCONFINED_ORACLE][0]
        self.assertIn("scratch.txt", wrote)
        self.assertNotIn("__pycache__", wrote)


class SharedScratchHarnessTest(unittest.TestCase):
    """What the module's own grading harness may and may not do to the tool.

    Every grading here but three runs `main` in this process against copies
    the whole module shares, which is what turns 231 clones of a 78M
    repository into 5. Three things have to stay true for that to be a
    measurement of the tool rather than of a stub: the patches are scoped to
    the call, the reports are values, and the shared root is this process's own.
    """

    def test_the_harness_leaves_the_real_scratch_lifecycle_in_place(self):
        """The two classes next door grade the real removal, so they must reach it.

        `ScratchCleanupReportingTest` and `ScratchRootPlacementTest` assert on
        `_scratch_root` and `_remove_scratch_root` themselves. A module-wide
        patch -- a `setUpModule` that starts one and never stops it -- would
        leave both of them grading a lambda and passing, so the harness patches
        inside the call it grades and nowhere else. Read after a grading, which
        is when a leaked patch would still be standing.
        """

        before = (cutcheck._scratch_root, cutcheck._remove_scratch_root)
        run_cutcheck("cutcheck-clean")
        self.assertEqual(
            (cutcheck._scratch_root, cutcheck._remove_scratch_root), before
        )
        for name, func in zip(("_scratch_root", "_remove_scratch_root"), before):
            with self.subTest(function=name):
                self.assertEqual(func.__name__, name)
                self.assertEqual(func.__module__, cutcheck.__name__)

    def test_two_readings_of_one_pair_are_one_grading_and_two_values(self):
        """A memoised report is handed out by copy, so no caller can spend it.

        The rewrite is the assertion. Two callers holding one object is a
        report the second one reads after the first edited it, and 41 call
        sites read this dictionary.
        """

        first, second = run_cutcheck("cutcheck-clean"), run_cutcheck("cutcheck-clean")
        self.assertIsNot(first, second)
        self.assertEqual(
            (first.returncode, first.stdout, first.stderr),
            (second.returncode, second.stdout, second.stderr),
        )
        first.stdout = "a caller rewrote its own copy"
        self.assertNotEqual(run_cutcheck("cutcheck-clean").stdout, first.stdout)

    def test_the_shared_root_is_this_processs_own_inside_the_tools_place(self):
        """Two suites at once share the directory and never a tree.

        The place is the host's temp directory, which every process on the
        machine shares, so a fixed name here would be two concurrent runs
        writing one tree. It is a `mkdtemp` of the tool's own making instead,
        and the neighbour built below is what says so rather than the prefix.
        """

        root = shared_root()
        self.assertEqual(shared_root(), root, "a second root is a second pair of clones")
        self.assertTrue(root.is_dir(), root)
        self.assertEqual(root.resolve().parent, Path(tempfile.gettempdir()).resolve())
        neighbour = cutcheck._scratch_root(ROOT)
        self.addCleanup(remove_repo_tree, neighbour)
        self.assertEqual(neighbour.resolve().parent, root.resolve().parent)
        self.assertNotEqual(neighbour, root)


class ScopeOpenLiteralTest(unittest.TestCase):
    """What an objective says it deletes, moves or renames.

    A literal is specific enough to be pinned: a path, a name carrying a
    separator, a constant. An ordinary word is not one, because every file in
    the tree holds ordinary words and a finding against all of them says
    nothing about this cut.
    """

    def test_scope_open_reads_a_deleted_path_and_the_name_it_ends_in(self):
        """The pin is usually on the basename, never on the path that held it.

        `scripts/tickets.py` spells the engine as a set member; nothing outside
        the library spells the directory it lives in. Reading only the path
        would find no pin and report a clean cut.
        """

        self.assertEqual(
            cutcheck._literals(
                "The item deletes the skill directory `skills/engines/orch-compose`."
            ),
            ["skills/engines/orch-compose", "orch-compose"],
        )

    def test_scope_open_reads_a_renamed_name_that_is_no_path_at_all(self):
        self.assertEqual(
            cutcheck._literals(
                "The item renames the role profile `orch-planner` to `orch-lead`."
            ),
            ["orch-planner", "orch-lead"],
        )

    def test_scope_open_reads_no_literal_out_of_an_ordinary_word(self):
        self.assertEqual(cutcheck._literals("The item deletes the gate."), [])

    def test_scope_open_leaves_a_denied_removal_alone(self):
        """The question `_scope_closure` asks of a write verb, asked of this one."""

        self.assertEqual(
            cutcheck._literals(
                "The item never deletes `skills/engines/orch-compose`."
            ),
            [],
        )


# What `cutcheck-scope-open`'s first ticket takes away, and every file the
# baseline revision pins it in. Read at the baseline, which is a frozen commit,
# so this table is a fact about that revision and not about today's tree: the
# engine name is a member of `ENGINE_EXECUTORS` in `scripts/tickets.py` and of
# three suites' expectations; the role name is in one transcript fixture and
# two suites. Eleven under-supplied grants in the 2026-08-16 build were exactly
# this shape -- a constant or a fixture pinning a name the item was cut to
# remove, from outside the item's own scope.
SCOPE_OPEN_PINS = {
    "scripts/tickets.py": "orch-compose",
    "tests/test_contracts.py": "orch-compose",
    "tests/test_roles.py": "orch-compose",
    "tests/test_installer.py": "orch-planner",
    "tests/test_live_profiles.py": "orch-planner",
    "tests/fixtures/transcripts/-Users-dmcinerney-tools-alpha/"
    "11111111-1111-4111-8111-111111111111/subagents/agent-aa12.meta.json":
        "orch-planner",
}
SCOPE_OPEN_CONSTANT = "scripts/tickets.py"
SCOPE_OPEN_FIXTURE = next(
    path for path in SCOPE_OPEN_PINS if path.startswith("tests/fixtures/")
)


class ScopeOpenTest(unittest.TestCase):
    """A cut closes over what it takes away, or the pin breaks unowned.

    Family 3 asked one direction of the question -- does the grant cover what
    the item writes -- and the other direction is where the 2026-08-16 build
    lost eleven items: the grant covered the file being changed and not the
    test, the constant or the fixture that pinned the name being changed away.
    Nothing failed at the cut; each item failed in flight, against a pin its
    executor was not licensed to repair.
    """

    def setUp(self):
        self.result = run_cutcheck("cutcheck-scope-open")
        self.lines = [
            line
            for line in reported(self.result, cutcheck.FAMILY_3)
            if cutcheck.SCOPE_OPEN in line
        ]

    def _pins(self):
        pins = {}
        for line in self.lines:
            where, _, literal = line.split(": ")[3].partition(" pins ")
            self.assertNotIn(where, pins, "one finding per pinning file")
            pins[where] = literal
        return pins

    def test_scope_open_names_each_pinning_file_once_and_says_what_it_pins(self):
        for line in self.lines:
            self.assertTrue(line.startswith("01-open: "), line)
        self.assertEqual(self._pins(), SCOPE_OPEN_PINS, self.result.stdout)

    def test_scope_open_reaches_a_constant_in_scripts_and_a_fixture_in_tests(self):
        """The two kinds of pin: one a script states, one a fixture holds.

        Named separately from the table above because they are the claim --
        that the search is not one directory's -- rather than a row of it.
        """

        pins = self._pins()
        self.assertEqual(pins.get(SCOPE_OPEN_CONSTANT), "orch-compose", pins)
        self.assertEqual(pins.get(SCOPE_OPEN_FIXTURE), "orch-planner", pins)

    def test_scope_open_is_silent_where_the_write_scope_carries_the_pins(self):
        """The same objective, granted the pinning files, and no finding.

        The can-fail direction of the whole class: a check that reported the
        removal itself would report this ticket too, and a cut nobody can
        satisfy is a cut nobody reads.
        """

        self.assertEqual(
            [line for line in self.lines if line.startswith("02-carried")],
            [],
            self.result.stdout,
        )

    def test_scope_open_sets_the_exit_status(self):
        self.assertNotIn(cutcheck.SCOPE_OPEN, cutcheck.ADVISORY)
        self.assertEqual(cutcheck.FAMILY_OF[cutcheck.SCOPE_OPEN], cutcheck.FAMILY_3)
        self.assertNotEqual(self.result.returncode, 0, self.result.stdout)

    def test_scope_open_says_nothing_about_a_cut_that_takes_nothing_away(self):
        """Every other fixture set in this suite, and the affirmative one first.

        The class runs over an objective's ordinary prose, and prose is where a
        false positive comes from. A set that removes nothing states nothing
        for this to find, whatever else it is reported for.
        """

        for run in fixture_sets():
            if run == "cutcheck-scope-open":
                continue
            with self.subTest(run=run):
                self.assertNotIn(cutcheck.SCOPE_OPEN, run_cutcheck(run).stdout)


class ScopeOpenWordLiteralTest(unittest.TestCase):
    """An enum member or a set member is a word, and the objective still names it.

    The literal kinds the class exists for are a path, a skill name, an enum
    member and a set member. The first two carry a separator; a status like
    `limited` or an independence value like `gate` carries none, and a bare
    word would name the whole tree. A span the objective sets in backticks is
    a literal on the author's word, and the tree's ordinary uses of the same
    word -- `delegate` for `gate`, `orch-composer` for `orch-compose` -- are
    told apart at the pin, which reads whole tokens.
    """

    def test_scope_open_reads_a_backticked_word_as_a_literal(self):
        self.assertEqual(
            cutcheck._literals(
                "Remove the status `limited` from the ticket lifecycle enum."
            ),
            ["limited"],
        )
        self.assertEqual(
            cutcheck._literals("Remove `gate` from the independence set."),
            ["gate"],
        )
        self.assertEqual(
            cutcheck._literals("Remove the status limited from the enum."), []
        )

    def test_scope_open_pins_whole_tokens_only(self):
        self.assertTrue(cutcheck._pins("gate", 'independence: "gate"'))
        self.assertTrue(cutcheck._pins("gate", "the gate."))
        self.assertFalse(cutcheck._pins("gate", "delegate to the aggregate"))
        self.assertTrue(cutcheck._pins("orch-compose", '{"orch-compose", "x"}'))
        self.assertTrue(
            cutcheck._pins("orch-compose", "skills/engines/orch-compose/SKILL.md")
        )
        self.assertFalse(cutcheck._pins("orch-compose", "orch-composer"))
        self.assertTrue(cutcheck._pins("friction.py", "run scripts/friction.py."))
        self.assertFalse(cutcheck._pins("friction.py", "friction.pyc"))
        self.assertTrue(cutcheck._pins("LIMITED", "Status.LIMITED"))

    def test_scope_open_reports_the_word_pin_and_not_the_word_inside_another(self):
        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            (tree / "tests").mkdir()
            (tree / "tests" / "pin.py").write_text(
                'INDEPENDENCE = {"gate", "checker"}\n', encoding="utf-8"
            )
            (tree / "tests" / "noise.py").write_text(
                "def delegate(): return aggregate()\n", encoding="utf-8"
            )
            (tree / "tests" / "longer.py").write_text(
                'NAMES = {"orch-composer"}\n', encoding="utf-8"
            )
            objective = (
                "Remove `gate` from the independence set and delete the skill "
                "`orch-compose`."
            )
            self.assertEqual(
                cutcheck._scope_open({"write_scope": []}, objective, tree),
                [(cutcheck.SCOPE_OPEN, "tests/pin.py pins gate")],
            )
            self.assertEqual(
                cutcheck._scope_open(
                    {"write_scope": ["tests/pin.py"]}, objective, tree
                ),
                [],
            )


class SearchSpanMatcherTest(unittest.TestCase):
    """A search span is decided by this tool's own matcher, never by a program
    on PATH.

    `grep` is a head this tool extracts, and it used to be a head this tool
    executed. Executing it made the verdict a fact about the host rather than
    about the cut: this same tree, this same command, exit 0 from Git Bash --
    whose PATH carries GNU grep -- and exit 1 with twenty `unrunnable-oracle`
    findings from PowerShell, whose PATH does not. The displaced findings were
    the ones each fixture set exists to pin, so the failure text read exactly
    like a content regression.

    Answered in the interpreter that is already running, the same span reads
    the same wherever it is read, and no fixture oracle had to be respelled to
    get there.
    """

    def setUp(self):
        # `_run_once` primes what a tree was carrying, and these probes read the
        # checkout itself rather than a scratch copy; the entry goes with them.
        self.addCleanup(cutcheck._MUTATED.clear)
        self.addCleanup(cutcheck._TREE_STATE.pop, str(ROOT), None)

    def ran(self, command):
        return cutcheck._run_once(command, ROOT)

    def test_no_process_is_started_for_a_search_span(self):
        """The claim itself, and the one node that can only pass by holding it.

        Read by refusing the spawn rather than by emptying PATH: what an empty
        PATH means is the host's own answer -- `execvp` falls back to a
        confstr default on some libcs -- so a node resting on it grades the
        libc. A `subprocess.run` that raises grades this module.
        """

        def refuse(*args, **kwargs):
            raise AssertionError("a search span reached subprocess.run: {}".format(args))

        with mock.patch.object(cutcheck.subprocess, "run", refuse):
            self.assertEqual(self.ran('grep -n "family 1" scripts/cutcheck.py'), 0)
            self.assertEqual(
                self.ran('grep -rn "zzqq-never-written" install.py'), cutcheck.NO_MATCH
            )

    def test_the_status_is_the_search_convention_and_not_a_reading_of_its_own(self):
        """0 selected, 1 nothing selected, 2 nothing this could read.

        The middle one is load-bearing beyond arithmetic: `_discrimination`
        reads `NO_MATCH` from a search head as `no-hits-both-revisions` and
        anything else as `fails-both-revisions`, so a matcher returning its own
        numbers would rename two finding classes.
        """

        self.assertEqual(self.ran('grep -n "SCRIPT_NAMES" install.py'), 0)
        self.assertEqual(
            self.ran('grep -n "zzqq-never-written" install.py'), cutcheck.NO_MATCH
        )
        self.assertEqual(self.ran('grep -n "SCRIPT_NAMES" no-such-file.txt'), 2)

    def test_a_directory_is_read_where_the_span_says_recurse_and_not_otherwise(self):
        self.assertEqual(self.ran('grep -rn "unrunnable-oracle" scripts/'), 0)
        self.assertEqual(self.ran('grep -n "unrunnable-oracle" scripts/'), 2)

    def _two_trees(self):
        """A copy, and a file standing beside it that the copy does not hold.

        Built rather than pointed at, because the claim is about containment
        and a path that merely does not exist proves nothing about it: the
        first spelling of this node named `../install.py` and `/etc/hosts`,
        neither of which resolves on a Windows host, so a matcher reading
        anything it was pointed at still returned 2 for both -- the node could
        not fail on the very claim it stood for. Here the outside file exists
        and holds the token, so a matcher that reads it answers 0.
        """

        base = Path(tempfile.mkdtemp(prefix=".cutcheck-search-copy-"))
        self.addCleanup(shutil.rmtree, str(base))
        copy = base / "copy"
        copy.mkdir()
        (copy / "inside.txt").write_bytes(b"one SCRIPT_NAMES line\n")
        (base / "outside.txt").write_bytes(b"one SCRIPT_NAMES line\n")
        return copy, base / "outside.txt"

    def test_an_operand_outside_the_copy_is_no_operand_at_all(self):
        """The copy is the whole of what a span reads, rooted or climbing.

        Shelling out left this to the tool: a span naming `/etc/hosts` read
        `/etc/hosts`. Deciding it here is where the containment can be held, so
        it is held -- and graded against a file that exists, holds the token,
        and stands one step outside the copy, so the only way to 2 is refusal.
        """

        copy, outside = self._two_trees()
        self.assertEqual(cutcheck._run_once('grep -n "SCRIPT_NAMES" inside.txt', copy), 0)
        self.assertEqual(cutcheck._run_once('grep -n "SCRIPT_NAMES" ../outside.txt', copy), 2)
        self.assertEqual(
            cutcheck._run_once('grep -n "SCRIPT_NAMES" {}'.format(shlex.quote(str(outside))), copy),
            2,
        )

    def test_the_status_agrees_with_grep_where_the_option_set_reaches(self):
        """The numbers are grep's own, on the spans the closed set admits.

        Three readings a first matcher got wrong, each measured against GNU
        grep 3.0 before it was fixed: `grep -r PATTERN` with no operand
        searches the working directory (2 here, 0 or 1 there); `-q` with a
        selected line exits 0 even where an operand was unreadable, which
        grep's manual states as the one exception to its status convention
        (2 here, 0 there); and `-w` asks for no word constituent on either
        side of the match rather than a `\\b`, which for a pattern whose own
        edge is not a word character -- `-w -- -x` -- never matched here and
        matches there.
        """

        copy, _ = self._two_trees()
        (copy / "edge.txt").write_bytes(b" a -x b\n")
        self.assertEqual(cutcheck._run_once('grep -rn "SCRIPT_NAMES"', copy), 0)
        self.assertEqual(cutcheck._run_once('grep -rn "zzqq-never-written"', copy), cutcheck.NO_MATCH)
        self.assertEqual(cutcheck._run_once('grep -n "SCRIPT_NAMES"', copy), 2)
        self.assertEqual(cutcheck._run_once('grep -q "SCRIPT_NAMES" no-such.txt inside.txt', copy), 0)
        self.assertEqual(cutcheck._run_once('grep -n "SCRIPT_NAMES" no-such.txt inside.txt', copy), 2)
        self.assertEqual(cutcheck._run_once('grep -wn -- "-x" edge.txt', copy), 0)
        # The underscore is a word constituent, so `SCRIPT` inside
        # `SCRIPT_NAMES` is not a word and `line` is.
        self.assertEqual(cutcheck._run_once('grep -wn "SCRIPT" inside.txt', copy), cutcheck.NO_MATCH)
        self.assertEqual(cutcheck._run_once('grep -wn "line" inside.txt', copy), 0)

    def test_an_option_the_matcher_cannot_read_is_extracted_by_nobody(self):
        """A guessed option would decide a cut from a reading nothing checked.

        Refused at extraction, so the criterion reports the gap a shell-headed
        span reports, which is advisory and settles nothing -- rather than a
        status invented for an option this tool never implemented.
        """

        frame = "1. **The installer lists the script.** `{}` returns a line."
        self.assertEqual(
            cutcheck._commands(frame.format('grep -rn "SCRIPT_NAMES" install.py')),
            ['grep -rn "SCRIPT_NAMES" install.py'],
        )
        self.assertEqual(
            cutcheck._commands(frame.format('grep -A2 "SCRIPT_NAMES" install.py')), []
        )

    def test_every_search_span_the_fixture_corpus_states_is_readable_here(self):
        """The corpus is what this repairs, so the corpus is what says it holds.

        A span the matcher cannot read becomes an extraction gap instead of a
        verdict, which is a quieter regression than the one being repaired.
        Read off the fixture tree rather than off a list, so a set added after
        this was written is graded by it too.
        """

        seen, unreadable = [], []
        for path in sorted(FIXTURES.rglob("*.md")):
            for match in cutcheck.BACKTICK_RE.finditer(path.read_text(encoding="utf-8")):
                span = " ".join(match.group(1).split())
                head = span.split()[:1]
                if not head or head[0] not in cutcheck.SEARCH_HEADS:
                    continue
                seen.append(span)
                try:
                    argv = shlex.split(span)
                except ValueError:
                    argv = []
                if not argv or cutcheck._search_span(argv) is None:
                    unreadable.append("{}: {}".format(path.name, span))
        self.assertEqual(unreadable, [])
        self.assertGreater(len(seen), 20, "an empty reading grades nothing")


if __name__ == "__main__":
    if "--record" in sys.argv:
        record_verdicts()
    else:
        unittest.main()
