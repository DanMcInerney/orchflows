"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck."""

from tests.test_cutcheck import *  # noqa: F401,F403

try:
    del load_tests
except NameError:
    pass

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
