"""The fork-arrival clause: its wording, its owner, and every surface it reaches.

Eighteen times in one run, an executor invoking an orchflows skill by
name spawned a fork that arrived with the contract loaded and no packet,
no ticket, no assigned name -- at every tier: workers, checkers, the
gate critique's own pass. The dispatch packet already carries a refusal
sentence and it structurally cannot reach these agents: a packet-less
fork never reads a packet.

The clause first aimed at the 22 skill contracts and was blocked twice
over: rules/token-economy.md 11 left four contracts with no headroom
(orch-frontier at exactly 450 of 450), and scripts/doclint.py's
distinctiveness threshold made a partial rollout strictly worse than
none (a measured 486 cross-tier warnings against a baseline of 27).
The relocation dissolved both: the *adapter* is upstream of the
contract in a fork's load path -- the installed Claude surface is
rendered frontmatter plus an ``@``-include of the canonical body, so
the clause above the include is the first body text a fork reads -- and
installer-rendered surfaces are outside doclint's population and outside
every skill-body budget. Precedent: ``ROLE_INSTRUCTIONS`` is behavioral
dispatch law the installer already renders into the role agent files.

So the clause has exactly one owner, ``installer.packages
.FORK_ARRIVAL_CLAUSE``, and this module guards three things: the
wording still states every property the firings paid for; every
rendered name surface of a role-bearing skill carries it (Claude
adapter, by-name pointer, Codex prompt and redirect); and no skill
contract body carries a copy -- restating it there would re-open the
doclint saturation the relocation closed.

What the firings proved, and what the clause therefore says:

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
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import install
from installer.packages import (
    FORK_ARRIVAL_CLAUSE,
    by_name_pointer_text,
    claude_role_adapter_text,
    codex_role_adapter_body,
    fork_arrival_preamble,
    split_frontmatter,
)

ROOT = Path(__file__).resolve().parents[1]

#: What each property is doing there, keyed by the words carrying it. A
#: future editor shortening the clause has to drop one of these to do it,
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

#: Wordings the clause must NOT use, and the owner each belongs to.
#: Both say what the clause says; both are pinned elsewhere, and reaching
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

#: The tiers the contract sweep must span; a glob that stopped matching
#: one would leave its contracts unswept while this module stayed green.
TIERS = {"kernel", "instances", "utilities", "engines", "workflows"}


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


def _frontmatter_of(relative: str) -> str:
    frontmatter, _body = split_frontmatter((ROOT / relative).read_text(encoding="utf-8"))
    return frontmatter


class TheSweptPopulationIsReal(unittest.TestCase):
    """A sweep over an empty or partial glob proves nothing at all."""

    def test_the_population_is_derived_and_non_empty(self):
        self.assertNotEqual(
            [], contracts(),
            "no skill contract was found under skills/; the absence sweep in "
            "this module would pass vacuously",
        )

    def test_the_population_spans_every_tier(self):
        tiers = {path.relative_to(ROOT).parts[1] for path in contracts()}
        self.assertEqual(
            TIERS, tiers,
            "the swept population does not span the library's tiers; a glob "
            "that stopped matching one tier would leave those contracts "
            "unswept while this module stayed green",
        )


class TheClauseStillSaysWhatItWasWrittenToSay(unittest.TestCase):
    """Guards on the one owned constant, which is what every surface renders."""

    def test_the_clause_states_every_property_the_firings_paid_for(self):
        for token, why in sorted(CLAUSE_PROPERTIES.items()):
            with self.subTest(property=token):
                self.assertIn(
                    token, FORK_ARRIVAL_CLAUSE,
                    f"the fork-arrival clause no longer says {token!r}, which "
                    f"{why}; shortening the clause past a property returns the "
                    "class of firing that property was written against",
                )

    def test_the_clause_leaves_the_reserved_wordings_to_their_owners(self):
        for phrase, owner in sorted(RESERVED_WORDINGS.items()):
            with self.subTest(phrase=phrase):
                self.assertNotIn(
                    phrase, FORK_ARRIVAL_CLAUSE,
                    f"the fork-arrival clause uses {phrase!r}: {owner}. The "
                    "clause says the same thing in words of its own on "
                    "purpose -- restoring the natural phrasing reddens a "
                    "module this change has no business reddening",
                )


class TheInstallerIsTheClausesOneOwner(unittest.TestCase):
    """The clause renders on role-bearing surfaces and lives nowhere else."""

    PLANNER = "skills/workflows/orch-spec/SKILL.md"
    WORKER = "skills/instances/orch-tdd/SKILL.md"
    GLUE = "skills/engines/orch-frontier/SKILL.md"

    def test_no_skill_contract_body_carries_a_copy(self):
        """A body copy re-opens the doclint saturation the relocation closed."""
        for path in contracts():
            with self.subTest(contract=label(path)):
                self.assertNotIn(
                    flat(FORK_ARRIVAL_CLAUSE), flat(body(path)),
                    f"{label(path)} restates the fork-arrival clause in its "
                    "body; the installer renders the one copy onto every "
                    "role-bearing surface, and a body copy is the partial "
                    "rollout doclint measured at 486 cross-tier warnings",
                )

    def test_only_role_bearing_surfaces_get_the_preamble(self):
        self.assertTrue(fork_arrival_preamble("planner").startswith(FORK_ARRIVAL_CLAUSE))
        self.assertTrue(fork_arrival_preamble("worker").startswith(FORK_ARRIVAL_CLAUSE))
        for role in ("none", "", None):
            with self.subTest(role=role):
                self.assertEqual(
                    "", fork_arrival_preamble(role),
                    "a role: none surface runs in the invoking context and "
                    "never produces the packet-less arrival the clause governs",
                )

    def test_the_claude_adapter_reads_the_clause_before_the_include(self):
        for relative in (self.PLANNER, self.WORKER):
            with self.subTest(contract=relative):
                text = claude_role_adapter_text(_frontmatter_of(relative), Path("X"))
                self.assertIn(FORK_ARRIVAL_CLAUSE, text)
                self.assertLess(
                    text.index(FORK_ARRIVAL_CLAUSE), text.index("@"),
                    "the clause must be the first body text a fork reads, "
                    "above the @-include that pulls the contract in",
                )
        self.assertNotIn(
            FORK_ARRIVAL_CLAUSE,
            claude_role_adapter_text(_frontmatter_of(self.GLUE), Path("X")),
        )

    def test_the_by_name_pointer_carries_it_for_role_bearing_names(self):
        pointed = by_name_pointer_text(_frontmatter_of(self.WORKER), "worker", Path("X"))
        self.assertIn(FORK_ARRIVAL_CLAUSE, pointed)
        clean = by_name_pointer_text(_frontmatter_of(self.GLUE), "none", Path("X"))
        self.assertNotIn(FORK_ARRIVAL_CLAUSE, clean)

    def test_the_codex_gate_carries_it(self):
        self.assertIn(
            FORK_ARRIVAL_CLAUSE,
            codex_role_adapter_body("orch-tdd", "worker", Path("X")),
        )

    def test_the_built_plan_renders_it_on_every_role_bearing_surface(self):
        """The wiring, not just the composers: what an install actually writes."""
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / ".claude").mkdir()
            (home / ".codex").mkdir()
            with patch.object(install.Path, "home", return_value=home), patch.object(
                install.shutil, "which", return_value="claude"
            ):
                plan = install.build_plan("user", None)

        roles = {}
        for skill_md in install.discover_packages():
            frontmatter, _body = install.split_frontmatter(skill_md.read_text(encoding="utf-8"))
            name = install.frontmatter_field(frontmatter, "name")
            roles[name] = install.frontmatter_field(frontmatter, "role") or "none"

        surfaces = {
            "claude adapter": {dest.parent.name: content for dest, content in plan.claude_adapters},
            "by-name pointer": {dest.parent.name: content for dest, content in plan.by_name},
        }
        for surface, rendered in surfaces.items():
            for name, content in rendered.items():
                role = roles.get(name)
                if role is None:
                    continue  # compositions and templates carry no role
                with self.subTest(surface=surface, name=name):
                    if role in ("planner", "worker"):
                        self.assertIn(
                            FORK_ARRIVAL_CLAUSE, content,
                            f"{surface} for {name} (role {role}) does not "
                            "carry the fork-arrival clause; a fork loading "
                            "this surface is ungoverned",
                        )
                    else:
                        self.assertNotIn(FORK_ARRIVAL_CLAUSE, content)


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
