#!/usr/bin/env python3
"""Static export: the archive as a read-only demo. $0, stdlib only.

Snapshots /api/manifest (generation off, `demo: true` — the flag the app UIs
key off to hide write actions), then copies the app shell and every asset the
manifest references into an output dir ready for any static host. Routing
(/, /fitting-room, /api/manifest) lives in vercel.json at the repo root;
Vercel runs this script as its build command.

Run:  python3 scripts/export_static.py [--out ../site]
"""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # virtual-closet/
sys.path.insert(0, str(Path(__file__).resolve().parent))
import closet_server

# sourcing.html stays out: its scan/save routes need the live local server
APP_FILES = ["carousel.html", "index.html", "app.js", "nav.js", "style.css",
             "entrance-bg.jpg", "stylist.html", "insights.html", "galaxy.html",
             "unlock.js", "wear.html"]

# How deep a ranked pool the browser gets. The live stylist shuffles the top
# max(n*6, 15% of ranked) ~= 333 and scans 3x that for a wildcard, so 1200
# reproduces both without shipping all 2220.
POOL_DEPTH = 1200


def asset_urls(node, found):
    """Collect every /assets/... string reachable in the manifest JSON."""
    if isinstance(node, str):
        if node.startswith("/assets/"):
            found.add(node)
    elif isinstance(node, list):
        for v in node:
            asset_urls(v, found)
    elif isinstance(node, dict):
        for v in node.values():
            asset_urls(v, found)


def stylist_pool(limit=POOL_DEPTH):
    """Everything /stylist needs to rank and re-roll in the browser.

    The RANKING is deterministic — the same closet and the same evidence always
    produce the same ordering — so it is computed here once and shipped as data.
    Only the parts that must vary per visit run client-side: the pool shuffle,
    the diversification pass and the wildcard draw. That is why the static
    stylist still re-rolls rather than being a screenshot of one set of cards,
    and why none of `server/engine/` had to be rewritten in JavaScript.

    Feedback is empty by construction here: the export has no log to read and no
    route to write one, so affinity rests on her published looks alone.
    """
    gaps, preference = closet_server._engine()
    data = json.loads(closet_server.SNAPSHOT.read_text())
    garments, looks = data["garments"], data["outfits"]
    by_id = {g["id"]: g for g in garments}
    # MEASURED 07-27 and reverted: 'worn' rows are NOT prior evidence. Held out
    # against the 15 logged wears (leave-one-out, per-fold AUC), adding them made
    # prediction WORSE — 0.660 -> 0.540 against the whole outfit space, and
    # 0.555 -> 0.383 once garment rotation is controlled for. Wear FREQUENCY is
    # not preference: she wears jeans and yello-heels constantly because they are
    # defaults, so a per-garment counter just ranks by frequency, and the boosted
    # garments sit in the negatives too. Same failure as rejections; this is the
    # sibling of preference.NEGATIVE_WEIGHT = 0.0. Wears TRAINED ALONE score about
    # the same as published-only (0.622/0.549) — it is COMBINING them that hurts.
    # Revisit at ~50 wears; repro in CLAUDE.md.
    PRIOR = ("manual",)
    published = [o for o in looks if o.get("source") in PRIOR]

    worn = set()
    for o in published:
        worn.update(o.get("garment_ids") or [])

    names = closet_server._garment_names()
    # same disambiguation the live route does: three garments are called
    # "scoop tank", so an un-prefixed rationale would name two pieces alike
    from collections import Counter
    dupes = {n for n, k in Counter(names.values()).items() if k > 1}
    for gid, nm in list(names.items()):
        if nm in dupes:
            cols = (by_id.get(gid) or {}).get("colors") or []
            if cols:
                names[gid] = "%s %s" % (cols[0].get("name", ""), nm)

    order = [g["id"] for g in garments]
    index = {gid: i for i, gid in enumerate(order)}

    table = []
    for gid in order:
        meta = {}
        mp = ROOT / "garments" / gid / "meta.json"
        if mp.is_file():
            try:
                meta = json.loads(mp.read_text())
            except ValueError:
                pass
        url, is_cutout = closet_server._stylist_thumb(gid)
        table.append({
            "id": gid,
            "name": names.get(gid, gid),
            "category": by_id[gid].get("category"),
            "subcategory": by_id[gid].get("subcategory"),
            "img": url,
            "framed": not is_cutout,
            "scale": closet_server._draw_scale(meta, by_id[gid].get("category")),
            "unworn": gid not in worn,
        })

    occasions = sorted({(o.get("context") or {}).get("occasion")
                        for o in published if (o.get("context") or {}).get("occasion")})

    out = {}
    for occ in [""] + occasions:
        if occ:
            matching = [o for o in published
                        if (o.get("context") or {}).get("occasion") == occ]
            # same rule as the live route: an affinity built on one look is noise
            prior = matching if len(matching) >= 4 else published
        else:
            prior = published
        aff = preference.affinity(garments, prior, ())
        full = gaps.ranked_outfits(garments, affinity=aff)
        ranked = full[:limit]
        out[occ] = {
            "prior_looks": len(prior),
            # the UNTRUNCATED count: the browser sizes its shuffle pool from
            # 15% of it, so shipping only the truncated length would quietly
            # narrow the rotation
            "total": len(full),
            # aligned to `garments` so it costs one number per garment, not a key
            "affinity": [round(aff.get(gid, 0.5), 4) for gid in order],
            "ranked": [
                ([index[g] for g in o["garment_ids"]], o.get("notes") or [])
                for o in ranked
            ],
        }

    idle = sum(float((by_id[gid].get("purchase") or {}).get("price_usd") or 0)
               for gid in order if gid not in worn)

    return {
        "pool": True,
        "garments": table,
        "occasions": out,
        "state": {
            "garments": len(garments),
            "unworn": sum(1 for gid in order if gid not in worn),
            "idle_usd": round(idle),
            "judgements": 0,
            "looks": len(published),
        },
    }


