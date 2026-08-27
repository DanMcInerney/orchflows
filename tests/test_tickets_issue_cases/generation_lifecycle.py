"""Executable draft, validation, seal, and correction lifecycle contract."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import tickets_admission as admission
from scripts import tickets_generations as generations
from scripts import tickets
from scripts import tickets_format, tickets_transitions
from scripts.tickets_dispatch import _dispatch
from scripts.tickets_format import _parse_frontmatter, _set_frontmatter_field
from tests.test_tickets_cases.admission_v1 import initialize_git_fixture
from tests.test_tickets_cases.common import run_cmd, use_sink


def ticket(ticket_id, *, executor="orch-tdd", objective="deliver", result="", regions=None):
    fields = [
        "---", f"id: {ticket_id}", "run: run", "status: pending",
        "admission: pending", f"executor: {executor}", "pack: orch-code-pack",
        "independence: gate", "depends_on: []", "write_scope: [scripts/example.py]",
        "mutations: [change:scripts/example.py]", "isolation: required", "bound: 30m",
        "claimed_by:", "claimed_at:",
    ]
    fields.append("ownership_regions: " + generations.canonical_json(regions or []))
    return "\n".join(fields + [
        "---", "", "## Objective", "", objective, "", "## Fixed inputs", "",
        '- input: {"identity":{"kind":"git-tree","repo":"run-project","revision":"02621f7005b0b4d37fa59b0d450ff742d9c1bfbd"},"name":"baseline","type":"identity"}',
        '- input: {"name":"fixture","type":"literal","value":1}', "",
        "## Completion test", "", "- works | oracle: `fixture` | oracle_class: deterministic | provenance: authored-here",
        "", "## Return fields", "", "status; result", "", "## Result", "", result,
        "", "## Verification", "", "", "## Feedback", "", "[]", "", "## Risks", "", "[]",
        "", "## Handoff", "", "",
    ])


def snapshot():
    return {
        "00-root": ticket("00-root", executor="orch-decompose", objective="root"),
        "00-root.01": ticket("00-root.01"),
    }


class GenerationIdentityTest(unittest.TestCase):
    def test_public_facade_exposes_generation_engine(self):
        self.assertIs(tickets.draft_snapshot, generations.draft_snapshot)
        self.assertIs(tickets.assignment_digest, generations.assignment_digest)

    def test_root_and_cut_identities_cover_assignment_not_bookkeeping(self):
        original = snapshot()
        draft = generations.draft_snapshot("00-root", original)
        self.assertRegex(draft["root_generation"], r"^root:00-root:1:sha256:[0-9a-f]{64}$")
        self.assertRegex(draft["cut_generation"], r"^cut:00-root:1:sha256:[0-9a-f]{64}$")
        bookkeeping = dict(original)
        bookkeeping["00-root.01"] = _set_frontmatter_field(bookkeeping["00-root.01"], "status", "ready")
        self.assertEqual(draft, generations.draft_snapshot("00-root", bookkeeping))
        executor_output = dict(original)
        executor_output["00-root.01"] = executor_output["00-root.01"].replace("## Result\n\n", "## Result\n\noutput\n")
        self.assertEqual(draft, generations.draft_snapshot("00-root", executor_output))
        assignment = dict(original)
        assignment["00-root.01"] = assignment["00-root.01"].replace("deliver", "deliver exactly")
        changed = generations.draft_snapshot("00-root", assignment)
        self.assertNotEqual(draft["cut_generation"], changed["cut_generation"])
        self.assertEqual(draft["root_generation"], changed["root_generation"])


class DraftValidateSealLifecycleTest(unittest.TestCase):
    def test_only_exact_validated_snapshot_seals_and_becomes_admissible(self):
        current = snapshot()
        draft = generations.draft_snapshot("00-root", current)
        receipt = generations.validate_draft("00-root", current, draft)
        sealed = generations.seal_assignments("00-root", current, draft, receipt)
        unit = _parse_frontmatter(sealed["00-root.01"])
        root = _parse_frontmatter(sealed["00-root"])
        self.assertEqual(draft["root_generation"], unit["root_generation"])
        self.assertEqual(draft["cut_generation"], unit["cut_generation"])
        self.assertEqual(generations.assignment_digest("00-root.01", sealed["00-root.01"]), unit["assignment_seal"])
        self.assertEqual(generations.assignment_digest("00-root", sealed["00-root"]), root["assignment_seal"])
        grade = admission.grade_admission("00-root.01", sealed["00-root.01"], sealed)
        self.assertIn("seal-state-unavailable", {item["code"] for item in grade["findings"]})
        changed = dict(current)
        changed["00-root.01"] = changed["00-root.01"].replace("deliver", "moved target")
        with self.assertRaises(generations.GenerationError):
            generations.seal_assignments("00-root", changed, draft, receipt)

    def test_commands_validate_seal_and_release_units_to_ready(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                run_dir = Path(directory) / "tickets" / "run"
                run_dir.mkdir(parents=True)
                for ticket_id, text in snapshot().items():
                    (run_dir / f"{ticket_id}.md").write_text(text, encoding="utf-8")
                self.assertNotIn("error", _dispatch(["stamp-generation", "run", "00-root"]))
                validated = _dispatch(["draft-validate", "run", "00-root"])
                self.assertEqual("validated", validated["draft_validation"]["state"])
                cut = validated["draft_validation"]["cut_generation"]
                sealed = _dispatch(["seal", "run", "00-root", "--cut-generation", cut])
                self.assertEqual(cut, sealed["assignment_seal"]["cut_generation"])
                ready = _dispatch(["ready", "--run", "run"])
                self.assertIn("00-root.01", {item["id"] for item in ready["ready"]})

    def test_cut_binds_gate_assignments_and_durable_coverage(self):
        current = snapshot()
        current["00-root.gate.verify"] = ticket("00-root.gate.verify", executor="orch-verify")
        first = generations.draft_snapshot("00-root", current, coverage_map="criterion: unit\n")
        changed_gate = dict(current)
        changed_gate["00-root.gate.verify"] = changed_gate["00-root.gate.verify"].replace("deliver", "verify exact")
        self.assertNotEqual(first["cut_generation"], generations.draft_snapshot("00-root", changed_gate, coverage_map="criterion: unit\n")["cut_generation"])
        self.assertNotEqual(first["cut_generation"], generations.draft_snapshot("00-root", current, coverage_map="criterion: gate\n")["cut_generation"])

class CorrectionGenerationPolicyTest(unittest.TestCase):
    def test_one_default_correction_and_recurrence_suspends_immediately(self):
        first = generations.correction_decision([{"code": "coverage", "field": "map"}], [], 1)
        self.assertEqual("new-generation", first["disposition"])
        self.assertEqual(2, first["next_ordinal"])
        repeated = generations.correction_decision([{"field": "map", "code": "coverage"}], first["history"], 1)
        self.assertEqual("suspend", repeated["disposition"])
        self.assertEqual("recurring-validation-failure", repeated["reason"])
        bounded = generations.correction_decision([{"code": "other", "field": "assignment"}], first["history"], 1)
        self.assertEqual("correction-bound-exhausted", bounded["reason"])

    def test_command_path_applies_bound_and_recurring_failure_policy(self):
        with tempfile.TemporaryDirectory() as directory:
            with mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": directory}):
                run_dir = Path(directory) / "tickets" / "run"
                run_dir.mkdir(parents=True)
                (run_dir / "00-root.md").write_text(ticket("00-root", executor="orch-decompose").replace("ownership_regions: []\n", ""), encoding="utf-8")
                first = _dispatch(["draft-validate", "run", "00-root", "--correction-bound", "2"])
                self.assertEqual("new-generation", first["correction"]["disposition"])
                repeated = _dispatch(["draft-validate", "run", "00-root", "--correction-bound", "2"])
                self.assertEqual("recurring-validation-failure", repeated["correction"]["reason"])


class DraftValidateTest(unittest.TestCase):
    """The entry `scripts/tickets_generations.py` validates a draft against."""

    def test_draft_validate_is_a_v2_entry_only(self):
        entry = tickets_transitions.stamp("draft-validate", 2)
        self.assertEqual(admission.ADMISSION_V2_PENDING, entry.admission)
        self.assertIsNone(tickets_transitions.stamp("draft-validate", 1))

    def test_a_v2_draft_may_sit_at_any_status_no_execution_has_reached(self):
        entry = tickets_transitions.stamp("draft-validate", 2)
        self.assertEqual(("pending", "ready", "suspended"), entry.draft_statuses)
        for status in entry.draft_statuses:
            with self.subTest(status=status):
                self.assertIn(status, tickets_format.VALID_STATUSES)
                self.assertNotIn(status, tickets_format.TERMINAL_STATES)

    def test_a_claimed_root_is_a_vantage_and_a_claimed_member_is_not(self):
        """Both directions, against the table and against the live command.

        A draft is graded from its root, so a claimed root is the position
        the snapshot is read from -- the route this run's own root took --
        while a claimed member is an execution the draft would be rewriting
        underneath it. The member set stays the entry's own; the root adds
        exactly `claimed` to it, which is why the entry must not carry it.
        """

        self.assertNotIn(
            tickets_transitions.CLAIMED,
            tickets_transitions.stamp("draft-validate", 2).draft_statuses,
        )
        for ticket_id, codes in (("00-root", []), ("00-root.01", ["v2-draft-status"])):
            with self.subTest(ticket=ticket_id), tempfile.TemporaryDirectory() as raw:
                current = dict(snapshot())
                current[ticket_id] = tickets_format._set_frontmatter_field(
                    current[ticket_id], "status", tickets_transitions.CLAIMED)
                findings = generations._v2_draft_findings("00-root", current)
                self.assertEqual(codes, [item["code"] for item in findings])
                run_dir = use_sink(Path(raw)) / "tickets" / "run"
                run_dir.mkdir(parents=True)
                for tid, text in current.items():
                    (run_dir / f"{tid}.md").write_text(text, encoding="utf-8")
                live = run_cmd(Path(raw), "draft-validate", "run", "00-root")
                self.assertEqual(codes, [item["code"] for item in live.get("findings", [])])
                self.assertEqual(not codes, "draft_validation" in live)
                if not codes:  # the route's second half: `seal` shares this grader
                    self.assertIn("assignment_seal", run_cmd(Path(raw), "seal", "run", "00-root",
                        "--cut-generation", live["draft_validation"]["cut_generation"]))


class ResumeGenerationTest(unittest.TestCase):
    """A caller can dispose one parked authority amendment durably."""

    def test_amend_and_reseal_resumes_the_same_ticket_in_a_new_generation(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            baseline = initialize_git_fixture(tmp)
            run_dir = use_sink(tmp) / "tickets" / "run"
            run_dir.mkdir(parents=True)
            for ticket_id, text in snapshot().items():
                text = text.replace("02621f7005b0b4d37fa59b0d450ff742d9c1bfbd", baseline)
                (run_dir / f"{ticket_id}.md").write_text(text, encoding="utf-8")

            validated = run_cmd(tmp, "draft-validate", "run", "00-root")
            cut = validated["draft_validation"]["cut_generation"]
            self.assertNotIn(
                "error", run_cmd(tmp, "seal", "run", "00-root", "--cut-generation", cut)
            )
            ready = run_cmd(tmp, "ready", "--run", "run")
            self.assertIn("00-root.01", {item["id"] for item in ready["ready"]}, ready)
            claim = run_cmd(tmp, "claim", "run", "00-root.01", "--by", "worker-a")
            self.assertNotIn("error", claim, claim)
            worker = tickets_format._parse_frontmatter(
                (run_dir / "00-root.01.md").read_text(encoding="utf-8")
            )
            request = {
                "bound-state": "within",
                "change-kind": "authority",
                "cut-generation": worker["cut_generation"],
                "evidence-identities": ["sha256:" + "1" * 64],
                "parent-ticket": "00-root",
                "reason": "one additional output is required",
                "request-id": "request-1",
                "requester-ticket": "00-root.01",
                "root-generation": worker["root_generation"],
                "target-fields": ["mutations", "write_scope"],
            }
            parked = run_cmd(
                tmp, "amendment-request", "run", "00-root.01", "--record",
                generations.canonical_json(request),
            )
            self.assertNotIn("error", parked, parked)
            self.assertEqual("suspended", parked["amendment_request"]["status"])
            disposition = {
                "amendments": {
                    "mutations": ["change:scripts/example.py", "create:scripts/extra.py"],
                    "write_scope": ["scripts/example.py", "scripts/extra.py"],
                },
                "disposition": "amend-and-reseal",
                "request-id": "request-1",
            }
            resumed = run_cmd(
                tmp, "resume-generation", "run", "00-root.01", "--record",
                generations.canonical_json(disposition),
            )
            self.assertNotIn("error", resumed)
            self.assertIn(":2:sha256:", resumed["resume_generation"]["cut_generation"])
            changed = (run_dir / "00-root.01.md").read_text(encoding="utf-8")
            data = tickets_format._parse_frontmatter(changed)
            self.assertEqual("suspended", data["status"])
            self.assertEqual("worker-a", data["claimed_by"])
            self.assertEqual(["scripts/example.py", "scripts/extra.py"], data["write_scope"])
            self.assertEqual([], generations.v2_seal_findings("00-root.01", changed))
            replay = run_cmd(
                tmp, "resume-generation", "run", "00-root.01", "--record",
                generations.canonical_json(disposition),
            )
            self.assertIn("already disposed", replay["error"])

    def test_resume_rejects_an_assignment_field_the_request_did_not_name(self):
        record = {
            "amendments": {"excluded_actions": ["new exclusion"]},
            "disposition": "amend-and-reseal",
            "request-id": "request-1",
        }
        result = generations._validate_resume_record(
            record, {"request-id": "request-1", "target-fields": ["write_scope"]}
        )
        self.assertIn("target-fields", result)


if __name__ == "__main__":
    unittest.main()
