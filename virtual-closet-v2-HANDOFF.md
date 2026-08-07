# Virtual Closet v2 — Handoff / Resume Point

**Last updated 2026-08-06 · branch `main`.** Read `CLAUDE.md` first — it is the source of
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
| Public site | virtual-closet-seven.vercel.app | builds from **`main`** · live at **`80233b3`** (08-06) |
| API | virtual-closet-api-production.up.railway.app | Railway, from **`main`**, root dir `server` |
| Postgres | Railway `Postgres` service | 58 garments · 59 outfits (18 published · 17 worn · 24 stylist) · **18 wears** |
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

### Resume here — analytics loop + cached try-ons deployed (2026-08-06)

**Analytics purpose and the cross-page loop are built.** Insights now leads with a wardrobe
brief — get dressed, bring one back, teach the system — and keeps the financial dashboard as
supporting evidence. It can open an occasion-filtered Stylist, decision history, or load a
rediscovery combination into the fitting room. Stylist cards now separate **TRY IT ON** from
**WOULD WEAR** and **NOT THIS**. Wear copy now accurately says logged outfits inform rotation
and recommendations but never enter the curated Archive without deliberate publication.

No ranking changed. New payload fields are descriptive: `brief`, `rotation_share`, and
rediscovery `partner_ids`.

**STYLIST → FITTING-ROOM RENDER — DONE AND DEPLOYED 2026-08-06 at `80233b3`.** The manifest
now carries an exact-set index of every cached FRONT outfit render,
including renders never saved or published as looks. Stylist and Insights handoffs equip the
pieces, then immediately stage the exact cache when one exists. A local miss keeps the pieces
equipped and exposes `GENERATE TRY-ON · ~$0.06`; only that click can reach the billed route.
The read-only deploy says to generate locally and keeps write controls hidden. The server
checks the cache again before the generation gate, so a stale page cannot bill a duplicate.
Generated and cached whole outfits hide per-garment corrective feedback because there is no
single garment to blame. The composed/flat-lay fallback remains deliberately out.

Verified with no paid verification calls: 40 server + 88 engine tests green, pinned model report green, JS
parses, real-browser miss and unsaved-cache hit both pass, server cache hit/miss guard passes,
static export succeeds (355 assets / 93.4 MB), privacy check passes.

Live acceptance: all six pages 200; manifest carries 20 cached sets; unsaved cache asset
`43+44+52` is 200; money remains sealed; all three style-profile paths 404; Railway health
200 and protected `/wear` 401.

**PAIRWISE YES-VERDICT AUDIT — CLOSED 2026-08-06, no model change.** The proposed removal was
already the deployed policy: `stylist_compat()` has consumed only published looks + blamed
rejections since `3de2a9c`. The full-verdict line in `wear_model_report.py` is an ablation, not
the production ranker. A new regression test pins that yes clicks never create runtime pair
positives while published looks and blamed rejections keep their respective roles.

**THREE-GARMENT IDENTIFICATION PILOT — RUN 2026-08-06; $0.1952 Anthropic.** Both ambiguous
dark garments honestly refused with zero searches and returned image-only prefill candidates.
The distinctive control failed the safety bar: it read Eckhaus Latta from the shoulder but
matched the painted-band hoodie to the wrong “Sprayed Hoodie” reseller page, then imported
fabric and fit from it. Three searches also cost $0.1468 alone. Search is now capped at one,
the estimator uses the measured search-context size, the shared hard budget gate runs before
the call, and the prompt requires an exact product/model code or two independent visual
matches; brand alone cannot unlock page provenance. Results are preserved under
`server/pilots/identification-2026-08-06/`. **Paid ingest stays disabled; the UI still uses its
$0 stub.**

**NEXT:** one separately approved (~$0.059 max estimate) re-run of the distinctive control
with the hardened prompt. Exact verification or honest refusal passes; another plausible
wrong product rejects identification-then-search as the prefill path.

### Future visual work — explicitly deferred 2026-08-05

After the analytics and cross-page decision loop are strengthened:

1. Pilot one fitting-room look as an 8-angle image sequence with drag-to-scrub,
   canonical angle buttons, progressive loading, and reduced-motion support.
