import json
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[3] / "skills" / "benchmaker" / "scripts"))

from metabench import claims, metrics as scoring, report  # noqa: E402

PASSING = {"G1_executability": {"pass": True, "preflight_exit": 0, "member_runs": 22, "schema_valid_share": 1.0,
                                "infrastructure_error_share": 0.0, "reasons": []},
           "G2_reference_and_floor": {"pass": True, "reference_pass_rate": 1.0, "noop_full_success_tasks": [], "noop_mean_credit": 0.0,
                                      "reasons": []},
           "crosscheck": {"pass": True, "count_mismatches": [], "grade_mismatches": []},
           "staging": {"pass": True, "cheater_findings": []}}

METRICS = {
    "M1_cheaters": {"credit_by_class": {"noop": {"mean_credit": 0.0}, "read_ancestors": {"mean_credit": 0.33}}, "hackable_task_ratio": 0.5,
                    "ci90": [0.2, 0.8], "hackable_tasks": ["t2", "t4"], "tasks": 6},
    "M2_order": {"pairs": 31, "pair_accuracy": 0.97, "ci90": [0.9, 1.0], "tau_b": 0.9, "null_p": 0.0004, "contradicted": [], "unresolved": [1, 2]},
    "M3_kill": {"killable": 6, "killed": 5, "rate": 0.83, "ci90": [0.5, 0.97], "by_origin": {"synthetic": 0.8, "natural": 1.0},
                "exercised_share": {"d1": 1.0, "d2": 0.0}},
    "M4_contrasts": {"resolution_recall": 1.0, "ci90": [0.4, 1.0], "aa_false_separation": 0.0, "aa_pairs": [1, 2], "reversed": []},
    "M5_reliability": {"computed": False, "reason": "single full run per member"},
    "M6_verifier": {"tasks_covered": 22, "tasks_total": 24, "oracle_coverage": 0.92, "tpr": 1.0, "tpr_ci90": [0.9, 1.0], "tnr": 0.98,
                    "tnr_ci90": [0.9, 1.0], "false_rejects": [], "false_accepts": [1]},
    "M7_task_profile": {"reference_fail": [], "floor_credit": [{"task": "t3"}], "flat": {"computed": False, "reason": "x"}, "inverted": [],
                        "informative_share": 0.83, "tasks": 6},
    "M8_range": {"computed": False, "reason": "no LLM members"},
    "speed": {"achieved_overlap_reported": 7.1, "achieved_overlap_measured": 6.8, "declared_concurrency": 8}}

M9 = {"claims": 10, "checkable": 6, "contradicted": [{"id": "c1", "type": "interval", "direction": "measured-above", "claimed": [0.2, 0.45],
                                                       "measured": [0.48, 0.62], "reason": None},
                                                      {"id": "c8", "type": "cost", "direction": "measured-above", "claimed": None,
                                                       "measured": None, "reason": "usd 4.2 above 3.0"}],
      "underclaimed": ["c1"], "uncheckable": [], "vacuous": [], "contradiction_rate": 0.33, "gap_recall": 1.0, "gap_precision": 0.5,
      "verdict_agreement": None, "disclosed_gaps": ["floor"], "measured_gaps": {"floor": ["floor credit on 1 tasks"], "hackable-task": ["t2"]}}


def make(gates=None, **parts):
    return report.assemble(meta_task="schedule-nosolver", build="reference", arm="reference", pool="p1", gates=gates or PASSING,
                           metrics=dict(METRICS), claims=M9, **parts)


