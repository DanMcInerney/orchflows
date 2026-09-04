"""The ladder's facts, each read at its one owner's anchor.

The five rungs -- applied skill, sheet, reusable workflow, glue workflow,
idiom -- are stated once each, in the file that owns the fact, and linked
from everywhere else. The failure this pins is placement drift: a fact
restated in a second file agrees with the first until one copy moves, and a
fact deleted from its owner leaves every link pointing at nothing.

Anchors, not sentences (`packs/orch-code-pack/SKILL.md`): each
fact is read inside a stable anchor -- a `##` heading, a numbered clause of a
rules file, a kernel body's Require/Never/Return anatomy -- and every case is
shown failing against an in-memory copy with the fact dropped and the anchor
left standing. Nothing here mutates the tree.
"""

from __future__ import annotations

import re
import unittest

from tests._repo_root import ROOT

# A numbered clause of a rules file: `N. text`, continuations indented.
CLAUSE_RE = re.compile(r"^(\d+)\.\s", re.MULTILINE)
IDIOM_RE = re.compile(r"^- \*\*([a-z-]+)\*\* — (.+?)(?=\n- \*\*|\n\n|\Z)", re.MULTILINE | re.DOTALL)


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


def flat(text: str) -> str:
    """One-line form, so a fact survives however its owner rewraps."""

    return " ".join(text.split())


def section(text: str, heading: str) -> str:
    """The `## heading` block, up to the next `##` heading."""

    start = text.find(heading + "\n")
    if start < 0:
        return ""
    rest = text[start + len(heading):]
    end = rest.find("\n## ")
    return rest if end < 0 else rest[:end]


# The ordered labels `tools/validate.py` requires of every skill body.
ANATOMY = ("Require:", "Never:", "Return:")


def primitive_body(text: str) -> str:
    """A kernel skill's body, and only while its anatomy stands.

    A primitive carries no headings, so the anchor for one is the shape the
    validator already enforces -- the ordered `Require:`, `Never:` and
    `Return:` labels -- which survives every rewording of the prose between
    them. A mutation that took the anatomy would be a different failure.
    """

    body = text.split("---", 2)[-1]
    standing = all(re.search(rf"^{label}", body, re.MULTILINE) for label in ANATOMY)
    return body if standing else ""


def clause(text: str, number: int) -> str:
    """One numbered clause of a rules file, continuations included."""

    matches = list(CLAUSE_RE.finditer(text))
    for index, match in enumerate(matches):
        if int(match.group(1)) != number:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        return text[match.start():end]
    return ""


# label -> (file, anchor kind + key, the facts that anchor must carry).
# The anchor is what survives a mutation; the facts are what the mutation
# drops, so a check whose wrong result is "anchor missing" would only be
# proving the grep.
CASES = {
    "vocabulary defines the five rungs": (
        "docs/vocabulary.md", ("section", "## Structure"),
        ("- **applied skill** —", "- **sheet** —", "- **reusable workflow** —",
         "- **glue workflow** —", "- **idiom** —"),
    ),
    "composition owns the stamping sentence": (
        "rules/composition.md", ("clause", 12),
        ("stamped by the caller", "read only by that ticket's maker and its judge"),
    ),
    "composition owns the recurrence rule": (
        "rules/composition.md", ("clause", 13),
        ("Recurrence.", "recurs across two or more workflows",
         "is a reusable workflow invoked by name", "is an idiom"),
    ),
    "composition owns the placement rule": (
        "rules/composition.md", ("clause", 14),
        ("Placement.", "innermost ring that contains every caller"),
    ),
    "token economy places a standard in the every-dispatch tier": (
        "rules/token-economy.md", ("clause", 11),
        ("every-dispatch units next", "stamped standard as",
         "`BODY_BUDGET`, `STANDARD_BUDGET`"),
    ),
    "architecture places the two directories": (
        "ARCHITECTURE.md", ("section", "## Four tiers"),
        ("`workflows/` the reusable domain-blind workflows", "`sheets/` narrows it"),
    ),
    "pack authoring states the pack-versus-sheet admission": (
        "docs/pack-authoring.md", ("clause", 1),
        ("is a sheet stamped beside that pack", "not a pack"),
    ),
    "authoring names the three dependency classes and their files": (
        "docs/custom-workflow-authoring.md", ("section", "## Dependencies"),
        ("three classes of dependency", "`requirements.txt` beside the item's manifest",
         "`tools.txt` beside the manifest", "`package.json` plus a committed lockfile",
         "The **artifact's** own dependencies are none of those three"),
    ),
    "authoring hands the frame law to the trunk": (
        "docs/custom-workflow-authoring.md", ("section", "## What a workflow is made of"),
        ("`tickets.py frame-open` prints the frame law",),
    ),
    "authoring picks the rung from the four questions": (
        "docs/custom-workflow-authoring.md", ("section", "## Procedure"),
        ("ask the four questions in *Which work earns a callable*",
         "picks the rung"),
    ),
    "design states why sheets and applied skills exist": (
        "DESIGN.md", ("section", "## Why two callables, frames, and prose"),
        ("**Why sheets and applied skills.**",
         "pass the perfect-model test from the other side"),
    ),
    "the maker's kernel binds it to every stamped sheet and to its method": (
        "skills/kernel/orch-do/SKILL.md", ("anatomy", None),
        ("Read whole each sheet the prompt hands you, at the digest it names",
         "relaxes none of them",
         "An applied skill the prompt names supplies the method only",
         "nothing in it loosens the Require, Never or Return here"),
    ),
    "the judge's kernel checks every sheet and reports a loosening": (
        "skills/kernel/orch-judge/SKILL.md", ("anatomy", None),
        ("Every sheet the ticket stamps is checked beside that entry",
         "file that loosening as a `sheet-defect` finding",
         "Where the ticket pins an applied skill, judge by it as method",
         "the Require, Never and Return stated here still govern this review"),
    ),
    "design states why there are three dependency classes": (
        "DESIGN.md", ("section", "## Why custom items live in rings"),
        ("**Why three dependency classes.**", "one environment\n  per item"),
    ),
}


