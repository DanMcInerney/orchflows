"""Calendar domain: recognition, the oracle, every policy rule type, preservation, defects, labels, policy text."""

import copy
import functools
import json
import random
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

BB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BB))

from metabench.domains import calendar as C  # noqa: E402
from metabench.domains import calendar_outputs as O  # noqa: E402
from metabench.domains import calendar_state as S  # noqa: E402
from metabench.domains import scheduling_rules as R  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "calendar"
RESULT = "result.json"
BUFFER_FILE = "calendars/ana.json"


@functools.lru_cache(maxsize=None)
def _fixtures():
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(FIXTURES.glob("*.json"))}


def fixtures():
    """The fixture data; callers copy before editing."""
    return _fixtures()


def in_memory(data):
    """The instance a fixture implies, built without touching the disk."""
    state = {**{S.calendar_path(k): v for k, v in data["calendars"].items()}, **{S.room_path(k): v for k, v in data.get("rooms", {}).items()}}
    instance = {"request": data["request"], "policy": data["policy"], "state": state}
    instance["schedule"] = S.schedule_instance(instance)
    return instance


def minute(clock, day="2026-10-05", zone="+00:00"):
    return R.stamp(f"{day}T{clock}{zone}")[0]


class CalendarCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def make(self, name, edit=None):
        """The instance for a fixture, optionally with its data edited first."""
        data = copy.deepcopy(fixtures()[name])
        if edit:
            edit(data)
        return in_memory(data)


class Fixtures(CalendarCase):
    def test_a_workspace_on_disk_is_recognized_as_the_instance_built_in_memory(self):
        for name, data in fixtures().items():
            with self.subTest(name):
                workspace = self.root / name
                C.build_workspace(workspace, request=data["request"], policy=data["policy"], calendars=data["calendars"],
                                  rooms=data.get("rooms"))
                self.assertEqual(C.recognize(workspace), in_memory(data))

    def test_valid_starts_match_the_hand_computed_expectations(self):
        for name, data in fixtures().items():
            with self.subTest(name):
                slots = R.slots(R.model(self.make(name)["schedule"]))
                expect = data["expect"]
                self.assertEqual(len(slots), expect["count"])
                if slots:
                    self.assertEqual((slots[0][0], slots[-1][0]), (R.stamp(expect["first"])[0], R.stamp(expect["last"])[0]))
                if "rooms_at_first" in expect:
                    self.assertEqual(slots[0][1], expect["rooms_at_first"])

    def test_oracle_outputs_are_valid_and_infeasible_requests_are_refused(self):
        for name, data in fixtures().items():
            with self.subTest(name):
                instance = self.make(name)
                outputs = C.solve(instance)
                self.assertTrue(outputs)
                want = "correct-infeasible" if data["expect"].get("infeasible") else "valid"
                for files in outputs:
                    self.assertEqual(C.check(instance, files)["label"], want)

    def test_defects_the_fixture_names_are_rejected(self):
        for name, data in fixtures().items():
            for defect in data["expect"]["wrong"]:
                with self.subTest(name, defect=defect):
                    instance = self.make(name)
                    self.assertIn(C.check(instance, C.DEFECTS[defect](instance, random.Random(0)))["label"], R.REJECTED)

    def test_oracle_enumerates_every_room_and_every_slot_for_any(self):
        instance = self.make("any")
        self.assertEqual(len(C.solve(instance)), 3)
        instance = self.make("room_small_group")
        rooms = {json.loads(f[RESULT])["booked"]["room"] for f in C.solve(instance)}
        self.assertEqual(rooms, {"birch", "elm"})

    def test_latest_preference_books_the_last_start(self):
        booked = json.loads(C.solve(self.make("latest_room"))[0][RESULT])["booked"]
        self.assertEqual((R.stamp(booked["start"])[0], booked["room"]), (minute("11:00"), "birch"))

    def test_new_entries_use_each_owners_offset_and_result_uses_the_window_offset(self):
        files = C.solve(self.make("offsets"))[0]
        self.assertEqual(json.loads(files[RESULT])["booked"]["start"], "2026-10-05T14:00+00:00")
        self.assertEqual(json.loads(files["calendars/ana.json"])["events"][-1]["start"], "2026-10-05T16:00+02:00")
        self.assertEqual(json.loads(files["calendars/bo.json"])["events"][-1]["start"], "2026-10-05T09:00-05:00")

    def test_event_ids_never_collide_with_existing_ones(self):
        instance = self.make("buffer", lambda d: d["calendars"]["ana"]["events"].append(
            {"id": "bk-1", "title": "x", "start": "2026-10-05T17:00+00:00", "end": "2026-10-05T17:30+00:00"}))
        self.assertEqual(json.loads(C.solve(instance)[0][RESULT])["booked"]["event_id"], "bk-2")


