"""Committed dispatch-v1 launch regressions.

The launch is what a dispatch commits and what the orchestrator invokes. It
replaced a twenty-one-field wire object nothing on the child's side could
read, so these cases hold the record's identity, its replay, and the ordering
that makes a filed record proof of a launch -- never the wire's field list.
"""

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

from tests._candidate_checkout import git_checkout, record_established_workspace
from tests import _retired_commands as retired_commands
from scripts import state_root
from scripts import tickets
from scripts.tickets_assignment import workspace_establishment_finding
from scripts.tickets_format import canonical_json, parse_canonical_json
from scripts.tickets_outcome import DISPATCH_OUTCOME_USAGE


class DispatchLaunchRecordTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        # ORCHFLOWS_WORKTREES_HOME rides beside the sink: unset, a derived
        # candidate would hang off the parent of a bare tempdir -- the
        # machine-shared system temp root -- instead of staying inside
        # this fixture's own tree.
        self.environment = mock.patch.dict(
            os.environ,
            {
                state_root.ENV_VAR: self.temporary.name,
                "ORCHFLOWS_WORKTREES_HOME": str(
                    Path(self.temporary.name) / "worktrees"
                ),
                "ORCHFLOWS_HOST": "",
            },
        )
        self.environment.start()
        self.run_command(
            "new", "run", "T", "--executor", "orch-do",
            "--goal", "Deliver the behavior.",
            "--context", "The repository is authoritative.",
            "--pack", "orch-code-pack", "--profile", "orch-worker",
            "--isolation", "required",
        )
        self.run_command("stamp-generation", "run", "T")
        validated = self.run_command("draft-validate", "run", "T")
        self.run_command(
            "seal", "run", "T", "--cut-generation",
            validated["draft_validation"]["cut_generation"],
        )
        self.run_command("ready", "--run", "run")
        # non-ASCII on purpose: the command must emit ASCII-escaped canonical
        # JSON whatever the subprocess code page is, and the workspace path is
        # the prompt value this fixture owns.
        self.candidate = git_checkout(Path(self.temporary.name) / "candidate-—")
        self.ticket_path = Path(self.temporary.name) / "tickets" / "run" / "T.md"
        established = self.ticket_path.read_text(encoding="utf-8")
        for key, value in (
            ("workspace_branch", "candidate-branch"),
            ("workspace_baseline", "0123456789abcdef clean"),
        ):
            established = tickets._set_frontmatter_field(established, key, value)
        self.ticket_path.write_text(established, encoding="utf-8")
        self.lease = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat().replace("+00:00", "Z")

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def run_command(self, *arguments):
        result = retired_commands.run(list(arguments))
        self.assertNotIn("error", result, result)
        return result

    def established(self, workspace=None):
        """Stand in for `workspace.py establish`: record the tree on the open
        attempt, which is where it lives, then answer as the real verb does."""

        tree = str(self.candidate if workspace is None else workspace)

        def establish(run, ticket_id, _source):
            record_established_workspace(
                Path(self.temporary.name) / "tickets" / run / f"{ticket_id}.md",
                tree, strict=False,
            )
            return {"establish": {"workspace_path": tree}}

        return mock.patch.object(
            tickets._tickets_dispatch_facade_module, "_workspace_establish",
            side_effect=establish,
        )

    def dispatch(self, *extra, workspace=None, ticket_id="T", dispatch_id="D1"):
        with self.established(workspace):
            return retired_commands.run([
                "dispatch", "run", ticket_id, "--by", "worker",
                "--dispatch-id", dispatch_id,
                "--lease-expires-at", self.lease, *extra,
            ])

    def seal(self) -> str:
        return self.ticket_state()["attempts"][0]["assignment_seal"]

    def ticket_state(self, ticket_id="T"):
        path = Path(self.temporary.name) / "tickets" / "run" / f"{ticket_id}.md"
        return parse_canonical_json(
            tickets._parse_frontmatter(path.read_text(encoding="utf-8"))["dispatch_v1"]
        )

    def records(self, ticket_id="T"):
        return self.ticket_state(ticket_id)["attempts"][0]["records"]

    def ticket_bytes(self):
        return self.ticket_path.read_bytes()

    def test_the_launch_is_committed_once_and_an_exact_retry_replays(self):
        first = self.dispatch()
        self.assertNotIn("error", first, first)
        launch = first["launch"]
        self.assertEqual({
            "host", "verb", "agent", "model", "effort", "fields", "prompt",
        }, set(launch))
        self.assertNotIn("packet", first)

        self.assertEqual(["launch"], [item["record_id"] for item in self.records()])
        stored = parse_canonical_json(self.records()[0]["content"])
        self.assertEqual({"launch": launch}, stored)
        self.assertEqual("launch", self.records()[0]["kind"])
        self.assertEqual(launch, self.dispatch()["launch"])
        self.assertEqual(1, len(self.records()))

    def test_the_prompt_fills_the_filing_commands_the_protocol_accepts(self):
        """End to end on the hop this closes: the commands the prompt hands
        the child are the ones `result` admits, so an orchestrator that passes
        the prompt through verbatim is correct without editing a token."""

        prompt = self.dispatch()["launch"]["prompt"]
        filing = [
            line.split()[2:]
            for line in prompt.splitlines()
            if len(line.split()) > 2
            and Path(line.split()[1]).name == "tickets.py"
            and line.split()[2] == "result"
        ]
        self.assertEqual(1, len(filing), prompt)
        for command in filing:
            self.assertNotIn("--section", command)
            self.assertNotIn("--append", command)

        text_command = next(command for command in filing if "--text" in command)
        text_command[text_command.index("TEXT")] = "first emitted text record"
        text_command[text_command.index("RECORD_ID")] = "R1"
        self.run_command(*text_command)
        text_command[text_command.index("first emitted text record")] = "second one"
        text_command[text_command.index("R1")] = "R2"
        self.run_command(*text_command)
        body = self.ticket_path.read_text(encoding="utf-8")
        self.assertIn("first emitted text record", body)
        self.assertIn("second one", body)

    def test_the_first_filed_record_is_the_acceptance(self):
        """No accept step stands between the committed launch and the child.

        The whole return runs off the launch alone: the identities `result`
        already validates on every write are the child's authority, and there
        is no receipt for any of the three to wait on.
        """

        self.dispatch()
        seal = self.seal()

        filed = self.run_command(
            "result", "run", "T", "--assignment-seal", seal,
            "--dispatch-id", "D1", "--record-id", "result-1",
            "--by", "worker", "--text", "delivered",
        )
        self.assertEqual("worker", filed["result"]["by"])
        self.run_command(
            "result", "run", "T", "--assignment-seal", seal,
            "--dispatch-id", "D1", "--record-id", "result-2",
            "--by", "worker", "--text", "checked",
        )
        note = Path(self.temporary.name) / "closing-note.txt"
        note.write_text("the closing note", encoding="utf-8")
        self.run_command(
            "dispatch-outcome", "run", "T", "--note-file", str(note),
        )
        joined = self.run_command(
            "dispatch-join", "run", "T", "--assignment-seal", seal,
            "--dispatch-id", "D1", "--outcome-record-id", "outcome", "--by", "root",
            "--status", "complete",
        )
        self.assertEqual("complete", joined["join"]["status"])
        self.assertEqual(
            ["launch", "result-1", "result-2", "outcome", "join:outcome"],
            [item["record_id"] for item in self.records()],
        )

    def test_an_execution_record_without_a_committed_launch_refuses(self):
        """The one ordering the grammar still keeps: a child that filed
        anything was launched, and the committed launch is that launch."""

        opened = self.run_command(
            "dispatch-open", "run", "T", "--by", "worker",
            "--dispatch-id", "D1", "--lease-expires-at", self.lease,
        )
        before = self.ticket_bytes()
        refusal = retired_commands.run([
            "result", "run", "T",
            "--assignment-seal", opened["dispatch"]["assignment_seal"],
            "--dispatch-id", "D1", "--record-id", "result-1",
            "--by", "worker", "--text", "delivered",
        ])
        self.assertEqual("dispatch-record-invalid", refusal["code"], refusal)
        self.assertIn("committed launch", refusal["error"])
        self.assertEqual(before, self.ticket_bytes())

    def test_the_retired_delivery_verbs_are_gone_from_the_public_surface(self):
        for verb in ("dispatch-receive", "dispatch-receipt", "dispatch-packet"):
            with self.subTest(verb=verb):
                refusal = retired_commands.run([verb, "run", "T"])
                self.assertEqual(f"unknown subcommand: {verb}", refusal["error"])
        subcommands = tickets._cmd_help()["help"]["subcommands"]
        self.assertNotIn("dispatch-receive", subcommands)
        self.assertNotIn("dispatch-packet", subcommands)

    def test_the_packet_file_flag_is_an_ordinary_unknown_argument(self):
        """There is no packet file: the ticket path is the pointer, and the
        flag that carried the wire may not be silently tolerated."""

        before = self.ticket_bytes()

        refused = self.dispatch("--packet-file", "anywhere.json")

        self.assertIn("usage: dispatch", refused["error"])
        self.assertNotIn("--packet-file", refused["error"])
        self.assertEqual(before, self.ticket_bytes())

    def test_a_committed_launch_replays_before_current_resolution(self):
        """A durable record is never re-resolved: the child was started with
        those exact bytes, so a second dispatch reports what happened rather
        than what would happen now."""

        self.dispatch()
        text = self.ticket_path.read_text(encoding="utf-8")
        state = parse_canonical_json(tickets._parse_frontmatter(text)["dispatch_v1"])
        record = state["attempts"][0]["records"][0]
        stored = parse_canonical_json(record["content"])
        stored["launch"]["model"] = "model-that-started-this-child"
        record["content"] = canonical_json(stored)
        self.ticket_path.write_text(
            tickets._set_frontmatter_field(text, "dispatch_v1", canonical_json(state)),
            encoding="utf-8",
        )

        replayed = self.dispatch("--host", "codex")

        self.assertEqual(stored, {"launch": replayed["launch"]})
        self.assertEqual(
            "model-that-started-this-child", replayed["launch"]["model"],
        )

    def test_a_committed_launch_replays_after_retirement(self):
        launched = self.dispatch()["launch"]
        self.run_command(
            "dispatch-retire", "run", "T", "--assignment-seal", self.seal(),
            "--dispatch-id", "D1", "--record-id", "lifecycle:retire-1",
        )

        self.assertEqual(launched, self.dispatch()["launch"])

    def test_dispatch_refuses_an_unrecorded_candidate_workspace(self):
        def establish(_run, _ticket_id, _source):
            return {"establish": {"workspace_path": str(self.candidate)}}

        with mock.patch.object(
            tickets._tickets_dispatch_facade_module, "_workspace_establish",
            side_effect=establish,
        ):
            refusal = retired_commands.run([
                "dispatch", "run", "T", "--by", "worker", "--dispatch-id", "D1",
                "--lease-expires-at", self.lease,
            ])

        self.assertEqual("workspace-unestablished", refusal["code"])
        self.assertNotIn("launch", refusal)

    def test_dispatch_refuses_a_workspace_other_than_the_recorded_candidate(self):
        other = git_checkout(Path(self.temporary.name) / "other")

        def establish(run, ticket_id, _source):
            record_established_workspace(
                Path(self.temporary.name) / "tickets" / run / f"{ticket_id}.md",
                self.candidate, strict=False,
            )
            return {"establish": {"workspace_path": str(other)}}

        with mock.patch.object(
            tickets._tickets_dispatch_facade_module, "_workspace_establish",
            side_effect=establish,
        ):
            refusal = retired_commands.run([
                "dispatch", "run", "T", "--by", "worker", "--dispatch-id", "D1",
                "--lease-expires-at", self.lease,
            ])

        self.assertEqual("workspace-mismatch", refusal["code"])
        self.assertNotIn("launch", refusal)

    @staticmethod
    def _recorded(workspace: str) -> dict:
        """Frontmatter whose live attempt records `workspace` and nothing else."""

        return {
            "pack": "orch-research-pack",
            "isolation": "required",
            "dispatch_v1": canonical_json({
                "protocol": "orchflows.dispatch.v1",
                "attempts": [{
                    "assignment_seal": "sha256:" + "0" * 64,
                    "dispatch_id": "D1",
                    "lease_expires_at": "2099-01-01T00:00:00Z",
                    "opened_at": "2026-01-01T00:00:00Z",
                    "outcome_record_id": "outcome",
                    "owner": "worker",
                    "records": [],
                    "state": "live",
                    "workspace_path": workspace,
                }],
            }),
        }

    def test_a_research_dispatch_requires_the_recorded_store_to_exist(self):
        with tempfile.TemporaryDirectory() as store:
            data = self._recorded(store)
            self.assertIsNone(workspace_establishment_finding(data, store))
        finding = workspace_establishment_finding(data, store)
        self.assertEqual("workspace-unestablished", finding[0])

    def test_the_removed_outcome_content_form_still_refuses(self):
        """The cutover removed the flag; it may not be silently tolerated."""

        self.dispatch()
        before = self.ticket_bytes()

        relayed_content = retired_commands.run([
            "dispatch-outcome", "run", "T", "--content",
            canonical_json({"status": "complete"}),
        ])
        self.assertEqual("outcome-invalid", relayed_content["code"])
        self.assertNotIn("--content", DISPATCH_OUTCOME_USAGE)
        self.assertEqual(before, self.ticket_bytes())


