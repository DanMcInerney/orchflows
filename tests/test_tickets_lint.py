"""`tickets.py lint`: every grader at once, and `--fix` on the syntactic half.

One module rather than a case package: this shard's cases are all one
subject, and the tables case is here because the tables and the subcommand
that extends them land together.
"""

import json
import subprocess

from tests.test_tickets_issue_cases.common import *  # noqa: F401,F403
from scripts import tickets_commands, tickets_dispatch
from scripts.tickets_format import _parse_frontmatter
from tests.test_tickets_cases.admission_v1 import initialize_git_fixture

# One narrowed oracle: `python -m unittest` alone is the whole-suite finding,
# and a draft meant to carry exactly five defects may not carry a sixth.
NARROW_ORACLE = "`python -m unittest tests.test_thing.CaseTest.test_one`"
GOOD_CRITERION_NARROW = (
    f"the artifact has the requested value | oracle: {NARROW_ORACLE} "
    "| oracle_class: deterministic | provenance: authored-here"
)
DRAFT = """---
id: {tid}
run: testrun
status: pending
admission: v1:pending
cohort: v1:ticket:{tid}
executor: orch-tdd
pack: orch-code-pack
independence: gate
depends_on: []
write_scope: [scratch/{tid}.txt]
mutations: [change:scratch/{tid}.txt]
excluded_actions: [{excluded}]
isolation: {isolation}
bound: 30m
claimed_by:
claimed_at:
---

## Objective

{objective}

## Fixed inputs

- input: {{"identity":{{"kind":"git-tree","repo":"run-project","revision":"{baseline}"}},"name":"baseline","type":"identity"}}
- input: {inputs}

## Completion test

- {criterion}

## Return fields

status; result; changed_artifacts; verification; feedback; risks

## Result

## Verification

## Feedback

[]

## Risks

[]
"""

CANONICAL_SECOND_INPUT = '{"name":"question","type":"literal","value":"fixed"}'
# The same record with its keys out of canonical order: the one defect the
# normaliser is allowed to repair on its own.
NONCANONICAL_SECOND_INPUT = '{"type":"literal","name":"question","value":"fixed"}'


def draft(baseline, *, tid="T1", isolation="required",
          excluded="vcs.integrate, vcs.push, vcs.open-pr",
          inputs=CANONICAL_SECOND_INPUT, criterion=GOOD_CRITERION_NARROW,
          objective="Change one observable artifact."):
    return DRAFT.format(
        tid=tid, baseline=baseline, isolation=isolation, excluded=excluded,
        inputs=inputs, criterion=criterion, objective=objective,
    )


def five_defect_draft(baseline, tid="T1"):
    """A draft carrying the five defects the item's completion test names.

    Three are syntactic -- a record whose keys are out of canonical order,
    `isolation: none` under `orch-tdd`, an exclusion written as prose. Two
    are decisions -- an instruction over the ceiling, and a criterion naming
    no oracle class -- and nothing may rewrite those.
    """
    spent = len("Change one observable artifact.".split())
    padded = "word " * (320 - _instruction_words(baseline, tid) + spent - 1) + "word"
    return draft(
        baseline, tid=tid, isolation="none",
        excluded="vcs.integrate, do not push to the remote",
        inputs=NONCANONICAL_SECOND_INPUT,
        criterion=f"the artifact changes | oracle: {NARROW_ORACLE}",
        objective=padded,
    )


def _instruction_words(baseline, tid):
    """The word count of the five-defect draft before its objective is padded."""
    import scripts.tickets_format as fmt

    skeleton = draft(
        baseline, tid=tid, isolation="none",
        excluded="vcs.integrate, do not push to the remote",
        inputs=NONCANONICAL_SECOND_INPUT,
        criterion=f"the artifact changes | oracle: {NARROW_ORACLE}",
        objective="Change one observable artifact.",
    )
    return fmt.instruction_words(skeleton)


class LintFixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.sink = use_sink(self.tmp)
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        self.baseline = initialize_git_fixture(self.repo)
        self._cwd = os.getcwd()
        os.chdir(self.repo)

    def tearDown(self):
        os.chdir(self._cwd)
        self._tmp.cleanup()

    def write_draft(self, text, name="draft.md"):
        path = self.tmp / name
        path.write_text(text, encoding="utf-8")
        return path

    def lint(self, *args):
        return run_cmd("lint", *args)

    def codes(self, payload):
        return {item["code"] for item in payload["lint"]["findings"]}


class LintDraftTest(LintFixture):
    def test_five_defects_are_reported_in_one_call(self):
        path = self.write_draft(five_defect_draft(self.baseline))
        payload = self.lint("--file", str(path))
        self.assertEqual(
            {"input-json-noncanonical", "vcs-isolation-required",
             "vcs-exclusion-not-tokenized", "instruction-ceiling", "ticket-defect"},
            self.codes(payload),
        )
        self.assertEqual(5, payload["lint"]["counts"]["total"])
        self.assertEqual(1, payload["exit_code"])

    def test_the_ceiling_finding_names_its_count_and_its_overage(self):
        path = self.write_draft(five_defect_draft(self.baseline))
        finding = next(
            item for item in self.lint("--file", str(path))["lint"]["findings"]
            if item["code"] == "instruction-ceiling"
        )
        self.assertIn("320-word instruction", finding["message"])
        self.assertIn("20 over the 300-word ceiling", finding["message"])
        self.assertEqual("semantic", finding["kind"])

    def test_a_clean_draft_exits_zero_with_no_finding(self):
        path = self.write_draft(draft(self.baseline))
        payload = self.lint("--file", str(path))
        self.assertEqual([], payload["lint"]["findings"], payload)
        self.assertEqual(0, payload["exit_code"])

    def test_a_root_and_a_gate_stub_stay_exempt_from_the_ceiling(self):
        over = five_defect_draft(self.baseline)
        root = over.replace("executor: orch-tdd", "executor: orch-decompose")
        path = self.write_draft(root, "root.md")
        self.assertNotIn("instruction-ceiling", self.codes(self.lint("--file", str(path))))
        gate = self.write_draft(
            over.replace("id: T1", "id: 00-root.gate.verify"), "gate.md"
        )
        self.assertNotIn("instruction-ceiling", self.codes(self.lint("--file", str(gate))))

    def test_an_unreadable_draft_is_exit_two(self):
        payload = self.lint("--file", str(self.tmp / "absent.md"))
        self.assertIn("unreadable draft", payload["error"])
        self.assertEqual(2, payload["exit_code"])

    def test_an_executor_named_on_the_command_line_is_graded(self):
        """`--executor` grades a draft that has not chosen one yet."""
        text = draft(self.baseline).replace("executor: orch-tdd", "executor: orch-repair")
        path = self.write_draft(text.replace("isolation: required", "isolation: none"))
        self.assertIn(
            "vcs-isolation-required",
            self.codes(self.lint("--file", str(path), "--executor", "orch-tdd")),
        )

    def test_a_whole_suite_oracle_is_reported_as_a_warning(self):
        text = draft(
            self.baseline,
            criterion="the suite passes | oracle: `python -m unittest discover` "
                      "| oracle_class: deterministic | provenance: pre-existing",
        )
        finding = next(
            item for item in self.lint("--file", str(self.write_draft(text)))["lint"]["findings"]
            if item["code"] == "whole-suite-oracle"
        )
        self.assertEqual("warning", finding["severity"])
        self.assertEqual("semantic", finding["kind"])


