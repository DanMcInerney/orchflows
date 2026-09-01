"""`dispatch` completes the launch and `land` completes the return.

The two hops a caller used to make by hand. Launch: read `hosts/<host>.json`,
find the profile row for the child's role, and type the model into the launch
verb -- a transcription that has killed a dispatch by naming the wrong model.
Return: import the outcome, join it, remove the derived worktree, then ask
what became ready -- four commands whose order was the caller's to remember.

Each case fires on the mechanism. The host cases hold the resolved launch
against the host record's own bytes in both directions, so a launch that
stops reading the record fails even if it keeps returning today's values.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import io
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
from scripts.tickets_format import canonical_json, parse_canonical_json

ROOT = Path(__file__).resolve().parents[1]
HOSTS = ROOT / "hosts"


class LaunchResolutionTest(unittest.TestCase):
    """The launch object is the host record, read rather than remembered."""

    def record(self, host: str) -> dict:
        return json.loads((HOSTS / f"{host}.json").read_text(encoding="utf-8"))

    def assignment(self, role: str) -> dict:
        """The graded facts a launch is resolved from, minimally filled."""

        return {
            "assigned_name": "child-1", "assignment_seal": "sha256:seal",
            "craft": None, "craft_scope": None, "dependencies": [],
            "dispatch_id": "D1", "executor": "orch-do",
            "executor_script": None, "id": "T", "lease_expires_at": "2099-01-01T00:00:00Z",
            "pack": None, "role": role,
            "run": "run", "ticket_path": "/sink/run/T.md",
            "workspace": "/tree",
        }

    def test_every_host_and_role_resolves_from_that_hosts_own_record(self):
        for host in ("claude", "codex", "grok"):
            declared = self.record(host)
            resolved, failure = launch.resolve_host(host)
            self.assertIsNone(failure, host)
            self.assertEqual(declared, resolved)
            for role in ("planner", "worker"):
                with self.subTest(host=host, role=role):
                    spec, failure = launch.launch_spec(resolved, self.assignment(role))
                    self.assertIsNone(failure)
                    binding = declared["role_profiles"][role]["binding"]
                    self.assertEqual(declared["launch"]["verb"], spec["verb"])
                    self.assertEqual(binding["model"], spec["model"])
                    self.assertEqual(host, spec["host"])
                    # every native field the host declares that it also binds
                    for key, value in binding.items():
                        if key in declared["launch"]["native_fields"]:
                            self.assertEqual(value, spec["fields"][key])

    def test_the_effort_is_the_one_this_host_spells_however_it_spells_it(self):
        for host, role, expected in (
            ("claude", "worker", "xhigh"), ("codex", "planner", "ultra"),
            ("grok", "worker", "high"),
        ):
            with self.subTest(host=host, role=role):
                resolved, _ = launch.resolve_host(host)
                spec, _ = launch.launch_spec(resolved, self.assignment(role))
                self.assertEqual(expected, spec["effort"])

    def test_a_changed_model_in_the_record_changes_the_launch(self):
        """The can-fail direction, on a copy in memory: a resolver that had
        stopped reading the record would still return today's model."""

        record, _ = launch.resolve_host("claude")
        moved = json.loads(json.dumps(record))
        moved["role_profiles"]["worker"]["binding"]["model"] = "claude-elsewhere"
        spec, _ = launch.launch_spec(moved, self.assignment("worker"))
        self.assertEqual("claude-elsewhere", spec["model"])

    def test_the_agent_identity_comes_from_the_hosts_own_role_agent_path(self):
        """Derived, never mapped: Codex identifies an agent by `agent_type`
        and Claude by the profile name, and each host's `role_agent` path
        says which."""

        for host, role, expected in (
            ("claude", "planner", "orch-planner"),
            ("codex", "planner", "orch_planner"),
            ("grok", "worker", "orch-worker"),
        ):
            with self.subTest(host=host):
                record, _ = launch.resolve_host(host)
                spec, _ = launch.launch_spec(record, self.assignment(role))
                self.assertEqual(expected, spec["agent"])

    def test_an_unknown_host_refuses_and_names_the_ones_that_resolve(self):
        record, failure = launch.resolve_host("nowhere")
        self.assertIsNone(record)
        self.assertEqual("host-unresolved", failure["code"])
        for name in launch.host_names():
            self.assertIn(name, failure["error"])

    def test_a_host_missing_the_role_profile_refuses(self):
        record, _ = launch.resolve_host("claude")
        stripped = json.loads(json.dumps(record))
        del stripped["role_profiles"]["worker"]
        spec, failure = launch.launch_spec(stripped, self.assignment("worker"))
        self.assertIsNone(spec)
        self.assertEqual("profile-unresolved", failure["code"])

    def test_an_unresolved_role_refuses_and_names_the_two_profiles(self):
        record, _ = launch.resolve_host("claude")
        spec, failure = launch.launch_spec(record, dict(self.assignment("worker"), role=None))
        self.assertIsNone(spec)
        self.assertEqual("role-unresolved", failure["code"])
        self.assertIn("orch-planner", failure["error"])
        self.assertIn("orch-worker", failure["error"])

    def test_the_selected_host_is_the_flag_then_the_environment_then_claude(self):
        with mock.patch.dict(os.environ, {launch.HOST_ENV_VAR: "grok"}):
            self.assertEqual("codex", launch.selected_host("codex"))
            self.assertEqual("grok", launch.selected_host(None))
        with mock.patch.dict(os.environ, {launch.HOST_ENV_VAR: ""}):
            self.assertEqual(launch.DEFAULT_HOST, launch.selected_host(None))

    def test_the_profile_override_decides_the_role_the_skill_declared(self):
        """rules/roles.md clause 4, through the one resolver both sides use:
        an explicit profile wins over the applied skill's own declaration."""

        self.assertEqual(
            ("worker", "orch-worker"),
            launch.resolved_role_profile("orch-do", None),
        )
        self.assertEqual(
            ("planner", "orch-planner"),
            launch.resolved_role_profile("orch-do", "orch-planner"),
        )
        self.assertEqual(
            ("worker", "house-profile"),
            launch.resolved_role_profile("orch-do", "house-profile"),
        )


