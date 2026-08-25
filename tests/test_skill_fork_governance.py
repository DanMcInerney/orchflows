"""The fork-arrival clause: its wording, its price, and what blocks it.

Eighteen times in one run, an executor invoking an orchflows skill by
name spawned a fork that arrived with the contract loaded and no packet,
no ticket, no assigned name -- at every tier: workers, checkers, the
gate critique's own pass. The dispatch packet already carries a refusal
sentence and it structurally cannot reach these agents: a packet-less
fork never reads a packet. The contract is the one document such a fork
provably read, so the contract is where the rule has to live.

What the firings proved, and what `CLAUSE` therefore says:

* The refusal needs no address. The seventeenth firing refused, then
  reasoned that the missing packet also carried the address the refusal
  was owed to, and concluded the coordinator must be a permitted
  fallback. It is not. A fork's final output *is* its return: it reaches
  whoever invoked the skill through the invocation channel itself, the
  way a function's value reaches its caller. There is no addressing act.
* The refusal precedes inspection. The eighteenth firing scavenged run
  state, the full ticket set and the join's ledger before standing down,
  and said so itself: that it stopped before acting "is not a property
  of the procedure, it's luck. The right stopping point was the absent
  packet, before .orch was ever listed." Safety one judgment call deep
  is not safety, so the clause refuses at the packet boundary.
* The fork never scopes itself, for that firing's own reason: deriving
  its own objective would make the check it writes unfalsifiable against
  a spec nobody stamped.
* A name is never invented, and a by-name invocation from inside a
  governed execution forwards the invoker's packet or refuses at spawn.

WHAT THIS MODULE DOES NOT YET DO, stated first so a green run is not
mistaken for the finished invariant: **no skill contract carries the
clause yet, and this module does not sweep for it.** Adoption is blocked
on a budget, and the block is measured rather than asserted --
`ADOPTION_BLOCKED` prices it per contract.

Two facts, both measured at this unit's tip, decide that:

1. rules/token-economy.md 11 caps each tier's body, and tools/validate.py
   enforces it. Four contracts sit at or within three words of their
   ceilings, so the clause does not fit them: orch-frontier is exactly at
   450 of 450. Adding it there means deleting standing law those
   contracts' owners wrote, which is their call and not a sweep's.
2. Adoption is all-or-nothing, which is the counter-intuitive half.
   scripts/doclint.py pairs two texts for duplicate comparison only when
   they share a word carried by no more than `DISTINCTIVE_MAX` texts, and
   skills are compared against each other. Below that threshold the
   clause's own words are distinctive and every pair of carriers is
   reported; above it they are idiom and none is. Measured: the clause in
   all 22 contracts left the cross-tier warning count at 27, unchanged;
   the same clause in 18 contracts raised it to 486, breaching the
   ceiling tests/test_cell_linter.py ratchets. So a partial rollout is
   strictly worse than none, and 21 of the 22 must land together.

`test_the_all_or_nothing_premise_still_holds` pins fact 2, because it is
the fact a later reader would otherwise rediscover by breaking the tree.
The clause, its properties and its price are kept here so that landing it
is one scoped change: free the words in `ADOPTION_BLOCKED`, then sweep.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

#: The fork-arrival clause, verbatim. One constant, one wording, because
#: a paraphrase is how these properties were lost before: a join once
#: relayed a packet clause in its own words and dropped the
#: invented-name half. Properties survive only verbatim transmission.
CLAUSE = (
    "Arriving without a packet, refuse before reading anything: your "
    "refusal is your return, reaching your invoker through the invocation "
    "itself, never the coordinator. Acquire nothing, claim no name, derive "
    "no objective. Invoking a skill by name, forward your packet or refuse."
)

#: What each property is doing there, keyed by the words carrying it. A
#: future editor shortening `CLAUSE` has to drop one of these to do it,
#: and this is the case that says which firing paid for the sentence.
CLAUSE_PROPERTIES = {
    "without a packet": "names the arrival the clause governs",
    "before reading anything": "refusal at the packet boundary, not after a look around",
    "your refusal is your return": "the return channel is the refusal channel",
    "reaching your invoker through the invocation itself": (
        "names the channel, which is the half the seventeenth firing got "
        "wrong: it accepted that the return is the refusal and still looked "
        "for an address to send it to. Unpinned, this span is the one part "
        "of the clause a shortening edit can remove silently"
    ),
    "never the coordinator": "forecloses the seventeenth firing's fallback address",
    "Acquire nothing": "the scavenging half, structural rather than one judgment deep",
    "claim no name": "no invented identity",
    "derive no objective": "a self-scoped fork writes an unfalsifiable check",
    "forward your packet or refuse": "the by-name invocation boundary",
}

#: Wordings this clause must NOT use, and the owner each belongs to.
#: Both say what `CLAUSE` says; both are pinned elsewhere, and reaching
#: for the more natural phrasing would redden a module this change has no
#: business reddening. Recorded so the near-miss stays a decision with a
#: reason rather than a coincidence a later edit undoes.
RESERVED_WORDINGS = {
    "gathers nothing": (
        "rules/delegation.md owns it, and tests/test_verification_owners.py "
        "pins it to exactly one carrier across contracts, rules and skills"
    ),
    "self-invented": (
        "scripts/tickets_packet.py owns it, and tests/test_verification_owners.py "
        "forbids a kernel skill from restating that dispatch part"
    ),
}

#: The contracts the clause does not fit, with the words each owes,
#: measured at this unit's tip. A shortfall recorded, never a licence:
#: a fork loading one of these and no packet is ungoverned, and so is a
#: fork loading any other contract until adoption lands.
#:
#: The set only shrinks. Nothing may join it -- a contract that grew until
#: the clause no longer fit would otherwise exempt itself by getting
#: fatter -- and a contract that frees the words leaves it, because
#: `test_every_blocked_contract_is_still_blocked` fails once one of these
#: can afford the clause.
ADOPTION_BLOCKED = {
    "skills/engines/orch-frontier/SKILL.md": 41,
    "skills/kernel/orch-decompose/SKILL.md": 38,
    "skills/kernel/orch-integrate/SKILL.md": 38,
    "skills/workflows/orch-spec/SKILL.md": 40,
}

#: rules/token-economy.md 11, as tools/validate.py enforces it. Restated
#: rather than imported because this module grades the tree the library
#: ships: if these and validate.py's ever disagree, one of the two is
#: wrong and the disagreement is the thing worth seeing.
BODY_BUDGET = {
    "kernel": 300,
    "instances": 300,
    "utilities": 300,
    "engines": 450,
    "workflows": 450,
}

LINK_TARGET_RE = re.compile(r"\]\([^)]*\)")


def contracts():
    """Every skill contract, derived from the tree rather than listed."""
    return sorted(ROOT.joinpath("skills").glob("*/*/SKILL.md"))


def label(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def body(path: Path) -> str:
    """The contract's body: everything past the frontmatter."""
    text = path.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    return parts[2] if len(parts) > 2 else text


