"""Whole runs of the package-mini fixture: solver statuses, retries, caps, resume and refusals."""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import _thread
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "scripts"
FIXTURES = TESTS / "fixtures"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from benchkit import cli, identity, runner, shapes  # noqa: E402


def agent(name):
    return str(FIXTURES / "agents" / name)


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(identity.discard, self.tmp)
        self.package, self.out = self.tmp / "package-mini", self.tmp / "o"
        shutil.copytree(FIXTURES / "package-mini", self.package)
        shutil.copytree(SCRIPTS / "benchkit", self.package / "benchkit", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy(SCRIPTS / "run.py", self.package / "run.py")

    def setenv(self, **values):
        patcher = mock.patch.dict(os.environ, {key: str(value) for key, value in values.items()})
        patcher.start()
        self.addCleanup(patcher.stop)

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

    def rows(self, out=None):
        text = ((out or self.out) / "attempts.jsonl").read_text(encoding="utf-8")
        return [json.loads(line) for line in text.splitlines()]

    def summary(self, out=None):
        return json.loads(((out or self.out) / "summary.json").read_text(encoding="utf-8"))

    def launches(self):
        rows = [json.loads(line) for line in (self.out / "ledger.jsonl").read_text(encoding="utf-8").splitlines()]
        return sum(row["kind"] == "launched" for row in rows)

    def one(self, name, *extra):
        """One attempt of t01 by the named fixture agent; every file the run leaves must validate."""
        done = self.run_cli("full", "--agent", agent(name), "--output", self.out, "--tasks", "t01", "--repeats", 1, *extra)
        self.assertEqual(shapes.run_problems(self.out), [])
        return done


class StatusTests(Case):
    def test_good_and_wrong_agents(self):
        for name, success, credit in (("good", 1.0, 1.0), ("wrong", 0.0, 0.5)):
            out = self.tmp / name
            code, _, err = self.run_cli("full", "--agent", agent(name), "--output", out)
            self.assertEqual(code, 0, err)
            overall = self.summary(out)["overall"]
            self.assertEqual((overall["full_success_rate"], overall["mean_credit"]), (success, credit))
            self.assertEqual(self.summary(out)["counts"]["launched"], 4)

    def test_refused_and_cut_off_are_graded_like_other_delivered_work(self):
        for name, status in (("refuse", "refused"), ("cutoff", "cut-off")):
            self.setUp()
            self.assertEqual(self.one(name)[0], 0)
            (row,) = self.rows()
            self.assertEqual((row["status"], row["grading_status"], row["full_success"], row["credit"]), (status, "scored", False, 0.0))
            self.assertEqual(self.summary()["counts"]["by_status"][status], 1)

    def test_a_crash_without_a_protocol_line_is_an_unscored_infrastructure_error(self):
        code, _, _ = self.one("crash")
        self.assertEqual(code, 0)
        (row,) = self.rows()
        self.assertEqual((row["status"], row["grading_status"], row["credit"]), ("infrastructure-error", "unscored", None))
        self.assertIn("no protocol line", row["reason"])
        self.assertIn("crashed on purpose", row["reason"])
        self.assertEqual(row["grade_reason"], "not graded: infrastructure-error")
        counts = self.summary()["counts"]
        self.assertEqual((counts["scored"], counts["unscored"]), (0, 1))
        self.assertTrue((self.out / "attempts" / "t01" / "1-0" / "workspace").is_dir())

    def test_a_solver_that_outlives_the_cap_is_agent_budget_exhausted_and_graded(self):
        self.edit("tasks/t01/task.toml", "timeout_sec = 5", "timeout_sec = 0.5")
        self.suite(grace_seconds=0.3)
        began = time.monotonic()
        self.assertEqual(self.one("slow")[0], 0)
        self.assertLess(time.monotonic() - began, 6)
        (row,) = self.rows()
        self.assertEqual((row["status"], row["grading_status"], row["full_success"]), ("agent-budget-exhausted", "scored", False))
        self.assertTrue(row["reason"].startswith("runner cap"))

    def test_processes_left_behind_are_stopped_and_flagged(self):
        marker = self.tmp / "marker"
        self.setenv(BENCHKIT_FIXTURE_MARKER=marker)
        self.assertEqual(self.one("grandchild")[0], 0)
        (row,) = self.rows()
        self.assertEqual((row["status"], row["left_running"], row["full_success"]), ("completed", True, True))
        self.assertIn("left running", row["reason"])
        time.sleep(2.2)
        self.assertFalse(marker.exists())

    def test_a_transient_failure_is_retried_only_within_the_budget(self):
        self.setenv(BENCHKIT_FIXTURE_STATE=self.tmp / "state-a")
        self.assertEqual(self.one("transient")[0], 0)
        (row,) = self.rows()
        self.assertEqual((row["status"], self.launches()), ("infrastructure-error", 1))
        self.assertIn("upstream hiccup", row["reason"])

        self.setUp()
        self.setenv(BENCHKIT_FIXTURE_STATE=self.tmp / "state-b")
        self.suite(transient_retry_budget=1)
        self.assertEqual(self.one("transient")[0], 0)
        first, second = self.rows()
        self.assertEqual([(r["retry"], r["status"]) for r in (first, second)], [(0, "infrastructure-error"), (1, "completed")])
        counts = self.summary()["counts"]
        self.assertEqual((counts["launched"], counts["retries"], counts["completed"], counts["passed"], counts["unscored"]), (2, 1, 1, 1, 0))

    def test_agent_budget_exhaustion_is_never_retried(self):
        self.edit("tasks/t01/task.toml", "timeout_sec = 5", "timeout_sec = 0.4")
        self.suite(grace_seconds=0.2, transient_retry_budget=3)
        self.one("slow")
        self.assertEqual(len(self.rows()), 1)

    def test_a_usage_limit_interrupts_the_run_and_resume_completes_it(self):
        code, out, _ = self.run_cli("full", "--agent", agent("usagelimit"), "--output", self.out, "--repeats", 1, "--jobs", 1)
        self.assertEqual(code, 4)
        self.assertIn("resume --output", out)
        self.assertEqual(json.loads((self.out / "run.json").read_text())["state"], "usage-limit")
        by = self.summary()["counts"]["by_status"]
        self.assertEqual((by["interrupted"], by["not-launched"]), (1, 1))
        self.assertFalse((self.out / "OWNER").exists())

        self.setenv(BENCHKIT_FIXTURE_OK=1)
        code, _, err = self.run_cli("resume", "--output", self.out)
        self.assertEqual(code, 0, err)
        summary = self.summary()
        self.assertEqual((summary["counts"]["completed"], summary["counts"]["passed"], summary["overall"]["full_success_rate"]), (2, 2, 1.0))
        done = {(row["task"], row["retry"]): row["status"] for row in self.rows()}
        self.assertEqual(done, {("t01", 0): "interrupted", ("t01", 1): "completed", ("t02", 0): "completed"})
        self.assertEqual(self.launches(), 3)
        self.assertEqual(shapes.run_problems(self.out), [])


class CapTests(Case):
    def slow_suite(self):
        self.edit("tasks/t01/task.toml", "timeout_sec = 5", "timeout_sec = 0.5")
        self.edit("tasks/t02/task.toml", "timeout_sec = 5", "timeout_sec = 0.5")
        for task in ("t01", "t02"):
            self.edit(f"tasks/{task}/task.toml", "timeout_sec = 10", "timeout_sec = 1")
        self.suite(grace_seconds=0.5)

    def test_the_deadline_stops_admission_and_resume_finishes_the_rest(self):
        self.slow_suite()
        code, out, _ = self.run_cli("full", "--agent", agent("slow"), "--output", self.out, "--jobs", 1, "--deadline", 2.5)
        self.assertEqual(code, 3)
        summary = self.summary()
        by = summary["counts"]["by_status"]
        self.assertGreaterEqual(by["not-launched"], 1)
        self.assertTrue(summary["run"]["deadline_reached"])
        self.assertIn("not launched", out)
        code, _, err = self.run_cli("resume", "--output", self.out, "--jobs", 4, "--deadline", 60)
        self.assertEqual(code, 0, err)
        by = self.summary()["counts"]["by_status"]
        self.assertEqual((by["agent-budget-exhausted"], by["not-launched"]), (4, 0))

    def test_the_launch_budget_counts_over_the_whole_run(self):
        self.suite(launch_budget=2)
        code, _, _ = self.run_cli("full", "--agent", "@reference", "--output", self.out, "--jobs", 1)
        self.assertEqual(code, 3)
        summary = self.summary()
        self.assertEqual((summary["counts"]["launched"], summary["counts"]["not_launched"]), (2, 2))
        self.assertEqual(self.launches(), 2)
        code, _, _ = self.run_cli("resume", "--output", self.out)
        self.assertEqual((code, self.launches()), (3, 2))

    def test_a_stop_band_skips_the_repeats_a_settled_task_would_run(self):
        self.suite(repeats=4)
        code, _, err = self.run_cli("full", "--agent", "@reference", "--output", self.out, "--stop-band", 0, 0.3, "--level", 0.8)
        self.assertEqual(code, 0, err)
        summary = self.summary()
        self.assertEqual((summary["counts"]["planned"], summary["counts"]["launched"], summary["counts"]["not_launched"]), (8, 4, 4))
        skipped = [item for item in summary["exclusions"] if item["reason"].startswith("not-launched: stopped early")]
        self.assertEqual(sorted((item["task"], item["repeat"]) for item in skipped),
                         [("t01", 3), ("t01", 4), ("t02", 3), ("t02", 4)])
        self.assertEqual(summary["tasks"]["t01"]["scored"], 2)
        self.assertEqual(summary["overall"]["missing_repeats"], 4)
        self.assertEqual(summary["overall"]["full_success_rate"], 1.0)
        code, _, _ = self.run_cli("resume", "--output", self.out)
        self.assertEqual((code, self.launches()), (0, 4))
        ledger = (self.out / "ledger.jsonl").read_text(encoding="utf-8")
        self.assertEqual(ledger.count("stopped early"), 4)

    def test_a_usage_limit_ends_the_stop_band_rounds_too(self):
        code, _, _ = self.run_cli("full", "--agent", agent("usagelimit"), "--output", self.out, "--jobs", 1, "--stop-band", 0, 1)
        self.assertEqual((code, self.launches()), (4, 1))
        self.assertEqual(self.summary()["counts"]["by_status"]["interrupted"], 1)

    def test_a_task_selection_replaces_the_profile(self):
        code, _, err = self.run_cli("smoke", "--agent", "@reference", "--output", self.out, "--tasks", "t02")
        self.assertEqual(code, 0, err)
        self.assertEqual(list(self.summary()["tasks"]), ["t02"])


class InterruptTests(Case):
    def interrupt_once_running(self):
        """Ctrl-C the main thread shortly after the first launch is on the ledger."""
        def watch():
            ledger = self.out / "ledger.jsonl"
            for _ in range(600):
                if ledger.is_file() and '"launched"' in ledger.read_text(encoding="utf-8"):
                    break
                time.sleep(0.05)
            time.sleep(0.4)
            _thread.interrupt_main()

        threading.Thread(target=watch, daemon=True).start()

    def test_ctrl_c_cancels_running_attempts_and_the_run_resumes(self):
        self.interrupt_once_running()
        began = time.monotonic()
        code, out, _ = self.run_cli("full", "--agent", agent("slow"), "--output", self.out)
        self.assertEqual(code, 4)
        self.assertLess(time.monotonic() - began, 5)
        by = self.summary()["counts"]["by_status"]
        self.assertEqual(by["canceled"] + by["not-launched"] + by["interrupted"], 4)
        self.assertGreaterEqual(by["canceled"], 1)
        self.assertEqual(json.loads((self.out / "run.json").read_text())["state"], "interrupted")
        self.assertIn("resume --output", out)
        self.assertFalse((self.out / "OWNER").exists())
        self.assertEqual(shapes.run_problems(self.out), [])

        self.setenv(BENCHKIT_FIXTURE_SLEEP=0)
        code, _, err = self.run_cli("resume", "--output", self.out)
        self.assertEqual(code, 0, err)
        summary = self.summary()
        self.assertEqual((summary["counts"]["completed"], summary["overall"]["full_success_rate"]), (4, 1.0))
        self.assertEqual(len(json.loads((self.out / "run.json").read_text())["invocations"]), 2)

    def test_an_interrupt_outside_a_run_exits_4(self):
        with mock.patch.object(cli.suites, "load", side_effect=KeyboardInterrupt):
            code, _, err = self.run_cli("full", "--agent", "@noop", "--output", self.out)
        self.assertEqual((code, "interrupted" in err), (4, True))

    def test_an_unexpected_failure_is_a_harness_error_that_still_leaves_the_outputs(self):
        with mock.patch.object(runner.Run, "execute", side_effect=RuntimeError("disk on fire")):
            code, _, err = self.run_cli("full", "--agent", "@noop", "--output", self.out)
        self.assertEqual(code, 1)
        self.assertIn("disk on fire", err)
        self.assertEqual(json.loads((self.out / "run.json").read_text())["state"], "failed")
        self.assertEqual(self.summary()["counts"]["not_launched"], 4)
        self.assertFalse((self.out / "OWNER").exists())
        self.assertEqual(self.run_cli("resume", "--output", self.out)[0], 0)
        self.assertEqual(self.summary()["counts"]["completed"], 4)


class ResumeTests(Case):
    def interrupted(self, name="usagelimit", agent_dir=None):
        code, _, err = self.run_cli("full", "--agent", agent_dir or agent(name), "--output", self.out, "--repeats", 1, "--jobs", 1)
        self.assertEqual(code, 4, err)

    def test_resume_after_a_ledger_truncated_mid_line(self):
        self.assertEqual(self.run_cli("full", "--agent", agent("good"), "--output", self.out)[0], 0)
        ledger = self.out / "ledger.jsonl"
        data = ledger.read_bytes()
        ledger.write_bytes(data[:-25])
        (self.out / "summary.json").unlink()
        code, _, err = self.run_cli("resume", "--output", self.out)
        self.assertEqual(code, 0, err)
        summary = self.summary()
        self.assertEqual((summary["counts"]["passed"], summary["counts"]["launched"]), (4, 5))
        self.assertEqual(summary["counts"]["completed"], 4)
        notes = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if '"note"' in line]
        self.assertTrue(any("torn" in note.get("message", "") for note in notes))
        self.assertEqual(shapes.run_problems(self.out), [])

    def test_a_launch_the_ledger_lost_is_rerun_over_its_stale_folder(self):
        self.assertEqual(self.run_cli("full", "--agent", agent("good"), "--output", self.out)[0], 0)
        ledger = self.out / "ledger.jsonl"
        kept = [line for line in ledger.read_text(encoding="utf-8").splitlines() if '"t02/2"' not in line or '"planned"' in line]
        ledger.write_text(chr(10).join(kept) + chr(10), encoding="utf-8")
        self.assertTrue((self.out / "attempts" / "t02" / "2-0").is_dir())
        code, _, err = self.run_cli("resume", "--output", self.out)
        self.assertEqual(code, 0, err)
        summary = self.summary()
        self.assertEqual((summary["counts"]["passed"], summary["counts"]["launched"], summary["counts"]["retries"]), (4, 4, 0))
        self.assertEqual(self.launches(), 4)

    def test_a_changed_task_byte_refuses_the_resume_and_changes_nothing(self):
        self.interrupted()
        before = (self.out / "ledger.jsonl").read_bytes()
        self.edit("tasks/t01/instruction.md", "Add", "Sum")
        code, _, err = self.run_cli("resume", "--output", self.out)
        self.assertEqual(code, 2)
        self.assertIn("changed: tasks/t01/instruction.md", err)
        self.assertEqual((self.out / "ledger.jsonl").read_bytes(), before)
        self.assertFalse((self.out / "OWNER").exists())

    def test_a_changed_agent_byte_refuses_the_resume(self):
        copy = self.tmp / "my-agent"
        shutil.copytree(agent("usagelimit"), copy)
        self.interrupted(agent_dir=str(copy))
        (copy / "run_agent.py").write_text((copy / "run_agent.py").read_text(encoding="utf-8") + "\n# tweak\n", encoding="utf-8")
        code, _, err = self.run_cli("resume", "--output", self.out)
        self.assertEqual(code, 2)
        self.assertIn("changed: agent/run_agent.py", err)

    def test_missing_and_extra_files_are_changes_too(self):
        self.interrupted()
        (self.package / "tasks" / "t02" / "extra.txt").write_text("x", encoding="utf-8")
        (self.package / "benchkit" / "INTERFACE.md").unlink()
        code, _, err = self.run_cli("resume", "--output", self.out)
        self.assertEqual(code, 2)
        self.assertIn("extra: tasks/t02/extra.txt", err)
        self.assertIn("missing: benchkit/INTERFACE.md", err)

    def test_a_changed_observed_version_refuses_the_resume(self):
        code = "import os; print(os.environ.get('BENCHKIT_TEST_VERSION', 'none'))"
        self.suite(observe=[[sys.executable, "-c", code]])
        self.setenv(BENCHKIT_TEST_VERSION="1.0")
        self.interrupted()
        self.assertEqual(self.summary()["run"]["observed_versions"], {f"{sys.executable} -c {code}": "1.0"})
        os.environ["BENCHKIT_TEST_VERSION"] = "2.0"
        code_, _, err = self.run_cli("resume", "--output", self.out)
        self.assertEqual(code_, 2)
        self.assertIn("'1.0' then, '2.0' now", err)

    def test_a_held_owner_lock_refuses(self):
        self.interrupted()
        (self.out / "OWNER").write_text(json.dumps({"pid": 4242, "host": "elsewhere", "started": "then"}), encoding="utf-8")
        code, _, err = self.run_cli("resume", "--output", self.out)
        self.assertEqual(code, 2)
        self.assertIn("4242", err)

    def test_a_foreign_or_corrupt_ledger_record_refuses_the_resume(self):
        self.interrupted()
        ledger = self.out / "ledger.jsonl"
        original = ledger.read_bytes()
        with open(ledger, "ab") as file:
            file.write(json.dumps({"kind": "launched", "key": "t99/1", "retry": 0}).encode() + b"\n")
        code, _, err = self.run_cli("resume", "--output", self.out)
        self.assertEqual(code, 2)
        self.assertIn("never planned: t99/1", err)
        ledger.write_bytes(original + b"garbage\n" + original.splitlines()[0] + b"\n")
        code, _, err = self.run_cli("resume", "--output", self.out)
        self.assertEqual(code, 2)
        self.assertIn("is not a ledger record", err)

    def test_resume_of_a_directory_that_is_not_a_run(self):
        self.out.mkdir()
        code, _, err = self.run_cli("resume", "--output", self.out)
        self.assertEqual(code, 2)
        self.assertIn("not a run directory", err)


