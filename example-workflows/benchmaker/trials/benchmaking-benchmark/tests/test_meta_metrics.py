import math
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))
sys.path.insert(0, str(HERE.parents[3] / "skills" / "benchmaker" / "scripts"))

from benchkit import stats  # noqa: E402
from metabench import metrics as scoring  # noqa: E402


def run(values, *, credit=None, anchors=(), wall=None, overlap=None, jobs=None, planned=1, **record):
    """A member run record from per-task full-success rates (credit defaults to the same values).

    Each task is its own source group. Overall metrics are plain means over the non-anchor tasks.
    """
    credit = values if credit is None else credit
    tasks = {t: {"family": "f", "source_group": t, "anchor": t in anchors, "planned": 1, "scored": 1, "full_success_rate": v,
                 "mean_credit": credit[t], "critical_failures": 0, "statuses": {"completed": 1}} for t, v in values.items()}
    scored = [t for t in tasks if t not in anchors]
    overall = {"full_success_rate": sum(values[t] for t in scored) / len(scored),
               "mean_credit": sum(credit[t] for t in scored) / len(scored)}
    summary = {"suite": {"name": "s", "tasks": len(tasks)}, "tasks": tasks, "overall": overall,
               "counts": {"planned": planned, "by_status": {"infrastructure-error": 0}},
               "run": {"wall_seconds": wall, "achieved_overlap": overlap, "jobs": jobs}}
    return {"summary": summary, **record}


def same(value, tasks=("t1", "t2", "t3", "t4", "t5", "t6")):
    return {t: value for t in tasks}


def spec(behavior, kind="scripted", **extra):
    return {"kind": kind, "behavior": behavior, **extra}


