"""Resumable acquisition keeps judgment explicit and completed reads immutable."""

import copy
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import acquire
from acquire_fixture import fixture_plan, fixture_runtime, choose
from acquire_plan import PlanError
from acquire_checkpoint import CheckpointError


class AcquisitionPlanTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "evidence"
        self.plan = fixture_plan()
        self.runtime, self.opened = fixture_runtime()

    def run_plan(self, selection=None, **kwargs):
        return acquire.execute(self.plan, self.output, selection=selection,
                               **self.runtime, **kwargs)

    def test_discovery_semantic_selection_depth_and_zero_read_resume(self):
        first = self.run_plan()
        self.assertEqual(first["phase"], "selection_required")
        self.assertEqual(len(self.opened), 2)
        rows = json.loads((self.output / "candidates.json").read_text())["candidates"]
        daily = next(row for row in rows if row["title"] == "Daily discussion")
        self.assertEqual(daily["community"], "BitcoinMarkets")
        self.assertTrue(daily["options"])
        selection = choose(self.output)
        second = self.run_plan(selection)
        self.assertEqual(second["phase"], "complete")
        self.assertEqual(len(self.opened), 4)
        packet = (self.output / "packet.json").read_bytes()
        artifact = json.loads(packet)
        self.assertEqual(len(artifact["edges"]), 2)
        self.assertIn("third_party_archive", artifact["records"][0]["loss"])
        self.assertTrue(any(row["body"] == "A conditional case, not a prediction."
                            for row in artifact["records"]))
        self.assertEqual(self.run_plan(selection)["requests_this_invocation"], 0)
        self.assertEqual(packet, (self.output / "packet.json").read_bytes())
        self.assertEqual(len(self.opened), 4)

    def test_changed_identity_corruption_and_selection_refuse_before_reads(self):
        self.run_plan()
        changed = copy.deepcopy(self.plan)
        changed["question"] = "A different question"
        with self.assertRaises(CheckpointError):
            acquire.execute(changed, self.output, **self.runtime)
        selection = choose(self.output)
        selection["choices"][0]["record_id"] = "invented"
        with self.assertRaises(PlanError):
            self.run_plan(selection)
        self.assertEqual(len(self.opened), 2)
        receipt = next((self.output / "steps").glob("*.json"))
        receipt.write_text("{}")
        with self.assertRaises(CheckpointError):
            self.run_plan()
        self.assertEqual(len(self.opened), 2)

    def test_interruption_reuses_finished_step_and_never_repeats_uncertain_read(self):
        def stop(step_id):
            if step_id == "archive":
                raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.run_plan(after_checkpoint=stop, lanes=1)
        self.assertEqual(len(self.opened), 1)
        self.run_plan(lanes=1)
        self.assertEqual(len(self.opened), 2)
        self.assertEqual(self.run_plan()["requests_this_invocation"], 0)

    def test_dates_policy_and_caps_reject_before_any_read(self):
        for change in (lambda p: p.update(as_of="2026-08-01T00:00:00Z"),
                       lambda p: p["discovery"][0].update(window_start="2025-01-01T00:00:00Z"),
                       lambda p: p["limits"].update(max_records=1),
                       lambda p: p["allowed_adapters"].remove("reddit_archive")):
            with self.subTest(change=change):
                plan = copy.deepcopy(self.plan)
                change(plan)
                with self.assertRaises(PlanError):
                    acquire.execute(plan, self.output, **self.runtime)
        self.assertEqual(self.opened, [])

    def test_refusal_is_checkpointed_and_never_retried_or_hidden(self):
        self.runtime, self.opened = fixture_runtime(refuse=True)
        self.run_plan()
        selection = choose(self.output)
        result = self.run_plan(selection)
        self.assertEqual(result["phase"], "complete")
        artifact = json.loads((self.output / "packet.json").read_text())
        self.assertIn("http_status", artifact["loss"])
        self.assertNotEqual(artifact["outcome"], "empty")
        count = len(self.opened)
        self.run_plan(selection)
        self.assertEqual(len(self.opened), count)

    def test_uncertain_inflight_step_is_not_retried_and_completed_other_step_survives(self):
        opener = self.runtime["opener"]
        def interrupted(request):
            if request.route_id == "arctic_shift_posts_search":
                self.opened.append(request)
                raise KeyboardInterrupt()
            return opener(request)
        self.runtime["opener"] = interrupted
        with self.assertRaises(KeyboardInterrupt):
            self.run_plan(lanes=1)
        self.runtime["opener"] = opener
        resumed = self.run_plan(lanes=1)
        self.assertEqual(resumed["phase"], "incomplete")
        self.assertEqual(resumed["gaps"][0]["code"], "interrupted_step_uncertain")
        self.assertEqual(len(self.opened), 2)
        self.assertEqual(self.run_plan()["requests_this_invocation"], 0)

    def test_request_cap_holds_across_process_resume(self):
        self.plan["limits"]["max_requests"] = 2
        self.run_plan()
        selected = choose(self.output)
        result = self.run_plan(selected)
        artifact = json.loads((self.output / "packet.json").read_text())
        self.assertEqual(result["requests_total"], 2)
        self.assertEqual(len(self.opened), 2)
        self.assertIn("unreachable", artifact["loss"])
        self.assertTrue(any("request cap" in warning for step in artifact["steps"] for warning in step["warnings"]))

    def test_package_change_and_changed_bound_selection_refuse_without_reads(self):
        self.run_plan()
        with patch.object(acquire, "package_identity", return_value="changed-package"):
            with self.assertRaises(CheckpointError):
                self.run_plan()
        selected = choose(self.output)
        self.run_plan(selected)
        selected["choices"][0]["reason"] = "Changed semantic authorization"
        with self.assertRaises(CheckpointError):
            self.run_plan(selected)
        self.assertEqual(len(self.opened), 4)

    def test_independent_source_reads_overlap_but_output_keeps_plan_order(self):
        barrier = threading.Barrier(2, timeout=3)
        opener = self.runtime["opener"]
        def concurrent(request):
            barrier.wait()
            return opener(request)
        self.runtime["opener"] = concurrent
        self.run_plan()
        packet = json.loads((self.output / "packet.json").read_text())
        self.assertEqual([step["step_id"] for step in packet["steps"]], ["archive", "index"])

    def test_unsupported_cross_adapter_and_duplicate_target_selection_are_refused(self):
        self.run_plan()
        selected = choose(self.output)
        selected["choices"][0]["depth_id"] = "pages"
        with self.assertRaises(PlanError):
            self.run_plan(selected)
        selected = choose(self.output)
        selected["choices"].append(dict(selected["choices"][0]))
        with self.assertRaises(PlanError):
            self.run_plan(selected)
        self.assertEqual(len(self.opened), 2)

    def test_empty_semantic_selection_is_explicit_and_makes_no_depth_reads(self):
        result = self.run_plan()
        result = self.run_plan({"candidate_id": result["candidate_id"], "choices": [],
                                "omission_reason": "No candidate justifies an authorized deeper read."})
        self.assertEqual(result["phase"], "complete")
        self.assertEqual(len(self.opened), 2)
        self.assertTrue(result["artifact_advisories"])

    def test_contradictory_dates_and_unknown_dates_remain_visible_without_keyword_filter(self):
        opener = self.runtime["opener"]
        def dated(request):
            status, body, content_type = opener(request)
            if request.route_id == "arctic_shift_posts_search":
                payload = json.loads(body)
                duplicate = dict(payload["data"][0])
                duplicate["created_utc"] += 3600
                unknown = dict(duplicate, id="unknown", created_utc=None)
                payload["data"].extend([duplicate, unknown])
                body = json.dumps(payload)
            return status, body, content_type
        self.runtime["opener"] = dated
        self.run_plan()
        batch = json.loads((self.output / "candidates.json").read_text())
        rows = batch["candidates"]
        daily = [row for row in rows if row["native_item_id"] == "t3_abc"]
        self.assertEqual(len(daily), 2)
        self.assertNotEqual(daily[0]["published_at"], daily[1]["published_at"])
        self.assertEqual(daily[1]["duplicate_of"], daily[0]["record_id"])
        self.assertTrue(any(row["date_eligibility"] == "unknown" for row in rows))
        self.assertTrue(any("outside" in warning for step in batch["steps"] for warning in step["warnings"]))

    def test_malformed_plan_and_embedded_date_bounds_refuse_before_reads(self):
        for key, value in (("allowed_adapters", [["reddit_archive"]]), ("version", True),
                           ("as_of", "2026-9-10T23:59:59Z"), ("depth", [{"bad": True}])):
            plan = copy.deepcopy(self.plan)
            plan[key] = value
            with self.subTest(key=key), self.assertRaises(PlanError):
                acquire.execute(plan, self.output, **self.runtime)
        self.plan["discovery"][1]["query"] = "bing:topic since:2025-01-01"
        with self.assertRaises(PlanError):
            self.run_plan()
        self.assertFalse(self.opened)

    def test_observation_ceiling_expiring_during_a_read_is_an_explicit_gap(self):
        self.runtime["now"] = lambda: "2026-09-11T00:00:00Z" if self.opened else "2026-09-10T12:00:00Z"
        result = self.run_plan(lanes=1)
        self.assertEqual(result["phase"], "incomplete")
        self.assertTrue(any(row["code"] == "observation_after_as_of" for row in result["gaps"]))
        self.assertEqual(len(self.opened), 1)

    def test_missing_checkpoint_does_not_silently_repeat_existing_evidence(self):
        self.run_plan()
        (self.output / "checkpoint.json").unlink()
        with self.assertRaises(CheckpointError):
            self.run_plan()
        self.assertEqual(len(self.opened), 2)

    def test_elapsed_budget_prevents_another_read_after_a_slow_answer(self):
        from tests.helpers import FakeClock
        clock = FakeClock()
        opener = self.runtime["opener"]
        def slow(request):
            answer = opener(request)
            clock.advance(31)
            return answer
        self.runtime.update(opener=slow, clock=clock.monotonic, sleep=clock.sleep)
        self.run_plan(lanes=1)
        self.assertEqual(len(self.opened), 1)
        packet = json.loads((self.output / "packet.json").read_text())
        self.assertTrue(any("elapsed-time budget" in warning for step in packet["steps"] for warning in step["warnings"]))


if __name__ == "__main__":
    unittest.main()
