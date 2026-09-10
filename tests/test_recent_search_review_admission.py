"""Execute public research review calls in a disposable consumer.

Outcomes and evidence packets are scripted lifecycle fixtures, never agent
research or substantive verdicts. Standards, package scope and admission are real.
"""
import json
import os
import re
import shlex
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import rings_trust, state_root, tickets, tickets_dispatch_launch, tickets_pins
from scripts.tickets_format import parse_canonical_json
from tests import test_3d_browser_game_admission as admission
from tests._candidate_checkout import git_checkout

DONE = json.dumps({"form": "command", "value": "git --version"}, sort_keys=True, separators=(",", ":"))

def carrier(path, values):
    """Execute the public research call after any private intake call."""
    body = path.read_text(encoding="utf-8")
    command = re.search(r"    tickets\.py frame-open[^\n]*--workflow recent-search[^\n]*(?:\n      [^\n]*)*", body)[0]
    command = re.sub(r"\[([^\]]+)\]", lambda match: match[1] if all(
        name in values for name in re.findall(r"<([^>]+)>", match[1])) else "", command)
    arguments = shlex.split(command)[1:]
    return [re.sub(r"<([^>]+)>", lambda match: values[match[1]], part) for part in arguments]


class RecentSearchReviewAdmissionTests(unittest.TestCase):
    def test_four_evidence_endings_and_nested_dossier_preserve_game_allowance(self):
        with tempfile.TemporaryDirectory(prefix="research-review-") as raw:
            temporary = Path(raw).resolve()
            project = git_checkout(temporary / "consumer")
            sink = temporary / "state"
            fixture = admission.ThreeDBrowserGameAdmissionTest()
            environment = {
                state_root.ENV_VAR: str(sink),
                state_root.WORKTREES_ENV_VAR: str(temporary / "worktrees"),
                tickets_dispatch_launch.HOST_ENV_VAR: "codex",
            }
            with mock.patch.dict(os.environ, environment), fixture._inside(project):
                ring, game_package = fixture._copy_package(project)
                rings_trust.grant(ring)
                goal = project / "goal.md"
                goal.write_text("Independent public evidence fixture; output=evidence; period=all-time; "
                                "as_of=2026-09-10T23:00:00Z; cap=5; source-policy=keyless; rigor-bar=primary.\n",
                                encoding="utf-8")
                game = fixture._call("frame-open", admission.RUN, "--workflow", admission.PUBLIC,
                                     "--goal-file", str(goal))["frame_open"]
                discovery = fixture._call("frame-open", admission.RUN, "--workflow", "discovery",
                                          "--parent", game["id"], "--goal-file", str(goal))["frame_open"]
                package = ring / "workflows/recent-search"
                digest = tickets_pins.tree_digest("workflow", package)
                evidence = temporary / "evidence"
                evidence.mkdir()
                for cluster in ("mechanics", "Three.js", "Blender", "play evidence"):
                    values = {"run": admission.RUN, "frame": discovery["id"],
                              "cluster-question-goal": str(goal)}
                    research = fixture._call(*carrier(
                        game_package / "workflows/discovery/SKILL.md", values))["frame_open"]
                    self._ordinary_ending(fixture, sink, research, goal, evidence,
                                          ["orch-research"], "evidence-store", digest)
                    # Helpers and later fixed packets remain independently judgeable.
                    helper = fixture._call(*carrier(package / "SKILL.md", {
                        "run": admission.RUN, "question-goal": str(goal),
                        "caller-frame": research["id"],
                    }))["frame_open"]
                    helper_data = fixture._ticket(sink, helper["id"])
                    self.assertEqual(helper_data["parent"], research["id"])
                    self._ordinary_ending(fixture, sink, helper, goal, evidence,
                                          ["orch-research"], "evidence-store", digest)
                    self._ordinary_ending(fixture, sink, research, goal, evidence,
                                          ["orch-research"], "evidence-store", digest)
                    fixture._call("frame-close", admission.RUN, helper["id"], "--done", DONE)
                    fixture._call("frame-close", admission.RUN, research["id"], "--done", DONE)
                # A dossier stage resolves both standards inside the public package.
                dossier = fixture._call(*carrier(package / "SKILL.md", {
                    "run": admission.RUN, "question-goal": str(goal),
                    "caller-frame": discovery["id"],
                }))["frame_open"]
                self._ordinary_ending(fixture, sink, dossier, goal, evidence,
                                      ["orch-content", "html-dossier"], "document-tree", digest)
                fixture._call("frame-close", admission.RUN, dossier["id"], "--done", DONE)
                fixture._call("frame-close", admission.RUN, discovery["id"], "--done", DONE)
                game_review = self._judge(fixture, game["id"], goal, evidence,
                                          ["orch-content"], "document-tree")
                self.assertNotIn("error", game_review, game_review)
                game_data = fixture._ticket(sink, game_review["judge"]["id"])
                self.assertEqual(game_data["parent"], game["id"])
                self.assertEqual(game_data["workflow"], admission.PUBLIC)
                self._complete(fixture, sink, game_review["judge"])
                fixture._call("frame-close", admission.RUN, game["id"], "--done", DONE)

    @staticmethod
    def _judge(fixture, parent, goal, workspace, standards, adapter):
        standard_args = [arg for name in standards for arg in ("--standard", name)]
        return tickets._dispatch([
            "judge", admission.RUN, "--parent", parent, "--goal-file", str(goal),
            *standard_args, "--artifacts", "evidence:scripted-fixture" if adapter == "evidence-store" else "doc:scripted-fixture",
            "--workspace", str(workspace), "--workspace-adapter", adapter,
            "--bound", "10m", "--profile", "orch-planner", "--host", "codex",
        ])

    def _ordinary_ending(self, fixture, sink, frame, goal, workspace, standards, adapter, digest):
        result = self._judge(fixture, frame["id"], goal, workspace, standards, adapter)
        self.assertNotIn("error", result, result)
        judged = result["judge"]
        data = fixture._ticket(sink, judged["id"])
        self.assertEqual(data["parent"], frame["id"])
        self.assertEqual(data["executor"], "orch-judge")
        self.assertEqual(data["workspace_adapter"], adapter)
        self.assertEqual(data["workflow_digest"], digest)
        self.assertEqual(set(dict(tickets_pins.standards_of(data["standards"]))), set(standards))
        self._complete(fixture, sink, judged)

    @staticmethod
    def _complete(fixture, sink, issued):
        data = fixture._ticket(sink, issued["id"])
        attempt = parse_canonical_json(data["dispatch_v1"])["attempts"][-1]
        fixture._file_result(issued["id"], attempt, "Scripted review lifecycle fixture; no real evidence judgment.\n")
        fixture._call("land", admission.RUN, issued["id"], "--by", issued["id"],
                      "--assignment-seal", attempt["assignment_seal"], "--dispatch-id", attempt["dispatch_id"],
                      "--outcome-record-id", "outcome", "--status", "complete")


if __name__ == "__main__":
    unittest.main()
