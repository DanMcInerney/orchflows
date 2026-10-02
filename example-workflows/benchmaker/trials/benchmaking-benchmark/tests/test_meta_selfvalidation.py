"""Mutation self-validation: each operator does what it says to a real reference package, every detection predicate
is quiet on a clean report, and a quick selfcheck of one meta-task catches its mutants. Zero model calls."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BB))
sys.path.insert(0, str(BB.parents[1] / "skills" / "benchmaker" / "scripts"))

from metabench import mutate, registry, selfvalidate  # noqa: E402

META = registry.get("schedule-nosolver")
TASKS = "ev-exec-pair,xz-arch-sync"
QUICK_SECONDS = 60


def run_python(*args, cwd=None):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, cwd=cwd, timeout=120)


def solve(package: Path, task: str, workspace: Path) -> None:
    shutil.copytree(package / "tasks" / task / "environment", workspace)
    done = run_python(package / "tasks" / task / "solution" / "solve.py", "--workspace", workspace)
    assert done.returncode == 0, done.stderr.decode()


def grade(package: Path, task: str, workspace: Path, result: Path) -> dict:
    run_python(package / "tasks" / task / "tests" / "verify.py", "--task", package / "tasks" / task,
               "--workspace", workspace, "--result", result)
    return json.loads(result.read_text(encoding="utf-8"))


def clean_report() -> dict:
    """A report as an unmutated reference produces it, for the metrics the predicates read."""
    gate = {"pass": True, "reasons": []}
    return {"gates": {"G1_executability": {**gate, "infrastructure_error_share": 0.0},
                      "G2_reference_and_floor": {**gate, "reference_pass_rate": 1.0, "noop_full_success_tasks": [], "noop_mean_credit": 0.0},
                      "crosscheck": {**gate, "count_mismatches": [], "grade_mismatches": []},
                      "staging": {**gate, "cheater_findings": []}},
            "metrics": {"M1_cheaters": {"hackable_task_ratio": 0.0, "hackable_tasks": [],
                                        "credit_by_class": {"noop": {"mean_credit": 0.0}, "tamper": {"mean_credit": 0.0},
                                                            "read_workspace": {"mean_credit": 0.0}}},
                        "M2_order": {"pairs": 11, "pair_accuracy": 1.0, "contradicted": [], "null_p": 0.0},
                        "M3_kill": {"killable": 1, "killed": 1, "rate": 1.0, "excluded_equivalent": []},
                        "M6_verifier": {"tpr": 1.0, "tnr": 1.0, "false_rejects": [], "false_accepts": []},
                        "M7_task_profile": {"reference_fail": [], "floor_credit": [], "flat": [], "inverted": [], "informative_share": 1.0},
                        "M9_claims": {"checkable": 4, "contradicted": [], "vacuous": []}}}


class OperatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(tempfile.mkdtemp(prefix="msv-"))
        cls.base = cls.root / "base"
        selfvalidate.assemble(META, cls.base, ["--only", TASKS])
        cls.tasks = sorted(path.name for path in (cls.base / "tasks").iterdir())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)

    def mutant(self, name: str) -> Path:
        package = self.root / f"mutant-{name}"
        if not package.exists():
            shutil.copytree(self.base, package)
            mutate.apply(name, package, META)
        return package

    def scratch(self) -> Path:
        return Path(tempfile.mkdtemp(dir=self.root, prefix="w-")) / "workspace"

    def test_unmutated_reference_is_graded_full_success(self):
        for task in self.tasks:
            workspace = self.scratch()
            solve(self.base, task, workspace)
            self.assertTrue(grade(self.base, task, workspace, workspace.parent / "r.json")["full_success"])

    def test_every_operator_applies_and_each_name_is_listed(self):
        self.assertEqual(len(mutate.MUTANTS), 12)
        self.assertTrue(set(mutate.QUICK) <= set(mutate.MUTANTS))
        for name in mutate.MUTANTS:
            self.mutant(name)

    def test_wrapping_twice_is_refused(self):
        package = self.mutant("accepts_empty")
        with self.assertRaises(mutate.MutationError):
            mutate.apply("accepts_empty", package, META)

    def test_accepts_empty_gives_full_credit_to_nothing(self):
        package = self.mutant("accepts_empty")
        for task in self.tasks:
            workspace = self.scratch()
            workspace.mkdir()
            result = grade(package, task, workspace, workspace.parent / "r.json")
            self.assertEqual((result["full_success"], result["credit"]), (True, 1.0))
            self.assertEqual(grade(self.base, task, workspace, workspace.parent / "b.json")["credit"], 0)

    def test_flat_grader_gives_half_credit_to_anything_non_empty(self):
        package = self.mutant("flat_grader")
        workspace = self.scratch()
        workspace.mkdir()
        (workspace / "output.json").write_text("{}", encoding="utf-8")
        result = grade(package, self.tasks[0], workspace, workspace.parent / "r.json")
        self.assertEqual((result["full_success"], result["credit"]), (True, 0.5))
        (workspace / "output.json").write_text("", encoding="utf-8")
        self.assertEqual(grade(package, self.tasks[0], workspace, workspace.parent / "e.json")["credit"], 0)

    def test_in_place_grading_trusts_a_reward_file(self):
        package = self.mutant("in_place_grading")
        workspace = self.scratch()
        workspace.mkdir()
        self.assertEqual(grade(package, self.tasks[0], workspace, workspace.parent / "a.json")["credit"], 0)
        (workspace / "reward.txt").write_text("1\n", encoding="utf-8")
        self.assertTrue(grade(package, self.tasks[0], workspace, workspace.parent / "b.json")["full_success"])

    def test_broken_reference_fails_its_own_verifier(self):
        package = self.mutant("broken_reference")
        feasible = [t for t in self.tasks if "start" in json.loads(self.answer(package, t))]
        self.assertTrue(feasible)
        for task in feasible:
            workspace = self.scratch()
            solve(package, task, workspace)
            self.assertFalse(grade(package, task, workspace, workspace.parent / "r.json")["full_success"])

    def answer(self, package: Path, task: str) -> bytes:
        workspace = self.scratch()
        shutil.copytree(package / "tasks" / task / "environment", workspace)
        done = run_python(package / "tasks" / task / "solution" / ("solve_base.py" if (package / "tasks" / task / "solution" / "solve_base.py").exists() else "solve.py"),
                          "--workspace", workspace)
        self.assertEqual(done.returncode, 0, done.stderr.decode())
        return (workspace / "output.json").read_bytes()

    def test_wrong_key_changes_every_second_task_and_the_reference_agrees_with_it(self):
        package = self.mutant("wrong_key")
        first, second = self.tasks
        self.assertFalse((package / "tasks" / first / "tests" / "verify_base.py").exists())
        self.assertTrue((package / "tasks" / second / "tests" / "verify_base.py").exists())
        workspace = self.scratch()
        solve(package, second, workspace)
        self.assertTrue(grade(package, second, workspace, workspace.parent / "r.json")["full_success"])
        truth = self.scratch()
        shutil.copytree(package / "tasks" / second / "environment", truth)
        (truth / "output.json").write_bytes(self.answer(package, second))
        self.assertFalse(grade(package, second, truth, truth.parent / "t.json")["full_success"])

    def test_shuffled_labels_grade_task_i_as_task_next_and_the_reference_follows(self):
        package = self.mutant("shuffled_labels")
        for task in self.tasks:
            workspace = self.scratch()
            solve(package, task, workspace)
            self.assertTrue(grade(package, task, workspace, workspace.parent / "r.json")["full_success"], task)
        truthful = self.scratch()
        shutil.copytree(package / "tasks" / self.tasks[0] / "environment", truthful)
        (truthful / "output.json").write_bytes(self.answer(package, self.tasks[0]))
        self.assertFalse(grade(package, self.tasks[0], truthful, truthful.parent / "t.json")["full_success"])

    def test_answers_reachable_stages_the_reference_answer_where_the_solver_can_read_it(self):
        package = self.mutant("answers_reachable")
        sys.path.insert(0, str(BB.parents[1] / "skills" / "benchmaker" / "scripts"))
        from benchkit import stage

        for task in self.tasks:
            cached = (package / "tasks" / task / "environment" / ".cache" / "expected.json").read_bytes()
            self.assertEqual(json.loads(cached), json.loads(self.answer(self.base, task)))
            scratch = self.scratch()
            stage.stage_public(package / "tasks" / task, scratch, scratch.parent / "prompt.md")
            self.assertTrue((scratch / ".cache" / "expected.json").is_file())

    def test_trivial_tasks_replaces_every_second_task_and_stays_gradable(self):
        package = self.mutant("trivial_tasks")
        first, second = self.tasks
        trivial = json.loads((package / "tasks" / second / "environment" / "input.json").read_text(encoding="utf-8"))
        self.assertEqual((len(trivial["participants"]), trivial["constraints"], trivial["preference"]), (1, [], "any"))
        self.assertEqual(json.loads((package / "tasks" / first / "environment" / "input.json").read_text(encoding="utf-8")),
                         json.loads((self.base / "tasks" / first / "environment" / "input.json").read_text(encoding="utf-8")))
        workspace = self.scratch()
        solve(package, second, workspace)
        self.assertTrue(grade(package, second, workspace, workspace.parent / "r.json")["full_success"])

    def test_card_mutants_edit_claims(self):
        fabricated = json.loads((self.mutant("fabricated_card") / "card.json").read_text(encoding="utf-8"))
        ids = {claim["id"] for claim in fabricated["claims"]}
        self.assertTrue({"f1", "f2", "c1"} <= ids)
        vacuous = json.loads((self.mutant("vacuous_card") / "card.json").read_text(encoding="utf-8"))
        self.assertEqual([c["id"] for c in vacuous["claims"]], ["v1", "v1"])
        self.assertTrue(all((c["low"], c["high"]) == (0.0, 1.0) for c in vacuous["claims"]))

    def test_runner_mutants_edit_the_kit_copy_only(self):
        mismatch = self.mutant("summary_mismatch")
        self.assertIn("kept = rows[::2]", (mismatch / "benchkit" / "records.py").read_text(encoding="utf-8"))
        capless = self.mutant("no_cap")
        self.assertIn("timeout=10 ** 9", (capless / "benchkit" / "adapters.py").read_text(encoding="utf-8"))
        self.assertTrue((capless / "tasks" / self.tasks[0] / "solution" / "solve_base.py").exists())
        self.assertFalse((capless / "tasks" / self.tasks[1] / "solution" / "solve_base.py").exists())
        self.assertNotIn("kept = rows[::2]", (self.base / "benchkit" / "records.py").read_text(encoding="utf-8"))

    def test_no_cap_refuses_a_kit_it_does_not_recognize(self):
        package = self.root / "other-kit"
        shutil.copytree(self.base, package)
        (package / "benchkit" / "adapters.py").write_text("# no timeout here\n", encoding="utf-8")
        with self.assertRaises(mutate.MutationError):
            mutate.apply("no_cap", package, META)


class DetectionTests(unittest.TestCase):
    def test_a_clean_report_passes_every_reference_check_and_flags_no_mutant(self):
        report = clean_report()
        self.assertTrue(all(c["pass"] for c in selfvalidate.reference_checks(report)))
        for name in mutate.MUTANTS:
            for domain in ("scheduling", "logtriage", "calendar"):
                flags = selfvalidate.detections(name, report, domain)
                self.assertTrue(flags and any(not f["pass"] for f in flags), f"{name} {domain}: a clean report must not look caught")

    def test_reference_checks_name_the_metric_that_failed(self):
        report = clean_report()
        report["metrics"]["M6_verifier"]["tpr"] = 0.7
        report["metrics"]["M2_order"]["pair_accuracy"] = 0.8
        report["gates"]["staging"]["pass"] = False
        failed = {c["name"] for c in selfvalidate.reference_checks(report) if not c["pass"]}
        self.assertEqual(failed, {"staging passes", "M2 pair accuracy on constructed pairs", "M6 true positive rate"})

    def test_shifted_reports_are_caught(self):
        report = clean_report()
        report["gates"]["crosscheck"].update(**{"pass": False, "count_mismatches": [{"x": 1}]})
        self.assertTrue(all(f["pass"] for f in selfvalidate.detections("summary_mismatch", report, "scheduling")))
        report = clean_report()
        report["gates"]["G2_reference_and_floor"].update(**{"pass": False, "noop_mean_credit": 1.0})
        report["metrics"]["M1_cheaters"]["credit_by_class"]["noop"]["mean_credit"] = 1.0
        self.assertTrue(all(f["pass"] for f in selfvalidate.detections("accepts_empty", report, "scheduling")))
        report = clean_report()
        report["gates"]["staging"].update(**{"pass": False, "cheater_findings": [{"kind": "workspace-file"}]})
        flags = selfvalidate.detections("answers_reachable", report, "calendar")
        self.assertEqual([f["name"] for f in flags], ["staging gate fails"])
        self.assertEqual(len(selfvalidate.detections("answers_reachable", report, "logtriage")), 2)
        report = clean_report()
        report["metrics"]["M7_task_profile"]["inverted"] = [{"task": "t2", "pairs": [["a", "b"]]}]
        self.assertTrue(all(f["pass"] for f in selfvalidate.detections("trivial_tasks", report, "logtriage", {"trivial": ["t2", "t4"]})))
        self.assertFalse(all(f["pass"] for f in selfvalidate.detections("trivial_tasks", report, "logtriage", {"trivial": ["t4"]})))

    def test_wrong_key_needs_only_the_verifier_check_and_records_the_order_check(self):
        report = clean_report()
        report["metrics"]["M6_verifier"].update(tpr=0.5, false_rejects=[{"task": "t"}])
        flags = selfvalidate.detections("wrong_key", report, "scheduling")
        self.assertEqual([f["required"] for f in flags], [True, False])
        self.assertEqual([f["pass"] for f in flags], [True, False])

    def test_render_lists_the_matrix(self):
        result = {"meta_task": "x", "quick": True, "caught": 1, "wall_seconds": 3.0, "tasks": 2, "members": 3, "repeats": 1,
                  "reference": {"pass": True, "checks": [selfvalidate.check("a", True, 1, "1")], "wall_seconds": 1.0},
                  "mutants": [{"name": "flat_grader", "edit": "e", "caught": False, "wall_seconds": 1.0,
                               "flags": [selfvalidate.check("M6 TNR falls", False, 1.0, "< 1")]}]}
        text = selfvalidate.render(result)
        self.assertIn("flat_grader", text)
        self.assertIn("MISSED: M6 TNR falls", text)


class PoolTests(unittest.TestCase):
    def test_scripted_pools_are_filtered_from_the_composed_pool_and_carry_no_model_members(self):
        for name in ("schedule-nosolver", "logtriage-llm", "calendar-skill"):
            meta = registry.get(name)
            for quick, expected in ((True, 8), (False, 13)):
                root = Path(tempfile.mkdtemp(prefix="msv-pool-"))
                self.addCleanup(shutil.rmtree, root, True)
                st = selfvalidate.stores.Store(root)
                selfvalidate.prepare_material(meta, st)
                pool_id = selfvalidate.scripted_pool(meta, st, quick)
                order = json.loads((root / "pools" / name / pool_id / "ORDER.json").read_text(encoding="utf-8"))
                labels = [spec["label"] for spec in order["members"].values()]
                self.assertEqual(len(labels), expected, (name, quick, labels))
                self.assertTrue(all(spec["kind"] == "scripted" for spec in order["members"].values()))
                self.assertIn("cheater:tamper", labels)
                self.assertEqual("floor:dump_all" in labels, name == "logtriage-llm" and not quick)
                self.assertTrue(order["known_pairs"])
                self.assertEqual(bool(order["aa_pairs"]), not quick)


class QuickSelfcheckTests(unittest.TestCase):
    def test_quick_selfcheck_passes_the_reference_and_catches_its_quick_mutants(self):
        root = Path(tempfile.mkdtemp(prefix="msv-store-"))
        self.addCleanup(shutil.rmtree, root, True)
        result = selfvalidate.run("schedule-nosolver", quick=True, store=root)
        failed = [c for c in result["reference"]["checks"] if not c["pass"]]
        self.assertEqual(failed, [])
        self.assertEqual([m["name"] for m in result["mutants"]], list(mutate.QUICK))
        missed = [(m["name"], m.get("error"), [f for f in m["flags"] if not f["pass"]]) for m in result["mutants"] if not m["caught"]]
        self.assertEqual(missed, [])
        self.assertTrue(result["pass"])
        self.assertLess(result["wall_seconds"], QUICK_SECONDS)
        written = root / "selfcheck" / "schedule-nosolver-quick"
        self.assertEqual(json.loads(written.with_suffix(".json").read_text(encoding="utf-8"))["caught"], 3)
        self.assertIn("Kill matrix", written.with_suffix(".md").read_text(encoding="utf-8"))
        self.assertEqual([p for p in (root / "selfcheck").iterdir() if p.is_dir()], [])


if __name__ == "__main__":
    unittest.main()
