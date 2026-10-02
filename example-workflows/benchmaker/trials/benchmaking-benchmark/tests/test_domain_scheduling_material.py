"""schedule-nosolver public files and Natural Plan material: conversion, fetch layout, and the files builders read."""

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

BB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BB))

from metabench.domains import scheduling as S  # noqa: E402
from metabench.domains import scheduling_naturalplan as NP  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "scheduling"
MT = BB / "meta-tasks" / "schedule-nosolver"
OUT = "output.json"


def records():
    return json.loads((FIXTURES / "natural_plan.json").read_text(encoding="utf-8"))["records"]


def spans(day, *pairs):
    return [{"start": f"2026-10-0{day}T{a}+00:00", "end": f"2026-10-0{day}T{b}+00:00"} for a, b in pairs]


def person(name, busy):
    return {"id": name, "utc_offset": "+00:00", "required": True, "busy": busy,
            "work_hours": [{"days": ["Mon"], "start": "09:00", "end": "17:00"}]}


class NaturalPlanConversion(unittest.TestCase):
    def test_single_day_record_converts_exactly(self):
        self.assertEqual(NP.convert_natural_plan(records()["calendar_scheduling_example_901"]), {
            "duration_minutes": 30, "granularity_minutes": 30,
            "window": {"start": "2026-10-05T09:00+00:00", "end": "2026-10-05T17:00+00:00"},
            "participants": [
                person("Mason", spans(5, ("09:30", "10:00"), ("11:00", "11:30"), ("14:30", "15:00"), ("16:30", "17:00"))),
                person("Bruce", []),
                person("Christopher", spans(5, ("09:30", "10:30"), ("11:30", "12:30"), ("15:00", "17:00")))],
            "rooms": [],
            "constraints": [{"type": "not_before", "participant": "Mason", "time": "12:30", "day": "2026-10-05"}],
            "preference": "any"})

    def test_multi_day_record_with_continued_sentences_and_a_typo(self):
        inst = NP.convert_natural_plan(records()["calendar_scheduling_example_902"])
        self.assertEqual(inst["duration_minutes"], 60)
        self.assertEqual(inst["window"], {"start": "2026-10-05T09:00+00:00", "end": "2026-10-07T17:00+00:00"})
        self.assertEqual([p["id"] for p in inst["participants"]], ["Ruth", "Leon", "Mia"])
        self.assertEqual(inst["participants"][1]["busy"], [])
        self.assertEqual(inst["participants"][0]["busy"], spans(5, ("09:00", "11:00"), ("12:00", "13:00"))
                         + spans(6, ("09:00", "10:00"), ("15:00", "17:00")) + spans(7, ("09:00", "09:30")))
        self.assertEqual(inst["participants"][2]["busy"], spans(5, ("11:00", "17:00")) + spans(6, ("09:00", "12:00")) + spans(7, ("09:00", "12:30")))
        self.assertEqual(inst["participants"][0]["work_hours"], [{"days": ["Mon", "Tue", "Wed"], "start": "09:00", "end": "17:00"}])
        self.assertEqual(inst["constraints"], [
            {"type": "avoid_day", "participant": "Ruth", "day": "2026-10-05"},
            {"type": "not_after", "participant": "Ruth", "time": "14:00", "day": "2026-10-06"},
            {"type": "not_before", "participant": "Mia", "time": "15:00", "day": "2026-10-07"}])
        self.assertEqual(inst["preference"], "earliest")

    def test_earliest_sentence_naming_the_requester(self):
        inst = NP.convert_natural_plan(records()["calendar_scheduling_example_903"])
        self.assertEqual((inst["preference"], inst["constraints"]), ("earliest", []))

    def test_golden_plans_are_valid_and_earliest_where_requested(self):
        for record_id, record in records().items():
            inst = NP.convert_natural_plan(record)
            answer = NP.natural_plan_answer(record)
            self.assertEqual(S.check(inst, answer)["label"], "valid", record_id)
            self.assertEqual(json.loads(S.solve(inst)[0][OUT]), json.loads(answer[OUT]), record_id)

    def test_five_shot_prompt_uses_its_last_task(self):
        record = dict(records()["calendar_scheduling_example_901"])
        expected = NP.convert_natural_plan(record)
        del record["prompt_0shot"]
        self.assertEqual(NP.convert_natural_plan(record), expected)

    def test_converted_instances_are_recognized(self):
        for record_id, record in records().items():
            with tempfile.TemporaryDirectory() as tmp:
                inst = NP.convert_natural_plan(record)
                (Path(tmp) / "input.json").write_text(json.dumps(inst), encoding="utf-8")
                self.assertEqual(S.recognize(Path(tmp), ""), inst, record_id)

    def test_unreadable_records_are_refused(self):
        record = records()["calendar_scheduling_example_901"]
        for edit in (lambda p: p.replace("TASK:", "JOB:"),
                     lambda p: p.replace("Mason would rather not meet on Monday before 12:30.", "Mason would prefer lunch."),
                     lambda p: p.replace("Bruce is free the entire day.", "Bruce is on holiday."),
                     lambda p: p.replace("Mason has meetings on", "Maisie has meetings on")):
            broken = {**record, "prompt_0shot": edit(record["prompt_0shot"]), "prompt_5shot": ""}
            with self.assertRaises(ValueError):
                NP.convert_natural_plan(broken)
        with self.assertRaises(ValueError):
            NP.natural_plan_answer({"golden_plan": "No time works."})

    def test_load_instances_reads_a_data_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "calendar_scheduling.json"
            path.write_text(json.dumps(records()), encoding="utf-8")
            loaded = S.load_instances(path)
            self.assertEqual(set(loaded), set(records()))
            path.write_text(json.dumps({"bad": {"prompt_0shot": "TASK: nothing"}}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "bad"):
                S.load_instances(path)


class FakeResponse:
    def __init__(self, data):
        self.data = data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.data


class FetchMaterial(unittest.TestCase):
    def test_fetch_splits_public_and_held_out_without_the_network(self):
        spec = json.loads((MT / "material.json").read_text(encoding="utf-8"))
        template = records()["calendar_scheduling_example_901"]
        held = [f"calendar_scheduling_example_{n}" for n in (1000, 1001, 1002)]
        everything = {i: dict(template) for i in [*spec["public_records"], *held]}
        seen = []

        def opener(request, timeout):
            seen.append((request, timeout))
            return FakeResponse(json.dumps(everything).encode("utf-8"))

        with tempfile.TemporaryDirectory() as store:
            summary = NP.fetch_material(store, opener=opener)
            root = Path(store) / "material" / "schedule-nosolver"
            self.assertEqual(seen[0][0].full_url, spec["source"]["data_url"])
            self.assertEqual(summary, {"records": len(everything), "public": len(spec["public_records"]), "held_out": 3, "unreadable": []})
            self.assertEqual((root / "source" / "calendar_scheduling.json").read_bytes(), json.dumps(everything).encode("utf-8"))
            public = json.loads((root / "public" / "calendar_scheduling.json").read_text(encoding="utf-8"))
            self.assertEqual(list(public), spec["public_records"])
            self.assertEqual(set(public["calendar_scheduling_example_" + spec["public_records"][0].rsplit("_", 1)[1]]), set(NP.KEPT_FIELDS))
            self.assertEqual(list(json.loads((root / "held-out" / "calendar_scheduling.json").read_text(encoding="utf-8"))), held)
            self.assertEqual(json.loads((root / "split.json").read_text(encoding="utf-8")), {"public": spec["public_records"], "held_out": held})
            self.assertIn("CC BY 4.0", (root / "public" / "NOTICE.md").read_text(encoding="utf-8"))
            self.assertEqual(len(S.load_instances(root / "public" / "calendar_scheduling.json")), 40)

    def test_fetch_stops_when_a_public_record_is_missing(self):
        with tempfile.TemporaryDirectory() as store:
            with self.assertRaisesRegex(ValueError, "missing"):
                NP.fetch_material(store, opener=lambda request, timeout: FakeResponse(b"{}"))
            self.assertFalse((Path(store) / "material" / "schedule-nosolver" / "public").exists())


class PublicFiles(unittest.TestCase):
    def test_material_json_records_licence_and_a_public_sample(self):
        spec = json.loads((MT / "material.json").read_text(encoding="utf-8"))
        self.assertEqual((spec["licence"]["code"], spec["licence"]["data"]), ("Apache-2.0", "CC-BY-4.0"))
        self.assertRegex(spec["licence"]["checked"], r"^\d{4}-\d{2}-\d{2}$")
        for key in ("statement_url", "code_url", "data_terms_url"):
            self.assertTrue(spec["licence"][key].startswith("https://"), key)
        self.assertEqual(spec["source"]["repository"], "https://github.com/google-deepmind/natural-plan")
        ids = spec["public_records"]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 40)
        self.assertTrue(all(re.fullmatch(r"calendar_scheduling_example_\d{1,3}", i) for i in ids))
        self.assertIn("CC BY 4.0", spec["attribution"])
        self.assertIn("template", spec["realism"])

    def test_request_has_budget_placeholders_and_no_hidden_pool(self):
        text = (MT / "request.md").read_text(encoding="utf-8")
        self.assertEqual(sorted(re.findall(r"\{[A-Z_]+\}", text)), ["{CONCURRENCY}", "{MINUTES}", "{SUBJECT_RUNS}"])
        for word in ("hidden", "held-out", "held out", "pool", "meta-verif", "ORDER", "oracle"):
            self.assertNotIn(word, text, word)
        for needed in ("interface.md", "interface/package.md", "material/", "./benchmark-run/", "conform.py", "run.py grade"):
            self.assertIn(needed, text)

    def test_interface_example_and_vocabulary(self):
        text = (MT / "interface.md").read_text(encoding="utf-8")
        blocks = re.findall(r"```json\n(.*?)```", text.replace("\r\n", "\n"), re.S)
        self.assertEqual(len(blocks), 2)
        example_in, example_out = json.loads(blocks[0]), json.loads(blocks[1])
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "input.json").write_text(blocks[0], encoding="utf-8")
            self.assertEqual(S.recognize(Path(tmp), ""), example_in)
        self.assertEqual(S.check(example_in, {OUT: blocks[1].encode()})["label"], "valid")
        self.assertEqual(example_out["start"], "2026-10-05T11:30+00:00")
        for word in ("not_before", "not_after", "avoid_day", "buffer_minutes", "room_feature", "earliest", "latest", "any",
                     "half-open", "infeasible", "explanation", "input.json", "output.json", "interface/package.md"):
            self.assertIn(word, text, word)

    def test_dev_pool_is_exposed_and_consistent(self):
        pool = json.loads((MT / "dev-pool.json").read_text(encoding="utf-8"))
        self.assertEqual((pool["meta_task"], pool["label"]), ("schedule-nosolver", "exposed"))
        members = pool["members"]
        self.assertEqual({m["behavior"] for m in members.values()}, {"oracle", "floor", "cheater", "defect", "ladder"})
        for name, member in members.items():
            if member["behavior"] == "defect":
                self.assertIn(member["defect"], S.DEFECTS, name)
            if member["behavior"] == "ladder":
                self.assertTrue(0 < member["q"] < 1, name)
        self.assertEqual({m["q"] for m in members.values() if m["behavior"] == "ladder"}, {0.2, 0.6})
        for pair in [*pool["known_pairs"], *pool["contrasts"]]:
            self.assertIn(pair["higher"], members)
            self.assertIn(pair["lower"], members)
            self.assertNotEqual(pair["higher"], pair["lower"])
        self.assertTrue(all(c["must_resolve"] for c in pool["contrasts"]))


if __name__ == "__main__":
    unittest.main()
