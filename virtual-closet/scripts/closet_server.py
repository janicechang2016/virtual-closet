#!/usr/bin/env python3
"""Virtual Closet local server. Zero dependencies (stdlib only).

Serves the app UI, repo assets, and a small JSON API:
  GET  /api/manifest      garments + looks + avatar + spend
  GET  /api/prompt?g=     try-on prompt for a garment (copy-paste mode)
  POST /api/feedback      {render, button, note} -> logs/feedback.jsonl
  POST /api/generate      REFUSED unless ENABLE_GENERATION=1 (credit guard)
  POST /api/looks         {title, items} -> save a draft look (free, looks.json)
  POST /api/looks/delete  {id} -> remove a look entry (render files stay on disk)
  POST /api/publish       {id, pose} -> render + cutout + publish (spend-gated)

Looks live in looks.json (draft -> published lifecycle); the carousel shows
published looks, the fitting room lists and manages all of them.

Run:  python3 scripts/closet_server.py   ->  http://localhost:8765
"""
import json
import os
import re
import subprocess
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


def hidden_stems():
    """renders/hidden.json: render stems kept out of the app (files stay on disk)."""
    try:
        return set(json.loads((ROOT / "renders" / "hidden.json").read_text()))
    except (OSError, ValueError):
        return set()


# pose-tagged render stems stay out of the fitting room (front pose only there);
# the carousel shows poses via each garment's cutout / the outfit list instead
POSE_TAGS = ("_contrapposto_", "_hand-on-hip_", "_34turn_")


def is_posed(stem):
    return any(t in f"{stem}_" for t in POSE_TAGS)


def garment_list():
    out = []
    hidden = hidden_stems()
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
                   if p.suffix.lower() in IMG_EXT and not p.stem.endswith("_raw")
                   and p.stem not in hidden and not is_posed(p.stem)]
        cuts = [p for p in sorted((ROOT / "renders" / "cutouts").glob(f"{folder.name}_*_cut.png"))
                if p.stem[:-len("_cut")] not in hidden]
        meta.update({"photos": photos, "renders": renders,
                     "cutout": f"/assets/renders/cutouts/{cuts[-1].name}" if cuts else None})
        out.append(meta)
    return out


LOOKS_PATH = ROOT / "looks.json"


def load_looks():
    try:
        return json.loads(LOOKS_PATH.read_text())
    except (OSError, ValueError):
        return []


def save_looks(looks):
    LOOKS_PATH.write_text(json.dumps(looks, indent=2) + "\n")


def looks_list():
    """looks.json entries with render/cutout resolved to asset URLs (or None)."""
    out = []
    for lk in load_looks():
        d = dict(lk)
        r = ROOT / "renders" / (lk.get("render") or "_")
        c = ROOT / "renders" / "cutouts" / (lk.get("cutout") or "_")
        d["render"] = f"/assets/renders/{r.name}" if r.is_file() else None
        d["cutout"] = f"/assets/renders/cutouts/{c.name}" if c.is_file() else None
        out.append(d)
    return out


def manifest():
    locked = ROOT / "avatar" / "avatar-v3" / "front.png"
    if locked.exists():
        avatar = {
            "draft": "/assets/avatar/avatar-v3/front.png",
            "locked_version": "avatar-v3",
            "status": "avatar-v3 canon 2026-07-14 (pose library in avatar/avatar-v3/; v1 renders legacy)",
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
        "looks": looks_list(),
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
        if url.path in ("/fitting-room", "/classic"):  # /classic kept as legacy alias
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
        if url.path == "/api/looks":
            items = [g for g in data.get("items", [])
                     if (ROOT / "garments" / g / "meta.json").is_file()]
            if not items:
                return self._json({"error": "a look needs at least one garment"}, 400)
            looks = load_looks()
            n = 1 + max([int(l["id"].rsplit("-", 1)[1]) for l in looks] + [0])
            lk = {"id": f"look-{n:03d}",
                  "title": (data.get("title") or "").strip() or f"look {n:03d}",
                  "items": items, "pose": None, "state": "draft",
                  "render": None, "cutout": None,
                  "created": datetime.now(timezone.utc).date().isoformat()}
            looks.append(lk)
            save_looks(looks)
            return self._json({"ok": True, "look": lk})
        if url.path == "/api/looks/delete":
            looks = load_looks()
            keep = [l for l in looks if l["id"] != data.get("id")]
            if len(keep) == len(looks):
                return self._json({"error": "unknown look"}, 404)
            save_looks(keep)   # render files stay on disk
            return self._json({"ok": True})
        if url.path == "/api/publish":
            if not GENERATION_ENABLED:
                return self._json({"error": "generation disabled",
                                   "detail": "Start the server with ENABLE_GENERATION=1 "
                                             "to allow fal spending."}, 403)
            looks = load_looks()
            lk = next((l for l in looks if l["id"] == data.get("id")), None)
            if not lk:
                return self._json({"error": "unknown look"}, 404)
            from tryon import tryon_outfit, POSES
            pose = data.get("pose", "front")
            if pose not in POSES:
                return self._json({"error": f"unknown pose (one of {', '.join(POSES)})"}, 400)
            try:
                out = tryon_outfit(lk["items"], pose=pose)
            except Exception as e:
                return self._json({"error": f"{type(e).__name__}: {e}"}, 500)
            lk.update({"state": "published", "pose": pose, "render": out.name})
            venv = Path("/Users/janice.chang/liminal-wardrobe/.venv/bin/python")
            if venv.exists():   # cutout pass (rembg lives in the liminal venv, not here)
                try:
                    subprocess.run([str(venv), str(ROOT / "scripts" / "cutout_render.py")],
                                   cwd=str(ROOT), capture_output=True, timeout=300)
                except Exception:
                    pass
            if (ROOT / "renders" / "cutouts" / f"{out.stem}_cut.png").is_file():
                lk["cutout"] = f"{out.stem}_cut.png"
            save_looks(looks)
            return self._json({"ok": True, "look": lk})
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
            # next free suffix among this garment's front v3 renders (poses live elsewhere)
            taken = [int(m.group(1)) for p in (ROOT / "renders").glob(f"{gid}_{arm}_v3_*.png")
                     if (m := re.fullmatch(rf"{re.escape(gid)}_{re.escape(arm)}_v3_(\d+)", p.stem))]
            n = 1 + max(taken + [0])
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
