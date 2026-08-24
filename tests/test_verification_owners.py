"""One owner per verification fact, and the §10 branches nothing consumed.

Two facts had four statements each: `checked_by`'s single immutable
identity, owned by contracts/work-item.md, and a verdict's invalidation
by its `covers`, owned by contracts/verdict.md. The kernel skills that
consume them may name them -- a reader of `orch-critique` needs to know
the refusal exists -- but a skill that states a contract's rule without
naming the contract becomes a second owner, and the two drift apart
silently. The form pinned here is link-not-restate: wherever a kernel
skill carries one of those facts, the sentence carrying it names the
owner.

The absences pinned here are the other half. rules/verification.md §10
listed two ordinary independence paths no ticket, engine or script ever
selected -- a bare judged verdict, and an unnamed remainder "covered per
§7" -- and each cost every reader of the section a branch to rule out.
The incentive guards in the same clause are asserted present, because
"shorter" is not the goal and deleting them would also make the module
green.

Three facts left ownerless by contracts/work-item.md's diet are asserted
back at rules/delegation.md, each once: the join's scope rejection, the
child's read boundary, and the bounds currency clause.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

WORK_ITEM = "contracts/work-item.md"
VERDICT = "contracts/verdict.md"
VERIFICATION = "rules/verification.md"
DELEGATION = "rules/delegation.md"
VERIFY = "skills/kernel/orch-verify/SKILL.md"
CRITIQUE = "skills/kernel/orch-critique/SKILL.md"
INTEGRATE = "skills/kernel/orch-integrate/SKILL.md"
PACKET = "scripts/tickets_packet.py"

KERNEL_SKILLS = (VERIFY, CRITIQUE, INTEGRATE)

#: Every CLI form `scripts/tickets_packet.py` already spells out in the
#: prompt a child receives. A skill body repeating one of them pays every
#: dispatch for a string the dispatch already carried, and goes stale the
#: moment the packet's flags change. `tickets.py result-grade` is not one
#: of them: it is the join's own verb, carried by no packet.
PACKET_CARRIED_CLI = (
    r"tickets\.py amend",
    r"tickets\.py new\b",
    r"tickets\.py result(?!-)",
    r"tickets\.py check\b",
    r"tickets\.py run-state",
    r"workspace\.py start",
)

#: What makes each absence above safe: `scripts/tickets_packet.py` still
#: builds that invocation into a child's prompt. Keyed by the sweep pattern
#: it licenses, so a swept form can never lose its premise silently.
PACKET_BUILDS = {
    r"tickets\.py amend": r"_command_text\([^\n]*'amend'",
    r"tickets\.py new\b": r"_command_text\([^\n]*'new'",
    r"tickets\.py result(?!-)": r"_command_text\([^\n]*'result'",
    r"tickets\.py check\b": r"_command_text\([^\n]*'check'",
    r"tickets\.py run-state": r"_command_text\([^\n]*'run-state'",
    r"workspace\.py start": r"_command_text\([^\n]*'workspace\.py'\)[^\n]*'start'",
}


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def unlinked(text: str) -> str:
    """The text with markdown link targets collapsed to their label.

    A link target holds periods and slashes that a sentence splitter
    reads as boundaries; the label is what a sentence actually says.
    """
    return re.sub(r"\]\([^)]*\)", "]", text)


def flat(text: str) -> str:
    return " ".join(text.split())


def sentences(text: str):
    """The body's sentences, link targets collapsed first."""
    return [
        part.strip()
        for part in re.split(r"(?<=[.;])\s+", flat(unlinked(text)))
        if part.strip()
    ]


def clause(relative: str, number: int) -> str:
    """One numbered rule of a `rules/*.md` file, flattened."""
    collected, capturing = [], False
    for line in read(relative).splitlines():
        head = re.match(r"^(\d+)\.\s", line)
        if head:
            if capturing:
                break
            capturing = int(head.group(1)) == number
        if capturing:
            collected.append(line)
    body = flat(" ".join(collected))
    if not body:
        raise AssertionError(f"{relative} carries no clause {number}")
    return body


def bullet(relative: str, opener: str) -> str:
    """One top-level `- ` bullet of a contract, flattened."""
    collected, capturing = [], False
    for line in read(relative).splitlines():
        if line.startswith("- "):
            if capturing:
                break
            capturing = line.startswith(f"- {opener}")
        if capturing:
            collected.append(line)
    body = flat(" ".join(collected))
    if not body:
        raise AssertionError(f"{relative} carries no bullet {opener!r}")
    return body


def never_line(relative: str) -> str:
    """The skill's `Never:` sentence, flattened."""
    match = re.search(r"^Never:.*?(?=\n\n|\Z)", read(relative), re.M | re.S)
    if match is None:
        raise AssertionError(f"{relative} states no Never:")
    return flat(unlinked(match.group(0)))


