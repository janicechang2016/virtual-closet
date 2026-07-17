"""Transparent drag-ghost cutouts for the fitting room's drag-to-dress card.

Writes clean/<id>_dragcut.png (RGBA, cropped, ≤512px) for every garment — the
silhouette the drag card flies as (Interactive-Styling-Canvas look). Writes ONLY
*_dragcut.png: never *_onwhite/*_extracted, so try-on inputs are untouched
(garment_asset ignores dragcuts; the server excludes them from photos[]).

Model per item: clothing → u2net_cloth_seg (region by category, as
extract_garment.py); shoes → general u2net (cloth-seg has no shoe class).
Weak/empty cloth-seg masks fall back to the general model; still-weak items are
skipped (the drag card falls back to its framed form).

    /Users/janice.chang/liminal-wardrobe/.venv/bin/python scripts/dragcut.py [id ...]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from rembg import new_session

ROOT = Path(__file__).resolve().parents[1]
GARMENTS = ROOT / "garments"
RAW_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

CLOTH_REGIONS = ["upper", "lower", "full"]
CATEGORY_TO_REGION = {"top": "upper", "outerwear": "upper", "layer": "upper",
                      "bottom": "lower", "dress": "full"}
MARGIN = 12
MAX_SIDE = 512
MIN_COVERAGE = 0.02   # of the full image; below this the mask is junk


def clean_mask(mask: Image.Image) -> Image.Image:
    m = (np.array(mask) > 128).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n > 1:
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        m = (labels == largest).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel)
    m = cv2.medianBlur((m * 255).astype(np.uint8), 9)
    return Image.fromarray(m)


def coverage(mask: Image.Image) -> float:
    a = np.array(mask)
    return float((a > 128).mean())


def source_image(folder: Path, meta: dict) -> Path | None:
    """Cleanest available product view: generative extraction > primary raw."""
    extracted = sorted((folder / "clean").glob("*_extracted.png"))
    if extracted:
        return extracted[0]
    raws = sorted(p for p in (folder / "raw").glob("*") if p.suffix.lower() in RAW_EXTS)
    return raws[0] if raws else None


def cut(folder: Path, cloth, general) -> str:
    meta = json.loads((folder / "meta.json").read_text())
    src = source_image(folder, meta)
    if not src:
        return f"skip  {folder.name}: no source image"
    img = Image.open(src).convert("RGB")

    mask, how = None, ""
    # Routing (learned from the first batch): on-model photos need cloth-seg to
    # separate garment from person — and must NEVER fall back to the general
    # model (it keeps the whole figure: a person-shaped drag ghost). Product
    # shots (ghost/flat/hanger/extracted) need plain background removal — the
    # general model — since cloth-seg rags or truncates them.
    on_model = (meta.get("source_photo_type") == "on-model"
                and src.parent.name == "raw" and meta.get("category") != "shoes")
    if on_model:
        region = CATEGORY_TO_REGION.get(meta.get("category", ""), "full")
        m = cloth.predict(img)[CLOTH_REGIONS.index(region)].resize(img.size)
        m = clean_mask(m)
        if coverage(m) >= MIN_COVERAGE:
            mask, how = m, f"cloth-seg/{region}"
    else:
        m = general.predict(img)[0].resize(img.size)
        m = clean_mask(m)
        if coverage(m) >= MIN_COVERAGE:
            mask, how = m, "general"
    if mask is None:
        return f"FAIL  {folder.name}: no usable mask (framed-card fallback)"

    cutout = img.convert("RGBA")
    cutout.putalpha(mask)
    bbox = mask.getbbox()
    bbox = (max(bbox[0] - MARGIN, 0), max(bbox[1] - MARGIN, 0),
            min(bbox[2] + MARGIN, img.width), min(bbox[3] + MARGIN, img.height))
    cutout = cutout.crop(bbox)
    cutout.thumbnail((MAX_SIDE, MAX_SIDE))

    clean_dir = folder / "clean"
    clean_dir.mkdir(exist_ok=True)
    out = clean_dir / f"{meta['id']}_dragcut.png"
    cutout.save(out)
    return f"ok    {folder.name}: {how} {cutout.size[0]}x{cutout.size[1]} from {src.name}"


def main() -> int:
    wanted = set(sys.argv[1:])
    folders = sorted(f for f in GARMENTS.iterdir()
                     if f.is_dir() and (f / "meta.json").exists()
                     and (not wanted or f.name in wanted))
    if not folders:
        print("nothing to do")
        return 1
    print("loading models (first run may download)...")
    cloth = new_session("u2net_cloth_seg")
    general = new_session("u2net")
    fails = 0
    for f in folders:
        line = cut(f, cloth, general)
        fails += line.startswith("FAIL")
        print(line, flush=True)
    print(f"done: {len(folders) - fails} cutouts, {fails} framed-card fallbacks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
