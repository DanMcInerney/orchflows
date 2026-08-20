"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck."""

import types

from tests.test_cutcheck import *  # noqa: F401,F403

try:
    del load_tests
except NameError:
    pass

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

    def test_cutcheck_contract_imports_the_lower_format_owner_not_the_facade(self):
        source = (ROOT / "scripts" / "cutcheck_contract.py").read_text(encoding="utf-8")
        self.assertNotIn("from scripts.tickets import", source)
        self.assertNotIn("from tickets import", source)
        self.assertIn("tickets_format", source)

    def test_lower_policy_hooks_keep_their_portable_codes(self):
        from scripts import cutcheck_ticket

        inputs = types.ModuleType("scripts.tickets_inputs")
        scope = types.ModuleType("scripts.tickets_scope")
        inputs.grade_inputs = lambda **kwargs: {
            "findings": [{"code": "input-unresolved", "field": "Fixed inputs", "detail": "baseline"}],
        }
        scope.grade_scope = lambda **kwargs: {
            "findings": [{"code": "scope-owner-missing", "field": "mutations", "detail": "change:a.py"}],
        }
        text = "---\nid: T1\npack: orch-code-pack\n---\n"
        with mock.patch.dict(sys.modules, {
            "scripts.tickets_inputs": inputs,
            "scripts.tickets_scope": scope,
        }):
            findings = cutcheck_ticket._policy_findings(
                "T1", text, {"T1": text}, Path("baseline"), Path("head")
            )
        self.assertEqual(["input-unresolved", "scope-owner-missing"], [row[2] for row in findings])
        self.assertEqual(cutcheck.FAMILY_2, cutcheck.FAMILY_OF["input-unresolved"])
        self.assertEqual(cutcheck.FAMILY_3, cutcheck.FAMILY_OF["scope-owner-missing"])


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
