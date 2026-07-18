"""Freezes the tier layout: every skill tier directory exists, and
every package's frontmatter name matches the folder it lives in."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_TIERS = ("kernel", "engines", "workflows", "instances", "utilities")


def frontmatter_name(skill_md: Path):
    text = skill_md.read_text(encoding="utf-8")
    for line in text.split("\n"):
        if line.startswith("name:"):
            return line.split(":", 1)[1].strip()
    return None


class TestTierDirectoriesExist(unittest.TestCase):
    def test_every_skill_tier_directory_exists(self):
        for tier in SKILL_TIERS:
            self.assertTrue((ROOT / "skills" / tier).is_dir(), f"missing skills/{tier}")


class TestPackageNamesMatchFolders(unittest.TestCase):
    def test_every_skill_folder_matches_its_frontmatter_name(self):
        for tier in SKILL_TIERS:
            tier_dir = ROOT / "skills" / tier
            for pkg_dir in sorted(p for p in tier_dir.iterdir() if p.is_dir()):
                skill_md = pkg_dir / "SKILL.md"
                self.assertTrue(skill_md.is_file(), f"{pkg_dir} has no SKILL.md")
                name = frontmatter_name(skill_md)
                self.assertEqual(name, pkg_dir.name, f"{skill_md} name {name!r} != folder {pkg_dir.name!r}")

    def test_every_pack_folder_matches_its_frontmatter_name(self):
        packs_dir = ROOT / "packs"
        if not packs_dir.is_dir():
            self.skipTest("no packs/ directory")
        for pkg_dir in sorted(p for p in packs_dir.iterdir() if p.is_dir()):
            skill_md = pkg_dir / "SKILL.md"
            self.assertTrue(skill_md.is_file(), f"{pkg_dir} has no SKILL.md")
            name = frontmatter_name(skill_md)
            self.assertEqual(name, pkg_dir.name, f"{skill_md} name {name!r} != folder {pkg_dir.name!r}")


if __name__ == "__main__":
    unittest.main()