class OrderTests(unittest.TestCase):
    def chain(self, scores):
        ids = [f"m{i}" for i in range(1, len(scores) + 1)]
        runs = {m: run(same(s)) for m, s in zip(ids, scores)}
        known = [{"higher": a, "lower": b, "basis": "construction"} for i, a in enumerate(ids) for b in ids[i + 1:]]
        order = {"members": {m: spec("heuristic") for m in ids}, "known_pairs": known}
        return runs, order, ids

    def test_hand_computed_accuracy_tau_and_null(self):
        scores = [0.8, 0.9, 0.5, 0.6, 0.3, 0.1]  # two adjacent swaps in a six-member chain: 13 of 15 pairs
        runs, order, ids = self.chain(scores)
        m2 = scoring.metrics(runs, order, None, None)["M2_order"]
        self.assertEqual(m2["pairs"], 15)
        self.assertAlmostEqual(m2["pair_accuracy"], 13 / 15)
        self.assertAlmostEqual(m2["tau_b"], 11 / 15)
        self.assertAlmostEqual(m2["tau_b"], stats.kendall_tau_b([6, 5, 4, 3, 2, 1], scores))
        self.assertAlmostEqual(m2["null_p"], 20 / 720)
        self.assertEqual(m2["ci90"], [13 / 15, 13 / 15])
        self.assertEqual(m2["ties"], 0)
        self.assertEqual([(c["higher"], c["lower"]) for c in m2["contradicted"]], [("m1", "m2"), ("m3", "m4")])
        self.assertAlmostEqual(m2["contradicted"][0]["mean_diff"], -0.1)
        self.assertEqual(m2["unresolved"], [])

    def test_perfect_order_and_tie_handling(self):
        runs, order, _ = self.chain([0.9, 0.6, 0.6, 0.1])
        m2 = scoring.metrics(runs, order, None, None)["M2_order"]
        # five strict pairs correct and one tie: accuracy 5.5 / 6, tau-b 5 / sqrt(6 * 5)
        self.assertAlmostEqual(m2["pair_accuracy"], 5.5 / 6)
        self.assertAlmostEqual(m2["tau_b"], 5 / math.sqrt(30))
        self.assertAlmostEqual(m2["tau_b"], stats.kendall_tau_b([4, 3, 2, 1], [0.9, 0.6, 0.6, 0.1]))
        self.assertEqual((m2["ties"], len(m2["unresolved"])), (1, 1))

    def test_a_pair_whose_interval_spans_zero_is_unresolved_not_contradicted(self):
        x = {"t1": 0.6, "t2": 0.6, "t3": 0.6, "t4": 0.2, "t5": 0.2, "t6": 0.4}
        runs = {"x": run(x), "y": run(same(0.4))}
        order = {"members": {}, "known_pairs": [{"higher": "x", "lower": "y"}]}
        m2 = scoring.metrics(runs, order, None, None)["M2_order"]
        self.assertAlmostEqual(m2["pair_accuracy"], 1.0)
        self.assertEqual(m2["contradicted"], [])
        self.assertEqual([(u["higher"], u["lower"]) for u in m2["unresolved"]], [("x", "y")])
        self.assertLess(m2["unresolved"][0]["ci95"][0], 0)
        self.assertGreater(m2["unresolved"][0]["ci95"][1], 0)

    def test_interval_resamples_tasks_and_is_deterministic(self):
        values = {"m1": {"t1": 1.0, "t2": 1.0, "t3": 0.0, "t4": 1.0}, "m2": {"t1": 0.0, "t2": 1.0, "t3": 1.0, "t4": 0.0}}
        runs = {m: run(v) for m, v in values.items()}
        order = {"members": {}, "known_pairs": [{"higher": "m1", "lower": "m2"}]}
        first = scoring.metrics(runs, order, None, None)["M2_order"]
        self.assertEqual(first, scoring.metrics(runs, order, None, None)["M2_order"])
        low, high = first["ci90"]
        self.assertTrue(0.0 <= low <= first["pair_accuracy"] <= high <= 1.0)
        self.assertLess(low, high)

    def test_pairs_without_scores_are_listed_not_scored(self):
        runs, order, _ = self.chain([0.9, 0.5, 0.1])
        order["known_pairs"].append({"higher": "m1", "lower": "ghost"})
        order["unconfirmed"] = [{"higher": "m2", "lower": "m1"}]
        m2 = scoring.metrics(runs, order, None, None)["M2_order"]
        self.assertEqual((m2["pairs"], m2["unscorable"], m2["unconfirmed_excluded"]), (3, [["m1", "ghost"]], 1))
        none = scoring.metrics(runs, {"members": {}, "known_pairs": []}, None, None)["M2_order"]
        self.assertIs(none["computed"], False)

    def test_uses_the_requested_metric(self):
        runs = {"a": run(same(1.0), credit=same(0.2)), "b": run(same(0.0), credit=same(0.6))}
        order = {"members": {}, "known_pairs": [{"higher": "a", "lower": "b"}]}
        self.assertEqual(scoring.metrics(runs, order, None, None)["M2_order"]["pair_accuracy"], 0.0)
        self.assertEqual(scoring.metrics(runs, order, None, None, metric="full_success_rate")["M2_order"]["pair_accuracy"], 1.0)