class LintFixTest(LintFixture):
    def test_fix_clears_the_three_syntactic_findings_and_leaves_the_two(self):
        path = self.write_draft(five_defect_draft(self.baseline))
        payload = self.lint("--file", str(path), "--fix")
        self.assertEqual(
            ["input-json-noncanonical", "vcs-exclusion-not-tokenized",
             "vcs-isolation-required"],
            payload["lint"]["fixed"],
        )
        self.assertEqual({"instruction-ceiling", "ticket-defect"}, self.codes(payload))
        self.assertEqual(1, payload["exit_code"])
        rewritten = path.read_text(encoding="utf-8")
        data = _parse_frontmatter(rewritten)
        self.assertEqual("required", data["isolation"])
        self.assertIn("vcs.push", data["excluded_actions"])
        self.assertIn("- input: " + CANONICAL_SECOND_INPUT, rewritten)

    def test_fix_never_rewrites_the_semantic_half(self):
        path = self.write_draft(five_defect_draft(self.baseline))
        before = path.read_text(encoding="utf-8")
        self.lint("--file", str(path), "--fix")
        after = path.read_text(encoding="utf-8")
        self.assertEqual(
            [line for line in before.splitlines() if line.startswith("word")],
            [line for line in after.splitlines() if line.startswith("word")],
        )
        criterion = next(line for line in after.splitlines() if line.startswith("- the artifact"))
        self.assertNotIn("oracle_class", criterion)
        self.assertIn(criterion, before)

    def test_prose_naming_no_single_token_is_semantic_and_stays_written(self):
        """`git` names two reserved actions, so the rewrite would be a guess."""
        text = draft(self.baseline, excluded="vcs.push, no git of any kind")
        path = self.write_draft(text)
        payload = self.lint("--file", str(path), "--fix")
        finding = next(
            item for item in payload["lint"]["findings"]
            if item["code"] == "vcs-exclusion-not-tokenized"
        )
        self.assertEqual("semantic", finding["kind"])
        self.assertIsNone(finding["fix"])
        self.assertEqual([], payload["lint"]["fixed"])
        self.assertIn("no git of any kind", path.read_text(encoding="utf-8"))

    def test_fix_on_a_claimed_ticket_refuses_and_writes_nothing(self):
        text = (five_defect_draft(self.baseline)
                .replace("status: pending", "status: claimed")
                .replace("claimed_by:\n", "claimed_by: someone\n"))
        path = place(self.sink, "testrun", "T1", text)
        claimed = path.read_text(encoding="utf-8")
        payload = self.lint("testrun", "T1", "--fix")
        self.assertEqual(2, payload["exit_code"])
        self.assertIn("is claimed by someone", payload["error"])
        self.assertEqual(claimed, path.read_text(encoding="utf-8"))

    def test_fix_refuses_every_cut_time_freeze_amend_refuses(self):
        """`--fix` is a cut-time rewrite, so it stops where `amend` stops.

        Each of these is unclaimed and `pending`, so both status guards pass
        and the ticket is one `amend` refuses on its own separate terms.
        """
        frozen = (
            ("checked_by: some_checker", "has an immutable checked_by"),
            ("assignment_seal: v2:sha256:deadbeef", "carries an assignment_seal"),
        )
        for index, (field, expected) in enumerate(frozen):
            tid = f"F{index}"
            text = five_defect_draft(self.baseline, tid=tid).replace(
                "claimed_at:", "claimed_at:" + chr(10) + field, 1)
            path = place(self.sink, "testrun", tid, text)
            before = path.read_text(encoding="utf-8")
            payload = self.lint("testrun", tid, "--fix")
            self.assertEqual(2, payload["exit_code"], payload)
            self.assertIn(expected, payload["error"])
            self.assertEqual(before, path.read_text(encoding="utf-8"))

    def test_fix_refuses_a_sealed_cohort(self):
        """A sibling of the cohort is claimed, so the cut is closed."""
        cohort = "cohort: v1:batch:wave"
        sibling = (draft(self.baseline, tid="S0")
                   .replace("cohort: v1:ticket:S0", cohort)
                   .replace("status: pending", "status: claimed")
                   .replace("claimed_by:", "claimed_by: someone", 1))
        place(self.sink, "testrun", "S0", sibling)
        path = place(self.sink, "testrun", "S1",
                     five_defect_draft(self.baseline, tid="S1")
                     .replace("cohort: v1:ticket:S1", cohort))
        before = path.read_text(encoding="utf-8")
        payload = self.lint("testrun", "S1", "--fix")
        self.assertEqual(2, payload["exit_code"], payload)
        self.assertIn("sealed cohort", payload["error"])
        self.assertEqual(before, path.read_text(encoding="utf-8"))

    def test_fix_rewrites_an_unclaimed_ticket_in_the_sink(self):
        path = place(self.sink, "testrun", "T1", five_defect_draft(self.baseline))
        payload = self.lint("testrun", "T1", "--fix")
        self.assertEqual(1, payload["exit_code"])
        self.assertEqual("required", _parse_frontmatter(path.read_text(encoding="utf-8"))["isolation"])


