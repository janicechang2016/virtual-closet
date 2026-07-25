"""Render the current v4 hair layers separately on face candidate 08."""
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "avatar" / "avatar-v4"
scene = bpy.context.scene
body = bpy.data.objects["avatar-v4.body"]
base = bpy.data.objects["avatar-v4.elvs_lady_hippy_hair"]
fringe = bpy.data.objects["avatar-v4.fitted-wispy-fringe"]

scene.frame_set(1)
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = -0.55

points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
min_z = min(point.z for point in points)
max_z = max(point.z for point in points)
height = max_z - min_z
target = Vector((0, -height * 0.012, min_z + height * 0.885))
camera = scene.camera
camera.location = Vector((0, -height * 0.79, target.z))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.lens = 84

for name, show_base, show_fringe in (
    ("base-only", True, False),
    ("fringe-only", False, True),
    ("combined", True, True),
):
    base.hide_render = not show_base
    fringe.hide_render = not show_fringe
    scene.render.filepath = str(OUT / f"hair-layer-diagnostic-{name}.png")
    bpy.ops.render.render(write_still=True)

print("AVATAR_V4_HAIR_LAYER_DIAGNOSTIC", OUT)
