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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("garment", nargs="?")
    ap.add_argument("--arm", default="nb2", choices=ARMS)  # Phase 3 winner (docs/phase3-benchmark.md)
    ap.add_argument("--suffix", default="1")
    ap.add_argument("--benchmark", action="store_true")
    args = ap.parse_args()

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
