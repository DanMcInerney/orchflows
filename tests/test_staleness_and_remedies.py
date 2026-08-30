"""Staleness heals itself, and a refusal names a command that exists.

Six wedges of one shape: the run was in a lawful state, one mechanical fact
about it had gone stale, and no command repaired it -- so the refusal was
correct and terminal, and a context spent its next twenty minutes
improvising. Each case here fires on the mechanism that heals, not on the
message that reports, because a rewrite keeps the message.
"""

from __future__ import annotations

import ast
import json
import os
import re
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from tests._receiver_vantage import git_checkout, receive_argv, standing_in
from scripts import tickets
from scripts import tickets_admission, tickets_join, tickets_seal, tickets_store
from scripts.tickets_dispatch_inline import _inline_assignment_failure
from scripts.tickets_format import (
    _parse_frontmatter, _section_body, _sections, _set_frontmatter_field,
    _write_section, canonical_json,
)
from scripts.tickets_lifecycle import _snapshot_matches
from scripts.tickets_markdown import quote_filed_body, unquote_filed_body

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"


class SinkTest(unittest.TestCase):
    """One temporary state sink per case, and the dispatch that writes it."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.home = Path(self.temporary.name)
        self.environment = mock.patch.dict(
            os.environ, {"ORCHFLOWS_STATE_HOME": str(self.home)}
        )
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def dispatch(self, *arguments):
        result = tickets._dispatch([str(value) for value in arguments])
        self.assertNotIn("error", result, result)
        return result

    def refuse(self, *arguments):
        result = tickets._dispatch([str(value) for value in arguments])
        self.assertIn("error", result, result)
        return result

    def ticket_path(self, ticket_id, run="run") -> Path:
        return self.home / "tickets" / run / f"{ticket_id}.md"

    def frontmatter(self, ticket_id, run="run") -> dict:
        return _parse_frontmatter(
            self.ticket_path(ticket_id, run).read_text(encoding="utf-8")
        )


class SealedRunTest(SinkTest):
    """A direct root sealed at generation 1, promoted, and claimed."""

    def setUp(self):
        super().setUp()
        self.dispatch(
            "new", "run", "T", "--executor", "orch-execute",
            "--goal", "Deliver the behavior.",
            "--context", "The repository is authoritative.",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.dispatch("stamp-generation", "run", "T")
        self.seal(self.dispatch("draft-validate", "run", "T"))
        self.dispatch("ready", "--run", "run")
        self.lease = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat().replace("+00:00", "Z")
        self.dispatch(
            "dispatch-open", "run", "T", "--by", "worker",
            "--dispatch-id", "D1", "--lease-expires-at", self.lease,
        )
        self.candidate = git_checkout(self.home / "candidate")
        self.stamp_workspace()

    def seal(self, validated):
        return self.dispatch(
            "seal", "run", "T", "--cut-generation",
            validated["draft_validation"]["cut_generation"],
        )

    def stamp_workspace(self):
        """What the dispatch facade's establishment step records."""

        path = self.ticket_path("T")
        text = path.read_text(encoding="utf-8")
        for key, value in (
            ("workspace_path", str(self.candidate)),
            ("workspace_branch", "candidate-branch"),
            ("workspace_baseline", "0123456789abcdef clean"),
        ):
            text = _set_frontmatter_field(text, key, value)
        path.write_text(text, encoding="utf-8")

    def recut(self):
        """The lawful membership change: one checker stage joins the cut."""

        self.dispatch("checker-stage", "run", "T")
        return self.dispatch("draft-validate", "run", "T")

    def project(self):
        return tickets._dispatch([
            "dispatch-packet", "run", "T", "--dispatch-id", "D1",
            "--reply-to", "root", "--workspace", str(self.candidate),
            "--form", "reference",
        ])


