"""`tickets.py lint`: every grader at once, and `--fix` on the syntactic half.

One module rather than a case package: this shard's cases are all one
subject, and the tables case is here because the tables and the subcommand
that extends them land together.
"""

import json
import subprocess
from unittest import mock

from tests.test_tickets_issue_cases.common import *  # noqa: F401,F403
from scripts import cutcheck_scope, tickets_commands, tickets_context, tickets_dispatch
from scripts.tickets_format import _parse_frontmatter, _sections
from tests.test_tickets_cases.admission_v1 import initialize_git_fixture
from scripts.tickets_store import _runs_root
from tests.test_tickets_issue_cases.generation_lifecycle import ticket as v2_ticket

# Two readings of one frozen ticket used to disagree; both halves land in the
# three classes at the foot of this module. Lint graded with no context, so the
# sealed run-state record could never be found and every sealed root reported
# `seal-state-unavailable` while `ready` admitted it clean; and lint said
# nothing on an exclusion contradicting its own write scope, which `cutcheck`
# family 3 reports on the cut -- by which time the root is sealed.
SEAL_STATE_CODES = {
    "seal-state-unavailable", "seal-state-missing", "seal-state-mismatch",
    "validation-receipt-mismatch", "sealed-assignment-mismatch",
}
CONTRADICTED = "vcs.integrate, vcs.push, vcs.open-pr, never write scratch/T1.txt"

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


# The five defects the item's completion test names, as one set of overrides
# rather than two copies of it. Three are syntactic -- keys out of canonical
# order, `isolation: none` under `orch-tdd`, an exclusion written as prose --
# and two are decisions nothing may rewrite: an instruction over the ceiling,
# and a criterion naming no oracle class.
FIVE_DEFECTS = {
    "isolation": "none",
    "excluded": "vcs.integrate, do not push to the remote",
    "inputs": NONCANONICAL_SECOND_INPUT,
    "criterion": f"the artifact changes | oracle: {NARROW_ORACLE}",
}
UNPADDED_OBJECTIVE = "Change one observable artifact."


def five_defect_draft(baseline, tid="T1"):
    """That draft, its objective padded to exactly 320 instruction words."""
    over = 320 - _instruction_words(baseline, tid) + len(UNPADDED_OBJECTIVE.split())
    return draft(baseline, tid=tid, objective="word " * (over - 1) + "word", **FIVE_DEFECTS)


def _instruction_words(baseline, tid):
    """The word count of the five-defect draft before its objective is padded."""
    import scripts.tickets_format as fmt

    return fmt.instruction_words(draft(baseline, tid=tid, objective=UNPADDED_OBJECTIVE, **FIVE_DEFECTS))


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

    def issue(self, run, ticket_id, text):
        """One ticket in the sink, where lint's issued half reads it."""
        run_dir = self.sink / "tickets" / run
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / f"{ticket_id}.md").write_text(text, encoding="utf-8")

    def lint(self, *args):
        return run_cmd("lint", *args)

    def codes(self, payload):
        return {item["code"] for item in payload["lint"]["findings"]}


