import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[3] / "skills" / "benchmaker" / "scripts"))

from metabench import claims  # noqa: E402


def interval(estimate, low, high):
    return {"estimate": estimate, "low": low, "high": high}


def system(**metrics):
    return {"member": "m", "metrics": metrics, "noise": {}, "cost_usd": 1.0, "cost_complete": True, "wall_seconds": 100.0}


def measured(**extra):
    base = {"systems": {
        "subject": {**system(full_success_rate=interval(0.55, 0.48, 0.62), mean_credit=interval(0.25, 0.2, 0.3)),
                    "noise": {"full_success_rate": {"sd": 0.05, "n": 4}}, "cost_usd": 4.2, "wall_seconds": 500.0},
        "sonnet-low": system(full_success_rate=interval(0.9, 0.85, 0.95))},
        "rates": {"trivial_credit": interval(0.0, 0.0, 0.05), "reference_pass_rate": interval(0.75, 0.5, 0.9)},
        "orders": {"c2": {"outcome": "lower", "mean_diff": -0.1, "ci95": [-0.2, -0.01]}},
        "defects": {"hackable-task": ["t2"], "unresolved-contrast": ["a over b"], "floor": ["t3"]},
        "checked": ["hackable-task", "unresolved-contrast", "floor", "ceiling", "verifier-false-accept"],
        "verdict": {"supports_claim": False}}
    base.update(extra)
    return base


def claim(cid, kind, **fields):
    return {"id": cid, "type": kind, **fields}


CARD = {"claims": [
    claim("c1", "interval", metric="full_success_rate", system="subject", low=0.2, high=0.45, level=0.9),
    claim("c1b", "interval", metric="mean_credit", system="subject", low=0.6, high=0.8, level=0.9),
    claim("c1c", "interval", metric="mean_credit", system="subject", low=0.1, high=0.4, level=0.9),
    claim("c2", "order", higher="sonnet-low", lower="subject", metric="mean_credit", resolved=True),
    claim("c3", "rate", metric="trivial_credit", max=0.0),
    claim("c4", "rate", metric="reference_pass_rate", min=1.0),
    claim("c5", "rate", metric="verifier_false_accept", max=0.0),
    claim("c6", "noise", metric="full_success_rate", system="subject", sd_max=0.08),
    claim("c6b", "noise", metric="full_success_rate", system="subject", sd_max=0.02),
    claim("c6c", "noise", metric="full_success_rate", system="subject", sd_max=0.01),
    claim("c7", "target", system="subject", metric="full_success_rate", low=0.2, high=0.8),
    claim("c7b", "target", system="sonnet-low", metric="full_success_rate", low=0.2, high=0.8),
    claim("c8", "cost", system="subject", profile="full", usd_max=3.0, wall_seconds_max=900),
    claim("c9", "verdict", supports_claim=False, reason="the suite is too easy"),
    claim("c10", "gap", category="floor", text="a no-op earns credit on t3"),
    claim("c11", "gap", category="hackable-task", text="t2 can be read"),
    claim("c12", "gap", category="exposure", text="material is public"),
    claim("c13", "gap", category="ceiling", text="may saturate"),
    claim("c14", "gap", category="made-up", text="?")]}


