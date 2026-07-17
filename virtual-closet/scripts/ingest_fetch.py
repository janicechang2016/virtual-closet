"""Pull the best product image(s) from an ecomm page into garments/raw/.

Give it a product-page URL; it collects every image the page declares
(og:image, JSON-LD Product images, <img>/srcset variants), downloads the
plausible candidates, ranks them by real pixel size, and saves the winner
as garments/raw/<slug>.<ext>. Works for any closet category — clothing,
shoes, accessories. $0, no fal calls.

Run on the liminal-wardrobe venv (PIL there reads webp/avif; system
python3 falls back to ranking by file size):

    /Users/janice.chang/liminal-wardrobe/.venv/bin/python scripts/ingest_fetch.py URL [SLUG]

    --list        rank and print candidates, save nothing
    --pick N[,M]  save candidate(s) N from the ranking (1-based)
    --keep N      save the top N candidates (default 1; use 2-3 to keep
                  a back/detail view alongside the front)
    --dest DIR    save directory (default garments/raw/)
    --max N       candidates to download for ranking (default 12)

Direct image URLs are saved as-is. Existing files are never overwritten
(a -2/-3 suffix is added). A warning prints when the best asset is under
1000px on its long side — that's thumbnail-grade; find the zoom asset.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qsl, urlencode, urlunparse

import requests

try:
    from PIL import Image
except ImportError:
    Image = None

ROOT = Path(__file__).resolve().parent.parent
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15")
HEADERS = {"User-Agent": UA,
           "Accept": "text/html,image/jpeg,image/png;q=0.9,image/webp;q=0.8,*/*;q=0.5",
           "Accept-Language": "en-US,en;q=0.9"}
TIMEOUT = 20

IMG_EXT = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
           "image/avif": ".avif", "image/gif": ".gif"}
JUNK = re.compile(r"logo|icon|sprite|favicon|badge|payment|swatch|flag[-_.]|"
                  r"placeholder|pixel|blank|loading|arrow", re.I)
SIZE_QUERY_KEYS = {"w", "h", "width", "height", "sw", "sh", "size", "imwidth",
                   "imheight", "wid", "hei", "maxwidth", "maxheight", "$"}


class PageImages(HTMLParser):
    """Collect candidate image URLs with a source tag and declared width."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found = []            # (url, source, declared_width)
        self.title = ""
        self._in_title = False
        self._in_ldjson = False
        self._ldjson_chunks = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            prop = (a.get("property") or a.get("name") or "").lower()
            if prop in ("og:image", "og:image:secure_url", "twitter:image") and a.get("content"):
                self.found.append((a["content"], "og", 0))
        elif tag == "link":
            if a.get("rel") == "preload" and a.get("as") == "image" and a.get("href"):
                self.found.append((a["href"], "preload", 0))
        elif tag in ("img", "source"):
            for key in ("src", "data-src", "data-original", "data-zoom-image", "data-large_image"):
                if a.get(key) and not a[key].startswith("data:"):
                    self.found.append((a[key], "img", 0))
            for key in ("srcset", "data-srcset"):
                if a.get(key):
                    for url, width in parse_srcset(a[key]):
                        self.found.append((url, "img", width))
        elif tag == "script" and (a.get("type") or "").lower() == "application/ld+json":
            self._in_ldjson = True

    def handle_data(self, data):
        if self._in_title:
            self.title += data
        if self._in_ldjson:
            self._ldjson_chunks.append(data)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._in_ldjson:
            self._in_ldjson = False
            blob = "".join(self._ldjson_chunks)
            self._ldjson_chunks = []
            try:
                self._harvest_ldjson(json.loads(blob))
            except (json.JSONDecodeError, ValueError):
                pass

    def _harvest_ldjson(self, node):
        if isinstance(node, list):
            for item in node:
                self._harvest_ldjson(item)
        elif isinstance(node, dict):
            types = node.get("@type", "")
            types = types if isinstance(types, list) else [types]
            if any("Product" in str(t) for t in types):
                self._collect_images(node.get("image"))
            for key in ("@graph", "itemListElement", "hasVariant", "item"):
                if key in node:
                    self._harvest_ldjson(node[key])

    def _collect_images(self, val):
        if isinstance(val, str):
            self.found.append((val, "ldjson", 0))
        elif isinstance(val, list):
            for v in val:
                self._collect_images(v)
        elif isinstance(val, dict):
            self._collect_images(val.get("url") or val.get("contentUrl"))


