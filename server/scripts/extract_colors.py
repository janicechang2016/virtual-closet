#!/usr/bin/env python
"""Phase 1 — programmatic colour extraction. $0, fully local, no API calls.

Emits colors.json: {garment_id: {"colors": [{lab, rgb, name, coverage}], ...meta}}
consumed by backfill_garments.py.

Run with the liminal venv (rembg/cv2/PIL/numpy):
    /Users/janice.chang/liminal-wardrobe/.venv/bin/python scripts/extract_colors.py

Pixel source, in priority order — first hit wins:
  1. clean/*_extracted.png   cloth-seg, garment only — cleanest signal
  2. clean/*_dragcut.png     transparent silhouette
  3. raw/<primary>           rembg applied on the fly (7 garments have no cutout)

White balance runs BEFORE quantisation (per the foundation plan). The illuminant is
estimated from the *raw* photo, not the cutout: cutouts have had their background
removed, and the background is exactly where the neutral reference lives. Gains are
clamped so an editorial shot on a dark ground can't blow the correction up.
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
CLOSET = os.path.normpath(os.path.join(HERE, "..", "..", "virtual-closet"))
GARMENTS = os.path.join(CLOSET, "garments")
OUT = os.path.join(HERE, "colors.json")

MAX_SAMPLES = 20000      # plenty for a stable palette; keeps this fast
N_CLUSTERS = 6           # quantise to 6, then prune
MIN_COVERAGE = 0.06      # drop clusters under 6% of garment pixels
MERGE_DE = 8.0           # merge clusters closer than this in ΔE76
ALPHA_MIN = 200          # opaque-enough to count
WB_CLAMP = (0.85, 1.18)  # per-channel gain limits
MIN_MASK_COVERAGE = 0.02  # of the frame; below this the mask is junk (matches dragcut.py)

# u2net_cloth_seg predicts [upper, lower, full], per extract_garment.py.
CLOTH_REGIONS = ["upper", "lower", "full"]
CATEGORY_TO_REGION = {"top": "upper", "outerwear": "upper", "layer": "upper",
                      "bottom": "lower", "dress": "full"}
# Vertical slice of the `full` mask's bbox to keep, as (start, end) fractions of its
# height. Only used by the fallback path below; deliberately conservative — the point
# is to exclude the neighbouring garment, not to trace the hem exactly.
BAND_BY_CATEGORY = {"top": (0.0, 0.42), "outerwear": (0.0, 0.55), "bottom": (0.48, 1.0)}

# Extra-view suffixes: the primary raw view is the one without any of these.
EXTRA_SUFFIXES = ("_back", "_side", "_alt", "_detail", "_model", "_onwhite")

# Named-colour anchors (sRGB). Deliberately weighted to what's actually in this
# closet: lots of black/cream/red, plus the usual neutrals.
NAMED = [
    # Neutral anchors are calibrated to how garments actually photograph, not to
    # ideal swatches: a real black top measures L*~15-22, never L*~7. Anchoring
    # black at pure #121214 sent every black item in the closet to "charcoal".
    ("black", (44, 43, 45)), ("charcoal", (76, 76, 80)), ("grey", (128, 128, 130)),
    ("light grey", (190, 190, 192)), ("white", (248, 248, 246)),
    ("off-white", (238, 236, 230)), ("cream", (240, 232, 214)),
    ("greige", (176, 168, 156)), ("oatmeal", (208, 196, 178)),
    ("pale blue", (200, 214, 226)),
    ("ivory", (250, 244, 227)), ("beige", (214, 196, 168)), ("tan", (186, 154, 116)),
    ("brown", (110, 78, 56)), ("chocolate", (68, 46, 34)), ("camel", (176, 138, 92)),
    ("navy", (28, 40, 72)), ("blue", (52, 88, 160)), ("light blue", (150, 184, 214)),
    ("teal", (40, 110, 110)), ("green", (66, 108, 70)), ("olive", (104, 104, 62)),
    ("sage", (156, 168, 142)), ("red", (168, 38, 42)), ("scarlet", (198, 46, 40)),
    ("burgundy", (98, 30, 44)), ("oxblood", (82, 28, 32)), ("pink", (222, 152, 168)),
    ("blush", (236, 202, 198)), ("rose", (200, 110, 122)), ("purple", (104, 64, 132)),
    ("violet", (138, 110, 190)), ("lavender", (196, 182, 220)), ("yellow", (226, 200, 92)),
    ("butter", (240, 226, 168)), ("gold", (188, 154, 74)), ("orange", (208, 118, 56)),
    ("rust", (156, 84, 50)), ("silver", (198, 200, 204)),
]


def srgb_to_lab(rgb):
    """sRGB (0-255, float array [...,3]) -> CIE LAB, D65. Exact, no colour lib."""
    rgb = np.asarray(rgb, dtype=np.float64) / 255.0
    m = rgb > 0.04045
    lin = np.where(m, ((rgb + 0.055) / 1.055) ** 2.4, rgb / 12.92)
    mat = np.array([[0.4124564, 0.3575761, 0.1804375],
                    [0.2126729, 0.7151522, 0.0721750],
                    [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ mat.T
    white = np.array([0.95047, 1.00000, 1.08883])
    xyz = xyz / white
    eps, kappa = 216.0 / 24389.0, 24389.0 / 27.0
    f = np.where(xyz > eps, np.cbrt(xyz), (kappa * xyz + 16.0) / 116.0)
    L = 116.0 * f[..., 1] - 16.0
    a = 500.0 * (f[..., 0] - f[..., 1])
    b = 200.0 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], axis=-1)


def name_for(lab):
    anchors = srgb_to_lab(np.array([c for _, c in NAMED], dtype=np.float64))
    d = np.sqrt(((anchors - np.asarray(lab)) ** 2).sum(axis=1))
    return NAMED[int(np.argmin(d))][0]


def primary_raw(gid):
    raw_dir = os.path.join(GARMENTS, gid, "raw")
    if not os.path.isdir(raw_dir):
        return None
    files = sorted(f for f in os.listdir(raw_dir) if not f.startswith("."))
    if not files:
        return None
    primary = [f for f in files
               if not any(s in os.path.splitext(f)[0].lower() for s in EXTRA_SUFFIXES)]
    return os.path.join(raw_dir, (primary or files)[0])


def wb_gains(raw_path):
    """White-patch illuminant estimate from the raw photo's brightest neutrals.

    Studio product shots sit on a white sweep, so the 99th percentile per channel is
    a good stand-in for the illuminant. Clamped: on an editorial/dark-ground shot the
    estimate is unreliable, and a clamped near-identity is the safe failure mode.
    """
    try:
        im = Image.open(raw_path).convert("RGB")
    except Exception:
        return (1.0, 1.0, 1.0), False
    im.thumbnail((400, 400))
    a = np.asarray(im, dtype=np.float64)
    p = np.percentile(a.reshape(-1, 3), 99, axis=0)
    if float(p.max()) < 1.0:
        return (1.0, 1.0, 1.0), False
    g = float(p.max()) / np.maximum(p, 1.0)
    clamped = np.clip(g, *WB_CLAMP)
    applied = bool(np.any(np.abs(clamped - 1.0) > 0.01))
    return tuple(float(x) for x in clamped), applied


def pixel_source(gid):
    """(path, kind) for the best available garment-only pixels."""
    clean = os.path.join(GARMENTS, gid, "clean")
    if os.path.isdir(clean):
        files = sorted(os.listdir(clean))
        for tag, kind in (("_extracted", "extracted"), ("_dragcut", "dragcut")):
            for f in files:
                if tag in f and f.lower().endswith(".png"):
                    return os.path.join(clean, f), kind
    p = primary_raw(gid)
    return (p, "raw_rembg") if p else (None, None)


_SESSIONS = {}


def _session(name):
    from rembg import new_session
    if name not in _SESSIONS:
        _SESSIONS[name] = new_session(name)
    return _SESSIONS[name]


def _clean_mask(mask):
    """Largest connected region, pinholes closed — same treatment as dragcut.py."""
    m = (np.array(mask) > 128).astype(np.uint8)
    try:
        import cv2
        n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        if n > 1:
            largest = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
            m = (labels == largest).astype(np.uint8)
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, k)
    except Exception:
        pass
    return m


def _informative_alpha(im):
    """True if alpha actually isolates a subject.

    Some `_extracted.png` files are composited on white with a fully opaque alpha
    channel. Trusting that alpha means masking in the white background — which is
    how 01-plain-tee, a black top, first read as 66% white.
    """
    a = np.asarray(im.convert("RGBA"))[..., 3]
    opaque = float((a >= ALPHA_MIN).mean())
    return 0.02 < opaque < 0.98


def segment(path, meta):
    """Mask an unmasked image, following dragcut.py's routing rule exactly.

    On-model photos MUST use cloth-seg and must never fall back to the general
    model: the general model keeps the whole figure, so a garment's palette picks
    up the model's skin and *other* clothing. That is exactly how 26-liniss-dune-
    pants (sand) first reported a phantom 21% charcoal — the model's black halter.
    Shoes have no cloth-seg class and always use the general model.
    """
    img = Image.open(path).convert("RGB")
    # dragcut.py's condition: only *raw* on-model photos need cloth-seg. A file in
    # clean/ is already garment-only; there only the backdrop needs removing.
    on_model = (meta.get("source_photo_type") == "on-model"
                and os.path.basename(os.path.dirname(path)) == "raw"
                and meta.get("category") != "shoes")
    if on_model:
        cat = meta.get("category", "")
        region = CATEGORY_TO_REGION.get(cat, "full")
        masks = _session("u2net_cloth_seg").predict(img)
        m = _clean_mask(masks[CLOTH_REGIONS.index(region)].resize(img.size))
        if m.mean() >= MIN_MASK_COVERAGE:
            return img, m.astype(bool), f"cloth-seg/{region}"

        # Fallback for the 7 garments dragcut could never cut: cloth-seg files the
        # whole outfit under `full` and leaves upper/lower empty. `full` alone is
        # contaminated (it includes the model's *other* garments), so intersect it
        # with a category-appropriate vertical band of its own bbox.
        full = _clean_mask(masks[CLOTH_REGIONS.index("full")].resize(img.size))
        if full.mean() >= MIN_MASK_COVERAGE and cat in BAND_BY_CATEGORY:
            ys = np.where(full.any(axis=1))[0]
            if len(ys):
                top, bot = int(ys[0]), int(ys[-1])
                h = bot - top + 1
                f0, f1 = BAND_BY_CATEGORY[cat]
                band = np.zeros_like(full)
                band[top + int(h * f0): top + int(h * f1), :] = 1
                m2 = (full & band).astype(np.uint8)
                if m2.mean() >= MIN_MASK_COVERAGE:
                    return img, m2.astype(bool), f"cloth-seg/full+band({cat})"
        return img, None, f"cloth-seg/{region} too sparse"
    m = _session("u2net").predict(img)[0]
    m = _clean_mask(m.resize(img.size))
    if m.mean() >= MIN_MASK_COVERAGE:
        return img, m.astype(bool), "general"
    return img, None, "general too sparse"


def masked_pixels(path, kind, meta):
    """Nx3 uint8 array of garment-only pixels, background and matte edges removed."""
    im = Image.open(path)
    how = kind
    if kind == "raw_rembg" or not _informative_alpha(im):
        img, mask, how = segment(path, meta)
        if mask is None:
            return None, how
        im = img.convert("RGBA")
        im.putalpha(Image.fromarray((mask * 255).astype(np.uint8)))
    im = im.convert("RGBA")
    im.thumbnail((700, 700))
    arr = np.asarray(im)
    rgb, alpha = arr[..., :3], arr[..., 3]
    mask = alpha >= ALPHA_MIN
    if mask.sum() < 50:
        return None, how + " (empty)"
    # Erode: matte edges are blended with the removed background and would drag
    # every palette entry toward white.
    try:
        import cv2
        mask = cv2.erode(mask.astype(np.uint8), np.ones((5, 5), np.uint8),
                         iterations=1).astype(bool)
    except Exception:
        pass
    px = rgb[mask]
    return (px if len(px) else None), how


def quantise(px, gains):
    """White-balance, median-cut, prune, merge. Returns list of colour dicts."""
    f = np.clip(px.astype(np.float64) * np.array(gains), 0, 255)
    if len(f) > MAX_SAMPLES:
        idx = np.random.default_rng(0).choice(len(f), MAX_SAMPLES, replace=False)
        f = f[idx]
    strip = Image.fromarray(f.astype(np.uint8).reshape(-1, 1, 3))
    q = strip.quantize(colors=N_CLUSTERS, method=Image.Quantize.MEDIANCUT)
    pal = np.array(q.getpalette()[: N_CLUSTERS * 3]).reshape(-1, 3)
    idxs = np.asarray(q).reshape(-1)
    counts = np.bincount(idxs, minlength=N_CLUSTERS).astype(float)
    total = counts.sum()

    out = []
    for i in np.argsort(-counts):
        cov = counts[i] / total
        if cov < MIN_COVERAGE:
            continue
        lab = srgb_to_lab(pal[i])
        merged = False
        for e in out:                          # merge perceptual near-duplicates
            if float(np.sqrt(((np.array(e["lab"]) - lab) ** 2).sum())) < MERGE_DE:
                e["coverage"] = round(e["coverage"] + cov, 4)
                merged = True
                break
        if not merged:
            out.append({
                "lab": [float(v) for v in lab],
                "rgb": [int(v) for v in pal[i]],
                "name": name_for(lab),
                "coverage": float(cov),
            })

    # Collapse entries that landed on the same name (e.g. two greys 10 ΔE apart):
    # one garment reporting "grey" twice is noise, not information.
    by_name = {}
    for c in out:
        prev = by_name.get(c["name"])
        if prev is None:
            by_name[c["name"]] = c
            continue
        w0, w1 = prev["coverage"], c["coverage"]
        tot = w0 + w1
        prev["lab"] = [(a * w0 + b * w1) / tot for a, b in zip(prev["lab"], c["lab"])]
        prev["rgb"] = [int((a * w0 + b * w1) / tot) for a, b in zip(prev["rgb"], c["rgb"])]
        prev["coverage"] = tot

    final = sorted(by_name.values(), key=lambda c: -c["coverage"])
    for c in final:
        c["lab"] = [round(v, 2) for v in c["lab"]]
        c["coverage"] = round(c["coverage"], 4)
    return final


def rename_only():
    """Recompute names from the LAB already in colors.json — no re-segmentation.

    Colour naming is cosmetic (the engine uses LAB), so recalibrating anchors must
    never cost another full rembg pass over the catalogue.
    """
    with open(OUT) as fh:
        data = json.load(fh)
    changed = 0
    for gid, v in data.items():
        for c in v.get("colors", []):
            new = name_for(np.array(c["lab"]))
            if new != c["name"]:
                print(f"  {gid:34s} {c['name']:12s} -> {new:12s} L*={c['lab'][0]:.1f}")
                c["name"] = new
                changed += 1
    with open(OUT, "w") as fh:
        json.dump(data, fh, indent=2)
    print(f"\nrenamed {changed} colour entries across {len(data)} garments")


def main():
    if "--rename" in sys.argv:
        return rename_only()
    only = set(sys.argv[1:])
    dirs = [d for d in sorted(os.listdir(GARMENTS))
            if os.path.isdir(os.path.join(GARMENTS, d)) and d not in ("raw", "archive")]
    if only:
        dirs = [d for d in dirs if d in only]

    results, failures = {}, []
    for gid in dirs:
        meta_path = os.path.join(GARMENTS, gid, "meta.json")
        if not os.path.exists(meta_path):
            failures.append((gid, "no meta.json"))
            continue
        with open(meta_path) as fh:
            meta = json.load(fh)
        path, kind = pixel_source(gid)
        if not path:
            failures.append((gid, "no pixel source"))
            continue
        raw = primary_raw(gid)
        gains, applied = wb_gains(raw) if raw else ((1.0, 1.0, 1.0), False)
        try:
            px, how = masked_pixels(path, kind, meta)
        except Exception as e:
            failures.append((gid, f"{type(e).__name__}: {e}"))
            continue
        if px is None:
            failures.append((gid, f"no usable mask ({how})"))
            continue
        colors = quantise(px, gains)
        results[gid] = {
            "colors": colors,
            "source": os.path.relpath(path, CLOSET),
            "source_kind": how,
            "wb_gains": [round(g, 4) for g in gains],
            "wb_applied": applied,
            "meta_color": meta.get("color"),      # for the QA comparison
            "source_photo_type": meta.get("source_photo_type"),
        }
        top = ", ".join(f"{c['name']} {c['coverage']:.0%}" for c in colors)
        print(f"  {gid:34s} [{how:18s}] {top:44s} meta: {meta.get('color')}")

    with open(OUT, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\n{len(results)} garments -> {os.path.relpath(OUT)}")
    if failures:
        print(f"{len(failures)} FAILED:")
        for gid, why in failures:
            print(f"  {gid}: {why}")


if __name__ == "__main__":
    main()