class LintTicketTest(LintFixture):
    def test_a_clean_issued_ticket_exits_zero(self):
        place(self.sink, "testrun", "T1", draft(self.baseline))
        payload = self.lint("testrun", "T1")
        self.assertEqual([], payload["lint"]["findings"], payload)
        self.assertEqual(0, payload["exit_code"])

    def test_a_dependency_that_is_not_complete_is_semantic(self):
        place(self.sink, "testrun", "T0", draft(self.baseline, tid="T0"))
        place(self.sink, "testrun", "T1", draft(self.baseline).replace(
            "depends_on: []", "depends_on: [T0]"))
        finding = next(
            item for item in self.lint("testrun", "T1")["lint"]["findings"]
            if item["code"] == "dependency-incomplete"
        )
        self.assertEqual("semantic", finding["kind"])
        self.assertIsNone(finding["fix"])

    def test_a_missing_ticket_is_exit_two(self):
        payload = self.lint("testrun", "absent")
        self.assertEqual(2, payload["exit_code"])

    def test_the_process_exit_status_carries_the_verdict(self):
        """Read through a real process: the exit code is the contract."""
        path = self.write_draft(five_defect_draft(self.baseline))
        completed = subprocess.run(
            [sys.executable, str(TICKETS_PY), "lint", "--file", str(path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(self.repo), env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        self.assertEqual(1, completed.returncode, completed.stderr)
        self.assertEqual(5, len(json.loads(completed.stdout)["lint"]["findings"]))
        clean = self.write_draft(draft(self.baseline), "clean.md")
        completed = subprocess.run(
            [sys.executable, str(TICKETS_PY), "lint", "--file", str(clean)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(self.repo), env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        self.assertEqual(0, completed.returncode, completed.stderr)


class CommandTableTest(unittest.TestCase):
    def test_tables_are_owned_by_the_commands_module(self):
        for name in ("SUBCOMMAND_USAGE", "SUBCOMMAND_SUMMARY", "VALUE_FLAGS",
                     "HELP_FLAGS", "HELP_COMMANDS", "GATE_USAGE",
                     "INSTANTIATE_USAGE"):
            self.assertIs(
                getattr(tickets_dispatch, name), getattr(tickets_commands, name),
                f"{name} is dispatch's copy rather than the table module's",
            )

    def test_every_routed_subcommand_states_a_usage_and_a_summary(self):
        for name in ("new", "amend", "recut", "instantiate", "gate", "list",
                     "ready", "claim", "grant", "check", "set-status",
                     "result-grade", "packet", "result", "worklog",
                     "run-state", "improvement", "lint"):
            self.assertIn(name, tickets_commands.SUBCOMMAND_USAGE)
            self.assertIn(name, tickets_commands.SUBCOMMAND_SUMMARY)

    def test_the_new_payload_flags_are_value_flags(self):
        self.assertIn("--record-file", tickets_commands.VALUE_FLAGS)
        self.assertIn("--file", tickets_commands.VALUE_FLAGS)


if __name__ == "__main__":
    unittest.main()
