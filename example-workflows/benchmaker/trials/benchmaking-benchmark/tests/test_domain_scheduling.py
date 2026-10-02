"""Scheduling domain: oracle and checker against an independent brute force, defects, heuristics, labels."""

import copy
import json
import random
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

BB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BB))

from metabench.domains import scheduling as S  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "scheduling"
CELL = timedelta(minutes=15)
UTC = timezone.utc
OUT = "output.json"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def fixtures():
    loaded = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(FIXTURES.glob("*.json"))}
    return {name: data for name, data in loaded.items() if "instance" in data}


def stamp(text):
    return datetime.fromisoformat(text).astimezone(UTC)


def epoch_minute(moment):
    return int(moment.timestamp()) // 60


def out(**body):
    return {OUT: json.dumps(body).encode()}


def zone(text):
    sign = -1 if text[0] == "-" else 1
    return timezone(sign * timedelta(hours=int(text[1:3]), minutes=int(text[4:6])))


class Reference:
    """Brute force written from interface.md alone: 15-minute cells and datetime arithmetic, no shared code."""

    def __init__(self, inst):
        self.inst = inst
        self.dur = timedelta(minutes=inst["duration_minutes"])
        self.gran = timedelta(minutes=inst.get("granularity_minutes", 15))
        self.w0, self.w1 = stamp(inst["window"]["start"]), stamp(inst["window"]["end"])
        self.required = [p for p in inst["participants"] if p.get("required", True)]
        self.rooms = {r["id"]: r for r in inst.get("rooms", [])}
        self.features = {c["feature"] for c in inst.get("constraints", []) if c["type"] == "room_feature"}
        self._busy, self._work = {}, {}
        self.starts = [self.w0 + self.gran * k for k in range(int((self.w1 - self.dur - self.w0) / self.gran) + 1)] \
            if self.w1 - self.dur >= self.w0 else []
        self.valid = {}
        for s in self.starts:
            if all(self.person_ok(p, s) for p in self.required):
                rooms = self.rooms_at(s)
                if rooms is not None:
                    self.valid[s] = rooms

    @staticmethod
    def cells(start, end):
        return [start + CELL * k for k in range(int((end - start) / CELL))]

    @staticmethod
    def clock(text):
        return int(text[:2]) * 60 + int(text[3:])

    def busy(self, owner):
        if owner["id"] not in self._busy:
            self._busy[owner["id"]] = {c for b in owner.get("busy", []) for c in self.cells(stamp(b["start"]), stamp(b["end"]))}
        return self._busy[owner["id"]]

    def working(self, p, cell):
        if (p["id"], cell) not in self._work:
            local = cell.astimezone(zone(p["utc_offset"]))
            minute = local.hour * 60 + local.minute
            self._work[(p["id"], cell)] = any(
                DAYS[local.weekday()] in w["days"] and self.clock(w["start"]) <= minute < self.clock(w["end"])
                for w in p["work_hours"])
        return self._work[(p["id"], cell)]

    def person_ok(self, p, s):
        e = s + self.dur
        cells = self.cells(s, e)
        if not all(self.working(p, c) for c in cells) or any(c in self.busy(p) for c in cells):
            return False
        z = zone(p["utc_offset"])
        local_start, local_end = s.astimezone(z), e.astimezone(z)
        for c in self.inst.get("constraints", []):
            if c.get("participant") != p["id"]:
                continue
            applies = "day" not in c or local_start.date() == date.fromisoformat(c["day"])
            if c["type"] == "not_before" and applies and local_start.hour * 60 + local_start.minute < self.clock(c["time"]):
                return False
            if c["type"] == "not_after" and applies:
                end_minute = local_end.hour * 60 + local_end.minute + (1440 if local_end.date() != local_start.date() else 0)
                if end_minute > self.clock(c["time"]):
                    return False
            if c["type"] == "avoid_day" and any(x.astimezone(z).date() == date.fromisoformat(c["day"]) for x in cells):
                return False
            if c["type"] == "buffer_minutes":
                pad = timedelta(minutes=c["minutes"])
                if any(x in self.busy(p) for x in self.cells(s - pad, e + pad)):
                    return False
        return True

    def rooms_at(self, s):
        """[] without rooms, the eligible room ids, or None when rooms exist and none is eligible."""
        if not self.rooms:
            return []
        cells = self.cells(s, s + self.dur)
        found = [r["id"] for r in self.rooms.values()
                 if r["capacity"] >= len(self.required) and self.features <= set(r["features"])
                 and not any(c in self.busy(r) for c in cells)]
        return found or None

    def best(self):
        order = sorted(self.valid)
        return {"earliest": order[:1], "latest": order[-1:]}.get(self.inst["preference"], order[:1])[0] if order else None

    def judge(self, files):
        """valid, suboptimal or invalid, from the output file alone."""
        try:
            body = json.loads(files[OUT].decode("utf-8"))
            if body.get("infeasible") is True:
                said = isinstance(body.get("explanation"), str) and body["explanation"].strip()
                return "valid" if said and not self.valid else "invalid"
            s, e = datetime.fromisoformat(body["start"]), datetime.fromisoformat(body["end"])
            if s.tzinfo is None or e.tzinfo is None:
                return "invalid"
            s, e = s.astimezone(UTC), e.astimezone(UTC)
        except (KeyError, ValueError, TypeError, AttributeError):
            return "invalid"
        if e - s != self.dur or s not in self.valid or (self.rooms and body.get("room") not in self.valid[s]):
            return "invalid"
        return "valid" if self.inst["preference"] == "any" or s == self.best() else "suboptimal"


