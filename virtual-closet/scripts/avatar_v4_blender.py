"""Build the avatar-v4 foundation and deterministic selection turntable.

Run with Blender 4.5 LTS (MPFB enabled):
  Blender --background --python scripts/avatar_v4_blender.py

This is a geometry/rig/turntable foundation, not a reverse-engineering of the
inconsistent avatar-v3 angle renders. It carries v3's art direction (slim East
Asian woman, long black hair/bangs, gray tank, black leggings, barefoot) on a
single consistent mesh. Look-specific garments come after this base is approved.
"""
from pathlib import Path
import importlib
import math
import sys

import bpy
import bmesh
from mathutils import Matrix, Vector


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "avatar" / "avatar-v4"
OUT.mkdir(parents=True, exist_ok=True)
ASSETS = ROOT / "tools" / "makehuman-system-assets-pack"
SHIRTS = ROOT / "tools" / "shirts01-pack"
HAIR = ROOT / "tools" / "hair01-pack"
SHIRTS3 = ROOT / "tools" / "shirts03-pack"
HAIR2 = ROOT / "tools" / "hair02-pack"


def dynamic_import(package_suffix, key):
    for module_name in sys.modules:
        if module_name.endswith(package_suffix):
            module = importlib.import_module(module_name)
            if hasattr(module, key):
                return getattr(module, key)
    raise RuntimeError(f"MPFB module not loaded: {package_suffix}.{key}")


def mat_principled(name, base, roughness=0.5, metallic=0.0):
    material = bpy.data.materials.new(name)
    material.diffuse_color = (*base, 1.0)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*base, 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Metallic"].default_value = metallic
    return material


