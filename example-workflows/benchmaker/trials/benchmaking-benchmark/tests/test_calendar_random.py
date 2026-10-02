"""Seeded random calendar workspaces: the skill's helper against the oracle, and labels against the checker.

`free_slots.py` is an independent implementation of the rules it claims to cover (busy, work hours, grid, buffer,
rooms by capacity and availability). On workspaces where only those rules matter its slots and rooms equal the
oracle's; where a room feature or an urgent request over focus blocks matters, its gaps show.
"""

import importlib.util
import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

BB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BB))

from metabench.domains import calendar as C  # noqa: E402
from metabench.domains import calendar_state as S  # noqa: E402
from metabench.domains import scheduling_rules as R  # noqa: E402

SKILL = BB / "meta-tasks" / "calendar-skill" / "subject" / "booking-rules" / "skills" / "booking-rules" / "scripts" / "free_slots.py"
SPEC = importlib.util.spec_from_file_location("calendar_skill_free_slots_random", SKILL)
FREE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FREE)

ZONES = ["-08:00", "-05:00", "+00:00", "+01:00", "+02:00", "+05:30", "+09:00"]
HOURS = [[("09:00", "17:00")], [("08:00", "12:00"), ("13:00", "17:30")], [("10:00", "18:00")], [("07:00", "11:00"), ("11:00", "15:00")]]
DAYS = [("Mon", "Tue", "Wed", "Thu", "Fri"), ("Mon", "Tue", "Wed", "Thu"), ("Mon", "Wed", "Fri", "Sat")]


def stamp(minute, zone):
    return R.iso(minute, R.stamp(f"2026-10-05T00:00{zone}")[1])


def random_workspace(rng):
    """(request, policy, calendars, rooms) over a window of about two and a half days."""
    first = R.stamp("2026-10-05T06:00+00:00")[0]
    last = R.stamp("2026-10-07T20:00+00:00")[0]
    names = ["ana", "bo", "cy", "dee", "eli"][:rng.randint(2, 5)]
    calendars = {}
    for name in names:
        zone = rng.choice(ZONES)
        days = rng.choice(DAYS)
        events = []
        for n in range(rng.randint(2, 9)):
            start = rng.randrange(first, last - 30, 15)
            events.append({"id": f"{name}-{n}", "title": "Busy", "kind": rng.choice(["meeting"] * 4 + ["focus"]),
                           "start": stamp(start, zone), "end": stamp(start + rng.choice([30, 45, 60, 90, 120]), zone)})
        calendars[name] = {"utc_offset": zone, "events": events,
                           "work_hours": [{"days": list(days), "start": a, "end": b} for a, b in rng.choice(HOURS)]}
    rooms = {}
    for n in range(rng.choice([0, 0, 1, 2, 3])):
        events = []
        for k in range(rng.randint(0, 4)):
            start = rng.randrange(first, last - 30, 15)
            events.append({"id": f"r{n}-{k}", "start": stamp(start, "+00:00"), "end": stamp(start + rng.choice([30, 60, 120]), "+00:00")})
        rooms[f"room{n}"] = {"capacity": rng.randint(2, 5), "features": rng.sample(["video", "whiteboard"], rng.randint(0, 2)),
                             "events": events}
    rules = []
    if rng.random() < 0.7:
        rules.append({"type": "buffer_minutes", "minutes": rng.choice([0, 10, 15, 30])})
    if rng.random() < 0.6:
        rules.append({"type": "focus_blocks", "urgent_may_override": rng.random() < 0.7})
    if rng.random() < 0.5:
        rules.append({"type": "room_feature", "min_attendees": rng.randint(1, 4), "feature": rng.choice(["video", "whiteboard"])})
    count = rng.randint(2, len(names))
    request = {"title": "Random", "attendees": names[:count], "optional": names[count:],
               "duration_minutes": rng.choice([30, 45, 60, 90]), "granularity_minutes": rng.choice([15, 30]),
               "window": {"start": stamp(first, "+00:00"), "end": stamp(last, "+00:00")},
               "preference": rng.choice(["earliest", "latest", "any"]), "priority": rng.choice(["normal", "urgent"])}
    return request, {"rules": rules}, calendars, rooms