class RefusalTests(Case):
    def refused(self, *argv, expect=""):
        code, _, err = self.run_cli(*argv)
        self.assertEqual(code, 2, err)
        self.assertIn(expect, err)
        return err

    def test_a_non_empty_output_directory(self):
        self.out.mkdir()
        (self.out / "x").write_text("x", encoding="utf-8")
        self.refused("smoke", "--agent", "@noop", "--output", self.out, expect="not empty")

    def test_an_output_inside_the_tasks(self):
        self.refused("smoke", "--agent", "@noop", "--output", self.package / "tasks" / "o", expect="inside tasks")

    def test_unknown_agent_and_task(self):
        self.refused("smoke", "--agent", "@mystery", "--output", self.out, expect="unknown built-in")
        self.refused("smoke", "--agent", self.tmp / "no-agent", "--output", self.out, expect="no directory with a run_agent.py")
        self.refused("smoke", "--agent", "@noop", "--output", self.out, "--tasks", "t99", expect="unknown task 't99'")

    def test_a_staging_leak_refuses_before_anything_runs(self):
        shutil.copy(self.package / "tasks" / "t01" / "tests" / "expected.json", self.package / "tasks" / "t01" / "environment" / "hint.json")
        self.refused("full", "--agent", "@noop", "--output", self.out, expect="byte-identical")
        self.assertFalse(self.out.exists())

    def test_an_invalid_suite_and_bad_stop_band(self):
        self.refused("full", "--agent", "@noop", "--output", self.out, "--stop-band", 0.8, 0.2, expect="--stop-band")
        self.suite(repeats=0)
        self.refused("full", "--agent", "@noop", "--output", self.out, expect="'repeats' must be an integer >= 1")

    def test_a_bad_command_line_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            cli.main(self.package, ["full"])
        self.assertEqual(raised.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
