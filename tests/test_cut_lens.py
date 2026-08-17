"""The cut lens and cutcheck's defect families answer for each other.

`skills/kernel/orch-decompose/references/cut-lens.md` says what a critique
over an issued ticket set looks for; `scripts/cutcheck.py` says what the tool
decides. Only a reader noticing held the two together, so a family the checker
gained or lost changed nothing in the lens, and five families standing in for
six was silent.

The lens sits with the cutter: `orch-decompose` issues the set, runs the
checker, and repairs what it reports, so the judgments the checker cannot
decide are the same package's to state.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LENS = ROOT / "skills" / "kernel" / "orch-decompose" / "references" / "cut-lens.md"
CHECKER_PATH = "scripts/cutcheck.py"
CHECKER = ROOT / CHECKER_PATH

# Every finding the checker reports carries one of these labels, so a family it
# decides is a label its source states. What each family is stays the checker's
# module docstring to own; the label is all the lens needs to name one.
CHECKER_FAMILY_RE = re.compile(r'"(family \d+)"')
LENS_FAMILY_RE = re.compile(r"\bfamily \d+\b")
DELEGATED = "## Delegated"
KEPT = "## Kept"
NO_DIVISION = "the lens states no {} / {} division".format(DELEGATED, KEPT)
UNCLAIMED = "the checker defines {}, which the lens neither delegates nor keeps"
UNDEFINED = "the lens delegates {}, which the checker does not define"


def checker_families(source):
    """Every defect family the checker's source defines."""

    return set(CHECKER_FAMILY_RE.findall(source))


def lens_division(lens):
    """The lens's two halves: what it delegates, and what it keeps.

    A half that is not there is the defect itself -- a lens that never says
    which side a family falls on can be guarded on neither.
    """

    if DELEGATED not in lens or KEPT not in lens:
        return None
    delegated, _, kept = lens.partition(KEPT)
    return delegated.partition(DELEGATED)[2], kept


def correspondence(lens, source):
    """Every way the lens and the checker fail to answer for each other."""

    division = lens_division(lens)
    if division is None:
        return [NO_DIVISION]
    delegated = set(LENS_FAMILY_RE.findall(division[0]))
    kept = set(LENS_FAMILY_RE.findall(division[1]))
    families = checker_families(source)
    return [
        UNDEFINED.format(family) for family in sorted(delegated - families)
    ] + [
        UNCLAIMED.format(family)
        for family in sorted(families - delegated - kept)
    ]


# The judgments the kept half owes beyond the correspondence above. `graph` is
# the checker block a false edge is read from -- a block name, not a family
# label, so naming it here cannot widen the correspondence.
FALSE_EDGE = "false edge"
COMPOUND_ITEM = "compound item"
GRAPH_BLOCK = "graph"
KEPT_JUDGMENTS = (FALSE_EDGE, COMPOUND_ITEM)
ABSENT = "the kept half names no {} judgment"
UNREAD = "the {} judgment names no `{}` block to read it from"


def kept_judgments(kept):
    """Each judgment the kept half states, by name, with its body joined.

    A bullet runs to the first line that is neither its own nor a continuation
    of it, so the copy recipe standing under its own heading below is never
    read as one.
    """

    judgments = {}
    name = None
    for line in kept.splitlines():
        if line.startswith("- "):
            name, _, body = line[2:].partition(":")
            name = name.strip()
            judgments[name] = body.strip()
        elif name and line.startswith("  ") and line.strip():
            judgments[name] = "{} {}".format(judgments[name], line.strip())
        else:
            name = None
    return judgments


def missing_judgments(lens):
    """Every judgment the kept half owes and does not state."""

    division = lens_division(lens)
    if division is None:
        return [NO_DIVISION]
    judgments = kept_judgments(division[1])
    missing = [
        ABSENT.format(name) for name in KEPT_JUDGMENTS if name not in judgments
    ]
    edge = judgments.get(FALSE_EDGE)
    if edge is not None and "`{}`".format(GRAPH_BLOCK) not in edge:
        missing.append(UNREAD.format(FALSE_EDGE, GRAPH_BLOCK))
    return missing


