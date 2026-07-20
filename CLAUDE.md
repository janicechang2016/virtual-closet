# Virtual Closet (wardrobe-v3)

Photorealistic virtual try-on with a persistent personal avatar. Single-user, local-first.
Working code in `virtual-closet/`; plan in `virtual-closet-execution-plan.md`; running
decisions in `virtual-closet/docs/decisions.md` (read it — it carries the standing rules).

## Current state (2026-07-20)

- **THE LOOKS ERA (07-19–20):** she published 19 looks (~$1.19) and then deleted one,
  so the archive is **18 published looks**, titled **"look 001"–"look 018"**. Title ≠ id
  and the drift is now large — carousel order is her 07-20 drag pass: **look-006 leads**,
  then look-014, look-013, … look-023 last (read `looks.json` for the live mapping;
  don't assume title order matches id order). `look-015` (43+44 subtle-mermaid set +
  52 flats) **deleted by her via the UI 07-20** — renders stay on disk
  (`outfit_43+44+52_1*.png`) and the entry survives in commit `8b309cc`, so restoring
  is $0. Server default-titles new looks from the *id* number, so the next save
  suggests "look 024" — rename at the prompt.

- **ORDER IS THE `looks.json` ARRAY (07-20):** nothing sorts anywhere — `load_looks`
  preserves file order, `buildItems` walks it — so reordering is a **$0 edit, no
  re-renders**. **`START_LOOK` is now `null`** = land on whatever is FIRST; it had been
  pinned to `look-006`, which silently swallowed a manual reorder and made it look
  like reordering "didn't work". Set it to a look id only if you want a fixed hero
  again — and know that it hides order changes when you do.
  - **DRAG-TO-REORDER SHIPPED 07-20** — index lens only (the grid is the one place
    order is legible; the carousel stays read-only). Pointer-driven cell drag w/
    floating ghost card, dimmed source, 3px black insertion bar; 6px threshold keeps
    a plain click opening the detail overlay (a committed drag rebuilds the grid so no
    trailing click fires; an aborted one is swallowed by a one-shot capture listener);
    ESC aborts. Optimistic → `POST /api/looks/reorder {order:[ids], renumber:true}`,
    reverts + alerts on failure. Server permutes only the payload's ids among the slots
    they already own, so drafts hold absolute positions. CDP 13/13
    (drag mechanics, persistence, renumbering, click-vs-drag, hero-follows-order).
  - **Titles follow position, on BOTH write paths (07-20):** shared `renumber_looks()`
    — the nth *published* look is "look 00n"; custom names survive but still consume
    their slot number; drafts untouched. Delete used to skip renumbering and leave a
    hole (that's how look-015's gap at "look 012" appeared) which the next drag would
    then silently close; the two paths now agree by construction. `/api/looks/delete`
    returns the refreshed `looks`, and the fitting room already re-fetches the manifest.

- **DEMO CHROME PARED BACK (07-20, static export only):** `body.demo` now also hides the
  **budget meter** (`#nav-cost` + `#cost-meter`, plus its dangling separator dot in the
  fitting-room strip) and the carousel's **"Archive demo" status line** (`#nav-gen`) —
  nothing is spendable from the export, so a frozen $/cap is just a question generator,
  and the public build shouldn't announce itself as a demo. The deployed carousel's
  top-right now carries only the avatar version. **Local is unchanged** (meter live,
  line reads "Generation live"/"Copy-prompt"). The fitting room still shows
  "read-only demo" in its strip — left deliberately, rewording is an open offer.
  **Why the deploy is read-only at all:** it's a static snapshot with no Python process
  and no `FAL_KEY`, so renders/publish/save/delete/reorder/sourcing/spin are all
  server-dependent and gated off; browsing, index lens, detail overlay and
  drag-to-dress swaps work fully. Hosting it truly live would put a public endpoint in
  front of the fal budget — **declined 07-20** as against the standing $0-first rule.