def _build_stamp():
    """Commit and timestamp of the tree being exported. Never fails the build —
    a missing git (as on some CI images) degrades to 'unknown'."""
    import subprocess
    from datetime import datetime, timezone

    def git(*args):
        try:
            return subprocess.run(("git",) + args, cwd=str(ROOT), capture_output=True,
                                  text=True, timeout=10).stdout.strip() or None
        except Exception:
            return None

    return {
        "commit": git("rev-parse", "--short", "HEAD") or "unknown",
        "branch": (git("rev-parse", "--abbrev-ref", "HEAD")
                   or os.environ.get("VERCEL_GIT_COMMIT_REF") or "unknown"),
        "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT.parent / "site"))
    args = ap.parse_args()
    out = Path(args.out).resolve()
    if out.exists():
        shutil.rmtree(out)

    m = closet_server.manifest()
    m["generation_enabled"] = False
    m["demo"] = True
    # Stamp the build. Twice this session a deploy looked wrong and the only way
    # to tell WHICH commit was live was hashing files against every branch. The
    # manifest is already fetched by every page, so this makes it one request:
    #   curl -s <site>/api/manifest | python3 -c "import json,sys;print(json.load(sys.stdin)['build'])"
    m["build"] = _build_stamp()

    (out / "api").mkdir(parents=True)
    (out / "api" / "manifest.json").write_text(json.dumps(m, indent=1) + "\n")

    # The read-only routes the other three pages fetch. /insights and /galaxy get
    # byte-identical payloads to the live ones, so those pages need no static
    # branch at all; /stylist gets a ranked pool instead of one set of cards,
    # which its own loader recognises by the `pool` flag.
    pool = stylist_pool()      # computed once; both payloads below read from it
    payloads = {
        "api/insights.json": closet_server.insights_data(),
        "api/galaxy.json": closet_server.galaxy_data(),
        "api/stylist/suggest.json": pool,
        # /wear needs only the cutouts and their names. The pool already carries a
        # garment table, but it is 163 KB of ranked outfits alongside — far too
        # much to make a phone download before it can log getting dressed.
        "api/garments.json": {"garments": [
            {"id": g["id"], "name": g["name"], "img": g["img"],
             "category": g["category"]}
            for g in pool["garments"]
        ]},
    }
    for rel, payload in payloads.items():
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(json.dumps(payload))
        print(f"{rel}: {dst.stat().st_size / 1e3:.0f} KB")

    (out / "app").mkdir()
    for name in APP_FILES:
        shutil.copy2(ROOT / "app" / name, out / "app" / name)

    found = set()
    asset_urls(m, found)
    # the stylist's cutouts and the galaxy's thumbnails live only in these
    # payloads — collect them too or every garment image 404s
    for payload in payloads.values():
        asset_urls(payload, found)
    copied, total, missing = 0, 0, []
    for url in sorted(found):
        src = ROOT / url[len("/assets/"):]
        if not src.is_file():
            missing.append(url)
            continue
        dst = out / "assets" / url[len("/assets/"):]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
        total += src.stat().st_size

    print(f"site -> {out}")
    print(f"assets: {copied} files, {total / 1e6:.1f} MB")
    if missing:
        print("MISSING — manifest points at files that don't exist:")
        for u in missing:
            print("  " + u)
        sys.exit(1)


if __name__ == "__main__":
    main()
