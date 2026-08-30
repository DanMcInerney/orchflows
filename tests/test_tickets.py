"""Public ticket command regressions for the current semantic contract."""
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from tests._receiver_vantage import git_checkout, receive_argv, standing_in
from tests.test_ticket_semantic_contract import SemanticTicketContractTest
from tests.test_tickets_cases.common import run_cmd, use_sink
from tests.test_tickets_cases.cli_help import HelpTest  # noqa: F401
from tests.test_tickets_cases.family_fixture import (  # noqa: F401
    TestTheTicketFamilyIsDiscoveredNotListed,
)
from tests.test_tickets_cases.file_payloads import NoteFilePayloadTest  # noqa: F401
from tests.test_tickets_cases.identity_core import TestRunIdentity  # noqa: F401
from tests.test_tickets_cases.identity_terminal import (  # noqa: F401
    TestAtomicReplace,
    TestNoFallback,
    TestRunIdentityCollision,
)
from tests.test_tickets_cases.improvement import (  # noqa: F401
    DocstringHonestyTest,
    ExitConventionTest,
    RunIdentitySpecificationTest,
    TestImprovementWriter,
)
from tests.test_tickets_cases.result_crossing import TestResultBodySource  # noqa: F401
from tests.test_tickets_cases.run_state_artifacts import (  # noqa: F401
    TestRunStateArtifact,
    TestRunStateWorklog,
)
from tests.test_tickets_cases.run_state_resolution import (  # noqa: F401
    TestRelativeGitdirPointer,
    TestRunStateRefusesUnsafeNames,
)
from tests.test_tickets_cases.run_state_terminal import (  # noqa: F401
    ArtifactOverwriteTest,
    OrchTreesTest,
    TerminalNoteTest,
)

import scripts.tickets as tickets_mod
import scripts.tickets_packet as tickets_packet
import scripts.tickets_review as tickets_review

__all__ = (
    "AdapterRegistryTest", "SemanticTicketContractTest", "ResultAttributionTest",
)