class TestARecutRepairsTheReceiptsItInvalidated(SealedRunTest):
    """A seal that re-generations a run re-issues the receipts it stales.

    The claimed root's receipt names generation 1's sealed record. Sealing
    generation 2 leaves it naming a record no grader will consult again, and
    the mandatory next packet is refused for a staleness the seal itself
    introduced -- five times in the friction record before this was written.
    """

    def test_the_seal_reissues_the_claimed_roots_receipt(self):
        before = self.frontmatter("T")["admission"]
        sealed = self.seal(self.recut())["assignment_seal"]
        after = self.frontmatter("T")["admission"]
        self.assertEqual(["T"], sealed["refreshed_admissions"])
        self.assertNotEqual(before, after)

    def test_the_next_packet_emission_needs_no_manual_repair(self):
        self.seal(self.recut())
        projected = self.project()
        self.assertNotIn("error", projected, projected)
        self.assertEqual(
            self.frontmatter("T")["admission"], projected["packet"]["admission"]
        )

    def test_without_the_repair_that_same_packet_is_refused(self):
        """The can-fail direction: the seal is what the packet depends on."""

        with mock.patch.object(
            tickets_seal, "refresh_admissions", return_value=[]
        ):
            self.seal(self.recut())
        refused = self.project()
        self.assertIn("error", refused)
        self.assertIn("admission receipt", refused["error"])

    def test_a_pending_member_is_left_at_its_pending_receipt(self):
        """Only a promoted member holds a receipt; a pending one takes its
        own at promotion, and handing it one early would admit it early."""

        self.seal(self.recut())
        self.assertEqual(
            tickets_admission.ADMISSION_PENDING,
            self.frontmatter("T.check")["admission"],
        )

    def test_resealing_the_same_generation_refreshes_nothing(self):
        validated = self.recut()
        self.seal(validated)
        again = self.seal(validated)["assignment_seal"]
        self.assertEqual([], again["refreshed_admissions"])


class TestTheCompareAndSwapIsScopedToTheGrade(unittest.TestCase):
    """A promotion loses only to a write it actually read.

    The whole-run comparison made every ready lose to any concurrent sibling
    write, including siblings the grade never consulted.
    """

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.run_dir = Path(self.temporary.name) / "run"
        self.run_dir.mkdir(parents=True)
        for name in ("a", "b", "c"):
            (self.run_dir / f"{name}.md").write_text(
                f"---\nid: {name}\n---\n\n## Goal\n\n{name}\n", encoding="utf-8"
            )
        self.snapshot = {
            path.stem: path.read_text(encoding="utf-8")
            for path in self.run_dir.glob("*.md")
        }

    def tearDown(self):
        self.temporary.cleanup()

    def touch(self, name, text="---\nid: x\n---\n\n## Goal\n\nmoved\n"):
        (self.run_dir / f"{name}.md").write_text(text, encoding="utf-8")

    def test_an_unread_sibling_moving_does_not_refuse(self):
        self.touch("c")
        self.assertTrue(_snapshot_matches(self.run_dir, self.snapshot, ["a", "b"]))

    def test_a_read_dependency_moving_refuses(self):
        self.touch("b")
        self.assertFalse(_snapshot_matches(self.run_dir, self.snapshot, ["a", "b"]))

    def test_a_scoped_member_that_vanished_refuses(self):
        (self.run_dir / "b.md").unlink()
        self.assertFalse(_snapshot_matches(self.run_dir, self.snapshot, ["a", "b"]))

    def test_no_scope_still_compares_the_whole_run(self):
        self.touch("c")
        self.assertFalse(_snapshot_matches(self.run_dir, self.snapshot))

    def test_the_grade_names_the_scope_it_read(self):
        """`snapshot_ids` is the grader's own answer, not a caller's guess."""

        grade = tickets_admission.grade_admission(
            "b", "---\nid: b\ndepends_on: [a]\n---\n\n## Goal\n\nb\n",
            {"a": "---\nid: a\nstatus: complete\n---\n"},
        )
        self.assertEqual(["a", "b"], grade["snapshot_ids"])