def pool():
    """Six tasks plus an anchor, a scripted pool and the built-in runs, with known results."""
    tasks = ["t1", "t2", "t3", "t4", "t5", "t6", "a1"]
    zero = {t: 0.0 for t in tasks}
    one = {t: 1.0 for t in tasks}
    noop_credit = {**zero, "t3": 0.4}
    read = {**zero, "t2": 1.0, "t4": 1.0, "a1": 1.0}
    exit_early = {**zero, "t5": 0.5}
    ladder = {"t1": 1.0, "t2": 1.0, "t3": 0.0, "t4": 1.0, "t5": 0.0, "t6": 1.0, "a1": 1.0}
    half = {t: 0.5 for t in tasks}
    runs = {
        "mO": run(one, anchors=("a1",)), "mD1": run(zero, anchors=("a1",)), "mD2": run(one, anchors=("a1",)),
        "mD3": run(one, anchors=("a1",)), "mH": run(zero, credit=half, anchors=("a1",)),
        "mN": run(zero, credit=noop_credit, anchors=("a1",)), "mR": run(read, anchors=("a1",)),
        "mX": run(zero, credit=exit_early, anchors=("a1",)), "mL1": run(ladder, anchors=("a1",)),
        "mL2": run(ladder, anchors=("a1",)), "mE1": run(half, anchors=("a1",)), "mE2": run(zero, anchors=("a1",)),
        "@reference": run({**one, "t6": 0.0}, anchors=("a1",)), "@noop": run(zero, anchors=("a1",))}
    members = {"mO": spec("oracle"), "mD1": spec("defect", origin="synthetic"), "mD2": spec("defect", origin="synthetic"),
               "mD3": spec("defect", origin="synthetic"), "mH": spec("heuristic", origin="natural"),
               "mN": spec("floor", name="noop"), "mR": spec("cheater", name="read_ancestors"),
               "mX": spec("cheater", name="exit_early"), "mL1": spec("ladder", q=0.4), "mL2": spec("ladder", q=0.4),
               "mE1": spec("ladder", q=0.1), "mE2": spec("ladder", q=0.1)}
    order = {"members": members,
             "known_pairs": [{"higher": h, "lower": l} for h, l in (("mO", "mD1"), ("mO", "mD2"), ("mO", "mD3"), ("mO", "mH"),
                                                                     ("mH", "mD1"), ("mH", "mN"))],
             "contrasts": [{"higher": "mO", "lower": "mN", "must_resolve": True}, {"higher": "mO", "lower": "mD2", "must_resolve": True},
                           {"higher": "mO", "lower": "mH", "must_resolve": False}],
             "aa_pairs": [["mL1", "mL2"], ["mE1", "mE2"]],
             "killable": {"mD1": {"basis": "checker", "confirmed": True}, "mD2": {"basis": "checker", "confirmed": True},
                          "mD3": {"basis": "checker", "confirmed": False}, "mH": {"basis": "slice", "confirmed": True}}}
    return runs, order


