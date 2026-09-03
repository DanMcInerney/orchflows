"""Sealed assignment identity covers semantics, not executor records."""
import unittest
from tests._repo_root import ROOT
from scripts.tickets_generations import assignment_digest
from scripts.tickets_format import _set_frontmatter_field
from scripts.tickets_issue_render import _render_ticket


def ticket(goal="done", details=None, result=""):
    sections = [("Goal", goal), ("Context", "fact")]
    if details:
        sections.append(("Details", details))
    sections.extend((("Result", result), ("Verification", ""), ("Feedback", "[]"), ("Risks", "[]")))
    return _render_ticket({"id": "R", "run": "r", "status": "pending", "executor": "orch-edit", "depends_on": [], "bound": "60m"}, sections)


class TicketProtocolTest(unittest.TestCase):
    def test_semantic_change_moves_assignment(self):
        self.assertNotEqual(assignment_digest("R", ticket()), assignment_digest("R", ticket(goal="other")))
        self.assertNotEqual(assignment_digest("R", ticket()), assignment_digest("R", ticket(details="- x")))

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
        root = ROOT
        dispatch = (root / "contracts" / "dispatch.md").read_text(encoding="utf-8")
        result = (root / "contracts" / "result.md").read_text(encoding="utf-8")
        delegation = (root / "rules" / "delegation.md").read_text(encoding="utf-8")
        vocabulary = (root / "docs" / "vocabulary.md").read_text(encoding="utf-8")
        for token in (
            "`dispatch_v1`", "`orchflows.dispatch.v1`", "`dispatch-open`",
            "`dispatch-commit`", "`dispatch-retire`", "`dispatch-replace`",
            "`dispatch-join`",
            "`claim-without-dispatch`", "`idempotency-conflict`",
            "`dispatch-mismatch`", "`assignment-mismatch`", "`stale-attempt`",
        ):
            self.assertIn(token, dispatch)
        self.assertIn("exactly-once external", result)
        self.assertIn("dispatch contract", delegation.lower())
        self.assertIn("**dispatch attempt**", vocabulary)

    def test_join_contract_consumes_one_fixed_result_and_absolute_attempt_lease(self):
        root = ROOT
        dispatch = (root / "contracts" / "dispatch.md").read_text(encoding="utf-8")
        work_item = (root / "contracts" / "work-item.md").read_text(encoding="utf-8")
        result = (root / "contracts" / "result.md").read_text(encoding="utf-8")
        delegation = (root / "rules" / "delegation.md").read_text(encoding="utf-8")
        self.assertIn("`dispatch-join`", dispatch)
        for projection in (work_item, result, delegation):
            self.assertIn("dispatch contract", projection.lower())
        # The join is a command, not a skill: delegation names the command and
        # the dispatch contract owns the transaction it commits.
        self.assertIn("`tickets.py land`", delegation)
        self.assertIn("`outcome_record_id`", dispatch)
        self.assertIn("`lease_expires_at`", dispatch)

    def test_dispatch_v1_contract_owns_the_launch(self):
        root = ROOT
        dispatch = (root / "contracts" / "dispatch.md").read_text(encoding="utf-8")
        delegation = (root / "rules" / "delegation.md").read_text(encoding="utf-8")
        roles = (root / "rules" / "roles.md").read_text(encoding="utf-8")
        vocabulary = (root / "docs" / "vocabulary.md").read_text(encoding="utf-8")
        for token in (
            "`launch`", "`prompt`",
            "`state-inaccessible`", "`stale-attempt`",
            "`idempotency-conflict`", "`dispatch-mismatch`",
            "ASCII-escaped canonical JSON",
        ):
            self.assertIn(token, dispatch)
        # The handshake half rode out with its machinery: no survivor keeps
        # its vocabulary alive in the contract that used to own it, and the
        # supersession records that named what they retired are gone, so the
        # whole file is the surface this reads.
        for retired in (
            "`dispatch-receive`", "`dispatch-receipt`", "`receipt-required`",
            "`authority-mismatch`", "`profile-mismatch`",
            "`assignment-divergent`", "`packet-invalid`", "`inline`",
            "`reply_to`", "`reference`", "`admission`", "`independence`",
            "`dispatch-packet`", "`durability`", "`review_kind`",
        ):
            self.assertNotIn(retired, dispatch)
        host = (root / "templates" / "host-block.md").read_text(encoding="utf-8")
        profiles = (root / "hosts" / "profiles.md").read_text(encoding="utf-8")
        tickets = (root / "TICKETS.md").read_text(encoding="utf-8")
        for command in (
            "tickets.py do", "tickets.py land",
            "tickets.py frame-open", "frame-close",
        ):
            self.assertIn(command, host)
        self.assertNotIn("tickets.py dispatch", host)
        self.assertNotIn("dispatch-receive", host)
        for surface in (profiles, tickets):
            for command in ("dispatch-open", "dispatch-retire"):
                self.assertIn(command, surface)
            self.assertNotIn("dispatch-packet", surface)
        self.assertNotIn("tickets.py claim", host)
        self.assertNotIn("tickets.py packet", host)
        collapsed_profiles = " ".join(profiles.split())
        self.assertIn("replaying the same `dispatch` call", collapsed_profiles)
        self.assertIn("`dispatch-replace`", profiles)
        self.assertIn("transport silence", delegation.lower())
        self.assertIn("`claim-without-dispatch`", tickets)
        for obsolete in (
            "completion test", "same write scope", "stale claim sent back",
            "Hitting an excluded action", "optional\n  `## Context`",
        ):
            self.assertNotIn(obsolete, tickets)
        for current in (
            "absolute lease", "`dispatch-join`", "outside-independence path",
        ):
            self.assertIn(current, tickets)
        self.assertIn("committed launch", delegation)
        self.assertIn("dispatch contract", roles.lower())
        self.assertIn("- **launch** —", vocabulary)
        self.assertNotIn("**packet projection**", vocabulary)

    def test_public_documents_project_the_current_dispatch_and_gate_model(self):
        root = ROOT
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
            "launch prompt", "replaying the same `dispatch` call",
            "tickets.py show", "tickets.py lint <run> [<id>] --file",
            "retired attempt", "successor run",
        ):
            self.assertIn(phrase, tickets)
        self.assertIn("Each physical run has one root ticket", worklog)
        self.assertNotIn("packet-only dispatch", vocabulary)
        self.assertNotIn("packet-only ticket", vocabulary)
        self.assertNotIn("gate-only cut", vocabulary)

    def test_host_skill_and_ui_project_established_non_live_suspension(self):
        root = ROOT
        host = (root / "templates" / "host-block.md").read_text(encoding="utf-8")
        dispatch = (root / "contracts" / "dispatch.md").read_text(encoding="utf-8")
        land_usage = __import__(
            "scripts.tickets_land", fromlist=["LAND_USAGE"]
        ).LAND_USAGE
        ui_model = (root / "reader" / "scripts" / "ui_model.py").read_text(encoding="utf-8")

        self.assertIn("emitted `launch`", host)
        self.assertIn("hand-adds nothing", dispatch)
        self.assertIn("--outcome-file <path|->", land_usage)
        for projection in (host, dispatch):
            self.assertIn("workspace", projection.lower())
        self.assertIn("tickets.py land", host)
        self.assertIn('LIVE_CLAIM_STATUSES = ("claimed",)', ui_model)
        self.assertNotIn("Parked claims stay live", dispatch)
        self.assertNotIn("holds the lease", ui_model)
