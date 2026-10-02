"""The booking-rules skill: package layout, the partial helper, its stated gaps, and the harmful variant."""

import importlib.util
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

BB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BB))

from metabench.domains import calendar as C  # noqa: E402
from metabench.domains import calendar_outputs as O  # noqa: E402
from metabench.members import llm  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures" / "calendar"
PLUGIN = BB / "meta-tasks" / "calendar-skill" / "subject" / "booking-rules"
SKILL = PLUGIN / "skills" / "booking-rules"
RESULT = "result.json"


def load_helper(script, name):
    spec = importlib.util.spec_from_file_location(name, script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HELPER = load_helper(SKILL / "scripts" / "free_slots.py", "calendar_skill_free_slots")


class SkillCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def workspace(self, name):
        data = json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))
        root = self.root / f"ws-{name}-{len(list(self.root.iterdir()))}"
        C.build_workspace(root, request=data["request"], policy=data["policy"], calendars=data["calendars"], rooms=data.get("rooms"))
        return root, C.recognize(root)

    def first_slot_label(self, helper, name):
        """The check label of booking the helper's first suggestion, and that suggestion."""
        root, instance = self.workspace(name)
        slot = helper.compute(root)["slots"][0]
        room = (slot.get("rooms") or [None])[0]
        files = O.booking(instance, helper.minute(slot["start"]), room)
        return C.check(instance, files)["label"], slot


