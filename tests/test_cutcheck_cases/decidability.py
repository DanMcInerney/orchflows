"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck."""

from tests.test_cutcheck import *  # noqa: F401,F403
from tests.test_cutcheck import _graded_with

try:
    del load_tests
except NameError:
    pass

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
        # and that no member standing beside it left with it. `shared-test-module`
        # joined later still, on those same terms, and `marker-only-relocation`
        # later again -- a joiner, never a survival.
        self.assertEqual(
            cutcheck.ADVISORY,
            frozenset(
                {
                    cutcheck.EXTRACTION_GAP,
                    cutcheck.COVERAGE_MAP_ABSENT,
                    cutcheck.VERDICT_IN_OUTPUT,
                    cutcheck.SYMLINK_IN_TREE,
                    cutcheck.BYTECODE_WRITTEN,
                    cutcheck.SCOPE_OPEN,
                    cutcheck.UNREAD_HALF,
                    cutcheck.SHARED_TEST_MODULE,
                    cutcheck.MARKER_ONLY_RELOCATION,
                    "ticket-result-not-terminal",
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
