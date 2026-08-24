"""Cut ordering, tip checks, and re-verification flow guardrails."""

import re
import tempfile
import unittest
from pathlib import Path

from ._support import CONTRACTS, ROOT, clause, clause_gaps, section

VERIFICATION = ROOT / "rules" / "verification.md"
FRONTIER = ROOT / "skills" / "engines" / "orch-frontier" / "SKILL.md"
WORK_ITEM = CONTRACTS / "work-item.md"
CRITIQUE = ROOT / "skills" / "kernel" / "orch-critique" / "SKILL.md"
DECOMPOSE = ROOT / "skills" / "kernel" / "orch-decompose" / "SKILL.md"
INTEGRATE = ROOT / "skills" / "kernel" / "orch-integrate" / "SKILL.md"
SPEC = ROOT / "skills" / "workflows" / "orch-spec" / "SKILL.md"

_FRONTIER_CUT_CHECK = {
    "the units wait rather than promote": ("stay `pending`",),
    "the field whose absence holds them": ("`checked_by`",),
    "the check the cut's correction is accepted on": ("cutcheck",),
    "the context whose cut-check re-run is the re-verification": (
        "`cutcheck.py`", "re-verification",
    ),
    "the threshold that buys a cut a fresh reader": ("three or more", "advisory"),
}

#: The contract keeps only the pointer: the staffing law is
#: rules/verification.md §10's and its threshold orch-frontier's, so the
#: Root ticket section is asserted to name its reader and defer, never to
#: restate the clause. The clause itself is checked at its one owner above.
_CONTRACT_CUT_POINTER = {
    "the field that records the root's cut reader": (
        "`checked_by`", "cut reader",
    ),
    "the law the contract defers to instead of restating": (
        "rules/verification.md", "§10",
    ),
}

_FRONTIER_CLAUSE_RE = re.compile(
    r"A\s+root\s+cut\s+reader.*?cut\s+alone\.\s*", re.S
)
_CONTRACT_POINTER_RE = re.compile(
    r"its\s+`checked_by`\s+recording.*?composite\s+gate\.\s*", re.S
)


class CutCheckOrderingTest(unittest.TestCase):
    """A fresh reader checks a cut before any unit is dispatched."""

    def test_the_engine_holds_the_units_until_the_cut_is_checked(self):
        gaps = clause_gaps(FRONTIER.read_text(encoding="utf-8"), _FRONTIER_CUT_CHECK)
        self.assertEqual(
            [],
            gaps,
            "orch-frontier's body states no cut-checker clause covering: "
            f"{', '.join(gaps)}",
        )

    def test_the_contract_points_a_root_ticket_at_its_cut_reader(self):
        gaps = clause_gaps(
            section(WORK_ITEM.read_text(encoding="utf-8"), "Root ticket"),
            _CONTRACT_CUT_POINTER,
        )
        self.assertEqual(
            [],
            gaps,
            "contracts/work-item.md's Root ticket section states no "
            f"cut-reader pointer covering: {', '.join(gaps)}",
        )

    def test_the_contract_does_not_restate_the_staffing_threshold(self):
        """The threshold has one prose owner, and it is not the contract."""
        contract = WORK_ITEM.read_text(encoding="utf-8")
        for token in ("three or more", "cutcheck advisory", "cut checker"):
            with self.subTest(token=token):
                self.assertNotIn(
                    token,
                    contract,
                    "contracts/work-item.md restates the cut-reader staffing "
                    f"threshold ({token!r}); orch-frontier owns it",
                )

    def test_an_engine_and_a_contract_without_the_clause_fail_the_check(self):
        """The can-fail direction excises each clause from a copy."""
        for path, required, pattern, reader in (
            (FRONTIER, _FRONTIER_CUT_CHECK, _FRONTIER_CLAUSE_RE, lambda t: t),
            (WORK_ITEM, _CONTRACT_CUT_POINTER, _CONTRACT_POINTER_RE,
             lambda t: section(t, "Root ticket")),
        ):
            real = path.read_text(encoding="utf-8")
            with tempfile.TemporaryDirectory() as tmp:
                beside = Path(tmp) / path.name
                beside.write_text(real, encoding="utf-8")
                self.assertEqual(
                    [],
                    clause_gaps(reader(beside.read_text(encoding="utf-8")), required),
                    f"the {path.name} copy must start with the clause intact, "
                    "or the excision below is not what the check reacted to",
                )
                excised = re.sub(pattern, "", real, count=1)
                self.assertNotEqual(
                    real, excised,
                    f"the {path.name} excision matched nothing, so the "
                    "assertion below would prove nothing",
                )
                beside.write_text(excised, encoding="utf-8")
                self.assertEqual(
                    sorted(required),
                    clause_gaps(reader(beside.read_text(encoding="utf-8")), required),
                )


