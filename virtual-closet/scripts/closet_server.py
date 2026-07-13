#!/usr/bin/env python3
"""Virtual Closet local server. Zero dependencies (stdlib only).

Serves the app UI, repo assets, and a small JSON API:
  GET  /api/manifest   garments + renders + avatar + spend
  GET  /api/prompt?g=  try-on prompt for a garment (copy-paste mode)
  POST /api/feedback   {render, button, note} -> logs/feedback.jsonl
  POST /api/generate   REFUSED unless ENABLE_GENERATION=1 (credit guard)

Run:  python3 scripts/closet_server.py   ->  http://localhost:8765
"""
import json
import os
import sys
from datetime import datetime, timezone
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from genlog import spend_summary

PORT = int(os.environ.get("CLOSET_PORT", "8765"))
GENERATION_ENABLED = os.environ.get("ENABLE_GENERATION") == "1"
IMG_EXT = {".png", ".jpg", ".jpeg", ".webp"}

TRYON_TEMPLATE = (
    "Dress the person from Image 1 (character reference — keep face, hair, body "
    "proportions identical; eyes dark brown nearly black; fair light East Asian "
    "complexion; clean unmarked skin, no tattoos) in the garment shown in Image 2. "
    "Reproduce the garment exactly: same color, pattern placement, neckline, sleeve "
    "length, buttons, and any text or logos. Natural fabric drape appropriate to "
    "{fabric}. Same light-gray studio background and soft even lighting as Image 1. "
    "Full-body, front-facing, one single figure."
)


def garment_list():
    out = []
    gdir = ROOT / "garments"
    for meta_path in sorted(gdir.glob("*/meta.json")):
        try:
            meta = json.loads(meta_path.read_text())
        except json.JSONDecodeError:
            continue
        folder = meta_path.parent
        photos = [f"/assets/garments/{folder.name}/{sub}/{p.name}"
                  for sub in ("clean", "raw")
                  for p in sorted((folder / sub).glob("*")) if p.suffix.lower() in IMG_EXT]
        renders = [f"/assets/renders/{p.name}" for p in sorted((ROOT / "renders").glob(f"{folder.name}_*"))
                   if p.suffix.lower() in IMG_EXT and not p.stem.endswith("_raw")]
        cuts = sorted((ROOT / "renders" / "cutouts").glob(f"{folder.name}_*_cut.png"))
        meta.update({"photos": photos, "renders": renders,
                     "cutout": f"/assets/renders/cutouts/{cuts[-1].name}" if cuts else None})
        out.append(meta)
    return out


def outfit_list():
    out = []
    for p in sorted((ROOT / "renders").glob("outfit_*.png")):
        if p.stem.endswith("_raw"):
            continue
        cut = ROOT / "renders" / "cutouts" / f"{p.stem}_cut.png"
        out.append({
            "id": p.stem,                       # e.g. outfit_01+02+04_1
            "items": p.stem.split("_")[1].split("+"),  # ["01","02","04"]
            "render": f"/assets/renders/{p.name}",
            "cutout": f"/assets/renders/cutouts/{cut.name}" if cut.exists() else None,
        })
    return out


