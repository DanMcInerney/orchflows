import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from benchkit import aggregate  # noqa: E402

DIMENSIONS = {"valid": {"credit": 1.0, "weight": 0.5, "required": True},
              "optimal": {"credit": 0.5, "weight": 0.5, "required": True}}


def row(task, repeat, status="completed", *, retry=0, full=None, credit=None, reason="", cost=0.01, seconds=10.0,
        **extra):
    scored = full is not None
    return {"task": task, "repeat": repeat, "retry": retry, "status": status, "reason": reason, "seconds": seconds,
            "cost_usd": cost, "grading_status": "scored" if scored else "unscored", "full_success": full,
            "credit": credit, "dimensions": {}, "critical_failures": [], **extra}


TASKS = {"t01": {"family": "alpha", "source_group": "g1", "anchor": False},
         "t02": {"family": "alpha", "source_group": "g1", "anchor": False},
         "t03": {"family": "beta", "source_group": "g2", "anchor": False}}

ATTEMPTS = [
    row("t01", 1, full=True, credit=1.0), row("t01", 2, full=False, credit=0.5), row("t01", 3, full=False, credit=0.0),
    row("t02", 1, full=True, credit=1.0, cost=0.02),
    row("t02", 2, "agent-budget-exhausted", full=False, credit=0.2, cost=0.02),
    row("t02", 3, "infrastructure-error", retry=0, cost=None, reason="api 529"),
    row("t02", 3, retry=1, full=True, credit=0.8, cost=0.02),
    row("t03", 1, full=False, credit=0.4, cost=0.05, critical_failures=["deleted calendar"]),
    row("t03", 2, "canceled", cost=None, reason="deadline"),
    row("t03", 3, "not-launched", cost=None, seconds=0.0, reason="deadline"),
]
RUN = {"profile": "full", "agent": "adapters/x", "repeats": 3, "jobs": 3, "started": "2026-10-02T10:00:00Z",
       "finished": "2026-10-02T10:00:30Z", "suite_name": "mini", "peak_concurrency": 3, "deadline_reached": True,
       "observed_versions": {"python --version": "Python 3.14.6"}, "setup_seconds": 2.0, "grading_seconds": 3.0}