class ScoreClaimsTests(unittest.TestCase):
    def setUp(self):
        self.m9 = claims.score_claims(CARD, measured())
        self.contradicted = {c["id"]: c for c in self.m9["contradicted"]}

    def test_contradicted_claims_and_their_direction(self):
        self.assertEqual(sorted(self.contradicted), ["c1", "c1b", "c2", "c4", "c6c", "c7b", "c8"])
        self.assertEqual({k: v["direction"] for k, v in self.contradicted.items()},
                         {"c1": "measured-above", "c1b": "measured-below", "c2": "reversed", "c4": "measured-below",
                          "c6c": "measured-above", "c7b": "measured-above", "c8": "measured-above"})
        self.assertEqual(self.contradicted["c1"]["claimed"], [0.2, 0.45])
        self.assertEqual(self.contradicted["c1"]["measured"], [0.48, 0.62])
        self.assertIn("usd", self.contradicted["c8"]["reason"])

    def test_underclaim_is_an_interval_measured_above_its_claim(self):
        self.assertEqual(self.m9["underclaimed"], ["c1"])
        self.assertAlmostEqual(self.m9["underclaim_rate"], 1 / 12)

    def test_counts_and_rates(self):
        self.assertEqual((self.m9["claims"], self.m9["checkable"]), (19, 12))
        self.assertAlmostEqual(self.m9["contradiction_rate"], 7 / 12)
        self.assertEqual(self.m9["inconclusive"], ["c6b"])
        self.assertEqual(self.m9["uncheckable"], [{"id": "c5", "reason": "rate 'verifier_false_accept' was not measured"},
                                                  {"id": "c14", "reason": "unknown gap category 'made-up'"}])

    def test_interval_scores_hand_computed(self):
        scores = self.m9["interval_scores"]
        # score = width + (2 / alpha) * distance of the estimate outside the interval, alpha = 0.1
        self.assertAlmostEqual(scores["c1"]["score"], 0.25 + 20 * (0.55 - 0.45))
        self.assertAlmostEqual(scores["c1b"]["score"], 0.2 + 20 * (0.6 - 0.25))
        self.assertAlmostEqual(scores["c1c"]["score"], 0.3)
        self.assertAlmostEqual(scores["c1"]["width"], 0.25)
        self.assertEqual(sorted(scores), ["c1", "c1b", "c1c"])

    def test_gap_recall_and_precision(self):
        # measured defects: hackable-task, unresolved-contrast, floor; the card disclosed floor, hackable-task,
        # exposure (not measurable) and ceiling (measurable and absent)
        self.assertAlmostEqual(self.m9["gap_recall"], 2 / 3)
        self.assertAlmostEqual(self.m9["gap_precision"], 2 / 3)
        self.assertEqual(self.m9["disclosed_gaps"], ["ceiling", "exposure", "floor", "hackable-task"])
        self.assertEqual(sorted(self.m9["measured_gaps"]), ["floor", "hackable-task", "unresolved-contrast"])

    def test_verdict_agreement(self):
        self.assertIs(self.m9["verdict_agreement"], True)
        other = claims.score_claims(CARD, measured(verdict={"supports_claim": True}))
        self.assertIs(other["verdict_agreement"], False)
        unknown = claims.score_claims(CARD, measured(verdict={"supports_claim": None}))
        self.assertIsNone(unknown["verdict_agreement"])

    def test_no_measured_defects_leaves_recall_undefined(self):
        m9 = claims.score_claims(CARD, measured(defects={}))
        self.assertIsNone(m9["gap_recall"])
        self.assertEqual(m9["gap_precision"], 0.0)

    def test_consistent_claims_are_not_listed(self):
        for cid in ("c1c", "c3", "c6", "c7"):
            self.assertNotIn(cid, self.contradicted)
            self.assertNotIn(cid, self.m9["inconclusive"])

    def test_order_claims(self):
        card = {"claims": [claim("a", "order", higher="x", lower="y", resolved=True), claim("b", "order", higher="x", lower="y", resolved=False),
                           claim("c", "order", higher="x", lower="z", resolved=True)]}
        found = {"orders": {"a": {"outcome": "unresolved", "mean_diff": 0.0, "ci95": [-0.1, 0.1]},
                            "b": {"outcome": "unresolved", "mean_diff": 0.0, "ci95": [-0.1, 0.1]}}}
        m9 = claims.score_claims(card, found)
        self.assertEqual((m9["inconclusive"], m9["contradicted"], m9["checkable"]), (["a"], [], 2))
        self.assertEqual([u["id"] for u in m9["uncheckable"]], ["c"])
        found["orders"]["a"] = {"outcome": "higher", "mean_diff": 0.2, "ci95": [0.1, 0.3]}
        self.assertEqual(claims.score_claims(card, found)["inconclusive"], [])

    def test_cost_claims(self):
        card = {"claims": [claim("a", "cost", system="s", usd_max=3.0, wall_seconds_max=900), claim("b", "cost", system="s", usd_max=3.0, profile="smoke"),
                           claim("c", "cost", system="s", wall_seconds_max=50), claim("d", "cost", system="nobody", usd_max=1)]}
        found = {"systems": {"s": {"cost_usd": 2.0, "cost_complete": False, "wall_seconds": 80.0, "metrics": {}}}}
        m9 = claims.score_claims(card, found)
        self.assertEqual(m9["inconclusive"], ["a"])  # under the cap but some attempts have unknown cost
        self.assertEqual([c["id"] for c in m9["contradicted"]], ["c"])
        self.assertEqual(sorted(u["id"] for u in m9["uncheckable"]), ["b", "d"])
        found["systems"]["s"]["cost_complete"] = True
        self.assertEqual(claims.score_claims(card, found)["inconclusive"], [])

    def test_malformed_claims_are_uncheckable_not_errors(self):
        card = {"claims": [claim("a", "interval", metric="mean_credit", system="subject"), claim("b", "no-such-type")]}
        m9 = claims.score_claims(card, measured())
        self.assertEqual([u["id"] for u in m9["uncheckable"]], ["a", "b"])
        self.assertIs(m9["computed"], False)

    def test_vacuous_claims_are_flagged(self):
        card = {"claims": [claim("a", "interval", metric="mean_credit", system="subject", low=0.0, high=1.0),
                           claim("b", "rate", metric="trivial_credit", max=1.0),
                           claim("c", "interval", metric="mean_credit", system="subject", low=0.1, high=0.4),
                           claim("d", "rate", metric="trivial_credit", max=0.0)]}
        m9 = claims.score_claims(card, measured())
        self.assertEqual(m9["vacuous"], ["a", "b"])
        self.assertEqual(m9["contradicted"], [])

    def test_card_without_claims_is_not_computed(self):
        self.assertEqual(claims.score_claims({"claims": []}, measured()), {"computed": False, "reason": "card has no claims"})
        self.assertEqual(claims.score_claims({}, measured())["computed"], False)

    def test_no_checkable_claims_is_not_computed(self):
        card = {"claims": [claim("a", "interval", metric="mean_credit", system="ghost", low=0.1, high=0.4)]}
        m9 = claims.score_claims(card, measured())
        self.assertIs(m9["computed"], False)
        self.assertEqual(m9["reason"], "no checkable claims")
        self.assertEqual(m9["uncheckable"][0]["id"], "a")

    def test_claims_without_ids_get_positional_ids(self):
        card = {"claims": [{"type": "interval", "metric": "mean_credit", "system": "subject", "low": 0.6, "high": 0.8}]}
        self.assertEqual(claims.score_claims(card, measured())["contradicted"][0]["id"], "claim-1")


