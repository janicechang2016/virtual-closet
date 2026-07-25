"""Restore the review previews from the immutable approved v4 checkpoint."""
from pathlib import Path
import bpy


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "avatar" / "avatar-v4"
scene = bpy.context.scene
scene.render.resolution_x = 720
scene.render.resolution_y = 960
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"

for frame, filename in (
    (1, "preview-front.png"),
    (76, "preview-right.png"),
    (151, "preview-rear.png"),
    (226, "preview-left.png"),
):
    scene.frame_set(frame)
    scene.render.filepath = str(OUT / filename)
    bpy.ops.render.render(write_still=True)
