# Virtual Closet v2 — Handoff / Resume Point

**Last updated 2026-07-27 (late) · branch `main`.** Read `CLAUDE.md` first — it is the source of
truth and is kept current. `virtual-closet/docs/decisions.md` carries the standing rules.
This file is the five-minute orientation: what runs where, what to do next, what has already
cost time.

*(The 07-25 version of this file described Phase 0 on a `2d-reboot` branch with "Phase 1 not
started". All of that is obsolete — Phases 0–3 and Track A's $0 half are done, and
`2d-reboot` no longer exists.)*

---

## 1. Where everything runs

| Thing | Where | State |
|---|---|---|
| Public site | virtual-closet-seven.vercel.app | builds from **`main`** |
| API | virtual-closet-api-production.up.railway.app | Railway, from **`main`**, root dir `server` |
| Postgres | Railway `Postgres` service | 58 garments · 57 outfits (18 published · 15 worn · 24 stylist) · **15 wears** |
| Local app | `localhost:8765` | `python3 scripts/closet_server.py` from `virtual-closet/` |

**A push to `main` redeploys BOTH** the site and the API. Deliberate — one branch, no
promotion step — and the fix for two separate stale-branch incidents (§5).

Check what is actually live in two requests:

```bash
curl -s https://virtual-closet-seven.vercel.app/api/manifest \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['build'])"
curl -s -o /dev/null -w "%{http_code}\n" \
  https://virtual-closet-api-production.up.railway.app/wear      # 401 = deployed
```

## 2. The pages

| Route | Deployed? | Reads | Writes |
|---|---|---|---|
| `/` archive carousel | yes | `looks.json` | — |
| `/fitting-room` | yes | manifest | local only |
| `/stylist` | yes, read-only | precomputed ranked pool | local only |
| `/insights` | yes, figures encrypted | `api/insights.json` | — |
| `/galaxy` | yes, figures encrypted | `api/galaxy.json` | — |
| `/wear` | **yes — and it writes** | `api/garments.json` | Railway `POST /wear` |
| `/ingest` | **no — local only** | — | garment folder + Postgres row |
| `/sourcing` | no — local only | — | `garments/raw/` |

Adding a page to the deploy takes **four** things; missing any one is a 404. A `vercel.json`
rewrite, the file in `APP_FILES`, a static payload *plus its own rewrite* for every route the
page fetches, and `asset_urls()` walking that payload or its images 404.

## 3. What to do next

1. **HER STATED NEXT STEP (07-27): evaluate where things stand, then tweak.** The wear track
   is DONE and deployed — 15 wears logged, snapshot refreshed, pages reading them. What the
   data REVEALED is the open work, not more plumbing. Read the Phase 3 section of `CLAUDE.md`
   for the measurements before deciding anything; the headline is that nothing currently
   predicts her wears well.
2. **FITTING-ROOM IMAGE RENDERING — her other stated next piece (07-27). NOT YET SPECIFIED.**
   She wants rendering updates in `/fitting-room`. Nothing is scoped: **ask what she wants
   changed before touching `tryon.py` or the stage.** Note this is the one live area that
   SPENDS — every render is a fal call at ~$0.059 and §6's batch-approval rule applies, and
   the fal balance was last seen at **-$0.08**, so a top-up may be needed before anything runs.
3. **The stylist cannot yet hit its own target.** Her call 07-27: `/stylist` should suggest
   outfits she would WEAR, not ones she would publish. Measured, it does not — 0.660 held out
   against real wears, and **0.555 (CI spanning chance)** once garment rotation is controlled
   for, versus 0.824 on her stated verdicts. Feeding wears into affinity was measured and makes
   it WORSE; that is settled, do not retry it. Candidates for a model that could hit the
   target, none built: **pairwise compatibility** (her blame data already encodes exactly
   this), **context/occasion** (`outfit.context` exists), or **frequency-normalised affinity**.
   All are speculative — at 15 wears the CIs are wide, and another few weeks of logging would
   sharpen the next measurement for free.