class RuleEnforcement(CalendarCase):
    def book(self, instance, clock, room=None, **options):
        return O.booking(instance, minute(clock), room, **options)

    def reasons(self, instance, files):
        verdict = C.check(instance, files)
        return verdict["label"], " ".join(verdict["reasons"])

    def test_buffer_minutes(self):
        instance = self.make("buffer")
        label, why = self.reasons(instance, self.book(instance, "11:30"))
        self.assertEqual(label, "invalid")
        self.assertIn("buffer_minutes", why)
        self.assertEqual(self.reasons(instance, self.book(instance, "11:45"))[0], "valid")
        self.assertEqual(self.reasons(instance, self.book(instance, "14:15"))[0], "suboptimal")
        self.assertEqual(self.reasons(instance, self.book(instance, "14:00"))[0], "invalid")

    def test_without_the_buffer_rule_back_to_back_is_valid(self):
        no_buffer = self.make("buffer", lambda d: d["policy"].update(rules=[]))
        self.assertEqual(self.reasons(no_buffer, self.book(no_buffer, "11:30"))[0], "valid")

    def test_focus_blocks_protect_normal_requests_and_yield_to_urgent_ones(self):
        normal = self.make("focus_normal")
        self.assertEqual(self.reasons(normal, self.book(normal, "09:00"))[0], "invalid")
        self.assertEqual(self.reasons(normal, self.book(normal, "11:00"))[0], "valid")
        urgent = self.make("focus_urgent")
        self.assertEqual(self.reasons(urgent, self.book(urgent, "09:00"))[0], "valid")

    def test_urgent_override_is_ignored_when_the_policy_does_not_grant_it(self):
        strict = self.make("focus_urgent", lambda d: d["policy"]["rules"][0].update(urgent_may_override=False))
        self.assertEqual(self.reasons(strict, self.book(strict, "09:00"))[0], "invalid")
        absent = self.make("focus_urgent", lambda d: d["policy"].update(rules=[]))
        self.assertEqual(self.reasons(absent, self.book(absent, "09:00"))[0], "invalid")

    def test_override_ignores_focus_buffers_but_not_meetings(self):
        def edit(data):
            data["policy"]["rules"].append({"type": "buffer_minutes", "minutes": 30})
            data["calendars"]["ana"]["events"].append({"id": "ev-m", "title": "Review", "kind": "meeting",
                                                       "start": "2026-10-05T10:30+00:00", "end": "2026-10-05T11:00+00:00"})
        instance = self.make("focus_urgent", edit)
        slots = [s for s, _ in R.slots(R.model(instance["schedule"]))]
        self.assertEqual(slots[0], minute("09:00"))
        self.assertNotIn(minute("10:00"), slots)
        self.assertIn(minute("11:30"), slots)

    def test_room_feature_threshold_capacity_and_busy(self):
        instance = self.make("room_feature")
        for room, clock, want in (("cedar", "10:00", "valid"), ("birch", "10:00", "invalid"), ("elm", "10:00", "invalid"),
                                  ("cedar", "09:00", "invalid")):
            with self.subTest(room=room, clock=clock):
                self.assertEqual(self.reasons(instance, self.book(instance, clock, room))[0], want)
        self.assertIn("cannot host", self.reasons(instance, self.book(instance, "10:00", "birch"))[1])
        small = self.make("room_small_group")
        for room in ("birch", "elm"):
            self.assertEqual(self.reasons(small, self.book(small, "09:00", room))[0], "valid")
        self.assertEqual(self.reasons(small, self.book(small, "09:00", "cedar"))[0], "invalid")

    def test_room_is_required_when_rooms_exist(self):
        instance = self.make("room_busy")
        files = self.book(instance, "10:00", "birch")
        body = json.loads(files[RESULT])
        del body["booked"]["room"]
        files[RESULT] = json.dumps(body).encode()
        self.assertEqual(C.check(instance, files)["label"], "invalid")

    def test_work_hours_busy_time_grid_and_window(self):
        instance = self.make("offsets")
        for clock, want in (("14:00", "valid"), ("13:00", "invalid"), ("15:00", "invalid"), ("14:15", "invalid"),
                            ("12:00", "invalid")):
            with self.subTest(clock=clock):
                self.assertEqual(self.reasons(instance, self.book(instance, clock))[0], want)

    def test_optional_attendees_never_restrict_the_time(self):
        instance = self.make("optional")
        self.assertEqual(C.check(instance, C.solve(instance)[0])["label"], "valid")
        self.assertEqual(R.slots(R.model(instance["schedule"]))[0][0], minute("09:00"))

    def test_infeasible_requests_must_be_refused_and_nothing_booked(self):
        instance = self.make("infeasible")
        self.assertEqual(C.check(instance, O.render(*O.refusal_docs(instance)))["label"], "correct-infeasible")
        self.assertEqual(C.check(instance, self.book(instance, "09:30"))["label"], "invalid")
        wrong = C.check(self.make("buffer"), O.render(*O.refusal_docs(self.make("buffer"))))
        self.assertEqual(wrong["label"], "wrong-infeasible")
        booked_anyway = json.loads(self.book(instance, "09:30")["calendars/bo.json"])
        files = O.render(*O.refusal_docs(instance))
        files["calendars/bo.json"] = json.dumps(booked_anyway).encode()
        verdict = C.check(instance, files)
        self.assertEqual(verdict["label"], "invalid")
        self.assertIn("declared infeasible", " ".join(verdict["reasons"]))
        empty = C.check(instance, O.render(*O.refusal_docs(instance, "  ")))
        self.assertEqual(empty["label"], "invalid")


