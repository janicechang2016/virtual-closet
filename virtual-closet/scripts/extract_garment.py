"""Strip on-model garment photos down to just the garment.

Uses rembg's u2net_cloth_seg model (local, $0) to segment clothing regions
from a worn photo, picks the region matching the garment's meta.json category,
and writes two assets into the garment's clean/ folder:

    <id>_cutout.png   transparent-background cutout, cropped to the garment
    <id>_onwhite.png  same cutout composited on white (try-on friendly)

Runs on the liminal-wardrobe venv, which already has rembg+onnxruntime:

    /Users/janice.chang/liminal-wardrobe/.venv/bin/python scripts/extract_garment.py [id ...]

With no args, processes every garments/*/ that has a raw/ photo. Re-running
overwrites clean/ outputs (cheap, deterministic).

Known limits (segmentation, not generation):
  - other garments of the SAME region are kept too (e.g. a tee under an open
    blazer is also "upper body") — flagged per item below
  - occluded parts (behind arms/hair) stay missing; no hallucinated fill
For a generative ghost-mannequin extraction, use the fal route instead
(costs credits; needs an approved batch).
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

# u2net_cloth_seg predicts masks in this order:
CLOTH_REGIONS = ["upper", "lower", "full"]
CATEGORY_TO_REGION = {
    "top": "upper",
    "outerwear": "upper",
    "layer": "upper",
    "bottom": "lower",
    "dress": "full",
}
MARGIN = 24  # px kept around the garment bbox


def clean_mask(mask: Image.Image) -> Image.Image:
    """Keep the largest connected region, close pinholes, smooth the edge."""
    m = (np.array(mask) > 128).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    if n > 1:
        largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
        m = (labels == largest).astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, kernel)
    m = cv2.medianBlur((m * 255).astype(np.uint8), 9)
    return Image.fromarray(m)


def extract(folder: Path, session) -> str:
    meta = json.loads((folder / "meta.json").read_text())
    raws = sorted(p for p in (folder / "raw").glob("*") if p.suffix.lower() in RAW_EXTS)
    if not raws:
        return f"skip  {folder.name}: no raw photo"
    region = CATEGORY_TO_REGION.get(meta.get("category", ""), "full")

    img = Image.open(raws[0]).convert("RGB")
    masks = session.predict(img)  # [upper, lower, full] PIL L masks
    mask = clean_mask(masks[CLOTH_REGIONS.index(region)].resize(img.size))

    cutout = img.convert("RGBA")
    cutout.putalpha(mask)
    bbox = mask.getbbox()
    if bbox is None:
        return f"FAIL  {folder.name}: {region} mask is empty"
    bbox = (
        max(bbox[0] - MARGIN, 0),
        max(bbox[1] - MARGIN, 0),
        min(bbox[2] + MARGIN, img.width),
        min(bbox[3] + MARGIN, img.height),
    )
    cutout = cutout.crop(bbox)

    clean = folder / "clean"
    clean.mkdir(exist_ok=True)
    cutout.save(clean / f"{meta['id']}_cutout.png")
    onwhite = Image.new("RGB", cutout.size, (255, 255, 255))
    onwhite.paste(cutout, mask=cutout.getchannel("A"))
    onwhite.save(clean / f"{meta['id']}_onwhite.png")

    cov = sum(1 for px in mask.crop(bbox).getdata() if px > 128) / (cutout.width * cutout.height)
    return f"ok    {folder.name}: region={region} bbox={cutout.size} coverage={cov:.0%}"


def main() -> int:
    wanted = set(sys.argv[1:])
    folders = sorted(
        f for f in GARMENTS.iterdir()
        if f.is_dir() and (f / "meta.json").exists() and (not wanted or f.name in wanted)
    )
    if not folders:
        print("nothing to do")
        return 1
    print("loading u2net_cloth_seg (first run downloads ~176MB)...")
    session = new_session("u2net_cloth_seg")
    for f in folders:
        print(extract(f, session))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