class ValidateGradeTests(unittest.TestCase):
    def raw(self, **fields):
        return {"grading_status": "scored", "full_success": True, "credit": 0.75, "dimensions": DIMENSIONS,
                "critical_failures": [], "reason": "", **fields}

    def test_scored_grade_derives_credit_from_dimensions(self):
        grade = aggregate.validate_grade(self.raw())
        self.assertEqual((grade["grading_status"], grade["full_success"], grade["credit"]), ("scored", True, 0.75))
        self.assertEqual(grade["credit_bounds"], [0.75, 0.75])
        self.assertAlmostEqual(aggregate.validate_grade(self.raw(credit=None))["credit"], 0.75)

    def test_validation_is_idempotent(self):
        once = aggregate.validate_grade(self.raw())
        self.assertEqual(aggregate.validate_grade(once), once)
        unscored = aggregate.validate_grade(None, "verifier exited 1")
        self.assertEqual(aggregate.validate_grade(unscored), unscored)

    def test_missing_result_is_unscored_with_reason(self):
        grade = aggregate.validate_grade(None, "verifier exited 1")
        self.assertEqual((grade["grading_status"], grade["reason"], grade["credit"]), ("unscored", "verifier exited 1", None))
        self.assertEqual(aggregate.validate_grade("junk")["grading_status"], "unscored")

    def test_indeterminate_passes_through(self):
        grade = aggregate.validate_grade({"grading_status": "indeterminate", "reason": "judge unavailable"})
        self.assertEqual((grade["grading_status"], grade["reason"], grade["full_success"]),
                         ("indeterminate", "judge unavailable", None))

    def test_unjudged_required_dimension_leaves_credit_unavailable_with_bounds(self):
        dims = {"valid": {"credit": 1.0, "weight": 0.5, "required": True},
                "optimal": {"credit": None, "weight": 0.5, "required": True}}
        grade = aggregate.validate_grade(self.raw(credit=None, dimensions=dims, full_success=False))
        self.assertEqual(grade["grading_status"], "scored")
        self.assertIsNone(grade["credit"])
        self.assertEqual(grade["credit_bounds"], [0.5, 1.0])

    def test_unjudged_optional_dimension_earns_nothing(self):
        dims = {"valid": {"credit": 1.0, "weight": 0.5, "required": True},
                "style": {"credit": None, "weight": 0.5, "required": False}}
        grade = aggregate.validate_grade(self.raw(credit=None, dimensions=dims))
        self.assertEqual((grade["credit"], grade["credit_bounds"]), (0.5, [0.5, 0.5]))

    def test_contract_violations_are_indeterminate(self):
        bad_weights = {"a": {"credit": 1.0, "weight": 0.5}, "b": {"credit": 1.0, "weight": 0.6}}
        cases = {
            "critical failure with full success": self.raw(critical_failures=["data loss"]),
            "weights": self.raw(credit=None, dimensions=bad_weights),
            "negative weight": self.raw(credit=None, dimensions={"a": {"credit": 1.0, "weight": -1.0},
                                                                  "b": {"credit": 1.0, "weight": 2.0}}),
            "credit above one": self.raw(credit=1.5, dimensions={}),
            "dimension credit below zero": self.raw(credit=None, dimensions={"a": {"credit": -0.1, "weight": 1.0}}),
            "credit disagrees": self.raw(credit=0.9),
            "credit with unjudged required": self.raw(
                credit=0.5, dimensions={"a": {"credit": None, "weight": 1.0, "required": True}}),
            "full_success missing": self.raw(full_success=None),
            "full_success not boolean": self.raw(full_success=1),
            "bad status": self.raw(grading_status="maybe"),
        }
        for name, raw in cases.items():
            with self.subTest(name):
                grade = aggregate.validate_grade(raw)
                self.assertEqual(grade["grading_status"], "indeterminate")
                self.assertTrue(grade["reason"].startswith("contract violation"), grade["reason"])
                self.assertIsNone(grade["credit"])

    def test_credit_without_dimensions_and_critical_failure_on_a_failure(self):
        grade = aggregate.validate_grade({"grading_status": "scored", "full_success": False, "credit": 0.25,
                                          "critical_failures": ["x"]})
        self.assertEqual((grade["grading_status"], grade["credit"], grade["critical_failures"]), ("scored", 0.25, ["x"]))
        bare = aggregate.validate_grade({"grading_status": "scored", "full_success": False, "credit": None})
        self.assertEqual((bare["credit"], bare["credit_bounds"]), (None, [0.0, 1.0]))


