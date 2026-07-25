"""Build and render an original, license-clean hair-card candidate on approved v4."""
from pathlib import Path
import math

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "avatar" / "avatar-v4"

scene = bpy.context.scene
root = bpy.data.objects["avatar-v4.turntable-root"]
body = bpy.data.objects["avatar-v4.body"]

for name in ("avatar-v4.elvs_lady_hippy_hair", "avatar-v4.fitted-wispy-fringe"):
    obj = bpy.data.objects.get(name)
    if obj:
        obj.hide_render = True

hair_material = bpy.data.materials.new("avatar-v4.original-hair")
hair_material.use_nodes = True
bsdf = hair_material.node_tree.nodes.get("Principled BSDF")
bsdf.inputs["Base Color"].default_value = (0.003, 0.002, 0.004, 1)
bsdf.inputs["Roughness"].default_value = 0.72
if "Specular IOR Level" in bsdf.inputs:
    bsdf.inputs["Specular IOR Level"].default_value = 0.14

world_points = [body.matrix_world @ vertex.co for vertex in body.data.vertices]
min_z = min(point.z for point in world_points)
max_z = max(point.z for point in world_points)
height = max_z - min_z
head_points = [point for point in world_points if point.z > min_z + height * 0.82]
center_x = sum(point.x for point in head_points) / len(head_points)
center_y = sum(point.y for point in head_points) / len(head_points)

head_center = Vector((center_x, center_y + height * 0.005, min_z + height * 0.925))
radius_x = height * 0.063
radius_y = height * 0.069
radius_z = height * 0.087


def mesh_object(name, vertices, faces):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(hair_material)
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = root
    return obj


# Fitted scalp hemisphere. The front-center hairline is raised slightly so the
# cap frames the forehead rather than covering it.
segments = 48
rings = 10
vertices = []
for ring in range(rings + 1):
    phi = (ring / rings) * math.radians(78)
    for segment in range(segments):
        theta = (segment / segments) * math.tau
        front = max(0.0, -math.sin(theta))
        z = head_center.z + radius_z * math.cos(phi) + front * height * 0.008
        vertices.append((
            head_center.x + radius_x * math.sin(phi) * math.cos(theta),
            head_center.y + radius_y * math.sin(phi) * math.sin(theta),
            z,
        ))
faces = []
for ring in range(rings):
    for segment in range(segments):
        nxt = (segment + 1) % segments
        a = ring * segments + segment
        b = ring * segments + nxt
        c = (ring + 1) * segments + nxt
        d = (ring + 1) * segments + segment
        faces.append((a, b, c, d))
mesh_object("avatar-v4.original-hair-cap", vertices, faces)


def ribbon(name, points, widths, axis):
    verts = []
    for point, width in zip(points, widths):
        offset = axis * width
        verts.extend((tuple(point - offset), tuple(point + offset)))
    quads = []
    for index in range(len(points) - 1):
        a = index * 2
        quads.append((a, a + 1, a + 3, a + 2))
    return mesh_object(name, verts, quads)


# Grouped cross-card clumps flow from the scalp to the requested upper-bust line.
end_z = min_z + height * 0.70
for index in range(42):
    theta = math.radians(20 + index * (320 / 41))
    root_point = Vector((
        head_center.x + radius_x * 0.92 * math.cos(theta),
        head_center.y + radius_y * 0.92 * math.sin(theta),
        head_center.z + radius_z * 0.18,
    ))
    side = 1 if root_point.x >= center_x else -1
    backness = max(0.0, math.sin(theta))
    tip_x = root_point.x + side * height * (0.018 + 0.012 * math.sin(index * 1.7))
    tip_y = head_center.y + height * (0.025 + backness * 0.035)
    tip_z = end_z + height * (0.006 * math.sin(index * 2.3))
    points = (
        root_point,
        Vector((root_point.x + side * height * 0.008, root_point.y, min_z + height * 0.86)),
        Vector((tip_x, (root_point.y + tip_y) * 0.5, min_z + height * 0.78)),
        Vector((tip_x, tip_y, tip_z)),
    )
    base_width = height * (0.0055 + 0.0015 * (0.5 + 0.5 * math.sin(index)))
    widths = (base_width * 0.55, base_width, base_width * 0.9, base_width * 0.28)
    ribbon(f"avatar-v4.hair-clump-front.{index:02d}", points, widths, Vector((1, 0, 0)))
    ribbon(f"avatar-v4.hair-clump-side.{index:02d}", points, widths, Vector((0, 1, 0)))


# Straight overall bang line, built from irregular grouped cards rather than
# evenly spaced strand tubes.
bang_count = 17
front_y = head_center.y - radius_y * 1.02
for index in range(bang_count):
    fraction = -1 + (2 * index / (bang_count - 1))
    x = center_x + fraction * radius_x * 0.82
    length = height * (0.052 + 0.004 * math.sin(index * 1.9))
    points = (
        Vector((x, front_y + height * 0.005, min_z + height * 0.946)),
        Vector((x + height * 0.002 * math.sin(index), front_y, min_z + height * 0.915)),
        Vector((x + height * 0.0025 * math.sin(index * 1.4), front_y, min_z + height * 0.946 - length)),
    )
    width = height * (0.0032 + 0.001 * (index % 3))
    ribbon(
        f"avatar-v4.bang-card.{index:02d}",
        points,
        (width * 0.75, width, width * 0.18),
        Vector((1, 0, 0)),
    )

scene.render.resolution_x = 720
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
for frame, filename in (
    (1, "hair-candidate-front.png"),
    (76, "hair-candidate-right.png"),
    (151, "hair-candidate-rear.png"),
    (226, "hair-candidate-left.png"),
):
    scene.frame_set(frame)
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)

bpy.ops.wm.save_as_mainfile(filepath=str(OUT / "avatar-v4-original-hair-candidate.blend"))
print("AVATAR_V4_ORIGINAL_HAIR_CANDIDATE", OUT)
