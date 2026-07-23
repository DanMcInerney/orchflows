"""Contract and replay checks for the canonical benchmark workflow."""

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "skills" / "workflows" / "orch-benchmaker"
SKILL = PACKAGE / "SKILL.md"
PROTOCOL = PACKAGE / "references" / "protocol.md"
MANIFEST_CONTRACT = PACKAGE / "references" / "manifest.md"
FIXTURE = ROOT / "tests" / "fixtures" / "benchmark"
FIXTURE_MANIFEST = FIXTURE / "manifest.json"
PROJECT_OWNER = ROOT / ".orchflows" / "skills" / "benchmaker" / "SKILL.md"
PROJECT_PROTOCOL = PROJECT_OWNER.parent / "references" / "protocol.md"
CLAUDE_ADAPTER = ROOT / ".claude" / "skills" / "benchmaker" / "SKILL.md"


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse the flat frontmatter shape used by orchflows skill files."""
    opening, frontmatter, body = text.split("---", 2)
    if opening:
        raise AssertionError("frontmatter must start at byte zero")
    fields = {}
    for line in frontmatter.strip().splitlines():
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields, body.lstrip("\r\n")


def markdown_section(text: str, heading: str) -> str:
    start = text.index(f"## {heading}")
    end = text.find("\n## ", start + len(heading) + 3)
    return text[start:] if end == -1 else text[start:end]


def squashed(text: str) -> str:
    return " ".join(text.split())


def sha256_identity(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def benchmark_identity(manifest: dict) -> str:
    payload = dict(manifest)
    payload.pop("benchmark_identity")
    canonical = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def qualification_evidence_identity(evidence: dict) -> str:
    payload = {key: value for key, value in evidence.items() if key != "identity"}
    canonical = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return f"sha256:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()}"


def write_json(path: Path, value: dict) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def reseal_manifest(fixture: Path) -> dict:
    manifest_path = fixture / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name in (
        "evaluation_design",
        "runnable_cases",
        "runner",
        "scoring",
        "provenance",
        "qualification",
    ):
        manifest[name]["identity"] = sha256_identity(
            fixture / manifest[name]["locator"]
        )
    manifest["benchmark_identity"] = "sha256:pending"
    manifest["benchmark_identity"] = benchmark_identity(manifest)
    write_json(manifest_path, manifest)
    return manifest


class TestCanonicalBenchmaker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.skill_text = SKILL.read_text(encoding="utf-8")
        cls.fields, cls.body = split_frontmatter(cls.skill_text)
        cls.protocol = PROTOCOL.read_text(encoding="utf-8")
        cls.manifest_contract = MANIFEST_CONTRACT.read_text(encoding="utf-8")

    def test_workflow_anatomy_budget_calls_and_delegation_mapping(self):
        self.assertEqual("orch-benchmaker", self.fields["name"])
        self.assertEqual("none", self.fields["role"])
        self.assertLessEqual(len(self.fields["description"]), 140)
        self.assertLess(self.body.index("Require:"), self.body.index("Never:"))
        self.assertLess(self.body.index("Never:"), self.body.index("Return:"))
        self.assertLessEqual(
            len([line for line in self.body.splitlines() if line.strip()]), 40
        )
        calls = re.findall(r"`(orch-[a-z0-9-]+)`", self.body)
        self.assertEqual(
            ["orch-spec", "orch-deliver", "orch-eval-design"], calls
        )
        self.assertEqual(
            1,
            self.body.count(
                "[internal-call carrier rule]"
                "(references/protocol.md#internal-call-carriage)"
            ),
        )
        self.assertEqual(
            1, self.body.count("[manifest](references/manifest.md)")
        )

        require = squashed(
            self.body[
                self.body.index("Require:") : self.body.index(
                    "\n\n", self.body.index("Require:")
                )
            ]
        )
        for packet_field in (
            "objective",
            "inputs",
            "authority",
            "bounds",
            "return_contract",
            "reply_to",
        ):
            self.assertIn(f"`{packet_field}`", require)
        for mapped_value in (
            "target identity",
            "intended observable outcome",
            "evidence identities",
            "source policy",
            "judgment permission",
            "benchmark write scope",
            "excluded actions",
            "one caller bound",
            "status",
            "benchmark identity",
            "qualification",
            "gaps",
            "bounds spent",
            "changed artifacts",
            "literal return address",
        ):
            self.assertIn(mapped_value, require)

    def test_ordered_stages_return_partial_evidence_and_do_not_evolve(self):
        body = squashed(self.body)
        stages = (
            "freeze an evidence-acquisition spec through `orch-spec`",
            "deliver it through `orch-deliver`",
            "Invoke `orch-eval-design`",
            "Materialize the selected case specifications",
            "qualify the assembled benchmark",
        )
        positions = [body.index(stage) for stage in stages]
        self.assertEqual(sorted(positions), positions)
        self.assertIn("one applicable pack per internal spec", body)
        self.assertIn("partial evidence", body)

        never = body[body.index("Never:") : body.index("Return:")]
        for forbidden_action in (
            "mutate the target",
            "generate a candidate",
            "promote",
            "activate",
            "revise a benchmark in place",
            "call Evolve",
        ):
            self.assertIn(forbidden_action, never)

        returned = body[body.index("Return:") :]
        self.assertIn("the closing result addresses `reply_to`", returned)
        for field in (
            "status",
            "benchmark identity",
            "qualification",
            "gaps",
            "bounds spent",
            "changed artifacts",
        ):
            self.assertIn(field, returned)
        self.assertIn("partial evidence", returned)

    def test_protocol_is_domain_blind_single_pack_and_single_bound(self):
        headings = re.findall(r"^## (.+)$", self.protocol, re.MULTILINE)
        self.assertEqual(
            [
                "Intake and bound",
                "Internal call carriage",
                "Evidence acquisition",
                "Evaluation design",
                "Materialization",
                "Qualification",
                "Manifest and return",
            ],
            headings,
        )
        packed = squashed(self.protocol)
        for phrase in (
            "partition one caller bound",
            "evidence, design, materialization, and qualification",
            "total cannot exceed",
            "unused allocation",
            "Never copy the caller bound",
            "one applicable pack",
            "exactly one pack per internal spec",
            "chain single-pack runs through frozen evidence identities",
            "supplied qualified synthesis",
            "source policy",
            "expected execution cost",
        ):
            self.assertIn(phrase, packed)
        self.assertIn(
            "BenchMaker neither fixes the evaluation boundary nor selects",
            packed,
        )

        known_pack_names = [
            path.name for path in (ROOT / "packs").iterdir() if path.is_dir()
        ]
        for pack_name in known_pack_names:
            self.assertNotIn(pack_name, self.protocol)
        for forbidden_owner in ("`orch-bench`", "`orch-evolve`"):
            self.assertNotIn(forbidden_owner, self.protocol)

    def test_internal_call_carriage_rule_maps_every_packet(self):
        carriage = squashed(
            markdown_section(self.protocol, "Internal call carriage")
        )
        self.assertIn(
            "Every internal Spec, Deliver, and evaluation-design invocation",
            carriage,
        )
        for packet_field in (
            "objective",
            "inputs",
            "authority",
            "bounds",
            "return_contract",
            "reply_to",
        ):
            self.assertIn(f"`{packet_field}`", carriage)
        for invariant in (
            "one applicable pack",
            "stage allocation",
            "never the caller bound",
            "callee's canonical Return",
            "closing recipient",
            "Qualification authority is disjoint from builders",
        ):
            self.assertIn(invariant, carriage)

    def test_protocol_qualifies_required_failures_and_protected_evidence(self):
        qualification = squashed(markdown_section(self.protocol, "Qualification"))
        for check in (
            "oracle failability",
            "coverage",
            "discrimination",
            "reproducibility",
            "redundancy",
            "provenance",
            "execution cost",
        ):
            self.assertIn(check, qualification)
        for policy in (
            "known-bad",
            "required deterministic failure blocks qualification",
            "anchors",
            "secondary",
            "cannot compensate",
            "visibility and release policy",
            "candidate-inaccessible check",
            "UNVERIFIED",
        ):
            self.assertIn(policy, qualification)
        self.assertIn("Builders never qualify", qualification)

    def test_manifest_owner_is_immutable_and_complete(self):
        manifest = squashed(self.manifest_contract)
        for field in (
            "`benchmark_identity`",
            "`evaluation_design`",
            "`runnable_cases`",
            "`runner`",
            "`scoring`",
            "`provenance`",
            "`qualification`",
            "`expected_cost`",
            "`gaps`",
            "`protected_evidence`",
        ):
            self.assertIn(field, manifest)
        for rule in (
            "Changing any covered byte mints a successor benchmark identity",
            "never edits the manifest in place",
            "identity and locator",
            "digest of its exact canonical bytes",
            "resolve the locator and verify that digest before use",
            "oracle_class",
            "evidence",
            "covers",
        ):
            self.assertIn(rule, manifest)


class TestBenchmarkFixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads(FIXTURE_MANIFEST.read_text(encoding="utf-8"))

    def _reference(self, name: str) -> Path:
        reference = self.manifest[name]
        path = (FIXTURE / reference["locator"]).resolve()
        path.relative_to(FIXTURE.resolve())
        self.assertTrue(path.is_file(), f"missing {name} reference: {path}")
        self.assertEqual(reference["identity"], sha256_identity(path))
        return path

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

    def test_manifest_references_are_complete_and_content_addressed(self):
        self.assertEqual(1, self.manifest["schema_version"])
        self.assertEqual(
            self.manifest["benchmark_identity"], benchmark_identity(self.manifest)
        )
        self.assertEqual(
            {
                "schema_version",
                "benchmark_identity",
                "evaluation_design",
                "runnable_cases",
                "runner",
                "scoring",
                "provenance",
                "qualification",
                "expected_cost",
                "gaps",
                "protected_evidence",
            },
            set(self.manifest),
        )
        for name in (
            "evaluation_design",
            "runnable_cases",
            "runner",
            "scoring",
            "provenance",
            "qualification",
        ):
            self._reference(name)
        self.assertEqual("public", self.manifest["protected_evidence"]["visibility"])
        self.assertIsNone(
            self.manifest["protected_evidence"]["candidate_inaccessible_check"]
        )
        self.assertTrue(self.manifest["gaps"])

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
        evidence_payload = {
            field: good_result[field]
            for field in (
                "benchmark_identity",
                "evaluation_design_identity",
                "runner_identity",
                "candidate_identity",
                "cases",
                "covered_evidence",
            )
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
        for identity_field in (
            "benchmark_identity",
            "evaluation_design_identity",
            "runner_identity",
        ):
            self.assertEqual(
                good_result[identity_field], bad_result[identity_field]
            )

    def test_runner_rejects_resealed_unsupported_scoring(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir) / "benchmark"
            shutil.copytree(FIXTURE, fixture)
            manifest = json.loads(
                (fixture / "manifest.json").read_text(encoding="utf-8")
            )
            old_design = manifest["evaluation_design"]["identity"]
            old_scoring = manifest["scoring"]["identity"]
            scoring_path = fixture / manifest["scoring"]["locator"]
            scoring = json.loads(scoring_path.read_text(encoding="utf-8"))
            scoring["aggregation"] = {
                "operator": "unsupported",
                "status": "PASS",
            }
            write_json(scoring_path, scoring)
            new_scoring = sha256_identity(scoring_path)
            design_path = fixture / manifest["evaluation_design"]["locator"]
            design = json.loads(design_path.read_text(encoding="utf-8"))
            design["aggregation"] = scoring["aggregation"]
            write_json(design_path, design)
            new_design = sha256_identity(design_path)

            qualification_path = fixture / manifest["qualification"]["locator"]
            qualification = json.loads(
                qualification_path.read_text(encoding="utf-8")
            )
            for entry in qualification["entries"]:
                entry["covers"] = [
                    (
                        new_scoring
                        if identity == old_scoring
                        else new_design
                        if identity == old_design
                        else identity
                    )
                    for identity in entry["covers"]
                ]
                entry["evidence"]["provenance"] = [
                    (
                        new_scoring
                        if identity == old_scoring
                        else new_design
                        if identity == old_design
                        else identity
                    )
                    for identity in entry["evidence"]["provenance"]
                ]
            write_json(qualification_path, qualification)
            reseal_manifest(fixture)

            result = self._run_fixture(fixture, "known_good.py")
            self.assertEqual(2, result.returncode)
            self.assertIn("unsupported scoring aggregation", result.stderr)

    def test_runner_rejects_incomplete_required_cover_union(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir) / "benchmark"
            shutil.copytree(FIXTURE, fixture)
            manifest = json.loads(
                (fixture / "manifest.json").read_text(encoding="utf-8")
            )
            scoring_identity = manifest["scoring"]["identity"]
            qualification_path = fixture / manifest["qualification"]["locator"]
            qualification = json.loads(
                qualification_path.read_text(encoding="utf-8")
            )
            for entry in qualification["entries"]:
                entry["covers"] = [
                    identity
                    for identity in entry["covers"]
                    if identity != scoring_identity
                ]
            write_json(qualification_path, qualification)
            reseal_manifest(fixture)

            result = self._run_fixture(fixture, "known_good.py")
            self.assertEqual(2, result.returncode)
            self.assertIn(
                "qualification oracle_failability verdict is invalid",
                result.stderr,
            )

    def test_runner_rejects_same_manifest_component_mutation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir) / "benchmark"
            shutil.copytree(FIXTURE, fixture)
            cases_path = fixture / self.manifest["runnable_cases"]["locator"]
            cases_path.write_text(
                cases_path.read_text(encoding="utf-8") + " ",
                encoding="utf-8",
            )

            result = self._run_fixture(fixture, "known_good.py")
            self.assertEqual(2, result.returncode)
            self.assertIn("identity mismatch: cases.json", result.stderr)

    def test_runner_rejects_resealed_self_certification(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture = Path(temp_dir) / "benchmark"
            shutil.copytree(FIXTURE, fixture)
            manifest = json.loads(
                (fixture / "manifest.json").read_text(encoding="utf-8")
            )
            old_cases = manifest["runnable_cases"]["identity"]
            cases_path = fixture / manifest["runnable_cases"]["locator"]
            cases = json.loads(cases_path.read_text(encoding="utf-8"))
            cases["cases"][0]["expected"]["text"] = "SELF-CERTIFIED"
            write_json(cases_path, cases)
            new_cases = sha256_identity(cases_path)

            qualification_path = fixture / manifest["qualification"]["locator"]
            qualification = json.loads(
                qualification_path.read_text(encoding="utf-8")
            )
            for entry in qualification["entries"]:
                entry["covers"] = [
                    new_cases if identity == old_cases else identity
                    for identity in entry["covers"]
                ]
                entry["evidence"]["provenance"] = [
                    new_cases if identity == old_cases else identity
                    for identity in entry["evidence"]["provenance"]
                ]
                entry["evidence"]["identity"] = qualification_evidence_identity(
                    entry["evidence"]
                )
            write_json(qualification_path, qualification)
            reseal_manifest(fixture)

            result = self._run_fixture(fixture, "known_good.py")
            self.assertEqual(2, result.returncode)
            self.assertIn("qualification discrimination failed", result.stderr)

    def test_qualification_recomputes_every_required_check(self):
        replay = self._run("known_good.py")
        self.assertEqual(0, replay.returncode, replay.stderr)
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
            candidate_path = (FIXTURE / candidate["locator"]).resolve()
            candidate_path.relative_to(FIXTURE.resolve())
            self.assertEqual(candidate["identity"], sha256_identity(candidate_path))
        required = {
            entry["criterion"]: entry
            for entry in qualification["entries"]
            if entry["required"]
        }
        required_cover_union = {
            identity
            for entry in required.values()
            for identity in entry["covers"]
        }
        preseal_identities = {
            self.manifest[name]["identity"]
            for name in (
                "evaluation_design",
                "runnable_cases",
                "runner",
                "scoring",
                "provenance",
            )
        }
        self.assertTrue(preseal_identities <= required_cover_union)
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
            for identity in entry["covers"]:
                self.assertTrue(identity.startswith("sha256:"), identity)
        self.assertEqual("PASS", qualification["overall_verdict"])
        optimization = next(
            entry
            for entry in qualification["entries"]
            if entry["criterion"] == "optimization_resistance"
        )
        self.assertFalse(optimization["required"])
        self.assertEqual("UNVERIFIED", optimization["verdict"])


class TestCanonicalSurface(unittest.TestCase):
    def test_canonical_owner_exists_and_project_surfaces_are_absent(self):
        for path in (SKILL, PROTOCOL, MANIFEST_CONTRACT):
            self.assertTrue(path.is_file(), f"missing canonical surface: {path}")
        for path in (PROJECT_OWNER, PROJECT_PROTOCOL, CLAUDE_ADAPTER):
            self.assertFalse(path.exists(), f"stale project surface: {path}")

        owners = []
        for skill_path in (ROOT / "skills").rglob("SKILL.md"):
            fields, _ = split_frontmatter(skill_path.read_text(encoding="utf-8"))
            if fields.get("name") == "orch-benchmaker":
                owners.append(skill_path)
        self.assertEqual([SKILL], owners)


if __name__ == "__main__":
    unittest.main()
