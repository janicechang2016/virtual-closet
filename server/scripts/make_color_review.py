#!/usr/bin/env python3
"""Visual adjudication for colour-QA flags. $0, no API calls.

    python3 scripts/make_color_review.py          # flagged garments only
    python3 scripts/make_color_review.py --all    # the whole catalogue

The flags are a crude word-overlap test between the measured palette and the
`color` text in meta.json, so a flag means "worth a human glance", not "wrong".
Two very different failures hide behind one flag, and they have different fixes:

  * CONTAMINATED  — the mask caught background, shadow, or a neighbouring garment.
                    Fix: re-extract with different settings.
  * MISNAMED      — the measurement is right, the colour NAME is off (greige vs
                    sand). Fix: move a naming anchor. The LAB the engine consumes
                    was already correct, so this is cosmetic.

Swatches are rendered from the stored LAB so what you see is what is in Postgres.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLOSET = os.path.normpath(os.path.join(HERE, "..", "..", "virtual-closet"))
GARMENTS = os.path.join(CLOSET, "garments")
COLORS = os.path.join(HERE, "colors.json")
OUT = os.path.join(HERE, "color_review.html")

sys.path.insert(0, HERE)
from backfill import _agrees  # noqa: E402  (same flagging rule as the report)


def image_for(gid):
    base = os.path.join(GARMENTS, gid)
    for sub, tags in (("clean", ("_dragcut", "_extracted")), ("raw", ())):
        d = os.path.join(base, sub)
        if not os.path.isdir(d):
            continue
        files = sorted(f for f in os.listdir(d) if not f.startswith("."))
        pick = None
        for t in tags:
            pick = pick or next((f for f in files if t in f), None)
        pick = pick or (files[0] if files else None)
        if pick:
            return f"../../virtual-closet/garments/{gid}/{sub}/{pick}"
    return ""


def collect(show_all):
    with open(COLORS) as fh:
        colors = json.load(fh)
    items = []
    for gid, v in sorted(colors.items()):
        measured = ", ".join(f"{c['name']} {c['coverage']:.0%}" for c in v.get("colors", []))
        meta_color = v.get("meta_color") or ""
        flagged = not _agrees(measured, meta_color)
        if not (show_all or flagged):
            continue
        items.append({
            "id": gid,
            "meta_color": meta_color,
            "colors": v.get("colors", []),
            "source_kind": v.get("source_kind", ""),
            "photo": v.get("source_photo_type", ""),
            "img": image_for(gid),
            "flagged": flagged,
            "verdict": "",
            "correction": "",
        })
    return items


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>the archive — colour review</title>
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
             color:var(--dim); }}
  .legend b {{ color:#000; text-transform:uppercase; letter-spacing:.12em; font-size:10px; }}
  .item {{ display:flex; gap:24px; padding:22px 24px; border-bottom:1px solid var(--line);
           align-items:flex-start; flex-wrap:wrap; }}
  .item.done {{ background:#fafafa; }}
  .fig {{ width:190px; height:250px; display:flex; align-items:center;
          justify-content:center; border:1px solid #eee; flex:none; }}
  .fig img {{ max-width:100%; max-height:100%; object-fit:contain; }}
  .body {{ flex:1; min-width:320px; display:flex; flex-direction:column; gap:14px; }}
  .gid {{ text-transform:uppercase; letter-spacing:.12em; font-size:11px; }}
  .kv {{ font-size:11px; color:var(--dim); }}
  .kv b {{ color:#000; font-weight:normal; }}
  .chips {{ display:flex; gap:14px; flex-wrap:wrap; }}
  .chip {{ width:112px; }}
  .chip .sw {{ height:64px; border:1px solid var(--line); }}
  .chip .cn {{ font-size:11px; margin-top:5px; }}
  .chip .cd {{ font-size:9px; color:var(--dim); font-family:ui-monospace,Menlo,monospace; }}
  .verdicts {{ display:flex; gap:0; flex-wrap:wrap; }}
  .verdicts label {{ border:1px solid var(--line); margin-right:-1px; padding:8px 14px;
                     cursor:pointer; font-size:11px; }}
  .verdicts input {{ position:absolute; opacity:0; pointer-events:none; }}
  .verdicts input:checked + span {{ display:inline-block; }}
  .verdicts label:has(input:checked) {{ background:#000; color:#fff; }}
  input[type=text] {{ font:inherit; font-size:12px; padding:8px; width:100%; max-width:460px;
                      border:1px solid var(--line); border-radius:0; }}
  footer {{ padding:26px 24px 60px; }}
  .note {{ color:var(--dim); font-size:11px; max-width:66ch; }}
</style></head><body>
<header>
  <span class="wordmark">the archive.</span>
  <span class="meta">colour review · phase 1</span>
  <span class="spacer"></span>
  <span class="meta" id="count">0 / {n} judged</span>
  <button id="dl" class="primary">download json</button>
</header>
<div class="legend">
  Swatches are drawn from the LAB stored in Postgres — this is exactly what the engine sees.
  <br><b>correct</b> the palette matches the garment ·
  <b>misnamed</b> the colours are right, the words are wrong (cosmetic — LAB is already fine) ·
  <b>contaminated</b> the palette picked up background, shadow, or another garment (I re-extract)
</div>
<div id="list"></div>
<footer><p class="note">Nothing here writes to the database. Export with DOWNLOAD JSON —
or just tell me the verdicts in chat, there are only a handful.</p></footer>
<script>
const ITEMS = {data};
const list = document.getElementById('list');
const V = ['correct', 'misnamed', 'contaminated'];

list.innerHTML = ITEMS.map(it => `
  <div class="item" id="it-${{it.id}}">
    <div class="fig">${{it.img ? `<img src="${{it.img}}" alt="">` : ''}}</div>
    <div class="body">
      <div>
        <div class="gid">${{it.id}}</div>
        <div class="kv">your meta.color: <b>${{it.meta_color || '—'}}</b></div>
        <div class="kv">measured via ${{it.source_kind}} · source photo ${{it.photo || '—'}}</div>
      </div>
      <div class="chips">${{it.colors.map(c => `
        <div class="chip">
          <div class="sw" style="background:rgb(${{c.rgb.join(',')}})"></div>
          <div class="cn">${{c.name}} · ${{Math.round(c.coverage * 100)}}%</div>
          <div class="cd">L*${{c.lab[0].toFixed(1)}} a*${{c.lab[1].toFixed(1)}} b*${{c.lab[2].toFixed(1)}}</div>
        </div>`).join('')}}</div>
      <div class="verdicts">${{V.map(v => `
        <label><input type="radio" name="${{it.id}}-v" data-id="${{it.id}}"
                      data-field="verdict" value="${{v}}"><span>${{v}}</span></label>`).join('')}}</div>
      <input type="text" data-id="${{it.id}}" data-field="correction"
             placeholder="if not correct — what colour should it read as?">
    </div>
  </div>`).join('');

function render() {{
  const n = ITEMS.filter(i => i.verdict).length;
  document.getElementById('count').textContent = `${{n}} / ${{ITEMS.length}} judged`;
}}

list.addEventListener('input', e => {{
  const id = e.target.dataset.id, field = e.target.dataset.field;
  if (!id || !field) return;
  const it = ITEMS.find(x => x.id === id);
  it[field] = e.target.value;
  document.getElementById('it-' + id).classList.toggle('done', !!it.verdict);
  render();
}});

document.getElementById('dl').onclick = () => {{
  const payload = {{generated: new Date().toISOString(),
    verdicts: Object.fromEntries(ITEMS.filter(i => i.verdict).map(i =>
      [i.id, {{verdict: i.verdict, correction: i.correction}}]))}};
  const blob = new Blob([JSON.stringify(payload, null, 2)], {{type:'application/json'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob); a.download = 'color_verdicts.json'; a.click();
}};
render();
</script></body></html>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="review the whole catalogue")
    args = ap.parse_args()

    items = collect(args.all)
    with open(OUT, "w") as fh:
        fh.write(HTML.format(n=len(items), data=json.dumps(items)))
    print(f"{len(items)} garments -> {os.path.relpath(OUT)}")
    print(f"open: file://{OUT}")


if __name__ == "__main__":
    main()
