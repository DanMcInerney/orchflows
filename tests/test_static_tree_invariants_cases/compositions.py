"""Static invariants owned by composition templates."""
import unittest

from ._support import COMPOSITIONS, LINK_RE, TEMPLATE_FILE, split_document, validate


class TestCompositionLinks(unittest.TestCase):
    """Every local markdown link from a composition resolves."""

    def test_every_composition_link_resolves(self):
        checked = 0
        for path in sorted(COMPOSITIONS.rglob("*.md")):
            for target in LINK_RE.findall(path.read_text(encoding="utf-8")):
                if target.startswith(("http://", "https://", "#", "mailto:")):
                    continue
                checked += 1
                resolved = (path.parent / target.split("#")[0]).resolve()
                with self.subTest(source=path.name, target=target):
                    self.assertTrue(
                        resolved.is_file(),
                        f"{path} cites {target}, which does not exist",
                    )
        self.assertTrue(checked, "found no composition links to resolve")


class TestCompositionTemplates(unittest.TestCase):
    """Composition stubs preserve their executor binding and terminal."""

    TEMPLATES = {
        "benchmaker": (
            {
                "00-acquire": "orch-frontier",
                "01-design": "orch-outline",
                "02-materialize": "orch-execute",
                "03-qualify": "orch-check",
                "04-audit": "orch-check",
                "05-measure": "orch-check",
            },
            "05-measure",
        ),
        "drift-canary": (
            {"00-run": "orch-frontier", "01-diff": "orch-execute"},
            "01-diff",
        ),
        "evolve": (
            {
                "00-eval": "orch-outline",
                "01-eligibility": "orch-check",
                "02-campaign": "orch-execute",
                "03-result": "orch-check",
            },
            "03-result",
        ),
        "renovate": (
            {
                "00-audit": "orch-check",
                "01-triage": "orch-check",
                "02-deliver": "orch-frontier",
            },
            "02-deliver",
        ),
        "self-improve": (
            {"00-mine": "orch-execute", "01-deliver": "orch-frontier"},
            "01-deliver",
        ),
        "skill-tournament": (
            {"00-benchmark": "orch-frontier", "01-campaign": "orch-frontier"},
            "01-campaign",
        ),
    }

    @staticmethod
    def _stubs(name):
        tickets = validate._ticket_law()
        directory = COMPOSITIONS / name
        return {
            path.stem: tickets._parse_frontmatter(
                path.read_text(encoding="utf-8")
            )
            for path in sorted(directory.glob("*.md"))
            if path.name != tickets.TEMPLATE_FILE
        }

    def test_each_template_binds_the_executors_its_composition_named(self):
        for name, (expected, _) in self.TEMPLATES.items():
            with self.subTest(template=name):
                stubs = self._stubs(name)
                self.assertEqual(
                    expected,
                    {stub: fields.get("executor") for stub, fields in stubs.items()},
                )

    def test_no_composition_stub_uses_a_removed_executor(self):
        registered = set(validate._ticket_law().CALLABLE_EXECUTORS)
        for directory in sorted(COMPOSITIONS.iterdir()):
            if not directory.is_dir() or directory.name == "references":
                continue
            with self.subTest(template=directory.name):
                for path in directory.glob("*.md"):
                    if path.name == TEMPLATE_FILE:
                        continue
                    fields = validate._ticket_law()._parse_frontmatter(
                        path.read_text(encoding="utf-8")
                    )
                    self.assertIn(fields.get("executor"), registered, path)

    def test_each_template_ends_at_the_stub_carrying_its_done_check(self):
        for name, (_, terminal) in self.TEMPLATES.items():
            with self.subTest(template=name):
                stubs = self._stubs(name)
                depended = {
                    edge
                    for fields in stubs.values()
                    for edge in fields.get("depends_on", [])
                }
                self.assertEqual({terminal}, set(stubs) - depended)
