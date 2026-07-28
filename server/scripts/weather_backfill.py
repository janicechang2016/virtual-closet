#!/usr/bin/env python3
"""Fill `wear_log.weather` from the date each wear was logged. $0, no API key.

THE POINT: this is the only context field that costs her nothing. Occasion has
to be tapped and the swap has to be remembered; weather is already implied by
`worn_on` and can be recovered for every wear that has ever been logged, and
every wear that ever will be, without a single extra interaction.

Source is Open-Meteo's ARCHIVE endpoint — free, no key, no attribution
requirement, and it serves reanalysis data rather than forecasts, so a date in
the past returns what actually happened rather than what was predicted. The
archive lags real time by ~5 days; days inside that window fall back to the
forecast endpoint, which still holds recent history. Both are flagged in
`weather.source` so a later analysis can tell reanalysis from forecast rather
than silently mixing them.

Idempotent: only rows with an empty `weather` are fetched unless --refetch.

    python3 scripts/weather_backfill.py --lat 40.7 --lon -74.0 --dry-run
    python3 scripts/weather_backfill.py --lat 40.7 --lon -74.0

Needs DATABASE_PUBLIC_URL (the internal railway.internal host is unreachable
from a laptop — see the handoff).
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, timedelta

ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FORECAST = "https://api.open-meteo.com/v1/forecast"
DAILY = "temperature_2m_max,temperature_2m_min,precipitation_sum,weather_code"

# Open-Meteo WMO code -> a word. Deliberately coarse: the model will have tens of
# wears, not thousands, so "rain" is a usable category and "light freezing
# drizzle, dense" is not.
def _describe(code):
    if code is None:
        return None
    c = int(code)
    if c == 0:
        return "clear"
    if c in (1, 2, 3):
        return "cloud"
    if c in (45, 48):
        return "fog"
    if 51 <= c <= 67 or 80 <= c <= 82:
        return "rain"
    if 71 <= c <= 77 or c in (85, 86):
        return "snow"
    if c >= 95:
        return "storm"
    return "other"


def fetch_range(lat, lon, start, end, tz="auto"):
    """One request for the whole span. 15 wears is 15 days, not 15 calls."""
    out = {}
    for base, tag in ((ARCHIVE, "archive"), (FORECAST, "forecast")):
        q = {"latitude": lat, "longitude": lon, "daily": DAILY,
             "timezone": tz, "start_date": start, "end_date": end}
        url = base + "?" + urllib.parse.urlencode(q)
        try:
            with urllib.request.urlopen(url, timeout=60) as fh:
                data = json.load(fh)
        except Exception as e:                       # noqa: BLE001
            print("  %s: %s" % (tag, e))
            continue
        d = data.get("daily") or {}
        for i, day in enumerate(d.get("time") or []):
            if day in out:
                continue                             # archive wins; it is reanalysis
            def at(key):
                seq = d.get(key) or []
                return seq[i] if i < len(seq) else None
            code = at("weather_code")
            if at("temperature_2m_max") is None and code is None:
                continue                             # no data for this day
            out[day] = {
                "temp_max_c": at("temperature_2m_max"),
                "temp_min_c": at("temperature_2m_min"),
                "precip_mm": at("precipitation_sum"),
                "code": code,
                "conditions": _describe(code),
                "source": "open-meteo/" + tag,
                "lat": lat, "lon": lon,
            }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lat", type=float, required=True)
    ap.add_argument("--lon", type=float, required=True)
    ap.add_argument("--timezone", default="auto")
    ap.add_argument("--refetch", action="store_true",
                    help="overwrite rows that already have weather")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    dsn = os.environ.get("DATABASE_PUBLIC_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit("set DATABASE_PUBLIC_URL (see handoff §9)")

    try:
        import psycopg
        connect, style = psycopg.connect, "psycopg3"
    except ImportError:
        try:
            import psycopg2
            connect, style = psycopg2.connect, "psycopg2"
        except ImportError:
            sys.exit("no psycopg installed — see the note at the bottom of this file")

    where = "" if args.refetch else " WHERE weather = '{}'::jsonb"
    with connect(dsn) as con:
        with con.cursor() as cur:
            cur.execute("SELECT id, worn_on FROM wear_log%s ORDER BY worn_on" % where)
            rows = cur.fetchall()
            if not rows:
                print("nothing to fill")
                return
            days = [r[1] for r in rows]
            start, end = min(days), max(days)
            # Open-Meteo rejects an end date in the future.
            end = min(end, date.today() - timedelta(days=0))
            print("%d wear(s), %s -> %s @ %.4f,%.4f"
                  % (len(rows), start, end, args.lat, args.lon))

            wx = fetch_range(args.lat, args.lon, start.isoformat(), end.isoformat(),
                             args.timezone)
            print("fetched %d day(s)" % len(wx))

            filled = missed = 0
            for wid, day in rows:
                w = wx.get(day.isoformat())
                if not w:
                    missed += 1
                    print("  no data %s" % day)
                    continue
                print("  %s  %s  %s%s" % (
                    day, w["conditions"] or "?",
                    ("%.1f-%.1fC" % (w["temp_min_c"], w["temp_max_c"]))
                    if w["temp_max_c"] is not None else "?",
                    "  [dry-run]" if args.dry_run else ""))
                if not args.dry_run:
                    cur.execute("UPDATE wear_log SET weather = %s::jsonb WHERE id = %s",
                                (json.dumps(w), wid))
                filled += 1
            if args.dry_run:
                con.rollback()
                print("dry run — nothing written (%s)" % style)
            else:
                con.commit()
                print("filled %d, no data for %d" % (filled, missed))


if __name__ == "__main__":
    main()

# psycopg is not a dependency of this repo's laptop-side scripts (the API uses
# asyncpg, which needs a running loop and is awkward in a one-shot script). If it
# is missing:  python3 -m pip install --user "psycopg[binary]"
# The alternative is piping the generated SQL through the keg-only psql at
# /opt/homebrew/opt/libpq/bin/psql, which is what the migrations already use.
