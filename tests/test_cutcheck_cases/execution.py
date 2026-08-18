"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck."""

from tests.test_cutcheck import *  # noqa: F401,F403

try:
    del load_tests
except NameError:
    pass

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
