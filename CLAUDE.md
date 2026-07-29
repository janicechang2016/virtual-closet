# Virtual Closet (wardrobe-v3)

Photorealistic virtual try-on with a persistent personal avatar, now extending into a
utility wardrobe tool. Working code in `virtual-closet/` (the 2D app) and `server/` (the v2
backend + engine); running decisions in `virtual-closet/docs/decisions.md` (read it — it
carries the standing rules). Plans: `virtual-closet-execution-plan.md` (v1),
`virtual-closet-plan-v2.md` (v2 spec), `virtual-closet-v2-foundation-plan.md` (Phases 0–2),
`virtual-closet-v2-HANDOFF.md` (cold-resume).

## v2 state (2026-07-27) — foundation + engine + stylist + wear logging done, $0.00 API spend

**DEPLOY SOURCE: `main`** (Vercel → Settings → Git → Production Branch, switched 07-26).
Pushing to `main` deploys the public archive; verify at virtual-closet-seven.vercel.app.

**All five pages deploy as of 07-26** — archive, fitting room, stylist, insights, galaxy.
Adding a page to the deploy takes FOUR things, and missing any one of them is a 404:
1. a rewrite in root `vercel.json` (`/stylist` → `/app/stylist.html`);
2. the file in `export_static.py`'s `APP_FILES`;
3. a static payload for every route it fetches, plus a rewrite for that too
   (`/api/galaxy` → `/api/galaxy.json`);
4. `asset_urls()` walking that payload, or every image in it 404s.
`server/scripts/closet_snapshot.json` is **deliberately tracked** — the Vercel build has no
Postgres and no `.app_secret`, so without it in the repo none of these payloads can be
generated. Refresh with `dump_closet.py` and commit. `/sourcing` stays out on purpose: its
scan/save routes need the live local server.
**The stylist ships as a ranked POOL, not as fixed cards.** Ranking is deterministic, so it
is precomputed per occasion at build time; the shuffle, the diversification pass and the
wildcard draw run in the browser, so the deployed stylist genuinely re-rolls. `engine/` was
NOT rewritten in JS. The page detects the payload by its `pool` flag and sets `body.demo`,
which hides the verdict controls and the decisions drawer — there is nowhere to write to.

Historical trap, recorded so it is not re-learned: Vercel deployed from a separate
**`production`** branch until 07-26, which sat **38 commits behind**. Work pushed to `main`
was correct and simply invisible — the giveaway was hashing the deployed
`/app/carousel.html` against each branch, since marker-grepping alone only says "old", not
"which". If a deploy ever looks stale, check the production-branch setting first.
**The deployed build now stamps itself** — `curl -s <site>/api/manifest` returns
`build: {commit, branch, exported_at}`, so "which commit is live?" is one request instead of
hashing files against every branch.

- **Phase 0 — hosted backend.** Railway (Hobby, $5/mo): Postgres 18 + `virtual-closet-api`
  at https://virtual-closet-api-production.up.railway.app. Both reversal guardrails verified
  live: `/health` open, `/budget` 401 without the bearer token, correct JSON with it via a
  real Postgres round-trip. Token in `server/.app_secret` (gitignored). R2 and the worker
  service are deliberately deferred. `railway up` (CLI upload) 403s for reasons never
  established — deploys come from GitHub instead.
- **Phase 1 — data.** 58 garments + 18 published looks in Postgres, fully attributed:
  measured LAB colour, category/subcategory, silhouette volume, formality, warmth, seasons,
  and purchase price/date (closet value $6,298). Looks carry occasion. Capture UIs are
  generated HTML opened via `file://` (`make_attr_grid.py`, `make_occasion_form.py`,
  `make_purchase_form.py` + matching `apply_*.py`); **she prefers browser forms to editing
  TSV in an editor.** `scripts/verify_backfill.sql` is the re-runnable acceptance check.
- **Phase 2 — engine.** `server/engine/`: `colour.py`, `constraints.py`, `gaps.py`,
  `preference.py` — pure functions, 28 stdlib unit tests, no I/O. `dump_closet.py` snapshots
  Postgres to JSON so the engine needs no database. 2320 valid outfits = (22×10 + 12)×10 (was 2220 = 21 tops, before 59-el-hoodie gained its `top` alt-role 07-27).
- **THE FINDING that shaped everything after it: colour theory does not predict her taste.**
  Measured blind on 24 outfits the model had never seen — colour + constraints AUC **0.491**
  (chance), learned per-garment affinity **0.824**. Hard constraints filter, learned
  preference ranks, colour is a low-weight tiebreak. Rejections are collected but NOT
  applied (`NEGATIVE_WEIGHT = 0.0`): measured twice, they cost accuracy, because a rejection
  is contextual ("wrong shoe for this outfit") and a per-garment scalar cannot hold that.
- **Track C preview:** 23 of 58 garments appear in no published look, $2,381 — but that is
  the PUBLISHED-ONLY figure. With the wear log it is **13 garments / $1,456**; see Phase 3c.
- Deferred, recorded, NOT priorities (her call): explore mode, pairwise compatibility,
  vertical body-stacked outfit cards, wildcard as a full-width interruption.

## Phase 3 — wear logging (2026-07-27), LIVE

**`/wear`** — the first page designed phone-first, because a wear is logged at the end of a
day away from the laptop. That is the whole reason it talks to the hosted API instead of
`closet_server.py`, and the first time Railway does anything the site actually needs.

- **The API has real endpoints now:** `POST /wear`, `GET /wear`, `DELETE /wear/{id}`, all
  behind `require_auth`, plus `CORSMiddleware` on an explicit origin allowlist — never `"*"`,
  because the bearer token rides in a header.
- **The token is entered once per device into `localStorage`.** No secret ships in the page.
- **`wear_log` references `outfit_id` and nothing else**, so an ad-hoc combination becomes an
  outfit row first (migration 0004 widened `outfit.source` to include `'worn'`). That is why
  wear logging compounds: every wear grows the corpus the stylist learns from. Matching is on
  the SORTED garment set and prefers a published look, so wearing something you published
  counts against that look rather than forking a twin.
- **Undo removes the outfit it created.** Leaving it was the first behaviour and was wrong —
  these outfits are destined to feed the stylist, so an orphan is a mis-tap that goes on
  teaching the model. Scoped to `source='worn'` with no wears left; published looks and
  stylist suggestions are never touched.
- Verified end to end against production, then production restored to `wear_log=0`,
  `manual=18`, `stylist=24`, 0 orphans. **That was the 07-27 acceptance run; production now
  holds 15 real wears and 57 outfits (18 manual · 15 worn · 24 stylist).**

**Railway is no longer misconfigured (07-27, her fix):** the duplicate `virtual-closet`
service — connected to `main` but with no `DATABASE_URL`, so it crash-looped on every push —
was deleted, and `virtual-closet-api` was repointed off the deleted `2d-reboot` branch to
`main`. Consequence: **a push to `main` now redeploys the API as well as the site.**

**Phase 3c — LANDED 07-27, and it was already built.** The previous note here claimed
`dump_closet.py` did not carry wear counts; that was wrong. It always selected
`wear_count`, `last_worn` and the whole `wear_log` as `wears`; `closet_server.py`
`_wear_counts()` already merged the log into per-garment counts ADDITIVELY (a published
look and a logged wear are two independent records of wearing, and it degrades to the old
numbers on an empty log); `/insights` already switched its caveat copy on `logged_wears`.
**The only blocker was a STALE `closet_snapshot.json`** — dumped while production was
restored to `wear_log=0` after the end-to-end verification. Lesson for the next one of
these: when logging "changes nothing downstream", suspect the snapshot before the code.
First real refresh (15 wears): **never-worn 23 → 13, idle $2,381 → $1,456** — 10 garments
and $925 stop being an accusation the data could not support.

**THE FINDING from the first 15 wears (07-27): what she WEARS and what she PUBLISHES do
not overlap.** All 15 wears created 15 NEW outfits — not one matched a published look —
and 18 of the 35 garments used by the 18 published looks have never actually been worn.
27 of 58 garments have been worn; 13 appear in neither record.

**HER CALL 07-27, a standing change of target: `/stylist` should suggest outfits SHE WOULD
WEAR, not outfits she would publish.** Everything below is measured against that target.
The v2 pivot to a utility app is the reason; treat wear-prediction as the objective from
here, and published looks as merely the training data that happened to exist first.

**MEASURED 07-27 — held-out test, the 15 wears as a test set the model never saw.** Same
AUC function as the blind 24-outfit calibration (`analyse_stylist_feedback.auc`) so the
numbers are comparable. Sanity check first: published looks vs the whole space scores 0.939
in-sample, so the pipeline is sound. Then, against the held-out wears:

| model | vs whole valid space | vs in-rotation outfits only |
|---|---|---|
| learned affinity (published looks) | **0.660** [0.554, 0.758] | **0.555** [0.440, 0.676] |
| colour + constraints | **0.360** [0.249, 0.482] | 0.385 [0.266, 0.504] |

- **Affinity scores 0.824 on her stated verdicts but 0.660 on her actual behaviour, and
  0.555 — a CI spanning chance — once garment rotation is controlled for.** The second
  column restricts negatives to outfits built only from garments she has worn or published,
  which removes the shortcut of scoring dead stock low. Removing the shortcut removes most
  of the signal: **the model is largely detecting WHICH GARMENTS ARE IN ROTATION, not which
  combinations she will put on.**
- **Colour is now measured BELOW chance (0.360, CI excludes 0.5)** — not merely
  uninformative but inverted against real wears. A stronger version of the 0.491 result.
- **Nothing currently predicts her wears well.** Under the new target that is the headline:
  the best available model is 0.660, and 0.555 once the rotation shortcut is removed.