def anchored(text: str, anchor):
    kind, key = anchor
    if kind == "section":
        return section(text, key)
    if kind == "anatomy":
        return primitive_body(text)
    return clause(text, key)


def drop(text: str, fact: str):
    """`text` with the first occurrence of `fact` removed, wrapping and all.

    The owner rewraps its prose freely, so a fact is matched across whatever
    whitespace currently separates its words rather than as a fixed string.
    Every occurrence goes, and the caller asserts there was exactly one: a
    fact spelled twice in one file is already the drift this module pins.
    """

    pattern = re.compile(r"\s+".join(re.escape(word) for word in fact.split()))
    return pattern.subn("", text)


def holds(text: str, anchor, facts) -> bool:
    body = flat(anchored(text, anchor))
    return bool(body) and all(flat(fact) in body for fact in facts)


class LadderFactsTest(unittest.TestCase):
    """Every ladder fact is present at the owner this run gave it."""

    def test_each_fact_is_carried_by_its_owner(self):
        missing = []
        for label, (rel, anchor, facts) in CASES.items():
            body = flat(anchored(read(rel), anchor))
            self.assertTrue(body, f"{label}: anchor {anchor} not found in {rel}")
            missing += [
                f"{label}: {rel} lacks {fact!r}"
                for fact in facts if flat(fact) not in body
            ]
        self.assertEqual([], missing, "; ".join(missing))

    def test_dropping_any_fact_fails_the_check_with_the_anchor_standing(self):
        for label, (rel, anchor, facts) in CASES.items():
            text = read(rel)
            for fact in facts:
                with self.subTest(label=label, fact=fact):
                    mutant, hits = drop(text, fact)
                    self.assertEqual(1, hits, "the fact is absent, or spelled twice")
                    self.assertTrue(
                        flat(anchored(mutant, anchor)),
                        "the mutation took the anchor, so the check would only prove the grep",
                    )
                    self.assertFalse(holds(mutant, anchor, facts))


class RetiredWordingTest(unittest.TestCase):
    """The two sentences this unit replaced are gone, not duplicated."""

    RETIRED = (
        ("docs/custom-workflow-authoring.md", "start from the nearest body"),
        ("docs/custom-workflow-authoring.md", "Write both into the"),
    )

    def test_no_owner_still_carries_the_replaced_wording(self):
        found = [f"{rel}: {phrase!r}" for rel, phrase in self.RETIRED
                 if phrase in read(rel)]
        self.assertEqual([], found, "; ".join(found))


class IdiomsTest(unittest.TestCase):
    """`## Idioms` is the one wording of each recurring sentence."""

    NAMES = ("bounded-repair", "fan-out", "freeze", "declare-gaps", "outside-close")
    WORD_CEILING = 30

    def entries(self):
        body = section(read("docs/custom-workflow-authoring.md"), "## Idioms")
        return {m.group(1): flat(m.group(2)) for m in IDIOM_RE.finditer(body)}

    def test_every_idiom_is_worded_once_under_the_heading(self):
        self.assertEqual(list(self.NAMES), list(self.entries()))

    def test_each_idiom_is_one_sentence_inside_its_ceiling(self):
        over = [f"{name}: {len(text.split())} words"
                for name, text in self.entries().items()
                if len(text.split()) > self.WORD_CEILING]
        self.assertEqual([], over, "; ".join(over))

    def test_a_padded_idiom_fails_the_ceiling_check(self):
        entries = self.entries()
        padded = dict(entries, freeze=entries["freeze"] + " word" * self.WORD_CEILING)
        over = [name for name, text in padded.items()
                if len(text.split()) > self.WORD_CEILING]
        self.assertEqual(["freeze"], over)

    def test_the_recurrence_rule_is_linked_rather_than_restated(self):
        body = flat(section(read("docs/custom-workflow-authoring.md"), "## Idioms"))
        self.assertIn("[composition](../rules/composition.md) §13", body)
        self.assertNotIn("whose run deserves its own journal", body)


if __name__ == "__main__":
    unittest.main()
