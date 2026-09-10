"""Caller-bound dispatch, cancellation, and bounded inspection seams."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

from scripts.tickets_format import _parse_frontmatter, _set_frontmatter_field, canonical_json
from tests import test_dispatch_v1 as fixtures
from tests import _retired_commands as commands
from tests.test_ticket_frames import FrameSinkTest


class FramePublicationTest(FrameSinkTest):


    def test_frame_close_files_its_own_explicit_identity(self):
        opened = self.frame()
        answer = self.call("frame-close", self.RUN, opened["id"], "--status", "limited")
        self.assertEqual("limited", answer["frame_close"]["status"])

    def test_nested_workflow_frame_keeps_its_own_inspection_origin(self):
        from scripts import rings_trust, tickets_store
        opened = self.frame()
        writer = tickets_store._writer_identity()
        nested = Path(self.temporary.name) / "nested"
        bundle = nested / ".orchflows"
        package = bundle / "workflows" / "nested-frame"
        package.mkdir(parents=True)
        (package / "SKILL.md").write_text("---\nname: nested-frame\nrole: none\n---\nWorkflow.\n", encoding="utf-8")
        rings_trust.grant(bundle)
        with mock.patch("pathlib.Path.cwd", return_value=nested), mock.patch("scripts.tickets_store._writer_identity", return_value=writer), mock.patch("scripts.tickets_project._writer_identity", return_value=writer):
            child = self.frame("--parent", opened["id"], "--workflow", "nested-frame")
        data = _parse_frontmatter(self.ticket_text(child["id"]))
        self.assertEqual(str(nested.resolve()), data.get("pin_origin"))
        inspected = self.call("show", self.RUN, child["id"], "--pins")
        self.assertEqual("nested-frame", inspected["ticket_pins"]["owner"])
        rings_trust.revoke(bundle)
        self.call("show", self.RUN, child["id"], "--pins", expect_error=True)


class ReliabilityDispatchTest(unittest.TestCase):
    setUp = fixtures.DispatchV1Test.setUp
    tearDown = fixtures.DispatchV1Test.tearDown
    dispatch = fixtures.DispatchV1Test.dispatch
    open = fixtures.DispatchV1Test.open
    _candidate_checkout = fixtures.DispatchV1Test._candidate_checkout
    ticket_text = fixtures.DispatchV1Test.ticket_text
    commit_launch = fixtures.DispatchV1Test.commit_launch
    retire = fixtures.DispatchV1Test.retire
    replace = fixtures.DispatchV1Test.replace
    join = fixtures.DispatchV1Test.join
    outcome = fixtures.DispatchV1Test.outcome
    result = fixtures.DispatchV1Test.result

    def start(self):
        self.opened_seal = self.open()["dispatch"]["assignment_seal"]
        self.commit_launch()

    def note(self, dispatch_id="D1", owner="worker", body="delivered"):
        return commands.run([
            "dispatch-outcome", "run", "T", "--assignment-seal", self.opened_seal,
            "--dispatch-id", dispatch_id, "--by", owner, "--note", body,
        ])

    def envelope_note(self, dispatch_id="D1", owner="worker", body="delivered"):
        path = Path(self.temporary.name) / "envelope.json"
        path.write_text(canonical_json({
            "protocol": "orchflows.dispatch.v1", "run": "run", "id": "T",
            "assignment_seal": self.opened_seal, "dispatch_id": dispatch_id,
            "outcome_record_id": "outcome", "by": owner, "evidence": body,
        }), encoding="utf-8")
        return commands.run(["dispatch-outcome", "run", "T", "--file", str(path)])

    def test_replaced_writer_and_identity_free_note_cannot_close_successor(self):
        self.start()
        self.assertNotIn("error", self.replace(supersede_live=True))
        self.commit_launch("D2")
        before = self.ticket_text()
        self.assertEqual("stale-attempt", self.note()["code"])
        self.assertEqual("outcome-invalid", commands.run([
            "dispatch-outcome", "run", "T", "--note", "late old writer",
        ])["code"])
        self.assertEqual(before, self.ticket_text())
        self.assertNotIn("error", self.note("D2", "worker-2"))

    def test_old_envelope_replays_after_replacement_and_expiry_but_conflict_refuses(self):
        self.start()
        first = self.envelope_note()
        carrier = Path(self.temporary.name) / "old.json"
        carrier.write_text(canonical_json(first["outcome"]), encoding="utf-8")
        self.assertNotIn("error", self.replace(supersede_live=True))
        self.commit_launch("D2")
        self.assertNotIn("error", self.envelope_note("D2", "worker-2"))
        joined = commands.run([
            "dispatch-join", "run", "T", "--assignment-seal", self.opened_seal,
            "--dispatch-id", "D2", "--outcome-record-id", "outcome", "--by", "root", "--status", "complete",
        ])
        self.assertNotIn("error", joined)
        before = self.ticket_text()
        class Later(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2100, 1, 1, tzinfo=timezone.utc)
        with mock.patch("scripts.tickets_attempts.datetime", Later):
            self.assertEqual(first, commands.run(["dispatch-outcome", "run", "T", "--file", str(carrier)]))
            carrier.write_text(canonical_json(dict(first["outcome"], evidence="changed")), encoding="utf-8")
            self.assertEqual("idempotency-conflict", commands.run([
                "dispatch-outcome", "run", "T", "--file", str(carrier),
            ])["code"])
        self.assertEqual(before, self.ticket_text())

    def test_join_disposition_conflicts_and_joined_status_cannot_be_overwritten(self):
        self.start()
        self.envelope_note()
        joined = self.join()
        before = self.ticket_text()
        self.assertEqual(joined, self.join())
        self.assertEqual("idempotency-conflict", self.join(status="failed")["code"])
        self.assertEqual("dispatch-join-required", commands.run(["set-status", "run", "T", "failed"])["code"])
        self.assertEqual(before, self.ticket_text())

    def test_legacy_join_replays_only_its_stored_disposition_without_rewrite(self):
        self.start()
        self.envelope_note()
        joined = self.join()
        data = _parse_frontmatter(self.ticket_text())
        state = json.loads(data["dispatch_v1"])
        record = state["attempts"][0]["records"][-1]
        content = json.loads(record["content"])
        content.pop("status", None)
        record["content"] = canonical_json(content)
        path = Path(self.temporary.name) / "tickets/run/T.md"
        path.write_text(_set_frontmatter_field(self.ticket_text(), "dispatch_v1", canonical_json(state)), encoding="utf-8")
        before = path.read_bytes()
        self.assertEqual(joined, self.join())
        self.assertEqual("idempotency-conflict", self.join(status="failed")["code"])
        self.assertEqual(before, path.read_bytes())

    def test_retired_outcome_still_requires_join_and_live_retry_refuses_cancellation(self):
        self.start()
        self.envelope_note()
        self.assertNotIn("error", self.retire())
        before = self.ticket_text()
        self.assertEqual("dispatch-join-required", commands.run(["set-status", "run", "T", "failed"])["code"])
        self.assertEqual(before, self.ticket_text())

    def test_sections_page_long_report_without_repeating_history(self):
        self.start()
        self.result(body="x" * 20000)
        before = self.ticket_text()
        chunks, offset = [], 0
        while offset is not None:
            page = commands.run(["show", "run", "T", "--section", "Report", "--offset", str(offset), "--limit", "1024"])["ticket_section"]
            self.assertLessEqual(len(page["text"]), 1024)
            self.assertNotIn("dispatch_v1", page)
            chunks.append(page["text"])
            offset = page["next_offset"]
        self.assertEqual(20000, "".join(chunks).count("x"))
        from scripts import tickets
        self.assertEqual("".join(chunks)[:10], tickets.section_page(before, "Report", 0, 10)["text"])
        self.assertIn("error", tickets.section_page(before, "Report", 0, 999999))
        self.assertIn("error", commands.run(["show", "run", "T", "--section", "Report", "--limit", "999999"]))
        self.assertEqual(before, self.ticket_text())

    def test_ticket_pin_inspection_uses_tree_digest_and_refuses_private_path_scope(self):
        self.start()
        result = commands.run(["show", "run", "T", "--pins"])
        pin = result["ticket_pins"]["standards"][0]
        self.assertNotEqual(pin["digest"], "sha256:" + hashlib.sha256(Path(pin["path"]).read_bytes()).hexdigest())
        data = _parse_frontmatter(self.ticket_text())
        from scripts.tickets_pins import inspect_ticket_pins
        forged = dict(data, workflow=str(Path(pin["path"]).parent), workflow_digest=pin["digest"], workflow_entry="STANDARD.md")
        self.assertIn("error", inspect_ticket_pins("run", "T", forged))

    def test_retire_help_names_lifecycle_namespace(self):
        self.assertIn("--record-id <lifecycle:id>", commands.run(["dispatch-retire", "--help"])["help"]["usage"])

    def test_pin_inspection_refuses_a_rewritten_sealed_origin_without_mutation(self):
        self.start()
        path = Path(self.temporary.name) / "tickets/run/T.md"
        path.write_text(_set_frontmatter_field(self.ticket_text(), "pin_origin", self.temporary.name), encoding="utf-8")
        before = path.read_bytes()
        answer = commands.run(["show", "run", "T", "--pins"])
        self.assertIn("assignment-seal-mismatch", {item["code"] for item in answer["findings"]})
        self.assertEqual(before, path.read_bytes())

    def test_nested_ticket_retains_its_own_pin_origin_under_a_root_run(self):
        from scripts import rings_trust, tickets_pins
        from scripts.tickets_generations import assignment_payload
        project = Path(self.temporary.name) / "project"
        nested = project / "nested"
        bundle = nested / ".orchflows"
        package = bundle / "workflows" / "nested-flow"
        standard = package / "standards" / "nested-code"
        standard.mkdir(parents=True)
        (package / "SKILL.md").write_text("---\nname: nested-flow\nrole: none\n---\nWorkflow.\n", encoding="utf-8")
        (standard / "STANDARD.md").write_text("---\nname: nested-code\nadapter: git\n---\nStandard.\n", encoding="utf-8")
        rings_trust.grant(bundle)
        with mock.patch("pathlib.Path.cwd", return_value=project):
            root_pins, failure = tickets_pins.pin_fields(["orch-code"], None)
            self.assertIsNone(failure)
        with mock.patch("pathlib.Path.cwd", return_value=nested):
            pins, failure = tickets_pins.pin_fields(["nested-code"], None, owner="nested-flow")
            self.assertIsNone(failure)
        self.assertEqual(str(nested.resolve()), pins.get("pin_origin"))
        self.assertNotEqual(root_pins.get("pin_origin"), pins["pin_origin"])
        data = dict(pins, workflow="nested-flow", workflow_entry="SKILL.md",
                    workflow_digest=tickets_pins.tree_digest("workflow", package))
        with mock.patch("scripts.tickets_project.recorded_project", return_value={"root": str(project)}), mock.patch("pathlib.Path.cwd", return_value=project):
            inspected = tickets_pins.inspect_ticket_pins("run", "T", data)
            self.assertEqual(str((standard / "STANDARD.md").resolve()), inspected["ticket_pins"]["standards"][0]["path"])
            rings_trust.revoke(bundle)
            self.assertIn("error", tickets_pins.inspect_ticket_pins("run", "T", data))
            rings_trust.grant(bundle)
            (package / "SKILL.md").write_text("changed package", encoding="utf-8")
            rings_trust.grant(bundle)
            self.assertIn("error", tickets_pins.inspect_ticket_pins("run", "T", data))
        # The origin is sealed with the assignment, not mutable run metadata.
        text = self.ticket_text()
        original = _set_frontmatter_field(text, "pin_origin", str(nested))
        changed = _set_frontmatter_field(text, "pin_origin", str(project))
        self.assertNotEqual(assignment_payload("T", original), assignment_payload("T", changed))

    def test_private_pin_uses_trusted_public_package_and_refuses_changed_owner(self):
        from scripts import rings_trust, tickets_pins
        project = Path(self.temporary.name) / "project"
        (project / ".git").mkdir(parents=True)
        bundle = project / ".orchflows"
        package = bundle / "workflows" / "private-test"
        standard = package / "standards" / "private-code"
        standard.mkdir(parents=True)
        (package / "SKILL.md").write_text("---\nname: private-test\nrole: none\n---\nWorkflow.\n", encoding="utf-8")
        (standard / "STANDARD.md").write_text("---\nname: private-code\nadapter: git\n---\nStandard.\n", encoding="utf-8")
        data = {"workflow": "private-test", "workflow_entry": "SKILL.md",
                "workflow_digest": tickets_pins.tree_digest("workflow", package),
                "standards": ["private-code@" + tickets_pins.tree_digest("standard", standard)]}
        with mock.patch("scripts.tickets_project.recorded_project", return_value={"root": str(project)}):
            self.assertIn("error", tickets_pins.inspect_ticket_pins("run", "T", data))
            rings_trust.grant(bundle)
            inspected = tickets_pins.inspect_ticket_pins("run", "T", data)
            self.assertEqual(str((standard / "STANDARD.md").resolve()), inspected["ticket_pins"]["standards"][0]["path"])
            (package / "SKILL.md").write_text("changed package", encoding="utf-8")
            self.assertIn("error", tickets_pins.inspect_ticket_pins("run", "T", data))
