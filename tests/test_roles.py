"""Pins the frozen role assignment table from
.orch/runs/20260717T185422Z-role-routing/spec-deliver.md binding_constraints
(acceptance 2); asserts every skills/*/*/SKILL.md frontmatter role matches
it verbatim."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import tools.validate as validate  # noqa: E402

ROLE_TABLE = {
    # none: all engines
    "orch-loop": "none",
    "orch-panel": "none",
    "orch-task": "none",
    "orch-frontier": "none",
    # none: all workflows
    "orch-benchmaker": "none",
    "orch-build": "none",
    "orch-deliver": "none",
    "orch-diagnose": "none",
    "orch-eval-design": "none",
    "orch-evolve": "none",
    "orch-fix": "none",
    "orch-fixture": "none",
    "orch-goal": "none",
    "orch-repair": "none",
    "orch-review-fix": "none",
    "orch-self-improve": "none",
    "orch-spec": "none",
    "orch-triage": "none",
    # none: named kernel
    "orch-delegate": "none",
    "orch-elicit": "none",
    "orch-integrate": "none",
    "orch-worklog": "none",
    # none: named utility
    "orch-off": "none",
    # planner
    "orch-critique": "planner",
    "orch-judge": "planner",
    "orch-synthesize": "planner",
    "orch-decompose": "planner",
    # worker
    "orch-check": "worker",
    "orch-investigate": "worker",
    "orch-verify": "worker",
    "orch-mechanize": "worker",
    "orch-workspace": "worker",
    "orch-tdd": "worker",
    "orch-draft": "worker",
    "orch-render": "worker",
    "orch-edit": "worker",
    "orch-resolve-conflicts": "worker",
    "orch-visualize": "worker",
}


class TestFrozenRoleTable(unittest.TestCase):
    def test_table_has_38_entries(self):
        self.assertEqual(38, len(ROLE_TABLE))

    def test_table_covers_exactly_every_skill(self):
        packages = validate.discover_packages()
        skill_names = {pkg["path"].name for pkg in packages if not pkg["is_pack"]}
        self.assertEqual(skill_names, set(ROLE_TABLE))

    def test_each_skill_declares_its_frozen_role(self):
        packages = validate.discover_packages()
        diag = validate.Diagnostics()
        for pkg in packages:
            if pkg["is_pack"]:
                continue
            text = validate._read_source(pkg["skill_md"])
            fm, _ = validate.parse_frontmatter(text, validate.rel(pkg["skill_md"]), diag)
            name = pkg["path"].name
            self.assertEqual(
                ROLE_TABLE[name], fm.get("role"),
                f"{name}: declared role does not match the frozen table",
            )


if __name__ == "__main__":
    unittest.main()
