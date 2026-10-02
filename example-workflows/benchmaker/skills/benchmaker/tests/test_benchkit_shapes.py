"""Shape validators, and the examples in INTERFACE.md that must keep passing them."""
from __future__ import annotations

import copy
import json
import re
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from benchkit import shapes  # noqa: E402

INTERFACE = SCRIPTS / "benchkit" / "INTERFACE.md"


def examples():
    """The fenced examples of INTERFACE.md by their info string, e.g. 'json suite.json'."""
    found = {}
    for info, body in re.findall(r"```(\w+ [\w.]+)\n(.*?)```", INTERFACE.read_text(encoding="utf-8"), re.S):
        language, name = info.split()
        found[name] = tomllib.loads(body) if language == "toml" else json.loads(body)
    return found


class InterfaceTests(unittest.TestCase):
    def test_every_documented_example_validates(self):
        docs = examples()
        self.assertEqual(sorted(docs), ["attempt", "card", "suite.json", "summary", "task.toml", "verifier"])
        self.assertEqual(shapes.suite_problems(docs["suite.json"]), [])
        self.assertEqual(shapes.task_problems(docs["task.toml"]), [])
        self.assertEqual(shapes.verifier_problems(docs["verifier"]), [])
        self.assertEqual(shapes.attempt_problems(docs["attempt"]), [])
        self.assertEqual(shapes.summary_problems(docs["summary"]), [])
        self.assertEqual(shapes.claims_problems(docs["card"]), [])

    def test_the_card_example_covers_every_claim_type_and_gap_category(self):
        card = examples()["card"]
        self.assertEqual({claim["type"] for claim in card["claims"]},
                         {"interval", "order", "rate", "noise", "target", "cost", "verdict", "gap"})
        text = INTERFACE.read_text(encoding="utf-8")
        for category in shapes.GAP_CATEGORIES:
            self.assertIn(category, text)

    def test_the_document_states_what_a_builder_needs_and_stays_short(self):
        text = INTERFACE.read_text(encoding="utf-8")
        for needed in ("scripts/benchkit/", "<package>/benchkit/", "scripts/run.py", "<package>/run.py", "stay each package's own",
                       "Harbor", "from benchkit.stopping import decide", "provision", "observe", "--stop-band"):
            self.assertIn(needed, text)
        self.assertLessEqual(len(text.splitlines()), 170)


class SuiteTests(unittest.TestCase):
    base = {"name": "s", "repeats": 1, "concurrency": 1}

    def problems(self, **changes):
        return shapes.suite_problems({**self.base, **changes})

    def test_the_minimum_is_valid_and_extras_are_allowed(self):
        self.assertEqual(self.problems(profiles=["x"]), [])
        self.assertEqual(self.problems(deadline_seconds=None, launch_budget=None, attempt_seconds_estimate=None), [])

    def test_bad_values_are_named(self):
        cases = {"name": ["", 3], "repeats": [0, 1.5, True, "2"], "concurrency": [0, -1], "deadline_seconds": [0, "soon"],
                 "grace_seconds": [-1], "transient_retry_budget": [-1, 1.5], "launch_budget": [0], "provision": ["uv sync", [[]], [["a", 1]]],
                 "observe": [{"python": "--version"}], "metrics": [[], {"primary": "speed"}]}
        for key, values in cases.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    found = self.problems(**{key: value})
                    self.assertEqual(len(found), 1, found)
                    self.assertIn(key, found[0])

    def test_required_keys_and_non_objects(self):
        self.assertEqual(len(shapes.suite_problems({})), 3)
        self.assertEqual(shapes.suite_problems([]), ["suite.json: must be a JSON object"])


class TaskTests(unittest.TestCase):
    good = {"metadata": {"family": "f", "source_group": "g", "split": "held-out"}, "agent": {"timeout_sec": 30}}

    def test_the_minimum_is_valid(self):
        self.assertEqual(shapes.task_problems(self.good), [])
        full = copy.deepcopy(self.good)
        full["metadata"].update(anchor=True, smoke=False, quick=True, weight=0.25, difficulty=0.4, expert_minutes=3, time_estimate="measured")
        full["verifier"] = {"timeout_sec": 5}
        self.assertEqual(shapes.task_problems(full), [])

    def test_bad_values_are_named(self):
        def with_meta(**changes):
            doc = copy.deepcopy(self.good)
            doc["metadata"].update(changes)
            return shapes.task_problems(doc)

        for key, value in (("split", "test"), ("family", ""), ("anchor", "yes"), ("smoke", 1), ("weight", -0.1), ("difficulty", True),
                           ("expert_minutes", 0), ("time_estimate", "guess")):
            with self.subTest(key=key):
                found = with_meta(**{key: value})
                self.assertEqual(len(found), 1, found)
                self.assertIn(key, found[0])
        self.assertIn("missing [metadata]", shapes.task_problems({"agent": {"timeout_sec": 1}})[0])
        self.assertIn("missing [agent]", shapes.task_problems({"metadata": self.good["metadata"]})[0])
        self.assertIn("'timeout_sec' must be a positive number", shapes.task_problems({**self.good, "agent": {"timeout_sec": 0}})[0])
        self.assertIn("'timeout_sec'", shapes.task_problems({**self.good, "verifier": {"timeout_sec": "x"}})[0])

    def test_weights_are_all_or_none_and_sum_to_one(self):
        self.assertEqual(shapes.weights_problems({"a": None, "b": None}), [])
        self.assertEqual(shapes.weights_problems({"a": 0.5, "b": 0.5}), [])
        self.assertIn("only 1 of 2", shapes.weights_problems({"a": 0.5, "b": None})[0])
        self.assertIn("sum to 0.9", shapes.weights_problems({"a": 0.5, "b": 0.4})[0])


