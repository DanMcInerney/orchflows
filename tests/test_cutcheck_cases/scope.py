"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck."""

from tests.test_cutcheck import *  # noqa: F401,F403
from scripts import cutcheck_scope

try:
    del load_tests
except NameError:
    pass

class ScopeOpenLiteralTest(unittest.TestCase):
    """What an objective says it deletes, moves or renames.

    A literal is specific enough to be pinned: a path, a name carrying a
    separator, a constant. An ordinary word is not one, because every file in
    the tree holds ordinary words and a finding against all of them says
    nothing about this cut.
    """

    def test_overlap_uses_the_same_slash_normalization_as_authorization(self):
        self.assertTrue(cutcheck_scope._overlaps("web\\src\\", "web/src/app.ts"))
        self.assertTrue(cutcheck_scope._overlaps("web/src/app.ts", "web\\src\\"))

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

    def test_reverse_scan_is_an_undeclared_scope_edge_advisory(self):
        self.assertEqual("undeclared-scope-edge", cutcheck.SCOPE_OPEN)
        self.assertIn(cutcheck.SCOPE_OPEN, cutcheck.ADVISORY)
        self.assertEqual(cutcheck.FAMILY_OF[cutcheck.SCOPE_OPEN], cutcheck.FAMILY_3)
        self.assertEqual(self.result.returncode, 0, self.result.stdout)

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
