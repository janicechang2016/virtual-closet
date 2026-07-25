"""Render nondestructive face-morph diagnostics from the material candidate.

Hair is hidden only for these diagnostic renders so the eye, cheek, nose,
mouth, jaw and chin geometry can be judged without the current hair occlusion.
"""
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "avatar" / "avatar-v4"
scene = bpy.context.scene
body = bpy.data.objects["avatar-v4.body"]
keys = body.data.shape_keys.key_blocks

for hair_name in (
    "avatar-v4.elvs_lady_hippy_hair",
    "avatar-v4.fitted-wispy-fringe",
):
    hair = bpy.data.objects.get(hair_name)
    if hair:
        hair.hide_render = True

# Keep the approved values available as the control. The three restrained
# candidates use only existing MPFB morph keys, so no topology is changed.
control = {
    key.name: key.value
    for key in keys
    if not key.name.startswith("$") and key.name != "Basis"
}
candidates = {
    "control": {},
    "balanced": {
        "head-oval": 0.90,
        "head-scale-horiz-decr": 0.32,
        "chin-width-decr": 0.38,
        "chin-height-decr": 0.10,
        "l-cheek-volume-incr": 0.14,
        "r-cheek-volume-incr": 0.14,
        "l-eye-scale-incr": 0.19,
        "r-eye-scale-incr": 0.19,
        "l-eye-height1-decr": 0.11,
        "r-eye-height1-decr": 0.11,
        "nose-scale-horiz-decr": 0.17,
        "nose-volume-decr": 0.10,
        "mouth-scale-horiz-incr": 0.12,
        "mouth-angles-up": 0.07,
        "mouth-upperlip-volume-incr": 0.10,
        "mouth-lowerlip-volume-incr": 0.08,
        "forehead-scale-vert-decr": 0.04,
    },
    "soft-oval": {
        "head-oval": 0.96,
        "head-scale-horiz-decr": 0.36,
        "chin-width-decr": 0.34,
        "chin-height-decr": 0.08,
        "l-cheek-volume-incr": 0.18,
        "r-cheek-volume-incr": 0.18,
        "l-eye-scale-incr": 0.20,
        "r-eye-scale-incr": 0.20,
        "l-eye-height1-decr": 0.09,
        "r-eye-height1-decr": 0.09,
        "nose-scale-horiz-decr": 0.18,
        "nose-volume-decr": 0.09,
        "mouth-scale-horiz-incr": 0.14,
        "mouth-angles-up": 0.08,
        "mouth-upperlip-volume-incr": 0.11,
        "mouth-lowerlip-volume-incr": 0.09,
        "forehead-scale-vert-decr": 0.03,
    },
    "tapered": {
        "head-oval": 0.92,
        "head-scale-horiz-decr": 0.34,
        "chin-width-decr": 0.48,
        "chin-height-decr": 0.12,
        "l-cheek-volume-incr": 0.16,
        "r-cheek-volume-incr": 0.16,
        "l-eye-scale-incr": 0.21,
        "r-eye-scale-incr": 0.21,
        "l-eye-height1-decr": 0.12,
        "r-eye-height1-decr": 0.12,
        "nose-scale-horiz-decr": 0.19,
        "nose-volume-decr": 0.11,
        "mouth-scale-horiz-incr": 0.11,
        "mouth-angles-up": 0.08,
        "mouth-upperlip-volume-incr": 0.10,
        "mouth-lowerlip-volume-incr": 0.08,
        "forehead-scale-vert-decr": 0.04,
    },
}

points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
min_z = min(point.z for point in points)
max_z = max(point.z for point in points)
height = max_z - min_z
target = Vector((0, -height * 0.01, min_z + height * 0.885))
camera = scene.camera
camera.location = Vector((0, -height * 0.79, min_z + height * 0.885))
camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.lens = 84

scene.frame_set(1)
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = False
scene.view_settings.look = "AgX - Medium High Contrast"

for name, values in candidates.items():
    for key_name, value in control.items():
        keys[key_name].value = value
    for key_name, value in values.items():
        keys[key_name].value = value
    scene.render.filepath = str(OUT / f"face-geometry-diagnostic-{name}.png")
    bpy.ops.render.render(write_still=True)

# Never save the source file: this script produces diagnostics only.
print("AVATAR_V4_FACE_GEOMETRY_DIAGNOSTIC", OUT)
