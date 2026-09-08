"""Caller-bound dispatch, cancellation, and bounded inspection seams."""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from unittest import mock

from scripts.tickets_format import _parse_frontmatter, _set_frontmatter_field, canonical_json
from scripts.tickets_install_guard import installation_lock
from tests import test_dispatch_v1 as fixtures
from tests import _retired_commands as commands
from tests.test_ticket_frames import FrameSinkTest


class FramePublicationTest(FrameSinkTest):
    def test_first_frame_waits_for_publication_before_resolving_pins(self):
        from scripts import tickets_frame
        from scripts import state_root
        entered = threading.Event()
        started = threading.Event()
        answers = []
        original = tickets_frame._workflow_record

        def resolve(*args):
            entered.set()
            return original(*args)

        def open_frame():
            started.set()
            answers.append(self.frame())

        worker = threading.Thread(target=open_frame)
        with mock.patch.object(tickets_frame, "_workflow_record", side_effect=resolve):
            try:
                with installation_lock(state_root.orchflows_home()):
                    worker.start()
                    self.assertTrue(started.wait(2))
                    self.assertFalse(entered.wait(0.1))
                    self.assertFalse(self.run_dir().exists())
            finally:
                worker.join(130)
        self.assertFalse(worker.is_alive())
        self.assertTrue(entered.is_set())
        self.assertEqual(1, len(answers))

    def test_publication_lock_refusal_leaves_first_frame_uncreated(self):
        with mock.patch("scripts.tickets_frame.installation_lock", side_effect=OSError("busy")):
            answer = self.call("frame-open", self.RUN, "--goal-file", str(self.goal_file), expect_error=True)
        self.assertIn("unable to guard frame open", answer["error"])
        self.assertFalse(self.run_dir().exists())

    def test_frame_close_files_its_own_explicit_identity(self):
        opened = self.frame()
        answer = self.call("frame-close", self.RUN, opened["id"], "--status", "limited")
        self.assertEqual("limited", answer["frame_close"]["status"])


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
            self.assertEqual(str(standard / "STANDARD.md"), inspected["ticket_pins"]["standards"][0]["path"])
            (package / "SKILL.md").write_text("changed package", encoding="utf-8")
            self.assertIn("error", tickets_pins.inspect_ticket_pins("run", "T", data))


class InstallationGuardTest(unittest.TestCase):
    def test_nested_lock_releases_after_failure_and_excludes_other_thread(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            entered = threading.Event()
            def acquire():
                with installation_lock(directory):
                    entered.set()
            with installation_lock(directory):
                with installation_lock(directory):
                    worker = threading.Thread(target=acquire)
                    worker.start()
                    self.assertFalse(entered.wait(0.05))
            worker.join(5)
            self.assertFalse(worker.is_alive())
            self.assertTrue(entered.is_set())
            with self.assertRaises(ValueError):
                with installation_lock(directory):
                    raise ValueError("release")
            with installation_lock(directory):
                pass

    def test_process_cannot_enter_until_publication_lock_releases(self):
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "entered"
            ready = Path(directory) / "ready"
            script = "from scripts.tickets_install_guard import installation_lock; from pathlib import Path; import sys\nPath(sys.argv[3]).write_text('ready')\nwith installation_lock(sys.argv[1]): Path(sys.argv[2]).write_text('entered')"
            with installation_lock(directory):
                process = subprocess.Popen([sys.executable, "-c", script, directory, str(marker), str(ready)])
                try:
                    import time
                    deadline = time.monotonic() + 5
                    while not ready.exists() and time.monotonic() < deadline:
                        time.sleep(0.01)
                    self.assertTrue(ready.exists())
                    self.assertFalse(marker.exists())
                    with self.assertRaises(subprocess.TimeoutExpired):
                        process.wait(timeout=0.15)
                except BaseException:
                    process.kill()
                    process.wait(timeout=5)
                    raise
            try:
                self.assertEqual(0, process.wait(timeout=10))
            finally:
                if process.poll() is None:
                    process.kill()
                    process.wait(timeout=5)
            self.assertEqual("entered", marker.read_text())
