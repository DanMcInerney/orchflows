"""The Constitution's amended principles, and the two pointers to it.

`docs/library-review.md`'s Constitution is the only place the library
states what every sentence in it must be required by, and until this
run no file outside it named it at all: an agent writing library text
could finish without meeting it. Pinned here are the three principles
this run amended -- 6 trimmed to the value it buys, 8 in the trunk form
that keeps domain out of control flow, and the new scaffolding
principle that decides when a guard expires -- and the two pointers
that put the file on the write-time path.

Anchors, not sentences
(`packs/orch-code-pack/references/craft.md`): each principle is read by
its number under the `## Constitution` heading, each pointer by its
file's own heading, and every check is shown failing against a copy
with the fact dropped and the anchor left standing. The can-fail
direction (`rules/verification.md` rule 8) mutates text in memory,
never the tree.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REVIEW = ROOT / "docs" / "library-review.md"
AGENTS = ROOT / "AGENTS.md"
DOCUMENTATION = ROOT / "docs" / "documentation.md"

CONSTITUTION = "## Constitution"
BOOTSTRAP = "## 6. Bootstrap"
# A numbered constitution entry; continuation lines are indented.
ENTRY_RE = re.compile(r"^(\d+)\.\s+(.*)$")

# What each amended principle must carry, and what its amendment took
# out. The fact, not the wording: principle 6 keeps the three forces
# that alone justify buying coordination and stops naming the rule
# downstream of it, and principle 8 states the domain-blindness itself
# instead of the pack-cell mechanism that happens to implement it here.
REQUIRED = {
    6: ("parallelism", "isolation", "durability"),
    8: ("domain-blind", "data", "control flow"),
}
REMOVED = {
    6: ("topology",),
    8: ("pack cell",),
}

# The scaffolding principle's three facts: what expires, what does not,
# and the test that separates them.
SCAFFOLDING = ("scaffolding", "expire", "incentive", "permanent", "perfect executor")

# The principle block was 20 lines at the baseline this run amended
# (808a038). The amendment is licensed as net near-zero, so the block
# is held to that count plus the drift a three-line principle costs;
# anything past it is accretion the report contract would have to
# defend.
BASELINE_LINES = 20
NEAR_ZERO = 3


def constitution_block(text):
    """The raw numbered lines under the Constitution heading."""

    body = text.split(CONSTITUTION, 1)[-1].split("\n## ", 1)[0]
    lines = []
    for line in body.splitlines():
        if ENTRY_RE.match(line):
            lines.append(line)
        elif lines and line[:1] == " " and line.strip():
            lines.append(line)
        elif lines:
            break
    return lines


def principles(text):
    """Each principle by its number, flattened to one line."""

    numbered = {}
    current = None
    for line in constitution_block(text):
        match = ENTRY_RE.match(line)
        if match:
            current = int(match.group(1))
            numbered[current] = match.group(2)
        else:
            numbered[current] += " " + line.strip()
    return {n: re.sub(r"\s+", " ", body) for n, body in numbered.items()}


def principle_lines(text, number):
    """One principle's raw lines, for building a wrong copy beside the tree."""

    lines = constitution_block(text)
    starts = [
        index
        for index, line in enumerate(lines)
        if ENTRY_RE.match(line) and int(ENTRY_RE.match(line).group(1)) == number
    ]
    if not starts:
        return None
    end = starts[0] + 1
    while end < len(lines) and not ENTRY_RE.match(lines[end]):
        end += 1
    return "\n".join(lines[starts[0]:end])


def scaffolding_principle(text):
    """The principle stating when a guard expires, or None."""

    for body in principles(text).values():
        if "scaffolding" in body.lower():
            return body.lower()
    return None


def missing_facts(text):
    """Every amended principle's fact the Constitution no longer carries."""

    numbered = principles(text)
    missing = []
    for number, phrases in sorted(REQUIRED.items()):
        body = numbered.get(number, "").lower()
        missing.extend(
            "{0}: {1}".format(number, phrase)
            for phrase in phrases
            if phrase not in body
        )
    for number, phrases in sorted(REMOVED.items()):
        body = numbered.get(number, "").lower()
        missing.extend(
            "{0}: still names {1}".format(number, phrase)
            for phrase in phrases
            if phrase in body
        )
    scaffolding = scaffolding_principle(text)
    if scaffolding is None:
        missing.append("scaffolding: absent")
    else:
        missing.extend(
            "scaffolding: {0}".format(phrase)
            for phrase in SCAFFOLDING
            if phrase not in scaffolding
        )
    return missing


def section(text, heading):
    """One section's body, flattened, by its heading anchor."""

    return re.sub(r"\s+", " ", text.split(heading, 1)[-1].split("\n## ", 1)[0])


def preamble(text):
    """AGENTS.md's write-time path: what precedes its first heading."""

    return text.split("\n## ", 1)[0]


