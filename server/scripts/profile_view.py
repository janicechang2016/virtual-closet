#!/usr/bin/env python3
"""Readable view of the style profile. READ-ONLY OUTPUT.

Rules are authored in `style_rules.txt`, which nothing here writes. This script
picks them up into `user_edits` and renders the whole profile for reading.

    python3 server/scripts/profile_view.py
"""
import argparse
import json
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROFILE = ROOT / "server/scripts/style_profile.json"
VIEW = ROOT / "server/scripts/style_profile.txt"
W = 88
RULES_HEAD = "YOUR RULES"
NEXT_HEAD = "OBSERVATIONS"


def wrap(t, indent=""):
    return "\n".join(
        textwrap.fill(x, W, initial_indent=indent, subsequent_indent=indent)
        for x in t.split("\n"))


RULES = ROOT / "server/scripts/style_rules.txt"


def load_rules():
    """Her rules, from a file this script NEVER writes.

    They lived in the rendered .txt briefly and that was a mistake: the view is
    regenerated, so parsing edits back out of it meant one fragile splitter
    standing between her and data loss — which it caused twice. A separate,
    never-regenerated file removes the failure mode instead of hardening it."""
    if not RULES.exists():
        return []
    return [" ".join(b.split()) for b in RULES.read_text().split("\n\n")
            if b.strip() and not b.strip().startswith("#")]


def render(p):
    e = p.get("evidence", {})
    L = ["STYLE PROFILE  ·  v%d" % p.get("version", 0)]
    L.append("generated %s  ·  %s  ·  $%.4f"
             % (p.get("updated_at", "")[:16].replace("T", " "),
                p.get("model", "?"), p.get("cost_usd", 0)))
    L.append("read from %s garments · %s published looks · %s logged wears"
             % (e.get("garments"), e.get("published_looks"), e.get("logged_wears")))
    L.append("")
    L.append("GENERATED FILE — every section here is rebuilt and edits are lost.")
    L.append("To change your rules, edit  server/scripts/style_rules.txt  instead.")
    L.append("=" * W)
    L += ["", "SUMMARY", "-" * W, wrap(p.get("summary", "")), "", ""]

    L.append(RULES_HEAD + "  (written by you — the model may not contradict these)")
    L.append("-" * W)
    rules = p.get("user_edits") or []
    if rules:
        for r in rules:
            L.append(wrap(r))
            L.append("")
    else:
        L += ["(none set — add them in server/scripts/style_rules.txt)", ""]
    L.append("")

    L += [NEXT_HEAD + "  (each with the evidence it was drawn from)", "-" * W]
    for i, o in enumerate(p.get("observations", []), 1):
        L.append("")
        L.append(wrap("%d. %s" % (i, o["claim"])))
        L.append(wrap(o["evidence"], indent="     "))
    L += ["", "", "NOT ENOUGH DATA FOR", "-" * W]
    for x in p.get("not_enough_data_for", []):
        L.append(wrap("· " + x))
    L += ["", "", "CONFIDENCE", "-" * W, wrap(p.get("confidence", "")), ""]
    VIEW.write_text("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.parse_args()

    p = json.loads(PROFILE.read_text()) if PROFILE.exists() else {}
    rules = load_rules()
    if rules != (p.get("user_edits") or []):
        p["user_edits"] = rules
        PROFILE.write_text(json.dumps(p, indent=2) + "\n")
        print("picked up %d rule(s) from %s" % (len(rules), RULES.name))
    else:
        print("%d rule(s), unchanged" % len(rules))
    render(p)
    print("rendered -> %s" % VIEW.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