class TaskMetricsTests(unittest.TestCase):
    def test_repeats_average_within_the_task(self):
        m = aggregate.task_metrics([a for a in ATTEMPTS if a["task"] == "t02"], 3)
        self.assertEqual((m["planned"], m["scored"], m["passed"], m["failed"], m["missing_repeats"]), (3, 3, 2, 1, 0))
        self.assertAlmostEqual(m["full_success_rate"], 2 / 3)
        self.assertAlmostEqual(m["mean_credit"], (1.0 + 0.2 + 0.8) / 3)
        self.assertEqual(m["statuses"], {"completed": 2, "agent-budget-exhausted": 1})
        self.assertEqual(m["excluded"], [])

    def test_final_attempt_decides_and_unscored_repeats_are_listed(self):
        m = aggregate.task_metrics([a for a in ATTEMPTS if a["task"] == "t03"], 3)
        self.assertEqual((m["scored"], m["missing_repeats"], m["passed"], m["failed"]), (1, 2, 0, 1))
        self.assertEqual(m["full_success_rate"], 0.0)
        self.assertEqual(m["critical_failures"], 1)
        self.assertEqual(m["excluded"], [{"repeat": 2, "reason": "canceled: deadline"},
                                         {"repeat": 3, "reason": "not-launched: deadline"}])

    def test_critical_failure_defeats_full_success(self):
        m = aggregate.task_metrics([row("t", 1, full=True, credit=1.0, critical_failures=["lost state"])], 1)
        self.assertEqual((m["passed"], m["failed"], m["critical_failures"], m["full_success_rate"]), (0, 1, 1, 0.0))

    def test_refused_and_cut_off_are_graded_like_delivered_work(self):
        m = aggregate.task_metrics([row("t", 1, "refused", full=False, credit=0.0),
                                    row("t", 2, "cut-off", full=False, credit=0.5)], 2)
        self.assertEqual((m["scored"], m["failed"], m["mean_credit"]), (2, 2, 0.25))
        self.assertEqual(m["statuses"], {"refused": 1, "cut-off": 1})

    def test_interrupted_and_missing_repeats_are_unscored(self):
        m = aggregate.task_metrics([row("t", 1, "interrupted", reason="usage limit")], 2)
        self.assertEqual((m["scored"], m["full_success_rate"], m["mean_credit"], m["credit_bounds"]), (0, None, None, None))
        self.assertEqual(m["statuses"], {"interrupted": 1, "not-launched": 1})
        self.assertEqual([e["reason"] for e in m["excluded"]], ["interrupted: usage limit", "not-launched: no attempt record"])

    def test_scored_status_with_unscored_grade_is_excluded_with_reason(self):
        crashed = row("t", 1, "completed", reason="", grade_reason="verifier crashed")
        m = aggregate.task_metrics([crashed], 1)
        self.assertEqual(m["scored"], 0)
        self.assertEqual(m["excluded"], [{"repeat": 1, "reason": "completed, grading unscored: verifier crashed"}])

    def test_unjudged_dimension_gives_bounds(self):
        dims = {"valid": {"credit": 1.0, "weight": 0.5, "required": True},
                "optimal": {"credit": None, "weight": 0.5, "required": True}}
        m = aggregate.task_metrics([row("t", 1, full=False, credit=None, dimensions=dims),
                                    row("t", 2, full=True, credit=1.0)], 2)
        self.assertIsNone(m["mean_credit"])
        self.assertEqual(m["credit_bounds"], [0.75, 1.0])

    def test_rejects_foreign_repeat_and_unknown_status(self):
        with self.assertRaises(ValueError):
            aggregate.task_metrics([row("t", 4, full=True, credit=1.0)], 3)
        with self.assertRaises(ValueError):
            aggregate.task_metrics([row("t", 1, "exploded")], 1)