class CheckedByHasOneOwner(unittest.TestCase):
    """contracts/work-item.md owns the field's single immutable identity."""

    def test_the_contract_states_the_immutability_and_its_producer(self):
        field = bullet(WORK_ITEM, "`checked_by`")
        for token in ("single immutable", "`tickets.py check`"):
            with self.subTest(token=token):
                self.assertIn(
                    token, field,
                    f"contracts/work-item.md's `checked_by` bullet omits "
                    f"{token!r}, so the fact the skills defer to has no owner",
                )

    def test_no_kernel_skill_states_immutability_without_naming_the_owner(self):
        for relative in KERNEL_SKILLS:
            for sentence in sentences(read(relative)):
                if "immutable" not in sentence:
                    continue
                with self.subTest(skill=relative, sentence=sentence[:60]):
                    self.assertIn(
                        "work-item.md", sentence,
                        f"{relative} states `checked_by`'s immutability without "
                        "naming contracts/work-item.md, so it reads as a second "
                        f"owner of the rule: {sentence!r}",
                    )

    def test_at_least_one_kernel_skill_actually_carries_the_deferral(self):
        """The check above is vacuous if no skill mentions the fact at all."""
        carriers = [
            relative
            for relative in KERNEL_SKILLS
            if "immutable" in read(relative)
        ]
        self.assertNotEqual(
            [], carriers,
            "no kernel skill names `checked_by`'s immutability, so the "
            "link-not-restate check above proves nothing",
        )


class CoversInvalidationHasOneOwner(unittest.TestCase):
    """contracts/verdict.md owns what a verdict's `covers` costs."""

    def test_the_verdict_contract_states_the_invalidation_clause(self):
        text = flat(read(VERDICT))
        self.assertIn(
            "A verdict is invalidated when anything it covers changes", text,
            "contracts/verdict.md lost the invalidation clause every reuse "
            "rule in the library defers to",
        )

    def test_orch_verify_defers_reuse_to_that_contract_not_to_a_rule_number(self):
        reuse = [
            sentence
            for sentence in sentences(read(VERIFY))
            if "already covered" in sentence
        ]
        self.assertEqual(
            1, len(reuse),
            "orch-verify states its reuse rule other than once; the sentence "
            "carrying it is what this check reads",
        )
        self.assertIn(
            "verdict.md", reuse[0],
            "orch-verify's reuse sentence does not name contracts/verdict.md, "
            f"the owner of the `covers` clause it rides on: {reuse[0]!r}",
        )
        self.assertNotIn(
            "§7", read(VERIFY),
            "orch-verify still routes reuse through rules/verification.md §7, "
            "which owns what a gate's findings cost, not what a `covers` "
            "change costs; the owner is named directly or not at all",
        )

    def test_orch_verify_does_not_restate_the_clause_in_its_never_line(self):
        self.assertNotIn(
            "covers", never_line(VERIFY),
            "orch-verify's Never: line restates contracts/verdict.md's "
            "invalidation clause; a prohibition that repeats a contract is a "
            "second copy of it",
        )


class SectionTenKeepsOnlyThePathsWithConsumers(unittest.TestCase):
    """§10's two zero-consumer ordinary paths are gone; the guards stay."""

    def section(self) -> str:
        return clause(VERIFICATION, 10)

    def test_the_bare_judged_verdict_path_is_gone(self):
        self.assertNotIn(
            "judged verdict", self.section(),
            "rules/verification.md §10 still lists a bare judged verdict as an "
            "ordinary independence path; no ticket, engine or script selects "
            "it, and §6 already owns how a judged verdict is rendered",
        )

    def test_the_unnamed_rest_covered_remainder_is_gone(self):
        section = self.section()
        for token in ("the rest covered", "§7"):
            with self.subTest(token=token):
                self.assertNotIn(
                    token, section,
                    f"rules/verification.md §10 still carries {token!r}: an "
                    "unnamed remainder deferred to a section about gate "
                    "findings, which no reader resolved into an action",
                )

    def test_the_incentive_guards_stay(self):
        section = self.section()
        for token, why in (
            ("never a second executor", "the checker is not a re-execution"),
            ("single and immutable", "one checker identity per ticket"),
            ("root cut reader", "the one exception, which work-item.md cites"),
            ("UNVERIFIED", "self-authored acceptance is worth nothing"),
            ("root-gate critique lens", "extra review is not a second path"),
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token, section,
                    f"rules/verification.md §10 lost {token!r} ({why}); the "
                    "branch removals pay for themselves out of dead paths, "
                    "never out of the guards",
                )

    def test_the_reverification_split_survives_the_removals(self):
        section = self.section()
        for token in ("invalidated", "deterministic", "the join", "fresh child"):
            with self.subTest(token=token):
                self.assertIn(
                    token, section,
                    f"rules/verification.md §10 lost {token!r}: the split "
                    "between a deterministic re-run at the join and a fresh "
                    "child for a judged oracle is a path with consumers",
                )


