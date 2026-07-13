#!/usr/bin/env python3
"""Try-on pipeline: garment + avatar-v1 -> render -> face-swap finish -> log.

Arms:
  nb-pro    fal-ai/nano-banana-pro   (avatar front + garment asset, prompt compose)
  nb2       fal-ai/nano-banana-2     (same inputs, cheaper)
  idm-vton  fal-ai/idm-vton          (specialist: human_image_url + garment_image_url)

Every face-visible render gets the fal-ai/face-swap finishing pass with
avatar/avatar-v1/front.png as the identity source (standing policy,
docs/decisions.md 2026-07-13). All calls are budget-gated and logged.

CLI:
    python3 scripts/tryon.py <garment-id> [--arm nb-pro] [--suffix 1]
    python3 scripts/tryon.py --benchmark          # all garments x all arms
"""
import argparse
import base64
import json
import mimetypes
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from genlog import check_budget, log_generation
from fal_generate import generate, load_key

ROOT = Path(__file__).resolve().parent.parent
AVATAR = ROOT / "avatar" / "avatar-v1" / "front.png"
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}
ARMS = ("nb-pro", "nb2", "idm-vton")

TRYON_PROMPT = (
    "Virtual try-on: show the person from Image 1 wearing the garment from Image 2. "
    "Keep the person EXACTLY as in Image 1: same face, same hair (black, wispy bangs, "
    "past shoulders), same body proportions as Image 1, same standing pose, same "
    "light-gray seamless studio background and soft even lighting. One single figure, "
    "not a collage. Reproduce the garment exactly: same color, pattern placement, "
    "neckline, sleeve length, buttons, hem length, and construction details. Natural "
    "fabric drape appropriate to {fabric}. {layer_note}Full-body, front-facing, "
    "photorealistic.{details}{cutout_note}"
)


def garment_asset(gid):
    """Best available garment image: generative extraction > seg cutout on white > raw."""
    folder = ROOT / "garments" / gid
    for pattern in ("clean/*_extracted.png", "clean/*_onwhite.png", "raw/*"):
        hits = [p for p in sorted(folder.glob(pattern)) if p.suffix.lower() in IMG_EXT]
        if hits:
            return hits[0]
    raise FileNotFoundError(f"no garment image for {gid}")


def data_uri(path):
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode()


def face_swap(base_path, out_path, source_path=AVATAR, purpose="tryon"):
    """fal-ai/face-swap: put source's face onto base. Returns out_path."""
    check_budget("fal-ai/face-swap")
    key = load_key()
    payload = {"base_image_url": data_uri(base_path), "swap_image_url": data_uri(source_path)}
    req = urllib.request.Request("https://fal.run/fal-ai/face-swap",
                                 data=json.dumps(payload).encode(), method="POST")
    req.add_header("Authorization", f"Key {key}")
    req.add_header("Content-Type", "application/json")
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                result = json.loads(r.read().decode())
            break
        except OSError as e:
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
    img = result.get("image") or (result.get("images") or [{}])[0]
    url = img["url"] if isinstance(img, dict) else img
    for attempt in range(4):
        try:
            urllib.request.urlretrieve(url, out_path)
            break
        except OSError:
            if attempt == 3:
                log_generation("fal-ai/face-swap", "face-swap finish", purpose,
                               ref_images=[str(base_path)], cost_usd=0.02,
                               outcome=f"completed-download-failed: {url}")
                raise
            time.sleep(3 * (attempt + 1))
    log_generation("fal-ai/face-swap", "face-swap finish (avatar-v1 identity)", purpose,
                   ref_images=[str(base_path), str(source_path)],
                   output_path=str(out_path), cost_usd=0.02)
    return out_path


