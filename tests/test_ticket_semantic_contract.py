"""Focused regressions for the sole semantic ticket contract."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import cutcheck
from tests._candidate_checkout import (
    git_checkout, record_established_workspace,
)
from tests import _retired_commands as retired_commands
from scripts import state_root
from scripts import tickets
from scripts import tickets_dispatch_launch as launch_module
from scripts import tickets_generations
from scripts import tickets_shapes
from scripts.tickets_format import (
    _parse_frontmatter, _remove_frontmatter_field, _sections, canonical_json,
)
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
        "isolation": "required" if executor == "orch-do" else "none",
        "bound": "30m",
        "root_generation": root_generation,
    }
    sections = [
        ("Goal", f"Deliver the observable result for {ticket_id}."),
        ("Context", "The root assignment and repository are authoritative."),
        ("Report", ""),
    ]
    return _render_ticket(fields, sections)


class SemanticTicketContractTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        # ORCHFLOWS_WORKTREES_HOME rides beside the sink: unset, a derived
        # candidate would hang off the parent of a bare tempdir -- the
        # machine-shared system temp root -- instead of staying inside
        # this fixture's own tree.
        self.environment = mock.patch.dict(os.environ, {
            state_root.ENV_VAR: self.temporary.name,
            "ORCHFLOWS_WORKTREES_HOME": str(Path(self.temporary.name) / "worktrees"),
        })
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def dispatch(self, *arguments):
        result = retired_commands.run(list(arguments))
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

    def launch(self, run, ticket_id, dispatch_id, workspace=None, record=True):
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
            run, ticket_id, host, dispatch_id=dispatch_id, workspace=workspace,
        )

    def committed_launch(self, *arguments, **facts) -> dict:
        committed = self.launch(*arguments, **facts)
        self.assertNotIn("error", committed, committed)
        return committed["launch"]

    def commit_outcome(self, run, ticket_id, opened, by, dispatch_id):
        """One free-text closing note; the envelope carries nothing typed."""

        return self.dispatch(
            "dispatch-outcome", run, ticket_id,
            "--note", f"closing note for {ticket_id}",
        )

    def test_a_long_assignment_is_issued_and_reaches_generation_stamping(self):
        """No length refuses a ticket: the planner owns what its child needs."""

        goal = " ".join(["word"] * 400)
        for executor in ("orch-do", "orch-judge"):
            run = "root-" + executor.removeprefix("orch-")
            with self.subTest(executor):
                created = retired_commands.run([
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
                stamped = retired_commands.run(["stamp-generation", run, "R"])
                self.assertNotIn("error", stamped, stamped)
                self.assertRegex(
                    stamped["stamp_generation"]["root_generation"],
                    r"^root:R:1:sha256:[0-9a-f]{64}$",
                )
                linted = retired_commands.run(["lint", run, "R"])
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
            "new", "unit-length", "R", "--executor", "orch-do",
            "--goal", "Deliver the run.", "--context", "[]",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        goal = " ".join(["word"] * 400)
        created = retired_commands.run([
            "new", "unit-length", "R.01", "--executor", "orch-judge",
            "--goal", goal, "--context", "[]", "--pack", "orch-code-pack",
        ])
        self.assertNotIn("error", created, created)

    def test_a_malformed_first_attempt_writes_no_run_directory(self):
        goal = " ".join(["word"] * 400)
        malformed = retired_commands.run([
            "new", "malformed-root", "R", "--executor", "orch-do",
            "--goal", goal,
        ])
        self.assertIn("error", malformed)
        run_dir = Path(self.temporary.name) / "tickets" / "malformed-root"
        self.assertFalse(run_dir.exists())
        accepted = retired_commands.run([
            "new", "malformed-root", "R", "--executor", "orch-do",
            "--goal", goal, "--context", "[]", "--pack", "orch-code-pack",
            "--isolation", "required",
        ])
        self.assertNotIn("error", accepted, accepted)

    def test_goal_context_only_direct_root_lifecycle(self):
        self.dispatch(
            "new", "direct", "R1", "--executor", "orch-do",
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
        self.assertIn("Details is the planner's guidance", launched["prompt"])
        text = (Path(self.temporary.name) / "tickets" / "direct" / "R1.md").read_text(encoding="utf-8")
        self.assertEqual({"Goal", "Context", "Report"}, set(_sections(text)))

    def test_preissue_lint_grades_the_projected_file_candidate(self):
        """`new --file` retired (routing-design M3): lint is the one reader

        left projecting a hand-authored file's pre-issue shape; a caller
        wanting it actually minted now uses `new`'s flags or a `do`/`judge`
        goal file instead.
        """
        source = Path(self.temporary.name) / "R1.md"
        draft = assignment("R1", "orch-do")
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

    def test_preissue_lint_refuses_a_file_identity_mismatch(self):
        source = Path(self.temporary.name) / "R1.md"
        draft = _remove_frontmatter_field(
            assignment("R1", "orch-do"), "admission"
        )
        source.write_text(draft, encoding="utf-8")
        before = source.read_bytes()

        linted = retired_commands.run(
            ["lint", "other-run", "R9", "--file", str(source)]
        )
        self.assertIn("placed as 'R9', but ticket file names 'R1'", linted["error"])
        self.assertEqual(before, source.read_bytes())

    def test_show_inspects_one_ticket_without_mutating_the_sink(self):
        self.dispatch(
            "new", "inspect-run", "R1", "--executor", "orch-do",
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
                refused = retired_commands.run(list(arguments))
                self.assertIn("error", refused)
        self.assertFalse((root / "tickets").exists())

    def test_details_do_not_limit_candidate_paths(self):
        self.dispatch(
            "new", "details", "R1", "--executor", "orch-do",
            "--goal", "Repair the behavior.", "--context", "The repository is authoritative.",
            "--details", "- start at src/start.py", "--pack", "orch-code-pack",
            "--isolation", "required",
        )
        self.seal("details", "R1")
        ready = self.dispatch("ready", "--run", "details")
        self.assertEqual(1, len(ready["ready"]))
        packet_path = Path(self.temporary.name) / "tickets" / "details" / "R1.md"
        self.assertNotIn("write_scope", _parse_frontmatter(packet_path.read_text(encoding="utf-8")))
        actual = workspace._actual_mutations("M\0other/path.py\0A\0tests/new_guard.py\0")
        self.assertEqual([("change", "other/path.py"), ("create", "tests/new_guard.py")], actual)

    def test_prompt_filing_command_carries_claimant_and_writes_the_ticket(self):
        self.dispatch(
            "new", "packet", "R1", "--executor", "orch-do",
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
        argv[argv.index("TEXT")] = "filed from the emitted prompt"
        filed = self.dispatch(*argv)
        self.assertEqual("worker", filed["result"]["by"])
        ticket = (
            Path(self.temporary.name) / "tickets" / "packet" / "R1.md"
        ).read_text(encoding="utf-8")
        self.assertIn(
            "### Written by `worker`\n\nfiled from the emitted prompt", ticket,
        )

    def test_complete_code_cut_keeps_one_root_generation_before_and_after_seal(self):
        initial = {"R": assignment("R", "orch-do")}
        root_draft = tickets_generations.draft_snapshot("R", initial)
        root_receipt = tickets_generations.validate_draft("R", initial, root_draft)
        rooted = tickets_generations.seal_assignments("R", initial, root_draft, root_receipt)
        inherited = root_draft["root_generation"]

        complete = {
            **rooted,
            "R.01": assignment("R.01", "orch-do", root_generation=inherited),
            "R.02": assignment("R.02", "orch-do", root_generation=inherited),
            "R.gate.critique.code": assignment(
                "R.gate.critique.code", "orch-judge", ("R.01", "R.02"),
                root_generation=inherited,
            ),
            "R.gate.repair": assignment(
                "R.gate.repair", "orch-do", ("R.gate.critique.code",),
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

        later_cut = tickets_generations.draft_snapshot(
            "S", {"S": assignment("S", "orch-do")}, ordinal=2
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

    def test_two_executor_members_validate_and_seal_with_no_gate_family(self):
        """The composite-gate topology law is gone with the command that met it.

        Validation used to refuse a two-member cut that carried no
        `<root>.gate.critique.<lens>` and `<root>.gate.repair` pair, because
        `tickets.py gate` was there to mint them. Nothing mints them now --
        a critique is a `judge` ticket and its repair a `do` ticket,
        sequenced by prose -- so requiring them would refuse every lawful
        cut.
        """

        snapshot = {
            "R": assignment("R", "orch-do"),
            "R.01": assignment("R.01", "orch-do"),
            "R.02": assignment("R.02", "orch-do"),
        }
        draft = tickets_generations.draft_snapshot("R", snapshot)
        receipt = tickets_generations.validate_draft("R", snapshot, draft)
        self.assertEqual("validated", receipt["state"])
        sealed = tickets_generations.seal_assignments("R", snapshot, draft, receipt)
        self.assertEqual({"R", "R.01", "R.02"}, set(sealed))
        self.assertFalse(
            hasattr(tickets_generations, "composite_gate_findings"),
            "the composite-gate topology grader outlived its command",
        )

    def test_a_checker_independence_dependency_no_longer_waits_on_anything(self):
        """The checker-stage apparatus that survived the `review_kind`
        deletion is gone: no live command ever built the `review_v1` chain
        `tickets.py check` required, so `checked_by` had no live producer.
        `independence: checker` no longer differs from the default in
        readiness -- both read the same status-only completeness.
        """
        from scripts import tickets_readiness

        target = {"id": "R", "status": "complete", "independence": "checker"}
        downstream = {"id": "R.next", "status": "pending", "depends_on": ["R"]}
        tickets_by_id = {"R": target, "R.next": downstream}
        self.assertTrue(
            tickets_readiness.readiness_facts(downstream, tickets_by_id)[
                "dependencies_complete"
            ]
        )

    def test_execute_owns_test_choice(self):
        self.dispatch(
            "new", "tdd", "R", "--executor", "orch-do",
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
        self.assertRegex(
            prompt.lower(),
            r"details is the planner's guidance[\s\S]*deviate and report the deviation",
        )
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
        paths = [ROOT / "contracts" / "work-item.md", *sorted((ROOT / "scripts").glob("tickets*.py")), *sorted((ROOT / "example-workflows").glob("**/*.md"))]
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
