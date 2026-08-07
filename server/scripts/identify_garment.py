#!/usr/bin/env python3
"""Identify a garment from her own photo, and pre-fill the ingest grid from the
product page it finds. **$0 by default**; `--generate` bills.

    python3 scripts/identify_garment.py --image ~/Desktop/thing.jpg          # $0 dry run
    python3 scripts/identify_garment.py --image ~/Desktop/thing.jpg --generate
    python3 scripts/identify_garment.py --garment 59-el-hoodie --generate    # re-identify

WHAT THIS IS FOR. `/ingest` asks her to type ~12 attributes per garment. The
bottleneck she named is the typing, so this pre-fills the grid and leaves her
reviewing instead of composing.

**THE WIN IS THE PRODUCT PAGE, NOT THE BETTER PHOTO.** A photo cannot tell you a
brand or a fabric composition; a product page states both in text — and `fabric`
is the one field her own ingest form gives up on ("models guess badly at this —
yours is better"). Finding the page is therefore worth more for TAGGING than for
imagery, even though it also yields a better image for the render tier.

ONE CALL, NOT THREE. Web search is an Anthropic SERVER tool, so the model
searches during the request: photo in -> identify -> search -> read the page ->
structured JSON out. No separate search API, no key, and `ingest_fetch.py` keeps
its existing job of ranking candidate images on whatever page this finds.

Consequently this needs NO fal credit — it is Anthropic plus local code. Track
A's SAM-detection half drops out entirely: she photographs one item at a time,
so multi-garment detection was never the thing that was slow.

FOUR THINGS THIS DELIBERATELY WILL NOT FILL
  colour            measured by extract_colors.py from pixels. Invariant #6 —
                    the model may NAME a colour, never MEASURE one. That rule
                    survived a QA round against her own eyes.
  purchase price    the listing price is NOT what she paid. Closet value
                    ($6,298) and every cost-per-wear figure in /insights are
                    built on her real purchase data; filling it from a retail
                    page would quietly corrupt the one hand-built dataset here.
  purchase date     same reason.
  size_owned        in no photo and on no page. Her standing ingest note: "log
                    real sizes at ingest — not everything is S."

CONFIRM BEFORE PRE-FILLING. A confident MISidentification is worse than a blank
grid: every field comes back plausible and wrong, and she is reviewing rather
than composing, so it is easy to wave through. The payload therefore separates
`identification` from `attributes`, and carries per-field `provenance` — the UI
must make her confirm the identification before applying anything.

FAILURE IS EXPECTED AND MUST BE GRACEFUL. A plain black tank with no visible
label is unidentifiable, and ~60% of this closet sits below L*25. When the model
cannot identify the garment it returns `identified: false` and image-only
attributes, which is a worse pre-fill but an honest one.
"""
import argparse
import base64
import json
import mimetypes
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CLOSET = ROOT / "virtual-closet"

# Sonnet 5, not Opus 5. This is classification, not reasoning — and Sonnet 5 is
# on introductory pricing ($2/$10 per MTok) through 2026-08-31.
MODEL = "claude-sonnet-5"

# Per-MTok, checked 2026-07-28 (introductory Sonnet 5 rates).
PRICE_IN, PRICE_OUT = 2.00, 10.00
SEARCH_PRICE = 0.010          # $10 per 1,000 searches
# One focused query is enough for this classification task. The first paid
# pilot allowed three and pulled 52.5k input tokens, turning a projected $0.059
# call into $0.1468. One is the cost boundary the original estimate assumed.
MAX_SEARCHES = 1

CATEGORIES = ("top", "bottom", "dress", "outerwear", "shoes")

