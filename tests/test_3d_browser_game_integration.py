"""End-to-end admission fixtures for the browser-game gate contract.

The fixture is deliberately temporary and its performance rows carry an
explicit ``controlled-test-fixture`` diagnostic.  The rows exercise the live
evidence shape required by the gate and are never shipped as game proof.
"""

from copy import deepcopy
import hashlib
import json
import shutil
import struct
import subprocess
import tempfile
import unittest
from pathlib import Path


# This test resolves its repository-owned fixture and package paths from the
# checkout root; the climb belongs to this test owner, not a wildcard exemption.
ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "example-workflows" / "3d-browser-game" / "scripts"
PERF_FIXTURE = ROOT / "example-workflows" / "3d-browser-game" / "references" / "performance-qualification" / "continuous-animation.json"
NODE = "node"


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def digest(value):
    return "sha256:" + hashlib.sha256(value).hexdigest()


def commit(value):
    return "git:" + value


def header(kind, identity, artifact_commit):
    return {
        "schema_version": "1.0.0", "kind": kind, "id": identity,
        "artifact_commit": artifact_commit, "created_at": "2026-09-06T00:00:00Z",
        "producer": {"name": "integration-fixture", "version": "1"},
        "inputs": [], "environment": {"host": "fixture", "os": "windows", "tools": []},
        "status": "complete", "gaps": [], "invalidates": [],
    }