def random_instance(seed):
    rng = random.Random(seed)
    offsets = [0, 0, 0, 0, 60, 60, 120, -60, -300, -210, 330, 345, 540]
    w0 = datetime(2026, 10, 5, tzinfo=UTC) + CELL * rng.randrange(0, 4 * 24 * 3)
    w1 = w0 + CELL * rng.randrange(8, 4 * 36)

    def text(moment, off):
        return moment.astimezone(timezone(timedelta(minutes=off))).isoformat(timespec="minutes")

    def clock(minute):
        return f"{minute // 60:02d}:{minute % 60:02d}"

    def spans(count, off):
        found = []
        for _ in range(count):
            start = w0 - CELL * 8 + CELL * rng.randrange(0, int((w1 - w0) / CELL) + 8)
            shown = rng.choice([off, 0, rng.choice(offsets)])
            found.append({"start": text(start, shown), "end": text(start + CELL * rng.randrange(1, 9), shown)})
        return found

    people = []
    for name in ["ana", "bo", "cy", "dee", "eli"][:rng.choice([2, 2, 3, 3, 4, 5])]:
        off = rng.choice(offsets)
        days = rng.sample(DAYS, rng.randrange(4, 8)) if rng.random() < 0.3 else DAYS
        kind = rng.random()
        if kind < 0.65:
            work = [{"days": days, "start": clock(15 * rng.randrange(24, 45)), "end": clock(15 * rng.randrange(56, 80))}]
        elif kind < 0.9:
            work = [{"days": days, "start": clock(15 * rng.randrange(24, 40)), "end": clock(15 * rng.randrange(44, 52))},
                    {"days": days, "start": clock(15 * rng.randrange(48, 56)), "end": clock(15 * rng.randrange(60, 76))}]
        else:
            work = [{"days": days, "start": "00:00", "end": "24:00"}]
        people.append({"id": name, "utc_offset": f"{'-' if off < 0 else '+'}{abs(off) // 60:02d}:{abs(off) % 60:02d}",
                       "required": rng.random() < 0.85, "work_hours": work, "busy": spans(rng.randrange(0, 4), off)})
    people[0]["required"] = True
    rooms = []
    if rng.random() < 0.4:
        rooms = [{"id": f"r{i}", "capacity": rng.randrange(2, 9), "features": rng.sample(["video", "board"], rng.randrange(0, 3)),
                  "busy": spans(rng.randrange(0, 3), 0)} for i in range(rng.randrange(1, 4))]
    constraints = []
    for _ in range(rng.choice([0, 0, 1, 1, 2, 3])):
        who = rng.choice(people)["id"]
        kind = rng.choice(["not_before", "not_after", "avoid_day", "buffer_minutes"] + (["room_feature"] if rooms else []))
        day = str((w0 + timedelta(days=rng.randrange(0, 3))).date())
        if kind in ("not_before", "not_after"):
            minute = rng.randrange(32, 48) if kind == "not_before" else rng.randrange(56, 76)
            c = {"type": kind, "participant": who, "time": clock(15 * minute)}
            if rng.random() < 0.5:
                c["day"] = day
        elif kind == "avoid_day":
            c = {"type": kind, "participant": who, "day": day}
        elif kind == "buffer_minutes":
            c = {"type": kind, "participant": who, "minutes": rng.choice([15, 30, 45])}
        else:
            c = {"type": kind, "feature": rng.choice(["video", "board"])}
        constraints.append(c)
    return {"duration_minutes": rng.choice([15, 30, 45, 60, 90]), "granularity_minutes": rng.choice([15, 30]),
            "window": {"start": text(w0, 0), "end": text(w1, 0)}, "participants": people, "rooms": rooms,
            "constraints": constraints, "preference": rng.choice(["earliest", "latest", "any"])}