def run_idm_vton(gid, meta, out_path):
    check_budget("fal-ai/idm-vton")
    key = load_key()
    desc = f"{meta.get('name', gid)} — {meta.get('color','')} {meta.get('fabric','')}".strip()
    payload = {
        "human_image_url": data_uri(AVATAR),
        "garment_image_url": data_uri(garment_asset(gid)),
        "description": desc,
    }
    req = urllib.request.Request("https://fal.run/fal-ai/idm-vton",
                                 data=json.dumps(payload).encode(), method="POST")
    req.add_header("Authorization", f"Key {key}")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=600) as r:
        result = json.loads(r.read().decode())
    img = result.get("image") or (result.get("images") or [{}])[0]
    url = img["url"] if isinstance(img, dict) else img
    urllib.request.urlretrieve(url, out_path)
    log_generation("fal-ai/idm-vton", f"idm-vton: {desc}", "tryon",
                   ref_images=[str(AVATAR), str(garment_asset(gid))],
                   output_path=str(out_path), cost_usd=0.03)
    return out_path


def tryon(gid, arm="nb-pro", suffix="1"):
    meta = json.loads((ROOT / "garments" / gid / "meta.json").read_text())
    out = ROOT / "renders" / f"{gid}_{arm}_v1_{suffix}.png"
    raw = ROOT / "renders" / f"{gid}_{arm}_v1_{suffix}_raw.png"

    if arm == "idm-vton":
        run_idm_vton(gid, meta, raw)
    else:
        # nb2's base endpoint is text-to-image and ignores image_urls; use /edit
        model = "fal-ai/nano-banana-pro" if arm == "nb-pro" else "fal-ai/nano-banana-2/edit"
        asset = garment_asset(gid)
        details = ""
        if meta.get("details_to_preserve"):
            details = " Pay particular attention to: " + ", ".join(meta["details_to_preserve"]) + "."
        cutout_note = ""
        if "clean" in str(asset):
            cutout_note = (" Image 2 is an isolated garment product shot; any small gaps or "
                           "ragged edges are extraction artifacts — render the garment complete.")
        layer_note = ""
        if meta.get("layer_order", 0) > 0:
            layer_note = ("Layer the garment OPEN over her existing gray tank top, tank visible "
                          "underneath. ")
        prompt = TRYON_PROMPT.format(fabric=meta.get("fabric") or "the fabric",
                                     details=details, cutout_note=cutout_note,
                                     layer_note=layer_note)
        generate(model, prompt, [str(AVATAR), str(asset)], purpose="tryon", out=str(raw))

    face_swap(raw, out)
    print(f"done {out.name}")
    return out


# feedback button -> canned corrective edit (plan §Phase 4); the user's note is appended
CORRECTIVE = {
    "wrong fit": "correct the garment's fit, cut and construction to exactly match the "
                 "garment reference in Image 2",
    "fabric off": "correct the garment's fabric texture, weight and sheen to exactly match "
                  "the garment reference in Image 2",
    "artifact": "remove the visual artifact",
    "pattern wrong": "correct the garment's pattern and its placement to exactly match the "
                     "garment reference in Image 2",
    "face drifted": None,  # face-swap only, no generation
}


def next_suffix(stem_prefix):
    return str(1 + len([p for p in (ROOT / "renders").glob(f"{stem_prefix}_*.png")
                        if not p.stem.endswith("_raw")]))


def correct(gid, button, note="", render=None):
    """Targeted corrective edit of a render (edit, don't regenerate)."""
    if render is None:  # newest final nb2 render for this garment
        cands = [p for p in sorted((ROOT / "renders").glob(f"{gid}_*_v1_*.png"))
                 if not p.stem.endswith("_raw")]
        if not cands:
            raise FileNotFoundError(f"no render to correct for {gid}")
        render = cands[-1]
    render = ROOT / "renders" / Path(render).name
    out = ROOT / "renders" / f"{gid}_nb2_v1_{next_suffix(f'{gid}_nb2_v1')}.png"

    if CORRECTIVE.get(button, "x") is None:  # face drifted -> swap only
        face_swap(render, out)
        print(f"done {out.name} (face-swap only)")
        return out

    correction = CORRECTIVE.get(button, "apply this correction")
    if note:
        correction += f". Specifically: {note.strip()}"
    prompt = (
        f"Edit Image 1, changing ONLY this: {correction}. Image 2 is the garment product "
        "photo and is the ground truth for how the garment must look. Keep the person, "
        "face, hair, pose, body, lighting, background and everything else in Image 1 "
        "exactly unchanged. One single image, one single figure, photorealistic."
    )
    raw = out.with_name(out.stem + "_raw.png")
    generate("fal-ai/nano-banana-2/edit", prompt, [str(render), str(garment_asset(gid))],
             purpose="tryon-corrective", out=str(raw))
    face_swap(raw, out)
    print(f"done {out.name}")
    return out


