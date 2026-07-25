"""Create a nondestructive photoreal-material candidate from approved avatar v4."""
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "avatar" / "avatar-v4"
scene = bpy.context.scene


def principled(material):
    return next(
        (node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED"),
        None,
    )


def set_input(shader, name, value):
    socket = shader.inputs.get(name)
    if socket is not None:
        socket.default_value = value


# Skin: retain the approved Asian skin diffuse map, then add restrained
# micro-surface response rather than changing identity or complexion.
body = bpy.data.objects["avatar-v4.body"]
skin = body.data.materials[0].copy()
skin.name = "avatar-v4.photoreal-skin"
body.data.materials[0] = skin
skin_shader = principled(skin)
set_input(skin_shader, "Roughness", 0.46)
set_input(skin_shader, "IOR", 1.45)
set_input(skin_shader, "Specular IOR Level", 0.32)
set_input(skin_shader, "Subsurface Weight", 0.075)
set_input(skin_shader, "Subsurface Radius", (1.0, 0.38, 0.2))
set_input(skin_shader, "Coat Weight", 0.018)
set_input(skin_shader, "Coat Roughness", 0.34)

# Eyes: preserve the brown-eye texture while adding a moist corneal highlight.
eyes = bpy.data.objects["avatar-v4.low-poly"]
eye_material = eyes.data.materials[0].copy()
eye_material.name = "avatar-v4.photoreal-eyes"
eyes.data.materials[0] = eye_material
eye_shader = principled(eye_material)
set_input(eye_shader, "Roughness", 0.16)
set_input(eye_shader, "IOR", 1.376)
set_input(eye_shader, "Specular IOR Level", 0.52)
set_input(eye_shader, "Coat Weight", 0.22)
set_input(eye_shader, "Coat Roughness", 0.08)

# Brows/lashes should remain soft, not glossy plastic.
for object_name in ("avatar-v4.eyebrow001", "avatar-v4.eyelashes01"):
    obj = bpy.data.objects[object_name]
    for index, material in enumerate(tuple(obj.data.materials)):
        if not material:
            continue
        copy = material.copy()
        copy.name = f"{material.name}.photoreal"
        obj.data.materials[index] = copy
        shader = principled(copy)
        set_input(shader, "Roughness", 0.7)
        set_input(shader, "Specular IOR Level", 0.12)

# Fabric differentiation: matte knit tank, subtly tighter leggings.
for object_name, roughness, specular in (
    ("avatar-v4.gray-sleeveless-tank", 0.82, 0.18),
    ("avatar-v4.gray-tank-black-leggings", 0.62, 0.24),
):
    obj = bpy.data.objects[object_name]
    for index, material in enumerate(tuple(obj.data.materials)):
        if not material:
            continue
        copy = material.copy()
        copy.name = f"{material.name}.photoreal"
        obj.data.materials[index] = copy
        shader = principled(copy)
        set_input(shader, "Roughness", roughness)
        set_input(shader, "Specular IOR Level", specular)

# Softer portrait-oriented studio lighting with a warm key and cool rim.
light_settings = {
    "studio.key": ((1.0, 0.91, 0.84), 520, 2.1),
    "studio.fill": ((0.82, 0.9, 1.0), 245, 2.4),
    "studio.rim": ((0.86, 0.92, 1.0), 360, 1.8),
}
for name, (color, energy, size) in light_settings.items():
    light = bpy.data.objects.get(name)
    if light:
        light.data.color = color
        light.data.energy = energy
        light.data.size = size

world = scene.world
if world and world.use_nodes:
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (0.54, 0.56, 0.58, 1)
    background.inputs["Strength"].default_value = 0.28

scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_percentage = 100
scene.render.resolution_x = 720
scene.render.resolution_y = 960
scene.render.image_settings.color_mode = "RGBA"
scene.render.film_transparent = False
scene.render.image_settings.color_depth = "8"
scene.render.fps = 30
scene.view_settings.look = "AgX - Medium High Contrast"

for frame, filename in (
    (1, "photoreal-candidate-front.png"),
    (76, "photoreal-candidate-right.png"),
    (151, "photoreal-candidate-rear.png"),
    (226, "photoreal-candidate-left.png"),
):
    scene.frame_set(frame)
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)

# Dedicated face/material gate at higher on-screen scale.
camera = scene.camera
saved_matrix = camera.matrix_world.copy()
saved_lens = camera.data.lens
body_points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
min_z = min(point.z for point in body_points)
max_z = max(point.z for point in body_points)
height = max_z - min_z
head_target = Vector((0, -height * 0.015, min_z + height * 0.88))
camera.location = Vector((0, -height * 1.12, min_z + height * 0.88))
camera.rotation_euler = (head_target - camera.location).to_track_quat("-Z", "Y").to_euler()
camera.data.lens = 78
scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.frame_set(1)
scene.render.filepath = str(OUT / "photoreal-candidate-face.png")
bpy.ops.render.render(write_still=True)
camera.matrix_world = saved_matrix
camera.data.lens = saved_lens

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "avatar-v4-photoreal-material-candidate.blend"))
print("AVATAR_V4_PHOTOREAL_MATERIAL_CANDIDATE", OUT)