def candidates(ref, first, rng):
    """Outputs of every kind for check() to judge: on and off the grid, wrong durations, rooms, odd offsets."""
    found = [first]
    for _ in range(8):
        s = ref.w0 + ref.gran * rng.randrange(-2, len(ref.starts) + 3) + (timedelta(minutes=5) if rng.random() < 0.1 else timedelta(0))
        if ref.valid and rng.random() < 0.5:
            s = rng.choice(sorted(ref.valid))
        e = s + ref.dur + (CELL if rng.random() < 0.1 else timedelta(0))
        shown = timezone(timedelta(minutes=rng.choice([0, 120, -300])))
        body = {"start": s.astimezone(shown).isoformat(timespec="minutes"), "end": e.astimezone(shown).isoformat(timespec="minutes")}
        if ref.rooms and rng.random() < 0.9:
            body["room"] = rng.choice(list(ref.rooms))
        found.append(out(**body))
    return found


CLASS = {"valid": "valid", "correct-infeasible": "valid", "suboptimal": "suboptimal"}


class OracleAgainstBruteForce(unittest.TestCase):
    def test_500_random_instances(self):
        feasible = rooms = bites = 0
        kinds = set()
        for seed in range(500):
            inst = random_instance(seed)
            ref = Reference(inst)
            self.assertEqual({epoch_minute(s): sorted(r) for s, r in ref.valid.items()},
                             {s: sorted(r) for s, r in S.valid_slots(inst)}, f"seed {seed}")
            first = S.solve(inst)[0]
            verdict = S.check(inst, first)
            self.assertEqual(verdict["label"], "valid" if ref.valid else "correct-infeasible", f"seed {seed}")
            self.assertEqual(ref.judge(first), "valid", f"seed {seed}")
            if ref.valid:
                feasible += 1
                if inst["preference"] != "any":
                    self.assertEqual(stamp(json.loads(first[OUT])["start"]), ref.best(), f"seed {seed}")
            else:
                self.assertTrue(json.loads(first[OUT])["infeasible"])
            rooms += bool(ref.rooms)
            kinds.update(c["type"] for c in inst["constraints"])
            bites += len(Reference({**inst, "constraints": []}).valid) != len(ref.valid)
            for files in candidates(ref, first, random.Random(seed)):
                self.assertEqual(CLASS.get(S.check(inst, files)["label"], "invalid"), ref.judge(files), f"seed {seed} {files}")
        self.assertTrue(150 < feasible < 400, feasible)
        self.assertGreater(rooms, 100)
        self.assertGreater(bites, 60)
        self.assertEqual(kinds, {"not_before", "not_after", "avoid_day", "buffer_minutes", "room_feature"})

    def test_hand_written_fixtures(self):
        self.assertGreaterEqual(len(fixtures()), 12)
        for name, data in fixtures().items():
            inst, expect = data["instance"], data["expect"]
            slots = S.valid_slots(inst)
            self.assertEqual(len(slots), expect["count"], name)
            if not slots:
                self.assertEqual(S.check(inst, S.solve(inst)[0])["label"], "correct-infeasible", name)
                continue
            self.assertEqual(slots[0][0], epoch_minute(stamp(expect["earliest"])), name)
            self.assertEqual(slots[-1][0], epoch_minute(stamp(expect["latest"])), name)
            if "rooms" in expect:
                self.assertEqual(slots[0][1], expect["rooms"], name)
            chosen = expect["latest"] if inst["preference"] == "latest" else expect["earliest"]
            self.assertEqual(stamp(json.loads(S.solve(inst)[0][OUT])["start"]), stamp(chosen), name)
            for preference in ("earliest", "latest", "any"):
                again = {**inst, "preference": preference}
                self.assertEqual(Reference(again).judge(S.solve(again)[0]), "valid", f"{name} {preference}")


