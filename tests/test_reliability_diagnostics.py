"""Occurrence attribution, privacy and bounded acquisition at public seams."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest

from scripts import state_root, trace
from tests import test_self_improve as fixtures


class Diagnostics(unittest.TestCase):
    setUp = fixtures.SelfImprove.setUp
    write = fixtures.SelfImprove.write
    cli = fixtures.SelfImprove.cli
    collect = fixtures.SelfImprove.collect

    def test_occurrences_and_same_timestamp_calls_keep_exact_origin(self):
        call = {"timestamp": fixtures.STAMP, "type": "response_item", "payload": {
            "type": "function_call", "name": "exec_command", "call_id": "call", "arguments": '{"cmd":"false"}'}}
        output = {"timestamp": fixtures.STAMP, "type": "response_item", "payload": {
            "type": "function_call_output", "call_id": "call", "output": "Exit code: 7"}}
        self.write("a.jsonl", [fixtures.meta("a", self.project), fixtures.message("same"), call, output])
        self.write("b.jsonl", [fixtures.meta("b", self.project), fixtures.message("same"), fixtures.message("different")])
        bundle = self.collect()
        self.assertEqual(5, len(bundle["observations"]))
        calls = [(o, e) for o in bundle["observations"] for e in o["normalized"] if e["type"] == "tool_call"]
        self.assertEqual(1, len(calls))
        origin, event = calls[0]
        self.assertEqual(("a", "false", 7), (origin["session"], event["command"], event["exit"]))
        self.assertEqual([origin["id"]], event["observation_ids"])
        for observation in bundle["observations"]:
            for event in observation["normalized"]:
                self.assertEqual([observation["id"]], event["observation_ids"])

    def test_excluded_historical_shape_and_stalled_are_not_selected_gaps(self):
        self.write("a.jsonl", [fixtures.meta("a", self.project),
            {"timestamp": "2020-01-01T00:00:00Z", "type": "future"}, fixtures.message()])
        self.assertEqual("complete", self.collect()["coverage"])
        self.write("events.jsonl", [{"ts": fixtures.STAMP, "event": "stalled"}])
        self.selection["projects"] = []
        self.selection["sources"] = [{"kind": "events", "path": str(self.logs / "events.jsonl")}]
        self.assertEqual("complete", self.collect()["coverage"])
        self.write("events.jsonl", [{"ts": fixtures.STAMP, "event": "future"}])
        self.assertEqual("partial", self.collect()["coverage"])

    def test_current_trace_failure_cmd_and_validated_usage(self):
        row = {"timestamp": fixtures.STAMP, "type": "event_msg", "payload": {
            "type": "item_completed", "item": {"id": "item", "type": "CommandExecution", "command": ["false"], "exit_code": 7}}}
        path = self.write("a.jsonl", [fixtures.meta("a", self.project), row,
            {"timestamp": fixtures.STAMP, "type": "token_usage_record", "payload": {
                "usage": {"input_tokens": 12, "output_tokens": 3, "api_token": "credential"}}}])
        event = trace.extract_codex(path)["events"][0]
        self.assertEqual(("false", 7), (event["command"], event["exit"]))
        self.assertEqual("check", trace._extract_codex_command({"arguments": {"cmd": "check"}}))
        bundle = self.collect()
        rendered = json.dumps(bundle)
        self.assertNotIn("credential", rendered)
        self.write("a.jsonl", [fixtures.meta("a", self.project),
            {"timestamp": fixtures.STAMP, "type": "token_usage_record", "payload": {
                "usage": {"input_tokens": 12, "output_tokens": 3}}}])
        usage = self.collect()["structural_context"][-1]["record"]["payload"]["usage"]
        self.assertEqual({"input_tokens": 12, "output_tokens": 3}, usage)
        self.write("a.jsonl", [fixtures.meta("a", self.project),
            {"timestamp": fixtures.STAMP, "type": "token_usage_record", "payload": {
                "usage": {"input_tokens": "12-secret", "output_tokens": True}}}])
        rendered = json.dumps(self.collect())
        self.assertNotIn("12-secret", rendered)

    def test_home_git_sink_requires_ignored_untracked_private_destination(self):
        home = self.root / "home"
        home.mkdir()
        subprocess.run(["git", "init", "-q", str(home)], check=True, timeout=10)
        self.env[state_root.ENV_VAR] = str(home / "state")
        self.write("a.jsonl", [fixtures.meta("a", self.project), fixtures.message()])
        selection = self.root / "selection.json"
        selection.write_text(json.dumps(self.selection))
        self.cli("collect", "--selection", str(selection), expected=2)
        (home / ".gitignore").write_text("state/improvement/\n")
        self.collect()
        tracked = home / "state" / "improvement" / "tracked"
        tracked.write_text("private")
        subprocess.run(["git", "-C", str(home), "add", "-f", str(tracked)], check=True, timeout=10)
        self.cli("collect", "--selection", str(selection), expected=2)

    def test_budget_partial_hash_continuation_and_bounded_page_without_bundle(self):
        path = self.write("a.jsonl", [fixtures.meta("a", self.project)] + [fixtures.message(str(i)) for i in range(100)])
        selection = self.root / "selection.json"
        selection.write_text(json.dumps(self.selection))
        result = self.cli("collect", "--selection", str(selection), "--disk-budget", "1500")
        self.assertEqual("partial", result["coverage"])
        self.assertNotIn("gaps", result)
        source = self.cli("show", "--review", result["review"], "--section", "sources")["items"][0]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source["sha256"])
        self.assertGreater(source["continuation"]["byte"], 0)
        from pathlib import Path
        Path(result["bundle"]).rename(Path(result["bundle"]).with_suffix(".hidden"))
        page = self.cli("show", "--review", result["review"], "--section", "observations", "--limit", "1")
        self.assertEqual(1, len(page["items"]))
        self.assertIsNotNone(page["next_offset"])

    def test_mutating_source_keeps_observed_prefix_hash_and_declares_gap(self):
        code = r"""
