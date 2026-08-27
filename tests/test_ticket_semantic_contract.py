"""Focused regressions for the sole semantic ticket contract."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import cutcheck
from scripts import tickets
from scripts import tickets_generations
from scripts.tickets_format import _parse_frontmatter, _sections
from scripts.tickets_issue_render import _render_ticket
from scripts import workspace

ROOT = Path(__file__).resolve().parents[1]


def assignment(ticket_id, executor, dependencies=(), *, root_generation=None):
    fields = {
        "id": ticket_id,
        "run": "cut",
        "status": "pending",
        "admission": "pending",
        "executor": executor,
        "pack": "orch-code-pack",
        "independence": "gate",
        "depends_on": list(dependencies),
        "isolation": "required" if executor == "orch-tdd" else "none",
        "bound": "30m",
        "claimed_by": "",
        "claimed_at": "",
        "root_generation": root_generation,
    }
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

    def accept_packet(self, run, ticket_id, by, dispatch_id, workspace=None):
        packet_args = [
            "dispatch-packet", run, ticket_id, "--dispatch-id", dispatch_id,
            "--reply-to", "root", "--form", "reference",
        ]
        if workspace is not None:
            packet_args.extend(("--workspace", workspace))
        packet = self.dispatch(*packet_args)["packet"]
        receive_args = [
            "dispatch-receive", "--content",
            json.dumps(packet, sort_keys=True, separators=(",", ":")),
            "--role", packet["role"], "--profile", packet["profile"],
            "--by", by, "--reply-to", "root",
        ]
        if workspace is not None:
            receive_args.extend(("--workspace", workspace))
        self.dispatch(*receive_args)
        return packet

    def commit_outcome(self, run, ticket_id, opened, by, dispatch_id, status="complete"):
        content = {
            "assignment_seal": opened["assignment_seal"],
            "by": by,
            "dispatch_id": dispatch_id,
            "evidence": {
                "Result": "closing result delta",
                "Verification": "closing verification delta",
                "Feedback": "closing feedback delta: []",
                "Risks": "closing risk delta: []", "Handoff": "",
            },
            "id": ticket_id, "outcome_record_id": "outcome",
            "protocol": "orchflows.dispatch.v1", "run": run, "status": status,
        }
        return self.dispatch(
            "dispatch-outcome", run, ticket_id, "--content",
            json.dumps(content, sort_keys=True, separators=(",", ":")),
        )

    def test_goal_context_only_direct_root_lifecycle(self):
        self.dispatch(
            "new", "direct", "R1", "--executor", "orch-edit",
            "--goal", "Create the observable artifact.",
            "--context", "No exceptional constraints.",
        )
        self.seal("direct", "R1")
        ready = self.dispatch("ready", "--run", "direct")
        self.assertEqual(["R1"], [item["id"] for item in ready["ready"]])
        opened = self.open_attempt("direct", "R1", "worker", "direct-D1")
        packet = self.dispatch(
            "dispatch-packet", "direct", "R1", "--dispatch-id", opened["dispatch_id"],
            "--reply-to", "root",
        )["packet"]
        self.assertIn("Suggested files are non-binding", packet["prompt"])
        text = (Path(self.temporary.name) / "tickets" / "direct" / "R1.md").read_text(encoding="utf-8")
        self.assertEqual({"Goal", "Context", "Result", "Verification", "Feedback", "Risks"}, set(_sections(text)))

    def test_suggested_files_do_not_limit_candidate_paths(self):
        self.dispatch(
            "new", "suggested", "R1", "--executor", "orch-tdd",
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

    def test_packet_filing_command_carries_claimant_and_writes_the_ticket(self):
        self.dispatch(
            "new", "packet", "R1", "--executor", "orch-edit",
            "--goal", "Create the artifact.", "--context", "Use repository facts.",
        )
        self.seal("packet", "R1")
        self.dispatch("ready", "--run", "packet")
        opened = self.open_attempt("packet", "R1", "worker", "packet-D1")
        prompt = self.accept_packet(
            "packet", "R1", "worker", "packet-D1"
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
        argv[argv.index("TEXT")] = "filed from emitted packet"
        filed = self.dispatch(*argv)
        self.assertEqual("worker", filed["result"]["by"])
        ticket = (
            Path(self.temporary.name) / "tickets" / "packet" / "R1.md"
        ).read_text(encoding="utf-8")
        self.assertIn("### Written by `worker`\n\nfiled from emitted packet", ticket)

    def test_decomposed_root_uses_same_semantic_shape(self):
        self.dispatch("new", "cut", "R", "--executor", "orch-decompose", "--goal", "Deliver the result.", "--context", "Use the repository facts.")
        self.dispatch("new", "cut", "R.01", "--executor", "orch-edit", "--goal", "Produce one component.", "--context", "It feeds the root result.")
        self.seal("cut", "R")
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
            "R.01": assignment("R.01", "orch-tdd", root_generation=inherited),
            "R.02": assignment("R.02", "orch-tdd", root_generation=inherited),
            "R.gate.critique.code": assignment(
                "R.gate.critique.code", "orch-critique", ("R.01", "R.02"),
                root_generation=inherited,
            ),
            "R.gate.repair": assignment(
                "R.gate.repair", "orch-repair", ("R.gate.critique.code",),
                root_generation=inherited,
            ),
            "R.gate.verify": assignment(
                "R.gate.verify", "orch-verify", ("R.gate.repair",),
                root_generation=inherited,
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

    def test_two_executor_members_cannot_validate_or_seal_without_the_composite_gate(self):
        snapshot = {
            "R": assignment("R", "orch-decompose"),
            "R.01": assignment("R.01", "orch-tdd"),
            "R.02": assignment("R.02", "orch-tdd"),
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
                "new", "clean", f"R.{suffix}", "--executor", "orch-tdd",
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
            candidate = f"C:/candidate-{suffix}"
            ticket = Path(self.temporary.name) / "tickets" / "clean" / f"{ticket_id}.md"
            established = ticket.read_text(encoding="utf-8")
            for key, value in (
                ("workspace_path", candidate),
                ("workspace_branch", f"candidate-{suffix}"),
                ("workspace_baseline", "0123456789abcdef clean"),
            ):
                established = tickets._set_frontmatter_field(established, key, value)
            ticket.write_text(established, encoding="utf-8")
            opened = self.open_attempt(
                "clean", ticket_id, f"member-{suffix}", f"member-D{suffix}"
            )
            self.accept_packet(
                "clean", ticket_id, f"member-{suffix}", f"member-D{suffix}",
                workspace=candidate,
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
            )
        ready = self.dispatch("ready", "--run", "clean")
        critique_id = "R.gate.critique.code"
        self.assertIn(critique_id, {item["id"] for item in ready["ready"]})
        opened = self.open_attempt("clean", critique_id, "critic", "critic-D1")
        artifact = "git:" + "a" * 40
        packet = self.dispatch(
            "dispatch-packet", "clean", critique_id,
            "--dispatch-id", "critic-D1", "--reply-to", "root",
            "--artifact", artifact,
        )["packet"]
        self.assertIn('"kind":"GatePlan"', packet["prompt"])
        self.dispatch(
            "dispatch-receive", "--content",
            json.dumps(packet, sort_keys=True, separators=(",", ":")),
            "--role", packet["role"], "--profile", packet["profile"],
            "--by", "critic", "--reply-to", "root",
        )
        self.dispatch(
            "result", "clean", critique_id,
            "--assignment-seal", opened["assignment_seal"],
            "--dispatch-id", "critic-D1", "--record-id", "feedback-1",
            "--by", "critic",
            "--section", "Feedback", "--text", "[]",
        )
        self.commit_outcome("clean", critique_id, opened, "critic", "critic-D1")
        self.dispatch(
            "dispatch-join", "clean", critique_id,
            "--assignment-seal", opened["assignment_seal"],
            "--dispatch-id", "critic-D1",
            "--outcome-record-id", "outcome", "--by", "root-join",
            "--accepted", "[]",
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
        ready = self.dispatch("ready", "--run", "clean")
        self.assertIn("R.gate.verify", {item["id"] for item in ready["ready"]})
        repair = (
            Path(self.temporary.name) / "tickets" / "clean" / "R.gate.repair.md"
        ).read_text(encoding="utf-8")
        self.assertIn("status: complete", repair)
        self.assertIn("claimed_by: root-join", repair)
        self.assertIn("### Written by `root-join`\n\n[]", repair)
        repair_review = json.loads(_parse_frontmatter(repair)["review_v1"])
        self.assertEqual(
            ["GatePlan", "CritiqueAdjudication", "RepairOutcome"],
            [record["kind"] for record in repair_review["records"]],
        )
        self.assertTrue(repair_review["records"][-1]["no_op"])
        self.assertEqual(artifact, repair_review["records"][-1]["artifact"])

        verify_id = "R.gate.verify"
        verify_opened = self.open_attempt(
            "clean", verify_id, "verifier", "verify-D1"
        )
        mismatch = tickets._dispatch([
            "dispatch-packet", "clean", verify_id,
            "--dispatch-id", "verify-D1", "--reply-to", "root",
            "--artifact", "git:" + "f" * 40,
        ])
        self.assertEqual("review-invalid", mismatch["code"])
        verify_packet = self.dispatch(
            "dispatch-packet", "clean", verify_id,
            "--dispatch-id", "verify-D1", "--reply-to", "root",
            "--artifact", artifact,
        )["packet"]
        self.assertIn('"kind":"RepairOutcome"', verify_packet["prompt"])
        self.dispatch(
            "dispatch-receive", "--content",
            json.dumps(verify_packet, sort_keys=True, separators=(",", ":")),
            "--role", verify_packet["role"],
            "--profile", verify_packet["profile"],
            "--by", "verifier", "--reply-to", "root",
        )
        verify_outcome = {
            "assignment_seal": verify_opened["assignment_seal"],
            "by": "verifier", "dispatch_id": "verify-D1",
            "evidence": {
                "Result": "verified fixed artifact",
                "Verification": "PASS: exact artifact checks are green",
                "Feedback": "[]", "Risks": "[]", "Handoff": "",
            },
            "id": verify_id, "outcome_record_id": "outcome",
            "protocol": "orchflows.dispatch.v1", "run": "clean",
            "status": "complete",
        }
        self.dispatch(
            "dispatch-outcome", "clean", verify_id, "--content",
            json.dumps(verify_outcome, sort_keys=True, separators=(",", ":")),
        )
        self.dispatch(
            "dispatch-join", "clean", verify_id,
            "--assignment-seal", verify_opened["assignment_seal"],
            "--dispatch-id", "verify-D1", "--outcome-record-id", "outcome",
            "--by", "root-join", "--artifact", artifact,
        )
        verify = (
            Path(self.temporary.name) / "tickets" / "clean" / f"{verify_id}.md"
        ).read_text(encoding="utf-8")
        verify_review = json.loads(_parse_frontmatter(verify)["review_v1"])
        verification = verify_review["records"][-1]
        self.assertEqual("Verification", verification["kind"])
        self.assertEqual("PASS", verification["verdict"])
        self.assertEqual(artifact, verification["artifact"])
        self.assertEqual(
            verify_review["records"][-2]["identity"],
            verification["predecessor"],
        )

    def test_gate_stubs_freeze_pack_isolation_and_lens_order(self):
        self.dispatch(
            "new", "ordered", "R", "--executor", "orch-decompose",
            "--goal", "Deliver the integrated result.", "--context", "Use two members.",
            "--pack", "orch-code-pack", "--independence", "gate",
        )
        for suffix in ("01", "02"):
            self.dispatch(
                "new", "ordered", f"R.{suffix}", "--executor", "orch-tdd",
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
            "new", "checker", "R", "--executor", "orch-tdd",
            "--goal", "Deliver the checked result.",
            "--context", "The artifact and evidence are authoritative.",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.seal("checker", "R")
        self.dispatch("ready", "--run", "checker")
        self.open_attempt("checker", "R", "worker", "worker-D1")
        ticket = Path(self.temporary.name) / "tickets" / "checker" / "R.md"
        artifact = "git:" + "b" * 40
        before = ticket.read_bytes()
        refused = tickets._dispatch([
            "check", "checker", "R", "--by", "checker-a",
        ])
        self.assertEqual("review-invalid", refused["code"])
        self.assertEqual(before, ticket.read_bytes())

        findings = '[{"evidence":"test-x failed","id":"B1"}]'
        checked = self.dispatch(
            "check", "checker", "R", "--by", "checker-a",
            "--artifact", artifact,
            "--findings", findings, "--accepted", findings,
        )
        self.assertEqual("checker-a", checked["check"]["checked_by"])
        data = _parse_frontmatter(ticket.read_text(encoding="utf-8"))
        review = json.loads(data["review_v1"])
        self.assertEqual(
            ["GatePlan", "CritiqueAdjudication"],
            [record["kind"] for record in review["records"]],
        )
        self.assertEqual("checker", review["records"][0]["mode"])
        self.assertEqual(json.loads(findings), review["records"][1]["accepted"])
        self.assertEqual(
            review["records"][0]["identity"],
            review["records"][1]["predecessor"],
        )

    def test_decompose_builds_the_complete_gate_bearing_draft_before_validation(self):
        skill = (ROOT / "skills" / "kernel" / "orch-decompose" / "SKILL.md").read_text(encoding="utf-8")
        commands = ("tickets.py gate", "cutcheck.py", "tickets.py draft-validate", "tickets.py seal")
        positions = [skill.index(command) for command in commands]
        self.assertEqual(sorted(positions), positions)
        for field in ("`root_generation`", "`executor`", "`assembly`", "`independence: gate`"):
            self.assertIn(field, skill)

    def test_fix_template_instantiates_current_sealed_format(self):
        result = self.dispatch(
            "instantiate", str(ROOT / "compositions" / "fix"), "--run", "fix",
            "--set", "failure=boom", "--set", "workspace=.",
        )
        self.assertEqual("root:00-reproduce", result["instantiate"]["generation"]["root_generation"].split(":1:")[0])
        for path in (Path(self.temporary.name) / "tickets" / "fix").glob("*.md"):
            sections = _sections(path.read_text(encoding="utf-8"))
            self.assertIn("Goal", sections)
            self.assertNotIn("Objective", sections)

    def test_gate_routes_actual_overlap_to_integration(self):
        self.dispatch("new", "gate", "R", "--executor", "orch-decompose", "--goal", "Deliver the result.", "--context", "Two candidates may touch one path.", "--pack", "orch-code-pack", "--independence", "gate")
        for suffix in ("01", "02"):
            self.dispatch("new", "gate", f"R.{suffix}", "--executor", "orch-tdd", "--goal", f"Deliver candidate {suffix}.", "--context", "The candidate feeds the integrated result.", "--pack", "orch-code-pack", "--independence", "gate", "--isolation", "required")
        self.dispatch("stamp-generation", "gate", "R")
        self.dispatch("gate", "gate", "R")
        repair = "\n".join(path.read_text(encoding="utf-8") for path in (Path(self.temporary.name) / "tickets" / "gate").glob("R.gate.*.md"))
        self.assertIn("actual overlapping candidate diffs", repair)
        self.assertIn("ordinary Git conflicts", repair)

    def test_tdd_executor_owns_test_choice(self):
        self.dispatch(
            "new", "tdd", "R", "--executor", "orch-tdd",
            "--goal", "Correct the observable behavior.",
            "--context", "The repository supplies the implementation facts.",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.seal("tdd", "R")
        self.dispatch("ready", "--run", "tdd")
        ticket = Path(self.temporary.name) / "tickets" / "tdd" / "R.md"
        established = ticket.read_text(encoding="utf-8")
        for key, value in (
            ("workspace_path", "C:/candidate"),
            ("workspace_branch", "candidate-branch"),
            ("workspace_baseline", "0123456789abcdef clean"),
        ):
            established = tickets._set_frontmatter_field(established, key, value)
        ticket.write_text(established, encoding="utf-8")
        opened = self.open_attempt("tdd", "R", "worker", "tdd-D1")
        prompt = self.dispatch(
            "dispatch-packet", "tdd", "R", "--dispatch-id", opened["dispatch_id"],
            "--reply-to", "root", "--workspace", "C:/candidate",
        )["packet"]["prompt"]
        self.assertIn("choose the implementation, tests, and verification", prompt.lower())
        self.assertNotIn("oracle_class", prompt)

    def test_content_pack_preserves_whole_artifact_direct_route(self):
        pack = (ROOT / "packs" / "orch-content-pack" / "SKILL.md").read_text(encoding="utf-8")
        slicing = (ROOT / "packs" / "orch-content-pack" / "references" / "slicing.md").read_text(encoding="utf-8")
        text = (pack + "\n" + slicing).lower()
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