class KillAndContrastTests(unittest.TestCase):
    def setUp(self):
        self.runs, self.order = pool()
        label = lambda *labels: {"t%d" % (i + 1): [{"label": l, "recognized": True}] for i, l in enumerate(labels)}  # noqa: E731
        self.captures = {"mD1": {**label(*["invalid"] * 6), "t7": [{"label": "invalid", "recognized": False}]},
                         "mD2": label(*["valid"] * 6), "mH": label("valid", "valid", "valid", "suboptimal", "suboptimal", "suboptimal")}
        self.result = scoring.metrics(self.runs, self.order, None, self.captures)

    def test_kill_rate_by_origin_and_exclusions(self):
        m3 = self.result["M3_kill"]
        self.assertEqual((m3["killable"], m3["killed"]), (3, 2))
        self.assertAlmostEqual(m3["rate"], 2 / 3)
        self.assertEqual(m3["killed_members"], ["mD1", "mH"])
        self.assertEqual(m3["excluded_equivalent"], ["mD3"])
        self.assertEqual(m3["by_origin"], {"natural": 1.0, "synthetic": 0.5})
        low, high = m3["ci90"]
        self.assertTrue(low < 2 / 3 < high)

    def test_kill_p_is_one_sided_sign_flip(self):
        by_member = {d["member"]: d for d in self.result["M3_kill"]["detail"]}
        self.assertAlmostEqual(by_member["mD1"]["p"], 1 / 64)
        self.assertAlmostEqual(by_member["mH"]["p"], 1 / 64)
        self.assertEqual(by_member["mD2"]["p"], 1.0)
        self.assertEqual(by_member["mD1"]["against"], "mO")
        self.assertEqual(by_member["mD1"]["ci95"], [1.0, 1.0])

    def test_inert_defect_is_not_killed_and_shows_in_exercised_share(self):
        m3 = self.result["M3_kill"]
        self.assertNotIn("mD2", m3["killed_members"])
        self.assertEqual(m3["exercised_share"], {"mD1": 1.0, "mD2": 0.0, "mH": 0.5})

    def test_no_confirmed_killable_defect_is_not_computed(self):
        order = {**self.order, "killable": {"mD1": {"confirmed": False}}}
        m3 = scoring.metrics(self.runs, order, None, None)["M3_kill"]
        self.assertIs(m3["computed"], False)
        self.assertEqual(m3["excluded_equivalent"], ["mD1"])
        self.assertEqual(m3["excluded_unconfirmed"], ["mD2", "mD3"])

    def test_designated_contrasts_and_aa_false_separation(self):
        m4 = self.result["M4_contrasts"]
        by_pair = {(d["higher"], d["lower"]): d for d in m4["designated"]}
        self.assertTrue(by_pair["mO", "mN"]["resolved"])
        self.assertFalse(by_pair["mO", "mD2"]["resolved"])
        self.assertTrue(by_pair["mO", "mH"]["resolved"] and not by_pair["mO", "mH"]["must_resolve"])
        self.assertAlmostEqual(m4["resolution_recall"], 0.5)
        pairs = {tuple(a["pair"]): a for a in m4["aa_pairs"]}
        self.assertEqual(pairs["mL1", "mL2"]["p"], 1.0)
        self.assertAlmostEqual(pairs["mE1", "mE2"]["p"], 2 / 64)
        self.assertAlmostEqual(m4["aa_false_separation"], 0.5)

    def test_identical_aa_pairs_give_no_false_separation(self):
        order = {**self.order, "aa_pairs": [["mL1", "mL2"], ["mO", "mD2"]]}
        m4 = scoring.metrics(self.runs, order, None, None)["M4_contrasts"]
        self.assertEqual(m4["aa_false_separation"], 0.0)

    def test_reversed_contrast_is_reported(self):
        order = {**self.order, "contrasts": [{"higher": "mD1", "lower": "mO", "must_resolve": True}]}
        m4 = scoring.metrics(self.runs, order, None, None)["M4_contrasts"]
        self.assertEqual((m4["resolution_recall"], m4["reversed"]), (0.0, [["mD1", "mO"]]))

    def test_nothing_designated_is_not_computed(self):
        order = {**self.order, "contrasts": [], "aa_pairs": []}
        self.assertIs(scoring.metrics(self.runs, order, None, None)["M4_contrasts"]["computed"], False)