class TestARefusalNamesACommandThatExists(unittest.TestCase):
    """Every command a script's message tells a caller to run is routed.

    A refusal naming a command that no longer exists is worse than one
    naming none: the caller runs it, gets `unknown subcommand`, and spends
    the next attempt deciding which of the two messages is lying.
    """

    # A delimited reference: the script name opens a quoted span or starts
    # the string, and a bare `tickets.py` in a sentence is prose about the
    # program rather than an instruction to run it.
    REFERENCE = re.compile(r"""(?:^|[`'"])(tickets|workspace)\.py[ ]+([a-z][a-z0-9-]*)""")

    def surfaces(self) -> dict:
        from scripts import workspace

        return {
            "tickets": set(tickets.SUBCOMMAND_USAGE) | {"help"},
            "workspace": set(workspace.COMMAND_USAGE),
        }

    def literals(self, source: str):
        """Every string constant in one module, f-string fragments included."""

        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                yield node.value

    def named_commands(self) -> list:
        found = []
        for path in sorted(SCRIPTS.glob("*.py")):
            for text in self.literals(path.read_text(encoding="utf-8")):
                for script, command in self.REFERENCE.findall(text):
                    found.append((path.name, script, command))
        return found

    def test_every_named_command_is_routed(self):
        surfaces = self.surfaces()
        liars = [
            f"{name}: {script}.py {command}"
            for name, script, command in self.named_commands()
            if command not in surfaces[script]
        ]
        self.assertEqual([], liars)

    def test_the_guard_reads_the_messages_it_is_for(self):
        """Can-fail: a guard that finds nothing proves nothing."""

        found = {(script, command) for _, script, command in self.named_commands()}
        self.assertIn(("tickets", "repair-run-identity"), found)
        self.assertIn(("tickets", "ready"), found)
        self.assertIn(("workspace", "retire"), found)

    def test_an_invented_command_is_caught(self):
        surfaces = self.surfaces()
        sample = "Replay `tickets.py unwedge-everything` to recover"
        caught = [
            command for _script, command in self.REFERENCE.findall(sample)
            if command not in surfaces["tickets"]
        ]
        self.assertEqual(["unwedge-everything"], caught)


class TestATerminalDependencyWithAResultAdmits(unittest.TestCase):
    """`limited` delivered part of the Goal and filed the evidence for it.

    A dependent written against that evidence was refused as though nothing
    had been delivered, so an honest partial close blocked its own
    successor. `blocked` and `failed` filed no artifact and still refuse.
    """

    DEPENDENT = "---\nid: b\ndepends_on: [a]\n---\n\n## Goal\n\nb\n"

    def codes(self, status: str) -> list:
        grade = tickets_admission.grade_admission(
            "b", self.DEPENDENT,
            {"a": f"---\nid: a\nstatus: {status}\n---\n"},
        )
        return [item["code"] for item in grade["findings"]]

    def test_complete_and_limited_carry_a_result(self):
        for status in ("complete", "limited"):
            with self.subTest(status=status):
                self.assertNotIn("dependency-incomplete", self.codes(status))

    def test_the_states_that_filed_nothing_still_refuse(self):
        for status in ("blocked", "failed", "stalled", "claimed", "ready"):
            with self.subTest(status=status):
                self.assertIn("dependency-incomplete", self.codes(status))

    def test_the_result_bearing_set_is_stated_once(self):
        self.assertEqual(
            ("complete", "limited"), tickets_admission.RESULT_BEARING_STATES
        )