class DelegationOwnsTheThreeRestoredFacts(unittest.TestCase):
    """Facts the work-item diet left with no owner anywhere."""

    def test_the_join_rejects_a_result_that_exceeded_its_scope(self):
        rule = clause(DELEGATION, 5)
        for token, why in (
            ("`changed_artifacts`", "names the field the join reads"),
            ("granted scope", "names what the field is compared against"),
            ("regardless of its verdicts", "green oracles do not buy scope"),
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token, rule,
                    f"rules/delegation.md §5 omits {token!r}, which {why}; "
                    "without it a result that wrote outside its authority is "
                    "accepted on its own passing checks",
                )

    def test_a_child_gathers_nothing_outside_its_packet_inputs(self):
        rule = clause(DELEGATION, 4)
        for token, why in (
            ("gathers nothing", "states the read boundary"),
            ("`inputs`", "names the packet part that bounds it"),
            ("investigation", "states the one exception"),
        ):
            with self.subTest(token=token):
                self.assertIn(
                    token, rule,
                    f"rules/delegation.md §4 omits {token!r}, which {why}; the "
                    "prohibition survives in scripts/tickets_packet.py's prompt "
                    "string, and unqualified it forbids an orch-investigate "
                    "child from doing its job",
                )

    def test_the_bounds_currency_clause_is_back(self):
        """§1, the packet-parts rule -- not §9, whose bound is another one.

        §9's bound is the once-per-dispatch count on suspension. A
        currency clause placed after it reads as qualifying it, which is
        the misreading this placement avoids: §1 already governs the
        packet's parts and the identities its `inputs` name.
        """
        rule = clause(DELEGATION, 1)
        for token in ("`bounds`", "`inputs`", "currency binds first"):
            with self.subTest(token=token):
                self.assertIn(
                    token, rule,
                    f"rules/delegation.md §1 omits {token!r}, so nothing states "
                    "that a budget covers reading the evidence its packet "
                    "names, in whichever currency binds first",
                )

    def test_the_suspension_bound_is_not_re_read_as_a_currency(self):
        """The clause the sentence was moved out of must stay clear of it."""
        self.assertNotIn(
            "currency", clause(DELEGATION, 9),
            "rules/delegation.md §9 carries a currency clause again; its own "
            "bound is the once-per-dispatch count on suspension, and a "
            "currency sentence beside it reads as qualifying that count",
        )

    def test_each_restored_fact_is_stated_exactly_once(self):
        """Restoring a fact twice recreates the defect it was restored for."""
        surfaces = sorted(
            path
            for directory in ("contracts", "rules", "skills")
            for path in (ROOT / directory).rglob("*.md")
        )
        for phrase in (
            "regardless of its verdicts",
            "gathers nothing",
            "currency binds first",
        ):
            carriers = [
                str(path.relative_to(ROOT)).replace("\\", "/")
                for path in surfaces
                if phrase in flat(path.read_text(encoding="utf-8"))
            ]
            with self.subTest(phrase=phrase):
                self.assertEqual(
                    1, len(carriers),
                    f"{phrase!r} is stated by {carriers}; a restored fact has "
                    "one owner or it has none",
                )


class KernelSkillsSpellOutNoPacketCarriedCLI(unittest.TestCase):
    """A dispatch packet already hands the child these invocations."""

    def test_no_kernel_skill_repeats_a_packet_carried_invocation(self):
        for relative in KERNEL_SKILLS:
            text = read(relative)
            for pattern in PACKET_CARRIED_CLI:
                with self.subTest(skill=relative, cli=pattern):
                    self.assertIsNone(
                        re.search(pattern, text),
                        f"{relative} spells out {pattern!r}, which "
                        "scripts/tickets_packet.py already writes into the "
                        "prompt of every child that needs it",
                    )

    def test_the_packet_generator_still_carries_every_swept_invocation(self):
        """The sweep above is a de-duplication only while this stays true.

        Dropping a skill's copy of an invocation costs a reader nothing
        while the dispatch hands the child the same string. If the
        generator stops emitting one, the library spells it out nowhere
        and the absence sweep goes on passing -- so the premise is pinned
        here, beside the sweep that rests on it.
        """
        self.assertEqual(
            sorted(PACKET_CARRIED_CLI), sorted(PACKET_BUILDS),
            "the swept forms and the premises licensing them have drifted "
            "apart; each absence needs the invocation it rests on",
        )
        generator = read(PACKET)
        for swept, builder in sorted(PACKET_BUILDS.items()):
            with self.subTest(cli=swept):
                self.assertIsNotNone(
                    re.search(builder, generator),
                    f"scripts/tickets_packet.py no longer builds {swept!r} "
                    f"({builder!r} matches nothing), so the kernel skills' "
                    "silence about it is a gap, not a de-duplication",
                )

    def test_the_joins_own_verb_is_not_caught_by_that_sweep(self):
        """`result-grade` is the join's, carried by no packet, and stays."""
        self.assertEqual(
            1, read(INTEGRATE).count("`tickets.py result-grade"),
            "orch-integrate must keep exactly one `tickets.py result-grade` "
            "invocation: contracts/result.md's crossing is the join's own, and "
            "the sweep above must not have taken it",
        )


if __name__ == "__main__":
    unittest.main()
