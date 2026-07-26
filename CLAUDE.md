# Virtual Closet (wardrobe-v3)

Photorealistic virtual try-on with a persistent personal avatar, now extending into a
utility wardrobe tool. Working code in `virtual-closet/` (the 2D app) and `server/` (the v2
backend + engine); running decisions in `virtual-closet/docs/decisions.md` (read it — it
carries the standing rules). Plans: `virtual-closet-execution-plan.md` (v1),
`virtual-closet-plan-v2.md` (v2 spec), `virtual-closet-v2-foundation-plan.md` (Phases 0–2),
`virtual-closet-v2-HANDOFF.md` (cold-resume).

## v2 state (2026-07-26) — foundation + engine + stylist all done, $0.00 API spend

Branch `2d-reboot` (pushed). `main` is untouched and is what Vercel builds the live archive
from — **do not merge**.

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
  `preference.py` — pure functions, 33 stdlib unit tests, no I/O. `dump_closet.py` snapshots
  Postgres to JSON so the engine needs no database. 2220 valid outfits = (21×10 + 12)×10.
- **THE FINDING that shaped everything after it: colour theory does not predict her taste.**
  Measured blind on 24 outfits the model had never seen — colour + constraints AUC **0.491**
  (chance), learned per-garment affinity **0.824**. Hard constraints filter, learned
  preference ranks, colour is a low-weight tiebreak. Rejections are collected but NOT
  applied (`NEGATIVE_WEIGHT = 0.0`): measured twice, they cost accuracy, because a rejection
  is contextual ("wrong shoe for this outfit") and a per-garment scalar cannot hold that.
- **Track C preview:** 23 of 58 garments appear in no published look, **$2,381 idle**.
- Deferred, recorded, NOT priorities (her call): explore mode, pairwise compatibility,
  vertical body-stacked outfit cards, wildcard as a full-width interruption.

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
  "scoop tank"; lead suggestion spans two columns; ambient state line (garments / looks /
  never worn / idle value / judgements). **The text panel is a FIXED 104px** — it is
  bottom-anchored, so a longer item list used to push it upward and cards in a row ended up
  with visibly different text blocks. The black rationale holds 13px (it is the sentence
  worth reading); only the grey block auto-fits, stepping down to as low as 6.5px.
  **Hover = the index lens's chrome-silver wash** (identical gradient to carousel `.gcell`),
  so it is obvious which card an action applies to; suppressed on already-judged cards. Side
  effect: the glass panel finally has a tinted backdrop to work against on hover. The 7 garments with no usable cutout are FRAMED as
  reference photos — generating silhouettes for them was tried and reverted as worse than
  the photo. Queued, not priority: vertical body-stacked outfits, wildcard as a full-width
  interruption.
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
- Spend: **$10.24 of $25 cap** (`python3 scripts/genlog.py summary`). Big items: July
  catalog batch $3.25 + $0.53 fix round + sundae fixes ~$0.18; Janice's own first live
  loop 07-14 ($0.118) validated the publish pipeline end-to-end.

## Standing rules

1. **Spending:** fal calls only in user-approved batches/envelopes. All calls go through
   `scripts/genlog.py` budget gate; never bypass it.
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

## Queued next (do not build until asked)

- **PHONE LAYOUT FIXED 07-26, NOT DEPLOYED.** Both public pages (archive carousel +
  fitting room) had no media queries at all and broke at 390px — overlapping HUD panels,
  ~39px flanking figures, a mirror squeezed to a 50px strip. Fixed on `2d-reboot` and
  verified at a true 390px viewport. **`main` is untouched, so the live site is still
  broken** — merging + redeploying is Janice's call.

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
- **Look cards, remaining half:** the content-unit half shipped with publish (rembg
  cutout → cleanup → crop, per CARD-PIPELINE). Still queued: a dense **grid/index view**
  of all looks (second lens beside the carousel) once the archive grows past ~10 looks,
  plus any coverflow treatment from `~/liminal-wardrobe-v2/spec/design/CARD-PIPELINE.md`.
- **Pose rollout DONE** (see current state) — going forward: assign one pose per saved
  look at creation (~$0.06/render). Do NOT re-pose via nb2/edit prompt language alone
  (it's an editor; re-posing fights it). Difficulty-4/5 garments stay on the front pose
  (03 plissé AND 05 draped maxi — check `difficulty` in meta.json, not folder names;
  03's drifted contrapposto rejected by Janice 07-14, hidden not deleted).
- **Render batch for items 06–58** (53 × $0.059 ≈ $3.13) — Janice said no exclusions
  (worksheet Q7) but the spend envelope itself is NOT yet explicitly approved. Run as
  ONE batch when approved; difficulty-4/5 stay front (they all only get front anyway);
  after renders, run cutout_render.py so the carousel picks the new figures up.
- **Drag-to-dress** (fitting room): next build after the render batch. Sourcing notes:
  `scripts/ingest_fetch.py` / the `/sourcing` page pull best-res product images;
  source-photo bar ≥1500px long side, ghost-mannequin/flat-lay > on-model > editorial;
  grab BACK views for the future turntable idea. Dropped items (in `_discarded/`, can
  be re-sourced any time): bitter-cells jacket, realisation scarlet, the "uniqlo"
  parka (actually Aritzia per baked-in tooltip), reformation leather dress.
