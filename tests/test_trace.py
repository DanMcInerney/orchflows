"""Session trace extractor: shape, drift-tolerance, and Mermaid oracles."""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests._repo_root import ROOT
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


class TestTraceHarvestsSinkPaths(unittest.TestCase):
    """Item 05 criterion 4. `runs_touched` is the join key between a trace
    and run state, so it has to survive the move: the sink is where every
    writer lands now, and a trace may cover a session that predates the
    migration, whose paths are the repository's."""

    SINK = "/Users/x/.orchflows/state"
    RUN = "20260814T124222Z-centralize-state"

    def harvest(self, tmp, *paths):
        main = Path(tmp) / "session.jsonl"
        main.write_text(
            json.dumps({
                "type": "assistant",
                "timestamp": "2026-01-01T00:00:00Z",
                "message": {"content": [
                    {"type": "tool_use", "id": "t%d" % i, "name": "Read",
                     "input": {"file_path": path}}
                    for i, path in enumerate(paths)
                ]},
            }),
            encoding="utf-8",
        )
        return trace.extract_claude(main)["runs_touched"]

    def test_a_sink_path_yields_the_run_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                [self.RUN],
                self.harvest(
                    tmp,
                    "{0}/runs/{1}/worklog.md".format(self.SINK, self.RUN),
                    "{0}/tickets/{1}/05-readers-follow-sink.md".format(
                        self.SINK, self.RUN
                    ),
                ),
            )

    def test_a_windows_sink_path_yields_the_run_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                [self.RUN],
                self.harvest(
                    tmp,
                    "C:\\Users\\x\\.orchflows\\state\\runs\\{0}\\run.json".format(
                        self.RUN
                    ),
                ),
            )

    def test_a_legacy_repository_path_still_yields_the_run_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                [self.RUN],
                self.harvest(tmp, "/repo/.orch/runs/{0}/spec.md".format(self.RUN)),
            )

    def test_both_shapes_in_one_transcript_yield_one_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(
                [self.RUN],
                self.harvest(
                    tmp,
                    "/repo/.orch/tickets/{0}/01.md".format(self.RUN),
                    "{0}/tickets/{1}/01.md".format(self.SINK, self.RUN),
                    "{0}/runs/{1}/worklog.md".format(self.SINK, self.RUN),
                ),
            )

    def test_the_sink_branch_never_swallows_the_repository_branch(self):
        """`.orch` is a string prefix of `.orchflows`; the separator after
        the root is what keeps the two apart, and a path under one is never
        read as a path under the other."""

        self.assertIsNone(trace.RUN_ID_RE.search("/repo/.orchestrator/runs/R1/x.md"))
        self.assertIsNone(trace.RUN_ID_RE.search("/x/.orchflows/runs/R1/x.md"))
        self.assertIsNone(trace.RUN_ID_RE.search("/x/.orchflows/state/R1/x.md"))
        for path in ("/x/.orchflows/state/runs/R1/x.md", "/repo/.orch/runs/R1/x.md"):
            match = trace.RUN_ID_RE.search(path)
            self.assertIsNotNone(match, path)
            self.assertEqual("R1", match.group(1), path)


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

    def test_a_transcript_that_cannot_be_read_is_not_full_confidence(self):
        # `_finalize` divides clean by total and reads a zero total as 1.0.
        # A file present and unreadable produces exactly that zero, with a
        # `cannot read file` parse error beside it -- and 1.0 there claims
        # full trust in data nothing was read from, the same false
        # confidence `extract_claude` already refuses for a missing file.
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "main.jsonl").write_text("{}\n", encoding="utf-8")

            with mock.patch.object(Path, "read_text", side_effect=OSError("gone")):
                result = trace.extract_claude(tmp)

            self.assertEqual(0.0, result["schema_confidence"])
            self.assertEqual(1, len(result["parse_errors"]))
            self.assertIn("cannot read file", result["parse_errors"][0]["error"])

    def test_an_empty_transcript_is_still_full_confidence(self):
        # The other zero total: nothing to read is not the same as nothing
        # read, and the file that is there and empty has nothing to distrust.
        # (`TestClaudeBoundaryInputs` asserts the same from the page's side;
        # this pins the two zeros apart at the seam that divides them.)
        self.assertEqual(1.0, trace._finalize("h", "s", [], 0, 0, [])["schema_confidence"])
        self.assertEqual(
            0.0,
            trace._finalize("h", "s", [], 0, 0, [{"line": None, "error": "cannot read file: x"}])[
                "schema_confidence"
            ],
        )

    def test_oversized_malformed_line_is_a_parse_error_not_a_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            garbage = "{" + ("x" * (2 * 1024 * 1024))
            (tmp / "main.jsonl").write_text(garbage, encoding="utf-8")
            result = trace.extract_claude(tmp)
            self.assertEqual(1, len(result["parse_errors"]))
            self.assertEqual([], result["events"])
            self.assertEqual(0.0, result["schema_confidence"])



if __name__ == "__main__":
    unittest.main()