class Preservation(CalendarCase):
    def setUp(self):
        super().setUp()
        self.instance = self.make("buffer")
        self.base = C.solve(self.instance)[0]

    def damaged(self, path, edit):
        files = dict(self.base)
        doc = json.loads(files[path])
        edit(doc)
        files[path] = json.dumps(doc).encode()
        return C.check(self.instance, files)

    def assert_clobber(self, verdict, text):
        self.assertEqual(verdict["label"], "invalid")
        self.assertEqual(verdict["critical"], ["clobber"])
        self.assertIn(text, " ".join(verdict["reasons"]))

    def test_the_oracle_booking_preserves_everything(self):
        self.assertEqual(C.check(self.instance, self.base), {"label": "valid", "reasons": [], "critical": []})

    def test_removed_edited_and_moved_entries_are_critical(self):
        self.assert_clobber(self.damaged(BUFFER_FILE, lambda d: d["events"].pop(0)), "removed")
        self.assert_clobber(self.damaged(BUFFER_FILE, lambda d: d["events"][0].update(title="renamed")), "was changed")
        self.assert_clobber(self.damaged(BUFFER_FILE, lambda d: d["events"][0].update(start="2026-10-05T09:15+00:00")), "was changed")
        self.assert_clobber(self.damaged(BUFFER_FILE, lambda d: d["events"][0].pop("title")), "was changed")

    def test_changed_calendar_fields_are_critical(self):
        self.assert_clobber(self.damaged(BUFFER_FILE, lambda d: d.update(work_hours=[])), "'work_hours' was changed")
        self.assert_clobber(self.damaged(BUFFER_FILE, lambda d: d.update(utc_offset="+01:00")), "'utc_offset' was changed")

    def test_missing_unreadable_and_non_calendar_files_are_critical(self):
        files = dict(self.base)
        del files[BUFFER_FILE]
        self.assert_clobber(C.check(self.instance, files), "is missing")
        files[BUFFER_FILE] = b"{not json"
        self.assert_clobber(C.check(self.instance, files), "not valid JSON")
        files[BUFFER_FILE] = b"[]"
        self.assert_clobber(C.check(self.instance, files), "no longer a calendar file")

    def test_formatting_changes_are_not_changes(self):
        def reformat(doc):
            doc["events"][0]["start"] = "2026-10-05T11:00+02:00"
            doc["events"][0]["end"] = "2026-10-05T12:00+02:00"
            doc["events"][0]["note"] = "added key"
            doc["events"].reverse()
        self.assertEqual(self.damaged(BUFFER_FILE, reformat)["label"], "valid")
        files = {path: (json.dumps(json.loads(data), indent=4, sort_keys=True).encode() if path != RESULT else data)
                 for path, data in self.base.items()}
        self.assertEqual(C.check(self.instance, files)["label"], "valid")

    def test_clobber_and_claims_done_defects_are_critical(self):
        clobbered = C.check(self.instance, C.DEFECTS["clobber"](self.instance, random.Random(0)))
        self.assertEqual((clobbered["label"], clobbered["critical"]), ("invalid", ["clobber"]))
        claimed = C.check(self.instance, C.DEFECTS["claims_done"](self.instance, random.Random(0)))
        self.assertEqual((claimed["label"], claimed["critical"]), ("invalid", ["false-claim"]))
        self.assertIn("exactly one new entry", " ".join(claimed["reasons"]))

    def test_booking_must_be_in_every_required_file_exactly_once(self):
        gone = self.damaged("calendars/bo.json", lambda d: d["events"].pop())
        self.assertEqual((gone["label"], gone["critical"]), ("invalid", []))
        twice = self.damaged(BUFFER_FILE, lambda d: d["events"].append({**d["events"][-1], "id": "bk-again"}))
        self.assertEqual(twice["label"], "invalid")
        elsewhere = self.damaged(BUFFER_FILE, lambda d: d["events"][-1].update(start="2026-10-05T14:15+00:00", end="2026-10-05T15:15+00:00"))
        self.assertEqual(elsewhere["label"], "invalid")
        renamed = self.damaged(BUFFER_FILE, lambda d: d["events"][-1].update(id="other"))
        self.assertEqual(renamed["label"], "invalid")

    def test_result_must_parse_and_agree_with_the_files(self):
        for raw, label in ((None, "unparseable"), (b"nope", "unparseable"), (b"[]", "unparseable"), (b"{}", "unparseable")):
            files = dict(self.base)
            if raw is None:
                del files[RESULT]
            else:
                files[RESULT] = raw
            self.assertEqual(C.check(self.instance, files)["label"], label)
        body = json.loads(self.base[RESULT])
        body["booked"]["event_id"] = "someone-else"
        self.assertEqual(C.check(self.instance, {**self.base, RESULT: json.dumps(body).encode()})["label"], "invalid")
        del body["booked"]["event_id"]
        verdict = C.check(self.instance, {**self.base, RESULT: json.dumps(body).encode()})
        self.assertEqual(verdict["label"], "invalid")
        self.assertIn("event_id", " ".join(verdict["reasons"]))

    def test_optional_invitees_may_gain_the_entry_but_bystanders_may_not(self):
        instance = self.make("optional")
        docs, result = O.booking_docs(instance, minute("09:00"), None, targets=O.default_targets(instance) + ["calendars/dee.json"])
        self.assertEqual(C.check(instance, O.render(docs, result))["label"], "valid")
        docs, result = O.booking_docs(instance, minute("09:00"), None, targets=O.default_targets(instance) + ["calendars/eve.json"])
        verdict = C.check(instance, O.render(docs, result))
        self.assertEqual(verdict["label"], "invalid")
        self.assertIn("takes no part", " ".join(verdict["reasons"]))
        docs, result = O.booking_docs(instance, minute("09:00"), None, targets=O.default_targets(instance) + ["calendars/dee.json"])
        docs["calendars/dee.json"]["events"].append({"id": "x", "start": "2026-10-05T09:00+00:00", "end": "2026-10-05T09:30+00:00"})
        self.assertEqual(C.check(instance, O.render(docs, result))["label"], "invalid")


