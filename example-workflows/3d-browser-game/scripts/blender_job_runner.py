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
import math
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
SEMANTIC_TOLERANCE = 1e-4
SEMANTIC_CHECKS = ("scale", "bounds", "orientation", "material", "attachments", "animation", "extensions", "collider", "cost")
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

_REQUIRED_BUDGETS = (
    "mesh_vertices",
    "mesh_polygons",
    "materials",
    "texture_bytes",
    "animations",
    "skeleton_bones",
)
_REQUIRED_OUTPUT_KINDS = {
    "source": ".blend",
    "inspection": ".json",
    "runtime": ".glb",
    "manifest": "asset-manifest.json",
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


def _require_mapping(value: Any, *, field: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise JobError(f"{field}: expected object")
    return value


def _require_string(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise JobError(f"{field}: expected a non-empty string")
    return value


def _validate_semantic_declaration(value: Any, *, field: str, require_name: bool = True) -> None:
    if not isinstance(value, dict):
        raise JobError(f"{field}: expected object")
    allowed = {
        "name", "type", "object", "shape", "dimensions", "position", "rotation", "scale", "bounds",
        "start", "end", "duration_seconds", "tolerance", "coordinate_space", "parent", "role", "objects",
        "decoder", "optional",
    }
    unknown = set(value) - allowed
    if unknown:
        raise JobError(f"{field}: unknown fields: {', '.join(sorted(unknown))}")
    if require_name and (not isinstance(value.get("name"), str) or not value["name"]):
        raise JobError(f"{field}/name: expected a non-empty name")
    for key in ("type", "object", "shape", "parent", "role", "decoder", "coordinate_space"):
        if key in value and (not isinstance(value[key], str) or not value[key]):
            raise JobError(f"{field}/{key}: expected a non-empty string")
    for key, size in (("dimensions", 3), ("position", 3), ("rotation", 3), ("scale", 3), ("bounds", 6)):
        if key in value:
            candidate = value[key]
            if not isinstance(candidate, list) or len(candidate) != size or any(not isinstance(item, (int, float)) or isinstance(item, bool) or not math.isfinite(float(item)) for item in candidate):
                raise JobError(f"{field}/{key}: expected {size} finite numbers")
    for key in ("start", "end"):
        if key in value and (not isinstance(value[key], (int, float)) or isinstance(value[key], bool)):
            raise JobError(f"{field}/{key}: expected a number")
    if "duration_seconds" in value and (not isinstance(value["duration_seconds"], (int, float)) or isinstance(value["duration_seconds"], bool) or value["duration_seconds"] < 0):
        raise JobError(f"{field}/duration_seconds: expected a non-negative number")
    if "tolerance" in value and (not isinstance(value["tolerance"], (int, float)) or isinstance(value["tolerance"], bool) or not 0 < value["tolerance"] <= SEMANTIC_TOLERANCE):
        raise JobError(f"{field}/tolerance: expected a number in (0, {SEMANTIC_TOLERANCE}]")
    if value.get("coordinate_space", "blender-world") not in {"blender-world", "runtime-world"}:
        raise JobError(f"{field}/coordinate_space: expected blender-world or runtime-world")
    if "optional" in value and not isinstance(value["optional"], bool):
        raise JobError(f"{field}/optional: expected boolean")
    if "objects" in value and (not isinstance(value["objects"], list) or any(not isinstance(item, str) or not item for item in value["objects"])):
        raise JobError(f"{field}/objects: expected an array of names")


def _semantic_declarations(job: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "scene": dict(job["scene"]),
        "budgets": dict(job["budgets"]),
        "colliders": list(job.get("colliders", [])),
        "attachments": list(job.get("attachments", [])),
        "material_roles": dict(job.get("material_roles", {})),
        "animation_clips": list(job.get("animation_clips", [])),
        "required_extensions": list(job.get("required_extensions", [])),
    }


def semantic_expectations(job: Mapping[str, Any], manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return the canonical job/manifest declaration surface used by both probes."""

    return {
        "job_id": job["id"],
        "artifact_commit": job["artifact_commit"],
        "job_declarations": _semantic_declarations(job),
        "manifest_declarations": {
            "units": manifest.get("units"),
            "unit_scale": manifest.get("unit_scale"),
            "up_axis": manifest.get("up_axis"),
            "gameplay_forward": manifest.get("gameplay_forward"),
            "origin": manifest.get("origin"),
            "colliders": manifest.get("colliders"),
            "attachments": manifest.get("attachments"),
            "material_roles": manifest.get("material_roles"),
            "animation_clips": manifest.get("animation_clips"),
            "required_extensions": manifest.get("required_extensions"),
            "semantic_contract": manifest.get("semantic_contract"),
        },
    }


def semantic_expectations_hash(job: Mapping[str, Any], manifest: Mapping[str, Any]) -> str:
    def normalize(value: Any) -> Any:
        if isinstance(value, float) and value.is_integer():
            return int(value)
        if isinstance(value, list):
            return [normalize(item) for item in value]
        if isinstance(value, dict):
            return {key: normalize(item) for key, item in value.items()}
        return value
    canonical = json.dumps(normalize(semantic_expectations(job, manifest)), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return sha256_bytes(canonical)


def _validate_asset_contract(job: Mapping[str, Any], root: Path) -> None:
    """Validate the closed asset contract before staging or starting Blender."""

    scene = _require_mapping(job.get("scene"), field="job/scene")
    unknown_scene = set(scene) - {"units", "unit_scale", "up_axis", "gameplay_forward", "origin", "frame_rate"}
    if unknown_scene:
        raise JobError(f"job/scene: unknown fields: {', '.join(sorted(unknown_scene))}")
    for key in ("units", "unit_scale", "up_axis", "gameplay_forward", "origin"):
        if key not in scene:
            raise JobError(f"job/scene/{key}: is required")
    _require_string(scene.get("units"), field="job/scene/units")
    unit_scale = scene.get("unit_scale")
    if not isinstance(unit_scale, (int, float)) or isinstance(unit_scale, bool) or unit_scale <= 0:
        raise JobError("job/scene/unit_scale: expected a positive number")
    if scene.get("up_axis") != "+Y":
        raise JobError("job/scene/up_axis: expected +Y for runtime export")
    _require_string(scene.get("gameplay_forward"), field="job/scene/gameplay_forward")
    _require_string(scene.get("origin"), field="job/scene/origin")
    if "frame_rate" in scene and (not isinstance(scene["frame_rate"], (int, float)) or isinstance(scene["frame_rate"], bool) or not math.isfinite(float(scene["frame_rate"])) or scene["frame_rate"] <= 0):
        raise JobError("job/scene/frame_rate: expected a positive number")

    allowlists = _require_mapping(job.get("allowlists"), field="job/allowlists")
    allowed_allowlist_fields = {
        "input_extensions", "output_extensions", "required_objects", "required_materials",
        "required_actions", "required_normals", "required_uvs", "required_uv_layers",
        "required_textures", "required_armature",
    }
    unknown_allowlists = set(allowlists) - allowed_allowlist_fields
    if unknown_allowlists:
        raise JobError(f"job/allowlists: unknown fields: {', '.join(sorted(unknown_allowlists))}")
    for key in ("input_extensions", "output_extensions"):
        values = allowlists.get(key)
        if not isinstance(values, list) or not values or any(not isinstance(item, str) or not item.startswith(".") for item in values):
            raise JobError(f"job/allowlists/{key}: expected a non-empty extension array")
    for key in ("required_objects", "required_materials", "required_actions"):
        values = allowlists.get(key, [])
        if not isinstance(values, list) or any(not isinstance(item, str) or not item for item in values):
            raise JobError(f"job/allowlists/{key}: expected an array of names")
    for key in ("required_normals", "required_uvs", "required_textures"):
        if key in allowlists and not isinstance(allowlists[key], bool):
            raise JobError(f"job/allowlists/{key}: expected boolean")
    if "required_uv_layers" in allowlists:
        value = allowlists["required_uv_layers"]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise JobError("job/allowlists/required_uv_layers: expected a non-negative integer")

    budgets = _require_mapping(job.get("budgets"), field="job/budgets")
    allowed_budget_fields = set(_REQUIRED_BUDGETS) | {"runtime_bytes", "draw_calls", "load_time_ms"}
    unknown_budgets = set(budgets) - allowed_budget_fields
    if unknown_budgets:
        raise JobError(f"job/budgets: unknown fields: {', '.join(sorted(unknown_budgets))}")
    for key in _REQUIRED_BUDGETS:
        value = budgets.get(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise JobError(f"job/budgets/{key}: expected a non-negative integer")
    for key in ("runtime_bytes", "draw_calls", "load_time_ms"):
        if key in budgets and (not isinstance(budgets[key], (int, float)) or isinstance(budgets[key], bool) or not math.isfinite(float(budgets[key])) or budgets[key] < 0):
            raise JobError(f"job/budgets/{key}: expected a non-negative number")

    colliders = job.get("colliders")
    attachments = job.get("attachments")
    if not isinstance(colliders, list) or not isinstance(attachments, list):
        raise JobError("job/colliders and job/attachments: expected arrays")
    for index, declaration in enumerate(colliders):
        _validate_semantic_declaration(declaration, field=f"job/colliders/{index}")
    for index, declaration in enumerate(attachments):
        _validate_semantic_declaration(declaration, field=f"job/attachments/{index}")
    material_roles = job.get("material_roles")
    if not isinstance(material_roles, dict):
        raise JobError("job/material_roles: expected an object")
    for material, declaration in material_roles.items():
        if not isinstance(material, str) or not material:
            raise JobError("job/material_roles: material names must be non-empty strings")
        if isinstance(declaration, str):
            if not declaration:
                raise JobError(f"job/material_roles/{material}: expected a non-empty role")
        else:
            _validate_semantic_declaration(declaration, field=f"job/material_roles/{material}", require_name=False)
            if not declaration.get("role"):
                raise JobError(f"job/material_roles/{material}/role: expected a non-empty role")
    clips = job.get("animation_clips")
    if not isinstance(clips, list):
        raise JobError("job/animation_clips: expected an array")
    for index, declaration in enumerate(clips):
        _validate_semantic_declaration(declaration, field=f"job/animation_clips/{index}")
        if "start" not in declaration or "end" not in declaration:
            raise JobError(f"job/animation_clips/{index}: start and end are required")
        if float(declaration["end"]) <= float(declaration["start"]):
            raise JobError(f"job/animation_clips/{index}: end must be after start")
    extensions = job.get("required_extensions")
    if not isinstance(extensions, list) or any(not isinstance(item, str) or not item for item in extensions):
        raise JobError("job/required_extensions: expected an array of non-empty extension names")

    cameras = job.get("cameras")
    if not isinstance(cameras, list) or len(cameras) < 2:
        raise JobError("job/cameras: at least gameplay and turntable cameras are required")
    camera_outputs: set[str] = set()
    labels: set[str] = set()
    for index, camera in enumerate(cameras):
        record = _require_mapping(camera, field=f"job/cameras/{index}")
        _require_string(record.get("camera"), field=f"job/cameras/{index}/camera")
        output = _relative_path(record.get("output"), field=f"job/cameras/{index}/output")
        camera_outputs.add(output.as_posix())
        label = _require_string(record.get("label"), field=f"job/cameras/{index}/label").lower()
        labels.add(label)
        if "gameplay" not in label and "turntable" not in label:
            raise JobError(f"job/cameras/{index}/label: must identify gameplay or turntable coverage")
    if not any("gameplay" in label for label in labels) or not any("turntable" in label for label in labels):
        raise JobError("job/cameras: gameplay and turntable coverage are both required")

    render = _require_mapping(job.get("render"), field="job/render")
    _require_string(render.get("engine"), field="job/render/engine")
    resolution = render.get("resolution")
    if not isinstance(resolution, list) or len(resolution) != 2 or any(not isinstance(item, int) or isinstance(item, bool) or item < 1 for item in resolution):
        raise JobError("job/render/resolution: expected positive [width, height]")
    if not isinstance(render.get("percentage"), int) or isinstance(render.get("percentage"), bool) or not 1 <= render["percentage"] <= 100:
        raise JobError("job/render/percentage: expected an integer from 1 to 100")
    if render.get("format") not in {"PNG", "JPEG", "OPEN_EXR"}:
        raise JobError("job/render/format: expected PNG, JPEG, or OPEN_EXR")
    export = _require_mapping(job.get("export"), field="job/export")
    if export.get("export_yup") is not True or not isinstance(export.get("animations"), bool):
        raise JobError("job/export: export_yup must be true and animations must be explicit")

    outputs = job.get("outputs")
    if not isinstance(outputs, list):
        raise JobError("job/outputs: expected an array")
    output_by_kind: dict[str, list[Mapping[str, Any]]] = {}
    for index, item in enumerate(outputs):
        record = _require_mapping(item, field=f"job/outputs/{index}")
        kind = _require_string(record.get("kind"), field=f"job/outputs/{index}/kind")
        output_by_kind.setdefault(kind, []).append(record)
        if "required" not in record or record.get("required") is not True:
            raise JobError(f"job/outputs/{index}: every asset evidence output is required")
    for kind, suffix in _REQUIRED_OUTPUT_KINDS.items():
        records = output_by_kind.get(kind, [])
        if len(records) != 1:
            raise JobError(f"job/outputs: exactly one required {kind} output is required")
        path = _relative_path(records[0].get("path"), field=f"job/outputs/{kind}/path")
        normalized = path.as_posix().lower()
        if kind == "manifest" and not normalized.endswith(suffix):
            raise JobError("job/outputs/manifest/path: must end in asset-manifest.json")
        if kind != "manifest" and not normalized.endswith(suffix):
            raise JobError(f"job/outputs/{kind}/path: must end in {suffix}")
    preview_records = output_by_kind.get("preview", [])
    if len(preview_records) < 2:
        raise JobError("job/outputs: at least gameplay and turntable previews are required")
    preview_paths = {_relative_path(item.get("path"), field="job/outputs/preview/path").as_posix() for item in preview_records}
    if not camera_outputs.issubset(preview_paths):
        raise JobError("job/outputs: every camera preview must be a declared preview output")

    validation = job.get("validation")
    if not isinstance(validation, dict):
        raise JobError("job/validation: target loader probe configuration is required")
    if set(validation) - {"target_workspace", "loader_probe"}:
        raise JobError("job/validation: verdict records are not accepted as job input")
    target_workspace = _require_string(validation.get("target_workspace"), field="job/validation/target_workspace")
    target_path = Path(target_workspace)
    if not target_path.is_absolute():
        raise JobError("job/validation/target_workspace: expected an absolute target workspace")
    probe = _require_mapping(validation.get("loader_probe"), field="job/validation/loader_probe")
    if set(probe) - {"three_root", "browser_executable"}:
        raise JobError("job/validation/loader_probe: only target Three.js and browser paths may be declared")
    three_root = _relative_path(probe.get("three_root"), field="job/validation/loader_probe/three_root")
    if not three_root.parts or three_root.name == ".":
        raise JobError("job/validation/loader_probe/three_root: expected a target-relative directory")
    browser_executable = _require_string(probe.get("browser_executable"), field="job/validation/loader_probe/browser_executable")
    if not Path(browser_executable).is_absolute():
        raise JobError("job/validation/loader_probe/browser_executable: expected an absolute browser executable")

    source = job.get("source")
    if source is not None and isinstance(source, dict):
        source_path = source.get("path")
        if isinstance(source_path, str) and Path(source_path).suffix.lower() != ".blend":
            raise JobError("job/source/path: source authority must be a .blend file")
    authoring = job.get("authoring")
    if authoring is not None and isinstance(authoring, dict):
        module_path = authoring.get("module")
        if isinstance(module_path, str) and Path(module_path).suffix.lower() != ".py":
            raise JobError("job/authoring/module: authoring module must be a .py file")


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
        if not isinstance(item, dict) or set(item) != {"name", "sha256"} or not isinstance(item["name"], str) or not item["name"] or not _is_digest(item["sha256"]):
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
    _validate_asset_contract(value, path.parent)
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


def _verify_promotion(job: Mapping[str, Any], stage: Path, result: Mapping[str, Any]) -> None:
    if result.get("status") != "complete":
        raise EvidenceError(f"worker status is {result.get('status')!r}")
    if result.get("job_sha256") != result.get("expected_job_sha256"):
        raise EvidenceError("worker job digest echo is missing or mismatched")
    if not _is_digest(result.get("job_sha256")):
        raise EvidenceError("worker job digest is not a sha256 identity")
    if result.get("input_hashes") != job.get("inputs"):
        raise EvidenceError("worker input identity echo is missing or mismatched")
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
    inspection_doc = _read_json_object(inspection_path, label="structural inspection")
    if inspection_doc.get("kind") != "blender-structural-inspection" or inspection_doc.get("job_id") != job.get("id"):
        raise EvidenceError("structural inspection is not bound to this job")
    if inspection_doc.get("status") != "complete" or inspection_doc.get("gaps"):
        raise EvidenceError("structural inspection did not prove complete measured state")
    asset = inspection_doc.get("asset")
    if not isinstance(asset, dict):
        raise EvidenceError("structural inspection measured asset surface is missing")
    for key in ("mesh_vertices", "mesh_polygons", "materials", "texture_bytes", "textures", "animation_clips", "skeleton_bones", "armatures", "mesh_normals", "mesh_uv_layers", "poses", "objects"):
        if key not in asset:
            raise EvidenceError(f"structural inspection is missing measured field {key}")
    if inspection_doc.get("declared_budgets") != job.get("budgets"):
        raise EvidenceError("structural inspection budget declaration is not bound to this job")
    declared_semantics = inspection_doc.get("declared_semantics")
    expected_semantics = _semantic_declarations(job)
    if declared_semantics != {key: expected_semantics[key] for key in ("colliders", "attachments", "material_roles", "animation_clips", "required_extensions")}:
        raise EvidenceError("structural inspection semantic declarations are not bound to this job")
    if inspection_doc.get("coordinate_conversion") != {
        "matrix": "Rx(-pi/2)",
        "mapping": "(x,y,z)->(x,z,-y)",
        "source_up": "+Z",
        "runtime_up": "+Y",
    } or inspection_doc.get("semantic_tolerance") != SEMANTIC_TOLERANCE:
        raise EvidenceError("structural inspection coordinate conversion contract is missing or changed")
    previews = result.get("previews")
    if not isinstance(previews, list) or not previews:
        raise EvidenceError("render/turntable preview coverage is missing")
    for preview in previews:
        if not isinstance(preview, dict) or not isinstance(preview.get("path"), str):
            raise EvidenceError("preview inventory is malformed")
        preview_path = contained_path(stage, preview["path"], field="worker/preview/path")
        if not preview_path.is_file() or preview_path.stat().st_size == 0:
            raise EvidenceError(f"preview is missing or empty: {preview.get('path')}")
    manifest_path = next((contained_path(stage, p, field="worker/manifest") for p in expected if p.lower().endswith("asset-manifest.json")), None)
    if manifest_path is None:
        raise EvidenceError("asset manifest output is required for promotion")
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
    scene = job.get("scene", {})
    for manifest_key, expected in (
        ("units", scene.get("units")),
        ("unit_scale", scene.get("unit_scale")),
        ("up_axis", scene.get("up_axis")),
        ("gameplay_forward", scene.get("gameplay_forward")),
        ("origin", scene.get("origin")),
        ("colliders", job.get("colliders", [])),
        ("attachments", job.get("attachments", [])),
        ("material_roles", job.get("material_roles", {})),
        ("animation_clips", job.get("animation_clips", [])),
        ("required_extensions", job.get("required_extensions", [])),
    ):
        if manifest.get(manifest_key) != expected:
            raise EvidenceError(f"asset manifest {manifest_key} declaration is not bound to this job")
    worker_semantics = result.get("semantics")
    if not isinstance(worker_semantics, dict) or worker_semantics.get("status") != "complete" or worker_semantics.get("coordinate_conversion") != {
        "matrix": "Rx(-pi/2)",
        "mapping": "(x,y,z)->(x,z,-y)",
        "source_up": "+Z",
        "runtime_up": "+Y",
    } or worker_semantics.get("tolerance") != SEMANTIC_TOLERANCE or worker_semantics.get("checks") != {
        "colliders": "pass",
        "attachments": "pass",
        "material_roles": "pass",
        "animation_clips": "pass",
        "required_extensions": "pass",
    }:
        raise EvidenceError("worker semantic checks are missing or incomplete")
    if manifest.get("status") != "unverified" or not manifest.get("gaps"):
        raise EvidenceError("worker manifest must remain unverified until fresh host validation")


def _finalize_manifest(stage: Path, worker_result: dict[str, Any], glb_digest: str, validation: Mapping[str, Any], blender_identity: Mapping[str, Any]) -> None:
    """Close a pending manifest with reports produced by fresh host processes."""

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
    environment = manifest.get("environment")
    if not isinstance(environment, dict):
        raise EvidenceError("asset manifest environment identity is missing")
    blender_path = blender_identity.get("path")
    blender_hash = blender_identity.get("sha256")
    if not isinstance(blender_path, str) or not blender_path or not isinstance(blender_hash, str) or not _is_digest(blender_hash):
        raise EvidenceError("actual Blender executable identity is missing")
    environment["blender"] = f"{blender_path}#{blender_hash}"
    manifest["environment"] = environment
    canonical_khronos = dict(validation["khronos"])
    canonical_loader = dict(validation["gltf_loader"])
    for value, path_key in ((canonical_khronos, "report_path"), (canonical_loader, "evidence_path")):
        target = contained_path(stage, value[path_key], field=f"validation/{path_key}")
        value[path_key] = target.relative_to(path.parent).as_posix()
    manifest["validation"] = {"khronos": canonical_khronos, "gltf_loader": canonical_loader}
    manifest["status"] = "complete"
    manifest["gaps"] = []
    worker_result["validation"] = {"khronos": dict(validation["khronos"]), "gltf_loader": dict(validation["gltf_loader"])}
    _write_json(path, manifest)
    for entry in worker_result.get("outputs", []):
        if isinstance(entry, dict) and entry.get("path") == path.relative_to(stage).as_posix():
            entry["sha256"] = sha256_file(path)
            entry["bytes"] = path.stat().st_size
    _write_json(stage / "worker-result.json", worker_result)


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{label} is not valid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} must be a JSON object")
    return value


def _fresh_validator(
    stage: Path,
    *,
    mode: str,
    glb_path: Path,
    report_path: Path,
    job: Mapping[str, Any],
    job_path: Path,
    manifest_path: Path | None = None,
    timeout: float,
) -> dict[str, Any]:
    """Run one package-owned validator in a new bounded process."""

    node = shutil.which("node")
    helper = Path(__file__).resolve().with_name("asset_validation.mjs")
    if node is None:
        raise EvidenceError("package validator capability is unavailable: node was not found")
    if not helper.is_file():
        raise EvidenceError("package validator capability is unavailable: asset_validation.mjs is missing")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    if report_path.exists():
        raise EvidenceError(f"validator report path is stale: {report_path.name}")
    argv = [
        node,
        str(helper),
        mode,
        "--glb",
        str(glb_path),
        "--report",
        str(report_path),
        "--artifact-commit",
        str(job["artifact_commit"]),
        "--job-id",
        str(job["id"]),
    ]
    if mode == "gltf-loader":
        if manifest_path is None or not manifest_path.is_file():
            raise EvidenceError("validation/gltf-loader: worker manifest is missing before runtime probe")
        argv.extend(["--job", str(job_path), "--manifest", str(manifest_path)])
        validation = job["validation"]
        target_workspace = Path(validation["target_workspace"]).resolve()
        three_root = validation["loader_probe"]["three_root"]
        three_path = contained_path(target_workspace, three_root, field="validation/loader_probe/three_root")
        browser_executable = Path(validation["loader_probe"]["browser_executable"]).resolve()
        if not target_workspace.is_dir() or not three_path.is_dir() or not browser_executable.is_file():
            raise EvidenceError("target Three.js workspace, package, or browser executable is missing")
        animation_count = len(job.get("animation_clips", []))
        collider_count = len(job.get("colliders", []))
        argv.extend([
            "--workspace", str(target_workspace),
            "--three-root", str(Path(three_root).as_posix()),
            "--browser-executable", str(browser_executable),
            "--timeout-ms", str(max(1, int(timeout * 1000))),
        ])
    exit_code, stdout, stderr, timed_out = _run_process(argv, stage, timeout)
    _write_bytes(report_path.with_suffix(report_path.suffix + ".stdout.log"), stdout)
    _write_bytes(report_path.with_suffix(report_path.suffix + ".stderr.log"), stderr)
    if timed_out or exit_code == EXIT_TIMEOUT:
        raise EvidenceError(f"validation/{mode}: validator timed out or lost its process")
    if exit_code != EXIT_OK:
        message = stderr.decode("utf-8", errors="replace").strip()
        raise EvidenceError(f"validation/{mode}: validator exited {exit_code}{(': ' + message) if message else ''}")
    try:
        summary = json.loads(stdout.decode("utf-8").splitlines()[-1])
    except (IndexError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"validation/{mode}: validator did not emit a JSON result") from exc
    if not isinstance(summary, dict) or summary.get("status") != "pass":
        raise EvidenceError(f"validation/{mode}: validator did not report pass")
    if not report_path.is_file() or report_path.stat().st_size == 0:
        raise EvidenceError(f"validation/{mode}: fresh report is missing or empty")
    observed_hash = sha256_file(report_path)
    glb_digest = sha256_file(glb_path)
    if summary.get("export_sha256") != glb_digest and summary.get("glb_hash") != glb_digest:
        raise EvidenceError(f"validation/{mode}: report is not bound to exact GLB bytes")
    report = _read_json_object(report_path, label=f"validation/{mode} report")
    if mode == "khronos":
        if (report.get("issues") or {}).get("numErrors") != 0 or summary.get("errors") != 0:
            raise EvidenceError("validation/khronos: fresh report did not prove zero errors")
        report_hash_key = "report_sha256"
        if summary.get("report_sha256") != observed_hash:
            raise EvidenceError("validation/khronos: report hash does not match fresh bytes")
        return {
            "status": "pass",
            "errors": 0,
            "export_sha256": glb_digest,
            "validator": summary.get("validator", "gltf-validator@2.0.0-dev.3.10"),
            "report_path": report_path.relative_to(stage).as_posix(),
            report_hash_key: observed_hash,
        }
    checks = report.get("checks")
    required_checks = {"scale": "pass", "material": "pass", "animation": "pass", "collider": "pass"}
    if report.get("kind") != "gltf-loader-evidence" or report.get("source") != "live-browser" or report.get("glb_hash") != glb_digest or checks != required_checks:
        raise EvidenceError("validation/gltf-loader: fresh target browser report is incomplete")
    target_probe = report.get("target_probe")
    if not isinstance(target_probe, dict) or not isinstance(target_probe.get("path"), str) or not _is_digest(target_probe.get("sha256")):
        raise EvidenceError("validation/gltf-loader: retained browser screenshot identity is missing")
    target_probe_path = contained_path(report_path.parent, target_probe["path"], field="validation/gltf-loader/target_probe/path")
    if not target_probe_path.is_file() or target_probe_path.stat().st_size == 0 or sha256_file(target_probe_path) != target_probe["sha256"]:
        raise EvidenceError("validation/gltf-loader: retained browser screenshot bytes are missing or mismatched")
    if report.get("browser", {}).get("screenshot_sha256") != target_probe["sha256"]:
        raise EvidenceError("validation/gltf-loader: browser screenshot hash does not match retained bytes")
    target_root = report.get("target_three_root")
    if not isinstance(target_root, dict) or not isinstance(target_root.get("path"), str) or not _is_digest(target_root.get("three_module_sha256")) or not _is_digest(target_root.get("gltf_loader_sha256")):
        raise EvidenceError("validation/gltf-loader: target Three.js module identities are missing")
    expected_three_root = Path(job["validation"]["loader_probe"]["three_root"]).as_posix()
    if Path(target_root["path"]).as_posix() != expected_three_root:
        raise EvidenceError("validation/gltf-loader: target Three.js root does not match the job")
    target_workspace = Path(job["validation"]["target_workspace"]).resolve()
    target_three_root = contained_path(target_workspace, expected_three_root, field="validation/loader_probe/three_root")
    three_module = contained_path(target_three_root, "build/three.module.js", field="validation/loader_probe/three_module")
    loader_module = contained_path(target_three_root, "examples/jsm/loaders/GLTFLoader.js", field="validation/loader_probe/gltf_loader")
    if sha256_file(three_module) != target_root["three_module_sha256"] or sha256_file(loader_module) != target_root["gltf_loader_sha256"]:
        raise EvidenceError("validation/gltf-loader: target module bytes do not match evidence identities")
    observed = report.get("observed")
    if not isinstance(observed, dict) or not isinstance(observed.get("meshes"), int) or observed["meshes"] < 1 or not isinstance(observed.get("materials"), int) or observed["materials"] < observed["meshes"] or not isinstance(observed.get("animations"), int) or observed["animations"] < 0:
        raise EvidenceError("validation/gltf-loader: actual scene inspection counts are missing")
    semantic_checks = report.get("semantic_checks")
    if not isinstance(semantic_checks, dict) or any(not isinstance(semantic_checks.get(key), dict) or semantic_checks[key].get("status") not in {"pass", "not_applicable"} for key in SEMANTIC_CHECKS):
        raise EvidenceError("validation/gltf-loader: declared asset semantics were not observed and passed")
    expected_job_path = contained_path(stage, job_path.relative_to(stage), field="validation/gltf-loader/job")
    expected_job_hash = sha256_file(expected_job_path)
    if report.get("job_sha256") != expected_job_hash or report.get("expectations_hash") != semantic_expectations_hash(job, _read_json_object(manifest_path, label="asset manifest")):
        raise EvidenceError("validation/gltf-loader: semantic expectations are not bound to the staged job and manifest")
    if summary.get("evidence_sha256") != observed_hash:
        raise EvidenceError("validation/gltf-loader: evidence hash does not match fresh bytes")
    if report.get("artifact_commit") != job["artifact_commit"] or not report.get("id"):
        raise EvidenceError("validation/gltf-loader: target report identity is missing or mismatched")
    return {
        "status": "pass",
        "artifact_commit": job["artifact_commit"],
        "evidence_id": report["id"],
        "glb_hash": glb_digest,
        "evidence_path": report_path.relative_to(stage).as_posix(),
        "evidence_sha256": observed_hash,
        "checks": required_checks,
        "semantic_checks": semantic_checks,
        "coordinate_conversion": report.get("coordinate_conversion"),
        "semantic_tolerance": report.get("semantic_tolerance"),
        "job_sha256": report.get("job_sha256"),
        "expectations_hash": report.get("expectations_hash"),
    }


def _run_fresh_validators(stage: Path, job: Mapping[str, Any], glb_path: Path, job_path: Path, timeout: float) -> dict[str, Any]:
    """Require both independent validators over the final exported GLB."""

    validation_root = stage / "validation"
    manifest_path = next((contained_path(stage, item["path"], field="worker/manifest") for item in job["outputs"] if item.get("kind") == "manifest"), None)
    khronos = _fresh_validator(stage, mode="khronos", glb_path=glb_path, report_path=validation_root / "khronos-report.json", job=job, job_path=job_path, timeout=timeout)
    loader = _fresh_validator(stage, mode="gltf-loader", glb_path=glb_path, report_path=validation_root / "gltf-loader-evidence.json", job=job, job_path=job_path, manifest_path=manifest_path, timeout=timeout)
    return {"khronos": khronos, "gltf_loader": loader}


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
        "blender": {
            "path": str(blender_executable.resolve()),
            "sha256": sha256_file(blender_executable) if blender_executable.is_file() else None,
        },
        "inventory": _inventory(stage),
    }
    try:
        worker_result = _read_worker_result(stage)
        result["worker"] = worker_result
        if exit_code == EXIT_OK:
            _verify_promotion(job, stage, worker_result)
            glb_paths = [contained_path(stage, item["path"], field="worker/glb") for item in job["outputs"] if item.get("kind") == "runtime" and str(item.get("path", "")).lower().endswith(".glb")]
            if not glb_paths:
                raise EvidenceError("runtime GLB output is required for promotion")
            glb_digest = sha256_file(glb_paths[0])
            validation = _run_fresh_validators(stage, job, glb_paths[0], staged_job, process_timeout)
            _finalize_manifest(stage, worker_result, glb_digest, validation, result["blender"])
            result["worker"] = worker_result
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