2. Use Janice's reference to prototype the Archive as an animated runway with one or
   two looks; evaluate Kling before quoting or using fal.
3. Compare both pilots before choosing a production pipeline or expanding either
   treatment across the catalog. Do not commit to catalog-wide generation first.

**DECIDED 07-30, AND IT QUALIFIES A STANDING DOCTRINE. The Keen rule STAYS.** She wore
`25-kotn-samira-tank + 32-personal-language-skirt + 53-keen-sandals` on 07-27 (`day_out`),
which her own rule forbids suggesting. The old reading — "if a rule ever fails something she
actually wore, the rule is what is wrong" — is now **too strong**: her ruling was *"just
keep, that was an exception."* A rule describes what she wants OFFERED, and one day she
reached past it does not invalidate it. **So a worn outfit breaking a rule is a PROMPT TO ASK
HER, never an automatic verdict against the rule.**
Recorded as a single allowlisted entry in `TestRealCloset.ACCEPTED_RULE_EXCEPTIONS`, keyed by
garment set, with a second test that fails if the exception ever stops matching a real
violation — an allowlist that quietly stops protecting is worse than none. **Nothing goes in
that set without her saying so.**
Fixed alongside it: `test_user_rules_do_not_invalidate_worn_outfits` keyed off
`source == "worn"` and so could not see this case at all, because that wear matched a
published look. It now takes the worn set from `wear_log`.

**THE SWAP IS CLOSED AS A QUESTION (07-31) — ASKED HER, AND IT IS NOT A UI PROBLEM.**
The 07-30 entry here said the swap sitting at 0 was "a design problem, not a patience
problem" and pointed at making the control more prominent. **Asked directly before building
anything, her answer was "rarely — I just get dressed."** There is usually no deliberation to
record, so no redesign can collect it. Nothing was removed — migration 0006, the API
validation and the collapsed control all stay, since they cost nothing unused and a real
near-miss is still the best record available — but **the swap is no longer a next step, a
blocker, or an argument for touching `/wear`.**
Two consequences to carry forward: **wear logging will not produce a true negative**, so
every negative in every measurement stays synthesised from the whole space (which is what the
in-rotation column is for, permanently, not until better data arrives); and **the negative
channel that works is `/stylist`** — her blames are true contextual negatives, they have gone
44 -> 65, and published-looks + blame-negatives is the best-scoring variant at 0.839 / 0.827.
Judging cards is the collection activity worth her time. See the matching `CLAUDE.md` section.


0. **HER RULES NOW RUN IN THE ENGINE — DONE 07-28, $0.** Both executable rules from
   `style_rules.txt` filter every suggestion. **The first time anything she wrote changes what
   `/stylist` suggests.** Built as a THIRD TIER (`constraints.user_rule_violations`), not as
   hard rules — measured: zero worn outfits break them, but two published looks do, and neither
   was ever worn, so folding them into `hard_violations()` would have retroactively invalidated
   her own archive. One insertion point (`gaps.enumerate_outfits(apply_user_rules=True)`) means
   both stylist paths inherited it without per-path edits. Space 2320 -> 1600 (-31%); nothing
   stranded; 50 tests green; deployed payload verified at 0 violations in 7,200 suggestions.
   See the "Her rules run in the engine" section of `CLAUDE.md`.
   **Still unenforced, and correctly so:** her other three rules are context, not constraints —
   dresses are event pieces (no events yet), weekday wears are work-from-home, and her
   silhouette is deliberately split. None is a filter; the first two are arguments for
   occasion/context modelling, which is candidate (3) below.

