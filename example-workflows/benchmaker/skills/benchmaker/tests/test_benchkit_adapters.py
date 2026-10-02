"""Solver protocol, status mapping, agent resolution, verifier invocation, suite loading and the run plan."""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
import unittest
from pathlib import Path

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "scripts"
FIXTURES = TESTS / "fixtures"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from benchkit import adapters, suite  # noqa: E402


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.package = self.tmp / "package-mini"
        shutil.copytree(FIXTURES / "package-mini", self.package)


class ClassifyTests(unittest.TestCase):
    def test_the_protocol_line_names_the_status_and_the_exit_code_must_agree(self):
        table = [
            (0, "completed", "completed", False), (0, "refused", "refused", False), (0, "cut-off", "cut-off", False),
            (2, "timeout", "agent-budget-exhausted", False), (3, "usage-limit", "interrupted", False),
            (1, "error", "infrastructure-error", True), (0, "error", "infrastructure-error", True),
            (1, "completed", "infrastructure-error", True), (0, "timeout", "infrastructure-error", True),
            (0, "usage-limit", "infrastructure-error", True), (2, "refused", "infrastructure-error", True),
        ]
        for code, reported, status, transient in table:
            with self.subTest(code=code, reported=reported):
                verdict = adapters.classify(code, {"status": reported, "final": "text"}, "")
                self.assertEqual((verdict["status"], verdict["transient"]), (status, transient))
                self.assertEqual(verdict["usage_limit"], reported == "usage-limit" and status == "interrupted")

    def test_a_missing_line_is_an_infrastructure_error_with_the_stderr_tail(self):
        verdict = adapters.classify(1, None, "Traceback\nValueError: nope")
        self.assertEqual((verdict["status"], verdict["transient"]), ("infrastructure-error", True))
        self.assertIn("exit code 1 and no protocol line", verdict["reason"])
        self.assertIn("ValueError: nope", verdict["reason"])

    def test_the_reason_carries_the_solvers_error_text(self):
        verdict = adapters.classify(1, {"status": "error", "final": "rate limited"}, "")
        self.assertEqual(verdict["reason"], "solver reported an error (exit code 1): rate limited")

    def test_nothing_but_an_ended_turn_is_a_clean_status(self):
        for reported in adapters.ENDED:
            self.assertEqual(adapters.classify(0, {"status": reported}, "")["reason"], "")


class ProtocolLineTests(Case):
    def read(self, text):
        path = self.tmp / "stdout.txt"
        path.write_bytes(text if isinstance(text, bytes) else text.encode("utf-8"))
        return adapters.protocol_line(path)

    def test_the_last_non_empty_line_is_the_record(self):
        line = json.dumps({"status": "completed", "model": "m"})
        self.assertEqual(self.read(f"chatter\n{{\"status\": \"error\"}}\n{line}\n\n")["model"], "m")
        self.assertEqual(self.read(b"\xef\xbb\xbf" + line.encode() + b"\r\n")["status"], "completed")

    def test_only_the_end_of_a_very_long_output_is_searched(self):
        line = json.dumps({"status": "refused", "final": "y" * 70000})
        self.assertEqual(self.read(b"noise" * 400000 + b"\n" + line.encode() + b"\n")["status"], "refused")

    def test_anything_else_is_no_record(self):
        for text in ("", "plain words\n", '{"status": "weird"}\n', '["completed"]\n', '{"status": "completed"}\ntrailing text\n'):
            with self.subTest(text=text):
                self.assertIsNone(self.read(text))
        self.assertIsNone(adapters.protocol_line(self.tmp / "missing.txt"))


class ResolveTests(Case):
    def test_builtins_and_directories(self):
        self.assertEqual(adapters.resolve("@reference"), adapters.Agent("@reference", "reference"))
        self.assertEqual(adapters.resolve("@noop").kind, "noop")
        found = adapters.resolve(str(FIXTURES / "agents" / "good"))
        self.assertEqual((found.kind, found.path), ("dir", (FIXTURES / "agents" / "good").resolve()))

    def test_a_relative_directory_is_found_from_the_package(self):
        shutil.copytree(FIXTURES / "agents" / "good", self.package / "adapters" / "good")
        self.assertEqual(adapters.resolve("adapters/good", self.package).path, (self.package / "adapters" / "good").resolve())

    def test_unknown_builtins_and_missing_directories_are_refused(self):
        for spec in ("@mystery", str(self.tmp / "none")):
            with self.assertRaises(adapters.AgentError):
                adapters.resolve(spec)
        (self.tmp / "empty").mkdir()
        with self.assertRaises(adapters.AgentError):
            adapters.resolve(str(self.tmp / "empty"))


