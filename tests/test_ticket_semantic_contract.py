"""Focused regressions for the sole semantic ticket contract."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
import subprocess
from unittest import mock

from scripts import cutcheck
from tests._candidate_checkout import (
    git_checkout, record_established_workspace,
)
from scripts import tickets
from scripts import tickets_dispatch_launch as launch_module
from scripts import tickets_generations
from scripts import tickets_join
from scripts import tickets_review
from scripts import tickets_shapes
from scripts import tickets_lifecycle
from scripts import tickets_readiness
from scripts.tickets_format import (
    _parse_frontmatter, _remove_frontmatter_field, _sections, canonical_json,
)
from scripts.tickets_issue_render import _render_ticket
from scripts import workspace

ROOT = Path(__file__).resolve().parents[1]


def assignment(ticket_id, executor, dependencies=(), *, root_generation=None, review_kind=None):
    fields = {
        "id": ticket_id,
        "run": "cut",
        "status": "pending",
        "admission": "pending",
        "executor": executor,
        "pack": "orch-code-pack",
        "independence": "gate",
        "depends_on": list(dependencies),
        "isolation": "required" if executor == "orch-execute" else "none",
        "bound": "30m",
        "root_generation": root_generation,
    }
    if review_kind is not None:
        fields["review_kind"] = review_kind
    sections = [
        ("Goal", f"Deliver the observable result for {ticket_id}."),
        ("Context", "The root assignment and repository are authoritative."),
        ("Result", ""),
        ("Verification", ""),
        ("Feedback", "[]"),
        ("Risks", "[]"),
    ]
    return _render_ticket(fields, sections)


class SemanticTicketContractTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.environment = mock.patch.dict(os.environ, {"ORCHFLOWS_STATE_HOME": self.temporary.name})
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def dispatch(self, *arguments):
        result = tickets._dispatch(list(arguments))
        self.assertNotIn("error", result, result)
        return result

    def test_critique_finding_contract_publishes_closed_shape_and_carriage(self):
        result_contract = (ROOT / "contracts" / "result.md").read_text(
            encoding="utf-8"
        )
        for text in (result_contract,):
            for field in (
                "`blocking`", "`class`", "`evidence`", "`goal_impact`",
                "`id`", "`repair`", "`summary`",
            ):
                self.assertIn(field, text)
            self.assertIn("either `Result` or `Feedback`", " ".join(text.split()))
        self.assertIn("has exactly", result_contract)
        self.assertIn("valid JSON encoding", result_contract)
        self.assertNotIn("records findings in `## Feedback`", result_contract)

    def test_critique_join_normalizes_result_findings_and_accepted_json(self):
        findings = [{
            "blocking": True,
            "class": "correctness",
            "evidence": ["render says ‘game over’"],
            "goal_impact": "The target Goal is false.",
            "id": "B1",
            "repair": "Repair the state transition.",
            "summary": "The final state is wrong — play cannot finish.",
        }]
        streamed = json.dumps(findings, ensure_ascii=False, indent=2)
        accepted = json.dumps(
            findings, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        )
        attempt = {"records": [
            {
                "kind": "result",
                "content": tickets_review.canonical_json({
                    "body": streamed,
                    "section": "Result",
                }),
            },
            {
                "kind": "result",
                "content": tickets_review.canonical_json({
                    "body": "Inspected the fixed render and transition trace.",
                    "section": "Feedback",
                }),
            },
        ]}
        extracted = tickets_join._critique_findings(
            attempt, {
                "Result": "No unstreamed finding delta.",
                "Feedback": "Inspected evidence already streamed.",
            }
        )
        self.assertEqual(tickets_review.canonical_json(findings), extracted)

        artifact = "git:" + subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            capture_output=True, check=True,
        ).stdout.strip()
        plan = tickets_review._record(
            "GatePlan", None, artifact=artifact,
            criteria=[{
                "identity": "sha256:criterion", "lens": "code",
                "order": 0, "ticket": "R.gate.critique.code",
            }],
            isolation="required", mode="gate", pack="orch-code-pack",
            root="R", workspace=str(ROOT.resolve()),
        )
        adjudicated = tickets_review.adjudicate(
            {"protocol": "orchflows.review.v1", "records": [plan]},
            extracted, accepted, "root-join", "code",
        )
        self.assertEqual(findings, adjudicated["records"][-1]["findings"])
        self.assertEqual(findings, adjudicated["records"][-1]["accepted"])

    def test_one_finding_on_both_carriers_is_one_finding_and_a_conflict_refuses(self):
        """A critique that streams a finding and repeats it in the reserved
        outcome recorded one fact twice.  Two records claiming one id with
        different content are two claims, and still refuse."""

        finding = {
            "blocking": True,
            "class": "correctness",
            "evidence": ["test-x failed"],
            "goal_impact": "The target Goal is false.",
            "id": "B1",
            "repair": "Repair test-x.",
            "summary": "test-x is red.",
        }
        streamed = {"records": [{
            "kind": "result",
            "content": tickets_review.canonical_json(
                {"body": json.dumps([finding], indent=2), "section": "Feedback"}
            ),
        }]}

        carried_twice = tickets_join._critique_findings(
            streamed,
            {"Result": tickets_review.canonical_json([finding]), "Feedback": ""},
        )
        self.assertEqual(tickets_review.canonical_json([finding]), carried_twice)

        conflicting = dict(finding, summary="test-x is green.")
        with self.assertRaisesRegex(Exception, "repeats finding id B1"):
            tickets_join._critique_findings(
                streamed,
                {"Result": tickets_review.canonical_json([conflicting]), "Feedback": ""},
            )

    def seal(self, run, root):
        self.dispatch("stamp-generation", run, root)
        validated = self.dispatch("draft-validate", run, root)
        generation = validated["draft_validation"]["cut_generation"]
        self.dispatch("seal", run, root, "--cut-generation", generation)

    def open_attempt(self, run, ticket_id, by, dispatch_id):
        lease = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        return self.dispatch(
            "dispatch-open", run, ticket_id, "--by", by,
            "--dispatch-id", dispatch_id, "--lease-expires-at", lease,
        )["dispatch"]

    def launch(self, run, ticket_id, dispatch_id, workspace=None,
               artifact=None, review_kind=None, record=True):
        """Establish, then commit the launch this child's records enter behind.

        Reached at the facade seam that owns it: `dispatch` composes the
        launch under the run lock and there is no verb for it alone. The
        establishment records the tree on the open attempt first, which is
        the order the facade runs those two steps in.
        """

        if workspace is not None and record:
            record_established_workspace(
                Path(self.temporary.name) / "tickets" / run / f"{ticket_id}.md",
                workspace,
            )
        host, failure = launch_module.resolve_host(launch_module.DEFAULT_HOST)
        self.assertIsNone(failure, failure)
        return tickets._tickets_dispatch_facade_module._launched_under_run_lock(
            run, ticket_id, host, dispatch_id=dispatch_id,
            workspace=workspace, artifact=artifact, review_kind=review_kind,
        )

    def committed_launch(self, *arguments, **facts) -> dict:
        committed = self.launch(*arguments, **facts)
        self.assertNotIn("error", committed, committed)
        return committed["launch"]

    def accepted_file(self, ticket_id, findings) -> list:
        """`dispatch-join --accepted` was removed; the subset crosses as a file."""

        path = Path(self.temporary.name) / f"accepted-{ticket_id}.json"
        path.write_text(findings, encoding="utf-8")
        return ["--accepted-file", str(path)]

    def evidence_flags(self, ticket_id, dispatch_id, evidence) -> list:
        """Typed closing files, the only carrier `dispatch-outcome` still takes."""

        flags = []
        for section, body in sorted(evidence.items()):
            if not body:
                continue
            path = (
                Path(self.temporary.name)
                / f"outcome-{ticket_id}-{dispatch_id}-{section}.txt"
            )
            path.write_text(body, encoding="utf-8")
            flags.extend((f"--{section.lower()}-file", str(path)))
        return flags

    def commit_outcome(self, run, ticket_id, opened, by, dispatch_id):
        review = ".gate.critique." in ticket_id or ticket_id.endswith(".check")
        content = {
            "assignment_seal": opened["assignment_seal"],
            "by": by,
            "dispatch_id": dispatch_id,
            "evidence": {
                # A review stage's Result and Feedback are finding carriers,
                # not prose: the same rule the join applies to the close.
                "Result": "[]" if review else "closing result delta",
                "Verification": "closing verification delta",
                # These fixtures stream Feedback as a result record first, and
                # the close carries only the delta that has not entered yet.
                "Feedback": "" if review else "closing feedback delta: []",
                "Risks": "closing risk delta: []", "Handoff": "",
            },
            "id": ticket_id, "outcome_record_id": "outcome",
            "protocol": "orchflows.dispatch.v1", "run": run,
        }
        return self.dispatch(
            "dispatch-outcome", run, ticket_id,
            *self.evidence_flags(ticket_id, dispatch_id, content["evidence"]),
        )

    def test_a_long_assignment_is_issued_and_reaches_generation_stamping(self):
        """No length refuses a ticket: the planner owns what its child needs."""

        goal = " ".join(["word"] * 400)
        for executor in ("orch-execute", tickets.ROOT_EXECUTOR):
            run = "root-" + executor.removeprefix("orch-")
            with self.subTest(executor):
                created = tickets._dispatch([
                    "new", run, "R", "--executor", executor,
                    "--goal", goal, "--context", "[]", "--pack", "orch-code-pack",
                    "--isolation", "required",
                ])
                self.assertNotIn("error", created, created)
                path = Path(created["new"]["path"])
                self.assertNotIn(
                    "root_generation",
                    _parse_frontmatter(path.read_text(encoding="utf-8")),
                )
                stamped = tickets._dispatch(["stamp-generation", run, "R"])
                self.assertNotIn("error", stamped, stamped)
                self.assertRegex(
                    stamped["stamp_generation"]["root_generation"],
                    r"^root:R:1:sha256:[0-9a-f]{64}$",
                )
                linted = tickets._dispatch(["lint", run, "R"])
                self.assertEqual(
                    {
                        "assignment-unsealed", "generation-invalid",
                        "seal-state-unavailable",
                    },
                    {item["code"] for item in linted["lint"]["findings"]},
                    linted,
                )

    def test_a_long_ordinary_member_is_issued_like_any_other(self):
        self.dispatch(
            "new", "unit-length", "R", "--executor", "orch-execute",
            "--goal", "Deliver the run.", "--context", "[]",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        goal = " ".join(["word"] * 400)
        created = tickets._dispatch([
            "new", "unit-length", "R.01", "--executor", tickets.ROOT_EXECUTOR,
            "--goal", goal, "--context", "[]",
        ])
        self.assertNotIn("error", created, created)

    def test_a_malformed_first_attempt_writes_no_run_directory(self):
        goal = " ".join(["word"] * 400)
        malformed = tickets._dispatch([
            "new", "malformed-root", "R", "--executor", "orch-execute",
            "--goal", goal,
        ])
        self.assertIn("error", malformed)
        run_dir = Path(self.temporary.name) / "tickets" / "malformed-root"
        self.assertFalse(run_dir.exists())
        accepted = tickets._dispatch([
            "new", "malformed-root", "R", "--executor", "orch-execute",
            "--goal", goal, "--context", "[]", "--pack", "orch-code-pack",
            "--isolation", "required",
        ])
        self.assertNotIn("error", accepted, accepted)

    def test_goal_context_only_direct_root_lifecycle(self):
        self.dispatch(
            "new", "direct", "R1", "--executor", "orch-execute",
            "--goal", "Create the observable artifact.",
            "--context", "No exceptional constraints.",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.seal("direct", "R1")
        ready = self.dispatch("ready", "--run", "direct")
        self.assertEqual(["R1"], [item["id"] for item in ready["ready"]])
        ticket_path = Path(self.temporary.name) / "tickets" / "direct" / "R1.md"
        established = ticket_path.read_text(encoding="utf-8")
        for key, value in (
            ("workspace_branch", "candidate-branch"),
            ("workspace_baseline", "0123456789abcdef clean"),
        ):
            established = tickets._set_frontmatter_field(established, key, value)
        ticket_path.write_text(established, encoding="utf-8")
        opened = self.open_attempt("direct", "R1", "worker", "direct-D1")
        launched = self.committed_launch(
            "direct", "R1", opened["dispatch_id"], workspace="C:/candidate",
        )
        self.assertIn("Suggested files are non-binding", launched["prompt"])
        text = (Path(self.temporary.name) / "tickets" / "direct" / "R1.md").read_text(encoding="utf-8")
        self.assertEqual({"Goal", "Context", "Result", "Verification", "Feedback", "Risks"}, set(_sections(text)))

    def test_preissue_lint_and_new_grade_the_same_projected_file_candidate(self):
        source = Path(self.temporary.name) / "R1.md"
        draft = assignment("R1", "orch-execute")
        draft = _remove_frontmatter_field(draft, "admission")
        draft = _remove_frontmatter_field(draft, "run")
        draft = tickets._set_frontmatter_field(draft, "status", "complete")
        source.write_text(draft, encoding="utf-8")
        before = source.read_bytes()

        linted = self.dispatch("lint", "issued-run", "R1", "--file", str(source))
        self.assertEqual([], linted["lint"]["findings"])
        self.assertEqual("issued-run", linted["lint"]["run"])
        self.assertEqual(before, source.read_bytes())
        self.assertFalse((Path(self.temporary.name) / "tickets" / "issued-run").exists())

        created = self.dispatch("new", "issued-run", "R1", "--file", str(source))
        self.assertEqual("R1", created["new"]["id"])
        issued = (
            Path(self.temporary.name) / "tickets" / "issued-run" / "R1.md"
        ).read_text(encoding="utf-8")
        data = _parse_frontmatter(issued)
        self.assertEqual("issued-run", data["run"])
        self.assertEqual("pending", data["status"])
        self.assertEqual("pending", data["admission"])
        self.assertNotIn("claimed_by", data)

    def test_preissue_lint_and_new_refuse_the_same_file_identity_mismatch(self):
        source = Path(self.temporary.name) / "R1.md"
        draft = _remove_frontmatter_field(
            assignment("R1", "orch-execute"), "admission"
        )
        source.write_text(draft, encoding="utf-8")
        before = source.read_bytes()

        linted = tickets._dispatch(
            ["lint", "other-run", "R9", "--file", str(source)]
        )
        issued = tickets._dispatch(
            ["new", "other-run", "R9", "--file", str(source)]
        )
        self.assertIn("placed as 'R9', but ticket file names 'R1'", linted["error"])
        self.assertEqual(linted["error"], issued["error"])
        self.assertEqual(before, source.read_bytes())

    def test_show_inspects_one_ticket_without_mutating_the_sink(self):
        self.dispatch(
            "new", "inspect-run", "R1", "--executor", "orch-execute",
            "--goal", "Expose this ticket.",
            "--context", "Inspection is read-only.",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        ticket_path = (
            Path(self.temporary.name) / "tickets" / "inspect-run" / "R1.md"
        )
        before = ticket_path.read_bytes()

        shown = self.dispatch("show", "inspect-run", "R1")["ticket"]

        self.assertEqual("R1", shown["id"])
        self.assertEqual("inspect-run", shown["run"])
        self.assertEqual("pending", shown["status"])
        self.assertEqual("Expose this ticket.", shown["sections"]["Goal"])
        self.assertEqual("Inspection is read-only.", shown["sections"]["Context"])
        self.assertEqual(before, ticket_path.read_bytes())

    def test_show_refuses_unsafe_or_missing_coordinates_without_creating_state(self):
        root = Path(self.temporary.name)
        for arguments in (
            ("show", "../escape", "R1"),
            ("show", "inspect-run", "a/b"),
            ("show", "inspect-run", "missing"),
        ):
            with self.subTest(arguments=arguments):
                refused = tickets._dispatch(list(arguments))
                self.assertIn("error", refused)
        self.assertFalse((root / "tickets").exists())

    def test_suggested_files_do_not_limit_candidate_paths(self):
        self.dispatch(
            "new", "suggested", "R1", "--executor", "orch-execute",
            "--goal", "Repair the behavior.", "--context", "The repository is authoritative.",
            "--suggested-file", "src/start.py", "--pack", "orch-code-pack",
            "--isolation", "required",
        )
        self.seal("suggested", "R1")
        ready = self.dispatch("ready", "--run", "suggested")
        self.assertEqual(1, len(ready["ready"]))
        packet_path = Path(self.temporary.name) / "tickets" / "suggested" / "R1.md"
        self.assertNotIn("write_scope", _parse_frontmatter(packet_path.read_text(encoding="utf-8")))
        actual = workspace._actual_mutations("M\0other/path.py\0A\0tests/new_guard.py\0")
        self.assertEqual([("change", "other/path.py"), ("create", "tests/new_guard.py")], actual)

    def test_prompt_filing_command_carries_claimant_and_writes_the_ticket(self):
        self.dispatch(
            "new", "packet", "R1", "--executor", "orch-execute",
            "--goal", "Create the artifact.", "--context", "Use repository facts.",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.seal("packet", "R1")
        self.dispatch("ready", "--run", "packet")
        candidate = git_checkout(Path(self.temporary.name) / "candidate")
        ticket_path = Path(self.temporary.name) / "tickets" / "packet" / "R1.md"
        established = ticket_path.read_text(encoding="utf-8")
        for key, value in (
            ("workspace_branch", "candidate-branch"),
            ("workspace_baseline", "0123456789abcdef clean"),
        ):
            established = tickets._set_frontmatter_field(established, key, value)
        ticket_path.write_text(established, encoding="utf-8")
        opened = self.open_attempt("packet", "R1", "worker", "packet-D1")
        prompt = self.committed_launch(
            "packet", "R1", "packet-D1", workspace=str(candidate)
        )["prompt"]
        command = next(
            line for line in prompt.splitlines()
            if len(line.split()) > 2
            and Path(line.split()[1]).name == "tickets.py"
            and line.split()[2:5] == ["result", "packet", "R1"]
            and "--text" in line.split()
        )
        argv = command.split()[2:]
        self.assertEqual(["--assignment-seal", opened["assignment_seal"]], argv[3:5])
        self.assertEqual(["--dispatch-id", "packet-D1"], argv[5:7])
        self.assertEqual(["--record-id", "RECORD_ID"], argv[7:9])
        self.assertEqual(["--by", "worker"], argv[9:11])
        argv[argv.index("RECORD_ID")] = "result-1"
        argv[argv.index("SECTION")] = "Result"
        argv[argv.index("TEXT")] = "filed from the emitted prompt"
        filed = self.dispatch(*argv)
        self.assertEqual("worker", filed["result"]["by"])
        ticket = (
            Path(self.temporary.name) / "tickets" / "packet" / "R1.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "### Written by `worker`\n\nfiled from the emitted prompt", ticket,
        )

    def test_decomposed_root_uses_same_semantic_shape(self):
        self.dispatch("new", "cut", "R", "--executor", "orch-decompose", "--goal", "Deliver the result.", "--context", "Use the repository facts.", "--pack", "orch-code-pack", "--independence", "gate")
        for suffix in ("01", "02"):
            self.dispatch("new", "cut", f"R.{suffix}", "--executor", "orch-execute", "--goal", f"Produce component {suffix}.", "--context", "It feeds the root result.", "--pack", "orch-code-pack", "--isolation", "required")
        self.dispatch("stamp-generation", "cut", "R")
        self.dispatch("gate", "cut", "R")
        validated = self.dispatch("draft-validate", "cut", "R")
        self.dispatch(
            "seal", "cut", "R", "--cut-generation",
            validated["draft_validation"]["cut_generation"],
        )
        for path in sorted((Path(self.temporary.name) / "tickets" / "cut").glob("*.md")):
            sections = _sections(path.read_text(encoding="utf-8"))
            self.assertIn("Goal", sections)
            self.assertIn("Context", sections)

    def test_complete_code_cut_keeps_one_root_generation_before_and_after_seal(self):
        initial = {"R": assignment("R", "orch-decompose")}
        root_draft = tickets_generations.draft_snapshot("R", initial)
        root_receipt = tickets_generations.validate_draft("R", initial, root_draft)
        rooted = tickets_generations.seal_assignments("R", initial, root_draft, root_receipt)
        inherited = root_draft["root_generation"]

        complete = {
            **rooted,
            "R.01": assignment("R.01", "orch-execute", root_generation=inherited),
            "R.02": assignment("R.02", "orch-execute", root_generation=inherited),
            "R.gate.critique.code": assignment(
                "R.gate.critique.code", "orch-check", ("R.01", "R.02"),
                root_generation=inherited, review_kind="critique",
            ),
            "R.gate.repair": assignment(
                "R.gate.repair", "orch-execute", ("R.gate.critique.code",),
                root_generation=inherited, review_kind="repair",
            ),
        }

        cut_draft = tickets_generations.draft_snapshot("R", complete, ordinal=2)
        self.assertEqual(inherited, cut_draft["root_generation"])
        self.assertNotEqual(root_draft["cut_generation"], cut_draft["cut_generation"])
        receipt = tickets_generations.validate_draft("R", complete, cut_draft)
        sealed = tickets_generations.seal_assignments("R", complete, cut_draft, receipt)
        for ticket_id in sorted(sealed):
            self.assertEqual([], tickets_generations.seal_findings(ticket_id, sealed[ticket_id]))

        self.assertEqual([], cutcheck.graph_findings(complete))
        self.assertEqual([], cutcheck.graph_findings(sealed))

        later_cut = tickets_generations.draft_snapshot(
            "S", {"S": assignment("S", "orch-decompose")}, ordinal=2
        )
        self.assertIn("root:S:1:", later_cut["root_generation"])
        self.assertIn("cut:S:2:", later_cut["cut_generation"])

        changed_root = dict(rooted)
        changed_root["R"] = changed_root["R"].replace(
            "Deliver the observable result for R.",
            "Deliver a semantically changed result for R.",
        )
        with self.assertRaisesRegex(
            tickets_generations.GenerationError,
            "successor run.*accepted predecessor result",
        ):
            tickets_generations.draft_snapshot("R", changed_root, ordinal=2)

        forged_second_root = rooted["R"].replace(
            "root:R:1:", "root:R:2:"
        ).replace("cut:R:1:", "cut:R:2:")
        self.assertIn(
            "root-generation-successor-required",
            {
                finding["code"]
                for finding in tickets_generations.seal_findings(
                    "R", forged_second_root
                )
            },
        )

    def test_two_executor_members_cannot_validate_or_seal_without_the_composite_gate(self):
        snapshot = {
            "R": assignment("R", "orch-decompose"),
            "R.01": assignment("R.01", "orch-execute"),
            "R.02": assignment("R.02", "orch-execute"),
        }
        draft = tickets_generations.draft_snapshot("R", snapshot)
        with self.assertRaisesRegex(tickets_generations.GenerationError, "composite gate"):
            tickets_generations.validate_draft("R", snapshot, draft)
        with self.assertRaisesRegex(tickets_generations.GenerationError, "composite gate"):
            tickets_generations.seal_assignments(
                "R", snapshot, draft,
                {
                    "cut_generation": draft["cut_generation"],
                    "draft_digest": "unreachable",
                    "root_generation": draft["root_generation"],
                    "state": "validated",
                },
            )

    def test_clean_gate_uses_attributed_join_noop_and_opens_verification(self):
        self.dispatch(
            "new", "clean", "R", "--executor", "orch-decompose",
            "--goal", "Deliver the integrated result.", "--context", "Use two members.",
            "--pack", "orch-code-pack", "--independence", "gate",
        )
        for suffix in ("01", "02"):
            self.dispatch(
                "new", "clean", f"R.{suffix}", "--executor", "orch-execute",
                "--goal", f"Deliver member {suffix}.", "--context", "Feed the root.",
                "--pack", "orch-code-pack", "--independence", "gate",
                "--isolation", "required",
            )
        self.dispatch("stamp-generation", "clean", "R")
        self.dispatch("gate", "clean", "R")
        validated = self.dispatch("draft-validate", "clean", "R")
        self.dispatch(
            "seal", "clean", "R", "--cut-generation",
            validated["draft_validation"]["cut_generation"],
        )
        self.dispatch("ready", "--run", "clean")
        for suffix in ("01", "02"):
            ticket_id = f"R.{suffix}"
            candidate = str(git_checkout(
                Path(self.temporary.name) / f"candidate-{suffix}"
            ))
            ticket = Path(self.temporary.name) / "tickets" / "clean" / f"{ticket_id}.md"
            established = ticket.read_text(encoding="utf-8")
            for key, value in (
                ("workspace_branch", f"candidate-{suffix}"),
                ("workspace_baseline", "0123456789abcdef clean"),
            ):
                established = tickets._set_frontmatter_field(established, key, value)
            ticket.write_text(established, encoding="utf-8")
            opened = self.open_attempt(
                "clean", ticket_id, f"member-{suffix}", f"member-D{suffix}"
            )
            self.committed_launch(
                "clean", ticket_id, f"member-D{suffix}", workspace=candidate,
            )
            self.dispatch(
                "result", "clean", ticket_id,
                "--assignment-seal", opened["assignment_seal"],
                "--dispatch-id", f"member-D{suffix}",
                "--record-id", "result-1", "--by", f"member-{suffix}",
                "--section", "Result", "--text", "done",
            )
            self.commit_outcome(
                "clean", ticket_id, opened, f"member-{suffix}", f"member-D{suffix}"
            )
            self.dispatch(
                "dispatch-join", "clean", ticket_id,
                "--assignment-seal", opened["assignment_seal"],
                "--dispatch-id", f"member-D{suffix}",
                "--outcome-record-id", "outcome", "--by", "root-join",
                "--status", "complete",
            )
        ready = self.dispatch("ready", "--run", "clean")
        critique_id = "R.gate.critique.code"
        self.assertIn(critique_id, {item["id"] for item in ready["ready"]})
        opened = self.open_attempt("clean", critique_id, "critic", "critic-D1")
        artifact = "git:" + subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            capture_output=True, check=True,
        ).stdout.strip()
        launched = self.committed_launch(
            "clean", critique_id, "critic-D1", workspace=str(ROOT),
            artifact=artifact, record=False,
        )
        # by path and tip identity, never a second copy of the ledger
        self.assertIn("Immutable review ledger: read", launched["prompt"])
        self.assertIn("tip is GatePlan", launched["prompt"])
        self.assertNotIn('"kind":"GatePlan"', launched["prompt"])
        # the root Goal three proven verdicts turned on, named by path
        self.assertIn(str(Path(self.temporary.name) / "tickets" / "clean" / "R.md"),
                      launched["prompt"])
        self.commit_outcome("clean", critique_id, opened, "critic", "critic-D1")
        self.dispatch(
            "dispatch-join", "clean", critique_id,
            "--assignment-seal", opened["assignment_seal"],
            "--dispatch-id", "critic-D1",
            "--outcome-record-id", "outcome", "--by", "root-join",
            "--status", "complete", *self.accepted_file(critique_id, "[]"),
        )
        critique = (
            Path(self.temporary.name) / "tickets" / "clean" / f"{critique_id}.md"
        ).read_text(encoding="utf-8")
        review = json.loads(_parse_frontmatter(critique)["review_v1"])
        self.assertEqual(
            ["GatePlan", "CritiqueAdjudication"],
            [record["kind"] for record in review["records"]],
        )
        self.assertEqual(artifact, review["records"][0]["artifact"])
        self.assertEqual(str(ROOT.resolve()), review["records"][0]["workspace"])
        self.assertEqual([], review["records"][1]["accepted"])
        self.assertEqual(
            review["records"][0]["identity"],
            review["records"][1]["predecessor"],
        )
        ready = self.dispatch("ready", "--run", "clean")
        self.assertIn("R.gate.repair", {item["id"] for item in ready["ready"]})

        closed = self.dispatch(
            "join-noop-repair", "clean", "R.gate.repair", "--by", "root-join"
        )
        self.assertEqual("root-join", closed["join_noop_repair"]["by"])
        # The gate ends at repair: the fresh outside check is the root's own
        # `done` predicate, run by land, and no verify stub is materialized.
        ready = self.dispatch("ready", "--run", "clean")
        self.assertNotIn("R.gate.verify", {item["id"] for item in ready["ready"]})
        repair = (
            Path(self.temporary.name) / "tickets" / "clean" / "R.gate.repair.md"
        ).read_text(encoding="utf-8")
        self.assertIn("status: complete", repair)
        self.assertIn("### Written by `root-join`\n\n[]", repair)
        repair_review = json.loads(_parse_frontmatter(repair)["review_v1"])
        self.assertEqual(
            ["GatePlan", "CritiqueAdjudication", "RepairOutcome"],
            [record["kind"] for record in repair_review["records"]],
        )
        self.assertTrue(repair_review["records"][-1]["no_op"])
        self.assertEqual(artifact, repair_review["records"][-1]["artifact"])
        # The immutable ledger ends there too: `Verification` is not a record
        # kind any more, so nothing can append one after the repair.
        self.assertNotIn("Verification", tickets_shapes.REVIEW_RECORD_COMMON_VALUES["kind"])

    def test_gate_stubs_freeze_pack_isolation_and_lens_order(self):
        self.dispatch(
            "new", "ordered", "R", "--executor", "orch-decompose",
            "--goal", "Deliver the integrated result.", "--context", "Use two members.",
            "--pack", "orch-code-pack", "--independence", "gate",
        )
        for suffix in ("01", "02"):
            self.dispatch(
                "new", "ordered", f"R.{suffix}", "--executor", "orch-execute",
                "--goal", f"Deliver member {suffix}.", "--context", "Feed the root.",
                "--pack", "orch-code-pack", "--independence", "gate",
                "--isolation", "required",
            )
        self.dispatch("stamp-generation", "ordered", "R")
        self.dispatch(
            "gate", "ordered", "R", "--ordered-lens-bundle", "security,code",
        )
        run_dir = Path(self.temporary.name) / "tickets" / "ordered"
        security = _parse_frontmatter(
            (run_dir / "R.gate.critique.security.md").read_text(encoding="utf-8")
        )
        code = _parse_frontmatter(
            (run_dir / "R.gate.critique.code.md").read_text(encoding="utf-8")
        )
        repair = _parse_frontmatter(
            (run_dir / "R.gate.repair.md").read_text(encoding="utf-8")
        )
        for record in (security, code, repair):
            self.assertEqual("orch-code-pack", record["pack"])
            self.assertEqual("none", record["isolation"])
        self.assertEqual("0", security["review_order"])
        self.assertEqual("1", code["review_order"])

    def test_distinct_checker_records_the_same_immutable_adjudication_carrier(self):
        self.dispatch(
            "new", "checker", "R", "--executor", "orch-execute",
            "--goal", "Deliver the checked result.",
            "--context", "The artifact and evidence are authoritative.",
            "--pack", "orch-code-pack", "--isolation", "required",
            "--independence", "checker",
        )
        self.seal("checker", "R")
        self.dispatch("ready", "--run", "checker")
        ticket = Path(self.temporary.name) / "tickets" / "checker" / "R.md"
        established = ticket.read_text(encoding="utf-8")
        for key, value in (
            ("workspace_branch", "integration"),
            ("workspace_baseline", "0123456789abcdef clean"),
        ):
            established = tickets._set_frontmatter_field(established, key, value)
        ticket.write_text(established, encoding="utf-8")
        opened = self.open_attempt("checker", "R", "worker", "worker-D1")
        self.committed_launch("checker", "R", "worker-D1", workspace=str(ROOT))
        self.commit_outcome("checker", "R", opened, "worker", "worker-D1")
        self.dispatch(
            "dispatch-join", "checker", "R",
            "--assignment-seal", opened["assignment_seal"],
            "--dispatch-id", "worker-D1", "--outcome-record-id", "outcome",
            "--by", "root-join", "--status", "complete",
        )
        artifact = "git:" + subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            capture_output=True, check=True,
        ).stdout.strip()
        before = ticket.read_bytes()
        refused = tickets._dispatch([
            "check", "checker", "R", "--by", "checker-a",
            "--artifact", artifact, "--findings", "[]", "--accepted", "[]",
        ])
        self.assertIn("usage: check", refused["error"])
        self.assertEqual(before, ticket.read_bytes())

        stage = self.dispatch("checker-stage", "checker", "R")
        self.assertEqual("R.check", stage["checker_stage"]["ticket"])
        ready = self.dispatch("ready", "--run", "checker")
        self.assertIn("R.check", {item["id"] for item in ready["ready"]})
        stage_opened = self.open_attempt(
            "checker", "R.check", "checker-a", "checker-D1"
        )
        self.committed_launch(
            "checker", "R.check", "checker-D1", workspace=str(ROOT),
            artifact=artifact, record=False,
        )
        findings = json.dumps([{
            "blocking": True,
            "class": "correctness",
            "evidence": ["test-x failed"],
            "goal_impact": "The target Goal is false.",
            "id": "B1",
            "repair": "Repair test-x.",
            "summary": "test-x is red — repair required.",
        }], sort_keys=True, separators=(",", ":"))
        self.dispatch(
            "result", "checker", "R.check",
            "--assignment-seal", stage_opened["assignment_seal"],
            "--dispatch-id", "checker-D1", "--record-id", "feedback-1",
            "--by", "checker-a", "--section", "Feedback", "--text", findings,
        )
        self.commit_outcome(
            "checker", "R.check", stage_opened, "checker-a", "checker-D1"
        )
        first_join = self.dispatch(
            "dispatch-join", "checker", "R.check",
            "--assignment-seal", stage_opened["assignment_seal"],
            "--dispatch-id", "checker-D1", "--outcome-record-id", "outcome",
            "--by", "root-join", "--status", "complete",
            *self.accepted_file("R.check", findings),
        )
        equivalent = json.dumps(json.loads(findings), ensure_ascii=False, indent=2)
        replayed_join = self.dispatch(
            "dispatch-join", "checker", "R.check",
            "--assignment-seal", stage_opened["assignment_seal"],
            "--dispatch-id", "checker-D1", "--outcome-record-id", "outcome",
            "--by", "root-join", "--status", "complete",
            *self.accepted_file("R.check-equivalent", equivalent),
        )
        self.assertEqual(first_join, replayed_join)
        stage_path = (
            Path(self.temporary.name) / "tickets" / "checker" / "R.check.md"
        )
        anchored_bytes = stage_path.read_bytes()
        stage_text = anchored_bytes.decode("utf-8")
        rewritten = json.loads(_parse_frontmatter(stage_text)["review_v1"])
        rewritten_record = rewritten["records"][-1]
        rewritten_record["accepted"] = []
        rewritten_record["identity"] = tickets_review._digest({
            key: value for key, value in rewritten_record.items() if key != "identity"
        })
        stage_path.write_text(
            tickets._set_frontmatter_field(
                stage_text, "review_v1", tickets_review.canonical_json(rewritten),
            ),
            encoding="utf-8",
        )
        unanchored = tickets._dispatch([
            "check", "checker", "R", "--stage", "R.check",
        ])
        self.assertEqual("dispatch-record-invalid", unanchored["code"])
        stage_path.write_bytes(anchored_bytes)
        checked = self.dispatch(
            "check", "checker", "R", "--stage", "R.check",
        )
        self.assertEqual("checker-a", checked["check"]["checked_by"])
        data = _parse_frontmatter(ticket.read_text(encoding="utf-8"))
        self.assertEqual("R.check", data["review_stage"])
        self.assertNotIn("review_v1", data)
        stage_text = stage_path.read_text(encoding="utf-8")
        review = json.loads(_parse_frontmatter(stage_text)["review_v1"])
        self.assertEqual(
            ["GatePlan", "CritiqueAdjudication"],
            [record["kind"] for record in review["records"]],
        )
        self.assertEqual("checker", review["records"][0]["mode"])
        self.assertEqual("orch-code-pack", review["records"][0]["pack"])
        self.assertEqual(json.loads(findings), review["records"][1]["accepted"])
        self.assertEqual("checker-a", review["records"][1]["adjudicated_by"])
        self.assertEqual(
            review["records"][0]["identity"],
            review["records"][1]["predecessor"],
        )

        continued = self.dispatch("gate", "checker", "R")
        self.assertEqual(["R.gate.repair"], continued["gate"]["tickets"])
        self.assertEqual(
            "replayed",
            self.dispatch("gate", "checker", "R")["gate"]["outcome"],
        )
        self.assertFalse(list(stage_path.parent.glob("R.gate.critique.*.md")))

        repair_path = stage_path.parent / "R.gate.repair.md"
        canonical_repair = repair_path.read_bytes()
        substituted = canonical_repair.decode("utf-8").replace(
            "Resolve accepted blockers for `R`",
            "Perform an unrelated operation for `R`",
        )
        substituted = tickets._set_frontmatter_field(
            substituted, "assignment_seal",
            tickets.assignment_digest("R.gate.repair", substituted),
        )
        repair_path.write_text(substituted, encoding="utf-8")
        replay_refused = tickets._dispatch(["gate", "checker", "R"])
        self.assertIn("different content", replay_refused["error"])
        substituted_ready = self.dispatch("ready", "--run", "checker")
        self.assertNotIn(
            "R.gate.repair",
            {item["id"] for item in substituted_ready["ready"]},
        )
        repair_skip = next(
            item for item in substituted_ready["skipped"]
            if item["id"] == "R.gate.repair"
        )
        self.assertIn(
            "ordinary-review-stage-mismatch",
            {item["code"] for item in repair_skip["findings"]},
        )
        repair_path.write_bytes(canonical_repair)

        ready = self.dispatch("ready", "--run", "checker")
        self.assertIn(
            "R.gate.repair", {item["id"] for item in ready["ready"]}, ready,
        )
        repair_opened = self.open_attempt(
            "checker", "R.gate.repair", "repairer", "repair-D1"
        )
        repair_launch = self.committed_launch(
            "checker", "R.gate.repair", "repair-D1", workspace=str(ROOT),
            artifact=artifact, record=False,
        )
        self.assertIn(review["records"][1]["identity"], repair_launch["prompt"])
        repair_outcome = {
            "assignment_seal": repair_opened["assignment_seal"],
            "by": "repairer", "dispatch_id": "repair-D1",
            "evidence": {
                "Result": "Repaired every accepted checker blocker.",
                "Verification": "Targeted repair checks are green.",
                "Feedback": "[]", "Risks": "[]", "Handoff": "",
            },
            "id": "R.gate.repair", "outcome_record_id": "outcome",
            "protocol": "orchflows.dispatch.v1", "run": "checker",
        }
        self.dispatch(
            "dispatch-outcome", "checker", "R.gate.repair",
            *self.evidence_flags(
                repair_outcome["id"], repair_outcome["dispatch_id"],
                repair_outcome["evidence"],
            ),
        )
        self.dispatch(
            "dispatch-join", "checker", "R.gate.repair",
            "--assignment-seal", repair_opened["assignment_seal"],
            "--dispatch-id", "repair-D1", "--outcome-record-id", "outcome",
            "--by", "root-join", "--status", "complete", "--artifact", artifact,
        )
        repair_text = (
            stage_path.parent / "R.gate.repair.md"
        ).read_text(encoding="utf-8")
        repair_review = json.loads(_parse_frontmatter(repair_text)["review_v1"])
        self.assertEqual(
            [record["identity"] for record in review["records"]],
            [record["identity"] for record in repair_review["records"][:2]],
        )
        self.assertEqual("RepairOutcome", repair_review["records"][-1]["kind"])
        # The continuation ends at the repair. The fresh outside check the
        # checker's acceptance used to materialize is the target's own `done`
        # predicate, run by land in the integrated tree, so no verify stage is
        # derived and none can be made ready.
        self.assertFalse((stage_path.parent / "R.gate.verify.md").exists())
        ready = self.dispatch("ready", "--run", "checker")
        self.assertNotIn("R.gate.verify", {item["id"] for item in ready["ready"]})

    def test_frontier_guidance_distinguishes_all_three_review_states(self):
        skill = (
            ROOT / "skills" / "engines" / "orch-frontier" / "SKILL.md"
        ).read_text(encoding="utf-8")
        for phrase in (
            "accepted checked target",
            "clean checked target",
            "gate-deferred root",
        ):
            self.assertIn(phrase, skill)
        self.assertNotIn("Gate-deferred and checked tickets do not", skill)

    def test_checker_stage_refuses_a_packless_target_without_state_mutation(self):
        self.dispatch(
            "new", "packless-checker", "R", "--executor", "orch-check",
            "--goal", "Deliver the checked result.",
            "--context", "The artifact and evidence are authoritative.",
            "--pack", "orch-code-pack",
            "--isolation", "required",
        )
        self.seal("packless-checker", "R")
        run_dir = Path(self.temporary.name) / "tickets" / "packless-checker"
        target = run_dir / "R.md"
        target.write_text(
            _remove_frontmatter_field(target.read_text(encoding="utf-8"), "pack"),
            encoding="utf-8",
        )
        before = target.read_bytes()

        refused = tickets._dispatch(["checker-stage", "packless-checker", "R"])

        self.assertIn("pack", refused["error"])
        self.assertEqual(before, target.read_bytes())
        self.assertFalse((run_dir / "R.check.md").exists())

    def test_review_schemas_reject_field_deletion_and_noop_bypass(self):
        artifact = "git:" + subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            capture_output=True, check=True,
        ).stdout.strip()
        plan = tickets_review._record(
            "GatePlan", None, artifact=artifact,
            criteria=[{
                "identity": "sha256:criterion", "lens": "code",
                "order": 0, "ticket": "R.check",
            }],
            isolation="none", mode="checker", pack="orch-code-pack",
            root="R", workspace=str(ROOT.resolve()),
        )
        finding = {
            "blocking": True, "class": "correctness",
            "evidence": ["test-x failed"],
            "goal_impact": "The Goal is false.", "id": "B1",
            "repair": "Repair test-x.", "summary": "test-x is red.",
        }
        member = tickets_review._record(
            "CritiqueAdjudication", plan["identity"], accepted=[finding],
            adjudicated_by="checker-a", artifact=artifact,
            findings=[finding], lens="code",
        )
        aggregate = tickets_review._record(
            "CritiqueAdjudication", plan["identity"], accepted=[finding],
            adjudicated_by="system:aggregate", adjudications=[member],
            artifact=artifact, findings=[finding], lens="*",
        )
        state = {"protocol": "orchflows.review.v1", "records": [plan, aggregate]}
        tickets_review.review_records(state)

        missing_authority = json.loads(tickets_review.canonical_json(state))
        del missing_authority["records"][1]["adjudicated_by"]
        record = missing_authority["records"][1]
        record["identity"] = tickets_review._digest({
            key: value for key, value in record.items() if key != "identity"
        })
        with self.assertRaises(tickets_review.ReviewError):
            tickets_review.review_records(missing_authority)

        rewritten_accepted = json.loads(tickets_review.canonical_json(state))
        record = rewritten_accepted["records"][1]
        record["accepted"] = []
        record["identity"] = tickets_review._digest({
            key: value for key, value in record.items() if key != "identity"
        })
        with self.assertRaises(tickets_review.ReviewError):
            tickets_review.review_records(rewritten_accepted)

        with self.assertRaises(tickets_review.ReviewError):
            tickets_review.repair_outcome(
                state, artifact, "no change", "root", no_op=True,
                workspace=str(ROOT),
            )

    def test_downstream_waits_for_checker_but_checker_stage_can_start(self):
        self.assertIs(tickets_lifecycle.readiness_facts, tickets_readiness.readiness_facts)
        target = {
            "id": "R", "status": "complete", "independence": "checker",
            "checked_by": "",
        }
        stage = {"id": "R.check", "status": "pending", "depends_on": ["R"]}
        downstream = {"id": "R.next", "status": "pending", "depends_on": ["R"]}
        tickets_by_id = {"R": target, "R.check": stage, "R.next": downstream}

        self.assertTrue(
            tickets_readiness.readiness_facts(stage, tickets_by_id)[
                "dependencies_complete"
            ]
        )
        self.assertFalse(
            tickets_readiness.readiness_facts(downstream, tickets_by_id)[
                "dependencies_complete"
            ]
        )
        target["checked_by"] = "checker-a"
        self.assertTrue(
            tickets_readiness.readiness_facts(downstream, tickets_by_id)[
                "dependencies_complete"
            ]
        )

    def test_decompose_builds_the_complete_gate_bearing_draft_before_validation(self):
        skill = (ROOT / "skills" / "kernel" / "orch-decompose" / "SKILL.md").read_text(encoding="utf-8")
        commands = ("tickets.py gate", "cutcheck.py", "tickets.py draft-validate", "tickets.py seal")
        positions = [skill.index(command) for command in commands]
        self.assertEqual(sorted(positions), positions)
        for field in ("`root_generation`", "`executor`", "`assembly`", "`independence: gate`"):
            self.assertIn(field, skill)

    def test_removed_fix_composition_has_no_instantiation_alias(self):
        result = tickets._dispatch([
            "instantiate", str(ROOT / "compositions" / "fix"), "--run", "fix",
            "--set", "failure=boom", "--set", "workspace=.",
        ])
        self.assertIn("template directory not found", result["error"])
        self.assertNotIn("executor-unregistered", result["error"])
        self.assertFalse((ROOT / "compositions" / "fix").exists())

    def test_gate_routes_actual_overlap_to_integration(self):
        self.dispatch("new", "gate", "R", "--executor", "orch-decompose", "--goal", "Deliver the result.", "--context", "Two candidates may touch one path.", "--pack", "orch-code-pack", "--independence", "gate")
        for suffix in ("01", "02"):
            self.dispatch("new", "gate", f"R.{suffix}", "--executor", "orch-execute", "--goal", f"Deliver candidate {suffix}.", "--context", "The candidate feeds the integrated result.", "--pack", "orch-code-pack", "--independence", "gate", "--isolation", "required")
        self.dispatch("stamp-generation", "gate", "R")
        self.dispatch("gate", "gate", "R")
        repair = "\n".join(path.read_text(encoding="utf-8") for path in (Path(self.temporary.name) / "tickets" / "gate").glob("R.gate.*.md"))
        self.assertIn("actual overlapping candidate diffs", repair)
        self.assertIn("ordinary Git conflicts", repair)

    def test_execute_owns_test_choice(self):
        self.dispatch(
            "new", "tdd", "R", "--executor", "orch-execute",
            "--goal", "Correct the observable behavior.",
            "--context", "The repository supplies the implementation facts.",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.seal("tdd", "R")
        self.dispatch("ready", "--run", "tdd")
        ticket = Path(self.temporary.name) / "tickets" / "tdd" / "R.md"
        established = ticket.read_text(encoding="utf-8")
        for key, value in (
            ("workspace_branch", "candidate-branch"),
            ("workspace_baseline", "0123456789abcdef clean"),
        ):
            established = tickets._set_frontmatter_field(established, key, value)
        ticket.write_text(established, encoding="utf-8")
        opened = self.open_attempt("tdd", "R", "worker", "tdd-D1")
        prompt = self.committed_launch(
            "tdd", "R", opened["dispatch_id"], workspace="C:/candidate",
        )["prompt"]
        self.assertRegex(prompt.lower(), r"choose the implementation,\s*tests, and verification")
        self.assertNotIn("oracle_class", prompt)

    def test_content_pack_preserves_whole_artifact_direct_route(self):
        pack = (ROOT / "packs" / "orch-content-pack" / "SKILL.md").read_text(encoding="utf-8")
        craft = (ROOT / "packs" / "orch-content-pack" / "references" / "craft.md").read_text(encoding="utf-8")
        text = (pack + "\n" + craft).lower()
        self.assertIn("whole", text)
        self.assertIn("direct", text)
        self.assertIn("one executor", text)

    def test_live_protocol_surfaces_exclude_removed_schema(self):
        forbidden = ("write_scope", "excluded_actions", "## Objective", "## Fixed inputs", "## Completion test", "## Return fields")
        paths = [ROOT / "contracts" / "work-item.md", *sorted((ROOT / "scripts").glob("tickets*.py")), *sorted((ROOT / "compositions").glob("**/*.md"))]
        findings = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            findings.extend(f"{path.relative_to(ROOT)}:{token}" for token in forbidden if token in text)
        self.assertEqual([], findings)

        evolution_requirements = {
            ROOT / "contracts" / "work-item.md": (
                "successor run", "accepted predecessor result identity",
                "not rewritten",
            ),
            ROOT / "rules" / "topology.md": (
                "`root_generation` ordinal is `1`", "cut generations",
                "accepted predecessor result identity", "not rewritten",
            ),
            ROOT / "rules" / "delegation.md": (
                "semantic-root change", "successor run",
                "accepted predecessor result identity",
            ),
            ROOT / "skills" / "workflows" / "orch-outline" / "SKILL.md": (
                "semantic-root change", "successor run",
                "accepted predecessor result identity", "unsupported",
            ),
            ROOT / "docs" / "vocabulary.md": (
                "run-local root identity", "successor run",
                "accepted predecessor result identity",
            ),
        }
        for path, required in evolution_requirements.items():
            text = " ".join(path.read_text(encoding="utf-8").split())
            for phrase in required:
                with self.subTest(path=path.relative_to(ROOT), phrase=phrase):
                    self.assertIn(phrase, text)
        self.assertNotIn(
            "post-seal assignment change is a new generation",
            " ".join(
                (ROOT / "skills" / "workflows" / "orch-outline" / "SKILL.md")
                .read_text(encoding="utf-8")
                .split()
            ),
        )
        self.assertNotIn(
            "changing sealed assignment fields creates a new assignment generation",
            " ".join(
                (ROOT / "docs" / "vocabulary.md")
                .read_text(encoding="utf-8")
                .split()
            ),
        )

    def test_result_contract_binds_records_to_the_current_claim_writer(self):
        result_contract = (ROOT / "contracts" / "result.md").read_text(encoding="utf-8")
        work_item = (ROOT / "contracts" / "work-item.md").read_text(encoding="utf-8")
        for phrase in (
            "exactly one canonical writer attribution",
            "dispatch attempt's recorded owner",
            "one atomic write",
            "never changes lifecycle state",
        ):
            self.assertIn(phrase, result_contract)
        for field in ("`assignment_seal`", "`dispatch_id`", "`record_id`"):
            self.assertIn(field, work_item)


if __name__ == "__main__":
    unittest.main()
