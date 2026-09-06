"""The disposable Blender-side worker for one ``blender-job`` document.

The script is intentionally a plain ``bpy`` entry point. A generator or
editor is an input file whose SHA-256 identity was checked by the host runner;
it receives a small context and may use normal Blender data/BMesh APIs. This
keeps custom asset work expressive while keeping process, path, and evidence
policy in the runner.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import random
import sys
import traceback
from pathlib import Path
from typing import Any, Mapping


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return "sha256:" + digest.hexdigest()


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name("." + path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _job_path() -> Path:
    try:
        separator = sys.argv.index("--")
        raw = sys.argv[separator + 1]
    except (ValueError, IndexError):
        raise ValueError("Blender worker requires -- <job.json>")
    path = Path(raw).resolve()
    if not path.is_file():
        raise ValueError(f"job does not exist: {path}")
    return path


def _load_job(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict) or value.get("kind") != "blender-job":
        raise ValueError("job must be a blender-job object")
    if value.get("mode") not in {"generate", "edit", "render", "export"}:
        raise ValueError("job/mode is invalid")
    return value, "sha256:" + hashlib.sha256(raw).hexdigest()


def _contained(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or candidate.drive or ".." in candidate.parts or not relative:
        raise ValueError(f"path is not a safe job-relative path: {relative!r}")
    result = (root / candidate).resolve()
    try:
        result.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes job root: {relative!r}") from exc
    return result


def _output(job: Mapping[str, Any], root: Path, *, kind: str | None = None, suffix: str | None = None) -> Path | None:
    for item in job.get("outputs", []):
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        if not isinstance(path, str):
            continue
        if kind is not None and item.get("kind") != kind:
            continue
        if suffix is not None and not path.lower().endswith(suffix.lower()):
            continue
        return _contained(root, path)
    return None


def _require_output(job: Mapping[str, Any], root: Path, *, kind: str | None = None, suffix: str | None = None) -> Path:
    path = _output(job, root, kind=kind, suffix=suffix)
    if path is None:
        label = kind or suffix or "output"
        raise ValueError(f"job has no {label} output")
    return path


def _assert_finished(result: Any, operation: str) -> None:
    if not result or "FINISHED" not in result:
        raise RuntimeError(f"Blender operator {operation} returned {result!r}")


def _configure_scene(job: Mapping[str, Any], bpy: Any) -> None:
    scene = bpy.context.scene
    units = job.get("scene", {})
    if not isinstance(units, dict):
        raise ValueError("job/scene must be an object")
    unit_settings = scene.unit_settings
    unit_settings.system = units.get("units", "METRIC")
    unit_settings.scale_length = float(units.get("unit_scale", 1.0))
    if unit_settings.scale_length <= 0:
        raise ValueError("job/scene/unit_scale must be positive")
    if bpy.context.scene != scene or bpy.context.view_layer is None:
        raise RuntimeError("Blender scene/view-layer context is unavailable")


def _load_source(job: Mapping[str, Any], root: Path, bpy: Any) -> Path | None:
    source = job.get("source")
    if not source:
        return None
    source_path = _contained(root, source["path"])
    if not source_path.is_file() or source_path.stat().st_size == 0:
        raise ValueError("job/source/path is missing or empty")
    if _sha256(source_path) != source.get("sha256"):
        raise ValueError("job/source/sha256 does not match source bytes")
    _assert_finished(bpy.ops.wm.open_mainfile(filepath=str(source_path)), "wm.open_mainfile")
    return source_path


def _run_authoring(job: Mapping[str, Any], root: Path, bpy: Any, bmesh: Any) -> None:
    authoring = job.get("authoring")
    if not authoring:
        return
    sys.dont_write_bytecode = True
    module_path = _contained(root, authoring["module"])
    if not module_path.is_file() or _sha256(module_path) != authoring.get("sha256"):
        raise ValueError("job/authoring/module is missing or its digest does not match")
    module_spec = importlib.util.spec_from_file_location("orchflows_worker_authoring", module_path)
    if module_spec is None or module_spec.loader is None:
        raise ValueError("cannot load authoring module")
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    entrypoint_name = authoring["entrypoint"]
    entrypoint = getattr(module, entrypoint_name, None)
    if not callable(entrypoint):
        raise ValueError(f"authoring module has no callable {entrypoint_name!r}")
    context = {
        "job": job,
        "bpy": bpy,
        "bmesh": bmesh,
        "root": root,
        "seed": job["seed"],
        "random": random.Random(job["seed"]),
    }
    entrypoint(context)


def _scene_inventory(bpy: Any) -> dict[str, Any]:
    scene = bpy.context.scene
    objects: list[dict[str, Any]] = []
    mesh_vertices = 0
    mesh_polygons = 0
    materials: set[str] = set()
    actions: list[str] = []
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        bound = [round(float(value), 6) for corner in obj.bound_box for value in corner]
        record: dict[str, Any] = {
            "name": obj.name,
            "type": obj.type,
            "location": [round(float(value), 6) for value in obj.location],
            "scale": [round(float(value), 6) for value in obj.scale],
            "bounds": [min(bound[axis::3]) if bound else 0.0 for axis in range(3)] + [max(bound[axis::3]) if bound else 0.0 for axis in range(3)],
        }
        if obj.type == "MESH" and obj.data:
            mesh_vertices += len(obj.data.vertices)
            mesh_polygons += len(obj.data.polygons)
            record["vertices"] = len(obj.data.vertices)
            record["polygons"] = len(obj.data.polygons)
            record["uv_layers"] = len(obj.data.uv_layers)
            for material in obj.data.materials:
                if material:
                    materials.add(material.name)
        if obj.animation_data:
            if obj.animation_data.action:
                actions.append(obj.animation_data.action.name)
            record["animated"] = True
        objects.append(record)
    return {
        "scene": scene.name,
        "units": scene.unit_settings.system,
        "unit_scale": scene.unit_settings.scale_length,
        "objects": objects,
        "object_count": len(objects),
        "mesh_vertices": mesh_vertices,
        "mesh_polygons": mesh_polygons,
        "materials": sorted(materials),
        "actions": sorted(set(actions)),
        "external_references": sorted({item.filepath for item in bpy.data.libraries if item.filepath}),
    }


def _write_inspection(job: Mapping[str, Any], root: Path, bpy: Any) -> Path:
    path = _require_output(job, root, kind="inspection", suffix=".json")
    _write_json(path, {
        "schema_version": "1.0.0",
        "kind": "blender-structural-inspection",
        "id": job["id"] + "-inspection",
        "artifact_commit": job["artifact_commit"],
        "created_at": job["created_at"],
        "producer": dict(job["producer"]),
        "inputs": list(job["inputs"]),
        "environment": dict(job["environment"]),
        "status": "complete",
        "gaps": [],
        "invalidates": list(job["invalidates"]),
        "job_id": job["id"],
        "asset": _scene_inventory(bpy),
    })
    return path


def _render_previews(job: Mapping[str, Any], root: Path, bpy: Any) -> list[Path]:
    cameras = job.get("cameras", [])
    if not isinstance(cameras, list) or not cameras:
        raise ValueError("job/cameras must declare at least one gameplay or turntable camera")
    render = job.get("render", {})
    if not isinstance(render, dict):
        raise ValueError("job/render must be an object")
    scene = bpy.context.scene
    if render.get("engine"):
        scene.render.engine = render["engine"]
    resolution = render.get("resolution", [512, 512])
    if not isinstance(resolution, list) or len(resolution) != 2:
        raise ValueError("job/render/resolution must be [width, height]")
    scene.render.resolution_x = int(resolution[0])
    scene.render.resolution_y = int(resolution[1])
    scene.render.resolution_percentage = int(render.get("percentage", 100))
    scene.render.image_settings.file_format = str(render.get("format", "PNG"))
    previews: list[Path] = []
    for camera_record in cameras:
        if not isinstance(camera_record, dict):
            raise ValueError("job/cameras entries must be objects")
        camera_name = camera_record.get("camera")
        camera = bpy.data.objects.get(camera_name) if isinstance(camera_name, str) else None
        if camera is None or camera.type != "CAMERA":
            raise ValueError(f"camera is missing or not a camera object: {camera_name!r}")
        scene.camera = camera
        if scene.camera != camera or bpy.context.scene != scene:
            raise RuntimeError("camera assignment did not take effect")
        if "frame" in camera_record:
            scene.frame_set(int(camera_record["frame"]))
        output = camera_record.get("output")
        if not isinstance(output, str):
            raise ValueError("camera output must be a relative path")
        render_path = _contained(root, output)
        render_path.parent.mkdir(parents=True, exist_ok=True)
        scene.render.filepath = str(render_path)
        _assert_finished(bpy.ops.render.render(write_still=True), "render.render")
        if not render_path.is_file() or render_path.stat().st_size == 0:
            raise RuntimeError(f"render did not produce a non-empty preview: {output}")
        previews.append(render_path)
    return previews


def _save_source(job: Mapping[str, Any], root: Path, bpy: Any) -> Path:
    path = _require_output(job, root, kind="source", suffix=".blend")
    path.parent.mkdir(parents=True, exist_ok=True)
    _assert_finished(bpy.ops.wm.save_as_mainfile(filepath=str(path)), "wm.save_as_mainfile")
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("save_as_mainfile did not produce a non-empty source")
    return path


def _export_glb(job: Mapping[str, Any], root: Path, bpy: Any) -> Path:
    path = _require_output(job, root, kind="runtime", suffix=".glb")
    settings = job.get("export", {})
    if not isinstance(settings, dict):
        raise ValueError("job/export must be an object")
    path.parent.mkdir(parents=True, exist_ok=True)
    options = {
        "filepath": str(path),
        "export_format": "GLB",
        "export_yup": bool(settings.get("export_yup", True)),
        "export_animations": bool(settings.get("animations", True)),
    }
    _assert_finished(bpy.ops.export_scene.gltf(**options), "export_scene.gltf")
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError("export_scene.gltf did not produce a non-empty GLB")
    return path


def _write_manifest(job: Mapping[str, Any], root: Path, source_path: Path, glb_path: Path | None, inspection: Path, previews: list[Path]) -> Path | None:
    manifest_path = _output(job, root, kind="manifest", suffix="asset-manifest.json")
    if manifest_path is None:
        return None
    if glb_path is None:
        raise ValueError("asset manifest requires a runtime GLB output")
    scene = job.get("scene", {})
    payload = {
        "schema_version": "1.0.0",
        "kind": "asset-manifest",
        "id": job["id"] + "-asset",
        "artifact_commit": job["artifact_commit"],
        "created_at": job["created_at"],
        "producer": dict(job["producer"]),
        "inputs": list(job["inputs"]),
        "environment": dict(job["environment"]),
        "status": "unverified",
        "gaps": ["external-validation-required"],
        "invalidates": list(job["invalidates"]),
        "source_kind": job.get("source", {}).get("kind", "generated"),
        "source_blend": source_path.relative_to(root).as_posix(),
        "source_blend_sha256": _sha256(source_path),
        "runtime_glb": glb_path.relative_to(root).as_posix(),
        "exported_glb_sha256": _sha256(glb_path),
        "inspection": inspection.relative_to(root).as_posix(),
        "previews": [path.relative_to(root).as_posix() for path in previews],
        "units": scene.get("units", "METRIC"),
        "unit_scale": scene.get("unit_scale", 1.0),
        "up_axis": "+Y",
        "gameplay_forward": scene.get("gameplay_forward", "+Z"),
        "origin": scene.get("origin", "asset-origin"),
        "colliders": list(job.get("colliders", [])),
        "attachments": list(job.get("attachments", [])),
        "material_roles": dict(job.get("material_roles", {})),
        "animation_clips": list(job.get("animation_clips", [])),
        "required_extensions": list(job.get("required_extensions", [])),
    }
    _write_json(manifest_path, payload)
    return manifest_path


def execute(job_path: Path) -> dict[str, Any]:
    """Execute a job in Blender and write ``worker-result.json``."""

    job, job_digest = _load_job(job_path)
    root = job_path.parent.resolve()
    result_path = root / "worker-result.json"
    result: dict[str, Any] = {
        "schema_version": "1.0.0",
        "kind": "blender-job-result",
        "status": "running",
        "job_id": job["id"],
        "job_sha256": job_digest,
        "expected_job_sha256": job_digest,
        "source_blend_sha256": None,
        "outputs": [],
        "previews": [],
    }
    try:
        import bpy  # type: ignore
        import bmesh  # type: ignore

        random.seed(job["seed"])
        _configure_scene(job, bpy)
        source_input = _load_source(job, root, bpy)
        _run_authoring(job, root, bpy, bmesh)
        source_output = _save_source(job, root, bpy)
        inspection = _write_inspection(job, root, bpy)
        previews = _render_previews(job, root, bpy)
        glb = _export_glb(job, root, bpy)
        _write_manifest(job, root, source_output, glb, inspection, previews)
        result["status"] = "complete"
        result["source_input_sha256"] = _sha256(source_input) if source_input else None
        result["source_blend_sha256"] = _sha256(source_output)
        result["inspection"] = {"path": inspection.relative_to(root).as_posix(), "sha256": _sha256(inspection)}
        result["previews"] = [{"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)} for path in previews]
        result["validation"] = job.get("validation")
        result["outputs"] = [
            {"path": path.relative_to(root).as_posix(), "sha256": _sha256(path), "bytes": path.stat().st_size}
            for path in sorted(root.rglob("*"))
            if path.is_file() and path.name not in {"worker-result.json"}
        ]
        _write_json(result_path, result)
        return result
    except Exception as exc:
        result["status"] = "failed"
        result["error"] = str(exc)
        result["traceback"] = traceback.format_exc()
        _write_json(result_path, result)
        raise


def main() -> int:
    try:
        execute(_job_path())
    except Exception as exc:
        print(f"blender asset job failed: {exc}", file=sys.stderr)
        return 23
    print(json.dumps({"status": "complete"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
