"""`checkpointed-build`'s prose says what its caller has to be handed.

The validator already grades the body as a workflow -- name, description,
manual-only flag, the 450-word tier budget, Require/Never/Return anatomy.
None of that reads what the steps *say*, and a workflow's steps are its
whole contract: a driver runs this prose, so a call line that lost
`--isolation required`, or a Return that stopped naming the `probe` its
frame closes on, would leave the body validating and the run wrong. What
the frame law itself prints -- relaying the returned lines, closing outside
the children -- is the trunk's to say and is pinned nowhere here.

Anchors, not sentences (`packs/orch-code-pack/references/craft.md`): each
fact is read inside a span the body's own structure marks -- the `Require:`
paragraph, one bolded step, the `Never:` paragraph, the `Return` paragraph
-- and each case is shown failing against an in-memory copy with the fact
dropped and the span left standing, so a wrong result drops the fact rather
than the anchor. Nothing here mutates the tree.
"""

from __future__ import annotations

import re
import unittest

from tests._repo_root import ROOT

BODY_PATH = ROOT / "skills" / "workflows" / "checkpointed-build" / "SKILL.md"

# Where one span ends: the next bolded step label, or the closing
# Never/Return paragraphs. Read off the body's own punctuation rather than
# a line count, so rewrapping the prose moves nothing.
SPAN_ENDS = ("**Plan**", "**Waves**", "**Judge**", "Never:", "Return:")


def flat(text: str) -> str:
    """One-line form, so a fact survives however its owner rewraps."""

    return " ".join(text.split())


def span(text: str, opener: str) -> str:
    """The body from ``opener`` up to the next span opener, or the end."""

    start = text.find(opener)
    if start < 0:
        return ""
    rest = text[start + len(opener):]
    ends = [rest.find(end) for end in SPAN_ENDS if rest.find(end) > 0]
    return rest if not ends else rest[: min(ends)]


# label -> (span opener, the facts that span must carry).
CASES = {
    "Require names every input the caller supplies": (
        "Require:",
        ("`goal`", "`pack`", "`judge-pack`", "`sheets`", "`[]` when none",
         "`probe`", "`bound`", "`workspace`"),
    ),
    "the plan step makes a cut and pins the dependency set": (
        "**Plan**",
        ("--makes cut", "The first wave pins the artifact's dependency set",
         "reports the addition as a deviation"),
    ),
    "each wave is isolated, stamped, and fanned out": (
        "**Waves**",
        ("--isolation required", "--sheet <sheet> [--sheet ...]",
         "--workspace <workspace>", "*fan-out*"),
    ),
    "the judge reads the joined tip under the same sheets": (
        "**Judge**",
        ("--pack <judge-pack>", "--sheet <sheet> [--sheet ...]",
         "--artifacts git:<tip>", "*bounded-repair*"),
    ),
    "Never forbids the shared tree, the unstamped judge and the inside close": (
        "Never:",
        ("make in a shared tree", "hand the judge a sheet the waves did not carry",
         "a candidate rather than the joined tip", "*outside-close*"),
    ),
    "Return closes on the probe over the joined tip": (
        "Return:",
        ("frame-close <run> <frame> --done <probe>", "joined tip",
         "artifact: git:<tip>"),
    ),
}


def drop(text: str, fact: str):
    """``text`` with every occurrence of ``fact`` removed, wrapping and all,
    and how many went. Matched across whatever whitespace currently
    separates the words, so the owner rewraps freely."""

    pattern = re.compile(r"\s+".join(re.escape(word) for word in fact.split()))
    return pattern.subn("", text)


def holds(text: str, opener: str, facts) -> bool:
    body = flat(span(text, opener))
    return bool(body) and all(flat(fact) in body for fact in facts)


class CheckpointedBuildBodyTest(unittest.TestCase):
    """Every fact the unit's Goal fixed is in the step that owns it."""

    def body(self) -> str:
        return BODY_PATH.read_text(encoding="utf-8")

    def test_each_step_carries_the_facts_its_caller_needs(self):
        text = self.body()
        missing = []
        for label, (opener, facts) in CASES.items():
            self.assertTrue(flat(span(text, opener)), f"{label}: no {opener} span")
            missing += [
                f"{label}: the {opener} span lacks {fact!r}"
                for fact in facts if flat(fact) not in flat(span(text, opener))
            ]
        self.assertEqual([], missing, "; ".join(missing))

    def test_dropping_any_fact_fails_the_check_with_the_span_standing(self):
        text = self.body()
        for label, (opener, facts) in CASES.items():
            for fact in facts:
                with self.subTest(label=label, fact=fact):
                    mutant, hits = drop(text, fact)
                    self.assertGreaterEqual(hits, 1, "the fact is absent")
                    self.assertTrue(
                        flat(span(mutant, opener)),
                        "the mutation took the span, so the check would only "
                        "prove the grep",
                    )
                    self.assertFalse(holds(mutant, opener, facts))


if __name__ == "__main__":
    unittest.main()
