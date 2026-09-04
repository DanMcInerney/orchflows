"""Deterministic proof that one run can span isolated standard adapters."""

import json
import re
import tempfile
import unittest
from pathlib import Path

from scripts import tickets
from tests.test_workspace_cases.common import (
    add_worktree,
    git_available,
    make_repo,
    make_ticket,
    payload_of,
    run_workspace,
)


from tests._repo_root import ROOT
FIXTURE = ROOT / "tests" / "fixtures" / "multi_standard_run.json"


class MultiStandardTopologyTest(unittest.TestCase):
    def test_topology_names_the_join_as_the_only_adapter_boundary(self):
        topology = (ROOT / "rules" / "topology.md").read_text(encoding="utf-8")
        self.assertIn(
            "Adapters meet only at the join: identities may cross dependency edges, "
            "but candidate bytes may not.",
            re.sub(r"\s+", " ", topology),
        )


class MultiStandardRunFixtureTest(unittest.TestCase):
    def test_fixture_carries_three_closed_adapters_and_distinct_workspaces(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual("multi-standard-run", fixture["run"])
        entries = fixture["tickets"]
        self.assertEqual(3, len(entries))
        self.assertEqual(
            {"document-tree", "evidence-store", "git"},
            {item["adapter"] for item in entries},
        )
        self.assertEqual(3, len({item["workspace"] for item in entries}))
        for item in entries:
            adapter = tickets.adapter_spec(item["standard"])
            self.assertEqual(adapter.key, item["adapter"])
            self.assertEqual(adapter.artifact_kind, item["artifact_kind"])

    def test_fixture_dependency_edges_carry_identities_not_candidate_bytes(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        by_id = {item["id"]: item for item in fixture["tickets"]}
        for item in fixture["tickets"]:
            for dependency in item["depends_on"]:
                predecessor = by_id[dependency]
                self.assertIn(
                    predecessor["artifact_identity"], item["context_identities"]
                )
                self.assertNotIn("workspace", item["context_identities"])
                self.assertNotIn("bytes", item["context_identities"])

    def test_fixture_join_uses_each_adapter_artifact_kind(self):
        fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
        by_id = {item["id"]: item for item in fixture["tickets"]}
        expected = {
            item["id"]: item["artifact_kind"] for item in fixture["joins"]
        }
        self.assertEqual(
            {"01-research": "evidence",
             "02-draft": "doc",
             "03-render": "git"},
            expected,
        )
        self.assertEqual(
            {item["id"]: item["adapter"] for item in fixture["tickets"]},
            {item["id"]: item["adapter"] for item in fixture["joins"]},
        )
        for item in fixture["joins"]:
            self.assertEqual(
                by_id[item["id"]]["artifact_identity"], item["artifact_identity"]
            )
            self.assertTrue(
                item["artifact_identity"].startswith(item["artifact_kind"] + ":"),
                item,
            )


@unittest.skipUnless(git_available(), "git is required for a real worktree fixture")
class MultiStandardWorkspaceTest(unittest.TestCase):
    def test_different_adapters_cannot_record_one_candidate_workspace(self):
        with tempfile.TemporaryDirectory() as raw:
            tmp = Path(raw)
            main, run_dir = make_repo(tmp)
            make_ticket(run_dir, "T-code", standard="orch-code")
            make_ticket(run_dir, "T-render", standard="orch-design")
            candidate = add_worktree(main, "candidate", tmp / "candidate")

            first = run_workspace(candidate, "start", "testrun", "T-code")
            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            second = run_workspace(candidate, "start", "testrun", "T-render")

            self.assertEqual(7, second.returncode, second.stdout + second.stderr)
            body = payload_of(second)["start"]
            self.assertEqual(["T-code"], body["shared_with"])
            self.assertFalse(body["isolated"])
