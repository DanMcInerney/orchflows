"""conform.py: standalone, passes the kit's package-mini, fails what is missing, and agrees with the kit's shape checks."""
import ast
import copy
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

HERE = Path(__file__).resolve()
BB = HERE.parents[1]
SK = BB.parents[1] / "skills" / "benchmaker"
CONFORM = BB / "public" / "conform.py"
INTERFACE = SK / "scripts" / "benchkit" / "INTERFACE.md"
if str(SK / "scripts") not in sys.path:
    sys.path.insert(0, str(SK / "scripts"))

from benchkit import shapes  # noqa: E402

spec = importlib.util.spec_from_file_location("conform_under_test", CONFORM)
conform = importlib.util.module_from_spec(spec)
spec.loader.exec_module(conform)


def assemble_mini(destination: Path) -> Path:
    shutil.copytree(SK / "tests" / "fixtures" / "package-mini", destination)
    shutil.copytree(SK / "scripts" / "benchkit", destination / "benchkit", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(SK / "scripts" / "run.py", destination / "run.py")
    return destination


def examples():
    found = {}
    for info, body in re.findall(r"```(\w+ [\w.]+)\n(.*?)```", INTERFACE.read_text(encoding="utf-8"), re.S):
        language, name = info.split()
        found[name] = tomllib.loads(body) if language == "toml" else json.loads(body)
    return found


class RunTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_passes_package_mini_from_the_command_line_with_a_json_report(self):
        package = assemble_mini(self.root / "package-mini")
        done = subprocess.run([sys.executable, str(CONFORM), str(package)], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        report = json.loads(done.stdout)
        self.assertTrue(report["pass"])
        names = [c["name"] for c in report["checks"]]
        for expected in ("layout", "package shapes", "preflight", "smoke with a no-op agent", "full with @reference",
                         "grade on the reference outputs", "grade rows"):
            self.assertIn(expected, names)
        self.assertTrue(all(c["passed"] for c in report["checks"]))
        self.assertEqual([c["command"][2] for c in report["commands"]], ["preflight", "smoke", "full", "grade"])
        self.assertEqual(Path(report["package"]), package.resolve())

    def test_fails_a_copy_whose_runner_has_no_grade_command(self):
        package = assemble_mini(self.root / "no-grade")
        (package / "run.py").rename(package / "run_real.py")
        (package / "run.py").write_text(
            "import runpy, sys\nfrom pathlib import Path\n"
            "if sys.argv[1:2] == ['grade']:\n    sys.stderr.write(\"invalid choice: 'grade'\\n\")\n    raise SystemExit(2)\n"
            "runpy.run_path(str(Path(__file__).with_name('run_real.py')), run_name='__main__')\n", encoding="utf-8")
        report = conform.conform(package)
        self.assertFalse(report["pass"])
        failed = [c["name"] for c in report["checks"] if not c["passed"]]
        self.assertEqual(failed, ["grade on the reference outputs"])
        self.assertIn("invalid choice", next(c["detail"] for c in report["checks"] if not c["passed"]))

    def test_a_missing_card_stops_at_the_layout_check(self):
        package = assemble_mini(self.root / "no-card")
        (package / "card.json").unlink()
        report = conform.conform(package)
        self.assertEqual([(c["name"], c["passed"]) for c in report["checks"]], [("layout", False)])
        self.assertIn("missing card.json", report["checks"][0]["detail"])
        self.assertEqual(report["commands"], [])

    def test_a_task_without_a_verifier_fails_the_layout(self):
        package = assemble_mini(self.root / "no-verifier")
        (package / "tasks" / "t02" / "tests" / "verify.py").unlink()
        self.assertIn("tasks/t02/tests/verify.py is missing", conform.layout_problems(package))

    def test_an_invalid_suite_fails_the_shape_check_and_preflight(self):
        package = assemble_mini(self.root / "bad-suite")
        suite = json.loads((package / "suite.json").read_text(encoding="utf-8"))
        suite["repeats"] = 0
        (package / "suite.json").write_text(json.dumps(suite), encoding="utf-8")
        report = conform.conform(package)
        failed = {c["name"] for c in report["checks"] if not c["passed"]}
        self.assertTrue({"package shapes", "preflight"} <= failed)
        self.assertIn("'repeats' must be an integer >= 1", next(c["detail"] for c in report["checks"] if c["name"] == "package shapes"))

    def test_a_command_that_hangs_is_stopped_at_the_timeout(self):
        record = conform.run_command([sys.executable, "-c", "import time; time.sleep(30)"], self.root, 0.5, self.root / "logs", "hang")
        self.assertEqual(record["status"], "timeout")
        self.assertLess(record["seconds"], 10)
        self.assertIn("timed out", record["reason"])


class GradeRowTests(unittest.TestCase):
    ROW = {"task": "t01", "submission": "a1-0", "grading_status": "scored", "full_success": True, "credit": 1.0,
           "dimensions": {}, "critical_failures": [], "reason": ""}

    def test_rows_must_exist_and_agree_with_the_runs_own_grades(self):
        tree = {("t01", "a1-0"): {**self.ROW}}
        self.assertEqual(conform.grade_problems([self.ROW], tree), [])
        self.assertTrue(conform.grade_problems([], tree)[0].startswith("grade wrote no row"))
        self.assertIn("full_success", conform.grade_problems([{**self.ROW, "full_success": False}], tree)[0])
        self.assertIn("credit 0.5 differs", " ".join(conform.grade_problems([{**self.ROW, "credit": 0.5}], tree)))
        self.assertTrue(conform.grade_problems([{**self.ROW, "grading_status": "mystery"}], tree))


class ShapeTests(unittest.TestCase):
    def test_the_documented_examples_validate(self):
        docs = examples()
        self.assertEqual(conform.suite_problems(docs["suite.json"]), [])
        self.assertEqual(conform.task_problems(docs["task.toml"]), [])
        self.assertEqual(conform.verifier_problems(docs["verifier"]), [])
        self.assertEqual(conform.attempt_problems(docs["attempt"]), [])
        self.assertEqual(conform.summary_problems(docs["summary"]), [])
        self.assertEqual(conform.claims_problems(docs["card"]), [])

    def test_conform_and_the_kit_agree_on_every_documented_shape_and_its_breakages(self):
        docs = examples()

        def mutated(name, edit):
            doc = copy.deepcopy(docs[name])
            edit(doc)
            return doc

        cases = [
            ("suite_problems", "suite.json", lambda d: d.update(repeats=0)),
            ("suite_problems", "suite.json", lambda d: d.pop("name")),
            ("suite_problems", "suite.json", lambda d: d.update(concurrency="many")),
            ("suite_problems", "suite.json", lambda d: d.update(provision=[["ok"], []])),
            ("suite_problems", "suite.json", lambda d: d.update(metrics={"primary": "vibes"})),
            ("suite_problems", "suite.json", lambda d: d.update(launch_budget=0)),
            ("suite_problems", "suite.json", lambda d: d.update(transient_retry_budget=-1)),
            ("task_problems", "task.toml", lambda d: d.pop("agent")),
            ("task_problems", "task.toml", lambda d: d["metadata"].update(split="somewhere")),
            ("task_problems", "task.toml", lambda d: d["metadata"].pop("source_group")),
            ("task_problems", "task.toml", lambda d: d["metadata"].update(weight=-1)),
            ("task_problems", "task.toml", lambda d: d["agent"].update(timeout_sec=0)),
            ("task_problems", "task.toml", lambda d: d["metadata"].update(time_estimate="guess")),
            ("verifier_problems", "verifier", lambda d: d["dimensions"]["valid"].update(weight=0.9)),
            ("verifier_problems", "verifier", lambda d: d.update(credit=2)),
            ("verifier_problems", "verifier", lambda d: d.update(full_success=True, critical_failures=["clobber"])),
            ("verifier_problems", "verifier", lambda d: d.pop("full_success")),
            ("verifier_problems", "verifier", lambda d: d.update(grading_status="indeterminate", reason="")),
            ("verifier_problems", "verifier", lambda d: d.update(credit=0.1)),
            ("verifier_problems", "verifier", lambda d: d["dimensions"]["valid"].update(credit=None)),
            ("attempt_problems", "attempt", lambda d: d.update(status="bogus")),
            ("attempt_problems", "attempt", lambda d: d.update(status="infrastructure-error")),
            ("attempt_problems", "attempt", lambda d: d.pop("task")),
            ("attempt_problems", "attempt", lambda d: d.update(credit=1.5)),
            ("attempt_problems", "attempt", lambda d: d.update(left_running="no")),
            ("summary_problems", "summary", lambda d: d["counts"]["by_status"].pop("canceled")),
            ("summary_problems", "summary", lambda d: d["counts"].update(planned=3)),
            ("summary_problems", "summary", lambda d: d.pop("families")),
            ("summary_problems", "summary", lambda d: d["tasks"]["t01"].pop("source_group")),
            ("claims_problems", "card", lambda d: d["claims"][0].update(system="ghost")),
            ("claims_problems", "card", lambda d: d["claims"][0].update(low=0.9, high=0.1)),
            ("claims_problems", "card", lambda d: d["claims"].append(dict(d["claims"][0]))),
            ("claims_problems", "card", lambda d: d["claims"][-1].update(category="mystery")),
            ("claims_problems", "card", lambda d: [d["claims"][2].pop("max")]),
            ("claims_problems", "card", lambda d: d["claims"][1].update(resolved="yes")),
            ("claims_problems", "card", lambda d: [d["claims"][6].pop("usd_max"), d["claims"][6].pop("wall_seconds_max")]),
            ("claims_problems", "card", lambda d: d.update(claims="none")),
        ]
        for function, name, edit in cases:
            doc = mutated(name, edit)
            ours, kit = getattr(conform, function)(doc), getattr(shapes, function)(doc)
            self.assertTrue(ours, (function, name, kit))
            self.assertTrue(kit, (function, name, ours))
        for function, name in (("suite_problems", "suite.json"), ("task_problems", "task.toml"), ("verifier_problems", "verifier"),
                               ("attempt_problems", "attempt"), ("summary_problems", "summary"), ("claims_problems", "card")):
            self.assertEqual(getattr(conform, function)(docs[name]), getattr(shapes, function)(docs[name]), function)

    def test_run_problems_reads_a_real_run_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            package = assemble_mini(Path(tmp) / "pkg")
            out = Path(tmp) / "out"
            done = subprocess.run([sys.executable, "run.py", "smoke", "--agent", "@reference", "--output", str(out)], cwd=package,
                                  capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
            self.assertEqual(conform.run_problems(out), [])
            self.assertEqual(shapes.run_problems(out), [])
            (out / "attempts.jsonl").write_text("not json\n", encoding="utf-8")
            self.assertTrue(conform.run_problems(out))
            self.assertTrue(conform.run_problems(Path(tmp) / "missing"))


class StandaloneTests(unittest.TestCase):
    def test_conform_imports_only_the_standard_library(self):
        tree = ast.parse(CONFORM.read_text(encoding="utf-8"))
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules |= {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0, "no relative imports")
                modules.add((node.module or "").split(".")[0])
        self.assertTrue(modules <= set(sys.stdlib_module_names), modules - set(sys.stdlib_module_names))
        self.assertFalse({"benchkit", "metabench"} & modules)

    def test_conform_runs_from_a_bare_directory_without_the_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            lone = Path(tmp) / "conform.py"
            shutil.copyfile(CONFORM, lone)
            done = subprocess.run([sys.executable, str(lone), str(Path(tmp) / "nothing-here")], cwd=tmp, capture_output=True, text=True)
            self.assertEqual(done.returncode, 1)
            self.assertFalse(json.loads(done.stdout)["pass"])


if __name__ == "__main__":
    unittest.main()