class CheaterAndProfileTests(unittest.TestCase):
    def setUp(self):
        self.runs, self.order = pool()
        self.result = scoring.metrics(self.runs, self.order, None, None)

    def test_hackable_tasks_and_ratio(self):
        m1 = self.result["M1_cheaters"]
        # t2 and t4: read_ancestors full success; t5: exit_early credit 0.5 = half the oracle's; t3: 0.4 is below half
        self.assertEqual(m1["hackable_tasks"], ["t2", "t4", "t5"])
        self.assertEqual(m1["hackable_by"], {"t2": ["mR"], "t4": ["mR"], "t5": ["mX"]})
        self.assertEqual((m1["tasks"], m1["oracle"]), (6, "mO"))
        self.assertAlmostEqual(m1["hackable_task_ratio"], 0.5)
        self.assertTrue(m1["ci90"][0] < 0.5 < m1["ci90"][1])

    def test_credit_by_class_is_relative_to_the_oracle(self):
        classes = self.result["M1_cheaters"]["credit_by_class"]
        self.assertEqual(sorted(classes), ["@noop", "exit_early", "noop", "read_ancestors"])
        self.assertAlmostEqual(classes["read_ancestors"]["mean_credit"], 2 / 6)
        self.assertAlmostEqual(classes["read_ancestors"]["relative_to_oracle"], 2 / 6)
        self.assertAlmostEqual(classes["noop"]["mean_credit"], 0.4 / 6)
        self.assertEqual(classes["@noop"]["mean_credit"], 0.0)
        self.assertEqual((classes["noop"]["role"], classes["exit_early"]["role"]), ("floor", "cheater"))

    def test_anchor_tasks_do_not_count(self):
        # read_ancestors earns full success on the anchor a1
        self.assertNotIn("a1", self.result["M1_cheaters"]["hackable_tasks"])

    def test_no_trivial_members_is_not_computed(self):
        order = {"members": {"mO": spec("oracle")}, "known_pairs": []}
        self.assertIs(scoring.metrics({"mO": self.runs["mO"]}, order, None, None)["M1_cheaters"]["computed"], False)

    def test_task_profile(self):
        m7 = self.result["M7_task_profile"]
        self.assertEqual(m7["reference_fail"], ["t6"])
        self.assertEqual([(r["task"], r["members"], r["max_credit"]) for r in m7["floor_credit"]],
                         [("t2", ["mR"], 1.0), ("t3", ["mN"], 0.4), ("t4", ["mR"], 1.0), ("t5", ["mX"], 0.5)])
        self.assertEqual(m7["flat"], [])
        self.assertEqual(m7["inverted"], [])
        self.assertAlmostEqual(m7["informative_share"], 1 / 6)
        self.assertEqual(m7["flags_used"], ["reference_fail", "floor_credit", "flat", "inverted"])

    def test_flat_task_has_no_spread_among_attempting_members(self):
        runs = {"a": run({"t1": 1.0, "t2": 1.0}), "b": run({"t1": 1.0, "t2": 0.0}), "c": run({"t1": 0.0, "t2": 0.0})}
        order = {"members": {"a": spec("oracle"), "b": spec("defect"), "c": spec("floor", name="noop")}, "known_pairs": []}
        m7 = scoring.metrics(runs, order, None, None)["M7_task_profile"]
        self.assertEqual(m7["flat"], ["t1"])  # a and b tie on t1 and differ on t2; the floor does not count as attempting
        self.assertEqual(m7["tasks"], 2)
        runs["b"] = run({"t1": 1.0, "t2": 1.0})
        self.assertEqual(scoring.metrics(runs, order, None, None)["M7_task_profile"]["flat"], ["t1", "t2"])
        self.assertIs(scoring.metrics(runs, order, None, None)["M7_task_profile"]["inverted"]["computed"], False)

    def test_inversions_beyond_the_noise_floor(self):
        runs = {"hi": run({"t1": 0.0, "t2": 0.2, "t3": 1.0}), "lo": run({"t1": 1.0, "t2": 0.8, "t3": 0.0}),
                "a": run({"t1": 0.5, "t2": 0.5, "t3": 0.5}), "b": run({"t1": 0.5, "t2": 0.5, "t3": 0.9})}
        order = {"members": {m: spec("heuristic") for m in runs}, "known_pairs": [{"higher": "hi", "lower": "lo"}],
                 "aa_pairs": [["a", "b"]]}
        m7 = scoring.metrics(runs, order, None, None)["M7_task_profile"]
        # lo beats hi by 1.0 on t1 and 0.6 on t2; the A/A pair differs by 0.4 only on t3, so the margin is 0 on t1 and t2
        self.assertEqual(m7["inverted"], [{"task": "t1", "pairs": [["hi", "lo"]]}, {"task": "t2", "pairs": [["hi", "lo"]]}])
        order["aa_pairs"] = [["a", "b"], ["hi", "a"]]  # hi/a differ by 0.5, 0.3, 0.5: margin 0.5 on t1 and 0.3 on t2
        m7 = scoring.metrics(runs, order, None, None)["M7_task_profile"]
        self.assertEqual([r["task"] for r in m7["inverted"]], ["t1", "t2"])
        order["aa_pairs"] = [["a", "b"], ["hi", "lo"]]  # margin 1.0 / 0.6 / 1.0 swallows both inversions
        self.assertEqual(scoring.metrics(runs, order, None, None)["M7_task_profile"]["inverted"], [])