class DispatchCarriageTest(unittest.TestCase):
    """The whole command, in its own process, over a non-ASCII workspace.

    The prompt is the delivery now, and it names absolute paths a console code
    page can mangle. Nothing here is stubbed: the real workspace verb runs, the
    real launch is composed, and the bytes that reach standard output are the
    ones an orchestrator reads.
    """

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        # ORCHFLOWS_WORKTREES_HOME rides beside the sink: unset, the real
        # workspace verb this fixture runs would derive a candidate off
        # the parent of a bare tempdir -- the machine-shared system temp
        # root -- instead of staying inside this fixture's own tree.
        self.environment = mock.patch.dict(
            os.environ,
            {
                state_root.ENV_VAR: self.temporary.name,
                "ORCHFLOWS_WORKTREES_HOME": str(
                    Path(self.temporary.name) / "worktrees"
                ),
                "ORCHFLOWS_HOST": "",
            },
        )
        self.environment.start()
        for arguments in (
            ("new", "run", "T", "--executor", "orch-do",
             "--goal", "Deliver the behavior.",
             "--context", "The repository is authoritative.",
             "--pack", "orch-code-pack", "--isolation", "none"),
            ("stamp-generation", "run", "T"),
        ):
            self.run_command(*arguments)
        validated = self.run_command("draft-validate", "run", "T")
        self.run_command(
            "seal", "run", "T", "--cut-generation",
            validated["draft_validation"]["cut_generation"],
        )
        self.run_command("ready", "--run", "run")
        self.candidate = git_checkout(Path(self.temporary.name) / "candidate-—")
        self.commit(self.candidate)
        self.lease = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat().replace("+00:00", "Z")

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def run_command(self, *arguments):
        result = retired_commands.run(list(arguments))
        self.assertNotIn("error", result, result)
        return result

    @staticmethod
    def commit(tree: Path) -> None:
        identity = dict(
            os.environ,
            GIT_AUTHOR_NAME="orchflows", GIT_AUTHOR_EMAIL="orchflows@example",
            GIT_COMMITTER_NAME="orchflows",
            GIT_COMMITTER_EMAIL="orchflows@example",
        )
        (tree / "seed.txt").write_text("seed\n", encoding="utf-8")
        for arguments in (["add", "-A"], ["commit", "-qm", "seed"]):
            subprocess.run(
                ["git", *arguments], cwd=str(tree), env=identity,
                capture_output=True, check=True,
            )

    def test_dispatch_emits_codepage_independent_canonical_ascii(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "tickets.py"
        completed = subprocess.run(
            [
                sys.executable, str(script), "dispatch", "run", "T",
                "--by", "worker", "--dispatch-id", "D1",
                "--lease-expires-at", self.lease,
                "--workspace", str(self.candidate),
            ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        decoded = completed.stdout.decode("ascii")
        response = json.loads(decoded)
        self.assertIn("—", response["launch"]["prompt"])
        expected = json.dumps(
            response, ensure_ascii=True, separators=(",", ":"), sort_keys=True,
        ) + "\n"
        self.assertEqual(expected, decoded)


if __name__ == "__main__":
    unittest.main()
