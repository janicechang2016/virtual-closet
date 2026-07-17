#!/usr/bin/env python3
"""Static export: the archive as a read-only demo. $0, stdlib only.

Snapshots /api/manifest (generation off, `demo: true` — the flag the app UIs
key off to hide write actions), then copies the app shell and every asset the
manifest references into an output dir ready for any static host. Routing
(/, /fitting-room, /api/manifest) lives in vercel.json at the repo root;
Vercel runs this script as its build command.

Run:  python3 scripts/export_static.py [--out ../site]
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # virtual-closet/
sys.path.insert(0, str(Path(__file__).resolve().parent))
import closet_server

# sourcing.html stays out: its scan/save routes need the live local server
APP_FILES = ["carousel.html", "index.html", "app.js", "style.css", "entrance-bg.jpg"]


def asset_urls(node, found):
    """Collect every /assets/... string reachable in the manifest JSON."""
    if isinstance(node, str):
        if node.startswith("/assets/"):
            found.add(node)
    elif isinstance(node, list):
        for v in node:
            asset_urls(v, found)
    elif isinstance(node, dict):
        for v in node.values():
            asset_urls(v, found)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT.parent / "site"))
    args = ap.parse_args()
    out = Path(args.out).resolve()
    if out.exists():
        shutil.rmtree(out)

    m = closet_server.manifest()
    m["generation_enabled"] = False
    m["demo"] = True

    (out / "api").mkdir(parents=True)
    (out / "api" / "manifest.json").write_text(json.dumps(m, indent=1) + "\n")

    (out / "app").mkdir()
    for name in APP_FILES:
        shutil.copy2(ROOT / "app" / name, out / "app" / name)

    found = set()
    asset_urls(m, found)
    copied, total, missing = 0, 0, []
    for url in sorted(found):
        src = ROOT / url[len("/assets/"):]
        if not src.is_file():
            missing.append(url)
            continue
        dst = out / "assets" / url[len("/assets/"):]
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
        total += src.stat().st_size

    print(f"site -> {out}")
    print(f"assets: {copied} files, {total / 1e6:.1f} MB")
    if missing:
        print("MISSING — manifest points at files that don't exist:")
        for u in missing:
            print("  " + u)
        sys.exit(1)


if __name__ == "__main__":
    main()