class SummarizeTests(unittest.TestCase):
    def setUp(self):
        self.summary = aggregate.summarize(ATTEMPTS, TASKS, RUN)

    def test_counts_use_units_for_quality_and_attempts_for_launches(self):
        counts = self.summary["counts"]
        self.assertEqual({k: v for k, v in counts.items() if k != "by_status"},
                         {"planned": 9, "launched": 9, "completed": 6, "scored": 7, "passed": 3, "failed": 4,
                          "unscored": 2, "canceled": 1, "not_launched": 1, "retries": 1})
        self.assertEqual(counts["by_status"], {"completed": 6, "refused": 0, "cut-off": 0, "agent-budget-exhausted": 1,
                                               "infrastructure-error": 0, "canceled": 1, "interrupted": 0,
                                               "not-launched": 1})
        self.assertEqual(counts["scored"] + counts["unscored"], counts["planned"])
        self.assertEqual(counts["passed"] + counts["failed"], counts["scored"])

    def test_overall_and_family_metrics(self):
        overall = self.summary["overall"]
        self.assertAlmostEqual(overall["full_success_rate"], (1 / 3 + 2 / 3 + 0.0) / 3)
        self.assertAlmostEqual(overall["mean_credit"], (0.5 + 2 / 3 + 0.4) / 3)
        self.assertEqual({k: overall[k] for k in ("critical_failures", "scored_tasks", "missing_repeats",
                                                  "anchors_excluded")}, {"critical_failures": 1, "scored_tasks": 3,
                                                                          "missing_repeats": 2, "anchors_excluded": 0})
        self.assertAlmostEqual(overall["credit_bounds"][0], overall["mean_credit"])
        self.assertAlmostEqual(overall["credit_bounds"][1], overall["mean_credit"])
        alpha, beta = self.summary["families"]["alpha"], self.summary["families"]["beta"]
        self.assertAlmostEqual(alpha["full_success_rate"], 0.5)
        self.assertAlmostEqual(alpha["mean_credit"], (0.5 + 2 / 3) / 2)
        self.assertEqual((beta["full_success_rate"], beta["mean_credit"], beta["critical_failures"]), (0.0, 0.4, 1))
        self.assertEqual(sorted(self.summary["families"]), ["alpha", "beta"])

    def test_task_entries(self):
        t = self.summary["tasks"]
        self.assertEqual(sorted(t["t01"]), sorted(["family", "source_group", "anchor", "planned", "scored",
                                                   "full_success_rate", "mean_credit", "critical_failures", "statuses"]))
        self.assertAlmostEqual(t["t01"]["full_success_rate"], 1 / 3)
        self.assertEqual(t["t01"]["mean_credit"], 0.5)
        self.assertEqual(t["t02"]["statuses"], {"completed": 2, "agent-budget-exhausted": 1})
        self.assertEqual((t["t03"]["scored"], t["t03"]["critical_failures"], t["t03"]["source_group"]), (1, 1, "g2"))

    def test_run_cost_time_and_exclusions(self):
        run = self.summary["run"]
        self.assertEqual((run["profile"], run["repeats"], run["jobs"], run["wall_seconds"], run["peak_concurrency"],
                          run["attempt_seconds_sum"], run["achieved_overlap"], run["deadline_reached"]),
                         ("full", 3, 3, 30.0, 3, 90.0, 3.0, True))
        self.assertEqual(run["observed_versions"], {"python --version": "Python 3.14.6"})
        self.assertEqual(self.summary["suite"], {"name": "mini", "tasks": 3})
        self.assertAlmostEqual(self.summary["cost"]["usd_known"], 0.14)
        self.assertEqual(self.summary["cost"]["attempts_with_unknown_cost"], 2)
        self.assertEqual(self.summary["time"], {"setup_seconds": 2.0, "execution_seconds": 25.0, "grading_seconds": 3.0,
                                                "total_seconds": 30.0})
        self.assertEqual(self.summary["exclusions"], [
            {"task": "t03", "repeat": 2, "reason": "canceled: deadline"},
            {"task": "t03", "repeat": 3, "reason": "not-launched: deadline"}])

    def test_summary_has_the_published_keys(self):
        self.assertEqual(list(self.summary), ["suite", "run", "counts", "overall", "families", "tasks", "cost", "time",
                                              "exclusions"])
        self.assertEqual(list(self.summary["run"]), ["profile", "agent", "repeats", "jobs", "started", "finished",
                                                     "wall_seconds", "attempt_seconds_sum", "achieved_overlap",
                                                     "peak_concurrency", "deadline_reached", "observed_versions"])
        self.assertEqual(list(self.summary["overall"]), ["full_success_rate", "mean_credit", "credit_bounds",
                                                         "critical_failures", "scored_tasks", "missing_repeats",
                                                         "anchors_excluded"])

    def test_declared_weights_apply_to_task_averages(self):
        weights = {"t01": 0.2, "t02": 0.2, "t03": 0.6}
        s = aggregate.summarize(ATTEMPTS, TASKS, RUN, weights=weights)
        self.assertAlmostEqual(s["overall"]["full_success_rate"], 0.2 / 3 + 0.2 * 2 / 3)
        self.assertAlmostEqual(s["overall"]["mean_credit"], 0.2 * 0.5 + 0.2 * 2 / 3 + 0.6 * 0.4)
        self.assertAlmostEqual(s["families"]["alpha"]["mean_credit"], (0.2 * 0.5 + 0.2 * 2 / 3) / 0.4)

    def test_task_metadata_weights_are_used_when_every_task_declares_one(self):
        weighted = {t: {**meta, "weight": w} for (t, meta), w in zip(TASKS.items(), (0.2, 0.2, 0.6))}
        s = aggregate.summarize(ATTEMPTS, weighted, RUN)
        self.assertAlmostEqual(s["overall"]["mean_credit"], 0.2 * 0.5 + 0.2 * 2 / 3 + 0.6 * 0.4)
        partial = {**weighted, "t03": dict(TASKS["t03"])}
        with self.assertRaises(ValueError):
            aggregate.summarize(ATTEMPTS, partial, RUN)

    def test_invalid_weights_raise(self):
        for weights in ({"t01": 0.5, "t02": 0.5, "t03": 0.5}, {"t01": 1.0, "t02": 0.0}, {"t01": 1.5, "t02": -0.5, "t03": 0.0}):
            with self.assertRaises(ValueError):
                aggregate.summarize(ATTEMPTS, TASKS, RUN, weights=weights)

    def test_weights_renormalize_over_tasks_with_scored_repeats(self):
        tasks = {"a": {"family": "f"}, "b": {"family": "f"}}
        attempts = [row("a", 1, full=True, credit=1.0), row("b", 1, "infrastructure-error", reason="boom")]
        s = aggregate.summarize(attempts, tasks, {"repeats": 1}, weights={"a": 0.25, "b": 0.75})
        self.assertEqual((s["overall"]["full_success_rate"], s["overall"]["scored_tasks"]), (1.0, 1))
        self.assertEqual(s["counts"]["unscored"], 1)

    def test_anchors_are_reported_but_excluded_from_overall_and_family(self):
        tasks = {**TASKS, "t04": {"family": "alpha", "source_group": "g3", "anchor": True}}
        attempts = ATTEMPTS + [row("t04", r, full=True, credit=1.0) for r in (1, 2, 3)]
        s = aggregate.summarize(attempts, tasks, RUN)
        self.assertEqual(s["overall"]["anchors_excluded"], 1)
        self.assertEqual(s["overall"]["scored_tasks"], 3)
        self.assertAlmostEqual(s["overall"]["full_success_rate"], 1 / 3)
        self.assertEqual(s["families"]["alpha"]["anchors_excluded"], 1)
        self.assertEqual((s["tasks"]["t04"]["anchor"], s["tasks"]["t04"]["full_success_rate"]), (True, 1.0))
        self.assertEqual(s["counts"]["scored"], 10)

    def test_critical_failure_flips_full_success_in_the_summary(self):
        s = aggregate.summarize([row("t", 1, full=True, credit=1.0, critical_failures=["lost state"])],
                                {"t": {"family": "f"}}, {"repeats": 1})
        self.assertEqual((s["counts"]["passed"], s["counts"]["failed"], s["overall"]["full_success_rate"],
                          s["overall"]["critical_failures"]), (0, 1, 0.0, 1))

    def test_unjudged_required_dimension_gives_unavailable_credit_with_bounds(self):
        dims = {"valid": {"credit": 1.0, "weight": 0.5, "required": True},
                "optimal": {"credit": None, "weight": 0.5, "required": True}}
        attempts = [row("u1", 1, full=False, credit=None, dimensions=dims), row("u2", 1, full=True, credit=1.0)]
        s = aggregate.summarize(attempts, {"u1": {}, "u2": {}}, {"repeats": 1})
        self.assertIsNone(s["overall"]["mean_credit"])
        self.assertEqual(s["overall"]["credit_bounds"], [0.75, 1.0])
        self.assertEqual(s["overall"]["full_success_rate"], 0.5)
        self.assertIsNone(s["tasks"]["u1"]["mean_credit"])

    def test_derived_wall_time_overlap_and_peak_from_rows(self):
        rows = [row("a", 1, full=True, credit=1.0, started="2026-10-02T10:00:00Z", finished="2026-10-02T10:00:10Z"),
                row("b", 1, full=True, credit=1.0, started="2026-10-02T10:00:05Z", finished="2026-10-02T10:00:15Z"),
                row("c", 1, full=True, credit=1.0, started="2026-10-02T10:00:10Z", finished="2026-10-02T10:00:20Z")]
        s = aggregate.summarize(rows, {"a": {}, "b": {}, "c": {}}, {"repeats": 1})
        self.assertEqual((s["run"]["wall_seconds"], s["run"]["peak_concurrency"], s["run"]["achieved_overlap"]), (20.0, 2, 1.5))
        self.assertIsNone(s["time"]["setup_seconds"])
        self.assertIsNone(s["time"]["execution_seconds"])

    def test_task_without_rows_is_not_launched_and_unknown_task_raises(self):
        s = aggregate.summarize([], {"t": {"family": "f"}}, {"repeats": 2})
        self.assertEqual((s["counts"]["planned"], s["counts"]["launched"], s["counts"]["not_launched"],
                          s["counts"]["unscored"]), (2, 0, 2, 2))
        self.assertEqual(len(s["exclusions"]), 2)
        self.assertIsNone(s["overall"]["full_success_rate"])
        with self.assertRaises(ValueError):
            aggregate.summarize([row("ghost", 1, full=True, credit=1.0)], {"t": {}}, {"repeats": 1})


