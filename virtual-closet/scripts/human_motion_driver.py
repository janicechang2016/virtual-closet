"""Prepare Janice's private human-motion clip for Kling without exposing her face.

The original is never modified. This pilot-specific trim uses the clean 2–12s
window from IMG_8576.MOV, applies an opaque tracked face oval, downsizes to
720x1280, and writes browser-compatible H.264 at the source frame rate.
"""
from pathlib import Path
import cv2
import numpy as np


SOURCE = Path("/Users/janice.chang/Desktop/IMG_8576.MOV")
OUTPUT = (Path(__file__).resolve().parent.parent / "pilots" /
          "spin-motion-control" / "human-turn-360-private-h264.mp4")
START_FRAME = 50                 # 2.00s at 25 fps
FRAME_COUNT = 250                # exactly 10.00s
SIZE = (720, 1280)

# Hand-checked face centers in source-frame coordinates. Interpolation keeps
# the privacy mask attached through profile/rear phases where a face detector
# intentionally has no frontal face to find.
TRACK = np.array([
    [50, 1030, 786],
    [90, 1030, 736],
    [125, 1030, 760],
    [175, 1030, 760],
    [220, 1030, 800],
    [240, 1030, 836],
    [299, 1030, 842],
], dtype=float)


def center_at(frame_index):
    x = np.interp(frame_index, TRACK[:, 0], TRACK[:, 1])
    y = np.interp(frame_index, TRACK[:, 0], TRACK[:, 2])
    return int(x * SIZE[0] / 2160), int(y * SIZE[1] / 3840)


def main():
    capture = cv2.VideoCapture(str(SOURCE))
    if not capture.isOpened():
        raise SystemExit(f"cannot open {SOURCE}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    capture.set(cv2.CAP_PROP_POS_FRAMES, START_FRAME)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(
        str(OUTPUT), cv2.VideoWriter_fourcc(*"avc1"), fps, SIZE
    )
    if not writer.isOpened():
        raise SystemExit("could not initialize H.264 writer")

    written = 0
    for source_index in range(START_FRAME, START_FRAME + FRAME_COUNT):
        ok, frame = capture.read()
        if not ok:
            break
        frame = cv2.resize(frame, SIZE, interpolation=cv2.INTER_AREA)
        cx, cy = center_at(source_index)
        # Neutral oval replaces the face completely while leaving the real
        # shoulders, limbs, footwork, and head trajectory available to Kling.
        # Cover the full head envelope: a frontal-face-sized oval leaves the
        # nose/cheek exposed when the head turns into profile.
        cv2.ellipse(frame, (cx, cy), (142, 132), 0, 0, 360,
                    (112, 112, 112), thickness=-1, lineType=cv2.LINE_AA)
        writer.write(frame)
        written += 1

    capture.release()
    writer.release()
    if written != FRAME_COUNT:
        raise SystemExit(f"short write: {written}/{FRAME_COUNT} frames")
    print(f"built {OUTPUT} ({written} frames, {fps:g} fps, 10 seconds, H.264)")


if __name__ == "__main__":
    main()