**MEASURED 07-27 — the open decision is now ANSWERED, and the answer is NO.** Leave-one-out
over the 15 wears, per-fold AUC (each fold has its own model, so pooling scores across folds
would be invalid — for each held-out positive, take the fraction of negatives it beats under
its own fold's model):

| training set | vs whole space | vs in-rotation |
|---|---|---|
| published looks only (today) | 0.660 | 0.555 |
| published + the other 14 wears | 0.540 (**−0.120**) | 0.383 (**−0.172**) |
| the other 14 wears only | 0.622 (−0.038) | 0.549 (−0.006) |

**Feeding `source='worn'` outfits into affinity makes prediction WORSE, consistently across
both negative pools. Do not do it.** **The code now matches: `PRIOR = ("manual",)` in BOTH
`closet_server.py` (live route) and `export_static.py` (deployed pool) — it had been
`("manual", "worn")`, i.e. the exact configuration this measured as harmful. Deployed stylist
prior dropped 33 -> 18 looks.** `NEGATIVE_WEIGHT = 0.0` has a sibling: wears stay out
of `affinity()` too. The reason is the same failure as rejections — **a per-garment scalar
cannot hold context. Wear FREQUENCY is not preference:** she wears jeans and yello-heels
constantly because they are defaults, not favourites, and adding wear counts just ranks by
frequency. In the in-rotation column the boosted garments appear in the negatives too, so
lifting them lifts negatives as much as positives and the score falls below chance.
CAVEAT, stated because 15 is thin: the CIs are wide and overlap A's estimate. The DIRECTION
is consistent across all four cells; the magnitude is not established. Revisit at ~50 wears.
- **TRAP, hit and fixed the same day: `PRIOR` is what TRAINS affinity — it is NOT what counts
  as WORN.** Both stylist paths derived their worn set from `published`, so narrowing `PRIOR`
  to `("manual",)` silently pushed the wildcard's never-worn set back to 23 and the stylist's
  idle figure to $2,381, disagreeing with /insights' 13 / $1,456. Caught on the deployed
  payload. Both paths now take the worn set from `_wear_counts()` — the same function
  /insights uses — so they cannot drift again. The wildcard depends on this: surfacing a
  "never-worn" piece she has actually been wearing is noise.
- **What this does NOT say:** that wear data is useless. It says this MODEL SHAPE cannot use
  it. Predicting wear plausibly needs pairwise/compatibility (already the designated home
  for the blame data), or context (occasion/season/weather — a Tuesday is a context, and
  `outfit.context` already exists), or frequency-NORMALISED affinity that down-weights
  repeats. Those are the candidates; none is built.
- **REPRO IS LOST (confirmed 07-28).** These numbers were produced by
  `scratchpad/heldout_wear_test.py` and `scratchpad/loo_wear_test.py`, which were never
  tracked — there is no `scratchpad/` directory and nothing in git history. **So 0.660 / 0.555
  and the whole leave-one-out table cannot currently be reproduced or extended**, and Phase 6's
  "re-measure at ~50 wears" has no harness: a rebuild risks not matching the original method,
  which would make the before/after comparison meaningless. Rebuilding this as TRACKED code,
  reproducing the 07-27 figures as its acceptance test, is the highest-value $0 work available
  while wear data accumulates. Do not let the next measurement be the thing that discovers this.

**THE ENGINE CANNOT SUGGEST 4 OF HER 15 REAL OUTFITS — and it is not a constraints
failure.** All four return `is_valid: True` with zero hard violations. Three are the same
shape: `bottom + shoes + 59-el-hoodie`. **`59-el-hoodie` is categorised `outerwear` but she
wears it AS THE TOP**, and `gaps.enumerate_outfits()` defaults to `with_outerwear=False`, so
an outfit whose top layer is a hoodie has no `top` and is never enumerated. It is one of her
most-worn garments (3 wears) and the stylist can never offer it. **Her call 07-27: the
hoodie should count as BOTH a top and outerwear.** Note `garment.category` is a
`text NOT NULL` column read in ~55 places across ~20 files, so making it a list is a large
refactor. **FIXED 07-27 the contained way: migration 0005 adds an ADDITIVE
`alt_categories text[]`, and ONLY `gaps._cat()` reads it** — `category` stays `outerwear`,
so /insights grouping, the /wear grid, tryon, dragcut and every other consumer are
untouched. Semantics: `category` is the primary identity, `alt_categories` are additional
slots the garment may fill. `constraints.py` needed NO change — `hard_violations` already
permitted outerwear-as-top (the rule that her own look-023 once failed); the gap was purely
that the enumerator never GENERATED the shape. `enumerate_outfits` also gained a guard so a
dual-role garment cannot be its own outer layer when `with_outerwear=True`.
**Result: worn outfits inside the engine's space 11/15 -> 14/15, space 2220 -> 2320.**
Held-out AUC essentially unchanged (0.660 -> 0.652 / 0.555 -> 0.548) — as expected, since
this was a COVERAGE fix, not a ranking one. Set `alt_categories` in BOTH stores
(migration + `garments/<id>/meta.json`), per the both-stores-or-neither rule.
The one wear still outside is 4-item (`02-jeans + 04-structured-blazer +
07-aritzia-suit-vest + 54-salomon-sneakers`) and needs `with_outerwear=True`, which is a
deliberate space-size choice — not yet revisited.

## Track A — ingestion (2026-07-27), $0 half done

**`/ingest`** (LOCAL ONLY — writes files and shells out to rembg, so it cannot exist on the
static deploy). Drop a photo → name + category → `process` → attributes → `add to closet`.

**Why this half and not the spec's.** Plan §5.A is SAM detection + vision-LLM tagging, both
paid, and fal sits at **-$0.08** so that half is blocked regardless. The gap that actually
hurt was different: `/sourcing` is URL-only, so a garment needed a product page to enter the
closet at all and anything photographed could not be added. Note the spec was written for
cold start (0 → 58 garments); the closet is past that, so the realistic shape is one to three
items at a time.

- **All local, all free**, reusing what this closet already proved: `dragcut.py` (rembg) for
  the cutout, `extract_colors.py` for LAB colour — which already does the white-balance
  normalisation A.3 asks for.
- **A.1's two tiers are decided by whether a clean cutout was possible, and said out loud in
  the UI**: `render_ready` generates, `catalog` only plans. Stating it at ingest is what stops
  a bad photo surprising her at render time instead.
- **Staging is reversible.** The folder is written with `pending: true`; `garment_list()`
  skips pending so a half-finished ingest never appears in the app; `discard` removes it, and
  refuses to touch a committed garment. **Commit writes meta.json AND the Postgres row — both
  stores or neither**, since a garment missing from the DB is invisible to every page that
  reads the snapshot.
- **After ingesting, run `server/scripts/dump_closet.py`** or the other pages will not see it.
- Structured for the paid half: `stage` takes one image and returns one garment, so
  multi-garment detection becomes N calls into the same commit path, not a rewrite.

Verified end to end against production, then removed from both stores (58 garments again).

## Fitting room — looks reach the mirror (2026-07-27)

**Her diagnosis, and it was right: opening a look never tried it on.** Both doors into a look
loaded the slots and left the base avatar on stage — the carousel handoff (`app.js`, which
only called `tryOn()` for `kind === "garment"` with one item) and `loadLook()` on the fitting
room's own rail, which never touched `#stage-img` at all. **Nothing was missing but the wiring:**
all 18 published looks already had a render and a cutout on disk, and `looks_list()` already
served them.

- **`stage_render()` (server) resolves the look's FRONT render** — the untagged
  `outfit_<nums>_<n>.png` — skipping `hidden.json` and pose-tagged stems, chosen by numeric
  suffix (a plain sort puts `_10` before `_2`). Served as a `stage_render` field per look.
  **Poses stay archive-only:** a look published on a pose shows its front twin in the fitting
  room while the posed render remains the archive's. `None` falls back to the base avatar.
- **`showLook()` (client)** is called from both doors. The handoff payload now carries
  `lookId`, with an items-set fallback so a payload written by the older carousel still
  resolves. The feedback bar stays hidden for a whole look — corrective edits need
  `currentGarment` to attribute an edit, and an outfit cannot supply one.
- **`stagedLook` had to exist.** `publish` overwrites the caption with "publishing…" and its
  `finally` restored it via `showAvatar()` — which only ran because `currentRender` was null
  for looks. Putting a render on the mirror silently broke that restore. The staged look is now
  tracked explicitly, re-read from the refreshed manifest (publishing on the front pose mints
  exactly the render `showLook()` wants), and cleared by `showAvatar()` and `tryOn()`.

**THE ASPECT-RATIO ARGUMENT FOR RENDERING FRONT TWINS WAS WRONG, recorded so it is not
re-derived:** front-pose look renders are *not* uniformly square — among the 7 pre-existing
front looks they are 1024×1024, 922×1152 **and** 843×1264. Pose does not predict aspect. And it
would not have mattered either way: `#stage-frame` has been a fixed rectangle with
`object-fit: contain` since July, locked precisely because "42 of 126 renders are not square."
CDP-verified across a look with a render and one without — the mirror held 760×712 in both.
**The real justification for front twins is the archive-only pose rule, nothing else.**

- **Batch sized by audit, not assumption:** `scripts/render_coverage.py` ($0, re-runnable)
  found garment-level coverage already complete — 0 of 58 garments lacking a visible render, a
  v3 render, or a cutout, and 0 of 18 looks missing files. Only **9** looks needed a front
  render, not 11: looks 004 and 006 already had clean untagged front renders on disk from the
  07-19 session, made minutes before their posed versions.
- **`next_suffix()` counts the whole outfit family**, pose-tagged siblings included, so the new
  front renders are not uniformly `_1` (the pilot came out `outfit_42+56+59_4.png`). Harmless —
  `stage_render()` picks by suffix, not by name — but do not assume `_1` means front.

## v1 state (2026-07-19)

- **Repo on GitHub (07-17):** github.com/janicechang2016/virtual-closet — PRIVATE
  until Janice flips it for the portfolio; all rollback tags pushed. **README
  added 07-18** (repo root, first-person as Janice, portfolio-facing: two views,
  pipeline + $0.059/render, budget story, rights note re retailer product photos;
  UI screenshots in `virtual-closet/docs/screenshots/` — headless-Chrome captures,
  she may swap). **Static Vercel export ($0):** `python3
  scripts/export_static.py --out site` snapshots the manifest (`demo: true`,
  generation off) + copies referenced assets (~80MB, 303 files) into `site/`
  (gitignored); root `vercel.json` runs it as the build command with rewrites
  for `/`, `/fitting-room`, `/api/manifest`. The app UIs gate on `M.demo`
  (body.demo CSS): Sourcing link, feedback bar (visibility — footprint kept,
  mirror must not shift), SAVE LOOK / RENDER OUTFIT / publish / delete /
  carousel CTA all hidden; read-only browsing + drag-to-dress instant swaps
  fully work from static files. `M.demo` is never set locally — zero behavior
  change for the live server. Vercel import is Janice's (she owns deploys);
  suggest Deployment Protection until the repo goes public.

- **Mirror reaction (07-17, $0):** while a dragged garment hovers the mirror and the
  stage shows the base avatar, it crossfades to `avatar/avatar-v3/front-receive.png`
  (Janice-supplied nano-banana edit of front.png; locally aligned via human-seg
  bboxes, original at `avatar/avatar-v3-front-receive.png`); drop holds the
  receiving frame ~220ms before the render lands. **UI frame only — never a render
  base.** Renders on stage get the CSS breath (scale 1.015 + brighten) instead —
  per-render hover variants deliberately rejected (cost + face risk). Drag ghost:
  50/57 items fly as bare transparent silhouettes (`scripts/dragcut.py`, run at
  every ingest; on-model→cloth-seg only NEVER general fallback [person-ghosts],
  product shots→general model), 7 fly as framed cards. CDP suite: 11 checks
  (`scratchpad dnd_test4.py` pattern — synthetic PointerEvents via
  --remote-allow-origins=*).

- **Catalog is now 57 garments** (22-gnur-hoodie ARCHIVED 07-16 by Janice — strange
  render off the weakest source; folder in `garments/archive/`, renders in
  `renders/archive/`, restore = move back) (01–05 benchmark + **53 ingested 07-16**: 43 clothing
  + 10 shoes — sizes/brands per `docs/ingest-worksheet.md`, Janice-filled; ingest
  details in decisions.md). New items have NO renders yet — they appear in the
  fitting-room racks but not the carousel (buildItems skips unrendered garments;
  carousel got a Shoes filter). **Render batch pending Janice's approval: 53 fronts
  × $0.059 ≈ $3.13.** raw/ naming: primary view = plain slug (sorts first for
  garment_asset), extras `_back/_side/_alt/_model-*/_detail`; avif→png at ingest;
  transparent sources composited on white (transparency reads as black downstream).
  Difficulty-4/5 (front-only): 23/24 issey, 26 liniss dune, 29 nin, 40 sheer top,
  43/44 subtle-mermaid (a SET, wearable separately, cross-noted). 22 gnur has a
  cloth-seg `_onwhite` (source was grey-on-black). **All 58 rendered + cutouts done
  (07-16, $3.25 + $0.53 fix round, spend $10.13/$25):** batch QA'd on contact sheets;
  10 failures traced to prompts missing the not-part notes → fixed via `SLOT_NOTES`
  category anchor + `exclude_from_photo` meta field in tryon.py (fill it at ingest
  for on-model photos!); 9 re-rendered clean (`_2` suffix, bad `_1`s hidden);
  30-off-shoulder borderline-kept; 45 sundae corrective 07-16 (pasted-on → worn,
  _1 hidden). **Drag-to-dress SHIPPED 07-16, ISC physics + bare silhouettes 07-17**
  (pointer-driven per kaberikram/Interactive-Styling-Canvas: garment cutout rides
  the cursor w/ grab lift + directional tilt + fly-back; 50/57 items fly as bare
  transparent silhouettes via `scripts/dragcut.py`, 7 as framed cards; mirror
  brightens on hover; base avatar swaps to `avatar/avatar-v3/front-receive.png`
  while a garment hovers the mirror + ~220ms "she takes it" hold on drop (UI frame
  ONLY — never a render base; Janice-supplied, locally aligned); drop = slot assignment + tryOn instant swap; position ≠
  meaning; CDP-verified; rollback tag `pre-drag-to-dress`). Collage preview = maybe-later. 360/turntable parked —
  revisit after renders; grab garment BACK views when sourcing.

- Phases 0–4 complete. **avatar-v3 is canon** (2026-07-14): user-supplied 4-pose library
  in `avatar/avatar-v3/` (front / contrapposto / hand-on-hip / 34turn) — new lineage
  superseding avatar-v1 (v1 4-view sheet kept in `avatar/avatar-v1/`). **Whole catalog
  re-rendered on v3 poses 07-14** (`tryon.py --pose <name>`, works for `--outfit` too;
  v1 renders legacy on disk, old look renders in hidden.json). Pose map: 01
  contrapposto, 02 hand-on-hip, 03 front (Janice rejected its drifted contrapposto —
  hidden via hidden.json, which now also governs cutout choice in the server AND
  cutout_render.py), 04 34turn, 05 front, look 01+02 34turn, look 01+02+04 hand-on-hip.
  One pose per saved look; difficulty-4/5 garments stay on front. **Poses are
  archive-only (Janice 07-14): the fitting room shows/corrects front renders exclusively**
  (server filters pose-tagged stems from `renders`). Front v3 renders exist for all five
  garments (01–04 batch $0.235, approved 07-14; 02 corrected twice via the feedback
  loop — navy→pure black, then waistband removed → `02-jeans_nb2_v3_4.png`).
  **Lesson (07-14): chained correctives compound face drift** — two stacked nb2 edits
  made 02's face uncanny despite face-swaps (each edit re-synthesizes the head; swap
  restores identity, not skin texture). Batch fixes into ONE corrective note when
  possible; after edits degrade a face, transplant the head from the cleanest render
  of the same chain locally ($0, alignment is pixel-close) → `02-jeans_nb2_v3_5.png`.
  05's front render was frame-padded locally to square 1824² to match the 1024² v3
  renders (nb2 returned a 1:3 sliver; original at `renders/archive/*_prepad.png` —
  `renders/archive/` is app-invisible).
- Phase 3 benchmark done (`docs/phase3-benchmark.md`): default try-on pipeline is
  **fal-ai/nano-banana-2/edit + fal-ai/face-swap finish** ($0.059/render). NB Pro is worse
  at try-on (re-stages scenes); IDM-VTON needs its `category` param wired.
