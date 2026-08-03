"""Freezes the committed tree: every skill tier directory exists, every
package's frontmatter name matches the folder it lives in, and a shell
entry point README tells the user to run is committed runnable."""
import subprocess
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


class TestRootShellEntryPointsAreExecutable(unittest.TestCase):
    """README documents `./install.sh`. Committed without the execute bit it
    answers `permission denied` on every fresh clone, which is how it shipped.

    Reads the index mode, never the filesystem: git checks out POSIX
    permissions only where the platform has them, so an `os.access` check
    would fail on the Windows leg for a tree that is correct.

    `install.cmd` stays 100644 on purpose -- Windows resolves it by extension
    and has no execute bit to set. `install.py` likewise: README invokes it as
    `python install.py`.
    """

    def test_every_root_shell_script_is_committed_executable(self):
        try:
            listing = subprocess.run(
                ["git", "ls-files", "-s"],
                cwd=ROOT, capture_output=True, text=True, check=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            self.skipTest(f"not a git checkout, so no index mode to read: {exc}")

        checked = []
        for line in listing.splitlines():
            meta, _, path = line.partition("\t")
            if "/" in path or not path.endswith(".sh"):
                continue
            checked.append(path)
            self.assertEqual(
                "100755", meta.split()[0],
                f"{path} is committed {meta.split()[0]}; README documents "
                f"./{path}, which needs the execute bit to run as written",
            )

        # Without this the test passes when the parse or the filter breaks.
        self.assertTrue(checked, "found no root-level *.sh to check")


if __name__ == "__main__":
    unittest.main()