def flat(text: str) -> str:
    """One line, single-spaced -- so a wrapped clause still reads as one."""
    return " ".join(text.split())


def body_words(text: str) -> int:
    """validate.py's counter: words with markdown link targets stripped."""
    return len(LINK_TARGET_RE.sub("]", text).split())


def deficit(path: Path) -> int:
    """Words `path` must free before the clause fits under its ceiling."""
    tier = path.relative_to(ROOT).parts[1]
    return body_words(body(path)) + len(CLAUSE.split()) - BODY_BUDGET[tier]


class TheSweptPopulationIsReal(unittest.TestCase):
    """A sweep over an empty or partial glob proves nothing at all."""

    def test_the_population_is_derived_and_non_empty(self):
        self.assertNotEqual(
            [], contracts(),
            "no skill contract was found under skills/; every sweep in this "
            "module would pass vacuously",
        )

    def test_the_population_spans_every_tier(self):
        tiers = {path.relative_to(ROOT).parts[1] for path in contracts()}
        self.assertEqual(
            set(BODY_BUDGET), tiers,
            "the swept population does not span the library's tiers; a glob "
            "that stopped matching one tier would leave those contracts "
            "unpriced while this module stayed green",
        )


class TheClauseStillSaysWhatItWasWrittenToSay(unittest.TestCase):
    """Guards on the constant itself, which is what adoption will copy."""

    def test_the_clause_states_every_property_the_firings_paid_for(self):
        for token, why in sorted(CLAUSE_PROPERTIES.items()):
            with self.subTest(property=token):
                self.assertIn(
                    token, CLAUSE,
                    f"the fork-arrival clause no longer says {token!r}, which "
                    f"{why}; shortening the clause past a property returns the "
                    "class of firing that property was written against",
                )

    def test_the_clause_leaves_the_reserved_wordings_to_their_owners(self):
        for phrase, owner in sorted(RESERVED_WORDINGS.items()):
            with self.subTest(phrase=phrase):
                self.assertNotIn(
                    phrase, CLAUSE,
                    f"the fork-arrival clause uses {phrase!r}: {owner}. The "
                    "clause says the same thing in words of its own on "
                    "purpose -- restoring the natural phrasing reddens a "
                    "module this change has no business reddening",
                )


