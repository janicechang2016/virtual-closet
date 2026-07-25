"""Render candidate-08 face geometry with the existing hair restored.

The source candidate remains unchanged; this produces integration previews and
a separate blend so the face can be judged in its current hairstyle context.
"""
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
AVATAR = ROOT / "avatar" / "avatar-v4"
OUT_BLEND = AVATAR / "avatar-v4-face-sculpt-candidate-08-hair-preview.blend"
scene = bpy.context.scene
body = bpy.data.objects["avatar-v4.body"]

for hair_name in (
    "avatar-v4.elvs_lady_hippy_hair",
    "avatar-v4.fitted-wispy-fringe",
):
    hair = bpy.data.objects.get(hair_name)
    if hair:
        hair.hide_render = False
        hair.hide_viewport = False

scene.frame_set(1)
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = False
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = -0.55

points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
min_z = min(point.z for point in points)
max_z = max(point.z for point in points)
height = max_z - min_z
target = Vector((0, -height * 0.012, min_z + height * 0.885))
camera = scene.camera
camera.data.lens = 84

views = (
    ("front", Vector((0, -height * 0.79, target.z))),
    ("right-threequarter", Vector((-height * 0.47, -height * 0.64, target.z))),
    ("left-profile", Vector((height * 0.79, 0, target.z))),
)
for name, location in views:
    camera.location = location
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(AVATAR / f"face-sculpt-candidate-08-hair-{name}.png")
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
print("AVATAR_V4_FACE_HAIR_INTEGRATION_PREVIEW", OUT_BLEND)
