"""Seam checks for ordinary play provenance and presented-frame evidence."""
import json
import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "example-workflows" / "3d-browser-game" / "scripts"
FIXTURES = ROOT / "example-workflows" / "3d-browser-game" / "references" / "performance-qualification"
NODE = "node"


def node_module(module, expression):
    script = f"import * as m from {json.dumps('./' + module)}; {expression}"
    return subprocess.run(
        [NODE, "--input-type=module", "-e", script], cwd=ROOT,
        capture_output=True, text=True, encoding="utf-8", timeout=30,
    )


class BrowserGamePlayEvidenceTests(unittest.TestCase):
    def fixture(self, name):
        return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))

    def qualify(self, fixture):
        expression = (
            "const f=" + json.dumps(fixture) + "; "
            "console.log(JSON.stringify(m.qualifyPerformance({cell:f.cell,trace:f.trace,callbacks:f.callbacks})));"
        )
        result = node_module("example-workflows/3d-browser-game/scripts/trace_frames.mjs", expression)
        self.assertEqual(0, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def test_the_four_qualification_boundaries_are_explicit(self):
        self.assertEqual("qualified", self.qualify(self.fixture("static-idle"))["status"])
        self.assertEqual("qualified", self.qualify(self.fixture("continuous-animation"))["status"])
        stall = self.qualify(self.fixture("deliberate-stall"))
        self.assertEqual("unverified", stall["status"])
        self.assertIn("unexplained-stall", [item["code"] for item in stall["failures"]])
        other_layer = self.qualify(self.fixture("canvas-stall-other-layer"))
        self.assertEqual("unverified", other_layer["status"])
        self.assertIn("canvas-frame-floor", [item["code"] for item in other_layer["failures"]])

    def test_overlapping_dropped_and_partial_flags_count_once(self):
        fixture = self.fixture("continuous-animation")
        fixture["trace"]["traceEvents"][10]["dropped"] = True
        fixture["trace"]["traceEvents"][10]["isPartial"] = True
        result = self.qualify(fixture)
        self.assertEqual(1, result["metrics"]["D"])

    def test_loss_and_missing_canvas_attribution_fail_closed(self):
        fixture = self.fixture("continuous-animation")
        fixture["trace"]["completion"]["dataLossOccurred"] = True
        self.assertEqual("unverified", self.qualify(fixture)["status"])
        fixture = self.fixture("continuous-animation")
        for event in fixture["trace"]["traceEvents"]:
            event.pop("attribution", None)
            event.pop("canvas", None)
        result = self.qualify(fixture)
        self.assertEqual("unverified", result["status"])
        self.assertIn("missing-canvas-attribution", [item["code"] for item in result["failures"]])

    def test_native_snapshot_binds_canvas_to_same_renderer_frames(self):
        trace = {
            "format": "cdp-return-as-stream",
            "completion": {"dataLossOccurred": False, "stream": "1", "transferMode": "ReturnAsStream"},
            "traceEvents": [
                {"name": "LayerTreeHostImpl:snapshot", "ts": 1000000, "pid": 7, "args": {"snapshot": {"active_tree": {"layers": [{"layer_name": "LayoutHTMLCanvas CANVAS id='game'", "layer_id": 6}]}}}},
                {"name": "BeginFrame", "ts": 1001000, "pid": 7, "args": {"frameSeqId": 1, "layerTreeId": 2}},
                {"name": "DrawFrame", "ts": 1001500, "pid": 7, "args": {"frameSeqId": 1, "layerTreeId": 2}},
            ],
        }
        expression = (
            "const r=m.buildFrameModel(" + json.dumps(trace) + ", "
            "{target:{canvas_selector:'#game'},startMs:0,endMs:2000}); "
            "console.log(JSON.stringify({attributed:r.attributed,frames:r.frames.length,ambiguous:r.ambiguous}));"
        )
        result = node_module("example-workflows/3d-browser-game/scripts/trace_frames.mjs", expression)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual({"attributed": 1, "frames": 1, "ambiguous": False}, json.loads(result.stdout))

    def test_input_label_cannot_be_spoofed_in_a_jsonl_command(self):
        result = node_module(
            "example-workflows/3d-browser-game/scripts/browser_harness.mjs",
            "try { m.validateCommand({type:'key',key:'w',action:'down',classification:'actual_play'}); process.exit(9); } "
            "catch (error) { console.log(JSON.stringify({code:error.code,pointer:error.pointer,message:error.message})); }",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('"code":"invalid-input"', result.stdout)
        self.assertIn('"pointer":"/classification"', result.stdout)

    def actual_session(self):
        snapshot = {"url": "http://127.0.0.1:3000/", "canvas_count": 1, "canvases": [{"width": 640, "height": 360, "connected": True}], "facts": []}
        transcript = [
            {"command": {"type": "observe"}, "reply": {"sequence": 1, "monotonic_ms": 1, "wall_time": "2026-09-06T00:00:01Z", "type": "observe", "status": "ok", "snapshot": snapshot, "screenshot_hash": "sha256:" + "1" * 64}},
            {"command": {"type": "key", "key": "w", "action": "down"}, "reply": {"sequence": 2, "monotonic_ms": 2, "wall_time": "2026-09-06T00:00:02Z", "type": "key", "status": "ok", "snapshot": snapshot}},
            {"command": {"type": "observe"}, "reply": {"sequence": 3, "monotonic_ms": 3, "wall_time": "2026-09-06T00:00:03Z", "type": "observe", "status": "ok", "snapshot": snapshot, "screenshot_hash": "sha256:" + "2" * 64}},
            {"command": {"type": "stop"}, "reply": {"sequence": 4, "monotonic_ms": 4, "wall_time": "2026-09-06T00:00:04Z", "type": "stop", "status": "ok", "snapshot": snapshot}},
        ]
        transcript_bytes = (json.dumps(transcript, sort_keys=True, indent=2) + "\n").encode("utf-8")
        return {
            "schema_version": "1.0.0", "kind": "play-session", "id": "session-positive",
            "artifact_commit": "git:" + "a" * 40, "created_at": "2026-09-06T00:00:00Z", "producer": {"name": "browser_harness.mjs"},
            "inputs": [], "environment": {"host": "codex", "os": "windows", "tools": [], "browser": "chromium", "browser_version": "124.0", "driver": "playwright-core"},
            "status": "complete", "gaps": [], "invalidates": [], "classification": "actual_play", "input_mode": "actual_play", "source": "live-browser", "headed": True,
            "url": "http://127.0.0.1:3000/", "operator": "operator-a", "independent_context_id": "context-a", "started_at": "2026-09-06T00:00:00Z", "ended_at": "2026-09-06T00:00:05Z",
            "transcript": transcript, "transcript_hash": "sha256:" + hashlib.sha256(transcript_bytes).hexdigest(),
            "adaptation": {"observation_sequence": 1, "action_sequence": 2, "subsequent_observation_sequence": 3, "rationale": "The observed state showed the player could advance, so the next input tested movement."},
        }

    def test_actual_play_requires_successful_causal_snapshots_and_accepts_harness_shape(self):
        session = self.actual_session()
        expression = "const s=" + json.dumps(session) + "; console.log(JSON.stringify(m.validatePlaySession(s)));"
        result = node_module("example-workflows/3d-browser-game/scripts/validate_evidence.mjs", expression)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("actual_play", json.loads(result.stdout)["requested"])

        session["transcript"][1]["reply"]["status"] = "error"
        expression = "const s=" + json.dumps(session) + "; try { m.validatePlaySession(s); process.exit(9); } catch (error) { console.log(JSON.stringify({code:error.code,pointer:error.pointer})); }"
        result = node_module("example-workflows/3d-browser-game/scripts/validate_evidence.mjs", expression)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('"code":"evidence-failure"', result.stdout)

    def test_frozen_performance_plan_requires_declared_scenario_coverage(self):
        plan = {
            "schema_version": "1.0.0", "kind": "performance-plan", "id": "plan-positive",
            "artifact_commit": "git:" + "a" * 40, "created_at": "2026-09-06T00:00:00Z",
            "producer": {"name": "test"}, "inputs": [], "environment": {"host": "test", "os": "windows", "tools": []},
            "status": "draft", "gaps": [], "invalidates": [],
            "scenarios": [{"scenario_id": "arena", "cells": ["arena-cell"], "required_runs": 3, "min_duration_seconds": 60, "animated": True}],
        }
        expression = "const p=" + json.dumps(plan) + "; console.log(JSON.stringify(m.validatePerformancePlan(p)));"
        result = node_module("example-workflows/3d-browser-game/scripts/validate_evidence.mjs", expression)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("arena", json.loads(result.stdout)["scenarios"][0]["id"])

        plan["scenarios"][0]["required_runs"] = 2
        expression = "const p=" + json.dumps(plan) + "; try { m.validatePerformancePlan(p); process.exit(9); } catch (error) { console.log(JSON.stringify({code:error.code,pointer:error.pointer})); }"
        result = node_module("example-workflows/3d-browser-game/scripts/validate_evidence.mjs", expression)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('"code":"evidence-failure"', result.stdout)

    def test_fixture_collector_and_validator_preserve_hash_bound_record(self):
        fixture = self.fixture("continuous-animation")
        cell = {**fixture["cell"], "artifact_commit": "git:" + "a" * 40, "trace": fixture["trace"], "callbacks": fixture["callbacks"]}
        with tempfile.TemporaryDirectory() as directory:
            cell_path = Path(directory) / "cell.json"
            out_dir = Path(directory) / "out"
            cell_path.write_text(json.dumps(cell), encoding="utf-8")
            collected = subprocess.run(
                [NODE, str(SCRIPTS / "performance_collect.mjs"), "--cell", str(cell_path), "--out", str(out_dir)],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
            )
            self.assertEqual(0, collected.returncode, collected.stderr + collected.stdout)
            result_path = out_dir / "cell-result.json"
            self.assertTrue(result_path.exists())
            checked = subprocess.run(
                [NODE, str(SCRIPTS / "validate_evidence.mjs"), "performance", "--cell", str(result_path)],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
            )
            self.assertEqual(0, checked.returncode, checked.stderr + checked.stdout)

    def test_outside_probe_requires_current_ordinary_input(self):
        result = node_module(
            "example-workflows/3d-browser-game/scripts/outside_probe.mjs",
            "try { m.probeTranscript([{type:'ready'},{type:'observe'},{type:'stop'}],'git:x'); process.exit(9); } "
            "catch (error) { console.log(JSON.stringify({code:error.code,pointer:error.pointer,message:error.message})); }",
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("ordinary input", result.stdout)

    def test_outside_probe_accepts_timestamped_rendered_observation_sequence(self):
        commit = "git:" + "a" * 40
        snapshot = {"url": "http://127.0.0.1:3000/", "canvas_count": 1, "canvases": [{"width": 640, "height": 360, "connected": True}]}
        transcript = [
            {"type": "ready", "status": "ready", "artifact_commit": commit, "session_id": "outside-a", "sequence": 1, "monotonic_ms": 0, "wall_time": "2026-09-06T00:00:00Z"},
            {"type": "observe", "status": "ok", "artifact_commit": commit, "session_id": "outside-a", "sequence": 2, "monotonic_ms": 1, "wall_time": "2026-09-06T00:00:01Z", "snapshot": snapshot, "screenshot_hash": "sha256:" + "1" * 64},
            {"type": "key", "status": "ok", "artifact_commit": commit, "session_id": "outside-a", "sequence": 3, "monotonic_ms": 2, "wall_time": "2026-09-06T00:00:02Z", "snapshot": snapshot},
            {"type": "observe", "status": "ok", "artifact_commit": commit, "session_id": "outside-a", "sequence": 4, "monotonic_ms": 3, "wall_time": "2026-09-06T00:00:03Z", "snapshot": snapshot, "screenshot_hash": "sha256:" + "2" * 64},
            {"type": "stop", "status": "ok", "artifact_commit": commit, "session_id": "outside-a", "sequence": 5, "monotonic_ms": 4, "wall_time": "2026-09-06T00:00:04Z", "snapshot": snapshot},
        ]
        expression = "const t=" + json.dumps(transcript) + "; console.log(JSON.stringify(m.probeTranscript(t," + json.dumps(commit) + ")));"
        result = node_module("example-workflows/3d-browser-game/scripts/outside_probe.mjs", expression)
        self.assertEqual(0, result.returncode, result.stderr)
        observed = json.loads(result.stdout)
        self.assertEqual("observed", observed["status"])
        self.assertTrue(observed["ordinary_input"])

    def test_evidence_index_rehashes_entries_and_rejects_stale_bytes(self):
        fixture = self.fixture("continuous-animation")
        cell = {**fixture["cell"], "artifact_commit": "git:" + "a" * 40, "trace": fixture["trace"], "callbacks": fixture["callbacks"]}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cell_path = root / "cell.json"
            out_dir = root / "out"
            cell_path.write_text(json.dumps(cell), encoding="utf-8")
            collected = subprocess.run(
                [NODE, str(SCRIPTS / "performance_collect.mjs"), "--cell", str(cell_path), "--out", str(out_dir)],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
            )
            self.assertEqual(0, collected.returncode, collected.stderr + collected.stdout)
            result_path = out_dir / "cell-result.json"
            digest = "sha256:" + hashlib.sha256(result_path.read_bytes()).hexdigest()
            index = {
                "schema_version": "1.0.0", "kind": "evidence-index", "id": "index-fixture",
                "artifact_commit": "git:" + "a" * 40, "created_at": "2026-09-06T00:00:00Z",
                "producer": {"name": "test"}, "inputs": [], "environment": {"host": "test", "os": "windows", "tools": []},
                "status": "draft", "gaps": [], "invalidates": [], "declared_ancestors": [],
                "entries": [{"path": "out/cell-result.json", "kind": "performance", "sha256": digest, "revision": "same-artifact"}],
            }
            index_path = root / "index.json"
            index_path.write_text(json.dumps(index), encoding="utf-8")
            promoted = subprocess.run(
                [NODE, str(SCRIPTS / "validate_evidence.mjs"), "--index", str(index_path), "--promote"],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
            )
            self.assertEqual(0, promoted.returncode, promoted.stderr + promoted.stdout)
            promoted_index = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertRegex(promoted_index["promotion"]["result_identity"], r"^sha256:[0-9a-f]{64}$")
            checked = subprocess.run(
                [NODE, str(SCRIPTS / "validate_evidence.mjs"), "--index", str(index_path)],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
            )
            self.assertEqual(0, checked.returncode, checked.stderr + checked.stdout)
            forged = dict(promoted_index)
            forged["promotion"] = dict(promoted_index["promotion"], result_identity="sha256:" + "0" * 64)
            forged_path = root / "forged-index.json"
            forged_path.write_text(json.dumps(forged), encoding="utf-8")
            forged_result = subprocess.run(
                [NODE, str(SCRIPTS / "validate_evidence.mjs"), "--index", str(forged_path)],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
            )
            self.assertEqual(4, forged_result.returncode, forged_result.stderr + forged_result.stdout)
            result_path.write_bytes(result_path.read_bytes() + b"\n")
            stale = subprocess.run(
                [NODE, str(SCRIPTS / "validate_evidence.mjs"), "--index", str(index_path)],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=30,
            )
            self.assertEqual(4, stale.returncode, stale.stderr + stale.stdout)


if __name__ == "__main__":
    unittest.main()
