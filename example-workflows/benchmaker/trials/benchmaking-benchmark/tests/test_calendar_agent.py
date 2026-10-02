"""The calendar-skill subject agent and the meta-task's public files: commands, runs against a stand-in CLI, consistency."""

import contextlib
import importlib.util
import io
import json
import re
import shutil
import sys
import tempfile
import time
import unittest
from pathlib import Path

BB = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BB))

from metabench import builders  # noqa: E402
from metabench.domains import calendar as C  # noqa: E402
from metabench.domains import calendar_state as S  # noqa: E402
from metabench.domains import scheduling_naturalplan as NP  # noqa: E402

MT = BB / "meta-tasks" / "calendar-skill"
SUBJECT = MT / "subject"
FAKE = Path(__file__).parent / "fixtures" / "calendar" / "fake_claude.py"
TOOLS = "Read,Write,Edit,Bash,Glob,Grep"


class AgentCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """One copy of subject/ for the class: relative skill paths resolve in it as they do in a package."""
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.subject = Path(tmp.name) / "subject"
        shutil.copytree(SUBJECT, cls.subject, ignore=shutil.ignore_patterns("__pycache__"))
        cls.default_config = (cls.subject / "agent" / "config.json").read_text(encoding="utf-8")

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.config_dir = self.root / "claude-home"
        self.config_dir.mkdir()
        (self.config_dir / "settings.json").write_text(json.dumps({"enabledPlugins": {"helper@market": True, "other@market": False}}))
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.prompt = self.root / "prompt.md"

    def agent(self, config=None):
        """run_agent.py from the copy of subject/, with `config` as its config.json."""
        (self.subject / "agent" / "config.json").write_text(json.dumps(config) if config is not None else self.default_config,
                                                           encoding="utf-8")
        spec = importlib.util.spec_from_file_location("calendar_subject_run_agent", self.subject / "agent" / "run_agent.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.subject_dir = self.subject
        return module

    def run_main(self, module, scenario="ok", *extra, claude=None, timeout="30"):
        self.prompt.write_text(f"scenario: {scenario}\nBook the meeting in request.json.\n", encoding="utf-8")
        transcript = self.root / "transcript.jsonl"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = module.main(["--workspace", str(self.workspace), "--prompt-file", str(self.prompt), "--transcript", str(transcript),
                                "--timeout", timeout, *extra], claude=claude or [sys.executable, str(FAKE)])
        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), 1, out.getvalue())
        return code, json.loads(lines[0]), transcript


