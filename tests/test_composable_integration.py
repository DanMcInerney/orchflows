"""One outside-project proof of a composed workflow's complete ticket path.

The fixture is an ordinary Git project with a project-ring workflow package.
It checks the package, runs its private helper through real ticket worktrees,
lands deterministic output, and judges the landed tip.  Launches are records
only: local fixture commands make the artifacts, so this test makes no claim
that a model ran.
"""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import (
    orchflows,
    orchflows_scaffold,
    rings,
    rings_trust,
    state_root,
    tickets,
    tickets_assignment,
    tickets_dispatch_launch,
    tickets_pins,
    workspace_record,
)
from scripts.tickets_format import _parse_frontmatter, parse_canonical_json
from tests._candidate_checkout import git_checkout
from tests._repo_root import ROOT


RUN = "composableproof"
PUBLIC = "composed-proof"
HELPER = "helper"
LOCAL_STANDARD = "local-proof"
LIB_STANDARD = "orch-code"


PROBE = r'''#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1]
PROJECT = Path(__file__).resolve().parents[4]
RESULT = PROJECT / "proof" / "result.txt"
FINDINGS = PROJECT / "review" / "findings.json"
MARKER = PROJECT / ".orch-notes" / "outside-probe-ran"


def expected():
    source = (PACKAGE / "references" / "brief.txt").read_bytes()
    return ("brief-sha256:" + hashlib.sha256(source).hexdigest() + "\n").encode()


def check():
    return RESULT.is_file() and RESULT.read_bytes() == expected()


command = sys.argv[1] if len(sys.argv) == 2 else ""
if command == "make":
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_bytes(expected())
elif command == "check":
    raise SystemExit(0 if check() else 1)
elif command == "review":
    if not check():
        raise SystemExit(1)
    FINDINGS.parent.mkdir(parents=True, exist_ok=True)
    FINDINGS.write_text(json.dumps({"blocking": [], "result": "pass"}, sort_keys=True) + "\n")
elif command == "outside-check":
    if not check():
        raise SystemExit(1)
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    MARKER.write_text("checked\n", encoding="utf-8")
else:
    raise SystemExit(2)
'''