class Semantics(unittest.TestCase):
    def label(self, name, start, end=None, room=None, preference="any"):
        """The checker's label for a slot starting at start (UTC unless it carries an offset), the fixture's duration long."""
        inst = {**fixtures()[name]["instance"], "preference": preference}
        first = stamp(start if len(start) > 16 else start + "+00:00")
        last = stamp(end) if end else first + timedelta(minutes=inst["duration_minutes"])
        body = {"start": first.isoformat(), "end": last.isoformat(), **({"room": room} if room else {})}
        return S.check(inst, out(**body))["label"]

    def test_busy_intervals_are_half_open(self):
        for start, label in [("09:30", "valid"), ("10:30", "valid"), ("09:45", "invalid"), ("10:15", "invalid"), ("10:00", "invalid")]:
            self.assertEqual(self.label("half_open", f"2026-10-05T{start}"), label, start)

    def test_offsets_compare_as_instants(self):
        for start, end in [("2026-10-05T11:30+00:00", "2026-10-05T12:00+00:00"), ("2026-10-05T13:30+02:00", "2026-10-05T14:00+02:00"),
                           ("2026-10-05T06:30-05:00", "2026-10-05T07:00-05:00"), ("2026-10-05T11:30Z", "2026-10-05T12:00:00Z")]:
            self.assertEqual(S.check(fixtures()["offsets"]["instance"], out(start=start, end=end))["label"], "valid", start)
        for start in ("2026-10-05T11:30+02:00", "2026-10-05T11:15+00:00", "2026-10-05T11:00+00:00"):
            self.assertEqual(self.label("offsets", start), "invalid", start)

    def test_work_hours_across_days_and_local_days(self):
        weekend = fixtures()["weekend"]["instance"]
        self.assertTrue(all(datetime.fromtimestamp(s * 60, UTC).weekday() == 0 for s, _ in S.valid_slots(weekend)))
        for start, label in [("2026-10-05T12:00", "valid"), ("2026-10-05T13:00", "valid"), ("2026-10-05T14:00", "invalid"),
                             ("2026-10-06T09:00", "invalid")]:
            self.assertEqual(self.label("local_day", start), label, start)
        for start, label in [("2026-10-05T09:10", "valid"), ("2026-10-05T10:10", "valid"), ("2026-10-05T10:00", "invalid"),
                             ("2026-10-05T09:40", "invalid")]:
            self.assertEqual(self.label("grid_anchor", start), label, start)

    def test_infeasibility(self):
        for name in ("infeasible", "window_too_short"):
            inst = fixtures()[name]["instance"]
            self.assertEqual(S.check(inst, S.solve(inst)[0])["label"], "correct-infeasible")
            self.assertEqual(S.check(inst, out(infeasible=True))["label"], "invalid")
            self.assertEqual(S.check(inst, out(infeasible=True, explanation="  "))["label"], "invalid")
            self.assertEqual(S.check(inst, out(start="2026-10-05T09:00+00:00", end="2026-10-05T09:30+00:00"))["label"], "invalid")
        self.assertEqual(S.check(fixtures()["basic"]["instance"], out(infeasible=True, explanation="busy"))["label"], "wrong-infeasible")

    def test_unreadable_outputs(self):
        inst = fixtures()["basic"]["instance"]
        for files in [{}, {OUT: b"not json"}, {OUT: b"[]"}, out(start="2026-10-05T10:30+00:00"),
                      out(start="2026-10-05T10:30", end="2026-10-05T11:00"), out(start=5, end=6)]:
            self.assertEqual(S.check(inst, files)["label"], "unparseable", files)

    def test_defaults_and_empty_work_hours(self):
        basic = copy.deepcopy(fixtures()["basic"]["instance"])
        expected = S.valid_slots(basic)
        del basic["granularity_minutes"]
        self.assertEqual(S.valid_slots(basic), expected)
        basic["participants"][0]["work_hours"] = []
        self.assertEqual(S.valid_slots(basic), [])

    def test_preferences(self):
        self.assertEqual(self.label("basic", "2026-10-05T10:30", preference="earliest"), "valid")
        self.assertEqual(self.label("basic", "2026-10-05T11:30", preference="earliest"), "suboptimal")
        self.assertEqual(self.label("basic", "2026-10-05T11:30", preference="latest"), "valid")
        self.assertEqual(self.label("basic", "2026-10-05T10:30", preference="latest"), "suboptimal")

    def test_rooms_and_optional_participants(self):
        self.assertEqual(self.label("rooms", "2026-10-05T09:00", room="r3"), "valid")
        for room in ("r1", "r2", "r9", None):
            self.assertEqual(self.label("rooms", "2026-10-05T09:00", room=room), "invalid", room)
        self.assertEqual(self.label("rooms", "2026-10-05T09:30", room="r3"), "invalid")
        self.assertEqual(self.label("optional", "2026-10-05T09:00"), "valid")
        self.assertEqual(len(S.solve(fixtures()["any_two_rooms"]["instance"])), 4)

    def test_constraints(self):
        for start, label in [("2026-10-06T12:00", "valid"), ("2026-10-06T15:00", "valid"), ("2026-10-07T10:00", "valid"),
                             ("2026-10-07T15:00", "valid"), ("2026-10-05T10:00", "invalid"), ("2026-10-06T10:00", "invalid"),
                             ("2026-10-06T11:00", "invalid"), ("2026-10-06T16:00", "invalid"), ("2026-10-07T09:00", "invalid")]:
            self.assertEqual(self.label("constraints", start), label, start)
        for start, label in [("2026-10-05T14:00", "valid"), ("2026-10-06T11:00", "valid"), ("2026-10-06T09:00", "valid"),
                             ("2026-10-05T13:00", "invalid"), ("2026-10-06T12:00", "invalid"), ("2026-10-05T09:00", "invalid")]:
            self.assertEqual(self.label("day_specific", start), label, start)