class RandomWorkspaces(unittest.TestCase):
    POOL = 100

    @classmethod
    def setUpClass(cls):
        """One pool of workspaces, written to disk for the helper, with the instance each implies kept in memory."""
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.pool, rng = [], random.Random(11)
        for n in range(cls.POOL):
            request, policy, calendars, rooms = random_workspace(rng)
            workspace = Path(tmp.name) / f"w{n}"
            C.build_workspace(workspace, request=request, policy=policy, calendars=calendars, rooms=rooms)
            state = {**{S.calendar_path(k): v for k, v in calendars.items()}, **{S.room_path(k): v for k, v in rooms.items()}}
            instance = {"request": request, "policy": policy, "state": state}
            instance["schedule"] = S.schedule_instance(instance)
            cls.pool.append((workspace, instance))

    @staticmethod
    def helper(workspace):
        return [(FREE.minute(s["start"]), s.get("rooms")) for s in FREE.compute(workspace)["slots"]]

    @staticmethod
    def gaps(instance):
        """(a room feature applies, an urgent request may book over focus blocks that exist)."""
        rules = instance["policy"]["rules"]
        feature = any(p.startswith("rooms/") for p in instance["state"]) and any(
            r["type"] == "room_feature" and len(instance["request"]["attendees"]) >= r.get("min_attendees", 1) for r in rules)
        focus = instance["request"]["priority"] == "urgent" and any(
            r["type"] == "focus_blocks" and r.get("urgent_may_override") for r in rules) and any(
            e.get("kind") == "focus" for p, d in instance["state"].items() if p.startswith("calendars/") for e in d["events"])
        return feature, focus

    def test_pool_is_recognized_from_disk_as_the_instances_built_in_memory(self):
        for workspace, instance in self.pool[:10]:
            self.assertEqual(C.recognize(workspace), instance)

    def test_helper_equals_the_oracle_where_it_claims_coverage(self):
        covered = rooms_seen = feasible = 0
        for workspace, instance in self.pool:
            if any(self.gaps(instance)):
                continue
            covered += 1
            oracle = R.slots(R.model(instance["schedule"]))
            feasible += bool(oracle)
            rooms_seen += bool(instance["schedule"]["rooms"])
            self.assertEqual(self.helper(workspace), [(s, rooms or None) for s, rooms in oracle], workspace.name)
        self.assertGreater(covered, 40)
        self.assertGreater(feasible, 20)
        self.assertGreater(rooms_seen, 8)

    def test_helper_lists_rooms_that_lack_a_required_feature(self):
        wider = 0
        for workspace, instance in self.pool:
            feature, focus = self.gaps(instance)
            if not feature or focus:
                continue
            oracle = {s: set(rooms) for s, rooms in R.slots(R.model(instance["schedule"]))}
            listed = {s: set(rooms or []) for s, rooms in self.helper(workspace)}
            for start, rooms in oracle.items():
                self.assertLessEqual(rooms, listed[start])
            wider += any(listed[s] > rooms for s, rooms in oracle.items()) or len(listed) > len(oracle)
        self.assertGreaterEqual(wider, 2)

    def test_helper_cannot_book_over_focus_blocks_for_urgent_requests(self):
        later = 0
        for workspace, instance in self.pool:
            feature, focus = self.gaps(instance)
            if not focus or feature:
                continue
            oracle = {s for s, _ in R.slots(R.model(instance["schedule"]))}
            listed = {s for s, _ in self.helper(workspace)}
            self.assertLessEqual(listed, oracle)
            later += listed < oracle
        self.assertGreaterEqual(later, 2)

    def test_labels_agree_with_the_checker_on_random_workspaces(self):
        labels = set()
        for workspace, instance in self.pool[:15]:
            for item in C.labeled(instance):
                verdict = C.check(instance, item["files"])
                labels.add(item["label"])
                if item["label"] == "valid":
                    self.assertIn(verdict["label"], ("valid", "correct-infeasible"), (workspace.name, item["kind"]))
                elif item["label"] == "suboptimal":
                    self.assertEqual(verdict["label"], "suboptimal", (workspace.name, item["kind"]))
                else:
                    self.assertIn(verdict["label"], R.REJECTED + ("invalid",), (workspace.name, item["kind"]))
        self.assertEqual(labels, {"valid", "suboptimal", "invalid"})

    def test_the_oracle_is_valid_and_books_the_preferred_end_of_the_valid_starts(self):
        optimal = 0
        for workspace, instance in self.pool[:40]:
            outputs = C.solve(instance)
            for files in outputs[:3]:
                self.assertIn(C.check(instance, files)["label"], ("valid", "correct-infeasible"), workspace.name)
            slots = R.slots(R.model(instance["schedule"]))
            if not slots or instance["request"]["preference"] == "any":
                continue
            booked = R.stamp(json.loads(outputs[0]["result.json"])["booked"]["start"])[0]
            self.assertEqual(booked, slots[0][0] if instance["request"]["preference"] == "earliest" else slots[-1][0])
            optimal += 1
        self.assertGreater(optimal, 8)


if __name__ == "__main__":
    unittest.main()
