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


# This is the shared source-to-runtime comparison tolerance.  It is frozen in
# both validators because Blender and glTF serialize floating point transforms
# at different points in the pipeline.  A declaration may tighten it, never
# widen it.
SEMANTIC_TOLERANCE = 1e-4
BLENDER_TO_RUNTIME_CONVERSION = {
    "matrix": "Rx(-pi/2)",
    "mapping": "(x,y,z)->(x,z,-y)",
    "source_up": "+Z",
    "runtime_up": "+Y",
}


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
    if "frame_rate" in units:
        frame_rate = float(units["frame_rate"])
        if not math.isfinite(frame_rate) or frame_rate <= 0:
            raise ValueError("job/scene/frame_rate must be positive")
        scene.render.fps = int(round(frame_rate))
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


def _action_fcurve_count(action: Any) -> int:
    """Count curves across both legacy and Blender 5.2 layered Actions."""

    direct = getattr(action, "fcurves", None)
    if direct is not None:
        try:
            count = len(direct)
        except TypeError:
            count = 0
        if count:
            return count
    count = 0
    for layer in getattr(action, "layers", ()):
        for strip in getattr(layer, "strips", ()):
            for channelbag in getattr(strip, "channelbags", ()):
                count += len(getattr(channelbag, "fcurves", ()))
    return count


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
    material_bindings: dict[str, dict[str, Any]] = {}
    for obj in sorted(bpy.data.objects, key=lambda item: item.name):
        bounds = _world_bounds(obj)
        world_matrix = obj.matrix_world
        world_position = [round(float(value), 6) for value in world_matrix.translation]
        world_rotation = [round(float(value), 6) for value in world_matrix.to_euler("XYZ")]
        world_scale = [round(float(value), 6) for value in world_matrix.to_scale()]
        record: dict[str, Any] = {
            "name": obj.name,
            "type": obj.type,
            "location": [round(float(value), 6) for value in obj.location],
            "rotation": [round(float(value), 6) for value in obj.rotation_euler],
            "scale": [round(float(value), 6) for value in obj.scale],
            "world_position": world_position,
            "world_rotation": world_rotation,
            "world_scale": world_scale,
            "matrix_world": [[round(float(value), 6) for value in row] for row in world_matrix],
            "parent": obj.parent.name if obj.parent else None,
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
            record["materials"] = [material.name for material in obj.data.materials if material]
            for material in obj.data.materials:
                if material:
                    materials.add(material.name)
                    binding = material_bindings.setdefault(material.name, {"objects": [], "roles": []})
                    binding["objects"].append(obj.name)
                    for property_name in ("orchflows_role", "role"):
                        role = material.get(property_name)
                        if isinstance(role, str) and role and role not in binding["roles"]:
                            binding["roles"].append(role)
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
        "material_bindings": material_bindings,
        "actions": sorted(set(actions)),
        "animation_clips": [
            {"name": action.name, "start": round(float(action.frame_range[0]), 6), "end": round(float(action.frame_range[1]), 6), "fcurves": _action_fcurve_count(action)}
            for action in sorted(bpy.data.actions, key=lambda item: item.name)
        ],
        "frame_rate": round(float(getattr(scene.render, "fps", 24.0)), 6),
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


def _numbers(value: Any, length: int, *, label: str) -> list[float] | None:
    if value is None:
        return None
    if not isinstance(value, (list, tuple)) or len(value) != length:
        raise ValueError(f"{label} must contain {length} numbers")
    converted = [float(item) for item in value]
    if not all(math.isfinite(item) for item in converted):
        raise ValueError(f"{label} must contain finite numbers")
    return converted


def _close_vector(actual: Any, expected: Any, *, label: str, tolerance: float = SEMANTIC_TOLERANCE) -> bool:
    if actual is None or expected is None:
        return False
    return len(actual) == len(expected) and all(abs(float(left) - float(right)) <= tolerance for left, right in zip(actual, expected))


def _semantic_tolerance(declaration: Mapping[str, Any]) -> float:
    value = declaration.get("tolerance", SEMANTIC_TOLERANCE)
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(float(value)):
        raise ValueError("semantic declaration tolerance must be a finite number")
    value = float(value)
    if value <= 0 or value > SEMANTIC_TOLERANCE:
        raise ValueError(f"semantic declaration tolerance must be in (0, {SEMANTIC_TOLERANCE}]" )
    return value


def _transform_failures(declaration: Mapping[str, Any], observed: Mapping[str, Any], *, kind: str, name: str) -> list[str]:
    failures: list[str] = []
    tolerance = _semantic_tolerance(declaration)
    coordinate_space = declaration.get("coordinate_space", "blender-world")
    if coordinate_space != "blender-world":
        failures.append(f"{kind}/{name}/coordinate_space: native Blender checks require blender-world declarations")
        return failures
    expected_position = _numbers(declaration.get("position"), 3, label=f"{kind}/{name}/position")
    expected_rotation = _numbers(declaration.get("rotation"), 3, label=f"{kind}/{name}/rotation")
    expected_scale = _numbers(declaration.get("scale"), 3, label=f"{kind}/{name}/scale")
    expected_dimensions = _numbers(declaration.get("dimensions"), 3, label=f"{kind}/{name}/dimensions")
    expected_bounds = _numbers(declaration.get("bounds"), 6, label=f"{kind}/{name}/bounds")
    actual_position = observed.get("world_position", observed.get("location"))
    actual_rotation = observed.get("world_rotation", observed.get("rotation"))
    actual_scale = observed.get("world_scale", observed.get("scale"))
    if expected_position is not None and not _close_vector(actual_position, expected_position, label=f"{kind}/{name}/position", tolerance=tolerance):
        failures.append(f"{kind}/{name}/position: measured Blender world position does not match declaration")
    if expected_rotation is not None and not _close_vector(actual_rotation, expected_rotation, label=f"{kind}/{name}/rotation", tolerance=tolerance):
        failures.append(f"{kind}/{name}/rotation: measured Blender world rotation does not match declaration")
    if expected_scale is not None and not _close_vector(actual_scale, expected_scale, label=f"{kind}/{name}/scale", tolerance=tolerance):
        failures.append(f"{kind}/{name}/scale: measured Blender world scale does not match declaration")
    if expected_dimensions is not None and not _close_vector(observed.get("dimensions"), expected_dimensions, label=f"{kind}/{name}/dimensions", tolerance=tolerance):
        failures.append(f"{kind}/{name}/dimensions: measured Blender world dimensions do not match declaration")
    if expected_bounds is not None and not _close_vector(observed.get("bounds"), expected_bounds, label=f"{kind}/{name}/bounds", tolerance=tolerance):
        failures.append(f"{kind}/{name}/bounds: measured Blender world bounds do not match declaration")
    if "parent" in declaration and observed.get("parent") != declaration.get("parent"):
        failures.append(f"{kind}/{name}/parent: measured parent does not match declaration")
    return failures


def _material_role_declaration(value: Any, *, material: str) -> tuple[str | None, list[str] | None]:
    if isinstance(value, str):
        return value, None
    if isinstance(value, dict):
        role = value.get("role")
        objects = value.get("objects")
        if role is not None and (not isinstance(role, str) or not role):
            raise ValueError(f"material role {material!r} has an invalid role")
        if objects is not None and (not isinstance(objects, list) or any(not isinstance(item, str) or not item for item in objects)):
            raise ValueError(f"material role {material!r} has invalid objects")
        return role, objects
    raise ValueError(f"material role {material!r} must be a role string or object")


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
    material_bindings = inventory.get("material_bindings", {})
    for name, declaration in job.get("material_roles", {}).items():
        if name not in inventory["materials"]:
            if isinstance(declaration, dict) and declaration.get("optional") is True:
                continue
            failures.append(f"material role references missing material: {name}")
            continue
        role, role_objects = _material_role_declaration(declaration, material=name)
        binding = material_bindings.get(name, {}) if isinstance(material_bindings, dict) else {}
        bound_objects = binding.get("objects", []) if isinstance(binding, dict) else []
        if not bound_objects:
            failures.append(f"material role is not bound to a mesh object: {name}")
        if role_objects is not None and any(item not in bound_objects for item in role_objects):
            failures.append(f"material role/{name}/objects: declared object binding is missing")
        actual_roles = binding.get("roles", []) if isinstance(binding, dict) else []
        if role and actual_roles and role not in actual_roles:
            failures.append(f"material role/{name}: measured role does not match declaration")
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
    frame_rate = float(inventory.get("frame_rate", job.get("scene", {}).get("frame_rate", 24.0)))
    if not math.isfinite(frame_rate) or frame_rate <= 0:
        failures.append("animation/frame_rate: measured frame rate is invalid")
        frame_rate = 24.0
    for clip in job.get("animation_clips", []):
        name = clip.get("name") if isinstance(clip, dict) else None
        observed = next((item for item in inventory["animation_clips"] if item["name"] == name), None)
        if observed is None:
            if isinstance(clip, dict) and clip.get("optional") is True:
                continue
            failures.append(f"required animation clip is missing: {name}")
            continue
        for bound in ("start", "end"):
            if bound in clip and float(observed[bound]) != float(clip[bound]):
                failures.append(f"animation/{name}/{bound}: observed {observed[bound]} expected {clip[bound]}")
        if float(observed.get("end", 0)) <= float(observed.get("start", 0)):
            failures.append(f"animation/{name}: clip range is empty")
        if int(observed.get("fcurves", 0)) <= 0:
            failures.append(f"animation/{name}: clip has no fcurves to play")
        if "duration_seconds" in clip:
            expected_duration = float(clip["duration_seconds"])
        else:
            expected_duration = (float(clip.get("end", observed.get("end", 0))) - float(clip.get("start", observed.get("start", 0)))) / frame_rate
        observed_duration = (float(observed.get("end", 0)) - float(observed.get("start", 0))) / frame_rate
        if abs(observed_duration - expected_duration) > max(SEMANTIC_TOLERANCE, 1.0 / frame_rate):
            failures.append(f"animation/{name}/duration: measured {observed_duration} expected {expected_duration}")
    for collider in job.get("colliders", []):
        name = collider.get("name") if isinstance(collider, dict) else None
        if name and name not in objects:
            if isinstance(collider, dict) and collider.get("optional") is True:
                continue
            failures.append(f"required collider object is missing: {name}")
        if name and isinstance(collider, dict):
            observed = next((item for item in inventory["objects"] if item["name"] == name), None)
            if observed is not None:
                failures.extend(_transform_failures(collider, observed, kind="collider", name=name))
    for attachment in job.get("attachments", []):
        name = attachment.get("name") if isinstance(attachment, dict) else None
        if not name:
            failures.append("attachment declaration is missing a name")
            continue
        observed = next((item for item in inventory["objects"] if item["name"] == name), None)
        if observed is None:
            if attachment.get("optional") is True:
                continue
            failures.append(f"required attachment object is missing: {name}")
        else:
            failures.extend(_transform_failures(attachment, observed, kind="attachment", name=name))
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
        "coordinate_conversion": dict(BLENDER_TO_RUNTIME_CONVERSION),
        "semantic_tolerance": SEMANTIC_TOLERANCE,
        "declared_semantics": {
            "colliders": list(job.get("colliders", [])),
            "attachments": list(job.get("attachments", [])),
            "material_roles": dict(job.get("material_roles", {})),
            "animation_clips": list(job.get("animation_clips", [])),
            "required_extensions": list(job.get("required_extensions", [])),
        },
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


def _read_glb_json(path: Path) -> dict[str, Any]:
    """Read the JSON chunk so required extensions are checked after export."""

    raw = path.read_bytes()
    if len(raw) < 20 or raw[:4] != b"glTF" or int.from_bytes(raw[4:8], "little") != 2:
        raise ValueError("runtime export is not a glTF 2.0 binary")
    chunk_length = int.from_bytes(raw[12:16], "little")
    if raw[16:20] != b"JSON" or 20 + chunk_length > len(raw):
        raise ValueError("runtime export has no JSON chunk")
    try:
        value = json.loads(raw[20 : 20 + chunk_length].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("runtime export JSON chunk is invalid") from exc
    if not isinstance(value, dict):
        raise ValueError("runtime export JSON chunk must be an object")
    return value


def _validate_export_semantics(job: Mapping[str, Any], path: Path) -> list[str]:
    """Check declarations that only become observable in exported glTF."""

    document = _read_glb_json(path)
    used = set(document.get("extensionsUsed", [])) if isinstance(document.get("extensionsUsed", []), list) else set()
    required = set(document.get("extensionsRequired", [])) if isinstance(document.get("extensionsRequired", []), list) else set()
    failures: list[str] = []
    for extension in job.get("required_extensions", []):
        name = extension.get("name") if isinstance(extension, dict) else extension
        if not isinstance(name, str) or not name:
            failures.append("extension declaration has no name")
            continue
        if name not in used and name not in required:
            failures.append(f"required extension is absent from exported GLB: {name}")
    return failures


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
        "semantic_contract": {
            "coordinate_conversion": dict(BLENDER_TO_RUNTIME_CONVERSION),
            "tolerance": SEMANTIC_TOLERANCE,
            "source_coordinate_space": "blender-world",
            "runtime_coordinate_space": "three-world",
            "runtime_budget_fields": [key for key in ("runtime_bytes", "draw_calls", "load_time_ms") if key in job.get("budgets", {})],
        },
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
        export_failures = _validate_export_semantics(job, glb)
        if export_failures:
            raise ValueError("export validation failed: " + "; ".join(export_failures))
        _write_manifest(job, root, source_output, glb, inspection, previews)
        result["status"] = "complete"
        result["inspection"] = {"path": inspection.relative_to(root).as_posix(), "sha256": _sha256(inspection)}
        result["previews"] = [{"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)} for path in previews]
        result["semantics"] = {
            "status": "complete",
            "coordinate_conversion": dict(BLENDER_TO_RUNTIME_CONVERSION),
            "tolerance": SEMANTIC_TOLERANCE,
            "checks": {"colliders": "pass", "attachments": "pass", "material_roles": "pass", "animation_clips": "pass", "required_extensions": "pass"},
        }
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
