"""Tier-3 spin video: a seamless slow-rotation loop for a chosen look.

For hero looks only (tier 3 costs real money; most items/looks use the $0 tier-2
aligned detents in the fitting-room scrub). Feeds each adjacent pair of the 8
aligned detent frames (renders/spin/<key>/f00..f07.jpg) to Wan-2.1 FLF2V, which
generates the real rotation motion between them - both endpoints are our own
QA'd frames, so identity/garment can only drift within a 45-deg gap. The 8
segments are stitched (cv2, no ffmpeg) into one loop, dropping each seam's
duplicate frame, at renders/spin_video/<key>/loop.mp4.

Cost: 8 segments x $0.40 (720p) = $3.20 per look, or x $0.20 (480p) = $1.60.
Presence of loop.mp4 is what marks a look as tier-3 (server exposes spin_video;
the carousel auto-plays it slowly on open).

  .../liminal-wardrobe/.venv/bin/python scripts/spin_video.py --outfit 03-patterned-dress 52-camper-flats
  .../liminal-wardrobe/.venv/bin/python scripts/spin_video.py 05-hardest-item [--480p] [--force]
"""
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parent.parent
SPIN = ROOT / "renders" / "spin"
VID = ROOT / "renders" / "spin_video"
sys.path.insert(0, str(ROOT / "scripts"))
from fal_generate import generate_flf2v

PROMPT = ("The woman stands in place and slowly rotates her whole body, a smooth "
          "continuous turntable rotation. Fixed camera, plain light-gray studio "
          "background, full body, photorealistic. She does not walk or step and "
          "does not change pose; only her facing direction rotates smoothly.")


def key_for(gids):
    return gids[0] if len(gids) == 1 else \
        "outfit_" + "+".join(g.split("-")[0] for g in sorted(gids))


def stitch(seg_paths, out):
    """Concatenate segment videos into one loop, dropping each seam's dup frame."""
    writer, size = None, None
    for si, seg in enumerate(seg_paths):
        cap = cv2.VideoCapture(str(seg))
        fps = cap.get(cv2.CAP_PROP_FPS) or 16
        frames = []
        while True:
            ok, fr = cap.read()
            if not ok:
                break
            frames.append(fr)
        cap.release()
        if si > 0:
            frames = frames[1:]          # seam: seg start == prev seg end
        if writer is None:
            size = (frames[0].shape[1], frames[0].shape[0])
            writer = cv2.VideoWriter(str(out), cv2.VideoWriter_fourcc(*"mp4v"),
                                     fps, size)
        for fr in frames:
            if (fr.shape[1], fr.shape[0]) != size:
                fr = cv2.resize(fr, size)
            writer.write(fr)
    if writer:
        writer.release()
    return out


def build(gids, resolution="720p", force=False):
    key = key_for(gids)
    src = SPIN / key
    frames = sorted(src.glob("f*.jpg"))
    if len(frames) != 8:
        sys.exit(f"{key}: need 8 aligned detents first (scripts/spin_smooth.py)")
    out_dir = VID / key
    loop = out_dir / "loop.mp4"
    if loop.is_file() and not force:
        print(f"{key}: loop.mp4 exists (use --force to rebuild)")
        return loop
    seg_dir = out_dir / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    pairs = [(frames[i], frames[(i + 1) % 8]) for i in range(8)]  # closes the loop
    segs = []
    for i, (a, b) in enumerate(pairs):
        seg = seg_dir / f"seg{i}.mp4"
        if seg.is_file() and not force:
            print(f"{key} seg{i}: exists, skip")
        else:
            print(f"{key} seg{i}: {a.name} -> {b.name}")
            generate_flf2v(str(a), str(b), PROMPT, str(seg), resolution=resolution)
        segs.append(seg)
    stitch(segs, loop)
    print(f"built {loop} ({loop.stat().st_size // 1024} KB)")
    return loop


def main():
    args = sys.argv[1:]
    force = "--force" in args
    res = "480p" if "--480p" in args else "720p"
    args = [a for a in args if a not in ("--force", "--480p")]
    if args and args[0] == "--outfit":
        build(args[1:], res, force)
    elif args:
        build([args[0]], res, force)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
