"""Build and render a conservative first manual face-sculpt candidate.

This operates only on the prepared ``v3-identity-manual-sculpt`` shape key in
the separate sculpt workspace.  The approved checkpoint and sculpt workspace
are never overwritten.
"""
from math import radians
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
AVATAR = ROOT / "avatar" / "avatar-v4"
OUT_BLEND = AVATAR / "avatar-v4-face-sculpt-candidate-08.blend"
body = bpy.data.objects["avatar-v4.body"]
keys = body.data.shape_keys.key_blocks
sculpt = keys["v3-identity-manual-sculpt"]
basis = keys["Basis"]

# Candidate 05 relaxes several over-tapered approved macro values before the
# custom sculpt is evaluated. These values live only in the candidate copy.
macro_values = {
    "head-scale-horiz-decr": 0.24,
    "chin-width-decr": 0.30,
    "chin-height-decr": 0.08,
    "l-eye-scale-incr": 0.28,
    "r-eye-scale-incr": 0.28,
    "l-eye-height1-decr": 0.12,
    "r-eye-height1-decr": 0.12,
    "nose-scale-horiz-decr": 0.02,
    "nose-volume-decr": 0.03,
    "mouth-scale-horiz-incr": 0.17,
    "mouth-upperlip-volume-incr": 0.09,
    "mouth-lowerlip-volume-incr": 0.07,
}
for name, value in macro_values.items():
    keys[name].value = value

# Make the result deterministic when the script is rerun.
for index, point in enumerate(sculpt.data):
    point.co = basis.data[index].co

points = [point.co.copy() for point in basis.data]
min_z = min(point.z for point in points)
max_z = max(point.z for point in points)
height = max_z - min_z

# MakeHuman is Z-up; the face looks toward +Y in this source.
head_bottom = min_z + height * 0.805
head_top = min_z + height * 0.985
face_h = head_top - head_bottom
center_z = head_bottom + face_h * 0.52
head_points = [point for point in points if head_bottom <= point.z <= head_top]
front_y = max(point.y for point in head_points)


def bell(value, center, radius):
    distance = abs(value - center) / radius
    return max(0.0, 1.0 - distance * distance) ** 2


for index, source in enumerate(points):
    x, y, z = source
    if z < head_bottom or z > head_top:
        continue

    nz = (z - head_bottom) / face_h
    target = sculpt.data[index].co

    # A softly tapered oval: retain forehead breadth, add mid-cheek fullness,
    # narrow the lower jaw, and reduce the pointed lower-chin impression.
    if nz > 0.22:
        cheek = bell(nz, 0.49, 0.27)
        jaw = bell(nz, 0.25, 0.20)
        forehead = bell(nz, 0.76, 0.24)
        x_scale = 1.0 + 0.024 * cheek + 0.008 * forehead - 0.012 * jaw
        target.x = x * x_scale

    # Slightly lengthen the upper/mid face while lifting the very bottom of the
    # chin. This matches the reference's long oval without making a sharp V.
    vertical = bell(nz, 0.56, 0.43)
    target.z += face_h * 0.012 * vertical * (nz - 0.48)
    if nz < 0.20:
        target.z -= face_h * 0.006 * bell(nz, 0.10, 0.12)

    # Symmetric socket spacing. The face points toward -Y; restrict this to the
    # eyelid/front-face band so the temples and rear cranium do not move.
    eye_socket_z = head_bottom + face_h * 0.60
    socket_weight = (
        bell(z, eye_socket_z, face_h * 0.075)
        * bell(abs(x), height * 0.027, height * 0.025)
        * bell(y, -height * 0.073, height * 0.030)
    )
    if socket_weight and abs(x) > height * 0.004:
        target.x += (1.0 if x > 0 else -1.0) * height * 0.0018 * socket_weight

    # Front-feature work is limited to the forward half of the head.
    frontness = bell(y, front_y, height * 0.070)
    if frontness <= 0.0:
        continue

    # Profile correction: flatten the overly domed frontal plane slightly.
    # The identity reference has a straighter forehead-to-brow transition.
    forehead_weight = bell(z, head_bottom + face_h * 0.77, face_h * 0.18) * frontness
    target.y -= height * 0.0030 * forehead_weight

    # Eye aperture: modest horizontal opening and slight vertical flattening,
    # producing the reference's relaxed almond shape without moving the globes.
    eye_z = head_bottom + face_h * 0.60
    eye_band = bell(z, eye_z, face_h * 0.075)
    eye_side = bell(abs(x), height * 0.027, height * 0.024)
    eye_weight = eye_band * eye_side * frontness
    if eye_weight:
        target.x *= 1.0 + 0.060 * eye_weight
        target.z = eye_z + (target.z - eye_z) * (1.0 - 0.045 * eye_weight)

    # Narrow the nose body while preserving nostril structure; add a restrained
    # bridge/tip projection based on the accepted profile guidance.
    nose_z = head_bottom + face_h * 0.45
    nose_band = bell(z, nose_z, face_h * 0.19)
    nose_side = bell(x, 0.0, height * 0.021)
    nose_weight = nose_band * nose_side * frontness
    if nose_weight:
        target.x *= 1.0 - 0.025 * nose_weight
        target.y += height * 0.0080 * nose_weight

    # Broaden the neutral mouth slightly and soften the lower-face taper.
    mouth_z = head_bottom + face_h * 0.29
    mouth_band = bell(z, mouth_z, face_h * 0.075)
    mouth_side = bell(x, 0.0, height * 0.036)
    mouth_weight = mouth_band * mouth_side * frontness
    if mouth_weight:
        target.x *= 1.0 + 0.090 * mouth_weight
        # Retract the lip/muzzle zone relative to the nose bridge and tip.
        target.y -= height * 0.0060 * mouth_weight

    # Bring the central chin just forward of the neck while keeping it behind
    # the lower lip, restoring the reference's clean jaw-to-chin line.
    chin_z = head_bottom + face_h * 0.12
    chin_weight = bell(z, chin_z, face_h * 0.10) * bell(x, 0.0, height * 0.034)
    if chin_weight:
        target.y += height * 0.0025 * chin_weight