def missing_pointers(agents_text, documentation_text):
    """Every anchor a write-time surface no longer carries.

    Both pointer checks and their can-fail mutant read through this one
    reader, so a surface mutated beside the tree is answered by exactly
    the code the green checks trust.
    """

    surfaces = (
        (
            "AGENTS.md",
            preamble(agents_text),
            ("docs/library-review.md", "constitution"),
        ),
        (
            "docs/documentation.md 6",
            section(documentation_text, BOOTSTRAP),
            ("library-review.md", "constitution"),
        ),
    )
    missing = []
    for label, body, anchors in surfaces:
        missing.extend(
            "{0}: {1}".format(label, anchor)
            for anchor in anchors
            if anchor not in body.lower()
        )
    return missing


class AmendedPrinciplesTest(unittest.TestCase):
    """The Constitution carries the three amended principles."""

    def setUp(self):
        self.text = REVIEW.read_text(encoding="utf-8")

    def test_the_constitution_carries_every_amended_fact(self):
        self.assertEqual([], missing_facts(self.text))

    def test_the_trimmed_clause_returning_fails_the_check(self):
        """The can-fail direction restores principle 6's trailing clause."""

        restored = self.text.replace(
            "durability forces it.",
            "durability forces it — the value\n   "
            "[rules/topology.md](../rules/topology.md) rule 2's intake serves.",
        )
        self.assertIn("rule 2's intake serves", restored)
        self.assertEqual(["6: still names topology"], missing_facts(restored))

    def test_principle_8_naming_the_mechanism_fails_the_check(self):
        """The can-fail direction restores the pack-cell wording."""

        superseded = self.text.replace(
            principle_lines(self.text, 8),
            "8. Generic bodies are domain-blind; domain deviations live in pack\n   cells.",
        )
        self.assertIn("live in pack cells", principles(superseded)[8])
        self.assertEqual(
            ["8: data", "8: control flow", "8: still names pack cell"],
            missing_facts(superseded),
        )

    def test_dropping_any_scaffolding_fact_fails_the_check(self):
        """The can-fail direction blanks one fact of the new principle."""

        for phrase in SCAFFOLDING:
            with self.subTest(phrase=phrase):
                without = re.sub(re.escape(phrase), "—", self.text, flags=re.IGNORECASE)
                self.assertNotIn(phrase, without.lower())
                # Blanking the word the principle is found by hides the
                # whole principle, which is the same fact lost.
                expected = "absent" if phrase == "scaffolding" else phrase
                self.assertIn("scaffolding: " + expected, missing_facts(without))


class NetLinesTest(unittest.TestCase):
    """The amendment stays inside the near-zero line budget it claimed."""

    def setUp(self):
        self.text = REVIEW.read_text(encoding="utf-8")
        self.lines = constitution_block(self.text)

    def test_every_principle_is_numbered_without_a_gap(self):
        """The reader parses the block; a gap would silence a check."""

        numbered = principles(self.text)
        self.assertEqual(list(range(1, len(numbered) + 1)), sorted(numbered))

    def test_the_block_stays_inside_the_near_zero_budget(self):
        self.assertLessEqual(len(self.lines), BASELINE_LINES + NEAR_ZERO)

    def test_padding_a_copy_past_the_budget_fails_the_check(self):
        over = BASELINE_LINES + NEAR_ZERO - len(self.lines) + 1
        padded = self.text.replace(
            "\n\n## Report contract", "\n   pad" * over + "\n\n## Report contract"
        )
        self.assertGreater(len(constitution_block(padded)), BASELINE_LINES + NEAR_ZERO)


class WriteTimePointerTest(unittest.TestCase):
    """Both write-time surfaces name the Constitution."""

    def setUp(self):
        self.agents = AGENTS.read_text(encoding="utf-8")
        self.documentation = DOCUMENTATION.read_text(encoding="utf-8")

    def missing_for(self, label):
        """One surface's missing anchors, off the shared reader."""

        return [
            entry
            for entry in missing_pointers(self.agents, self.documentation)
            if entry.startswith(label + ":")
        ]

    def test_agents_md_points_at_the_constitution(self):
        """The standards owner an agent loads before writing names it."""

        self.assertEqual([], self.missing_for("AGENTS.md"))

    def test_documentation_lists_it_among_the_day_zero_artifacts(self):
        self.assertEqual([], self.missing_for("docs/documentation.md 6"))

    def test_a_copy_without_either_pointer_fails_the_check(self):
        """The can-fail direction drops the path from each surface.

        Asserting only that a deleted substring is gone would hold
        against any text at all -- this repository included, before
        either pointer existed. The mutant is answered by
        `missing_pointers`, the same reader both checks above assert
        through, so a reader that stopped seeing a surface fails here.
        """

        self.assertEqual([], missing_pointers(self.agents, self.documentation))
        blinded = self.agents.replace("docs/library-review.md", "")
        self.assertEqual(
            ["AGENTS.md: docs/library-review.md"],
            missing_pointers(blinded, self.documentation),
        )
        dropped = self.documentation.replace("library-review.md", "")
        self.assertEqual(
            ["docs/documentation.md 6: library-review.md"],
            missing_pointers(self.agents, dropped),
        )
        self.assertEqual(
            [
                "AGENTS.md: docs/library-review.md",
                "docs/documentation.md 6: library-review.md",
            ],
            missing_pointers(blinded, dropped),
        )


if __name__ == "__main__":
    unittest.main()