# Mirrors the fields on /ingest's form, minus the four above. `enum` where the
# app already constrains the value, so a pre-fill cannot introduce a category
# the rest of the closet has never heard of.
SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["identification", "attributes"],
    "properties": {
        "identification": {
            "type": "object",
            "additionalProperties": False,
            "required": ["identified", "confidence", "evidence"],
            "properties": {
                "identified": {"type": "boolean"},
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                # What in the IMAGE led here — a label, a hardware detail, a
                # print. Her review needs to check the reasoning, not just the
                # answer; "it looks like a black tank" is not evidence.
                "evidence": {"type": "string"},
                "brand": {"type": "string"},
                "product_name": {"type": "string"},
                "product_url": {"type": "string"},
                "image_url": {"type": "string"},
            },
        },
        "attributes": {
            "type": "object",
            "additionalProperties": False,
            "required": ["category", "subcategory", "formality", "warmth",
                         "volume", "pattern", "fabric", "fit", "seasons",
                         "provenance"],
            "properties": {
                "category": {"type": "string", "enum": list(CATEGORIES)},
                "subcategory": {"type": "string"},
                "formality": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
                "warmth": {"type": "integer", "enum": [1, 2, 3, 4, 5]},
                "volume": {"type": "string",
                           "enum": ["fitted", "regular", "oversized"]},
                "pattern": {"type": "string"},
                "fabric": {"type": "string"},
                "fit": {"type": "string"},
                "seasons": {"type": "array", "items": {
                    "type": "string",
                    "enum": ["spring", "summer", "autumn", "winter"]}},
                # Per-field: which of the three sources produced it. This is what
                # tells her which cells deserve scrutiny — a fabric read off a
                # page is trustworthy, a formality inferred from a photo is a
                # guess wearing the same typeface.
                "provenance": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["category", "subcategory", "formality", "warmth",
                                 "volume", "pattern", "fabric", "fit", "seasons"],
                    "properties": {
                        k: {"type": "string", "enum": ["page", "image", "inferred"]}
                        for k in ("category", "subcategory", "formality", "warmth",
                                  "volume", "pattern", "fabric", "fit", "seasons")
                    },
                },
            },
        },
    },
}

SYSTEM = """You identify a single garment from a photograph its owner took, then \
fill in a catalogue entry for it.

Work in this order:
1. Read the image for anything that IDENTIFIES this specific product: a brand \
label, a care tag, a logo, distinctive hardware, an unusual print or seam.
2. If you found something identifying, search the web for that specific product \
and open the product page.
3. Compare the candidate page back to the input image. Set identified=true only \
when a legible product name or model code matches, or at least two independent \
distinctive visual details match. A brand match alone is not a product match.
4. Only after that exact-product check may you fill attributes from the page. \
Otherwise return an honest image-only result.

Rules you must follow:
- If the image contains nothing that identifies a specific product — a plain \
garment with no visible label — set identified=false and DO NOT GUESS a brand \
or product. Fill the attributes from the image alone and mark their provenance \
"image" or "inferred". An honest blank beats a confident wrong answer, because \
the owner is reviewing these fields rather than writing them and a plausible \
error will pass unnoticed.
- A reseller search result without a comparable product image does not verify \
the product. If no candidate passes the exact-product check, set identified=false, \
leave brand/product_name/product_url/image_url blank, and use no "page" provenance. \
Never import fabric or fit merely because a page has the right brand.
- `evidence` must say what IN THE IMAGE led you to the identification (e.g. "care \
label reads ARITZIA; side-seam zip matches the product photo"). Never cite the \
search result as its own evidence.
- Mark provenance per field honestly: "page" only where the product page states \
it, "image" where you read it off the photograph, "inferred" where you reasoned \
from something else. Formality and warmth are almost always "inferred".
- Never report a colour. Colour is measured from pixels elsewhere.
- Never report a price, a purchase date, or a size."""


def _b64_image(path: Path):
    mime = mimetypes.guess_type(str(path))[0] or "image/jpeg"
    if mime not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        raise SystemExit("unsupported image type: %s" % mime)
    return mime, base64.standard_b64encode(path.read_bytes()).decode()


