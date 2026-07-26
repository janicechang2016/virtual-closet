#!/usr/bin/env python3
"""Blind calibration set for outfit ranking. $0, offline, no API calls.

    python3 scripts/make_ranking_review.py     # -> scripts/ranking_review.html

The engine ranks her own 18 published looks at mean percentile 39 — below the
median outfit it would suggest. Before retuning anything, get her judgement on
outfits WITHOUT showing her the scores: seeing "0.900" first anchors the answer
and the calibration is then worth nothing.

The set mixes:
  * all 18 published looks — known-good ground truth, and the control
  * engine picks sampled evenly across the score range, top to bottom

Shuffled with a fixed seed, presented identically, scores hidden. Export gives
`would wear` / `would not` per outfit; analyse_ranking.py scores the engine
against it.
"""
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from engine import colour, constraints, gaps  # noqa: E402

CLOSET = os.path.normpath(os.path.join(HERE, "..", "..", "virtual-closet"))
GARMENTS = os.path.join(CLOSET, "garments")
SNAPSHOT = os.path.join(HERE, "closet_snapshot.json")
OUT = os.path.join(HERE, "ranking_review.html")

N_BANDS = 6          # sample evenly across the score range
PER_BAND = 4
SEED = 20260725      # fixed: the same set every regeneration, so answers persist


def thumb(gid):
    d = os.path.join(GARMENTS, gid, "clean")
    if os.path.isdir(d):
        files = sorted(os.listdir(d))
        pick = ([f for f in files if "_dragcut" in f]
                or [f for f in files if "_extracted" in f] or files)
        if pick:
            return "../../virtual-closet/garments/%s/clean/%s" % (gid, pick[0])
    d = os.path.join(GARMENTS, gid, "raw")
    if os.path.isdir(d):
        files = sorted(f for f in os.listdir(d) if not f.startswith("."))
        if files:
            return "../../virtual-closet/garments/%s/raw/%s" % (gid, files[0])
    return ""


