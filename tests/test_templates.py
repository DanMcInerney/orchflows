"""Every shipped composition is admitted by the callable ticket registry."""
import unittest
import os
import tempfile
from pathlib import Path
from scripts import tickets

ROOT = Path(__file__).resolve().parents[1]


class TemplateTest(unittest.TestCase):
    def test_all_routed_compositions_have_current_ticket_shape(self):
        findings = []
        for directory in sorted((ROOT / "example-workflows").iterdir()):
            if directory.is_dir() and directory.name != "references":
                if not (directory / tickets.TEMPLATE_FILE).is_file():
                    continue
                findings.extend((str(path.relative_to(ROOT)), message) for path, message in tickets.template_defects(directory))
        self.assertEqual([], findings)

    def test_every_routed_composition_instantiates(self):
        values = {
            "bound": "<= 30 tool calls",
            "audit_bound": "<= 30 tool calls",
            "brief_bound": "<= 30 tool calls",
            "pack": "orch-code-pack",
            "workspace": "workspace",
        }
        with tempfile.TemporaryDirectory() as state:
            previous = os.environ.get(tickets.state_root.ENV_VAR)
            os.environ[tickets.state_root.ENV_VAR] = state
            try:
                for directory in sorted((ROOT / "example-workflows").iterdir()):
                    if not directory.is_dir() or directory.name == "references":
                        continue
                    if not (directory / tickets.TEMPLATE_FILE).is_file():
                        continue
                    manifest = tickets._parse_frontmatter(
                        (directory / tickets.TEMPLATE_FILE).read_text(encoding="utf-8")
                    )
                    args = [str(directory), "--run", f"admission-{directory.name}"]
                    for placeholder in manifest.get("placeholders", []):
                        args.extend(("--set", f"{placeholder}={values.get(placeholder, 'value')}"))
                    with self.subTest(composition=directory.name):
                        result = tickets._cmd_instantiate(args)
                        self.assertNotIn("error", result, result)
            finally:
                if previous is None:
                    os.environ.pop(tickets.state_root.ENV_VAR, None)
                else:
                    os.environ[tickets.state_root.ENV_VAR] = previous