class SolveTests(Case):
    def attempt(self, spec, **options):
        task = suite.load(self.package).tasks["t01"]
        folder, workspace = self.tmp / "attempt", self.tmp / "workspace"
        folder.mkdir()
        workspace.mkdir()
        (workspace / "input.json").write_text('{"numbers": [1, 2, 3]}', encoding="utf-8")
        (folder / "prompt.md").write_text("add them\n", encoding="utf-8")
        return adapters.solve(adapters.resolve(spec), task, workspace, folder, grace=options.get("grace", 1.0),
                              cancel=options.get("cancel")), workspace, folder

    def test_the_noop_agent_launches_nothing(self):
        result, workspace, _ = self.attempt("@noop")
        self.assertEqual((result["status"], result["command"], result["cost_usd"]), ("completed", [], 0.0))
        self.assertEqual(sorted(path.name for path in workspace.iterdir()), ["input.json"])

    def test_the_reference_runs_solve_py_in_the_workspace(self):
        result, workspace, _ = self.attempt("@reference")
        self.assertEqual(result["status"], "completed")
        self.assertEqual(json.loads((workspace / "output.json").read_text()), {"sum": 6})

    def test_a_failing_reference_is_an_infrastructure_error(self):
        (self.package / "tasks" / "t01" / "solution" / "solve.py").write_text("raise SystemExit('no good')\n", encoding="utf-8")
        result, _, _ = self.attempt("@reference")
        self.assertEqual(result["status"], "infrastructure-error")
        self.assertIn("reference solution failed: exit code 1: no good", result["reason"])

    def test_a_directory_agent_gets_the_documented_command_and_reports_usage(self):
        result, workspace, folder = self.attempt(str(FIXTURES / "agents" / "good"))
        command = result["command"]
        self.assertEqual(command[1:2], [str(FIXTURES / "agents" / "good" / "run_agent.py")])
        self.assertEqual(command[2:], ["--workspace", str(workspace), "--prompt-file", str(folder / "prompt.md"),
                                       "--transcript", str(folder / "transcript.jsonl"), "--timeout", "5"])
        self.assertEqual((result["status"], result["model"], result["cost_usd"], result["exit_code"]), ("completed", "fixture-model", 0.01, 0))
        self.assertEqual((result["final"], result["live_workspace"]), ("completed", str(workspace)))
        self.assertTrue((folder / "stdout.txt").read_text().strip().endswith("}"))

    def test_cancel_stops_the_solver(self):
        cancel = threading.Event()
        cancel.set()
        result, _, _ = self.attempt(str(FIXTURES / "agents" / "slow"), cancel=cancel)
        self.assertEqual(result["status"], "canceled")

    def test_a_program_that_cannot_start_is_an_infrastructure_error(self):
        broken = self.tmp / "broken"
        broken.mkdir()
        (broken / "run_agent.py").write_text("raise SystemExit(7)\n", encoding="utf-8")
        result, _, _ = self.attempt(str(broken))
        self.assertEqual((result["status"], result["exit_code"]), ("infrastructure-error", 7))


class VerifyTests(Case):
    def verify(self, source=None, text=None):
        task = suite.load(self.package).tasks["t01"]
        if source is not None:
            (self.package / "tasks" / "t01" / "tests" / "verify.py").write_text(source, encoding="utf-8")
        workspace = self.tmp / "workspace"
        shutil.rmtree(workspace, ignore_errors=True)
        workspace.mkdir()
        if text is not None:
            (workspace / "output.json").write_text(text, encoding="utf-8")
        return adapters.verify(task, workspace, self.tmp / "log")

    def test_a_scored_result_is_normalized(self):
        grade = self.verify(text='{"sum": 6}')
        self.assertEqual((grade["grading_status"], grade["full_success"], grade["credit"], grade["exit_code"]), ("scored", True, 1.0, 0))
        self.assertTrue((self.tmp / "log" / "verifier-result.json").is_file())

    def test_a_crash_a_missing_result_a_bad_result_and_a_timeout_are_unscored(self):
        cases = {"crash": ("raise SystemExit('boom')\n", "boom"), "nothing": ("pass\n", "no valid JSON"),
                 "garbage": ("import sys; open(sys.argv[sys.argv.index('--result') + 1], 'w').write('{')\n", "no valid JSON"),
                 "list": ("import sys; open(sys.argv[sys.argv.index('--result') + 1], 'w').write('[1]')\n", "not a JSON object")}
        for name, (source, expect) in cases.items():
            with self.subTest(name):
                grade = self.verify(source)
                self.assertEqual(grade["grading_status"], "unscored")
                self.assertIn(expect, grade["reason"])
        self.edit_timeout()
        grade = self.verify("import time; time.sleep(30)\n")
        self.assertEqual(grade["grading_status"], "unscored")
        self.assertIn("exceeded its", grade["reason"])

    def edit_timeout(self):
        path = self.package / "tasks" / "t01" / "task.toml"
        path.write_text(path.read_text(encoding="utf-8").replace("timeout_sec = 10", "timeout_sec = 0.5"), encoding="utf-8")

    def test_a_contract_violation_is_indeterminate(self):
        source = ("import json, sys\n"
                  "open(sys.argv[sys.argv.index('--result') + 1], 'w').write(json.dumps("
                  "{'grading_status': 'scored', 'full_success': True, 'credit': 1.0, 'critical_failures': ['cheated']}))\n")
        grade = self.verify(source)
        self.assertEqual(grade["grading_status"], "indeterminate")
        self.assertIn("critical failure with full_success true", grade["reason"])


