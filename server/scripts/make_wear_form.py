#!/usr/bin/env python3
"""Occasion backfill for wears already logged. $0, no API calls.

    python3 scripts/make_wear_form.py      # -> scripts/wear_form.html

WHY THIS EXISTS: migration 0006 adds occasion to `wear_log`, but the 15 wears
already logged have none, and Phase 6 is calendar-gated at ~50 wears. Waiting
for context means the next measurement runs on whatever has been logged since —
backfilling means it runs on everything. Her call 07-28: yes, occasion from
memory, weather fetched separately.

Scoped deliberately to OCCASION ONLY. The swap is not backfilled: "what did I
nearly wear on the 14th" is exactly the kind of recall people confabulate, and a
fabricated negative is worse than no negative. Weather is not asked either —
it comes from `worn_on` via weather_backfill.py at zero cost to her.

The weekday is printed next to every date because her own standing rule keys off
it ("weekday wears are work-from-home") and because a bare date two weeks old is
much harder to place than "Tuesday the 14th".

Open via file://, fill, DOWNLOAD JSON, then: apply_wear_context.py <file>.
"""
import json
import os
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
CLOSET = os.path.normpath(os.path.join(HERE, "..", "..", "virtual-closet"))
SNAPSHOT = os.path.join(HERE, "closet_snapshot.json")
OUT = os.path.join(HERE, "wear_form.html")

# (slug, label, hint) — slugs must match wear.OCCASIONS and the 0006 CHECK.
OCCASIONS = [
    ("work_home", "work — from home", "a working weekday, not going out"),
    ("work_out", "work — out", "into an office, a client, a work thing"),
    ("day_out", "day out", "errands, friends, walking around"),
    ("dinner", "dinner", "dinner out, drinks"),
    ("event", "event / formal", "the thing the dresses are for"),
    ("home", "home / lounge", "not working, not going out"),
]


