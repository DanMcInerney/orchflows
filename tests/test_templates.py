"""Shipped compositions expose explicit superseded-executor refusals."""
import unittest
from pathlib import Path
from scripts import tickets

ROOT = Path(__file__).resolve().parents[1]


class TemplateTest(unittest.TestCase):
    def test_all_routed_compositions_have_current_ticket_shape(self):
        findings = []
        for directory in sorted((ROOT / "compositions").iterdir()):
            if directory.is_dir() and directory.name != "references":
                findings.extend((str(path.relative_to(ROOT)), message) for path, message in tickets.template_defects(directory))
        self.assertTrue(findings)
        self.assertTrue(
            all("executor-unregistered:" in message for _path, message in findings),
            findings,
        )