_REVERIFICATION_SPLIT = {
    "the context that re-runs a deterministic invalidation": (
        "invalidated", "deterministic", "the join",
    ),
    "the one invalidation that still takes a fresh child": (
        "fresh child", "judged",
    ),
}

_FRONTIER_REVERIFICATION = {
    "the packet form kept for a judged oracle": (
        "`--executor orch-verify`", "judged",
    ),
    "what the engine re-runs itself, and at which identity": (
        "deterministic", "checked identity",
    ),
}

_SPLIT_CLAUSE_RE = re.compile(
    r"—\s+where\s+every\s+invalidated.*?fresh\s+child", re.S
)
_FRONTIER_SPLIT_RE = re.compile(
    r"(?:;\s+then,|\.\s+Then,)\s+where\s+its\s+pass.*?§10\)\.", re.S
)

_FRONTIER_TIP_CHECK = {
    "what one lane is dispatched to run": (
        "oracles", "nothing wider",
    ),
    "whose checks run at the tip, and how often": (
        "standards owner", "each merge batch",
    ),
    "the revision they run on": ("integrated tip",),
    "where that revision is recorded": ("tip's revision", "run's notes"),
    "what a red tip costs, and what a lane's green is worth before it": (
        "red tip", "next dispatch", "provisional",
    ),
}

_TIP_CLAUSE_RE = re.compile(r"After\s+each\s+merge\s+batch.*?its\s+repair's\.", re.S)


class TipCheckTest(unittest.TestCase):
    """The frontier engine owns checks on the integrated tip."""

    def test_the_engine_runs_the_required_checks_once_on_the_tip(self):
        gaps = clause_gaps(FRONTIER.read_text(encoding="utf-8"), _FRONTIER_TIP_CHECK)
        self.assertEqual(
            [],
            gaps,
            "orch-frontier's body states no tip-check clause covering: "
            f"{', '.join(gaps)}",
        )

    def test_an_engine_without_the_clause_fails_the_check(self):
        """The can-fail direction excises the tip clause from a copy."""
        real = FRONTIER.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            beside = Path(tmp) / FRONTIER.name
            beside.write_text(real, encoding="utf-8")
            self.assertEqual(
                [],
                clause_gaps(beside.read_text(encoding="utf-8"), _FRONTIER_TIP_CHECK),
                "the copy must start with the clause intact, or the excision "
                "below is not what the check reacted to",
            )
            excised = re.sub(_TIP_CLAUSE_RE, "", real, count=1)
            self.assertNotEqual(
                real, excised,
                "the excision matched nothing, so the assertion below would "
                "prove nothing",
            )
            beside.write_text(excised, encoding="utf-8")
            self.assertEqual(
                sorted(_FRONTIER_TIP_CHECK),
                clause_gaps(beside.read_text(encoding="utf-8"), _FRONTIER_TIP_CHECK),
            )


