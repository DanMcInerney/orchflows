"""Static contract checks for super-research preparation."""

from pathlib import Path
import re
import unittest


SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"


def preparation_violations(text: str):
    """Return missing or malformed preparation obligations."""

    match = re.search(
        r"^Preparation, in order:\s*$\n(?P<steps>.*?)(?=\n\n\S)",
        text,
        flags=re.MULTILINE | re.DOTALL,
    )
    if match is None:
        return ("ordered preparation block",)

    steps = match.group("steps")
    numbered = {
        int(number): body
        for number, body in re.findall(
            r"^(\d+)\.\s+(.*?)(?=^\d+\.\s+|\Z)",
            steps,
            flags=re.MULTILINE | re.DOTALL,
        )
    }
    violations = []
    if tuple(numbered) != (1, 2, 3, 4):
        violations.append("four ordered steps")
        return tuple(violations)

    normalized = {
        number: " ".join(body.lower().split()) for number, body in numbered.items()
    }
    required = {
        1: (
            "references/protocol.md",
            "alone",
            "first unread byte",
            "eof",
        ),
        2: (
            "paginated",
            "truncated",
            "same file",
            "next unread offset",
            "do not open another reference",
        ),
        3: (
            "only after protocol eof",
            "references/operating.md",
            "alone",
            "eof",
            "same way",
        ),
        4: (
            "only after both eofs",
            "write a manifest",
            "begin acquisition",
            "combined/multi-file read",
            "never satisfies either eof obligation",
        ),
    }
    for number, fragments in required.items():
        missing = tuple(fragment for fragment in fragments if fragment not in normalized[number])
        if missing:
            violations.append(f"step {number}: {', '.join(missing)}")
    return tuple(violations)


VALID_CONTRACT = """\
Preparation, in order:
1. Read [references/protocol.md](references/protocol.md) alone from its first unread byte through EOF.
2. If the response is paginated or truncated, continue that same file from the next unread offset. Do not open another reference yet.
3. Only after protocol EOF, read [references/operating.md](references/operating.md) alone through EOF, continuing it the same way if necessary.
4. Only after both EOFs may the executor write a manifest or begin acquisition. A combined/multi-file read never satisfies either EOF obligation.

Put this item's scripts on PYTHONPATH.
"""


class SkillPreparationContractTests(unittest.TestCase):
    def test_accepts_complete_contract(self):
        self.assertEqual((), preparation_violations(VALID_CONTRACT))

    def test_project_skill_has_serial_eof_preparation_contract(self):
        self.assertEqual((), preparation_violations(SKILL.read_text(encoding="utf-8")))

    def test_rejects_reversed_references(self):
        reversed_contract = VALID_CONTRACT.replace(
            "[references/protocol.md](references/protocol.md)", "[references/SWAP.md](references/SWAP.md)"
        ).replace(
            "[references/operating.md](references/operating.md)",
            "[references/protocol.md](references/protocol.md)",
        ).replace(
            "[references/SWAP.md](references/SWAP.md)",
            "[references/operating.md](references/operating.md)",
        )
        self.assertTrue(preparation_violations(reversed_contract))

    def test_rejects_combined_read(self):
        combined = VALID_CONTRACT.replace(
            "A combined/multi-file read never satisfies either EOF obligation.",
            "A combined/multi-file read satisfies both EOF obligations.",
        )
        self.assertTrue(preparation_violations(combined))

    def test_rejects_incomplete_continuation(self):
        incomplete = VALID_CONTRACT.replace(" from the next unread offset", "")
        self.assertTrue(preparation_violations(incomplete))

    def test_rejects_early_acquisition(self):
        early = VALID_CONTRACT.replace("Only after both EOFs", "Only after protocol EOF")
        self.assertTrue(preparation_violations(early))


if __name__ == "__main__":
    unittest.main()