def parse_srcset(srcset):
    out = []
    for part in srcset.split(","):
        bits = part.strip().split()
        if not bits or bits[0].startswith("data:"):
            continue
        width = 0
        if len(bits) > 1 and bits[1].endswith("w"):
            try:
                width = int(bits[1][:-1])
            except ValueError:
                pass
        out.append((bits[0], width))
    return out


def group_key(url):
    """Same image at different sizes → one key (strip query + size tokens in path)."""
    p = urlparse(url)
    path = re.sub(r"[_-]\d{2,4}x\d{2,4}(?=\.|$)", "", p.path)
    path = re.sub(r"[_-]\d{2,4}w(?=\.|$)", "", path)
    return p.netloc.lower() + path.lower()


def unsized_variant(url):
    """URL with size-constraining query params dropped — often the full-res original."""
    p = urlparse(url)
    params = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
              if k.lower() not in SIZE_QUERY_KEYS]
    if len(params) == len(parse_qsl(p.query, keep_blank_values=True)):
        return None
    return urlunparse(p._replace(query=urlencode(params)))


def fetch_image(session, url):
    """Download url if it's an image. Returns (bytes, content_type) or None."""
    try:
        r = session.get(url, timeout=TIMEOUT, headers=HEADERS)
        r.raise_for_status()
    except requests.RequestException:
        return None
    ctype = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if not ctype.startswith("image/") or ctype == "image/svg+xml":
        return None
    return r.content, ctype


def measure(data):
    """(width, height) via PIL, or (0, 0) when PIL is missing/can't parse."""
    if Image is None:
        return 0, 0
    try:
        with Image.open(io.BytesIO(data)) as im:
            return im.size
    except Exception:
        return 0, 0


GENERIC_SEGS = {"products", "product", "item", "items", "p", "dp", "shop",
                "en", "us", "en-us", "women", "men", "www"}


def slug_from_url(url):
    """Last URL path segment that looks like words (skip color codes / SKUs)."""
    best = ""
    for seg in reversed([s for s in urlparse(url).path.split("/") if s]):
        seg = re.sub(r"\.[a-z0-9]{2,5}$", "", seg, flags=re.I)
        clean = re.sub(r"[^a-z0-9]+", "-", seg.lower()).strip("-")
        if not clean or clean in GENERIC_SEGS:
            continue
        if re.search(r"[a-z]{3,}", clean):
            return clean[:60]
        if len(clean) > len(best):
            best = clean
    return best[:60] or "item"


def slug_from_title(title):
    """Page <title> up to the first separator — usually the product name."""
    head = re.split(r"[|–—·:]", title or "")[0]
    clean = re.sub(r"[^a-z0-9]+", "-", head.lower()).strip("-")
    return clean[:48].rsplit("-", 1)[0] if len(clean) > 48 else clean


def collect_candidates(session, page_url):
    """Returns (candidates, direct_image, page_title)."""
    r = session.get(page_url, timeout=TIMEOUT, headers=HEADERS)
    r.raise_for_status()
    ctype = r.headers.get("Content-Type", "").split(";")[0].strip().lower()
    if ctype.startswith("image/"):
        return None, (r.content, ctype), ""   # URL was the image itself

    parser = PageImages()
    parser.feed(r.text)

    groups = {}   # key -> dict(url, source, declared_width)
    src_rank = {"ldjson": 0, "og": 1, "preload": 2, "img": 3}
    for url, source, width in parser.found:
        url = urljoin(page_url, url.strip())
        if not url.startswith("http") or JUNK.search(url):
            continue
        if re.search(r"\.(svg|gif|ico)(\?|$)", url, re.I):
            continue
        key = group_key(url)
        cur = groups.get(key)
        better = cur is None or width > cur["width"] or (
            width == cur["width"] and src_rank[source] < src_rank[cur["source"]])
        if better:
            groups[key] = {"url": url, "source": source, "width": width}

    cands = sorted(groups.values(),
                   key=lambda c: (src_rank[c["source"]], -c["width"]))
    return cands, None, parser.title.strip()