class GateFixture:
    CORE_HARD = [
        "production-boot", "focus-controls", "fundamental-loop",
        "central-mechanics-state-transitions", "core-progression-content-paths",
        "terminal-continuing-behavior", "replay-reentry",
        "readable-feedback-camera-collision", "no-undisclosed-placeholder",
        "complete-core-captures", "qualified-representative-performance",
    ]
    FINAL_HARD = [
        "clean-production-boot", "documented-controls-focus", "all-prompt-concept-promises",
        "mechanics-content-progression", "terminal-continuing-behavior", "replay-reentry",
        "no-blocking-errors-placeholders", "asset-provenance-disposal",
        "complete-capture-adaptive-play", "performance-cell-coverage",
    ]
    CORE_DIMS = [
        "loop-purpose-clarity", "controls-camera-feel", "interaction-feedback-readability",
        "fairness-challenge", "meaningful-choice-progression", "pacing-continued-engagement",
        "prompt-fidelity", "stability",
    ]
    FINAL_DIMS = [
        "prompt-fidelity", "loop-purpose", "controls-camera", "feedback-readability-fairness",
        "challenge-choice-pacing-engagement", "level-world-coherence",
        "3d-art-animation-motion-coherence", "promised-ui-audio-accessibility", "stability", "polish",
    ]

    def __init__(self, root):
        self.root = root
        self.core_commit = self.git_parent()
        self.final_commit = self.git_head()
        self.brief_hash = digest(canonical({"promises": ["promise-loop", "promise-terminal"]}))

    def git_head(self):
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assert_command(result, "git rev-parse HEAD")
        return result.stdout.strip()

    def git_parent(self):
        result = subprocess.run(["git", "rev-parse", "HEAD^"], cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assert_command(result, "git rev-parse HEAD^")
        return result.stdout.strip()

    def assert_command(self, result, label):
        if result.returncode:
            raise AssertionError(f"{label} failed with exit {result.returncode}: {result.stderr}\n{result.stdout}")

    def write_bytes(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
        return path

    def write_json(self, relative, value):
        return self.write_bytes(relative, canonical(value))

    def entry(self, identity, relative, kind, artifact_commit, revision="same-artifact", source_commit=None):
        value = {"id": identity, "path": relative.replace("\\", "/"), "kind": kind, "sha256": digest((self.root / relative).read_bytes()), "revision": revision}
        if source_commit is not None:
            value["source_commit"] = source_commit
        return value

    def asset_manifest(self, artifact_commit, directory):
        asset_dir = self.root / directory
        source = self.write_bytes(f"{directory}/source.blend", b"controlled source blend bytes\n")
        glb = self.write_bytes(f"{directory}/asset.glb", self.triangle_glb())
        self.write_json(f"{directory}/inspection.json", {"meshes": 1, "materials": 1, "animations": 0})
        self.write_bytes(f"{directory}/preview.png", b"controlled preview bytes\n")
        glb_hash = digest(glb.read_bytes())
        target = self.root / f"{directory}/target-three"
        self.write_bytes(f"{directory}/target-three/build/three.module.js", b"three module fixture\n")
        self.write_bytes(f"{directory}/target-three/examples/jsm/loaders/GLTFLoader.js", b"loader module fixture\n")
        three_hash = digest((target / "build/three.module.js").read_bytes())
        loader_hash = digest((target / "examples/jsm/loaders/GLTFLoader.js").read_bytes())
        screenshot = self.write_bytes(f"{directory}/loader.png", b"retained loader screenshot bytes\n")
        screenshot_hash = digest(screenshot.read_bytes())
        loader_id = f"loader-evidence-{directory.replace('/', '-')}"
        loader_document = {
            "kind": "gltf-loader-evidence", "id": loader_id, "artifact_commit": artifact_commit,
            "source": "live-browser", "glb_hash": glb_hash, "target_workspace": str(target),
            "target_probe": {"path": "loader.png", "sha256": screenshot_hash},
            "browser": {"screenshot_sha256": screenshot_hash},
            "target_three_root": {"path": ".", "three_module_sha256": three_hash, "gltf_loader_sha256": loader_hash},
            "observed": {"meshes": 1, "materials": 1, "animations": 0},
            "checks": {"scale": "pass", "material": "pass", "animation": "pass", "collider": "pass"},
        }
        loader_path = self.write_json(f"{directory}/loader.json", loader_document)
        khronos_document = {
            "issues": {"numErrors": 0},
            "orchflows": {"kind": "khronos-validation", "source": "package-owned-fresh-process", "artifact_commit": artifact_commit, "glb_hash": glb_hash},
        }
        khronos_path = self.write_json(f"{directory}/khronos.json", khronos_document)
        manifest = header("asset-manifest", "asset", artifact_commit)
        manifest.update({
            "source_kind": "generated", "source_blend": "source.blend", "source_blend_sha256": digest(source.read_bytes()),
            "runtime_glb": "asset.glb", "exported_glb_sha256": glb_hash, "inspection": "inspection.json", "previews": ["preview.png"],
            "units": "meters", "unit_scale": 1, "up_axis": "+Y", "gameplay_forward": "+Z", "origin": "feet",
            "colliders": [], "attachments": [], "material_roles": {"body": "body"}, "animation_clips": [], "required_extensions": [],
            "validation": {
                "khronos": {"status": "pass", "errors": 0, "export_sha256": glb_hash, "validator": "gltf-validator", "report_path": "khronos.json", "report_sha256": digest(khronos_path.read_bytes())},
                "gltf_loader": {"status": "pass", "artifact_commit": artifact_commit, "evidence_id": loader_id, "glb_hash": glb_hash, "checks": {"scale": "pass", "material": "pass", "animation": "pass", "collider": "pass"}, "evidence_path": "loader.json", "evidence_sha256": digest(loader_path.read_bytes())},
            },
        })
        self.write_json(f"{directory}/manifest.json", manifest)
        return f"{directory}/manifest.json", manifest["id"]

    @staticmethod
    def triangle_glb():
        payload = {
            "asset": {"version": "2.0"}, "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0}],
            "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "mode": 4}]}],
            "buffers": [{"byteLength": 36}], "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": 36, "target": 34962}],
            "accessors": [{"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3", "min": [0, 0, 0], "max": [1, 1, 0]}],
        }
        encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        encoded += b" " * ((4 - len(encoded) % 4) % 4)
        binary = struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0)
        body = struct.pack("<I4s", len(encoded), b"JSON") + encoded + struct.pack("<I4s", len(binary), b"BIN\x00") + binary
        return struct.pack("<4sII", b"glTF", 2, 12 + len(body)) + body

    def play_session(self, artifact_commit, identity, operator, context):
        snapshot = {"url": "http://127.0.0.1:3000/", "canvas_count": 1, "canvases": [{"width": 640, "height": 360, "connected": True}], "facts": []}
        transcript = [
            {"command": {"type": "observe"}, "reply": {"sequence": 1, "monotonic_ms": 1, "wall_time": "2026-09-06T00:00:01Z", "type": "observe", "status": "ok", "snapshot": snapshot, "screenshot_hash": "sha256:" + "1" * 64}},
            {"command": {"type": "key", "key": "w", "action": "down"}, "reply": {"sequence": 2, "monotonic_ms": 2, "wall_time": "2026-09-06T00:00:02Z", "type": "key", "status": "ok", "snapshot": snapshot}},
            {"command": {"type": "observe"}, "reply": {"sequence": 3, "monotonic_ms": 3, "wall_time": "2026-09-06T00:00:03Z", "type": "observe", "status": "ok", "snapshot": snapshot, "screenshot_hash": "sha256:" + "2" * 64}},
            {"command": {"type": "stop"}, "reply": {"sequence": 4, "monotonic_ms": 4, "wall_time": "2026-09-06T00:00:04Z", "type": "stop", "status": "ok", "snapshot": snapshot}},
        ]
        value = header("play-session", identity, artifact_commit)
        value.update({
            "classification": "actual_play", "input_mode": "actual_play", "source": "live-browser", "headed": True,
            "url": snapshot["url"], "operator": operator, "independent_context_id": context,
            "started_at": "2026-09-06T00:00:00Z", "ended_at": "2026-09-06T00:00:05Z", "transcript": transcript,
            "transcript_hash": digest(canonical(transcript)), "adaptation": {"observation_sequence": 1, "action_sequence": 2, "subsequent_observation_sequence": 3, "rationale": "The observed state guided the movement input."},
        })
        value["environment"].update({"browser": "chromium", "browser_version": "124.0", "driver": "playwright-core"})
        return value

    def performance_cell(self, artifact_commit, scenario, cell_id, run_number):
        fixture = json.loads(PERF_FIXTURE.read_text(encoding="utf-8"))
        trace = deepcopy(fixture["trace"])
        repeated_events = []
        for cycle in range(60):
            for event in trace["traceEvents"]:
                repeated = deepcopy(event)
                repeated["timestamp_ms"] += cycle * 1000
                repeated["id"] = f"{event['id']}-{cycle}"
                repeated_events.append(repeated)
        trace["traceEvents"] = repeated_events
        trace["metadata"]["window_start_ms"] = -6000
        trace["metadata"]["window_end_ms"] = 66000
        callbacks = [value + cycle * 1000 for cycle in range(60) for value in fixture["callbacks"]]
        cell = deepcopy(fixture["cell"])
        cell.update({"id": cell_id, "scenario_id": scenario, "artifact_commit": artifact_commit, "duration_seconds": 60, "run_id": f"{cell_id}-run-{run_number}"})
        cell["window"] = {"start_ms": 0, "end_ms": 60000}
        cell["game_canvas"] = {"layer_ids": ["canvas-layer"]}
        sampling = {
            "explicit": True, "coordinate_space": "viewport",
            "requested_region": {"x": 0, "y": 0, "width": 1, "height": 1},
            "resolved_region": {"x": 0, "y": 719, "width": 1, "height": 1},
            "drawing_buffer": {"width": 1280, "height": 720},
            "viewport": {"width": 1280, "height": 720}, "dpr": 1,
            "sample_pixels": 1, "bytes_per_sample": 4,
            "origin": "viewport-top-left-to-webgl-bottom-left",
        }
        cell["sampling"] = sampling
        measurement = {
            "scenario_id": scenario, "observer": "render-callback-post-callback", "presentation": "render-callback-post-callback", "preserve_drawing_buffer": False,
            "sampling": sampling,
            "lifecycle": {
                "status": "observed", "scenario_id": scenario, "seed": 1,
                "configured_url": "http://127.0.0.1:3000/", "viewport": {"width": 1280, "height": 720}, "dpr": 1,
                "start": {"method": "page.goto", "observed": True},
                "reset": {"method": "page.reload", "observed": True},
                "phase_transitions": [
                    {"phase": "control", "start_observed": True},
                    {"phase": "instrumented", "start_observed": True},
                ],
            },
            "warmup": {"status": "observed", "requested_ms": 1000, "observed_ms": 1000, "callbacks": 60, "callback_rate_hz": 60},
            "control": {"status": "observed", "requested_ms": 60000, "observed_ms": 60000, "callbacks": 3600, "callback_rate_hz": 60},
            "instrumented": {"status": "observed", "requested_ms": 60000, "observed_ms": 60000, "callbacks": 3600, "callback_rate_hz": 60, "samples": 3600, "readback_errors": 0},
            "perturbation": {"status": "observed", "basis": "control-vs-instrumented", "control_callbacks": 3600, "instrumented_callbacks": 3600, "control_callback_rate_hz": 60, "instrumented_callback_rate_hz": 60, "callback_rate_delta_hz": 0, "callback_interval_delta_ms": 0, "samples": 3600, "readback_errors": 0},
        }
        value = header("performance-cell", f"{cell_id}-result-{run_number}", artifact_commit)
        value.update({"cell": cell, "trace": trace, "callbacks": callbacks, "measurement": measurement, "qualification": {"status": "qualified", "metrics": {"duration_seconds": 60}, "failures": []}, "source": "live-browser", "diagnostics": {"controlled-test-fixture": True, "statement": "Synthetic trace used only to exercise gate admission; it is not game proof."}, "observed_at": "2026-09-06T00:01:00Z"})
        return value

    def run_record(self, artifact_commit, identity, relation, predecessor=None, predecessor_hash=None):
        value = header("run-record", identity, artifact_commit)
        value.update({
            "brief": {"identity": "brief", "revision": "original", "sha256": self.brief_hash}, "amendments": [],
            "workspace": {"repository": "3d-browser-game", "baseline_commit": artifact_commit, "working_tree": "clean"},
            "package": {"name": "3d-browser-game", "digest": "sha256:" + "1" * 64}, "tools": [], "decisions": [], "freezes": [],
            "increments": [{"id": "increment", "artifact_commit": artifact_commit, "status": "complete", "evidence": ["increment"]}],
            "jobs": [], "sessions": [], "captures": [], "cells": [], "verdicts": [], "complaints": [],
            "resume_cursor": {"stage": "gate", "cursor": identity, "next_action": "continue validation", "open_findings": []},
            "lineage": {"relation": relation, "predecessor": predecessor, "predecessor_sha256": predecessor_hash, "complaints": [], "changed_mechanics": []},
            "predecessor": predecessor, "predecessor_sha256": predecessor_hash,
        })
        return value

    def traceability(self, artifact_commit, gate_id, final=False):
        value = header("traceability", f"trace-{gate_id}", artifact_commit)
        value.update({
            "brief": {"identity": "brief", "sha256": self.brief_hash}, "promise_ids": ["promise-loop", "promise-terminal"],
            "rows": [
                {"prompt_promise": {"identity": "promise-loop", "text": "The player has a repeatable movement loop."}, "amendment_identity": None, "requirement": {"identity": "req-loop", "kind": "state", "text": "Movement and feedback remain playable."}, "playable_evidence_ids": ["increment"], "normal_input_path": "observe -> key -> observe", "core_gate_verdict": "core-gate", "final_gate_verdict": "final-gate" if final else None, "owner": "gameplay", "invalidation_trigger": "Loop state changes."},
                {"prompt_promise": {"identity": "promise-terminal", "text": "The player can reach a terminal and continue or replay."}, "amendment_identity": None, "requirement": {"identity": "req-terminal", "kind": "content", "text": "Terminal and replay behavior are observable."}, "playable_evidence_ids": ["increment"], "normal_input_path": "observe -> key -> observe", "core_gate_verdict": "core-gate", "final_gate_verdict": "final-gate" if final else None, "owner": "gameplay", "invalidation_trigger": "Terminal behavior changes."},
            ],
        })
        return value

    def gate_verdict(self, gate, artifact_commit, index_id, trace_id, plan_id, matrix_id, cells, run_id, predecessor_id=None):
        ids = self.CORE_HARD if gate == "core" else self.FINAL_HARD
        dimensions = self.CORE_DIMS if gate == "core" else self.FINAL_DIMS
        value = header("gate-verdict", f"{gate}-gate", artifact_commit)
        fixed = {"artifact_commit": artifact_commit, "evidence_index": index_id, "traceability": trace_id, "rubric_revision": f"{gate}-rubric", "capture_matrix": matrix_id, "play_sessions": [f"{gate}-session-a", f"{gate}-session-b"], "performance_plan": plan_id, "performance_cells": cells, "run_record": run_id}
        if gate == "final":
            fixed.update({"accepted_core_verdict": "core-gate", "concept_artifacts": ["concept"], "asset_manifests": ["asset"], "predecessor_run_record": "core-run"})
        value.update({
            "gate": gate, "fixed_inputs": fixed,
            "hard_gates": [{"id": identity, "name": identity, "result": "pass", "evidence": ["increment"]} for identity in ids],
            "scores": [{"dimension": identity, "score": 4, "floor": 3, "evidence": ["increment"], "rationale": "The bound fixture covers this dimension."} for identity in dimensions],
            "strengths": ["All required evidence identities are bound."], "complaints": [], "contrary_evidence": [], "confidence": 1, "disposition": "pass",
            "resume_state": {"stage": "accepted", "cursor": f"{gate}-gate", "open_complaint_ids": [], "next_action": "continue"},
        })
        return value

    def performance_plan(self, artifact_commit):
        value = header("performance-plan", "performance-plan", artifact_commit)
        value["groups"] = [{"id": "representative-animation", "cells": ["representative-cell"], "required_runs": 3, "min_duration_seconds": 60, "animated": True}, {"id": "worst-case-animation", "cells": ["worst-case-cell"], "required_runs": 3, "min_duration_seconds": 60, "animated": True}]
        return value

    def capture(self, artifact_commit, identity, screenshot_name):
        self.write_bytes(screenshot_name, b"capture bytes for " + identity.encode("ascii"))
        value = header("capture", identity, artifact_commit)
        value.update({"capture": {"path": Path(screenshot_name).name, "hash": digest((self.root / screenshot_name).read_bytes())}, "viewport": {"width": 1280, "height": 720}, "dpr": 1, "state": "boot"})
        return value

    def build_index(self, gate, artifact_commit, index_id, include_core=False):
        prefix = "core" if gate == "core" else "final"
        entries = []
        def add(identity, kind, value, relative, revision="same-artifact", source_commit=None):
            self.write_json(relative, value)
            entries.append(self.entry(identity, relative, kind, artifact_commit, revision, source_commit))

        brief = header("brief", "brief", artifact_commit)
        brief.update({"sha256": self.brief_hash, "promises": ["promise-loop", "promise-terminal"]})
        add("brief", "brief", brief, f"{prefix}/brief.json")
        run_id = f"{prefix}-run"
        predecessor = None if gate == "core" else "core-run"
        predecessor_hash = None if gate == "core" else digest((self.root / "core/run-record.json").read_bytes())
        run = self.run_record(artifact_commit, run_id, "root" if gate == "core" else "integration", predecessor, predecessor_hash)
        add(run_id, "run-record", run, f"{prefix}/run-record.json")
        trace_id = f"trace-{gate}"
        add(trace_id, "traceability", self.traceability(artifact_commit, gate, gate == "final"), f"{prefix}/traceability.json")
        add(f"{gate}-rubric", "research", {"kind": "rubric", "id": f"{gate}-rubric", "artifact_commit": artifact_commit}, f"{prefix}/rubric.json")
        add("increment", "increment", {"kind": "increment", "id": "increment", "artifact_commit": artifact_commit}, f"{prefix}/increment.json")
        plan = self.performance_plan(artifact_commit)
        add("performance-plan", "performance-plan", plan, f"{prefix}/performance-plan.json")
        cells = []
        for scenario, cell_id in [("representative-animation", "representative-cell"), ("worst-case-animation", "worst-case-cell")]:
            for number in range(1, 4):
                result_id = f"{cell_id}-result-{number}"
                add(result_id, "performance", self.performance_cell(artifact_commit, scenario, cell_id, number), f"{prefix}/{result_id}.json")
                cells.append(result_id)
        for suffix, operator, context in [("a", "operator-a", "context-a"), ("b", "operator-b", "context-b")]:
            identity = f"{gate}-session-{suffix}"
            add(identity, "play-session", self.play_session(artifact_commit, identity, operator, context), f"{prefix}/{identity}.json")
        capture_id = f"{gate}-capture"
        capture_path = f"{prefix}/{capture_id}.json"
        capture_value = self.capture(artifact_commit, capture_id, f"{prefix}/{capture_id}.png")
        add(capture_id, "capture", capture_value, capture_path)
        matrix = header("capture-matrix", f"{gate}-capture-matrix", artifact_commit)
        matrix["cells"] = [{"id": "boot", "state": "boot", "viewport": {"width": 1280, "height": 720}, "dpr": 1, "required": True, "capture_ids": [capture_id]}]
        matrix_id = f"{gate}-capture-matrix"
        add(matrix_id, "capture-matrix", matrix, f"{prefix}/capture-matrix.json")
        if gate == "final":
            add("concept", "concept", {"kind": "concept", "id": "concept", "artifact_commit": artifact_commit}, "final/concept.json")
            manifest_path, manifest_id = self.asset_manifest(artifact_commit, "final/assets")
            entries.append(self.entry(manifest_id, manifest_path, "manifest", artifact_commit))
        gate_id = f"{gate}-gate"
        verdict = self.gate_verdict(gate, artifact_commit, index_id, trace_id, "performance-plan", matrix_id, cells, run_id)
        add(gate_id, "verdict", verdict, f"{prefix}/gate.json")
        if include_core:
            for relative, identity, kind in [("core/run-record.json", "core-run", "run-record"), ("core/gate.json", "core-gate", "verdict")]:
                entries.append(self.entry(identity, relative, kind, artifact_commit, "declared-ancestor", self.core_commit))
        value = header("evidence-index", index_id, artifact_commit)
        value.update({"status": "draft", "declared_ancestors": [] if gate == "core" else [commit(self.core_commit)], "entries": entries, "required": [item["id"] for item in entries]})
        if gate == "final":
            value["declared_ancestors"] = [commit(self.core_commit)]
        path = self.write_json(f"{prefix}-index.json", value)
        return path, value

    def build(self):
        core_path, _ = self.build_index("core", commit(self.core_commit), "core-index")
        final_path, _ = self.build_index("final", commit(self.final_commit), "final-index", include_core=True)
        return core_path, final_path


