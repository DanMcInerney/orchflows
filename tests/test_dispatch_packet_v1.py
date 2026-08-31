"""Committed dispatch-v1 packet projection regressions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from scripts import tickets, tickets_review
from scripts.tickets_packet import workspace_establishment_finding
from scripts.tickets_format import canonical_json, parse_canonical_json
from scripts.tickets_outcome import DISPATCH_OUTCOME_USAGE


class DispatchPacketV1Test(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.environment = mock.patch.dict(
            os.environ, {"ORCHFLOWS_STATE_HOME": self.temporary.name}
        )
        self.environment.start()
        self.dispatch(
            "new", "run", "T", "--executor", "orch-execute",
            "--goal", "Deliver the behavior.",
            "--context", "The repository is authoritative.",
            "--pack", "orch-code-pack", "--profile", "orch-worker",
            "--isolation", "required",
        )
        self.dispatch("stamp-generation", "run", "T")
        validated = self.dispatch("draft-validate", "run", "T")
        self.dispatch(
            "seal", "run", "T", "--cut-generation",
            validated["draft_validation"]["cut_generation"],
        )
        self.dispatch("ready", "--run", "run")
        # non-ASCII on purpose: the packet command must emit ASCII-escaped
        # canonical JSON whatever the subprocess code page is, and the
        # workspace path is the prompt value this fixture owns.
        self.candidate = Path(self.temporary.name) / "candidate-—"
        self.candidate.mkdir()
        self.ticket_path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        established = self.ticket_path.read_text(encoding="utf-8")
        for key, value in (
            ("workspace_path", str(self.candidate)),
            ("workspace_branch", "candidate-branch"),
            ("workspace_baseline", "0123456789abcdef clean"),
        ):
            established = tickets._set_frontmatter_field(established, key, value)
        self.ticket_path.write_text(established, encoding="utf-8")
        self.lease = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat().replace("+00:00", "Z")
        opened = self.dispatch(
            "dispatch-open", "run", "T", "--by", "worker",
            "--dispatch-id", "D1", "--lease-expires-at", self.lease,
        )
        self.assignment_seal = opened["dispatch"]["assignment_seal"]

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def dispatch(self, *arguments):
        result = tickets._dispatch(list(arguments))
        self.assertNotIn("error", result, result)
        return result

    def project(self, workspace=None):
        return tickets._dispatch([
            "dispatch-packet", "run", "T", "--dispatch-id", "D1",
            "--workspace", str(self.candidate) if workspace is None else workspace,
        ])

    def ticket_state(self):
        path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        encoded = next(
            line.partition(":")[2].strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.startswith("dispatch_v1:")
        )
        return parse_canonical_json(encoded)

    def ticket_bytes(self):
        return (
            Path(self.temporary.name) / "tickets" / "run" / "T.md"
        ).read_bytes()

    def test_reference_projection_is_committed_and_exact_retry_replays(self):
        first = self.project()
        self.assertNotIn("error", first, first)
        packet = first["packet"]
        self.assertEqual("orchflows.dispatch.v1", packet["protocol"])
        self.assertEqual("D1", packet["dispatch_id"])
        self.assertEqual("worker", packet["assigned_name"])
        self.assertEqual("worker", packet["role"])
        self.assertEqual({"run": "run", "id": "T"}, packet["source"])
        for retired in ("form", "inline", "reference", "reply_to", "admission",
                        "executor", "profile", "independence", "isolation",
                        "outcome_record_id"):
            self.assertNotIn(retired, packet)
        self.assertIn(
            f"--assignment-seal {packet['assignment_seal']} --dispatch-id D1 "
            "--record-id RECORD_ID --by worker",
            packet["prompt"],
        )
        self.assertNotIn("workspace.py", packet["prompt"])
        self.assertNotIn("dispatch-receive", packet["prompt"])

        self.assertEqual(first, self.project())
        records = self.ticket_state()["attempts"][0]["records"]
        self.assertEqual(["dispatch-packet"], [item["record_id"] for item in records])

        filing = [
            line.split()[2:]
            for line in packet["prompt"].splitlines()
            if len(line.split()) > 2
            and Path(line.split()[1]).name == "tickets.py"
            and line.split()[2] == "result"
        ]
        self.assertEqual(2, len(filing), packet["prompt"])
        for command in filing:
            self.assertIn("--append", command)

        text_command = next(command for command in filing if "--text" in command)
        text_command[text_command.index("SECTION")] = "Result"
        text_command[text_command.index("TEXT")] = "first emitted text record"
        text_command[text_command.index("RECORD_ID")] = "R1"
        first_result = self.dispatch(*text_command)
        self.assertEqual("append", first_result["result"]["mode"])
        text_command[text_command.index("first emitted text record")] = "second emitted text record"
        text_command[text_command.index("R1")] = "R2"
        second_result = self.dispatch(*text_command)
        self.assertEqual("append", second_result["result"]["mode"])
        body = self.ticket_path.read_text(encoding="utf-8")
        self.assertIn("first emitted text record", body)
        self.assertIn("second emitted text record", body)

    def test_the_first_filed_record_is_the_acceptance(self):
        """No accept step stands between the committed packet and the child.

        The whole return runs off the committed packet alone: the identities
        `result` already validates on every write are the child's authority,
        and there is no receipt for any of the three to wait on.
        """

        self.project()

        filed = self.dispatch(
            "result", "run", "T", "--assignment-seal", self.assignment_seal,
            "--dispatch-id", "D1", "--record-id", "result-1",
            "--by", "worker", "--section", "Result", "--text", "delivered",
        )
        self.assertEqual("write", filed["result"]["mode"])
        self.dispatch(
            "result", "run", "T", "--assignment-seal", self.assignment_seal,
            "--dispatch-id", "D1", "--record-id", "result-2",
            "--by", "worker", "--section", "Verification", "--text", "checked",
        )
        delta = Path(self.temporary.name) / "closing-delta.txt"
        delta.write_text("the unstreamed closing delta", encoding="utf-8")
        self.dispatch(
            "dispatch-outcome", "run", "T", "--status", "complete",
            "--result-file", str(delta), "--verification-file", str(delta),
        )
        joined = self.dispatch(
            "dispatch-join", "run", "T", "--assignment-seal", self.assignment_seal,
            "--dispatch-id", "D1", "--outcome-record-id", "outcome", "--by", "root",
        )
        self.assertEqual("complete", joined["join"]["status"])
        self.assertEqual(
            ["dispatch-packet", "result-1", "result-2", "outcome", "join:outcome"],
            [item["record_id"] for item in self.ticket_state()["attempts"][0]["records"]],
        )

    def test_an_execution_record_without_a_committed_packet_refuses(self):
        """The one ordering the grammar still keeps: a child that filed
        anything was launched, and the committed packet is that launch."""

        before = self.ticket_bytes()
        refusal = tickets._dispatch([
            "result", "run", "T", "--assignment-seal", self.assignment_seal,
            "--dispatch-id", "D1", "--record-id", "result-1",
            "--by", "worker", "--section", "Result", "--text", "delivered",
        ])
        self.assertEqual("dispatch-record-invalid", refusal["code"], refusal)
        self.assertIn("committed packet", refusal["error"])
        self.assertEqual(before, self.ticket_bytes())

    def test_the_handshake_verbs_are_gone_from_the_public_surface(self):
        for verb in ("dispatch-receive", "dispatch-receipt"):
            with self.subTest(verb=verb):
                refusal = tickets._dispatch([verb, "run", "T"])
                self.assertEqual(
                    f"unknown subcommand: {verb}", refusal["error"],
                )
        self.assertNotIn("dispatch-receive", tickets._cmd_help()["help"]["subcommands"])

    def test_uncommitted_projection_still_runs_current_review_validation(self):
        before = self.ticket_bytes()
        owner = tickets._tickets_dispatch_packet_module
        with mock.patch.object(
            owner, "packet_state_result", return_value=(None, "current review is invalid"),
        ):
            refusal = self.project()

        self.assertEqual("review-invalid", refusal["code"])
        self.assertEqual(before, self.ticket_bytes())
        self.assertEqual([], self.ticket_state()["attempts"][0]["records"])

    def test_the_return_address_is_no_longer_a_flag_or_a_field(self):
        """Ten of ten returning children resolved it to nothing: the channel
        is the ticket's records plus the harness notification, so no in-band
        routing fact survives to be validated, carried, or mistyped."""

        before = self.ticket_bytes()

        refused = tickets._dispatch([
            "dispatch-packet", "run", "T", "--dispatch-id", "D1",
            "--reply-to", "root", "--workspace", str(self.candidate),
        ])

        self.assertIn("usage: dispatch-packet", refused["error"])
        self.assertNotIn("--reply-to", refused["error"])
        self.assertEqual(before, self.ticket_bytes())
        self.assertNotIn("reply_to", self.project()["packet"])

    def test_a_committed_packet_replays_before_current_validation(self):
        """A durable record is never re-graded: a stored projection whose
        delivery content today's validation would refuse still replays."""

        self.project()
        text = self.ticket_path.read_text(encoding="utf-8")
        state = parse_canonical_json(
            tickets._parse_frontmatter(text)["dispatch_v1"]
        )
        packet_record = state["attempts"][0]["records"][0]
        stored = parse_canonical_json(packet_record["content"])
        stored["packet"]["review_kind"] = "no-such-lane"
        packet_record["content"] = canonical_json(stored)
        packet_record["success"]["committed_record"]["content"] = stored
        self.ticket_path.write_text(
            tickets._set_frontmatter_field(
                text, "dispatch_v1", canonical_json(state),
            ),
            encoding="utf-8",
        )

        replayed = tickets._dispatch([
            "dispatch-packet", "run", "T", "--dispatch-id", "D1",
            "--workspace", str(self.candidate),
            "--review-kind", "no-such-lane",
        ])

        self.assertEqual(stored, replayed)
        self.assertEqual("no-such-lane", replayed["packet"]["review_kind"])

    def test_legacy_gate_repair_replays_stored_packet_across_head_change(self):
        committed = self.project()
        old_head = subprocess.run(
            ["git", "rev-parse", "HEAD^"], cwd=Path(__file__).resolve().parents[1],
            text=True, capture_output=True, check=True,
        ).stdout.strip()
        current_head = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parents[1],
            text=True, capture_output=True, check=True,
        ).stdout.strip()
        self.assertNotEqual(old_head, current_head)

        legacy_id = "T.gate.repair"
        stored_packet = dict(committed["packet"])
        stored_packet.update({
            "review_kind": "repair",
            "source": {"id": legacy_id, "run": "run"},
        })
        stored = {"packet": stored_packet}
        text = self.ticket_path.read_text(encoding="utf-8")
        data = tickets._parse_frontmatter(text)
        state = parse_canonical_json(data["dispatch_v1"])
        packet_record = state["attempts"][0]["records"][0]
        packet_record["content"] = canonical_json(stored)
        packet_record["success"] = {"committed_record": {
            "content": stored, "dispatch_id": "D1", "id": legacy_id,
            "protocol": "orchflows.dispatch.v1", "record_id": "dispatch-packet",
            "run": "run",
        }}
        legacy_plan = tickets_review._record(
            "GatePlan", None, artifact=f"git:{old_head}",
            criteria=[{
                "identity": "sha256:" + "a" * 64, "lens": "code",
                "order": 0, "ticket": "T.gate.critique.code",
            }],
            isolation="none", mode="gate", pack="orch-code-pack", root="T",
        )
        text = tickets._set_frontmatter_field(text, "id", legacy_id)
        text = tickets._set_frontmatter_field(text, "executor", "orch-execute")
        text = tickets._set_frontmatter_field(text, "review_kind", "repair")
        text = tickets._set_frontmatter_field(
            text, "dispatch_v1", canonical_json(state),
        )
        text = tickets._set_frontmatter_field(
            text, "review_v1", canonical_json({
                "protocol": "orchflows.review.v1", "records": [legacy_plan],
            }),
        )
        legacy_path = self.ticket_path.with_name(f"{legacy_id}.md")
        legacy_path.write_text(text, encoding="utf-8")
        before = legacy_path.read_bytes()

        replayed = tickets._dispatch([
            "dispatch-packet", "run", legacy_id, "--dispatch-id", "D1",
 "--workspace", str(self.candidate),
            "--artifact", f"git:{old_head}", "--review-kind", "repair",
        ])

        self.assertEqual(stored, replayed)
        self.assertEqual(packet_record["content"], canonical_json(replayed))
        self.assertEqual(before, legacy_path.read_bytes())

    def test_projection_refuses_an_unrecorded_candidate_workspace(self):
        text = self.ticket_path.read_text(encoding="utf-8")
        text = "\n".join(
            line for line in text.splitlines()
            if not line.startswith("workspace_path:")
        ) + "\n"
        self.ticket_path.write_text(text, encoding="utf-8")

        refusal = self.project()

        self.assertEqual("workspace-unestablished", refusal["code"])
        self.assertNotIn("packet", refusal)

    def test_projection_refuses_a_workspace_other_than_the_recorded_candidate(self):
        refusal = self.project(workspace="C:/other")

        self.assertEqual("workspace-mismatch", refusal["code"])
        self.assertNotIn("packet", refusal)

    def test_research_projection_requires_the_recorded_store_to_exist(self):
        with tempfile.TemporaryDirectory() as store:
            data = {
                "pack": "orch-research-pack",
                "isolation": "required",
                "workspace_path": store,
            }
            self.assertIsNone(workspace_establishment_finding(data, store))
        finding = workspace_establishment_finding(data, store)
        self.assertEqual("workspace-unestablished", finding[0])

    def test_packet_command_emits_codepage_independent_canonical_ascii(self):
        packet = self.project()["packet"]
        self.assertIn("—", packet["workspace"])
        self.assertIn("—", packet["prompt"])
        script = Path(__file__).resolve().parents[1] / "scripts" / "tickets.py"
        completed = subprocess.run(
            [
                sys.executable, str(script), "dispatch-packet", "run", "T",
                "--dispatch-id", "D1",
                "--workspace", str(self.candidate),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        decoded = completed.stdout.decode("ascii")
        response = json.loads(decoded)
        self.assertEqual(packet, response["packet"])
        expected = json.dumps(
            response, ensure_ascii=True, separators=(",", ":"), sort_keys=True,
        ) + "\n"
        self.assertEqual(expected, decoded)

    def test_the_removed_outcome_content_form_still_refuses(self):
        """The cutover removed the flag; it may not be silently tolerated."""

        self.project()
        before = self.ticket_bytes()

        relayed_content = tickets._dispatch([
            "dispatch-outcome", "run", "T", "--content",
            canonical_json({"status": "complete"}),
        ])
        self.assertEqual("outcome-invalid", relayed_content["code"])
        self.assertNotIn("--content", DISPATCH_OUTCOME_USAGE)
        self.assertEqual(before, self.ticket_bytes())

    def test_committed_projection_replay_precedes_retirement_and_conflict(self):
        committed = self.project()
        self.dispatch(
            "dispatch-retire", "run", "T",
            "--assignment-seal", self.assignment_seal,
            "--dispatch-id", "D1", "--record-id", "lifecycle:retire-1",
        )

        self.assertEqual(committed, self.project())
        changed = tickets._dispatch([
            "dispatch-packet", "run", "T", "--dispatch-id", "D1",
            "--workspace", str(self.candidate) + "-elsewhere",
        ])
        self.assertEqual("idempotency-conflict", changed["code"])


if __name__ == "__main__":
    unittest.main()
