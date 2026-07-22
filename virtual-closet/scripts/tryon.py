#!/usr/bin/env python3
"""Try-on pipeline: garment + avatar-v3 pose base -> render -> face-swap finish -> log.

Arms:
  nb-pro    fal-ai/nano-banana-pro   (avatar base + garment asset, prompt compose)
  nb2       fal-ai/nano-banana-2     (same inputs, cheaper)
  idm-vton  fal-ai/idm-vton          (specialist: human_image_url + garment_image_url)

Every face-visible render gets the fal-ai/face-swap finishing pass with
avatar/avatar-v3/front.png as the identity source (standing policy,
docs/decisions.md 2026-07-14; v1 renders are legacy lineage). All calls are
budget-gated and logged.

CLI:
    python3 scripts/tryon.py <garment-id> [--arm nb-pro] [--suffix 1] [--pose contrapposto]
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
AVATAR_DIR = ROOT / "avatar" / "avatar-v3"
AVATAR = AVATAR_DIR / "front.png"          # identity source for every face-swap
AVA_VER = "v3"
POSES = ("front", "contrapposto", "hand-on-hip", "34turn")
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}
ARMS = ("nb-pro", "nb2", "idm-vton")

# 360 spin (fitting room, 2026-07-19): 45-degree frames on neutral turn bases
# (avatar/avatar-v3/turn-###.png, Janice-supplied like front-receive). Face-swap
# only where the face is frontal enough for the swap model; rear frames carry
# identity via hair/build. Rear frames get each garment's back photo as extra
# ground truth when one exists.
ANGLES = ("a045", "a090", "a135", "a180", "a225", "a270", "a315")
ANGLE_BASE = {a: f"turn-{a[1:]}.png" for a in ANGLES}
ANGLE_VIEW = {
    "a045": "a front three-quarter view, her right shoulder nearer the camera",
    "a090": "a full right-side profile view",
    "a135": "a back three-quarter view, her right shoulder nearer the camera",
    "a180": "a view directly from behind, her back to the camera",
    "a225": "a back three-quarter view, her left shoulder nearer the camera",
    "a270": "a full left-side profile view",
    "a315": "a front three-quarter view, her left shoulder nearer the camera",
}
ANGLE_FACED = {"a045", "a315"}          # frames that get the face-swap finish
ANGLE_REAR = {"a135", "a180", "a225"}   # frames that want garment back photos


def garment_back_asset(gid):
    """Back-view photo for rear spin frames (product back preferred), or None."""
    raw = ROOT / "garments" / gid / "raw"
    hits = [p for p in sorted(raw.glob("*back*")) if p.suffix.lower() in IMG_EXT]
    if not hits:
        return None
    product = [p for p in hits if "model" not in p.stem]
    return product[0] if product else hits[0]

TRYON_PROMPT = (
    "Virtual try-on: show the person from Image 1 wearing the garment from Image 2. "
    "Keep the person EXACTLY as in Image 1: same face, same hair (black, soft parted "
    "bangs, long loose waves), same body proportions as Image 1, same pose, same "
    "seamless studio background and soft even lighting. One single figure, "
    "not a collage. Reproduce the garment exactly: same color, pattern placement, "
    "neckline, sleeve length, buttons, hem length, and construction details. Natural "
    "fabric drape appropriate to {fabric}. {slot_note}{layer_note}Full-body, {facing}"
    "photorealistic.{details}{exclude_note}{cutout_note}"
)

# category -> what the garment replaces and what stays from the base outfit
# (2026-07-16: without this anchor, skirts became dresses and flats became a
# printed dress; companion garments in on-model photos leaked in)
SLOT_NOTES = {
    "top":       "The garment is a TOP: she keeps her black leggings from Image 1 "
                 "unchanged. ",
    "bottom":    "The garment is worn on the LOWER BODY, replacing the leggings: she "
                 "keeps her gray tank top from Image 1 unchanged. ",
    "dress":     "The garment is a DRESS, replacing both the tank top and the "
                 "leggings. ",
    "outerwear": "She keeps her gray tank top and black leggings from Image 1 "
                 "visible beneath. ",
    "shoes":     "The garment is FOOTWEAR only, worn on her feet: her gray tank top "
                 "and black leggings stay exactly as in Image 1. ",
}


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
    log_generation("fal-ai/face-swap", f"face-swap finish (avatar-{AVA_VER} identity)", purpose,
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


def tryon(gid, arm="nb-pro", suffix="1", pose="front"):
    meta = json.loads((ROOT / "garments" / gid / "meta.json").read_text())
    base = AVATAR_DIR / f"{pose}.png"
    pose_tag = "" if pose == "front" else f"_{pose}"
    out = ROOT / "renders" / f"{gid}_{arm}_{AVA_VER}{pose_tag}_{suffix}.png"
    raw = ROOT / "renders" / f"{gid}_{arm}_{AVA_VER}{pose_tag}_{suffix}_raw.png"

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
        if meta.get("wear_note"):  # per-garment override: not every layer is worn open
            layer_note = meta["wear_note"].strip() + ". "
        elif meta.get("layer_order", 0) > 0:
            layer_note = ("Layer the garment OPEN over her existing gray tank top, tank visible "
                          "underneath. ")
        facing = ("front-facing, " if pose == "front"
                  else "in the same stance and camera angle as Image 1, ")
        slot_note = SLOT_NOTES.get(meta.get("category", ""), "")
        exclude_note = ""
        if meta.get("exclude_from_photo"):
            exclude_note = (" In Image 2 the garment is shown worn with other items ("
                            + ", ".join(meta["exclude_from_photo"])
                            + ") — those are NOT part of this garment; do not add them.")
        prompt = TRYON_PROMPT.format(fabric=meta.get("fabric") or "the fabric",
                                     details=details, cutout_note=cutout_note,
                                     layer_note=layer_note, facing=facing,
                                     slot_note=slot_note, exclude_note=exclude_note)
        generate(model, prompt, [str(base), str(asset)], purpose="tryon", out=str(raw))

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
    if render is None:  # newest final FRONT render (feedback loop is fitting-room only)
        pose_tags = tuple(f"_{p}_" for p in POSES if p != "front")
        cands = [p for p in sorted((ROOT / "renders").glob(f"{gid}_*_v*_*.png"))
                 if not p.stem.endswith("_raw")
                 and not any(t in f"{p.stem}_" for t in pose_tags)]
        if not cands:
            raise FileNotFoundError(f"no render to correct for {gid}")
        render = cands[-1]
    render = ROOT / "renders" / Path(render).name
    out = ROOT / "renders" / f"{gid}_nb2_{AVA_VER}_{next_suffix(f'{gid}_nb2_{AVA_VER}')}.png"

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


def tryon_outfit(gids, suffix=None, pose="front"):
    """Single-shot multi-garment compose: avatar pose base + one image per garment."""
    metas = []
    for gid in gids:
        metas.append(json.loads((ROOT / "garments" / gid / "meta.json").read_text()))
    # dress the avatar inside-out: base layers first in the description
    order = {"dress": 0, "bottom": 1, "top": 2, "layer": 3, "outerwear": 3, "shoes": 4}
    pairs = sorted(zip(gids, metas), key=lambda p: order.get(p[1].get("category"), 2))

    lines, images = [], [str(AVATAR_DIR / f"{pose}.png")]
    for i, (gid, meta) in enumerate(pairs):
        images.append(str(garment_asset(gid)))
        hint = meta.get("wear_note", "").strip() or LAYER_HINTS.get(meta.get("category", ""), "")
        details = "; ".join(meta.get("details_to_preserve", [])[:3])
        line = (f"Image {i + 2}: {meta.get('name', gid)} ({meta.get('color','')}, "
                f"{hint}). Key details: {details}")
        if meta.get("exclude_from_photo"):
            line += (" (its reference photo also shows "
                     + ", ".join(meta["exclude_from_photo"])
                     + " - NOT part of this garment; do not add them)")
        lines.append(line)

    prompt = (
        "Virtual try-on: show the person from Image 1 wearing ALL of the following garments "
        "together as one complete outfit, layered naturally: " + " | ".join(lines) + ". "
        "Keep the person EXACTLY as in Image 1: same face, same hair, same body proportions, "
        "same standing pose, same light-gray seamless studio background and soft even "
        "lighting. One single figure, not a collage. Reproduce every garment exactly as in "
        "its reference image: colors, patterns, necklines, lengths, construction. The "
        "garment reference images are isolated product shots; any small gaps or ragged "
        "edges are extraction artifacts - render each garment complete. Full-body, "
        + ("front-facing, " if pose == "front"
           else "in the same stance and camera angle as Image 1, ")
        + "photorealistic."
    )
    slug = ("outfit_" + "+".join(g.split("-")[0] for g in sorted(gids))
            + ("" if pose == "front" else f"_{pose}"))
    n = suffix or next_suffix(slug)
    out = ROOT / "renders" / f"{slug}_{n}.png"
    raw = out.with_name(out.stem + "_raw.png")
    generate("fal-ai/nano-banana-2/edit", prompt, images, purpose="tryon-outfit", out=str(raw))
    face_swap(raw, out)
    print(f"done {out.name}")
    return out


def spin_stem(gids, angle):
    """Render stem for one spin frame; single-garment stems keep the gid prefix."""
    if len(gids) == 1:
        return f"{gids[0]}_nb2_{AVA_VER}_{angle}"
    return "outfit_" + "+".join(g.split("-")[0] for g in sorted(gids)) + f"_{angle}"


def spin_frame(gids, angle):
    """One 45-degree spin frame: compose all garments on the matching turn base."""
    base = AVATAR_DIR / ANGLE_BASE[angle]
    if not base.is_file():
        raise FileNotFoundError(f"missing avatar turn base: {base.name} (Janice supplies these)")
    metas = [json.loads((ROOT / "garments" / g / "meta.json").read_text()) for g in gids]
    order = {"dress": 0, "bottom": 1, "top": 2, "layer": 3, "outerwear": 3, "shoes": 4}
    pairs = sorted(zip(gids, metas), key=lambda p: order.get(p[1].get("category"), 2))

    lines, images = [], [str(base)]
    backs = []
    for i, (gid, meta) in enumerate(pairs):
        images.append(str(garment_asset(gid)))
        hint = meta.get("wear_note", "").strip() or LAYER_HINTS.get(meta.get("category", ""), "")
        details = "; ".join(meta.get("details_to_preserve", [])[:3])
        line = (f"Image {i + 2}: {meta.get('name', gid)} ({meta.get('color','')}, "
                f"{hint}). Key details: {details}")
        if meta.get("exclude_from_photo"):
            line += (" (its reference photo also shows "
                     + ", ".join(meta["exclude_from_photo"])
                     + " - NOT part of this garment; do not add them)")
        if angle in ANGLE_REAR:
            back = garment_back_asset(gid)
            if back:
                backs.append((meta.get("name", gid), back))
            elif meta.get("back_note"):
                line += f" From behind: {meta['back_note']}"
        lines.append(line)
    for name, back in backs:  # back refs follow the garment images
        images.append(str(back))
        lines.append(f"Image {len(images)}: the BACK of the {name} - ground truth "
                     "for how that garment looks from behind")

    prompt = (
        "Virtual try-on: show the person from Image 1 wearing ALL of the following "
        "garments together as one complete outfit, layered naturally: "
        + " | ".join(lines) + ". "
        f"Image 1 shows the person in {ANGLE_VIEW[angle]}; render the garments "
        "correctly for exactly that viewpoint. Keep the person EXACTLY as in Image 1: "
        "same body proportions, same stance and camera angle, same hair, same "
        "light-gray seamless studio background and soft even lighting. One single "
        "figure, not a collage. Reproduce every garment exactly as in its reference "
        "image: colors, patterns, lengths, construction. The garment reference images "
        "are isolated product shots; any small gaps or ragged edges are extraction "
        "artifacts - render each garment complete. Full-body, photorealistic."
    )
    stem = spin_stem(gids, angle)
    out = ROOT / "renders" / f"{stem}_{next_suffix(stem)}.png"
    raw = out.with_name(out.stem + "_raw.png")
    generate("fal-ai/nano-banana-2/edit", prompt, images, purpose="tryon-spin", out=str(raw))
    if angle in ANGLE_FACED:
        face_swap(raw, out)
    else:  # no frontal face to restore; the raw IS the frame
        out.write_bytes(raw.read_bytes())
    print(f"done {out.name}")
    return out


def spin_existing(gids, angle):
    """Newest non-raw render for a spin stem, or None."""
    stem = spin_stem(gids, angle)
    hits = [p for p in sorted((ROOT / "renders").glob(f"{stem}_*.png"))
            if not p.stem.endswith("_raw")]
    return hits[-1] if hits else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("garment", nargs="?")
    ap.add_argument("--arm", default="nb2", choices=ARMS)  # Phase 3 winner (docs/phase3-benchmark.md)
    ap.add_argument("--suffix", default="1")
    ap.add_argument("--pose", default="front", choices=POSES,
                    help="avatar-v3 pose base (one pose per saved look)")
    ap.add_argument("--benchmark", action="store_true")
    ap.add_argument("--correct", metavar="BUTTON", help="corrective edit; pass the feedback button text")
    ap.add_argument("--note", default="", help="freeform correction note (with --correct)")
    ap.add_argument("--outfit", nargs="+", metavar="GID", help="compose several garments in one render")
    ap.add_argument("--spin", action="store_true",
                    help="generate the 7 missing 45-degree spin frames for the garment/outfit")
    args = ap.parse_args()

    if args.spin:
        gids = args.outfit or ([args.garment] if args.garment else None)
        if not gids:
            ap.error("--spin needs a garment id or --outfit")
        for angle in ANGLES:
            if spin_existing(gids, angle):
                print(f"skip {angle}: frame exists")
                continue
            try:
                spin_frame(gids, angle)
            except Exception as e:  # keep the batch going
                print(f"FAIL {angle}: {e}")
        return

    if args.outfit:
        tryon_outfit(args.outfit, pose=args.pose)
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
        tryon(args.garment, args.arm, args.suffix, args.pose)
    else:
        ap.error("garment id or --benchmark required")


if __name__ == "__main__":
    main()