class LintDraftTest(LintFixture):
    def test_five_defects_are_reported_in_one_call(self):
        path = self.write_draft(five_defect_draft(self.baseline))
        payload = self.lint("--file", str(path))
        self.assertEqual({"input-json-noncanonical", "vcs-isolation-required", "instruction-ceiling",
                          "vcs-exclusion-not-tokenized", "ticket-defect"}, self.codes(payload))
        self.assertEqual(5, payload["lint"]["counts"]["total"])
        self.assertEqual(1, payload["exit_code"])

    def test_the_ceiling_finding_names_its_count_and_its_overage(self):
        path = self.write_draft(five_defect_draft(self.baseline))
        findings = self.lint("--file", str(path))["lint"]["findings"]
        finding = next(item for item in findings if item["code"] == "instruction-ceiling")
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
        gate = self.write_draft(over.replace("id: T1", "id: 00-root.gate.verify"), "gate.md")
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

    def test_a_checked_ticket_lints_clean(self):
        """`check` writes `checked_by`; the issued form may not call that a defect.

        `new`'s grader refuses `checked_by` because an unissued ticket
        carrying it would suppress the checker before dispatch. Once
        `check` has written it the same field is the lawful record, and
        `lint <run> <id>` reads issued tickets only.
        """
        text = (draft(self.baseline)
                .replace("independence: gate", "independence: checker")
                .replace("status: pending", "status: complete")
                .replace("claimed_by:\n", "claimed_by: unit_01\n")
                .replace("claimed_at:\n",
                         "claimed_at: 2026-08-23T14:25:12Z\nchecked_by: check_unit_01\n"))
        place(self.sink, "testrun", "T1", text)
        payload = self.lint("testrun", "T1")
        self.assertEqual([], payload["lint"]["findings"], payload)
        self.assertEqual(0, payload["exit_code"])

    def test_a_draft_carrying_checked_by_is_still_a_defect(self):
        """The issue-time rule stands where issue time is: `--file`."""
        text = (draft(self.baseline)
                .replace("independence: gate", "independence: checker")
                .replace("claimed_at:", "claimed_at:\nchecked_by: check_unit_01", 1))
        payload = self.lint("--file", str(self.write_draft(text)))
        self.assertIn(
            "an unissued ticket cannot carry 'checked_by'",
            " ".join(item["message"] for item in payload["lint"]["findings"]),
        )
        self.assertEqual(1, payload["exit_code"])

    def test_a_non_root_gate_ticket_carrying_checked_by_stays_a_defect(self):
        """The contract half of the rule is not issue-time and does not lift."""
        text = draft(self.baseline).replace(
            "claimed_at:", "claimed_at:\nchecked_by: check_gate", 1)
        place(self.sink, "testrun", "T1", text)
        payload = self.lint("testrun", "T1")
        self.assertIn("non-root independence 'gate' cannot carry 'checked_by'",
                      " ".join(item["message"] for item in payload["lint"]["findings"]))
        self.assertEqual(1, payload["exit_code"])

    def test_a_missing_ticket_is_exit_two(self):
        payload = self.lint("testrun", "absent")
        self.assertEqual(2, payload["exit_code"])

    def lint_process(self, path):
        return subprocess.run(
            [sys.executable, str(TICKETS_PY), "lint", "--file", str(path)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=str(self.repo), env={**os.environ, "PYTHONIOENCODING": "utf-8"})

    def test_the_process_exit_status_carries_the_verdict(self):
        """Read through a real process: the exit code is the contract."""
        completed = self.lint_process(self.write_draft(five_defect_draft(self.baseline)))
        self.assertEqual(1, completed.returncode, completed.stderr)
        self.assertEqual(5, len(json.loads(completed.stdout)["lint"]["findings"]))
        clean = self.lint_process(self.write_draft(draft(self.baseline), "clean.md"))
        self.assertEqual(0, clean.returncode, clean.stderr)


class SealedRootLintTest(LintFixture):
    """Lint reads a sealed v2 root the way `ready` and `claim` read it."""

    def test_a_sealed_cut_is_graded_against_its_run_state_record(self):
        """Threading the context is not silencing the finding: a record
        naming another cut still fails."""
        run_dir = self.sink / "tickets" / "run"
        run_dir.mkdir(parents=True)
        for tid, executor in (("00-root", "orch-decompose"), ("00-root.01", "orch-tdd")):
            (run_dir / f"{tid}.md").write_text(v2_ticket(tid, executor=executor), encoding="utf-8")
        cut = run_cmd("draft-validate", "run", "00-root")["draft_validation"]["cut_generation"]
        sealed = run_cmd("seal", "run", "00-root", "--cut-generation", cut)
        self.assertEqual(cut, sealed["assignment_seal"]["cut_generation"], sealed)
        for tid in ("00-root", "00-root.01"):
            codes = self.codes(self.lint("run", tid))
            self.assertEqual(set(), codes & SEAL_STATE_CODES, (tid, codes))
        records = sorted((_runs_root() / "run" / "generations").glob("*.sealed.json"))
        self.assertTrue(records, "the seal wrote no run-state record to grade against")
        for record in records:
            payload = json.loads(record.read_text(encoding="utf-8"))
            payload["root_generation"] = "v2:root:00-root:9:sha256:" + "cd" * 32
            record.write_text(json.dumps(payload), encoding="utf-8")
        self.assertIn("seal-state-mismatch", self.codes(self.lint("run", "00-root")))


class ScopeContradictionLintTest(LintFixture):
    """Family 3's judgment, surfaced while the text can still be changed."""

    def test_an_exclusion_naming_a_granted_path_is_reported(self):
        path = self.write_draft(draft(self.baseline, excluded=CONTRADICTED))
        payload = self.lint("--file", str(path))
        finding = next(item for item in payload["lint"]["findings"] if item["code"] == "scope-contradiction")
        self.assertEqual("semantic", finding["kind"])
        self.assertIn("never write scratch/T1.txt | scratch/T1.txt", finding["message"])
        self.assertEqual(1, payload["exit_code"])
        self.issue("testrun", "T1", path.read_text(encoding="utf-8"))
        self.assertIn("scope-contradiction", self.codes(self.lint("testrun", "T1")))

    def test_lint_and_cutcheck_report_the_same_contradictions(self):
        """One judgment, two readers: the finding sets must not drift apart."""
        for excluded in (CONTRADICTED, "vcs.integrate, vcs.push, vcs.open-pr",
                         "vcs.push, never write docs/other.md",
                         "vcs.push, never write scratch/T1.txt, and never write scratch/T1.txt"):
            text = draft(self.baseline, excluded=excluded)
            path = self.write_draft(text, "case.md")
            mine = {item["message"].split(": ", 1)[1]
                    for item in self.lint("--file", str(path))["lint"]["findings"]
                    if item["code"] == "scope-contradiction"}
            prose = "\n".join(_sections(text).values())
            theirs = {detail for code, detail
                      in cutcheck_scope._scope_closure(_parse_frontmatter(text), prose)
                      if code == cutcheck_scope.SCOPE_CONTRADICTION}
            self.assertEqual(theirs, mine, excluded)


class GraderContextTest(LintFixture):
    """One factory, four consumers: no site can omit the context again
    without omitting it for lint, ready, claim and packet at once."""

    def test_all_four_sites_reach_the_grader_through_the_one_factory(self):
        self.issue("testrun", "T1", draft(self.baseline))
        seen, per_command = [], {}
        real = tickets_context.grade_admission

        def spy(ticket_id, text, siblings, context=None):
            seen.append(dict(context or {}))
            return real(ticket_id, text, siblings, context=context)

        with mock.patch.object(tickets_context, "grade_admission", spy):
            for name, args in (("lint", ("lint", "testrun", "T1")),
                               ("ready", ("ready", "--run", "testrun")),
                               ("claim", ("claim", "testrun", "T1", "--by", "tester")),
                               ("packet", ("packet", "testrun", "T1", "--reply-to", "main"))):
                del seen[:]
                run_cmd(*args)
                per_command[name] = list(seen)
        expected = tickets_context.grader_context("testrun")
        self.assertEqual({"runs_root": str(_runs_root()), "run": "testrun"}, expected)
        for name, contexts in per_command.items():
            self.assertTrue(contexts, f"{name} graded through no factory")
            self.assertEqual([expected] * len(contexts), contexts, name)


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
