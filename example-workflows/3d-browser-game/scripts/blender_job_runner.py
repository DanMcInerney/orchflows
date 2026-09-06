"""Run one hash-bound Blender job and promote only complete evidence.

The runner is the process boundary.  A job is copied into a new staging
directory together with its declared inputs, Blender is started with an argv
array, and the staging directory is promoted atomically only after the worker
echoes the job identity and every declared evidence/validation seam passes.
Failure directories remain available for diagnosis and are never considered
runtime assets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


EXIT_OK = 0
EXIT_INVALID = 2
EXIT_CAPABILITY = 3
EXIT_EVIDENCE = 4
EXIT_TIMEOUT = 5

_HASH_LENGTH = 64
_HASH_PREFIX = "sha256:"
_JOB_KINDS = {"blender-job"}
_MODES = {"generate", "edit", "render", "export"}
_SOURCE_KINDS = {"generated", "edited"}
_REQUIRED_HEADER = {
    "schema_version",
    "kind",
    "id",
    "artifact_commit",
    "created_at",
    "producer",
    "inputs",
    "environment",
    "status",
    "gaps",
    "invalidates",
}
_JOB_FIELDS = _REQUIRED_HEADER | {
    "mode",
    "source",
    "authoring",
    "seed",
    "scene",
    "allowlists",
    "budgets",
    "cameras",
    "render",
    "export",
    "outputs",
    "validation",
    "timeout_seconds",
    "colliders",
    "attachments",
    "material_roles",
    "animation_clips",
    "required_extensions",
}


class JobError(ValueError):
    """A job is malformed or requests an unsafe path."""


class EvidenceError(ValueError):
    """A worker result or validation record cannot justify promotion."""


def sha256_bytes(data: bytes) -> str:
    return _HASH_PREFIX + hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return _HASH_PREFIX + digest.hexdigest()


def _is_digest(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(_HASH_PREFIX) and len(value) == len(_HASH_PREFIX) + _HASH_LENGTH and all(
        char in "0123456789abcdef" for char in value[len(_HASH_PREFIX) :]
    )


def _relative_path(value: Any, *, field: str) -> Path:
    if not isinstance(value, str) or not value or "\x00" in value:
        raise JobError(f"{field}: expected a non-empty relative path")
    candidate = Path(value)
    if candidate.is_absolute() or candidate.drive:
        raise JobError(f"{field}: absolute paths are not allowed")
    parts = candidate.parts
    if ".." in parts:
        raise JobError(f"{field}: parent traversal is not allowed")
    if candidate == Path("."):
        raise JobError(f"{field}: directory path is not allowed")
    return candidate


def contained_path(root: Path, relative: str | Path, *, field: str = "path") -> Path:
    """Resolve a relative path and prove it stays under ``root``."""

    path = _relative_path(str(relative), field=field)
    root_resolved = root.resolve()
    resolved = (root_resolved / path).resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise JobError(f"{field}: path escapes its job directory") from exc
    return resolved


def load_job(path: Path) -> tuple[dict[str, Any], bytes, str]:
    """Load and validate a closed job document, returning its byte identity."""

    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise JobError(f"job: cannot read {path}: {exc}") from exc
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise JobError(f"job: invalid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise JobError("job: top-level value must be an object")
    unknown = set(value) - _JOB_FIELDS
    if unknown:
        raise JobError(f"job: unknown fields: {', '.join(sorted(unknown))}")
    missing = _REQUIRED_HEADER - set(value)
    if missing:
        raise JobError(f"job: missing fields: {', '.join(sorted(missing))}")
    if value.get("kind") not in _JOB_KINDS:
        raise JobError("job/kind: expected blender-job")
    if value.get("schema_version") not in {"1", "1.0.0"}:
        raise JobError("job/schema_version: expected 1.0.0")
    if not isinstance(value.get("id"), str) or not value["id"]:
        raise JobError("job/id: expected non-empty string")
    if value.get("mode") not in _MODES:
        raise JobError(f"job/mode: expected one of {sorted(_MODES)}")
    if not isinstance(value.get("inputs"), list):
        raise JobError("job/inputs: expected array of named SHA-256 identities")
    for index, item in enumerate(value["inputs"]):
        if not isinstance(item, dict) or set(item) != {"name", "sha256"} or not isinstance(item["name"], str) or not _is_digest(item["sha256"]):
            raise JobError(f"job/inputs/{index}: expected name and sha256")
    if not isinstance(value.get("producer"), dict) or not isinstance(value["producer"].get("name"), str):
        raise JobError("job/producer: expected object with name")
    if not isinstance(value.get("environment"), dict):
        raise JobError("job/environment: expected object")
    if not all(isinstance(value["environment"].get(key), str) and value["environment"][key] for key in ("host", "os")):
        raise JobError("job/environment: host and os are required")
    if not isinstance(value["environment"].get("tools"), list):
        raise JobError("job/environment/tools: expected array")
    if not isinstance(value.get("status"), str):
        raise JobError("job/status: expected string")
    if not isinstance(value.get("gaps"), list) or not isinstance(value.get("invalidates"), list):
        raise JobError("job/gaps and job/invalidates: expected arrays")
    if not isinstance(value.get("seed"), int) or isinstance(value.get("seed"), bool):
        raise JobError("job/seed: expected integer")
    if not isinstance(value.get("outputs"), list) or not value["outputs"]:
        raise JobError("job/outputs: expected a non-empty array")
    output_paths: set[str] = set()
    for index, item in enumerate(value["outputs"]):
        if not isinstance(item, dict) or set(item) - {"path", "kind", "required"}:
            raise JobError(f"job/outputs/{index}: expected path, kind, required")
        relative = _relative_path(item.get("path"), field=f"job/outputs/{index}/path")
        normalized = relative.as_posix()
        if normalized in output_paths:
            raise JobError(f"job/outputs/{index}/path: duplicate output")
        output_paths.add(normalized)
        if not isinstance(item.get("kind"), str) or not item["kind"]:
            raise JobError(f"job/outputs/{index}/kind: expected string")
        if "required" in item and not isinstance(item["required"], bool):
            raise JobError(f"job/outputs/{index}/required: expected boolean")
    allowlists = value.get("allowlists", {})
    if allowlists is not None and not isinstance(allowlists, dict):
        raise JobError("job/allowlists: expected object")
    input_extensions = {str(item).lower() for item in (allowlists or {}).get("input_extensions", [])}
    output_extensions = {str(item).lower() for item in (allowlists or {}).get("output_extensions", [])}
    for field, item in (("source", value.get("source")), ("authoring", value.get("authoring"))):
        path_value = item.get("path" if field == "source" else "module") if isinstance(item, dict) else None
        if input_extensions and isinstance(path_value, str) and Path(path_value).suffix.lower() not in input_extensions:
            raise JobError(f"job/{field}: extension is outside input allowlist")
    if output_extensions:
        for index, item in enumerate(value["outputs"]):
            suffix = Path(item["path"]).suffix.lower()
            if suffix and suffix not in output_extensions:
                raise JobError(f"job/outputs/{index}: extension is outside output allowlist")
    input_paths: set[str] = set()
    source = value.get("source")
    if isinstance(source, dict) and isinstance(source.get("path"), str):
        input_paths.add(Path(source["path"]).as_posix())
    authoring = value.get("authoring")
    if isinstance(authoring, dict) and isinstance(authoring.get("module"), str):
        input_paths.add(Path(authoring["module"]).as_posix())
    overlap = output_paths.intersection(input_paths)
    if overlap:
        raise JobError(f"job/outputs: output overlaps declared input: {sorted(overlap)[0]}")
    timeout = value.get("timeout_seconds", 120)
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or timeout <= 0:
        raise JobError("job/timeout_seconds: expected positive number")
    _validate_source_and_authoring(value, path.parent)
    return value, raw, sha256_bytes(raw)


def _validate_source_and_authoring(job: Mapping[str, Any], root: Path) -> None:
    mode = job["mode"]
    source = job.get("source")
    if source is not None:
        if not isinstance(source, dict) or set(source) - {"kind", "path", "sha256"}:
            raise JobError("job/source: expected kind, path, sha256")
        if source.get("kind") not in _SOURCE_KINDS:
            raise JobError("job/source/kind: expected generated or edited")
        source_path = contained_path(root, source.get("path"), field="job/source/path")
        if not _is_digest(source.get("sha256")):
            raise JobError("job/source/sha256: expected sha256 digest")
        if not source_path.is_file():
            raise JobError("job/source/path: file does not exist")
        if sha256_file(source_path) != source["sha256"]:
            raise JobError("job/source/sha256: digest does not match source bytes")
    elif mode in {"edit", "render", "export"}:
        raise JobError(f"job/source: required for {mode} mode")
    authoring = job.get("authoring")
    if mode in {"generate", "edit"}:
        if not isinstance(authoring, dict) or set(authoring) - {"kind", "module", "sha256", "entrypoint"}:
            raise JobError("job/authoring: expected kind, module, sha256, entrypoint")
        expected_kind = "generated" if mode == "generate" else "edited"
        if authoring.get("kind") != expected_kind:
            raise JobError(f"job/authoring/kind: expected {expected_kind}")
        module_path = contained_path(root, authoring.get("module"), field="job/authoring/module")
        if module_path.suffix.lower() != ".py" or not module_path.is_file():
            raise JobError("job/authoring/module: expected an existing .py file")
        if not _is_digest(authoring.get("sha256")):
            raise JobError("job/authoring/sha256: expected sha256 digest")
        if sha256_file(module_path) != authoring["sha256"]:
            raise JobError("job/authoring/sha256: digest does not match module bytes")
        if not isinstance(authoring.get("entrypoint"), str) or not authoring["entrypoint"].isidentifier():
            raise JobError("job/authoring/entrypoint: expected Python identifier")
    elif authoring is not None:
        raise JobError(f"job/authoring: not allowed for {mode} mode")
    if mode == "edit" and job["source"]["kind"] != "edited":
        raise JobError("job/source/kind: edit jobs require edited source authority")
    if mode in {"render", "export"} and job["source"]["kind"] not in _SOURCE_KINDS:
        raise JobError("job/source/kind: invalid source authority")


def _copy_declared_inputs(job: Mapping[str, Any], source_root: Path, stage_root: Path) -> None:
    """Copy only hash-checked source/module inputs into the fresh job root."""

    paths: list[tuple[str, str]] = []
    source = job.get("source")
    if source:
        paths.append((source["path"], "source/path"))
    authoring = job.get("authoring")
    if authoring:
        paths.append((authoring["module"], "authoring/module"))
    for relative, label in paths:
        original = contained_path(source_root, relative, field=f"job/{label}")
        destination = contained_path(stage_root, relative, field=f"stage/{label}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, destination)


def _process_group_flags() -> dict[str, Any]:
    if os.name == "nt":
        return {"creationflags": getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)}
    return {"start_new_session": True}


def _terminate_tree(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            capture_output=True,
            timeout=10,
            check=False,
        )
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        time.sleep(0.25)
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass


def _run_process(argv: Sequence[str], cwd: Path, timeout: float) -> tuple[int, bytes, bytes, bool]:
    try:
        process = subprocess.Popen(
            list(argv),
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            **_process_group_flags(),
        )
    except FileNotFoundError:
        return EXIT_CAPABILITY, b"", f"executable not found: {argv[0]}\n".encode(), False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        _terminate_tree(process)
        stdout, stderr = process.communicate()
        stdout = stdout or exc.output or b""
        stderr = stderr or exc.stderr or b""
        return EXIT_TIMEOUT, stdout, stderr + b"process tree terminated after timeout\n", True
    return process.returncode if process.returncode is not None else EXIT_TIMEOUT, stdout, stderr, False


def _write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    _write_bytes(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def _inventory(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root).as_posix()
        try:
            size = path.stat().st_size
        except OSError:
            size = -1
        entries.append({"path": relative, "bytes": size, "sha256": sha256_file(path) if size > 0 else None})
    return entries


def _required_outputs(job: Mapping[str, Any]) -> list[str]:
    return [item["path"] for item in job["outputs"] if item.get("required", True)]


def _read_worker_result(stage: Path) -> dict[str, Any]:
    result_path = stage / "worker-result.json"
    if not result_path.is_file() or result_path.stat().st_size == 0:
        raise EvidenceError("worker-result.json is missing or empty")
    try:
        value = json.loads(result_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"worker-result.json is invalid: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError("worker-result.json must be an object")
    return value


def _verify_report(report: Any, *, glb_digest: str, name: str) -> None:
    if not isinstance(report, dict):
        raise EvidenceError(f"validation/{name}: expected object")
    if report.get("status") != "pass":
        raise EvidenceError(f"validation/{name}: status is not pass")
    if report.get("export_sha256") != glb_digest:
        raise EvidenceError(f"validation/{name}: exported hash is unrelated or stale")
    if name == "khronos" and report.get("errors") != 0:
        raise EvidenceError("validation/khronos: validator reported errors")
    if name == "gltfloader" and report.get("checks") != {"scale": "pass", "material": "pass", "animation": "pass", "collider": "pass"}:
        raise EvidenceError("validation/gltfloader: required production checks did not pass")


def _verify_promotion(job: Mapping[str, Any], stage: Path, result: Mapping[str, Any]) -> None:
    if result.get("status") != "complete":
        raise EvidenceError(f"worker status is {result.get('status')!r}")
    if result.get("job_sha256") != result.get("expected_job_sha256"):
        raise EvidenceError("worker job digest echo is missing or mismatched")
    if not _is_digest(result.get("job_sha256")):
        raise EvidenceError("worker job digest is not a sha256 identity")
    output_records = result.get("outputs")
    if not isinstance(output_records, list):
        raise EvidenceError("worker outputs inventory is missing")
    by_path = {entry.get("path"): entry for entry in output_records if isinstance(entry, dict)}
    expected = _required_outputs(job)
    for relative in expected:
        path = contained_path(stage, relative, field="worker/output")
        if not path.is_file() or path.stat().st_size == 0:
            raise EvidenceError(f"required output is missing or empty: {relative}")
        record = by_path.get(Path(relative).as_posix())
        if not isinstance(record, dict) or record.get("sha256") != sha256_file(path):
            raise EvidenceError(f"output hash is missing or mismatched: {relative}")
    inspection = result.get("inspection")
    if not isinstance(inspection, dict) or inspection.get("path") is None:
        raise EvidenceError("structural inspection evidence is missing")
    inspection_path = contained_path(stage, inspection["path"], field="worker/inspection/path")
    if not inspection_path.is_file() or inspection_path.stat().st_size == 0:
        raise EvidenceError("structural inspection evidence is missing or empty")
    previews = result.get("previews")
    if not isinstance(previews, list) or not previews:
        raise EvidenceError("render/turntable preview coverage is missing")
    for preview in previews:
        if not isinstance(preview, dict) or not isinstance(preview.get("path"), str):
            raise EvidenceError("preview inventory is malformed")
        preview_path = contained_path(stage, preview["path"], field="worker/preview/path")
        if not preview_path.is_file() or preview_path.stat().st_size == 0:
            raise EvidenceError(f"preview is missing or empty: {preview.get('path')}")
    manifest_path = next((contained_path(stage, p, field="worker/manifest") for p in expected if p.endswith("asset-manifest.json")), None)
    if manifest_path is not None:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EvidenceError(f"asset manifest is invalid: {exc}") from exc
        if not isinstance(manifest, dict):
            raise EvidenceError("asset manifest must be an object")
        glb_path = next((contained_path(stage, p, field="worker/glb") for p in expected if p.lower().endswith(".glb")), None)
        if glb_path is None:
            raise EvidenceError("asset manifest has no runtime GLB output")
        if manifest.get("source_blend_sha256") != result.get("source_blend_sha256"):
            raise EvidenceError("asset manifest source identity does not match worker result")
        if manifest.get("exported_glb_sha256") != sha256_file(glb_path):
            raise EvidenceError("asset manifest GLB identity does not match output bytes")
        validation = result.get("validation")
        if not isinstance(validation, dict):
            raise EvidenceError("validator/import evidence is missing")
        _verify_report(validation.get("khronos"), glb_digest=sha256_file(glb_path), name="khronos")
        _verify_report(validation.get("gltfloader"), glb_digest=sha256_file(glb_path), name="gltfloader")


def _finalize_manifest(stage: Path, worker_result: dict[str, Any], glb_digest: str) -> None:
    """Turn a worker's pending manifest into a complete, hash-bound record."""

    manifests = sorted(stage.rglob("*asset-manifest.json"))
    if not manifests:
        return
    if len(manifests) != 1:
        raise EvidenceError("multiple asset manifests prevent unambiguous promotion")
    path = manifests[0]
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"asset manifest is invalid: {exc}") from exc
    if manifest.get("exported_glb_sha256") != glb_digest:
        raise EvidenceError("asset manifest GLB identity changed before promotion")
    manifest["status"] = "complete"
    manifest["gaps"] = []
    _write_json(path, manifest)
    for entry in worker_result.get("outputs", []):
        if isinstance(entry, dict) and entry.get("path") == path.relative_to(stage).as_posix():
            entry["sha256"] = sha256_file(path)
            entry["bytes"] = path.stat().st_size
    _write_json(stage / "worker-result.json", worker_result)