sculpt.value = 1.0
sculpt.slider_min = 0.0
sculpt.slider_max = 1.0

# Move the paired eye accessories by the same 3 mm per side as the socket
# centers. Each object contains both left and right halves split by local X.
eye_shift = height * 0.0018
for object_name in (
    "avatar-v4.low-poly",
    "avatar-v4.eyebrow001",
    "avatar-v4.eyelashes01",
):
    obj = bpy.data.objects[object_name]
    obj.data = obj.data.copy()
    for vertex in obj.data.vertices:
        if abs(vertex.co.x) > height * 0.004:
            vertex.co.x += eye_shift if vertex.co.x > 0 else -eye_shift

# Candidate 07 keeps candidate 06 geometry and replaces the washed-out sculpt
# gate with restrained portrait lighting. This reveals facial planes without
# baking pores, marks, complexion changes, or generated asymmetry into identity.
for light_name, energy_scale in (
    ("studio.key", 0.62),
    ("studio.fill", 0.48),
    ("studio.rim", 0.55),
):
    light = bpy.data.objects.get(light_name)
    if light:
        light.data.energy *= energy_scale

for hair_name in (
    "avatar-v4.elvs_lady_hippy_hair",
    "avatar-v4.fitted-wispy-fringe",
):
    hair = bpy.data.objects.get(hair_name)
    if hair:
        hair.hide_render = True

scene = bpy.context.scene
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

world_points = [body.matrix_world @ point.co for point in basis.data]
world_min_z = min(point.z for point in world_points)
world_max_z = max(point.z for point in world_points)
world_height = world_max_z - world_min_z
target = Vector((0, -world_height * 0.012, world_min_z + world_height * 0.885))
camera = scene.camera
camera.data.lens = 84

views = (
    ("front", Vector((0, -world_height * 0.79, target.z))),
    (
        "right-threequarter",
        Vector((-world_height * 0.47, -world_height * 0.64, target.z)),
    ),
    ("left-profile", Vector((world_height * 0.79, 0, target.z))),
)
for name, location in views:
    camera.location = location
    camera.rotation_euler = (target - location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(AVATAR / f"face-sculpt-candidate-08-{name}.png")
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
print("AVATAR_V4_FACE_SCULPT_CANDIDATE", OUT_BLEND)
