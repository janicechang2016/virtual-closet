"""Prepare a nondestructive v4 facial-sculpt workspace.

Run against avatar-v4-photoreal-material-candidate.blend. The script adds
locked, non-rendering image references and an empty manual-sculpt shape key,
then saves a separate workspace. It does not change the approved checkpoint.
"""
from math import radians
from pathlib import Path

import bpy


ROOT = Path(__file__).resolve().parent.parent
AVATAR = ROOT / "avatar" / "avatar-v4"
REFS = AVATAR / "references" / "face" / "gemini"
OUT = AVATAR / "avatar-v4-face-sculpt-workspace.blend"

body = bpy.data.objects["avatar-v4.body"]
points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
min_x = min(point.x for point in points)
max_x = max(point.x for point in points)
min_y = min(point.y for point in points)
max_y = max(point.y for point in points)
min_z = min(point.z for point in points)
max_z = max(point.z for point in points)
height = max_z - min_z
head_z = min_z + height * 0.88

# A fresh custom key is deliberately initialized to the current approved face.
# All future manual edits live here and can be muted or discarded independently.
bpy.context.view_layer.objects.active = body
body.select_set(True)
sculpt_key = body.data.shape_keys.key_blocks.get("v3-identity-manual-sculpt")
if sculpt_key is None:
    sculpt_key = body.shape_key_add(name="v3-identity-manual-sculpt", from_mix=False)
sculpt_key.value = 1.0
sculpt_key.slider_min = 0.0
sculpt_key.slider_max = 1.0

collection = bpy.data.collections.get("V3_FACE_SCULPT_REFERENCES")
if collection is None:
    collection = bpy.data.collections.new("V3_FACE_SCULPT_REFERENCES")
    bpy.context.scene.collection.children.link(collection)


def add_reference(name, filename, location, rotation):
    existing = bpy.data.objects.get(name)
    if existing:
        return existing
    image = bpy.data.images.load(str(REFS / filename), check_existing=True)
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = "IMAGE"
    obj.data = image
    obj.empty_display_size = height * 0.29
    obj.color[3] = 0.55
    obj.empty_image_depth = "BACK"
    obj.show_in_front = False
    obj.location = location
    obj.rotation_euler = tuple(radians(value) for value in rotation)
    obj.hide_render = True
    obj.hide_select = True
    obj["reference_role"] = "sculpt-only; generated geometry advisory"
    collection.objects.link(obj)
    return obj


# Front is the immutable identity master. The adjacent views are advisory for
# depth only because Gemini introduced minor cross-view inconsistencies.
front = add_reference(
    "REF.v3-face-front.IDENTITY-MASTER",
    "v3-face-front.png",
    (0, max_y + height * 0.018, head_z),
    (90, 0, 0),
)
front["authority"] = "PRIMARY_IDENTITY_AND_PROPORTIONS"

three_quarter = add_reference(
    "REF.v3-face-right-threequarter.DEPTH",
    "right-threequarter.png",
    (min_x - height * 0.34, max_y + height * 0.018, head_z),
    (90, 0, 0),
)
three_quarter["authority"] = "SECONDARY_TRANSITIONAL_VOLUME"

profile = add_reference(
    "REF.v3-face-left-profile.DEPTH",
    "left-profile.png",
    (max_x + height * 0.34, 0, head_z),
    (90, 0, 90),
)
profile["authority"] = "SECONDARY_DEPTH; MIRROR FOR OPPOSITE SIDE"

collection["identity_master"] = str(REFS / "v3-face-front.png")
collection["reference_policy"] = (
    "Front controls identity. Right three-quarter and left profile are depth-only. "
    "Ignore generated moles, pores, and cross-view asymmetry."
)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT))
print("AVATAR_V4_FACE_SCULPT_WORKSPACE", OUT)
