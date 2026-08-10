"""Deterministic contract checks for the canonical benchmark architecture."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
EVAL_DESIGN = ROOT / "skills" / "workflows" / "orch-eval-design" / "SKILL.md"
OLD_BENCH = ROOT / "skills" / "workflows" / "orch-bench"
OLD_EVOLVE = ROOT / "skills" / "workflows" / "orch-evolve"
# Demoted per contracts/composition.md: evolve is a named composition.
EVOLVE = ROOT / "compositions" / "evolve.md"
EVOLVE_EVALUATION = ROOT / "compositions" / "references" / "evolve-evaluation.md"
EVOLVE_GENERATION = ROOT / "compositions" / "references" / "evolve-generation.md"
TOURNAMENT = ROOT / "compositions" / "skill-tournament.md"
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
            "candidate-blind judge brief",
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
    def test_evolve_is_a_named_composition_not_a_skill(self):
        self.assertFalse(
            (OLD_EVOLVE / "SKILL.md").exists(),
            "orch-evolve must not remain as a skill; it is compositions/evolve.md",
        )
        self.assertTrue(EVOLVE.is_file())
        fields, _ = split_skill(EVOLVE)
        self.assertEqual("evolve", fields["name"])
        # Manual-only survives the demotion as entry: named.
        self.assertEqual("named", fields["entry"])
        self.assertLessEqual(len(fields["description"]), 140)

    def test_requires_the_frozen_campaign_inputs_and_mutation_intersection(self):
        _, body = split_skill(EVOLVE)
        require = normalized(paragraph(body, "Require:"))
        for required in (
            "frozen evolve spec",
            "`evidence`",
            "incumbent identity",
            "frozen evaluation identity",
            "`affected_surfaces`",
            "`authority`",
            "intersection",
            "lane count per candidate",
        ):
            self.assertIn(required, require)

    def test_verifies_required_eligibility_before_ranking_survivors(self):
        _, body = split_skill(EVOLVE)
        combined = body + read(EVOLVE_GENERATION)
        self.assertLess(combined.index("`orch-verify`"), combined.index("`orch-panel`"))
        contract = normalized(combined)
        self.assertIn("required admission", contract)
        self.assertIn("eligible candidates", contract)
        self.assertIn("required admission criterion", contract)
        self.assertIn("cannot compensate", contract)
        self.assertIn("fixed result/evidence", contract)
        self.assertIn("score card cites admitted evidence", contract)

    def test_owns_generation_and_promotion_against_one_frozen_evaluation(self):
        _, body = split_skill(EVOLVE)
        combined = body + read(EVOLVE_GENERATION)
        contract = normalized(combined)
        for required in (
            "generation direction",
            "score the fixed incumbent",
            "frozen evaluation",
            "freeze the evaluation identity",
            "result/evidence identity",
            "evaluation mode",
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
            "evaluation-design gap",
        ):
            self.assertIn(required, contract)

        calls = set(CALL_EDGE_RE.findall(combined))
        for sentence in re.split(r"(?<=[.!?])\s+", normalized(procedure(body))):
            if "runner" in sentence:
                self.assertNotIn("score card", sentence)
        self.assertNotIn("orch-bench", calls)
        self.assertNotIn("orch-benchmaker", calls)
        self.assertTrue(
            {
                "orch-eval-design",
                "orch-loop",
                "orch-delegate",
                "orch-integrate",
                "orch-verify",
                "orch-panel",
                "orch-judge",
                "orch-search-plan",
                "orch-worklog",
            }
            <= calls
        )

    def test_missing_evaluation_defaults_to_a_frozen_judge_brief(self):
        _, body = split_skill(EVOLVE)
        combined = normalized(body + read(EVOLVE_GENERATION))
        self.assertTrue(EVOLVE_EVALUATION.is_file())
        mapping = normalized(read(EVOLVE_EVALUATION))
        self.assertIn("when no frozen evaluation is supplied", combined)
        self.assertIn("candidate-blind judge brief", combined)
        self.assertIn("before generation", combined)
        self.assertIn("frozen panel binding before the first plan", combined)
        self.assertIn("score card identity and complete numeric dimension vector", combined)
        self.assertIn("benchmark mode", combined)
        self.assertIn("judged mode", combined)
        self.assertIn("never: change evaluation after campaign open", combined)
        self.assertNotIn("`orch-benchmaker`", combined)
        for carrier in (
            "`objective`",
            "`inputs`",
            "`authority`",
            "`bounds`",
            "`return_contract`",
            "`reply_to`",
        ):
            self.assertIn(carrier, mapping)
        self.assertIn("evaluation-design write scope", mapping)
        self.assertIn("candidate mutation authority", mapping)

    def test_skill_tournament_campaigns_over_one_fixed_benchmark_revision(self):
        fields, body = split_skill(TOURNAMENT)
        self.assertEqual("skill-tournament", fields["name"])
        self.assertLessEqual(len(fields["description"]), 140)
        contract = normalized(body)
        # What the sealed identity was standing in for, and all of it that
        # survives: every candidate scored against the same benchmark bytes.
        self.assertIn("one benchmark revision the campaign never changes", contract)
        self.assertIn("qualified benchmark revision", contract)
        self.assertNotIn("seal", contract)
        # A done check naming something a run can check.
        done = normalized(paragraph(body, "Done check:"))
        self.assertIn("final score card", done)
        self.assertIn("benchmark revision", done)
        self.assertEqual(
            set(),
            set(CALL_EDGE_RE.findall(body)),
            "Tournament binds Evolve and its writer, never Evolve internals",
        )
        self.assertIn("writer binding orch-build", contract)
        self.assertNotIn("promotion", contract)

    def test_loop_supplies_the_fresh_final_score_card_without_a_wrapper(self):
        _, body = split_skill(EVOLVE)
        combined = body + read(EVOLVE_GENERATION)
        self.assertLess(combined.index("`orch-panel`"), combined.index("`orch-judge`"))
        contract = normalized(combined)
        self.assertIn("final incumbent identity", contract)
        self.assertIn("fresh `orch-judge` done-check", contract)
        self.assertIn("final score card", contract)
        self.assertNotRegex(body, r"(?im)^-\s*closing\b")


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
        self.assertIn("frozen evaluation and scoring identities", active_procedure)
        self.assertIn("frozen evaluation mode", active_procedure)
        self.assertIn("frozen candidate-blind judge brief", active_procedure)
        self.assertIn(
            "carry the frozen candidate-blind judge brief verbatim",
            active_procedure,
        )
        self.assertIn("static artifact snapshot", active_procedure)
        self.assertNotIn("render one candidate-blind judge brief", active_procedure)
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
        self.assertIn("replace or alter the frozen brief", never)
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