class ReturnLineConditionalTest(unittest.TestCase):
    """U2a: the commit clause is conditional on the adapter's git candidate.

    An adapter that establishes one (git, git-plus-render) still gets told
    to commit; one that establishes none (evidence-store, document-tree)
    gets its own craft's `## Workspace` sentence instead -- never both, never
    neither.
    """

    def assignment(self, *, pack: str, artifact_kind, git_candidate: bool, workspace_line):
        return {
            "assigned_name": "child-1", "assignment_seal": "sha256:seal",
            "artifact_kind": artifact_kind, "craft": None, "craft_scope": None,
            "dependencies": [], "dispatch_id": "D1", "executor": "orch-do",
            "executor_script": None, "git_candidate": git_candidate, "id": "T",
            "lease_expires_at": "2099-01-01T00:00:00Z", "pack": pack,
            "role": "worker", "run": "run", "ticket_path": "/sink/run/T.md",
            "workspace": "/tree", "workspace_line": workspace_line,
        }

    def test_a_research_pack_do_launch_carries_no_commit_clause(self):
        from scripts.tickets_assignment import _workspace_line, git_candidate

        craft = ROOT / "packs" / "orch-research-pack" / "references" / "craft.md"
        research_line = _workspace_line(craft)
        self.assertIsNotNone(research_line)
        self.assertFalse(git_candidate("orch-research-pack"))

        prompt = launch.launch_prompt(self.assignment(
            pack="orch-research-pack", artifact_kind="evidence",
            git_candidate=False, workspace_line=research_line,
        ))

        self.assertNotIn("Commit your work inside this candidate", prompt)
        self.assertIn(research_line, prompt)

    def test_a_code_pack_do_launch_still_commits(self):
        from scripts.tickets_assignment import git_candidate

        self.assertTrue(git_candidate("orch-code-pack"))

        prompt = launch.launch_prompt(self.assignment(
            pack="orch-code-pack", artifact_kind="git",
            git_candidate=True, workspace_line=None,
        ))

        self.assertIn(
            "Commit your work inside this candidate before you close", prompt,
        )
        self.assertIn("artifact: git:<full-commit-id>", prompt)


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
        ):
            with self.subTest(fact=fact):
                self.assertIn(fact, prompt)
        self.assertNotIn("python ", prompt.replace(sys.executable, ""))
        # every fact once: the prompt states, never restates
        self.assertEqual(1, prompt.count(state["lease_expires_at"]))
        self.assertEqual(1, prompt.count(str(craft)))
        self.assertEqual(1, prompt.count(state["assignment_seal"]))
        self.assertEqual(1, prompt.count(str(friction)))
        # the craft's quoted scope is the one scope statement: the standing
        # gate line yields to it rather than restating the same law
        self.assertNotIn("run it here only if this ticket is the gate", prompt)

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
            "craft": None, "craft_scope": None, "dependencies": [],
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
        self.assertEqual("claude-opus-5", result["launch"]["model"])

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
            "executor", "script:scripts/cutcheck.py",
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


