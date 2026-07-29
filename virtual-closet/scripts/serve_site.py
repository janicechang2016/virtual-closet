#!/usr/bin/env python3
"""Serve a built `site/` with vercel.json's rewrites applied.

    python3 scripts/export_static.py --out /tmp/site
    python3 scripts/serve_site.py /tmp/site 8792
    python3 scripts/cdp.py eval http://localhost:8792/stylist "..."

WHY THIS EXISTS. `python3 -m http.server` over a built site is NOT the deployed
site: the routes are rewrites, so `/stylist` and `/api/stylist/suggest` both
404, and `stylist.html` responds by rendering NOTHING — which looks exactly
like a broken feature rather than a broken test. That cost a false negative on
07-29 while checking the reasoning toggle, and it is the same trap the handoff
already records as "serving a copy of a page from another path breaks it".

The map is read from vercel.json rather than copied, so it cannot drift from
what actually deploys. Test harness only — never part of a build.
"""
import http.server
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VERCEL = os.path.normpath(os.path.join(HERE, "..", "..", "vercel.json"))


def rewrites():
    with open(VERCEL) as fh:
        return {r["source"]: r["destination"] for r in json.load(fh)["rewrites"]}


class Handler(http.server.SimpleHTTPRequestHandler):
    MAP = {}

    def translate_path(self, path):
        clean = path.split("?", 1)[0].split("#", 1)[0]
        return super().translate_path(self.MAP.get(clean, path))

    def log_message(self, *args):
        pass


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    root = os.path.abspath(sys.argv[1])
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 8792
    Handler.MAP = rewrites()
    os.chdir(root)
    print("serving %s on http://localhost:%d with %d rewrites"
          % (root, port, len(Handler.MAP)))
    http.server.HTTPServer(("", port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