def rank_candidates(session, cands, max_dl):
    ranked = []
    for c in cands[:max_dl]:
        got, used_url = None, c["url"]
        alt = unsized_variant(c["url"])
        for url in filter(None, [alt, c["url"]]):
            got = fetch_image(session, url)
            if got:
                used_url = url
                break
        if not got:
            continue
        data, ctype = got
        w, h = measure(data)
        score = w * h if w else len(data)
        if c["source"] in ("ldjson", "og"):
            score *= 1.15
        ranked.append({"url": used_url, "source": c["source"], "data": data,
                       "ctype": ctype, "w": w, "h": h, "score": score})
    ranked.sort(key=lambda r: -r["score"])
    return ranked


def save(data, ctype, url, dest, slug, n):
    ext = IMG_EXT.get(ctype) or Path(urlparse(url).path).suffix or ".jpg"
    stem = slug if n == 1 else "%s-%d" % (slug, n)
    path = dest / (stem + ext)
    bump = 2
    while path.exists():
        path = dest / ("%s-%d%s" % (stem, bump, ext))
        bump += 1
    path.write_bytes(data)
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("url", help="product-page URL (or a direct image URL)")
    ap.add_argument("slug", nargs="?", help="filename slug, e.g. weejuns-loafers")
    ap.add_argument("--list", action="store_true", help="rank only, save nothing")
    ap.add_argument("--pick", help="save candidate(s) by rank, e.g. 2 or 1,3")
    ap.add_argument("--keep", type=int, default=1, help="save top N (default 1)")
    ap.add_argument("--dest", default=str(ROOT / "garments" / "raw"))
    ap.add_argument("--max", type=int, default=12, dest="max_dl")
    args = ap.parse_args()

    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)
    session = requests.Session()

    try:
        cands, direct, title = collect_candidates(session, args.url)
    except requests.RequestException as e:
        sys.exit("page fetch failed: %s" % e)

    slug = args.slug or slug_from_title(title) or slug_from_url(args.url)
    if not args.slug:
        print("slug: %s" % slug)

    if direct:
        data, ctype = direct
        w, h = measure(data)
        path = save(data, ctype, args.url, dest, slug, 1)
        print("saved %s  (%s, %dx%d)" % (path, ctype, w, h))
        warn_if_small(w, h)
        return

    if not cands:
        sys.exit("no image candidates found on the page (JS-only gallery? "
                 "grab the zoom-image URL from the browser and pass it directly)")

    print("ranking %d candidate(s) from %d found..." % (min(len(cands), args.max_dl), len(cands)))
    ranked = rank_candidates(session, cands, args.max_dl)
    if not ranked:
        sys.exit("candidates found but none downloaded as images (site may block "
                 "non-browser fetches; save the zoom image manually)")

    for i, r in enumerate(ranked, 1):
        dims = "%dx%d" % (r["w"], r["h"]) if r["w"] else "?"
        print("%2d. %-9s %-7s %5dKB  %s" %
              (i, dims, r["source"], len(r["data"]) // 1024, r["url"][:100]))

    if args.list:
        return

    if args.pick:
        picks = [int(x) for x in args.pick.split(",")]
    else:
        picks = list(range(1, min(args.keep, len(ranked)) + 1))

    for n, idx in enumerate(picks, 1):
        if not 1 <= idx <= len(ranked):
            sys.exit("--pick %d out of range (1-%d)" % (idx, len(ranked)))
        r = ranked[idx - 1]
        path = save(r["data"], r["ctype"], r["url"], dest, slug, n)
        print("saved %s  (%dx%d)" % (path, r["w"], r["h"]))
        if n == 1:
            warn_if_small(r["w"], r["h"])


def warn_if_small(w, h):
    if 0 < max(w, h) < 1000:
        print("WARNING: best asset is under 1000px on its long side — "
              "thumbnail-grade. Look for the site's zoom asset.")


if __name__ == "__main__":
    main()