class TestRepairingAnUnreadableRunIdentity(SinkTest):
    """The one command that gets a run past a corrupt `run.json`.

    Refusing to overwrite an identity with a guess is right, and until now
    it was terminal: every command reported the same refusal and none
    repaired it.
    """

    def setUp(self):
        super().setUp()
        self.dispatch(
            "new", "run", "T", "--executor", "orch-execute",
            "--goal", "Deliver the behavior.",
            "--context", "The repository is authoritative.",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.identity = self.home / "runs" / "run" / "run.json"

    def corrupt(self):
        self.identity.write_text("{not json", encoding="utf-8")

    def test_an_intact_identity_is_left_exactly_alone(self):
        before = self.identity.read_bytes()
        repaired = self.dispatch("repair-run-identity", "run")
        self.assertEqual("intact", repaired["repair_run_identity"]["outcome"])
        self.assertEqual(before, self.identity.read_bytes())

    def test_a_corrupt_identity_is_quarantined_and_rebuilt(self):
        self.corrupt()
        repaired = self.dispatch("repair-run-identity", "run")["repair_run_identity"]
        self.assertEqual("rebuilt", repaired["outcome"])
        quarantined = Path(repaired["quarantined"])
        self.assertEqual("{not json", quarantined.read_text(encoding="utf-8"))
        rebuilt = json.loads(self.identity.read_text(encoding="utf-8"))
        self.assertEqual("run", rebuilt["run"])
        self.assertIn("opened_at", rebuilt)
        self.assertNotIn("terminal_at", rebuilt)

    def test_the_run_is_writable_again_and_the_repair_replays(self):
        self.corrupt()
        self.dispatch("repair-run-identity", "run")
        self.dispatch("run-state", "run", "--note", "back in service")
        self.assertEqual(
            "intact",
            self.dispatch("repair-run-identity", "run")["repair_run_identity"]["outcome"],
        )

    def test_a_run_with_no_ticket_evidence_is_refused(self):
        refused = self.refuse("repair-run-identity", "other-run")
        self.assertIn("no ticket evidence", refused["error"])
        self.assertFalse((self.home / "runs" / "other-run" / "run.json").exists())

    def test_a_malformed_run_id_is_refused_before_any_lock(self):
        refused = self.refuse("repair-run-identity", "..")
        self.assertIn("run id", refused["error"])

    def test_the_stores_own_refusal_names_this_command(self):
        self.corrupt()
        refused = self.refuse("run-state", "run", "--note", "wedged")
        self.assertIn("tickets.py repair-run-identity run", refused["error"])


class TestAFiledBodyKeepsItsOwnHeadings(SealedRunTest):
    """`## Findings` inside `## Result` is the writer's heading, not a
    sibling ticket section. It was refused about eighteen times; it is now
    indent-quoted on the way in and read back byte for byte."""

    BODY = "## Findings\n\nOne finding.\n\n## Method\n\n- ran the suite\n"

    def file_result(self, body, section="Result"):
        path = self.home / "body.md"
        path.write_text(body, encoding="utf-8")
        return tickets._dispatch([
            "result", "run", "T",
            "--assignment-seal", self.frontmatter("T")["assignment_seal"],
            "--dispatch-id", "D1", "--record-id", "R1", "--by", "worker",
            "--section", section, "--file", str(path),
        ])

    def accept(self):
        packet = self.project()["packet"]
        path = self.home / "packet.json"
        path.write_text(canonical_json(packet), encoding="utf-8")
        with standing_in(self.candidate):
            return self.dispatch(*receive_argv(path, packet, "worker"))

    def test_the_body_survives_the_round_trip(self):
        self.accept()
        self.assertNotIn("error", self.file_result(self.BODY))
        filed = _section_body(
            self.ticket_path("T").read_text(encoding="utf-8"), "Result"
        )
        self.assertIn(self.BODY.strip(), filed)

    def test_the_headings_do_not_become_ticket_sections(self):
        self.accept()
        self.file_result(self.BODY)
        sections = _sections(self.ticket_path("T").read_text(encoding="utf-8"))
        self.assertNotIn("Findings", sections)
        self.assertNotIn("Method", sections)

    def test_the_quoting_is_injective_and_byte_stable(self):
        """A body's own leading whitespace has never survived the read --
        `_section_body` strips it -- so these bodies open at column zero, as
        a filed one does behind its writer attribution."""

        ticket = "---\nid: a\n---\n\n## Result\n\n[]\n"
        for body in (
            "## a", "## a\n\n ## b\n\n  ## c", "prose\n\n ## indented",
            "### deeper\n\n## a\n", "no headings at all",
        ):
            with self.subTest(body=body):
                written = _write_section(ticket, "Result", body)
                read_back = _section_body(written, "Result")
                self.assertEqual(body.strip(), read_back)
                self.assertEqual(written, _write_section(ticket, "Result", read_back))

    def test_a_cut_section_is_left_exactly_as_authored(self):
        """Goal, Context and Suggested files feed the assignment digest, so
        nothing here may re-spell them."""

        for heading in ("Goal", "Context", "Suggested files"):
            with self.subTest(heading=heading):
                self.assertEqual("## a", quote_filed_body(heading, "## a"))
                self.assertEqual("## a", unquote_filed_body(heading, "## a"))


class TestDependsOnIsCanonicallyOrdered(SinkTest):
    """Two orderings of one edge set are two assignment digests.

    The digest is not changed to absorb that -- every historical seal would
    stop verifying -- so the order is settled where the list is authored.
    """

    def issue(self, ticket_id, depends_on=None):
        arguments = [
            "new", "run", ticket_id, "--executor", "orch-execute",
            "--goal", "Deliver the behavior.",
            "--context", "The repository is authoritative.",
            "--pack", "orch-code-pack", "--isolation", "required",
        ]
        if depends_on is not None:
            arguments.extend(("--depends-on", depends_on))
        return self.dispatch(*arguments)

    def test_the_authoring_flag_writes_them_sorted(self):
        self.issue("a")
        self.issue("b")
        self.issue("c", depends_on="b,a")
        self.assertEqual(["a", "b"], self.frontmatter("c")["depends_on"])

    def test_no_dependency_still_writes_the_empty_list(self):
        self.issue("a")
        self.assertEqual([], self.frontmatter("a")["depends_on"])

    def test_the_finding_names_the_order_it_wants(self):
        findings = tickets_admission.dependency_order_findings(
            "c", {"depends_on": ["b", "a"]}
        )
        self.assertEqual(["depends-on-unsorted"], [item["code"] for item in findings])
        self.assertIn("a, b", findings[0]["detail"])
        self.assertEqual(
            [], tickets_admission.dependency_order_findings("c", {"depends_on": ["a", "b"]})
        )

    def test_draft_validation_refuses_an_unsorted_member(self):
        self.issue("R")
        path = self.ticket_path("R")
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "depends_on: []", "depends_on: [b, a]"
            ),
            encoding="utf-8",
        )
        self.dispatch("stamp-generation", "run", "R")
        refused = self.refuse("draft-validate", "run", "R")
        self.assertIn(
            "depends-on-unsorted", [item["code"] for item in refused["findings"]]
        )