def summary_of(values, *, anchors=(), groups=None, extra=None):
    tasks = {t: {"source_group": (groups or {}).get(t, t), "anchor": t in anchors, "full_success_rate": v,
                 "mean_credit": v} for t, v in values.items()}
    tasks.update(extra or {})
    return {"suite": {"name": "s", "tasks": len(tasks)}, "tasks": tasks}


class PairedTests(unittest.TestCase):
    def test_per_task_differences_ties_and_exact_inference(self):
        a = summary_of({"t1": 1.0, "t2": 1.0, "t3": 0.5, "t4": 1.0})
        b = summary_of({"t1": 0.0, "t2": 0.5, "t3": 0.5, "t4": 0.0})
        r = aggregate.paired(a, b, metric="full_success_rate", clusters={})
        self.assertEqual(r["per_task"], {"t1": 1.0, "t2": 0.5, "t3": 0.0, "t4": 1.0})
        self.assertEqual((r["common"], r["ties"], r["only_a"], r["only_b"]), (4, 1, [], []))
        self.assertAlmostEqual(r["mean_diff"], 0.625)
        self.assertEqual(r["sign_flip_p"], 0.25)
        self.assertAlmostEqual(r["ci95"][0], 0.25)
        self.assertAlmostEqual(r["ci95"][1], 1.0)
        self.assertEqual(r["clusters"], {"t1": 1.0, "t2": 0.5, "t3": 0.0, "t4": 1.0})
        self.assertEqual(r["method"]["clusters"], 4)
        self.assertEqual(r["method"]["p"], "exact sign-flip")

    def test_four_positive_clusters(self):
        a = summary_of({"t1": 1.0, "t2": 1.0, "t3": 1.0, "t4": 1.0})
        b = summary_of({"t1": 0.0, "t2": 0.0, "t3": 0.0, "t4": 0.0})
        self.assertEqual(aggregate.paired(a, b, metric="mean_credit", clusters={})["sign_flip_p"], 0.125)
        one = aggregate.paired(a, b, metric="mean_credit", clusters={}, direction="greater")
        self.assertEqual(one["sign_flip_p"], 0.0625)
        self.assertEqual(aggregate.paired(a, b, metric="mean_credit", clusters={}, direction="less")["sign_flip_p"], 1.0)

    def test_source_group_clusters_default_and_override(self):
        a = summary_of({"t1": 1.0, "t2": 0.5, "t3": 1.0}, groups={"t1": "g1", "t2": "g1", "t3": "g2"})
        b = summary_of({"t1": 0.0, "t2": 0.5, "t3": 0.5}, groups={"t1": "g1", "t2": "g1", "t3": "g2"})
        r = aggregate.paired(a, b, metric="full_success_rate", clusters={})
        self.assertEqual(r["clusters"], {"g1": 0.5, "g2": 0.5})
        self.assertAlmostEqual(r["mean_diff"], 0.5)
        # contributions 2/3 and 1/3: |sum| reaches 1 under 2 of 4 sign patterns
        self.assertEqual(r["sign_flip_p"], 0.5)
        self.assertAlmostEqual(r["ci95"][0], 1 / 3)
        self.assertAlmostEqual(r["ci95"][1], 2 / 3)
        merged = aggregate.paired(a, b, metric="full_success_rate", clusters={"t1": "one", "t2": "one", "t3": "one"})
        self.assertEqual(merged["clusters"], {"one": 0.5})
        self.assertEqual(merged["sign_flip_p"], 1.0)
        self.assertIsNone(merged["ci95"])

    def test_anchors_and_unavailable_tasks_are_left_out(self):
        a = summary_of({"t1": 1.0, "t2": 0.5, "t3": 1.0, "anc": 1.0}, anchors=("anc",), extra={"t5": {"mean_credit": None}})
        b = summary_of({"t1": 0.5, "t2": 0.5, "anc": 0.0, "t4": 0.2})
        r = aggregate.paired(a, b, metric="mean_credit", clusters={})
        self.assertEqual(sorted(r["per_task"]), ["t1", "t2"])
        self.assertEqual((r["only_a"], r["only_b"], r["anchors_excluded"]), (["t3"], ["t4"], ["anc"]))
        kept = aggregate.paired(a, b, metric="mean_credit", clusters={}, exclude_anchors=False)
        self.assertEqual(sorted(kept["per_task"]), ["anc", "t1", "t2"])

    def test_nothing_in_common(self):
        r = aggregate.paired(summary_of({"t1": 1.0}), summary_of({"t2": 1.0}), metric="full_success_rate", clusters={})
        self.assertEqual((r["common"], r["mean_diff"], r["sign_flip_p"], r["ci95"], r["per_task"]), (0, None, None, None, {}))

    def test_accepts_tasks_maps_and_summarize_output(self):
        a = aggregate.summarize(ATTEMPTS, TASKS, RUN)
        flipped = [dict(r, full_success=False, credit=0.0) if r["grading_status"] == "scored" else r for r in ATTEMPTS]
        b = aggregate.summarize(flipped, TASKS, RUN)
        r = aggregate.paired(a, b, metric="mean_credit", clusters={})
        self.assertEqual(sorted(r["per_task"]), ["t01", "t02", "t03"])
        self.assertEqual(r["per_task"], aggregate.paired(a["tasks"], b["tasks"], metric="mean_credit", clusters={})["per_task"])
        self.assertEqual(r["clusters"].keys(), {"g1", "g2"})
        self.assertGreater(r["mean_diff"], 0)

    def test_bad_direction_raises(self):
        with self.assertRaises(ValueError):
            aggregate.paired(summary_of({"t": 1.0}), summary_of({"t": 0.0}), metric="mean_credit", clusters={},
                             direction="up")


if __name__ == "__main__":
    unittest.main()
