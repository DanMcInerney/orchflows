"""Session trace extractor: shape, drift-tolerance, mining, and Mermaid oracles."""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import scripts.trace as trace  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
TRACE_PY = ROOT / "scripts" / "trace.py"

MERMAID_NODE_RE = re.compile(r'^    n\d+\["[^"]*"\]$')
MERMAID_EDGE_RE = re.compile(r"^    n\d+ --> n\d+$")


def run_cli(args):
    result = subprocess.run(
        [sys.executable, str(TRACE_PY), *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    return result


def assert_valid_mermaid(text: str):
    lines = text.rstrip("\n").split("\n")
    assert lines[0] == "flowchart TD", lines[0]
    for line in lines[1:]:
        if MERMAID_NODE_RE.match(line) or MERMAID_EDGE_RE.match(line):
            continue
        raise AssertionError(f"line does not parse as a Mermaid node or edge: {line!r}")


class TestClaudeAdapter(unittest.TestCase):
    def test_clean_fixture_shape_and_fields(self):
        result = trace.extract_claude(FIXTURES / "claude" / "clean")

        self.assertEqual("claude-code", result["host"])
        self.assertEqual("redacted-session-aaaa1111", result["session_id"])
        self.assertEqual(1.0, result["schema_confidence"])
        self.assertEqual([], result["parse_errors"])

        events = result["events"]
        types = [ev["type"] for ev in events]
        self.assertEqual(
            ["request", "narration", "skill_invocation", "tool_call", "subagent",
             "request", "tool_call", "tool_call", "narration", "narration"],
            types,
        )
        self.assertEqual("REDACTED user request text", events[0]["text"])
        self.assertEqual("REDACTED reasoning text", events[1]["text"])

        skill_ev = events[2]
        self.assertEqual("redacted-skill-name", skill_ev["name"])
        self.assertEqual(42, skill_ev["tokens"])

        parent_tool_call = events[3]
        self.assertEqual("redacted-list-command", parent_tool_call["command"])
        self.assertEqual(0, parent_tool_call["exit"])
        self.assertEqual(1000, parent_tool_call["duration_ms"])
        self.assertEqual(14, parent_tool_call["tokens"])

        subagent_ev = events[4]
        self.assertEqual("worker-a", subagent_ev["agent_type"])
        self.assertEqual("unknown", subagent_ev["model"])
        self.assertEqual("unknown", subagent_ev["effort"])

        child_failing_call = events[6]
        self.assertEqual("redacted-failing-command", child_failing_call["command"])
        self.assertEqual(1, child_failing_call["exit"])

        child_fallback_call = events[7]
        self.assertEqual("WebSearch", child_fallback_call["command"])
        self.assertEqual(0, child_fallback_call["exit"])

    def test_malformed_fixture_yields_partial_trace(self):
        result = trace.extract_claude(FIXTURES / "claude" / "malformed" / "main.jsonl")

        self.assertEqual(0.4, result["schema_confidence"])
        self.assertEqual(3, len(result["parse_errors"]))
        self.assertEqual(["request"], [ev["type"] for ev in result["events"]])

    def test_cli_exits_zero_on_malformed_input(self):
        result = run_cli(["--claude", str(FIXTURES / "claude" / "malformed" / "main.jsonl")])
        self.assertEqual(0, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual(3, len(payload["parse_errors"]))


class TestCodexAdapter(unittest.TestCase):
    def test_clean_fixture_shape_and_fields(self):
        result = trace.extract_codex(FIXTURES / "codex" / "clean")

        self.assertEqual("codex", result["host"])
        self.assertEqual("redacted-root-thread", result["session_id"])
        self.assertEqual(1.0, result["schema_confidence"])
        self.assertEqual([], result["parse_errors"])

        types = [ev["type"] for ev in result["events"]]
        self.assertEqual(["request", "tool_call", "tool_call", "subagent", "tool_call", "narration"], types)

        shell_call = result["events"][1]
        self.assertEqual("redacted-list-command", shell_call["command"])
        self.assertEqual(0, shell_call["exit"])
        self.assertEqual(1000, shell_call["duration_ms"])

        exec_call = result["events"][2]
        self.assertEqual("redacted-failing-command", exec_call["command"])
        self.assertEqual(1, exec_call["exit"])

        subagent_ev = result["events"][3]
        self.assertEqual("REDACTED-Nickname", subagent_ev["agent_type"])
        self.assertEqual("redacted-model-child", subagent_ev["model"])
        self.assertEqual("high", subagent_ev["effort"])
        self.assertEqual("redacted-root-thread", subagent_ev["parent"])
        self.assertEqual(1, subagent_ev["depth"])

    def test_boilerplate_user_message_is_not_a_request(self):
        result = trace.extract_codex(FIXTURES / "codex" / "clean")
        requests = [ev for ev in result["events"] if ev["type"] == "request"]
        self.assertEqual(1, len(requests))

    def test_malformed_fixture_yields_partial_trace(self):
        result = trace.extract_codex(FIXTURES / "codex" / "malformed" / "root.jsonl")

        self.assertEqual(0.4, result["schema_confidence"])
        self.assertEqual(3, len(result["parse_errors"]))
        self.assertEqual([], result["events"])

    def test_cli_exits_zero_on_malformed_input(self):
        result = run_cli(["--codex", str(FIXTURES / "codex" / "malformed" / "root.jsonl")])
        self.assertEqual(0, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual(3, len(payload["parse_errors"]))


class TestMermaid(unittest.TestCase):
    def test_renders_valid_mermaid_for_fixture_corpus(self):
        traces = [
            trace.extract_claude(FIXTURES / "claude" / "clean"),
            trace.extract_claude(FIXTURES / "claude" / "malformed" / "main.jsonl"),
            trace.extract_codex(FIXTURES / "codex" / "clean"),
            trace.extract_codex(FIXTURES / "codex" / "malformed" / "root.jsonl"),
        ]
        for t in traces:
            assert_valid_mermaid(trace.render_mermaid(t))

    def test_cli_mermaid_mode(self):
        result = run_cli(["--claude", str(FIXTURES / "claude" / "clean"), "--mermaid"])
        self.assertEqual(0, result.returncode)
        assert_valid_mermaid(result.stdout)


class TestTraceV2(unittest.TestCase):
    def _extract_lines(self, tmp: Path, lines):
        main = Path(tmp) / "session.jsonl"
        main.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
        return trace.extract_claude(main)

    def test_claude_request_text_and_narration(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._extract_lines(tmp, [
                {"type": "user", "timestamp": "2026-01-01T00:00:00Z",
                 "message": {"content": "please fix the login bug"}},
                {"type": "assistant", "timestamp": "2026-01-01T00:00:01Z",
                 "message": {"content": [
                     {"type": "text", "text": "I'm going to use the orch-fix skill and decompose this."},
                 ]}},
            ])
            types = [e["type"] for e in result["events"]]
            self.assertEqual(["request", "narration"], types)
            self.assertEqual("please fix the login bug", result["events"][0]["text"])
            self.assertIn("orch-fix", result["events"][1]["text"])

    def test_system_reminder_text_is_never_a_request(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._extract_lines(tmp, [
                {"type": "user", "timestamp": "2026-01-01T00:00:00Z",
                 "message": {"content": [
                     {"type": "tool_result", "tool_use_id": "t1", "content": "ok"},
                     {"type": "text", "text": "<system-reminder>Run tests before committing.</system-reminder>"},
                 ]}},
                {"type": "user", "timestamp": "2026-01-01T00:00:01Z",
                 "message": {"content": [
                     {"type": "text", "text": "<system-reminder>standalone reminder turn</system-reminder>"},
                 ]}},
                {"type": "user", "timestamp": "2026-01-01T00:00:02Z",
                 "message": {"content": [
                     {"type": "text", "text": "a real follow-up question"},
                 ]}},
            ])
            requests = [e for e in result["events"] if e["type"] == "request"]
            self.assertEqual(1, len(requests))
            self.assertEqual("a real follow-up question", requests[0]["text"])

    def test_malformed_runs_touched_does_not_poison_mining(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bad = tmp / "bad.json"
            bad.write_text(json.dumps({
                "host": "claude-code", "session_id": "b", "schema_confidence": 1.0,
                "runs_touched": 12345,
                "events": [
                    {"type": "tool_call", "command": "pytest", "exit": 1, "ts": "2026-01-01T00:00:00Z"},
                    {"type": "tool_call", "command": "pytest", "exit": 1, "ts": "2026-01-01T00:01:00Z"},
                ],
                "parse_errors": [],
            }), encoding="utf-8")
            run_state = tmp / "repo"
            spec_dir = run_state / ".orch" / "runs" / "runa"
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec-deliver.md").write_text(
                "routing: pattern `deliver`, pack `orch-content-pack`\n", encoding="utf-8"
            )
            findings = trace.mine_observations([bad], run_state)
            failures = [f for f in findings if f["category"] == "tool-failure"]
            self.assertEqual(1, len(failures))

    def test_is_error_result_without_exit_text_is_a_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            lines = []
            for i, tid in enumerate(("t1", "t2")):
                lines.append({"type": "assistant", "timestamp": f"2026-01-01T00:0{i}:00Z",
                              "message": {"content": [
                                  {"type": "tool_use", "id": tid, "name": "Read",
                                   "input": {"file_path": "C:\\missing\\file.md"}},
                              ]}})
                lines.append({"type": "user", "timestamp": f"2026-01-01T00:0{i}:01Z",
                              "message": {"content": [
                                  {"type": "tool_result", "tool_use_id": tid,
                                   "is_error": True, "content": "File does not exist."},
                              ]}})
            result = self._extract_lines(tmp, lines)
            calls = [e for e in result["events"] if e["type"] == "tool_call"]
            self.assertEqual([1, 1], [e["exit"] for e in calls])
            trace_path = Path(tmp) / "t.json"
            trace_path.write_text(json.dumps(result), encoding="utf-8")
            findings = trace.mine_observations([trace_path], None)
            failures = [f for f in findings if f["category"] == "tool-failure"]
            self.assertEqual(1, len(failures))

    def test_thinking_blocks_are_not_narration(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._extract_lines(tmp, [
                {"type": "assistant", "timestamp": "2026-01-01T00:00:01Z",
                 "message": {"content": [
                     {"type": "thinking", "thinking": "private reasoning"},
                 ]}},
            ])
            self.assertEqual([], [e for e in result["events"] if e["type"] == "narration"])

    def test_text_clip_sets_truncated_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            long_text = "x" * (trace.TEXT_CLIP + 500)
            result = self._extract_lines(tmp, [
                {"type": "user", "timestamp": "2026-01-01T00:00:00Z",
                 "message": {"content": long_text}},
            ])
            ev = result["events"][0]
            self.assertEqual(trace.TEXT_CLIP, len(ev["text"]))
            self.assertTrue(ev["truncated"])

    def test_runs_touched_harvested_from_tool_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self._extract_lines(tmp, [
                {"type": "assistant", "timestamp": "2026-01-01T00:00:00Z",
                 "message": {"content": [
                     {"type": "tool_use", "id": "t1", "name": "Read",
                      "input": {"file_path": "C:\\repo\\.orch\\runs\\20260101T0000Z-x\\spec-deliver.md"}},
                     {"type": "tool_use", "id": "t2", "name": "Read",
                      "input": {"file_path": "/repo/.orch/tickets/20260101T0000Z-x/T1.md"}},
                 ]}},
            ])
            self.assertEqual(["20260101T0000Z-x"], result["runs_touched"])

    def test_codex_assistant_narration(self):
        with tempfile.TemporaryDirectory() as tmp:
            rollout = Path(tmp) / "root.jsonl"
            lines = [
                {"type": "session_meta", "timestamp": "2026-01-01T00:00:00Z",
                 "payload": {"id": "thread-1", "source": {}}},
                {"type": "response_item", "timestamp": "2026-01-01T00:00:01Z",
                 "payload": {"type": "message", "role": "assistant", "content": [
                     {"type": "output_text", "text": "Decomposing under the code pack now."},
                 ]}},
            ]
            rollout.write_text("\n".join(json.dumps(l) for l in lines), encoding="utf-8")
            result = trace.extract_codex(rollout)
            narrations = [e for e in result["events"] if e["type"] == "narration"]
            self.assertEqual(1, len(narrations))
            self.assertIn("code pack", narrations[0]["text"])

    def test_misrouting_scoped_by_runs_touched(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_state = tmp / "repo"
            for run, pack in (("runa", "orch-content-pack"), ("runb", "orch-code-pack")):
                spec_dir = run_state / ".orch" / "runs" / run
                spec_dir.mkdir(parents=True)
                (spec_dir / "spec-deliver.md").write_text(
                    f"routing: pattern `deliver`, pack `{pack}`\n", encoding="utf-8"
                )
            code_events = [{"type": "tool_call", "command": "Write:/repo/module.py", "exit": 0, "ts": "2026-01-01T00:00:00Z"}]
            mismatch = tmp / "mismatch.json"
            mismatch.write_text(json.dumps({
                "host": "claude-code", "session_id": "m", "schema_confidence": 1.0,
                "runs_touched": ["runa"], "events": code_events, "parse_errors": [],
            }), encoding="utf-8")
            match = tmp / "match.json"
            match.write_text(json.dumps({
                "host": "claude-code", "session_id": "n", "schema_confidence": 1.0,
                "runs_touched": ["runb"], "events": code_events, "parse_errors": [],
            }), encoding="utf-8")
            findings = trace.mine_observations([mismatch, match], run_state)
            misrouting = [f for f in findings if f["category"] == "misrouting"]
            self.assertEqual(1, len(misrouting))
            self.assertIn("runa", misrouting[0]["observed"])
            self.assertIn("orch-content-pack", misrouting[0]["observed"])

    def test_bom_prefixed_trace_input_is_readable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bom.json"
            payload = {"host": "claude-code", "session_id": "b", "schema_confidence": 1.0,
                       "events": [], "parse_errors": []}
            path.write_bytes(b"\xef\xbb\xbf" + json.dumps(payload).encode("utf-8"))
            findings = trace.mine_observations([path], None)
            self.assertEqual([], [f for f in findings if f["source"] == "miner"])


class TestClaudeBoundaryInputs(unittest.TestCase):
    """Boundary hardening: empty file, BOM-only, oversized line, an entirely
    empty transcript directory, and malformed JSON mixed with clean lines."""

    def test_directory_with_no_transcript_files_yields_empty_trace_shape(self):
        # No main.jsonl and no subagents/ at all: extract_claude must degrade
        # to the same honest _empty_trace shape extract_codex already uses
        # for "no rollout file(s) found" -- schema_confidence 0.0, no
        # runs_touched key, not a false-confident schema_confidence: 1.0.
        with tempfile.TemporaryDirectory() as tmp:
            result = trace.extract_claude(Path(tmp))
            self.assertEqual(0.0, result["schema_confidence"])
            self.assertEqual([], result["events"])
            self.assertNotIn("runs_touched", result)
            self.assertEqual(1, len(result["parse_errors"]))
            self.assertIsNone(result["parse_errors"][0]["line"])

    def test_empty_main_jsonl_degrades_gracefully(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "main.jsonl").write_text("", encoding="utf-8")
            result = trace.extract_claude(tmp)
            self.assertEqual([], result["events"])
            self.assertEqual([], result["parse_errors"])
            self.assertEqual(1.0, result["schema_confidence"])

    def test_bom_only_main_jsonl_is_not_a_parse_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "main.jsonl").write_bytes(b"\xef\xbb\xbf")
            result = trace.extract_claude(tmp)
            self.assertEqual([], result["events"])
            self.assertEqual([], result["parse_errors"])

    def test_malformed_json_mixed_with_clean_lines_counts_parse_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            lines = [
                json.dumps({"type": "user", "timestamp": "2026-01-01T00:00:00Z",
                            "message": {"content": "clean request"}}),
                "{not valid json",
                json.dumps({"type": "assistant", "timestamp": "2026-01-01T00:00:01Z",
                            "message": {"content": [{"type": "text", "text": "clean narration"}]}}),
                json.dumps(["not", "an", "object"]),
                json.dumps({"missing": "type key"}),
            ]
            (tmp / "main.jsonl").write_text("\n".join(lines), encoding="utf-8")
            result = trace.extract_claude(tmp)
            self.assertEqual(3, len(result["parse_errors"]))
            self.assertEqual(["request", "narration"], [e["type"] for e in result["events"]])
            self.assertEqual(0.4, result["schema_confidence"])  # 2 clean / 5 total

    def test_oversized_single_line_does_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            huge_text = "x" * (3 * 1024 * 1024)  # 3 MB single field
            line = json.dumps({"type": "user", "timestamp": "2026-01-01T00:00:00Z",
                                "message": {"content": huge_text}})
            (tmp / "main.jsonl").write_text(line, encoding="utf-8")
            result = trace.extract_claude(tmp)
            self.assertEqual([], result["parse_errors"])
            self.assertEqual(1, len(result["events"]))
            ev = result["events"][0]
            self.assertEqual(trace.TEXT_CLIP, len(ev["text"]))
            self.assertTrue(ev["truncated"])

    def test_oversized_malformed_line_is_a_parse_error_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            garbage = "{" + ("x" * (2 * 1024 * 1024))
            (tmp / "main.jsonl").write_text(garbage, encoding="utf-8")
            result = trace.extract_claude(tmp)
            self.assertEqual(1, len(result["parse_errors"]))
            self.assertEqual([], result["events"])
            self.assertEqual(0.0, result["schema_confidence"])


class TestObservations(unittest.TestCase):
    def _write_trace(self, tmp: Path, name: str, events, host="claude-code"):
        path = tmp / name
        path.write_text(json.dumps({
            "host": host,
            "session_id": name,
            "schema_confidence": 1.0,
            "events": events,
            "parse_errors": [],
        }), encoding="utf-8")
        return path

    def test_repeated_tool_failure_across_two_traces(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            a = self._write_trace(tmp, "a.json", [
                {"type": "tool_call", "command": "pytest", "exit": 1, "ts": "2026-01-01T00:00:00Z"},
            ])
            b = self._write_trace(tmp, "b.json", [
                {"type": "tool_call", "command": "pytest", "exit": 1, "ts": "2026-01-01T00:00:00Z"},
            ])
            findings = trace.mine_observations([a, b], None)
            failures = [f for f in findings if f["category"] == "tool-failure"]
            self.assertEqual(1, len(failures))
            finding = failures[0]
            self.assertEqual("trace", finding["source"])
            self.assertIn("pytest", finding["observed"])
            self.assertIn("2 traces", finding["observed"])
            for key in ("ts", "observed", "expected", "category", "host", "source"):
                self.assertIn(key, finding)

    def test_single_trace_failure_is_not_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            a = self._write_trace(tmp, "a.json", [
                {"type": "tool_call", "command": "pytest", "exit": 1, "ts": "2026-01-01T00:00:00Z"},
            ])
            findings = trace.mine_observations([a], None)
            self.assertEqual([], [f for f in findings if f["category"] == "tool-failure"])

    def test_repeated_failure_within_one_trace_is_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            a = self._write_trace(tmp, "a.json", [
                {"type": "tool_call", "command": "pytest", "exit": 1, "ts": "2026-01-01T00:00:00Z"},
                {"type": "tool_call", "command": "pytest", "exit": 1, "ts": "2026-01-01T00:01:00Z"},
            ])
            findings = trace.mine_observations([a], None)
            failures = [f for f in findings if f["category"] == "tool-failure"]
            self.assertEqual(1, len(failures))
            self.assertIn("2 times across 1 trace", failures[0]["observed"])
            self.assertEqual("trace", failures[0]["source"])

    def test_unreadable_trace_input_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "no-such-trace.json"
            findings = trace.mine_observations([missing], None)
            self.assertEqual(1, len(findings))
            self.assertEqual("miner", findings[0]["source"])
            self.assertIn("unreadable", findings[0]["observed"])
            for key in ("ts", "observed", "expected", "category", "host", "source"):
                self.assertIn(key, findings[0])

    def test_misrouting_pack_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_state = tmp / "repo"
            spec_dir = run_state / ".orch" / "runs" / "testrun"
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec-deliver.md").write_text(
                "routing: pattern `deliver`, pack `orch-content-pack`\n", encoding="utf-8"
            )
            trace_path = self._write_trace(tmp, "code-trace.json", [
                {"type": "tool_call", "command": "Write:/repo/module.py", "exit": 0, "ts": "2026-01-01T00:00:00Z"},
            ])
            findings = trace.mine_observations([trace_path], run_state)
            misrouting = [f for f in findings if f["category"] == "misrouting"]
            self.assertEqual(1, len(misrouting))
            self.assertIn("orch-content-pack", misrouting[0]["observed"])
            self.assertIn("code", misrouting[0]["observed"])

    def test_misrouting_matching_kind_is_not_a_finding(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_state = tmp / "repo"
            spec_dir = run_state / ".orch" / "runs" / "testrun"
            spec_dir.mkdir(parents=True)
            (spec_dir / "spec-deliver.md").write_text(
                "routing: pattern `deliver`, pack `orch-content-pack`\n", encoding="utf-8"
            )
            trace_path = self._write_trace(tmp, "content-trace.json", [
                {"type": "tool_call", "command": "Write:/repo/README.md", "exit": 0, "ts": "2026-01-01T00:00:00Z"},
            ])
            findings = trace.mine_observations([trace_path], run_state)
            self.assertEqual([], [f for f in findings if f["category"] == "misrouting"])

    def _run_state_with(self, tmp: Path, run: str, pack: str) -> Path:
        run_state = tmp / "repo"
        spec_dir = run_state / ".orch" / "runs" / run
        spec_dir.mkdir(parents=True)
        (spec_dir / "spec-deliver.md").write_text(
            f"routing: pattern `deliver`, pack `{pack}`\n", encoding="utf-8"
        )
        return run_state

    def test_design_run_with_markup_and_ticket_write_is_not_misrouted(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_state = self._run_state_with(tmp, "designrun", "orch-design-pack")
            a = self._write_trace(tmp, "d.json", [
                {"type": "tool_call", "command": "Write:/repo/component.html", "exit": 0, "ts": "2026-01-01T00:00:00Z"},
                {"type": "tool_call", "command": "Write:/repo/styles.css", "exit": 0, "ts": "2026-01-01T00:01:00Z"},
                {"type": "tool_call", "command": "Edit:/repo/.orch/tickets/designrun/T1.md", "exit": 0, "ts": "2026-01-01T00:02:00Z"},
            ])
            findings = trace.mine_observations([a], run_state)
            self.assertEqual([], [f for f in findings if f["category"] == "misrouting"])

    def test_research_declaration_is_never_judged(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_state = self._run_state_with(tmp, "resrun", "orch-research-pack")
            a = self._write_trace(tmp, "r.json", [
                {"type": "tool_call", "command": "Read:/repo/docs/source.md", "exit": 0, "ts": "2026-01-01T00:00:00Z"},
            ])
            findings = trace.mine_observations([a], run_state)
            self.assertEqual([], [f for f in findings if f["category"] == "misrouting"])

    def test_extension_match_is_suffix_not_substring(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_state = self._run_state_with(tmp, "docrun", "orch-content-pack")
            a = self._write_trace(tmp, "s.json", [
                {"type": "tool_call", "command": "Write:/repo/notes.config", "exit": 0, "ts": "2026-01-01T00:00:00Z"},
                {"type": "tool_call", "command": "Write:/repo/guide.md", "exit": 0, "ts": "2026-01-01T00:01:00Z"},
            ])
            findings = trace.mine_observations([a], run_state)
            self.assertEqual([], [f for f in findings if f["category"] == "misrouting"])

    def test_ticket_only_writes_never_fire_misrouting(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_state = self._run_state_with(tmp, "coderun", "orch-code-pack")
            a = self._write_trace(tmp, "t.json", [
                {"type": "tool_call", "command": "Edit:/repo/.orch/tickets/coderun/T1.md", "exit": 0, "ts": "2026-01-01T00:00:00Z"},
            ])
            findings = trace.mine_observations([a], run_state)
            self.assertEqual([], [f for f in findings if f["category"] == "misrouting"])

    def test_misrouting_ambiguous_declared_packs_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            run_state = tmp / "repo"
            for run, pack in (("runa", "orch-content-pack"), ("runb", "orch-code-pack")):
                spec_dir = run_state / ".orch" / "runs" / run
                spec_dir.mkdir(parents=True)
                (spec_dir / "spec-deliver.md").write_text(
                    f"routing: pattern `deliver`, pack `{pack}`\n", encoding="utf-8"
                )
            trace_path = self._write_trace(tmp, "code-trace.json", [
                {"type": "tool_call", "command": "Write:/repo/module.py", "exit": 0, "ts": "2026-01-01T00:00:00Z"},
            ])
            findings = trace.mine_observations([trace_path], run_state)
            self.assertEqual([], [f for f in findings if f["category"] == "misrouting"])

    def test_machinery_ratio_exceeds_threshold(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            events = (
                [{"type": "tool_call", "command": "x", "exit": 0, "ts": "2026-01-01T00:00:00Z"} for _ in range(3)]
                + [{"type": "skill_invocation", "name": "s", "ts": "2026-01-01T00:00:00Z"}]
                + [{"type": "subagent", "agent_type": "a", "model": "m", "effort": "e", "depth": 2,
                    "ts": "2026-01-01T00:00:00Z"}]
            )
            trace_path = self._write_trace(tmp, "ratio-trace.json", events)
            (tmp / "ratio-trace.budget.json").write_text(
                json.dumps({"expected_event_budget": 4, "threshold": 1.0}), encoding="utf-8"
            )
            findings = trace.mine_observations([trace_path], None)
            ratio_findings = [f for f in findings if f["category"] == "misrouting"]
            self.assertEqual(1, len(ratio_findings))
            self.assertIn("1.75", ratio_findings[0]["observed"])

    def test_machinery_ratio_without_budget_file_is_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            trace_path = self._write_trace(tmp, "no-budget-trace.json", [
                {"type": "tool_call", "command": "x", "exit": 0, "ts": "2026-01-01T00:00:00Z"},
            ])
            findings = trace.mine_observations([trace_path], None)
            self.assertEqual([], findings)

    def test_cli_observations_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            a = self._write_trace(tmp, "a.json", [
                {"type": "tool_call", "command": "pytest", "exit": 1, "ts": "2026-01-01T00:00:00Z"},
            ])
            b = self._write_trace(tmp, "b.json", [
                {"type": "tool_call", "command": "pytest", "exit": 1, "ts": "2026-01-01T00:00:00Z"},
            ])
            result = run_cli(["--observations", str(a), str(b)])
            self.assertEqual(0, result.returncode)
            lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
            self.assertEqual(1, len(lines))
            finding = json.loads(lines[0])
            self.assertEqual("tool-failure", finding["category"])

    def test_mining_end_to_end_over_extracted_fixture_trace(self):
        extracted = trace.extract_claude(FIXTURES / "claude" / "clean")
        with tempfile.TemporaryDirectory() as tmp:
            trace_path = Path(tmp) / "session.json"
            trace_path.write_text(json.dumps(extracted), encoding="utf-8")
            budget_path = Path(tmp) / "session.budget.json"
            budget_path.write_text(
                json.dumps({"expected_event_budget": 1, "threshold": 0.1}),
                encoding="utf-8",
            )
            findings = trace.mine_observations([trace_path], run_state=None)
        self.assertTrue(findings, "expected at least one finding from the fixture trace")
        for finding in findings:
            for key in ("ts", "observed", "expected", "category", "host", "source"):
                self.assertIn(key, finding)
            self.assertEqual("trace", finding["source"])
            self.assertEqual(extracted["host"], finding["host"])


if __name__ == "__main__":
    unittest.main()