class RangeReliabilityAndSpeedTests(unittest.TestCase):
    def test_llm_range_and_floor_ceiling(self):
        tasks = ("t1", "t2", "t3", "t4")
        runs = {"L1": run(dict(zip(tasks, (0.0, 0.0, 1.0, 1.0)))), "L2": run(dict(zip(tasks, (0.0, 1.0, 1.0, 1.0)))),
                "L3": run(dict(zip(tasks, (0.0, 0.0, 0.0, 1.0))))}
        order = {"members": {m: {"kind": "llm", "model": "x", "effort": "low", "harness_defect": None} for m in runs}}
        m8 = scoring.metrics(runs, order, None, None)["M8_range"]
        self.assertEqual(m8["members"], {"L1": 0.5, "L2": 0.75, "L3": 0.25})
        self.assertEqual((m8["min"], m8["max"], m8["range"]), (0.25, 0.75, 0.5))
        self.assertEqual((m8["floor_share"], m8["ceiling_share"], m8["tasks"]), (0.25, 0.25, 4))
        self.assertEqual((m8["weakest"], m8["strongest"]), ("L3", "L2"))

    def test_saturated_member_is_not_the_strongest_non_degenerate_one(self):
        runs = {"L1": run(same(1.0)), "L2": run(same(0.5)), "L3": run(same(0.0))}
        order = {"members": {m: {"kind": "llm", "model": "x", "effort": "low"} for m in runs}}
        m8 = scoring.metrics(runs, order, None, None)["M8_range"]
        self.assertEqual((m8["weakest"], m8["strongest"]), ("L2", "L2"))

    def test_no_llm_members_is_not_computed(self):
        runs, order = pool()
        m8 = scoring.metrics(runs, order, None, None)["M8_range"]
        self.assertEqual(m8, {"computed": False, "reason": "no LLM members"})

    def test_reliability_needs_a_second_full_run(self):
        runs, order = pool()
        self.assertEqual(scoring.metrics(runs, order, None, None)["M5_reliability"],
                         {"computed": False, "reason": "single full run per member"})

    def test_hand_computed_reliability(self):
        def member(first, second):
            return {**run(same(first)), "replicates": [run(same(second))["summary"]]}
        runs = {"a": member(0.8, 0.6), "b": member(0.5, 0.5), "c": member(0.2, 0.4)}
        m5 = scoring.metrics(runs, {"members": {}}, None, None)["M5_reliability"]
        self.assertEqual((m5["members"], m5["test_retest_tau_b"], m5["decision_accuracy"]), (3, 1.0, 1.0))
        self.assertAlmostEqual(m5["noise_sd"]["a"], 0.2 / math.sqrt(2))
        self.assertEqual(m5["noise_sd"]["b"], 0.0)
        self.assertAlmostEqual(m5["pooled_sd"], math.sqrt(0.04 / 3))
        self.assertAlmostEqual(m5["snr"], 0.4 / math.sqrt(0.04 / 3))
        runs["c"] = member(0.2, 0.9)  # swaps c above a and b between runs
        swapped = scoring.metrics(runs, {"members": {}}, None, None)["M5_reliability"]
        self.assertAlmostEqual(swapped["decision_accuracy"], 1 / 3)

    def test_speed_prefers_the_meta_verifiers_own_measurements(self):
        runs = {"A": run(same(1.0), wall=100.0, overlap=7.0, jobs=8, wall_seconds=140.0,
                         invocations=[{"seconds": 300.0}, {"seconds": 400.0}]),
                "B": run(same(1.0), wall=50.0, overlap=4.0, jobs=8, invocations=[{"seconds": 150.0}, {"seconds": 50.0}]),
                "@reference": run(same(1.0), wall=10.0, jobs=2)}
        speed = scoring.metrics(runs, {"members": {}}, None, None)["speed"]
        self.assertEqual(speed["full_wall_seconds"], {"A": 140.0, "B": 50.0, "@reference": 10.0})
        self.assertAlmostEqual(speed["achieved_overlap_reported"], 5.5)
        self.assertAlmostEqual(speed["achieved_overlap_measured"], 4.5)
        self.assertEqual(speed["declared_concurrency"], 8)
        self.assertEqual(speed["overlap_by_member"]["A"], {"reported": 7.0, "measured": 5.0})

    def test_verifier_metric_is_passed_through(self):
        runs, order = pool()
        m6 = {"tpr": 1.0, "tnr": 0.5}
        self.assertEqual(scoring.metrics(runs, order, m6, None)["M6_verifier"], m6)
        self.assertIs(scoring.metrics(runs, order, None, None)["M6_verifier"]["computed"], False)

    def test_blocked_leaves_every_metric_undefined(self):
        blocked = scoring.blocked("G1 failed")
        self.assertEqual(sorted(blocked), sorted(scoring.metrics(*pool(), None, None)))
        self.assertTrue(all(v == {"computed": False, "reason": "G1 failed"} for v in blocked.values()))

    def test_scoring_constants_are_echoed(self):
        names = {c["name"]: c["value"] for c in scoring.conditions()}
        self.assertEqual((names["alpha"], names["hackable_fraction"], names["interval_level"]), (0.05, 0.5, 0.9))