def collect():
    with open(SNAPSHOT) as fh:
        snap = json.load(fh)

    outfits = {o["id"]: o for o in snap.get("outfits", [])}
    names, imgs = {}, {}
    gdir = os.path.join(CLOSET, "garments")
    # The snapshot carries attributes, not display names — `name` lives only in
    # each garment's meta.json, same as make_occasion_form.py reads it. Ids are a
    # poor recall aid two weeks after the fact, and recall is the whole task here.
    for g in snap.get("garments", []):
        names[g["id"]] = g["id"]
    if os.path.isdir(gdir):
        for gid in os.listdir(gdir):
            mp = os.path.join(gdir, gid, "meta.json")
            if os.path.exists(mp):
                with open(mp) as fh:
                    names[gid] = (json.load(fh).get("name") or gid)
            cut = os.path.join(gdir, gid, "clean", "%s_dragcut.png" % gid)
            if os.path.exists(cut):
                imgs[gid] = "../../virtual-closet/garments/%s/clean/%s_dragcut.png" % (gid, gid)

    rows = []
    for w in snap.get("wears", []):
        o = outfits.get(w.get("outfit_id")) or {}
        try:
            d = date.fromisoformat(w["worn_on"])
            weekday = d.strftime("%A")
            pretty = d.strftime("%a %-d %b")
        except (ValueError, KeyError):
            weekday, pretty = "", w.get("worn_on", "")
        rows.append({
            # `id` needs dump_closet.py at or past the 0006 refresh; without it
            # the row can still be matched on (outfit_id, worn_on).
            "wear_id": w.get("id"),
            "worn_on": w.get("worn_on"),
            "outfit_id": w.get("outfit_id"),
            "weekday": weekday,
            "pretty": pretty,
            "is_weekend": weekday in ("Saturday", "Sunday"),
            "occasion": w.get("occasion") or "",
            "items": [{"id": i, "name": names.get(i, i), "img": imgs.get(i, "")}
                      for i in (o.get("garment_ids") or [])],
        })
    rows.sort(key=lambda r: r["worn_on"] or "")
    return rows


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>the archive — wear occasions</title>
<style>
  :root {{ --line:#000; --bg:#fff; --dim:#8a8a8a; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:#000;
         font:13px/1.45 Helvetica,Arial,sans-serif; -webkit-font-smoothing:antialiased; }}
  header {{ position:sticky; top:0; z-index:10; background:var(--bg);
            border-bottom:1px solid var(--line); padding:18px 24px;
            display:flex; align-items:baseline; gap:24px; flex-wrap:wrap; }}
  .wordmark {{ font-style:italic; font-size:17px; }}
  .meta {{ text-transform:uppercase; letter-spacing:.14em; font-size:10px; color:var(--dim); }}
  .spacer {{ flex:1; }}
  button {{ font:inherit; text-transform:uppercase; letter-spacing:.14em; font-size:10px;
            background:var(--bg); border:1px solid var(--line); padding:9px 16px; cursor:pointer; }}
  button.primary {{ background:#000; color:#fff; }}
  button:hover {{ opacity:.7; }}
  .legend {{ padding:14px 24px; border-bottom:1px solid var(--line);
             font-size:11px; color:#444; max-width:78ch; }}
  .legend b {{ font-weight:600; color:#000; }}
  .row {{ border-bottom:1px solid var(--line); padding:16px 24px;
          display:grid; grid-template-columns:130px 1fr; gap:20px; align-items:start; }}
  .row.touched {{ background:#fafafa; }}
  .when .day {{ text-transform:uppercase; letter-spacing:.12em; font-size:10px; }}
  .when .dt {{ font-size:11px; color:var(--dim); margin-top:3px; }}
  .when .wk {{ font-size:9px; letter-spacing:.14em; text-transform:uppercase;
               color:var(--dim); margin-top:6px; border:1px solid #ddd;
               display:inline-block; padding:2px 6px; }}
  .fits {{ display:flex; gap:10px; align-items:flex-end; margin-bottom:10px; flex-wrap:wrap; }}
  .it {{ text-align:center; width:74px; }}
  .it img {{ height:60px; max-width:100%; object-fit:contain; display:block; margin:0 auto 4px; }}
  .it span {{ font-size:9px; color:var(--dim); line-height:1.25; display:block; }}
  .chips {{ display:flex; gap:6px; flex-wrap:wrap; }}
  .chip {{ border:1px solid var(--line); padding:7px 11px; cursor:pointer;
           text-transform:uppercase; letter-spacing:.1em; font-size:9.5px;
           background:var(--bg); user-select:none; }}
  .chip:hover {{ background:#f0f0f0; }}
  .chip.on {{ background:#000; color:#fff; }}
  .chip .hint {{ display:block; text-transform:none; letter-spacing:0;
                 font-size:9px; color:var(--dim); margin-top:2px; }}
  .chip.on .hint {{ color:#bbb; }}
  footer {{ padding:26px 24px 60px; }}
  .note {{ color:var(--dim); font-size:11px; max-width:70ch; }}
  @media (max-width:640px) {{ .row {{ grid-template-columns:1fr; gap:10px; }} }}
</style></head><body>
<header>
  <span class="wordmark">the archive.</span>
  <span class="meta">wear occasions · backfill</span>
  <span class="spacer"></span>
  <span class="meta" id="count">0 / {n} filled</span>
  <button id="dl" class="primary">download json</button>
</header>
<div class="legend">
  One tap per day. <b>Only answer where you actually remember</b> — a blank row is
  written as nothing, and no occasion is much better than a guessed one. Weather is
  not asked here; it is fetched from the date. The weekday is shown because your own
  rule keys off it: weekday wears are work-from-home.
</div>
<div id="rows"></div>
<footer><p class="note">Nothing here writes to the database. Export with DOWNLOAD JSON,
then run <code>apply_wear_context.py &lt;file&gt;</code>. Only rows you tapped are written.</p></footer>
<script>
const WEARS = {data};
const OCC = {occ};
const host = document.getElementById('rows');

host.innerHTML = WEARS.map((w, i) => `
  <div class="row" id="row-${{i}}">
    <div class="when">
      <div class="day">${{w.weekday || '—'}}</div>
      <div class="dt">${{w.pretty}}</div>
      ${{w.is_weekend ? '<div class="wk">weekend</div>' : ''}}
    </div>
    <div>
      <div class="fits">
        ${{w.items.map(it => `<div class="it">
            ${{it.img ? `<img src="${{it.img}}" alt="" loading="lazy">` : ''}}
            <span>${{it.name}}</span></div>`).join('')}}
      </div>
      <div class="chips">
        ${{OCC.map(o => `<div class="chip" data-i="${{i}}" data-slug="${{o[0]}}">
            ${{o[1]}}<span class="hint">${{o[2]}}</span></div>`).join('')}}
      </div>
    </div>
  </div>`).join('');

function paint() {{
  let n = 0;
  WEARS.forEach((w, i) => {{
    if (w.occasion) n++;
    document.getElementById('row-' + i).classList.toggle('touched', !!w.occasion);
  }});
  document.getElementById('count').textContent = n + ' / ' + WEARS.length + ' filled';
}}

host.addEventListener('click', e => {{
  const chip = e.target.closest('.chip');
  if (!chip) return;
  const i = +chip.dataset.i, slug = chip.dataset.slug;
  // Tapping the active chip clears it — a mis-tap must be undoable without a reload.
  WEARS[i].occasion = (WEARS[i].occasion === slug) ? '' : slug;
  document.querySelectorAll(`.chip[data-i="${{i}}"]`).forEach(c =>
    c.classList.toggle('on', c.dataset.slug === WEARS[i].occasion));
  paint();
}});

document.getElementById('dl').addEventListener('click', () => {{
  const wears = WEARS.filter(w => w.occasion).map(w => ({{
    wear_id: w.wear_id, outfit_id: w.outfit_id,
    worn_on: w.worn_on, occasion: w.occasion,
  }}));
  const blob = new Blob([JSON.stringify({{wears}}, null, 2)], {{type: 'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'wear_context.json';
  a.click();
}});

paint();
</script></body></html>
"""


def main():
    rows = collect()
    if not rows:
        print("no wears in the snapshot — run dump_closet.py first")
        return 1
    html = HTML.format(n=len(rows), data=json.dumps(rows),
                       occ=json.dumps([list(o) for o in OCCASIONS]))
    with open(OUT, "w") as fh:
        fh.write(html)
    missing_id = sum(1 for r in rows if not r["wear_id"])
    print("%d wear(s) -> %s" % (len(rows), os.path.relpath(OUT)))
    if missing_id:
        print("NOTE: %d row(s) have no wear_id — re-run dump_closet.py after "
              "migration 0006 so rows can be addressed directly." % missing_id)
    print("open with:  open %s" % os.path.relpath(OUT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