def run_job(job_path: Path, out_dir: Path, blender_executable: Path, *, timeout: float | None = None) -> dict[str, Any]:
    """Execute a job and return a machine-readable result.

    ``out_dir`` is a fresh promotion destination.  A non-empty existing
    destination is rejected before Blender starts, preventing stale output
    from being mistaken for the current job.
    """

    job, raw_job, job_digest = load_job(job_path)
    if not blender_executable.is_absolute():
        raise JobError("blender executable must be an absolute path")
    if out_dir.exists() and any(out_dir.iterdir()):
        raise JobError("out directory must be fresh and empty")
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{job['id']}-", dir=str(out_dir.parent)))
    _copy_declared_inputs(job, job_path.parent, stage)
    staged_job = stage / job_path.name
    _write_bytes(staged_job, raw_job)
    process_timeout = float(timeout if timeout is not None else job.get("timeout_seconds", 120))
    worker = Path(__file__).resolve().with_name("blender_asset_job.py")
    argv = [
        str(blender_executable),
        "--background",
        "--factory-startup",
        "--python-exit-code",
        "23",
        "--python",
        str(worker),
        "--",
        str(staged_job),
    ]
    exit_code, stdout, stderr, timed_out = _run_process(argv, stage, process_timeout)
    _write_bytes(stage / "stdout.log", stdout)
    _write_bytes(stage / "stderr.log", stderr)
    result: dict[str, Any] = {
        "schema_version": "1.0.0",
        "kind": "blender-job-result",
        "job_id": job["id"],
        "job_sha256": job_digest,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "promoted": False,
        "staging_path": str(stage),
        "inventory": _inventory(stage),
    }
    try:
        worker_result = _read_worker_result(stage)
        result["worker"] = worker_result
        if exit_code == EXIT_OK:
            _verify_promotion(job, stage, worker_result)
            glb_paths = [contained_path(stage, item["path"], field="worker/glb") for item in job["outputs"] if item.get("kind") == "runtime" and str(item.get("path", "")).lower().endswith(".glb")]
            if glb_paths:
                _finalize_manifest(stage, worker_result, sha256_file(glb_paths[0]))
            result["promoted"] = True
    except (EvidenceError, JobError) as exc:
        result["error"] = str(exc)
        if exit_code == EXIT_OK:
            exit_code = EXIT_EVIDENCE
    result["exit_code"] = exit_code
    result["inventory"] = _inventory(stage)
    _write_json(stage / "runner-result.json", result)
    if out_dir.exists() and not any(out_dir.iterdir()):
        out_dir.rmdir()
    os.replace(stage, out_dir)
    result["staging_path"] = str(out_dir)
    return result


def _cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--job", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--blender", type=Path, help="absolute Blender executable (defaults to capability discovery)")
    parser.add_argument("--timeout", type=float, default=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _cli_parser()
    args = parser.parse_args(argv)
    try:
        blender = args.blender
        if blender is None:
            from capability_probe import locate_blender

            blender = locate_blender()
        if blender is None:
            print(json.dumps({"status": "unverified", "error": "no Blender executable was discovered", "exit_code": EXIT_CAPABILITY}, sort_keys=True))
            return EXIT_CAPABILITY
        result = run_job(args.job, args.out, blender, timeout=args.timeout)
    except JobError as exc:
        print(json.dumps({"status": "invalid", "error": str(exc), "exit_code": EXIT_INVALID}, sort_keys=True))
        return EXIT_INVALID
    except OSError as exc:
        print(json.dumps({"status": "unverified", "error": str(exc), "exit_code": EXIT_CAPABILITY}, sort_keys=True))
        return EXIT_CAPABILITY
    print(json.dumps(result, sort_keys=True))
    return int(result["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
