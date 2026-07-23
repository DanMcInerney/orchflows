"""Deterministic contract checks for the canonical benchmark architecture."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVAL_DESIGN = ROOT / "skills" / "workflows" / "orch-eval-design" / "SKILL.md"
OLD_BENCH = ROOT / "skills" / "workflows" / "orch-bench"
EVOLVE = ROOT / "skills" / "workflows" / "orch-evolve" / "SKILL.md"
PANEL = ROOT / "skills" / "engines" / "orch-panel" / "SKILL.md"

CALL_EDGE_RE = re.compile(r"`(orch-[a-z0-9-]+)`")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def split_skill(path: Path) -> tuple[dict[str, str], str]:
    text = read(path)
    match = re.fullmatch(r"---\n(.*?)\n---\n(.*)", text, re.DOTALL)
    if match is None:
        raise AssertionError(f"{path} does not have canonical frontmatter")
    fields = {}
    for line in match.group(1).splitlines():
        key, value = line.split(":", 1)
        fields[key] = value.strip()
    return fields, match.group(2)


def paragraph(body: str, label: str) -> str:
    match = re.search(
        rf"^{re.escape(label)}(.*?)(?:\n[ \t]*\n|\Z)",
        body,
        re.MULTILINE | re.DOTALL,
    )
    if match is None:
        raise AssertionError(f"missing {label}")
    return match.group(1)


def procedure(body: str) -> str:
    require_end = body.index("\n\n", body.index("Require:")) + 2
    return body[require_end : body.index("Never:")]


def normalized(text: str) -> str:
    return " ".join(text.lower().split())


def assert_canonical_anatomy(
    case: unittest.TestCase,
    path: Path,
    expected_name: str,
    expected_role: str,
    body_budget: int,
) -> tuple[dict[str, str], str]:
    fields, body = split_skill(path)
    case.assertEqual(expected_name, fields["name"])
    case.assertEqual(expected_role, fields["role"])
    case.assertLessEqual(len(fields["description"]), 140)
    case.assertLess(body.index("Require:"), body.index("Never:"))
    case.assertLess(body.index("Never:"), body.index("Return:"))
    case.assertLessEqual(
        sum(bool(line.strip()) for line in body.splitlines()),
        body_budget,
    )
    return fields, body


class TestEvaluationDesign(unittest.TestCase):
    def test_replaces_bench_with_one_canonical_skill(self):
        self.assertFalse(
            (OLD_BENCH / "SKILL.md").exists(),
            "orch-bench must not remain as an alias",
        )
        self.assertTrue(EVAL_DESIGN.is_file())
        assert_canonical_anatomy(
            self,
            EVAL_DESIGN,
            expected_name="orch-eval-design",
            expected_role="none",
            body_budget=40,
        )

    def test_maps_the_delegation_packet_and_return_address(self):
        _, body = split_skill(EVAL_DESIGN)
        require = paragraph(body, "Require:")
        for field in (
            "objective",
            "inputs",
            "authority",
            "bounds",
            "return_contract",
            "reply_to",
        ):
            self.assertIn(f"`{field}`", require)

        returned = normalized(paragraph(body, "Return:"))
        for field in (
            "evaluation-design identity",
            "assumptions",
            "gaps",
            "changed artifacts",
        ):
            self.assertIn(field, returned)
        self.assertIn("addresses `reply_to`", returned)

    def test_owns_candidate_blind_evaluation_semantics_only(self):
        _, body = split_skill(EVAL_DESIGN)
        contract = normalized(body)
        for required in (
            "candidate-comparison-blind",
            "target boundary",
            "case specifications",
            "required criteria",
            "oracle_class",
            "anchors",
            "scoring",
            "aggregation",
            "intended coverage",
            "source identities",
            "expected execution cost",
            "smallest",
            "discrimination",
            "explicit gaps",
        ):
            self.assertIn(required, contract)
        self.assertEqual(set(), set(CALL_EDGE_RE.findall(body)))

        active_procedure = normalized(procedure(body))
        for forbidden_action in (
            "gather research",
            "materialize",
            "execute candidate",
            "generate candidate",
            "promote",
            "revise",
        ):
            self.assertNotIn(forbidden_action, active_procedure)


class TestFrozenBenchmarkEvolution(unittest.TestCase):
    def test_requires_the_frozen_campaign_inputs_and_mutation_intersection(self):
        fields, body = assert_canonical_anatomy(
            self,
            EVOLVE,
            expected_name="orch-evolve",
            expected_role="none",
            body_budget=40,
        )
        self.assertEqual("true", fields["disable-model-invocation"])
        require = normalized(paragraph(body, "Require:"))
        for required in (
            "frozen evolve spec",
            "`evidence`",
            "incumbent identity",
            "qualified benchmark identity",
            "`affected_surfaces`",
            "`authority`",
            "intersection",
            "lane count per candidate",
        ):
            self.assertIn(required, require)

    def test_verifies_required_eligibility_before_ranking_survivors(self):
        _, body = split_skill(EVOLVE)
        self.assertLess(body.index("`orch-verify`"), body.index("`orch-panel`"))
        contract = normalized(body)
        self.assertIn("required eligibility", contract)
        self.assertIn("verified survivors", contract)
        self.assertIn("required deterministic", contract)
        self.assertIn("cannot compensate", contract)
        self.assertIn("covered-pass result/evidence identity", contract)
        self.assertIn("score card cites the admitted evidence", contract)

    def test_owns_generation_and_promotion_against_one_frozen_benchmark(self):
        _, body = split_skill(EVOLVE)
        contract = normalized(body)
        for required in (
            "generation direction",
            "incumbent score card",
            "judge-owned incumbent score card",
            "benchmark identity",
            "result/evidence identity",
            "runner",
            "scoring",
            "protected evidence policy",
            "mutation authority",
            "promotion rule",
            "required margin",
            "done-check",
            "new campaign",
            "retained candidate",
            "blocked partial result",
            "separate benchmaker run",
        ):
            self.assertIn(required, contract)

        calls = set(CALL_EDGE_RE.findall(body))
        for sentence in re.split(r"(?<=[.!?])\s+", normalized(procedure(body))):
            if "runner" in sentence:
                self.assertNotIn("score card", sentence)
        self.assertNotIn("orch-bench", calls)
        self.assertNotIn("orch-eval-design", calls)
        self.assertNotIn("orch-benchmaker", calls)
        self.assertTrue(
            {
                "orch-loop",
                "orch-delegate",
                "orch-integrate",
                "orch-verify",
                "orch-panel",
                "orch-judge",
            }
            <= calls
        )

    def test_judged_done_check_gets_a_fresh_closing_score_card(self):
        _, body = split_skill(EVOLVE)
        self.assertLess(body.index("`orch-panel`"), body.index("`orch-judge`"))
        contract = normalized(body)
        self.assertIn("judged done-check pass is provisional", contract)
        self.assertIn("final incumbent identity", contract)
        self.assertIn("fresh `orch-judge`", contract)
        self.assertIn("closing score card", contract)


class TestPanelPacketShape(unittest.TestCase):
    def test_each_judge_packet_contains_exactly_one_candidate(self):
        _, body = assert_canonical_anatomy(
            self,
            PANEL,
            expected_name="orch-panel",
            expected_role="none",
            body_budget=40,
        )
        active_procedure = normalized(procedure(body))
        self.assertIn("exactly one fixed candidate identity", active_procedure)
        self.assertIn("frozen scoring criteria", active_procedure)
        self.assertIn("exact result/evidence identity", active_procedure)
        self.assertIn("frozen benchmark and scoring identities", active_procedure)
        self.assertIn("score card citing the exact evidence identity", active_procedure)
        self.assertNotIn("candidate set as the packet", active_procedure)
        self.assertEqual(
            {"orch-judge", "orch-delegate", "orch-integrate"},
            set(CALL_EDGE_RE.findall(body)),
        )

    def test_preserves_predeclared_aggregation_and_disagreement(self):
        _, body = split_skill(PANEL)
        require = normalized(paragraph(body, "Require:"))
        for required in (
            "fixed candidate set",
            "frozen scoring criteria",
            "declared aggregation method",
            "lane count",
        ):
            self.assertIn(required, require)

        active_procedure = normalized(procedure(body))
        self.assertIn("aggregate exactly by the declared method", active_procedure)
        self.assertIn("disagreement", active_procedure)
        never = normalized(paragraph(body, "Never:"))
        self.assertIn("change the aggregation method", never)
        self.assertIn("drop a dissenting lane", never)
        self.assertIn("re-execute or substitute admitted evidence", never)

        returned = normalized(paragraph(body, "Return:"))
        for field in (
            "aggregate order or verdict",
            "per-lane score cards",
            "admitted result/evidence identities",
            "disagreement register",
        ):
            self.assertIn(field, returned)


if __name__ == "__main__":
    unittest.main()