class TestPendingNamesItsPromotion(SinkTest):
    """`dispatch-open` on a pending ticket is one command away from working,
    and said only that the status was wrong."""

    def setUp(self):
        super().setUp()
        self.dispatch(
            "new", "run", "T", "--executor", "orch-execute",
            "--goal", "Deliver the behavior.",
            "--context", "The repository is authoritative.",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.dispatch("stamp-generation", "run", "T")
        validated = self.dispatch("draft-validate", "run", "T")
        self.dispatch(
            "seal", "run", "T", "--cut-generation",
            validated["draft_validation"]["cut_generation"],
        )
        self.lease = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat().replace("+00:00", "Z")

    def open_it(self):
        return self.refuse(
            "dispatch-open", "run", "T", "--by", "worker",
            "--dispatch-id", "D9", "--lease-expires-at", self.lease,
        )

    def test_the_refusal_names_the_promotion(self):
        """This is the door a claim on a pending ticket actually reaches:
        the receipt is still the placeholder, so the admission grade refuses
        before the status check downstream is ever consulted."""

        refused = self.open_it()
        self.assertEqual("admission-mismatch", refused["code"])
        self.assertIn("tickets.py ready --run run", refused["error"])

    def test_a_stale_receipt_is_not_told_to_promote(self):
        """A promoted ticket whose receipt went stale is a different repair,
        and sending it to `ready` would be the wrong instruction."""

        self.dispatch("ready", "--run", "run")
        path = self.ticket_path("T")
        path.write_text(
            _set_frontmatter_field(
                path.read_text(encoding="utf-8"), "admission",
                "git:sha256:" + "0" * 64,
            ),
            encoding="utf-8",
        )
        refused = self.open_it()
        self.assertEqual("admission-mismatch", refused["code"])
        self.assertNotIn("tickets.py ready", refused["error"])

    def test_the_named_promotion_is_the_one_that_works(self):
        self.open_it()
        self.dispatch("ready", "--run", "run")
        self.dispatch(
            "dispatch-open", "run", "T", "--by", "worker",
            "--dispatch-id", "D9", "--lease-expires-at", self.lease,
        )


class TestTheJoinsTerminalWriteIsInsideTheLock(SealedRunTest):
    """The join's record commit and the run's terminal timing are one
    critical section on the direct route too.

    The identity is written once and never rewritten, so a loss in the
    window between `_commit_record` releasing its lock and the timing write
    is permanent.
    """

    def close(self):
        outcome = self.home / "outcome.json"
        evidence = {name: "" for name in (
            "Result", "Verification", "Feedback", "Risks", "Handoff",
        )}
        evidence.update({
            "Result": "Delivered.", "Verification": "Ran the suite.",
            "Feedback": "[]", "Risks": "[]",
        })
        outcome.write_text(canonical_json({
            "protocol": "orchflows.dispatch.v1", "run": "run", "id": "T",
            "assignment_seal": self.frontmatter("T")["assignment_seal"],
            "dispatch_id": "D1", "outcome_record_id": "outcome",
            "by": "worker", "status": "complete", "evidence": evidence,
        }), encoding="utf-8")
        packet = self.project()["packet"]
        path = self.home / "packet.json"
        path.write_text(canonical_json(packet), encoding="utf-8")
        with standing_in(self.candidate):
            self.dispatch(*receive_argv(path, packet, "worker"))
        self.dispatch("dispatch-outcome", "run", "T", "--file", str(outcome))
        return outcome

    def test_the_identity_is_stamped_while_the_run_lock_is_held(self):
        """A second acquirer cannot get the lock at the moment of the write.

        The probe is a thread rather than an inspection of the source: what
        must hold is that the lock is *held*, not that some line mentions it.
        """

        self.close()
        held, probes = [], []
        original = tickets_join._write_identity

        def probing_write(identity_dir, document):
            waiting = threading.Thread(target=self.take_the_lock, daemon=True)
            probes.append(waiting)
            waiting.start()
            waiting.join(timeout=2.0)
            held.append(waiting.is_alive())
            return original(identity_dir, document)

        with mock.patch.object(tickets_join, "_write_identity", probing_write):
            self.dispatch(
                "dispatch-join", "run", "T",
                "--assignment-seal", self.frontmatter("T")["assignment_seal"],
                "--dispatch-id", "D1", "--outcome-record-id", "outcome",
                "--by", "joiner",
            )
        for probe in probes:
            # Released now, so the probe finishes and closes its handle;
            # Windows will not remove the sink while one is still open.
            probe.join(timeout=30.0)
            self.assertFalse(probe.is_alive(), "the run lock was never released")
        self.assertEqual([True], held, "the terminal identity was written unlocked")

    def take_the_lock(self):
        with tickets_store._run_lock("run"):
            pass

    def test_the_join_still_records_the_terminal_timing(self):
        self.close()
        self.dispatch(
            "dispatch-join", "run", "T",
            "--assignment-seal", self.frontmatter("T")["assignment_seal"],
            "--dispatch-id", "D1", "--outcome-record-id", "outcome",
            "--by", "joiner",
        )
        identity = json.loads(
            (self.home / "runs" / "run" / "run.json").read_text(encoding="utf-8")
        )
        self.assertEqual("complete", identity["terminal_status"])
        self.assertEqual("T", identity["terminal_ticket_id"])


class TestInlineIsolationIsReadTheOneWay(unittest.TestCase):
    """The seal stores the rare declared override verbatim and the packet
    carries the derived value, so both sides read through the one
    derivation: absent on a git pack derives `required`."""

    def packet(self, **overrides) -> dict:
        base = {
            "assigned_name": "worker", "assignment_seal": "sha256:" + "0" * 64,
            "dispatch_id": "D1", "durability": "ticket", "executor": "orch-execute",
            "form": "inline", "independence": "checker", "isolation": "none",
            "lease_expires_at": "2026-01-01T00:00:00Z", "outcome_record_id": "outcome",
            "pack": "orch-code-pack", "profile": "orch-worker", "review_kind": None,
            "reply_to": "root", "role": "worker",
            "source": {"id": "T", "run": "run"}, "workspace": None,
        }
        base.update(overrides)
        return base

    def assignment(self, **system) -> dict:
        return {
            "semantic": {}, "dependencies": [], "executor": "orch-execute",
            "system": dict({"pack": "orch-code-pack"}, **system), "ticket": "T",
        }

    def sealed(self, packet: dict, assignment: dict) -> dict:
        from scripts.tickets_dispatch_inline import _semantic_digest

        envelope = {
            key: packet.get(key) for key in (
                "assigned_name", "assignment_seal", "dispatch_id", "durability",
                "lease_expires_at", "outcome_record_id", "reply_to", "role",
                "profile", "review_kind", "source", "workspace",
            )
        }
        envelope["assignment"] = assignment
        return dict(packet, inline={
            "assignment": assignment, "envelope_seal": _semantic_digest(envelope),
        })

    def test_an_absent_isolation_field_accepts_the_derived_packet(self):
        assignment = self.assignment()
        packet = self.sealed(self.packet(isolation="required"), assignment)
        self.assertIsNone(_inline_assignment_failure(packet, assignment))

    def test_a_backticked_isolation_value_still_accepts(self):
        assignment = self.assignment(isolation="`required`")
        packet = self.sealed(self.packet(isolation="required"), assignment)
        self.assertIsNone(_inline_assignment_failure(packet, assignment))

    def test_a_real_divergence_is_still_refused(self):
        assignment = self.assignment(isolation="required")
        packet = self.sealed(self.packet(isolation="none"), assignment)
        failure = _inline_assignment_failure(packet, assignment)
        self.assertEqual("assignment-divergent", failure["code"])


class TestIdempotencyConflictsNameDistinctRemedies(SealedRunTest):
    """Three refusals share one code, `idempotency-conflict`, and until now
    one message: a reopened dispatch id, a recommitted record, and a reused
    replacement id were all silent on the fix, or -- worse -- pointed a
    driver at attempt surgery (`dispatch-retire`) that a different cause's
    refusal does not accept.
    """

    def replace(self, dispatch_id, replacement_id, record_id):
        return tickets._dispatch([
            "dispatch-replace", "run", "T",
            "--assignment-seal", self.frontmatter("T")["assignment_seal"],
            "--dispatch-id", dispatch_id, "--record-id", record_id,
            "--replacement-dispatch-id", replacement_id,
            "--by", "worker", "--lease-expires-at", self.lease,
            "--supersede-live",
        ])

    def test_a_reopened_dispatch_id_is_pointed_at_dispatch_and_replace(self):
        changed = self.refuse(
            "dispatch-open", "run", "T", "--by", "worker",
            "--dispatch-id", "D1", "--lease-expires-at", "2099-01-01T00:00:00Z",
        )
        self.assertEqual("idempotency-conflict", changed["code"])
        self.assertIn("`tickets.py dispatch`", changed["error"])
        self.assertIn("`tickets.py dispatch-replace`", changed["error"])
        self.assertNotIn("--record-id", changed["error"])
        self.assertNotIn("--replacement-dispatch-id", changed["error"])

    def test_a_recommitted_record_is_pointed_at_a_fresh_record_id(self):
        self.assertNotIn("error", self.dispatch(
            "dispatch-commit", "run", "T", "--dispatch-id", "D1",
            "--record-id", "R1", "--content", '{"value":1}',
        ))
        conflict = self.refuse(
            "dispatch-commit", "run", "T", "--dispatch-id", "D1",
            "--record-id", "R1", "--content", '{"value":2}',
        )
        self.assertEqual("idempotency-conflict", conflict["code"])
        self.assertIn("--record-id", conflict["error"])
        self.assertNotIn("dispatch-replace", conflict["error"])
        self.assertNotIn("--replacement-dispatch-id", conflict["error"])

    def test_a_reused_replacement_id_is_pointed_at_a_fresh_replacement_id(self):
        self.assertNotIn(
            "error", self.replace("D1", "D2", "lifecycle:replace-1")
        )
        conflict = self.refuse(
            "dispatch-replace", "run", "T",
            "--assignment-seal", self.frontmatter("T")["assignment_seal"],
            "--dispatch-id", "D2", "--record-id", "lifecycle:replace-2",
            "--replacement-dispatch-id", "D1",
            "--by", "worker", "--lease-expires-at", self.lease,
            "--supersede-live",
        )
        self.assertEqual("idempotency-conflict", conflict["code"])
        self.assertIn("--replacement-dispatch-id", conflict["error"])
        self.assertNotIn("--record-id", conflict["error"])
        self.assertNotIn("fresh --dispatch-id", conflict["error"])


if __name__ == "__main__":
    unittest.main()
