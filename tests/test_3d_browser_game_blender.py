"""Acceptance seams for the native Blender boundary.

These tests deliberately use a controlled worker subprocess seam for
promotion and a real short-lived Python process for timeout handling. They do
not call Blender; the checked-in probe fixture is exercised separately when
the host capability is available.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


# This test resolves its repository-owned fixture and package paths from the
# checkout root; the climb belongs to this test owner, not a wildcard exemption.
HERE = Path(__file__).resolve().parents[1]
RUNNER_PATH = HERE / "example-workflows" / "3d-browser-game" / "scripts" / "blender_job_runner.py"
SPEC = importlib.util.spec_from_file_location("blender_job_runner_test_module", RUNNER_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)
WORKER_SPEC = importlib.util.spec_from_file_location("blender_asset_job_test_module", HERE / "example-workflows" / "3d-browser-game" / "scripts" / "blender_asset_job.py")
assert WORKER_SPEC and WORKER_SPEC.loader
worker = importlib.util.module_from_spec(WORKER_SPEC)
WORKER_SPEC.loader.exec_module(worker)


def digest(path: Path) -> str:
    return runner.sha256_file(path)


class BlenderBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="blender-boundary-")
        self.root = Path(self.temp.name)
        self.job_root = self.root / "request"
        self.job_root.mkdir()
        self.module = self.job_root / "author.py"
        self.module.write_text("def build(context):\n    return None\n", encoding="utf-8")
        self.blender = self.root / "blender.exe"
        self.blender.write_bytes(b"fake blender executable")
        self.target = self.root / "target"
        self.target.mkdir()
        self.three = self.target / "node_modules" / "three"
        (self.three / "build").mkdir(parents=True)
        (self.three / "examples" / "jsm" / "loaders").mkdir(parents=True)
        (self.three / "build" / "three.module.js").write_text("export const REVISION = '185';\n", encoding="utf-8")
        (self.three / "examples" / "jsm" / "loaders" / "GLTFLoader.js").write_text("export class GLTFLoader {}\n", encoding="utf-8")
        self.job = self._write_job()

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_job(self, **changes: object) -> Path:
        value: dict[str, object] = {
            "schema_version": "1.0.0",
            "kind": "blender-job",
            "id": "test-job",
            "artifact_commit": "git:" + "a" * 40,
            "created_at": "2026-09-06T00:00:00Z",
            "producer": {"name": "test"},
            "inputs": [{"name": "author", "sha256": digest(self.module)}],
            "environment": {"host": "test", "os": "test", "tools": []},
            "status": "draft",
            "gaps": [],
            "invalidates": [],
            "mode": "generate",
            "authoring": {"kind": "generated", "module": "author.py", "sha256": digest(self.module), "entrypoint": "build"},
            "seed": 3,
            "scene": {"units": "METRIC", "unit_scale": 1.0, "up_axis": "+Y", "gameplay_forward": "+Z", "origin": "asset-origin"},
            "allowlists": {"input_extensions": [".py"], "output_extensions": [".blend", ".json", ".png", ".glb"]},
            "budgets": {"mesh_vertices": 1000, "mesh_polygons": 2000, "materials": 8, "texture_bytes": 0, "animations": 4, "skeleton_bones": 0},
            "cameras": [
                {"camera": "Camera", "output": "preview/gameplay.png", "label": "gameplay-camera"},
                {"camera": "Camera", "output": "preview/turntable.png", "label": "turntable-camera"},
            ],
            "render": {"engine": "BLENDER_EEVEE", "resolution": [320, 240], "percentage": 100, "format": "PNG"},
            "export": {"export_yup": True, "animations": True},
            "outputs": [
                {"path": "source.blend", "kind": "source", "required": True},
                {"path": "inspection.json", "kind": "inspection", "required": True},
                {"path": "preview/gameplay.png", "kind": "preview", "required": True},
                {"path": "preview/turntable.png", "kind": "preview", "required": True},
                {"path": "asset.glb", "kind": "runtime", "required": True},
                {"path": "asset-manifest.json", "kind": "manifest", "required": True},
            ],
            "validation": {"target_workspace": str(self.target), "loader_probe": {"three_root": "node_modules/three", "browser_executable": str(self.blender)}},
            "colliders": [],
            "attachments": [],
            "material_roles": {},
            "animation_clips": [],
            "required_extensions": [],
            "timeout_seconds": 5,
        }
        value.update(changes)
        path = self.job_root / "job.json"
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
        return path

    def _fake_worker(self, *, complete: bool = True, mismatch: bool = False):
        def run(argv, cwd, timeout):
            job_path = Path(cwd) / "job.json"
            job = json.loads(job_path.read_text(encoding="utf-8"))
            job_hash = digest(job_path)
            (Path(cwd) / "source.blend").write_bytes(b"blend-source")
            inspection = {
                "kind": "blender-structural-inspection",
                "job_id": job["id"],
                "status": "complete",
                "gaps": [],
                "declared_budgets": job["budgets"],
                "coordinate_conversion": {"matrix": "Rx(-pi/2)", "mapping": "(x,y,z)->(x,z,-y)", "source_up": "+Z", "runtime_up": "+Y"},
                "semantic_tolerance": runner.SEMANTIC_TOLERANCE,
                "declared_semantics": {"colliders": job["colliders"], "attachments": job["attachments"], "material_roles": job["material_roles"], "animation_clips": job["animation_clips"], "required_extensions": job["required_extensions"]},
                "asset": {
                    "mesh_vertices": 1, "mesh_polygons": 1, "materials": ["mat"], "texture_bytes": 0,
                    "animation_clips": [], "skeleton_bones": 0, "armatures": [], "textures": [], "mesh_normals": 1, "mesh_uv_layers": 0,
                    "poses": [], "objects": [],
                },
            }
            (Path(cwd) / "inspection.json").write_text(json.dumps(inspection) + "\n", encoding="utf-8")
            (Path(cwd) / "preview").mkdir(exist_ok=True)
            (Path(cwd) / "preview" / "gameplay.png").write_bytes(b"png-preview")
            (Path(cwd) / "preview" / "turntable.png").write_bytes(b"png-turntable")
            (Path(cwd) / "asset.glb").write_bytes(b"glb-runtime")
            glb_hash = digest(Path(cwd) / "asset.glb")
            source_hash = digest(Path(cwd) / "source.blend")
            manifest = {"source_blend_sha256": source_hash, "exported_glb_sha256": glb_hash, "status": "unverified", "gaps": ["external-validation-required"], "environment": {}, "units": job["scene"]["units"], "unit_scale": job["scene"]["unit_scale"], "up_axis": job["scene"]["up_axis"], "gameplay_forward": job["scene"]["gameplay_forward"], "origin": job["scene"]["origin"], "colliders": job["colliders"], "attachments": job["attachments"], "material_roles": job["material_roles"], "animation_clips": job["animation_clips"], "required_extensions": job["required_extensions"], "semantic_contract": {"coordinate_conversion": {"matrix": "Rx(-pi/2)", "mapping": "(x,y,z)->(x,z,-y)", "source_up": "+Z", "runtime_up": "+Y"}, "tolerance": runner.SEMANTIC_TOLERANCE, "source_coordinate_space": "blender-world", "runtime_coordinate_space": "three-world", "runtime_budget_fields": []}}
            (Path(cwd) / "asset-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            outputs = [
                {"path": path, "sha256": digest(Path(cwd) / path)}
                for path in ("source.blend", "inspection.json", "preview/gameplay.png", "preview/turntable.png", "asset.glb", "asset-manifest.json")
            ]
            result = {
                "status": "complete" if complete else "failed",
                "job_sha256": "sha256:" + "0" * 64 if mismatch else job_hash,
                "expected_job_sha256": job_hash,
                "source_blend_sha256": source_hash,
                "input_hashes": job["inputs"],
                "outputs": outputs if complete else outputs[:1],
                "inspection": {"path": "inspection.json"},
                "previews": [{"path": "preview/gameplay.png"}, {"path": "preview/turntable.png"}],
                "semantics": {"status": "complete", "coordinate_conversion": {"matrix": "Rx(-pi/2)", "mapping": "(x,y,z)->(x,z,-y)", "source_up": "+Z", "runtime_up": "+Y"}, "tolerance": runner.SEMANTIC_TOLERANCE, "checks": {"colliders": "pass", "attachments": "pass", "material_roles": "pass", "animation_clips": "pass", "required_extensions": "pass"}},
                "validation": {
                    "khronos": {"status": "pass", "errors": 0, "export_sha256": glb_hash},
                    "gltfloader": {"status": "pass", "export_sha256": glb_hash, "checks": {"scale": "pass", "material": "pass", "animation": "pass", "collider": "pass"}},
                },
            }
            (Path(cwd) / "worker-result.json").write_text(json.dumps(result), encoding="utf-8")
            return 0, b"worker stdout\n", b"", False

        return run

    def _fake_validator_process(self, argv, cwd, timeout):
        if "asset_validation.mjs" not in [Path(part).name for part in argv if isinstance(part, str)]:
            return self._fake_worker()(argv, cwd, timeout)
        mode = argv[2]
        report_path = Path(argv[argv.index("--report") + 1])
        glb_path = Path(argv[argv.index("--glb") + 1])
        glb_hash = digest(glb_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        if mode == "khronos":
            report = {"issues": {"numErrors": 0, "numWarnings": 0}}
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            return 0, json.dumps({"status": "pass", "errors": 0, "export_sha256": glb_hash, "report_sha256": digest(report_path) }).encode() + b"\n", b"", False
        screenshot_path = report_path.with_name("gltf-loader-evidence.png")
        screenshot_path.write_bytes(b"png-evidence")
        screenshot_hash = digest(screenshot_path)
        target_workspace = Path(json.loads((Path(cwd) / "job.json").read_text(encoding="utf-8"))["validation"]["target_workspace"])
        three_root = target_workspace / "node_modules" / "three"
        job = json.loads((Path(cwd) / "job.json").read_text(encoding="utf-8"))
        manifest = json.loads((Path(cwd) / "asset-manifest.json").read_text(encoding="utf-8"))
        semantic_checks = {key: {"status": "pass", "basis": "controlled test observation", "observed": {}} for key in runner.SEMANTIC_CHECKS}
        report = {"kind": "gltf-loader-evidence", "id": "test-loader", "artifact_commit": job["artifact_commit"], "glb_hash": glb_hash, "job_sha256": digest(Path(cwd) / "job.json"), "expectations_hash": runner.semantic_expectations_hash(job, manifest), "coordinate_conversion": {"matrix": "Rx(-pi/2)", "mapping": "(x,y,z)->(x,z,-y)", "source_up": "+Z", "runtime_up": "+Y"}, "semantic_tolerance": runner.SEMANTIC_TOLERANCE, "source": "live-browser", "checks": {"scale": "pass", "material": "pass", "animation": "pass", "collider": "pass"}, "semantic_checks": semantic_checks, "target_workspace": str(target_workspace), "target_three_root": {"path": "node_modules/three", "three_module_sha256": digest(three_root / "build" / "three.module.js"), "gltf_loader_sha256": digest(three_root / "examples" / "jsm" / "loaders" / "GLTFLoader.js")}, "target_probe": {"path": screenshot_path.name, "sha256": screenshot_hash}, "browser": {"screenshot_sha256": screenshot_hash}, "observed": {"meshes": 1, "materials": 1, "animations": 0}}
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        return 0, json.dumps({"status": "pass", "export_sha256": glb_hash, "evidence_sha256": digest(report_path)}).encode() + b"\n", b"", False

    def test_malformed_unknown_field_is_rejected(self) -> None:
        job = self._write_job(unexpected=True)
        with self.assertRaises(runner.JobError):
            runner.load_job(job)

    def test_traversal_and_absolute_input_paths_are_rejected(self) -> None:
        traversal = self._write_job(authoring={"kind": "generated", "module": "../author.py", "sha256": digest(self.module), "entrypoint": "build"})
        with self.assertRaises(runner.JobError):
            runner.load_job(traversal)
        absolute = self._write_job(authoring={"kind": "generated", "module": str(self.module.resolve()), "sha256": digest(self.module), "entrypoint": "build"})
        with self.assertRaises(runner.JobError):
            runner.load_job(absolute)

    def test_changed_authoring_module_digest_is_rejected(self) -> None:
        self.module.write_text("def build(context):\n    return 'changed'\n", encoding="utf-8")
        with self.assertRaises(runner.JobError):
            runner.load_job(self.job)

    def test_inline_validation_verdict_is_rejected_as_job_input(self) -> None:
        inline = self._write_job(validation={"khronos": {"status": "pass", "errors": 0}})
        with self.assertRaises(runner.JobError):
            runner.load_job(inline)

    def test_missing_budget_dimension_is_rejected(self) -> None:
        budgets = dict(json.loads(self.job.read_text(encoding="utf-8"))["budgets"])
        budgets.pop("animations")
        missing = self._write_job(budgets=budgets)
        with self.assertRaises(runner.JobError):
            runner.load_job(missing)

    def test_manifest_omission_is_rejected(self) -> None:
        outputs = [item for item in json.loads(self.job.read_text(encoding="utf-8"))["outputs"] if item["kind"] != "manifest"]
        missing = self._write_job(outputs=outputs)
        with self.assertRaises(runner.JobError):
            runner.load_job(missing)

    def test_overbudget_measurement_is_rejected(self) -> None:
        job = json.loads(self.job.read_text(encoding="utf-8"))
        inventory = {
            "mesh_vertices": 1001, "mesh_polygons": 1, "materials": [], "texture_bytes": 0,
            "animation_clips": [], "skeleton_bones": 0, "mesh_normals": 1, "mesh_uv_layers": 0,
            "poses": [], "objects": [], "actions": [],
        }
        failures = worker._validate_scene(job, inventory)
        self.assertTrue(any(item.startswith("budget/mesh_vertices") for item in failures))

    def _semantic_inventory(self):
        return {
            "units": "METRIC", "unit_scale": 1.0,
            "mesh_vertices": 3, "mesh_polygons": 1, "materials": ["BodyMaterial"], "texture_bytes": 0,
            "animation_clips": [{"name": "Idle", "start": 1, "end": 25, "fcurves": 1}], "skeleton_bones": 0,
            "mesh_normals": 1, "mesh_uv_layers": 0, "poses": [], "actions": ["Idle"],
            "objects": [
                {"name": "BodyCollider", "type": "MESH", "location": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0], "scale": [1.0, 1.0, 1.0], "world_position": [0.0, 0.0, 0.0], "world_rotation": [0.0, 0.0, 0.0], "world_scale": [1.0, 1.0, 1.0], "dimensions": [2.0, 1.0, 2.0], "bounds": [-1.0, -0.5, -1.0, 1.0, 0.5, 1.0], "parent": None},
                {"name": "WeaponSocket", "type": "EMPTY", "location": [0.0, 0.0, 1.0], "rotation": [0.0, 0.0, 0.0], "scale": [1.0, 1.0, 1.0], "world_position": [0.0, 0.0, 1.0], "world_rotation": [0.0, 0.0, 0.0], "world_scale": [1.0, 1.0, 1.0], "dimensions": [0.0, 0.0, 0.0], "bounds": [0.0, 0.0, 1.0, 0.0, 0.0, 1.0], "parent": "BodyCollider"},
            ],
            "material_bindings": {"BodyMaterial": {"objects": ["BodyCollider"], "roles": []}},
            "frame_rate": 24.0,
        }

    def _semantic_job(self, **changes):
        return json.loads(self._write_job(**{
            "colliders": [{"name": "BodyCollider", "dimensions": [2.0, 1.0, 2.0], "position": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0]}],
            "attachments": [{"name": "WeaponSocket", "position": [0.0, 0.0, 1.0], "rotation": [0.0, 0.0, 0.0], "parent": "BodyCollider"}],
            "material_roles": {"BodyMaterial": {"role": "body", "objects": ["BodyCollider"]}},
            "animation_clips": [{"name": "Idle", "start": 1, "end": 25}],
            **changes,
        }).read_text(encoding="utf-8"))

    def test_collider_position_and_rotation_declarations_are_enforced(self) -> None:
        job = self._semantic_job()
        failures = worker._validate_scene(job, self._semantic_inventory())
        self.assertEqual([], failures)
        inventory = self._semantic_inventory()
        inventory["objects"][0]["world_position"] = [0.25, 0.0, 0.0]
        inventory["objects"][0]["world_rotation"] = [0.0, 0.25, 0.0]
        failures = worker._validate_scene(job, inventory)
        self.assertTrue(any("collider/BodyCollider/position" in item for item in failures))
        self.assertTrue(any("collider/BodyCollider/rotation" in item for item in failures))

    def test_attachment_transform_and_parent_are_enforced(self) -> None:
        job = self._semantic_job()
        inventory = self._semantic_inventory()
        inventory["objects"][1]["parent"] = "OtherBody"
        inventory["objects"][1]["world_position"] = [0.0, 0.1, 1.0]
        failures = worker._validate_scene(job, inventory)
        self.assertTrue(any("attachment/WeaponSocket/position" in item for item in failures))
        self.assertTrue(any("attachment/WeaponSocket/parent" in item for item in failures))

    def test_material_role_object_binding_is_enforced(self) -> None:
        job = self._semantic_job()
        inventory = self._semantic_inventory()
        inventory["material_bindings"]["BodyMaterial"]["objects"] = ["OtherBody"]
        failures = worker._validate_scene(job, inventory)
        self.assertTrue(any("material role/BodyMaterial/objects" in item for item in failures))

    def test_animation_clip_range_and_playability_are_enforced(self) -> None:
        job = self._semantic_job()
        inventory = self._semantic_inventory()
        inventory["animation_clips"][0]["fcurves"] = 0
        failures = worker._validate_scene(job, inventory)
        self.assertTrue(any("animation/Idle: clip has no fcurves" in item for item in failures))

    def test_required_extension_absence_is_enforced_after_export(self) -> None:
        job = self._semantic_job(required_extensions=["KHR_materials_unlit"])
        path = self.root / "plain.glb"
        path.write_bytes(b"not-a-glb")
        with self.assertRaises(ValueError):
            worker._validate_export_semantics(job, path)

    def test_stale_output_is_rejected_before_worker_starts(self) -> None:
        out = self.root / "out"
        out.mkdir()
        (out / "stale.glb").write_bytes(b"old")
        with mock.patch.object(runner, "_run_process", side_effect=AssertionError("worker must not start")):
            with self.assertRaises(runner.JobError):
                runner.run_job(self.job, out, Path("C:/absolute/blender.exe"))

    def test_timeout_returns_exit_five_and_terminates_process(self) -> None:
        code, stdout, stderr, timed_out = runner._run_process(
            [sys.executable, "-c", "import time; time.sleep(10)"], self.root, 0.1
        )
        self.assertEqual(runner.EXIT_TIMEOUT, code)
        self.assertTrue(timed_out)
        self.assertIn(b"timeout", stderr)

    def test_partial_output_is_preserved_but_not_promoted(self) -> None:
        out = self.root / "partial"
        calls = 0

        def partial_then_validate(argv, cwd, timeout):
            nonlocal calls
            calls += 1
            if calls == 1:
                return self._fake_worker(complete=False)(argv, cwd, timeout)
            return self._fake_validator_process(argv, cwd, timeout)

        with mock.patch.object(runner, "_run_process", side_effect=partial_then_validate):
            result = runner.run_job(self.job, out, self.blender)
        self.assertEqual(runner.EXIT_EVIDENCE, result["exit_code"])
        self.assertFalse(result["promoted"])
        self.assertTrue((out / "stdout.log").is_file())
        self.assertTrue((out / "worker-result.json").is_file())

    def test_mismatched_job_digest_is_not_promoted(self) -> None:
        out = self.root / "mismatch"
        with mock.patch.object(runner, "_run_process", side_effect=self._fake_worker(mismatch=True)):
            result = runner.run_job(self.job, out, self.blender)
        self.assertEqual(runner.EXIT_EVIDENCE, result["exit_code"])
        self.assertFalse(result["promoted"])
        self.assertIn("digest", result["error"])

    def test_complete_outputs_require_hash_bound_external_validators(self) -> None:
        out = self.root / "promoted"
        with mock.patch.object(runner, "_run_process", side_effect=self._fake_validator_process):
            result = runner.run_job(self.job, out, self.blender)
        self.assertEqual(runner.EXIT_OK, result["exit_code"])
        self.assertTrue(result["promoted"])
        manifest = json.loads((out / "asset-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("complete", manifest["status"])
        self.assertEqual([], manifest["gaps"])

    def test_missing_validator_evidence_keeps_complete_worker_unverified(self) -> None:
        out = self.root / "unvalidated"
        with mock.patch.object(runner, "_run_process", side_effect=self._fake_worker()):
            result = runner.run_job(self.job, out, self.blender)
        self.assertEqual(runner.EXIT_EVIDENCE, result["exit_code"])
        self.assertFalse(result["promoted"])
        self.assertIn("validator", result["error"])

    def test_worker_output_path_traversal_is_preserved_without_promotion(self) -> None:
        fake = self._fake_worker()

        def with_traversal(argv, cwd, timeout):
            response = fake(argv, cwd, timeout)
            result_path = Path(cwd) / "worker-result.json"
            result = json.loads(result_path.read_text(encoding="utf-8"))
            result["previews"] = [{"path": "../outside.png"}]
            result_path.write_text(json.dumps(result), encoding="utf-8")
            return response

        out = self.root / "traversal-output"
        with mock.patch.object(runner, "_run_process", side_effect=with_traversal):
            result = runner.run_job(self.job, out, self.blender)
        self.assertEqual(runner.EXIT_EVIDENCE, result["exit_code"])
        self.assertFalse(result["promoted"])


if __name__ == "__main__":
    unittest.main()