class Command(AgentCase):
    def build(self, module, config, plugins=(), **options):
        return module.build_command(config, list(plugins), ["claude"], str(self.config_dir), **options) if False else \
            module.build_command(config, list(plugins), ["claude"], str(self.config_dir))

    def test_default_config_is_haiku_low_without_skills(self):
        config = json.loads((SUBJECT / "agent" / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(config, {"model": "claude-haiku-4-5", "effort": "low", "skills": []})

    def test_without_a_skill_the_run_is_in_safe_mode(self):
        module = self.agent()
        command = self.build(module, json.loads((SUBJECT / "agent" / "config.json").read_text(encoding="utf-8")))
        self.assertEqual(command, ["claude", "-p", "--verbose", "--output-format", "stream-json", "--model", "claude-haiku-4-5",
                                   "--effort", "low", "--permission-mode", "dontAsk", "--tools", TOOLS, "--allowedTools", TOOLS,
                                   "--no-session-persistence", "--safe-mode"])

    def test_with_a_skill_the_run_loads_the_plugin_and_isolates_through_settings(self):
        module = self.agent({"model": "claude-haiku-4-5", "effort": "low", "skills": ["../booking-rules"]})
        plugins = module.skill_plugins(json.loads((module.HERE / "config.json").read_text(encoding="utf-8")))
        self.assertEqual(plugins, [(module.subject_dir / "booking-rules").resolve()])
        command = module.build_command({"model": "claude-haiku-4-5", "effort": "low", "skills": ["../booking-rules"]},
                                       plugins, ["claude"], str(self.config_dir))
        self.assertNotIn("--safe-mode", command)
        self.assertEqual(command[command.index("--plugin-dir") + 1], str(plugins[0]))
        self.assertEqual(command[command.index("--tools") + 1], TOOLS + ",Skill")
        self.assertEqual(command[command.index("--allowedTools") + 1], TOOLS + ",Skill")
        self.assertIn("--strict-mcp-config", command)
        self.assertEqual(command[command.index("--setting-sources") + 1], "user")
        settings = json.loads(command[command.index("--settings") + 1])
        self.assertEqual(settings, {"disableAllHooks": True, "syncClaudeAiSkills": False, "syncClaudeAiPlugins": False,
                                    "autoMemoryEnabled": False, "enabledPlugins": {"helper@market": False, "other@market": False}})
        for flag in ("-p", "--verbose", "--no-session-persistence"):
            self.assertIn(flag, command)

    def test_a_missing_settings_file_disables_nothing_extra(self):
        module = self.agent()
        self.assertEqual(module.isolation_settings(str(self.root / "nowhere"))["enabledPlugins"], {})

    def test_safe_mode_can_be_switched_off_to_match_a_run_with_a_skill(self):
        module = self.agent()
        command = module.build_command({"model": "m", "effort": "low", "safe_mode": False}, [], ["claude"], str(self.config_dir))
        self.assertNotIn("--safe-mode", command)
        self.assertNotIn("--plugin-dir", command)
        self.assertIn("--settings", command)
        self.assertEqual(command[command.index("--tools") + 1], TOOLS)

    def test_safe_mode_and_a_skill_cannot_be_combined(self):
        module = self.agent()
        with self.assertRaises(ValueError):
            module.build_command({"model": "m", "effort": "low", "safe_mode": True}, [Path("x")], ["claude"])

    def test_tools_can_be_replaced(self):
        module = self.agent()
        command = module.build_command({"model": "m", "effort": "low", "tools": "Read,Write"}, [], ["claude"])
        self.assertEqual(command[command.index("--tools") + 1], "Read,Write")

    def test_print_command_prints_the_command_and_prompt_and_calls_nothing(self):
        module = self.agent({"model": "claude-haiku-4-5", "effort": "low", "skills": ["../booking-rules"]})
        self.prompt.write_text("Book it.\n", encoding="utf-8")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = module.main(["--workspace", str(self.workspace), "--prompt-file", str(self.prompt), "--print-command"],
                               claude=[sys.executable, "-c", "raise SystemExit('must not run')"])
        self.assertEqual(code, 0)
        shown = json.loads(out.getvalue())
        self.assertEqual((shown["prompt"], shown["cwd"]), ("Book it.\n", str(self.workspace)))
        self.assertIn("--plugin-dir", shown["command"])
        self.assertFalse((self.workspace / "agent-ran.json").exists())

    def test_a_skill_that_is_not_a_plugin_is_an_error_before_anything_runs(self):
        module = self.agent({"model": "claude-haiku-4-5", "effort": "low", "skills": ["../nothing-here"]})
        code, line, _ = self.run_main(module)
        self.assertEqual((code, line["status"]), (1, "error"))
        self.assertIn("not a plugin directory", line["final"])
        self.assertFalse((self.workspace / "agent-ran.json").exists())


class Runs(AgentCase):
    def test_a_completed_run_reports_the_protocol_line_and_records_the_stream(self):
        module = self.agent({"model": "claude-haiku-4-5", "effort": "low", "skills": ["../booking-rules"]})
        code, line, transcript = self.run_main(module)
        self.assertEqual(code, 0)
        self.assertEqual({k: line[k] for k in ("status", "exit_code", "model", "cost_usd", "final", "turns", "skill_calls", "plugins")},
                         {"status": "completed", "exit_code": 0, "model": "claude-haiku-4-5-20251001", "cost_usd": 0.0123,
                          "final": "Booked the meeting.", "turns": 4, "skill_calls": 1, "plugins": ["booking-rules"]})
        self.assertIsInstance(line["seconds"], float)
        seen = json.loads((self.workspace / "agent-ran.json").read_text(encoding="utf-8"))
        self.assertEqual(Path(seen["cwd"]).resolve(), self.workspace.resolve())
        self.assertTrue(seen["prompt"].endswith("Book the meeting in request.json.\n"))
        self.assertIn("--plugin-dir", seen["argv"])
        events = [json.loads(row) for row in transcript.read_text(encoding="utf-8").splitlines() if row.startswith("{")]
        self.assertEqual((events[0]["event"], events[-1]["event"]), ("call", "return"))
        self.assertIn("result", [e.get("type") for e in events])
        self.assertEqual(events[0]["prompt"], seen["prompt"])

    def test_a_run_without_a_skill_uses_safe_mode(self):
        code, line, _ = self.run_main(self.agent())
        seen = json.loads((self.workspace / "agent-ran.json").read_text(encoding="utf-8"))
        self.assertEqual((code, line["status"]), (0, "completed"))
        self.assertIn("--safe-mode", seen["argv"])
        self.assertNotIn("--plugin-dir", seen["argv"])

    def test_statuses_and_exit_codes(self):
        module = self.agent()
        for scenario, status, code in (("limit", "usage-limit", 3), ("throttled", "usage-limit", 3), ("refusal", "refused", 0),
                                       ("cutoff", "cut-off", 0), ("crash", "error", 1)):
            with self.subTest(scenario):
                got, line, _ = self.run_main(module, scenario)
                self.assertEqual((line["status"], got), (status, code))
        _, crash, _ = self.run_main(module, "crash")
        self.assertIn("something broke", crash["final"])
        _, limit, _ = self.run_main(module, "limit")
        self.assertIn("session limit", limit["final"])

    def test_a_run_past_the_timeout_is_stopped(self):
        started = time.monotonic()
        code, line, transcript = self.run_main(self.agent(), "sleep", timeout="0.5")
        self.assertEqual((code, line["status"], line["exit_code"]), (2, "timeout", None))
        self.assertLess(time.monotonic() - started, 20)
        self.assertEqual(json.loads(transcript.read_text(encoding="utf-8").splitlines()[-1])["event"], "return")

    def test_a_missing_workspace_or_prompt_is_an_error(self):
        module = self.agent()
        shutil.rmtree(self.workspace)
        self.assertEqual(self.run_main(module)[1]["status"], "error")
        self.workspace.mkdir()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = module.main(["--workspace", str(self.workspace), "--prompt-file", str(self.root / "no-prompt.md")], claude=["claude"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out.getvalue())["status"], "error")

    def test_an_unstartable_cli_is_an_error(self):
        code, line, _ = self.run_main(self.agent(), claude=[str(self.root / "no-such-claude")])
        self.assertEqual((code, line["status"]), (1, "error"))
        self.assertIn("cannot start", line["final"])


class PublicFiles(unittest.TestCase):
    def test_request_fills_its_placeholders_and_names_what_a_builder_needs(self):
        text = (MT / "request.md").read_text(encoding="utf-8")
        for size in ("small", "standard"):
            filled = builders.fill_request(text, builders.budget("calendar-skill", size))
            self.assertNotRegex(filled, r"\{[A-Z_]+\}")
        for name in ("./subject/agent/", "./subject/booking-rules/", "interface.md", "interface/package.md", "conform.py",
                     "run.py full --agent", "run.py grade --input", "./material/", "no retries"):
            self.assertIn(name, text)
        self.assertNotRegex(text.lower(), r"held-out|hidden|private")

    def test_interface_examples_are_a_conforming_workspace(self):
        blocks = re.findall(r"```json\n(.*?)\n```", (MT / "interface.md").read_text(encoding="utf-8"), re.S)
        request, calendar, policy = (json.loads(b) for b in blocks[:3])
        with tempfile.TemporaryDirectory() as tmp:
            S.build_workspace(tmp, request=request, policy=policy, calendars={n: calendar for n in ("ana", "bo", "dee")},
                              rooms={"birch": {"capacity": 4, "features": ["video"], "events": []}})
            instance = C.recognize(tmp)
            self.assertIsNotNone(instance)
            self.assertEqual({r["type"] for r in policy["rules"]}, set(S.RULE_TYPES))
            self.assertEqual([c["type"] for c in instance["schedule"]["constraints"]], ["buffer_minutes", "buffer_minutes"])

    def test_interface_documents_every_rule_type_and_failure_class(self):
        text = (MT / "interface.md").read_text(encoding="utf-8")
        for needle in (*S.RULE_TYPES, "urgent_may_override", "min_attendees", "Critical failure", "Full success",
                       "Valid but not optimal", "half-open", "granularity_minutes", "event_id", "result.json"):
            self.assertIn(needle, text)

    def test_material_is_a_checked_subset_of_the_scheduling_sample(self):
        material = json.loads((MT / "material.json").read_text(encoding="utf-8"))
        scheduling = json.loads((MT.parent / "schedule-nosolver" / "material.json").read_text(encoding="utf-8"))
        self.assertEqual(material["meta_task"], "calendar-skill")
        self.assertEqual(len(material["public_records"]), 20)
        self.assertEqual(len(set(material["public_records"])), 20)
        self.assertLessEqual(set(material["public_records"]), set(scheduling["public_records"]))
        self.assertEqual(material["licence"], scheduling["licence"])
        self.assertIn("CC BY 4.0", material["attribution"])
        self.assertEqual(material["public_fields"], list(NP.KEPT_FIELDS))

    def test_fetch_material_splits_the_download_and_reuses_a_shared_copy(self):
        material = json.loads((MT / "material.json").read_text(encoding="utf-8"))
        record = {key: "x" for key in (*NP.KEPT_FIELDS, "prompt_5shot", "pred_5shot_pro")}
        records = {f"calendar_scheduling_example_{n}": dict(record) for n in range(1000)}
        records.update({i: dict(record) for i in material["public_records"]})

        def opener(payload, calls):
            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, *exc):
                    return False

                def read(self):
                    return payload

            return lambda request, timeout: calls.append(request.full_url) or Response()

        data, calls = json.dumps(records).encode("utf-8"), []
        with tempfile.TemporaryDirectory() as store:
            summary = C.fetch_material(store, opener=opener(data, calls))
            root = Path(store) / "material" / "calendar-skill"
            self.assertEqual(calls, [material["source"]["data_url"]])
            self.assertEqual(summary, {"records": len(records), "public": 20, "held_out": len(records) - 20})
            public = json.loads((root / "public" / "calendar_scheduling.json").read_text(encoding="utf-8"))
            self.assertEqual(sorted(public), sorted(material["public_records"]))
            self.assertEqual(set(public[material["public_records"][0]]), set(NP.KEPT_FIELDS))
            split = json.loads((root / "split.json").read_text(encoding="utf-8"))
            self.assertFalse(set(split["public"]) & set(split["held_out"]))
            self.assertEqual(len(split["held_out"]), len(records) - 20)
            self.assertIn("CC BY 4.0", (root / "public" / "NOTICE.md").read_text(encoding="utf-8"))
            self.assertFalse((root / "source").exists())
            shared = Path(store) / "material" / "schedule-nosolver" / "source"
            shared.mkdir(parents=True)
            (shared / "calendar_scheduling.json").write_bytes(data)
            shutil.rmtree(root)
            C.fetch_material(store, opener=lambda *a, **k: self.fail("the shared download should be reused"))
            self.assertTrue((root / "split.json").is_file())
        with tempfile.TemporaryDirectory() as store, self.assertRaises(ValueError):
            C.fetch_material(store, opener=opener(json.dumps({"calendar_scheduling_example_1": record}).encode("utf-8"), []))

    def test_dev_pool_names_only_known_members_and_behaviors(self):
        pool = json.loads((MT / "dev-pool.json").read_text(encoding="utf-8"))
        self.assertEqual(pool["label"], "exposed")
        members = pool["members"]
        for spec in members.values():
            if spec["behavior"] == "defect":
                self.assertIn(spec["defect"], C.DEFECTS)
            if spec["behavior"] == "heuristic":
                self.assertIn(spec["name"], C.HEURISTICS)
        self.assertEqual({s["defect"] for s in members.values() if s["behavior"] == "defect"}, set(C.DEFECTS))
        for pair in pool["known_pairs"] + pool["contrasts"]:
            self.assertIn(pair["higher"], members)
            self.assertIn(pair["lower"], members)
        self.assertTrue(all(c["must_resolve"] for c in pool["contrasts"]))


if __name__ == "__main__":
    unittest.main()