class RecordTests(unittest.TestCase):
    def test_verifier_results(self):
        scored = {"grading_status": "scored", "full_success": True, "credit": 1.0, "dimensions": {}, "critical_failures": []}
        self.assertEqual(shapes.verifier_problems(scored), [])
        self.assertEqual(shapes.verifier_problems({"grading_status": "indeterminate", "reason": "judge unavailable"}), [])
        cases = [("not an object", []), ("status", {"grading_status": "maybe"}), ("reason", {"grading_status": "unscored"}),
                 ("full_success", {"grading_status": "scored", "full_success": "yes", "credit": 1.0}),
                 ("critical failure", {**scored, "critical_failures": ["cheat"]}),
                 ("outside", {**scored, "credit": 1.5}),
                 ("sum to", {**scored, "credit": None, "dimensions": {"a": {"credit": 1.0, "weight": 0.6}}})]
        for name, doc in cases:
            with self.subTest(name):
                found = shapes.verifier_problems(doc)
                self.assertEqual(len(found), 1, found)

    def test_attempt_rows(self):
        row = {"task": "t", "repeat": 1, "retry": 0, "status": "completed", "reason": "", "grading_status": "scored", "full_success": True}
        self.assertEqual(shapes.attempt_problems(row), [])
        cases = {"status": "done", "repeat": 0, "retry": -1, "seconds": "7", "left_running": 1, "credit": 2, "cost_usd": -1,
                 "grading_status": "graded", "task": ""}
        for key, value in cases.items():
            with self.subTest(key=key):
                found = shapes.attempt_problems({**row, key: value})
                self.assertTrue(found and key in found[0], found)
        self.assertIn("cannot be scored", shapes.attempt_problems({**row, "status": "canceled"})[0])
        self.assertIn("needs 'full_success'", shapes.attempt_problems({**row, "full_success": None})[0])
        self.assertEqual(shapes.attempt_problems({**row, "status": "canceled", "grading_status": "unscored", "full_success": None}), [])

    def test_summary_invariants(self):
        good = examples()["summary"]
        self.assertEqual(shapes.summary_problems(good), [])
        for name, edit in {
            "scored + unscored": lambda s: s["counts"].update(unscored=1),
            "passed + failed": lambda s: s["counts"].update(passed=2),
            "by_status must sum": lambda s: s["counts"]["by_status"].update(completed=1),
            "tasks x repeats": lambda s: s["run"].update(repeats=3),
            "every suite task": lambda s: s["suite"].update(tasks=2),
            "full_success_rate": lambda s: s["overall"].update(full_success_rate=1.5),
            "missing 'cost'": lambda s: s.pop("cost"),
            "missing 'exclusions'": lambda s: s.pop("exclusions"),
            "missing 'peak_concurrency'": lambda s: s["run"].pop("peak_concurrency"),
            "exactly": lambda s: s["counts"]["by_status"].pop("canceled"),
        }.items():
            with self.subTest(name):
                broken = copy.deepcopy(good)
                edit(broken)
                self.assertTrue(any(name in found for found in shapes.summary_problems(broken)), shapes.summary_problems(broken))
        self.assertEqual(shapes.summary_problems([]), ["summary.json: must be a JSON object"])


