"""The calendar reference package has no task that pays the content-blind floor (the earliest free slot, policy ignored)."""
import importlib.util
import json
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


if __name__ == "__main__":
    unittest.main()