class ReverificationSplitTest(unittest.TestCase):
    """Deterministic and judged invalidations take distinct contexts."""

    def test_the_rule_names_a_context_per_oracle_class(self):
        gaps = clause_gaps(
            clause(VERIFICATION.read_text(encoding="utf-8"), 10),
            _REVERIFICATION_SPLIT,
        )
        self.assertEqual(
            [],
            gaps,
            "rules/verification.md §10 states no re-verification split "
            f"covering: {', '.join(gaps)}",
        )

    def test_the_engine_dispatches_a_child_only_for_a_judged_oracle(self):
        gaps = clause_gaps(
            FRONTIER.read_text(encoding="utf-8"), _FRONTIER_REVERIFICATION
        )
        self.assertEqual(
            [],
            gaps,
            "orch-frontier's checker path states no re-verification split "
            f"covering: {', '.join(gaps)}",
        )

    def test_workflows_carry_successor_runs_selected_independence_and_single_gate(self):
        """Every workflow carries the same topology guardrail."""
        clauses = {
            "orch-spec": (
                SPEC,
                {
                    "successor intake": (
                        "successor run", "predecessor", "result identity",
                        "resolved", "cited", "`successors.md`", "sole writer",
                        "materialization owner", "successor trigger", "replace",
                    ),
                    "one physical root": ("never", "second root", "same run"),
                },
            ),
            "orch-decompose": (
                DECOMPOSE,
                {
                    "selected gate independence": (
                        "`independence: gate`", "all authored-here criteria",
                        "regardless of oracle class", "`independence: checker`",
                    ),
                    "single composite gate": (
                        "one composite gate", "unique lens", "one repair",
                        "one verification",
                    ),
                },
            ),
            "orch-frontier": (
                FRONTIER,
                {
                    "exclusive dispatch": (
                        "one outside-independence path", "checker packet",
                        "gate-deferred", "already checked", "never",
                    ),
                    "root exception": ("root cut reader", "exception"),
                    "successor trigger": (
                        "`successors.md`", "`planned`", "successor trigger",
                        "plan's materialization owner", "accepted", "`## Result` identity",
                        "materializes", "replaces the plan",
                    ),
                },
            ),
            "orch-critique": (
                CRITIQUE,
                {
                    "checker refusal": ("Refuse", "non-root", "gate-deferred"),
                    "single checker": ("single immutable", "`checked_by`"),
                    "additional review": (
                        "unique named", "root-gate critique lens",
                    ),
                },
            ),
            "orch-integrate": (
                INTEGRATE,
                {
                    "contradiction refusal": (
                        "reject", "non-root", "`independence: gate`",
                        "`checked_by`",
                    ),
                    "one path": ("one outside-independence path",),
                    "root cut bookkeeping": (
                        "on a root", "`checked_by`", "cut reader",
                        "never", "final checker acceptance", "composite gate",
                    ),
                },
            ),
        }
        gaps = []
        for owner, (path, required) in clauses.items():
            for gap in clause_gaps(path.read_text(encoding="utf-8"), required):
                gaps.append(f"{owner}: {gap}")
        self.assertEqual(
            [], gaps,
            "workflow owners do not carry the verification split: "
            + ", ".join(gaps),
        )

    def test_successor_owner_and_trigger_cannot_be_replaced_by_return_only_prose(self):
        required = (
            "`successors.md`", "sole writer", "materialization owner",
            "successor trigger", "replace `successors.md`",
        )
        real = SPEC.read_text(encoding="utf-8")
        required_clause = {"durable successor": required}
        self.assertEqual([], clause_gaps(real, required_clause))
        return_only = (
            "Return the ordered successor-run plan; a caller may open later kinds."
        )
        self.assertTrue(clause_gaps(return_only, required_clause))

    def test_contradictory_checker_and_second_gate_paths_fail_the_guardrail(self):
        forbidden = (
            "also dispatch a checker for a gate-deferred ticket",
            "create a second composite gate",
        )

        def gaps(text):
            flat = " ".join(text.split()).lower()
            return [phrase for phrase in forbidden if phrase in flat]

        joined = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (DECOMPOSE, FRONTIER, INTEGRATE)
        )
        self.assertEqual([], gaps(joined))
        for contradiction in forbidden:
            self.assertEqual([contradiction], gaps(joined + "\n" + contradiction))

    def test_a_rule_and_an_engine_without_the_split_fail_the_check(self):
        """The can-fail direction excises both split clauses from copies."""
        for path, required, pattern, reader in (
            (VERIFICATION, _REVERIFICATION_SPLIT, _SPLIT_CLAUSE_RE,
             lambda t: clause(t, 10)),
            (FRONTIER, _FRONTIER_REVERIFICATION, _FRONTIER_SPLIT_RE, lambda t: t),
        ):
            real = path.read_text(encoding="utf-8")
            with tempfile.TemporaryDirectory() as tmp:
                beside = Path(tmp) / path.name
                beside.write_text(real, encoding="utf-8")
                self.assertEqual(
                    [],
                    clause_gaps(reader(beside.read_text(encoding="utf-8")), required),
                    f"the {path.name} copy must start with the split intact, "
                    "or the excision below is not what the check reacted to",
                )
                excised = re.sub(pattern, "", real, count=1)
                self.assertNotEqual(
                    real, excised,
                    f"the {path.name} excision matched nothing, so the "
                    "assertion below would prove nothing",
                )
                beside.write_text(excised, encoding="utf-8")
                self.assertEqual(
                    sorted(required),
                    clause_gaps(reader(beside.read_text(encoding="utf-8")), required),
                )
