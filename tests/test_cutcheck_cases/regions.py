"""Stable ownership-region and merge-oracle admission contract."""

import unittest

from scripts import cutcheck_graph
from scripts import tickets_regions as regions


def region(owner, value, *, artifact="scripts/shared.py", oracle="oracle:git:abc", kind="json-pointer"):
    return {"artifact": artifact, "merge_oracle": oracle, "owner": owner, "selector": {"kind": kind, "value": value}}


def ticket(*selectors, scopes=None):
    return {"pack": "orch-code-pack", "write_scope": scopes or ["scripts/shared.py"], "ownership_regions": list(selectors)}


class RegionSelectorContractTest(unittest.TestCase):
    def test_stable_selector_kinds_require_pinned_adapter_proof(self):
        self.assertEqual([], regions.region_findings("left", ticket(region("left", "/alpha"))))
        line = regions.region_findings("left", ticket(region("left", "12-18", kind="line")))
        self.assertIn("region-selector-kind", {item["code"] for item in line})
        wrong_pack = {**ticket(region("left", "/alpha")), "pack": "orch-content-pack"}
        self.assertIn("region-selector-adapter", {item["code"] for item in regions.region_findings("left", wrong_pack)})


class RegionParallelAdmissionTest(unittest.TestCase):
    def test_only_adapter_proven_non_overlap_admits_shared_artifact(self):
        safe = regions.parallel_admission("left", ticket(region("left", "/alpha")), "right", ticket(region("right", "/beta")), "scripts/shared.py", prover=lambda *_: True)
        self.assertTrue(safe["admitted"])
        overlap = regions.parallel_admission("left", ticket(region("left", "/alpha")), "right", ticket(region("right", "/alpha/child")), "scripts/shared.py")
        self.assertFalse(overlap["admitted"])
        self.assertEqual("dependency-order-or-sole-owner", overlap["fallback"])
        calls = []
        symbolic = regions.parallel_admission(
            "left", ticket(region("left", "alpha", kind="symbol")),
            "right", ticket(region("right", "beta", kind="symbol")), "scripts/shared.py",
            prover=lambda *args: calls.append(args) or True,
        )
        self.assertTrue(symbolic["admitted"])
        self.assertEqual("git", calls[0][0])

    def test_cut_graph_uses_region_proof_instead_of_path_collision(self):
        siblings = {"left": ticket(region("left", "/alpha")), "right": ticket(region("right", "/beta"))}
        siblings["left"].update({"executor": "orch-tdd", "depends_on": []})
        siblings["right"].update({"executor": "orch-tdd", "depends_on": []})
        self.assertEqual([], cutcheck_graph._pairwise(siblings, {}, region_prover=lambda *_: True))
        siblings["right"]["ownership_regions"][0]["merge_oracle"] = ""
        findings = cutcheck_graph._pairwise(siblings, {}, region_prover=lambda *_: True)
        self.assertEqual("scope-collision", findings[0][2])

    def test_every_shared_artifact_requires_its_own_region_proof(self):
        left = ticket(region("left", "/alpha", artifact="a.json"), scopes=["a.json", "b.json"])
        right = ticket(region("right", "/beta", artifact="a.json"), scopes=["a.json", "b.json"])
        for item in (left, right): item.update({"executor": "orch-tdd", "depends_on": []})
        findings = cutcheck_graph._pairwise({"left": left, "right": right}, {}, region_prover=lambda *_: True)
        self.assertEqual(1, len(findings))
        self.assertIn("b.json", findings[0][3])


class RegionMergeOracleTest(unittest.TestCase):
    def test_same_artifact_parallelism_requires_matching_merge_oracle_identity(self):
        missing = region("left", "/alpha", oracle="")
        grade = regions.parallel_admission("left", ticket(missing), "right", ticket(region("right", "/beta")), "scripts/shared.py")
        self.assertFalse(grade["admitted"])
        self.assertIn("merge-oracle-missing", {item["code"] for item in grade["findings"]})
        mismatch = regions.parallel_admission("left", ticket(region("left", "/alpha")), "right", ticket(region("right", "/beta", oracle="oracle:different")), "scripts/shared.py")
        self.assertFalse(mismatch["admitted"])
        self.assertIn("merge-oracle-mismatch", {item["code"] for item in mismatch["findings"]})


if __name__ == "__main__":
    unittest.main()
