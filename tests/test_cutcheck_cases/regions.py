"""Stable ownership-region and merge-oracle admission contract."""

import unittest

from scripts import cutcheck_graph
from scripts import tickets_regions as regions


def region(symbol, *, proof="proof-1", kind="symbol"):
    return {"artifact": "scripts/shared.py", "proof": {"adapter": "git", "identity": "git:abc", "non-overlap": proof}, "selector": {"kind": kind, "value": symbol}}


def ticket(selector, *, merge=True):
    item = {"write_scope": ["scripts/shared.py"], "ownership_regions": [selector]}
    if merge:
        item["merge_oracles"] = [{"artifact": "scripts/shared.py", "identity": "oracle:unit", "oracle": "python -m unittest test_shared"}]
    return item


class RegionSelectorContractTest(unittest.TestCase):
    def test_stable_selector_kinds_require_pinned_adapter_proof(self):
        self.assertEqual([], regions.region_findings("left", ticket(region("alpha"))))
        line = regions.region_findings("left", ticket(region("12-18", kind="line")))
        self.assertIn("region-selector-kind", {item["code"] for item in line})
        missing = region("alpha")
        del missing["proof"]
        self.assertIn("region-proof-missing", {item["code"] for item in regions.region_findings("left", ticket(missing))})


class RegionParallelAdmissionTest(unittest.TestCase):
    def test_only_adapter_proven_non_overlap_admits_shared_artifact(self):
        safe = regions.parallel_admission("left", ticket(region("alpha")), "right", ticket(region("beta")), "scripts/shared.py")
        self.assertTrue(safe["admitted"])
        overlap = regions.parallel_admission("left", ticket(region("alpha")), "right", ticket(region("alpha")), "scripts/shared.py")
        self.assertFalse(overlap["admitted"])
        self.assertEqual("dependency-order-or-sole-owner", overlap["fallback"])
        inequality = regions.parallel_admission("left", ticket(region("alpha", proof="a")), "right", ticket(region("beta", proof="b")), "scripts/shared.py")
        self.assertFalse(inequality["admitted"])

    def test_cut_graph_uses_region_proof_instead_of_path_collision(self):
        siblings = {"left": ticket(region("alpha")), "right": ticket(region("beta"))}
        siblings["left"].update({"executor": "orch-tdd", "depends_on": []})
        siblings["right"].update({"executor": "orch-tdd", "depends_on": []})
        self.assertEqual([], cutcheck_graph._pairwise(siblings, {}))
        del siblings["right"]["merge_oracles"]
        findings = cutcheck_graph._pairwise(siblings, {})
        self.assertEqual("scope-collision", findings[0][2])


class RegionMergeOracleTest(unittest.TestCase):
    def test_same_artifact_parallelism_requires_matching_merge_oracle_identity(self):
        missing = regions.parallel_admission("left", ticket(region("alpha"), merge=False), "right", ticket(region("beta")), "scripts/shared.py")
        self.assertFalse(missing["admitted"])
        self.assertIn("merge-oracle-missing", {item["code"] for item in missing["findings"]})
        right = ticket(region("beta"))
        right["merge_oracles"][0]["identity"] = "oracle:different"
        mismatch = regions.parallel_admission("left", ticket(region("alpha")), "right", right, "scripts/shared.py")
        self.assertFalse(mismatch["admitted"])
        self.assertIn("merge-oracle-mismatch", {item["code"] for item in mismatch["findings"]})


if __name__ == "__main__":
    unittest.main()