class LandTest(unittest.TestCase):
    """One command closes the return, and closes it the same way twice."""

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
            },
        )
        self.environment.start()
        self.run_command(
            "new", "run", "T", "--executor", "orch-do",
            "--goal", "Deliver the behavior.",
            "--context", "The repository is authoritative.",
            "--pack", "orch-code-pack", "--isolation", "required",
        )
        self.run_command("stamp-generation", "run", "T")
        validated = self.run_command("draft-validate", "run", "T")
        self.run_command(
            "seal", "run", "T", "--cut-generation",
            validated["draft_validation"]["cut_generation"],
        )
        self.run_command("ready", "--run", "run")
        self.candidate = git_checkout(Path(self.temporary.name) / "candidate")
        text = self.ticket_path().read_text(encoding="utf-8")
        for key, value in (
            ("workspace_branch", "candidate-branch"),
            ("workspace_baseline", "0123456789abcdef clean"),
        ):
            text = tickets._set_frontmatter_field(text, key, value)
        self.ticket_path().write_text(text, encoding="utf-8")
        lease = (
            datetime.now(timezone.utc) + timedelta(hours=1)
        ).isoformat().replace("+00:00", "Z")

        def establish(run, ticket_id, _workspace):
            record_established_workspace(
                Path(self.temporary.name) / "tickets" / run / f"{ticket_id}.md",
                self.candidate, strict=False,
            )
            return {"establish": {"workspace_path": str(self.candidate)}}

        # through the facade, because the committed launch this return runs
        # behind is the facade's own step
        with mock.patch.object(
            tickets._tickets_dispatch_facade_module, "_workspace_establish",
            side_effect=establish,
        ):
            self.run_command(
                "dispatch", "run", "T", "--by", "worker", "--dispatch-id", "D1",
                "--lease-expires-at", lease, "--workspace", str(self.candidate),
            )
        self.seal = parse_canonical_json(tickets._parse_frontmatter(
            self.ticket_path().read_text(encoding="utf-8")
        )["dispatch_v1"])["attempts"][0]["assignment_seal"]

    def tearDown(self):
        self.environment.stop()
        self.temporary.cleanup()

    def ticket_path(self) -> Path:
        return Path(self.temporary.name) / "tickets" / "run" / "T.md"

    def run_command(self, *arguments):
        result = retired_commands.run(list(arguments))
        self.assertNotIn("error", result, result)
        return result

    def evidence(self, name: str, body: str) -> str:
        path = Path(self.temporary.name) / f"outcome-{name}.txt"
        path.write_text(body, encoding="utf-8")
        return str(path)

    def commit_outcome(self, note="delivered and verified"):
        return self.run_command(
            "dispatch-outcome", "run", "T", "--note", note,
        )

    def land(self, *extra, status="complete"):
        graded = ["--status", status] if status is not None else []
        return retired_commands.run([
            "land", "run", "T", "--assignment-seal", self.seal,
            "--dispatch-id", "D1", "--outcome-record-id", "outcome",
            "--by", "root-join", *graded, *extra,
        ])

    def steps(self, landed) -> dict:
        return {step["step"]: step["outcome"] for step in landed["land"]["steps"]}

    def test_land_joins_a_committed_outcome_and_reports_the_frontier(self):
        self.commit_outcome()

        landed = self.land()

        self.assertNotIn("error", landed, landed)
        self.assertEqual("complete", landed["land"]["status"])
        self.assertEqual(
            {"dispatch-outcome": "skipped", "workspace-integrate": "absent",
             "done": "graded", "dispatch-join": "committed",
             "workspace-retire": "removed"},
            self.steps(landed),
        )
        self.assertIn("ready", landed["land"]["frontier"])
        self.assertEqual(
            "complete", tickets._parse_frontmatter(
                self.ticket_path().read_text(encoding="utf-8")
            )["status"],
        )

    def test_land_replays_end_to_end_and_says_which_steps_it_found_done(self):
        self.commit_outcome()
        first = self.land()
        self.assertNotIn("error", first, first)

        second = self.land()

        self.assertNotIn("error", second, second)
        self.assertEqual("replayed", self.steps(second)["dispatch-join"])
        self.assertEqual(first["land"]["join"], second["land"]["join"])

    def test_land_imports_the_outcome_it_is_handed(self):
        envelope = {
            "assignment_seal": self.seal,
            "by": "worker",
            "dispatch_id": "D1",
            "evidence": "delivered and verified",
            "id": "T",
            "outcome_record_id": "outcome",
            "protocol": "orchflows.dispatch.v1",
            "run": "run",
        }
        path = Path(self.temporary.name) / "outcome.json"
        path.write_text(canonical_json(envelope), encoding="utf-8")

        landed = self.land("--outcome-file", str(path))

        self.assertNotIn("error", landed, landed)
        self.assertEqual(
            {"dispatch-outcome": "committed", "workspace-integrate": "absent",
             "done": "graded", "dispatch-join": "committed",
             "workspace-retire": "removed"},
            self.steps(landed),
        )
        self.assertIn("delivered", self.ticket_path().read_text(encoding="utf-8"))

    def test_land_imports_an_outcome_handed_to_it_on_standard_input(self):
        """`-` so a relaying coordinator holding the envelope in memory does
        not have to land it in a file first."""

        envelope = {
            "assignment_seal": self.seal, "by": "worker", "dispatch_id": "D1",
            "evidence": "delivered and verified",
            "id": "T", "outcome_record_id": "outcome",
            "protocol": "orchflows.dispatch.v1", "run": "run",
        }
        carried = io.TextIOWrapper(
            io.BytesIO(canonical_json(envelope).encode("utf-8")), encoding="utf-8"
        )
        with mock.patch.object(sys, "stdin", carried):
            landed = self.land("--outcome-file", "-")

        self.assertNotIn("error", landed, landed)
        self.assertEqual("committed", self.steps(landed)["dispatch-outcome"])

    def test_a_suspended_join_keeps_the_tree_its_handoff_resumes_in(self):
        self.commit_outcome(note="parked; resume here")

        landed = self.land(status="suspended")

        self.assertNotIn("error", landed, landed)
        self.assertEqual("suspended", landed["land"]["status"])
        self.assertEqual("skipped", self.steps(landed)["workspace-retire"])

    def test_land_refuses_a_malformed_identity_without_writing(self):
        before = self.ticket_path().read_text(encoding="utf-8")

        refusal = retired_commands.run([
            "land", "..", "T", "--assignment-seal", self.seal,
            "--dispatch-id", "D1", "--outcome-record-id", "outcome",
            "--by", "root-join", "--status", "complete",
        ])

        self.assertIn("unsafe run id", refusal["error"])
        self.assertEqual(before, self.ticket_path().read_text(encoding="utf-8"))

    def test_land_relays_a_join_refusal_unchanged(self):
        refusal = self.land()

        self.assertEqual("outcome-record-mismatch", refusal["code"])


if __name__ == "__main__":
    unittest.main()
