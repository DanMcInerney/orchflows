"""Structural audit for browser-game intake authority and activation policy."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = (
    ROOT
    / "compositions"
    / "references"
    / "browser-game-intake-policy.json"
)
COMPOSITION = ROOT / "compositions" / "browser-game"

USER_ONLY_CATEGORIES = {
    "product_intent",
    "commercial_or_legal_acceptance",
    "accessibility_promises",
    "risk_appetite",
    "target_cohorts",
    "public_release_commitments",
}
REQUIRED_DEFAULT_PROHIBITIONS = {
    "stack",
    "cohort",
    "support_promise",
    "numeric_budget",
    "fallback",
    "provider",
    "license_acceptance",
    "release_policy",
    "renderer",
    "engine",
    "webgpu",
    "worker_topology",
    "performance_number",
    "functional_fallback",
    "qa_ladder",
    "release_model",
    "ai_policy",
    "transport",
}


class BrowserGameIntakePolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))

    def test_atomic_intake_uses_the_versioned_program_record_contract(self):
        self.assertEqual("1.0.0", self.policy["policy_version"])
        self.assertEqual(
            "browser-game-program-record.schema.json",
            self.policy["program_record_contract"],
        )
        self.assertEqual(
            {"PJ-06", "PJ-09", "PJ-10", "PJ-22", "PJ-23"},
            set(self.policy["governing_identities"]),
        )
        self.assertEqual(
            {
                "record": "product_brief",
                "questions": [f"Q-{number:02d}" for number in range(1, 13)],
                "unit": "atomic-field",
            },
            self.policy["intake_source"],
        )
        self.assertEqual(
            {"answered", "deferred", "experiment", "not-applicable"},
            set(self.policy["field_dispositions"]),
        )

    def test_user_only_gaps_have_one_verbatim_root_relay_shape(self):
        user_only = self.policy["authority"]["user-only"]
        self.assertEqual(USER_ONLY_CATEGORIES, set(user_only["categories"]))
        self.assertEqual("open-question", user_only["missing_field_state"])
        self.assertEqual("verbatim-user-answer", user_only["settled_by"])
        self.assertEqual("attach-only", user_only["evidence_effect"])

        envelope = user_only["question_envelope"]
        self.assertEqual(
            {
                "kind",
                "question",
                "field_id",
                "open_question_id",
                "program_revision_id",
            },
            set(envelope["required"]),
        )
        self.assertEqual("user-only", envelope["constants"]["kind"])
        self.assertEqual("verbatim", envelope["question_handling"])
        self.assertEqual("root", envelope["relay_owner"])

    def test_empirical_gaps_remain_independent_and_require_evidence(self):
        empirical = self.policy["authority"]["empirical"]
        self.assertEqual(
            {"open-decision", "experiment"}, set(empirical["missing_routes"])
        )
        self.assertEqual("matched-experiment-evidence", empirical["settled_by"])
        self.assertTrue(empirical["independently_schedulable"])
        self.assertFalse(empirical["blocked_by_unrelated_user_only_gap"])

    def test_intake_policy_has_no_product_default_escape_hatch(self):
        self.assertTrue(
            REQUIRED_DEFAULT_PROHIBITIONS
            <= set(self.policy["default_prohibitions"])
        )
        self.assertNotIn("default", self.policy)

    def test_record_ticket_links_both_intake_contracts(self):
        record = (COMPOSITION / "00-record.md").read_text(encoding="utf-8")
        self.assertIn("browser-game-program-record.schema.json", record)
        self.assertIn("browser-game-intake-policy.json", record)


if __name__ == "__main__":
    unittest.main()
