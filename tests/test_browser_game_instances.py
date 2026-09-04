"""Semantic instance checks for browser-game records and checkpoints."""

from __future__ import annotations

import copy
import json
import unittest

from scripts import browser_game_validate


from tests._repo_root import ROOT
REFERENCES = ROOT / "example-workflows" / "references"

# BGW-TRACE[test:instance-validation|PJ-05,PJ-06,PJ-09,PJ-10,PJ-22,PJ-24,PJ-25,PJ-28]


class BrowserGameInstanceValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(
            (REFERENCES / "browser-game-intake-policy.json").read_text(encoding="utf-8")
        )
        fixtures = json.loads(
            (REFERENCES / "browser-game-instance-fixtures.json").read_text(encoding="utf-8")
        )
        cls.program_record = fixtures["program_record"]
        cls.checkpoint = fixtures["checkpoint"]

    def _errors(self, *, program_record=None, checkpoint=None):
        return browser_game_validate.validate_instances(
            program_record or self.program_record,
            checkpoint or self.checkpoint,
            self.policy,
        )

    def test_repository_fixture_is_semantically_valid(self):
        self.assertEqual([], self._errors())

    def test_legal_acceptance_cannot_be_marked_empirical(self):
        record = copy.deepcopy(self.program_record)
        field = record["records"]["product_brief"]["entries"][0]["questions"]["Q-02"][
            "commercial_license_constraints"
        ]
        field["authority_kind"] = "empirical"
        self.assertTrue(any("commercial_license_constraints" in error for error in self._errors(program_record=record)))

    def test_accessibility_promise_cannot_use_empirical_source(self):
        record = copy.deepcopy(self.program_record)
        field = record["records"]["product_brief"]["entries"][0]["questions"]["Q-06"][
            "accessibility_conformance_target"
        ]
        field["authority_source"] = "empirical-evidence"
        self.assertTrue(any("accessibility_conformance_target" in error for error in self._errors(program_record=record)))

    def test_target_cohort_cannot_be_settled_by_experiment(self):
        record = copy.deepcopy(self.program_record)
        field = record["records"]["product_brief"]["entries"][0]["questions"]["Q-01"][
            "target_browser_cohorts"
        ]
        field["disposition"] = "experiment"
        field["resolution"] = {"state": "decision", "decision_id": "decision:cohort"}
        self.assertTrue(any("target_browser_cohorts" in error for error in self._errors(program_record=record)))

    def test_empirical_cell_cannot_claim_user_only_authority(self):
        record = copy.deepcopy(self.program_record)
        field = record["records"]["product_brief"]["entries"][0]["questions"]["Q-10"][
            "gpu_memory_evidence"
        ]
        field["authority_kind"] = "user-only"
        self.assertTrue(any("gpu_memory_evidence" in error for error in self._errors(program_record=record)))

    def test_outer_and_open_resolution_authority_must_agree(self):
        record = copy.deepcopy(self.program_record)
        field = record["records"]["product_brief"]["entries"][0]["questions"]["Q-06"][
            "accessibility_conformance_target"
        ]
        field["resolution"]["authority_kind"] = "empirical"
        self.assertTrue(any("resolution authority" in error for error in self._errors(program_record=record)))

    def test_user_only_answer_must_preserve_verbatim_settlement(self):
        record = copy.deepcopy(self.program_record)
        field = record["records"]["product_brief"]["entries"][0]["questions"]["Q-02"][
            "commercial_license_constraints"
        ]
        field["resolution"]["verbatim_user_answer"] = "paraphrased"
        self.assertTrue(any("verbatim user answer" in error for error in self._errors(program_record=record)))

    def test_disposition_must_match_resolution_state(self):
        record = copy.deepcopy(self.program_record)
        field = record["records"]["product_brief"]["entries"][0]["questions"]["Q-10"][
            "gpu_memory_evidence"
        ]
        field["disposition"] = "answered"
        self.assertTrue(any("disposition" in error for error in self._errors(program_record=record)))

    def test_checkpoint_coverage_must_equal_bound_identities(self):
        checkpoint = copy.deepcopy(self.checkpoint)
        checkpoint["invalidation"]["covered_candidate_identity"] = "candidate:other"
        self.assertTrue(any("covered candidate" in error for error in self._errors(checkpoint=checkpoint)))

    def test_checkpoint_coverage_must_equal_evidence_set(self):
        checkpoint = copy.deepcopy(self.checkpoint)
        checkpoint["invalidation"]["covered_evidence_identities"] = ["evidence:other"]
        self.assertTrue(any("covered evidence" in error for error in self._errors(checkpoint=checkpoint)))

    def test_disposition_requires_its_exact_branch_payload(self):
        checkpoint = copy.deepcopy(self.checkpoint)
        checkpoint["disposition"] = "experiment"
        self.assertTrue(any("experiment branch" in error for error in self._errors(checkpoint=checkpoint)))

    def test_experiment_branch_must_match_the_program_record(self):
        checkpoint = copy.deepcopy(self.checkpoint)
        checkpoint["disposition"] = "experiment"
        checkpoint["branch"] = {
            "kind": "experiment",
            "decision_id": "decision:other",
            "experiment_id": "experiment:missing",
            "result_identity": "evidence:missing",
        }
        self.assertTrue(any("admitted experiment" in error for error in self._errors(checkpoint=checkpoint)))

    def test_choice_authorizing_disposition_requires_settled_q12(self):
        checkpoint = copy.deepcopy(self.checkpoint)
        checkpoint["q12_revalidation"] = {
            "status": "open",
            "open_decision_identity": "decision:q12",
        }
        self.assertTrue(any("Q-12" in error for error in self._errors(checkpoint=checkpoint)))

    def test_successor_aggregates_must_equal_ordered_entries(self):
        checkpoint = copy.deepcopy(self.checkpoint)
        checkpoint["branch"]["successor_plan"]["standards"]["value"] = ["orch-content"]
        self.assertTrue(any("standards aggregate" in error for error in self._errors(checkpoint=checkpoint)))


if __name__ == "__main__":
    unittest.main()