class AdoptionIsPricedAndTheBillIsCurrent(unittest.TestCase):
    """What landing the clause costs, per contract, measured not asserted."""

    def test_no_contract_joins_the_blocked_set_by_growing(self):
        unknown = sorted(set(ADOPTION_BLOCKED) - {label(p) for p in contracts()})
        self.assertEqual(
            [], unknown,
            f"{unknown} is recorded as blocked but is not a contract in the "
            "tree; a stale entry prices work against a file nobody reads",
        )

    def test_every_blocked_contract_is_still_blocked(self):
        """Free the words and the entry goes, rather than being banked."""
        for relative in sorted(ADOPTION_BLOCKED):
            with self.subTest(contract=relative):
                self.assertGreater(
                    deficit(ROOT / relative), 0,
                    f"{relative} now has room for the fork-arrival clause. "
                    "Drop the entry and carry the clause: the block was the "
                    "ceiling's, and the ceiling no longer binds this body",
                )

    def test_the_recorded_deficit_is_what_the_tree_actually_owes(self):
        """A stale number is worse than none: it prices the wrong repair."""
        for relative, recorded in sorted(ADOPTION_BLOCKED.items()):
            with self.subTest(contract=relative):
                self.assertEqual(
                    recorded, deficit(ROOT / relative),
                    f"{relative} is recorded as owing {recorded} words and "
                    f"owes {deficit(ROOT / relative)}; whoever reads this "
                    "table to size the repair would size it against a tree "
                    "that moved",
                )

    def test_every_other_contract_can_already_afford_the_clause(self):
        """The blocked set is exactly the blocked ones, so the bill is whole."""
        for path in contracts():
            if label(path) in ADOPTION_BLOCKED:
                continue
            with self.subTest(contract=label(path)):
                self.assertLessEqual(
                    deficit(path), 0,
                    f"{label(path)} cannot afford the clause either and is "
                    f"not priced: it owes {deficit(path)} words. The blocked "
                    "table is what adoption is scoped against, so a contract "
                    "missing from it is work nobody has counted",
                )


class TheAllOrNothingPremiseHolds(unittest.TestCase):
    """Why the clause lands in 21 contracts at once or in none.

    scripts/doclint.py pairs two texts only when they share a word
    carried by no more than DISTINCTIVE_MAX texts, and
    tools/validate_support/duplication.py compares skills against skills.
    A clause in more contracts than that threshold is idiom in every one
    of them and pairs with nothing; a clause in fewer is distinctive and
    reports every pair of its carriers. That is why a partial rollout
    measured 486 cross-tier warnings against a ceiling of 56 while the
    full one measured 27 -- the tree's own baseline, unchanged.
    """

    def test_the_all_or_nothing_premise_still_holds(self):
        from scripts import doclint
        from tools.validate_support import duplication

        self.assertIn(
            "skills", duplication.SAME_TIER_COMPARED,
            "skill bodies are no longer compared against each other, so the "
            "all-or-nothing reasoning above no longer describes this tree",
        )
        self.assertGreater(
            len(contracts()), doclint.DISTINCTIVE_MAX,
            "the library has no more skill contracts than doclint's "
            f"DISTINCTIVE_MAX of {doclint.DISTINCTIVE_MAX}, so even a "
            "complete rollout would leave the clause's words distinctive and "
            "every pair of carriers reported. Adoption would need the "
            "duplication owner's licence rather than this threshold",
        )
        self.assertLessEqual(
            len(contracts()) - len(ADOPTION_BLOCKED), doclint.DISTINCTIVE_MAX,
            "the contracts that can already afford the clause now outnumber "
            f"doclint's DISTINCTIVE_MAX of {doclint.DISTINCTIVE_MAX}, so "
            "landing it in those alone is lint-safe and no longer has to wait "
            "on the blocked four. Re-read the rollout scope before trimming "
            "anything: the all-or-nothing constraint above has lifted",
        )


class TheBudgetTheClauseIsSpentAgainstIsReal(unittest.TestCase):
    """rules/token-economy.md 11: a standing demand buys no width."""

    def test_every_body_stays_within_its_tier_budget(self):
        for path in contracts():
            tier = path.relative_to(ROOT).parts[1]
            count = body_words(body(path))
            with self.subTest(contract=label(path)):
                self.assertLessEqual(
                    count, BODY_BUDGET[tier],
                    f"{label(path)} has {count} words against the {tier} "
                    f"budget of {BODY_BUDGET[tier]}. The fork-arrival clause "
                    "is paid for out of the body, never out of the ceiling",
                )


class SpecStatesItsDirectTicketLane(unittest.TestCase):
    """One executor plus the mandatory join needs no decomposition.

    Five consecutive runs went to landing one direct verifier ticket
    because the contract routed every stamped root through
    orch-decompose. The lane has to be stated, and stated with its
    mechanics: a lane a reader cannot execute is the gap it was written
    to close.
    """

    SPEC = "skills/workflows/orch-spec/SKILL.md"

    def spec_body(self) -> str:
        return flat(body(ROOT / self.SPEC))

    def test_the_direct_lane_names_its_condition_and_its_mechanics(self):
        text = self.spec_body()
        for token, why in (
            ("one executor", "the condition the lane turns on"),
            ("orch-integrate", "the join that owns the outcome's other half"),
            # The bare name appears twice more in this body, so a bare-token
            # assertion passes with the whole lane deleted. Only the lane
            # says it this way, which is what makes the case able to fail.
            ("rather than `orch-decompose`", "what the direct root is emitted instead of"),
            ("write scope", "what the directly bound executor is given"),
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token, text,
                    f"orch-spec's direct lane omits {token!r}, which names "
                    f"{why}; without it the lane is an intention rather than "
                    "something a reader can run",
                )


if __name__ == "__main__":
    unittest.main()
