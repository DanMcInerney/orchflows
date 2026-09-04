"""Public ticket command regressions for the current semantic contract."""
import contextlib
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from tests import _retired_commands as retired_commands
from tests._candidate_checkout import (
    git_checkout, record_established_workspace,
)
from tests.test_ticket_semantic_contract import SemanticTicketContractTest
from tests.test_tickets_cases.common import run_cmd, use_sink
from tests.test_tickets_cases.cli_help import HelpTest  # noqa: F401
from tests.test_tickets_cases.escaped_newline import (  # noqa: F401
    EscapedNewlineShapeTest,
)
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

import scripts.rings_trust as rings_trust
import scripts.state_root as state_root
import scripts.tickets as tickets_mod
import scripts.tickets_assignment as tickets_assignment
import scripts.tickets_dispatch_launch as launch_module

from tests._repo_root import ROOT

__all__ = (
    "AdapterRegistryTest", "PackPinTest", "SemanticTicketContractTest",
    "ResultAttributionTest",
)


class AdapterRegistryTest(unittest.TestCase):
    """A pack selects one registered mechanism through its typed adapter cell."""

    @contextlib.contextmanager
    def _project(self):
        """A trusted project ring under a temporary home.

        The ring is `<root>/.orchflows/packs`, the one fixed path
        `scripts/rings.py` reads; the bare `<root>/packs` this fixture used
        to write is no longer a resolution root anywhere.
        """

        with tempfile.TemporaryDirectory() as raw, tempfile.TemporaryDirectory() as raw_home:
            root = Path(raw).resolve()
            home = Path(raw_home).resolve()
            (root / ".orchflows" / "packs").mkdir(parents=True)
            with mock.patch.dict(os.environ, {state_root.ENV_VAR: str(home / "state")}):
                yield root

    def _pack(self, root: Path, adapter: str, body: str = None):
        pack = root / ".orchflows" / "packs" / "widget-pack"
        pack.mkdir(parents=True, exist_ok=True)
        (pack / "SKILL.md").write_text(
            body if body is not None else (
                "---\nname: widget-pack\ndescription: Synthetic project pack.\n---\n\n"
                "| cell | binding |\n| --- | --- |\n"
                f"| adapter | {adapter} |\n"
            ),
            encoding="utf-8",
        )
        rings_trust.grant(root / ".orchflows")

    def test_a_project_pack_selects_git_without_a_pack_name_registration(self):
        with self._project() as root:
            self._pack(root, "git")

            self.assertEqual("git", tickets_mod.adapter_id("widget-pack", root=root))
            adapter = tickets_mod.adapter_spec("widget-pack", root=root)
            self.assertEqual("git", adapter.artifact_kind)
            self.assertTrue(adapter.establishes_isolation)
            self.assertTrue(adapter.deterministic_gate)
            self.assertEqual("git", adapter.workspace_strategy)

    def test_an_untrusted_project_pack_refuses_before_its_adapter_is_read(self):
        with self._project() as root:
            self._pack(root, "git")
            rings_trust.revoke(root / ".orchflows")

            with self.assertRaises(tickets_mod.AdapterError) as caught:
                tickets_mod.adapter_id("widget-pack", root=root)
            self.assertEqual("pack-untrusted", caught.exception.code)

    def test_an_unregistered_declared_key_fails_closed(self):
        with self._project() as root:
            self._pack(root, "no-such-adapter")

            with self.assertRaises(tickets_mod.AdapterError) as caught:
                tickets_mod.adapter_id("widget-pack", root=root)
            self.assertEqual("adapter-unregistered", caught.exception.code)

    def test_unknown_pack_cells_fail_through_the_shared_resolver_parser(self):
        with self._project() as root:
            self._pack(root, "git", body=(
                "---\nname: widget-pack\n---\n\n"
                "| cell | binding |\n| --- | --- |\n"
                "| workspace | widget records |\n"
                "| adapter | git |\n"
                "| executor | orch-tdd |\n"
            ))

            with self.assertRaises(tickets_mod.AdapterError) as caught:
                tickets_mod.adapter_id("widget-pack", root=root)
            self.assertEqual("adapter-declaration-invalid", caught.exception.code)

    def test_admission_reports_exactly_adapter_unregistered_for_the_pack_key(self):
        with self._project() as root:
            self._pack(root, "no-such-adapter")
            ticket = (
                "---\nid: T1\nrun: testrun\nstatus: pending\n"
                "executor: orch-do\ndepends_on: []\nbound: 30m\n"
                "pack: widget-pack\nisolation: required\n---\n\n"
                "## Goal\n\nDeliver the widget.\n\n## Context\n\n[]\n"
            )
            with mock.patch("scripts.rings.Path.cwd", return_value=root):
                grade = tickets_mod.grade_admission("T1", ticket, {}, context={})
            adapter_codes = [
                item["code"] for item in grade["findings"]
                if item["code"].startswith("adapter-")
            ]
            self.assertEqual(["adapter-unregistered"], adapter_codes)

    def test_consumers_branch_on_properties_not_the_adapter_key(self):
        adapter = tickets_mod.Adapter(
            key="synthetic",
            artifact_kind="git",
            establishes_isolation=True,
            deterministic_gate=True,
            workspace_strategy="git",
            commits_in_place=True,
        )
        with mock.patch.object(tickets_assignment, "adapter_spec", return_value=adapter):
            finding = tickets_assignment.workspace_establishment_finding(
                {"pack": "widget-pack", "isolation": "required"}, None,
            )
        self.assertEqual("workspace-unestablished", finding[0])


