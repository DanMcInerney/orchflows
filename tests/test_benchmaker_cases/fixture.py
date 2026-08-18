"""Runnable fixture and qualification checks for benchmaker."""

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from .shared import (
    ATTACK_CHECKLIST,
    ATTACK_CLASSES,
    ATTACK_OUTCOMES,
    COMPONENT_FIELDS,
    CONTEXT_AXIS_KEYS,
    DECLARATION_FIELDS,
    FIXTURE,
    FIXTURE_MANIFEST,
    POST_QUALIFICATION_FIELDS,
    qualification_evidence_identity,
    write_json,
)


class TestBenchmarkFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))

    def _reference(self, name: str) -> Path:
        path = (FIXTURE / self.manifest[name]["locator"]).resolve()
        path.relative_to(FIXTURE.resolve())
        self.assertTrue(path.is_file(), f"missing {name} reference: {path}")
        return path

    def _record(self, name: str) -> dict:
        """One stage record, read through the component locator that names it."""
        return json.loads(self._reference(name).read_text(encoding="utf-8"))

    def _run_fixture(
        self, fixture: Path, candidate: str
    ) -> subprocess.CompletedProcess[str]:
        manifest = json.loads(
            (fixture / "manifest.json").read_text(encoding="utf-8")
        )
        return subprocess.run(
            [
                sys.executable,
                str(fixture / manifest["runner"]["locator"]),
                "--manifest",
                str(fixture / "manifest.json"),
                "--candidate",
                str(fixture / candidate),
            ],
            cwd=fixture,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def _run(self, candidate: str) -> subprocess.CompletedProcess[str]:
        return self._run_fixture(FIXTURE, candidate)

    def test_manifest_references_are_complete_and_locator_addressed(self):
        self.assertEqual(1, self.manifest["schema_version"])
        fixture_text = FIXTURE_MANIFEST.read_text(encoding="utf-8")
        self.assertNotIn("sha256:", fixture_text)
        # The reference manifest states the law the package manifest states.
        self.assertNotIn("benchmark identity", fixture_text)
        self.assertEqual(
            {"schema_version", *COMPONENT_FIELDS, *DECLARATION_FIELDS,
             *POST_QUALIFICATION_FIELDS},
            set(self.manifest),
        )
        for name in COMPONENT_FIELDS:
            self.assertEqual({"locator"}, set(self.manifest[name]), name)
            self._reference(name)
        self.assertEqual("public", self.manifest["protected_evidence"]["visibility"])
        self.assertIsNone(
            self.manifest["protected_evidence"]["candidate_inaccessible_check"]
        )
        self.assertTrue(self.manifest["gaps"])

    def test_stage_records_and_post_qualification_fields_state_what_ran(self):
        cases = [
            case["case_identity"]
            for case in json.loads(
                (FIXTURE / "cases.json").read_text(encoding="utf-8")
            )["cases"]
        ]
        # Per case, and never silent: `none` with a reason is the legal form.
        for field in ("anchors", "builders"):
            self.assertEqual(set(cases), set(self.manifest[field]))
            for value in self.manifest[field].values():
                self.assertTrue(value.strip())
        for anchor in self.manifest["anchors"].values():
            if anchor.startswith("none"):
                self.assertIn("—", anchor, "a `none` anchor carries its reason")
        # `qualifier` and `attacker` in `builders`' shape: every axis present,
        # each a value or a declared `none` carrying its reason.
        for field in ("qualifier", "attacker"):
            context = self.manifest[field]
            self.assertEqual(set(CONTEXT_AXIS_KEYS), set(context), field)
            for axis, value in context.items():
                self.assertTrue(value.strip(), f"{field}.{axis}")
                if value.startswith("none"):
                    self.assertIn("—", value, f"{field}.{axis} carries its reason")
        # The three stage records are components now, so each figure below is
        # read through the locator rather than inline in the manifest.
        audit = self._record("reference_audit")
        attack = self._record("attack_audit")
        measurement = self._record("measurement")
        # A count and classes, never a rate.
        self.assertIsInstance(audit["defect_count"], int)
        self.assertEqual(len(audit["defect_classes"]), audit["defect_count"])
        self.assertEqual(set(cases), set(audit["method"]))
        self.assertTrue(audit["declared_sample"].strip())
        # Who audited is the record's own first substance: a stage record
        # naming no context is a stage that did not run, whatever it says.
        self.assertEqual(set(CONTEXT_AXIS_KEYS), set(audit["auditor_context"]))
        for axis, value in audit["auditor_context"].items():
            self.assertTrue(value.strip(), f"auditor_context.{axis}")
        # No stage is recorded as not run — all three, here and in gaps.
        gaps = " ".join(self.manifest["gaps"])
        for name, record in (
            ("reference_audit", audit),
            ("attack_audit", attack),
            ("measurement", measurement),
        ):
            self.assertNotIn("not run", record["status"], name)
        self.assertNotIn("attack pass not run", gaps)
        self.assertNotIn("measurement pass not run", gaps)
        # Every class of the dated checklist carries one of the protocol's
        # three outcomes, and every SUCCEEDED class is declared with the attack
        # that works. An undeclared hole is the failure; a declared one is a gap.
        self.assertEqual(ATTACK_CHECKLIST, attack["checklist_identity"])
        self.assertEqual(set(ATTACK_CLASSES), set(attack["classes"]))
        self.assertEqual(set(ATTACK_CLASSES), set(attack["outcomes"]))
        for name, recorded in attack["outcomes"].items():
            self.assertIn(recorded["outcome"], ATTACK_OUTCOMES, name)
            self.assertTrue(recorded["observed"].strip(), name)
        declared = {
            name for hole in attack["unrepaired"] for name in hole["classes"]
        }
        succeeded = {
            name
            for name, recorded in attack["outcomes"].items()
            if recorded["outcome"] == "SUCCEEDED"
        }
        self.assertTrue(succeeded, "a pass that repelled everything is a claim")
        self.assertLessEqual(succeeded, declared)
        for hole in attack["unrepaired"]:
            self.assertTrue(hole["attack"].strip())
        # The measurement separates the two rungs and says by how much: one
        # repeated candidate habit is one signature, not one per case.
        self.assertEqual(2, len(measurement["candidates"]))
        self.assertEqual(set(cases), set(measurement["per_case_status"]))
        self.assertEqual(1, measurement["distinct_failure_signatures"])
        self.assertEqual(2, measurement["margin_cases"])
        # Resolution rests on the one-case floor while the spread is unmeasured.
        self.assertIsNone(self.manifest["resolution"]["measured_rerun_spread"])
        self.assertEqual(1, self.manifest["resolution"]["one_case"])
        for field in ("retirement_trigger", "incomparability"):
            self.assertTrue(self.manifest[field].strip())

    def test_runner_accepts_good_rejects_bad_and_replays_evidence(self):
        good_first = self._run("known_good.py")
        good_second = self._run("known_good.py")
        bad = self._run("known_bad.py")
        self.assertEqual(0, good_first.returncode, good_first.stderr)
        self.assertEqual(0, good_second.returncode, good_second.stderr)
        self.assertEqual(1, bad.returncode, bad.stderr)

        good_result = json.loads(good_first.stdout)
        replay_result = json.loads(good_second.stdout)
        bad_result = json.loads(bad.stdout)
        self.assertEqual(good_result, replay_result)
        self.assertEqual("PASS", good_result["verdict"])
        self.assertEqual("FAIL", bad_result["verdict"])
        self.assertEqual("deterministic", good_result["oracle_class"])
        self.assertEqual(1, good_result["score"])
        self.assertEqual(0, bad_result["score"])
        self.assertTrue(good_result["eligible_for_ranking"])
        self.assertFalse(bad_result["eligible_for_ranking"])
        self.assertEqual(
            good_result["covered_evidence"], bad_result["covered_evidence"]
        )
        # The result identifies the candidate and itself; the benchmark it ran
        # against is a git revision of this tree, not a field it can restate.
        evidence_payload = {
            field: good_result[field]
            for field in ("candidate_identity", "cases", "covered_evidence")
        }
        canonical = json.dumps(
            evidence_payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        self.assertEqual(
            good_result["evidence_identity"],
            f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}",
        )
        self.assertNotEqual(
            good_result["candidate_identity"], bad_result["candidate_identity"]
        )

    def _copy(self, temp_dir: str) -> tuple[Path, dict]:
        fixture = Path(temp_dir) / "benchmark"
        shutil.copytree(FIXTURE, fixture)
        return fixture, json.loads(
            (fixture / "manifest.json").read_text(encoding="utf-8")
        )

    def test_runner_rejects_unsupported_scoring(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture, manifest = self._copy(temp_dir)
            scoring_path = fixture / manifest["scoring"]["locator"]
            scoring = json.loads(scoring_path.read_text(encoding="utf-8"))
            scoring["aggregation"] = {"operator": "unsupported", "status": "PASS"}
            write_json(scoring_path, scoring)
            design_path = fixture / manifest["evaluation_design"]["locator"]
            design = json.loads(design_path.read_text(encoding="utf-8"))
            design["aggregation"] = scoring["aggregation"]
            write_json(design_path, design)

            result = self._run_fixture(fixture, "known_good.py")
            self.assertEqual(2, result.returncode)
            self.assertIn("unsupported scoring aggregation", result.stderr)

    def test_runner_rejects_incomplete_required_cover_union(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture, manifest = self._copy(temp_dir)
            scoring_locator = manifest["scoring"]["locator"]
            qualification_path = fixture / manifest["qualification"]["locator"]
            qualification = json.loads(
                qualification_path.read_text(encoding="utf-8")
            )
            for entry in qualification["entries"]:
                entry["covers"] = [
                    covered
                    for covered in entry["covers"]
                    if covered != scoring_locator
                ]
            write_json(qualification_path, qualification)

            result = self._run_fixture(fixture, "known_good.py")
            self.assertEqual(2, result.returncode)
            self.assertIn(
                "qualification oracle_failability verdict is invalid",
                result.stderr,
            )

    def test_runner_rejects_an_unresolvable_component_locator(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture, manifest = self._copy(temp_dir)
            manifest["runnable_cases"]["locator"] = "absent-cases.json"
            write_json(fixture / "manifest.json", manifest)

            result = self._run_fixture(fixture, "known_good.py")
            self.assertEqual(2, result.returncode)
            self.assertIn("missing reference: absent-cases.json", result.stderr)

    def test_runner_rejects_self_certification(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture, manifest = self._copy(temp_dir)
            cases_path = fixture / manifest["runnable_cases"]["locator"]
            cases = json.loads(cases_path.read_text(encoding="utf-8"))
            cases["cases"][0]["expected"]["text"] = "SELF-CERTIFIED"
            write_json(cases_path, cases)

            result = self._run_fixture(fixture, "known_good.py")
            self.assertEqual(2, result.returncode)
            self.assertIn("qualification discrimination failed", result.stderr)

    def test_qualification_recomputes_every_required_check(self):
        qualification = json.loads(
            self._reference("qualification").read_text(encoding="utf-8")
        )
        design = json.loads(
            self._reference("evaluation_design").read_text(encoding="utf-8")
        )
        case_set = json.loads(
            self._reference("runnable_cases").read_text(encoding="utf-8")
        )
        declared_coverage = set(design["intended_coverage"])
        case_coverage = [set(case["coverage"]) for case in case_set["cases"]]
        self.assertEqual(
            set(design["case_specifications"]),
            {case["case_identity"] for case in case_set["cases"]},
        )
        self.assertEqual(declared_coverage, set().union(*case_coverage))
        for index, coverage in enumerate(case_coverage):
            others = set().union(
                *(other for other_index, other in enumerate(case_coverage) if other_index != index)
            )
            self.assertTrue(coverage - others)
        self.assertEqual(
            {"replays": 3, "candidate_processes": 6},
            qualification["actual_qualification_spend"],
        )
        for candidate in qualification["calibration_candidates"].values():
            self.assertEqual({"locator"}, set(candidate))
            candidate_path = (FIXTURE / candidate["locator"]).resolve()
            candidate_path.relative_to(FIXTURE.resolve())
            self.assertTrue(candidate_path.is_file(), candidate["locator"])
        required = {
            entry["criterion"]: entry
            for entry in qualification["entries"]
            if entry["required"]
        }
        required_cover_union = {
            covered
            for entry in required.values()
            for covered in entry["covers"]
        }
        # `compositions/benchmaker.md`'s done check reads "every component but
        # its own": `qualification` is excluded here because a verdict set
        # covering itself is self-certification, not coverage.
        component_locators = {
            self.manifest[name]["locator"]
            for name in COMPONENT_FIELDS
            if name != "qualification"
        }
        self.assertTrue(component_locators <= required_cover_union)
        self.assertEqual(
            {
                "oracle_failability",
                "coverage",
                "discrimination",
                "reproducibility",
                "redundancy",
                "provenance",
                "execution_cost",
            },
            set(required),
        )
        for entry in required.values():
            self.assertEqual("PASS", entry["verdict"])
            self.assertEqual("deterministic", entry["oracle_class"])
            for field in ("oracle", "evidence", "covers"):
                self.assertTrue(entry[field])
            self.assertIn("identity", entry["evidence"])
            self.assertIn("reproduce", entry["evidence"])
            self.assertIn("observation", entry["evidence"])
            self.assertTrue(entry["evidence"]["provenance"])
            self.assertEqual(
                entry["evidence"]["identity"],
                qualification_evidence_identity(entry["evidence"]),
            )
            # A cover names a component by the locator it resolves through.
            for covered in entry["covers"]:
                self.assertTrue((FIXTURE / covered).is_file(), covered)
        self.assertEqual("PASS", qualification["overall_verdict"])
        optimization = next(
            entry
            for entry in qualification["entries"]
            if entry["criterion"] == "optimization_resistance"
        )
        self.assertFalse(optimization["required"])
        self.assertEqual("UNVERIFIED", optimization["verdict"])
