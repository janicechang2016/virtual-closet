#!/usr/bin/env python3
"""Build the $0 confirmation grid for the subjective garment attributes.

    python3 scripts/make_attr_grid.py     # -> scripts/attr_grid.html

formality and warmth have no source in meta.json and are the user's call (standing
rule: she decides aesthetics). This generates a local, SYVE-styled page that
pre-fills a PROPOSAL for each garment from its own text — category, fabric, fit,
name — so the job is confirming rather than authoring 116 values from scratch.

Open the file directly (file://). It writes nothing; export with DOWNLOAD JSON and
hand the file to apply_attrs.py. Stdlib only. No API calls.
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
CLOSET = os.path.normpath(os.path.join(HERE, "..", "..", "virtual-closet"))
GARMENTS = os.path.join(CLOSET, "garments")
OUT = os.path.join(HERE, "attr_grid.html")

FORMALITY_SCALE = ["1 lounge", "2 casual", "3 smart casual", "4 dressy", "5 formal"]
WARMTH_SCALE = ["1 barely", "2 light", "3 mid", "4 warm", "5 very warm"]


def propose(meta):
    """Heuristic first guesses. Deliberately transparent and easy to override."""
    # `notes` is deliberately excluded: it describes the PHOTO, not the garment —
    # 04-structured-blazer's note "worn open over a white tee" matched "tee" and
    # classified a tailored blazer as casual.
    text = " ".join(str(meta.get(k, "")) for k in ("name", "fabric", "fit")).lower()
    cat = meta.get("category", "")

    def has(*words):
        return any(re.search(r"\b" + w, text) for w in words)

    if cat == "shoes":
        formality = (2 if has("sneaker", "trainer", "sandal", "flat") else
                     4 if has("heel", "pump") else
                     3 if has("loafer", "boot") else 3)
        warmth = 4 if has("boot") else 2
    else:
        formality = 3
        # "jersey" is a knit construction, not loungewear — it appears in slip
        # dresses and draped tops here, and reading it as lounge was wrong.
        if has("hoodie", "sweatshirt", "fleece", "sweatpant"):
            formality = 1
        elif has("tank", "tee", "t-shirt", "denim", "jean"):
            formality = 2
        elif has("silk", "satin", "blazer", "suiting", "tailored", "vest",
                 "slip", "pleated"):
            formality = 4
        if has("gown", "sequin"):
            formality = 5

        warmth = 2
        if has("sleeveless", "tank", "halter", "strapless", "camisole", "sheer",
               "mesh", "slip"):
            warmth = 1
        elif has("long sleeve", "long-sleeve", "knit", "wool", "sweater", "fleece"):
            warmth = 4
        elif has("coat", "jacket", "puffer", "parka"):
            warmth = 5
        if cat == "outerwear":
            warmth = max(warmth, 4)
    return formality, warmth


def image_for(gid):
    """Relative path from scripts/ to the best available thumbnail."""
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
    colors = {}
    cpath = os.path.join(HERE, "colors.json")
    if os.path.exists(cpath):
        with open(cpath) as fh:
            colors = json.load(fh)

    items = []
    for gid in sorted(os.listdir(GARMENTS)):
        d = os.path.join(GARMENTS, gid)
        if not os.path.isdir(d) or gid in ("raw", "archive"):
            continue
        mp = os.path.join(d, "meta.json")
        if not os.path.exists(mp):
            continue
        with open(mp) as fh:
            meta = json.load(fh)
        f, w = propose(meta)
        cols = colors.get(gid, {}).get("colors", [])
        items.append({
            "id": gid,
            "name": meta.get("name", ""),
            "category": meta.get("category", ""),
            "brand": meta.get("brand", ""),
            "size": meta.get("size_owned", ""),
            "fabric": (meta.get("fabric") or "")[:90],
            "img": image_for(gid),
            "swatches": [c["rgb"] for c in cols[:3]],
            "formality": f,
            "warmth": w,
        })
    return items


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>the archive — attribute confirmation</title>
<style>
  :root {{ --line:#000; --bg:#fff; --dim:#8a8a8a; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; background:var(--bg); color:#000;
         font:13px/1.45 Helvetica,Arial,sans-serif; -webkit-font-smoothing:antialiased; }}
  header {{ position:sticky; top:0; z-index:10; background:var(--bg);
            border-bottom:1px solid var(--line); padding:18px 24px;
            display:flex; align-items:baseline; gap:24px; flex-wrap:wrap; }}
  .wordmark {{ font-style:italic; font-size:17px; letter-spacing:.01em; }}
  .meta {{ text-transform:uppercase; letter-spacing:.14em; font-size:10px; color:var(--dim); }}
  .spacer {{ flex:1; }}
  button {{ font:inherit; text-transform:uppercase; letter-spacing:.14em; font-size:10px;
            background:var(--bg); border:1px solid var(--line); padding:9px 16px;
            cursor:pointer; }}
  button.primary {{ background:#000; color:#fff; }}
  button:hover {{ opacity:.7; }}
  .legend {{ padding:14px 24px; border-bottom:1px solid var(--line);
             text-transform:uppercase; letter-spacing:.1em; font-size:10px; color:var(--dim); }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(260px,1fr)); }}
  .card {{ border-right:1px solid var(--line); border-bottom:1px solid var(--line);
           padding:18px; display:flex; flex-direction:column; gap:12px; }}
  .card.touched {{ background:#fafafa; }}
  .fig {{ height:190px; display:flex; align-items:center; justify-content:center; }}
  .fig img {{ max-height:100%; max-width:100%; object-fit:contain; }}
  .gid {{ text-transform:uppercase; letter-spacing:.12em; font-size:10px; }}
  .nm {{ font-size:12px; }}
  .sub {{ font-size:10px; color:var(--dim); text-transform:uppercase; letter-spacing:.1em; }}
  .sw {{ display:flex; gap:4px; }}
  .sw i {{ width:14px; height:14px; border:1px solid #ddd; display:block; }}
  .row {{ display:flex; flex-direction:column; gap:5px; }}
  .row .lbl {{ text-transform:uppercase; letter-spacing:.14em; font-size:9px; color:var(--dim); }}
  .opts {{ display:flex; }}
  .opts label {{ flex:1; text-align:center; border:1px solid var(--line);
                 margin-right:-1px; padding:6px 0; cursor:pointer; font-size:11px; }}
  .opts input {{ position:absolute; opacity:0; pointer-events:none; }}
  .opts input:checked + span {{ display:block; background:#000; color:#fff;
                                margin:-6px 0; padding:6px 0; }}
  footer {{ padding:26px 24px 60px; }}
  .note {{ color:var(--dim); font-size:11px; max-width:60ch; }}
</style></head><body>
<header>
  <span class="wordmark">the archive.</span>
  <span class="meta">attribute confirmation · phase 1</span>
  <span class="spacer"></span>
  <span class="meta" id="count">0 / {n} touched</span>
  <button id="accept">accept all proposals</button>
  <button id="dl" class="primary">download json</button>
</header>
<div class="legend">
  formality 1 lounge · 2 casual · 3 smart casual · 4 dressy · 5 formal &nbsp;&nbsp;|&nbsp;&nbsp;
  warmth 1 barely · 2 light · 3 mid · 4 warm · 5 very warm &nbsp;&nbsp;|&nbsp;&nbsp;
  values shown are PROPOSALS derived from each garment's own text — override freely
</div>
<div class="grid" id="grid"></div>
<footer>
  <p class="note">Nothing here writes to the database. Export with DOWNLOAD JSON and
  hand the file to <code>apply_attrs.py</code>. Season tags are derived from warmth
  at apply time, so they are not asked for separately.</p>
</footer>
<script>
const ITEMS = {data};
const FORM = {form};
const WARM = {warm};
const touched = new Set();
const grid = document.getElementById('grid');

function scaleRow(item, field, scale) {{
  const opts = scale.map((s, i) => {{
    const v = i + 1, id = `${{item.id}}-${{field}}-${{v}}`;
    const on = item[field] === v ? 'checked' : '';
    return `<label for="${{id}}" title="${{s}}">
      <input type="radio" id="${{id}}" name="${{item.id}}-${{field}}" value="${{v}}" ${{on}}>
      <span>${{v}}</span></label>`;
  }}).join('');
  return `<div class="row"><span class="lbl">${{field}}</span>
          <div class="opts">${{opts}}</div></div>`;
}}

grid.innerHTML = ITEMS.map(it => `
  <div class="card" id="card-${{it.id}}">
    <div class="fig">${{it.img ? `<img src="${{it.img}}" alt="" loading="lazy">` : ''}}</div>
    <div>
      <div class="gid">${{it.id}}</div>
      <div class="nm">${{it.name}}</div>
      <div class="sub">${{it.category}} · ${{it.brand}} · ${{it.size || '—'}}</div>
    </div>
    <div class="sw">${{it.swatches.map(c =>
        `<i style="background:rgb(${{c.join(',')}})"></i>`).join('')}}</div>
    ${{scaleRow(it, 'formality', FORM)}}
    ${{scaleRow(it, 'warmth', WARM)}}
  </div>`).join('');

grid.addEventListener('change', e => {{
  const [id] = e.target.name.split(/-(formality|warmth)$/);
  const it = ITEMS.find(x => x.id === id);
  const field = e.target.name.endsWith('warmth') ? 'warmth' : 'formality';
  it[field] = +e.target.value;
  touched.add(id);
  document.getElementById('card-' + id).classList.add('touched');
  render();
}});

function render() {{
  document.getElementById('count').textContent = `${{touched.size}} / ${{ITEMS.length}} touched`;
}}

document.getElementById('accept').onclick = () => {{
  ITEMS.forEach(it => touched.add(it.id));
  document.querySelectorAll('.card').forEach(c => c.classList.add('touched'));
  render();
}};

document.getElementById('dl').onclick = () => {{
  const payload = {{
    generated: new Date().toISOString(),
    touched: [...touched],
    attributes: Object.fromEntries(ITEMS.map(it =>
      [it.id, {{formality: it.formality, warmth: it.warmth}}]))
  }};
  const blob = new Blob([JSON.stringify(payload, null, 2)], {{type: 'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'attributes.json';
  a.click();
}};
render();
</script></body></html>
"""


def main():
    items = collect()
    with open(OUT, "w") as fh:
        fh.write(HTML.format(
            n=len(items),
            data=json.dumps(items),
            form=json.dumps(FORMALITY_SCALE),
            warm=json.dumps(WARMTH_SCALE),
        ))
    print(f"{len(items)} garments -> {os.path.relpath(OUT)}")
    print(f"open: file://{OUT}")


if __name__ == "__main__":
    main()