0b. **WEAR CONTEXT — LIVE 07-28.** Migration 0006 adds `occasion`, `weather` and the swap
   (`nearly_wore`/`instead_of`) to `wear_log`, which until now held `outfit_id` and `worn_on`
   and nothing else. COLLECTION, not modelling — it changes no ranking; it changes what the
   next measurement can use. **The swap is the first true negative the dataset has ever had.**
   See the "Wear CONTEXT" section of `CLAUDE.md`.
   **Done:** 0006 applied · **15/15 wears carry NYC weather** (Open-Meteo archive, $0) ·
   API + site deployed at `e282c58` · acceptance run passed against production (reversed swap
   and unknown occasion both 400; valid wear round-trips; undo removes wear + created outfit;
   restored to 15 wears / 57 outfits / 0 orphans).
   **BACKFILL DONE 07-28 — 15/15 wears carry occasion and weather.** She filled the form; all
   15 applied by `wear_id`. Mix: dinner 6, day_out 4, work_home 3, work_out 2.
   **First finding: occasion removes 59% of the uncertainty about footwear** (yello-heels
   worn 5×, all dinner; sneakers 5×, never dinner) — the first real account of the rotation
   shortcut. Descriptive only at n=15. It also partly contradicts her weekday/WFH rule; see
   the "Wear CONTEXT" section of `CLAUDE.md`. **From here the swap is the field that moves the
   number, and it only accrues from the next wear onward.**

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
3. **PAIRWISE COMPATIBILITY — BUILT, MEASURED, WIRED AND DEPLOYED 07-29, $0.** She reviewed it
   locally over 34 verdicts, liked it, and approved the deploy. It is the first model to beat
   chance on what she actually wears:
   **0.814 whole / 0.794 in-rotation**, against affinity's 0.648 / 0.543, with the in-rotation
   CI [0.707, 0.871] excluding 0.5 for the first time. Most of the win is the model SHAPE, not
   new data — on the same 18 published looks and nothing else, pairs score 0.754 / 0.726. Her
   44 blamed rejections are load-bearing, and this is their first use for anything.
   Both stylist paths rank with it through the ONE insertion point
   `gaps.ranked_outfits(..., compat=...)`, and the model is built by
   `closet_server.stylist_compat()` — defined once, imported by the exporter, top-50 verified
   identical across both. Read the "PAIRWISE COMPATIBILITY" section of `CLAUDE.md` before
   touching it — especially the calibration trap (raw pair scoring measured 0.809 while putting
   a dress in 10 of its top 12, which AUC cannot see) and the fact that her "yes" verdicts
   measurably HURT this model.
   **To deploy: commit and push `main`** — that redeploys the site and the API together, and
   regenerates the pool with pairs. To back it out, drop `compat=` at the two call sites.
   Still-unbuilt candidates from the 07-27 list: **context/occasion** (`outfit.context` and now
   `wear_log.occasion` exist) and **frequency-normalised affinity**.
   **Do not retry feeding wears into `preference.affinity`** — settled, -0.123 / -0.172. That
   finding does NOT transfer to pairwise, where the same test gives +0.012 / +0.005.
4. **`/galaxy` time scrubber — BUILT 07-27 (E.4), and it runs on ACQUISITION, not wear.** (This
   entry previously said it was unbuilt; that was stale.) The wear log is one row per day across
   a fortnight, so replaying it is a ticker; purchase dates span 2018-10 -> 2026-07 and carry
   the real shape. See the `/galaxy` notes in `CLAUDE.md`.
5. **Track A paid half** — multi-garment detection + vision-LLM tagging. Blocked on the fal
   balance (**-$0.08**) and needs approval. Build only if *tagging* rather than *photographing*
   turns out to be her bottleneck. `/ingest`'s `stage` already returns one garment per call,
   so detection becomes N calls into the same commit path, not a rewrite.
6. **Track D — style learning + gap analysis.** The last unbuilt track, materially better once
   real wear data exists. Do it after (1).

## 3b. Session of 2026-07-28/29 — what changed

Read the matching sections of `CLAUDE.md` before touching any of it.

