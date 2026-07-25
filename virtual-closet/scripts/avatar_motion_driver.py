"""Build a privacy-safe Kling motion driver from synthetic avatar spin frames.

The procedural mannequin was rejected by Kling's human detector. This variant
uses the eight already-generated, photorealistic synthetic-avatar detents and
RIFE only to create temporal transitions between them. It contains no source
photograph of the owner.

Run with the liminal wardrobe venv:
  .../liminal-wardrobe/.venv/bin/python scripts/avatar_motion_driver.py
"""
from pathlib import Path
import shutil
import subprocess
import tempfile

import cv2


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "renders" / "spin" / "outfit_03+52"
OUTPUT = ROOT / "pilots" / "spin-motion-control" / "avatar-turn-360-h264.mp4"
RIFE = ROOT / "tools" / "rife-ncnn-vulkan" / "rife-ncnn-vulkan"
MODEL = ROOT / "tools" / "rife-ncnn-vulkan" / "rife-v4.6"


def main():
    frames = [SOURCE / f"f{i:02d}.jpg" for i in range(8)]
    missing = [str(p) for p in frames if not p.is_file()]
    if missing:
        raise SystemExit(f"missing source frames: {missing}")

    with tempfile.TemporaryDirectory() as td:
        work = Path(td)
        inputs = work / "in"
        interpolated = work / "out"
        inputs.mkdir()
        interpolated.mkdir()

        # Repeat the front at the end so the generated motion closes its loop.
        for i, source in enumerate(frames + [frames[0]]):
            shutil.copyfile(source, inputs / f"{i:02d}.jpg")

        result = subprocess.run(
            [str(RIFE), "-i", str(inputs), "-o", str(interpolated),
             "-m", str(MODEL), "-n", "301"],
            capture_output=True,
            text=True,
        )
        generated = sorted(interpolated.glob("*.png"))
        if result.returncode != 0 or len(generated) < 300:
            raise SystemExit(
                f"RIFE failed: rc={result.returncode}, frames={len(generated)}\n"
                f"{result.stderr}"
            )

        first = cv2.imread(str(generated[0]))
        height, width = first.shape[:2]
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        writer = cv2.VideoWriter(
            str(OUTPUT), cv2.VideoWriter_fourcc(*"avc1"), 30.0, (width, height)
        )
        if not writer.isOpened():
            raise SystemExit("could not initialize H.264 writer")
        for path in generated[:300]:
            writer.write(cv2.imread(str(path)))
        writer.release()

    print(f"built {OUTPUT} (300 frames, 30 fps, 10 seconds, H.264)")


if __name__ == "__main__":
    main()