def workspace_with(testcase, inst):
    tmp = tempfile.TemporaryDirectory()
    testcase.addCleanup(tmp.cleanup)
    (Path(tmp.name) / "input.json").write_text(inst if isinstance(inst, str) else json.dumps(inst), encoding="utf-8")
    return Path(tmp.name)


class Recognition(unittest.TestCase):
    def test_round_trip_and_extra_keys(self):
        inst = fixtures()["rooms"]["instance"]
        self.assertEqual(S.recognize(workspace_with(self, inst), ""), inst)
        self.assertEqual(S.recognize(workspace_with(self, "﻿" + json.dumps({**inst, "notes": [1]})), "")["notes"], [1])

    def test_non_conforming_inputs_are_not_recognized(self):
        inst = fixtures()["constraints"]["instance"]

        def recognized(edit):
            edited = copy.deepcopy(inst)
            edit(edited)
            return S.recognize(workspace_with(self, edited), "")

        self.assertIsNone(S.recognize(Path(tempfile.gettempdir()) / "no-such-dir", ""))
        self.assertIsNone(S.recognize(workspace_with(self, "{not json"), ""))
        self.assertIsNone(recognized(lambda d: d["window"].update(start="2026-10-05T09:00")))
        self.assertIsNone(recognized(lambda d: d["constraints"].append({"type": "no_lunch", "participant": "ana"})))
        self.assertIsNone(recognized(lambda d: d["constraints"].append({"type": "avoid_day", "participant": "zed", "day": "2026-10-06"})))
        self.assertIsNone(recognized(lambda d: d.update(preference="soonest")))
        self.assertIsNone(recognized(lambda d: d["participants"][0].update(utc_offset="CET")))
        self.assertIsNone(recognized(lambda d: d["participants"][0]["work_hours"][0].update(days=["Monday"])))
        self.assertIsNone(recognized(lambda d: d["participants"][0]["busy"].append({"start": "2026-10-05T10:00+00:00", "end": "2026-10-05T09:00+00:00"})))
        self.assertIsNone(recognized(lambda d: d["participants"].append(dict(d["participants"][0]))))
        self.assertIsNone(recognized(lambda d: d.pop("participants")))
        self.assertIsNotNone(recognized(lambda d: d.pop("granularity_minutes", None)))


