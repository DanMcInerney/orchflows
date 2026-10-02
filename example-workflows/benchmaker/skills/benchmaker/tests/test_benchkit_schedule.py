"""Ledger, OwnerLock and run_units: overlap, caps, retries, resume."""
from __future__ import annotations

import _thread
import json
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from benchkit import launch  # noqa: E402
from benchkit.schedule import Busy, Ledger, LedgerError, OwnerLock, Unit, run_units  # noqa: E402


TREE = """
import subprocess, sys, time
subprocess.Popen([sys.executable, "-c", "import sys, time; time.sleep(0.8); open(sys.argv[1], 'w').write('x')", sys.argv[1]])
time.sleep(60)
"""


def units(count):
    return [Unit(f"t{number:02d}/1", f"t{number:02d}", 1) for number in range(1, count + 1)]


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.ledger = Ledger(self.tmp / "ledger.jsonl")
        self.calls = []
        self.lock = threading.Lock()

    def call(self, unit, retry):
        with self.lock:
            self.calls.append((unit.key, retry))

    def go(self, items, attempt=None, **options):
        def default(unit, retry, cancel):
            self.call(unit, retry)
            return {"status": "completed"}
        options.setdefault("jobs", 2)
        return run_units(items, attempt or default, ledger=self.ledger, **options)

    def rows(self, kind):
        return [row for row in self.ledger.records() if row["kind"] == kind]


