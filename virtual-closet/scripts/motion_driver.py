"""Render a privacy-safe 360-degree mannequin motion-control driver.

This is deliberately an appearance-free procedural mannequin. It supplies only
the motion, timing, framing, and facing direction for a character-animation
model; the avatar/look reference supplies the visible person and clothing.

Run with the project's image-processing environment:

  /Users/janice.chang/liminal-wardrobe/.venv/bin/python \
      scripts/motion_driver.py [--seconds 10] [--fps 30]

Output: pilots/spin-motion-control/mannequin-turn-360.mp4
"""
import argparse
import math
from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "pilots" / "spin-motion-control" / "mannequin-turn-360.mp4"
W, H = 720, 960
CX, GROUND = W // 2, 865
SCALE = 410.0


def rotate(point, angle):
    """Rotate an (x, y, z) point around the mannequin's vertical axis."""
    x, y, z = point
    c, s = math.cos(angle), math.sin(angle)
    return np.array((x * c + z * s, y, -x * s + z * c), dtype=float)


def project(point):
    """Mild perspective keeps the volume readable without camera movement."""
    x, y, z = point
    perspective = 1.0 / (1.0 + 0.10 * z)
    return np.array((CX + x * SCALE * perspective,
                     GROUND - y * SCALE * perspective))


def capsule(frame, a, b, radius, color):
    pa, pb = project(a), project(b)
    depth_scale = 1.0 / (1.0 + 0.10 * ((a[2] + b[2]) / 2))
    thickness = max(2, int(2 * radius * SCALE * depth_scale))
    aa, bb = tuple(np.rint(pa).astype(int)), tuple(np.rint(pb).astype(int))
    cv2.line(frame, aa, bb, color, thickness, cv2.LINE_AA)
    cv2.circle(frame, aa, thickness // 2, color, -1, cv2.LINE_AA)
    cv2.circle(frame, bb, thickness // 2, color, -1, cv2.LINE_AA)


def ellipse(frame, center, axes, color, angle=0):
    p = tuple(np.rint(project(center)).astype(int))
    zscale = 1.0 / (1.0 + 0.10 * center[2])
    ax = (max(2, int(axes[0] * SCALE * zscale)),
          max(2, int(axes[1] * SCALE * zscale)))
    cv2.ellipse(frame, p, ax, angle, 0, 360, color, -1, cv2.LINE_AA)


def frame_at(angle):
    frame = np.full((H, W, 3), (232, 230, 226), dtype=np.uint8)

    # Fixed studio cues make unintended camera movement obvious in the output.
    cv2.line(frame, (70, GROUND + 8), (W - 70, GROUND + 8),
             (202, 199, 194), 2, cv2.LINE_AA)
    cv2.ellipse(frame, (CX, GROUND + 10), (142, 24), 0, 0, 360,
                (211, 208, 203), -1, cv2.LINE_AA)
    cv2.ellipse(frame, (CX, GROUND + 8), (132, 18), 0, 0, 360,
                (221, 219, 215), -1, cv2.LINE_AA)

    # Petite neutral figure, with arms separated so pose extraction sees limbs.
    pts = {
        "head": (0.0, 1.76, 0.0), "neck": (0.0, 1.57, 0.0),
        "chest": (0.0, 1.34, 0.0), "pelvis": (0.0, 1.02, 0.0),
        "ls": (-0.25, 1.50, 0.0), "rs": (0.25, 1.50, 0.0),
        "le": (-0.31, 1.24, 0.015), "re": (0.31, 1.24, 0.015),
        "lw": (-0.30, 0.96, 0.03), "rw": (0.30, 0.96, 0.03),
        "lh": (-0.14, 1.01, 0.0), "rh": (0.14, 1.01, 0.0),
        "lk": (-0.13, 0.55, 0.018), "rk": (0.13, 0.55, -0.018),
        "la": (-0.13, 0.10, 0.02), "ra": (0.13, 0.10, -0.02),
        "lt": (-0.13, 0.04, -0.12), "rt": (0.13, 0.04, -0.12),
        "nose": (0.0, 1.77, -0.13),
    }
    p = {k: rotate(v, angle) for k, v in pts.items()}
    skin = (177, 174, 169)
    suit = (112, 116, 119)
    joint = (129, 132, 134)

    parts = []
    for a, b, r, color in [
        ("ls", "le", .060, suit), ("le", "lw", .052, suit),
        ("rs", "re", .060, suit), ("re", "rw", .052, suit),
        ("lh", "lk", .082, suit), ("lk", "la", .065, suit),
        ("rh", "rk", .082, suit), ("rk", "ra", .065, suit),
        ("la", "lt", .070, suit), ("ra", "rt", .070, suit),
    ]:
        parts.append(((p[a][2] + p[b][2]) / 2,
                      lambda f, a=a, b=b, r=r, c=color: capsule(f, p[a], p[b], r, c)))

    # Torso/pelvis volumes and head are also depth-sorted with the limbs.
    parts.extend([
        (p["pelvis"][2], lambda f: ellipse(f, p["pelvis"], (.20, .20), suit)),
        (p["chest"][2], lambda f: ellipse(f, p["chest"], (.255, .30), suit)),
        (p["neck"][2], lambda f: capsule(f, p["neck"] + (0, -.05, 0), p["neck"], .065, skin)),
        (p["head"][2], lambda f: ellipse(f, p["head"], (.135, .175), skin)),
    ])
    for _, draw in sorted(parts, key=lambda item: item[0], reverse=True):
        draw(frame)

    # Direction marker: a subtle nose and chest stripe distinguish front/back.
    capsule(frame, p["head"], p["nose"], .022, (150, 147, 142))
    chest_front = rotate((0.0, 1.34, -0.105), angle)
    chest_low = rotate((0.0, 1.17, -0.105), angle)
    if chest_front[2] < 0.08:
        capsule(frame, chest_front, chest_low, .012, (75, 79, 82))

    cv2.putText(frame, "MOTION REFERENCE ONLY", (24, 42),
                cv2.FONT_HERSHEY_SIMPLEX, .62, (120, 117, 113), 1, cv2.LINE_AA)
    return frame


def render(out, seconds, fps):
    out.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"),
                             fps, (W, H))
    if not writer.isOpened():
        raise RuntimeError("Could not create MP4 writer")
    count = int(seconds * fps)
    for i in range(count):
        # Do not duplicate the first frame; playback wraps 359.x degrees to zero.
        writer.write(frame_at(2 * math.pi * i / count))
    writer.release()
    print(f"wrote {out} ({count} frames, {fps} fps, {seconds:.1f}s)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--seconds", type=float, default=10.0)
    ap.add_argument("--fps", type=int, default=30)
    args = ap.parse_args()
    render(args.out, args.seconds, args.fps)


if __name__ == "__main__":
    main()