class PackageLayout(unittest.TestCase):
    def test_the_plugin_manifest_is_native_and_unversioned(self):
        manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["name"], "booking-rules")
        self.assertEqual(manifest["skills"], "./skills/")
        self.assertNotIn("version", manifest)
        self.assertTrue((PLUGIN / "skills" / "booking-rules" / "SKILL.md").is_file())
        self.assertTrue((PLUGIN / "README.md").is_file())

    def test_nothing_in_the_benchmark_looks_like_a_fixture_package_or_a_case(self):
        self.assertEqual([p for p in BB.rglob("plugin.json") if not p.parent.name.startswith(".")], [])
        self.assertEqual(list(BB.rglob("case.json")), [])

    def test_skill_frontmatter_reads_like_a_team_skill(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = text.split("---", 2)[1]
        self.assertRegex(frontmatter, r"(?m)^name: booking-rules$")
        description = re.search(r"(?m)^description: (.+)$", frontmatter).group(1)
        self.assertIn("meeting", description)
        self.assertNotIn("disable-model-invocation", frontmatter)
        self.assertLess(len(text.splitlines()), 80)

    def test_skill_states_what_it_covers_and_what_it_does_not(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        covered, _, gaps = text.partition("## Not covered")
        for rule in ("work hours", "Buffers", "granularity grid", "Optional invitees"):
            self.assertIn(rule, covered)
        self.assertIn("Room features", gaps)
        self.assertIn("Focus-block exceptions", gaps)
        self.assertIn("scripts/free_slots.py", text)
        self.assertIn("Room features and the urgent-request exception", HELPER.NOTE)

    def test_hiding_the_skill_keeps_it_loadable(self):
        hidden = llm.hide_description((SKILL / "SKILL.md").read_text(encoding="utf-8"))
        self.assertIn(llm.HIDDEN_DESCRIPTION, hidden)
        self.assertNotIn("Book a meeting", hidden)
        self.assertIn("## Not covered", hidden)


class Helper(SkillCase):
    def run_cli(self, root, *args):
        return subprocess.run([sys.executable, str(SKILL / "scripts" / "free_slots.py"), "--workspace", str(root), *args],
                              capture_output=True, text=True, timeout=30)

    def test_cli_lists_slots_earliest_first_or_latest_first(self):
        root, _ = self.workspace("buffer")
        done = self.run_cli(root, "--limit", "3")
        self.assertEqual(done.returncode, 0, done.stderr)
        result = json.loads(done.stdout)
        self.assertEqual([s["start"] for s in result["slots"]], ["2026-10-05T11:45+00:00", "2026-10-05T14:15+00:00", "2026-10-05T14:30+00:00"])
        self.assertEqual((result["total"], result["buffer_minutes"], result["attendees"]), (9, 15, ["ana", "bo"]))
        latest = json.loads(self.run_cli(root, "--latest", "--limit", "2").stdout)
        self.assertEqual([s["start"] for s in latest["slots"]], ["2026-10-05T16:00+00:00", "2026-10-05T15:45+00:00"])
        self.assertEqual(len(json.loads(self.run_cli(root, "--limit", "0").stdout)["slots"]), 9)

    def test_cli_reports_an_unreadable_workspace(self):
        done = self.run_cli(self.root / "nothing")
        self.assertEqual(done.returncode, 2)
        self.assertIn("cannot read the workspace", done.stderr)
        self.assertEqual(done.stdout, "")

    def test_rooms_are_listed_by_availability_and_capacity(self):
        root, _ = self.workspace("room_busy")
        slots = HELPER.compute(root)["slots"]
        self.assertEqual([(s["start"], s["rooms"]) for s in slots[:3]], [
            ("2026-10-05T10:00+00:00", ["birch"]), ("2026-10-05T10:30+00:00", ["birch"]), ("2026-10-05T11:00+00:00", ["birch", "cedar"])])

    def test_the_helper_agrees_with_the_oracle_on_the_rules_it_covers(self):
        for name in ("buffer", "focus_normal", "room_busy", "offsets", "optional", "latest_room", "any", "room_small_group"):
            with self.subTest(name):
                label, slot = self.first_slot_label(HELPER, name)
                self.assertIn(label, ("valid", "suboptimal"))
                if name != "latest_room" and name != "any":
                    self.assertEqual(label, "valid")

    def test_the_helper_reports_nothing_when_no_slot_exists(self):
        root, _ = self.workspace("infeasible")
        self.assertEqual(HELPER.compute(root)["slots"], [])

    def test_gap_room_features_are_not_checked(self):
        label, slot = self.first_slot_label(HELPER, "room_feature")
        self.assertEqual((label, slot["start"], slot["rooms"]), ("invalid", "2026-10-05T09:00+00:00", ["birch"]))

    def test_gap_urgent_requests_do_not_get_the_focus_block_exception(self):
        label, slot = self.first_slot_label(HELPER, "focus_urgent")
        self.assertEqual((label, slot["start"]), ("suboptimal", "2026-10-05T11:00+00:00"))


class HarmfulVariant(SkillCase):
    def test_the_copy_differs_only_in_the_buffer_rule(self):
        harmful = C.harmful_skill(PLUGIN, self.root / "harmful")
        before = {p.relative_to(PLUGIN).as_posix() for p in PLUGIN.rglob("*") if p.is_file() and "__pycache__" not in p.parts}
        self.assertEqual({p.relative_to(harmful).as_posix() for p in harmful.rglob("*") if p.is_file()}, before)
        changed = {}
        for rel in before:
            a = (PLUGIN / rel).read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()
            b = (harmful / rel).read_text(encoding="utf-8").replace("\r\n", "\n").splitlines()
            if a != b:
                changed[rel] = sum(x != y for x, y in zip(a, b)) + abs(len(a) - len(b))
        self.assertEqual(changed, {"skills/booking-rules/SKILL.md": 1, "skills/booking-rules/scripts/free_slots.py": 3})
        self.assertIn("slack, not a gap", (harmful / "skills/booking-rules/SKILL.md").read_text(encoding="utf-8"))

    def test_following_the_harmful_helper_breaks_the_buffer(self):
        harmful = C.harmful_skill(PLUGIN, self.root / "harmful")
        helper = load_helper(harmful / "skills" / "booking-rules" / "scripts" / "free_slots.py", "calendar_skill_harmful_slots")
        label, slot = self.first_slot_label(helper, "buffer")
        self.assertEqual((label, slot["start"]), ("invalid", "2026-10-05T09:45+00:00"))
        self.assertEqual(self.first_slot_label(HELPER, "buffer")[0], "valid")
        root, _ = self.workspace("focus_normal")
        self.assertEqual(helper.compute(root)["slots"], HELPER.compute(root)["slots"])

    def test_the_destination_must_be_new_and_the_skill_must_still_contain_the_rule(self):
        harmful = C.harmful_skill(PLUGIN, self.root / "harmful")
        with self.assertRaises(ValueError):
            C.harmful_skill(PLUGIN, harmful)
        edited = self.root / "edited"
        edited.mkdir()
        shutil.copytree(PLUGIN, edited / "plugin")
        skill = edited / "plugin" / "skills" / "booking-rules" / "SKILL.md"
        skill.write_text(skill.read_text(encoding="utf-8").replace("is a gap", "is a margin"), encoding="utf-8")
        with self.assertRaises(ValueError):
            C.harmful_skill(edited / "plugin", edited / "out")
        self.assertFalse((edited / "out").exists())


if __name__ == "__main__":
    unittest.main()
