# Virtual Closet v2 — Handoff / Resume Point

**Last updated 2026-07-28 · branch `main`.** Read `CLAUDE.md` first — it is the source of
truth and is kept current. `virtual-closet/docs/decisions.md` carries the standing rules.
This file is the five-minute orientation: what runs where, what to do next, what has already
cost time.

> ## ⛔ READ FIRST — two things that will bite you
>
> **1. THE STYLE PROFILE NEVER SHIPS PUBLICLY (her directive 07-28).** `style_profile.json`,
> `style_profile.txt`, `style_rules.txt`. The deploy is public so interviewers can look at it;
> the profile records what she wore by date, what she rejects, and her own note that weekday
> wears are work-from-home. `export_static.assert_private()` fails the build if any of them
> reach the output — verified in both directions. Building a `/profile` page into the deploy
> means deciding to publish her. Don't.
>
> **2. THE PROFILE IS NOT IN GIT, BY DESIGN.** `style_profile.json` and `.txt` are gitignored
> (her call 07-28). They are NOT missing and NOT lost — regenerate with
> `build_profile.py --generate` (~$0.27) or just re-render from an existing json with
> `profile_view.py` ($0). **`style_rules.txt` IS tracked** — it is her authored work and the
> one irreplaceable file here. Never "fix" this by adding the profile back to git.

## 0. Where the style-profile files live (decided 07-28)

| File | In git? | Why |
|---|---|---|
| `server/scripts/style_rules.txt` | **tracked** | Her 5 authored rules. Irreplaceable — no way to regenerate a rule she wrote. Least revealing of the three. |
| `server/scripts/style_profile.json` | gitignored | Generated. Regenerable for ~$0.27, and the sensitive artifact (wears by date, rejections). |
| `server/scripts/style_profile.txt` | gitignored | Rendered view of the json; `profile_view.py` rebuilds it for $0. |

The repo is private, so tracking everything would have been *safe today* — but it is one
visibility flip from public and that repo's intent has already been flipped once for the
portfolio. Backing up only the irreplaceable half removes the question entirely.

**This is separate from, and weaker than, the public-deploy rule.** Gitignoring is about the
private repo; `assert_private()` is what stops the profile reaching the public site, and it
fails the build rather than trusting anyone to remember.

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

0. **STRONGEST NEXT BUILD — wire her rules into the engine as hard constraints ($0).**
   Two of her five rules in `style_rules.txt` are executable today: *"Never suggest a sneaker
   with a skirt or dress"* and *"Keen sandals are for extremely casual and walking days only —
   never with a skirt or dress."* `constraints.hard_violations()` can enforce both at
   $0/suggestion. **This would be the first time anything she wrote changes what `/stylist`
   actually suggests** — the profile itself changes nothing (see the Track D.1 section of
   `CLAUDE.md`). It also validates the sneaker/skirt finding cheaply, ahead of the ~50-wear
   Phase 6 measurement, since she has now confirmed it by rule rather than by inference.
   Note the interaction: enforcing these SHRINKS the valid outfit space, so re-run
   `engine_report.py` and the 41 tests afterwards — `TestRealCloset` asserts on space size.

1. **HER STATED NEXT STEP (07-27): evaluate where things stand, then tweak.** The wear track
   is DONE and deployed — 15 wears logged, snapshot refreshed, pages reading them. What the
   data REVEALED is the open work, not more plumbing. Read the Phase 3 section of `CLAUDE.md`
   for the measurements before deciding anything; the headline is that nothing currently
   predicts her wears well.
2. **FITTING-ROOM RENDERING — SPECIFIED AND DONE 07-27.** Her reading was *coverage*, and the
   specific gap was that **opening a look never tried it on**. Fixed: `stage_render()` +
   `showLook()` put a look's front render on the mirror from both doors, and the 9 looks that
   had no front render got one (~$0.53). See the "Fitting room — looks reach the mirror"
   section of `CLAUDE.md`, and `virtual-closet-v2-completion-plan.md` §4.1 for the audit that
   sized it. **`scripts/render_coverage.py` is the re-runnable check** — it found garment-level
   coverage already complete, which is why this was a wiring job and not a render backlog.
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
- **The style profile never ships publicly** (07-28) — see the banner at the top. Enforced by
  `export_static.assert_private()`, which fails the build rather than trusting anyone to
  remember.
- **Anthropic spend goes through `genlog.py` too**, not just fal. It is one shared $25 cap;
  `claude-opus-5` sits in `by_model` beside the fal models. `build_profile.py` records spend
  BEFORE checking the outcome, because a refused or truncated call is billed just the same —
  a truncated one slipped past the ledger on 07-28 and had to be reconstructed.
- **Thinking bills as OUTPUT on Opus 5, and is on by default.** A "short JSON answer" is not a
  short response: measured output ran 4–9x the naive estimate, and `max_tokens` caps thinking
  and response TOGETHER (8000 truncated mid-object; it is now 20000). Budget from measured
  `usage`, never from the expected length of the visible answer.
- **Never round-trip user edits out of a regenerated document.** The style profile's rendered
  `.txt` was briefly editable and the parser ate her rules twice — once by merging the first
  rule into the section header, once because the banner text itself contained the heading the
  splitter anchored on. Rules now live in `style_rules.txt`, which nothing regenerates.
- **When a model reports that data is missing, suspect your digest first.** The D.1 profile
  correctly said no rejection named a garment; the blame data was there, and the builder was
  reading `garment_ids`/`reason_code` instead of the log's real `ids`/`blame`. Cost a whole
  billed call and produced a confidently wrong profile.

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