class SuiteTests(Case):
    def test_the_fixture_loads_with_its_tasks_and_defaults(self):
        loaded = suite.load(self.package)
        self.assertEqual((loaded.name, loaded.repeats, loaded.concurrency, loaded.grace, loaded.primary), ("package-mini", 2, 2, 1.0, "full_success_rate"))
        self.assertEqual(list(loaded.tasks), ["t01", "t02"])
        task = loaded.tasks["t01"]
        self.assertEqual((task.family, task.source_group, task.split, task.agent_seconds, task.verifier_seconds, task.weight),
                         ("arithmetic", "g1", "development", 5.0, 10.0, None))
        self.assertEqual(suite.attempt_cap(loaded, task), 16.0)

    def test_defaults_when_the_optional_keys_are_absent(self):
        (self.package / "suite.json").write_text('{"name": "x", "repeats": 1, "concurrency": 1}', encoding="utf-8")
        loaded = suite.load(self.package)
        self.assertEqual((loaded.grace, loaded.deadline_seconds, loaded.launch_budget, loaded.retry_budget, loaded.observe), (5.0, None, None, 0, []))

    def test_profiles_select_flagged_tasks_and_a_selection_overrides_them(self):
        loaded = suite.load(self.package)
        names = lambda profile, only=None: [task.id for task in suite.select(loaded, profile, only)]  # noqa: E731
        self.assertEqual((names("smoke"), names("quick"), names("full")), (["t01"], ["t01", "t02"], ["t01", "t02"]))
        self.assertEqual(names("smoke", ["t02"]), ["t02"])
        with self.assertRaises(suite.SuiteError):
            suite.select(loaded, "smoke", ["t99"])
        self.assertEqual((suite.repeats_for(loaded, "smoke"), suite.repeats_for(loaded, "full"), suite.repeats_for(loaded, "full", 5)), (1, 2, 5))

    def test_every_problem_is_reported_at_once(self):
        (self.package / "tasks" / "t01" / "instruction.md").write_text("  \n", encoding="utf-8")
        (self.package / "tasks" / "t02" / "task.toml").write_text("[metadata\n", encoding="utf-8")
        (self.package / "tasks" / "Bad Name").mkdir()
        (self.package / "suite.json").write_text('{"repeats": "2"}', encoding="utf-8")
        found, problems = suite.read(self.package)
        self.assertIsNone(found)
        text = "\n".join(problems)
        for expect in ("tasks/t01: instruction.md is empty", "tasks/t02/task.toml", "tasks/Bad Name: task ids", "missing 'name'", "'repeats' must be"):
            self.assertIn(expect, text)

    def test_plan_estimates_wall_time_and_bounds_it(self):
        loaded = suite.load(self.package)
        tasks = suite.select(loaded, "full")
        plan = suite.plan(loaded, tasks, 2, jobs=2, deadline=None)
        self.assertEqual((plan["planned_attempts"], plan["estimated_wall_seconds"], plan["wall_upper_bound_seconds"]), (4, 2, 48.0))
        self.assertEqual((plan["estimated_spend_usd"], plan["launch_budget"], plan["attempt_caps_seconds"]), (0.04, 20, {"t01": 16.0, "t02": 16.0}))
        capped = suite.plan(loaded, tasks, 2, jobs=2, deadline=10.0)
        self.assertEqual(capped["wall_upper_bound_seconds"], 10.0)
        single = suite.plan(loaded, suite.select(loaded, "smoke"), 1, jobs=8, deadline=None)
        self.assertEqual((single["planned_attempts"], single["estimated_wall_seconds"], single["wall_upper_bound_seconds"]), (1, 1, 18.0))
        loaded.attempt_seconds_estimate = loaded.attempt_cost_estimate_usd = None
        unknown = suite.plan(loaded, tasks, 2, jobs=2, deadline=None)
        self.assertEqual((unknown["estimated_wall_seconds"], unknown["estimated_spend_usd"]), (None, None))

    def test_staging_problems_name_each_leaking_task(self):
        loaded = suite.load(self.package)
        self.assertEqual(suite.staging_problems(list(loaded.tasks.values())), [])
        (self.package / "tasks" / "t01" / "environment" / "solution").mkdir()
        (self.package / "tasks" / "t01" / "environment" / "solution" / "a.txt").write_text("x", encoding="utf-8")
        problems = suite.staging_problems(list(loaded.tasks.values()))
        self.assertEqual(len(problems), 1)
        self.assertIn("tasks/t01: staging refused: evaluator name 'solution'", problems[0])


if __name__ == "__main__":
    unittest.main()
