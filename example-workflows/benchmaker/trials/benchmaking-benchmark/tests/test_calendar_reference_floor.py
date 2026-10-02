"""The calendar reference package has no task that pays the content-blind floor (the earliest free slot, policy ignored),
and its admission labels hold where attendees have empty calendars."""
import importlib.util
import json
import random
import tempfile
import unittest
from pathlib import Path

BB = Path(__file__).resolve().parents[1]
SOURCES = BB / "reference-packages" / "calendar-skill" / "sources"


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


defects = load(SOURCES / "defects.py", "calendar_reference_defects")
SOLVE = load(SOURCES / "task" / "solve.py", "calendar_reference_solve")
INSTANCES = sorted((BB / "reference-packages" / "calendar-skill" / "offline-instances").glob("*.json"))


class BlindFloorTests(unittest.TestCase):
    def test_no_offline_task_pays_the_policy_blind_floor(self):
        self.assertGreaterEqual(len(INSTANCES), 15)
        paying = [path.stem for path in INSTANCES
                  if defects.pays_blind(SOLVE, json.loads(path.read_text(encoding="utf-8"))["workspace"])]
        self.assertEqual(paying, [])

    def test_the_filter_sees_a_task_where_the_policy_does_not_matter(self):
        docs = json.loads(INSTANCES[0].read_text(encoding="utf-8"))["workspace"]
        docs["policy"]["rules"] = []
        docs["request"]["preference"] = "earliest"
        self.assertTrue(defects.pays_blind(SOLVE, docs))


class EmptyCalendarTests(unittest.TestCase):
    """Real material has attendees with empty calendars; held-out task np-438 broke admission on both counts."""

    def setUp(self):
        self.generate = load(BB / "reference-packages" / "calendar-skill" / "generate.py", "calendar_reference_generate")
        self.doc = json.loads(INSTANCES[0].read_text(encoding="utf-8"))
        self.ws = self.doc["workspace"]

    def empty(self, paths):
        for path in paths:
            defects.doc_at(self.ws, path)["events"] = []

    def test_every_label_agrees_with_the_verifier_when_attendees_have_empty_calendars(self):
        self.empty(defects.attendee_paths(self.ws)[:-1])
        self.assertEqual(defects.holders(self.ws), defects.attendee_paths(self.ws)[-1:])
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            self.generate.admit(out, self.doc, self.generate.write_task(out, self.doc, "development"))

    def test_a_clobber_only_counts_where_it_destroys_an_entry(self):
        self.empty(defects.attendee_paths(self.ws)[:-1])
        for seed in range(8):
            outcome = defects.clobber(SOLVE, self.ws, random.Random(seed))
            self.assertEqual(defects.defect_label(SOLVE, self.ws, "clobber", outcome), "invalid")
        self.empty(defects.attendee_paths(self.ws))
        self.assertEqual(defects.defect_label(SOLVE, self.ws, "clobber", defects.clobber(SOLVE, self.ws, random.Random(0))), "valid")
        kinds = {kind for kind, _, _ in defects.labeled(SOLVE, self.ws)}
        self.assertNotIn("id-reuse", kinds)
        self.assertIn("clobber:changed-work-hours", kinds)


if __name__ == "__main__":
    unittest.main()