def main():
    with open(SNAPSHOT) as fh:
        data = json.load(fh)
    G, O = data["garments"], data["outfits"]
    by_id = {g["id"]: g for g in G}

    ranked = gaps.ranked_outfits(G)
    scores = sorted(o["score"] for o in ranked)

    def pct(s):
        return 100.0 * sum(1 for x in scores if x < s) / len(scores)

    items, seen = [], set()

    # Her looks, scored the same way as everything else.
    for o in O:
        ids = [i for i in o["garment_ids"] if i in by_id]
        if not ids:
            continue
        combo = [by_id[i] for i in ids]
        h, worst = colour.outfit_harmony(combo)
        s, notes = constraints.score(combo, h)
        key = tuple(sorted(ids))
        seen.add(key)
        items.append({
            "key": "look:" + (o.get("render_cache_key") or ""),
            "ids": ids,
            "origin": "hers",
            "score": round(s, 4),
            "pct": round(pct(s)),
            "notes": notes,
            "occasion": (o.get("context") or {}).get("occasion") or "",
        })

    # Engine picks, evenly spread across the range rather than only the top —
    # a calibration set of nothing but 0.900s cannot tell agreement from luck.
    rng = random.Random(SEED)
    band = max(1, len(ranked) // N_BANDS)
    for b in range(N_BANDS):
        pool = [o for o in ranked[b * band:(b + 1) * band]
                if tuple(sorted(o["garment_ids"])) not in seen]
        rng.shuffle(pool)
        for o in pool[:PER_BAND]:
            key = tuple(sorted(o["garment_ids"]))
            if key in seen:
                continue
            seen.add(key)
            items.append({
                "key": "engine:" + "+".join(o["garment_ids"]),
                "ids": o["garment_ids"],
                "origin": "engine",
                "score": o["score"],
                "pct": round(pct(o["score"])),
                "notes": o["notes"],
                "occasion": "",
            })

    rng.shuffle(items)
    for it in items:
        it["garments"] = [{"id": i, "img": thumb(i),
                           "name": by_id[i].get("subcategory") or by_id[i]["category"]}
                          for i in it["ids"]]

    with open(OUT, "w") as fh:
        fh.write(HTML.format(n=len(items), data=json.dumps(items)))
    hers = sum(1 for i in items if i["origin"] == "hers")
    print("%d outfits (%d hers, %d engine) -> %s"
          % (len(items), hers, len(items) - hers, os.path.relpath(OUT)))
    print("open: file://%s" % OUT)
    return 0


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>the archive — ranking calibration</title>
<style>
  :root {{ --line:#000; --bg:#fff; --dim:#8a8a8a; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:#000;
         font:13px/1.45 Helvetica,Arial,sans-serif; -webkit-font-smoothing:antialiased; }}
  header {{ position:sticky; top:0; z-index:10; background:var(--bg);
            border-bottom:1px solid var(--line); padding:18px 24px;
            display:flex; align-items:baseline; gap:20px; flex-wrap:wrap; }}
  .wordmark {{ font-style:italic; font-size:17px; }}
  .meta {{ text-transform:uppercase; letter-spacing:.14em; font-size:10px; color:var(--dim); }}
  .spacer {{ flex:1; }}
  button {{ font:inherit; text-transform:uppercase; letter-spacing:.14em; font-size:10px;
            background:var(--bg); border:1px solid var(--line); padding:9px 16px; cursor:pointer; }}
  button.primary {{ background:#000; color:#fff; }}
  button:hover {{ opacity:.7; }}
  .legend {{ padding:14px 24px; border-bottom:1px solid var(--line); font-size:11px;
             color:var(--dim); max-width:none; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); }}
  .card {{ border-right:1px solid var(--line); border-bottom:1px solid var(--line);
           padding:18px; display:flex; flex-direction:column; gap:12px; }}
  .card.yes {{ background:#f6f6f6; }}
  .card.no {{ background:#fff; opacity:.55; }}
  .row {{ display:flex; gap:8px; align-items:flex-end; height:150px; }}
  .g {{ flex:1; display:flex; flex-direction:column; align-items:center; gap:4px; }}
  .g img {{ max-height:120px; max-width:100%; object-fit:contain; }}
  .g span {{ font-size:9px; color:var(--dim); text-transform:uppercase;
             letter-spacing:.08em; text-align:center; }}
  .ids {{ font-size:10px; color:var(--dim); }}
  .opts {{ display:flex; }}
  .opts label {{ flex:1; text-align:center; border:1px solid var(--line); margin-right:-1px;
                 padding:8px 0; cursor:pointer; font-size:11px; }}
  .opts input {{ position:absolute; opacity:0; pointer-events:none; }}
  .opts label:has(input:checked) {{ background:#000; color:#fff; }}
  footer {{ padding:26px 24px 60px; }}
  .note {{ color:var(--dim); font-size:11px; max-width:66ch; }}
</style></head><body>
<header>
  <span class="wordmark">the archive.</span>
  <span class="meta">ranking calibration · blind</span>
  <span class="spacer"></span>
  <span class="meta" id="count">0 / {n} judged</span>
  <button id="dl" class="primary">download json</button>
</header>
<div class="legend">
  Would you wear this? Not “is it valid” — whether you would actually put it on.
  <b>Scores are deliberately hidden</b>, and your own published looks are mixed in
  unlabelled, so the answers stay honest. Judge on the clothes, not the order.
</div>
<div class="grid" id="grid"></div>
<footer><p class="note">Nothing here writes to the database. Export with DOWNLOAD JSON,
then run <code>analyse_ranking.py &lt;file&gt;</code> — it measures the engine's ranking
against your answers and says which rule is wrong.</p></footer>
<script>
const ITEMS = {data};
const grid = document.getElementById('grid');
const state = {{}};

grid.innerHTML = ITEMS.map((it, n) => `
  <div class="card" id="c${{n}}">
    <div class="row">${{it.garments.map(g => `
      <div class="g">${{g.img ? `<img src="${{g.img}}" alt="" loading="lazy">` : ''}}
        <span>${{g.name}}</span></div>`).join('')}}</div>
    <div class="ids">${{it.ids.join(' · ')}}</div>
    <div class="opts">
      <label><input type="radio" name="r${{n}}" data-n="${{n}}" value="yes">would wear</label>
      <label><input type="radio" name="r${{n}}" data-n="${{n}}" value="no">would not</label>
    </div>
  </div>`).join('');

grid.addEventListener('change', e => {{
  const n = e.target.dataset.n;
  if (n === undefined) return;
  state[ITEMS[n].key] = e.target.value;
  const card = document.getElementById('c' + n);
  card.classList.toggle('yes', e.target.value === 'yes');
  card.classList.toggle('no', e.target.value === 'no');
  document.getElementById('count').textContent =
    `${{Object.keys(state).length}} / ${{ITEMS.length}} judged`;
}});

document.getElementById('dl').onclick = () => {{
  const payload = {{generated: new Date().toISOString(), verdicts: state,
    items: ITEMS.map(i => ({{key: i.key, ids: i.ids, origin: i.origin,
                            score: i.score, pct: i.pct}}))}};
  const blob = new Blob([JSON.stringify(payload, null, 2)], {{type:'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'ranking_verdicts.json'; a.click();
}};
</script></body></html>
"""


if __name__ == "__main__":
    sys.exit(main())
