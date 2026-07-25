"""Render front and side diagnostics from the exported runtime GLB."""
from pathlib import Path
import math
import sys

import bpy
from mathutils import Vector


ROOT = Path(__file__).resolve().parent.parent
runtime_name = sys.argv[-1] if sys.argv[-1].endswith(".glb") else "avatar-v4-runtime.glb"
GLB = ROOT / "avatar" / "avatar-v4" / runtime_name
OUT = ROOT / "avatar" / "avatar-v4"
label = Path(runtime_name).stem

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(GLB))

scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 640
scene.render.resolution_y = 800
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.world = bpy.data.worlds.new("Diagnostic world")
scene.world.color = (0.7, 0.7, 0.7)

meshes = [obj for obj in scene.objects if obj.type == "MESH" and obj.name != "Plane"]
corners = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
lo = Vector((min(v.x for v in corners), min(v.y for v in corners), min(v.z for v in corners)))
hi = Vector((max(v.x for v in corners), max(v.y for v in corners), max(v.z for v in corners)))
center = (lo + hi) / 2
height = hi.z - lo.z

camera_data = bpy.data.cameras.new("Diagnostic camera")
camera = bpy.data.objects.new("Diagnostic camera", camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera.data.type = "ORTHO"
camera.data.ortho_scale = height * 1.15

def point_camera(position):
    camera.location = position
    camera.rotation_euler = (center - camera.location).to_track_quat("-Z", "Y").to_euler()

for name, position in (
    (f"{label}-diagnostic-front.png", center + Vector((0, -height * 2, 0))),
    (f"{label}-diagnostic-side.png", center + Vector((height * 2, 0, 0))),
):
    point_camera(position)
    scene.render.filepath = str(OUT / name)
    bpy.ops.render.render(write_still=True)

print("BOUNDS", tuple(round(x, 4) for x in lo), tuple(round(x, 4) for x in hi))
