"""Structural audit for the browser-game product-checkpoint contract."""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = (
    ROOT / "example-workflows" / "references" / "browser-game-checkpoint.schema.json"
)
WORKFLOW_PATH = ROOT / "example-workflows" / "browser-game" / "SKILL.md"

DISPOSITIONS = {
    "advance",
    "revise",
    "experiment",
    "user-decision-required",
    "stop",
}
TIME_SENSITIVE_SUBJECTS = {
    "browser",
    "engine",
    "model",
    "tool",
    "license",
    "compatibility",
    "adoption",
    "vendor-terms",
    "security",
}


class BrowserGameCheckpointContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.defs = cls.schema["$defs"]

    def test_the_workflow_owns_and_links_the_checkpoint_contract(self):
        checkpoint = WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("../references/browser-game-checkpoint.schema.json", checkpoint)
        self.assertEqual(
            {"PJ-05", "PJ-08", "PJ-24", "PJ-25"},
            set(self.schema["x-governing-identities"]),
        )

    def test_one_disposition_is_bound_to_fixed_candidate_and_evidence(self):
        self.assertEqual(
            {
                "contract_version",
                "checkpoint_id",
                "governing_requirement_identity",
                "candidate_identity",
                "program_record_revision_identity",
                "evidence",
                "disposition",
                "branch",
                "invalidation",
                "q12_revalidation",
            },
            set(self.schema["required"]),
        )
        self.assertFalse(self.schema["additionalProperties"])
        self.assertEqual(
            DISPOSITIONS,
            set(self.schema["properties"]["disposition"]["enum"]),
        )
        self.assertEqual(1, self.schema["properties"]["evidence"]["minItems"])
        self.assertTrue(self.schema["properties"]["evidence"]["uniqueItems"])

    def test_each_disposition_is_bound_to_one_branch_shape(self):
        clauses = self.schema["allOf"][1:]
        bindings = {}
        for clause in clauses:
            disposition = clause["if"]["properties"]["disposition"]
            values = disposition.get("enum", [disposition.get("const")])
            branch_ref = clause["then"]["properties"]["branch"]["$ref"]
            for value in values:
                bindings[value] = branch_ref
        self.assertEqual(
            {
                "advance": "#/$defs/successorPlanBranch",
                "revise": "#/$defs/successorPlanBranch",
                "stop": "#/$defs/successorPlanBranch",
                "experiment": "#/$defs/experimentBranch",
                "user-decision-required": "#/$defs/userQuestionBranch",
            },
            bindings,
        )

    def test_covered_candidate_or_evidence_change_invalidates_disposition(self):
        invalidation = self.defs["invalidationBoundary"]

        self.assertEqual(
            {
                "covered_candidate_identity",
                "covered_program_record_revision_identity",
                "covered_evidence_identities",
                "candidate_change",
                "program_record_change",
                "evidence_change",
            },
            set(invalidation["required"]),
        )
        for field in ("candidate_change", "program_record_change", "evidence_change"):
            self.assertEqual("invalidate", invalidation["properties"][field]["const"])

    def test_time_sensitive_evidence_carries_its_dated_q12_boundary(self):
        evidence = self.defs["evidenceBinding"]
        conditional = evidence["allOf"][0]

        self.assertEqual(
            {"evidence_identity", "observed_on", "subject"},
            set(evidence["required"]),
        )
        self.assertEqual(
            TIME_SENSITIVE_SUBJECTS,
            set(conditional["if"]["properties"]["subject"]["enum"]),
        )
        self.assertEqual(
            ["revalidation_boundary"],
            conditional["then"]["required"],
        )
        boundary = self.defs["settledQ12Boundary"]
        self.assertEqual(
            {
                "q12_cadence_decision_identity",
                "last_revalidated_on",
                "revalidate_by_or_trigger",
            },
            set(boundary["required"]),
        )

    def test_choice_authorizing_dispositions_require_settled_q12(self):
        authorization = self.schema["allOf"][0]

        self.assertEqual(
            {"advance", "revise", "stop"},
            set(authorization["if"]["properties"]["disposition"]["enum"]),
        )
        q12 = authorization["then"]["properties"]["q12_revalidation"]
        self.assertEqual("settled", q12["properties"]["status"]["const"])
        self.assertEqual(
            ["status", "boundary"],
            q12["required"],
        )


if __name__ == "__main__":
    unittest.main()