def _result_ticket(tmp: Path, *, status="claimed", claimed_by="agent-a"):
    # The lease is the dispatch attempt; the fixture writes the record the
    # attribution check reads through lease_of.
    (tmp / ".git").mkdir()
    run_dir = use_sink(tmp) / "tickets" / "testrun"
    run_dir.mkdir(parents=True)
    claim = ""
    if claimed_by is not None:
        state = {"protocol": "orchflows.dispatch.v1", "attempts": [{
            "assignment_seal": "sha256:sealed", "dispatch_id": "D1",
            "lease_expires_at": "2099-01-01T00:00:00Z",
            "opened_at": "2026-01-01T00:00:00Z",
            "outcome_record_id": "outcome", "owner": claimed_by,
            "records": [], "state": "live",
        }]}
        claim = "dispatch_v1: " + json.dumps(state, separators=(",", ":"), sort_keys=True) + "\n"
    ticket = run_dir / "T1.md"
    ticket.write_text(
        "---\n"
        "id: T1\n"
        "run: testrun\n"
        f"status: {status}\n"
        f"{claim}"
        "executor: orch-slice\n"
        "depends_on: []\n"
        "assignment_seal: sha256:current\n"
        "---\n\n"
        "## Goal\n\nTest result attribution.\n\n"
        "## Context\n\n[]\n\n"
        "## Report\n",
        encoding="utf-8",
    )
    return ticket


def _v1_result_ticket(tmp: Path, *, by="agent-a"):
    # The establishment grade reads git from inside the candidate, so the
    # fixture needs an actual checkout rather than a bare `.git` directory.
    git_checkout(tmp)
    sink = use_sink(tmp)
    retired_commands.run([
        "new", "testrun", "T1", "--executor", "orch-do",
        "--goal", "Test result attribution.", "--context", "[]",
        "--pack", "orch-code-pack", "--isolation", "required",
    ])
    retired_commands.run(["stamp-generation", "testrun", "T1"])
    validated = retired_commands.run(["draft-validate", "testrun", "T1"])
    retired_commands.run([
        "seal", "testrun", "T1", "--cut-generation",
        validated["draft_validation"]["cut_generation"],
    ])
    retired_commands.run(["ready", "--run", "testrun"])
    ticket = sink / "tickets" / "testrun" / "T1.md"
    established = ticket.read_text(encoding="utf-8")
    for key, value in (
        ("workspace_branch", "candidate-branch"),
        ("workspace_baseline", "0123456789abcdef clean"),
    ):
        established = tickets_mod._set_frontmatter_field(established, key, value)
    ticket.write_text(established, encoding="utf-8")
    lease = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    opened = retired_commands.run([
        "dispatch-open", "testrun", "T1", "--by", by,
        "--dispatch-id", "D1", "--lease-expires-at", lease,
    ])["dispatch"]
    record_established_workspace(ticket, tmp.resolve())
    # the committed launch every execution record enters behind, at the
    # facade seam that owns it -- there is no verb for the launch alone
    host, failure = launch_module.resolve_host(launch_module.DEFAULT_HOST)
    assert failure is None, failure
    launched = tickets_mod._tickets_dispatch_facade_module._launched_under_run_lock(
        "testrun", "T1", host, dispatch_id="D1",
        workspace=str(tmp.resolve()),
    )
    assert "error" not in launched, launched
    return ticket, opened["assignment_seal"]


class ResultAttributionTest(unittest.TestCase):
    def test_each_append_records_and_returns_exactly_one_current_claim_writer(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            ticket, seal = _v1_result_ticket(tmp)
            first = run_cmd(
                tmp, "result", "testrun", "T1", "--assignment-seal", seal,
                "--dispatch-id", "D1", "--record-id", "R1", "--by", "agent-a",
                "--text", "first record",
            )
            second = run_cmd(
                tmp, "result", "testrun", "T1", "--assignment-seal", seal,
                "--dispatch-id", "D1", "--record-id", "R2", "--by", "agent-a",
                "--text", "second record",
            )

            self.assertEqual("agent-a", first["result"]["by"])
            self.assertEqual("agent-a", second["result"]["by"])
            text = ticket.read_text(encoding="utf-8")
            body = tickets_mod._sections(text)["Report"]
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
                        "--text", body,
                    )
                    self.assertIn("error", payload)
                    self.assertEqual(before, ticket.read_bytes())

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            ticket, seal = _v1_result_ticket(tmp)
            run_cmd(
                tmp, "result", "testrun", "T1", "--assignment-seal", seal,
                "--dispatch-id", "D1", "--record-id", "R1", "--by", "agent-a",
                "--text", "first",
            )
            before = ticket.read_bytes()
            refused = run_cmd(
                tmp, "result", "testrun", "T1", "--assignment-seal", seal,
                "--dispatch-id", "D1", "--record-id", "R2", "--by", "agent-a",
                "--section", "Result", "--text", "replacement",
            )
            self.assertIn("--section", refused["error"])
            self.assertEqual(before, ticket.read_bytes())


