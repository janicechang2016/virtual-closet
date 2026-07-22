"""Smooth 360 spins: normalize the 8 real frames, interpolate to 64 with RIFE.

$0, fully local (rembg human-seg for figure bboxes + rife-ncnn-vulkan v4.6 on
the GPU). Why normalization matters: nb2 returns each frame on its own canvas
(560x1835, 843x1264, ...) with the figure at wildly different scales (974px to
1755px tall on the same garment) - interpolating those directly produces ghost
dissolves, and the visible gray photo-canvas changes shape in the mirror. Every
frame is rescaled so the figure is one height on one baseline, centered on one
canvas padded with that frame's own background tone; RIFE then reads the 45-deg
gaps as genuine rotation.

Run with the liminal venv python (rembg lives there):
  .../liminal-wardrobe/.venv/bin/python scripts/spin_smooth.py 05-hardest-item
  .../liminal-wardrobe/.venv/bin/python scripts/spin_smooth.py --outfit 01-plain-tee 02-jeans
  .../liminal-wardrobe/.venv/bin/python scripts/spin_smooth.py --all   [--force]

Output: renders/spin/<key>/f00.jpg .. f63.jpg (632x1148, ~40KB each; key =
garment id, or the outfit stem for looks). The server's /api/spin probe
returns the sequence as "smooth" when all 64 frames exist; a re-rendered
angle frame makes the sequence stale - re-run with --force for that key.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RENDERS = ROOT / "renders"
SPIN_DIR = RENDERS / "spin"
RIFE = ROOT / "tools" / "rife-ncnn-vulkan" / "rife-ncnn-vulkan"
RIFE_MODEL = ROOT / "tools" / "rife-ncnn-vulkan" / "rife-v4.6"

ANGLES = ("a045", "a090", "a135", "a180", "a225", "a270", "a315")
POSE_TAG = re.compile(r"_(contrapposto|hand-on-hip|34turn)_")
ANGLE_TAG = re.compile(r"_a\d{3}_")

# normalization geometry (matches the piloted values)
CW, CH = 1010, 1836          # working canvas
FH, BASE = 1500, 1690        # figure height / feet baseline on that canvas
OW, OH = 632, 1148           # stored frame size (mirror is ~570px tall, x2 retina)

_session = None
def seg_bbox(im):
    global _session
    from rembg import remove, new_session
    if _session is None:
        _session = new_session("u2net_human_seg")
    mask = np.array(remove(im, session=_session, only_mask=True))
    ys, xs = np.where(mask > 128)
    if not len(ys):
        raise RuntimeError("human-seg found no figure")
    return ys.min(), ys.max(), xs.min(), xs.max()


def hidden_stems():
    p = RENDERS / "hidden.json"
    return set(json.loads(p.read_text())) if p.is_file() else set()


def newest(stem_glob):
    hidden = hidden_stems()
    hits = [p for p in sorted(RENDERS.glob(stem_glob))
            if not p.stem.endswith("_raw") and p.stem not in hidden
            and not POSE_TAG.search(p.name)]
    return hits[-1] if hits else None


def frame_paths(gids):
    """[front, a045..a315] for a garment or an outfit, or None if incomplete."""
    if len(gids) == 1:
        key = gids[0]
        front = newest(f"{key}_nb2_v3_*.png")
        # the glob above also catches angle frames - the front is the newest non-angle
        hidden = hidden_stems()
        fronts = [p for p in sorted(RENDERS.glob(f"{key}_nb2_v3_*.png"))
                  if not p.stem.endswith("_raw") and p.stem not in hidden
                  and not POSE_TAG.search(p.name) and not ANGLE_TAG.search(p.name)]
        front = fronts[-1] if fronts else None
        stem = f"{key}_nb2_v3"
    else:
        key = "outfit_" + "+".join(g.split("-")[0] for g in sorted(gids))
        hidden = hidden_stems()
        fronts = [p for p in sorted(RENDERS.glob(f"{key}_*.png"))
                  if not p.stem.endswith("_raw") and p.stem not in hidden
                  and not POSE_TAG.search(p.name) and not ANGLE_TAG.search(p.name)]
        front = fronts[-1] if fronts else None
        stem = key
    if not front:
        return key, None
    frames = [front]
    hidden = hidden_stems()
    for a in ANGLES:
        hits = [p for p in sorted(RENDERS.glob(f"{stem}_{a}_*.png"))
                if not p.stem.endswith("_raw") and p.stem not in hidden]
        if not hits:
            return key, None
        frames.append(hits[-1])
    return key, frames


def normalize(path):
    im = Image.open(path).convert("RGB")
    top, bot, l, r = seg_bbox(im)
    scale = FH / (bot - top)
    im2 = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    arr = np.array(im)
    edge = np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]])
    bg = tuple(int(v) for v in np.median(edge, axis=0))
    canvas = Image.new("RGB", (CW, CH), bg)
    canvas.paste(im2, (int(CW / 2 - (l + r) / 2 * scale), int(BASE - bot * scale)))
    return canvas


def build(gids, force=False):
    key, frames = frame_paths(gids)
    out = SPIN_DIR / key
    if not frames:
        print(f"skip {key}: incomplete frame set")
        return False
    if not force and out.is_dir() and len(list(out.glob("f*.jpg"))) == 64:
        print(f"skip {key}: already built")
        return True
    with tempfile.TemporaryDirectory() as td:
        tin, tout = Path(td) / "in", Path(td) / "out"
        tin.mkdir(); tout.mkdir()
        for i, p in enumerate(frames + [frames[0]]):     # wrap the loop closed
            normalize(p).save(tin / f"{i:02d}.png")
        r = subprocess.run([str(RIFE), "-i", str(tin), "-o", str(tout),
                            "-m", str(RIFE_MODEL), "-n", "65"],
                           capture_output=True, text=True)
        results = sorted(tout.glob("*.png"))[:-1]        # drop the wrap duplicate
        if r.returncode != 0 or len(results) != 64:
            print(f"FAIL {key}: rife rc={r.returncode} frames={len(results)}")
            return False
        if out.is_dir():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        for i, p in enumerate(results):
            im = Image.open(p); im.thumbnail((OW, OH))
            im.save(out / f"f{i:02d}.jpg", quality=88)
    print(f"built {key} (64 frames)")
    return True


def main():
    args = sys.argv[1:]
    force = "--force" in args
    args = [a for a in args if a != "--force"]
    if args and args[0] == "--all":
        garments = sorted(p.name for p in (ROOT / "garments").iterdir()
                          if p.is_dir() and p.name[0].isdigit())
        for g in garments:
            build([g], force)
        looks = [l for l in json.loads((ROOT / "looks.json").read_text())
                 if l.get("state") == "published"]
        for l in looks:
            build(l["items"], force)
    elif args and args[0] == "--outfit":
        build(args[1:], force)
    elif args:
        build([args[0]], force)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
