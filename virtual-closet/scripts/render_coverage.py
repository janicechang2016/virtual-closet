#!/usr/bin/env python3
"""Render-coverage audit. Mirrors closet_server.garment_list()'s visibility rules
exactly (hidden.json + is_posed + _raw), so 'visible' here means visible in the app."""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # virtual-closet/
IMG = {".png", ".jpg", ".jpeg", ".webp"}
POSES = ("contrapposto", "hand-on-hip", "34turn", "front")

hidden = set(json.loads((ROOT / "renders" / "hidden.json").read_text()))
# same rule as the server: a stem is "posed" if it carries a non-front pose tag
POSE_RE = re.compile(r"_(contrapposto|hand-on-hip|34turn)(_\d+)?$")


def is_posed(stem):
    return bool(POSE_RE.search(stem))


renders = [p for p in (ROOT / "renders").glob("*") if p.suffix.lower() in IMG]
cutouts = list((ROOT / "renders" / "cutouts").glob("*_cut.png"))

rows = []
for meta_path in sorted((ROOT / "garments").glob("*/meta.json")):
    meta = json.loads(meta_path.read_text())
    if meta.get("pending"):
        continue
    gid = meta_path.parent.name
    mine = [p for p in renders if p.name.startswith(gid + "_") and not p.stem.endswith("_raw")]
    visible = [p for p in mine if p.stem not in hidden and not is_posed(p.stem)]
    v3 = [p for p in visible if "_v3" in p.stem]
    posed = sorted({m.group(1) for p in mine if (m := POSE_RE.search(p.stem))
                    and p.stem not in hidden})
    cuts = [p for p in cutouts if p.name.startswith(gid + "_")
            and p.stem[:-4] not in hidden]
    drag = (meta_path.parent / "clean" / f"{gid}_dragcut.png").is_file()
    rows.append(dict(gid=gid, cat=meta.get("category", "?"), n_all=len(mine),
                     n_vis=len(visible), n_v3=len(v3), poses=posed,
                     n_cut=len(cuts), drag=drag,
                     diff=meta.get("difficulty"), tier=meta.get("asset_tier")))

print(f"GARMENTS: {len(rows)}\n")

def show(title, sel, extra=lambda r: ""):
    hits = [r for r in rows if sel(r)]
    print(f"--- {title}: {len(hits)}")
    for r in hits:
        print(f"    {r['gid']:<32} {r['cat']:<10} {extra(r)}")
    print()

show("NO visible render at all (invisible in fitting room)", lambda r: r["n_vis"] == 0,
     lambda r: f"all={r['n_all']} v3={r['n_v3']} cut={r['n_cut']}")
show("visible renders exist but NONE on avatar-v3 (legacy v1 lineage)",
     lambda r: r["n_vis"] > 0 and r["n_v3"] == 0, lambda r: f"vis={r['n_vis']}")
show("NO cutout (cannot appear in carousel/flat-lays)", lambda r: r["n_cut"] == 0,
     lambda r: f"vis={r['n_vis']}")
show("NO dragcut silhouette (flies as a framed card)", lambda r: not r["drag"])

print("--- pose coverage (archive-only; front is the fitting-room pose)")
for r in rows:
    if r["poses"]:
        print(f"    {r['gid']:<32} {', '.join(r['poses'])}")
n_posed = sum(1 for r in rows if r["poses"])
print(f"    => {n_posed}/{len(rows)} garments have any non-front pose render\n")

# ---- looks ----
looks = json.loads((ROOT / "looks.json").read_text())
pub = [l for l in looks if l.get("state") == "published"]
print(f"LOOKS: {len(looks)} total, {len(pub)} published")
missing_r = [l for l in looks if not l.get("render")
             or not (ROOT / "renders" / l["render"]).is_file()]
missing_c = [l for l in looks if not l.get("cutout")
             or not (ROOT / "renders" / "cutouts" / l["cutout"]).is_file()]
print(f"    looks missing a render file: {len(missing_r)}")
for l in missing_r:
    print(f"      {l['id']:<10} {l.get('state'):<10} {l.get('render')}")
print(f"    looks missing a cutout file: {len(missing_c)}")
for l in missing_c:
    print(f"      {l['id']:<10} {l.get('state'):<10} {l.get('cutout')}")

from collections import Counter
print("\n    pose distribution across published looks:",
      dict(Counter(l.get("pose") for l in pub)))

# garments never appearing in any published look
in_looks = {g for l in pub for g in l["items"]}
never = [r["gid"] for r in rows if r["gid"] not in in_looks]
print(f"\n    garments in NO published look: {len(never)}")
print("      " + ", ".join(never))
