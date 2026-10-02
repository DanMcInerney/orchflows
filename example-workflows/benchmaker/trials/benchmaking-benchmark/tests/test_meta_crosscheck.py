"""Crosscheck: the runner's records against what the member did, with hand-edited and dropped records flagged."""
import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve()
BB = HERE.parents[1]
SK = BB.parents[1] / "skills" / "benchmaker"
for path in (BB, SK / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from metabench import crosscheck, delivered, execute, pool, registry, store  # noqa: E402
from metabench.execute import Run  # noqa: E402

TOY = registry.MetaTask("toy-sum", "toydomain", {"output": "output.json", "inputs": ["input.json"], "number_lines": False},
                        (("oracle", "floor:noop"),), domain_file=HERE.parent / "fixtures" / "toydomain.py")


def setUpModule():
    registry.register(TOY)


class CrosscheckCase(unittest.TestCase):
    """One real run of an oracle and a defective member on package-mini; each test edits a copy of the outputs."""

    @classmethod
    def setUpClass(cls):
        registry.register(TOY)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        package = cls.root / "package-mini"
        shutil.copytree(SK / "tests" / "fixtures" / "package-mini", package)
        shutil.copytree(SK / "scripts" / "benchkit", package / "benchkit", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copyfile(SK / "scripts" / "run.py", package / "run.py")
        st = store.Store(cls.root / "store")
        document = {"meta_task": "toy-sum", "exposure": "private", "known_pairs": [], "contrasts": [], "aa_pairs": [], "unconfirmed": [],
                    "members": {"oracle": {"kind": "scripted", "behavior": "oracle"},
                                "defect": {"kind": "scripted", "behavior": "defect", "defect": "off_by_one"}}}
        cls.pool_id, pool_dir = pool.assemble(TOY, pool.normalize(document, "toy-sum"), st)
        cls.order = pool.read_order(st, "toy-sum", cls.pool_id)
        cls.ids = {spec["label"]: m for m, spec in cls.order["members"].items()}
        cls.rec = Run("r1", st.run("r1"), cls.root / "out")
        execute.intake(cls.rec, package, None)
        cls.results = execute.run_all(cls.rec, pool_dir, cls.order, sorted(cls.order["members"]), jobs=2, cap=120.0, builtins=())
        cls.tasks = delivered.tasks(cls.rec.intake)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def setUp(self):
        self.copy = Path(tempfile.mkdtemp(dir=self.root))
        self.addCleanup(shutil.rmtree, self.copy, ignore_errors=True)

    def edited(self, label):
        """A private copy of a member's output directory, with the attempts and summary loaded for editing."""
        member = self.ids[label]
        out = self.copy / member
        shutil.copytree(self.results[member]["out"], out)
        rows = [json.loads(line) for line in (out / "attempts.jsonl").read_text(encoding="utf-8").splitlines()]
        summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
        return member, out, rows, summary

    def save(self, out, rows=None, summary=None):
        if rows is not None:
            (out / "attempts.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        if summary is not None:
            (out / "summary.json").write_text(json.dumps(summary), encoding="utf-8")

    def check(self, member, out, regrade=True):
        """The member's crosscheck; `regrade=False` skips the `run.py grade` pass when a test is about counts only."""
        if regrade:
            return crosscheck.check_member(self.rec, member, out, self.tasks, grade_cap=60.0)
        with mock.patch.object(crosscheck, "_regrade", return_value=0):
            return crosscheck.check_member(self.rec, member, out, self.tasks, grade_cap=60.0)

    def kinds(self, found, key="count_mismatches"):
        return sorted(item["kind"] for item in found[key] if "kind" in item)

    def test_an_honest_run_has_no_mismatches_and_every_attempt_is_regraded(self):
        for label in ("oracle", "defect"):
            member, out, rows, _ = self.edited(label)
            found = self.check(member, out)
            self.assertEqual((found["count_mismatches"], found["grade_mismatches"], found["regraded"]), ([], [], len(rows)))

    def test_a_hand_edited_credit_is_a_grade_mismatch(self):
        member, out, rows, _ = self.edited("defect")
        self.assertEqual(rows[0]["credit"], 0.5)
        rows[0]["credit"], rows[0]["full_success"] = 1.0, True
        self.save(out, rows)
        found = self.check(member, out)
        fields = sorted(m["field"] for m in found["grade_mismatches"])
        self.assertEqual(fields, ["credit", "full_success"])
        self.assertEqual(found["count_mismatches"], [])

    def test_a_dropped_attempt_is_an_invocation_without_a_row(self):
        member, out, rows, summary = self.edited("oracle")
        self.save(out, rows[:-1])
        found = self.check(member, out, regrade=False)
        self.assertEqual(self.kinds(found), ["invocation-without-attempt", "summary-scored"])
        self.assertEqual(found["grade_mismatches"], [])

    def test_a_dropped_attempt_with_full_counts_reported_is_flagged_on_the_summary_too(self):
        member, out, rows, summary = self.edited("oracle")
        self.save(out, rows[:2])
        summary["counts"]["scored"] = 4
        self.save(out, summary=summary)
        found = self.check(member, out, regrade=False)
        self.assertEqual(self.kinds(found), ["invocation-without-attempt", "invocation-without-attempt", "summary-scored"])

    def test_inflated_launch_counts_in_the_summary_are_flagged(self):
        member, out, rows, summary = self.edited("oracle")
        summary["counts"]["launched"] = 8
        self.save(out, summary=summary)
        found = self.check(member, out, regrade=False)
        self.assertEqual(self.kinds(found), ["summary-launched"])
        self.assertEqual(found["count_mismatches"][0]["summary"], 8)

    def test_an_attempt_with_no_member_invocation_is_flagged(self):
        member, out, rows, _ = self.edited("oracle")
        fake = copy.deepcopy(rows[0])
        fake["repeat"], fake["retry"] = 3, 0
        (out / "attempts" / fake["task"] / "3-0").mkdir(parents=True)
        self.save(out, rows + [fake])
        found = self.check(member, out, regrade=False)
        self.assertEqual(self.kinds(found), ["attempt-without-invocation", "summary-scored"])

    def test_a_row_naming_a_task_the_member_was_not_given_is_flagged(self):
        member, out, rows, _ = self.edited("oracle")
        row = rows[0]
        claimed = {"t01": "t02", "t02": "t01"}[row["task"]]
        shutil.copytree(out / "attempts" / row["task"] / f"{row['repeat']}-{row['retry']}", out / "attempts" / claimed / "9-0")
        row["task"], row["repeat"] = claimed, 9
        self.save(out, rows)
        found = self.check(member, out, regrade=False)
        self.assertIn("task-differs", self.kinds(found))

    def test_a_row_for_the_wrong_task_without_a_matching_attempt_folder_is_flagged_too(self):
        member, out, rows, _ = self.edited("oracle")
        rows[0]["task"] = {"t01": "t02", "t02": "t01"}[rows[0]["task"]]
        self.save(out, rows)
        found = self.check(member, out, regrade=False)
        self.assertTrue({"attempt-without-invocation", "invocation-without-attempt"} <= set(self.kinds(found)))

    def test_missing_attempts_file_is_reported(self):
        member, out, rows, _ = self.edited("oracle")
        (out / "attempts.jsonl").unlink()
        self.assertIn("attempts", self.kinds(self.check(member, out, regrade=False)))

    def test_the_gate_input_aggregates_members_and_fails_on_any_mismatch(self):
        found = crosscheck.crosscheck(self.rec, self.results, self.tasks, grade_cap=60.0, jobs=2)
        self.assertTrue(found["pass"])
        self.assertEqual(found["regraded"], 8)
        self.assertEqual(sorted(found["members"]), sorted(self.order["members"]))
        member, out, rows, _ = self.edited("defect")
        rows[1]["credit"] = 0.0
        self.save(out, rows)
        broken = {**self.results, member: {**self.results[member], "out": out}}
        found = crosscheck.crosscheck(self.rec, broken, self.tasks, grade_cap=60.0, jobs=2)
        self.assertFalse(found["pass"])
        self.assertEqual(found["members"][member]["grade_mismatches"], 1)
        self.assertEqual(found["members"][self.ids["oracle"]]["grade_mismatches"], 0)

    def test_builtin_runs_are_not_crosschecked(self):
        found = crosscheck.crosscheck(self.rec, {"@reference": {"out": self.root}}, self.tasks, grade_cap=1.0)
        self.assertEqual((found["pass"], found["members"], found["regraded"]), (True, {}, 0))


class JoinTests(unittest.TestCase):
    def test_final_units_take_the_highest_retry_and_launched_skips_unreached_rows(self):
        rows = [{"task": "a", "repeat": 1, "retry": 0, "status": "completed", "workspace": "w", "exit_code": 0},
                {"task": "a", "repeat": 1, "retry": 1, "status": "infrastructure-error", "workspace": "w2"},
                {"task": "a", "repeat": 2, "retry": 0, "status": "not-launched", "workspace": None, "exit_code": None},
                {"task": "a", "repeat": 3, "retry": 0, "status": "infrastructure-error", "workspace": None, "exit_code": None}]
        self.assertEqual(crosscheck.final_units(rows)[("a", 1)]["retry"], 1)
        self.assertEqual([r["repeat"] for r in crosscheck.launched(rows)], [1, 1])

    def test_identify_tells_tasks_with_one_instruction_apart_by_their_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            package = tmp / "pkg"
            for name, numbers in (("a", "[1]"), ("b", "[2]")):
                (package / "tasks" / name / "environment").mkdir(parents=True)
                (package / "tasks" / name / "instruction.md").write_text("Add them up.\n", encoding="utf-8")
                (package / "tasks" / name / "environment" / "input.json").write_text(numbers, encoding="utf-8")
            tasks = delivered.tasks(package)
            capture = tmp / "capture"
            capture.mkdir()
            (capture / "input.json").write_text("[2]", encoding="utf-8")
            self.assertEqual(delivered.identify(tasks, "Add them up.\n", capture), "b")
            self.assertIsNone(delivered.identify(tasks, "Add them up.\n", None))
            self.assertIsNone(delivered.identify(tasks, "something else", capture))
            self.assertEqual(delivered.identify({"a": tasks["a"]}, "Add them up.\n"), "a")


if __name__ == "__main__":
    unittest.main()