def patterned_material():
    material = bpy.data.materials.new("look001_pattern_placeholder")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.62

    tex = nodes.new("ShaderNodeTexNoise")
    tex.inputs["Scale"].default_value = 2.7
    tex.inputs["Detail"].default_value = 4.0
    tex.inputs["Roughness"].default_value = 0.72
    mapping = nodes.new("ShaderNodeMapping")
    coords = nodes.new("ShaderNodeTexCoord")
    ramp = nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
    stops = [
        (0.00, (0.006, 0.004, 0.008, 1)),
        (0.37, (0.025, 0.007, 0.010, 1)),
        (0.48, (0.16, 0.004, 0.008, 1)),
        (0.64, (0.38, 0.010, 0.018, 1)),
        (0.77, (0.015, 0.06, 0.38, 1)),
        (0.90, (0.015, 0.18, 0.66, 1)),
    ]
    first = ramp.color_ramp.elements[0]
    first.position, first.color = stops[0]
    for pos, color in stops[1:]:
        element = ramp.color_ramp.elements.new(pos)
        element.color = color
    links.new(coords.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    return material


def point_camera(camera, target):
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()


def keep_lower_garment_island(outfit):
    """Delete the disconnected shirt island, retaining the fitted leggings mesh."""
    mesh = bmesh.new()
    mesh.from_mesh(outfit.data)
    unseen = set(mesh.faces)
    islands = []
    while unseen:
        seed = unseen.pop()
        island = {seed}
        frontier = [seed]
        while frontier:
            face = frontier.pop()
            for edge in face.edges:
                for linked in edge.link_faces:
                    if linked in unseen:
                        unseen.remove(linked)
                        island.add(linked)
                        frontier.append(linked)
        islands.append(island)
    upper = max(islands, key=lambda island: sum(f.calc_center_median().z for f in island) / len(island))
    bmesh.ops.delete(mesh, geom=list(upper), context="FACES")
    mesh.to_mesh(outfit.data)
    mesh.free()
    outfit.data.update()


def keep_fitted_fringe(hair, min_z, height):
    """Retain only the forehead fringe from a complete fitted hairstyle."""
    mesh = bmesh.new()
    mesh.from_mesh(hair.data)
    keep = []
    for face in mesh.faces:
        center = face.calc_center_median()
        if (center.y < -height * 0.058
                and min_z + height * 0.835 < center.z < min_z + height * 0.955
                and abs(center.x) < height * 0.075):
            keep.append(face)
    doomed = [face for face in mesh.faces if face not in keep]
    bmesh.ops.delete(mesh, geom=doomed, context="FACES")
    mesh.to_mesh(hair.data)
    mesh.free()
    hair.data.update()


def shorten_hair_to_upper_bust(hair, min_z, height):
    """Trim—not compress—the lower hair at the upper-bust plane."""
    mesh = bmesh.new()
    mesh.from_mesh(hair.data)
    bmesh.ops.bisect_plane(
        mesh,
        geom=list(mesh.verts) + list(mesh.edges) + list(mesh.faces),
        plane_co=(0, 0, min_z + height * 0.73),
        plane_no=(0, 0, 1),
        clear_inner=True,
        clear_outer=False,
    )
    mesh.to_mesh(hair.data)
    mesh.free()
    hair.data.update()


def darken_hair(hair, tint=(0.025, 0.018, 0.028, 1.0)):
    """Preserve a hair asset's alpha/detail while shifting it to v3 near-black."""
    material = hair.data.materials[0]
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    image = next(node for node in nodes if node.bl_idname == "ShaderNodeTexImage" and node.image)
    for link in list(bsdf.inputs["Base Color"].links):
        links.remove(link)
    darken = nodes.new("ShaderNodeMixRGB")
    darken.blend_type = "MULTIPLY"
    darken.inputs[0].default_value = 1.0
    darken.inputs[2].default_value = tint
    links.new(image.outputs["Color"], darken.inputs[1])
    links.new(darken.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.58
    if "Specular IOR Level" in bsdf.inputs:
        bsdf.inputs["Specular IOR Level"].default_value = 0.22
    return material


def shape_v3_hair(hair, min_z, height):
    """Turn the straight system hair into a restrained, symmetric soft wave."""
    for vertex in hair.data.vertices:
        if vertex.co.z < min_z + height * 0.91:
            falloff = max(0.0, min(1.0, (min_z + height * 0.91 - vertex.co.z) / (height * 0.34)))
            phase = (vertex.co.z - min_z) * 34.0
            side = -1.0 if vertex.co.x < 0 else 1.0
            vertex.co.x += side * math.sin(phase) * height * 0.0065 * falloff
            vertex.co.y += math.cos(phase * 0.83) * height * 0.0045 * falloff
    hair.data.update()


def add_wispy_bangs(root, material, center_x, front_y, top_z, height):
    """Create a dense, level, tapered fringe suitable for a groom candidate."""
    curve = bpy.data.curves.new("avatar-v4.custom-wispy-fringe", "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = height * 0.00017
    curve.bevel_resolution = 1
    for index in range(181):
        fraction = -0.054 + index * (0.108 / 180)
        x = center_x + height * fraction
        length = height * (
            0.026
            + 0.0014 * math.sin(index * 2.17)
            + 0.0009 * math.sin(index * 0.71)
        )
        spline = curve.splines.new("BEZIER")
        spline.bezier_points.add(3)
        for point_index, (point, co) in enumerate(zip(spline.bezier_points, (
                (x, front_y + height * 0.004, top_z),
                (x + height * math.sin(index * 0.43) * 0.0008,
                 front_y, top_z - length * 0.34),
                (x + height * math.sin(index * 0.83) * 0.0012,
                 front_y - height * 0.001, top_z - length * 0.69),
                (x + height * math.sin(index * 1.37) * 0.0018,
                 front_y, top_z - length)))):
            point.co = co
            point.handle_left_type = "AUTO"
            point.handle_right_type = "AUTO"
            point.radius = (1.0, 0.9, 0.65, 0.12)[point_index]
    fringe = bpy.data.objects.new(curve.name, curve)
    bpy.context.collection.objects.link(fringe)
    fringe.data.materials.append(material)
    fringe.parent = root
    bpy.ops.object.select_all(action="DESELECT")
    fringe.select_set(True)
    bpy.context.view_layer.objects.active = fringe
    bpy.ops.object.convert(target="MESH")
    fringe = bpy.context.object
    fringe.name = "avatar-v4.fitted-wispy-fringe"
    return fringe


def v3_outfit_material():
    """Use the fitted sportsuit UV islands as v3's gray tank and black leggings."""
    material = bpy.data.materials.new("avatar-v4.v3-base-outfit")
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = 0.76
    uv = nodes.new("ShaderNodeTexCoord")
    separate = nodes.new("ShaderNodeSeparateXYZ")
    threshold = nodes.new("ShaderNodeMath")
    threshold.operation = "GREATER_THAN"
    threshold.inputs[1].default_value = 0.52
    mix = nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MIX"
    mix.inputs[1].default_value = (0.008, 0.009, 0.012, 1.0)
    mix.inputs[2].default_value = (0.20, 0.22, 0.23, 1.0)
    # Generated Z is stable for this single fitted mesh: torso above, legs below.
    links.new(uv.outputs["Generated"], separate.inputs["Vector"])
    links.new(separate.outputs["Z"], threshold.inputs[0])
    links.new(threshold.outputs[0], mix.inputs[0])
    links.new(mix.outputs[0], bsdf.inputs["Base Color"])
    return material


# Clean scene.
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

HumanService = dynamic_import("mpfb.services.humanservice", "HumanService")
TargetService = dynamic_import("mpfb.services.targetservice", "TargetService")
RigService = dynamic_import("mpfb.services.rigservice", "RigService")
HumanObjectProperties = dynamic_import("mpfb.entities.objectproperties", "HumanObjectProperties")

body = HumanService.create_human()
body.name = "avatar-v4.body"
for key, value in {
    "gender": 0.0,
    "asian": 0.84,
    "caucasian": 0.16,
    "african": 0.0,
    "age": 0.46,
    "height": 0.56,
    "weight": 0.32,
    "muscle": 0.24,
    "proportions": 0.34,
}.items():
    HumanObjectProperties.set_value(key, value, entity_reference=body)
TargetService.reapply_macro_details(body)

# V3 art-direction targets: small oval face, tapered jaw, almond eyes, compact
# nose and a subtle resting smile. These are aesthetic—not biometric—settings.
targets_root = Path(dynamic_import("mpfb.services.locationservice", "LocationService").get_mpfb_data("targets"))
for target, weight in {
    "head/head-oval.target.gz": 0.84,
    "head/head-scale-horiz-decr.target.gz": 0.30,
    "chin/chin-width-decr.target.gz": 0.46,
    "chin/chin-height-decr.target.gz": 0.14,
    "cheek/l-cheek-volume-incr.target.gz": 0.10,
    "cheek/r-cheek-volume-incr.target.gz": 0.10,
    "eyes/l-eye-scale-incr.target.gz": 0.23,
    "eyes/r-eye-scale-incr.target.gz": 0.23,
    "eyes/l-eye-height1-decr.target.gz": 0.16,
    "eyes/r-eye-height1-decr.target.gz": 0.16,
    "eyes/l-eye-epicanthus-in.target.gz": 0.22,
    "eyes/r-eye-epicanthus-in.target.gz": 0.22,
    "nose/nose-scale-horiz-decr.target.gz": 0.20,
    "nose/nose-volume-decr.target.gz": 0.14,
    "mouth/mouth-scale-horiz-incr.target.gz": 0.08,
    "mouth/mouth-angles-up.target.gz": 0.10,
    "mouth/mouth-upperlip-volume-incr.target.gz": 0.08,
    "mouth/mouth-lowerlip-volume-incr.target.gz": 0.06,
    "forehead/forehead-scale-vert-decr.target.gz": 0.08,
}.items():
    TargetService.load_target(body, str(targets_root / target), weight=weight)

HumanService.set_character_skin(
    str(ASSETS / "skins" / "young_asian_female" / "young_asian_female.mhmat"),
    body,
    skin_type="GAMEENGINE",
)
for polygon in body.data.polygons:
    polygon.use_smooth = True

# Rigify foundation: generate the production control/deform rig from MPFB's
# fitted human metarig. This supplies forearm twist, palm and finger controls
# missing from the rejected game-engine skeleton.
metarig = HumanService.add_builtin_rig(body, "rigify.human")
rig = RigService.generate_rigify_rig(metarig, meta_rig_action="delete")
rig.name = "avatar-v4.rig"

world_points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
min_x = min(v.x for v in world_points); max_x = max(v.x for v in world_points)
min_y = min(v.y for v in world_points); max_y = max(v.y for v in world_points)
min_z = min(v.z for v in world_points); max_z = max(v.z for v in world_points)
height = max_z - min_z
center_x = (min_x + max_x) / 2
center_y = (min_y + max_y) / 2

root = bpy.data.objects.new("avatar-v4.turntable-root", None)
bpy.context.collection.objects.link(root)
rig.parent = root

# Production assets conform to the same basemesh and rig, eliminating the
# floating eyes, clay hair, and torn clothing seen in the rejected prototype.
eyes = HumanService.add_mhclo_asset(
    str(ASSETS / "eyes" / "low-poly" / "low-poly.mhclo"), body,
    asset_type="Eyes", material_type="GAMEENGINE")
eyebrows = HumanService.add_mhclo_asset(
    str(ASSETS / "eyebrows" / "eyebrow001" / "eyebrow001.mhclo"), body,
    asset_type="Eyebrows", material_type="GAMEENGINE")
eyelashes = HumanService.add_mhclo_asset(
    str(ASSETS / "eyelashes" / "eyelashes01" / "eyelashes01.mhclo"), body,
    asset_type="Eyelashes", material_type="GAMEENGINE")
hair = HumanService.add_mhclo_asset(
    str(HAIR2 / "hair" / "elvs_lady_hippy_hair" / "elvs_lady_hippy_hair.mhclo"), body,
    asset_type="Hair", material_type="GAMEENGINE")
# The source texture is light brown. Preserve its strand alpha and tonal detail,
# but multiply the visible color down to v3's near-black hair.
hair_material = darken_hair(hair, tint=(0.002, 0.002, 0.004, 1.0))
fringe = HumanService.add_mhclo_asset(
    str(HAIR2 / "hair" / "elvs_katherine_hair" / "elvs_katherine_hair.mhclo"), body,
    asset_type="Hair", material_type="GAMEENGINE")
fringe.name = "avatar-v4.fitted-wispy-fringe"
darken_hair(fringe, tint=(0.002, 0.002, 0.004, 1.0))
keep_fitted_fringe(fringe, min_z, height)
outfit = HumanService.add_mhclo_asset(
    str(ASSETS / "clothes" / "female_sportsuit01" / "female_sportsuit01.mhclo"), body,
    asset_type="Clothes", material_type="GAMEENGINE")
outfit.name = "avatar-v4.gray-tank-black-leggings"
outfit.data.materials.clear()
outfit.data.materials.append(mat_principled(
    "avatar-v4.black-leggings", (0.008, 0.009, 0.012), roughness=0.78))
keep_lower_garment_island(outfit)
tank = HumanService.add_mhclo_asset(
    str(SHIRTS3 / "clothes" / "punkduck_high_neck_crop_top" / "punkduck_high_neck_crop_top.mhclo"), body,
    asset_type="Clothes", material_type="GAMEENGINE")
tank.name = "avatar-v4.gray-sleeveless-tank"
tank.data.materials.clear()
tank.data.materials.append(mat_principled(
    "avatar-v4.gray-sleeveless-tank", (0.20, 0.22, 0.23), roughness=0.76))
# The sportsuit originally included a shirt, so its mask still erases shoulders
# after that mesh island is removed. Restrict that mask to the retained leggings;
# the tank's own fitted torso mask remains active.
for modifier in body.modifiers:
    if modifier.type == "MASK" and modifier.name == "Delete.female_sportsuit01":
        group = body.vertex_groups.get(modifier.vertex_group)
        if group:
            group.remove([vertex.index for vertex in body.data.vertices
                          if vertex.co.z > min_z + height * 0.54])

# V3 neutral stance through Rigify FK controls. Lowering the complete arms from
# Rigify's fitted A-pose preserves anatomical forearm roll and turns the palms
# toward the thighs without any wrist rotation.
for side_name in ("L", "R"):
    rig.pose.bones[f"upper_arm_parent.{side_name}"]["IK_FK"] = 1.0
    rig.pose.bones[f"thigh_parent.{side_name}"]["IK_FK"] = 1.0
for bone_name, angle in (("upper_arm_fk.L", math.radians(-37)),
                         ("upper_arm_fk.R", math.radians(37))):
    bone = rig.pose.bones[bone_name]
    bone.rotation_mode = "XYZ"
    bone.rotation_euler.z = angle

# Extend the elbows from the fitted A-pose so the wrists land beside the
# thighs. Both sides use the same FK flexion value; no wrist roll is applied.
for bone_name in ("forearm_fk.L", "forearm_fk.R"):
    bone = rig.pose.bones[bone_name]
    bone.rotation_mode = "XYZ"
    bone.rotation_euler.x = math.radians(-40)

# Lightly group the four fingers for a relaxed side silhouette. Rigify's curve
# property bends the full chains without changing palm, thumb, or wrist pose.
for side_name in ("L", "R"):
    for finger_name in ("index", "middle", "ring", "pinky"):
        rig.pose.bones[
            f"f_{finger_name}.01_master.{side_name}"
        ]["finger_curve"] = 0.12

# Bring the feet to v3's close, parallel stance using the frontal-plane axis.
for bone_name, angle in (("thigh_fk.L", math.radians(6)),
                         ("thigh_fk.R", math.radians(-6))):
    bone = rig.pose.bones[bone_name]
    bone.rotation_mode = "XYZ"
    bone.rotation_euler.z = angle

bpy.context.view_layer.update()

# Turntable animation: frame 301 equals frame 1; render/export frames 1–300.
root.rotation_euler.z = 0
root.keyframe_insert(data_path="rotation_euler", index=2, frame=1)
root.rotation_euler.z = math.tau
root.keyframe_insert(data_path="rotation_euler", index=2, frame=301)
if root.animation_data and root.animation_data.action:
    for curve in root.animation_data.action.fcurves:
        for keyframe in curve.keyframe_points:
            keyframe.interpolation = "LINEAR"

# Studio stage and lighting.
floor = mat_principled("studio.floor", (0.70, 0.71, 0.70), roughness=0.88)
bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, min_z - height * 0.005))
plane = bpy.context.object
plane.name = "studio.floor"
plane.data.materials.append(floor)

world = bpy.context.scene.world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.70, 0.71, 0.70, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.22

for name, location, energy, size in [
    ("key", (-height * 1.1, -height * 1.5, min_z + height * 1.45), 620, height * 0.8),
    ("fill", (height * 1.2, -height * 0.8, min_z + height * 1.05), 330, height * 0.7),
    ("rim", (0, height * 1.3, min_z + height * 1.25), 480, height * 0.6),
]:
    bpy.ops.object.light_add(type="AREA", location=location)
    light = bpy.context.object
    light.name = f"studio.{name}"
    light.data.energy = energy
    light.data.shape = "DISK"
    light.data.size = size
    light.rotation_euler = (Vector((center_x, center_y, min_z + height * 0.55)) - light.location).to_track_quat("-Z", "Y").to_euler()

bpy.ops.object.camera_add(location=(center_x, center_y - height * 2.65,
                                    min_z + height * 0.52))
camera = bpy.context.object
camera.name = "studio.camera"
camera.data.lens = 68
point_camera(camera, (center_x, center_y, min_z + height * 0.50))
bpy.context.scene.camera = camera

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = 300
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 720
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.render.filepath = str(OUT / "preview-front.png")
scene.render.image_settings.color_mode = "RGBA"
scene.render.fps = 30
scene.render.fps_base = 1.0
scene.view_settings.look = "AgX - Medium High Contrast"

# Four cardinal previews for the visual gate.
for frame, filename in (
    (1, "preview-front.png"),
    (76, "preview-right.png"),
    (151, "preview-rear.png"),
    (226, "preview-left.png"),
):
    scene.frame_set(frame)
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)

# Interactive game asset and editable source.
scene.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "avatar-v4-foundation.blend"))
bpy.ops.export_scene.gltf(
    filepath=str(OUT / "avatar-v4-foundation.glb"),
    export_format="GLB",
    export_animations=True,
    export_frame_range=True,
    export_yup=True,
)
print(f"AVATAR_V4_BUILT {OUT}")
