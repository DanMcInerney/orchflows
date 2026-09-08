"""Nested diagnostic coverage through the public collector and review close."""
import copy
import hashlib
import json
import unittest

from tests import test_self_improve as support


class DiagnosticShapes(unittest.TestCase):
    def test_selected_attribution_failures_reach_public_gap_pages_once(self):
        case = support.SelfImprove()
        case.setUp()
        self.addCleanup(case.doCleanups)
        for host in ("codex", "claude"):
            if host == "codex":
                call = {"type": "response_item", "timestamp": support.STAMP, "payload": {
                    "type": "function_call", "name": "exec_command", "call_id": "call",
                    "arguments": '{"cmd":"false"}'}}
                output = {"type": "response_item", "timestamp": support.STAMP, "payload": {
                    "type": "function_call_output", "call_id": "call", "output": "Exit code: 7"}}
            else:
                call = {"type": "assistant", "timestamp": support.STAMP, "sessionId": "fixture",
                        "cwd": str(case.project), "message": {"content": [{"type": "tool_use",
                        "id": "call", "name": "Bash", "input": {"command": "false"}}]}}
                output = dict(call, type="user", message={"content": [{"type": "tool_result",
                              "tool_use_id": "call", "content": "Exit code: 7", "is_error": True}]})
            excluded = dict(output, timestamp=case.selection["end"])
            for label, rows, expected in (("valid", [call, output], 0),
                                           ("orphan", [output], 1),
                                           ("ambiguous", [call, call, output], 2),
                                           ("excluded", [call, output, excluded], 0)):
                with self.subTest(host=host, case=label):
                    path = case.write(host + "-" + label + ".jsonl",
                                      ([support.meta("fixture", case.project)] if host == "codex" else []) + rows)
                    original = path.read_bytes()
                    case.selection["sources"] = [{"kind": host, "path": str(path)}]
                    bundle = case.collect()
                    coverage = "partial" if expected else "complete"
                    self.assertEqual(coverage, bundle["coverage"])
                    source = bundle["sources"][0]
                    self.assertEqual(coverage, source["coverage"])
                    self.assertEqual(expected, source["gap_count"])
                    observations = {o["id"]: o for o in bundle["observations"]}
                    page = case.cli("show", "--review", case.review, "--section", "gaps", "--limit", "1")
                    self.assertEqual(expected, page["gap_count"])
                    self.assertEqual(coverage, page["coverage"])
                    self.assertEqual(page, case.cli("show", "--review", case.review, "--section", "gaps", "--limit", "1"))
                    gaps = list(page["items"])
                    while page["next_offset"] is not None:
                        page = case.cli("show", "--review", case.review, "--section", "gaps",
                                        "--limit", "1", "--offset", str(page["next_offset"]))
                        gaps.extend(page["items"])
                    self.assertEqual(expected, len(gaps))
                    self.assertEqual(bundle["gaps"], gaps)
                    for gap in gaps:
                        observation = observations[gap["observation_id"]]
                        self.assertIn(gap["reason"], observation["attribution_gaps"])
                        self.assertEqual("selection-or-diagnostic", gap["scope"])
                        self.assertEqual(observation["sources"][0],
                                         {key: gap[key] for key in ("path", "sha256", "locator")})
                    for observation in observations.values():
                        self.assertEqual(hashlib.sha256(original).hexdigest(), observation["sources"][0]["sha256"])
                        self.assertEqual("call", observation["links"][0]["id"])
                    if not expected:
                        event = next(e for o in observations.values() for e in o["normalized"] if e["type"] == "tool_call")
                        self.assertEqual(7, event["exit"])
                        self.assertIn(event["result_observation_id"], observations)
                    self.assertEqual(original, path.read_bytes())

    def test_correlation_keys_retain_invalid_identities_with_named_gaps(self):
        case = support.SelfImprove()
        case.setUp()
        self.addCleanup(case.doCleanups)
        for host in ("codex", "claude"):
            with self.subTest(host=host):
                rows = []
                for field in ("run", "ticket"):
                    for value in (None, True, 42, [], {}, ["bad"], {"bad": "id"}, "valid-id"):
                        row = support.message()
                        if host == "claude":
                            row = {"type": "assistant", "timestamp": support.STAMP, "sessionId": "fixture",
                                   "cwd": str(case.project), "message": {"content": [{"type": "text", "text": "ok"}]}}
                        row.update(run="valid-run", ticket="valid-ticket")
                        row[field] = value
                        row["fixture_case"] = field + ":" + json.dumps(value)
                        rows.append(row)
                expected = {row["fixture_case"]: row for row in rows}
                if host == "codex":
                    rows.insert(0, support.meta("fixture", case.project))
                path = case.write(host + "-correlation.jsonl", rows)
                original = path.read_bytes()
                case.selection["sources"] = [{"kind": host, "path": str(path)}]
                bundle = case.collect()
                self.assertEqual("partial", bundle["coverage"])
                self.assertEqual(expected, {o["record"]["fixture_case"]: o["record"] for o in bundle["observations"]})
                for observation in bundle["observations"]:
                    row = observation["record"]
                    valid = all(row[key] is None or isinstance(row[key], str) for key in ("run", "ticket"))
                    self.assertEqual(valid, observation["supported_shape"])
                    if not valid:
                        locator = observation["sources"][0]["locator"]
                        self.assertTrue(any("invalid " in gap["reason"] and gap["reason"].endswith(" identity at " + locator) for gap in bundle["gaps"]))
                    if row["run"] == "valid-id":
                        self.assertIn("valid-id", observation["runs"])
                self.assertEqual(original, path.read_bytes())
                case.record(case.analysis(bundle, positive=[o["id"] for o in bundle["observations"]]))
                closed = case.cli("close", "--review", case.review, "--mode", "review")
                self.assertTrue(closed["review_completed"])
                self.assertEqual(bundle["gaps"], closed["gaps"])

    def test_malformed_json_fields_remain_partial_retained_observations(self):
        case = support.SelfImprove()
        case.setUp()
        self.addCleanup(case.doCleanups)
        text = {"type": "text", "text": "visible success"}
        claude = {"type": "assistant", "sessionId": "fixture", "cwd": str(case.project),
                  "timestamp": support.STAMP, "message": {"content": [text]}}
        codex = support.message()
        result = dict(codex, payload={"type": "function_call_output", "call_id": "call", "output": [text]})
        completed = dict(codex, type="event_msg", payload={"type": "item_completed", "item": {
            "type": "AgentMessage", "id": "item", "content": [{"type": "Text", "text": "visible success"}]}})
        tool = dict(claude, message={"content": [{"type": "tool_use", "id": "call", "name": "Bash", "input": {}}]})
        tool_result = dict(claude, type="user", message={"content": [{"type": "tool_result", "tool_use_id": "call", "content": [text]}]})
        # Each site is a public envelope field, not an implementation call site.
        sites = [
            ("claude", claude, ("type",), "discriminator"),
            ("claude", claude, ("message", "content", 0, "type"), "discriminator"),
            ("claude", tool_result, ("message", "content", 0, "content", 0, "type"), "discriminator"),
            ("claude", claude, ("message", "content", 0, "text"), "string"),
            ("claude", tool, ("message", "content", 0, "id"), "string"),
            ("claude", tool_result, ("message", "content", 0, "tool_use_id"), "string"),
            ("claude", tool_result, ("message", "content", 0, "is_error"), "boolean"),
            ("codex", codex, ("type",), "discriminator"),
            ("codex", codex, ("payload", "type"), "discriminator"),
            ("codex", codex, ("payload", "content", 0, "type"), "discriminator"),
            ("codex", codex, ("payload", "content", 0, "text"), "string"),
            ("codex", result, ("payload", "output", 0, "type"), "discriminator"),
            ("codex", result, ("payload", "call_id"), "string"),
            ("codex", completed, ("payload", "type"), "discriminator"),
            ("codex", completed, ("payload", "item", "type"), "discriminator"),
            ("codex", completed, ("payload", "item", "id"), "string"),
            ("codex", completed, ("payload", "item", "content", 0, "type"), "discriminator"),
            ("codex", completed, ("payload", "item", "content", 0, "text"), "string"),
        ]
        for kind in ("agent_message", "agent_reasoning", "user_message"):
            event = dict(codex, type="event_msg", payload={"type": kind, "message": [text]})
            sites.append(("codex", event, ("payload", "message", 0, "type"), "discriminator"))
        for kind in ("function_call_output", "custom_tool_call_output"):
            output = dict(codex, payload={"type": kind, "call_id": "call", "output": [text]})
            sites.extend(("codex", output, ("payload", field), required) for field, required in
                         (("call_id", "string"), ("output", "content")))
        agent = dict(codex, payload={"type": "agent_message", "content": [{"type": "output_text", "text": "ok"}]})
        reasoning = dict(codex, payload={"type": "reasoning", "summary": [{"type": "summary_text", "text": "ok"}]})
        sites.extend([
            ("codex", agent, ("payload", "content", 0, "type"), "discriminator"),
            ("codex", reasoning, ("payload", "summary", 0, "type"), "discriminator"),
            ("claude", tool, ("message", "content", 0, "input"), "object"),
            ("claude", tool_result, ("message", "content", 0, "content"), "content"),
        ])
        for kind, field in (("Reasoning", "summary_text"), ("Reasoning", "raw_content"),
                            ("CommandExecution", "output"), ("CommandExecution", "aggregated_output")):
            item = {"id": "item", "type": kind, "summary_text": [], "raw_content": [], "command": "check", field: [text]}
            event = dict(codex, type="event_msg", payload={"type": "item_completed", "item": item})
            sites.append(("codex", event, ("payload", "item", field, 0, "type"), "discriminator"))
        for host in ("claude", "codex"):
            rows = []
            for index, (kind, base, path, required) in enumerate(sites):
                if kind != host:
                    continue
                for value in (None, True, 42, "future_content", [], {}, ["bad"], {"bad": "id"}):
                    if (required == "string" and isinstance(value, str)
                            or required == "boolean" and type(value) is bool
                            or required == "object" and isinstance(value, dict)
                            or required == "content" and isinstance(value, (str, list))):
                        continue
                    row = copy.deepcopy(base)
                    cursor = row
                    for key in path[:-1]:
                        cursor = cursor[key]
                    cursor[path[-1]] = value
                    row["fixture_case"] = str(index) + ":" + json.dumps(value)
                    rows.append(row)
            with self.subTest(host=host):
                expected = {row["fixture_case"]: row for row in rows}
                if host == "codex":
                    rows.insert(0, support.meta("fixture", case.project))
                path = case.write(host + "-malformed.jsonl", rows)
                original = path.read_bytes()
                case.selection["sources"] = [{"kind": host, "path": str(path)}]
                bundle = case.collect()
                self.assertEqual("partial", bundle["coverage"])
                self.assertEqual(len(expected), bundle["sources"][0]["counts"]["unsupported"])
                self.assertTrue(any("unsupported record" in gap["reason"] for gap in bundle["gaps"]))
                self.assertEqual(expected, {o["record"]["fixture_case"]: o["record"] for o in bundle["observations"]})
                self.assertTrue(all(not o["supported_shape"] for o in bundle["observations"]))
                self.assertTrue(all(isinstance(link["id"], str) and link["id"] for o in bundle["observations"] for link in o["links"]))
                self.assertEqual(original, path.read_bytes())
                case.record(case.analysis(bundle, positive=[o["id"] for o in bundle["observations"]]))
                closed = case.cli("close", "--review", case.review, "--mode", "review")
                self.assertTrue(closed["review_completed"])
                self.assertEqual(bundle["gaps"], closed["gaps"])

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
            ("codex-result-text", "codex", [codex({"type": "function_call", "name": "exec_command", "call_id": "call", "arguments": '{"cmd":"check"}'}), codex({"type": "function_call_output", "call_id": "call", "output": [output]})], "complete", False),
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