LAYER_HINTS = {
    "outerwear": "worn OPEN as the outermost layer",
    "layer": "worn OPEN as the outermost layer",
    "top": "worn over the bottom garment",
    "bottom": "worn as the base lower-body garment",
    "dress": "worn as the base garment",
    "shoes": "worn on the feet",
}


def tryon_outfit(gids, suffix=None):
    """Single-shot multi-garment compose: avatar + one image per garment."""
    metas = []
    for gid in gids:
        metas.append(json.loads((ROOT / "garments" / gid / "meta.json").read_text()))
    # dress the avatar inside-out: base layers first in the description
    order = {"dress": 0, "bottom": 1, "top": 2, "layer": 3, "outerwear": 3, "shoes": 4}
    pairs = sorted(zip(gids, metas), key=lambda p: order.get(p[1].get("category"), 2))

    lines, images = [], [str(AVATAR)]
    for i, (gid, meta) in enumerate(pairs):
        images.append(str(garment_asset(gid)))
        hint = LAYER_HINTS.get(meta.get("category", ""), "")
        details = "; ".join(meta.get("details_to_preserve", [])[:3])
        lines.append(f"Image {i + 2}: {meta.get('name', gid)} ({meta.get('color','')}, "
                     f"{hint}). Key details: {details}")

    prompt = (
        "Virtual try-on: show the person from Image 1 wearing ALL of the following garments "
        "together as one complete outfit, layered naturally: " + " | ".join(lines) + ". "
        "Keep the person EXACTLY as in Image 1: same face, same hair, same body proportions, "
        "same standing pose, same light-gray seamless studio background and soft even "
        "lighting. One single figure, not a collage. Reproduce every garment exactly as in "
        "its reference image: colors, patterns, necklines, lengths, construction. The "
        "garment reference images are isolated product shots; any small gaps or ragged "
        "edges are extraction artifacts - render each garment complete. Full-body, "
        "front-facing, photorealistic."
    )
    slug = "outfit_" + "+".join(g.split("-")[0] for g in sorted(gids))
    n = suffix or next_suffix(slug)
    out = ROOT / "renders" / f"{slug}_{n}.png"
    raw = out.with_name(out.stem + "_raw.png")
    generate("fal-ai/nano-banana-2/edit", prompt, images, purpose="tryon-outfit", out=str(raw))
    face_swap(raw, out)
    print(f"done {out.name}")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("garment", nargs="?")
    ap.add_argument("--arm", default="nb2", choices=ARMS)  # Phase 3 winner (docs/phase3-benchmark.md)
    ap.add_argument("--suffix", default="1")
    ap.add_argument("--benchmark", action="store_true")
    ap.add_argument("--correct", metavar="BUTTON", help="corrective edit; pass the feedback button text")
    ap.add_argument("--note", default="", help="freeform correction note (with --correct)")
    ap.add_argument("--outfit", nargs="+", metavar="GID", help="compose several garments in one render")
    args = ap.parse_args()

    if args.outfit:
        tryon_outfit(args.outfit)
        return

    if args.correct:
        if not args.garment:
            ap.error("--correct needs a garment id")
        correct(args.garment, args.correct, args.note)
        return

    if args.benchmark:
        gids = sorted(p.parent.name for p in (ROOT / "garments").glob("*/meta.json"))
        for gid in gids:
            for arm in ARMS:
                if (ROOT / "renders" / f"{gid}_{arm}_v1_1.png").exists():
                    print(f"skip {gid} {arm}: render exists")
                    continue
                try:
                    tryon(gid, arm)
                except Exception as e:  # keep the batch going; report at the end
                    print(f"FAIL {gid} {arm}: {e}")
    elif args.garment:
        tryon(args.garment, args.arm, args.suffix)
    else:
        ap.error("garment id or --benchmark required")


if __name__ == "__main__":
    main()
