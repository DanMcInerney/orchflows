"""Native history is evidence, not a replay engine. Fixtures contain no user data."""

import hashlib
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("native_logs", ROOT / "scripts/native_logs.py")
logs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logs)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def transcript(path, records):
    write(path, "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records))


def response(kind, **fields):
    return {"type": "response_item", "timestamp": "2026-09-11T12:00:00Z", "payload": {"type": kind, **fields}}


def claude(role, *blocks):
    return {"type": role, "message": {"content": list(blocks)}, "timestamp": "2026-09-11T12:00:00Z"}


class NativeHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="orchflows-native-history-")
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name).resolve()

    def index(self):
        db = sqlite3.connect(self.home / "state_5.sqlite")
        db.execute("CREATE TABLE IF NOT EXISTS threads (id TEXT, rollout_path TEXT, cwd TEXT, title TEXT, created_at INTEGER, updated_at INTEGER)")
        db.execute("CREATE TABLE IF NOT EXISTS thread_spawn_edges (parent_thread_id TEXT, child_thread_id TEXT)")
        return db

    def codex(self, identifier, records, parent=None, cwd="/tools/project", created="2026-08-01", updated="2026-09-12"):
        path = self.home / "sessions/2026/09/11" / (identifier + ".jsonl")
        transcript(path, [{"type": "session_meta", "payload": {"id": identifier}}] + records)
        with closing(self.index()) as db:
            db.execute("INSERT INTO threads VALUES (?,?,?,?,?,?)", (identifier, str(path), cwd, identifier,
                       int(logs._timestamp(created).timestamp()), int(logs._timestamp(updated).timestamp())))
            if parent:
                db.execute("INSERT INTO thread_spawn_edges VALUES (?,?)", (parent, identifier))
            db.commit()
        return path

    def claude_tree(self):
        root = self.home / "projects/project/session.jsonl"
        transcript(root, [claude("assistant", {"type": "tool_use", "id": "launch", "name": "Agent", "input": {"prompt": "Inspect the failure."}}),
                          claude("user", {"type": "tool_result", "tool_use_id": "launch", "content": "agentId: child"})])
        child = root.parent / "session/subagents/agent-child.jsonl"
        transcript(child, [claude("user", {"type": "text", "text": "Inspect the failure."}),
                           claude("assistant", {"type": "tool_use", "id": "bash", "name": "Bash", "input": {"command": "test"}}),
                           claude("user", {"type": "tool_result", "tool_use_id": "bash", "is_error": True, "content": "Exit code 1\nAssertion failed"})])
        write(child.with_suffix(".meta.json"), json.dumps({"agentType": "general-purpose"}))
        grandchild = child.with_name("agent-grandchild.jsonl")
        transcript(grandchild, [claude("assistant", {"type": "tool_use", "id": "pending", "name": "Read", "input": {"file_path": "result.txt"}})])
        write(grandchild.with_suffix(".meta.json"), json.dumps({"parentAgentId": "child", "spawnDepth": 2}))
        return root, child, grandchild

    def test_claude_tree_errors_unknown_outcomes_and_read_only(self):
        self.claude_tree()
        before = {p: hashlib.sha256(p.read_bytes()).digest() for p in self.home.rglob("*") if p.is_file()}
        summary = logs.inspect("claude", "session", self.home)
        self.assertEqual([a["id"] for a in summary["agents"]], ["session", "child", "grandchild"])
        self.assertEqual(summary["agents"][1]["error_count"], 1)
        self.assertEqual(summary["agents"][2]["unmatched_count"], 1)
        self.assertEqual(summary["agents"][2]["calls_without_recorded_results"][0]["call_id"], "pending")
        self.assertEqual(summary["discovery_gaps"], [])
        first = logs.inspect("claude", "session", self.home, limit=1)
        second = logs.inspect("claude", "session", self.home, limit=2, after=first["next_cursor"])
        self.assertEqual([a["id"] for a in second["agents"]], ["child", "grandchild"])
        self.assertIsNone(second["next_cursor"])
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).digest() for p in self.home.rglob("*") if p.is_file()})

    def test_claude_agent_without_metadata_is_a_visible_gap(self):
        _, child, _ = self.claude_tree()
        child.with_suffix(".meta.json").unlink()
        summary = logs.inspect("claude", "session", self.home)
        self.assertEqual([a["id"] for a in summary["agents"]], ["session", "child", "grandchild"])
        self.assertEqual(summary["discovery_gaps"][0]["kind"], "metadata_unavailable")

    def test_codex_nested_message_encryption_is_not_plaintext(self):
        self.codex("root", [response("function_call", name="spawn_agent", call_id="spawn", arguments=json.dumps({"task_name": "maker", "message": "gAAAAencrypted"})),
                            response("function_call_output", call_id="spawn", output="child")])
        self.codex("child", [response("agent_message", author="/root", recipient="/root/maker", content=[{"type": "encrypted_content", "encrypted_content": "gAAAAencrypted"}])], parent="root")
        summary = logs.inspect("codex", "root", self.home)
        self.assertEqual(summary["agent_count"], 2)
        self.assertEqual(summary["agents"][0]["flags"]["encrypted_content"], 1)
        events = logs.read("codex", "root", self.home)["events"]
        call = next(e for e in events if e["kind"] == "tool_call")
        expanded = logs.read("codex", "root", self.home, event_id=call["event_id"])
        self.assertEqual(json.loads(expanded["text"])["message"]["unavailable"], "encrypted")
        self.assertNotIn("gAAAAencrypted", json.dumps(events))

    def test_codex_index_is_the_only_discovery_path(self):
        root = self.codex("root", [])
        with closing(self.index()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("INSERT INTO threads VALUES (?,?,?,?,?,?)", ("missing", str(root.with_name("missing.jsonl")), "/tools/project", "missing", 0, 0))
            db.execute("INSERT INTO thread_spawn_edges VALUES ('root','missing')")
            db.commit()
            result = logs.inspect("codex", "root", self.home)
            self.assertEqual(result["agent_count"], 2)
            self.assertIn("read_gap", result["agents"][1])
            self.assertEqual(db.execute("SELECT count(*) FROM threads").fetchone()[0], 2)
        transcript(self.home / "sessions/2026/09/11/unindexed.jsonl", [{"type": "session_meta", "payload": {"id": "unindexed"}}])
        with self.assertRaisesRegex(ValueError, "not found"):
            logs.inspect("codex", "unindexed", self.home)
        (self.home / "state_5.sqlite").unlink()
        with self.assertRaisesRegex(ValueError, "index not found"):
            logs.find("codex", self.home)

    def test_pagination_handles_multiple_blocks_unicode_and_append(self):
        root = self.home / "projects/project/session.jsonl"
        transcript(root, [claude("assistant", {"type": "thinking", "thinking": "not part of reader output"},
                                 {"type": "text", "text": "α first"}, {"type": "tool_use", "id": "a", "name": "Read", "input": {"file_path": "λ.txt"}}),
                          claude("user", {"type": "tool_result", "tool_use_id": "a", "content": "héllo"})])
        all_events = logs.read("claude", "session", self.home)["events"]
        after, collected = None, []
        for _ in range(5):
            page = logs.read("claude", "session", self.home, limit=1, after=after)
            collected.extend(page["events"])
            after = page["next_cursor"]
            if not page["has_more"]:
                break
        self.assertEqual(collected, all_events)
        self.assertNotIn("not part of reader output", json.dumps(collected))
        self.assertEqual(logs.read("claude", "session", self.home, after=after)["events"], [])
        with root.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(claude("assistant", {"type": "text", "text": "appended"})) + "\n")
        self.assertEqual(len(logs.read("claude", "session", self.home, after=after)["events"]), 1)
        expanded = logs.read("claude", "session", self.home, event_id=all_events[0]["event_id"], offset=2, chars=3)
        self.assertEqual(expanded["text"], "fir")
        self.assertEqual(expanded["source"]["line"], 1)

    def test_changed_source_cursor_and_invalid_event_are_rejected(self):
        self.claude_tree()
        page = logs.read("claude", "child", self.home, limit=1)
        path = self.home / "projects/project/session/subagents/agent-child.jsonl"
        write(path, "{}\n")
        with self.assertRaisesRegex(ValueError, "changed/truncated"):
            logs.read("claude", "child", self.home, after=page["next_cursor"])
        with self.assertRaisesRegex(ValueError, "record boundary"):
            logs.read("claude", "session", self.home, event_id="3:0")
        with self.assertRaises(ValueError):
            logs.read("claude", "session", self.home, after="bad-cursor")

    def test_malformed_middle_and_partial_tail_are_visible(self):
        path = self.codex("root", [])
        with path.open("a", encoding="utf-8") as stream:
            stream.write('not json\n' + json.dumps(response("function_call", name="shell", call_id="pending", arguments="{}")) + '\n{"type":')
        page = logs.read("codex", "root", self.home)
        gaps = [json.loads(e["data"]["text"])["_gap"] for e in page["events"] if e["kind"] == "gap"]
        self.assertEqual(gaps, ["malformed_record", "incomplete_tail"])
        self.assertEqual(logs.inspect("codex", "root", self.home)["agents"][0]["unmatched_count"], 1)

    def test_captured_output_is_separate_from_presented_output(self):
        full = "x" * 40000 + "TAIL EVIDENCE"
        self.codex("root", [{"type": "event_msg", "payload": {"type": "item_completed", "item": {
            "type": "CommandExecution", "id": "exec-1", "status": "completed", "exit_code": 0,
            "command": ["test"], "stdout": full, "formatted_output": "Output truncated"}}}])
        event = next(e for e in logs.read("codex", "root", self.home)["events"] if e["kind"] == "command")
        self.assertEqual(event["captured_output"]["characters"], len(full))
        self.assertTrue(event["captured_output"]["truncated"])
        self.assertIn("output_shortened_or_spilled", event["flags"])
        expanded = logs.read("codex", "root", self.home, event_id=event["event_id"], field="captured_output", offset=40000)
        self.assertEqual(expanded["text"], "TAIL EVIDENCE")
        self.assertIsNone(expanded["next_offset"])

    def test_sidecar_expansion_missing_and_outside_home(self):
        sidecar = self.home / "projects/project/session/tool-results/output.txt"
        write(sidecar, "λ" * 900 + "end")
        root = self.home / "projects/project/session.jsonl"
        transcript(root, [claude("user", {"type": "tool_result", "tool_use_id": "big", "content":
                                          f"<persisted-output>\nFull output saved to: {sidecar}\nPreview..."})])
        event = logs.read("claude", "session", self.home)["events"][0]
        expanded = logs.read("claude", "session", self.home, event_id=event["event_id"], field="sidecar", offset=899, chars=3)
        self.assertEqual(expanded["text"], "λen")
        self.assertEqual(expanded["next_offset"], 902)
        sidecar.unlink()
        self.assertEqual(logs.inspect("claude", "session", self.home)["agents"][0]["flags"]["missing"], 1)
        with self.assertRaisesRegex(ValueError, "available native output"):
            logs.read("claude", "session", self.home, event_id=event["event_id"], field="sidecar")
        outside = self.home.parent / "unrelated-private.txt"
        transcript(root, [claude("user", {"type": "tool_result", "tool_use_id": "bad", "content": f"Full output saved to: {outside}"})])
        self.assertEqual(logs.read("claude", "session", self.home)["events"][0]["sidecars"][0]["state"], "outside_native_home")

    def test_unknown_records_are_identified_without_hidden_context(self):
        self.codex("root", [response("future_tool", something="unknown"), response("reasoning", content="private"),
                            response("message", role="system", content="private")])
        result = logs.read("codex", "root", self.home)
        self.assertEqual(result["events"][-1]["record_type"], "future_tool")
        self.assertNotIn("private", json.dumps(result))

    def test_find_claude_scopes_dates_projects_and_orphan_agents(self):
        def dated(path, cwd, *dates):
            transcript(path, [{**claude("user", {"type": "text", "text": "request"}), "cwd": cwd, "timestamp": date} for date in dates])
        base = self.home / "projects/project"
        dated(base / "a.jsonl", r"C:\tools\bench-stack", "2026-09-01T12:00:00Z", "2026-09-11T12:00:00Z")
        dated(base / "b.jsonl", r"C:\tools\another-project", "2026-09-11T12:00:00Z")
        dated(base / "old.jsonl", r"C:\tools\bench-stack", "2026-08-01T12:00:00Z")
        dated(base / "missing/subagents/agent-child.jsonl", r"C:\worktrees\bench-stack", "2026-09-11T12:00:00Z")
        before = {p: p.read_bytes() for p in self.home.rglob("*.jsonl")}
        page = logs.find("claude", self.home, since="2026-09-04", project="BENCH-STACK", limit=1)
        self.assertEqual(page["page_count"], 1)
        self.assertEqual(page["candidates"][0]["id"], "a")
        following = logs.find("claude", self.home, since="2026-09-04", project="bench-stack", after=page["next_cursor"])
        self.assertEqual(following["candidates"][0]["id"], "child")
        self.assertEqual(following["candidates"][0]["parent_id"], "missing")
        self.assertIsNone(following["next_cursor"])
        with self.assertRaisesRegex(ValueError, "changed filters"):
            logs.find("claude", self.home, since="2026-09-05", project="bench-stack", after=page["next_cursor"])
        self.assertEqual(before, {p: p.read_bytes() for p in self.home.rglob("*.jsonl")})

    def test_find_codex_index_candidates_can_have_no_events_in_window(self):
        self.codex("root", [response("function_call", name="test", call_id="a", arguments="{}")], cwd="/tools/bench-stack")
        found = logs.find("codex", self.home, since="2026-09-04", until="2026-09-05", project="bench-stack")
        self.assertEqual([c["id"] for c in found["candidates"]], ["root"])
        page = logs.read("codex", "root", self.home, since="2026-09-04", until="2026-09-05")
        self.assertFalse(any(e["kind"] == "tool_call" for e in page["events"]))
        self.assertIn("timestamp_unavailable", page["events"][0]["flags"])

    def test_find_reads_large_claude_endpoints_and_keeps_missing_metadata(self):
        path = self.home / "projects/project/session.jsonl"
        transcript(path, [claude("user", {"type": "tool_result", "tool_use_id": "a", "content": "x" * 200000})])
        with path.open("a", encoding="utf-8") as stream:
            stream.write('{"incomplete":')
        page = logs.find("claude", self.home, since="2026-09-04", project="bench-stack")
        self.assertEqual(page["candidates"][0]["updated_at"], "2026-09-11T12:00:00+00:00")
        self.assertEqual(page["candidates"][0]["scope_unknown"], ["project"])

    def test_read_window_boundaries_pagination_and_resumed_session(self):
        path = self.home / "projects/project/session.jsonl"
        dates = ["2026-08-01T00:00:00Z", "2026-09-04T04:00:00Z", "2026-09-06T12:00:00Z", "2026-09-11T04:00:00Z"]
        transcript(path, [{**claude("user", {"type": "text", "text": str(i)}), "timestamp": date} for i, date in enumerate(dates)])
        scope = {"since": "2026-09-04T00:00:00-04:00", "until": "2026-09-11T00:00:00-04:00"}
        first = logs.read("claude", "session", self.home, limit=1, **scope)
        self.assertEqual(first["events"][0]["data"]["text"], "1")
        self.assertTrue(first["has_more"])
        second = logs.read("claude", "session", self.home, limit=1, after=first["next_cursor"], **scope)
        self.assertEqual(second["events"][0]["data"]["text"], "2")
        self.assertFalse(second["has_more"])
        self.assertEqual(logs.read("claude", "session", self.home, after=second["next_cursor"], **scope)["events"], [])
        for since, until in [("2026-09-04T00:00:00", None), ("bad", None), ("2026-09-11", "2026-09-04")]:
            with self.assertRaises(ValueError):
                logs.find("claude", self.home, since=since, until=until)


if __name__ == "__main__":
    unittest.main()
