"""Structural audit for the browser-game program-record contract.

The authoritative specification's section 3.2 owns the record roster and
minimum content.  PJ-03 and PJ-07 additionally require named revisions and an
explicit identity wherever a material record or field is still unresolved.
"""

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = ROOT / "compositions" / "references" / "browser-game-program-record.schema.json"


REQUIRED_RECORDS = {
    "product_brief": (
        "productBriefRevision",
        {"PJ-03", "PJ-06", "PJ-09", "PJ-10"},
        {"questions"},
    ),
    "decision_ledger": (
        "decisionRevision",
        {"PJ-03"},
        {
            "decision_id",
            "status",
            "alternatives",
            "evidence",
            "class",
            "owner",
            "date",
            "invalidation_trigger",
        },
    ),
    "risk_register": (
        "riskRevision",
        {"PJ-04"},
        {
            "risk",
            "affected_outcome",
            "likelihood_basis",
            "consequence",
            "cost_of_delayed_discovery",
            "retirement_action",
            "owner",
        },
    ),
    "support_contracts": (
        "supportContractRevision",
        {"CR-06", "CR-11", "CR-12", "PJ-13"},
        {
            "browser_cells",
            "os_cells",
            "device_cells",
            "webview_cells",
            "pwa_cells",
            "input_cells",
            "locale_cells",
            "accessibility_cells",
            "promised_tier",
            "acquisition_failure_behavior",
            "context_or_device_loss_behavior",
            "missing_input_behavior",
            "unsupported_execution_behavior",
        },
    ),
    "experiment_register": (
        "experimentRevision",
        {"EX-01", "EX-02", "EX-03", "EX-04", "EX-05", "EX-06", "EX-07", "EX-08", "PJ-16"},
        {
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
        },
    ),
    "asset_contracts": (
        "assetContractRevision",
        {"CR-08"},
        {
            "source_runtime_boundary",
            "runtime_formats",
            "bundle_boundaries",
            "provenance",
            "versioned_manifest_decision",
            "validation_oracles",
        },
    ),
    "performance_contracts": (
        "performanceContractRevision",
        {"CR-09", "PJ-14"},
        {
            "device_scenario_metric_cells",
            "physical_device_coverage",
            "device",
            "os_browser_backend",
            "display_condition",
            "power_thermal_condition",
            "scenario",
            "build_identity",
            "warm_cold_state",
            "metric_definition",
            "sample_distribution",
            "baseline_distribution",
            "comparison_baseline",
            "distribution_tails",
            "thresholds",
            "invalidation_rules",
        },
    ),
    "qa_oracle_map": (
        "qaOracleRevision",
        {"CR-10"},
        {"defect_class", "falsifiable_oracle", "environment", "cadence", "evidence_identity"},
    ),
    "release_contracts": (
        "releaseContractRevision",
        {"CR-13"},
        {
            "build_identity",
            "security_controls",
            "rollout",
            "state_api_compatibility",
            "cache_behavior",
            "recovery",
        },
    ),
    "successor_plans": (
        "successorPlanRevision",
        {"AUTH-05", "PJ-18", "PJ-19", "PJ-28"},
        {
            "ordered_artifact_kinds",
            "packs",
            "run_identities",
            "root_identities",
            "dependencies",
            "current_status",
            "ordered_artifacts",
        },
    ),
}

