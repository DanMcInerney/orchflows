"""ARCHITECTURE.md names this run's three new repository tools.

A tool nobody can find is a tool the next agent rebuilds. The cold
ownership map is where an executing agent looks for who owns what, so each
new `tools/` program earns one sentence there naming the responsibility it
owns -- and the map stays inside the ceiling it states for itself, since a
map that grows without bound stops being read.

Both directions are graded here. The can-fail direction (rules/verification
Section 8) mutates a copy of the text in memory, never the tree.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARCHITECTURE = ROOT / "ARCHITECTURE.md"

# The section an executing agent reads for cross-cutting ownership.
SECTION = "## Cross-cutting owners"
# `tools/validate_support/common.py`'s counter: a markdown link target is
# stripped before the split, so a citation costs its label, not its path.
LINK_TARGET_RE = re.compile(r"\]\([^)]*\)")
# A `tools/<name>.py` ownership clause, up to the sentence or clause end.
OWNERSHIP_CLAUSE = re.compile(r"`tools/([^`]+\.py)`\]? owns ([^;.]+)")
# The map states its own ceiling; nothing else in the tree states it, so the
# number a reader is held to is the number the file carries.
CEILING_RE = re.compile(r"Ceiling: (\d+) whitespace-delimited words")

# The three tools this run added, and the words each sentence must carry.
# The responsibility, not the wording: what is pinned is that the map says
# what the program is for, and each phrase below is the fact a reader who
# has never opened the file needs in order to route to it.
NEW_TOOLS = {
    "run_required.py": ("required-check run", "verdict cache"),
    "affected_tests.py": ("write-scope-to-test-module derivation",),
    "run_report.py": ("retrospective speed report",),
}


def cross_cutting_owners(text):
    """The Cross-cutting owners section, flattened, link targets stripped."""

    body = text.split(SECTION, 1)[-1].split("\n## ", 1)[0]
    return LINK_TARGET_RE.sub("]", re.sub(r"\s+", " ", body))


def unnamed_tools(text):
    """The new tools the section does not name with what they own."""

    clauses = dict(OWNERSHIP_CLAUSE.findall(cross_cutting_owners(text)))
    missing = []
    for name, phrases in sorted(NEW_TOOLS.items()):
        owned = clauses.get(name)
        if owned is None or any(phrase not in owned for phrase in phrases):
            missing.append(name)
    return missing


def stated_ceiling(text):
    """The word ceiling the map states for itself, or None."""

    match = CEILING_RE.search(re.sub(r"\s+", " ", text))
    return None if match is None else int(match.group(1))


def counted_words(text):
    """The validator's count: link targets stripped, then a whitespace split."""

    return len(LINK_TARGET_RE.sub("]", text).split())


class StatedCeilingTest(unittest.TestCase):
    """The map holds itself to the ceiling it publishes."""

    def setUp(self):
        self.text = ARCHITECTURE.read_text(encoding="utf-8")
        self.ceiling = stated_ceiling(self.text)

    def test_the_map_states_a_ceiling(self):
        self.assertIsNotNone(self.ceiling, "ARCHITECTURE.md states no ceiling")

    def test_the_map_is_inside_the_ceiling_it_states(self):
        self.assertLessEqual(counted_words(self.text), self.ceiling)

    def test_padding_a_copy_past_the_ceiling_fails_the_check(self):
        """The can-fail direction pads a copy, never the tree."""

        over = self.ceiling - counted_words(self.text) + 1
        padded = self.text + " pad" * over
        self.assertGreater(counted_words(padded), self.ceiling)


class NewToolOwnershipTest(unittest.TestCase):
    """Cross-cutting owners names each new tool by what it owns."""

    def setUp(self):
        self.text = ARCHITECTURE.read_text(encoding="utf-8")

    def test_the_section_names_each_new_tool_with_its_responsibility(self):
        self.assertEqual([], unnamed_tools(self.text))

    def test_dropping_any_one_sentence_fails_the_check(self):
        """The can-fail direction renames one owner per subtest."""

        clauses = dict(OWNERSHIP_CLAUSE.findall(cross_cutting_owners(self.text)))
        for name in sorted(NEW_TOOLS):
            with self.subTest(tool=name):
                self.assertIsNotNone(clauses.get(name), "no clause for " + name)
                wrong = self.text.replace(
                    "`tools/{0}`".format(name), "`tools/absent.py`"
                )
                self.assertNotEqual(self.text, wrong)
                self.assertEqual([name], unnamed_tools(wrong))


if __name__ == "__main__":
    unittest.main()