class PackPinTest(unittest.TestCase):
    """The seal is the lockfile: what you approved is what runs."""

    @contextlib.contextmanager
    def _pinned_world(self):
        """A trusted project ring holding one complete pack, and a sink."""

        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw).resolve()
            use_sink(tmp)
            (tmp / ".git").mkdir()
            pack = tmp / ".orchflows" / "packs" / "widget-pack"
            pack.mkdir(parents=True)
            source = ROOT / "packs" / "orch-code-pack"
            for path in source.rglob("*"):
                if path.is_file():
                    target = pack / path.relative_to(source)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(path.read_bytes())
            skill = pack / "SKILL.md"
            skill.write_bytes(
                skill.read_bytes().replace(b"name: orch-code-pack", b"name: widget-pack")
            )
            with mock.patch.dict(
                os.environ, {state_root.ENV_VAR: str(tmp / "state-sink")}
            ), mock.patch("scripts.rings.Path.cwd", return_value=tmp):
                rings_trust.grant(tmp / ".orchflows")
                yield tmp, pack

    def test_new_pins_the_stamped_packs_digest_at_issue_time(self):
        with self._pinned_world() as (tmp, pack):
            payload = run_cmd(
                tmp, "new", "testrun", "T1", "--executor", "orch-do",
                "--goal", "Deliver the widget.", "--context", "[]",
                "--pack", "widget-pack",
            )

            self.assertNotIn("error", payload)
            text = Path(payload["new"]["path"]).read_text(encoding="utf-8")
            expected = tickets_mod._tickets_adapters_module.pack_digest("widget-pack")
            self.assertIn(f"pack_digest: {expected}", text)

    def test_a_pack_edited_under_the_pin_refuses_at_admission(self):
        with self._pinned_world() as (tmp, pack):
            payload = run_cmd(
                tmp, "new", "testrun", "T1", "--executor", "orch-do",
                "--goal", "Deliver the widget.", "--context", "[]",
                "--pack", "widget-pack",
            )
            text = Path(payload["new"]["path"]).read_text(encoding="utf-8")
            craft = pack / "references" / "craft.md"
            craft.write_bytes(craft.read_bytes() + b"\nchanged under the seal\n")
            rings_trust.grant(tmp / ".orchflows")

            findings = tickets_mod.binding_findings(
                "T1", tickets_mod._parse_frontmatter(text)
            )

            codes = [item["code"] for item in findings]
            self.assertIn("pack-digest-mismatch", codes)
            detail = next(
                item["detail"] for item in findings
                if item["code"] == "pack-digest-mismatch"
            )
            self.assertIn("changed under the seal", detail)
            # The remedy names a living command: the generation stamp retired
            # into the callable fold, so a caller is sent to `do` or `judge`.
            self.assertIn("tickets.py do | judge", detail)
            self.assertNotIn("stamp-generation", detail)

    def test_an_unchanged_pack_grades_clean(self):
        with self._pinned_world() as (tmp, _pack):
            payload = run_cmd(
                tmp, "new", "testrun", "T1", "--executor", "orch-do",
                "--goal", "Deliver the widget.", "--context", "[]",
                "--pack", "widget-pack",
            )
            text = Path(payload["new"]["path"]).read_text(encoding="utf-8")

            findings = tickets_mod.binding_findings(
                "T1", tickets_mod._parse_frontmatter(text)
            )

            self.assertEqual([], findings)

    def test_a_pack_that_cannot_be_pinned_refuses_at_issue(self):
        with self._pinned_world() as (tmp, _pack):
            payload = run_cmd(
                tmp, "new", "testrun", "T2", "--executor", "orch-do",
                "--goal", "Deliver the widget.", "--context", "[]",
                "--pack", "no-such-pack",
            )

            self.assertIn("cannot be pinned", payload["error"])

    def test_the_pinned_digest_is_inside_the_sealed_assignment(self):
        """The trust grant and the seal cite one digest, so what was
        approved is what runs: re-pointing the pack changes the seal."""

        with self._pinned_world() as (tmp, _pack):
            payload = run_cmd(
                tmp, "new", "testrun", "T1", "--executor", "orch-do",
                "--goal", "Deliver the widget.", "--context", "[]",
                "--pack", "widget-pack",
            )
            text = Path(payload["new"]["path"]).read_text(encoding="utf-8")
            digest = tickets_mod._tickets_adapters_module.pack_digest("widget-pack")

            system = tickets_mod.assignment_payload("T1", text)["system"]
            self.assertEqual(digest, system["pack_digest"])
            repointed = text.replace(digest, "sha256:" + "0" * 64)
            self.assertNotEqual(
                tickets_mod.assignment_digest("T1", text),
                tickets_mod.assignment_digest("T1", repointed),
            )
