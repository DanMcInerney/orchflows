"""Structural audit for browser-game intake authority and activation policy."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = (
    ROOT
    / "example-workflows"
    / "references"
    / "browser-game-intake-policy.json"
)
COMPOSITION = ROOT / "example-workflows" / "browser-game"

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
EXPERIMENT_FIELDS = {
    "experiment_id",
    "predeclared_decision",
    "frozen_candidates",
    "workload_corpus_or_cohort",
    "environment",
    "metrics",
    "stopping_rule",
    "falsifiable_oracle",
    "result_identity",
    "transfer_boundary",
}
CONDITIONAL_CONTROLS = {f"CR-{number:02d}" for number in range(1, 17)}
CONDITIONAL_EXPERIMENTS = {f"EX-{number:02d}" for number in range(1, 9)}


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

    def test_atomic_authority_rule_is_deterministic(self):
        classifier = self.policy["atomic_authority"]
        self.assertEqual(
            ["question_id", "field_id", "authority_source"],
            classifier["decision_key"],
        )
        self.assertEqual("empirical-evidence", classifier["default_source"])
        self.assertEqual(
            "commercial_or_legal_acceptance",
            classifier["overrides"]["Q-02"]["commercial_license_constraints"],
        )
        self.assertEqual(
            "accessibility_promises",
            classifier["overrides"]["Q-06"]["accessibility_conformance_target"],
        )
        self.assertEqual(
            "target_cohorts",
            classifier["overrides"]["Q-01"]["target_browser_cohorts"],
        )
        self.assertEqual("empirical", classifier["source_kinds"]["empirical-evidence"])

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

    def test_the_record_call_links_both_intake_contracts(self):
        record = (COMPOSITION / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("browser-game-program-record.schema.json", record)
        self.assertIn("browser-game-intake-policy.json", record)

    def test_experiment_matches_one_open_decision_and_only_its_cells(self):
        experiment = self.policy["experiment_match"]
        self.assertEqual("experiment", experiment["field_disposition"])
        self.assertEqual("decision", experiment["field_resolution_state"])
        self.assertEqual("decision_id", experiment["match_key"])
        self.assertEqual(EXPERIMENT_FIELDS, set(experiment["required_fields"]))
        self.assertTrue(experiment["result_identity_required"])
        self.assertTrue(experiment["transfer_boundary_required"])
        self.assertTrue(experiment["settles_matched_cells_only"])
        self.assertTrue(experiment["preserve_negative_null_and_inconclusive"])
        self.assertFalse(experiment["may_settle_user_only"])

    def test_conditional_controls_are_inactive_without_a_recorded_trigger(self):
        activation = self.policy["conditional_activation"]
        self.assertEqual(
            {
                "governing_identity",
                "decision_id",
                "trigger_record_id",
                "trigger_revision_id",
            },
            set(activation["required_trigger_identity"]),
        )
        self.assertEqual("inactive", activation["state_without_recorded_trigger"])
        self.assertEqual(CONDITIONAL_CONTROLS, set(activation["controls"]))
        for identity, rule in activation["controls"].items():
            with self.subTest(identity=identity):
                self.assertTrue(rule["recorded_trigger_required"])
                self.assertTrue(rule["trigger"])

    def test_conditional_experiments_are_inactive_without_their_promotion_trigger(self):
        activation = self.policy["conditional_activation"]
        self.assertEqual(CONDITIONAL_EXPERIMENTS, set(activation["experiments"]))
        for identity, rule in activation["experiments"].items():
            with self.subTest(identity=identity):
                self.assertTrue(rule["recorded_trigger_required"])
                self.assertTrue(rule["trigger"])

    def test_the_evidence_call_consumes_the_intake_policy(self):
        evidence = (COMPOSITION / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("browser-game-intake-policy.json", evidence)


if __name__ == "__main__":
    unittest.main()
