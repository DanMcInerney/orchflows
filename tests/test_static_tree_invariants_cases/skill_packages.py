"""Static invariants owned by skill and standard package structure."""
import unittest

from ._support import ROOT, frontmatter_name, packages, split_document, validate

SKILL_TIERS = ("kernel", "workflows")

# The frozen role census. The census is deliberately explicit: adding,
# removing, or renaming a skill requires a role decision here.
# A reusable workflow's `None` is a role decision like any other: its
# prose runs in the orchestrator's own context, so nothing forks and no
# role is declared -- `tools/validate_support/packages.py`'s
# `validate_role` refuses one there.
ROLE_TABLE = {
    # Kernel operations are launched in a resolved profiled child, but do not
    # choose that profile themselves.
    "orch-judge": "none",
    "orch-do": "none",
    # A reusable workflow's `None` is its role decision: `validate_role`
    # refuses a role in a workflow home, because a workflow's prose is
    # driven in the orchestrator's own context and never forks, so there
    # is no role for a host surface to bind.
    "bakeoff": None,
    "checkpointed-build": None,
}


class TestFrozenRoleTable(unittest.TestCase):
    def test_table_covers_exactly_every_skill(self):
        skill_names = {pkg["path"].name for pkg in packages() if not pkg["is_standard"]}
        self.assertEqual(skill_names, set(ROLE_TABLE))

    def test_each_skill_declares_its_frozen_role(self):
        diag = validate.Diagnostics()
        for pkg in packages():
            if pkg["is_standard"]:
                continue
            text = validate._read_source(pkg["skill_md"])
            fm, _ = validate.parse_frontmatter(text, validate.rel(pkg["skill_md"]), diag)
            name = pkg["path"].name
            self.assertEqual(
                ROLE_TABLE[name], fm.get("role"),
                f"{name}: declared role does not match the frozen table",
            )


class TestTierDirectoriesExist(unittest.TestCase):
    def test_only_surviving_skill_tiers_are_declared(self):
        self.assertEqual(
            SKILL_TIERS,
            ("kernel", "workflows"),
        )

    def test_every_skill_tier_directory_exists(self):
        for tier in SKILL_TIERS:
            self.assertTrue((ROOT / "skills" / tier).is_dir(), f"missing skills/{tier}")


class TestPackageNamesMatchFolders(unittest.TestCase):
    def test_every_skill_folder_matches_its_frontmatter_name(self):
        """Every directory under a tier owns a matching ``SKILL.md``."""
        for tier in SKILL_TIERS:
            tier_dir = ROOT / "skills" / tier
            for pkg_dir in sorted(p for p in tier_dir.iterdir() if p.is_dir()):
                skill_md = pkg_dir / "SKILL.md"
                if not skill_md.is_file():
                    continue
                self.assertTrue(
                    skill_md.is_file(),
                    f"{pkg_dir} is a package directory with no SKILL.md; a "
                    "tier holds packages and nothing else",
                )
                name = frontmatter_name(skill_md)
                self.assertEqual(
                    name, pkg_dir.name,
                    f"{skill_md} name {name!r} != folder {pkg_dir.name!r}",
                )

    def test_every_standard_folder_matches_its_frontmatter_name(self):
        standards_dir = ROOT / "standards"
        if not standards_dir.is_dir():
            self.skipTest("no standards/ directory")
        for pkg_dir in sorted(p for p in standards_dir.iterdir() if p.is_dir()):
            manifest = pkg_dir / "STANDARD.md"
            self.assertTrue(manifest.is_file(), f"{pkg_dir} has no STANDARD.md")
            name = frontmatter_name(manifest)
            self.assertEqual(
                name, pkg_dir.name,
                f"{manifest} name {name!r} != folder {pkg_dir.name!r}",
            )


class TestSkillAnatomyOrder(unittest.TestCase):
    """Dispatchable skill bodies order Require, Never, then Return."""

    def test_every_skill_body_orders_require_then_never_then_return(self):
        for pkg in packages():
            if pkg["is_standard"]:
                continue
            with self.subTest(skill=pkg["path"].name):
                _, body = split_document(pkg["skill_md"])
                self.assertLess(body.index("Require:"), body.index("Never:"))
                self.assertLess(body.index("Never:"), body.index("Return:"))
