"""Fit CC-BY Female hairs style 02 to face candidate 08."""
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
AVATAR = ROOT / "avatar" / "avatar-v4"
ASSET = AVATAR / "references" / "hair" / "female-hairs"
SOURCE = ASSET / "source" / "Female-Hairs.blend"
TEXTURE = ASSET / "textures" / "02.png"
OUT_BLEND = AVATAR / "avatar-v4-female-hair-02-fit-candidate.blend"
scene = bpy.context.scene
body = bpy.data.objects["avatar-v4.body"]

for old_name in (
    "avatar-v4.elvs_lady_hippy_hair",
    "avatar-v4.fitted-wispy-fringe",
):
    old = bpy.data.objects.get(old_name)
    if old:
        old.hide_render = True
        old.hide_viewport = True

with bpy.data.libraries.load(str(SOURCE), link=False) as (source, target):
    target.objects = ["02.001"] if "02.001" in source.objects else []

hair = target.objects[0]
collection = bpy.data.collections.new("FEMALE_HAIR_02_FIT_CANDIDATE")
scene.collection.children.link(collection)
collection.objects.link(hair)
hair.name = "avatar-v4.female-hair-02-candidate"
hair.hide_render = False
hair.hide_viewport = False

# Normalize the source's arranged showcase coordinates directly into avatar
# world space. Z maps crown→upper bust; X/Y are fitted independently to avoid
# the source mannequin's excessive front/back volume.
bpy.context.view_layer.update()
bpy.ops.object.select_all(action="DESELECT")
hair.select_set(True)
bpy.context.view_layer.objects.active = hair
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
points = [vertex.co.copy() for vertex in hair.data.vertices]
center_x = (min(point.x for point in points) + max(point.x for point in points)) * 0.5
center_y = (min(point.y for point in points) + max(point.y for point in points)) * 0.5
max_z = max(point.z for point in points)
for vertex in hair.data.vertices:
    vertex.co.x = (vertex.co.x - center_x) * 0.0105
    vertex.co.y = -0.090 + (vertex.co.y - center_y) * 0.0062
    vertex.co.z = 1.555 + (vertex.co.z - max_z) * 0.0105

# The source texture has no alpha; several beige front cards therefore overlay
# the eyes, nose and cheeks. Remove only central forward faces below the brow
# line, retaining the upper straight fringe and both long side curtains.
mesh_edit = bmesh.new()
mesh_edit.from_mesh(hair.data)
remove_faces = []
for face in mesh_edit.faces:
    center = face.calc_center_median()
    if center.y < -0.125 and abs(center.x) < 0.078 and center.z < 1.485:
        remove_faces.append(face)
bmesh.ops.delete(mesh_edit, geom=remove_faces, context="FACES")
mesh_edit.to_mesh(hair.data)
mesh_edit.free()
hair.data.update()

# Replace the packed source reference with the preserved project texture.
image = bpy.data.images.load(str(TEXTURE), check_existing=True)
material = hair.data.materials[0].copy()
hair.data.materials[0] = material
for node in material.node_tree.nodes:
    if node.type == "TEX_IMAGE":
        node.image = image
        texture_node = node
image.pack()

# Preserve strand variation while changing the source's pale pink/blonde atlas
# to near-black brown. The original image remains packed and unmodified.
shader = next(node for node in material.node_tree.nodes if node.type == "BSDF_PRINCIPLED")
for link in tuple(material.node_tree.links):
    if link.to_node == shader and link.to_socket.name == "Base Color":
        material.node_tree.links.remove(link)
darken = material.node_tree.nodes.new("ShaderNodeMixRGB")
darken.blend_type = "MULTIPLY"
darken.inputs[0].default_value = 1.0
darken.inputs[2].default_value = (0.095, 0.075, 0.070, 1.0)
material.node_tree.links.new(texture_node.outputs["Color"], darken.inputs[1])
material.node_tree.links.new(darken.outputs["Color"], shader.inputs["Base Color"])
shader.inputs["Roughness"].default_value = 0.48

scene.frame_set(1)
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 720
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = -0.55

body_points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
min_z = min(point.z for point in body_points)
max_body_z = max(point.z for point in body_points)
height = max_body_z - min_z
target_point = Vector((0, -height * 0.012, min_z + height * 0.885))
camera = scene.camera
camera.data.lens = 84
views = (
    ("front", Vector((0, -height * 0.79, target_point.z))),
    ("right-threequarter", Vector((-height * 0.47, -height * 0.64, target_point.z))),
    ("left-profile", Vector((height * 0.79, 0, target_point.z))),
    ("rear", Vector((0, height * 0.79, target_point.z))),
)
for name, location in views:
    camera.location = location
    camera.rotation_euler = (target_point - location).to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = str(AVATAR / f"female-hair-02-fit-candidate-{name}.png")
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
print("AVATAR_V4_FEMALE_HAIR_02_FIT_CANDIDATE", OUT_BLEND)
