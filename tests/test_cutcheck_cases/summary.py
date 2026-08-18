"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck."""

from tests.test_cutcheck import *  # noqa: F401,F403

try:
    del load_tests
except NameError:
    pass

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