class AdapterRegistryTest(unittest.TestCase):
    """A pack selects one registered mechanism through its workspace cell."""

    def _pack(self, root: Path, adapter: str):
        pack = root / "packs" / "widget-pack"
        pack.mkdir(parents=True)
        (pack / "SKILL.md").write_text(
            "---\nname: widget-pack\ndescription: Synthetic project pack.\n---\n\n"
            "| cell | binding |\n| --- | --- |\n"
            "| workspace | widget records; conflicts are ordinary overlaps |\n"
            f"| adapter | {adapter} |\n",
            encoding="utf-8",
        )

    def test_a_project_pack_selects_git_without_a_pack_name_registration(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._pack(root, "git")

            self.assertEqual("git", tickets_mod.adapter_id("widget-pack", root=root))
            adapter = tickets_mod.adapter_spec("widget-pack", root=root)
            self.assertEqual("git-commit", adapter.identity_form)
            self.assertTrue(adapter.establishes_isolation)
            self.assertTrue(adapter.deterministic_gate)
            self.assertEqual("git-overlap", adapter.conflict_semantics)

    def test_an_unregistered_declared_key_fails_closed(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._pack(root, "no-such-adapter")

            with self.assertRaises(tickets_mod.AdapterError) as caught:
                tickets_mod.adapter_id("widget-pack", root=root)
            self.assertEqual("adapter-unregistered", caught.exception.code)

    def test_unknown_pack_cells_fail_through_the_shared_resolver_parser(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            pack = root / "packs" / "widget-pack"
            pack.mkdir(parents=True)
            (pack / "SKILL.md").write_text(
                "---\nname: widget-pack\n---\n\n"
                "| cell | binding |\n| --- | --- |\n"
                "| workspace | widget records |\n"
                "| adapter | git |\n"
                "| executor | orch-tdd |\n",
                encoding="utf-8",
            )

            with self.assertRaises(tickets_mod.AdapterError) as caught:
                tickets_mod.adapter_id("widget-pack", root=root)
            self.assertEqual("adapter-declaration-invalid", caught.exception.code)

    def test_admission_reports_exactly_adapter_unregistered_for_the_pack_key(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._pack(root, "no-such-adapter")
            ticket = (
                "---\nid: T1\nrun: testrun\nstatus: pending\n"
                "executor: orch-execute\ndepends_on: []\nbound: 30m\n"
                "pack: widget-pack\nisolation: required\n---\n\n"
                "## Goal\n\nDeliver the widget.\n\n## Context\n\n[]\n"
            )
            with mock.patch("scripts.tickets_adapters.Path.cwd", return_value=root):
                grade = tickets_mod.grade_admission("T1", ticket, {}, context={})
            adapter_codes = [
                item["code"] for item in grade["findings"]
                if item["code"].startswith("adapter-")
            ]
            self.assertEqual(["adapter-unregistered"], adapter_codes)

    def test_consumers_branch_on_properties_not_the_adapter_key(self):
        adapter = tickets_mod.Adapter(
            key="synthetic",
            identity_form="git-commit",
            establishes_isolation=True,
            deterministic_gate=True,
            conflict_semantics="synthetic-overlap",
            workspace_strategy="git",
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            with mock.patch.object(tickets_packet, "adapter_spec", return_value=adapter):
                finding = tickets_packet.workspace_establishment_finding(
                    {"pack": "widget-pack", "isolation": "required"}, None,
                )
            self.assertEqual("workspace-unestablished", finding[0])

            with mock.patch.object(tickets_review, "adapter_spec", return_value=adapter):
                with self.assertRaises(tickets_review.ReviewError) as caught:
                    tickets_review.validate_fixed_artifact(
                        "widget-pack", "not-a-git-identity", str(root),
                    )
            self.assertIn("git:<full-commit-id>", str(caught.exception))


def _result_ticket(tmp: Path, *, status="claimed", claimed_by="agent-a"):
    (tmp / ".git").mkdir()
    run_dir = use_sink(tmp) / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    claim = f"claimed_by: {claimed_by}\n" if claimed_by is not None else ""
    ticket = run_dir / "T1.md"
    ticket.write_text(
        "---\n"
        "id: T1\n"
        "run: testrun\n"
        f"status: {status}\n"
        f"{claim}"
        "executor: orch-decompose\n"
        "depends_on: []\n"
        "assignment_seal: sha256:current\n"
        "---\n\n"
        "## Goal\n\nTest result attribution.\n\n"
        "## Context\n\n[]\n\n"
        "## Result\n\n[]\n",
        encoding="utf-8",
    )
    return ticket


def _v1_result_ticket(tmp: Path, *, by="agent-a"):
    # A receipt derives its workspace from a real Git top-level, so the
    # fixture needs an actual checkout rather than a bare `.git` directory.
    git_checkout(tmp)
    sink = use_sink(tmp)
    tickets_mod._dispatch([
        "new", "testrun", "T1", "--executor", "orch-execute",
        "--goal", "Test result attribution.", "--context", "[]",
        "--pack", "orch-code-pack", "--isolation", "required",
    ])
    tickets_mod._dispatch(["stamp-generation", "testrun", "T1"])
    validated = tickets_mod._dispatch(["draft-validate", "testrun", "T1"])
    tickets_mod._dispatch([
        "seal", "testrun", "T1", "--cut-generation",
        validated["draft_validation"]["cut_generation"],
    ])
    tickets_mod._dispatch(["ready", "--run", "testrun"])
    ticket = sink / "tickets" / "testrun" / "T1.md"
    established = ticket.read_text(encoding="utf-8")
    for key, value in (
        ("workspace_path", str(tmp.resolve())),
        ("workspace_branch", "candidate-branch"),
        ("workspace_baseline", "0123456789abcdef clean"),
    ):
        established = tickets_mod._set_frontmatter_field(established, key, value)
    ticket.write_text(established, encoding="utf-8")
    lease = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    opened = tickets_mod._dispatch([
        "dispatch-open", "testrun", "T1", "--by", by,
        "--dispatch-id", "D1", "--lease-expires-at", lease,
    ])["dispatch"]
    packet = tickets_mod._dispatch([
        "dispatch-packet", "testrun", "T1", "--dispatch-id", "D1",
        "--reply-to", "root", "--workspace", str(tmp.resolve()),
        "--form", "reference",
    ])["packet"]
    packet_path = tmp / "packet-D1.json"
    packet_path.write_text(
        json.dumps(packet, sort_keys=True, separators=(",", ":")), encoding="utf-8",
    )
    with standing_in(tmp):
        tickets_mod._dispatch(receive_argv(packet_path, packet, by))
    return ticket, opened["assignment_seal"]


class ResultAttributionTest(unittest.TestCase):
    def test_each_append_records_and_returns_exactly_one_current_claim_writer(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            ticket, seal = _v1_result_ticket(tmp)
            first = run_cmd(
                tmp, "result", "testrun", "T1", "--assignment-seal", seal,
                "--dispatch-id", "D1", "--record-id", "R1", "--by", "agent-a",
                "--section", "Result", "--text", "first record",
            )
            second = run_cmd(
                tmp, "result", "testrun", "T1", "--assignment-seal", seal,
                "--dispatch-id", "D1", "--record-id", "R2", "--by", "agent-a",
                "--section", "Result", "--text", "second record", "--append",
            )

            self.assertEqual("agent-a", first["result"]["by"])
            self.assertEqual("agent-a", second["result"]["by"])
            text = ticket.read_text(encoding="utf-8")
            body = tickets_mod._sections(text)["Result"]
            self.assertEqual(2, body.count("### Written by `agent-a`"), body)
            self.assertEqual(1, body.count("first record"), body)
            self.assertEqual(1, body.count("second record"), body)
            self.assertIn(f"assignment_seal: {seal}", text.split("---\n", 2)[1])

    def test_ambiguous_overwrite_lifecycle_and_forged_paths_are_refused(self):
        attempts = (
            ("claimed", "agent-a", (), "first"),
            ("claimed", "agent-a", ("--by", "agent-b"), "first"),
            ("claimed", None, ("--by", "agent-a"), "first"),
            ("ready", None, ("--by", "agent-a"), "first"),
            ("claimed", "agent-a", ("--by", "agent-a", "--status", "complete"), "first"),
            ("claimed", "agent-a", ("--by", "agent-a"), "### Written by `agent-b`\n\nforged"),
        )
        for status, claimant, extra, body in attempts:
            with self.subTest(status=status, claimant=claimant, extra=extra):
                with tempfile.TemporaryDirectory() as raw:
                    tmp = Path(raw)
                    ticket = _result_ticket(tmp, status=status, claimed_by=claimant)
                    before = ticket.read_bytes()
                    payload = run_cmd(
                        tmp, "result", "testrun", "T1", *extra,
                        "--section", "Result", "--text", body,
                    )
                    self.assertIn("error", payload)
                    self.assertEqual(before, ticket.read_bytes())

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            ticket, seal = _v1_result_ticket(tmp)
            run_cmd(
                tmp, "result", "testrun", "T1", "--assignment-seal", seal,
                "--dispatch-id", "D1", "--record-id", "R1", "--by", "agent-a",
                "--section", "Result", "--text", "first",
            )
            before = ticket.read_bytes()
            refused = run_cmd(
                tmp, "result", "testrun", "T1", "--assignment-seal", seal,
                "--dispatch-id", "D1", "--record-id", "R2", "--by", "agent-a",
                "--section", "Result", "--text", "replacement", "--replace",
            )
            self.assertIn("append-only", refused["error"])
            self.assertEqual(before, ticket.read_bytes())