INTAKE_FIELDS = {
    "Q-01": {
        "player", "audience", "genre", "core_loop", "target_browser_cohorts",
        "target_os_cohorts", "target_device_cohorts", "target_webview_cohorts",
        "target_pwa_cohorts", "display_modes", "input_modes", "support_horizon",
    },
    "Q-02": {
        "dimensional_scope", "engine", "renderer", "editor", "physics", "app_shell",
        "dependency_assembly", "commercial_license_constraints",
    },
    "Q-03": {
        "representative_slice", "corpus", "device_lab_evidence", "boot_budget",
        "memory_budget", "cpu_budget", "gpu_budget", "frame_budget", "input_budget",
        "network_budget", "thermal_budget", "power_budget", "quality_budget", "bundle_budget",
    },
    "Q-04": {
        "asset_corpus", "image_recipe", "texture_recipe", "audio_recipe", "video_recipe",
        "font_recipe", "localization_recipe", "legal_provenance", "quality_thresholds",
        "content_bundles", "content_lifetimes", "shader_pipeline",
    },
    "Q-05": {
        "player_mode", "authority_model", "transport", "tick_model", "snapshot_model",
        "rollback_model", "anti_cheat", "ugc", "backend", "cloud_save_conflicts",
        "recovery", "server_operations",
    },
    "Q-06": {
        "accessibility_conformance_target", "browser_at_matrix", "caption_design",
        "narration_design", "spatial_assist_design", "timing_tradeoffs",
        "difficulty_tradeoffs", "competitive_tradeoffs", "participant_cohorts",
        "residual_exclusions",
    },
    "Q-07": {
        "jurisdiction", "age_policy", "children_policy", "privacy_policy", "consent_policy",
        "advertising_policy", "payments_policy", "telemetry_policy", "replay_policy",
        "retention", "data_residency", "incident_notification", "providers", "sla_obligations",
    },
    "Q-08": {
        "offline_mode", "pwa_mode", "cdn", "hosting", "rollout", "rollout_cohort",
        "cache_policy", "service_worker_policy", "state_migration", "rollback_window",
        "rpo", "rto", "incident_drills",
    },
    "Q-09": {
        "ai_provider", "ai_model", "ai_feature", "ai_privacy", "commercial_content_rights",
        "art_approval", "audio_approval", "provenance_format", "task_class_pilot", "cost",
        "latency", "long_term_maintenance_policy",
    },
    "Q-10": {
        "safari_profiler_parity", "firefox_profiler_parity", "gpu_memory_evidence",
        "thermal_evidence", "power_evidence", "variable_refresh_measurement",
        "action_to_photon_measurement", "codec_quirks", "controller_quirks",
        "device_quirks", "webgpu_field_reliability",
    },
    "Q-11": {
        "canonical_item_overlap", "canonical_item_roster", "composition_graph",
        "workspace_semantics", "render_semantics", "evidence_semantics", "fixtures",
        "registry_supersession", "r17_mig_001_numbering",
    },
    "Q-12": {
        "browser_revalidation_cadence", "engine_revalidation_cadence",
        "model_revalidation_cadence", "tool_revalidation_cadence",
        "license_revalidation_cadence", "compatibility_revalidation_cadence",
        "adoption_revalidation_cadence", "security_revalidation_cadence",
    },
}

SUCCESSOR_KIND_PACKS = {
    "research": "orch-research-pack",
    "prose": "orch-content-pack",
    "code": "orch-code-pack",
    "rendered-interface": "orch-design-pack",
}


