"""Public benchmaker package seams; controls here do not attest live execution."""
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts import orchflows_adapters, rings
from tests._repo_root import ROOT
from tools.validate_support import packages, workflows

PACKAGE = ROOT / "example-workflows" / "benchmaker"
PUBLIC = PACKAGE / "SKILL.md"
TOURNAMENT = ROOT / "example-workflows" / "skill-tournament" / "SKILL.md"
HELPERS = ("benchmark-construct", "benchmark-qualify", "benchmark-calibrate")
STANDARDS = ("benchmark-quality", "benchmark-evidence")


def public_facts(text):
    require = text.split("Require:", 1)[1].split("tickets.py frame-open", 1)[0]
    return {
        "inputs": set(re.findall(r"`([a-z_]+)`", require)),
        "children": re.findall(r"--parent <frame>.*?--workflow ([a-z-]+)", text),
        "return": text.split("Return:", 1)[1],
    }


class PublicIntegrationTests(unittest.TestCase):
    def test_public_handoff_has_required_inputs_and_ordered_private_calls(self):
        text = PUBLIC.read_text(encoding="utf-8")
        facts = public_facts(text)
        required = {"target", "outcome", "sources", "rigor", "standard", "package",
                    "target_configuration", "calibration_policy", "workspace",
                    "evidence_workspace", "access_policy"}
        self.assertLessEqual(required, facts["inputs"])
        self.assertEqual(list(HELPERS), facts["children"])
        self.assertIn("disable-model-invocation: true", text)
        for field in ("validity", "calibration", "final", "gaps"):
            self.assertIn(field, facts["return"])
        # Fact-removal controls retain the Require and frame command anchors.
        for field in ("target_configuration", "calibration_policy"):
            changed = text.replace("`" + field + "`", field)
            self.assertFalse(required <= public_facts(changed)["inputs"])
        changed = text.replace("--workflow benchmark-qualify", "--workflow benchmark-construct")
        self.assertNotEqual(list(HELPERS), public_facts(changed)["children"])

    def test_tournament_forwards_configuration_and_gates_frozen_eligibility(self):
        text = TOURNAMENT.read_text(encoding="utf-8")
        require = text.split("Require:", 1)[1].split("One skill improves", 1)[0]
        self.assertLessEqual(
            {"target_configuration", "calibration_policy", "workspace", "evidence_workspace"},
            set(re.findall(r"`([a-z_]+)`", require)))
        self.assertRegex(text, r"--parent <frame>.*--workflow benchmaker")
        gate = text.split("Enter the campaign", 1)[1].split("**Spend the campaign", 1)[0]
        self.assertLessEqual({"VALID", "CALIBRATED", "INVALID", "UNVERIFIED", "OUT_OF_BAND"},
                             set(re.findall(r"\b[A-Z_]+\b", gate)))
        self.assertIn("frozen git", gate)

    def test_private_names_resolve_only_inside_public_package(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            arguments = dict(project=root / "project", home=root / "home", lib=ROOT, trust=False)
            for kind, names in (("workflow", HELPERS), ("standard", STANDARDS)):
                for name in names:
                    with self.subTest(name=name):
                        record = rings.resolve(kind, name, owner="benchmaker", **arguments)
                        self.assertTrue(record["private"])
                        self.assertEqual("benchmaker", record["owner"])
                        self.assertTrue(Path(record["path"]).is_relative_to(PACKAGE))
                        with self.assertRaises(rings.RingError):
                            rings.resolve(kind, name, **arguments)
            visible = {row["name"] for row in rings.inventory(
                project=root / "project", home=root / "home", lib=ROOT)}
            self.assertIn("benchmaker", visible)
            self.assertFalse(visible & set(HELPERS + STANDARDS))

    def test_generated_project_adapters_expose_only_benchmaker(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            project = root / "project"
            destination = project / ".orchflows" / "workflows" / "benchmaker"
            shutil.copytree(PACKAGE, destination, ignore=shutil.ignore_patterns("__pycache__"))
            entries = orchflows_adapters.plan("project", project=project, home=root / "home", lib=ROOT)
            self.assertEqual(2, len(entries))
            self.assertEqual({"benchmaker-workflow"}, {path.parent.name for path, _ in entries})
            for _path, body in entries:
                self.assertIn("disable-model-invocation: true", body)
                self.assertIn(".orchflows/workflows/benchmaker/SKILL.md", body)

    def test_package_resource_containment_and_literal_standard_calls(self):
        diag = packages.Diagnostics()
        workflows.validate_workflow_packages(
            ROOT, [(PACKAGE, PUBLIC)], diag,
            standard_roots=[ROOT / "standards"],
            overrides={"lib": ROOT, "project": ROOT})
        self.assertFalse(diag.has_errors, "\n".join(diag.lines()))


if __name__ == "__main__":
    unittest.main()