class LedgerTests(Case):
    def test_records_round_trip_in_order(self):
        self.ledger.append("planned", key="a")
        self.ledger.append("launched", key="a", retry=0)
        self.assertEqual([(row["kind"], row["key"]) for row in self.ledger.records()], [("planned", "a"), ("launched", "a")])
        self.assertEqual(Ledger(self.tmp / "none.jsonl").records(), [])

    def test_an_unknown_kind_is_refused(self):
        with self.assertRaises(ValueError):
            self.ledger.append("weird")

    def test_a_torn_final_line_is_ignored_with_a_note_and_dropped_on_the_next_append(self):
        self.ledger.append("planned", key="a")
        with open(self.ledger.path, "ab") as file:
            file.write(b'{"kind": "launched", "ke')
        records = self.ledger.records()
        self.assertEqual([row["kind"] for row in records], ["planned", "note"])
        self.ledger.append("launched", key="a", retry=0)
        records = self.ledger.records()
        self.assertEqual([row["kind"] for row in records], ["planned", "note", "launched"])
        self.assertIn("torn", records[1]["message"])
        self.assertEqual(self.ledger.path.read_bytes().count(b"\n"), 3)

    def test_a_valid_final_line_without_a_newline_is_kept(self):
        self.ledger.append("planned", key="a")
        with open(self.ledger.path, "ab") as file:
            file.write(json.dumps({"kind": "launched", "key": "a", "retry": 0}).encode())
        self.assertEqual(len(self.ledger.records()), 2)
        self.ledger.append("finished", key="a", retry=0, status="completed")
        self.assertEqual([row["kind"] for row in self.ledger.records()], ["planned", "launched", "finished"])

    def test_any_other_bad_line_raises(self):
        self.ledger.append("planned", key="a")
        with open(self.ledger.path, "ab") as file:
            file.write(b"not json\n")
        with open(self.ledger.path, "ab") as file:
            file.write(json.dumps({"kind": "planned", "key": "b"}).encode() + b"\n")
        with self.assertRaises(LedgerError):
            self.ledger.records()

    def test_a_row_that_is_not_a_record_raises(self):
        self.ledger.path.write_bytes(b'["kind"]\n')
        with self.assertRaises(LedgerError):
            self.ledger.records()

    def test_concurrent_appends_stay_whole_lines(self):
        def write(number):
            for step in range(12):
                self.ledger.append("note", worker=number, step=step)
        threads = [threading.Thread(target=write, args=(number,)) for number in range(4)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(len(self.ledger.records()), 48)


class OwnerLockTests(Case):
    def test_a_held_lock_raises_busy_naming_its_owner(self):
        with OwnerLock(self.tmp) as lock:
            self.assertTrue((self.tmp / "OWNER").exists())
            owner = json.loads((self.tmp / "OWNER").read_text())
            self.assertEqual(set(owner), {"pid", "host", "started"})
            with self.assertRaises(Busy) as raised:
                OwnerLock(self.tmp).acquire()
            self.assertIn(str(owner["pid"]), str(raised.exception))
            self.assertTrue(lock.held)
        self.assertFalse((self.tmp / "OWNER").exists())

    def test_release_frees_the_run_even_after_an_error(self):
        with self.assertRaises(RuntimeError):
            with OwnerLock(self.tmp):
                raise RuntimeError("boom")
        OwnerLock(self.tmp).acquire().release()

    def test_a_refused_acquire_leaves_the_owner_in_place(self):
        with OwnerLock(self.tmp):
            with self.assertRaises(Busy):
                OwnerLock(self.tmp).acquire()
            self.assertTrue((self.tmp / "OWNER").exists())


class RunUnitsTests(Case):
    def test_units_overlap_up_to_jobs(self):
        def attempt(unit, retry, cancel):
            time.sleep(0.5)
            return {"status": "completed"}
        stats = self.go(units(4), attempt, jobs=4)
        self.assertLess(stats.wall_seconds, 1.3)
        self.assertGreaterEqual(stats.achieved_overlap, 3)
        self.assertEqual((stats.peak, stats.launched, stats.planned, stats.by_status), (4, 4, 4, {"completed": 4}))
        self.assertEqual(len(stats.timeline), 4)
        self.assertEqual(stats.stopped, "")

    def test_jobs_bounds_concurrency(self):
        active, peak = [0], [0]
        def attempt(unit, retry, cancel):
            with self.lock:
                active[0] += 1
                peak[0] = max(peak[0], active[0])
            time.sleep(0.05)
            with self.lock:
                active[0] -= 1
            return {"status": "completed"}
        stats = self.go(units(8), attempt, jobs=2)
        self.assertEqual((peak[0], stats.peak), (2, 2))

    def test_the_ledger_orders_each_unit_planned_launched_finished(self):
        self.go(units(1))
        self.assertEqual([row["kind"] for row in self.ledger.records()], ["planned", "launched", "finished"])
        self.assertEqual(self.rows("launched")[0]["cause"], "first")

    def test_finished_units_are_not_run_again_and_nothing_is_duplicated(self):
        self.go(units(3))
        stats = self.go(units(3))
        self.assertEqual(len(self.calls), 3)
        self.assertEqual((stats.launched, stats.by_status), (0, {"completed": 3}))
        self.assertEqual(len(self.rows("planned")), 3)
        self.assertEqual(len(self.rows("launched")), 3)

    def test_launches_without_results_are_closed_as_interrupted_and_relaunched(self):
        items = units(3)
        self.ledger.append("planned", key=items[0].key, task="t01", repeat=1)
        self.ledger.append("launched", key=items[0].key, retry=0, cause="first")
        self.ledger.append("finished", key=items[0].key, retry=0, status="completed")
        self.ledger.append("planned", key=items[1].key, task="t02", repeat=1)
        self.ledger.append("launched", key=items[1].key, retry=0, cause="first")  # the run died here
        stats = self.go(items)
        self.assertEqual(sorted(self.calls), [("t02/1", 1), ("t03/1", 0)])
        closing = [row for row in self.rows("finished") if row["status"] == "interrupted"]
        self.assertEqual([(row["key"], row["retry"]) for row in closing], [("t02/1", 0)])
        self.assertIn("billing uncertain", closing[0]["reason"])
        self.assertEqual((stats.launched, stats.by_status), (2, {"completed": 3}))
        self.assertEqual([row["cause"] for row in self.rows("launched") if row["key"] == "t02/1"], ["first", "resume"])

    def test_an_attempt_killed_mid_run_is_relaunched_by_the_next_call(self):
        def dies(unit, retry, cancel):
            self.call(unit, retry)
            if unit.key == "t02/1":
                raise KeyboardInterrupt
            return {"status": "completed"}
        stats = self.go(units(3), dies, jobs=1)
        self.assertEqual(self.calls, [("t01/1", 0), ("t02/1", 0)])
        self.assertEqual((stats.stopped, stats.by_status), ("interrupt", {"completed": 1, "interrupted": 1, "not-launched": 1}))
        stats = self.go(units(3))
        self.assertEqual(self.calls[2:], [("t02/1", 1), ("t03/1", 0)])
        self.assertEqual(stats.by_status, {"completed": 3})

    def test_ctrl_c_cancels_running_attempts_and_records_them(self):
        def attempt(unit, retry, cancel):
            self.call(unit, retry)
            if unit.key == "t02/1":
                _thread.interrupt_main()
            if cancel.wait(10):
                return {"status": "canceled", "reason": "canceled"}
            return {"status": "completed"}
        began = time.monotonic()
        stats = self.go(units(4), attempt, jobs=2)
        self.assertLess(time.monotonic() - began, 5)
        self.assertEqual(sorted(self.calls), [("t01/1", 0), ("t02/1", 0)])
        self.assertEqual((stats.stopped, stats.by_status), ("interrupt", {"canceled": 2, "not-launched": 2}))
        stats = self.go(units(4))
        self.assertEqual(sorted(self.calls[2:]), [("t01/1", 1), ("t02/1", 1), ("t03/1", 0), ("t04/1", 0)])
        self.assertEqual(stats.by_status, {"completed": 4})

    def test_retry_only_when_transient_and_within_budget(self):
        outcomes = {"t01/1": ["infrastructure-error", "completed"], "t02/1": ["infrastructure-error"] * 5,
                    "t03/1": ["refused"]}
        def attempt(unit, retry, cancel):
            self.call(unit, retry)
            return {"status": outcomes[unit.key][min(retry, len(outcomes[unit.key]) - 1)]}
        stats = self.go(units(3), attempt, jobs=1, transient=lambda result: result["status"] == "infrastructure-error",
                         retry_budget=2)
        self.assertEqual(self.calls, [("t01/1", 0), ("t01/1", 1), ("t02/1", 0), ("t02/1", 1), ("t03/1", 0)])
        self.assertEqual((stats.retries, stats.launched), (2, 5))
        self.assertEqual(stats.by_status, {"completed": 1, "infrastructure-error": 1, "refused": 1})
        self.assertEqual([row["cause"] for row in self.rows("launched")].count("transient"), 2)
        self.assertTrue(self.rows("note"))

    def test_the_retry_budget_covers_the_whole_ledger(self):
        def attempt(unit, retry, cancel):
            self.call(unit, retry)
            return {"status": "infrastructure-error"}
        options = dict(jobs=1, transient=lambda result: True, retry_budget=1)
        self.go(units(1), attempt, **options)
        self.assertEqual(len(self.calls), 2)
        self.go(units(1) + units(2)[1:], attempt, **options)
        self.assertEqual(self.calls[2:], [("t02/1", 0)])

    def test_nothing_is_retried_without_a_transient_rule(self):
        def attempt(unit, retry, cancel):
            self.call(unit, retry)
            return {"status": "infrastructure-error"}
        stats = self.go(units(2), attempt, retry_budget=3)
        self.assertEqual((len(self.calls), stats.retries), (2, 0))

    def test_launch_budget_covers_the_whole_ledger(self):
        stats = self.go(units(6), jobs=2, launch_budget=4)
        self.assertEqual((len(self.calls), stats.launched, stats.stopped), (4, 4, "launch-budget"))
        self.assertEqual(stats.by_status, {"completed": 4, "not-launched": 2})
        stats = self.go(units(6), jobs=2, launch_budget=4)
        self.assertEqual((len(self.calls), stats.launched), (4, 0))
        stats = self.go(units(6), jobs=2, launch_budget=6)
        self.assertEqual((len(self.calls), stats.by_status), (6, {"completed": 6}))

    def test_retries_spend_the_launch_budget(self):
        def failing(unit, retry, cancel):
            self.call(unit, retry)
            return {"status": "infrastructure-error"}
        stats = self.go(units(1), failing, jobs=1, launch_budget=3, transient=lambda result: True, retry_budget=9)
        self.assertEqual((len(self.calls), stats.retries, stats.stopped), (3, 2, "launch-budget"))

    def test_the_deadline_refuses_units_whose_cap_would_pass_it(self):
        stats = self.go(units(3), deadline=1.0, attempt_cap=2.0)
        self.assertEqual(self.calls, [])
        self.assertEqual((stats.stopped, stats.by_status), ("deadline", {"not-launched": 3}))
        self.assertIn("deadline", self.rows("finished")[0]["reason"])

    def test_the_deadline_cancels_what_is_running_and_a_resume_finishes_it(self):
        def slow(unit, retry, cancel):
            self.call(unit, retry)
            if cancel.wait(10):
                return {"status": "canceled", "reason": "canceled"}
            return {"status": "completed"}
        began = time.monotonic()
        stats = self.go(units(3), slow, jobs=1, deadline=0.4, attempt_cap=0.1)
        self.assertLess(time.monotonic() - began, 3)
        self.assertEqual(self.calls, [("t01/1", 0)])
        self.assertEqual((stats.stopped, stats.by_status), ("deadline", {"canceled": 1, "not-launched": 2}))
        stats = self.go(units(3))
        self.assertEqual(self.calls[1:], [("t01/1", 1), ("t02/1", 0), ("t03/1", 0)])
        self.assertEqual(stats.by_status, {"completed": 3})

    def test_a_per_unit_cap_function_is_honored(self):
        stats = self.go(units(2), deadline=1.0, attempt_cap=lambda unit: 5.0 if unit.task == "t01" else 0.1, jobs=1)
        self.assertEqual(self.calls, [("t02/1", 0)])
        self.assertEqual(stats.by_status, {"completed": 1, "not-launched": 1})

    def test_stop_on_ends_admission_and_a_resume_relaunches_the_interrupted_unit(self):
        def attempt(unit, retry, cancel):
            self.call(unit, retry)
            return {"status": "interrupted", "reason": "usage limit"} if retry == 0 else {"status": "completed"}
        stats = self.go(units(4), attempt, jobs=1, stop_on=lambda result: result["status"] == "interrupted")
        self.assertEqual((self.calls, stats.stopped), ([("t01/1", 0)], "stop-on"))
        self.assertEqual(stats.by_status, {"interrupted": 1, "not-launched": 3})
        stats = self.go(units(4), attempt, jobs=1)
        self.assertEqual(self.calls[1:], [("t01/1", 1), ("t02/1", 0), ("t03/1", 0), ("t04/1", 0)])

    def test_an_attempt_that_raises_is_an_infrastructure_error_and_the_run_goes_on(self):
        def attempt(unit, retry, cancel):
            self.call(unit, retry)
            if unit.key == "t01/1":
                raise ValueError("bad grader")
            return {"status": "completed"}
        stats = self.go(units(2), attempt, jobs=1)
        self.assertEqual(stats.by_status, {"infrastructure-error": 1, "completed": 1})
        failed = [row for row in self.rows("finished") if row["status"] == "infrastructure-error"][0]
        self.assertIn("ValueError: bad grader", failed["reason"])

    def test_a_result_without_a_status_is_an_infrastructure_error(self):
        stats = self.go(units(1), lambda unit, retry, cancel: {"credit": 1})
        self.assertEqual(stats.by_status, {"infrastructure-error": 1})

    def test_duplicate_keys_and_bad_jobs_are_refused(self):
        with self.assertRaises(ValueError):
            self.go([Unit("a/1", "a", 1), Unit("a/1", "a", 1)])
        with self.assertRaises(ValueError):
            self.go(units(1), jobs=0)

    def test_graded_records_written_by_an_attempt_survive_alongside(self):
        def attempt(unit, retry, cancel):
            self.ledger.append("graded", key=unit.key, retry=retry, credit=1.0)
            return {"status": "completed"}
        self.go(units(2), attempt)
        self.assertEqual(len(self.rows("graded")), 2)

    def test_a_running_attempt_tree_is_reaped_when_the_deadline_cancels_it(self):
        marker = self.tmp / "done"

        def attempt(unit, retry, cancel):
            outcome = launch.run_capped([sys.executable, "-c", TREE, str(marker)], cwd=self.tmp, stdout=self.tmp / "o",
                                        stderr=self.tmp / "e", timeout=60, cancel=cancel)
            return {"status": outcome.status}
        began = time.monotonic()
        stats = self.go(units(1), attempt, jobs=1, deadline=0.4, attempt_cap=0.2)
        self.assertLess(time.monotonic() - began, 10)
        self.assertEqual(stats.by_status, {"canceled": 1})
        time.sleep(1.0)
        self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
