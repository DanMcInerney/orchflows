"""Compatibility discovery seam for every workspace behavioral case."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tests.test_workspace_cases.cli_cases import *  # noqa: E402,F401,F403
from tests.test_workspace_cases.contract_cases import *  # noqa: E402,F401,F403
from tests.test_workspace_cases.emission_cases import *  # noqa: E402,F401,F403
from tests.test_workspace_cases.grade_cases import *  # noqa: E402,F401,F403
from tests.test_workspace_cases.operation_cases import *  # noqa: E402,F401,F403
from tests.test_workspace_cases.prepare import *  # noqa: E402,F401,F403
from tests.test_workspace_cases.sharing_cases import *  # noqa: E402,F401,F403
from tests.test_workspace_cases.start_cases import *  # noqa: E402,F401,F403
from scripts import cutcheck_graph  # noqa: E402


class TestDocumentTreeWorkspace(unittest.TestCase):
    """The content adapter owns isolation and durable heading proof."""

    DIGEST = "0" * 64

    @classmethod
    def ticket(cls, run, ticket_id="00-root.01", regions=True):
        ownership = []
        if regions:
            ownership = [{
                "artifact": "article.md",
                "merge_oracle": "document-tree:sha256:" + cls.DIGEST,
                "owner": ticket_id,
                "selector": {"kind": "heading", "value": "Introduction"},
            }]
        return """---
id: {ticket_id}
run: {run}
status: claimed
executor: orch-draft
pack: orch-content-pack
depends_on: []
isolation: required
write_scope: [Introduction]
bound: 30m
claimed_by: writer
claimed_at: 2099-01-01T00:00:00Z
root_generation: v2:root:00-root:1:sha256:{digest}
cut_generation: v2:cut:00-root:1:sha256:{digest}
ownership_regions: {ownership}
assignment_seal: sha256:{digest}
---

## Objective

Draft the introduction.

## Fixed inputs

- input: {{"name":"audience","type":"literal","value":"operators"}}

## Completion test

- the section fits | oracle: review | oracle_class: judged | provenance: authored-here

## Return fields

status.
""".format(
            ticket_id=ticket_id,
            run=run,
            digest=cls.DIGEST,
            ownership=json.dumps(ownership, separators=(",", ":")),
        )

    def invoke(self, sink, *args):
        environment = os.environ.copy()
        environment["ORCHFLOWS_STATE_HOME"] = str(sink)
        completed = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "workspace.py"), *args],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            check=False,
        )
        payload = json.loads(completed.stdout.splitlines()[0])
        return completed, payload

    def write_ticket(self, sink, run, *, regions=True):
        ticket_dir = sink / "tickets" / run
        ticket_dir.mkdir(parents=True)
        (ticket_dir / "00-root.01.md").write_text(
            self.ticket(run, regions=regions), encoding="utf-8"
        )

    def test_concurrent_runs_receive_distinct_script_owned_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "state"
            for run in ("content-a", "content-b"):
                self.write_ticket(sink, run)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(self.invoke, sink, "start", run, "00-root.01")
                    for run in ("content-a", "content-b")
                ]
            results = [future.result() for future in futures]
            self.assertEqual([0, 0], [result[0].returncode for result in results])
            roots = [Path(result[1]["start"]["workspace_root"]) for result in results]
            self.assertEqual(2, len(set(roots)))
            for completed, payload in results:
                self.assertTrue(Path(payload["start"]["region_receipt"]).is_file(), completed.stderr)

    def test_check_requires_and_revalidates_the_durable_region_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "state"
            self.write_ticket(sink, "content-proof")
            started, payload = self.invoke(sink, "start", "content-proof", "00-root.01")
            self.assertEqual(0, started.returncode, started.stderr)
            workspace_root = Path(payload["start"]["workspace_root"])
            (workspace_root / "article.md").write_text("# Wrong\n\nDraft.\n", encoding="utf-8")
            outside, failure = self.invoke(
                sink, "check", "content-proof", "00-root.01", "--base", "HEAD"
            )
            self.assertNotEqual(0, outside.returncode)
            self.assertIn("heading region", failure["error"])
            (workspace_root / "article.md").write_text("# Introduction\n\nDraft.\n", encoding="utf-8")
            checked, verdict = self.invoke(
                sink, "check", "content-proof", "00-root.01", "--base", "HEAD"
            )
            self.assertEqual(0, checked.returncode, checked.stderr)
            self.assertEqual("pass", verdict["check"]["verdict"])
            receipt = Path(payload["start"]["region_receipt"])
            receipt.write_text(receipt.read_text(encoding="utf-8").replace("Introduction", "Altered"), encoding="utf-8")
            rejected, failure = self.invoke(
                sink, "check", "content-proof", "00-root.01", "--base", "HEAD"
            )
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn("region proof", failure["error"])

    def test_start_refuses_a_claimed_document_mutation_without_regions(self):
        with tempfile.TemporaryDirectory() as tmp:
            sink = Path(tmp) / "state"
            self.write_ticket(sink, "content-unproved", regions=False)
            completed, payload = self.invoke(
                sink, "start", "content-unproved", "00-root.01"
            )
            self.assertNotEqual(0, completed.returncode)
            self.assertIn("ownership region", payload["error"])

    def test_cutcheck_admits_only_headings_proved_disjoint_in_the_document(self):
        def item(owner, heading):
            return {
                "executor": "orch-draft",
                "pack": "orch-content-pack",
                "depends_on": [],
                "write_scope": [heading],
                "ownership_regions": [{
                    "artifact": "article.md",
                    "merge_oracle": "document-tree:sha256:" + self.DIGEST,
                    "owner": owner,
                    "selector": {"kind": "heading", "value": heading},
                }],
            }

        with tempfile.TemporaryDirectory() as tmp:
            tree = Path(tmp)
            (tree / "article.md").write_text(
                "# Introduction\n\nA.\n\n# Conclusion\n\nB.\n", encoding="utf-8"
            )
            siblings = {
                "00-root.01": item("00-root.01", "Introduction"),
                "00-root.02": item("00-root.02", "Conclusion"),
            }
            self.assertEqual([], cutcheck_graph._pairwise(siblings, {}, tree=tree))
            siblings["00-root.02"]["ownership_regions"][0]["selector"]["value"] = "Missing"
            findings = cutcheck_graph._pairwise(siblings, {}, tree=tree)
            self.assertEqual(cutcheck_graph.SCOPE_COLLISION, findings[0][2])


if __name__ == "__main__":
    unittest.main()
