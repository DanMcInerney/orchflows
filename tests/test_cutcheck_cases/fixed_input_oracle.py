"""Cutcheck behavioral cases loaded explicitly by tests.test_cutcheck."""

from tests.test_cutcheck import *  # noqa: F401,F403

from scripts import tickets_input_producers, tickets_inputs  # noqa: E402
from scripts.tickets_format import canonical_json  # noqa: E402  the record's writer

try:
    del load_tests
except NameError:
    pass

# The acceptance an item names rather than states. Each value is what a
# `## Fixed inputs` record holds, and the criterion below names the record by
# its name and states no command at all -- the indirection this module grades.
ACCEPTANCE = (
    "python tools/validate.py; python tools/run_tests.py; "
    "python tools/run_serial_compat.py; python install.py --dry-run; "
    "git diff --check"
)
FOCUSED = "python tools/run_tests.py --scope scripts/cutcheck_search.py"

TICKET = """---
id: {id}
run: fixed-input-oracle
executor: {executor}
pack: orch-code-pack
independence: checker
depends_on: []
write_scope: [scripts/cutcheck_search.py]
mutations: [change:scripts/cutcheck_search.py]
excluded_actions: [vcs.push]
---

## Objective

The item extends the whole-suite reading in scripts/cutcheck_search.py.

## Fixed inputs

{inputs}

## Completion test

- {prose} | oracle: {oracle} | oracle_class: deterministic | provenance: authored-here
"""

# A policy record, spelled as this run's own `unit-oracle-policy` is: prose
# about which oracles a unit states, holding a required check inside it. The
# name is what a criterion cites; the value is what makes the citation
# dangerous to read from anywhere but the oracle field.
POLICY = (
    "A unit names its own focused oracles, and git diff --check, "
    "and tools/validate.py only where it edits rules/."
)

INPUT_LINE = '- input: {}'


def input_record(name, value):
    """One canonical literal Fixed-input line, spelled as the writer spells it."""

    return INPUT_LINE.format(
        canonical_json({"name": name, "type": "literal", "value": value})
    )


class InputRecordCutcheckCases:
    """Input-identity cases owned by the cutcheck policy seam."""

    def test_cutcheck_renders_the_shared_input_codes_unchanged(self):
        revision = tickets_input_producers.git_head()
        inputs = "\n".join((
            self.record("baseline", identity={"kind": "git-tree", "repo": "run-project", "revision": revision}),
            self.record("missing", identity={"kind": "git-path", "path": "absent-input-identity", "repo": "run-project", "revision": revision}),
        ))
        text = self.ticket(inputs, pack="orch-code-pack")
        expected = [item["code"] for item in tickets_inputs.grade_inputs(
            ticket_id="T", text=text, siblings={"T": text}, adapter_id="git",
        )["findings"]]
        rendered = cutcheck_ticket._policy_findings("T", text, {"T": text}, revision, revision)
        actual = [item[2] for item in rendered if item[2] in expected]
        self.assertEqual(expected, actual)

    def test_cutcheck_reports_pending_dependency_as_advisory(self):
        revision = tickets_input_producers.git_head()
        predecessor = self.ticket("", ticket_id="P")
        dependent = self.ticket(
            self.record("predecessor", identity={
                "kind": "ticket-section", "run": "run", "section": "Result", "ticket": "P",
            }),
            ticket_id="D", depends="[P]",
        )
        rendered = cutcheck_ticket._policy_findings(
            "D", dependent, {"D": dependent, "P": predecessor}, revision, revision,
        )
        codes = [item[2] for item in rendered]
        self.assertIn("ticket-result-not-terminal", codes)
        self.assertIn("ticket-result-not-terminal", cutcheck_ticket._contract.ADVISORY)


def graded(case, oracle, inputs, ticket_id="01-unit", executor="orch-tdd",
           prose="the item's acceptance holds"):
    """Every finding class cutcheck reports for one ticket holding this oracle.

    Written into a directory of its own so that `_check_ticket`'s sibling glob
    reads this ticket and nothing else, and graded against the harness's real
    baseline clone: the whole-suite reading resolves a target against a tree,
    so a fabricated tree would grade the fixture and not the rule.
    """

    directory = Path(tempfile.mkdtemp(prefix="cutcheck-indirection-"))
    # Strictly: this directory holds one file this process wrote, so a removal
    # that fails is a fact about the run and not noise to be swallowed.
    case.addCleanup(shutil.rmtree, str(directory))
    text = TICKET.format(
        id=ticket_id, executor=executor, oracle=oracle, prose=prose,
        inputs="\n".join(inputs),
    )
    path = directory / (ticket_id + ".md")
    # Bytes with LF: a text-mode write on Windows lands CRLF, and the section
    # reader would then hand every value a trailing carriage return.
    path.write_bytes(text.encode("utf-8"))
    siblings = {ticket_id: cutcheck._parse_frontmatter(text)}
    findings = cutcheck._check_ticket(path, shared_baseline_tree(), None, siblings)
    return [klass for _, _, klass, _ in findings]