class ComposableIntegrationTest(unittest.TestCase):
    def test_outside_project_package_lands_and_is_judged(self):
        with tempfile.TemporaryDirectory() as raw:
            temporary = Path(raw).resolve()
            project = git_checkout(temporary / "consumer")
            sink = temporary / "home" / "state"
            worktrees = temporary / "worktrees"
            environment = {
                state_root.ENV_VAR: str(sink),
                state_root.WORKTREES_ENV_VAR: str(worktrees),
                tickets_dispatch_launch.HOST_ENV_VAR: "codex",
            }
            with mock.patch.dict(os.environ, environment), self._inside(project):
                self._git(project, "config", "user.name", "composable fixture")
                self._git(project, "config", "user.email", "fixture@example.invalid")
                self._git(project, "config", "core.autocrlf", "false")
                ring, package, probe, brief = self._package(project)

                broken_code, broken = self._check(ring)
                self.assertEqual(1, broken_code, broken)
                self.assertIn("obsolete flag --pack", broken)
                self.assertFalse((project / ".orch-notes" / "outside-probe-ran").exists())

                public = package / "SKILL.md"
                public.write_text(
                    public.read_text(encoding="utf-8").replace(" --pack legacy", ""),
                    encoding="utf-8",
                )
                checked_code, checked = self._check(ring)
                self.assertEqual(0, checked_code, checked)
                self.assertIn("orchflows trust", checked)
                self.assertFalse((project / ".orch-notes" / "outside-probe-ran").exists())

                source_commit = self._git(ROOT, "rev-parse", "HEAD").strip()
                sink.parent.mkdir(parents=True)
                (sink.parent / "receipt.json").write_text(
                    json.dumps({"version": 4, "source_commit": source_commit}),
                    encoding="utf-8",
                )
                rings_trust.grant(ring)
                self._git(project, "add", ".")
                self._git(project, "commit", "--quiet", "-m", "composed package")

                goal = project / "goal.md"
                root = self._call(
                    "frame-open", RUN, "--goal-file", str(goal),
                    "--workflow", PUBLIC,
                )["frame_open"]
                helper = self._call(
                    "frame-open", RUN, "--goal-file", str(goal),
                    "--parent", root["id"], "--workflow", HELPER,
                )["frame_open"]

                root_data = self._ticket(sink, root["id"])
                helper_data = self._ticket(sink, helper["id"])
                package_digest = tickets_pins.tree_digest("workflow", package)
                self.assertEqual(
                    (PUBLIC, package_digest, "SKILL.md"),
                    tuple(root_data[name] for name in (
                        "workflow", "workflow_digest", "workflow_entry",
                    )),
                )
                self.assertEqual(
                    (PUBLIC, package_digest, "workflows/helper/SKILL.md"),
                    tuple(helper_data[name] for name in (
                        "workflow", "workflow_digest", "workflow_entry",
                    )),
                )

                made = self._call(
                    "do", RUN, "--goal-file", str(goal),
                    "--parent", helper["id"],
                    "--standard", LIB_STANDARD,
                    "--standard", LOCAL_STANDARD,
                    "--profile", "orch-worker",
                    "--workspace", str(project),
                    "--isolation", "required",
                    "--host", "codex",
                )["do"]
                made_data, made_attempt, made_assignment = self._assignment(
                    sink, made["id"], made["launch"], "worker",
                )
                self._assert_package_and_standard_pins(
                    made_data, package_digest, "workflows/helper/SKILL.md",
                )
                made_workspace = Path(workspace_record.attempt_workspace(made_data))
                self._run_probe(made_workspace, "make")
                self._run_probe(made_workspace, "check")
                self._git(made_workspace, "add", "proof/result.txt")
                self._git(made_workspace, "commit", "--quiet", "-m", "make proof")
                made_tip = self._git(made_workspace, "rev-parse", "HEAD").strip()
                self._finish_and_land(sink, made["id"], made_attempt, f"git:{made_tip}")
                self.assertTrue((project / "proof" / "result.txt").is_file())
                self.assertFalse(made_workspace.exists())

                brief_digest = hashlib.sha256(brief.read_bytes()).hexdigest()
                landed_tip = self._git(project, "rev-parse", "HEAD").strip()
                judged = self._call(
                    "judge", RUN, "--goal-file", str(goal),
                    "--parent", root["id"],
                    "--standard", LIB_STANDARD,
                    "--standard", LOCAL_STANDARD,
                    "--profile", "orch-planner",
                    "--workspace", str(project),
                    "--isolation", "required",
                    "--host", "codex",
                    "--artifacts", f"git:{landed_tip}",
                    "--artifacts", f"doc:{brief}@sha256:{brief_digest}",
                )["judge"]
                judged_data, judged_attempt, judged_assignment = self._assignment(
                    sink, judged["id"], judged["launch"], "planner",
                )
                self._assert_package_and_standard_pins(
                    judged_data, package_digest, "SKILL.md",
                )
                self.assertEqual("git", judged_assignment["artifact_kind"])
                self.assertEqual(["doc", "git"], judged_assignment["lens_keys"])
                judged_workspace = Path(workspace_record.attempt_workspace(judged_data))
                self._run_probe(judged_workspace, "review")
                self._git(judged_workspace, "add", "review/findings.json")
                self._git(judged_workspace, "commit", "--quiet", "-m", "judge proof")
                judged_tip = self._git(judged_workspace, "rev-parse", "HEAD").strip()
                findings = "review/findings.json"
                self._finish_and_land(
                    sink, judged["id"], judged_attempt, f"git:{judged_tip}",
                    findings=findings,
                )
                self.assertTrue((project / findings).is_file())
                self.assertFalse(judged_workspace.exists())

                self._call("frame-close", RUN, helper["id"], "--status", "complete")
                self._call("frame-close", RUN, root["id"], "--status", "complete")

                identity = json.loads(
                    (sink / "runs" / RUN / "run.json").read_text(encoding="utf-8")
                )
                self.assertEqual(source_commit, identity["orchflows"]["source_commit"])
                self.assertEqual(4, identity["orchflows"]["receipt_version"])
                self.assertEqual(str(project), identity["project"]["root"])

                final_code, final = self._check(ring)
                self.assertEqual(0, final_code, final)
                self.assertNotIn("orchflows trust", final)
                self.assertEqual(
                    "checked\n",
                    (project / ".orch-notes" / "outside-probe-ran").read_text(
                        encoding="utf-8",
                    ),
                )
                inventory = rings.inventory(start=project)
                names = {(record["kind"], record["name"]) for record in inventory}
                self.assertIn(("workflow", PUBLIC), names)
                self.assertNotIn(("workflow", HELPER), names)
                self.assertNotIn(("standard", LOCAL_STANDARD), names)

    @staticmethod
    @contextlib.contextmanager
    def _inside(directory: Path):
        prior = Path.cwd()
        os.chdir(directory)
        try:
            yield
        finally:
            os.chdir(prior)

    def _package(self, project: Path):
        ring = project / rings.BUNDLE_DIR
        orchflows_scaffold.write_bundle(ring, "consumer-proof", "1.0.0")
        orchflows_scaffold.write(ring / "workflows", "workflow", PUBLIC)
        package = ring / "workflows" / PUBLIC
        orchflows_scaffold.write(package / "workflows", "workflow", HELPER)
        orchflows_scaffold.write(package / "standards", "standard", LOCAL_STANDARD)
        references = package / "references"
        references.mkdir()
        brief = references / "brief.txt"
        brief.write_text("render the package proof\n", encoding="utf-8")
        scripts = package / "scripts"
        scripts.mkdir()
        probe = scripts / "probe.py"
        probe.write_text(PROBE, encoding="utf-8")
        (package / "tools.txt").write_text(
            "package-probe :: "
            + subprocess.list2cmdline([sys.executable, str(probe), "outside-check"])
            + "\n",
            encoding="utf-8",
        )
        public = package / "SKILL.md"
        public.write_text(
            public.read_text(encoding="utf-8").replace(
                "Never:",
                "    tickets.py frame-open <run> --goal-file <goal> "
                "--parent <frame> --workflow helper --pack legacy\n\nNever:",
            )
            + "\n[Brief](references/brief.txt) and [probe](scripts/probe.py).\n",
            encoding="utf-8",
        )
        helper = package / "workflows" / HELPER / "SKILL.md"
        helper.write_text(
            helper.read_text(encoding="utf-8").replace(
                "--standard <standard>",
                "--standard orch-code --standard local-proof --profile orch-worker",
            ),
            encoding="utf-8",
        )
        goal = project / "goal.md"
        goal.write_text("Produce and judge the deterministic package proof.\n", encoding="utf-8")
        return ring, package, probe, brief

    @staticmethod
    def _git(directory: Path, *arguments: str) -> str:
        completed = subprocess.run(
            ["git", *arguments], cwd=str(directory), capture_output=True,
            text=True, encoding="utf-8", errors="replace",
        )
        if completed.returncode:
            raise AssertionError(completed.stderr or completed.stdout)
        return completed.stdout

    @staticmethod
    def _check(ring: Path):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = orchflows.main(["check", str(ring)])
        return code, stdout.getvalue() + stderr.getvalue()

    def _call(self, *arguments: str):
        answer = tickets._dispatch(list(arguments))
        self.assertNotIn("error", answer, answer)
        return answer

    @staticmethod
    def _ticket(sink: Path, ticket_id: str):
        path = sink / "tickets" / RUN / f"{ticket_id}.md"
        return _parse_frontmatter(path.read_text(encoding="utf-8"))

    def _assignment(self, sink: Path, ticket_id: str, launch: dict, role: str):
        data = self._ticket(sink, ticket_id)
        attempt = parse_canonical_json(data["dispatch_v1"])["attempts"][-1]
        workspace = workspace_record.attempt_workspace(data)
        response = tickets_assignment.dispatch_assignment(
            [RUN, ticket_id, "--by", ticket_id, "--workspace", workspace],
            attempt=attempt,
        )
        self.assertNotIn("error", response, response)
        assignment = response["assignment"]
        self.assertEqual(f"orch-{role}", data["profile"])
        self.assertEqual(f"orch-{role}", assignment["profile"])
        self.assertEqual(role, assignment["role"])
        self.assertEqual("git", data["workspace_adapter"])
        self._assert_binding(launch, role)
        return data, attempt, assignment

    def _assert_binding(self, launch: dict, role: str):
        host = json.loads((ROOT / "hosts" / "codex.json").read_text(encoding="utf-8"))
        row = host["role_profiles"][role]
        binding = row["binding"]
        effort_keys = sorted(key for key in binding if key.endswith("_effort"))
        effort = binding.get("effort")
        if effort is None and len(effort_keys) == 1:
            effort = binding[effort_keys[0]]
        placeholders = re.findall(
            r"\{([A-Za-z_][A-Za-z0-9_]*)\}", host["installed_items"]["role_agent"],
        )
        agent = binding[placeholders[0]] if placeholders else row["name"]
        native = set(host["launch"]["native_fields"])
        fields = {key: value for key, value in binding.items() if key in native}
        self.assertEqual(
            {
                "host": host["id"],
                "verb": host["launch"]["verb"],
                "agent": agent,
                "model": binding["model"],
                "effort": effort,
                "fields": fields,
            },
            {key: launch[key] for key in (
                "host", "verb", "agent", "model", "effort", "fields",
            )},
        )

    def _assert_package_and_standard_pins(
        self, data: dict, package_digest: str, workflow_entry: str,
    ):
        self.assertEqual(PUBLIC, data["workflow"])
        self.assertEqual(package_digest, data["workflow_digest"])
        self.assertEqual(workflow_entry, data["workflow_entry"])
        pinned = dict(tickets_pins.standards_of(data["standards"]))
        self.assertEqual({LIB_STANDARD, LOCAL_STANDARD}, set(pinned))
        self.assertEqual(
            tickets_pins.item_digest("standard", LIB_STANDARD, owner=PUBLIC),
            pinned[LIB_STANDARD],
        )
        self.assertEqual(
            tickets_pins.item_digest("standard", LOCAL_STANDARD, owner=PUBLIC),
            pinned[LOCAL_STANDARD],
        )

    def _run_probe(self, workspace: Path, command: str):
        probe = workspace / ".orchflows" / "workflows" / PUBLIC / "scripts" / "probe.py"
        completed = subprocess.run(
            [sys.executable, str(probe), command], cwd=str(workspace),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        )
        self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)

    def _finish_and_land(
        self, sink: Path, ticket_id: str, attempt: dict, artifact: str,
        *, findings: str | None = None,
    ):
        lines = ["deterministic fixture command exited 0", f"artifact: {artifact}"]
        if findings is not None:
            lines.append(f"findings: {findings}")
        self._call(
            "result", RUN, ticket_id,
            "--assignment-seal", attempt["assignment_seal"],
            "--dispatch-id", attempt["dispatch_id"],
            "--record-id", "deterministic-result", "--by", ticket_id,
            "--text", "\n".join(lines),
        )
        self._call(
            "dispatch-outcome", RUN, ticket_id,
            "--note", "; ".join(lines[1:]),
        )
        landed = self._call(
            "land", RUN, ticket_id,
            "--assignment-seal", attempt["assignment_seal"],
            "--dispatch-id", attempt["dispatch_id"],
            "--outcome-record-id", "outcome", "--by", "integration-driver",
            "--status", "complete",
        )
        self.assertEqual("complete", landed["land"]["status"])
        data = self._ticket(sink, ticket_id)
        self.assertEqual(
            "retired",
            parse_canonical_json(data["dispatch_v1"])["attempts"][-1]["state"],
        )


if __name__ == "__main__":
    unittest.main()
