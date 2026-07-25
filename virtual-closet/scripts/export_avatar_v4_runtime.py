"""Export the approved avatar-v4 pose as a reliable browser turntable GLB.

The editable checkpoint retains the complete Rigify rig. The browser review
asset intentionally bakes the evaluated frame-1 pose into ordinary meshes and
animates only a clean parent root. This avoids exporting Rigify control-bone
constraints as an invalid reduced skin.
"""
from pathlib import Path
import math

import bpy


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "avatar" / "avatar-v4"
OUTPUT = OUT / "avatar-v4-runtime.glb"

RUNTIME_MESHES = (
    "avatar-v4.body",
    "avatar-v4.elvs_lady_hippy_hair",
    "avatar-v4.eyebrow001",
    "avatar-v4.eyelashes01",
    "avatar-v4.fitted-wispy-fringe",
    "avatar-v4.gray-sleeveless-tank",
    "avatar-v4.gray-tank-black-leggings",
    "avatar-v4.low-poly",
)

RUNTIME_COLORS = {
    "avatar-v4.elvs_lady_hippy_hair": (0.012, 0.009, 0.011, 1.0),
    "avatar-v4.fitted-wispy-fringe": (0.012, 0.009, 0.011, 1.0),
    "avatar-v4.eyebrow001": (0.018, 0.012, 0.014, 1.0),
    "avatar-v4.eyelashes01": (0.008, 0.006, 0.007, 1.0),
    "avatar-v4.gray-sleeveless-tank": (0.56, 0.58, 0.59, 1.0),
    "avatar-v4.gray-tank-black-leggings": (0.025, 0.027, 0.03, 1.0),
}

def tinted_image(source_image, tint, label):
    """Copy an image and bake a color multiplier while retaining its alpha."""
    source_image.colorspace_settings.name = "sRGB"
    image = source_image.copy()
    image.name = f"{label}.runtime"
    pixels = list(image.pixels[:])
    for index in range(0, len(pixels), 4):
        pixels[index] *= tint[0]
        pixels[index + 1] *= tint[1]
        pixels[index + 2] *= tint[2]
    image.pixels[:] = pixels
    image.pack()
    return image


def export_material(source_material, source_name):
    """Create a glTF-native Principled material with one color/alpha texture."""
    material = bpy.data.materials.new(f"{source_material.name}.runtime")
    material.use_nodes = True
    material.surface_render_method = "DITHERED"
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    nodes.clear()

    output = nodes.new("ShaderNodeOutputMaterial")
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    principled.inputs["Roughness"].default_value = 0.58
    links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    source_image_node = next(
        (
            node for node in source_material.node_tree.nodes
            if node.type == "TEX_IMAGE" and node.name == "DiffuseTexture" and node.image
        ),
        None,
    ) if source_material.use_nodes else None

    if source_name in {
        "avatar-v4.gray-sleeveless-tank",
        "avatar-v4.gray-tank-black-leggings",
    }:
        principled.inputs["Base Color"].default_value = RUNTIME_COLORS[source_name]
        return material

    if source_image_node:
        image = source_image_node.image
        if "hair" in source_name or source_name == "avatar-v4.fitted-wispy-fringe":
            image = tinted_image(image, (0.055, 0.045, 0.06), source_name)
        texture = nodes.new("ShaderNodeTexImage")
        texture.name = "RuntimeColorAlpha"
        texture.image = image
        links.new(texture.outputs["Color"], principled.inputs["Base Color"])
        if (
            "hair" in source_name
            or source_name == "avatar-v4.fitted-wispy-fringe"
            or source_name in {"avatar-v4.eyebrow001", "avatar-v4.eyelashes01"}
        ):
            links.new(texture.outputs["Alpha"], principled.inputs["Alpha"])
        else:
            material.surface_render_method = "DITHERED"
            principled.inputs["Alpha"].default_value = 1.0
    else:
        principled.inputs["Base Color"].default_value = RUNTIME_COLORS.get(
            source_name, source_material.diffuse_color
        )

    return material


missing = [name for name in RUNTIME_MESHES if name not in bpy.data.objects]
if missing:
    raise RuntimeError(f"Missing runtime meshes: {missing}")

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 300
scene.frame_set(1)
bpy.context.view_layer.update()
depsgraph = bpy.context.evaluated_depsgraph_get()

collection = bpy.data.collections.new("avatar-v4.runtime-export")
scene.collection.children.link(collection)

root = bpy.data.objects.new("avatar-v4.runtime-root", None)
collection.objects.link(root)
root.rotation_mode = "XYZ"
root.rotation_euler.z = 0
root.keyframe_insert("rotation_euler", index=2, frame=1)
root.rotation_euler.z = math.tau
root.keyframe_insert("rotation_euler", index=2, frame=301)
for fcurve in root.animation_data.action.fcurves:
    for point in fcurve.keyframe_points:
        point.interpolation = "LINEAR"
root.rotation_euler.z = 0

baked = []
for source_name in RUNTIME_MESHES:
    source = bpy.data.objects[source_name]
    evaluated = source.evaluated_get(depsgraph)
    mesh = bpy.data.meshes.new_from_object(
        evaluated,
        preserve_all_data_layers=True,
        depsgraph=depsgraph,
    )
    obj = bpy.data.objects.new(f"{source.name}.runtime", mesh)
    collection.objects.link(obj)
    obj.matrix_world = source.matrix_world.copy()
    obj.parent = root
    obj.matrix_parent_inverse = root.matrix_world.inverted()
    for slot_index, source_material in enumerate(tuple(mesh.materials)):
        if source_material:
            mesh.materials[slot_index] = export_material(source_material, source_name)
    baked.append(obj)

bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object and bpy.context.object.mode != "OBJECT" else None
bpy.ops.object.select_all(action="DESELECT")
root.select_set(True)
for obj in baked:
    obj.select_set(True)
bpy.context.view_layer.objects.active = root

bpy.ops.export_scene.gltf(
    filepath=str(OUTPUT),
    export_format="GLB",
    use_selection=True,
    export_cameras=False,
    export_lights=False,
    export_yup=True,
    export_apply=False,
    export_materials="EXPORT",
    export_image_format="AUTO",
    export_texcoords=True,
    export_normals=True,
    export_tangents=False,
    export_vertex_color="MATERIAL",
    export_attributes=False,
    export_animations=True,
    export_frame_range=True,
    export_force_sampling=False,
    export_skins=False,
    export_morph=False,
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=6,
    export_draco_position_quantization=14,
    export_draco_normal_quantization=10,
    export_draco_texcoord_quantization=12,
    export_use_gltfpack=False,
)

print(f"AVATAR_V4_RUNTIME_EXPORTED {OUTPUT} {OUTPUT.stat().st_size}")
