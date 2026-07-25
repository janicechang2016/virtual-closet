"""Render standardized front thumbnails from the downloaded eight-hair source."""
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "avatar" / "avatar-v4" / "references" / "hair" / "female-hairs-inspection"
OUT.mkdir(parents=True, exist_ok=True)

meshes = [obj for obj in bpy.data.objects if obj.type == "MESH"]
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.view_settings.look = "Medium High Contrast"

world = scene.world or bpy.data.worlds.new("inspection.world")
scene.world = world
world.use_nodes = True
background = world.node_tree.nodes.get("Background")
background.inputs["Color"].default_value = (0.12, 0.12, 0.12, 1)
background.inputs["Strength"].default_value = 0.5

camera_data = bpy.data.cameras.new("inspection.camera")
camera = bpy.data.objects.new("inspection.camera", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera.data.type = "ORTHO"

light_data = bpy.data.lights.new("inspection.key", "AREA")
light = bpy.data.objects.new("inspection.key", light_data)
scene.collection.objects.link(light)
light.data.energy = 900
light.data.shape = "DISK"
light.data.size = 8

for obj in meshes:
    for candidate in meshes:
        candidate.hide_render = candidate != obj

    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    minimum = Vector(
        (
            min(point.x for point in points),
            min(point.y for point in points),
            min(point.z for point in points),
        )
    )
    maximum = Vector(
        (
            max(point.x for point in points),
            max(point.y for point in points),
            max(point.z for point in points),
        )
    )
    center = (minimum + maximum) * 0.5
    span = maximum - minimum
    camera.location = center + Vector((0, -max(span.x, span.z) * 3.0, 0))
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.ortho_scale = max(span.x, span.z) * 1.16
    light.location = center + Vector((-span.x, -span.y * 2.5, span.z))
    light.rotation_euler = (center - light.location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"{obj.name.replace('.', '-')}-front.png")
    bpy.ops.render.render(write_still=True)

print("FEMALE_HAIRS_INSPECTION", OUT)
