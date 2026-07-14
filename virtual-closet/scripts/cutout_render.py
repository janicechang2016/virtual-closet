"""Cut the figure out of try-on renders for the carousel (white-floor look).

rembg u2net_human_seg (per liminal-wardrobe-v2 CARD-PIPELINE.md — default u2net
keeps furniture), largest-component cleanup, tight crop. $0, local.

    /Users/janice.chang/liminal-wardrobe/.venv/bin/python scripts/cutout_render.py

Idempotent: skips existing cutouts. Outputs renders/cutouts/<stem>_cut.png.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session, remove

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders" / "cutouts"
MARGIN_X, MARGIN_Y = 0.05, 0.02


def clean(img: Image.Image) -> Image.Image:
    a = np.array(img.getchannel("A"))
    m = (a > 8).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n > 1:
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        a[labels != largest] = 0
        img.putalpha(Image.fromarray(a))
    bbox = img.getbbox()
    if bbox:
        mx, my = int(img.width * MARGIN_X), int(img.height * MARGIN_Y)
        img = img.crop((max(bbox[0] - mx, 0), max(bbox[1] - my, 0),
                        min(bbox[2] + mx, img.width), min(bbox[3] + my, img.height)))
    return img


def hidden_stems():
    try:
        import json
        return set(json.loads((ROOT / "renders" / "hidden.json").read_text()))
    except (OSError, ValueError):
        return set()


def targets():
    hidden = hidden_stems()
    yield ROOT / "avatar" / "avatar-v1" / "front.png"
    for gdir in sorted((ROOT / "garments").glob("*/")):
        finals = [p for p in sorted((ROOT / "renders").glob(f"{gdir.name}_nb2_*.png"))
                  if not p.stem.endswith("_raw") and p.stem not in hidden]
        if finals:
            yield finals[-1]
    for p in sorted((ROOT / "renders").glob("outfit_*.png")):
        if not p.stem.endswith("_raw") and p.stem not in hidden:
            yield p


def main():
    OUT.mkdir(exist_ok=True)
    session = new_session("u2net_human_seg")
    for src in targets():
        dst = OUT / f"{src.stem}_cut.png"
        if dst.exists():
            print("skip", dst.name)
            continue
        img = remove(Image.open(src).convert("RGB"), session=session)
        clean(img).save(dst)
        print("ok  ", dst.name)


if __name__ == "__main__":
    main()
