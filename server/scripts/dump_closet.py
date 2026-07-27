#!/usr/bin/env python3
"""Snapshot the closet from Postgres to JSON so the engine can run offline. $0.

    python3 scripts/dump_closet.py            # -> scripts/closet_snapshot.json

Keeps the engine a pure library: it takes plain dicts and never opens a socket,
so the tests are fast, deterministic, and runnable without the database up.
Requires the psql on PATH used elsewhere in this project, via `railway run`.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "closet_snapshot.json")
PSQL = "/opt/homebrew/opt/libpq/bin/psql"

QUERY = """
SELECT json_build_object(
  'garments', (SELECT coalesce(json_agg(row_to_json(g)), '[]'::json) FROM (
      SELECT id, category, subcategory, colors, pattern, formality, warmth,
             season_tags, fabric, fit, volume, asset_tier, size_owned, brand,
             purchase, wear_count, last_worn
      FROM garment ORDER BY id) g),
  'outfits', (SELECT coalesce(json_agg(row_to_json(o)), '[]'::json) FROM (
      SELECT id, garment_ids, source, context, render_cache_key
      FROM outfit ORDER BY render_cache_key) o),
  'wears', (SELECT coalesce(json_agg(row_to_json(w)), '[]'::json) FROM (
      SELECT outfit_id, worn_on FROM wear_log ORDER BY worn_on) w)
);
"""


def main():
    # Flatten to one line: json.dumps would emit literal \n sequences, which psql
    # reads as backslash meta-commands rather than whitespace.
    one_line = " ".join(QUERY.split())
    cmd = ["railway", "run", "--service", "Postgres", "bash", "-c",
           '%s "$DATABASE_PUBLIC_URL" -X -A -t -c %s' % (PSQL, json.dumps(one_line))]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stderr[-2000:], file=sys.stderr)
        return 1

    # Railway's CLI injects unrelated chatter; the payload is the one JSON line.
    payload = None
    for line in res.stdout.splitlines():
        line = line.strip()
        if line.startswith("{") and '"garments"' in line:
            payload = json.loads(line)
            break
    if payload is None:
        print("no JSON payload in psql output", file=sys.stderr)
        print(res.stdout[-2000:], file=sys.stderr)
        return 1

    with open(OUT, "w") as fh:
        json.dump(payload, fh, indent=1)
    print("garments %d · outfits %d · wears %d -> %s"
          % (len(payload["garments"]), len(payload["outfits"]),
             len(payload.get("wears") or []), os.path.relpath(OUT)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
