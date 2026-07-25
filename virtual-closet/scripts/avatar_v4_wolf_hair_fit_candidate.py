"""Fit the preserved CC-BY Wolf Hair source to face candidate 08."""
from pathlib import Path

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
AVATAR = ROOT / "avatar" / "avatar-v4"
ASSET = AVATAR / "references" / "hair" / "wolf-hair"
SOURCE = ASSET / "source" / "Hair.blend"
TEXTURE = ASSET / "textures" / "HairStrand.jpg"
OUT_BLEND = AVATAR / "avatar-v4-wolf-hair-fit-candidate.blend"

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
    target.objects = [name for name in ("FrontHair", "SideHair", "WolfHair") if name in source.objects]

collection = bpy.data.collections.new("WOLF_HAIR_FIT_CANDIDATE")
scene.collection.children.link(collection)
imported = []
for obj in target.objects:
    if obj is None:
        continue
    # Appended objects are not linked to this scene automatically.
    collection.objects.link(obj)
    obj.name = f"avatar-v4.wolf-{obj.name.lower()}"
    obj.location.z -= 0.045
    imported.append(obj)

# Fit the source's much larger mannequin head around the MPFB crown. Work in
# world space so all three independently transformed layers remain registered.
crown = Vector((0.0, -0.045, 1.675))
for obj in imported:
    matrix = obj.matrix_world.copy()
    inverse = matrix.inverted()
    for vertex in obj.data.vertices:
        world = matrix @ vertex.co
        world.x = crown.x + (world.x - crown.x) * 0.67
        world.y = crown.y + (world.y - crown.y) * 0.78 - 0.110
        world.z = crown.z + (world.z - crown.z) * 1.42
        vertex.co = inverse @ world

# Point the active image node at the preserved local texture and pack it into
# the candidate blend. The stale, unused HairStripDepth reference is removed.
image = bpy.data.images.load(str(TEXTURE), check_existing=True)
for obj in imported:
    for material in obj.data.materials:
        if not material or not material.use_nodes:
            continue
        material = material.copy()
        obj.data.materials[0] = material
        for node in material.node_tree.nodes:
            if node.type == "TEX_IMAGE":
                if node.image and node.image.name == "HairStrand.jpg":
                    node.image = image
                elif node.image and node.image.name == "HairStripDepth.png":
                    material.node_tree.nodes.remove(node)
image.pack()

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
    scene.render.filepath = str(AVATAR / f"wolf-hair-fit-candidate-{name}.png")
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT_BLEND))
print("AVATAR_V4_WOLF_HAIR_FIT_CANDIDATE", OUT_BLEND)