def find_image(garment_id: str) -> Path:
    """The primary raw photo for an existing garment (the plain-slug one sorts
    first, per the raw/ naming convention)."""
    raw = CLOSET / "garments" / garment_id / "raw"
    if not raw.is_dir():
        raise SystemExit("no raw/ folder for %s" % garment_id)
    shots = sorted(p for p in raw.iterdir()
                   if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    if not shots:
        raise SystemExit("no photo in %s" % raw)
    return shots[0]


def build_request(image_path: Path, hint: str = ""):
    """The exact request that --generate would send. Returned rather than sent so
    the whole flow can be exercised for $0."""
    mime, data = _b64_image(image_path)
    text = "Identify this garment and fill in its catalogue entry."
    if hint:
        text += "\n\nThe owner says: %s" % hint
    return {
        "model": MODEL,
        "max_tokens": 4096,
        "system": SYSTEM,
        # Classification, not reasoning. Thinking is ON BY DEFAULT on Sonnet 5
        # and Opus 5 — that default is what made the D.1 profile cost 20x its
        # estimate, so it is pinned low here rather than left implicit.
        "output_config": {
            "effort": "low",
            "format": {"type": "json_schema", "schema": SCHEMA},
        },
        "tools": [{"type": "web_search_20260209", "name": "web_search",
                   "max_uses": MAX_SEARCHES}],
        "messages": [{"role": "user", "content": [
            {"type": "image", "source": {"type": "base64",
                                         "media_type": mime, "data": data}},
            {"type": "text", "text": text},
        ]}],
    }


def estimate(image_path: Path):
    """Rough per-garment cost, stated in the same shape genlog records."""
    px = image_path.stat().st_size
    # Sonnet 5 is the high-res tier (2576px long edge, up to 4784 image tokens).
    img_tokens = 1600 if px < 900_000 else 4784
    # The first paid run averaged roughly 16k pulled-in tokens per search.
    in_tokens = img_tokens + 700 + 16000 * MAX_SEARCHES
    out_tokens = 1200                        # JSON + low-effort thinking
    tokens = in_tokens / 1e6 * PRICE_IN + out_tokens / 1e6 * PRICE_OUT
    search = MAX_SEARCHES * SEARCH_PRICE
    return {"image_tokens": img_tokens, "input_tokens": in_tokens,
            "output_tokens": out_tokens, "token_cost": round(tokens, 4),
            "search_cost_max": round(search, 4),
            "total_max": round(tokens + search, 4)}


def record_spend(spent, usage, searches, outcome, gid=""):
    """Standing rule #1: every paid call reaches genlog — including the ones that
    fail. Logged BEFORE the outcome is inspected, because a refusal or a
    truncation is billed exactly like a success (the 07-28 D.1 lesson)."""
    try:
        sys.path.insert(0, str(CLOSET / "scripts"))
        from genlog import log_generation
        log_generation(
            model=MODEL,
            prompt="identify garment from own photo + pre-fill ingest grid",
            purpose="garment-identify",
            cost_usd=round(spent, 4),
            outcome=outcome,
            extra={"garment": gid,
                   "input_tokens": getattr(usage, "input_tokens", None),
                   "output_tokens": getattr(usage, "output_tokens", None),
                   "web_searches": searches},
        )
    except Exception as exc:                                   # noqa: BLE001
        print("WARNING: genlog write failed (%s)" % exc, file=sys.stderr)


def check_spend_budget():
    """Apply the shared hard cap before creating a billable request."""
    sys.path.insert(0, str(CLOSET / "scripts"))
    from genlog import check_budget
    return check_budget(MODEL)


# Canned results shaped exactly like the real payload, so the whole flow — the
# confirm step, the provenance markers, the fallback path — can be built and
# reviewed for $0 before a single billed call. `hard` is the case that matters
# most: a plain dark garment with no label, which is what ~60% of this closet
# looks like to a camera.
STUBS = {
    "easy": {
        "identification": {
            "identified": True, "confidence": "high",
            "evidence": "Care label reads ARITZIA; the asymmetric side-seam zip "
                        "and cropped hem match the product photo.",
            "brand": "Aritzia", "product_name": "Divinity Cropped Jacket",
            "product_url": "https://example.invalid/divinity-jacket",
            "image_url": "https://example.invalid/divinity-jacket/front.jpg",
        },
        "attributes": {
            "category": "outerwear", "subcategory": "cropped jacket",
            "formality": 3, "warmth": 3, "volume": "fitted",
            "pattern": "solid", "fabric": "94% polyester, 6% elastane",
            "fit": "cropped, slightly tapered",
            "seasons": ["spring", "autumn"],
            "provenance": {
                "category": "image", "subcategory": "page", "formality": "inferred",
                "warmth": "inferred", "volume": "image", "pattern": "image",
                "fabric": "page", "fit": "page", "seasons": "inferred",
            },
        },
    },
    "hard": {
        "identification": {
            "identified": False, "confidence": "low",
            "evidence": "No label, logo, hardware or print is visible; a plain "
                        "black knit tank is not distinguishable from many others.",
            "brand": "", "product_name": "", "product_url": "", "image_url": "",
        },
        "attributes": {
            "category": "top", "subcategory": "tank",
            "formality": 2, "warmth": 1, "volume": "fitted",
            "pattern": "solid", "fabric": "", "fit": "close to body",
            "seasons": ["spring", "summer"],
            "provenance": {
                "category": "image", "subcategory": "image", "formality": "inferred",
                "warmth": "inferred", "volume": "image", "pattern": "image",
                "fabric": "inferred", "fit": "image", "seasons": "inferred",
            },
        },
    },
}


def call(req, gid=""):
    """The one billed call. Everything above this line is free."""
    try:
        import anthropic
    except ImportError:
        raise SystemExit("anthropic SDK not installed — `pip install anthropic`")

    check_spend_budget()
    client = anthropic.Anthropic()
    resp = client.messages.create(**req)

    usage = resp.usage
    searches = getattr(getattr(usage, "server_tool_use", None),
                       "web_search_requests", 0) or 0
    spent = (usage.input_tokens / 1e6 * PRICE_IN
             + usage.output_tokens / 1e6 * PRICE_OUT
             + searches * SEARCH_PRICE)
    # BEFORE the outcome checks below — a refusal is billed just the same.
    record_spend(spent, usage, searches, resp.stop_reason or "ok", gid)

    if resp.stop_reason == "refusal":
        raise SystemExit("model declined this request (billed and logged)")
    text = next((b.text for b in resp.content if b.type == "text"), "")
    if not text:
        raise SystemExit("no text block in the response (billed and logged)")
    try:
        parsed = json.loads(text)
    except ValueError:
        raise SystemExit("response was not valid JSON despite the schema:\n" + text[:500])
    parsed["_meta"] = {"model": MODEL, "spent_usd": round(spent, 4),
                       "web_searches": searches,
                       "input_tokens": usage.input_tokens,
                       "output_tokens": usage.output_tokens}
    return parsed


def render(result):
    ident = result.get("identification") or {}
    attrs = result.get("attributes") or {}
    prov = attrs.get("provenance") or {}
    out = []
    if ident.get("identified"):
        out.append("IDENTIFIED (%s confidence)" % ident.get("confidence", "?"))
        out.append("  %s — %s" % (ident.get("brand") or "?",
                                  ident.get("product_name") or "?"))
        if ident.get("product_url"):
            out.append("  %s" % ident["product_url"])
    else:
        out.append("NOT IDENTIFIED — attributes are from the image alone")
    out.append("  evidence: %s" % (ident.get("evidence") or "(none given)"))
    out.append("")
    out.append("  %-13s %-26s %s" % ("FIELD", "VALUE", "FROM"))
    for k in ("category", "subcategory", "formality", "warmth", "volume",
              "pattern", "fabric", "fit", "seasons"):
        v = attrs.get(k)
        v = ", ".join(v) if isinstance(v, list) else v
        out.append("  %-13s %-26s %s" % (k, v, prov.get(k, "?")))
    out.append("")
    out.append("  NOT FILLED, by design: colour (measured), price, purchase date, size")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--image", help="path to a photo")
    src.add_argument("--garment", help="existing garment id — uses its raw photo")
    ap.add_argument("--hint", default="",
                    help="anything she already knows (e.g. 'Aritzia, bought 2024')")
    ap.add_argument("--generate", action="store_true",
                    help="make the billed call (otherwise $0 dry run)")
    ap.add_argument("--stub", choices=sorted(STUBS),
                    help="$0: emit a canned result of that shape, for building "
                         "and reviewing the UI without a billed call")
    ap.add_argument("--out", help="write the JSON result here")
    args = ap.parse_args()

    if args.stub:
        result = dict(STUBS[args.stub])
        result["_meta"] = {"model": "stub", "spent_usd": 0.0, "web_searches": 0,
                           "input_tokens": 0, "output_tokens": 0}
        print(render(result))
        if args.out:
            Path(os.path.expanduser(args.out)).write_text(
                json.dumps(result, indent=2) + "\n")
            print("\nwrote %s" % args.out)
        return 0

    gid = args.garment or ""
    path = find_image(gid) if gid else Path(os.path.expanduser(args.image))
    if not path.is_file():
        raise SystemExit("no such image: %s" % path)

    req = build_request(path, args.hint)
    est = estimate(path)

    if not args.generate:
        print("DRY RUN — $0, nothing sent.\n")
        print("image      %s (%.0f KB)" % (path.name, path.stat().st_size / 1024))
        print("model      %s   effort=low" % MODEL)
        print("tools      web_search (max %d)" % MAX_SEARCHES)
        print("schema     %d attribute fields + per-field provenance"
              % len(SCHEMA["properties"]["attributes"]["properties"]))
        print("\nestimated cost")
        print("  tokens   ~%d in / ~%d out  = $%.4f"
              % (est["input_tokens"], est["output_tokens"], est["token_cost"]))
        print("  search   up to %d × $%.3f    = $%.4f"
              % (MAX_SEARCHES, SEARCH_PRICE, est["search_cost_max"]))
        print("  TOTAL    up to                $%.4f" % est["total_max"])
        print("\nre-run with --generate to make the billed call.")
        return 0

    result = call(req, gid)
    print(render(result))
    print("\nspent $%.4f (%d search%s) — logged to genlog"
          % (result["_meta"]["spent_usd"], result["_meta"]["web_searches"],
             "" if result["_meta"]["web_searches"] == 1 else "es"))
    if args.out:
        Path(os.path.expanduser(args.out)).write_text(json.dumps(result, indent=2) + "\n")
        print("wrote %s" % args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