class AssembleTests(unittest.TestCase):
    def test_shape_follows_the_report_contract(self):
        result = make(copied_reference_files=["tasks/t1/tests/verify.py"], conditions=[{"name": "profile", "value": "full"}])
        self.assertEqual(list(result), ["meta_task", "build", "arm", "pool", "gates", "metrics", "copied_reference_files", "conditions", "gaps"])
        self.assertEqual(result["gates"], PASSING)
        self.assertEqual(result["metrics"]["M9_claims"], M9)
        self.assertEqual(result["metrics"]["builder"], {"seconds": None, "cost_usd": None, "out_of_workspace_reads": []})
        self.assertEqual(result["copied_reference_files"], ["tasks/t1/tests/verify.py"])
        json.dumps(result, allow_nan=False)

    def test_scoring_constants_come_first_in_conditions(self):
        names = [c["name"] for c in make(conditions=[{"name": "profile", "value": "full"}])["conditions"]]
        self.assertEqual(names[:2], ["alpha", "interval_level"])
        self.assertEqual(names[-1], "profile")

    def test_gaps_mark_what_the_card_disclosed(self):
        self.assertEqual(make()["gaps"], [{"category": "floor", "evidence": ["floor credit on 1 tasks"], "disclosed": True},
                                          {"category": "hackable-task", "evidence": ["t2"], "disclosed": False}])

    def test_without_claims_or_builder_data(self):
        result = report.assemble(meta_task="m", build="b", arm="plain", pool="p", gates=PASSING, metrics={}, builder={"seconds": 3.0})
        self.assertEqual(result["metrics"]["M9_claims"], {"computed": False, "reason": "no card claims scored"})
        self.assertEqual(result["metrics"]["builder"], {"seconds": 3.0})
        self.assertEqual(result["gaps"], [])


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.text = report.render(make())

    def test_gates_come_before_everything_else(self):
        headings = [line for line in self.text.splitlines() if line.startswith("#")]
        self.assertEqual(headings[:3], ["# Meta-verification: schedule-nosolver", "## Gates", "## Metrics"])
        self.assertLess(self.text.index("## Gates"), self.text.index("| M1_cheaters"))
        self.assertLess(self.text.index("G2_reference_and_floor"), self.text.index("## Metrics"))
        self.assertLess(self.text.index("## Metrics"), self.text.index("## Contradicted claims"))
        self.assertLess(self.text.index("## Contradicted claims"), self.text.index("## Gaps"))
        self.assertLess(self.text.index("## Gaps"), self.text.index("## Conditions"))

    def test_every_gate_has_a_row(self):
        for name in report.GATES:
            self.assertIn(f"| {name} | pass |", self.text)
        self.assertNotIn("FAIL", self.text)
        self.assertNotIn("A failed gate", self.text)

    def test_failed_gate_is_marked_with_its_reasons(self):
        gates = {**PASSING, "G1_executability": {**PASSING["G1_executability"], "pass": False, "reasons": ["m3: killed at the cap"]},
                 "staging": {"pass": False, "cheater_findings": [{"path": "../tests"}]}}
        text = report.render(make(gates))
        self.assertIn("| G1_executability | FAIL |", text)
        self.assertIn("Failed: m3: killed at the cap", text)
        self.assertIn("| staging | FAIL | 1 cheater findings |", text)
        self.assertIn("A failed gate is reported", text)
        self.assertLess(text.index("A failed gate"), text.index("## Metrics"))

    def test_one_row_per_metric_with_its_interval(self):
        rows = {line.split("|")[1].strip(): line for line in self.text.splitlines()
                if line.startswith(("| M", "| speed", "| builder")) and not line.startswith("| Metric")}
        self.assertEqual(list(rows), ["M1_cheaters", "M2_order", "M3_kill", "M4_contrasts", "M5_reliability", "M6_verifier", "M7_task_profile",
                                      "M8_range", "M9_claims", "speed", "builder"])
        self.assertIn("pair accuracy 0.97 (90% interval 0.90 to 1.00) over 31 pairs", rows["M2_order"])
        self.assertIn("hackable-task ratio 0.50 (90% interval 0.20 to 0.80) over 6 tasks (t2, t4)", rows["M1_cheaters"])
        self.assertIn("killed 5 of 6", rows["M3_kill"])
        self.assertIn("never exercised: d2", rows["M3_kill"])
        self.assertIn("TPR 1.00 (90% interval 0.90 to 1.00), TNR 0.98", rows["M6_verifier"])
        self.assertIn("not computed: single full run per member", rows["M5_reliability"])
        self.assertIn("not computed: no LLM members", rows["M8_range"])
        self.assertIn("flagged: reference_fail 0, floor_credit 1, flat n/a, inverted 0", rows["M7_task_profile"])
        self.assertIn("6 of 10 claims checkable; contradicted 2", rows["M9_claims"])
        self.assertIn("overlap reported 7.1, measured 6.8, declared concurrency 8", rows["speed"])

    def test_contradicted_claims_and_gaps_are_listed(self):
        self.assertIn("- c1 (interval): measured-above; claimed [0.2, 0.45], measured [0.48, 0.62]", self.text)
        self.assertIn("- c8 (cost): measured-above; claimed None, measured None (usd 4.2 above 3.0)", self.text)
        self.assertIn("- floor: floor credit on 1 tasks (disclosed)", self.text)
        self.assertIn("- hackable-task: t2 (not disclosed)", self.text)

    def test_empty_sections_say_so(self):
        text = report.render(report.assemble(meta_task="m", build="b", arm="a", pool="p", gates=PASSING, metrics=dict(METRICS)))
        self.assertIn("## Contradicted claims\n\nNone.", text)
        self.assertIn("## Gaps\n\nNone measured.", text)

    def test_conditions_and_copied_files_are_listed(self):
        text = report.render(make(copied_reference_files=["tasks/t1/solution/solve.py"], conditions=[{"name": "profile", "value": "full"}]))
        self.assertIn("- alpha: 0.05", text)
        self.assertIn("- profile: full", text)
        self.assertIn("## Files copied from the reference packages\n\n- tasks/t1/solution/solve.py", text)
        self.assertNotIn("Files copied", self.text)

    def test_conditions_given_as_a_mapping_or_plain_strings(self):
        base = {"meta_task": "m", "gates": PASSING, "metrics": {}}
        self.assertIn("- jobs: 3", report.render({**base, "conditions": {"jobs": 3}}))
        self.assertIn("- no LLM members", report.render({**base, "conditions": ["no LLM members"]}))

    def test_table_cells_survive_pipes_and_unknown_metrics(self):
        text = report.render({"gates": PASSING, "metrics": {"extra": {"a|b": 1}}})
        row = [line for line in text.splitlines() if line.startswith("| extra")][0]
        self.assertEqual(row.count("|"), 3)
        self.assertIn('"a/b": 1', row)

    def test_a_failed_gate_missing_from_the_report_counts_as_failed(self):
        text = report.render({"gates": {}, "metrics": {}})
        self.assertEqual(text.count("| FAIL |"), 4)


