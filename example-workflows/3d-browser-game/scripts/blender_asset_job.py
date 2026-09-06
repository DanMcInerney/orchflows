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
import math
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


def _world_bounds(obj: Any) -> list[float]:
    corners = []
    for corner in obj.bound_box:
        world = obj.matrix_world @ type(obj.location)(corner)
        corners.extend((float(world.x), float(world.y), float(world.z)))
    return [round(min(corners[axis::3]), 6) if corners else 0.0 for axis in range(3)] + [round(max(corners[axis::3]), 6) if corners else 0.0 for axis in range(3)]


def _image_bytes(image: Any) -> int:
    packed = getattr(image, "packed_file", None)
    if packed is not None and getattr(packed, "size", 0):
        return int(packed.size)
    filepath = getattr(image, "filepath", "")
    if filepath:
        try:
            return max(0, int(Path(filepath).resolve().stat().st_size))
        except (OSError, ValueError):
            pass
    return 0


def _scene_inventory(bpy: Any) -> dict[str, Any]:
    scene = bpy.context.scene
    objects: list[dict[str, Any]] = []
    mesh_vertices = 0
    mesh_polygons = 0
    materials: set[str] = set()
    actions: list[str] = []
    mesh_normals = 0
    mesh_uv_layers = 0
    morph_targets = 0
    skeleton_bones = 0
    poses: set[str] = set()
    armatures: list[dict[str, Any]] = []
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        bounds = _world_bounds(obj)
        record: dict[str, Any] = {
            "name": obj.name,
            "type": obj.type,
            "location": [round(float(value), 6) for value in obj.location],
            "rotation": [round(float(value), 6) for value in obj.rotation_euler],
            "scale": [round(float(value), 6) for value in obj.scale],
            "bounds": bounds,
            "dimensions": [round(bounds[axis + 3] - bounds[axis], 6) for axis in range(3)],
        }
        if obj.type == "MESH" and obj.data:
            mesh_vertices += len(obj.data.vertices)
            mesh_polygons += len(obj.data.polygons)
            normal_count = sum(1 for polygon in obj.data.polygons if all(math.isfinite(float(value)) for value in polygon.normal) and polygon.normal.length > 0)
            mesh_normals += normal_count
            mesh_uv_layers += len(obj.data.uv_layers)
            morph_targets += len(getattr(obj.data, "shape_keys", None).key_blocks) - 1 if getattr(obj.data, "shape_keys", None) else 0
            record["vertices"] = len(obj.data.vertices)
            record["polygons"] = len(obj.data.polygons)
            record["uv_layers"] = len(obj.data.uv_layers)
            record["normals"] = len(obj.data.polygons) == 0 or normal_count == len(obj.data.polygons)
            record["normal_count"] = normal_count
            record["morph_targets"] = len(getattr(obj.data, "shape_keys", None).key_blocks) - 1 if getattr(obj.data, "shape_keys", None) else 0
            for material in obj.data.materials:
                if material:
                    materials.add(material.name)
        if obj.type == "ARMATURE" and obj.data:
            skeleton_bones += len(obj.data.bones)
            poses.update(bone.name for bone in obj.data.bones)
            armatures.append({
                "name": obj.name,
                "bones": [
                    {"name": bone.name, "head": [round(float(value), 6) for value in bone.head_local], "tail": [round(float(value), 6) for value in bone.tail_local]}
                    for bone in sorted(obj.data.bones, key=lambda item: item.name)
                ],
            })
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
        "animation_clips": [
            {"name": action.name, "start": round(float(action.frame_range[0]), 6), "end": round(float(action.frame_range[1]), 6), "fcurves": len(getattr(action, "fcurves", []))}
            for action in sorted(bpy.data.actions, key=lambda item: item.name)
        ],
        "mesh_normals": mesh_normals,
        "mesh_uv_layers": mesh_uv_layers,
        "texture_bytes": sum(_image_bytes(image) for image in bpy.data.images),
        "texture_count": len(bpy.data.images),
        "textures": [
            {"name": image.name, "path": image.filepath, "bytes": _image_bytes(image), "width": int(image.size[0]), "height": int(image.size[1])}
            for image in sorted(bpy.data.images, key=lambda item: item.name)
        ],
        "skeleton_bones": skeleton_bones,
        "poses": sorted(poses),
        "armatures": armatures,
        "morph_targets": morph_targets,
        "external_references": sorted({item.filepath for item in bpy.data.libraries if item.filepath}),
    }