def small(**changes):
    inst = {"duration_minutes": 30, "granularity_minutes": 15,
            "window": {"start": "2026-10-05T09:00+00:00", "end": "2026-10-05T11:00+00:00"},
            "participants": [{"id": who, "utc_offset": "+00:00", "busy": [],
                              "work_hours": [{"days": ["Mon"], "start": "09:00", "end": "17:00"}]} for who in ("ana", "bo")],
            "constraints": [], "preference": "earliest"}
    inst.update(changes)
    return inst


def busy(inst, who, start, end):
    inst = copy.deepcopy(inst)
    inst["participants"][who]["busy"].append({"start": f"2026-10-05T{start}+00:00", "end": f"2026-10-05T{end}+00:00"})
    return inst


class Defects(unittest.TestCase):
    def label(self, inst, files):
        verdict = S.check(inst, files)["label"]
        self.assertEqual(Reference(inst).judge(files), CLASS.get(verdict, "invalid"))
        return verdict

    def test_each_defect_is_wrong_on_its_crafted_instance(self):
        zoned = small(window={"start": "2026-10-05T07:00+00:00", "end": "2026-10-05T17:00+00:00"}, granularity_minutes=30, preference="latest")
        zoned["participants"][0]["utc_offset"] = "+02:00"
        crafted = {
            "ignore_participant": busy(small(), 0, "09:00", "09:30"),
            "ignore_constraints": small(constraints=[{"type": "not_before", "participant": "ana", "time": "10:00"}]),
            "boundary": busy(small(window={"start": "2026-10-05T09:00+00:00", "end": "2026-10-05T10:30+00:00"}, preference="latest"), 0, "10:00", "11:00"),
            "ignore_offsets": zoned,
            "never_infeasible": fixtures()["infeasible"]["instance"],
            "always_infeasible": fixtures()["basic"]["instance"],
        }
        self.assertEqual(set(crafted), set(S.DEFECTS))
        for name, inst in crafted.items():
            expected = "correct-infeasible" if name == "never_infeasible" else "valid"
            self.assertEqual(self.label(inst, S.solve(inst)[0]), expected, name)
            self.assertIn(self.label(inst, S.DEFECTS[name](inst, random.Random(1))), ("invalid", "wrong-infeasible"), name)

    def test_defects_are_right_where_they_do_not_apply(self):
        basic, infeasible = fixtures()["basic"]["instance"], fixtures()["infeasible"]["instance"]
        self.assertEqual(self.label(basic, S.DEFECTS["never_infeasible"](basic, random.Random(0))), "valid")
        self.assertEqual(self.label(infeasible, S.DEFECTS["always_infeasible"](infeasible, random.Random(0))), "correct-infeasible")
        self.assertEqual(self.label(basic, S.DEFECTS["ignore_constraints"](basic, random.Random(0))), "valid")
        self.assertEqual(self.label(basic, S.DEFECTS["ignore_offsets"](basic, random.Random(0))), "valid")

    def test_defects_run_on_random_instances(self):
        for seed in range(60):
            inst = random_instance(seed)
            for name, defect in S.DEFECTS.items():
                files = defect(inst, random.Random(seed))
                self.assertEqual(set(files), {OUT}, (seed, name))
                self.label(inst, files)

    def test_greedy_first_ignores_preference_and_constraints(self):
        greedy = S.HEURISTICS["greedy_first"]
        latest = busy(small(preference="latest"), 0, "09:00", "09:30")
        self.assertEqual(self.label(latest, greedy(workspace_with(self, latest), "")), "suboptimal")
        constrained = small(constraints=[{"type": "not_before", "participant": "ana", "time": "10:00"}])
        self.assertEqual(self.label(constrained, greedy(workspace_with(self, constrained), "")), "invalid")
        plain = busy(small(), 1, "09:00", "10:00")
        self.assertEqual(self.label(plain, greedy(workspace_with(self, plain), "")), "valid")
        none = fixtures()["infeasible"]["instance"]
        self.assertEqual(self.label(none, greedy(workspace_with(self, none), "")), "correct-infeasible")
        self.assertEqual(greedy(Path(tempfile.gettempdir()) / "no-such-dir", ""), {})

    def test_random_valid_format_is_well_formed(self):
        for seed in (3, 8, 21, 34, 55):
            inst = random_instance(seed)
            ref = Reference(inst)
            body = json.loads(S.HEURISTICS["random_valid_format"](workspace_with(self, inst), "")[OUT])
            self.assertIn(stamp(body["start"]), ref.starts)
            self.assertEqual(stamp(body["end"]) - stamp(body["start"]), ref.dur)
            self.assertEqual("room" in body, bool(ref.rooms))