4. **`/galaxy` time scrubber** (plan E.4) — previously impossible because `wear_log` was
   empty. It now carries 15 dated rows, so it finally has something to animate.
5. **Track A paid half** — multi-garment detection + vision-LLM tagging. Blocked on the fal
   balance (**-$0.08**) and needs approval. Build only if *tagging* rather than *photographing*
   turns out to be her bottleneck. `/ingest`'s `stage` already returns one garment per call,
   so detection becomes N calls into the same commit path, not a rewrite.
6. **Track D — style learning + gap analysis.** The last unbuilt track, materially better once
   real wear data exists. Do it after (1).

## 4. Queued and discussed, NOT started

- **Galaxy title type** — six treatments built, previews in
  `virtual-closet/design-inspo/galaxy-title-previews/`. She looked and tabled it.
- **Non-black galaxy ground** — her idea; the glass effect is limited by what sits behind it.
  Touches the locked Ink-palette decision, so discuss before building.
- **Find-a-better-photo search** — reverse image search is blocked (Lens has no API, Bing
  Visual Search retired, TinEye matches exact reuse). Workable route is
  identify-then-text-search, reusing `ingest_fetch.py` and the `/sourcing` grid.
- **Carousel detail glassmorphism**, **looks grid/index lens**, **fal top-up → recover the
  $0 pilot segment → hero look videos**.

- **Entrance passphrase gate** — built 07-27, fully working, then REVERTED: the site stays
  public so interviewers can look at it. Vercel Deployment Protection is Pro-only and not
  available on her plan; the free replacement if it ever returns is a root `middleware.ts`.
  See CLAUDE.md for the findings and why an in-page check is ceremony, not a lock.

**Closed — do not re-propose:** stylist index/catalog numbering (four treatments previewed,
all rejected 07-26), Aquiline Two on the entrance (built then reverted at her request),
stylist explore mode, vertical body-stacked cards, wildcard as a full-width interruption.
**`pairwise compatibility` was on this list (07-26) but that call PREDATES the 07-27
measurement showing a per-garment scalar cannot reach her stated target — it is now the
strongest candidate, so raise it with her rather than treating it as closed.**

## 5. Traps that have already cost time

- **Stale deploy branches, twice.** Vercel built from a `production` branch 38 commits behind.
  Railway built from `2d-reboot` after it was deleted, while a *duplicate* service that was on
  `main` crash-looped for want of `DATABASE_URL`. Both now point at `main`. **If a deploy looks
  wrong, check the branch setting before reading the code.**
- **`--virtual-time-budget` starves `/galaxy`'s rAF load-in** — headless `--screenshot` always
  captures an empty field. Drive it over CDP on a real clock with `--remote-allow-origins=*`.
- **Chrome clamps `--window-size` to ~500px** — a true phone viewport needs
  `Emulation.setDeviceMetricsOverride`, or you are not testing what you think you are.
- **`server/scripts/closet_snapshot.json` is deliberately TRACKED.** The Vercel build has no
  Postgres and no `.app_secret`; without it in the repo, `/insights`, `/galaxy` and `/stylist`
  cannot be generated at all.
- **`INSIGHTS_PASSCODE` must exist in Vercel, Production *and* Preview.** Missing it fails the
  build on purpose — a silent skip would publish real figures.
- **Serving a copy of a page from another path breaks it** — node and garment images resolve
  relative. Test on the real route.
- **A stale `closet_snapshot.json` looks exactly like unbuilt features.** Phase 3c appeared
  "not done" for a day; the code had always been there and the snapshot was old. When new data
  "changes nothing downstream", re-dump before reading code.
- **Run the engine tests AFTER re-dumping the snapshot, not before.** `TestRealCloset` reads
  it, so a suite that passes pre-dump can fail post-dump — this shipped a red test to `main`
  on 07-27.

## 6. Standing rules — re-read before touching anything

