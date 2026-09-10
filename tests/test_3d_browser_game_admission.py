"""Outside-project admission proof for the 3D browser-game package.

The test copies the shipped package into a disposable Git project and drives
the real ring, trust, sync, frame, dispatch, landing, and resume doors. The
child commands are deterministic fixture scripts: they prove lifecycle and
identity wiring only, and make no claim about an LLM playing or judging a
game.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import (
    orchflows,
    orchflows_node,
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


PUBLIC = "3d-browser-game"
PRIVATE_WORKFLOW = "discovery"
PRIVATE_STANDARD = "blender-game-asset"
PRIVATE_SKILL = "blender-bpy"
RUN = "3d-admission"


class ThreeDBrowserGameAdmissionTest(unittest.TestCase):
    def test_discovery_calls_public_recent_search_with_its_own_private_scope(self):
        """Actual admission doors; no fixture claims an agent researched a game."""
        with tempfile.TemporaryDirectory(prefix="recent-search-admission-") as raw:
            temporary = Path(raw).resolve()
            project = git_checkout(temporary / "consumer")
            sink = temporary / "home" / "state"
            environment = {
                state_root.ENV_VAR: str(sink),
                state_root.WORKTREES_ENV_VAR: str(temporary / "worktrees"),
                tickets_dispatch_launch.HOST_ENV_VAR: "codex",
            }
            with mock.patch.dict(os.environ, environment), self._inside(project):
                ring, _ = self._copy_package(project)
                code, output = self._orchflows(["check", str(ring)])
                self.assertEqual(code, 0, output)
                code, output = self._orchflows(["trust", str(ring)])
                self.assertEqual(code, 0, output)
                goal = project / "research-goal.md"
                goal.write_text(
                    "Find public Three.js guidance. output=evidence; period=all-time; "
                    "source-policy=public documentation; rigor-bar=primary evidence; "
                    "as_of=2026-09-10T23:00:00Z; cap=5.\n\n"
                    "### Sub-questions\n\n1. Which public documentation supports the design?\n",
                    encoding="utf-8",
                )
                game = self._call("frame-open", RUN, "--workflow", PUBLIC,
                                  "--goal-file", str(goal))["frame_open"]
                discovery = self._call("frame-open", RUN, "--workflow", "discovery",
                                       "--parent", game["id"], "--goal-file", str(goal))["frame_open"]
                # This is the public call printed in discovery/SKILL.md.
                research = self._call("frame-open", RUN, "--workflow", "recent-search",
                                      "--parent", discovery["id"], "--goal-file", str(goal))["frame_open"]
                data = self._ticket(sink, research["id"])
                package = ring / "workflows/recent-search"
                digest = tickets_pins.tree_digest("workflow", package)
                self.assertEqual(data["workflow"], "recent-search")
                self.assertEqual(data["workflow_entry"], "SKILL.md")
                self.assertEqual(data["workflow_digest"], digest)
                # Sibling private access is refused; only the public frame grants scope.
                with self.assertRaises(rings.RingError):
                    rings.resolve("skill", "research-acquire", owner=PUBLIC,
                                  project=project, home=temporary / "missing", lib=ROOT)
                (temporary / "evidence").mkdir()
                acquisition = self._call(
                    "do", RUN, "--parent", research["id"], "--goal-file", str(goal),
                    "--standard", "orch-research", "--skill", "research-acquire",
                    "--workspace-adapter", "evidence-store", "--workspace", str(temporary / "evidence"),
                    "--bound", "10m", "--profile", "orch-worker", "--host", "codex",
                )["do"]
                child = self._ticket(sink, acquisition["id"])
                self.assertEqual(child["workflow"], "recent-search")
                self.assertEqual(child["workflow_digest"], digest)
                self.assertEqual(child["skill"], "research-acquire")
                self.assertEqual(child["workspace_adapter"], "evidence-store")
                self.assertIn("orch-research", dict(tickets_pins.standards_of(child["standards"])))
                self.assertTrue(Path(workspace_record.attempt_workspace(child)).is_dir())
                coverage = self._call(
                    "judge", RUN, "--parent", research["id"], "--goal-file", str(goal),
                    "--standard", "orch-research", "--review-independent", "research coverage before synthesis",
                    "--artifacts", "evidence:admission-fixture", "--workspace-adapter", "evidence-store",
                    "--workspace", str(temporary / "evidence"), "--bound", "10m",
                    "--profile", "orch-planner", "--host", "codex",
                )["judge"]
                review = self._ticket(sink, coverage["id"])
                self.assertEqual(review["workflow_digest"], digest)
                self.assertEqual(review["workspace_adapter"], "evidence-store")
                (temporary / "document").mkdir()
                dossier = self._call(
                    "do", RUN, "--parent", research["id"], "--goal-file", str(goal),
                    "--standard", "orch-content", "--standard", "html-dossier",
                    "--workspace-adapter", "document-tree", "--workspace", str(temporary / "document"),
                    "--bound", "10m", "--profile", "orch-worker", "--host", "codex",
                )["do"]
                document = self._ticket(sink, dossier["id"])
                self.assertEqual(document["workflow_digest"], digest)
                self.assertEqual(document["workspace_adapter"], "document-tree")
                self.assertEqual(set(dict(tickets_pins.standards_of(document["standards"]))),
                                 {"orch-content", "html-dossier"})
                # Admission fixture ends here: no dispatched agent or review is fabricated.

    def test_external_package_admission_and_resumable_lifecycle(self):
        with tempfile.TemporaryDirectory(prefix="3d-browser-game-admission-") as raw:
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
                self._git(project, "config", "user.name", "3d admission fixture")
                self._git(project, "config", "user.email", "fixture@example.invalid")
                self._git(project, "config", "core.autocrlf", "false")
                source = self._assert_source_copy_boundary(temporary)
                ring, package = self._copy_package(project, source=source)
                self.assertFalse((package / "node_modules").exists())
                goal = project / "goal.md"
                goal.write_text("Admit the copied 3D browser-game package.\n", encoding="utf-8")
                self._git(project, "add", ".")
                self._git(project, "commit", "--quiet", "-m", "copy 3d package")

                package_digest = tickets_pins.tree_digest("workflow", package)
                self.assertTrue((package / "package.json").is_file())
                package_json = json.loads((package / "package.json").read_text(encoding="utf-8"))
                self.assertEqual(">=24.15.0", package_json["engines"]["node"])
                self.assertEqual(
                    {
                        "ajv": "8.20.0",
                        "ajv-formats": "3.0.1",
                        "gltf-validator": "2.0.0-dev.3.10",
                        "playwright-core": "1.62.1",
                    },
                    package_json["dependencies"],
                )
                self.assertTrue((package / "package-lock.json").is_file())

                # Static admission is allowed to inspect an untrusted ring,
                # but its declared tooling is never probed or installed.
                code, output = self._orchflows(["check", str(ring)])
                self.assertEqual(0, code, output)
                self.assertIn("trust", output)
                self._assert_private_names_are_scoped(project)

                install_calls = []

                def fake_install(item_dir, command):
                    install_calls.append((Path(item_dir), tuple(command)))

                code, output = self._orchflows(["sync", "--project"])
                self.assertEqual(0, code, output)
                self.assertIn("trust", output)
                self.assertEqual([], install_calls)
                self._assert_adapters(project)

                code, output = self._orchflows(["trust", str(ring)])
                self.assertEqual(0, code, output)
                with mock.patch.object(orchflows.orchflows_node, "install", side_effect=fake_install):
                    code, output = self._orchflows(["sync", "--project"])
                self.assertEqual(0, code, output)
                self.assertEqual([(package, ("npm", "ci"))], install_calls)
                stamp = orchflows_node.read_stamp(package)
                self.assertIsNotNone(stamp)
                self.assertEqual(
                    orchflows_node.digest(package / "package-lock.json"),
                    stamp["lock_sha256"],
                )
                # node_modules is a generated cache and is excluded from the
                # package ticket digest. Remove the fixture cache before
                # re-granting trust so the next real resolution has the same
                # content identity as the copied source package.
                shutil.rmtree(package / "node_modules")
                rings_trust.grant(ring)

                self._assert_public_adapter_and_inventory(project)

                root = self._call(
                    "frame-open", RUN, "--goal-file", str(goal), "--workflow", PUBLIC,
                )["frame_open"]
                root_data = self._ticket(sink, root["id"])
                self.assertEqual(PUBLIC, root_data["workflow"])
                self.assertEqual(package_digest, root_data["workflow_digest"])
                self.assertEqual("SKILL.md", root_data["workflow_entry"])

                # Change the package and explicitly re-grant the changed
                # content. The parent frame still carries the old digest, so
                # the child admission door must refuse the stale pin.
                public = package / "SKILL.md"
                original = public.read_bytes()
                public.write_bytes(original + b"\n<!-- stale admission fixture -->\n")
                rings_trust.grant(ring)
                stale = tickets._dispatch([
                    "frame-open", RUN, "--goal-file", str(goal),
                    "--parent", root["id"], "--workflow", PRIVATE_WORKFLOW,
                ])
                self.assertIn("pinned", stale["error"])
                self.assertIn("changed under the seal", stale["error"])
                public.write_bytes(original)
                rings_trust.grant(ring)

                helper = self._call(
                    "frame-open", RUN, "--goal-file", str(goal),
                    "--parent", root["id"], "--workflow", PRIVATE_WORKFLOW,
                )["frame_open"]
                helper_data = self._ticket(sink, helper["id"])
                self.assertEqual(PUBLIC, helper_data["workflow"])
                self.assertEqual(package_digest, helper_data["workflow_digest"])
                self.assertEqual(
                    "workflows/discovery/SKILL.md", helper_data["workflow_entry"],
                )

                failed = self._call(
                    "do", RUN, "--goal-file", str(goal), "--parent", helper["id"],
                    "--standard", PRIVATE_STANDARD, "--skill", PRIVATE_SKILL,
                    "--profile", "orch-worker", "--workspace", str(project),
                    "--isolation", "required", "--host", "codex",
                )["do"]
                failed_data, failed_attempt = self._assignment(sink, failed["id"], failed["launch"])
                self._assert_pins(failed_data, package_digest, "workflows/discovery/SKILL.md")
                failed_workspace = Path(workspace_record.attempt_workspace(failed_data))
                failed_probe = subprocess.run(
                    [sys.executable, "-c", "raise SystemExit(7)"],
                    cwd=str(failed_workspace), capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=30,
                )
                self.assertEqual(7, failed_probe.returncode)
                self._file_result(
                    failed["id"], failed_attempt,
                    "fixture/scripted command exited 7; no artifact promoted",
                )
                failed_land = self._call(
                    "land", RUN, failed["id"],
                    "--assignment-seal", failed_attempt["assignment_seal"],
                    "--dispatch-id", failed_attempt["dispatch_id"],
                    "--outcome-record-id", "outcome", "--by", failed["id"],
                    "--status", "failed",
                )["land"]
                self.assertEqual("failed", failed_land["status"])
                self.assertFalse(failed_workspace.exists())

                resume_code, resume_output = self._orchflows(["resume"])
                self.assertEqual(0, resume_code, resume_output)
                self.assertIn(root["id"], resume_output)
                self.assertIn(helper["id"], resume_output)

                completed = self._call(
                    "do", RUN, "--goal-file", str(goal), "--parent", helper["id"],
                    "--standard", PRIVATE_STANDARD, "--skill", PRIVATE_SKILL,
                    "--profile", "orch-worker", "--workspace", str(project),
                    "--isolation", "required", "--host", "codex",
                )["do"]
                completed_data, completed_attempt = self._assignment(
                    sink, completed["id"], completed["launch"],
                )
                self._assert_pins(completed_data, package_digest, "workflows/discovery/SKILL.md")
                completed_workspace = Path(workspace_record.attempt_workspace(completed_data))
                (completed_workspace / "admission-proof.txt").write_text(
                    "fixture/scripted lifecycle proof\n", encoding="utf-8",
                )
                self._git(completed_workspace, "add", "admission-proof.txt")
                self._git(completed_workspace, "commit", "--quiet", "-m", "fixture admission proof")
                completed_tip = self._git(completed_workspace, "rev-parse", "HEAD").strip()
                self._file_result(
                    completed["id"], completed_attempt,
                    "fixture/scripted command exited 0\nartifact: git:" + completed_tip,
                )
                completed_land = self._call(
                    "land", RUN, completed["id"],
                    "--assignment-seal", completed_attempt["assignment_seal"],
                    "--dispatch-id", completed_attempt["dispatch_id"],
                    "--outcome-record-id", "outcome", "--by", completed["id"],
                    "--status", "complete",
                )["land"]
                self.assertEqual("complete", completed_land["status"])
                self.assertFalse(completed_workspace.exists())
                self.assertTrue((project / "admission-proof.txt").is_file())

                judged = self._call(
                    "judge", RUN, "--goal-file", str(goal), "--parent", helper["id"],
                    "--standard", "threejs-browser-game", "--profile", "orch-planner",
                    "--workspace", str(project), "--isolation", "required",
                    "--host", "codex", "--artifacts", "git:" + completed_tip,
                )["judge"]
                judged_data, judged_attempt = self._assignment(sink, judged["id"], judged["launch"])
                self._assert_pins(
                    judged_data, package_digest, "workflows/discovery/SKILL.md",
                    standard="threejs-browser-game", skill=None,
                )
                judged_workspace = Path(workspace_record.attempt_workspace(judged_data))
                (judged_workspace / "admission-review.json").write_text(
                    json.dumps({"result": "fixture/scripted", "blocking": []}) + "\n",
                    encoding="utf-8",
                )
                self._git(judged_workspace, "add", "admission-review.json")
                self._git(judged_workspace, "commit", "--quiet", "-m", "fixture review")
                self._file_result(
                    judged["id"], judged_attempt,
                    "fixture/scripted review command exited 0",
                )
                judged_land = self._call(
                    "land", RUN, judged["id"],
                    "--assignment-seal", judged_attempt["assignment_seal"],
                    "--dispatch-id", judged_attempt["dispatch_id"],
                    "--outcome-record-id", "outcome", "--by", judged["id"],
                    "--status", "complete",
                )["land"]
                self.assertEqual("complete", judged_land["status"])
                self.assertFalse(judged_workspace.exists())

                self._call("frame-close", RUN, helper["id"], "--status", "complete")
                self._call("frame-close", RUN, root["id"], "--status", "complete")
                resume_code, resume_output = self._orchflows(["resume"])
                self.assertEqual(0, resume_code, resume_output)
                self.assertIn("no open frames", resume_output)

    @staticmethod
    def _copy_source(source: Path, destination: Path):
        """Copy authored package files while leaving generated Node state behind."""

        shutil.copytree(
            source, destination, ignore=shutil.ignore_patterns("node_modules"),
        )
        return destination

    def _author_source(self, destination: Path, *, with_cache: bool) -> Path:
        source = self._copy_source(ROOT / "example-workflows" / PUBLIC, destination)
        if with_cache:
            modules = source / "node_modules"
            modules.mkdir()
            (modules / orchflows_node.STAMP_NAME).write_text(
                json.dumps(
                    {
                        "schema": orchflows_node.STAMP_SCHEMA,
                        "kind": "workflow",
                        "name": PUBLIC,
                        "lockfile": str(source / "package-lock.json"),
                        "lock_sha256": orchflows_node.digest(
                            source / "package-lock.json"
                        ),
                    },
                    sort_keys=True,
                ) + "\n",
                encoding="utf-8",
            )
        return source

    def _assert_source_copy_boundary(self, temporary: Path) -> Path:
        source_without_cache = self._author_source(
            temporary / "author-source-without-cache", with_cache=False,
        )
        copied_without_cache = self._copy_source(
            source_without_cache, temporary / "copied-without-cache",
        )
        self.assertFalse((copied_without_cache / "node_modules").exists())
        self.assertEqual(
            tickets_pins.tree_digest("workflow", source_without_cache),
            tickets_pins.tree_digest("workflow", copied_without_cache),
        )

        source_with_cache = self._author_source(
            temporary / "author-source-with-cache", with_cache=True,
        )
        self.assertTrue((source_with_cache / "node_modules").is_dir())
        copied_with_cache = self._copy_source(
            source_with_cache, temporary / "copied-with-cache",
        )
        self.assertFalse((copied_with_cache / "node_modules").exists())
        self.assertEqual(
            tickets_pins.tree_digest("workflow", source_with_cache),
            tickets_pins.tree_digest("workflow", copied_with_cache),
        )
        return source_with_cache

    def _copy_package(self, project: Path, *, source: Path | None = None):
        ring = project / rings.BUNDLE_DIR
        orchflows_scaffold.write_bundle(ring, "3d-browser-game-consumer", "1.0.0")
        package = ring / "workflows" / PUBLIC
        self._copy_source(
            ROOT / "example-workflows" / PUBLIC if source is None else source,
            package,
        )
        # The public research package establishes its own private method scope.
        shutil.copytree(
            ROOT / "example-workflows" / "recent-search",
            ring / "workflows" / "recent-search",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        return ring, package

    @staticmethod
    @contextlib.contextmanager
    def _inside(directory: Path):
        prior = Path.cwd()
        os.chdir(directory)
        try:
            yield
        finally:
            os.chdir(prior)

    @staticmethod
    def _git(directory: Path, *arguments: str) -> str:
        completed = subprocess.run(
            ["git", *arguments], cwd=str(directory), capture_output=True,
            text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        if completed.returncode:
            raise AssertionError(completed.stderr or completed.stdout)
        return completed.stdout

    @staticmethod
    def _orchflows(arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = orchflows.main(arguments)
        return code, stdout.getvalue() + stderr.getvalue()

    @staticmethod
    def _call(*arguments):
        answer = tickets._dispatch(list(arguments))
        if "error" in answer:
            raise AssertionError(answer["error"])
        return answer

    @staticmethod
    def _ticket(sink: Path, ticket_id: str) -> dict:
        path = sink / "tickets" / RUN / f"{ticket_id}.md"
        return _parse_frontmatter(path.read_text(encoding="utf-8"))

    def _assignment(self, sink: Path, ticket_id: str, launch: dict):
        data = self._ticket(sink, ticket_id)
        attempt = parse_canonical_json(data["dispatch_v1"])["attempts"][-1]
        workspace = workspace_record.attempt_workspace(data)
        assignment = tickets_assignment.dispatch_assignment(
            [RUN, ticket_id, "--by", ticket_id, "--workspace", workspace],
            attempt=attempt,
        )["assignment"]
        self.assertEqual("git", data["workspace_adapter"])
        self.assertEqual("orch-worker" if data["executor"] == "orch-do" else "orch-planner", data["profile"])
        self.assertEqual(data["profile"], assignment["profile"])
        expected_role = "worker" if data["executor"] == "orch-do" else "planner"
        self.assertEqual(expected_role, assignment["role"])
        self._assert_launch(launch, assignment["role"])
        return data, attempt

    def _assert_pins(
        self, data: dict, package_digest: str, entry: str,
        *, standard: str = PRIVATE_STANDARD, skill: str | None = PRIVATE_SKILL,
    ):
        self.assertEqual(PUBLIC, data["workflow"])
        self.assertEqual(package_digest, data["workflow_digest"])
        self.assertEqual(entry, data["workflow_entry"])
        standards = dict(tickets_pins.standards_of(data["standards"]))
        self.assertIn(standard, standards)
        if skill is not None:
            self.assertEqual(
                tickets_pins.item_digest("skill", skill, owner=PUBLIC),
                data["skill_digest"],
            )

    def _file_result(self, ticket_id: str, attempt: dict, text: str):
        result = self._call(
            "result", RUN, ticket_id,
            "--assignment-seal", attempt["assignment_seal"],
            "--dispatch-id", attempt["dispatch_id"],
            "--record-id", "fixture-result", "--by", ticket_id,
            "--text", text,
        )
        self.assertNotIn("error", result)
        outcome = self._call(
            "dispatch-outcome", RUN, ticket_id, "--note", text,
            "--assignment-seal", attempt["assignment_seal"],
            "--dispatch-id", attempt["dispatch_id"], "--by", ticket_id,
        )
        self.assertNotIn("error", outcome)

    def _assert_private_names_are_scoped(self, project: Path):
        records = rings.inventory(project=project, home=project / "missing-home", lib=ROOT)
        names = {(item["kind"], item["name"]) for item in records}
        self.assertIn(("workflow", PUBLIC), names)
        self.assertNotIn(("workflow", PRIVATE_WORKFLOW), names)
        self.assertNotIn(("standard", PRIVATE_STANDARD), names)
        self.assertNotIn(("skill", PRIVATE_SKILL), names)
        private_names = (
            ("workflow", PRIVATE_WORKFLOW),
            ("standard", PRIVATE_STANDARD),
            ("skill", PRIVATE_SKILL),
        )
        for kind, name in private_names:
            with self.assertRaises(rings.RingError):
                rings.resolve(
                    kind, name, trust=False, project=project,
                    home=project / "missing-home", lib=ROOT,
                )
            private = rings.resolve(
                kind, name, owner=PUBLIC, trust=False,
                project=project, home=project / "missing-home", lib=ROOT,
            )
            self.assertTrue(private["private"])
            self.assertTrue(
                Path(private["path"]).resolve().is_relative_to(
                    Path(project / ".orchflows" / "workflows" / PUBLIC).resolve()
                )
            )

    @staticmethod
    def _assert_adapters(project: Path):
        for relative in (
            ".claude/skills/3d-browser-game-workflow/SKILL.md",
            ".agents/skills/3d-browser-game-workflow/SKILL.md",
        ):
            path = project / relative
            assert path.is_file(), path
            text = path.read_text(encoding="utf-8")
            assert PUBLIC in text, path
            assert PRIVATE_WORKFLOW not in path.parts, path

    def _assert_public_adapter_and_inventory(self, project: Path):
        self._assert_adapters(project)
        output_code, output = self._orchflows(["list"])
        self.assertEqual(0, output_code, output)
        self.assertIn(PUBLIC, output)
        self.assertNotIn(PRIVATE_WORKFLOW, output)
        records = rings.inventory()
        self.assertIn(
            ("workflow", PUBLIC),
            {(item["kind"], item["name"]) for item in records},
        )

    @staticmethod
    def _assert_launch(launch: dict, role: str):
        host = json.loads((ROOT / "hosts" / "codex.json").read_text(encoding="utf-8"))
        binding = host["role_profiles"][role]["binding"]
        effort = binding.get("effort")
        effort_keys = [key for key in binding if key.endswith("_effort")]
        if effort is None and len(effort_keys) == 1:
            effort = binding[effort_keys[0]]
        fields = {
            key: value for key, value in binding.items()
            if key in host["launch"]["native_fields"]
        }
        expected_agent = binding.get("agent_type", host["role_profiles"][role]["name"])
        assert {
            "host": host["id"], "verb": host["launch"]["verb"],
            "agent": expected_agent, "model": binding["model"],
            "effort": effort, "fields": fields,
        } == {key: launch[key] for key in ("host", "verb", "agent", "model", "effort", "fields")}

if __name__ == "__main__":
    unittest.main()