class ClaimTests(unittest.TestCase):
    conditions = {"subject": {"agent": "adapters/a"}, "other": {"agent": "@reference"}}

    def card(self, *claims, conditions=None):
        return {"conditions": self.conditions if conditions is None else conditions, "claims": list(claims)}

    def problems(self, claim):
        return shapes.claims_problems(self.card({"id": "c1", **claim}))

    def test_malformed_claims_are_rejected_by_type(self):
        cases = [
            ({"type": "interval", "metric": "m", "system": "subject", "low": 0.5, "high": 0.2, "level": 0.9}, "'low' exceeds 'high'"),
            ({"type": "interval", "metric": "m", "system": "subject", "low": 0.1, "high": 0.2, "level": 1.0}, "'level' must be a number in (0, 1)"),
            ({"type": "interval", "metric": "m", "system": "ghost", "low": 0.1, "high": 0.2, "level": 0.9}, "'system' must be a system named in conditions"),
            ({"type": "interval", "system": "subject", "low": 0.1, "high": 0.2, "level": 0.9}, "missing 'metric'"),
            ({"type": "order", "higher": "subject", "lower": "other", "metric": "m", "resolved": "yes"}, "'resolved' must be true or false"),
            ({"type": "order", "higher": "subject", "metric": "m", "resolved": True}, "missing 'lower'"),
            ({"type": "rate", "metric": "m"}, "needs 'min' or 'max'"),
            ({"type": "rate", "metric": "m", "min": 0.9, "max": 0.1}, "'min' exceeds 'max'"),
            ({"type": "rate", "metric": "m", "max": "0"}, "'max' must be a number"),
            ({"type": "noise", "metric": "m", "system": "subject", "sd_max": -1}, "'sd_max'"),
            ({"type": "target", "metric": "m", "system": "subject", "low": 0.2}, "missing 'high'"),
            ({"type": "cost", "system": "subject", "profile": "full"}, "needs 'usd_max' or 'wall_seconds_max'"),
            ({"type": "cost", "system": "subject", "profile": "huge", "usd_max": 1}, "'profile' must be one of smoke, quick, full"),
            ({"type": "verdict", "supports_claim": False}, "missing 'reason'"),
            ({"type": "gap", "category": "flaky", "text": "x"}, "'category' must be one of hackable-task"),
            ({"type": "gap", "category": "floor", "text": " "}, "'text' must be a non-empty string"),
            ({"type": "mystery"}, "'type' must be interval"),
            ({}, "'type' must be interval"),
        ]
        for claim, expect in cases:
            with self.subTest(claim=claim):
                found = self.problems(claim)
                self.assertTrue(any(expect in item for item in found), found)

    def test_valid_claims_of_every_type_pass(self):
        claims = [{"type": "interval", "metric": "m", "system": "subject", "low": 0.1, "high": 0.2, "level": 0.9},
                  {"type": "order", "higher": "subject", "lower": "other", "metric": "m", "resolved": False},
                  {"type": "rate", "metric": "m", "min": 0.0, "max": 1.0}, {"type": "noise", "metric": "m", "system": "other", "sd_max": 0},
                  {"type": "target", "metric": "m", "system": "subject", "low": 0.0, "high": 1.0},
                  {"type": "cost", "system": "subject", "profile": "quick", "wall_seconds_max": 60},
                  {"type": "verdict", "supports_claim": True, "reason": "why"}, {"type": "gap", "category": "exposure", "text": "t"}]
        self.assertEqual(shapes.claims_problems(self.card(*({"id": f"c{n}", **claim} for n, claim in enumerate(claims)))), [])

    def test_ids_and_conditions_and_structure(self):
        gap = {"type": "gap", "category": "floor", "text": "t"}
        self.assertIn("duplicate id 'c1'", shapes.claims_problems(self.card({"id": "c1", **gap}, {"id": "c1", **gap}))[0])
        self.assertIn("missing 'id'", shapes.claims_problems(self.card(gap))[0])
        self.assertIn("needs an 'agent' string", shapes.claims_problems(self.card(conditions={"x": {"model": "m"}}))[0])
        self.assertIn("'conditions' must be an object", shapes.claims_problems({"claims": []})[0])
        self.assertEqual(shapes.claims_problems({"conditions": {}}), ["card.json: 'claims' must be a list"])
        self.assertEqual(shapes.claims_problems([]), ["card.json: must be a JSON object"])
        self.assertIn("claim 1: must be an object", shapes.claims_problems(self.card("nope"))[0])


class RunDirectoryTests(unittest.TestCase):
    def test_a_directory_without_records_reports_each_missing_file(self):
        with tempfile.TemporaryDirectory() as folder:
            found = shapes.run_problems(Path(folder))
        self.assertTrue(any(item.startswith("run.json") for item in found))
        self.assertTrue(any(item.startswith("attempts.jsonl") for item in found))

    def test_bad_lines_and_rows_are_reported(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            (out / "run.json").write_text(json.dumps({"profile": "full"}), encoding="utf-8")
            (out / "attempts.jsonl").write_text('{"task": "t"}\nnot json\n', encoding="utf-8")
            (out / "ledger.jsonl").write_text('{"kind": "launched"}\nnope\n{"kind": "launched"}\n', encoding="utf-8")
            (out / "grades-1.jsonl").write_text('{"grading_status": "bad"}\n', encoding="utf-8")
            (out / "summary.json").write_text("{}", encoding="utf-8")
            found = "\n".join(shapes.run_problems(out))
        for expect in ("run.json: missing 'agent'", "attempts.jsonl row 1: missing 'repeat'", "attempts.jsonl: line 2 is not JSON",
                       "ledger.jsonl: line 2 is not a ledger record", "grades-1.jsonl row 1", "summary.json: missing 'suite'"):
            self.assertIn(expect, found)


if __name__ == "__main__":
    unittest.main()