class Outputs(CalendarCase):
    def test_apply_collect_and_recognition_round_trip(self):
        data = fixtures()["room_feature"]
        source = self.root / "source"
        C.build_workspace(source, request=data["request"], policy=data["policy"], calendars=data["calendars"], rooms=data["rooms"])
        instance = C.recognize(source)
        files = C.solve(instance)[0]
        final = self.root / "final"
        shutil.copytree(source, final)
        C.apply(final, files)
        self.assertEqual(C.collect(final), files)
        self.assertEqual(C.check(instance, C.collect(final))["label"], "valid")
        self.assertIsNotNone(C.recognize(final))

    def test_collect_reads_only_state_files_and_the_result(self):
        data = fixtures()["buffer"]
        C.build_workspace(self.root, request=data["request"], policy=data["policy"], calendars=data["calendars"])
        (self.root / "notes.txt").write_text("x")
        self.assertEqual(sorted(C.collect(self.root)), ["calendars/ana.json", "calendars/bo.json"])
        (self.root / RESULT).write_text("{}")
        self.assertIn(RESULT, C.collect(self.root))

    def test_defects_are_wrong_only_where_they_matter(self):
        instance = self.make("room_small_group")
        for name in ("policy_blind_buffer", "policy_blind_focus", "policy_blind_room_feature", "double_book"):
            self.assertEqual(C.check(instance, C.DEFECTS[name](instance, random.Random(0)))["label"], "valid", name)
        self.assertEqual(C.check(self.make("any"), C.DEFECTS["clobber"](self.make("any"), random.Random(0)))["label"], "valid")

    def test_double_book_takes_a_room_that_is_busy(self):
        instance = self.make("room_busy")
        verdict = C.check(instance, C.DEFECTS["double_book"](instance, random.Random(0)))
        self.assertEqual(verdict["label"], "invalid")
        self.assertIn("cannot host", " ".join(verdict["reasons"]))

    def test_busy_only_heuristic_is_the_hurried_assistant(self):
        for name, want in (("buffer", "invalid"), ("focus_normal", "valid"), ("room_feature", "invalid"), ("any", "valid"),
                           ("infeasible", "invalid")):
            with self.subTest(name):
                data = fixtures()[name]
                workspace = self.root / f"busy-{name}"
                C.build_workspace(workspace, request=data["request"], policy=data["policy"], calendars=data["calendars"],
                                  rooms=data.get("rooms"))
                instance = C.recognize(workspace)
                label = C.check(instance, C.HEURISTICS["busy_only"](workspace, ""))["label"]
                self.assertIn(label, ("valid",) if want == "valid" else R.REJECTED)
        self.assertEqual(C.HEURISTICS["busy_only"](self.root / "missing", ""), {})


