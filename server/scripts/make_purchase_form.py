#!/usr/bin/env python3
"""Purchase capture as a browser form. $0, no API calls.

    python3 scripts/make_purchase_form.py     # -> scripts/purchase_form.html

Replaces the TSV workflow — same data, less friction. `garment.purchase` is {} for
all 58 and cannot be reconstructed later; it is the one input Track C (cost-per-wear)
is arithmetically impossible without. Approximate is fine.

Open via file://, fill, DOWNLOAD JSON, then: apply_purchase.py <file>.
Blank rows are skipped, so partial fills are safe and repeatable.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
CLOSET = os.path.normpath(os.path.join(HERE, "..", "..", "virtual-closet"))
GARMENTS = os.path.join(CLOSET, "garments")
OUT = os.path.join(HERE, "purchase_form.html")

CATEGORY_ORDER = ["top", "bottom", "dress", "outerwear", "shoes"]


def image_for(gid):
    base = os.path.join(GARMENTS, gid)
    clean = os.path.join(base, "clean")
    if os.path.isdir(clean):
        files = sorted(os.listdir(clean))
        pick = ([f for f in files if "_dragcut" in f]
                or [f for f in files if "_extracted" in f] or files)
        if pick:
            return f"../../virtual-closet/garments/{gid}/clean/{pick[0]}"
    raw = os.path.join(base, "raw")
    if os.path.isdir(raw):
        files = sorted(f for f in os.listdir(raw) if not f.startswith("."))
        if files:
            return f"../../virtual-closet/garments/{gid}/raw/{files[0]}"
    return ""


def collect():
    items = []
    for gid in sorted(os.listdir(GARMENTS)):
        d = os.path.join(GARMENTS, gid)
        if not os.path.isdir(d) or gid in ("raw", "archive"):
            continue
        mp = os.path.join(d, "meta.json")
        if not os.path.exists(mp):
            continue
        with open(mp) as fh:
            m = json.load(fh)
        items.append({
            "id": gid,
            "name": m.get("name", ""),
            "brand": m.get("brand", ""),
            "size": m.get("size_owned", ""),
            "category": m.get("category", ""),
            "img": image_for(gid),
        })
    items.sort(key=lambda i: (CATEGORY_ORDER.index(i["category"])
                              if i["category"] in CATEGORY_ORDER else 9, i["id"]))
    brands = sorted({i["brand"] for i in items if i["brand"]})
    return items, brands


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>the archive — purchase data</title>
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
  .legend {{ padding:14px 24px; border-bottom:1px solid var(--line);
             text-transform:uppercase; letter-spacing:.1em; font-size:10px; color:var(--dim); }}
  .catbar {{ padding:12px 24px; border-bottom:1px solid var(--line); background:#fafafa;
             text-transform:uppercase; letter-spacing:.16em; font-size:10px; }}
  table {{ width:100%; border-collapse:collapse; }}
  tr {{ border-bottom:1px solid var(--line); }}
  tr.filled {{ background:#fafafa; }}
  td {{ padding:10px 12px; vertical-align:middle; }}
  td.thumb {{ width:74px; }}
  td.thumb img {{ width:56px; height:70px; object-fit:contain; display:block; }}
  .gid {{ text-transform:uppercase; letter-spacing:.1em; font-size:9px; color:var(--dim); }}
  .nm {{ font-size:12px; }}
  .br {{ font-size:10px; color:var(--dim); text-transform:uppercase; letter-spacing:.1em; }}
  input {{ font:inherit; font-size:12px; padding:7px 8px; border:1px solid var(--line);
           background:var(--bg); border-radius:0; width:100%; }}
  td.price {{ width:130px; }} td.when {{ width:160px; }} td.src {{ width:210px; }}
  .prefix {{ display:flex; align-items:center; gap:4px; }}
  .prefix span {{ color:var(--dim); }}
  footer {{ padding:26px 24px 60px; }}
  .note {{ color:var(--dim); font-size:11px; max-width:64ch; }}
</style></head><body>
<header>
  <span class="wordmark">the archive.</span>
  <span class="meta">purchase data · phase 1</span>
  <span class="spacer"></span>
  <span class="meta" id="count">0 / {n} filled</span>
  <span class="meta" id="total">total —</span>
  <button id="fill">copy first row's date + source down</button>
  <button id="dl" class="primary">download json</button>
</header>
<div class="legend">
  approximate is fine — nearest ten, and a month is enough. any row left blank is skipped.
  this is the only input cost-per-wear can be built from, and it cannot be reconstructed later.
</div>
<div id="rows"></div>
<footer><p class="note">Nothing here writes to the database. Export with DOWNLOAD JSON,
then run <code>apply_purchase.py &lt;file&gt;</code>.</p></footer>
<datalist id="brands">{brands}</datalist>
<script>
const ITEMS = {data};
const host = document.getElementById('rows');

let html = '', lastCat = null;
for (const it of ITEMS) {{
  if (it.category !== lastCat) {{
    if (lastCat !== null) html += '</table>';
    html += `<div class="catbar">${{it.category}}</div><table>`;
    lastCat = it.category;
  }}
  html += `<tr id="row-${{it.id}}">
    <td class="thumb">${{it.img ? `<img src="${{it.img}}" alt="" loading="lazy">` : ''}}</td>
    <td><div class="gid">${{it.id}}</div><div class="nm">${{it.name}}</div>
        <div class="br">${{it.brand}} · ${{it.size || '—'}}</div></td>
    <td class="price"><div class="prefix"><span>$</span>
        <input type="number" min="0" step="1" inputmode="decimal"
               data-id="${{it.id}}" data-field="price_usd" placeholder="0"></div></td>
    <td class="when"><input type="month" data-id="${{it.id}}" data-field="purchased"></td>
    <td class="src"><input type="text" list="brands" data-id="${{it.id}}"
               data-field="source" placeholder="where from"></td>
  </tr>`;
}}
html += '</table>';
host.innerHTML = html;

const state = Object.fromEntries(ITEMS.map(i => [i.id, {{}}]));

function render() {{
  const filled = Object.values(state).filter(v =>
      v.price_usd || v.purchased || v.source).length;
  const total = Object.values(state).reduce((a, v) => a + (+v.price_usd || 0), 0);
  document.getElementById('count').textContent = `${{filled}} / ${{ITEMS.length}} filled`;
  document.getElementById('total').textContent =
      total ? `total $${{total.toLocaleString()}}` : 'total —';
}}

host.addEventListener('input', e => {{
  const id = e.target.dataset.id, field = e.target.dataset.field;
  if (!id || !field) return;
  const v = e.target.value.trim();
  if (v) state[id][field] = v; else delete state[id][field];
  const row = document.getElementById('row-' + id);
  row.classList.toggle('filled', Object.keys(state[id]).length > 0);
  render();
}});

// Most of a wardrobe is bought from a handful of places in a few bursts — copying
// the first filled row's date and source down saves the bulk of the typing.
document.getElementById('fill').onclick = () => {{
  const seed = ITEMS.find(i => state[i.id].purchased || state[i.id].source);
  if (!seed) return alert('Fill one row first, then copy it down.');
  const {{purchased, source}} = state[seed.id];
  for (const it of ITEMS) {{
    if (purchased && !state[it.id].purchased) {{
      state[it.id].purchased = purchased;
      document.querySelector(`input[data-id="${{it.id}}"][data-field="purchased"]`).value = purchased;
    }}
    if (source && !state[it.id].source) {{
      state[it.id].source = source;
      document.querySelector(`input[data-id="${{it.id}}"][data-field="source"]`).value = source;
    }}
    if (Object.keys(state[it.id]).length) document.getElementById('row-' + it.id).classList.add('filled');
  }}
  render();
}};

document.getElementById('dl').onclick = () => {{
  const purchases = {{}};
  for (const [id, v] of Object.entries(state)) {{
    if (!v.price_usd && !v.purchased && !v.source) continue;
    purchases[id] = v;
  }}
  const blob = new Blob([JSON.stringify({{generated: new Date().toISOString(), purchases}}, null, 2)],
                        {{type: 'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'purchases.json';
  a.click();
}};
render();
</script></body></html>
"""


def main():
    items, brands = collect()
    opts = "".join(f'<option value="{b}">' for b in brands)
    with open(OUT, "w") as fh:
        fh.write(HTML.format(n=len(items), data=json.dumps(items), brands=opts))
    print(f"{len(items)} garments -> {os.path.relpath(OUT)}")
    print(f"open: file://{OUT}")


if __name__ == "__main__":
    main()
