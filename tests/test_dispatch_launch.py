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

from tests._repo_root import ROOT
HOSTS = ROOT / "hosts"


class LaunchResolutionTest(unittest.TestCase):
    """The launch object is the host record, read rather than remembered."""

    def record(self, host: str) -> dict:
        return json.loads((HOSTS / f"{host}.json").read_text(encoding="utf-8"))

    def assignment(self, role: str) -> dict:
        """The graded facts a launch is resolved from, minimally filled."""

        return {
            "assigned_name": "child-1", "assignment_seal": "sha256:seal",
            "standard": None, "dependencies": [],
            "dispatch_id": "D1", "executor": "orch-do",
            "executor_script": None, "id": "T", "lease_expires_at": "2099-01-01T00:00:00Z",
            "standard": None, "role": role,
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
            ("claude", "worker", "high"), ("codex", "planner", "ultra"),
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
            "--standard", "orch-code", "--isolation", "required",
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

    def test_a_land_with_no_predicate_and_no_status_refuses_before_integrating(self):
        """The grade question reads the ticket's own frontmatter, never the
        merged tree, so it is asked first: this call once merged the
        candidate into the run's checkout and then refused itself."""

        self.commit_outcome()
        entered = []

        def integrate(*arguments):
            entered.append(arguments)
            return {"step": "workspace-integrate", "outcome": "absent"}

        with mock.patch.object(
            tickets._tickets_land_module, "_integrate_workspace",
            side_effect=integrate,
        ):
            refusal = self.land(status=None)

        self.assertIn("carries no done predicate", refusal["error"])
        self.assertIn("--status", refusal["error"])
        self.assertFalse(entered, "the candidate was integrated before the refusal")

    def test_land_relays_a_join_refusal_unchanged(self):
        refusal = self.land()

        self.assertEqual("outcome-record-mismatch", refusal["code"])


if __name__ == "__main__":
    unittest.main()