class Labeled(CalendarCase):
    EXPECTED = {"valid": ("valid", "correct-infeasible"), "suboptimal": ("suboptimal",), "invalid": R.REJECTED + ("invalid",)}

    def test_labels_agree_with_check_on_every_fixture(self):
        for name in fixtures():
            with self.subTest(name):
                instance = self.make(name)
                items = C.labeled(instance)
                self.assertGreater(len(items), 10)
                self.assertEqual(len({tuple(sorted(i["files"].items())) for i in items}), len(items))
                for item in items:
                    self.assertIn(C.check(instance, item["files"])["label"], self.EXPECTED[item["label"]], item["kind"])

    def test_feasible_instances_cover_the_variants_and_failures(self):
        kinds = {i["kind"] for i in C.labeled(self.make("buffer"))}
        for kind in ("canonical", "offset-variant", "key-order-variant", "whitespace-variant", "seconds-variant",
                     "extra-key-variant", "entry-order-variant", "valid-not-optimal", "shifted-later", "wrong-infeasible",
                     "no-result", "wrong-event-id", "state-result-mismatch", "missing-attendee-entry", "duplicate-entry",
                     "defect:policy_blind_buffer", "defect:clobber", "defect:claims_done", "clobber:removed-entry",
                     "clobber:edited-entry", "clobber:moved-entry", "clobber:changed-work-hours"):
            self.assertIn(kind, kinds)
        self.assertIn("invited-optional", {i["kind"] for i in C.labeled(self.make("optional"))})
        self.assertIn("entry-for-bystander", {i["kind"] for i in C.labeled(self.make("optional"))})
        self.assertIn("missing-room-entry", {i["kind"] for i in C.labeled(self.make("room_busy"))})
        self.assertIn("alternate-optimal", {i["kind"] for i in C.labeled(self.make("any"))})

    def test_infeasible_instances_label_refusals_valid_and_bookings_invalid(self):
        items = C.labeled(self.make("infeasible"))
        by_kind = {i["kind"]: i["label"] for i in items}
        self.assertEqual(by_kind["canonical"], "valid")
        self.assertEqual(by_kind["explanation-variant"], "valid")
        self.assertEqual(by_kind["empty-explanation"], "invalid")
        self.assertEqual(by_kind["slot-for-infeasible"], "invalid")
        self.assertEqual(by_kind["defect:policy_blind_buffer"], "invalid")

    def test_outputs_are_whole_states(self):
        instance = self.make("room_busy")
        state = set(instance["state"])
        for item in C.labeled(instance):
            self.assertLessEqual(state, set(item["files"]))
            self.assertLessEqual(set(item["files"]) - state, {RESULT})