class Labeled(unittest.TestCase):
    def test_labels_agree_with_check_and_brute_force(self):
        every = [(n, d["instance"]) for n, d in fixtures().items()] + [(f"seed {s}", random_instance(s)) for s in range(80)]
        accepted = {"valid": ("valid", "correct-infeasible"), "suboptimal": ("suboptimal",),
                    "invalid": ("invalid", "unparseable", "wrong-infeasible")}
        for name, inst in every:
            ref = Reference(inst)
            items = S.labeled(inst)
            for item in items:
                where = (name, item["kind"])
                self.assertIn(S.check(inst, item["files"])["label"], accepted[item["label"]], where)
                self.assertEqual(ref.judge(item["files"]), item["label"], where)
                self.assertTrue(all(isinstance(k, str) and isinstance(v, bytes) for k, v in item["files"].items()), where)
            self.assertEqual(len({tuple(sorted(i["files"].items())) for i in items}), len(items), f"{name}: duplicate outputs")
            self.assertTrue({"valid", "invalid"} <= {i["label"] for i in items}, name)

    def test_kinds(self):
        def kinds(name, **changes):
            return {i["kind"]: i["label"] for i in S.labeled({**fixtures()[name]["instance"], **changes})}

        found = kinds("basic")
        for kind in ("canonical", "offset-variant", "key-order-variant", "whitespace-variant", "seconds-variant", "extra-key-variant",
                     "shifted-earlier", "wrong-duration", "off-grid", "no-offset", "missing-end", "prose"):
            self.assertIn(kind, found)
        self.assertEqual(found["valid-not-optimal"], "suboptimal")
        defects = {k: v for k, v in found.items() if k.startswith("defect:")}
        self.assertTrue(defects)
        self.assertEqual(set(defects.values()), {"invalid"})
        self.assertNotIn("valid-not-optimal", kinds("basic", preference="any"))
        self.assertEqual(kinds("any_two_rooms")["alternate-optimal"], "valid")
        self.assertEqual(kinds("rooms")["unknown-room"], "invalid")
        gone = kinds("infeasible")
        self.assertEqual((gone["empty-explanation"], gone["explanation-variant"]), ("invalid", "valid"))
        slots = [i for i in S.labeled(fixtures()["infeasible"]["instance"]) if i["label"] == "invalid" and b'"start"' in i["files"][OUT]]
        self.assertTrue(slots, "a slot offered for an infeasible request is labelled invalid")

    def test_variants_name_the_same_instants(self):
        items = S.labeled(fixtures()["offsets"]["instance"])
        starts = {stamp(json.loads(i["files"][OUT])["start"]) for i in items if i["kind"].endswith("variant") or i["kind"] == "canonical"}
        self.assertEqual(starts, {stamp("2026-10-05T11:30+00:00")})
        shown = {json.loads(i["files"][OUT])["start"][-6:] for i in items if i["kind"] == "offset-variant"}
        self.assertGreaterEqual(len(shown), 2)


if __name__ == "__main__":
    unittest.main()
