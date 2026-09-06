"""Small but production-shaped procedural scene used by the host probe.

It intentionally exercises the same BMesh/data API that a worker-authored
asset may use: a faceted orb, a frame ring, materials, a camera, lighting,
and one named animation action. It is a capability fixture, not a game asset.
"""

from __future__ import annotations

import math


def _material(bpy, name, color, metallic=0.0, roughness=0.45, emission=None):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*color, 1.0)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    if principled:
        principled.inputs["Base Color"].default_value = (*color, 1.0)
        principled.inputs["Metallic"].default_value = metallic
        principled.inputs["Roughness"].default_value = roughness
        if emission is not None:
            principled.inputs["Emission Color"].default_value = (*emission, 1.0)
            principled.inputs["Emission Strength"].default_value = 2.0
    return material


def build(context):
    bpy = context["bpy"]
    bmesh = context["bmesh"]

    # Start from a known empty data state without relying on selection.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    scene = bpy.context.scene
    scene.world.color = (0.008, 0.012, 0.025)

    orb_material = _material(bpy, "Probe_Orb", (0.08, 0.24, 0.72), metallic=0.35, roughness=0.24, emission=(0.02, 0.08, 0.5))
    frame_material = _material(bpy, "Probe_Frame", (0.12, 0.72, 0.95), metallic=0.8, roughness=0.2)
    ground_material = _material(bpy, "Probe_Ground", (0.02, 0.035, 0.06), metallic=0.15, roughness=0.6)

    mesh = bpy.data.meshes.new("ProbeOrbMesh")
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.2)
    bm.to_mesh(mesh)
    bm.free()
    orb = bpy.data.objects.new("ProbeOrb", mesh)
    bpy.context.collection.objects.link(orb)
    mesh.materials.append(orb_material)
    orb.rotation_euler = (0.15, 0.0, 0.2)
    orb.keyframe_insert(data_path="rotation_euler", frame=1, index=-1)
    orb.rotation_euler.z = 6.283185307
    orb.keyframe_insert(data_path="rotation_euler", frame=48, index=-1)
    if orb.animation_data and orb.animation_data.action:
        orb.animation_data.action.name = "OrbTurntable"

    ring_mesh = bpy.data.meshes.new("ProbeRingMesh")
    ring_bm = bmesh.new()
    # Blender's BMesh operator set is intentionally small and does not expose
    # a torus primitive in every release. Build the same closed surface with
    # BMesh data calls so the fixture remains portable across 5.x.
    major_segments, minor_segments = 48, 12
    ring_vertices = []
    for major in range(major_segments):
        u = 2.0 * math.pi * major / major_segments
        row = []
        for minor in range(minor_segments):
            v = 2.0 * math.pi * minor / minor_segments
            radius = 1.65 + 0.055 * math.cos(v)
            row.append(ring_bm.verts.new((radius * math.cos(u), radius * math.sin(u), 0.055 * math.sin(v))))
        ring_vertices.append(row)
    ring_bm.verts.ensure_lookup_table()
    for major in range(major_segments):
        next_major = (major + 1) % major_segments
        for minor in range(minor_segments):
            next_minor = (minor + 1) % minor_segments
            ring_bm.faces.new((ring_vertices[major][minor], ring_vertices[next_major][minor], ring_vertices[next_major][next_minor], ring_vertices[major][next_minor]))
    ring_bm.normal_update()
    ring_bm.to_mesh(ring_mesh)
    ring_bm.free()
    ring = bpy.data.objects.new("ProbeFrame", ring_mesh)
    bpy.context.collection.objects.link(ring)
    ring_mesh.materials.append(frame_material)
    ring.rotation_euler.x = 0.3

    ground_mesh = bpy.data.meshes.new("ProbeGroundMesh")
    ground_bm = bmesh.new()
    bmesh.ops.create_grid(ground_bm, x_segments=2, y_segments=2, size=12.0)
    ground_bm.to_mesh(ground_mesh)
    ground_bm.free()
    ground = bpy.data.objects.new("ProbeGround", ground_mesh)
    bpy.context.collection.objects.link(ground)
    ground.location.z = -1.35
    ground_mesh.materials.append(ground_material)

    camera_data = bpy.data.cameras.new("ProbeGameplayCamera")
    camera = bpy.data.objects.new("ProbeGameplayCamera", camera_data)
    bpy.context.collection.objects.link(camera)
    camera.location = (4.8, -6.2, 3.7)
    camera.rotation_euler = (0.0, 0.0, 0.0)
    # Point the camera at the orb using a track quaternion, avoiding an
    # operator whose context would be ambiguous in background mode.
    direction = (orb.location - camera.location).normalized()
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera_data.lens = 48
    scene.camera = camera

    for name, location, energy, color in (
        ("ProbeKey", (4.0, -4.0, 6.0), 950.0, (0.35, 0.55, 1.0)),
        ("ProbeFill", (-4.0, -1.0, 3.0), 600.0, (0.2, 0.45, 1.0)),
    ):
        light_data = bpy.data.lights.new(name, type="AREA")
        light_data.energy = energy
        light_data.color = color
        light_data.shape = "DISK"
        light_data.size = 4.0
        light = bpy.data.objects.new(name, light_data)
        bpy.context.collection.objects.link(light)
        light.location = location
        direction = orb.location - light.location
        light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