class PolicyAndRecognition(CalendarCase):
    def test_policy_text_states_each_rule_and_the_baseline(self):
        text = C.render_policy({"rules": [{"type": "buffer_minutes", "minutes": 20}, {"type": "focus_blocks", "urgent_may_override": True},
                                          {"type": "room_feature", "min_attendees": 5, "feature": "video"}]})
        for fragment in ("at least 20 minutes", "`urgent` may be booked over them", "5 or more people must attend",
                         "`video` feature", "Optional attendees never restrict", "granularity grid", "Never change or remove"):
            self.assertIn(fragment, text)
        strict = C.render_policy({"team": "Platform", "rules": [{"type": "focus_blocks"}, {"type": "room_feature", "feature": "audio"}]})
        self.assertIn("# Booking policy for Platform", strict)
        self.assertIn("Not even an urgent request", strict)
        self.assertIn("The room needs the `audio` feature", strict)
        self.assertNotIn("minutes between", C.render_policy({"rules": []}))

    def test_policy_md_in_a_workspace_is_the_rendering_of_policy_json(self):
        for name, data in fixtures().items():
            with self.subTest(name):
                workspace = self.root / name
                C.build_workspace(workspace, request=data["request"], policy=data["policy"], calendars=data["calendars"],
                                  rooms=data.get("rooms"))
                self.assertEqual((workspace / "policy.md").read_text(encoding="utf-8"), C.render_policy(data["policy"]))

    def test_recognition_round_trip(self):
        instance = self.make("room_feature")
        self.assertEqual(set(instance), {"request", "policy", "state", "schedule"})
        self.assertEqual(set(instance["state"]), {"calendars/ana.json", "calendars/bo.json", "calendars/cy.json", "calendars/dee.json",
                                                  "rooms/birch.json", "rooms/cedar.json", "rooms/elm.json"})
        schedule = instance["schedule"]
        self.assertEqual([p["id"] for p in schedule["participants"]], ["ana", "bo", "cy", "dee"])
        self.assertEqual(schedule["constraints"], [{"type": "room_feature", "feature": "video"}])
        self.assertEqual(json.loads(json.dumps(instance)), instance)

    def test_buffer_and_threshold_become_constraints(self):
        schedule = self.make("buffer")["schedule"]
        self.assertEqual(schedule["constraints"], [{"type": "buffer_minutes", "participant": p, "minutes": 15} for p in ("ana", "bo")])
        self.assertEqual(self.make("room_small_group")["schedule"]["constraints"], [])

    def test_non_conforming_workspaces_are_not_recognized(self):
        def broken(edit):
            data = copy.deepcopy(fixtures()["optional"])
            edit(data)
            workspace = self.root / f"broken-{len(list(self.root.iterdir()))}"
            files = {"request.json": data["request"], "policy.json": data["policy"],
                     **{f"calendars/{k}.json": v for k, v in data["calendars"].items()}}
            for rel, doc in files.items():
                (workspace / rel).parent.mkdir(parents=True, exist_ok=True)
                (workspace / rel).write_text(json.dumps(doc), encoding="utf-8")
            return workspace
        cases = {
            "unknown rule": lambda d: d["policy"].update(rules=[{"type": "no_fridays"}]),
            "duplicate buffer": lambda d: d["policy"].update(rules=[{"type": "buffer_minutes", "minutes": 5}] * 2),
            "negative buffer": lambda d: d["policy"].update(rules=[{"type": "buffer_minutes", "minutes": -1}]),
            "room_feature without feature": lambda d: d["policy"].update(rules=[{"type": "room_feature"}]),
            "missing calendar": lambda d: d["calendars"].pop("bo"),
            "no attendees": lambda d: d["request"].update(attendees=[]),
            "overlapping optional": lambda d: d["request"].update(optional=["ana"]),
            "bad priority": lambda d: d["request"].update(priority="whenever"),
            "bad preference": lambda d: d["request"].update(preference="soonish"),
            "duplicate entry ids": lambda d: d["calendars"]["ana"].update(events=[
                {"id": "x", "start": "2026-10-05T09:00+00:00", "end": "2026-10-05T10:00+00:00"}] * 2),
            "entry without offset": lambda d: d["calendars"]["ana"].update(events=[
                {"id": "x", "start": "2026-10-05T09:00", "end": "2026-10-05T10:00"}]),
            "entry ends before it starts": lambda d: d["calendars"]["ana"].update(events=[
                {"id": "x", "start": "2026-10-05T10:00+00:00", "end": "2026-10-05T09:00+00:00"}]),
        }
        for name, edit in cases.items():
            with self.subTest(name):
                self.assertIsNone(C.recognize(broken(edit)))
                with self.assertRaises(ValueError):
                    C.load(broken(edit))
        self.assertIsNone(C.recognize(self.root / "does-not-exist"))
        empty = self.root / "empty"
        empty.mkdir()
        self.assertIsNone(C.recognize(empty))

    def test_from_schedule_makes_a_workspace_with_the_same_valid_starts(self):
        instance = {"duration_minutes": 30, "granularity_minutes": 30,
                    "window": {"start": "2026-10-05T09:00+00:00", "end": "2026-10-05T17:00+00:00"},
                    "participants": [
                        {"id": "Mason", "utc_offset": "+00:00", "required": True,
                         "work_hours": [{"days": ["Mon"], "start": "09:00", "end": "17:00"}],
                         "busy": [{"start": "2026-10-05T09:30+00:00", "end": "2026-10-05T10:30+00:00"}]},
                        {"id": "Bruce", "utc_offset": "+00:00", "required": True, "busy": [],
                         "work_hours": [{"days": ["Mon"], "start": "09:00", "end": "17:00"}]},
                        {"id": "Cy", "utc_offset": "+00:00", "required": False, "busy": [],
                         "work_hours": []}],
                    "rooms": [{"id": "r1", "capacity": 2, "features": ["video"], "busy": []}],
                    "constraints": [{"type": "buffer_minutes", "participant": "Mason", "minutes": 30},
                                    {"type": "buffer_minutes", "participant": "Bruce", "minutes": 30},
                                    {"type": "room_feature", "feature": "video"}],
                    "preference": "earliest"}
        workspace = self.root / "converted"
        C.build_workspace(workspace, **C.from_schedule(instance, title="Planning"))
        converted = C.recognize(workspace)
        self.assertIsNotNone(converted)
        self.assertEqual(R.slots(R.model(converted["schedule"])), R.slots(R.model(instance)))
        self.assertEqual(converted["request"]["optional"], ["Cy"])
        self.assertEqual({r["type"] for r in converted["policy"]["rules"]}, {"buffer_minutes", "room_feature"})
        for bad in ({"type": "avoid_day", "participant": "Mason", "day": "2026-10-05"},
                    {"type": "not_before", "participant": "Mason", "time": "10:00"}):
            with self.assertRaises(ValueError):
                C.from_schedule({**instance, "constraints": [bad]})
        with self.assertRaises(ValueError):
            C.from_schedule({**instance, "constraints": [instance["constraints"][0]]})


if __name__ == "__main__":
    unittest.main()