def reference(passes, tasks=("t1", "t2", "t3", "t4")):
    return run({t: 1.0 if t in passes else 0.0 for t in tasks})


class GateTests(unittest.TestCase):
    def execs(self, **members):
        return {"preflight": {"exit_code": 0}, "members": members}

    def member(self, **extra):
        return {"exit_code": 0, "status": "completed", "schema_valid": True, "planned": 6, "infrastructure_errors": 0, **extra}

    def gates(self, execs=None, ref=None, noop=None, cross=None, staging=None):
        return scoring.gates(execs or self.execs(m1=self.member()), ref or reference("t1 t2 t3 t4".split()),
                             noop or reference([]), cross if cross is not None else {"count_mismatches": [], "grade_mismatches": []},
                             [] if staging is None else staging)

    def test_clean_run_passes_every_gate(self):
        result = self.gates(self.execs(m1=self.member(), m2=self.member()))
        self.assertTrue(scoring.gates_pass(result))
        g1 = result["G1_executability"]
        self.assertEqual((g1["pass"], g1["preflight_exit"], g1["member_runs"], g1["schema_valid_share"], g1["infrastructure_error_share"]),
                         (True, 0, 2, 1.0, 0.0))
        g2 = result["G2_reference_and_floor"]
        self.assertEqual((g2["pass"], g2["reference_pass_rate"], g2["noop_full_success_tasks"], g2["noop_mean_credit"]), (True, 1.0, [], 0.0))
        self.assertEqual(result["crosscheck"], {"count_mismatches": [], "grade_mismatches": [], "pass": True})
        self.assertEqual(result["staging"], {"pass": True, "cheater_findings": [], "warnings": []})

    def test_infrastructure_share_counts_killed_runs_as_all_infrastructure_errors(self):
        execs = self.execs(m1=self.member(), m2=self.member(infrastructure_errors=3),
                           m3=self.member(status="timeout", exit_code=None, schema_valid=False, reason="killed at the cap"))
        g1 = self.gates(execs)["G1_executability"]
        self.assertAlmostEqual(g1["infrastructure_error_share"], (0 + 3 + 6) / 18)
        self.assertAlmostEqual(g1["schema_valid_share"], 2 / 3)
        self.assertEqual(g1["failed_runs"], [{"member": "m3", "reason": "killed at the cap"}])
        self.assertFalse(g1["pass"])

    def test_a_few_infrastructure_errors_are_tolerated_but_many_fail(self):
        small = self.gates(self.execs(m1=self.member(planned=100, infrastructure_errors=5)))["G1_executability"]
        self.assertEqual((small["pass"], small["infrastructure_error_share"]), (True, 0.05))
        big = self.gates(self.execs(m1=self.member(planned=100, infrastructure_errors=6)))["G1_executability"]
        self.assertFalse(big["pass"])

    def test_counts_default_from_the_summary(self):
        summary = run(same(1.0), planned=24)["summary"]
        summary["counts"]["by_status"]["infrastructure-error"] = 3
        entry = {"exit_code": 0, "status": "completed", "schema_valid": True, "summary": summary}
        g1 = self.gates(self.execs(m1=entry))["G1_executability"]
        self.assertAlmostEqual(g1["infrastructure_error_share"], 3 / 24)

    def test_failed_preflight_invalid_records_and_nonzero_exit_fail(self):
        failing = scoring.gates({"preflight": {"exit_code": 2}, "members": {"m1": self.member()}}, reference(["t1", "t2", "t3", "t4"]),
                                reference([]), {}, [])["G1_executability"]
        self.assertFalse(failing["pass"])
        self.assertIn("preflight exit 2", failing["reasons"])
        self.assertFalse(self.gates(self.execs(m1=self.member(schema_valid=False)))["G1_executability"]["pass"])
        self.assertFalse(self.gates(self.execs(m1=self.member(exit_code=4)))["G1_executability"]["pass"])
        self.assertFalse(scoring.gates({}, None, None, None, None)["G1_executability"]["pass"])

    def test_reference_that_misses_a_task_fails(self):
        g2 = self.gates(ref=reference(["t1", "t2", "t3"]))["G2_reference_and_floor"]
        self.assertEqual((g2["pass"], g2["reference_pass_rate"], g2["reference_failed_tasks"]), (False, 0.75, ["t4"]))

    def test_a_noop_that_earns_anything_fails(self):
        g2 = self.gates(noop=reference(["t2"]))["G2_reference_and_floor"]
        self.assertEqual((g2["pass"], g2["noop_full_success_tasks"], g2["noop_mean_credit"]), (False, ["t2"], 0.25))
        partial = run(same(0.0, ("t1", "t2")), credit=same(0.3, ("t1", "t2")))
        g2 = self.gates(noop=partial)["G2_reference_and_floor"]
        self.assertEqual((g2["pass"], g2["noop_full_success_tasks"]), (False, []))

    def test_missing_runs_fail_the_floor_gate(self):
        g2 = scoring.gates(self.execs(m1=self.member()), None, None, {}, [])["G2_reference_and_floor"]
        self.assertEqual((g2["pass"], g2["reasons"]), (False, ["reference run missing", "no-op run missing"]))

    def test_crosscheck_mismatches_and_staging_findings_fail(self):
        mismatch = {"count_mismatches": [{"member": "m1", "task": "t1"}], "grade_mismatches": [], "unmatched": 1}
        cross = self.gates(cross=mismatch)["crosscheck"]
        self.assertEqual((cross["pass"], cross["unmatched"], len(cross["count_mismatches"])), (False, 1, 1))
        self.assertFalse(self.gates(cross={"count_mismatches": [], "grade_mismatches": [{"task": "t2"}]})["crosscheck"]["pass"])
        found = [{"member": "mR", "path": "../tests/expected.json"}]
        self.assertEqual(self.gates(staging=found)["staging"], {"pass": False, "cheater_findings": found, "warnings": []})
        self.assertFalse(self.gates(staging={"cheater_findings": found})["staging"]["pass"])
        self.assertFalse(scoring.gates(self.execs(m1=self.member()), reference(["t1"]), reference([]), None, None)["crosscheck"]["pass"])
        self.assertFalse(scoring.gates(self.execs(m1=self.member()), reference(["t1"]), reference([]), {}, None)["staging"]["pass"])


if __name__ == "__main__":
    unittest.main()