def run(values, **record):
    tasks = {t: {"source_group": t, "anchor": False, "scored": 1, "full_success_rate": v, "mean_credit": v} for t, v in values.items()}
    overall = {"full_success_rate": sum(values.values()) / len(values), "mean_credit": sum(values.values()) / len(values)}
    return {"summary": {"suite": {}, "tasks": tasks, "overall": overall, "cost": {"usd_known": 1.5, "attempts_with_unknown_cost": 0},
                        "run": {"wall_seconds": 60.0}}, **record}


TASKS = ("t1", "t2", "t3", "t4", "t5", "t6")


class MeasureTests(unittest.TestCase):
    def setUp(self):
        llm = {"kind": "llm", "mode": "single-call", "model": "claude-haiku-4-5", "effort": "low", "harness_defect": None}
        self.order = {"members": {"mH1": llm, "mH2": llm, "mHT": {**llm, "harness_defect": "truncate_busy:0.6"},
                                  "mS": {**llm, "model": "claude-sonnet-5-5"}, "mN": {"kind": "scripted", "behavior": "floor", "name": "noop"}},
                      "aa_pairs": [["mH1", "mH2"]]}
        self.card = {"conditions": {"subject": {"agent": "adapters/haiku-low", "model": "claude-haiku-4-5", "effort": "low"},
                                    "sonnet-low": {"agent": "adapters/sonnet-low", "model": "claude-sonnet-5-5", "effort": "low"},
                                    "reference": {"agent": "@reference"}, "noop": {"agent": "@noop"},
                                    "gpt": {"agent": "adapters/gpt", "model": "gpt-9", "effort": "low"}},
                     "claims": [claim("c1", "interval", metric="mean_credit", system="subject", low=0.3, high=0.6),
                                claim("c2", "order", higher="sonnet-low", lower="subject", metric="mean_credit", resolved=True),
                                claim("c3", "order", higher="gpt", lower="subject", metric="mean_credit")]}
        half = dict(zip(TASKS, (1.0, 1.0, 1.0, 0.0, 0.0, 0.0)))
        self.runs = {"mH1": run(half), "mH2": run(dict(zip(TASKS, (1.0, 1.0, 0.0, 0.0, 0.0, 0.0)))),
                     "mS": run(dict.fromkeys(TASKS, 1.0)), "mN": run({**dict.fromkeys(TASKS, 0.0), "t3": 0.3}),
                     "@reference": run({**dict.fromkeys(TASKS, 1.0), "t6": 0.0}), "@noop": run(dict.fromkeys(TASKS, 0.0))}
        self.results = {
            "M1_cheaters": {"credit_by_class": {"noop": {"members": ["mN"]}}, "hackable_tasks": ["t2"], "tasks": 4},
            "M3_kill": {"killable": 3, "killed": 2, "detail": [{"member": "d1", "killed": True}, {"member": "d2", "killed": False}]},
            "M4_contrasts": {"designated": [{"higher": "a", "lower": "b", "must_resolve": True, "resolved": False}]},
            "M6_verifier": {"positives": 10, "negatives": 8, "false_rejects": [], "false_accepts": [{"task": "t1"}]},
            "M7_task_profile": {"floor_credit": []}, "M8_range": {"ceiling_share": 0.25}}

    def test_systems_map_to_members_by_model_effort_and_builtin_agent(self):
        self.assertEqual(claims.systems(self.card, self.order),
                         {"subject": "mH1", "sonnet-low": "mS", "reference": "@reference", "noop": "@noop", "gpt": None})

    def test_system_entries(self):
        found = claims.measure(self.card, self.order, self.runs, self.results)
        subject = found["systems"]["subject"]
        self.assertEqual(subject["member"], "mH1")
        credit = subject["metrics"]["mean_credit"]
        self.assertEqual(credit["estimate"], 0.5)
        self.assertTrue(0.0 <= credit["low"] <= 0.5 <= credit["high"] <= 1.0)
        passed = subject["metrics"]["full_success_rate"]
        self.assertTrue(passed["low"] <= 0.5 <= passed["high"])
        # noise: the member and its A/A partner score 0.5 and 1/3
        self.assertEqual(subject["noise"]["mean_credit"]["n"], 2)
        self.assertAlmostEqual(subject["noise"]["mean_credit"]["sd"], (0.5 - 1 / 3) / 2 ** 0.5)
        self.assertEqual((subject["cost_usd"], subject["cost_complete"], subject["wall_seconds"]), (1.5, True, 60.0))
        self.assertIsNone(found["systems"]["gpt"])
        self.assertEqual(found["systems"]["sonnet-low"]["metrics"]["mean_credit"]["estimate"], 1.0)

    def test_order_outcomes_by_claim_id(self):
        orders = claims.measure(self.card, self.order, self.runs, self.results)["orders"]
        self.assertEqual(sorted(orders), ["c2"])
        self.assertEqual(orders["c2"]["outcome"], "higher")
        self.assertAlmostEqual(orders["c2"]["mean_diff"], 0.5)

    def test_rates_from_the_metric_results(self):
        rates = claims.measure(self.card, self.order, self.runs, self.results)["rates"]
        self.assertEqual(rates["reference_pass_rate"]["estimate"], 5 / 6)
        self.assertEqual((rates["hackable_task_ratio"]["k"], rates["hackable_task_ratio"]["n"]), (1, 4))
        self.assertAlmostEqual(rates["defect_kill_rate"]["estimate"], 2 / 3)
        self.assertAlmostEqual(rates["verifier_false_accept"]["estimate"], 1 / 8)
        self.assertEqual(rates["verifier_false_reject"]["estimate"], 0.0)
        self.assertAlmostEqual(rates["trivial_credit"]["estimate"], 0.05)

    def test_defects_found_and_categories_checked(self):
        found = claims.measure(self.card, self.order, self.runs, self.results)
        self.assertEqual(found["defects"], {
            "hackable-task": ["hackable tasks: t2"], "unresolved-contrast": ["a over b"],
            "verifier-false-accept": ["1 wrong outputs accepted"], "ceiling": ["every LLM member at ceiling on 25% of tasks"],
            "unprotected-boundary": ["defect not killed: d2"]})
        self.assertEqual(sorted(found["checked"]), sorted(claims.MEASURABLE))
        self.assertEqual(found["verdict"], {"supports_claim": None})
        self.assertEqual(claims.measure(self.card, self.order, self.runs, self.results, verdict=True)["verdict"], {"supports_claim": True})

    def test_unmeasured_metrics_are_not_checked(self):
        found = claims.measure(self.card, self.order, self.runs, {})
        self.assertEqual((found["defects"], found["checked"], found["rates"].keys() - {"reference_pass_rate"}), ({}, [], set()))

    def test_end_to_end(self):
        m9 = claims.score_claims(self.card, claims.measure(self.card, self.order, self.runs, self.results))
        self.assertEqual(m9["checkable"], 2)
        self.assertEqual([u["id"] for u in m9["uncheckable"]], ["c3"])
        self.assertEqual(m9["contradicted"], [])
        self.assertAlmostEqual(m9["interval_scores"]["c1"]["score"], 0.3)


if __name__ == "__main__":
    unittest.main()
