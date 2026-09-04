"""The `dispatch` command end to end, from a sealed item to one invocation.

The launch object's own resolution is checked in `test_dispatch_launch.py`
and any single prompt line group in `test_dispatch_launch_lines.py`. What
runs here is the command that puts them together: a sealed item is readied,
an attempt opened, a workspace established, and the launch comes back
carrying every fact the child cannot derive. Each case fires through the
`dispatch` command itself, so a refusal that stopped arriving before its
side effect fails here rather than in a run.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest import mock

from tests._candidate_checkout import (
    git_checkout, record_established_workspace,
)
from tests import _retired_commands as retired_commands
from scripts import state_root
from scripts import tickets
from scripts import tickets_dispatch_launch as launch
from scripts import workspace_git
from scripts.tickets_format import parse_canonical_json

from tests._repo_root import ROOT
HOSTS = ROOT / "hosts"


class DispatchLaunchTest(unittest.TestCase):
    """The facade emits the one invocation, prompt and all."""

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        # the host is pinned as well as the sink: the default this suite
        # asserts is the absent-environment default, not this machine's.
        # ORCHFLOWS_WORKTREES_HOME rides beside the sink for a third
        # reason: unset, a derived candidate would hang off the parent of
        # a bare tempdir -- the machine-shared system temp root -- instead
        # of staying inside this fixture's own tree.
        self.environment = mock.patch.dict(
            os.environ,
            {
                state_root.ENV_VAR: self.temporary.name,
                "ORCHFLOWS_WORKTREES_HOME": str(
                    Path(self.temporary.name) / "worktrees"
                ),
                launch.HOST_ENV_VAR: "",
            },
        )
        self.environment.start()
        self.candidate = git_checkout(Path(self.temporary.name) / "candidate")
        self.seal_ticket("run")
        self.lease = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat().replace("+00:00", "Z")

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def seal_ticket(self, run: str, *extra, admit: bool = True):
        """One sealed, admitted, workspace-stamped item, ready to dispatch.

        Each in its own run: a run has one root identity, and everything the
        launch turns on -- the sealed profile above all -- has to be inside
        the seal rather than edited past it.
        """

        self.run_command(
            "new", run, "T", "--executor", "orch-do",
            "--goal", "Deliver the behavior.",
            "--context", "The repository is authoritative.",
            "--pack", "orch-code-pack", "--isolation", "required", *extra,
        )
        self.run_command("stamp-generation", run, "T")
        validated = self.run_command("draft-validate", run, "T")
        self.run_command(
            "seal", run, "T", "--cut-generation",
            validated["draft_validation"]["cut_generation"],
        )
        if admit:
            self.run_command("ready", "--run", run)
        path = self.ticket_path(run)
        text = path.read_text(encoding="utf-8")
        for key, value in (
            ("workspace_branch", "candidate-branch"),
            ("workspace_baseline", "0123456789abcdef clean"),
        ):
            text = tickets._set_frontmatter_field(text, key, value)
        path.write_text(text, encoding="utf-8")

    def ticket_path(self, run: str = "run") -> Path:
        return Path(self.temporary.name) / "tickets" / run / "T.md"

    def run_command(self, *arguments):
        result = retired_commands.run(list(arguments))
        self.assertNotIn("error", result, result)
        return result

    def established(self):
        """Stand in for `workspace.py establish`: record the tree on the open
        attempt, which is where it lives, then answer as the real verb does."""

        def establish(run, ticket_id, _workspace):
            record_established_workspace(
                Path(self.temporary.name) / "tickets" / run / f"{ticket_id}.md",
                self.candidate, strict=False,
            )
            return {"establish": {"workspace_path": str(self.candidate)}}

        return mock.patch.object(
            tickets._tickets_dispatch_facade_module, "_workspace_establish",
            side_effect=establish,
        )

    def dispatch(self, *extra, dispatch_id="D1", run="run"):
        arguments = [
            "dispatch", run, "T", "--by", "worker",
            "--dispatch-id", dispatch_id, "--lease-expires-at", self.lease,
 "--workspace", str(self.candidate), *extra,
        ]
        with self.established():
            return retired_commands.run(arguments)

    def test_the_dispatch_carries_the_launch_its_host_record_declares(self):
        result = self.dispatch()

        self.assertNotIn("error", result, result)
        record = json.loads((HOSTS / "claude.json").read_text(encoding="utf-8"))
        binding = record["role_profiles"]["worker"]["binding"]
        self.assertEqual(record["launch"]["verb"], result["launch"]["verb"])
        self.assertEqual(binding["model"], result["launch"]["model"])
        self.assertEqual(binding["effort"], result["launch"]["effort"])
        self.assertEqual("orch-worker", result["launch"]["agent"])
        prompt = result["launch"]["prompt"]
        for retired in ("dispatch-receive", "dispatch-packet", "packs.py resolve"):
            self.assertNotIn(retired, prompt)

    def test_the_prompt_carries_every_fact_a_child_cannot_derive(self):
        """The eight orphans that made twelve of twelve launches hand-written.

        Each is asserted where it lives -- the established tree, this host's
        interpreter, the stamped pack's own craft file -- so a prompt that
        stopped resolving one of them fails here rather than in a run.
        """

        prompt = self.dispatch()["launch"]["prompt"]
        attempt = tickets._parse_frontmatter(
            self.ticket_path().read_text(encoding="utf-8")
        )
        state = parse_canonical_json(attempt["dispatch_v1"])["attempts"][0]
        craft = ROOT / "packs" / "orch-code-pack" / "references" / "craft.md"
        friction = ROOT / "scripts" / "friction.py"
        skill = ROOT / "skills" / "kernel" / "orch-do" / "SKILL.md"

        for fact in (
            str(self.ticket_path()), str(self.candidate), sys.executable,
            str(craft), state["assignment_seal"], "D1", "worker",
            state["lease_expires_at"], "outcome",
            "the gate's row", "to completion in the turn it starts",
            workspace_git.NOTES_DIR + "/",
            "Close only after everything you dispatched has returned.",
            # U13(c): a forked child does not receive the host block's
            # friction law (rules/token-economy.md's prompt-budget escape
            # hatch), so the prompt is its only carrier.
            "log friction, then continue", str(friction),
            # S7(a), 2026-09-01: the resolved skill file, so a forked child
            # never fires a filesystem search to find its own definition.
            str(skill),
            # S6, 2026-09-01: the check sentence names the mechanism the
            # host's own auto-backgrounding disagreed with the old
            # instruction over.
            "with an explicit timeout longer than the check",
            # S7(b), 2026-09-01: hygiene for a background command the child
            # itself supersedes, reusing this same command-running sentence
            # rather than opening a third surface.
            "kill anything you background once it is superseded",
        ):
            with self.subTest(fact=fact):
                self.assertIn(fact, prompt)
        self.assertNotIn("python ", prompt.replace(sys.executable, ""))
        # every fact once: the prompt states, never restates
        self.assertEqual(1, prompt.count(state["lease_expires_at"]))
        self.assertEqual(1, prompt.count(str(craft)))
        self.assertEqual(1, prompt.count(state["assignment_seal"]))
        self.assertEqual(1, prompt.count(str(friction)))
        self.assertEqual(1, prompt.count(str(skill)))
        # the standing gate line is the one scope statement, rendered once
        # for every dispatch: no craft carries a second wording of it
        self.assertEqual(
            1, prompt.count("run it here only if this ticket is the gate")
        )

    def test_no_lane_asks_a_child_for_a_verdict_token(self):
        """A command verdict is an exit code and a check's verdict is its
        findings, so no prompt teaches a prefix a join used to parse."""

        prompt = launch.launch_prompt(self.assignment_facts())
        for token in ("PASS:", "FAIL:", "UNVERIFIED:"):
            self.assertNotIn(token, prompt)

    @staticmethod
    def assignment_facts() -> dict:
        return {
            "assigned_name": "child-1", "assignment_seal": "sha256:seal",
            "craft": None, "dependencies": [],
            "dispatch_id": "D1", "executor": "orch-judge",
            "executor_script": None, "id": "R1.gate.critique.code",
            "lease_expires_at": "2099-01-01T00:00:00Z", "pack": "orch-code-pack",
            "role": "worker", "run": "run",
            "ticket_path": "/sink/run/R1.gate.critique.code.md", "workspace": "/tree",
        }

    def test_dispatching_a_sealed_pending_item_readies_it_without_hanging(self):
        """The command's own first step, on the state it exists for.

        `ready` promotes a sealed pending item by taking the run lock per
        admitted ticket, and `_run_lock` is not reentrant -- so while that
        promotion ran inside the facade's own lock, the ordinary first
        dispatch of a sealed root was a process waiting on itself. In a
        thread, so the regression is a failed join rather than a hung suite.
        """

        self.seal_ticket("fresh", admit=False)
        # deliberately no `ready` call: this is what `dispatch` advertises
        text = self.ticket_path("fresh").read_text(encoding="utf-8")
        self.assertIn("status: pending", text)

        outcome = {}

        def dispatch():
            outcome["result"] = self.dispatch(run="fresh")

        worker = threading.Thread(target=dispatch, daemon=True)
        worker.start()
        worker.join(timeout=60)

        self.assertFalse(worker.is_alive(), "dispatch waited for its own run lock")
        self.assertNotIn("error", outcome["result"], outcome["result"])
        self.assertIn("launch", outcome["result"])

    def test_the_host_flag_selects_another_hosts_binding(self):
        result = self.dispatch("--host", "codex")

        self.assertEqual("spawn_agent", result["launch"]["verb"])
        self.assertEqual("orch_worker", result["launch"]["agent"])
        self.assertEqual("gpt-5.6-luna", result["launch"]["model"])
        self.assertEqual("fast", result["launch"]["fields"]["service_tier"])

    def test_a_sealed_profile_override_resolves_the_planner_binding(self):
        """rules/roles.md clause 4 through the whole facade: the sealed
        profile decides the role, so the launch establishes the planner."""

        self.seal_ticket("planned", "--profile", "orch-planner")

        result = self.dispatch(run="planned")

        self.assertEqual("orch-planner", result["launch"]["agent"])
        self.assertEqual("claude-fable-5-1", result["launch"]["model"])

    def test_an_unknown_host_refuses_before_the_attempt_is_opened(self):
        before = self.ticket_path().read_text(encoding="utf-8")
        with mock.patch.object(
            tickets._tickets_dispatch_facade_module, "_cmd_dispatch_open",
        ) as opened:
            result = self.dispatch("--host", "nowhere")

        self.assertEqual("host-unresolved", result["code"])
        opened.assert_not_called()
        self.assertEqual(before, self.ticket_path().read_text(encoding="utf-8"))

    def test_an_unresolved_role_refuses_before_the_attempt_is_opened(self):
        # Every registered callable declares planner or worker now, so the
        # one executor form left that resolves to neither is the `script:`
        # escape hatch: it names no skill, so it declares no role.
        text = tickets._set_frontmatter_field(
            self.ticket_path().read_text(encoding="utf-8"),
            "executor", "script:scripts/harvest.py",
        )
        self.ticket_path().write_text(text, encoding="utf-8")
        before = self.ticket_path().read_text(encoding="utf-8")
        with mock.patch.object(
            tickets._tickets_dispatch_facade_module, "_cmd_ready",
            return_value={"ready": []},
        ), mock.patch.object(
            tickets._tickets_dispatch_facade_module, "_cmd_dispatch_open",
        ) as opened:
            result = self.dispatch()

        self.assertEqual("role-unresolved", result["code"])
        opened.assert_not_called()
        self.assertEqual(before, self.ticket_path().read_text(encoding="utf-8"))

    def test_the_prompt_names_the_identities_every_record_is_filed_under(self):
        """End to end on the hop this closes: the identities the prompt tells
        the child to use are exactly the ones the protocol accepts, so an
        orchestrator that passes the prompt through verbatim is correct."""

        result = self.dispatch()
        state = parse_canonical_json(tickets._parse_frontmatter(
            self.ticket_path().read_text(encoding="utf-8")
        )["dispatch_v1"])["attempts"][0]
        prompt = result["launch"]["prompt"]
        for token in (
            state["assignment_seal"], state["dispatch_id"], state["owner"],
            "outcome",
        ):
            self.assertIn(token, prompt)

        filed = retired_commands.run([
            "result", "run", "T", "--assignment-seal", state["assignment_seal"],
            "--dispatch-id", state["dispatch_id"], "--record-id", "R1",
            "--by", state["owner"],
            "--text", "the first filed record is the acceptance",
        ])

        self.assertNotIn("error", filed, filed)

    def test_the_removed_carriage_selectors_are_ordinary_unknown_arguments(self):
        """The inline form went out with the handshake that policed it, the
        ceiling that bounded its snapshot went with it, and the packet file
        went with the wire it carried: none may be silently tolerated."""

        for flag, value in (("--form", "inline"), ("--inline-limit", "64"),
                            ("--packet-file", "anywhere.json")):
            with self.subTest(flag=flag):
                result = self.dispatch(flag, value)
                self.assertIn("usage: dispatch", result["error"])
                self.assertNotIn(flag, result["error"])


if __name__ == "__main__":
    unittest.main()