def manifest():
    locked = ROOT / "avatar" / "avatar-v1" / "front.png"
    if locked.exists():
        avatar = {
            "draft": "/assets/avatar/avatar-v1/front.png",
            "locked_version": "avatar-v1",
            "status": "avatar-v1 locked 2026-07-13 (4-view sheet in avatar/avatar-v1/)",
        }
    else:
        # newest avatar-draft*.png is the working base
        drafts = sorted((ROOT / "avatar").glob("avatar-draft*.png"), key=lambda p: p.stat().st_mtime)
        draft = drafts[-1] if drafts else None
        avatar = {
            "draft": f"/assets/avatar/{draft.name}" if draft else None,
            "locked_version": None,
            "status": "draft — lock deferred (see docs/decisions.md)",
        }
    return {
        "avatar": avatar,
        "garments": garment_list(),
        "outfits": outfit_list(),
        "spend": spend_summary(),
        "generation_enabled": GENERATION_ENABLED,
    }


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep the terminal quiet

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _file(self, path: Path):
        if not path.is_file():
            self.send_error(404)
            return
        ctype = self.guess_type(str(path))
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/" or url.path == "/index.html":
            carousel = ROOT / "app" / "carousel.html"
            return self._file(carousel if carousel.exists() else ROOT / "app" / "index.html")
        if url.path == "/classic":
            return self._file(ROOT / "app" / "index.html")
        if url.path.startswith("/app/"):
            return self._file((ROOT / url.path.lstrip("/")).resolve())
        if url.path == "/api/manifest":
            return self._json(manifest())
        if url.path == "/api/prompt":
            gid = parse_qs(url.query).get("g", [""])[0]
            meta_path = ROOT / "garments" / gid / "meta.json"
            if not meta_path.is_file():
                return self._json({"error": "unknown garment"}, 404)
            meta = json.loads(meta_path.read_text())
            prompt = TRYON_TEMPLATE.format(fabric=meta.get("fabric") or "the garment's fabric")
            if meta.get("details_to_preserve"):
                prompt += " Pay particular attention to: " + ", ".join(meta["details_to_preserve"]) + "."
            if sorted((ROOT / "garments" / gid / "clean").glob("*_onwhite.png")):
                prompt += (" Image 2 is a garment cutout extracted from a worn photo; any small "
                           "gaps, notches, or ragged edges are extraction artifacts, not part of "
                           "the design - render the garment complete and intact.")
            return self._json({"prompt": prompt, "garment": gid})
        if url.path.startswith("/assets/"):
            target = (ROOT / url.path[len("/assets/"):]).resolve()
            if ROOT not in target.parents:
                self.send_error(403)
                return
            return self._file(target)
        self.send_error(404)

    def do_POST(self):
        url = urlparse(self.path)
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length) or b"{}")
        if url.path == "/api/feedback":
            entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "render": data.get("render"),
                "garment": data.get("garment"),
                "button": data.get("button"),
                "note": data.get("note", ""),
            }
            fb = ROOT / "logs" / "feedback.jsonl"
            with fb.open("a") as f:
                f.write(json.dumps(entry) + "\n")
            result = {"ok": True}
            # live mode: one tap = one targeted corrective edit (plan §Phase 4)
            if data.get("regenerate") and GENERATION_ENABLED and data.get("garment"):
                try:
                    from tryon import correct
                    out = correct(data["garment"], data.get("button", ""),
                                  data.get("note", ""), render=data.get("render"))
                    result["render"] = f"/assets/renders/{out.name}"
                except Exception as e:
                    result["error"] = f"{type(e).__name__}: {e}"
            return self._json(result)
        if url.path == "/api/generate":
            if not GENERATION_ENABLED:
                return self._json({
                    "error": "generation disabled",
                    "detail": "Credit guard is on. Start the server with ENABLE_GENERATION=1 "
                              "to allow fal spending, or use Copy Prompt mode.",
                }, 403)
            if data.get("outfit"):
                try:
                    from tryon import tryon_outfit
                    out = tryon_outfit(data["outfit"])
                    return self._json({"ok": True, "render": f"/assets/renders/{out.name}"})
                except Exception as e:
                    return self._json({"error": f"{type(e).__name__}: {e}"}, 500)
            gid = data.get("garment")
            if not gid or not (ROOT / "garments" / gid / "meta.json").is_file():
                return self._json({"error": "unknown garment"}, 404)
            arm = data.get("arm", os.environ.get("TRYON_ARM", "nb2"))  # Phase 3 winner
            n = 1 + len([p for p in (ROOT / "renders").glob(f"{gid}_{arm}_v1_*.png")
                         if not p.stem.endswith("_raw")])
            try:
                from tryon import tryon as run_tryon
                out = run_tryon(gid, arm, suffix=str(n))
                return self._json({"ok": True, "render": f"/assets/renders/{out.name}"})
            except Exception as e:
                return self._json({"error": f"{type(e).__name__}: {e}"}, 500)
        self.send_error(404)


if __name__ == "__main__":
    print(f"Virtual Closet → http://localhost:{PORT}")
    print(f"Generation: {'ENABLED — fal spending live' if GENERATION_ENABLED else 'disabled (credit guard on)'}")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
