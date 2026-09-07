"""Nested diagnostic coverage through the public collector and review close."""
import json
import unittest

from tests import test_self_improve as support


class DiagnosticShapes(unittest.TestCase):
    def test_nested_host_content_preserves_known_text_tools_and_declares_gaps(self):
        case = support.SelfImprove()
        case.setUp()
        self.addCleanup(case.doCleanups)
        future = {"type": "future_content", "data": {"diagnostic": "unknown"}}
        text = {"type": "text", "text": "visible success"}
        output = {"type": "output_text", "text": "visible success"}
        claude = lambda role, content: {"type": role, "sessionId": "fixture", "cwd": str(case.project), "timestamp": support.STAMP, "message": {"role": role, "content": content}}
        codex = lambda content: {"timestamp": support.STAMP, "type": "response_item", "payload": content}
        completed = lambda item: {"timestamp": support.STAMP, "type": "event_msg", "payload": {"type": "item_completed", "item": dict(item, id="item")}}
        scenarios = [
            ("claude-text", "claude", [claude("assistant", [text])], "complete", False),
            ("claude-user", "claude", [claude("user", "visible success")], "complete", False),
            ("claude-tool", "claude", [claude("assistant", [{"type": "tool_use", "id": "call", "name": "Bash", "input": {"command": "check"}}]), claude("user", [{"type": "tool_result", "tool_use_id": "call", "content": [text]}])], "complete", False),
            ("claude-tool-error", "claude", [claude("assistant", [{"type": "tool_use", "id": "call", "name": "Bash", "input": {"command": "check"}}]), claude("user", [{"type": "tool_result", "tool_use_id": "call", "is_error": True, "content": "Exit code: 2"}])], "complete", False),
            ("claude-thinking", "claude", [claude("assistant", [{"type": "thinking", "thinking": "visible reasoning"}])], "complete", False),
            ("claude-future", "claude", [claude("assistant", [text, future])], "partial", True),
            ("claude-user-future", "claude", [claude("user", [future])], "partial", True),
            ("claude-result-future", "claude", [claude("user", [{"type": "tool_result", "tool_use_id": "call", "content": [future]}])], "partial", True),
            ("claude-malformed", "claude", [claude("assistant", [{"type": "text", "text": {"future": "data"}}])], "partial", True),
            ("claude-opaque", "claude", [claude("assistant", [text, {"type": "redacted_thinking", "data": "opaque-fixture-bytes"}])], "partial", False),
            ("codex-completed-text", "codex", [completed({"type": "AgentMessage", "content": [output]})], "complete", False),
            ("codex-modern-Text", "codex", [completed({"type": "AgentMessage", "content": [{"type": "Text", "text": "visible success"}]})], "complete", False),
            ("codex-completed-future", "codex", [completed({"type": "AgentMessage", "content": [future]})], "partial", True),
            ("codex-reasoning-future", "codex", [completed({"type": "Reasoning", "summary_text": [], "raw_content": [future]})], "partial", True),
            ("codex-result-text", "codex", [codex({"type": "function_call_output", "call_id": "call", "output": [output]})], "complete", False),
            ("codex-result-future", "codex", [codex({"type": "function_call_output", "call_id": "call", "output": [future]})], "partial", True),
            ("codex-message-future", "codex", [codex({"type": "message", "role": "assistant", "content": [output, future]})], "partial", True),
            ("codex-event-text", "codex", [{"timestamp": support.STAMP, "type": "event_msg", "payload": {"type": "agent_message", "message": "visible success"}}], "complete", False),
            ("codex-event-future", "codex", [{"timestamp": support.STAMP, "type": "event_msg", "payload": {"type": "agent_message", "message": [future]}}], "partial", True),
            ("codex-opaque", "codex", [codex({"type": "reasoning", "summary": [], "encrypted_content": "opaque-fixture-bytes"})], "partial", False),
        ]
        for name, host, rows, coverage, unsupported in scenarios:
            with self.subTest(name=name):
                if host == "codex":
                    rows.insert(0, support.meta("fixture", case.project))
                path = case.write(name + ".jsonl", rows)
                original = path.read_bytes()
                case.selection["sources"] = [{"kind": host, "path": str(path)}]
                bundle = case.collect()
                self.assertEqual(coverage, bundle["coverage"])
                self.assertEqual(unsupported, bundle["sources"][0]["counts"]["unsupported"] > 0)
                self.assertEqual(coverage == "partial", bool(bundle["gaps"]))
                self.assertEqual(original, path.read_bytes())
                self.assertNotIn("opaque-fixture-bytes", json.dumps(bundle))
                if "future" in name:
                    self.assertIn("future_content", json.dumps(bundle))
                if name in {"claude-text", "claude-future", "claude-opaque", "codex-message-future"}:
                    self.assertTrue(any(e.get("type") == "narration" for o in bundle["observations"] for e in o["normalized"]))
                if name == "claude-tool":
                    self.assertTrue(any(e.get("exit") == 0 for o in bundle["observations"] for e in o["normalized"]))
                if name == "claude-tool-error":
                    self.assertTrue(any(e.get("exit") == 2 for o in bundle["observations"] for e in o["normalized"]))
                case.record(case.analysis(bundle, positive=[o["id"] for o in bundle["observations"]]))
                closed = case.cli("close", "--review", case.review, "--mode", "review")
                self.assertTrue(closed["review_completed"])
                self.assertEqual(bundle["gaps"], closed["gaps"])


if __name__ == "__main__":
    unittest.main()