class IndirectWholeSuiteValueTest(unittest.TestCase):
    """What a fixed input's literal value is read as, before any ticket."""

    def setUp(self):
        self.tree = shared_baseline_tree()

    def test_each_required_check_convicts_the_value_holding_it(self):
        for value in (
            "python tools/validate.py",
            "python tools/run_tests.py",
            "python tools/run_serial_compat.py",
            "python install.py --dry-run",
            "git diff --check",
            ACCEPTANCE,
        ):
            self.assertIsNotNone(
                cutcheck._whole_suite_value(value, self.tree), value
            )

    def test_a_bare_runner_and_a_discover_invocation_convict(self):
        # A whole module, named the way the baseline clone holds it: the
        # target reading resolves against that tree, so the module has to be
        # one the graded revision actually carries.
        for value in (
            "python3 -m unittest discover -s tests",
            "uv run --no-project python -m unittest tests.test_installer -v",
        ):
            self.assertIsNotNone(
                cutcheck._whole_suite_value(value, self.tree), value
            )

    def test_a_selected_run_of_the_shard_runner_is_not_whole_suite(self):
        """The carve-out this reading owns, and the reason it has to.

        `tools/run_tests.py` is a required check by name and a focused oracle
        with a selection on it, so the name alone decides nothing. A value
        naming what it runs -- through `--scope` or through a positional
        module -- is the oracle the unit policy asks a unit to state, and
        convicting it would convict every unit of this specification.
        """

        for value in (
            FOCUSED,
            "python tools/run_tests.py --scope scripts/a.py,scripts/b.py",
            "python tools/run_tests.py tests.test_cutcheck tests.test_tickets",
        ):
            self.assertIsNone(cutcheck._whole_suite_value(value, self.tree), value)

    def test_a_value_naming_no_check_at_all_is_not_whole_suite(self):
        for value in (
            "uv run --no-project python (bare python is a Windows Store stub)",
            "Item 6",
            "",
        ):
            self.assertIsNone(cutcheck._whole_suite_value(value, self.tree), value)


class FixedInputIndirectionTest(unittest.TestCase):
    """An oracle naming its acceptance instead of stating it."""

    def test_an_oracle_naming_the_acceptance_input_is_convicted(self):
        classes = graded(
            self,
            "run the `acceptance-as-runnable-checks` fixed input",
            [input_record("acceptance-as-runnable-checks", ACCEPTANCE)],
        )
        self.assertIn(cutcheck.WHOLE_SUITE_ORACLE, classes, classes)

    def test_the_same_oracle_naming_a_focused_input_is_not(self):
        classes = graded(
            self,
            "run the `focused-regression` fixed input",
            [input_record("focused-regression", FOCUSED)],
        )
        self.assertNotIn(cutcheck.WHOLE_SUITE_ORACLE, classes, classes)

    def test_only_the_input_the_criterion_names_is_read(self):
        """Both records stand in the section; the criterion names one."""

        inputs = [
            input_record("acceptance-as-runnable-checks", ACCEPTANCE),
            input_record("focused-regression", FOCUSED),
        ]
        self.assertIn(
            cutcheck.WHOLE_SUITE_ORACLE,
            graded(self, "run the `acceptance-as-runnable-checks` fixed input", inputs),
        )
        self.assertNotIn(
            cutcheck.WHOLE_SUITE_ORACLE,
            graded(self, "run the `focused-regression` fixed input", inputs),
        )

    def test_a_name_standing_inside_a_longer_word_names_nothing(self):
        classes = graded(
            self,
            "run the `focused-regression-suite` fixed input",
            [input_record("focused-regression", ACCEPTANCE)],
        )
        self.assertNotIn(cutcheck.WHOLE_SUITE_ORACLE, classes, classes)

    def test_a_name_cited_in_the_prose_half_is_not_an_oracle(self):
        """Where the name stands decides what it names.

        A criterion cites the policy it works under and states its own focused
        check. Policy prose holds commands -- this run's `unit-oracle-policy`
        states `git diff --check` inside its value -- so reading the whole
        criterion convicted the citation, and this class sets the exit status.
        An honest cut is refused by it, which is why the reading is the oracle
        field's alone.
        """

        classes = graded(
            self,
            "`{}`".format(FOCUSED),
            [input_record("unit-oracle-policy", POLICY)],
            prose="the item states the oracles unit-oracle-policy asks for",
        )
        self.assertNotIn(cutcheck.WHOLE_SUITE_ORACLE, classes, classes)

    def test_the_convicted_criterion_is_not_also_an_extraction_gap(self):
        """The oracle was read, so the gap it would otherwise be is closed.

        An extraction gap says no extractor recognized the oracle. This one
        was recognized -- through its record -- and reporting both would name
        one criterion twice for opposite reasons.
        """

        classes = graded(
            self,
            "run the `acceptance-as-runnable-checks` fixed input",
            [input_record("acceptance-as-runnable-checks", ACCEPTANCE)],
        )
        self.assertNotIn(cutcheck.EXTRACTION_GAP, classes, classes)

    def test_a_frozen_root_naming_its_acceptance_is_exempt(self):
        """A root's completion test is the acceptance, not an item's oracle.

        The five checks are the gate's row, and a root freezes that row. The
        finding is a unit's, so the exemption `_frozen_authority` already
        draws for write authority is drawn here too.
        """

        for ticket_id, executor in (
            ("00-root", "orch-decompose"),
            ("00-root.gate.verify", "orch-verify"),
        ):
            classes = graded(
                self,
                "run the `acceptance-as-runnable-checks` fixed input",
                [input_record("acceptance-as-runnable-checks", ACCEPTANCE)],
                ticket_id=ticket_id,
                executor=executor,
            )
            self.assertNotIn(cutcheck.WHOLE_SUITE_ORACLE, classes, ticket_id)

    def test_the_finding_still_sets_the_exit_status(self):
        """The class is family 1 and outside the advisory set, as it was."""

        self.assertEqual(
            cutcheck.FAMILY, cutcheck.FAMILY_OF[cutcheck.WHOLE_SUITE_ORACLE]
        )
        self.assertNotIn(cutcheck.WHOLE_SUITE_ORACLE, cutcheck.ADVISORY)


if __name__ == "__main__":
    unittest.main()