import hashlib, json, sys, tempfile
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, sys.argv[1])
from improve_sources import snapshot
with tempfile.TemporaryDirectory() as directory:
    path = Path(directory) / 'source.jsonl'
    original = b'{"type":"observation","ts":"2026-09-07T10:00:00Z"}\n'
    path.write_bytes(original)
    original_open = Path.open
    class MutatingRead:
        def __enter__(self):
            self.stream = original_open(path, 'rb')
            return self.stream
        def __exit__(self, *args):
            self.stream.close()
            with original_open(path, 'ab') as stream:
                stream.write(b'{"appended":true}\n')
    def changed_open(target, *args, **kwargs):
        return MutatingRead() if target == path and args == ('rb',) else original_open(target, *args, **kwargs)
    with patch.object(Path, 'open', changed_open):
        source, rows = snapshot(path, 'other')
    assert source['sha256'] == hashlib.sha256(original).hexdigest()
    assert source['coverage'] == 'partial'
    assert source['size'] == len(original)
    assert len(rows) == 1
    assert any('changed' in gap for gap in source['gaps'])
    rows.close()
"""
        result = subprocess.run([sys.executable, "-c", code, str(fixtures.SCRIPTS)], capture_output=True, text=True, timeout=30)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_scaled_history_and_selected_payload_have_bounded_resident_memory(self):
        code = r"""
import ctypes, hashlib, json, os, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from improve_collect import collect
from improve_store import create, show
count, selected = int(sys.argv[2]), sys.argv[3] == 'selected'
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    os.environ['ORCHFLOWS_STATE_HOME'] = str(root / 'sink')
    # Read the environment key from its owner in case the host spelling changes.
    import state_root
    os.environ[state_root.ENV_VAR] = str(root / 'sink')
    path = root / 'rows.jsonl'
    hasher = hashlib.sha256()
    with path.open('wb') as stream:
        for index in range(count):
            row = {'type':'observation', 'ts':'2026-09-07T10:00:00Z' if selected or index == count - 1 else '2020-01-01T00:00:00Z', 'text':'x' * 2048, 'index':index}
            data = (json.dumps(row) + '\n').encode()
            hasher.update(data)
            stream.write(data)
    frozen = {'mode':'review','timezone':'UTC','timezone_provenance':'fixture','as_of':'2026-09-08T00:00:00Z','start':'2026-09-07T00:00:00Z','end':'2026-09-08T00:00:00Z','sources':[{'kind':'other','path':str(path)}],'projects':[],'sessions':[],'runs':[],'descendants':True,'repair_bound':2}
    bundle = collect(frozen, disk_budget=64 * 1024 * 1024)
    assert bundle['sources'][0]['sha256'] == hasher.hexdigest()
    result = create(bundle)
    page = show(result['review'], 'observations', 0, 1)
    assert len(page['items']) == 1
    assert result['counts']['observations'] == (count if selected else 1)
    if os.name == 'nt':
        class Counters(ctypes.Structure):
            _fields_ = [('cb',ctypes.c_ulong),('faults',ctypes.c_ulong)] + [(key,ctypes.c_size_t) for key in ('peak','working','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        process = ctypes.windll.kernel32.GetCurrentProcess
        process.restype = ctypes.c_void_p
        assert ctypes.windll.psapi.GetProcessMemoryInfo(ctypes.c_void_p(process()), ctypes.byref(counters), counters.cb)
        peak = counters.peak
    else:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == 'darwin' else 1024)
    print(json.dumps({'rows':count,'selected':selected,'peak_bytes':peak,'budget_bytes':64*1024*1024,'source_bytes':path.stat().st_size,'observations':result['counts']['observations']}))
"""
        readings = []
        for selected in ("irrelevant", "selected"):
            for count in (1000, 12000):
                result = subprocess.run([sys.executable, "-c", code, str(fixtures.SCRIPTS), str(count), selected],
                                        capture_output=True, text=True, timeout=180)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                readings.append(json.loads(result.stdout))
            self.assertLess(readings[-1]["peak_bytes"] - readings[-2]["peak_bytes"], 12 * 1024 * 1024)
            self.assertLess(readings[-1]["peak_bytes"], 80 * 1024 * 1024)
        print("diagnostics resident memory " + json.dumps(readings))


if __name__ == "__main__":
    unittest.main()
