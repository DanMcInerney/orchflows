"""run.py commands on the package-mini fixture: profiles, preflight, grade-only, rescore, compare and the shim."""
from __future__ import annotations

import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "scripts"
FIXTURES = TESTS / "fixtures"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from benchkit import cli, identity, shapes  # noqa: E402


def agent(name):
    return str(FIXTURES / "agents" / name)


def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(identity.discard, self.tmp)
        self.package, self.out = self.tmp / "package-mini", self.tmp / "o"
        shutil.copytree(FIXTURES / "package-mini", self.package)
        shutil.copytree(SCRIPTS / "benchkit", self.package / "benchkit", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(SCRIPTS / "run.py", self.package / "run.py")

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(self.package, [str(item) for item in argv])
        return code, out.getvalue(), err.getvalue()

    def edit(self, relative, old, new):
        path = self.package / relative
        text = path.read_text(encoding="utf-8")
        self.assertIn(old, text)
        path.write_text(text.replace(old, new, 1), encoding="utf-8")

    def suite(self, **changes):
        path = self.package / "suite.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc.update(changes)
        path.write_text(json.dumps(doc), encoding="utf-8")

    def summary(self, out=None):
        return json.loads(((out or self.out) / "summary.json").read_text(encoding="utf-8"))


class ProfileTests(Case):
    def test_smoke_with_the_reference_agent_passes_and_its_files_validate(self):
        code, out, err = self.run_cli("smoke", "--agent", "@reference", "--output", self.out)
        self.assertEqual(code, 0, err)
        summary = self.summary()
        self.assertEqual((summary["counts"]["planned"], list(summary["tasks"])), (1, ["t01"]))
        self.assertEqual((summary["overall"]["full_success_rate"], summary["overall"]["mean_credit"]), (1.0, 1.0))
        self.assertIn("full_success_rate 1", out)
        self.assertEqual(shapes.run_problems(self.out), [])
        self.assertFalse((self.out / "OWNER").exists())

    def test_full_runs_every_task_and_repeat_and_keeps_each_attempt(self):
        code, _, err = self.run_cli("full", "--agent", "@reference", "--output", self.out)
        self.assertEqual(code, 0, err)
        summary = self.summary()
        self.assertEqual((summary["counts"]["planned"], summary["counts"]["passed"], summary["run"]["repeats"]), (4, 4, 2))
        self.assertEqual(sorted(summary["families"]), ["arithmetic"])
        rows = jsonl(self.out / "attempts.jsonl")
        self.assertEqual([(r["task"], r["repeat"], r["retry"]) for r in rows], [("t01", 1, 0), ("t01", 2, 0), ("t02", 1, 0), ("t02", 2, 0)])
        folder = self.out / "attempts" / "t02" / "1-0"
        self.assertEqual(sorted(path.name for path in folder.iterdir()),
                         ["grade.json", "prompt.md", "solver.json", "stderr.txt", "stdout.txt", "verifier-result.json",
                          "verify-stderr.txt", "verify-stdout.txt", "workspace"])
        self.assertEqual(json.loads((folder / "workspace" / "output.json").read_text()), {"sum": 100})
        self.assertEqual((folder / "prompt.md").read_bytes(), (self.package / "tasks" / "t02" / "instruction.md").read_bytes())
        self.assertEqual(sorted(path.name for path in (folder / "workspace").iterdir()), ["input.json", "output.json"])
        self.assertEqual(sorted(path.name for path in (self.out / "identity").iterdir()), ["benchkit", "run.py", "suite.json", "tasks"])
        self.assertEqual(shapes.run_problems(self.out), [])

    def test_a_task_may_have_no_environment(self):
        shutil.rmtree(self.package / "tasks" / "t01" / "environment")
        self.assertEqual(self.run_cli("smoke", "--agent", "@noop", "--output", self.out)[0], 0)
        self.assertEqual(list((self.out / "attempts" / "t01" / "1-0" / "workspace").iterdir()), [])
        self.assertEqual(self.summary()["counts"]["completed"], 1)

    def test_a_verifier_that_writes_files_never_alters_the_captured_workspace(self):
        for task in ("t01", "t02"):
            self.edit(f"tasks/{task}/tests/verify.py", "Path(args.result).write_text",
                      "(Path(args.workspace) / 'scribble.txt').write_text('x')" + chr(10) + "Path(args.result).write_text")
        self.assertEqual(self.run_cli("full", "--agent", "@reference", "--output", self.out, "--repeats", 1)[0], 0)
        for task in ("t01", "t02"):
            self.assertEqual(sorted(p.name for p in (self.out / "attempts" / task / "1-0" / "workspace").iterdir()), ["input.json", "output.json"])
        self.assertEqual(self.summary()["overall"]["full_success_rate"], 1.0)

    def test_quick_runs_the_flagged_tasks_once_each(self):
        self.assertEqual(self.run_cli("quick", "--agent", "@reference", "--output", self.out)[0], 0)
        self.assertEqual((self.summary()["counts"]["planned"], sorted(self.summary()["tasks"])), (2, ["t01", "t02"]))

    def test_the_noop_agent_earns_nothing(self):
        self.assertEqual(self.run_cli("full", "--agent", "@noop", "--output", self.out)[0], 0)
        overall = self.summary()["overall"]
        self.assertEqual((overall["full_success_rate"], overall["mean_credit"]), (0.0, 0.0))
        self.assertEqual(self.summary()["cost"], {"usd_known": 0.0, "attempts_with_unknown_cost": 0})

    def test_declared_task_weights_apply_and_are_renormalized_over_the_selected_tasks(self):
        self.edit("tasks/t01/task.toml", "quick = true", "quick = true\nweight = 0.75")
        self.edit("tasks/t02/task.toml", "quick = true", "quick = true\nweight = 0.25")
        (self.package / "tasks" / "t02" / "solution" / "solve.py").write_text(
            "import json, sys\nfrom pathlib import Path\n"
            "Path(sys.argv[2], 'output.json').write_text(json.dumps({'sum': 1}))\n", encoding="utf-8")
        self.assertEqual(self.run_cli("full", "--agent", "@reference", "--output", self.out, "--repeats", 1)[0], 0)
        overall = self.summary()["overall"]
        self.assertEqual((overall["full_success_rate"], overall["mean_credit"]), (0.75, 0.875))
        self.assertEqual(self.run_cli("smoke", "--agent", "@reference", "--output", self.tmp / "s")[0], 0)
        self.assertEqual(self.summary(self.tmp / "s")["overall"]["full_success_rate"], 1.0)

    def test_repeats_and_jobs_overrides_apply(self):
        self.assertEqual(self.run_cli("full", "--agent", "@reference", "--output", self.out, "--repeats", 1, "--jobs", 1)[0], 0)
        summary = self.summary()
        self.assertEqual((summary["counts"]["planned"], summary["run"]["jobs"], summary["run"]["repeats"]), (2, 1, 1))

    def test_a_run_overlaps_attempts_up_to_the_declared_concurrency(self):
        self.suite(repeats=3, concurrency=3)
        self.assertEqual(self.run_cli("full", "--agent", "@reference", "--output", self.out)[0], 0)
        run = self.summary()["run"]
        self.assertGreater(run["peak_concurrency"], 1)
        self.assertLessEqual(run["peak_concurrency"], 3)

    def test_run_py_is_a_shim_that_finishes_a_smoke_run_quickly(self):
        began = time.monotonic()
        done = subprocess.run([sys.executable, str(self.package / "run.py"), "smoke", "--agent", "@reference", "--output", str(self.out)],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertLess(time.monotonic() - began, 5)
        self.assertEqual(self.summary()["overall"]["full_success_rate"], 1.0)
        refused = subprocess.run([sys.executable, str(self.package / "run.py"), "smoke", "--agent", "@mystery", "--output", str(self.tmp / "p")],
                                 capture_output=True, text=True, timeout=60)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("unknown built-in", refused.stderr)


class PreflightTests(Case):
    def test_preflight_validates_provisions_selfchecks_and_prints_the_plan(self):
        marker = self.package / "provisioned"
        shutil.copytree(FIXTURES / "agents" / "good", self.package / "adapters" / "good")
        (self.package / "adapters" / "shared").mkdir()
        (self.package / "adapters" / "shared" / "notes.txt").write_text("not an agent", encoding="utf-8")
        self.suite(provision=[[sys.executable, "-c", "open('provisioned', 'a').write('x')"]])
        report = self.tmp / "report.json"
        code, out, err = self.run_cli("preflight", "--agent", agent("good"), "--report", report)
        self.assertEqual(code, 0, out + err)
        self.assertEqual(marker.read_text(), "x")
        self.assertIn("planned attempts: 4 (2 tasks x 2 repeats), concurrency 2", out)
        self.assertIn("estimated wall time 2.0 s, upper bound 48 s", out)
        self.assertIn("estimated spend $0.04", out)
        self.assertIn("selfcheck: 7/7 passed", out)
        self.assertIn("note: adapters/shared has no run_agent.py", out)
        self.assertNotIn("adapters/ is absent", out)
        data = json.loads(report.read_text(encoding="utf-8"))
        self.assertTrue(all(check["passed"] for check in data["selfcheck"]["checks"]))
        self.assertEqual(data["problems"], [])
        self.assertEqual(data["plan"]["planned_attempts"], 4)
        self.assertEqual(data["observed_versions"], {"python --version": data["observed_versions"]["python --version"]})
        self.assertEqual(data["provision"][0]["status"], "completed")
        self.assertFalse((self.out).exists())

    def test_a_failing_selfcheck_is_a_harness_error(self):
        broken = {"platform": "test", "python": "3", "checks": [{"name": "overlap", "passed": False, "detail": "no overlap"}]}
        with mock.patch.object(cli.selfcheck, "run", return_value=broken):
            code, out, _ = self.run_cli("preflight")
        self.assertEqual(code, 1)
        self.assertIn("selfcheck: 0/1 passed", out)
        self.assertIn("FAIL overlap: no overlap", out)

    def test_preflight_notes_a_deadline_shorter_than_an_attempt(self):
        self.suite(deadline_seconds=5)
        with mock.patch.object(cli.selfcheck, "run", return_value={"platform": "t", "python": "3", "checks": []}):
            code, out, _ = self.run_cli("preflight")
        self.assertEqual(code, 0)
        self.assertIn("deadline_seconds 5 is below the longest attempt cap 16", out)

    def refused(self, expect, *argv):
        code, out, _ = self.run_cli("preflight", *argv)
        self.assertEqual(code, 2, out)
        self.assertIn(expect, out)
        self.assertNotIn("selfcheck:", out)

    def test_preflight_refuses_what_a_run_could_not_use(self):
        (self.package / "tasks" / "t01" / "solution" / "solve.py").unlink()
        self.refused("tasks/t01: missing solution/solve.py")

    def test_preflight_refuses_malformed_task_toml_and_suite(self):
        self.edit("tasks/t01/task.toml", 'split = "development"', 'split = "dev"')
        self.edit("tasks/t02/task.toml", "[agent]", "[agnet]")
        self.suite(concurrency=0)
        code, out, _ = self.run_cli("preflight")
        self.assertEqual(code, 2)
        for expect in ("t01/task.toml [metadata]: 'split' must be one of development, held-out", "t02/task.toml: missing [agent]",
                       "suite.json: 'concurrency' must be an integer >= 1"):
            self.assertIn(expect, out)

    def test_preflight_refuses_invalid_weights_and_empty_profiles(self):
        self.edit("tasks/t01/task.toml", "quick = true", "quick = true\nweight = 0.7")
        self.refused("weight declared for only 1 of 2 tasks")
        self.edit("tasks/t02/task.toml", "quick = true", "quick = true\nweight = 0.7")
        self.refused("task weights sum to 1.4, not 1")
        self.edit("tasks/t01/task.toml", "smoke = true", "smoke = false")
        self.refused("the smoke profile is empty")

    def test_preflight_refuses_a_malformed_card(self):
        card = json.loads((self.package / "card.json").read_text())
        card["claims"].append({"id": "c4", "type": "order", "higher": "ghost", "lower": "noop", "metric": "mean_credit", "resolved": "yes"})
        (self.package / "card.json").write_text(json.dumps(card), encoding="utf-8")
        code, out, _ = self.run_cli("preflight")
        self.assertEqual(code, 2)
        self.assertIn("claim c4: 'higher' must be a system named in conditions", out)
        self.assertIn("claim c4: 'resolved' must be true or false", out)

    def test_preflight_refuses_a_staging_leak_and_a_missing_agent(self):
        shutil.copy(self.package / "tasks" / "t02" / "tests" / "expected.json", self.package / "tasks" / "t02" / "environment" / "leak.json")
        self.refused("tasks/t02: staging refused: environment file leak.json is byte-identical to tests/expected.json")
        self.refused("no directory with a run_agent.py", "--agent", str(self.tmp / "nowhere"))

    def test_preflight_refuses_when_provisioning_fails(self):
        self.suite(provision=[[sys.executable, "-c", "import sys; sys.exit(3)"]])
        self.refused("provision")

    def test_preflight_without_a_suite(self):
        (self.package / "suite.json").unlink()
        self.refused("suite.json: not found")


class GradeTests(Case):
    def submissions(self):
        source = self.tmp / "subs"
        for task, name, text in (("t01", "right", '{"sum": 6}'), ("t01", "off", '{"sum": 7}'), ("t01", "empty", None),
                                 ("t02", "right", '{"sum": 100}'), ("nope", "x", "{}")):
            folder = source / task / name
            folder.mkdir(parents=True)
            if text is not None:
                (folder / "output.json").write_text(text, encoding="utf-8")
        return source

    def test_grade_only_writes_one_row_per_submission_and_leaves_them_alone(self):
        source = self.submissions()
        before = sorted(path.relative_to(source).as_posix() for path in source.rglob("*"))
        target = self.tmp / "grades.jsonl"
        code, out, err = self.run_cli("grade", "--input", source, "--output", target)
        self.assertEqual(code, 0, err)
        rows = jsonl(target)
        self.assertEqual([(r["task"], r["submission"]) for r in rows],
                         [("nope", "x"), ("t01", "empty"), ("t01", "off"), ("t01", "right"), ("t02", "right")])
        got = {(r["task"], r["submission"]): (r["grading_status"], r["full_success"], r["credit"]) for r in rows}
        self.assertEqual(got, {("nope", "x"): ("unscored", None, None), ("t01", "empty"): ("scored", False, 0.0),
                               ("t01", "off"): ("scored", False, 0.5), ("t01", "right"): ("scored", True, 1.0),
                               ("t02", "right"): ("scored", True, 1.0)})
        self.assertEqual(rows[0]["reason"], "task is not in the package")
        self.assertEqual(sorted(path.relative_to(source).as_posix() for path in source.rglob("*")), before)
        self.assertIn("graded 5 submissions", out)

    def test_grade_only_refuses_a_missing_or_empty_input(self):
        self.assertEqual(self.run_cli("grade", "--input", self.tmp / "none", "--output", self.tmp / "g.jsonl")[0], 2)
        (self.tmp / "empty").mkdir()
        self.assertEqual(self.run_cli("grade", "--input", self.tmp / "empty", "--output", self.tmp / "g.jsonl")[0], 2)

    def test_a_crashing_verifier_leaves_the_submission_unscored(self):
        (self.package / "tasks" / "t01" / "tests" / "verify.py").write_text("raise SystemExit('boom')\n", encoding="utf-8")
        source = self.submissions()
        self.run_cli("grade", "--input", source, "--output", self.tmp / "g.jsonl")
        row = next(r for r in jsonl(self.tmp / "g.jsonl") if (r["task"], r["submission"]) == ("t01", "right"))
        self.assertEqual(row["grading_status"], "unscored")
        self.assertIn("boom", row["reason"])

    def test_grade_only_reproduces_the_grades_of_a_run_from_its_captured_workspaces(self):
        self.run_cli("full", "--agent", agent("wrong"), "--output", self.out)
        source = self.tmp / "captured"
        for row in jsonl(self.out / "attempts.jsonl"):
            shutil.copytree(self.out / row["workspace"], source / row["task"] / f"{row['repeat']}-{row['retry']}")
        self.run_cli("grade", "--input", source, "--output", self.tmp / "g.jsonl")
        regraded = {(r["task"], r["submission"]): r["credit"] for r in jsonl(self.tmp / "g.jsonl")}
        ran = {(r["task"], f"{r['repeat']}-{r['retry']}"): r["credit"] for r in jsonl(self.out / "attempts.jsonl")}
        self.assertEqual(regraded, ran)


class RescoreAndCompareTests(Case):
    def test_rescore_grades_again_with_the_current_verifier_and_relaunches_nothing(self):
        self.run_cli("full", "--agent", agent("wrong"), "--output", self.out)
        ledger, attempts = (self.out / "ledger.jsonl").read_bytes(), (self.out / "attempts.jsonl").read_bytes()
        for task in ("t01", "t02"):
            self.edit(f"tasks/{task}/tests/verify.py", "W_VALID = 0.5", "W_VALID = 0.2")
        code, out, err = self.run_cli("rescore", "--output", self.out)
        self.assertEqual(code, 0, err)
        self.assertIn("nothing was relaunched", out)
        grades = jsonl(self.out / "grades-1.jsonl")
        self.assertEqual(len(grades), 4)
        self.assertEqual({(g["credit"], g["previous"]["credit"]) for g in grades}, {(0.2, 0.5)})
        summary = self.summary()
        self.assertEqual(summary["overall"]["mean_credit"], 0.2)
        self.assertEqual(summary["rescore"], {"grades": "grades-1.jsonl"})
        self.assertEqual(json.loads((self.out / "summary-0.json").read_text())["overall"]["mean_credit"], 0.5)
        self.assertEqual(json.loads((self.out / "summary-1.json").read_text()), summary)
        self.assertEqual((self.out / "ledger.jsonl").read_bytes(), ledger)
        self.assertEqual((self.out / "attempts.jsonl").read_bytes(), attempts)
        self.assertEqual(summary["counts"]["launched"], 4)
        self.assertEqual(shapes.run_problems(self.out), [])
        self.assertFalse((self.out / "OWNER").exists())

        self.edit("tasks/t01/tests/verify.py", "W_VALID = 0.2", "W_VALID = 0.4")
        self.assertEqual(self.run_cli("rescore", "--output", self.out)[0], 0)
        self.assertTrue((self.out / "grades-2.jsonl").is_file())
        self.assertEqual(json.loads((self.out / "summary-1.json").read_text())["overall"]["mean_credit"], 0.2)
        self.assertEqual(self.summary()["rescore"], {"grades": "grades-2.jsonl"})

    def test_rescore_leaves_the_captured_evidence_untouched(self):
        self.run_cli("full", "--agent", agent("good"), "--output", self.out)
        before = sorted((p.relative_to(self.out).as_posix(), p.read_bytes()) for p in (self.out / "attempts").rglob("*") if p.is_file())
        self.edit("tasks/t01/tests/verify.py", "Path(args.result).write_text",
                  "(Path(args.workspace) / 'scribble.txt').write_text('x')\nPath(args.result).write_text")
        self.assertEqual(self.run_cli("rescore", "--output", self.out)[0], 0)
        after = sorted((p.relative_to(self.out).as_posix(), p.read_bytes()) for p in (self.out / "attempts").rglob("*") if p.is_file())
        self.assertEqual([name for name, _ in after if "scribble" in name], [])
        self.assertEqual([item for item in after if "workspace" in item[0]], [item for item in before if "workspace" in item[0]])

    def test_rescore_refuses_a_directory_that_is_not_a_run(self):
        self.out.mkdir()
        self.assertEqual(self.run_cli("rescore", "--output", self.out)[0], 2)

    def test_compare_reports_paired_per_task_differences(self):
        good, wrong = self.tmp / "good", self.tmp / "wrong"
        self.run_cli("full", "--agent", agent("good"), "--output", good)
        self.run_cli("full", "--agent", agent("wrong"), "--output", wrong)
        target = self.tmp / "compare.json"
        code, out, err = self.run_cli("compare", "--a", good, "--b", wrong, "--output", target)
        self.assertEqual(code, 0, err)
        result = json.loads(out)
        self.assertEqual(json.loads(target.read_text()), result)
        self.assertEqual((result["metric"], result["common"], result["ties"], result["mean_diff"]), ("full_success_rate", 2, 0, 1.0))
        self.assertEqual(result["per_task"], {"t01": 1.0, "t02": 1.0})
        self.assertEqual(sorted(result["clusters"]), ["g1", "g2"])
        self.assertEqual((result["a"]["overall"], result["b"]["overall"], result["warnings"]), (1.0, 0.0, []))
        code, out, _ = self.run_cli("compare", "--a", good, "--b", wrong, "--metric", "mean_credit")
        self.assertEqual(json.loads(out)["mean_diff"], 0.5)
        self.assertEqual(json.loads(self.run_cli("compare", "--a", good, "--b", good)[1])["ties"], 2)

    def test_compare_warns_when_the_runs_differ_and_refuses_without_a_summary(self):
        full, smoke = self.tmp / "full", self.tmp / "smoke"
        self.run_cli("full", "--agent", "@reference", "--output", full)
        self.run_cli("smoke", "--agent", "@reference", "--output", smoke)
        result = json.loads(self.run_cli("compare", "--a", full, "--b", smoke)[1])
        self.assertEqual((result["common"], result["only_a"]), (1, ["t02"]))
        self.assertEqual(sorted(w.split(" differs")[0] for w in result["warnings"]), ["profile", "repeats"])
        self.assertEqual(self.run_cli("compare", "--a", full, "--b", self.tmp / "none")[0], 2)


class SplitTests(Case):
    """Development and held-out tasks are selected, reported and compared apart."""

    def setUp(self):
        super().setUp()
        self.edit("tasks/t02/task.toml", 'split = "development"', 'split = "held-out"')

    def test_a_mixed_run_reports_each_split_and_never_a_pooled_headline(self):
        code, out, err = self.run_cli("full", "--agent", agent("wrong"), "--output", self.out, "--repeats", 1)
        self.assertEqual(code, 0, err)
        summary = self.summary()
        self.assertEqual(sorted(summary["splits"]), ["development", "held-out"])
        self.assertEqual({name: task["split"] for name, task in summary["tasks"].items()}, {"t01": "development", "t02": "held-out"})
        self.assertEqual((summary["overall"]["split"], summary["overall"]["scored_tasks"]), ("held-out", 1))
        self.assertIn("  development: full_success_rate 0, mean_credit 0.5 over 1 tasks", out)
        self.assertIn("  held-out: full_success_rate 0, mean_credit 0.5 over 1 tasks", out)
        self.assertNotIn("units scored, 0 passed, 0 unscored; full_success_rate", out)
        self.assertEqual(shapes.run_problems(self.out), [])

    def test_split_runs_one_split_alone(self):
        code, _, err = self.run_cli("full", "--agent", "@reference", "--output", self.out, "--split", "held-out", "--repeats", 1)
        self.assertEqual(code, 0, err)
        self.assertEqual(sorted(self.summary()["tasks"]), ["t02"])
        self.assertEqual(json.loads((self.out / "run.json").read_text(encoding="utf-8"))["split"], "held-out")

    def test_an_empty_selection_is_refused_not_run(self):
        for argv in (("full", "--split", "development", "--tasks", "t02"), ("smoke", "--split", "held-out")):
            code, _, err = self.run_cli(*argv, "--agent", "@noop", "--output", self.tmp / "none")
            self.assertEqual(code, 2, err)
            self.assertIn("no task is selected", err)
            self.assertFalse((self.tmp / "none").exists())

    @mock.patch.object(cli.selfcheck, "run", return_value={"checks": [], "platform": "test"})   # timing checks are not under test
    def test_preflight_refuses_an_empty_selection_and_notes_a_mixed_one(self, _selfcheck):
        self.edit("tasks/t02/task.toml", 'split = "held-out"', 'split = "development"')
        code, out, err = self.run_cli("preflight", "--split", "held-out")
        self.assertEqual((code, "traceback" in (out + err).lower()), (2, False))
        self.assertIn("no task is selected", out)
        self.edit("tasks/t02/task.toml", 'split = "development"', 'split = "held-out"')
        code, out, err = self.run_cli("preflight")
        self.assertEqual(code, 0, out + err)
        self.assertIn("note: the selection spans the development and held-out splits", out)
        code, out, err = self.run_cli("preflight", "--split", "held-out")
        self.assertEqual(code, 0, out + err)
        self.assertNotIn("spans", out)
        self.assertIn("planned attempts: 2 (1 tasks x 2 repeats)", out)

    def test_compare_warns_on_mixed_splits_and_can_take_one(self):
        good, wrong = self.tmp / "good", self.tmp / "wrong"
        self.run_cli("full", "--agent", agent("good"), "--output", good, "--repeats", 1)
        self.run_cli("full", "--agent", agent("wrong"), "--output", wrong, "--repeats", 1)
        mixed = json.loads(self.run_cli("compare", "--a", good, "--b", wrong)[1])
        self.assertEqual((mixed["common"], mixed["warnings"]),
                         (2, ["the tasks span the development and held-out splits and are paired together; --split compares one"]))
        one = json.loads(self.run_cli("compare", "--a", good, "--b", wrong, "--split", "held-out")[1])
        self.assertEqual((one["common"], one["per_task"], one["split"], one["warnings"]), (1, {"t02": 1.0}, "held-out", []))
        self.assertEqual((one["a"]["overall"], one["b"]["overall"]), (1.0, 0.0))


if __name__ == "__main__":
    unittest.main()
