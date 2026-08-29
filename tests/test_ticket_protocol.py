"""Sealed assignment identity covers semantics, not executor records."""
import unittest
from scripts.tickets_generations import assignment_digest
from scripts.tickets_format import _set_frontmatter_field
from scripts.tickets_issue_render import _render_ticket


def ticket(goal="done", suggested=None, result=""):
    sections = [("Goal", goal), ("Context", "fact")]
    if suggested:
        sections.append(("Suggested files", suggested))
    sections.extend((("Result", result), ("Verification", ""), ("Feedback", "[]"), ("Risks", "[]")))
    return _render_ticket({"id": "R", "run": "r", "status": "pending", "executor": "orch-edit", "depends_on": [], "bound": "60m"}, sections)


class TicketProtocolTest(unittest.TestCase):
    def test_semantic_change_moves_assignment(self):
        self.assertNotEqual(assignment_digest("R", ticket()), assignment_digest("R", ticket(goal="other")))
        self.assertNotEqual(assignment_digest("R", ticket()), assignment_digest("R", ticket(suggested="- x")))

    def test_result_does_not_move_assignment(self):
        self.assertEqual(assignment_digest("R", ticket()), assignment_digest("R", ticket(result="landed")))

    def test_dispatch_attempt_state_does_not_move_assignment(self):
        original = ticket()
        dispatched = _set_frontmatter_field(
            original, "dispatch_v1",
            '{"attempts":[],"protocol":"orchflows.dispatch.v1"}',
        )
        self.assertEqual(
            assignment_digest("R", original), assignment_digest("R", dispatched)
        )

    def test_dispatch_v1_contract_owns_the_closed_public_seam(self):
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        dispatch = (root / "contracts" / "dispatch.md").read_text(encoding="utf-8")
        result = (root / "contracts" / "result.md").read_text(encoding="utf-8")
        delegation = (root / "rules" / "delegation.md").read_text(encoding="utf-8")
        vocabulary = (root / "docs" / "vocabulary.md").read_text(encoding="utf-8")
        for token in (
            "`dispatch_v1`", "`orchflows.dispatch.v1`", "`dispatch-open`",
            "`dispatch-commit`", "`dispatch-retire`", "`dispatch-replace`",
            "`dispatch-join`",
            "`legacy-live-claim`", "`idempotency-conflict`",
            "`dispatch-mismatch`", "`assignment-mismatch`", "`stale-attempt`",
        ):
            self.assertIn(token, dispatch)
        self.assertIn("exactly-once external", result)
        self.assertIn("dispatch contract", delegation.lower())
        self.assertIn("**dispatch attempt**", vocabulary)

    def test_join_contract_consumes_one_fixed_result_and_absolute_attempt_lease(self):
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        dispatch = (root / "contracts" / "dispatch.md").read_text(encoding="utf-8")
        work_item = (root / "contracts" / "work-item.md").read_text(encoding="utf-8")
        result = (root / "contracts" / "result.md").read_text(encoding="utf-8")
        delegation = (root / "rules" / "delegation.md").read_text(encoding="utf-8")
        integrate = (root / "skills" / "kernel" / "orch-integrate" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("`dispatch-join`", dispatch)
        for projection in (work_item, result, delegation):
            self.assertIn("dispatch contract", projection.lower())
        self.assertIn("tickets.py dispatch-join", integrate)
        self.assertIn("`outcome_record_id`", dispatch)
        self.assertIn("`lease_expires_at`", dispatch)
        self.assertNotIn("only this join calls `tickets.py set-status`", integrate)

    def test_dispatch_v1_contract_owns_packet_projection_and_receipt(self):
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        dispatch = (root / "contracts" / "dispatch.md").read_text(encoding="utf-8")
        delegation = (root / "rules" / "delegation.md").read_text(encoding="utf-8")
        roles = (root / "rules" / "roles.md").read_text(encoding="utf-8")
        vocabulary = (root / "docs" / "vocabulary.md").read_text(encoding="utf-8")
        for token in (
            "`dispatch-packet`", "`dispatch-receive`", "`reference`",
            "`inline`", "`state-inaccessible`", "`assignment-divergent`",
            "`identity-mismatch`", "`authority-mismatch`",
            "`role-mismatch`", "`profile-mismatch`", "`dispatch-receipt`",
            "`receipt-required`", "`--file -`", "ASCII-escaped canonical JSON",
        ):
            self.assertIn(token, dispatch)
        host = (root / "templates" / "host-block.md").read_text(encoding="utf-8")
        frontier = (root / "skills" / "engines" / "orch-frontier" / "SKILL.md").read_text(encoding="utf-8")
        profiles = (root / "skills" / "engines" / "orch-frontier" / "references" / "profiles.md").read_text(encoding="utf-8")
        tickets = (root / "TICKETS.md").read_text(encoding="utf-8")
        for surface in (host, frontier):
            self.assertIn("tickets.py dispatch", surface)
            self.assertIn("dispatch-receive", surface)
        for surface in (profiles, tickets):
            for command in ("dispatch-open", "dispatch-packet", "dispatch-receive"):
                self.assertIn(command, surface)
        loop = (root / "skills" / "engines" / "orch-loop" / "SKILL.md").read_text(encoding="utf-8")
        for routing in (host, frontier, loop):
            self.assertNotIn("tickets.py claim", routing)
            self.assertNotIn("tickets.py packet", routing)
        collapsed_frontier = " ".join(frontier.split())
        self.assertIn("transport silence", collapsed_frontier.lower())
        self.assertIn("same recorded child", collapsed_frontier)
        self.assertIn("`dispatch-replace`", frontier)
        self.assertIn("`legacy-live-claim`", tickets)
        for obsolete in (
            "completion test", "same write scope", "stale claim sent back",
            "Hitting an excluded action", "optional\n  `## Context`",
        ):
            self.assertNotIn(obsolete, tickets)
        for current in (
            "absolute lease", "`dispatch-join`", "outside-independence path",
        ):
            self.assertIn(current, tickets)
        self.assertIn("committed packet", delegation)
        self.assertIn("receipt", roles.lower())
        self.assertIn("**packet projection**", vocabulary)

    def test_public_documents_project_the_current_dispatch_and_gate_model(self):
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        readme = (root / "README.md").read_text(encoding="utf-8")
        design = (root / "DESIGN.md").read_text(encoding="utf-8")
        tickets = (root / "TICKETS.md").read_text(encoding="utf-8")
        vocabulary = (root / "docs" / "vocabulary.md").read_text(encoding="utf-8")
        worklog = (root / "contracts" / "worklog.md").read_text(encoding="utf-8")

        for projection in (readme, design):
            self.assertIn("six", projection.lower())
            self.assertIn("dispatch", projection.lower())
        for field in (
            "assignment_seal", "dispatch_id", "outcome_record_id", "evidence",
        ):
            self.assertIn(field, readme)

        for phrase in (
            "response `.packet` value", "`--file -`", "durable accepted receipt",
            "GatePlan", "CritiqueAdjudication", "RepairOutcome",
            "tickets.py checker-stage", "--stage <id>.check",
            "tickets.py show", "tickets.py lint <run> [<id>] --file",
            "retired attempt", "successor run",
        ):
            self.assertIn(phrase, tickets)
        self.assertIn("decomposed root-ticket run", worklog)
        self.assertNotIn("packet-only dispatch", vocabulary)
        self.assertNotIn("packet-only ticket", vocabulary)
        self.assertNotIn("gate-only cut", vocabulary)

    def test_host_skill_and_ui_project_established_non_live_suspension(self):
        root = __import__("pathlib").Path(__file__).resolve().parents[1]
        host = (root / "templates" / "host-block.md").read_text(encoding="utf-8")
        frontier = (
            root / "skills" / "engines" / "orch-frontier" / "SKILL.md"
        ).read_text(encoding="utf-8")
        ui_model = (root / "scripts" / "ui_model.py").read_text(encoding="utf-8")

        for projection in (host, frontier):
            self.assertIn("response `.packet`", projection)
            self.assertIn("--file", projection)
            self.assertIn("workspace", projection.lower())
            self.assertIn("evidence-store", projection.lower())
        self.assertIn('LIVE_CLAIM_STATUSES = ("claimed",)', ui_model)
        self.assertNotIn("Parked claims stay live", frontier)
        self.assertNotIn("holds the lease", ui_model)