- Carousel = **outfits only** (see the two-views section). A vortex-boots look was
  deleted by her via the UI 07-19 (renders stayed on disk), as was look-015 on 07-20.
  **`look-023`** (59-el-hoodie + 42-sagittarius + 56-mizuno — titled "look 018" as of
  the 07-20 renumber) went through the full gauntlet: zip-up invention corrected, pants
  length corrected (meta was wrong, not the render), **hood-up variant is its carousel
  figure** (Janice's pick; hood-down `_2` kept unhidden as chain reference).

- **360 SPIN (07-19, BUILT + pilot CLEAN; full batch HOLDING):** fitting-room ONLY —
  Janice amended her "poses/angles are archive-only" rule for angle frames; archive
  posed-look system untouched; correctives stay front-frame-only. 8 frames at 45°
  (`avatar/avatar-v3/turn-045…315.png` — Janice-supplied nano-banana singles off
  front.png, originals in `avatar/turn-bases-original/`, aligned via human-seg
  bboxes to front.png geometry; quarters run shallow ~20°, accepted). Pipeline:
  `tryon.py` ANGLES/`spin_frame` (rear frames auto-attach garment `*back*` raw
  photos as ground truth; face-swap ONLY on a045/a315 — no face on rear/profile
  frames, so those cost $0.039 not $0.059; `--spin` CLI), `/api/spin` (probe =
  frames/cost/no-back warnings; then per-angle generate so progress shows and
  aborts resume free), angle stems (`_a###_`) filtered like pose tags, mirror
  scrub viewer (drag 40px/frame, ESC exits), billed-batch confirm modal, and the
  **receive gesture baked in**: garment dragged over a mid-spin mirror steps her
  back to front first, then front-receive plays. CDP 11/11 with stubs. **Pilot
  (`look-023` hoodie combo, $0.31) CLEAN** — band continuity via back photos, profiles
  correctly handed (small contact sheets MISLEAD on handedness; verify full-size).
  **Cap raised to $45 (Janice +$20, credits confirmed). Full batch = 58 garments +
  18 outfits ≈ $23.79 — HOLDING until her back photos land** (else ~35 invented
  rears get paid twice). Back-photo priority list delivered 07-19 (A: distinct
  backs — 03/05/06/07/37/43/44, dresses; B: all shoes need heel views; C: symmetric
  basics skippable); 3 backs + 2 sides rescued from mislabeled `_alt` files ($0).
  Fitting-room spin of a look needs its front-pose outfit render first (~$0.059).
  Her server was restarted 07-20 and now carries `/api/spin` and
  `/api/looks/reorder` — but it came back up **without `ENABLE_GENERATION`**, so
  restart it with the env var before any billed run.

- **Index lens (07-19, SHIPPED):** `/?view=index` or the **Carousel / Index toggle**
  in carousel.html nav-left — dense SYVE hairline grid of all published looks over
  the carousel (native scroll; wheel/touch/morph guarded; #info/#controls hidden
  while up; cells open the shared detail overlay). Hover = **chrome-silver gradient
  wash** (Janice rejected the black invert as too heavy; the silver is a deliberate
  whisper of the shelved Holo Mirror skin). CARD-PIPELINE's transferable polish
  kept (one figure height, bottom baseline, min-height captions).

- **59-el-hoodie ingested + rendered (07-19):** Janice's "EL-hoodie" webps =
  **Eckhaus Latta** (baked-in shoulder print identified it), painted-band pullover,
  size M, difficulty 3, model front/alt/back views banked. Render `_1` invented a
  full-zip worn open → **new failure flavor: nb2 invents garment CONSTRUCTION** —
  root cause: BOTH prompt paths hard-coded outer layers "worn OPEN". Fix: per-garment
  **`wear_note` meta override** (59: "worn CLOSED as a pullover — no zipper") honored
  by single AND outfit paths; outfit path also finally carries `exclude_from_photo`
  (the 07-16 fix had only reached the single path). Also: 42-sagittarius meta said
  "cropped ankle" — WRONG vision tag, pants are full length (owner's word + product
  photo override auto-tags; meta corrected).

- **README (07-19):** outfits-only carousel copy; fitting-room visual is now an
  **animated drag-to-dress GIF** (`docs/screenshots/fitting-room-drag.gif`, CDP
  screencast capture at $0, ~5MB — per-frame palettes REQUIRED, shared palettes
  speckle the face red); sourcing screenshot added + note that the static demo
  excludes /sourcing (live-server dependent). Fresh 1440×900 captures of both views.

- **Fitting room looks rail (07-19):** looks index scrolls independently (slots +
  action buttons pinned, racks' 6px black scrollbar), per-row "in archive" badge
  dropped (publish button marks drafts), save scrolls the new draft into view.
  A look hover-preview frame was built, shown, and **REJECTED by Janice — do not
  rebuild.**

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

- **Catalog is now 58 active garments** (01–05 benchmark + 53 ingested 07-16 +
  59-el-hoodie 07-19; 22-gnur-hoodie ARCHIVED 07-16 by Janice — folder in
  `garments/archive/`, renders in `renders/archive/`, restore = move back;
  sizes/brands per `docs/ingest-worksheet.md`, Janice-filled; ingest
  details in decisions.md). raw/ naming: primary view = plain slug (sorts first for
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
  (server filters pose-tagged stems from `renders`). **AMENDED 07-19 for angle
  frames only:** the 360 spin's `_a###_` frames live in the FITTING ROOM (scrub
  viewer); posed looks remain archive-only and correctives remain front-only. Front v3 renders exist for all five
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
    as of 07-19** (queued item triggered by Janice with 19 looks published, 18 now — buildItems
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
- Spend: **$12.09 of $45 cap** (`python3 scripts/genlog.py summary`; cap raised from
  $25 on 07-19, Janice +$20 for the spin batches). Big items: July catalog batch
  $3.25 + $0.53 fix round; Janice's 19-look publish run ~$1.19; hoodie saga $0.24;
  pilot spin $0.31. Reserved: ~$23.79 for the full spin batch (holding — one fewer
  outfit since look-015's deletion).

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
python3 scripts/tryon.py <gid> --spin                    # 7 missing 45° spin frames (garment)
python3 scripts/tryon.py --outfit <gid> <gid> --spin     # spin frames for an outfit combo
python3 scripts/genlog.py summary                        # spend vs cap
/Users/janice.chang/liminal-wardrobe/.venv/bin/python scripts/extract_garment.py  # cloth-seg cutouts
/Users/janice.chang/liminal-wardrobe/.venv/bin/python scripts/ingest_fetch.py URL [SLUG]  # $0: pull best product image from an ecomm page into garments/raw/ (--list to rank, --pick N to choose, --keep N for extra views)
/Users/janice.chang/liminal-wardrobe/.venv/bin/python scripts/dragcut.py [id ...]  # $0: transparent drag-ghost silhouettes (run at every ingest; on-model→cloth-seg only, product→general)
```

The liminal-wardrobe venv (Python 3.9) has rembg/cv2/PIL; system python3 is 3.9 (no
`str | None` syntax). Headless design QA: Chrome `--headless=new --screenshot=…` then
actually look at the PNG.

## Queued next (do not build until asked)

- **FULL SPIN BATCH (approved, HOLDING):** 58 garments + 18 outfits × ~$0.313 ≈
  $23.79 via `tryon.py … --spin`. Fire when Janice's back photos arrive (she's
  sourcing per the 07-19 priority list — A: distinct backs, B: shoe heel views,
  C: skippable symmetric basics) OR on her explicit "fire anyway". Ingest incoming
  backs into each `garments/<id>/raw/` as `*_back.*`; QA one batch tranche before
  the next. Items still lacking backs render invented rears — flag them for QA.
- **Pose rollout DONE** — going forward: one pose per saved look at creation
  (~$0.06/render). Do NOT re-pose via nb2/edit prompt language alone. Difficulty-4/5
  garments stay on the front pose (check `difficulty` in meta.json, not folder names).
- **Look cards, coverflow remainder:** the grid/index lens SHIPPED 07-19; any
  coverflow treatment from `~/liminal-wardrobe-v2/spec/design/CARD-PIPELINE.md`
  remains available if she ever wants a third lens.
- Sourcing notes: source-photo bar ≥1500px long side, ghost-mannequin/flat-lay >
  on-model > editorial; grab BACK views (spin rears use them as ground truth).
  Dropped items live in `garments/raw/_discarded/`, re-sourceable any time.
