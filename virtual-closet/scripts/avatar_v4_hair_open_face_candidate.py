"""Create an open-face candidate from the licensed v4 long-hair base.

The rejected extracted fringe is removed. The front curtain is symmetrically
eased away from both eyes with smooth spatial falloff. No source is overwritten.
"""
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "avatar" / "avatar-v4"
OUT_BLEND = OUT / "avatar-v4-hair-open-face-candidate.blend"
scene = bpy.context.scene
body = bpy.data.objects["avatar-v4.body"]
hair = bpy.data.objects["avatar-v4.elvs_lady_hippy_hair"]
fringe = bpy.data.objects["avatar-v4.fitted-wispy-fringe"]

hair.data = hair.data.copy()
hair.name = "avatar-v4.hair-open-face-candidate"
hair.hide_render = False
hair.hide_viewport = False
fringe.hide_render = True
fringe.hide_viewport = True


def bell(value, center, radius):
    distance = abs(value - center) / radius
    return max(0.0, 1.0 - distance * distance) ** 2


# The face looks toward -Y. Open only the forward curtain around the brow/eye
# band; preserve scalp, crown, rear volume, ears, and the long-hair silhouette.
for vertex in hair.data.vertices:
    x, y, z = vertex.co
    front = bell(y, -0.155, 0.060)
    vertical = bell(z, 1.438, 0.150)
    center = bell(x, 0.0, 0.085)
    weight = front * vertical * center
    if weight <= 0.0:
        continue
    side = 1.0 if x >= 0 else -1.0
    desired_abs_x = max(abs(x), 0.050 * bell(z, 1.430, 0.125))
    vertex.co.x = x + (side * desired_abs_x - x) * weight
    # Seat the opened curtain closer to the temples instead of floating forward.
    vertex.co.y += 0.014 * weight

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
camera.data.lens = 84
views = (
    ("front", Vector((0, -height * 0.79, target.z))),
    ("right-threequarter", Vector((-height * 0.47, -height * 0.64, target.z))),
    ("left-profile", Vector((height * 0.79, 0, target.z))),
    ("rear", Vector((0, height * 0.79, target.z))),
)
for name, location in views:
    camera.location = location
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(OUT / f"hair-open-face-candidate-{name}.png")
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
print("AVATAR_V4_HAIR_OPEN_FACE_CANDIDATE", OUT_BLEND)