- **Measurement harness REBUILT and tracked** (`server/scripts/wear_model_report.py`). The
  07-27 figures had become unreproducible; this reproduces them and fails on drift. **Run
  `--check` before quoting any number**, and always with `apply_user_rules=False`.
  **REPINNED 07-31 to the 18-wear data state** (affinity rotation 0.548 -> 0.583, colour
  0.360 -> 0.399, affinity whole 0.652 -> 0.682): the test set grew, so the old values are
  permanently unreproducible and a permanently-red check stops being read. **The rule is
  "repin when the data grew, investigate when it did not."** Both load-bearing findings were
  re-verified first — wears still hurt affinity (-0.118 / -0.170) and are still neutral for
  pairwise (+0.001 / -0.002). `EXPECTED_PAIRWISE` was repinned too, 0.768/0.774 -> **0.803 /
  0.802**, but only after her stylist session closed — her verdicts train that model, so it
  moves on two inputs rather than one. **Repin pairwise only between stylist sessions**, and
  check the report header's verdict count matches the constant (18 wears / 140 verdicts).
  **`--check` exits 0 with every figure green.**
- **One definition of "worn"** — `gaps.worn_outfits()` (published + logged). `engine_report`
  had been counting stylist SUGGESTIONS as wears: 9 never-worn against /insights' 13.
- **Her rules run in the engine**, occasion-aware. Third rule added from behaviour, not speech:
  no sneakers for dinner. `occasion=None` cannot violate an occasion rule.
- **Wear context is live** (migration 0006): occasion, weather, and the swap. **15/15 wears
  carry occasion and weather; the swap is still 0 and only accrues forward.**
- **Mobile is done, layout and touch.** Sticky hover and 16–35px tap targets were the real
  faults, both fixed in `nav.js` (the one file every page loads). `/galaxy` gained
  `touch-action` and pinch-zoom.
- **`/galaxy` is now a LIGHT ground** (her call). `?ground=dark` restores the old field.
- **Find-a-better-photo -> grid pre-fill: $0 skeleton built, never run paid.** One approved
  batch of 3 garments (~18c) is the next step; see the CLAUDE.md section.
- **`engine/pairwise.py` is new (07-29) and is the first model to beat chance on her wears.**
  Measured, tested (engine 56 -> 76 tests), NOT wired into `/stylist`. See §3.3.
- **`scripts/cdp.py` is new and is how any of this gets checked.** `--touch` for real
  touchscreen emulation, `--gpu` for software WebGL. **Without `--gpu` every /galaxy
  screenshot is the 2D fallback, not the shader.**

## 4. Queued and discussed, NOT started

- **Galaxy title type** — six treatments built, previews in
  `virtual-closet/design-inspo/galaxy-title-previews/`. She looked and tabled it. **Explicitly
  set aside again 07-29** ("ignore the galaxy title and glassmorphism points").
- **Non-black galaxy ground — DONE 07-29.** Shipped as a light ground; see `CLAUDE.md`.
- **Runway motion in the carousel** (her idea 07-28) — avatars appearing to walk as the
  carousel scrolls, possibly via her existing **Kling** subscription, which changes the
  economics completely from 4.4's $3.20/look fal quote. **Do not re-quote fal without checking
  Kling first.** The fitting room's missing hands-reaching frame on swap belongs to this
  conversation too: it is gated to the base-avatar state by design (`baseHover()` bails when
  `currentRender` is set) because `front-receive.png` is an edit of the BASE avatar and no
  render has a receiving twin. Per-render variants were rejected 07-17 for cost and face risk.
- **Multi-item try-on ALREADY EXISTS** — the fitting room's outfit slots + **Render outfit**
  ($0.059, ~1 min). She did not know; the open question is discoverability, not capability.
  On a phone it needs a drag onto a slot, which has no tap path — a design question, not a bug.
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
- **`/api/manifest`'s build stamp reports `branch: master`, and that is COSMETIC.** The deploy
  really is from `main`. `export_static.py` reads `git rev-parse --abbrev-ref HEAD` inside
  Vercel's checkout, which does not carry the real ref name. **Trust the `commit` field only** —
  it is the one that answers "which commit is live". Do not let the branch field send you down
  the stale-branch path above; check the commit hash against `git log` first.
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
  relative. Test on the real route. **`scripts/serve_site.py` (07-29) is how**: a plain
  `http.server` over a built site 404s `/stylist` and `/api/stylist/suggest`, and stylist.html
  answers by rendering NOTHING, which reads as a broken feature rather than a broken test. It
  applies vercel.json's rewrites, read from the file so they cannot drift.
