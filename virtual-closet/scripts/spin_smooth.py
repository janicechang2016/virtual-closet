"""Aligned 360 spin detents: normalize the 8 real frames to the canon front.

$0, fully local (rembg human-seg for figure bboxes). nb2 returns each angle
frame on its own canvas (560x1835, 843x1264, ...) with the figure anywhere
from 974px to 1755px tall - so the visible gray photo-canvas changed shape in
the mirror and the figure jumped in scale at every detent. Fix: frame 0 IS the
untouched canon front render (entering spin changes nothing on the mirror);
frames 1-7 are rescaled so the figure matches the canon's height, feet on the
canon's baseline, centered on the canon's figure axis, on a canvas of the
canon's exact size padded with each frame's own background tone.

RIFE interpolation (rife-ncnn-vulkan in tools/) was piloted and PARKED
2026-07-22: the turn-base quarters run shallow (~20 deg), making the
a045->a090 gap a ~70 deg rotation - optical flow smears the face mid-gap.
The --interp flag keeps that path runnable for future experiments; true
continuous rotation needs video-model segments (tier 3, unpriced).

Run with the liminal venv python (rembg lives there):
  .../liminal-wardrobe/.venv/bin/python scripts/spin_smooth.py 05-hardest-item
  .../liminal-wardrobe/.venv/bin/python scripts/spin_smooth.py --outfit 01-plain-tee 02-jeans
  .../liminal-wardrobe/.venv/bin/python scripts/spin_smooth.py --all   [--force]

Output: renders/spin/<key>/f00.jpg .. f07.jpg (canon-sized; key = garment id,
or the outfit stem for looks). The server probe returns them as "norm" (8) or
"smooth" (64, interp mode); a re-rendered frame makes a sequence stale -
re-run with --force for that key.
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

# interp-mode geometry (parked pilot; detent mode anchors on the canon instead)
CW, CH = 1010, 1836
FH, BASE = 1500, 1690
OW, OH = 632, 1148

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
    """[front, a045..a315] for a garment or an outfit, or None if incomplete.

    The 0-degree frame is the render on the mirror when spin opens. Prefer a
    neutral (non-posed) front; some published looks only have a posed render
    (contrapposto / hand-on-hip / 34turn), so fall back to that - the detent
    alignment still holds the mirror constant, the pose just carries into the
    0-degree detent (flagged; 34turn fronts read as a slight pre-turn)."""
    key = gids[0] if len(gids) == 1 else \
        "outfit_" + "+".join(g.split("-")[0] for g in sorted(gids))
    stem = f"{key}_nb2_v3" if len(gids) == 1 else key
    hidden = hidden_stems()

    def pick(allow_posed):
        hits = [p for p in sorted(RENDERS.glob(f"{stem}_*.png"))
                if not p.stem.endswith("_raw") and p.stem not in hidden
                and not ANGLE_TAG.search(p.name)
                and (allow_posed or not POSE_TAG.search(p.name))]
        return hits[-1] if hits else None

    front = pick(allow_posed=False) or pick(allow_posed=True)
    if not front:
        return key, None
    frames = [front]
    for a in ANGLES:
        hits = [p for p in sorted(RENDERS.glob(f"{stem}_{a}_*.png"))
                if not p.stem.endswith("_raw") and p.stem not in hidden]
        if not hits:
            return key, None
        frames.append(hits[-1])
    return key, frames


def edge_tone(im):
    arr = np.array(im)
    edge = np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]])
    return tuple(int(v) for v in np.median(edge, axis=0))


def normalize(path, geom=None):
    """Scale/place the figure. geom = canon anchor (cw,ch,fh,base,cx); without
    it, the parked interp-mode working canvas is used."""
    im = Image.open(path).convert("RGB")
    top, bot, l, r = seg_bbox(im)
    cw, ch, fh, base, cx = geom if geom else (CW, CH, FH, BASE, CW / 2)
    scale = fh / (bot - top)
    im2 = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGB", (cw, ch), edge_tone(im))
    canvas.paste(im2, (int(cx - (l + r) / 2 * scale), int(base - bot * scale)))
    return canvas


def canon_geom(path):
    im = Image.open(path).convert("RGB")
    top, bot, l, r = seg_bbox(im)
    return (im.width, im.height, bot - top, bot, (l + r) / 2)


def build(gids, force=False, interp=False):
    key, frames = frame_paths(gids)
    out = SPIN_DIR / key
    want = 64 if interp else 8
    if not frames:
        print(f"skip {key}: incomplete frame set")
        return False
    if not force and out.is_dir() and len(list(out.glob("f*.jpg"))) == want:
        print(f"skip {key}: already built")
        return True

    if not interp:
        # detent mode: frame 0 = the untouched canon; 1-7 anchored to its geometry
        geom = canon_geom(frames[0])
        results = [Image.open(frames[0]).convert("RGB")]
        results += [normalize(p, geom) for p in frames[1:]]
        if out.is_dir():
            shutil.rmtree(out)
        out.mkdir(parents=True)
        for i, im in enumerate(results):
            im.save(out / f"f{i:02d}.jpg", quality=92)
        print(f"built {key} (8 aligned detents)")
        return True

    # parked interp mode (RIFE) — kept runnable for future experiments
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
    interp = "--interp" in args
    args = [a for a in args if a not in ("--force", "--interp")]
    if args and args[0] == "--all":
        garments = sorted(p.name for p in (ROOT / "garments").iterdir()
                          if p.is_dir() and p.name[0].isdigit())
        for g in garments:
            build([g], force, interp)
        looks = [l for l in json.loads((ROOT / "looks.json").read_text())
                 if l.get("state") == "published"]
        for l in looks:
            build(l["items"], force, interp)
    elif args and args[0] == "--outfit":
        build(args[1:], force, interp)
    elif args:
        build([args[0]], force, interp)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