class TestBrowserGameProgramRecord(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        cls.defs = cls.schema["$defs"]
        cls.records = cls.schema["properties"]["records"]

    def test_contract_and_program_revisions_are_versioned(self):
        self.assertEqual(
            "https://json-schema.org/draft/2020-12/schema", self.schema["$schema"]
        )
        self.assertRegex(self.schema["$id"], r"/browser-game/program-record/v1\.json$")
        self.assertEqual(
            {
                "contract_version",
                "program_id",
                "program_revision_id",
                "supersedes_program_revision_id",
                "records",
            },
            set(self.schema["required"]),
        )
        self.assertEqual("1.0.0", self.schema["properties"]["contract_version"]["const"])

    def test_section_3_2_record_roster_and_minimum_fields_are_complete(self):
        self.assertEqual(set(REQUIRED_RECORDS), set(self.records["required"]))
        self.assertEqual(set(REQUIRED_RECORDS), set(self.records["properties"]))
        for record_name, (definition_name, governing, minimum_fields) in REQUIRED_RECORDS.items():
            with self.subTest(record=record_name):
                collection = self.records["properties"][record_name]
                present = collection["oneOf"][0]
                item_ref = present["properties"]["entries"]["items"]["$ref"]
                self.assertEqual(f"#/$defs/{definition_name}", item_ref)
                definition = self.defs[definition_name]
                self.assertEqual(governing, set(definition["x-governing-identities"]))
                self.assertTrue(minimum_fields <= set(definition["required"]))
                refs = {part.get("$ref") for part in definition["allOf"]}
                self.assertIn("#/$defs/recordRevision", refs)

    def test_each_required_record_is_present_or_has_a_stable_open_identity(self):
        for record_name in REQUIRED_RECORDS:
            with self.subTest(record=record_name):
                alternatives = self.records["properties"][record_name]["oneOf"]
                self.assertEqual("present", alternatives[0]["properties"]["state"]["const"])
                self.assertEqual("#/$defs/openQuestion", alternatives[1]["$ref"])
                self.assertEqual("#/$defs/openDecision", alternatives[2]["$ref"])

    def test_material_fields_cannot_disappear_into_null_or_a_default(self):
        alternatives = self.defs["materialField"]["oneOf"]
        self.assertEqual(
            {"settled", "open-question", "decision"},
            {choice["properties"]["state"]["const"] for choice in alternatives},
        )
        self.assertIn("value", alternatives[0]["required"])
        self.assertIn("open_question_id", alternatives[1]["required"])
        self.assertIn("decision_id", alternatives[2]["required"])

        def walk(value):
            if isinstance(value, dict):
                self.assertNotIn("default", value)
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)

        walk(self.schema)

    def test_product_brief_exposes_every_intake_question_and_atomic_field_state(self):
        questions = self.defs["productBriefRevision"]["properties"]["questions"]
        expected = {f"Q-{number:02d}" for number in range(1, 13)}
        self.assertEqual(expected, set(questions["required"]))
        self.assertEqual(expected, set(questions["properties"]))

        field = self.defs["productBriefField"]
        self.assertTrue(
            {
                "field_id",
                "disposition",
                "resolution",
                "authority_source",
                "authority_kind",
                "owner",
                "rationale",
                "evidence",
                "revision",
            }
            <= set(field["required"])
        )
        self.assertEqual(
            {"answered", "deferred", "experiment", "not-applicable"},
            set(field["properties"]["disposition"]["enum"]),
        )

    def test_product_brief_cannot_silently_omit_atomic_intake_fields(self):
        questions = self.defs["productBriefRevision"]["properties"]["questions"]
        for question_id, expected_fields in INTAKE_FIELDS.items():
            with self.subTest(question=question_id):
                bucket = questions["properties"][question_id]
                self.assertEqual("object", bucket["type"])
                self.assertFalse(bucket["additionalProperties"])
                self.assertEqual(expected_fields, set(bucket["required"]))
                self.assertEqual(expected_fields, set(bucket["properties"]))
                self.assertTrue(
                    all(
                        field_schema["$ref"] == "#/$defs/productBriefField"
                        for field_schema in bucket["properties"].values()
                    )
                )

    def test_successor_plan_keeps_kind_bound_artifacts_and_successor_roots_distinct(self):
        plan = self.defs["successorPlanRevision"]
        self.assertIn("ordered_artifacts", plan["required"])
        ordered = plan["properties"]["ordered_artifacts"]
        self.assertEqual("array", ordered["type"])
        self.assertEqual(1, ordered["minItems"])
        self.assertTrue(ordered["uniqueItems"])
        self.assertEqual("#/$defs/successorArtifact", ordered["items"]["$ref"])

        artifact = self.defs["successorArtifact"]
        self.assertFalse(artifact["additionalProperties"])
        self.assertEqual(
            {
                "artifact_identity",
                "artifact_kind",
                "pack",
                "run_identity",
                "root_identity",
                "dependencies",
                "current_status",
            },
            set(artifact["required"]),
        )
        self.assertEqual(
            set(SUCCESSOR_KIND_PACKS),
            set(artifact["properties"]["artifact_kind"]["enum"]),
        )
        self.assertEqual(
            {"planned", "opened"},
            set(artifact["properties"]["current_status"]["enum"]),
        )
        self.assertEqual(
            "#/$defs/stableIdentity",
            artifact["properties"]["artifact_identity"]["$ref"],
        )
        self.assertEqual(
            "#/$defs/stableIdentity",
            artifact["properties"]["run_identity"]["$ref"],
        )
        self.assertEqual(
            "#/$defs/stableIdentity",
            artifact["properties"]["root_identity"]["$ref"],
        )
        self.assertEqual(
            "#/$defs/stableIdentity",
            artifact["properties"]["dependencies"]["items"]["$ref"],
        )
        self.assertTrue(artifact["properties"]["dependencies"]["uniqueItems"])

        bindings = {
            clause["if"]["properties"]["artifact_kind"]["const"]:
            clause["then"]["properties"]["pack"]["const"]
            for clause in artifact["allOf"]
        }
        self.assertEqual(SUCCESSOR_KIND_PACKS, bindings)


if __name__ == "__main__":
    unittest.main()