class BrowserGameGateIntegrationTests(unittest.TestCase):
    def run_cli(self, *arguments):
        return subprocess.run([NODE, str(SCRIPTS / "validate_evidence.mjs"), *map(str, arguments)], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", timeout=120)

    def test_promoted_core_and_final_gate_rehash_full_lineage_and_reject_tampering(self):
        with tempfile.TemporaryDirectory(dir=ROOT, prefix="orchflows-integration-") as directory:
            fixture = GateFixture(Path(directory))
            core_path, final_path = fixture.build()
            core_promote = self.run_cli("--index", core_path, "--promote")
            self.assertEqual(0, core_promote.returncode, core_promote.stderr + core_promote.stdout)
            core_gate = self.run_cli("gate", "--index", core_path, "--gate", "core")
            self.assertEqual(0, core_gate.returncode, core_gate.stderr + core_gate.stdout)
            final_promote = self.run_cli("--index", final_path, "--promote")
            self.assertEqual(0, final_promote.returncode, final_promote.stderr + final_promote.stdout)
            final_gate = self.run_cli("gate", "--index", final_path, "--gate", "final")
            self.assertEqual(0, final_gate.returncode, final_gate.stderr + final_gate.stdout)
            accepted = json.loads(final_gate.stdout)
            self.assertEqual("valid", accepted["status"])
            self.assertEqual("core-gate", accepted["lineage"]["core_verdict_id"])
            self.assertEqual(2, len(accepted["performance_coverage"]))
            self.assertTrue(all(len(item["runs"]) == 3 for item in accepted["performance_coverage"]))

            forged = Path(directory) / "forged-index.json"
            forged.write_bytes(Path(final_path).read_bytes())
            forged_value = json.loads(forged.read_text(encoding="utf-8"))
            forged_value["promotion"]["result_identity"] = "sha256:" + "0" * 64
            forged.write_bytes(canonical(forged_value))
            forged_result = self.run_cli("gate", "--index", forged, "--gate", "final")
            self.assertEqual(4, forged_result.returncode, forged_result.stderr + forged_result.stdout)

            screenshot = Path(directory) / "final/assets/loader.png"
            screenshot.write_bytes(screenshot.read_bytes() + b"tampered")
            stale_result = self.run_cli("gate", "--index", final_path, "--gate", "final")
            self.assertEqual(4, stale_result.returncode, stale_result.stderr + stale_result.stdout)


if __name__ == "__main__":
    unittest.main()
