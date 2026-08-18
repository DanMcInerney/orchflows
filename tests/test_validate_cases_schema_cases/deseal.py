"""Mechanical de-sealing tool checks."""

import json
import unittest

from tests.test_validate_cases_schema import CASES, REPO_ROOT, dc

SEALED_MANIFEST = """{
  "benchmark_identity": "sha256:%s",
  "evaluation_design": {
    "identity": "sha256:%s",
    "locator": "provenance/design.md"
  },
  "gaps": [],
  "runnable_cases": {
    "locator": "cases/cases.json",
    "sha256": "%s"
  }
}
""" % ("a" * 64, "b" * 64, "c" * 64)

SEALED_QUALIFICATION = """{
  "entries": [
    {
      "covers": [
        "runnable_cases sha256:%s"
      ],
      "criterion": "schema-valid",
      "evidence": {
        "summary": "benchmark_identity recomputed equal; six component digests verified over shipped bytes"
      },
      "oracle": "manifest canonicalization audit: recompute benchmark_identity and every component digest over the shipped bytes"
    }
  ]
}
""" % ("c" * 64)

CLEAN_SIBLING = """{
 "cases": [
  {"id": "one", "provenance": "evidence@sha256:b933dcd4a99f560b factors table"}
 ]
}
"""


class DesealToolTest(unittest.TestCase):
    """T05a criterion 1: the mechanical edit is tested rather than hand-applied."""

    def setUp(self):
        self.manifest = json.loads(SEALED_MANIFEST)
        self.locators = dc.digest_to_locator(self.manifest)

    def test_locator_map_reads_both_dialects(self):
        self.assertEqual(
            {"b" * 64: "provenance/design.md", "c" * 64: "cases/cases.json"},
            self.locators,
        )

    def test_an_already_clean_file_is_returned_unchanged(self):
        self.assertEqual(
            CLEAN_SIBLING, dc.deseal_text(CLEAN_SIBLING, self.locators, "clean.json")
        )

    def test_evidence_identity_is_not_a_component_digest(self):
        out = dc.deseal_text(CLEAN_SIBLING, self.locators, "clean.json")
        self.assertIn("evidence@sha256:b933dcd4a99f560b", out)

    def test_a_sealed_manifest_loses_its_identity_and_every_digest(self):
        out = dc.deseal_text(SEALED_MANIFEST, self.locators, "manifest.json")
        self.assertNotIn("benchmark_identity", out)
        self.assertNotIn("sha256", out)
        self.assertEqual(
            {
                "evaluation_design": {"locator": "provenance/design.md"},
                "gaps": [],
                "runnable_cases": {"locator": "cases/cases.json"},
            },
            json.loads(out),
        )

    def test_formatting_outside_the_deleted_lines_survives(self):
        out = dc.deseal_text(SEALED_MANIFEST, self.locators, "manifest.json")
        kept = [line for line in SEALED_MANIFEST.splitlines() if "sha256" not in line]
        self.assertEqual(
            [line.rstrip(",") for line in kept], [line.rstrip(",") for line in out.splitlines()]
        )
        self.assertTrue(out.endswith("}\n"))

    def test_a_cover_addresses_its_component_by_locator(self):
        out = dc.deseal_text(SEALED_QUALIFICATION, self.locators, "qualification.json")
        self.assertEqual(
            ["runnable_cases cases/cases.json"], json.loads(out)["entries"][0]["covers"]
        )

    def test_a_held_back_store_identity_is_not_a_component_digest(self):
        store = '{\n "protected_evidence": {\n  "identity": "sha256:%s",\n  "visibility": "held"\n }\n}\n' % (
            "e" * 64
        )
        self.assertEqual(store, dc.deseal_text(store, self.locators, "manifest.json"))

    def test_retired_audit_prose_is_replaced_not_left(self):
        out = dc.deseal_text(SEALED_QUALIFICATION, self.locators, "qualification.json")
        self.assertNotIn("benchmark_identity", out)
        self.assertNotIn("canonicalization", out)
        entry = json.loads(out)["entries"][0]
        self.assertIn("component locator", entry["oracle"])
        self.assertIn("nine schema fields present", entry["evidence"]["summary"])

    def test_malformed_json_is_refused_not_skipped(self):
        with self.assertRaises(dc.DesealError) as caught:
            dc.deseal_text('{"gaps": [,]}\n', self.locators, "broken.json")
        self.assertIn("does not parse as JSON", str(caught.exception))

    def test_a_cover_no_component_claims_is_refused_not_left(self):
        orphan = SEALED_QUALIFICATION.replace("c" * 64, "d" * 64)
        with self.assertRaises(dc.DesealError) as caught:
            dc.deseal_text(orphan, self.locators, "qualification.json")
        self.assertIn("no component of this package claims", str(caught.exception))

    def test_an_uncovered_retired_token_is_refused_not_left(self):
        surviving = SEALED_QUALIFICATION.replace(
            "manifest canonicalization audit: recompute benchmark_identity and every "
            "component digest over the shipped bytes",
            "a phrase no rule knows, naming benchmark_identity",
        )
        with self.assertRaises(dc.DesealError) as caught:
            dc.deseal_text(surviving, self.locators, "qualification.json")
        self.assertIn("no rule covers", str(caught.exception))

    def test_a_package_without_a_manifest_is_refused(self):
        with self.assertRaises(dc.DesealError) as caught:
            dc.deseal_package(REPO_ROOT / "benchmarks", write=False)
        self.assertIn("no manifest.json", str(caught.exception))

    def test_the_live_set_is_already_de_sealed(self):
        self.assertEqual(0, dc.main(["--check", "--cases-dir", str(CASES)]))
