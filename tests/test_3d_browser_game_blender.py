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


HERE = Path(__file__).resolve().parents[1]
RUNNER_PATH = HERE / "example-workflows" / "3d-browser-game" / "scripts" / "blender_job_runner.py"
SPEC = importlib.util.spec_from_file_location("blender_job_runner_test_module", RUNNER_PATH)
assert SPEC and SPEC.loader
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


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
            "cameras": [{"camera": "Camera", "output": "preview/hero.png"}],
            "outputs": [
                {"path": "source.blend", "kind": "source"},
                {"path": "inspection.json", "kind": "inspection"},
                {"path": "preview/hero.png", "kind": "preview"},
                {"path": "asset.glb", "kind": "runtime"},
                {"path": "asset-manifest.json", "kind": "manifest"},
            ],
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
            (Path(cwd) / "inspection.json").write_bytes(b"{\"object_count\":1}\n")
            (Path(cwd) / "preview").mkdir()
            (Path(cwd) / "preview" / "hero.png").write_bytes(b"png-preview")
            (Path(cwd) / "asset.glb").write_bytes(b"glb-runtime")
            glb_hash = digest(Path(cwd) / "asset.glb")
            source_hash = digest(Path(cwd) / "source.blend")
            manifest = {"source_blend_sha256": source_hash, "exported_glb_sha256": glb_hash, "status": "unverified", "gaps": ["external-validation-required"]}
            (Path(cwd) / "asset-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            outputs = [
                {"path": path, "sha256": digest(Path(cwd) / path)}
                for path in ("source.blend", "inspection.json", "preview/hero.png", "asset.glb", "asset-manifest.json")
            ]
            result = {
                "status": "complete" if complete else "failed",
                "job_sha256": "sha256:" + "0" * 64 if mismatch else job_hash,
                "expected_job_sha256": job_hash,
                "source_blend_sha256": source_hash,
                "outputs": outputs if complete else outputs[:1],
                "inspection": {"path": "inspection.json"},
                "previews": [{"path": "preview/hero.png"}],
                "validation": {
                    "khronos": {"status": "pass", "errors": 0, "export_sha256": glb_hash},
                    "gltfloader": {"status": "pass", "export_sha256": glb_hash, "checks": {"scale": "pass", "material": "pass", "animation": "pass", "collider": "pass"}},
                },
            }
            (Path(cwd) / "worker-result.json").write_text(json.dumps(result), encoding="utf-8")
            return 0, b"worker stdout\n", b"", False

        return run

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
        with mock.patch.object(runner, "_run_process", side_effect=self._fake_worker(complete=False)):
            result = runner.run_job(self.job, out, Path("C:/absolute/blender.exe"))
        self.assertEqual(runner.EXIT_EVIDENCE, result["exit_code"])
        self.assertFalse(result["promoted"])
        self.assertTrue((out / "stdout.log").is_file())
        self.assertTrue((out / "worker-result.json").is_file())

    def test_mismatched_job_digest_is_not_promoted(self) -> None:
        out = self.root / "mismatch"
        with mock.patch.object(runner, "_run_process", side_effect=self._fake_worker(mismatch=True)):
            result = runner.run_job(self.job, out, Path("C:/absolute/blender.exe"))
        self.assertEqual(runner.EXIT_EVIDENCE, result["exit_code"])
        self.assertFalse(result["promoted"])
        self.assertIn("digest", result["error"])

    def test_complete_outputs_require_hash_bound_external_validators(self) -> None:
        out = self.root / "promoted"
        with mock.patch.object(runner, "_run_process", side_effect=self._fake_worker()):
            result = runner.run_job(self.job, out, Path("C:/absolute/blender.exe"))
        self.assertEqual(runner.EXIT_OK, result["exit_code"])
        self.assertTrue(result["promoted"])
        manifest = json.loads((out / "asset-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("complete", manifest["status"])
        self.assertEqual([], manifest["gaps"])

    def test_missing_validator_evidence_keeps_complete_worker_unverified(self) -> None:
        fake = self._fake_worker()

        def without_validation(argv, cwd, timeout):
            response = fake(argv, cwd, timeout)
            result_path = Path(cwd) / "worker-result.json"
            result = json.loads(result_path.read_text(encoding="utf-8"))
            result.pop("validation", None)
            result_path.write_text(json.dumps(result), encoding="utf-8")
            return response

        out = self.root / "unvalidated"
        with mock.patch.object(runner, "_run_process", side_effect=without_validation):
            result = runner.run_job(self.job, out, Path("C:/absolute/blender.exe"))
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
            result = runner.run_job(self.job, out, Path("C:/absolute/blender.exe"))
        self.assertEqual(runner.EXIT_EVIDENCE, result["exit_code"])
        self.assertFalse(result["promoted"])


if __name__ == "__main__":
    unittest.main()