- **`dump_closet.py` MUST BE RUN FROM `server/`.** The Railway link is registered against
  `/Users/janice.chang/wardrobe-v3/server`; anywhere else the CLI answers "No linked project
  found" and the script exits 1, which reads as a broken script rather than a wrong cwd.
- **"Structural" in a function name is a claim that must be enforced in code.** `orphans()`
  enumerated the rule-FILTERED space while promising a structural answer, so the first garment
  she gated by rule was reported as having "no structural partner" on `/insights`. Any
  measurement of the closet's SHAPE takes `apply_user_rules=False`. (07-30)
- **A stale `closet_snapshot.json` looks exactly like unbuilt features.** Phase 3c appeared
  "not done" for a day; the code had always been there and the snapshot was old. When new data
  "changes nothing downstream", re-dump before reading code.
- **The 07-27 measurement scripts were lost to an untracked `scratchpad/`. REBUILT 07-28 as
  `server/scripts/wear_model_report.py`** — run `--check` before trusting any number that
  claims to compare against 07-27. Anything worth quoting later belongs in `server/scripts/`
  and in git, never in scratchpad.
- **NEVER SCORE A RANKER ON THE CARDS IT CHOSE.** Her first pairwise session (07-29) scored
  0.557 for pairwise and 0.725 for affinity on the same 34 verdicts — which reads as a
  regression and is not one. She only saw cards pairwise ranked p65-p100 (IQR 13 points);
  affinity spreads those same cards p2-p98 (IQR 46). The filtered model has no variance left to
  discriminate with. **The wear log is the only unbiased benchmark** — no verdict touches it.
- **AUC CANNOT SEE A BAD TOP-OF-LIST, and on 07-29 it hid a disqualifying one.** Raw pair
  scoring measured 0.809 while putting a dress in 10 of its top 12 — dresses are 5% of the
  space and 1 of 15 wears — because floating 120 of 2320 negatives barely moves a rank
  statistic. A ranking model is judged on its first row. `wear_model_report.top_of_list()`
  prints that row's composition beside the space's own shares; read it every run.
- **Measurements must run with `apply_user_rules=False`.** The 07-27 figures are on the 2320
  structural space; her rules cut the suggestable space to 1600 on 07-28. Comparing across the
  two silently compares different questions.
- **`dump_closet.py` FLATTENS ITS QUERY TO ONE LINE** before handing it to psql, so a `--`
  comment inside `QUERY` silently swallows the rest of the statement. Use no line comments
  there. Cost a broken dump on 07-28.
- **`IS DISTINCT FROM` treats two NULLs as NOT distinct**, so a CHECK written that way rejects
  every row where both columns are null. Broke migration 0006's first run against all 15
  existing wears; written as "null, or different" instead.
- **asyncpg returns jsonb as TEXT unless a codec is registered.** `GET /wear` returned the
  string `"{}"` — which is truthy, so an empty weather read as a present one. Caught only by
  the acceptance run, never by the tests.
- **Run the engine tests AFTER re-dumping the snapshot, not before.** `TestRealCloset` reads
  it, so a suite that passes pre-dump can fail post-dump — this shipped a red test to `main`
  on 07-27.

## 6. Standing rules — re-read before touching anything

- **Spending is gated.** fal only in approved batches, every call through `scripts/genlog.py`
  (**$13.15 of $25 used** — fal $12.31 + `claude-opus-5` $0.84, one shared cap; re-check with
  the command rather than trusting this line). Track A's paid half and Track F need approval
  *and* a top-up.
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
  **This rule is about `preference.affinity` SPECIFICALLY and does not generalise** — the same
  test on `engine/pairwise.py` gives +0.012 / +0.005 (07-29). A pair either co-occurred or did
  not, so repeats cannot inflate it the way frequency inflated a per-garment scalar.
- **Rejections are unusable by a SCALAR, not unusable full stop** (07-29). `NEGATIVE_WEIGHT = 0.0`
  stands for `preference.affinity`. Read as PAIRS, the same 44 blamed rejections are worth
  +0.17 AUC — they are the largest single contribution to the pairwise model.
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