- **Spending is gated.** fal only in approved batches, every call through `scripts/genlog.py`
  ($11.78 of $25 used). Track A's paid half and Track F need approval *and* a top-up.
- **She decides aesthetics.** Build it, show it, expect rejection sometimes. Rejected variants
  get tags or preview folders, never deletion.
- **Logged outfits never reach the archive carousel** (07-27). Holds structurally — the
  carousel reads `looks.json`, wear logging writes Postgres `outfit` rows. Any change that
  builds the carousel from the snapshot breaks it.
- **Colour theory does not predict her taste** — AUC 0.491 (chance) vs 0.824 learned, on her
  stated verdicts. Hard constraints filter, learned preference ranks, colour is a low-weight
  tiebreak. **Against actual BEHAVIOUR (07-27) colour is 0.360 — below chance — and affinity
  is only 0.660 / 0.555.** Stated preference and lived behaviour are not the same target.
- **Wears do NOT feed affinity** (`PRIOR = ("manual",)`). Measured by leave-one-out: adding
  them costs 0.120–0.172 AUC. Wear FREQUENCY is not preference. Sibling of NEGATIVE_WEIGHT.
- **`PRIOR` is what TRAINS affinity; it is NOT what counts as WORN.** The worn set comes from
  `_wear_counts()` — published appearances PLUS the wear log — which is what /insights reports.
  Conflating them made /stylist and /insights disagree (23 vs 13 never-worn) on 07-27.
- **Rejections are collected but NOT applied** (`NEGATIVE_WEIGHT = 0.0`) — measured twice, on
  independent data, and they cost accuracy both times.
- **Money on the deployed site is encrypted, not masked.** `lock_money.mjs` strips 283 figures
  into an AES-GCM blob; a UI-only mask would leave them in the JSON for anyone to curl.

## 7. Infrastructure facts worth not re-deriving

- Railway **Hobby $5/mo** was required — the trial had expired and `railway init` refused
  without a plan. Separate recurring cost from the fal budget.
- **`railway up` (CLI upload) returns 403 — unexplained.** Auth was fine on the same
  credentials. Deploys come from GitHub instead; this is the known blocker if CLI upload is
  ever needed.
- `DATABASE_URL` is **not** auto-injected — Railway variables are per-service. Set as a
  reference: `DATABASE_URL=${{Postgres.DATABASE_URL}}`.
- Migrations from a laptop need **`DATABASE_PUBLIC_URL`**, not `DATABASE_URL` (the latter is a
  `railway.internal` host, unreachable off-platform). `psql` is keg-only from `brew install
  libpq` → `/opt/homebrew/opt/libpq/bin/psql`.
- **R2 credentials and the worker service are still deliberately deferred.** Nothing built so
  far touches object storage or needs a second process.

## 8. Safety nets

- `2d-final-pre-v2` — tag at `3b069e0`, pushed. The complete pre-pivot 2D app.
- `archive/360-avatar-v4-20260724` — the 3D/360 exploration.
- `~/wardrobe-v3-360-local-assets-20260724/` — 2.1 GB of parked 360 assets.

## 9. Commands

```bash
python3 scripts/closet_server.py                              # local app, from virtual-closet/
python3 server/scripts/dump_closet.py                         # Postgres -> snapshot (after ingesting!)
python3 virtual-closet/scripts/export_static.py --out site    # exactly what Vercel builds
INSIGHTS_PASSCODE=... node virtual-closet/scripts/lock_money.mjs site
python3 scripts/genlog.py summary                             # spend vs cap
railway variables -s Postgres --kv | grep DATABASE_PUBLIC_URL # psql from the laptop
/opt/homebrew/opt/libpq/bin/psql "$URL" -v ON_ERROR_STOP=1 -f server/migrations/000N_x.sql
```

API bearer token: `server/.app_secret` (gitignored). The liminal venv
(`/Users/janice.chang/liminal-wardrobe/.venv/bin/python`) is where rembg/cv2/PIL live —
system python3 is 3.9 and has none of them.
