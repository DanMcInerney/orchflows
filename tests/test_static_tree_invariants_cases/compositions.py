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
                "00-acquire": "orch-decompose",
                "01-design": "orch-eval-design",
                "02-materialize": "orch-decompose",
                "03-qualify": "orch-decompose",
                "04-audit": "orch-critique",
                "05-measure": "orch-verify",
            },
            "05-measure",
        ),
        "drift-canary": (
            {"00-run": "orch-frontier", "01-diff": "orch-verify"},
            "01-diff",
        ),
        "renovate": (
            {
                "00-audit": "orch-critique",
                "01-triage": "orch-triage",
                "02-deliver": "orch-decompose",
            },
            "02-deliver",
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
