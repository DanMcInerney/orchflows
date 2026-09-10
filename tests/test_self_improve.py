"""Public collection/lifecycle seams over realistic host records and sink isolation."""
from __future__ import annotations

import concurrent.futures
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts import state_root
from tests._repo_root import ROOT


SCRIPTS = ROOT / "example-workflows" / "orch-self-improve" / "scripts"
COMMAND = SCRIPTS / "self_improve.py"
STAMP = "2026-09-07T10:00:00Z"


def meta(sid, cwd=None, parent=None):
    payload = {"id": sid, "cwd": str(cwd) if cwd else None, "source": "cli"}
    if parent:
        payload["source"] = {"subagent": {"thread_spawn": {"parent_thread_id": parent, "depth": 1}}}
    return {"timestamp": "2026-08-01T00:00:00Z", "type": "session_meta", "payload": payload}


def message(text="hello", stamp=STAMP):
    return {"timestamp": stamp, "type": "response_item", "payload": {
        "type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]}}


class SelfImprove(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="self-improve-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.logs = self.root / "logs"
        self.logs.mkdir()
        self.project = self.root / "one" / "bench-stack"
        self.project.mkdir(parents=True)
        (self.project / ".git").mkdir()
        self.env = dict(os.environ)
        self.env[state_root.ENV_VAR] = str(self.root / "sink")
        self.selection = {"mode": "review", "timezone": "America/Indianapolis",
            "timezone_provenance": "agent resolved offset-aware bounds; preceding elapsed week",
            "as_of": "2026-09-07T07:00:00-04:00", "start": "2026-08-31T11:00:00Z",
            "end": "2026-09-07T11:00:00Z", "sources": [{"kind": "codex", "path": str(self.logs)}],
            "projects": [str(self.project)], "sessions": [], "runs": [], "descendants": True, "repair_bound": 2}

    def write(self, name, rows):
        path = self.logs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return path

    def cli(self, *args, expected=0):
        result = subprocess.run([sys.executable, str(COMMAND), *args], env=self.env,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(expected, result.returncode, result.stdout + result.stderr)
        return json.loads(result.stdout)

    def collect(self):
        path = self.root / "selection.json"
        path.write_text(json.dumps(self.selection), encoding="utf-8")
        result = self.cli("collect", "--selection", str(path))
        self.review = result["review"]
        self.head = result["revision"]
        return self.cli("show", "--review", self.review)["bundle"]

    def record(self, entry, expected=0):
        entry = dict(entry, predecessor=entry.get("predecessor", self.head))
        path = self.root / "record.json"
        path.write_text(json.dumps(entry), encoding="utf-8")
        result = self.cli("record", "--review", self.review, "--file", str(path), expected=expected)
        if expected == 0:
            self.head = result.get("head", result["revision"])
        return result

    def analysis(self, bundle, proposals=(), positive=()):
        return {"id": "analysis", "kind": "analysis", "report": "Agent diagnosis with coverage limits",
                "artifact": "content:review-report", "agent_ticket": "review/A1", "positive": list(positive),
                "unresolved": [], "gaps": bundle["gaps"], "ranked_proposals": list(proposals)}

    def incident(self, oid, name="i1", episode="episode1"):
        return {"id": name, "kind": "incident", "members": [oid], "rationale": "original tool failure, copies grouped",
                "uncertainty": [], "classification": "workflow", "primary_owner": "scripts/owner.py",
                "obstruction": "lost-error", "independent_episode": episode}

    def proposal(self):
        return {"id": "p1", "kind": "proposal", "incidents": ["i1"],
            "owner": {"path": "scripts/owner.py", "revision": "a" * 40, "class": "workflow"},
            "dependents": [], "qualification": "reproduced", "hypothesis": "lost error", "minimal_fix": "preserve error",
            "failure_oracle": {"command": "check original", "fixture_sha256": "f" * 64, "revision": "a" * 40, "observed_exit": 1},
            "nearby_success": [{"command": "check adjacent", "fixture_sha256": "e" * 64, "revision": "a" * 40, "observed_exit": 0}],
            "cost": "small", "impact": "all failed tools", "risk": "low", "rank": 1, "rationale": "reproduced one-off", "gaps": []}

    def test_codex_tracer_descendants_time_project_success_and_original_hash(self):
        main = self.write("main.jsonl", [meta("parent", self.project), message("parent")])
        self.write("child.jsonl", [meta("child", parent="parent"), message("child"),
            {"timestamp": STAMP, "type": "response_item", "payload": {"type": "function_call", "name": "exec_command", "call_id": "c1", "arguments": '{"command":"check"}'}},
            {"timestamp": "2026-09-07T10:00:01Z", "type": "response_item", "payload": {"type": "function_call_output", "call_id": "c1", "output": "Exit code: 0"}},
            message("edge-start", self.selection["start"]), message("edge-end", self.selection["end"])])
        other = self.root / "two" / "bench-stack"
        other.mkdir(parents=True)
        self.write("other.jsonl", [meta("other", other), message("excluded")])
        main = main.parent / ".." / main.parent.name / main.name
        self.selection["sessions"] = ["parent"]
        original = main.read_bytes()
        bundle = self.collect()
        self.assertEqual("complete", bundle["coverage"])
        self.assertEqual({"parent", "child"}, {o["session"] for o in bundle["observations"]})
        self.assertFalse(any("edge-end" in json.dumps(o) for o in bundle["observations"]))
        self.assertTrue(any(e.get("exit") == 0 for o in bundle["observations"] for e in o["normalized"]))
        self.assertEqual(hashlib.sha256(original).hexdigest(), next(s["sha256"] for s in bundle["sources"] if os.path.normcase(s["path"]) == os.path.normcase(str(main.resolve()))))
        self.assertEqual(original, main.read_bytes())
        self.record(self.analysis(bundle, positive=[o["id"] for o in bundle["observations"]]))
        result = self.cli("close", "--review", self.review, "--mode", "review")
        self.assertTrue(result["review_completed"])
        self.assertFalse(result["repair_completed"])

    def test_nested_and_string_credentials_are_redacted_before_persistence(self):
        secret = "sensitive-value-123"
        self.write("main.jsonl", [meta("parent", self.project), message(
            'Authorization: Bearer ' + secret + '\nhttps://user:' + secret + '@host/?token=' + secret +
            '\n{"nested":{"api_key":"' + secret + '"}}\n-----BEGIN PRIVATE KEY-----\n' + secret + '\n-----END PRIVATE KEY-----')])
        bundle = self.collect()
        self.assertNotIn(secret, json.dumps(bundle))
        self.assertNotIn(secret, (self.root / "sink" / "improvement" / "reviews" / self.review / "bundle.json").read_text())

    def test_unknown_malformed_truncated_missing_and_empty_are_distinct(self):
        path = self.write("bad.jsonl", [meta("p", self.project), {"timestamp": STAMP, "type": "future_secret_shape", "payload": {}}])
        with path.open("a") as stream:
            stream.write('{"unfinished":')
        bundle = self.collect()
        self.assertEqual("partial", bundle["coverage"])
        self.assertEqual(1, bundle["sources"][0]["counts"]["unsupported"])
        self.assertEqual(1, bundle["sources"][0]["counts"]["truncated"])
        self.selection["sources"][0]["path"] = str(self.root / "missing")
        self.assertEqual("unavailable", self.collect()["coverage"])
        self.selection["sources"][0]["path"] = str(self.root / "empty")
        (self.root / "empty").mkdir()
        self.assertEqual("empty", self.collect()["coverage"])

    def test_cycles_orphans_duplicates_missing_metadata_cannot_expand_scope(self):
        self.write("cycle-a.jsonl", [meta("a", self.project, "b"), message("a")])
        self.write("cycle-b.jsonl", [meta("b", self.project, "a"), message("b")])
        self.write("orphan.jsonl", [meta("orphan", self.project, "absent"), message("orphan")])
        self.write("duplicate.jsonl", [meta("orphan", self.project), message("copy")])
        self.write("no-meta.jsonl", [message("unknown")])
        self.selection["sessions"] = ["a"]
        bundle = self.collect()
        self.assertEqual("partial", bundle["coverage"])
        self.assertEqual({"a"}, {o["session"] for o in bundle["observations"]})
        reasons = {g["reason"] for g in bundle["gaps"]}
        self.assertTrue(any("cycle" in r for r in reasons))
        self.assertTrue(any("duplicate" in r for r in reasons))
        self.assertTrue(any("missing session" in r for r in reasons))

    def test_claude_subagent_tree_and_copied_evidence_links(self):
        self.selection["sources"][0]["kind"] = "claude"
        self.selection["sessions"] = ["parent"]
        self.write("parent.jsonl", [{"type": "assistant", "sessionId": "parent", "cwd": str(self.project), "timestamp": STAMP,
            "message": {"content": [{"type": "text", "text": "copied result"}]}}])
        self.write("parent/subagents/agent-child.jsonl", [{"type": "assistant", "isSidechain": True,
            "sessionId": "parent", "agentId": "child", "timestamp": STAMP, "copied_from": "call1",
            "message": {"content": [{"type": "tool_use", "id": "call1", "name": "Bash", "input": {"command": "true"}}]}},
            {"type": "user", "isSidechain": True, "sessionId": "parent", "agentId": "child", "timestamp": "2026-09-07T10:00:01Z",
             "message": {"content": [{"type": "tool_result", "tool_use_id": "call1", "content": "ok"}]}}])
        bundle = self.collect()
        self.assertEqual({"parent", "child"}, {o["session"] for o in bundle["observations"]})
        self.assertTrue(any(l["kind"] == "copied_from" for o in bundle["observations"] for l in o["links"]))
        self.assertTrue(any(e.get("exit") == 0 for o in bundle["observations"] for e in o["normalized"]))

    def test_repair_lifecycle_rejects_stale_idempotency_replay_and_reopens(self):
        self.selection["mode"] = "repair"
        self.write("main.jsonl", [meta("p", self.project), message("original failure"), message("later recurrence", "2026-09-07T10:01:00Z")])
        bundle = self.collect()
        first, second = [o["id"] for o in bundle["observations"]]
        original_head = self.head
        incident = dict(self.incident(first), predecessor=self.head)
        self.record(incident)
        self.assertTrue(self.record(incident)["idempotent"])
        self.record(dict(incident, rationale="different"), expected=2)
        self.record(dict(self.incident(second, "i2", "episode2"), predecessor=original_head), expected=2)
        self.record(self.incident(second, "i2", "episode2"))
        proposal = self.proposal()
        self.record(proposal)
        self.record(self.analysis(bundle, ["p1"]))
        self.record({"id": "select", "kind": "transition", "proposal": "p1", "stage": "selected", "evidence": {"reason": "top"}})
        commit = "b" * 40
        failure = dict(proposal["failure_oracle"], observed_exit=0, revision=commit)
        nearby = [dict(p, revision=commit) for p in proposal["nearby_success"]]
        implementation = {"id": "implement", "kind": "transition", "proposal": "p1", "stage": "implemented", "evidence": {
            "commit": commit, "checks": [{"command": "scoped", "exit": 0}], "original_replay": failure,
            "nearby_replays": nearby, "judge_artifact": "findings:judge", "judge_verdict": "PASS", "delivery_run": "delivery", "accepted_ticket": "repair/A1"}}
        wrong = copy.deepcopy(implementation)
        wrong["evidence"]["original_replay"]["command"] = "weakened"
        self.record(wrong, expected=2)
        self.record(implementation)
        self.assertTrue(self.cli("close", "--review", self.review, "--mode", "repair")["repair_completed"])
        self.record({"id": "deploy", "kind": "transition", "proposal": "p1", "stage": "deployed", "evidence": {
            "receipt": "receipt:runtime", "installed_commit": commit, "deployed_at": "2026-09-07T12:00:00Z"}})
        later = {"id": "later", "kind": "transition", "proposal": "p1", "stage": "later-use-verified", "evidence": {
            "run": "delivery", "started_at": "2026-09-08T12:00:00Z", "matching_owner": "scripts/owner.py", "matching_obstruction": "lost-error", "artifact": "trace:later"}}
        self.record(later, expected=2)
        later["evidence"]["run"] = "independent"
        self.record(later)
        self.record({"id": "reopen", "kind": "transition", "proposal": "p1", "stage": "reopened", "evidence": {"incidents": ["i2"], "rationale": "same obstruction on fresh episode"}})
        self.assertFalse(self.cli("close", "--review", self.review, "--mode", "repair", expected=3)["repair_completed"])

    def test_concurrent_records_have_one_winner_and_no_lost_predecessor(self):
        bundle = self.collect()
        paths = []
        for index in range(2):
            entry = dict(self.analysis(bundle), id="analysis" + str(index), predecessor=self.head)
            path = self.root / (str(index) + ".json")
            path.write_text(json.dumps(entry))
            paths.append(path)
        def write(path):
            return subprocess.run([sys.executable, str(COMMAND), "record", "--review", self.review, "--file", str(path)], env=self.env, capture_output=True, text=True, timeout=30)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(write, paths))
        self.assertEqual([0, 2], sorted(r.returncode for r in results))
        self.assertEqual(1, len(self.cli("show", "--review", self.review)["records"]))

    def test_repair_without_proposal_reports_incomplete_and_review_closes(self):
        self.selection["mode"] = "repair"
        bundle = self.collect()
        self.record(self.analysis(bundle))
        self.record({"id": "none", "kind": "repair_not_completed", "reason": "fully inspected empty selection; no qualifying repair", "gaps": []})
        self.assertTrue(self.cli("close", "--review", self.review, "--mode", "review")["review_completed"])
        self.assertIn("no qualifying", self.cli("close", "--review", self.review, "--mode", "repair", expected=3)["repair_not_completed"])

    def test_sink_run_friction_ticket_association_does_not_import_whole_run(self):
        runfile = self.root / "run.json"
        runfile.write_text(json.dumps({"run": "R1", "project": {"root": str(self.project)}, "opened_at": "2026-08-01T00:00:00Z"}))
        ticket = self.root / "tickets" / "R1" / "A1.md"
        ticket.parent.mkdir(parents=True)
        dispatch = {"attempts": [{"dispatch_id": "A1:d1", "records": [
            {"record_id": "outcome", "committed_at": STAMP, "content": "Copied original tool failure"}]}]}
        ticket.write_text('---\nrun: R1\nid: A1\ndispatch_v1: ' + json.dumps(dispatch) + '\n---\n\n## Report\nCopied original tool failure\n')
        self.write("parent.jsonl", [meta("parent", self.project), message("parent context")])
        alias = self.root / "ticket alias"
        if os.name == "nt":
            linked = subprocess.run(["cmd", "/c", "mklink", "/J", str(alias), str(ticket.parent)],
                                    capture_output=True, text=True, timeout=30)
            self.assertEqual(0, linked.returncode, linked.stdout + linked.stderr)
        else:
            alias.symlink_to(ticket.parent, target_is_directory=True)
        referenced = alias / ticket.name
        self.assertNotEqual(str(referenced), str(referenced.resolve()))
        self.assertEqual(ticket.resolve(), referenced.resolve())
        self.write("child.jsonl", [meta("child", parent="parent"), message("Read `" + str(referenced) + "` for evidence.")])
        friction = self.root / "friction.jsonl"
        friction.write_text(json.dumps({"ts": STAMP, "session": "child", "run": "R1", "observed": "failure", "expected": "success"}) + '\n' +
                            json.dumps({"ts": STAMP, "session": "unrelated", "run": "R1", "observed": "outside", "expected": "success"}) + '\n')
        self.selection["sources"].extend([{"kind": "runs", "path": str(runfile)}, {"kind": "tickets", "path": str(ticket)}, {"kind": "friction", "path": str(friction)}])
        self.selection["sessions"] = ["parent"]
        self.selection["runs"] = ["R1"]
        bundle = self.collect()
        formats = {o["format"] for o in bundle["observations"]}
        self.assertTrue({"tickets", "friction"} <= formats)
        source = next(s for s in bundle["sources"] if s["format"] == "tickets")
        self.assertEqual(os.path.normcase(str(ticket.resolve())), source["path"])
        self.assertEqual(hashlib.sha256(ticket.read_bytes()).hexdigest(), source["sha256"])
        self.assertEqual({"child"}, {o["session"] for o in bundle["observations"] if o["format"] == "tickets"})
        self.assertFalse(any(o["session"] == "unrelated" for o in bundle["observations"]))
        self.assertTrue(any(o["record"].get("type") == "ticket_projection" for o in bundle["structural_context"]))

    def test_exact_duplicates_keep_each_locator_and_covered_never_filters(self):
        duplicate = message("repeat")
        self.write("p.jsonl", [meta("p", self.project), duplicate, duplicate])
        legacy = self.root / "sink" / "improvement"
        legacy.mkdir(parents=True)
        covered = legacy / "covered.jsonl"
        covered.write_text('{"matcher":[".*"],"watermark":"2099-01-01T00:00:00Z"}\n')
        before = covered.read_bytes()
        bundle = self.collect()
        self.assertEqual(2, len(bundle["observations"]))
        self.assertEqual({"line:2", "line:3"}, {o["sources"][0]["locator"] for o in bundle["observations"]})
        self.assertEqual(2, len({o["id"] for o in bundle["observations"]}))
        self.assertEqual(before, covered.read_bytes())

    def test_cross_review_recurrence_carries_immutable_original_proposal(self):
        self.write("p.jsonl", [meta("p", self.project), message("original")])
        first_bundle = self.collect()
        self.record(self.incident(first_bundle["observations"][0]["id"]))
        self.record(self.proposal())
        self.record(self.analysis(first_bundle, ["p1"]))
        self.record({"id": "defer", "kind": "transition", "proposal": "p1", "stage": "deferred", "evidence": {"reason": "repair not authorized yet"}})
        prior = self.cli("show", "--review", self.review)
        self.write("p.jsonl", [meta("p", self.project), message("new recurrence", "2026-09-07T10:02:00Z")])
        self.selection["mode"] = "repair"
        bundle = self.collect()
        carry = {"id": "p1", "kind": "prior_proposal", "source_review": prior["review"], "source_revision": prior["revision"],
                 "proposal": prior["projection"]["proposals"]["p1"], "stage": "deferred", "original_incidents": prior["projection"]["incidents"]}
        wrong = copy.deepcopy(carry)
        wrong["proposal"]["minimal_fix"] = "different fix"
        self.record(wrong, expected=2)
        self.record(carry)
        self.record(self.incident(bundle["observations"][0]["id"], "i2", "episode2"))
        self.record({"id": "reopen", "kind": "transition", "proposal": "p1", "stage": "reopened", "evidence": {"incidents": ["i2"], "rationale": "new independent original evidence"}})
        self.record(self.analysis(bundle, ["p1"]))
        self.assertTrue(self.cli("close", "--review", self.review, "--mode", "review")["review_completed"])
        self.assertEqual(prior, self.cli("show", "--review", prior["review"]))

    def test_invalid_selection_and_repository_sink_refuse(self):
        path = self.root / "selection.json"
        for key, value in (("start", "2026-08-31T11:00:00"), ("projects", ["bench-stack"]), ("timezone", ""), ("repair_bound", 3)):
            candidate = dict(self.selection, **{key: value})
            path.write_text(json.dumps(candidate))
            self.cli("collect", "--selection", str(path), expected=2)
        path.write_text(json.dumps(self.selection))
        sink = self.root / "sink"
        sink.mkdir(exist_ok=True)
        (sink / ".git").mkdir()
        self.cli("collect", "--selection", str(path), expected=2)

    def test_pages_name_complete_collection_and_never_hide_remaining_evidence(self):
        self.write("p.jsonl", [meta("p", self.project), message("first"), message("second")])
        bundle = self.collect()
        first = self.cli("show", "--review", self.review, "--section", "observations", "--limit", "1")
        second = self.cli("show", "--review", self.review, "--section", "observations", "--offset", "1", "--limit", "1")
        self.assertEqual(2, first["total"])
        self.assertEqual(1, first["next_offset"])
        self.assertIsNone(second["next_offset"])
        self.assertFalse(first["page_is_collection"])
        self.assertEqual(first["revision"], second["revision"])
        self.assertEqual(bundle["observations"], first["items"] + second["items"])
        self.cli("show", "--review", self.review, "--section", "observations", "--limit", "0", expected=2)

    def test_drifted_nested_tool_shape_retains_raw_evidence_and_refuses_nonobject_record(self):
        self.write("p.jsonl", [meta("p", self.project), message("nearby success"),
            {"type": "response_item", "timestamp": STAMP, "payload": {"type": "function_call", "call_id": {}, "name": "tool"}},
            {"type": "response_item", "timestamp": STAMP, "payload": {"type": "function_call", "call_id": ["bad"], "name": "tool"}}])
        bundle = self.collect()
        self.assertEqual("partial", bundle["coverage"])
        self.assertEqual(3, len(bundle["observations"]))
        path = self.root / "bad-record.json"
        path.write_text("[]")
        self.assertEqual("evidence-refusal", self.cli("record", "--review", self.review, "--file", str(path), expected=2)["kind"])



    def test_current_codex_items_and_metadata_keep_unknown_shapes_partial(self):
        rows = [meta('current', self.project),
            {'timestamp': STAMP, 'type': 'world_state', 'payload': {'full': True, 'state': {'api_key': 'fixture-secret'}}},
            {'timestamp': STAMP, 'type': 'token_usage_record', 'payload': {'usage': {'total_tokens': 42}}},
            {'timestamp': STAMP, 'type': 'inter_agent_communication_metadata', 'payload': {'trigger_turn': True}},
            {'timestamp': STAMP, 'type': 'response_item', 'payload': {'type': 'agent_message', 'author': 'parent', 'recipient': 'child', 'content': [{'type': 'input_text', 'text': 'Retry failed check'}]}}]
        items = [
            {'type': 'CommandExecution', 'id': 'call-1', 'command': ['check', 'original'], 'exit_code': 1},
            {'type': 'AgentMessage', 'id': 'message-1', 'content': 'Nearby check passed'},
            {'type': 'Reasoning', 'id': 'reason-1', 'summary_text': [], 'raw_content': []},
            {'type': 'SubAgentActivity', 'id': 'spawn-1', 'agent_thread_id': 'child', 'kind': 'spawn'},
            {'type': 'FileChange', 'id': 'edit-1', 'changes': {}, 'status': 'completed'}]
        rows.extend({'timestamp': STAMP, 'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': item}} for item in items)
        self.write('current.jsonl', rows)
        bundle = self.collect()
        self.assertEqual('complete', bundle['coverage'])
        self.assertEqual(6, len(bundle['observations']))
        self.assertEqual(3, sum(n for key, n in bundle['excluded'].items() if key.startswith('non-diagnostic ')))
        self.assertTrue(all(o['supported_shape'] for o in bundle['observations']))
        self.assertTrue(any(e.get('exit') == 1 for o in bundle['observations'] for e in o['normalized']))
        self.assertTrue(any(e.get('type') == 'agent_message' for o in bundle['observations'] for e in o['normalized']))
        self.assertNotIn('fixture-secret', json.dumps(bundle))
        self.write('encrypted.jsonl', [meta('encrypted', self.project), {'timestamp': STAMP, 'type': 'response_item', 'payload': {'type': 'agent_message', 'content': [{'type': 'input_text', 'text': 'Visible message'}, {'type': 'encrypted_content', 'encrypted_content': 'opaque-fixture-bytes'}]}}])
        encrypted = self.collect()
        self.assertEqual('partial', encrypted['coverage'])
        self.assertEqual(0, sum(s['counts']['unsupported'] for s in encrypted['sources']))
        self.assertNotIn('opaque-fixture-bytes', json.dumps(encrypted))
        self.assertTrue(any(e.get('text') == 'Visible message' for o in encrypted['observations'] for e in o['normalized']))
        self.write('future.jsonl', [meta('future', self.project), {'timestamp': STAMP, 'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': {'type': 'FutureItem', 'id': 'future'}}}])
        future = self.collect()
        self.assertEqual('partial', future['coverage'])
        self.assertEqual(1, sum(s['counts']['unsupported'] for s in future['sources']))


    def test_source_failure_matrix_never_reports_clean_empty(self):
        self.selection['projects'] = []
        valid = json.dumps(meta('matrix', self.project)) + '\n' + json.dumps(message()) + '\n'
        cases = [('empty', '', 'empty', 0, 0), ('valid', valid, 'complete', 0, 0),
                 ('malformed', 'bad json\n', 'partial', 1, 0),
                 ('mixed', valid + 'bad json\n', 'partial', 1, 0),
                 ('truncated', '{"unfinished":', 'partial', 1, 1)]
        for name, raw, coverage, malformed, truncated in cases:
            with self.subTest(name=name):
                path = self.root / (name + '.jsonl')
                path.write_text(raw, encoding='utf-8')
                self.selection['sources'] = [{'kind': 'codex', 'path': str(path)}]
                bundle = self.collect()
                self.assertEqual(coverage, bundle['coverage'])
                self.assertEqual(malformed, bundle['sources'][0]['counts']['malformed'])
                self.assertEqual(truncated, bundle['sources'][0]['counts']['truncated'])
                self.assertEqual(bool(malformed), bool(bundle['gaps']))
        self.selection['sources'] = [{'kind': 'codex', 'path': str(self.root / 'absent.jsonl')}]
        self.assertEqual('unavailable', self.collect()['coverage'])
        self.selection['sources'].append({'kind': 'codex', 'path': str(self.root / 'empty.jsonl')})
        self.assertEqual('partial', self.collect()['coverage'])

    def test_nested_legacy_content_and_opaque_reasoning_are_gaps(self):
        self.write('nested.jsonl', [meta('nested', self.project), {'timestamp': STAMP, 'type': 'response_item', 'payload': {'type': 'message', 'role': 'assistant', 'content': [{'type': 'future_content', 'data': {}}]}}])
        bundle = self.collect()
        self.assertEqual('partial', bundle['coverage'])
        self.assertEqual(1, bundle['sources'][0]['counts']['unsupported'])
        self.write('nested.jsonl', [meta('nested', self.project), {'timestamp': STAMP, 'type': 'response_item', 'payload': {'type': 'reasoning', 'summary': [], 'encrypted_content': 'opaque-reasoning'}}])
        bundle = self.collect()
        self.assertEqual('partial', bundle['coverage'])
        self.assertEqual(0, bundle['sources'][0]['counts']['unsupported'])
        self.assertTrue(any('opaque encrypted' in gap['reason'] for gap in bundle['gaps']))
        self.assertNotIn('opaque-reasoning', json.dumps(bundle))


if __name__ == "__main__":
    unittest.main()