def _validate_scene(job: Mapping[str, Any], inventory: Mapping[str, Any]) -> list[str]:
    """Compare measured Blender state with every declared requirement."""

    failures: list[str] = []
    scene = job["scene"]
    if inventory.get("units") != scene["units"] or abs(float(inventory.get("unit_scale", 0.0)) - float(scene["unit_scale"])) > 1e-9:
        failures.append("scene units or unit scale changed after job configuration")
    budgets = job["budgets"]
    measures = {
        "mesh_vertices": inventory["mesh_vertices"],
        "mesh_polygons": inventory["mesh_polygons"],
        "materials": len(inventory["materials"]),
        "texture_bytes": inventory["texture_bytes"],
        "animations": len(inventory["animation_clips"]),
        "skeleton_bones": inventory["skeleton_bones"],
    }
    for key, observed in measures.items():
        if observed > budgets[key]:
            failures.append(f"budget/{key}: observed {observed} exceeds {budgets[key]}")
    if measures["mesh_vertices"] <= 0 or measures["mesh_polygons"] <= 0:
        failures.append("runtime asset contains no mesh geometry")
    allowlists = job["allowlists"]
    objects = {item["name"] for item in inventory["objects"]}
    for name in allowlists.get("required_objects", []):
        if name not in objects:
            failures.append(f"required object is missing: {name}")
    for name in allowlists.get("required_materials", []):
        if name not in inventory["materials"]:
            failures.append(f"required material is missing: {name}")
    for name in job.get("material_roles", {}):
        if name not in inventory["materials"]:
            failures.append(f"material role references missing material: {name}")
    for name in allowlists.get("required_actions", []):
        if name not in inventory["actions"]:
            failures.append(f"required animation action is missing: {name}")
    if allowlists.get("required_normals", True) and inventory["mesh_polygons"] and inventory["mesh_normals"] != inventory["mesh_polygons"]:
        failures.append("required mesh normals are missing or non-finite")
    required_uv_layers = allowlists.get("required_uv_layers", 1 if allowlists.get("required_uvs", False) else 0)
    if required_uv_layers and any(item.get("uv_layers", 0) < required_uv_layers for item in inventory["objects"] if item["type"] == "MESH"):
        failures.append(f"required UV layers are missing: {required_uv_layers}")
    if allowlists.get("required_textures", False) and inventory["texture_bytes"] <= 0:
        failures.append("required textures have no measured bytes")
    if allowlists.get("required_armature", False) and inventory["skeleton_bones"] <= 0:
        failures.append("required armature has no measured bones")
    for clip in job.get("animation_clips", []):
        name = clip.get("name") if isinstance(clip, dict) else None
        observed = next((item for item in inventory["animation_clips"] if item["name"] == name), None)
        if observed is None:
            failures.append(f"required animation clip is missing: {name}")
            continue
        for bound in ("start", "end"):
            if bound in clip and float(observed[bound]) != float(clip[bound]):
                failures.append(f"animation/{name}/{bound}: observed {observed[bound]} expected {clip[bound]}")
    for collider in job.get("colliders", []):
        name = collider.get("name") if isinstance(collider, dict) else None
        if name and name not in objects:
            failures.append(f"required collider object is missing: {name}")
        if name and isinstance(collider, dict) and isinstance(collider.get("dimensions"), list):
            observed = next((item for item in inventory["objects"] if item["name"] == name), None)
            expected_dimensions = collider["dimensions"]
            if observed is not None and len(expected_dimensions) == 3 and any(abs(float(observed["dimensions"][index]) - float(expected_dimensions[index])) > 1e-5 for index in range(3)):
                failures.append(f"collider/{name}/dimensions: measured placement does not match declaration")
    return failures


def _write_inspection(job: Mapping[str, Any], root: Path, inventory: Mapping[str, Any], *, status: str = "complete", gaps: list[str] | None = None) -> Path:
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
        "status": status,
        "gaps": list(gaps or []),
        "invalidates": list(job["invalidates"]),
        "job_id": job["id"],
        "declared_budgets": dict(job["budgets"]),
        "declared_scene": dict(job["scene"]),
        "declared_allowlists": dict(job["allowlists"]),
        "asset": dict(inventory),
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
    labels: set[str] = set()
    for camera_record in cameras:
        if not isinstance(camera_record, dict):
            raise ValueError("job/cameras entries must be objects")
        camera_name = camera_record.get("camera")
        label = camera_record.get("label")
        if not isinstance(label, str) or not label:
            raise ValueError("camera label is required for gameplay/turntable coverage")
        labels.add(label.lower())
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
    if not any("gameplay" in label for label in labels) or not any("turntable" in label for label in labels):
        raise ValueError("camera previews must include gameplay and turntable labels")
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
        "input_hashes": list(job.get("inputs", [])),
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
        result["source_input_sha256"] = _sha256(source_input) if source_input else None
        result["source_blend_sha256"] = _sha256(source_output)
        inventory = _scene_inventory(bpy)
        failures = _validate_scene(job, inventory)
        inspection = _write_inspection(job, root, inventory, status="failed" if failures else "complete", gaps=failures)
        if failures:
            raise ValueError("scene validation failed: " + "; ".join(failures))
        previews = _render_previews(job, root, bpy)
        glb = _export_glb(job, root, bpy)
        _write_manifest(job, root, source_output, glb, inspection, previews)
        result["status"] = "complete"
        result["inspection"] = {"path": inspection.relative_to(root).as_posix(), "sha256": _sha256(inspection)}
        result["previews"] = [{"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)} for path in previews]
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