- Server `scripts/closet_server.py` → http://localhost:8765 (run with
  `ENABLE_GENERATION=1` for live spending). Single-item try-on, multi-item outfit compose,
  feedback→corrective-edit loop, clear-to-base, look save/publish/delete
  (`/api/looks`, `/api/looks/delete`, `/api/publish`) — all working from the UI.
  **Feedback is revisable (07-25):** the toast carries an `undo`, and a `log` button in the
  bar opens a dialog of standing feedback for the current garment, each row undoable.
  `logs/feedback.jsonl` stays APPEND-ONLY — a retraction is a tombstone naming the `ts` it
  voids (`feedback_current()` resolves). Undo lives in the toast/dialog, never in the bar
  itself, so the bar keeps its footprint and the centred mirror never shifts. **Undo
  withdraws the RECORD only: a corrective render that already ran was billed and stays on
  disk.** `GET /api/feedback/history`, `POST /api/feedback/retract {ts}`.
- **`/stylist` — stylist UI (07-25, Track B v1, $0):** ranked outfit suggestions over
  `server/engine`, served by `closet_server.py` from `server/scripts/closet_snapshot.json`
  (refresh with `server/scripts/dump_closet.py`). **Ranking is learned per-garment affinity,
  NOT colour harmony** — measured blind on 24 unseen outfits, colour scored AUC 0.491
  (chance), affinity from her published looks 0.824. Suggestions are flat-lays of existing
  cutouts; nothing renders, nothing spends. Fills exactly ONE ROW — the count follows the grid's
  column count (4 at ~1400px, 3 at ~1120px), since auto-fill makes that a property of the
  window rather than a number to hard-code; the wildcard takes the last slot. Picks are
  diversified (a garment may not repeat until the pool is exhausted, or every card is one
  favourite top), plus one **wildcard**
  built around a never-worn garment — affinity alone would make the stylist a mirror and
  never surface the 23 unworn pieces. Feedback: "wear this" credits every garment; "not
  this" asks **which piece was wrong** and penalises only that one — an unattributed
  rejection cannot be assigned blame and measurably made prediction worse. **Every judgement is revisable:** undo/change on the card, or the `decisions`
  drawer (`/stylist#decisions`) to revisit anything ruled on. The log stays APPEND-ONLY —
  re-judging appends a new verdict, undo appends a `retracted` tombstone, and
  `stylist_current()` resolves newest-wins per outfit. Only the surviving verdict feeds the
  model; an undone outfit becomes suggestable again. Writes
  `logs/stylist_feedback.jsonl`; `server/scripts/sync_stylist_feedback.py` carries it into
  Postgres `interaction_log` (blamed garment in `reason_code`). **Local-only by design:**
  putting `APP_SECRET` in a public page would undo the auth guardrail the hosted-Postgres
  reversal depends on. Hidden in the static demo (`body.demo`) like Sourcing.
  **Design pass 07-26:** flat-lay scaled by category off a shared top line (a flat is not
  the size of trousers); per-card rationale from computed data ("built around your samira
  draped tank"), with names disambiguated by dominant colour since three garments are called
  "scoop tank"; lead suggestion spans two columns; **The text panel is a FIXED 104px** — it is
  bottom-anchored, so a longer item list used to push it upward and cards in a row ended up
  with visibly different text blocks. The black rationale holds 13px (it is the sentence
  worth reading); only the grey block auto-fits, stepping down to as low as 6.5px.
  **Hover = the index lens's chrome-silver wash** (identical gradient to carousel `.gcell`),
  so it is obvious which card an action applies to; suppressed on already-judged cards. Side
  effect: the glass panel finally has a tinted backdrop to work against on hover. The 7 garments with no usable cutout are FRAMED as
  reference photos — generating silhouettes for them was tried and reverted as worse than
  the photo. Queued, not priority: vertical body-stacked outfits, wildcard as a full-width
  interruption.
- **`/galaxy` — Track E constellation (07-26, $0; built on branch `track-e-galaxy`, merged and
  DEPLOYED since 07-26 — figures encrypted like /insights):**
  canvas force graph on the tokens' Ink ground. `/api/galaxy` serves it; no new tables.
  - **Nodes are Bayer-DITHERED dot fields, not photos and not tinted by garment colour.** Dot
    density carries luminance, so a near-black garment (60% of this closet is below L*25)
    renders as a DENSE field of light instead of vanishing. Coverage floored at 0.30 so white
    garments still read. This retired the white plates an earlier pass needed.
  - Colour does STATE only: oxblood ring = never worn, amber = selected. Size = wear count.
  - **Detection HUD on hover** (corner-ticked box, dotted tracking lines, real readout) —
    drawn in SCREEN space after the world transform, so it keeps its weight at any zoom.
  - **The field never rests** (~25px drift/3s); hover slows it to a crawl (motion 0.14) but
    never stops. Load-in mirrors the hamburger glyph resolve.
  - **Reeded glass is a standing right-hand column, and really refracts** — 21 ribs each
    sampling a wider slice and squeezing it, the magnify-and-displace behaviour of real
    fluted glass. Possible only because we own the canvas pixels. The never-worn box and
    detail card layer on top of it.
  - **The glass runs as a real fragment shader (07-26)** on a second stacked canvas that
    takes the field canvas as a texture — ported from Brik's "Refractive Glass Studio" by
    Raquel Gómez Arango, raw WebGL rather than its React/Three.js (one quad, one shader; the
    page stays single-file and offline-capable). It adds mouse-proximity refraction, an idle
    orbit, and a rib-profile knob. **Chromatic aberration ships at 0**: the dithered dot
    nodes are single-pixel high frequency, so separating channels yields rainbow speckle, not
    edge fringing — and colour is exactly what this page's palette rule excludes.
    `drawReededGlass()` remains the no-WebGL fallback.
  - **The glass GATHERS.** Imaging only the strip behind the panel made the column read as
    plain stripes — that strip is empty ground, and refracted black is black (the reference
    looks alive because its source is a full-bleed photo). The ribs instead image the whole
    field to their left, compressed across the column, so the archive appears inside the
    glass as vertical flutes of light. Consequence: `#panel` and `#detail` carry `.74` ink,
    not the old `.34` — against gathered streaks the type was unreadable.
  - **Do not screenshot this page with `--virtual-time-budget`** — it starves the rAF load-in
    reveal and you will capture an empty field. Drive it over CDP on a real clock.
  - Cybercore comes from processing artifacts (dither, refraction, HUD), NOT colour — both
    supplied references were monochrome. Palette unchanged.
  - Worn edges from look co-occurrence; could-pair edges from the constraint engine capped at
    3/node (uncapped is ~520 edges — the hairball the plan warns about).
  - **TIME SCRUBBER BUILT 07-27 (E.4) — and it runs on ACQUISITION, not wear.** The plan
    specs "replaying 12 months of wear history", but the wear log is 15 rows, exactly one per
    day across 2026-07-13..27: replaying it is a ticker, not a constellation. Purchase dates
    span **2018-10 → 2026-07, 27 distinct months**, and carry the real shape — 27 garments
    over seven years, then **31 in 2026 alone** (+14 in April). E.4's own stated payoff, "a
    March purchase that never lit up becomes obvious", is a claim about acquisition. Node
    `acquired` + a `months` list ship in `/api/galaxy`.
    **Presence COMPOSES with the load-in reveal rather than replacing it** — folded into the
    single `rv` value both loops already multiply by, so nodes, edges, halos and plates gate
    at once and edges needed no special case (they were already `min()` across both endpoints).
    **Positions are NOT recomputed while scrubbing:** absent nodes stay in the force sim, so
    garments arrive into the place they will finally occupy and the field fills in instead of
    reflowing under the cursor. Playback advances on the clamped frame delta (~230ms/month,
    ~6s total), so it runs at the same speed at 120Hz as at 60Hz.
    **Two honesty constraints, both load-bearing:** the oxblood ring is TODAY's wear state, not
    that month's — wear history at a past date is unknown, and the page says so in a standing
    caveat line; and the never-worn panel is scoped to garments owned at the cutoff, since
    listing something she had not bought yet answers for a closet that did not exist. An empty
    panel says "none owned at this point" — a header with nothing under it reads as a failed
    load rather than an empty set (E.6's "empty graph reads as broken", in miniature).
    Opens at the last month, so the page looks exactly as it did before the scrubber existed.
  - NOT built: LLM cluster labels (paid), the references' poetic text fragments (their
    conceit, would be costume here).
## Track D — gap analysis (2026-07-27), D.4/D.5 built, D.1 not

**THE FINDING that shaped it: D.4's purchase recommender has nothing true to say about this
closet, and no amount of wear data will change that.** Three measurements:
1. **The hypothetical's attributes cannot discriminate on validity.** `hard_violations` counts
   slots and nothing else, so a bottom at formality 1 and one at formality 5 both unlock
   exactly 220 outfits. D.4's "category + colour band + formality" collapses to category.
2. **That count is pure arithmetic** — a new top unlocks bottoms×shoes, a new bottom
   tops×shoes. It describes the closet's shape, not her.
3. **Nothing is structurally stranded.** `orphans()` returns EMPTY, and all 13 never-worn
   garments already sit in 60–2,220 valid outfits (the never-worn hoodie is in **2,220**).
   The idle $1,456 is a WEARING problem, not a combinatorics one.
**The blocker is structural, not sample size** — more wears shrink the never-worn set but can
never create a structural orphan, so "wait for more data" does not unblock D.4.

**What makes it discriminate: count GOOD outfits, not valid ones** — the same move
`quality_participation` already made for stranded garments. Against a quality bar (the closet's
own median, 0.847) formality and warmth separate cleanly: a bottom at f2–f3 unlocks 209, at f5
only 39; warmth 5 unlocks 30.

**COLOUR IS DELIBERATELY EXCLUDED from `HYPOTHETICAL_DIMS`, and this is the concrete proof of
the standing colour rule.** Held otherwise equal: black bottom **101** good outfits, white
**208**, red 188, green 158. The harmony scorer rewards lightness contrast and penalises the
tonal black-on-black that is her signature — so a colour-aware recommender would confidently
tell her to buy white and avoid black, on a signal measured at **0.360 (below chance)** against
her real wears. A wrong answer delivered with a number attached.

- `engine/gaps.py`: `hypothetical_unlocks()` (sweeps category × formality × warmth, never
  colour) and `rediscovery()` (D.5's "default to unlock, not acquire" — the best outfit she
  ALREADY OWNS for each never-worn garment, ranked by affinity). 41 engine tests.
- **`rediscovery()` needs an outerwear fallback pass:** `enumerate_outfits` omits outerwear by
  default, so a never-worn COAT appears in no outfit and silently drops out of the report —
  the one kind of garment most likely to be sitting unworn. Caught because the never-worn
  hoodie produced no row.
- **`/insights` sections 08–09.** 08 "Bring one back" leads (unlock); 09 "If you were adding
  one" is explicitly framed as *not* a need, and prints the reasoning on the page rather than
  only in the code. **D.5's ≥8-new-outfits gate is NOT used — it is meaningless here**, since
  any bottom clears it at 220.
- **Section 09 shows the best per CATEGORY, not the top N overall.** The sweep's leaders are
  all the same slot at adjacent formalities (209, 209, 209, 209, 201), which compares a garment
  against itself; across slots the numbers actually differ — bottom 209, shoes 176, top 89,
  dress 10.
- **NOT built: D.1 style profile** (LLM-maintained, must be user-visible and user-editable per
  invariant #10). Needs Anthropic calls; the $0 half shipped first per the conserve-credits rule.

## Track D.1 — the style profile (2026-07-28), BUILT. **It powers no feature yet.**

**Say this plainly before spending again: `/stylist` ranks exactly as it did before.** The
profile is a document, not an input — `engine.preference` has never heard of it. What the
Anthropic spend actually buys is a DIAGNOSTIC that surfaces patterns worth turning into
rules, and **her rules are free to enforce forever after**. Two of her five are already hard
constraints in disguise ("never suggest a sneaker with a skirt or dress"; the Keen sandals
rule) — `constraints.py` could apply them at $0/suggestion. **The LLM is the elicitation
cost, not the running cost**, which argues for regenerating at ~50 wears, not weekly.

- `server/scripts/build_profile.py` — one `messages.create` on `claude-opus-5`, structured
  outputs (`output_config.format` + json_schema) so the response cannot come back unparseable.
  **$0 by default**; `--generate` bills. Reads the closet, published looks, wears and stylist
  verdicts (~13KB digest — her whole history fits in one call, no retrieval or chunking).
- `server/scripts/profile_view.py` — READ-ONLY renderer → `style_profile.txt`.
- **`server/scripts/style_rules.txt` IS THE SINGLE SOURCE OF TRUTH FOR HER RULES.** Nothing
  regenerates it. Both scripts read from it.
- **Git split, her call 07-28: `style_rules.txt` is TRACKED; `style_profile.json`/`.txt` are
  GITIGNORED.** Rules are irreplaceable (nothing can regenerate a rule she wrote); the profile
  is regenerable for ~$0.27 and is the sensitive half. A clone with no `style_profile.json` is
  correct, not broken — run `build_profile.py --generate`, or `profile_view.py` for $0 if a
  json already exists. **Do not "restore" the profile to git.** This is about the private repo
  and is independent of standing rule #0, which is what keeps it off the public site.

**COST REALITY — the first quote was wrong by 20x, twice over.** Estimated $0.04/run;
**actual total $0.842 across 4 calls**. Two independent causes, both worth remembering:
(a) **output tokens ran 4–9x the estimate because THINKING BILLS AS OUTPUT** and is on by
default on Opus 5 — a "short JSON answer" is not a short response; (b) two calls were wasted
(see below). `max_tokens` must cover thinking + response TOGETHER: 8000 truncated, it is now
20000. Measured: ~8000 in / ~9000 out ≈ **$0.27 per regeneration**.

**THREE FAILURES, all mine, all worth not repeating:**
1. **Wrong field names cost a whole call.** The digest read `garment_ids`/`reason_code`; the
   feedback log uses **`ids`/`blame`**. It did not raise — all 85 verdicts arrived as
   `no||blame=`, and the model correctly reported that no rejection named a garment. The
   blame data is the single most valuable signal here, and it was silently absent. There is
   now a warning if blame ever parses empty. **When an LLM says the data lacks something you
   know exists, suspect the digest before the model.**
2. **Round-tripping edits out of a REGENERATED document ate her rules twice.** The rendered
   `.txt` was briefly editable; the parser first merged her opening rule into the section
   header and dropped it, then the banner I added itself contained the words "YOUR RULES", so
   the splitter re-anchored there and swallowed the summary, compounding per run. The fix was
   not a better parser — it was moving her rules into a file nothing regenerates.
3. **Spend bypassed genlog** (standing rule #1) and had to be logged retroactively; a
   truncated call slipped past entirely because the early `return 1` sat above the ledger
   write. `record_spend()` now runs BEFORE the outcome checks — a refusal or truncation is
   billed and must be recorded.

**INVARIANT #10 IS VERIFIED END TO END.** Her 5 rules pass in as authoritative, are restated
verbatim in `confirmed_preferences`, and are re-attached to the output afterwards, so a
regeneration cannot overwrite them. The system prompt forbids contradicting them.
**And they measurably changed the reading:** v2 called her sneaker wears a contradiction it
could not resolve; v3, given her rule that weekday wears are work-from-home, read them as
comfort rather than taste, and read the unworn Woodrose/event pieces as "no occasion yet"
rather than dislike. That is the difference between an accusation and an explanation.

**WHAT IT FOUND (v3):** footwear decides almost everything — **29 of 44 rejections blame a
shoe**, while tops and bottoms scatter across 14 garments blamed once each. `52-camper-flats`
is never blamed in 82 verdicts. `53-keen-sandals` was genuinely unresolved (blamed 6,
accepted 4) — **she then resolved it by rule**. Boots are "live but not safe": often accepted
AND often killed. **The sneaker finding is the Phase 6 pairwise signal in prose** — sneakers
were never worn with a skirt or dress, only with trousers or the hoodie, and the rejected
suggestions had paired them with skirts. She confirmed it as an explicit rule.

## Wear CONTEXT — migration 0006 (2026-07-28, $0). Collection, not modelling.

**THE DIAGNOSIS: `wear_log` carried `outfit_id` and `worn_on` and nothing else** — the
thinnest record in the system, and the one that is now the stylist's TARGET. With only what
and when, the only pattern available to learn is which garments are in rotation, which is
exactly what the held-out test measured (0.660, and 0.555 once rotation is controlled for).
Meanwhile **all 18 published looks carry `context.occasion`** — the field sits entirely on the
half of the data that is no longer the target. This is a COLLECTION problem, not a model one,
so nothing here changes a ranking. It changes what the next measurement has to work with.

- **`occasion`** — six slugs, her call 07-28: `work_home`, `work_out`, `day_out`, `dinner`,
  `event`, `home`. **Work SPLITS into from-home and out**, because under the published looks'
  single `work` a WFH day is ambiguous with `home / lounge`, and that is the majority of her
  logging. Two of her five style rules are context claims ("weekday wears are work-from-home",
  "the dresses are event pieces — I've had no events") and **neither was representable before
  this**, so the model could not tell comfort-first from taste.
- **`weather` jsonb** — the ONLY context field that costs her nothing. Derived from `worn_on`
  via Open-Meteo (free, no key, no attribution). `weather_backfill.py` uses the ARCHIVE
  endpoint (reanalysis — what happened, not what was forecast) and falls back to the forecast
  endpoint for the ~5-day lag, tagging which in `weather.source` so the two are never silently
  mixed. Verified: all 15 wear dates return from the archive in one request.
- **THE SWAP (`nearly_wore` / `instead_of`) — the first TRUE NEGATIVE in the dataset.** Every
  negative until now was synthesised from the whole space, which is precisely why controlling
  for rotation collapses the score: the model could win by scoring dead stock low. A swap is a
  negative from the same day, same weather, same occasion, and it is PAIRWISE — where the blame
  data already points (29 of 44 rejections blame a shoe). Shape chosen over a full alternative
  outfit because it is two taps, and a wear is logged tired.
- **THE SWAP CREATES NO OUTFIT ROW**, unlike a wear. A near-miss is a pair, not something she
  put on; minting a `considered` outfit would grow the corpus with clothes she did NOT wear,
  and `_resolve_outfit`'s set-matching would then return that row the day she actually wears
  it. It also cannot inflate wear counts — `_wear_counts()` reads only `outfit_id ->
  garment_ids` and never touches the swap columns.
- **DIRECTION IS VALIDATED, NOT ASSUMED.** `instead_of` must be IN the outfit and `nearly_wore`
  OUT of it. Reversed, the pair records a true negative with its sign flipped — worse than
  collecting nothing — and on a phone the two are easy to transpose. Enforced in the API AND
  made unpickable in the UI (the two selects are drawn from disjoint lists).
- **Everything is OPTIONAL.** A wear with no context is still a wear; losing the wear to enforce
  the field would be the wrong trade. A half-filled swap is sent as nothing rather than as an
  error.
- **`app/wear_rules.py` is pure and DB-free**, split out of `wear.py` because that module
  imports asyncpg and could therefore only be tested where a driver is installed. Same doctrine
  as `engine/`. **62 tests now** (41 -> 50 -> 62).
- **Backfill, her call 07-28: occasion from memory + weather fetched, for all 15 existing
  wears.** `make_wear_form.py` -> browser form -> `apply_wear_context.py` -> SQL, matching the
  established capture pattern (she prefers browser forms). Prints the WEEKDAY beside each date,
  because her own rule keys off it and a bare date two weeks old is hard to place. **The swap is
  deliberately NOT backfilled** — "what did I nearly wear on the 14th" is exactly what people
  confabulate, and a fabricated negative is worse than none. Garment display names come from
  each `meta.json`, not the snapshot, which carries attributes only.
- The generated form addresses rows by `wear_id` where available, else `(outfit_id, worn_on)` —
  unique in practice at one wear a day, and the generated SQL RAISEs rather than trusting it.

**LIVE AND BACKFILLED 07-28. 15/15 wears carry occasion AND weather.** Mix: dinner 6, day_out 4,
work_home 3, work_out 2. Applied by `wear_id`, all 15, no fallback matching needed.

**THE FIRST FINDING FROM OCCASION, and it is the best explanation yet for why nothing predicts
her wears: OCCASION REMOVES 59% OF THE UNCERTAINTY ABOUT FOOTWEAR.** H(shoe) 2.68 bits ->
H(shoe|occasion) 1.11, over 8 distinct shoes in 15 wears.

| occasion | n | shoes |
|---|---|---|
| dinner | 6 | **yello-heels ×5**, flats ×1 |
| work_home | 3 | **sneakers ×3** (three different pairs) |
| day_out | 4 | flats ×2, boots, sneakers |
| work_out | 2 | salomon, loafers |

- **`50-yello-heels` is worn 5 times and ALL FIVE are dinner. Sneakers are worn 5 times and
  NEVER to dinner.** This is D.1's "footwear decides everything" (29 of 44 rejections blame a
  shoe) with the missing variable supplied, and it is the first concrete account of the
  ROTATION SHORTCUT: affinity read yello-heels as a favourite because they are frequent. They
  are not a favourite, they are a DINNER SHOE. Frequency was standing in for context.
- **DESCRIPTIVE, NOT INFERENTIAL — n=15, at most 6 per occasion.** Do NOT build an
  occasion-conditioned ranker on this. It is a reason to keep collecting, not a result.
- **IT ALSO CORRECTS A STANDING RULE, and the correction matters.** `style_rules.txt` says
  "weekday wears are work-from-home ... anything logged Mon–Fri tends to be comfort-first".
  Of 11 weekday wears: **3 work_home, 2 work_out, 3 dinner, 3 day_out** — and of the 5 days
  that were work at all, 3 were from home. The rule holds for HOW SHE WORKS, not for what a
  weekday IS; 6 of 11 weekdays were not work. **D.1's profile leaned on the stronger reading**
  to reinterpret her sneaker wears as comfort rather than taste, and that reading is now
  supported for about a quarter of weekdays. Her file, her call to amend — recorded, not edited.
- Weather landed but says nothing yet: 15 wears, **2 distinct conditions** (rain/cloud) across
  one humid NYC fortnight. Its value is that it now accrues for free.

## GALAXY IS NOW A LIGHT GROUND (2026-07-29, $0) — HER CALL, SHIPPED

**`/galaxy` renders black-on-paper by default.** The near-black Ink field is kept, not
deleted — **`?ground=dark` restores it** — per the standing rule that rejected variants keep a
way back. Note this supersedes the page's own opening comment about an "Ink ground"; the
tokens are now inverted at the root.

**THE THEME IS SET IN A BLOCKING `<head>` SCRIPT, and that is load-bearing.** The header,
legend and panel are markup above the main script, so applying the class down there rendered
the dark chrome and then flipped it. One decision point: the head script sets
`ground-light`, and the main script READS that class rather than re-deriving it from the URL.

- **THE DITHER NEEDS NO NEW MATHS, AND THAT IS THE ARGUMENT FOR IT.** Coverage is already
  `0.30 + 0.70 * (1 - lum)` — dense for dark. On the ink ground those dense dots must be drawn
  in PAPER, so a black garment reads as a dense field of LIGHT: right by density, backwards by
  tone, which is precisely why it needed a paragraph of explanation. On paper the identical
  formula draws dense BLACK dots for a black garment. **The encoding stops needing a note**,
  which matters when 60% of the closet is below L*25.
- **Edges invert their BLEND, not their idea.** `lighter` is additive so crossings bloom; on
  white it adds toward white and edges vanish. `multiply` is the mirror — overlapping strokes
  darken — so the nebula-convergence behaviour survives in ink. `T.edgeGain` (1.9 on paper)
  compensates because multiply needs more ink than lighter needs light.
- **THE GLASS WORKS ON PAPER. I gated it off first and that was wrong.** The reasoning —
  "refracted black is black, so refracted white is white" — ignored that the ribs GATHER the
  field (07-26). The field on paper is black marks on white, which gives refraction plenty to
  bend; the empty-strip problem the gathering fix solved is polarity-independent. It renders as
  flutes of INK rather than flutes of light, arguably with more tonal range, because ink on
  paper spans 0–100% while light on ink is capped by the field's own brightness.
- **What was traded, knowingly: the emitted-light quality.** Dark read as an instrument, light
  reads as an engraved plate. The never-worn row hover became ink WEIGHT instead of a glow,
  because paper cannot emit. **Oxblood never-worn rings read better on white** and match
  /insights, where oxblood already sits on white as the alert token.
- **THE RIGHT-HAND COLUMN CAME IN TWO NOTCHES: 334 -> 254px** (23.9% of a 1400px viewport down
  to 18.1%). The width is **DERIVED, not chosen** — it is `PANEL_W + GLASS_INSET * 2`, so
  narrowing the glass alone would leave `#panel` and `#detail` hanging off the surface they sit
  on. Change either constant and the glass follows; the panels read them back as CSS custom
  properties. This was the answer to "is the glass good UX practice" — measured, the column was
  23.9% of the viewport with a panel on only 22.7% of it, so ~77% was bare refraction carrying
  no information. Narrowing kept the signature and the compositional job (the panels get a
  ground) without the waste, and did not reverse the deliberate standing-column decision.
- **At 230px the panel no longer fitted `.mono`'s .16em tracking** — three of eight never-worn
  rows wrapped, plus the header. Tracking is the cheapest width to give back on short labels,
  so the panel is set at .07em and long names now TRUNCATE with an ellipsis rather than
  wrapping. That is a real trade on the field she scans to locate a garment, made explicitly
  and reversible in one line.
- **A HALF-TOKENISED PALETTE CANNOT BE THEMED, and it failed twice the same way.** The chrome
  was already in `--ink`/`--paper` but every canvas colour was a literal. Two hardcoded
  `rgba(245,243,239,…)` survived the first pass — the edge CORE (white lines on a white ground,
  i.e. **the graph's entire structure invisible**) and the legend swatches for *worn together*
  and *could pair* (paper lines on paper, so the key showed nothing). Both are now tokens
  (`--edge-strong` / `--edge-weak`), so the key and the field are described in one place.

**`cdp.py --gpu` (new): every /galaxy screenshot before 07-29 was the 2D FALLBACK.** Headless
Chrome ran `--disable-gpu`, so `GLASS_GL` went null and `drawReededGlass()` painted the
stand-in — meaning the reeded glass had never actually been reviewed in a screenshot, only its
substitute. `--gpu` uses SwiftShader (software GL, slow, correct). **Use it for any page with a
shader**, or the image shows something the user will never see.

## TOUCH — the interaction half of mobile (2026-07-28, $0)

**Her ask: mobile across the board, layout AND interactions.** Audited at a real 390px WITH
touch emulation (`cdp.py --touch`, which sets `Emulation.setTouchEmulationEnabled` so
`(hover:none)` and `(pointer:coarse)` actually match — without it, hover-gated affordances
look reachable in a screenshot and are not on a thumb).

**LAYOUT WAS ALREADY FINE. The gap was entirely interaction.** Zero horizontal overflow on
any of the six pages, and every page already uses **PointerEvents, never MouseEvents**, so
the gestures were never dead. Two things were genuinely wrong and are fixed:

- **STICKY HOVER, on every page.** Not one page carried a single `(hover:...)` media query,
  so on a touchscreen a tapped element KEEPS its `:hover` state until something else is
  tapped — and these pages dim buttons to `opacity:.72` on hover, so **the button she just
  pressed sits there looking disabled.** Guarded on `(hover:none)`, not a width breakpoint:
  the question is whether a hover exists, not how wide the screen is.
- **TAP TARGETS at 16–35px** across all six (the galaxy sliders were 16). Now `min-height:44px`
  on buttons/selects/ranges under `(pointer:coarse)` — WCAG 2.5.5. Verified: **0 controls
  under 44px on any page**, and desktop is unchanged (buttons still 35px, hover still live).
- **BOTH LIVE IN `nav.js`**, because it is the ONLY file every page already loads. The
  carousel and galaxy are deliberately single-file and offline-capable, so a shared
  stylesheet would cost them that; nav.js already injects CSS into all of them and is
  already in `APP_FILES`. One edit, six pages.

**`/galaxy` was the one page with a real gesture gap.** Fixed:
- **No `touch-action` on the canvas**, so the browser claimed the gesture first — a one-finger
  drag scrolled the page and a pinch zoomed the document, and the pan handler never saw
  either. Now `touch-action:none`; the field IS the interaction surface.
- **Zoom was `wheel`-only, so on a phone the field could be panned but never scaled** — and at
  390px the whole archive is a thumbnail. Pinch added through the SAME pointer events as the
  pan, so there is one gesture model rather than a parallel touch path. A second finger clears
  `dragging`, which is what stops the pinch's release from firing `select()`. Verified: 1× → 3×
  with no node selected on release.

**ALREADY WORKED, DO NOT REBUILD:** tap-to-try-on in the fitting room (`click` on a rack row
calls `tryOn()`; the row's own tooltip says so), tap-to-select on `/galaxy` (`pointerup` with
<4px movement, and the HUD draws from `hover || selected`), the carousel's touch scrolling
(explicit `touchstart/move/end`), and `touch-action:pan-y` on the draggable garment rows —
someone had already thought about letting a long rack scroll while still allowing a drag out.

**THE TRAP THAT NEARLY COST A REGRESSION: a full-page screenshot captures the DOCUMENT, not
"the whole page".** The fitting room's `main` has its own `overflow-y:auto` while `body` is
`height:100vh;overflow:hidden`, so `--full` returned an 844px image of the mirror alone and
read as a broken layout with 58 unreachable rack rows. It scrolls fine —
`main.scrollHeight` 5584 vs 731 — and the stacked mobile layout has been correct since 07-26.
**Check `el.scrollHeight > el.clientHeight` before believing a full-page shot.** Recorded in
`cdp.py`'s docstring too.

**Known and NOT fixed, because it is a design question not a bug:** building a multi-item
outfit needs a drag onto a slot, which is awkward on a phone. Single try-on is a tap and
works; slot assignment has no tap path. Raise it with her before inventing one.

## PHONE LAYOUT — the first REAL 390px audit (2026-07-28, $0)

**EVERY EARLIER "TESTED AT 390px" CLAIM WAS A TEST AT 500px.** Chrome clamps
`--window-size`, verified in BOTH `--headless=new` and `--headless=old`: ask for 390, get a
390-wide image of a 500px viewport. So `carousel.html`'s own 400px breakpoint never fired in
any check ever run here. **`virtual-closet/scripts/cdp.py`** (new, pure stdlib, ~90 lines of
RFC 6455) drives Chrome over DevTools and uses `Emulation.setDeviceMetricsOverride`, which is
the only way to get a true phone viewport. It also drives on a real clock — the documented
workaround for `--virtual-time-budget` starving `/galaxy`'s rAF load-in.

Audit result at a real 390px: **`/`, `/fitting-room` and `/wear` passed** (the fitting room
has no media queries at all and is simply fluid — the 07-26 note claiming it was "fixed" was
right about the outcome, wrong about the mechanism). Three faults found and fixed:

- **`/galaxy` was the real failure.** The reeded glass still rendered as a band across a third
  of the field with nothing layered on it — `#panel`/`#legend` hide below 860px but the glass
  did not. **Fixed in `glassRect()`, NOT in CSS, because there are TWO render paths:** WebGL
  draws onto `#glass`, but when WebGL is unavailable `drawReededGlass()` paints onto the MAIN
  field canvas, which no rule on `#glass` can reach. Both paths already bail on a sub-4px
  rect, so an empty rect disables both from one place and stops the shader running rather than
  merely hiding it. Also: `#controls` and `#hint` were both `bottom:22px`, printing sliders,
  chips, caveat and hint on top of each other; controls are now a bottom bar with a ground,
  `#hint` is dropped on phones (it said "drag to pan · scroll to zoom" on a touch device), and
  `.tnote`'s `white-space:nowrap` no longer pushes the caveat off-screen.
- **The shared nav orphaned its hamburger** on `/stylist` and `/insights`. `nav.js` guarded
  against a column mount but not a WRAPPING row. **The check compares against the mount's
  FIRST child, not the previous last one** — on `/stylist` the header wraps to three rows and
  the burger shares its row with a button that also wrapped, so "is it below the thing before
  it" reads false while the burger is plainly misplaced. **Desktop behaviour verified
  unchanged against the live site on all five pages** (carousel/galaxy floating,
  stylist/insights/wear mounted, before and after).
- Copy, only visible narrow: `/stylist` read **"1 SUGGESTIONS"** when the grid collapses to one
  column; `/insights` said "hover any of them" on a touch device.

## Measurement harness + four foundation fixes (2026-07-28, $0)

- **`server/scripts/wear_model_report.py` — THE MEASUREMENT HARNESS, TRACKED.** Replaces the
  lost `scratchpad/*.py`. Reproduces 07-27 with the figures as its acceptance test (`--check`,
  exit 1 on drift): affinity 0.648/0.543 (expected 0.652/0.548), colour 0.373, in-sample
  sanity **0.940 against a documented 0.939** — that last one is the evidence the METHOD
  matches, not merely the neighbourhood. LOO reproduces too: adding wears costs **−0.123 /
  −0.172** (documented −0.120 / −0.172), pinned separately and failing loudly if it ever stops
  being negative, since that is what justifies `PRIOR = ("manual",)`.
  **THE TRAP IT IS BUILT AROUND: the 07-27 space was STRUCTURAL (2320); her rules cut the
  suggestable space to 1600 on 07-28.** Everything runs `apply_user_rules=False` or it is not
  comparable. `--rules` measures the filtered space and answers a different question — there
  affinity falls to 0.630/0.507, because **her rules removed 720 outfits that were free wins
  for the ranker.** The remaining space is a harder, more honest benchmark.
- **ONE DEFINITION OF "WORN" (`gaps.worn_outfits()` = published + logged).** `engine_report.py`
  passed the RAW outfit list to `unworn()`/`cost_per_wear()`, so a garment counted as worn
  because the stylist once SUGGESTED it — 9 never-worn against /insights' 13, and every
  cost-per-wear deflated. Now 13 / $1,456 on both surfaces, pinned by a test that recomputes
  the /insights figure independently.
- **USER RULES ARE OCCASION-AWARE**, and her third rule is the first derived from BEHAVIOUR:
  **"never suggest a sneaker for dinner"** (6 logged dinners: 5 yello-heels, 1 flats; sneakers
  worn 5×, never to dinner). Rules take `(garments, occasion)`; **`occasion=None` cannot violate
  an occasion rule** — None means "not stated", never "assume the strictest", or the default
  tab would silently shrink on a premise nobody made. Dinner tab 1600 -> 1248; both stylist
  paths verified at 0 violations across 7,200 deployed + 42 live suggestions.
  **`OCCASION_ALIASES` maps the two vocabularies** (published-look labels vs 0006 slugs);
  `dinner` matching in both is a COINCIDENCE, not a design. **`work` maps to nothing on
  purpose** — a look tagged "work" does not say whether it was from home or in an office, and
  0006 split those precisely because that difference matters.
- **THE OUTERWEAR COVERAGE GAP IS A DECISION, NOT AN OVERSIGHT.** One logged wear
  (`02-jeans + 04-structured-blazer + 07-aritzia-suit-vest + 54-salomon-sneakers`) needs
  `with_outerwear=True`. Measured: space 1600 -> 9250, coverage 14/15 -> 15/15, **but 0 of the
  top 12 shown are outerwear (the visible stylist is unchanged), 46% of the top 180 the
  deployed page shuffles from ARE — in a 27–37°C New York July — and the outfit that motivates
  the change ranks 5389 of 9250.** Enabling outerwear does not surface it; it only makes it
  enumerable. **The real fix is to gate outerwear on WEATHER**, which 0006 now collects but
  cannot yet support. Revisit with a winter's data. Pinned by a test so it stays decided.

## Her rules run in the engine (2026-07-28, $0) — the FIRST time her words change `/stylist`

**`constraints.py` now has THREE tiers, not two: HARD (structural) · USER (hers) · SOFT
(judgement).** Two of her five rules in `style_rules.txt` are executable and now filter every
suggestion at $0/suggestion: *never a sneaker with a skirt or dress*, and *never the Keen
sandals with a skirt or dress*. Everything else about the stylist is unchanged — this is a
FILTER, not a ranker; affinity still does the ranking.

- **WHY A SEPARATE TIER AND NOT `hard_violations()` — measured, not assumed.** Checked against
  all 57 outfits: **zero WORN outfits break either rule**, but **two PUBLISHED looks do** (both
  `32-personal-language-skirt` + `53-keen-sandals`) and **neither was ever worn**. Folding these
  into the hard rules would retroactively declare two of her own published looks structurally
  invalid — the exact failure the module header warns about, and the one that already bit
  look-023. Published-but-never-worn is precisely the 07-27 gap, so her rule corrects what gets
  SUGGESTED; it does not claim those looks were never outfits.
- **The affinity prior is deliberately untouched.** Those two looks still train
  `preference.affinity()` — they are real evidence about tops and skirts, and the rule is about
  the shoe. Filtering suggestions and training preference are separate concerns.
- **One insertion point: `gaps.enumerate_outfits(..., apply_user_rules=True)`.** Every consumer
  funnels through it — ranked suggestions, wildcard, gap analysis, rediscovery — so both stylist
  paths (`closet_server.py` live route and `export_static.py` deployed pool) inherited it with
  NO per-path change. That is the fix for the 07-27 trap where the two paths drifted. Pass
  `apply_user_rules=False` for the unfiltered structural space.
- **Cost of the rules, printed by `engine_report.py` rather than buried: 2320 -> 1600 outfits,
  -720 (31%)** — 576 sneaker, 144 Keen. With outerwear 13420 -> 9250. **Nothing is stranded:**
  every garment still appears in a suggestable outfit (sneakers and Keen drop 232 -> 88, losing
  exactly their skirt/dress pairings; dresses 10 -> 5). `orphans()` still returns empty.
- **`KEEN_SANDALS` is keyed by ID, not by `subcategory == "sandal"`** — her rule names that
  specific shoe. It is the only sandal in the closet today, so the two are indistinguishable
  now, but a future sandal must not silently inherit a rule she wrote about her Keens.
- **The engine does NOT parse `style_rules.txt`.** Her prose stays the source of truth and
  nothing regenerates it; the two executable rules are hand-translated into `USER_RULES` with
  her sentence quoted verbatim above each, so drift between the two is visible on sight. This is
  the D.1 lesson applied — round-tripping her words through a parser ate them twice.
- **50 engine tests (was 41).** The +9 include: her rules must never reject an outfit she
  actually WORE, the rules must strand no garment, a non-Keen sandal is not covered, and the
  tiers must stay separate. `test_enumeration_matches_arithmetic` now asserts on the UNFILTERED
  space; the filtered count is derived from slot arithmetic rather than pinned to 1600, so it
  still means something after an ingest.
- Verified on the real deployed payload: **7,200 precomputed suggestions across all six
  occasions, 0 violations** (entries are index-encoded `[[23,1,50],[]]` — decode through
  `payload["garments"]` or a scan silently passes on zero resolved ids).

## PAIRWISE COMPATIBILITY (2026-07-29, $0) — the first model that beats chance on her WEARS. **RANKS `/stylist` ON BOTH PATHS, DEPLOYED.**

**THE HEADLINE: 0.814 whole space / 0.794 in-rotation, against affinity's 0.648 / 0.543.**
The in-rotation column is the one that matters — it restricts negatives to garments she
actually has in rotation, removing the shortcut of scoring dead stock low, and it is where
every previous model collapsed to a CI spanning chance. Pairwise is the **first model whose
in-rotation CI [0.707, 0.871] excludes 0.5.** `server/engine/pairwise.py`, 20 new tests
(engine 56 -> 76).

- **THE SHAPE, NOT NEW DATA, IS MOST OF THE WIN.** Trained on the SAME 18 published looks and
  nothing else, pair structure scores 0.754 / 0.726 where per-garment affinity scores
  0.648 / 0.543. No wear data, no verdicts — the identical evidence, read as pairs instead of
  as a scalar. That retires the standing read that the dataset was the constraint: for the
  in-rotation question, the model shape was.
- **HER BLAME DATA IS LOAD-BEARING, and this is its first use.** Ablated: positives only
  (looks + "yes" verdicts) 0.599 / 0.601; adding the 44 blamed rejections 0.768 / 0.774.
  A rejection naming a shoe is evidence about (shoe, skirt) — it says nothing bad about the
  skirt, which is exactly why `NEGATIVE_WEIGHT = 0.0` was the right answer for a scalar and
  the wrong question to ask of it. **The negatives finally have somewhere to go.**
- **HER "YES" VERDICTS MEASURABLY HURT: 0.809 -> 0.768 when included.** Best variant is
  published looks + blamed rejections ONLY. Mechanism, and it is a known one: the yes-verdicts
  were given on outfits the AFFINITY model chose, so they import that model's taste, and
  stated preference has already been measured as a different target from lived behaviour
  (0.824 stated vs 0.660 behavioural, 07-27). Kept as a documented ablation rather than a
  silent default — n=15 cannot separate 0.809 from 0.768 with confidence.
- **TWO LEVELS, because garment pairs are sparse: only 39% of the pairs in the test set have
  any garment-level evidence.** A pair backs off to its TYPE pair (subcategory x subcategory)
  via hierarchical shrinkage — the type score IS the prior mean for the garment pair, so it is
  one formula and no threshold. Both levels earn their place: type-only 0.733 / 0.743,
  garment-only 0.695 / 0.689, together 0.768 / 0.774.
- **IT LEARNS HER WRITTEN RULES FROM BEHAVIOUR, WITHOUT BEING TOLD THEM.** Type scores:
  `sneaker x skirt` **0.071**, `boot x skirt` 0.190, `flat x skirt` 0.615. Her hand-written
  rule ("never a sneaker with a skirt or dress") and D.1's prose finding fall out of the blame
  data as numbers. The hand-written USER tier in `constraints.py` stays regardless — a rule she
  wrote is not up for re-derivation, and a filter is not a ranker.

**THE FAILURE AUC COULD NOT SEE, and it is the most useful thing here.** Raw pair scoring
measured 0.809 while putting a **DRESS in 10 of its top 12** — dresses are 5% of the space,
appear in **1 of her 15 wears**, and are the pieces her own rules call event wear for events
she has not had. Cause: a two-item outfit (dress + shoes) has exactly ONE pair, so its mean IS
its minimum and nothing can drag it down, while a three-item outfit is always judged by its
weakest of three. AUC did not move because dress outfits are only 120 of 2320 negatives —
floating all of them costs almost nothing on a rank statistic, and costs everything on the row
she actually sees.
- **Fix: `rank_calibrator()` ranks an outfit within its own pair-count class.** Monotone inside
  each class, so it changes no within-class ordering — it only makes the classes comparable.
  Top-12 dress share **10/12 -> 0/12**, distinct garments 16 -> 18 (more variety than
  affinity's 12), and AUC went UP: 0.809 -> **0.814** whole, 0.795 -> 0.794 in-rotation.
- **`top_of_list()` in the harness is now a standing guard** — it prints the two-item and dress
  share of any model's top 12 beside the space's own shares. **A ranking model must be LOOKED
  AT, not only scored**; this pair of numbers is what looking at it costs.
- Size was ruled out as an explanation of the AUC itself: restricted to three-item outfits
  only, pairwise still scores 0.760 / 0.767.

**WEARS MAY TRAIN THIS ONE — the opposite of the affinity finding, and measured the same way.**
Leave-one-out over the 15 wears: **+0.012 whole, +0.005 in-rotation**, against affinity's
**-0.123 / -0.172**. Neutral-to-slightly-positive, i.e. no evidence it helps yet, but the
harm is specific to the scalar and does NOT generalise — a pair either co-occurred or did not,
so repeats cannot inflate it the way wear frequency inflated affinity. **`PRIOR = ("manual",)`
stays correct for `preference.affinity` and must not be quietly reused as a rule about
pairwise.**

- **LEAKAGE GUARD, built because it will matter later:** `load_verdicts()` drops any judged
  outfit she has also WORN. It is 0 today (verified) and will not stay 0 — the wears are the
  test set, and a judged copy of one would train the model on its own answer.
- **Acceptance is a RELATION, not a float.** `PAIRWISE_MARGIN = 0.15` pins "pairwise beats
  affinity in-rotation by a wide margin" (currently +0.231), because that is the claim that
  must survive more data; the exact figures are pinned only as "the data state that produced
  the write-up" and are expected to move. **The 07-27 affinity/colour figures still reproduce
  unchanged** — this work added a model, it did not perturb the old ones.
- **CAVEATS, stated because n is small.** 15 worn outfits and 82 verdicts; every CI here is
  wide. The verdicts are self-selected — they were passed on outfits the old model chose — so
  they describe her judgement of what it shows, not of the closet as a whole. And picking the
  best of six ablations on a 15-positive test set is selection on the test set: the ROBUST
  claim is "pair structure beats a per-garment scalar in-rotation" (every variant except
  positives-only clears 0.726 against 0.543), not any single decimal.
**WIRED AND DEPLOYED 07-29 at commit `3de2a9c`.** She reviewed it locally over 34 verdicts
first, then approved the push — the review is what produced the session findings below.
Verified against the LIVE payload, not the local build: build stamp `3de2a9c`, all six pages
200, Railway `/health` 200 and `/wear` 401, **7,200 live suggestions at 0 user-rule
violations**, dress share of the live top 12 **0/12**, money still sealed (closet value not in
the clear anywhere). The full Vercel build command was run locally BEFORE the push —
`export_static.py` + `lock_money.mjs`, privacy check included — rather than discovering a
broken build in production. **The deployed pool was rebuilt after her session, so her 13 new
blames are already in the live ranking.** Test counts: **76 engine + 31 server = 107.**
**`/stylist` on the deploy stays read-only** (`body.demo`), so judging still happens locally —
which is also the only thing that improves the model.
- **ONE INSERTION POINT, `gaps.ranked_outfits(..., compat=...)`** — the same discipline that
  made her rules land on both stylist paths with no per-path edit. The live route
  (`closet_server.stylist_suggest`) and the deployed pool builder (`export_static.stylist_pool`)
  both pass it, and the model itself is built by **`closet_server.stylist_compat()` — defined
  once and imported by the exporter**, because these two paths silently disagreeing is a
  mistake this project has already made (23 vs 13 never-worn, 07-27). **Verified: the top 50 is
  identical across both paths.**
- **CALIBRATION LIVES INSIDE `ranked_outfits`, against the space it is actually ranking.** That
  is deliberate: `occasion` changes the space, and a percentile borrowed from the unfiltered
  space would be quietly wrong on every occasion tab.
- **`compat_weight = 0.75` (`gaps.COMPAT_WEIGHT`), and it is NOT tuned to the third decimal.**
  On the shipped scoring path, in-rotation: affinity alone 0.507, pairwise at 1.00 -> 0.708,
  0.75 -> 0.708, 0.50 -> 0.710 but two-item outfits climb back into the top 12. The three are
  indistinguishable at n=14. It is 0.75 because affinity is worth keeping as a MINORITY voice —
  a newly ingested garment has no pair evidence at either level and scores a flat 0.5, and
  affinity is what breaks that tie until it has been worn with things.
- **The colour tiebreak was left at 0.25 on purpose.** Sweeping it (0.25 -> 0) moves in-rotation
  0.708 -> 0.709. Below the noise floor, so it stays where it is rather than being churned for
  a number that does not exist.
- **The whole shipped path improves in-rotation 0.507 -> 0.708.** Lower than the pure model's
  0.794 because the colour tiebreak and soft penalties ride along; measured on the SHIPPED
  scoring function rather than on the model in isolation, which is the honest comparison and
  the one that closes the gap between what is measured and what runs.
- **The deployed exporter now READS `logs/stylist_feedback.jsonl`** (it is tracked, so it is in
  the Vercel checkout). If it ever becomes untracked, the deployed pool silently degrades to a
  published-looks-only pairwise model — weaker, still well ahead of affinity, and easy to miss.
  **7,200 deployed suggestions re-verified at 0 user-rule violations.**

- **Latent bug found and fixed in passing:** `unittest.main()` sat MID-FILE in
  `engine/tests/test_engine.py`, so direct invocation ran 49 tests and silently skipped the 7
  `TestPreference` ones while `discover` ran 56. Both now run the full suite.
- **`engine_report.py` WAS CRASHING, and had been before this session** — `pcts.sort()` fell
  through to comparing `render_cache_key` (None) against a str whenever two looks tied, so the
  acceptance-evidence script died partway through its own output. Sorts on the numbers now.
### Her first session on the pairwise stylist (07-29, 34 verdicts) — what it taught

**SHE LIKES IT, AND HER CLICKS AGREE: acceptance 46% -> 62%** (50% -> 67% excluding
wildcards). Same session, different cards, n=34 — corroboration, not proof, but it is
independent of the impression.

**THE TRAP THIS SESSION SET, AND IT WILL BE SET AGAIN: scored on her new verdicts, pairwise
gets 0.557 and affinity 0.725.** Read naively that says the change was a regression. It is
RANGE RESTRICTION: she only ever saw cards pairwise had already ranked at the top — p65-p100
of its own ranking, IQR 13 points — while affinity spreads those same cards over p2-p98, IQR
46. A model that has already filtered out what it dislikes has no variance left to discriminate
with. **A ranker cannot be evaluated on the slice it selected** (the caveat
`analyse_stylist_feedback.py` has always carried, now with a number attached). **The wear log
is the only unbiased benchmark, because no verdict touches it.**

- **On that benchmark her new blames HELPED, mostly by narrowing the interval:** in-rotation
  0.794 -> **0.799**, whole 0.814 -> 0.821, CI [0.707, 0.871] -> **[0.728, 0.863]**. The point
  estimate barely moved; the uncertainty did.
- **Today's 13 blames ALONE score 0.539 — chance.** One session cannot carry this model; it
  refines accumulated evidence rather than replacing it. Do not read a single session as a
  result.
- **THE FRONTIER MOVED FROM SHOES TO BOTTOMS.** Blame was 29/44 shoes (66%) through 07-26;
  this session it was bottoms 6, shoes 5, tops 2. The shoe lesson has been absorbed.
  **`26-liniss-dune-pants` is the new sore point** — blamed 3x in one session against 1x in all
  prior history, in **0 of her 15 worn outfits** and 1 published look. A garment the model likes
  and she does not wear.
- **`51-weejuns-loafers` was over-promoted and she corrected it** — 3 blames, while sitting in
  55 of the top 200 on zero published looks and one worn outfit. Generalised up from
  loafer-shaped evidence; this is the type backoff's failure mode, seen live.
- **THE CLEANEST VINDICATION OF THE PAIR SHAPE.** She blamed `52-camper-flats` on the two-item
  wildcard `34-realisation-allegra-dress + 52-camper-flats` — the FIRST blame those flats have
  taken in 116 verdicts. A scalar would have docked her most-accepted shoe globally (3 of 15
  wears, never blamed). Pairwise penalised only that pairing: **0.833 -> 0.381**, and her flats
  elsewhere were untouched by it. This is exactly the contextual rejection that forced
  `NEGATIVE_WEIGHT = 0.0`, now handled instead of discarded.
- **WATCH THE TYPE BACKOFF: IT IS VOLATILE.** 11 type pairings moved >0.15 on 13 blames;
  `trousers x flat` went 0.667 -> 0.333 on three negatives against one positive, and only **59
  of 231 possible type pairings have any evidence at all**. The mechanism that generalises one
  sneaker to all sneakers overreacts from one trouser to all trousers. Consequence worth
  knowing: a pair with NO garment-level evidence — e.g. `(02-jeans, 52-camper-flats)`, which she
  has neither worn nor published — is 100% type prior and swings with it. **`TYPE_PRIOR` is the
  knob; tuning it on 13 blames would be fitting noise.** Let it accumulate first.

- **AND IT WAS SCORING THE ENGINE'S OWN SUGGESTIONS AS HER TASTE.** The section headed "her 18
  published looks" iterated every outfit row — all 57, including the 24 the stylist proposed
  and the 15 logged wears. Filtered to `source == "manual"`; her published looks sit at **mean
  percentile 42** against the rule-filtered space. **This is the third instance of the same
  confusion** (never-worn 9 vs 13 on 07-28; `PRIOR` vs worn on 07-27): a stylist SUGGESTION is
  not evidence of anything she did.

- **`/insights` — Track C sustainability dashboard (07-26, $0):** cost-per-wear, idle
  value, spend and wear distribution, computed by `insights_data()` from the same snapshot
  the stylist uses. Leads with a **unit chart** (one mark per garment, ramp steps by wear
  count, oxblood for never-worn) and a **meter** for the idle share, then garment
  **photographs** for the never-worn and best-cost-per-wear lists — the subject is clothes,
  and numbers alone read as a spreadsheet about a wardrobe rather than a view of one. **Wears are a FLOOR, not the truth** — they count appearances in the 18
  published looks, the only wear record that exists, so a garment worn often but never
  photographed reads as never worn; every surface says so, because an unqualified "$2,381
  never worn" would be an accusation the data cannot support. Built to the dataviz method:
  headline numbers are stat tiles (not one-bar charts), comparisons are thin bars in a
  single ink with direct labels, per-mark hover tooltips, and a full 58-row table view so
  nothing is gated behind hover. **Not a categorical palette** — one ink for the series plus
  the brand's reserved oxblood `#6F2B2B` alert token for the idle measure only, never used
  without a written label. Local-only like the stylist; hidden in the static demo.
- **`/sourcing` — photo-sourcing UI (07-15):** SYVE-styled third page over
  `ingest_fetch.py` (imported as a module; the only route needing `requests`).
  Paste a product URL → `/api/source/scan` ranks candidates (bytes held in
  memory, served via `/api/source/img?i=`; browser measures real dims —
  server python has no PIL), click-select → `/api/source/save {picks, slug}`
  writes `garments/raw/<slug>.<ext>`. Staged strip lists `garments/raw/*` with
  <1000px "thumb — re-source" flags (currently flags yello-heels, mizuno,
  asics, keen); × discards to `garments/raw/_discarded/` (move, not delete).
  Slug auto-derives from page `<title>`. CLEAR (ghost button, appears after a
  scan) resets the page + drops the server cache (`/api/source/clear`).
  `?url=` prefills + auto-scans (bookmarklet-friendly). Linked from both navs. $0, works without
  ENABLE_GENERATION.
- **One brand ("the archive."), two views, one SYVE language** (white void, black 1px
  hairlines, uppercase Helvetica, italic lowercase wordmark):
  - `/` — **SYVE-style carousel** (`app/carousel.html`, single-file): **OUTFITS ONLY
    as of 07-19** (queued item triggered by Janice with 19 looks published — buildItems
    shows published looks exclusively, category filter nav removed, nav-left = Fitting
    room / Sourcing links; single garments stay in the fitting room racks). Figure
    cutouts (from `scripts/cutout_render.py`, rembg u2net_human_seg), spec-faithful slot
    interpolation + infinite wrap + 80px snap/dwell, x-axis scroll + click-to-center;
    hero slot at 85% of spec size (Janice: full size
    too big); snap ease slowed to 0.08 (07-14); hero click opens the detail overlay
    (item rows + pose, RE-RENDER LOOK wired to the publish pipeline, OPEN IN FITTING
    ROOM as the black primary). Spec: `virtual-closet/design-inspo/`
    (docx + reel).
    A **runway-procession variant** (single-file line receding to a vanishing point, per
    `design-inspo/runway-inspo.avif`) was built and shelved same night — saved at tag
    `runway-procession-v1` (restore: `git checkout runway-procession-v1 -- virtual-closet/app/carousel.html`).
    An **auto-scroll variant** (ambient drift + hover slow-to-crawl) was built and shelved
    2026-07-14 — saved at tag `auto-drift-v1` (restore:
    `git checkout auto-drift-v1 -- virtual-closet/app/carousel.html`).
    **ASCII entrance SHIPPED 07-15** (in carousel.html, from Janice's design handoff at
    `design-inspo/design_handoff_ascii_entrance/`, SYVE-skinned): full-bleed cleaned
    grayscale interior (`app/entrance-bg.jpg`), black glyphs of the handoff quote trace
    its edges (charSize 12, shimmerDepth 0.9 — new knob, handoff twinkle invisible in
    b/w), "enter the archive." label; click → pulse-fade dispel (glyphs stop reappearing,
    photo fades to white, NO ghost) revealing the live carousel; once per session
    (`sessionStorage.archiveEntered`), reduced-motion skip, `?entrance=1/0` debug.
    Previews kept in `design-inspo/entrance-previews/` (options 1–3; see decisions.md).
    **PASSPHRASE GATE — BUILT AND REVERTED 07-27 (her call). NOT IN THE CODE.**
    Explored, fully working, then backed out: **THE SITE STAYS PUBLIC, because she wants
    interviewers to be able to look at it.** Topic tabled, not closed. Do not rebuild
    without a new ask. What it was: click morphed "enter the archive." into a password
    field *inside the same pill*, Enter submitted, wrong answers dissolved into noise.
    Findings worth keeping, since they are what a rebuild would otherwise re-derive:
    - **Vercel Deployment Protection is NOT available to her — paid Pro feature ($20/mo),
      this project is on Hobby.** It was the "real lock" half of the original plan and its
      absence is what collapsed the plan. Do not suggest it again.
    - **The free replacement, researched but NOT built:** Vercel **Routing Middleware**
      (ex-Edge Middleware) is framework-agnostic — a root `middleware.ts` works on a
      non-Next build like this one's Python `export_static.py` — and runs BEFORE the cache,
      so it covers the ~80MB of assets, with the password in an env var rather than in the
      page. Hobby includes 1M invocations / 1M edge requests / 4 CPU-hours free.
      **And it need not cost the morph a single pixel:** protect `/api/manifest` and
      `/assets/*` but let the carousel SHELL through, so the cover stays up while JS
      fetches and builds the archive behind it, then dissolves onto a loaded carousel —
      the current reveal exactly, no navigation. Est. 2–3h.
    - **Any in-page check is ceremony, never a lock** — the deploy is static, so it runs in
      the browser and its secret ships in the page; the carousel underneath is already
      loaded, every garment image is fetchable at its own URL, `?entrance=0` walks past it,
      and `/fitting-room` is reachable directly. If a gate is ever wanted for real, it goes
      at the edge; hardening the page is wasted work.
    - Build notes if it returns: **the pill must be ONE object across both states**, never
      swapped — label in normal flow so it decides the natural width (164px), field
      absolutely positioned so it contributes nothing to sizing, and JS pins the measured
      width before easing to 244px (`width:auto` cannot transition). Refusal was nav.js's
      resolve-out-of-noise run BACKWARDS, borrowing its `POOL` verbatim, eroding to zero
      over 460ms at ~22fps (re-randomising every rAF reads as a strobe); the value must be
      overwritten with noise BEFORE unmasking `password`->`text`, or the real passphrase
      renders for a frame. A switch constant must fail OPEN — a non-empty *invalid* value
      fails closed and locks her out of her own archive (`?entrance=0` is the way back in).
  - `/fitting-room` (`/classic` kept as alias) — **fitting room** (outfit rail | stage |
    racks). Design lineage: Boutique v3 (313NY, tag `boutique-v3`; amber rejected as
    masculine, violet/rose rejected outright) → SYVE restyle 07-13 (tag
    `fitting-room-syve-v1`) → **prettier pass 07-14** (current): mirror stage + gallery
    label, text-first index racks with hover preview, manifest outfit rail, "Nº 313"
    copy removed. Feedback bar keeps its footprint when hidden and fades in place
    (07-15) — appearing must never shift the centered mirror.
  - `renders/hidden.json` — render stems the server keeps out of the app (files stay on
    disk). Size row reads `size_owned` from each garment's `meta.json`; unset = no
    highlight (log real sizes at ingest — not everything is S).
- **Two-view architecture BUILT (2026-07-14, user-approved):** home = archive (`/`);
  fitting room at `/fitting-room` (`/classic` alias). The **look is the atom**:
  `looks.json` is the canonical store (draft → published lifecycle; see decisions.md).
  Doors: archive hero click → detail overlay (items+sizes, pose, re-render, OPEN IN
  FITTING ROOM → localStorage handoff into slots); fitting room SAVE LOOK = free draft,
  PUBLISH = pose-picker + $0.06 render + cutout → appears in carousel. Cross-document
  view transitions morph the hero ↔ stage (`view-transition-name: figure`) — polished
  07-14: 0.55s soft-ease morph over a 0.35s root crossfade; the detail overlay's image
  anchors the morph while open; plain header links clear the names (quiet crossfade,
  morphs reserved for the deliberate doors). Publishing runs the cutout pass via the
  liminal venv subprocess. Poses remain archive-only,
  no exceptions (Janice 07-14): looks arriving via OPEN IN FITTING ROOM load the slots
  and show the base avatar. **Prettier pass shipped 07-14** (mirror stage + gallery
  label, text-first index racks with hover preview, manifest outfit rail — see
  decisions.md); pre-pass design tagged **`fitting-room-syve-v1`**
  (revert: `git checkout fitting-room-syve-v1 -- virtual-closet/app/`). Garment `meta.json` has a `brand` field (all five
  filled — Peachy Den / In This Era / Nin Studio / Musinsa Standard / Woodrose Deli),
  shown as the first line of the archive detail overlay; fill at ingest for new items.
- Spend: **$13.15 of $25 cap** (`python3 scripts/genlog.py summary`; fal $12.31 +
  `claude-opus-5` $0.84 — one shared cap). Big items: July
  catalog batch $3.25 + $0.53 fix round + sundae fixes ~$0.18; Janice's own first live
  loop 07-14 ($0.118) validated the publish pipeline end-to-end.

## Standing rules

0. **THE STYLE PROFILE NEVER SHIPS PUBLICLY (her directive 07-28).** `style_profile.json`,
   `style_profile.txt` and `style_rules.txt` stay off the public deploy. The site is public so
   interviewers can look at it; the profile is a document about *her* — what she wore by date,
   what she rejects, her own note that weekday wears are work-from-home. Enforced, not
   remembered: `export_static.assert_private()` FAILS the build if any file matching
   `style_profile` / `style_rules` reaches the output. Adding a `/profile` page to the deploy
   means deciding to publish her; don't.
1. **Spending:** fal calls only in user-approved batches/envelopes. All calls go through
   `scripts/genlog.py` budget gate; never bypass it — **including Anthropic calls** (07-28:
   the D.1 profile ran outside it and had to be logged retroactively; `build_profile.py` now
   logs before checking the outcome, so a refused or truncated call is still recorded).
2. **Identity:** every render with a visible avatar face gets a `fal-ai/face-swap`
   finishing pass, source `avatar/avatar-v3/front.png` (v3 canon 2026-07-14; v1 renders
   are legacy lineage). Never edit the avatar's head region with NB models (edits collage
   or regress the face — regenerate instead).
3. **Prompts for nb2/edit must be neutrally worded** ("virtual try-on: show the person
   wearing…", never "dress the woman", no body-size adjectives) — its content checker is
   strict. Anti-collage phrasing ("one single figure, not a collage…") in every prompt.
4. **Renders:** `renders/<garment>_<arm>_v3[_<pose>]_<n>.png` (v1 = legacy lineage);
   look renders `outfit_<nums>[_<pose>]_<n>.png`; `_raw` = pre-swap intermediate
   (excluded from the app). Garment-id prefix is how the app matches renders;
   `renders/hidden.json` hides stems from render lists AND cutout choice;
   `renders/archive/` is app-invisible.

## Key commands

```bash
ENABLE_GENERATION=1 python3 scripts/closet_server.py     # app (from virtual-closet/)
python3 scripts/tryon.py <garment-id>                    # one try-on render
python3 scripts/tryon.py <gid> --pose contrapposto       # render on an avatar-v3 pose base
python3 scripts/tryon.py --outfit 01-plain-tee 02-jeans  # multi-item compose
python3 scripts/tryon.py <gid> --correct "wrong fit" --note "…"  # corrective edit
python3 scripts/genlog.py summary                        # spend vs cap
/Users/janice.chang/liminal-wardrobe/.venv/bin/python scripts/extract_garment.py  # cloth-seg cutouts
/Users/janice.chang/liminal-wardrobe/.venv/bin/python scripts/ingest_fetch.py URL [SLUG]  # $0: pull best product image from an ecomm page into garments/raw/ (--list to rank, --pick N to choose, --keep N for extra views)
/Users/janice.chang/liminal-wardrobe/.venv/bin/python scripts/dragcut.py [id ...]  # $0: transparent drag-ghost silhouettes (run at every ingest; on-model→cloth-seg only, product→general)
```

The liminal-wardrobe venv (Python 3.9) has rembg/cv2/PIL; system python3 is 3.9 (no
`str | None` syntax). Headless design QA: Chrome `--headless=new --screenshot=…` then
actually look at the PNG.

- **SHARED NAV (07-26):** `app/nav.js` injects a hamburger on every page. It MOUNTS into the page's own
  top-right cluster (`[data-nav-mount]`) so it aligns with what is already there — but the
  mount is container-aware: a column stack would put it under the readout and a
  space-between row would shove the readout to centre (both observed), so those fall back to
  floating, and in a space-between row the previous sibling is pinned with `margin-left:auto`.
  No box — three hairlines at the site's own weight. **The wordmark links home on every page
  except the archive itself**, where it would be a dead control.
  Opens as a top-to-bottom roll (`clip-path`), then labels **resolve out of noise** — the
  ASCII entrance run backwards, same monospace face, italic. A new route is one line in
  `ROUTES`. Labels render as real text first, so no-JS and reduced-motion get the finished
  menu, never noise. `body.demo` omits local-server routes; nav.js is in
  `export_static.py`'s APP_FILES or the deploy 404s. **Inline per-page nav REMOVED 07-26;
  the pre-removal state is tagged `inline-nav-v1`** (restore:
  `git checkout inline-nav-v1 -- virtual-closet/app/carousel.html`). In-page controls stay
  put — the carousel's Carousel/Index viewtabs are a lens toggle, not navigation.

## Find-a-better-photo → grid pre-fill (2026-07-28) — $0 SKELETON BUILT, NOT YET RUN PAID

**Her call 07-28, and it re-scopes Track A.** The queued note treated
find-a-better-photo and vision tagging as two separate stretch items; she asked for the
combination, and it is better than either half. **THE WIN IS THE PRODUCT PAGE, NOT THE
BETTER PHOTO** — a photo cannot supply a brand or a fabric composition, a product page states
both in text, and `fabric` is the one field her own ingest form gives up on ("models guess
badly at this — yours is better"). The better image is a bonus for the render tier.

- **ONE CALL, NOT THREE.** Anthropic's web search is a SERVER tool, so the model searches
  during the request: photo -> identify -> search -> read the page -> structured JSON.
  No search API, no key. `ingest_fetch.py` keeps its existing job of ranking candidate images
  on whatever page this finds.
- **SAM DETECTION DROPS OUT, SO THIS NEEDS NO FAL TOP-UP.** She photographs one item at a
  time; multi-garment detection was never the slow part. Track A's paid half is now
  Anthropic + local code only. **The fal top-up is off the critical path entirely** (the
  hero-video half was tabled the same day).
- **COST, CHECKED NOT GUESSED: ~$0.059/garment.** Web search is **$10 per 1,000 searches**
  ($0.01 each, capped at 3), plus tokens on **`claude-sonnet-5`** — classification, not
  reasoning, and on introductory pricing ($2/$10 per MTok) through 2026-08-31. `--generate`
  bills; everything else is $0. Spend goes through genlog BEFORE the outcome checks
  (standing rule #1, the D.1 lesson).
- **`effort: "low"` is pinned, not left implicit. THINKING IS ON BY DEFAULT on Sonnet 5 AND
  Opus 5** — that default, more than "thinking bills as output", is why D.1 cost 20x its
  estimate. Correct the older note when re-reading it.
- **FOUR THINGS THE MODEL MAY NEVER SUPPLY**, enforced by a closed schema and pinned by
  tests: **colour** (measured by `extract_colors.py`, invariant #6 — the model may NAME a
  colour, never MEASURE one), **purchase price** (a listing price is NOT what she paid;
  closet value $6,298 and every cost-per-wear in /insights rest on her real data), **purchase
  date**, and **size_owned**.
- **CONFIRM BEFORE PRE-FILL — the safety property.** `identification` is returned SEPARATELY
  from `attributes` and nothing touches the form until she confirms. A confident
  MISidentification is worse than a blank grid: every cell comes back plausible and wrong,
  and she is reviewing rather than composing, so it would pass. `evidence` must cite what is
  IN THE IMAGE, never the search result as its own justification.
- **PER-FIELD PROVENANCE** (`page` / `image` / `inferred`), shown as tags in the UI — page in
  black, image in grey, inferred in the oxblood alert ink. A fabric read off a page is
  trustworthy; a formality inferred from a photo is a guess wearing the same typeface.
- **FAILURE IS THE COMMON CASE AND IS GRACEFUL.** A plain dark garment with no label is
  unidentifiable, and ~60% of this closet is below L*25. Then `identified: false`, no brand,
  no URL, image-only attributes — a worse pre-fill but an honest one.
- Files: `server/scripts/identify_garment.py` (`--stub easy|hard` emits canned payloads of the
  exact API shape, which is what let the whole UI be built and reviewed for $0),
  `POST /api/ingest/identify` in `closet_server.py` (**$0 unless `generate` is explicitly
  true** — billing is never a button press), the identify card in `app/ingest.html`, and
  `server/tests/test_identify_garment.py` (19 tests; **87 total**).
- **NOT YET RUN PAID.** Next step is one approved batch of 3 garments (~18c): one branded and
  distinctive, one plain and dark, one expected to fail — then judge the edit-count reduction
  against that before building further.

## Queued next (do not build until asked)

- **RUNWAY MOTION IN THE CAROUSEL (her idea 07-28, NOT started, discuss cost/feasibility
  first).** As the carousel scrolls, each avatar should appear to MOVE IN REAL TIME — the
  models walking as if on a runway, rather than the stills sliding past. This supersedes the
  motivation behind 4.4's hero-look video, which she TABLED the same day.
  - **She has a KLING subscription, and that is the point.** 4.4 priced video through fal at
    $0.40/segment = $3.20/look, which is what made it hard to justify for a page that produces
    no data. On an existing subscription the marginal cost is roughly zero, so the economics
    are completely different from the ones the completion plan reasoned about. **Do not
    re-quote fal for this without checking Kling first.**
  - Consequence worth noting: with 4.4 tabled, **the fal top-up is no longer on the critical
    path for Phase 4** — it is now needed only for Track A's detection half.
  - Open questions for that discussion, none answered: per-look clips vs one loop; how motion
    interacts with the existing 80px snap/dwell and the slot interpolation; whether it survives
    `prefers-reduced-motion` (it must); payload size on a page already shipping ~93MB of
    assets; and whether Kling output can hold avatar-v3's face across a walk cycle, given the
    standing rule that every visible face gets a face-swap finish (rule #2) and that chained
    edits compound face drift.

- **HER NEXT SESSION, stated 07-27:** (a) evaluate where things stand and what needs
  tweaking — start from `virtual-closet-v2-HANDOFF.md` §3, which was rewritten for exactly
  this; (b) **IMAGE RENDERING UPDATES IN `/fitting-room` — NOT YET SPECIFIED. Ask her what
  she wants changed before touching `tryon.py` or the stage.** This is the one live area that
  SPENDS: every render is a fal call at ~$0.059, standing rule #1 (approved batches only)
  applies, and the fal balance was last seen at **-$0.08**, so a top-up likely comes first.
  Relevant constraints already recorded above and worth re-reading before proposing anything:
  face-swap finish is mandatory on any visible face (rule #2), never edit the avatar's head
  region with NB models, prompts must stay neutrally worded (rule #3), chained correctives
  compound face drift, and difficulty-4/5 garments stay on the front pose.

- **FIND-A-BETTER-PHOTO SEARCH (her note 07-27, Track A stretch, NOT started):** from a photo
  she took, find a better product shot of the same garment on the web. Reverse image search is
  the obvious route and is BLOCKED: Google Lens has no official API, Bing Visual Search was
  retired, and TinEye matches exact image reuse rather than "same garment, better photo".
  The workable architecture is identification-then-text-search, and it reuses most of what
  exists: vision LLM reads brand / label / distinctive details -> text query -> search API ->
  `ingest_fetch.py --list` ranks images on the candidate pages -> she picks in the `/sourcing`
  grid. Only the identification call and the search API are new, and both cost money.
  Caveats to weigh before building: it works on identifiable pieces (this closet is full of
  them) and not at all on a plain black tank; and for ~10 items, searching the brand herself
  and pasting the URL into `/sourcing` is faster and free. The case it genuinely wins is
  garments she cannot identify — a model reading a care label beats her there.

- **GALAXY TITLE FONT (her note 07-26):** explore changing the type for the `/galaxy` page
  title. Currently the shared italic wordmark + uppercase mono label; the page's cybercore
  direction may want something else for the title specifically. Not started.
- **STYLIST "INDEX/CATALOG" NUMBERING — EXPLORED AND DROPPED 07-26 (her call).** From the
  *Stills 2026 Design Trend Report* §2.6. Scoped down in discussion to numbering only, with
  the layout untouched, then four treatments were previewed against real cards: slot number
  on the card, catalogue numbers in the item list, keyed numbers under each garment, and
  slot+catalogue. **Her verdict: none of them; topic closed.** Do not rebuild without a new
  ask. Two findings worth keeping if it ever returns:
  - **A keyed plate cannot be done without moving things.** `.flat .it` cells are full
    height, so a number placed under a garment either lands behind the fixed 104px panel or
    forces the flat-lay to reflow (`flex-direction:column` shifts the whole composition).
    "Numbering only, no layout change" and "keyed numbers" are mutually exclusive here.
  - **A card slot number means nothing on this page.** Suggestions re-roll on every "suggest
    again", so `[01]` labels a position that is not stable — catalogue styling without
    catalogue substance. Only the garment ids (`01`…`58`, already a real catalogue) carry
    meaning, which is the one variant that had any argument behind it.
- **REFERENCE GLASS CODE — DONE 07-26.** Ported to a WebGL layer; see the `/galaxy` notes
  above and decisions.md. Aberration ships at 0 by measurement, not by omission.
- **GALAXY GROUND / BACKGROUND IMAGE (her note 07-26, TABLED — discuss):** the glass effect
  is limited by what is behind it. A near-black ground gives refraction almost nothing to
  bend, which is why the flutes had to be given light to catch and why the ribs gather the
  field rather than the strip behind them. A non-black ground — a photograph, a texture, a
  luminous field — would exaggerate the effect the way the reference's full-bleed image does.
  Not started; it touches the page's Ink-ground palette decision, so discuss before building.

- **PHONE LAYOUT FIXED AND DEPLOYED 07-26.** Both public pages (archive carousel + fitting
  room) had no media queries at all and broke at 390px — overlapping HUD panels, ~39px
  flanking figures, a mirror squeezed to a 50px strip. Fixed and verified at a true 390px
  viewport. The fix is on `main` and live: the build stamp at `/api/manifest` reports the
  deployed commit, and the media queries are present in it.

- **2D reboot handoff (2026-07-24):** this branch intentionally resumes from
  the approved pre-360 UI snapshot. The complete tracked 360/avatar-v4
  exploration and its detailed context are preserved on
  `archive/360-avatar-v4-20260724` (tip `ef96165`); the remaining 2.1 GB of
  generated/vendor assets are at
  `/Users/janice.chang/wardrobe-v3-360-local-assets-20260724/`. Hair work is
  paused with the 3D exploration, not discarded.
- **CAROUSEL DETAIL GLASSMORPHISM EXPLORATION (requested 07-23):** when a look is
  clicked in the archive carousel, explore a glassmorphism treatment for the
  detail/preview panel that opens. Treat this as a visual-design study first,
  preserving the existing hero transition, legibility, and action hierarchy;
  do not ship it until Janice reviews the direction.
- **Look cards — the grid/index lens ALREADY SHIPPED (verified 07-28).** This entry used to
  say a dense grid view was "still queued once the archive grows past ~10 looks"; the archive
  is at 18 and `carousel.html` has had the Carousel/Index viewtabs, the `.gcell` grid and
  drag-reordering for some time. Do not rebuild it. Genuinely still open: any coverflow
  treatment from `~/liminal-wardrobe-v2/spec/design/CARD-PIPELINE.md`.
**Standing rules that outlived their queue entries** (the work itself shipped in July —
these are the constraints to honour, not tasks):
- **Poses:** assign one per saved look at creation (~$0.06/render). Do NOT re-pose via
  nb2/edit prompt language alone — it's an editor, and re-posing fights it. Difficulty-4/5
  garments stay on the front pose (03 plissé AND 05 draped maxi — check `difficulty` in
  meta.json, not folder names; 03's drifted contrapposto rejected 07-14, hidden not deleted).
- **Sourcing quality bar:** source-photo ≥1500px long side; ghost-mannequin/flat-lay >
  on-model > editorial; grab BACK views for any future turntable work. Dropped items sit in
  `_discarded/` and can be re-sourced any time: bitter-cells jacket, realisation scarlet, the
  "uniqlo" parka (actually Aritzia per baked-in tooltip), reformation leather dress.

**Still genuinely queued, not started:**
- **Galaxy (`/galaxy`, Track E)** — last of the three v2 UI candidates and the designated
  home for the parked glassmorphism study. Needs design direction first.
- Deferred by explicit decision, revisit only if suggestions go stale: stylist explore mode,
  pairwise garment compatibility, vertical body-stacked outfit cards, wildcard as a
  full-width interruption.
- **fal balance** was **-$0.08** (07-22); one pilot segment is $0-recoverable once topped up.
- **360/avatar-v4** exploration parked on `archive/360-avatar-v4-20260724` + 2.1GB of assets
  at `~/wardrobe-v3-360-local-assets-20260724/`.