def without_judgment(lens, name):
    """The lens with one kept judgment dropped -- bullet and continuations.

    The wrong result each pin fails against drops the judgment, never only the
    name it is anchored on: a lens still stating the judgment under a renamed
    anchor would prove the search, not the fact.
    """

    return re.sub(
        r"^- {}:.*\n(?:  \S.*\n)*".format(re.escape(name)), "", lens, flags=re.M
    )


class FamilyCorrespondenceTest(unittest.TestCase):
    def setUp(self):
        self.lens = LENS.read_text(encoding="utf-8")
        self.source = CHECKER.read_text(encoding="utf-8")
        self.families = sorted(checker_families(self.source))
        self.assertTrue(self.families, "the checker defines no family to guard")

    def test_lens_and_checker_answer_for_each_other(self):
        self.assertEqual([], correspondence(self.lens, self.source))

    def test_a_family_the_lens_stops_naming_is_reported(self):
        dropped = self.families[-1]
        five_for_six = self.lens.replace(dropped, "")
        self.assertEqual(
            [UNCLAIMED.format(dropped)], correspondence(five_for_six, self.source)
        )

    def test_a_family_the_checker_drops_is_reported(self):
        dropped = self.families[-1]
        without = re.sub(
            r"^.*{}.*\n".format(re.escape(dropped)), "", self.source, flags=re.M
        )
        self.assertEqual(
            [UNDEFINED.format(dropped)], correspondence(self.lens, without)
        )

    def test_a_family_the_lens_keeps_for_itself_is_no_defect(self):
        kept = self.families[-1]
        moved = self.lens.replace(kept, "").replace(
            KEPT,
            "{}\n\n- {}: judged by reading, never by the tool.".format(KEPT, kept),
        )
        self.assertEqual([], correspondence(moved, self.source))


class DelegationStatedTest(unittest.TestCase):
    """The division the correspondence is read from is stated, not inferred."""

    def setUp(self):
        self.lens = LENS.read_text(encoding="utf-8")
        self.division = lens_division(self.lens)
        self.assertIsNotNone(self.division, NO_DIVISION)

    def test_the_delegated_half_names_the_tool_and_the_families(self):
        delegated = self.division[0]
        self.assertIn(CHECKER_PATH, delegated)
        self.assertTrue(LENS_FAMILY_RE.findall(delegated))

    def test_the_kept_half_names_the_judgments_it_keeps(self):
        judgments = [
            line for line in self.division[1].splitlines() if line.startswith("- ")
        ]
        self.assertTrue(judgments)
        for judgment in judgments:
            self.assertIn(":", judgment)

    def test_a_lens_stating_no_division_is_reported(self):
        source = CHECKER.read_text(encoding="utf-8")
        self.assertEqual(
            [NO_DIVISION], correspondence(self.lens.replace(DELEGATED, ""), source)
        )


class GraphJudgmentsTest(unittest.TestCase):
    """The kept half names the judgments no checker report reaches.

    The checker decides its families over fields each item states about
    itself. An edge nothing justifies is not one of them -- it is read across
    the set, from the checker's own `graph` block beside each item's oracles
    and fixed inputs -- and neither is an item that is two atoms, which every
    field it states is consistent with.
    """

    def setUp(self):
        self.lens = LENS.read_text(encoding="utf-8")

    def test_the_kept_half_names_the_false_edge_and_the_compound_item(self):
        self.assertEqual([], missing_judgments(self.lens))

    def test_a_judgment_the_lens_drops_is_reported(self):
        for name in KEPT_JUDGMENTS:
            with self.subTest(judgment=name):
                dropped = without_judgment(self.lens, name)
                self.assertNotEqual(self.lens, dropped, "nothing was dropped")
                self.assertEqual([ABSENT.format(name)], missing_judgments(dropped))

    def test_a_false_edge_with_no_block_behind_it_is_reported(self):
        unread = without_judgment(self.lens, FALSE_EDGE).replace(
            KEPT, "{}\n\n- {}: an edge nothing justifies.".format(KEPT, FALSE_EDGE)
        )
        self.assertEqual(
            [UNREAD.format(FALSE_EDGE, GRAPH_BLOCK)], missing_judgments(unread)
        )


if __name__ == "__main__":
    unittest.main()
