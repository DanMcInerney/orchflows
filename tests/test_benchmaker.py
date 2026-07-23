"""Contract checks for the project-scoped benchmaker workflow."""

import re
import unittest
from pathlib import Path, PureWindowsPath


ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / ".orchflows" / "skills" / "benchmaker" / "SKILL.md"
PROTOCOL = SKILL.parent / "references" / "protocol.md"
ADAPTER = ROOT / ".claude" / "skills" / "benchmaker" / "SKILL.md"


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Parse the flat frontmatter shape used by orchflows skill files."""
    opening, frontmatter, body = text.split("---", 2)
    if opening:
        raise AssertionError("frontmatter must start at byte zero")
    fields = {}
    for line in frontmatter.strip().splitlines():
        key, value = line.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields, body.lstrip("\r\n")


class TestBenchmakerSurface(unittest.TestCase):
    def test_project_scoped_entrypoints_are_discoverable_and_well_formed(self):
        for path in (SKILL, PROTOCOL, ADAPTER):
            self.assertTrue(path.is_file(), f"missing project entrypoint: {path}")

        fields, body = split_frontmatter(SKILL.read_text(encoding="utf-8"))
        self.assertEqual("benchmaker", fields["name"])
        self.assertEqual("none", fields["role"])
        self.assertLessEqual(len(fields["description"]), 140)
        self.assertLess(body.index("Require:"), body.index("Never:"))
        self.assertLess(body.index("Never:"), body.index("Return:"))
        self.assertLessEqual(len([line for line in body.splitlines() if line.strip()]), 40)
        self.assertEqual(
            {"orch-bench", "orch-deliver", "orch-spec"},
            set(re.findall(r"`(orch-[a-z0-9-]+)`", body)),
        )
        self.assertEqual(1, body.count("[references/protocol.md](references/protocol.md)"))

        adapter_fields, adapter_body = split_frontmatter(ADAPTER.read_text(encoding="utf-8"))
        self.assertEqual({"name", "description"}, set(adapter_fields))
        self.assertEqual("benchmaker", adapter_fields["name"])
        owner_include = adapter_body.strip()
        self.assertTrue(owner_include.startswith("@"))
        owner_path = PureWindowsPath(owner_include[1:])
        self.assertTrue(owner_path.is_absolute())
        self.assertEqual(
            (".orchflows", "skills", "benchmaker", "SKILL.md"),
            owner_path.parts[-4:],
        )

        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        routing_line = (
            "- `benchmaker`: build and qualify one benchmark suite; "
            "read `.orchflows/skills/benchmaker/SKILL.md`."
        )
        self.assertEqual(1, agents.count(routing_line))


if __name__ == "__main__":
    unittest.main()
