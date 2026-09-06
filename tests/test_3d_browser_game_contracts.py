"""Shape and negative admission checks for the 3D browser-game records."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = ROOT / "example-workflows" / "3d-browser-game" / "references"
SCHEMA_NAMES = (
    "common.schema.json",
    "run-record.schema.json",
    "traceability.schema.json",
    "evidence-index.schema.json",
    "gate-verdict.schema.json",
)
HEADER = {
    "schema_version",
    "kind",
    "id",
    "artifact_commit",
    "created_at",
    "producer",
    "inputs",
    "environment",
    "status",
    "gaps",
    "invalidates",
}


def load(name: str) -> dict:
    return json.loads((REFERENCES / name).read_text(encoding="utf-8"))


def declared_shape(schema: dict, document: dict) -> tuple[bool, str]:
    """Check the closed top-level contract without importing an optional validator."""

    required = set(schema.get("required", ()))
    missing = required - set(document)
    if missing:
        return False, f"missing {sorted(missing)}"
    if schema.get("additionalProperties") is False:
        unknown = set(document) - set(schema.get("properties", ()))
        if unknown:
            return False, f"unknown {sorted(unknown)}"
    for field, rule in schema.get("properties", {}).items():
        if field in document and "const" in rule and document[field] != rule["const"]:
            return False, f"wrong const for {field}"
    return True, "accepted"


class ContractSchemaTests(unittest.TestCase):
    def test_common_header_and_each_concrete_schema_are_closed(self):
        common = load("common.schema.json")
        self.assertEqual(HEADER, set(common["required"]))
        self.assertFalse(common["additionalProperties"])
        self.assertEqual("1.0.0", common["properties"]["schema_version"]["const"])
        for name in SCHEMA_NAMES[1:]:
            schema = load(name)
            self.assertTrue(HEADER.issubset(schema["required"]), name)
            self.assertFalse(schema["additionalProperties"], name)

    def test_unknown_top_level_field_and_missing_header_are_rejected(self):
        for name in SCHEMA_NAMES[1:]:
            schema = load(name)
            document = {field: None for field in schema["required"]}
            document["schema_version"] = "1.0.0"
            if name == "run-record.schema.json":
                document["kind"] = "run-record"
            elif name == "traceability.schema.json":
                document["kind"] = "traceability"
            elif name == "evidence-index.schema.json":
                document["kind"] = "evidence-index"
            else:
                document["kind"] = "gate-verdict"
            accepted, reason = declared_shape(schema, document)
            self.assertTrue(accepted, (name, reason))
            document["unowned_field"] = True
            accepted, reason = declared_shape(schema, document)
            self.assertFalse(accepted, (name, reason))
            del document["unowned_field"]
            document.pop("id")
            accepted, reason = declared_shape(schema, document)
            self.assertFalse(accepted, (name, reason))

    def test_concrete_kinds_and_gate_score_floor_are_declared(self):
        expected = {
            "run-record.schema.json": "run-record",
            "traceability.schema.json": "traceability",
            "evidence-index.schema.json": "evidence-index",
            "gate-verdict.schema.json": "gate-verdict",
        }
        for name, kind in expected.items():
            self.assertEqual(kind, load(name)["properties"]["kind"]["const"])
        score = load("gate-verdict.schema.json")["$defs"]["score"]["properties"]["score"]
        self.assertEqual("integer", score["type"])
        self.assertEqual(0, score["minimum"])
        self.assertEqual(4, score["maximum"])
        self.assertEqual({"pass", "fix", "redesign", "unverified"}, set(load("gate-verdict.schema.json")["properties"]["disposition"]["enum"]))

    def test_traceability_rows_bind_both_verdicts_and_invalidation(self):
        row = load("traceability.schema.json")["$defs"]["row"]
        self.assertTrue(
            {
                "prompt_promise",
                "requirement",
                "playable_evidence_ids",
                "normal_input_path",
                "core_gate_verdict",
                "final_gate_verdict",
                "owner",
                "invalidation_trigger",
            }.issubset(row["required"])
        )

    def test_evidence_index_accepts_unpromoted_draft_but_requires_promotion_when_complete(self):
        schema = load("evidence-index.schema.json")
        self.assertNotIn("promotion", schema["required"])
        self.assertEqual("null", schema["properties"]["promotion"]["oneOf"][0]["type"])
        condition = schema["allOf"][0]
        self.assertEqual("complete", condition["if"]["properties"]["status"]["const"])
        self.assertEqual(["promotion"], condition["then"]["required"])

    def test_commit_and_relative_path_shapes_reject_unpinned_values(self):
        commit = load("common.schema.json")["$defs"]["commit"]["pattern"]
        self.assertRegex("git:" + "a" * 40, commit)
        self.assertNotRegex("working-tree", commit)
        path = load("evidence-index.schema.json")["$defs"]["relativePath"]["pattern"]
        self.assertRegex("evidence/core/session.json", path)
        self.assertNotRegex("../outside.json", path)
        self.assertNotRegex("C:/outside.json", path)


if __name__ == "__main__":
    unittest.main()
