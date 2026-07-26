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
  POST /api/source/scan   {url} -> rank product images from an ecomm page ($0)
  GET  /api/source/img    ?i=   -> a scanned candidate's bytes (in-memory)
  POST /api/source/save   {picks, slug} -> write picks into garments/raw/
  GET  /api/source/staged        -> files staged in garments/raw/
  POST /api/source/discard{name} -> move a staged file to garments/raw/_discarded/
  GET  /stylist                  the stylist UI ($0, no generation)
  GET  /api/stylist/suggest      ?occasion=&n=  ranked outfits + one wildcard
  POST /api/stylist/feedback     {ids, verdict, blame} -> logs/stylist_feedback.jsonl

The /sourcing page is the UI over the /api/source/* routes (scan needs the
`requests` package; everything else stays stdlib).

Looks live in looks.json (draft -> published lifecycle); the carousel shows
published looks, the fitting room lists and manages all of them.

Run:  python3 scripts/closet_server.py   ->  http://localhost:8765
"""
import json
import os
import random
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
                  for p in sorted((folder / sub).glob("*"))
                  if p.suffix.lower() in IMG_EXT and not p.stem.endswith("_dragcut")]
        dragcut = folder / "clean" / f"{folder.name}_dragcut.png"
        renders = [f"/assets/renders/{p.name}" for p in sorted((ROOT / "renders").glob(f"{folder.name}_*"))
                   if p.suffix.lower() in IMG_EXT and not p.stem.endswith("_raw")
                   and p.stem not in hidden and not is_posed(p.stem)]
        cuts = [p for p in sorted((ROOT / "renders" / "cutouts").glob(f"{folder.name}_*_cut.png"))
                if p.stem[:-len("_cut")] not in hidden]
        meta.update({"photos": photos, "renders": renders,
                     "cutout": f"/assets/renders/cutouts/{cuts[-1].name}" if cuts else None,
                     "dragcut": (f"/assets/garments/{folder.name}/clean/{dragcut.name}"
                                 if dragcut.is_file() else None)})
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


def renumber_looks(looks):
    """Auto-titles follow carousel position: the nth published look is 'look 00n'.

    Both reorder and delete call this, so the two paths cannot drift apart —
    deleting used to leave a hole in the numbering (Janice 07-20: look 012)
    that the next drag would then silently close. Custom names survive, but
    still consume their slot number so the rest stay true to position. Drafts
    aren't in the carousel and are left alone.
    """
    n = 0
    for lk in looks:
        if lk.get("state") != "published":
            continue
        n += 1
        if re.match(r"^look \d+$", lk.get("title", "")):
            lk["title"] = "look %03d" % n
    return looks


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
        receive = ROOT / "avatar" / "avatar-v3" / "front-receive.png"
        avatar = {
            "draft": "/assets/avatar/avatar-v3/front.png",
            # UI-only reaction frame for drag-to-dress (never a render base)
            "receive": "/assets/avatar/avatar-v3/front-receive.png" if receive.is_file() else None,
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


# ── sourcing: the last scan's downloaded candidates, held in memory ──
SCAN = {"items": []}   # [{data, ctype, url, source, w, h}] per ingest_fetch ranking
RAW_DIR = ROOT / "garments" / "raw"


def source_scan(page_url):
    import ingest_fetch as ifetch   # lazy — the only route needing `requests`
    session = ifetch.requests.Session()
    cands, direct, title = ifetch.collect_candidates(session, page_url)
    if direct:
        data, ctype = direct
        w, h = ifetch.measure(data)
        ranked = [{"data": data, "ctype": ctype, "url": page_url,
                   "source": "direct", "w": w, "h": h}]
    else:
        if not cands:
            return {"error": "no image candidates found on the page (JS-only "
                             "gallery? paste the zoom-image URL directly)"}
        ranked = ifetch.rank_candidates(session, cands, 12)
        if not ranked:
            return {"error": "candidates found but none downloaded (site may "
                             "block non-browser fetches; save manually)"}
    SCAN["items"] = ranked
    return {"slug": ifetch.slug_from_title(title) or ifetch.slug_from_url(page_url),
            "candidates": [{"i": i, "w": r["w"], "h": r["h"],
                            "kb": len(r["data"]) // 1024,
                            "source": r["source"], "url": r["url"]}
                           for i, r in enumerate(ranked)]}


def source_staged():
    files = [p for p in RAW_DIR.glob("*")
             if p.is_file() and p.suffix.lower() in IMG_EXT | {".avif"}]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return {"files": [{"name": p.name, "kb": p.stat().st_size // 1024,
                       "url": f"/assets/garments/raw/{p.name}"} for p in files]}



# ---------------------------------------------------------------------------
# Stylist (Track B, v1). $0: no generation, no LLM, no network.
#
# Ranking is learned per-garment affinity, NOT colour harmony. Measured on 24
# outfits the model had never seen, colour scored AUC 0.491 (chance) while
# affinity from her published looks scored 0.824. Colour rides along as a
# tiebreak only.
#
# Negative feedback is used ONLY when attributed to a garment. An outfit-level
# "no" cannot be assigned blame, and including such rejections measurably made
# prediction worse (0.583) by penalising garments that were fine.
# ---------------------------------------------------------------------------
ENGINE_DIR = ROOT.parent / "server"
SNAPSHOT = ENGINE_DIR / "scripts" / "closet_snapshot.json"
STYLIST_LOG = ROOT / "logs" / "stylist_feedback.jsonl"


def _engine():
    if str(ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_DIR))
    from engine import gaps, preference  # noqa: E402
    return gaps, preference


def stylist_log_entries():
    """Every line in the log, oldest first. Malformed lines are skipped."""
    out = []
    if not STYLIST_LOG.exists():
        return out
    for line in STYLIST_LOG.read_text().splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def stylist_current():
    """Resolve the log to her CURRENT judgement per outfit, newest wins.

    The log stays append-only — changing your mind should not erase what you
    first thought, and a retraction is itself a fact worth keeping. Editing
    appends a new verdict for the same outfit; retracting appends a tombstone.
    Only the surviving verdict is fed to the model.
    """
    current = {}
    for e in stylist_log_entries():
        ids = e.get("ids") or []
        if not ids:
            continue
        sig = tuple(sorted(ids))
        if e.get("verdict") == "retracted":
            current.pop(sig, None)
        elif e.get("verdict") in ("yes", "no"):
            current[sig] = e
    return current


def stylist_feedback():
    """Current verdicts, shaped for engine.preference.

    A "yes" credits every garment in the outfit. A "no" penalises only the
    garment she blamed; an unattributed "no" is dropped rather than smeared.
    """
    out = []
    for e in stylist_current().values():
        if e.get("verdict") == "yes":
            out.append(({"ids": e.get("ids") or []}, "yes"))
        elif e.get("verdict") == "no" and e.get("blame"):
            out.append(({"ids": [e["blame"]]}, "no"))
    return out


def stylist_history(limit=24):
    """Her standing decisions, newest first, for the review panel."""
    rows = []
    for e in stylist_current().values():
        rows.append({
            "ids": e.get("ids") or [],
            "verdict": e.get("verdict"),
            "blame": e.get("blame"),
            "occasion": e.get("occasion") or "",
            "ts": e.get("ts"),
            "garments": [{"id": g, "img": _stylist_thumb(g)} for g in (e.get("ids") or [])],
        })
    rows.sort(key=lambda r: r["ts"] or "", reverse=True)
    return rows[:limit]


def _stylist_thumb(gid):
    """Cutout for a garment, as an /assets/ URL. Falls back to the raw photo."""
    clean = ROOT / "garments" / gid / "clean"
    if clean.is_dir():
        files = sorted(f.name for f in clean.iterdir() if f.is_file())
        pick = ([f for f in files if "_dragcut" in f]
                or [f for f in files if "_extracted" in f] or files)
        if pick:
            return "/assets/garments/%s/clean/%s" % (gid, pick[0])
    raw = ROOT / "garments" / gid / "raw"
    if raw.is_dir():
        files = sorted(f.name for f in raw.iterdir()
                       if f.is_file() and not f.name.startswith("."))
        if files:
            return "/assets/garments/%s/raw/%s" % (gid, files[0])
    return ""


def _judged_signatures():
    """Outfits with a standing judgement — not shown again until retracted."""
    return set(stylist_current().keys())


def stylist_suggest(occasion="", n=6):
    if not SNAPSHOT.exists():
        return {"error": "no closet snapshot - run server/scripts/dump_closet.py"}
    gaps, preference = _engine()
    data = json.loads(SNAPSHOT.read_text())
    garments, looks = data["garments"], data["outfits"]
    by_id = {g["id"]: g for g in garments}

    published = [o for o in looks if o.get("source") == "manual"]
    if occasion:
        matching = [o for o in published
                    if (o.get("context") or {}).get("occasion") == occasion]
        # Fall back to the whole history rather than to nothing: outside "day out"
        # there are only a handful of looks per occasion, and an affinity built on
        # one look is noise.
        prior = matching if len(matching) >= 4 else published
    else:
        prior = published

    aff = preference.affinity(garments, prior, stylist_feedback())
    ranked = gaps.ranked_outfits(garments, affinity=aff)

    # Rotate. Ranking is deterministic, so without this every "suggest again"
    # returned the identical six cards and the feedback loop could never be fed.
    # Sample from a high-scoring pool rather than the strict top: the top of the
    # list is not meaningfully better than the rest of that band, and showing
    # different clothes is worth more than a third decimal place of score.
    judged = _judged_signatures()
    ranked = [o for o in ranked if tuple(sorted(o["garment_ids"])) not in judged]
    pool_size = max(n * 6, int(len(ranked) * 0.15))
    pool = ranked[:pool_size]
    random.shuffle(pool)
    ranked = pool + ranked[pool_size:]

    worn = set()
    for o in published:
        worn.update(o.get("garment_ids") or [])

    # Diversify. Pure ranking returns six variations of one favourite top,
    # because affinity is a property of garments and the best garment wins every
    # slot. A suggestion list has to show different clothes, not different shoes.
    picks, used = [], {}
    for max_repeat in (1, 2, 3):
        for o in ranked:
            if len(picks) >= n:
                break
            if any(used.get(g, 0) >= max_repeat for g in o["garment_ids"]):
                continue
            picks.append(o)
            for g in o["garment_ids"]:
                used[g] = used.get(g, 0) + 1
        if len(picks) >= n:
            break

    # Wildcard: the best outfit built around something she has never worn.
    # Affinity alone would never surface these - unworn garments sit at neutral
    # and lose to her favourites forever, which makes the stylist a mirror.
    wildcard = None
    unworn_pool = [o for o in ranked[:pool_size * 3]
                   if any(g not in worn for g in o["garment_ids"])
                   and tuple(sorted(o["garment_ids"])) not in judged]
    if unworn_pool:
        # Work through the 23 unworn garments rather than re-offering one.
        # Anything already judged is exhausted evidence; prefer what has never
        # been put in front of her.
        judged_garments = set()
        for sig in judged:
            judged_garments.update(sig)
        by_garment = {}
        for o in unworn_pool:
            for g in o["garment_ids"]:
                if g not in worn:
                    by_garment.setdefault(g, []).append(o)
        fresh = [g for g in by_garment if g not in judged_garments]
        target = random.choice(fresh or list(by_garment))
        wildcard = dict(random.choice(by_garment[target]), wildcard=True)

    def decorate(o):
        out = dict(o)
        out["garments"] = [{
            "id": gid,
            "category": by_id[gid].get("category"),
            "subcategory": by_id[gid].get("subcategory"),
            "affinity": round(aff.get(gid, 0.5), 3),
            "unworn": gid not in worn,
            "img": _stylist_thumb(gid),
        } for gid in o["garment_ids"]]
        return out

    return {
        "occasion": occasion,
        "prior_looks": len(prior),
        "suggestions": [decorate(o) for o in picks],
        "wildcard": decorate(wildcard) if wildcard else None,
        "feedback_count": len(stylist_feedback()),
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
        ctype = "image/avif" if path.suffix.lower() == ".avif" else self.guess_type(str(path))
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
        if url.path == "/sourcing":
            return self._file(ROOT / "app" / "sourcing.html")
        if url.path == "/stylist":
            return self._file(ROOT / "app" / "stylist.html")
        if url.path == "/api/stylist/history":
            return self._json({"history": stylist_history()})
        if url.path == "/api/stylist/suggest":
            q = parse_qs(url.query)
            try:
                n = max(1, min(12, int(q.get("n", ["6"])[0])))
            except ValueError:
                n = 6
            return self._json(stylist_suggest(q.get("occasion", [""])[0], n))
        if url.path == "/api/source/img":
            try:
                item = SCAN["items"][int(parse_qs(url.query).get("i", ["-1"])[0])]
            except (ValueError, IndexError):
                return self._json({"error": "no such candidate (re-scan?)"}, 404)
            body = item["data"]
            self.send_response(200)
            self.send_header("Content-Type", item["ctype"])
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if url.path == "/api/source/staged":
            return self._json(source_staged())
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
        if url.path == "/api/stylist/retract":
            ids = data.get("ids") or []
            if not ids:
                return self._json({"error": "no ids"}, 400)
            entry = {"ts": datetime.now(timezone.utc).isoformat(),
                     "ids": ids, "verdict": "retracted"}
            STYLIST_LOG.parent.mkdir(exist_ok=True)
            with STYLIST_LOG.open("a") as f:
                f.write(json.dumps(entry) + "\n")
            return self._json({"ok": True, "count": len(stylist_feedback())})
        if url.path == "/api/stylist/feedback":
            entry = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "ids": data.get("ids") or [],
                "verdict": data.get("verdict"),
                "blame": data.get("blame") or None,
                "occasion": data.get("occasion") or "",
                "wildcard": bool(data.get("wildcard")),
            }
            STYLIST_LOG.parent.mkdir(exist_ok=True)
            with STYLIST_LOG.open("a") as f:
                f.write(json.dumps(entry) + "\n")
            return self._json({"ok": True, "count": len(stylist_feedback())})
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
            if data.get("renumber", True):
                renumber_looks(keep)
            save_looks(keep)   # render files stay on disk
            return self._json({"ok": True, "looks": looks_list()})
        if url.path == "/api/looks/reorder":
            # Carousel order IS looks.json array order (nothing sorts downstream),
            # so a drag in the index lens is a $0 rewrite of this list.
            order = [str(i) for i in data.get("order", [])]
            looks = load_looks()
            by = {l["id"]: l for l in looks}
            unknown = [i for i in order if i not in by]
            if unknown:
                return self._json({"error": f"unknown look(s): {', '.join(unknown)}"}, 404)
            if len(set(order)) != len(order):
                return self._json({"error": "duplicate ids in order"}, 400)
            moved = [by[i] for i in order]
            # Looks absent from the payload (drafts) hold their absolute slots;
            # only the dragged set is permuted among the slots it already owned.
            slots = [i for i, l in enumerate(looks) if l["id"] in set(order)]
            new = list(looks)
            for slot, lk in zip(slots, moved):
                new[slot] = lk
            if data.get("renumber", True):
                renumber_looks(new)
            save_looks(new)
            return self._json({"ok": True, "looks": looks_list()})
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
        if url.path == "/api/source/scan":
            if not (data.get("url") or "").startswith("http"):
                return self._json({"error": "paste an http(s) URL"}, 400)
            try:
                res = source_scan(data["url"])
            except ImportError:
                return self._json({"error": "the `requests` package is missing "
                                            "for this python"}, 500)
            except Exception as e:
                return self._json({"error": f"{type(e).__name__}: {e}"}, 500)
            return self._json(res, 400 if "error" in res else 200)
        if url.path == "/api/source/save":
            import ingest_fetch as ifetch
            slug = re.sub(r"[^a-z0-9-]+", "-", (data.get("slug") or "").lower()).strip("-")
            picks = data.get("picks") or []
            if not slug or not picks:
                return self._json({"error": "need a slug and at least one pick"}, 400)
            RAW_DIR.mkdir(parents=True, exist_ok=True)
            saved = []
            for n, i in enumerate(picks, 1):
                try:
                    r = SCAN["items"][int(i)]
                except (ValueError, IndexError):
                    return self._json({"error": "stale candidate — re-scan"}, 409)
                path = ifetch.save(r["data"], r["ctype"], r["url"], RAW_DIR, slug, n)
                name = Path(path).name
                saved.append({"name": name, "url": f"/assets/garments/raw/{name}"})
            return self._json({"ok": True, "saved": saved})
        if url.path == "/api/source/clear":
            SCAN["items"] = []
            return self._json({"ok": True})
        if url.path == "/api/source/discard":
            name = Path(data.get("name") or "").name   # basename only — no traversal
            target = RAW_DIR / name
            if not name or not target.is_file():
                return self._json({"error": "unknown staged file"}, 404)
            bin_dir = RAW_DIR / "_discarded"
            bin_dir.mkdir(exist_ok=True)
            dest, bump = bin_dir / name, 2
            while dest.exists():
                dest = bin_dir / f"{target.stem}-{bump}{target.suffix}"
                bump += 1
            target.rename(dest)
            return self._json({"ok": True})
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
