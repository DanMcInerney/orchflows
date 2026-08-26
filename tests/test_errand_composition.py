"""The named errand composition is one code-delivery ticket."""

import unittest
from pathlib import Path

from scripts import tickets


ROOT = Path(__file__).resolve().parents[1]
ERRAND = ROOT / "compositions" / "errand"


class ErrandCompositionTest(unittest.TestCase):
    def test_the_named_composition_has_exactly_one_delivery_stub(self):
        manifest = tickets._parse_frontmatter(
            (ERRAND / "template.md").read_text(encoding="utf-8")
        )
        self.assertEqual("errand", manifest["name"])
        self.assertEqual("named", manifest["entry"])
        stubs = sorted(
            path for path in ERRAND.glob("*.md") if path.name != "template.md"
        )
        self.assertEqual(["00-deliver.md"], [path.name for path in stubs])

    def test_the_delivery_stub_binds_the_code_pack_and_delivery_shape(self):
        text = (ERRAND / "00-deliver.md").read_text(encoding="utf-8")
        data = tickets._parse_frontmatter(text)
        self.assertEqual("orch-code-pack", data["pack"])
        self.assertEqual([], data["depends_on"])
        self.assertIn("{{simple_task}}", text)
        self.assertIn("{{executor}}", text)
        self.assertIn("{{bound}}", text)
        self.assertIn("{{oracle_command}}", text)


if __name__ == "__main__":
    unittest.main()
