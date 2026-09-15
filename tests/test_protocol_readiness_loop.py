from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "example-workflows" / "protocol-readiness-loop"
SKILL = PACKAGE / "skills" / "protocol-readiness-loop"
SCRIPT = SKILL / "scripts" / "validate_readiness_ledger.py"
FIXTURES = SKILL / "tests" / "fixtures"

spec = importlib.util.spec_from_file_location("validate_readiness_ledger", SCRIPT)
validator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(validator)


class ProtocolReadinessLoopTests(unittest.TestCase):
    def load(self, name: str):
        return validator.load_ledger(FIXTURES / name)

    def assert_valid(self, name: str):
        records = self.load(name)
        self.assertEqual(validator.validate_records(records), [])
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(FIXTURES / name)],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "valid")
        return records

    def test_ordinary_readiness_convergence(self):
        records = self.assert_valid("ordinary-convergence.jsonl")
        self.assertEqual(records[-1]["terminal_disposition"], "READY_FOR_OWNER_FREEZE")
        self.assertEqual(records[-1]["conformance_defect_count"], 0)
        self.assertEqual(records[-1]["stress_finding_count"], 0)

    def test_repeated_same_class_stops_after_two_revisions(self):
        records = self.assert_valid("recurrence-stop.jsonl")
        terminal = records[-1]
        self.assertEqual(terminal["terminal_disposition"], "BLOCKED")
        self.assertEqual(terminal["terminal_reason"]["code"], "RECURRENT_FAILURE_CLASS")
        self.assertEqual(terminal["terminal_reason"]["revisions_observed"], 2)

    def test_mechanism_probe_routes_without_building_in_loop(self):
        records = self.assert_valid("mechanism-probe-required.jsonl")
        self.assertEqual(records[0]["phase_duration_ms"], "UNKNOWN")
        reason = records[-1]["terminal_reason"]
        self.assertEqual(reason["code"], "MECHANISM_PROBE_REQUIRED")
        self.assertEqual(reason["authorization"], "separate")
        self.assertIs(reason["loop_built_probe"], False)

    def test_conformance_repair_limit_exhaustion(self):
        records = self.assert_valid("conformance-repair-limit.jsonl")
        reason = records[-1]["terminal_reason"]
        self.assertEqual(reason["code"], "CONFORMANCE_REPAIR_LIMIT_REACHED")
        self.assertEqual(reason["repair_attempts"], reason["repair_limit"])

    def test_ledger_validation_rejects_bad_timing(self):
        records = self.load("ordinary-convergence.jsonl")
        records[0]["phase_duration_ms"] += 1
        errors = validator.validate_records(records)
        self.assertTrue(any("timestamp difference" in error for error in errors), errors)

    def test_terminal_status_parser_is_backward_compatible(self):
        expected = {
            "READY_FOR_OWNER_FREEZE",
            "OWNER_DECISION_REQUIRED",
            "ROUND_LIMIT_REACHED",
            "BLOCKED",
            "INVALID",
        }
        self.assertEqual(validator.ALLOWED_TERMINAL_STATUSES, expected)
        baseline = self.load("ordinary-convergence.jsonl")
        for status in expected:
            with self.subTest(status=status):
                records = copy.deepcopy(baseline)
                terminal = records[-1]
                terminal["terminal_disposition"] = status
                terminal["terminal_reason"] = (
                    {"code": "REQUIRED_INPUT_UNAVAILABLE"} if status == "BLOCKED" else None
                )
                self.assertEqual(validator.validate_records(records), [])
        records = copy.deepcopy(baseline)
        records[-1]["terminal_disposition"] = "MECHANISM_PROBE_REQUIRED"
        errors = validator.validate_records(records)
        self.assertTrue(any("unknown terminal_disposition" in error for error in errors), errors)

    def test_reusable_package_is_domain_neutral_and_manual_only(self):
        text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in PACKAGE.rglob("*")
            if path.is_file() and path.suffix in {".md", ".yaml", ".json", ".py"}
        )
        self.assertNotIn("Small League", text)
        self.assertNotIn("AGENT_CALL", text)
        skill_text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("disable-model-invocation: true", skill_text)
        metadata = (SKILL / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("allow_implicit_invocation: false", metadata)

    def test_package_manifests_and_relative_links_are_consistent(self):
        manifests = [
            PACKAGE / "plugin.json",
            PACKAGE / ".codex-plugin" / "plugin.json",
            PACKAGE / ".claude-plugin" / "plugin.json",
        ]
        identities = {
            (value["name"], value["version"], value["skills"])
            for value in (json.loads(path.read_text(encoding="utf-8")) for path in manifests)
        }
        self.assertEqual(identities, {("protocol-readiness-loop", "0.1.0", "./skills/")})

        link_pattern = re.compile(r"\[[^]]+\]\(([^)]+)\)")
        for document in PACKAGE.rglob("*.md"):
            for target in link_pattern.findall(document.read_text(encoding="utf-8")):
                if "://" in target or target.startswith("#"):
                    continue
                relative = target.split("#", 1)[0]
                linked = (document.parent / relative).resolve()
                self.assertTrue(linked.is_relative_to(PACKAGE.resolve()), target)
                self.assertTrue(linked.exists(), f"{document}: missing {target}")


if __name__ == "__main__":
    unittest.main()
