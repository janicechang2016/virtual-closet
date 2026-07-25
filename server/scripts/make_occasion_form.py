#!/usr/bin/env python3
"""Occasion capture for the 18 published looks. $0, no API calls.

    python3 scripts/make_occasion_form.py     # -> scripts/occasion_form.html

The 18 looks are the cold-start preference prior. Without occasion they teach the
engine only "these items go together"; with it they teach "these go together FOR
dinner / for work" — which is the difference between plausible pairings and an
answer to the question actually asked. Nothing else in the closet supplies this.

Open via file://, fill, DOWNLOAD JSON, then: apply_occasions.py <file>.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CLOSET = os.path.normpath(os.path.join(HERE, "..", "..", "virtual-closet"))
OUT = os.path.join(HERE, "occasion_form.html")

OCCASIONS = ["", "work", "dinner", "day out", "event / formal", "travel",
             "home / lounge", "other"]
TIMES = ["", "day", "evening", "either"]


def collect():
    with open(os.path.join(CLOSET, "looks.json")) as fh:
        looks = json.load(fh)
    if isinstance(looks, dict):
        looks = looks.get("looks", [])

    names = {}
    gdir = os.path.join(CLOSET, "garments")
    for gid in os.listdir(gdir):
        mp = os.path.join(gdir, gid, "meta.json")
        if os.path.exists(mp):
            with open(mp) as fh:
                names[gid] = json.load(fh).get("name", gid)

    out = []
    for lk in looks:
        if lk.get("state") != "published":
            continue
        cut = lk.get("cutout") or ""
        img = ""
        if cut and os.path.exists(os.path.join(CLOSET, "renders", "cutouts", cut)):
            img = f"../../virtual-closet/renders/cutouts/{cut}"
        out.append({
            "id": lk.get("id"),
            "title": lk.get("title", ""),
            "items": [{"id": i, "name": names.get(i, i)} for i in lk.get("items", [])],
            "img": img,
            "occasion": "",
            "time": "",
            "venue": "",
        })
    return out


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>the archive — look occasions</title>
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
             text-transform:uppercase; letter-spacing:.1em; font-size:10px; color:var(--dim); }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); }}
  .card {{ border-right:1px solid var(--line); border-bottom:1px solid var(--line);
           padding:18px; display:flex; flex-direction:column; gap:12px; }}
  .card.touched {{ background:#fafafa; }}
  .fig {{ height:240px; display:flex; align-items:center; justify-content:center; }}
  .fig img {{ max-height:100%; max-width:100%; object-fit:contain; }}
  .ttl {{ text-transform:uppercase; letter-spacing:.12em; font-size:10px; }}
  .items {{ font-size:11px; color:#444; }}
  .items div {{ padding:1px 0; }}
  .row {{ display:flex; flex-direction:column; gap:5px; }}
  .row .lbl {{ text-transform:uppercase; letter-spacing:.14em; font-size:9px; color:var(--dim); }}
  select, input[type=text] {{ font:inherit; font-size:11px; width:100%; padding:7px 8px;
      border:1px solid var(--line); background:var(--bg); border-radius:0; }}
  footer {{ padding:26px 24px 60px; }}
  .note {{ color:var(--dim); font-size:11px; max-width:64ch; }}
</style></head><body>
<header>
  <span class="wordmark">the archive.</span>
  <span class="meta">look occasions · phase 1</span>
  <span class="spacer"></span>
  <span class="meta" id="count">0 / {n} filled</span>
  <button id="dl" class="primary">download json</button>
</header>
<div class="legend">
  these 18 looks are the cold-start prior — occasion is what turns them from
  “these go together” into “these go together for X”. venue is optional free text.
  leave any look blank to skip it.
</div>
<div class="grid" id="grid"></div>
<footer><p class="note">Nothing here writes to the database. Export with DOWNLOAD JSON,
then run <code>apply_occasions.py &lt;file&gt;</code>. Only looks with an occasion set
are written; blanks are left untouched.</p></footer>
<script>
const LOOKS = {data};
const OCC = {occ};
const TIMES = {times};
const grid = document.getElementById('grid');

const sel = (lk, field, opts) => `
  <div class="row"><span class="lbl">${{field}}</span>
    <select data-id="${{lk.id}}" data-field="${{field}}">
      ${{opts.map(o => `<option value="${{o}}">${{o || '—'}}</option>`).join('')}}
    </select></div>`;

grid.innerHTML = LOOKS.map(lk => `
  <div class="card" id="card-${{lk.id}}">
    <div class="fig">${{lk.img ? `<img src="${{lk.img}}" alt="" loading="lazy">` : ''}}</div>
    <div class="ttl">${{lk.title}} · ${{lk.id}}</div>
    <div class="items">${{lk.items.map(i => `<div>${{i.name}}</div>`).join('')}}</div>
    ${{sel(lk, 'occasion', OCC)}}
    ${{sel(lk, 'time', TIMES)}}
    <div class="row"><span class="lbl">venue / note</span>
      <input type="text" data-id="${{lk.id}}" data-field="venue" placeholder="optional"></div>
  </div>`).join('');

function render() {{
  const n = LOOKS.filter(l => l.occasion).length;
  document.getElementById('count').textContent = `${{n}} / ${{LOOKS.length}} filled`;
}}

grid.addEventListener('input', e => {{
  const id = e.target.dataset.id, field = e.target.dataset.field;
  if (!id || !field) return;
  const lk = LOOKS.find(x => x.id === id);
  lk[field] = e.target.value;
  document.getElementById('card-' + id).classList.toggle('touched', !!lk.occasion);
  render();
}});

document.getElementById('dl').onclick = () => {{
  const payload = {{
    generated: new Date().toISOString(),
    looks: Object.fromEntries(LOOKS.filter(l => l.occasion).map(l =>
      [l.id, {{occasion: l.occasion, time: l.time, venue: l.venue}}]))
  }};
  const blob = new Blob([JSON.stringify(payload, null, 2)], {{type:'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'occasions.json';
  a.click();
}};
render();
</script></body></html>
"""


def main():
    looks = collect()
    with open(OUT, "w") as fh:
        fh.write(HTML.format(n=len(looks), data=json.dumps(looks),
                             occ=json.dumps(OCCASIONS), times=json.dumps(TIMES)))
    print(f"{len(looks)} looks -> {os.path.relpath(OUT)}")
    print(f"open: file://{OUT}")


if __name__ == "__main__":
    main()