class IntegrationTests(unittest.TestCase):
    """The pieces fit: metrics -> measure -> score_claims -> assemble -> render."""

    def test_pipeline_on_a_small_pool(self):
        def run(values):
            tasks = {t: {"source_group": t, "anchor": False, "scored": 1, "full_success_rate": v, "mean_credit": v} for t, v in values.items()}
            mean = sum(values.values()) / len(values)
            return {"summary": {"suite": {}, "tasks": tasks, "overall": {"full_success_rate": mean, "mean_credit": mean}, "counts": {"planned": 6},
                                "cost": {"usd_known": 0.0, "attempts_with_unknown_cost": 0}, "run": {"wall_seconds": 5.0}}}
        names = ("t1", "t2", "t3", "t4", "t5", "t6")
        runs = {"mO": run(dict.fromkeys(names, 1.0)), "mD": run(dict.fromkeys(names, 0.0)), "mN": run(dict.fromkeys(names, 0.0)),
                "@reference": run(dict.fromkeys(names, 1.0)), "@noop": run(dict.fromkeys(names, 0.0))}
        order = {"members": {"mO": {"kind": "scripted", "behavior": "oracle"}, "mD": {"kind": "scripted", "behavior": "defect", "origin": "synthetic"},
                             "mN": {"kind": "scripted", "behavior": "floor", "name": "noop"}},
                 "known_pairs": [{"higher": "mO", "lower": "mD"}, {"higher": "mO", "lower": "mN"}],
                 "contrasts": [{"higher": "mO", "lower": "mN", "must_resolve": True}],
                 "killable": {"mD": {"confirmed": True}}}
        card = {"conditions": {"reference": {"agent": "@reference"}},
                "claims": [{"id": "c4", "type": "rate", "metric": "reference_pass_rate", "min": 1.0}, {"id": "g", "type": "gap", "category": "floor"}]}
        found = scoring.metrics(runs, order, None, None)
        m9 = claims.score_claims(card, claims.measure(card, order, runs, found))
        gates = scoring.gates({"preflight": {"exit_code": 0}, "members": {m: {"exit_code": 0, "status": "completed", "schema_valid": True}
                                                                          for m in ("mO", "mD", "mN")}},
                              runs["@reference"], runs["@noop"], {"count_mismatches": [], "grade_mismatches": []}, [])
        self.assertTrue(scoring.gates_pass(gates))
        self.assertEqual((found["M2_order"]["pair_accuracy"], found["M3_kill"]["killed"], found["M4_contrasts"]["resolution_recall"]), (1.0, 1, 1.0))
        self.assertEqual(found["M1_cheaters"]["hackable_tasks"], [])
        self.assertEqual((m9["contradicted"], m9["checkable"]), ([], 1))
        text = report.render(report.assemble(meta_task="toy", build="reference", arm="reference", pool="p", gates=gates, metrics=found, claims=m9))
        json.dumps(report.assemble(meta_task="toy", build="reference", arm="reference", pool="p", gates=gates, metrics=found, claims=m9),
                   allow_nan=False)
        self.assertLess(text.index("## Gates"), text.index("## Metrics"))
        self.assertIn("| G1_executability | pass |", text)


if __name__ == "__main__":
    unittest.main()
