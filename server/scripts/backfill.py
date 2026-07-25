#!/usr/bin/env python3
"""Phase 1 — build the backfill SQL from the existing file store. $0, no API calls.

    python3 scripts/backfill.py            # writes scripts/backfill.sql
    python3 scripts/backfill.py --report   # colour QA table, writes nothing

Reads virtual-closet/garments/*/meta.json + scripts/colors.json (produced by
extract_colors.py) and virtual-closet/looks.json. Emits ONE idempotent .sql file:

  * 58 garment rows — id is the existing slug, preserving render-id matching.
  * 18 published looks as outfit rows, source='manual' — the cold-start prior.

Stdlib only, runs on system python3 (3.9). Values are carried into Postgres as a
dollar-quoted JSON document expanded by jsonb_to_recordset, so nothing is
string-escaped by hand.

DELIBERATELY NOT SET HERE: formality, warmth, season_tags. Those are subjective,
they have no source in meta.json, and the standing rule is that she decides
aesthetics — they come from the confirmation grid. Re-running this script never
overwrites them.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLOSET = os.path.normpath(os.path.join(HERE, "..", "..", "virtual-closet"))
GARMENTS = os.path.join(CLOSET, "garments")
COLORS = os.path.join(HERE, "colors.json")
OVERRIDES = os.path.join(HERE, "color_overrides.json")
OUT_SQL = os.path.join(HERE, "backfill.sql")

RAW_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}


def garment_dirs():
    return [d for d in sorted(os.listdir(GARMENTS))
            if os.path.isdir(os.path.join(GARMENTS, d)) and d not in ("raw", "archive")]


def hidden_stems():
    p = os.path.join(CLOSET, "renders", "hidden.json")
    if not os.path.exists(p):
        return set()
    with open(p) as fh:
        data = json.load(fh)
    if isinstance(data, dict):
        data = data.get("hidden", data.get("stems", []))
    return set(data or [])


def render_index():
    """garment id -> its visible render filenames (drives asset_tier)."""
    rdir = os.path.join(CLOSET, "renders")
    if not os.path.isdir(rdir):
        return {}
    hidden = hidden_stems()
    out = {}
    for f in sorted(os.listdir(rdir)):
        if not f.lower().endswith(".png") or "_raw" in f:
            continue
        stem = os.path.splitext(f)[0]
        if stem in hidden or f in hidden:
            continue
        gid = re.split(r"_(?:nb2|nb-pro|idm-vton)", stem)[0]
        out.setdefault(gid, []).append(f)
    return out


def images_for(gid):
    """{raw:[...], clean:..., back:...} — paths relative to virtual-closet/."""
    base = os.path.join(GARMENTS, gid)
    imgs = {"raw": []}
    raw_dir = os.path.join(base, "raw")
    if os.path.isdir(raw_dir):
        for f in sorted(os.listdir(raw_dir)):
            if os.path.splitext(f)[1].lower() in RAW_EXTS:
                rel = os.path.join("garments", gid, "raw", f)
                imgs["raw"].append(rel)
                if "_back" in f.lower():
                    imgs["back"] = rel
    clean_dir = os.path.join(base, "clean")
    if os.path.isdir(clean_dir):
        files = sorted(os.listdir(clean_dir))
        pick = ([f for f in files if "_extracted" in f]
                or [f for f in files if "_dragcut" in f] or files)
        if pick:
            imgs["clean"] = os.path.join("garments", gid, "clean", pick[0])
    return imgs


def build_garments(colors):
    renders = render_index()
    rows, missing_colors = [], []
    for gid in garment_dirs():
        mp = os.path.join(GARMENTS, gid, "meta.json")
        if not os.path.exists(mp):
            continue
        with open(mp) as fh:
            m = json.load(fh)
        c = colors.get(gid, {})
        if not c.get("colors"):
            missing_colors.append(gid)
        rows.append({
            "id": gid,
            "category": m.get("category"),
            "subcategory": m.get("subcategory"),
            "colors": c.get("colors", []),
            "pattern": m.get("pattern"),
            "fabric": m.get("fabric"),
            "fit": m.get("fit"),
            "asset_tier": "render_ready" if renders.get(gid) else "catalog",
            "images": images_for(gid),
            "size_owned": m.get("size_owned"),
            "brand": m.get("brand"),
        })
    return rows, missing_colors


def build_outfits():
    with open(os.path.join(CLOSET, "looks.json")) as fh:
        looks = json.load(fh)
    if isinstance(looks, dict):
        looks = looks.get("looks", [])
    known = set(garment_dirs())
    rows, orphans = [], []
    for lk in looks:
        if lk.get("state") != "published":
            continue
        bad = [i for i in lk.get("items", []) if i not in known]
        if bad:
            orphans.append((lk.get("id"), bad))
        rows.append({
            "look_id": lk.get("id"),
            "garment_ids": lk.get("items", []),
            "context": {"look_id": lk.get("id"), "title": lk.get("title"),
                        "pose": lk.get("pose"), "created": lk.get("created"),
                        "render": lk.get("render"), "cutout": lk.get("cutout")},
            "rationale": None,
        })
    return rows, orphans


SQL_TEMPLATE = """-- Phase 1 backfill — GENERATED by scripts/backfill.py, do not hand-edit.
-- Idempotent: re-running refreshes objective fields and leaves formality/warmth/
-- season_tags untouched (those are the user's, set via the confirmation grid).
BEGIN;

-- Deterministic key so re-seeding the 18 looks updates instead of duplicating.
CREATE UNIQUE INDEX IF NOT EXISTS outfit_render_cache_key_uniq
    ON outfit (render_cache_key) WHERE render_cache_key IS NOT NULL;

INSERT INTO garment (id, category, subcategory, colors, pattern, fabric, fit,
                     asset_tier, images, size_owned, brand)
SELECT id, category, subcategory, colors, pattern, fabric, fit,
       asset_tier, images, size_owned, brand
FROM jsonb_to_recordset($garments${garments}$garments$::jsonb)
  AS x(id text, category text, subcategory text, colors jsonb, pattern text,
       fabric text, fit text, asset_tier text, images jsonb, size_owned text,
       brand text)
ON CONFLICT (id) DO UPDATE SET
    category    = EXCLUDED.category,
    colors      = EXCLUDED.colors,
    pattern     = EXCLUDED.pattern,
    fabric      = EXCLUDED.fabric,
    fit         = EXCLUDED.fit,
    asset_tier  = EXCLUDED.asset_tier,
    images      = EXCLUDED.images,
    size_owned  = EXCLUDED.size_owned,
    brand       = EXCLUDED.brand;
    -- USER-OWNED, never written here: formality, warmth, season_tags, volume,
    -- subcategory. meta.json has no source for any of them, so refreshing from
    -- it would silently blank confirmed answers — which is exactly what an
    -- earlier version of this statement did to subcategory.

INSERT INTO outfit (garment_ids, source, context, render_cache_key, rationale)
SELECT garment_ids, 'manual', context, look_id, rationale
FROM jsonb_to_recordset($outfits${outfits}$outfits$::jsonb)
  AS y(look_id text, garment_ids text[], context jsonb, rationale text)
-- The predicate must be repeated: ON CONFLICT can only infer a PARTIAL index when
-- the conflict target restates its WHERE clause.
ON CONFLICT (render_cache_key) WHERE render_cache_key IS NOT NULL DO UPDATE SET
    garment_ids = EXCLUDED.garment_ids,
    -- MERGE, never replace. Existing keys first so the refreshed mechanical
    -- values win, but user keys this statement knows nothing about (occasion,
    -- time, venue) survive. Replacing outright wiped them once already.
    context     = outfit.context || EXCLUDED.context;

COMMIT;
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", action="store_true",
                    help="print the colour QA table and exit without writing SQL")
    args = ap.parse_args()

    colors = {}
    if os.path.exists(COLORS):
        with open(COLORS) as fh:
            colors = json.load(fh)
    else:
        print("!! scripts/colors.json missing — run extract_colors.py first", file=sys.stderr)

    # User adjudications win over measurement, and survive re-measuring.
    if os.path.exists(OVERRIDES):
        with open(OVERRIDES) as fh:
            overrides = json.load(fh)
        applied = []
        for gid, ov in overrides.items():
            if gid.startswith("_") or gid not in colors:
                continue
            colors[gid] = dict(colors[gid], colors=ov["colors"], overridden=True,
                               verdict=ov.get("verdict", ""))
            applied.append(gid)
        if applied:
            print(f"colour overrides applied: {', '.join(applied)}")

    garments, missing_colors = build_garments(colors)
    outfits, orphans = build_outfits()

    if args.report:
        print(f"{'garment':34s} {'measured':46s} meta.color")
        print("-" * 110)
        for g in garments:
            meas = ", ".join(f"{c['name']} {c['coverage']:.0%}" for c in g["colors"]) or "—"
            meta_c = colors.get(g["id"], {}).get("meta_color", "")
            flag = "  <-- CHECK" if not _agrees(meas, meta_c) else ""
            print(f"{g['id']:34s} {meas:46s} {meta_c}{flag}")
        return 0

    sql = SQL_TEMPLATE.format(
        garments=json.dumps(garments, indent=1),
        outfits=json.dumps(outfits, indent=1),
    )
    with open(OUT_SQL, "w") as fh:
        fh.write(sql)

    print(f"garments: {len(garments)}   outfits: {len(outfits)}")
    print(f"render_ready: {sum(1 for g in garments if g['asset_tier'] == 'render_ready')}")
    if missing_colors:
        print(f"!! no colours for {len(missing_colors)}: {missing_colors}")
    if orphans:
        print(f"!! outfits referencing unknown garments: {orphans}")
    print(f"-> {os.path.relpath(OUT_SQL)}")
    return 0


def _agrees(measured, meta_color):
    """Loose containment check — just to surface rows worth a human glance."""
    if not meta_color:
        return True
    mwords = {w for w in re.split(r"[^a-z]+", measured.lower()) if len(w) > 2}
    cwords = {w for w in re.split(r"[^a-z]+", meta_color.lower()) if len(w) > 2}
    return bool(mwords & cwords)


if __name__ == "__main__":
    sys.exit(main())
