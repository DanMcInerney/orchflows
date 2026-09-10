"""The public research workflow carries its acquisition method across projects."""
import tempfile
import unittest
from pathlib import Path

from tests._repo_root import ROOT
from scripts import rings


class RecentSearchPackageTests(unittest.TestCase):
    def test_gallery_resolves_with_contained_acquisition_and_no_project_skill(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            record = rings.resolve("workflow", "recent-search", start=home, home=home)
        owner = Path(record["dir"])
        self.assertEqual(owner, ROOT / "example-workflows" / "recent-search")
        self.assertTrue((owner / "skills/research-acquire/scripts/super_research/runner.py").is_file())
        self.assertFalse((ROOT / ".orchflows/skills/research-acquire/SKILL.md").exists())


if __name__ == "__main__":
    unittest.main()
