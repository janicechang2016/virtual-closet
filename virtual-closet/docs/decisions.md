# Decision log

## 2026-07-22 (later) — Spin viewer: aligned detents beat interpolation

Janice wanted the 360 scrub to be a smooth photoreal animation, and flagged
that the mirror's grey square changed size per frame. Both trace to one cause:
**nb2 draws the figure at wildly different scales (974–1755px tall) on
differing canvases (560×1835, 843×1264, …).** So the visible photo-canvas
changed shape in the mirror, and naive frame interpolation ghosted.

Tried tier-2 **RIFE interpolation** (rife-ncnn-vulkan, local, $0) to synthesize
64 in-between frames → real ghosting from ~frame 10 on (Janice caught it). Root
cause: the avatar turn-base quarters run shallow (~20°, noted back on 07-19), so
the a045→a090 gap is a ~70° rotation — too big for optical flow, it smears the
face mid-gap. **PARKED** behind `spin_smooth.py --interp`; `tools/rife-ncnn-vulkan`
kept (gitignored). True continuous rotation needs image-to-video segments
(tier 3, per-segment $ + identity risk) — declined for now.

**Shipped instead: aligned detents (`spin_smooth.py`, default mode, $0).**
rembg human-seg measures the figure per frame; frame 0 is the untouched canon
(entering spin changes nothing on the mirror), frames 1–7 are rescaled to the
canon's figure height, feet on its baseline, centered on its axis, on a canvas
of the canon's exact size padded with each frame's own edge tone. 8 frames →
`renders/spin/<key>/f00..f07.jpg` (gitignored; rebuild `--all`). Mirror now
CDP-constant across all frames (measure load-synced — a raw getBoundingClientRect
mid-src-swap reads a collapsed box and lies). Scrub still uses the crossfade,
now dissolving between properly-aligned frames instead of scale-jumping ones.
Honest limit told to Janice: this is clean stepped rotation with soft blends,
not true continuous motion.

Posed-front looks (9 of 18 have hand-on-hip / contrapposto / 34turn published
renders, no neutral front): `frame_paths` falls back to the posed render as
frame 0 — mirror stays constant, but the pose carries into the 0° detent
(contrapposto/hand-on-hip read fine; 34turn is a slight pre-turn). Fixing those
properly = a neutral front outfit render each (~$0.06×5), deferred to Janice.

## 2026-07-22 (later) — Spin batch COMPLETE: 58 garments + 18 looks × 7 frames

All spins rendered and QA'd (~$26.9 total, genlog $38.97/$45, 1071 gens).
Closing-phase lessons on top of the morning's:
- **Outfit spins drift differently than garment spins:** backgrounds shift
  (look-006 a225), skin tone can drift (look-010 a090), a 4-item look can
  drop its outermost layer on rear frames (look-021 — took a wear_note
  pinning the coat "ON her body, arms through sleeves" + re-rolls), and an
  editorial source photo without anchoring reads as a simpler garment
  (look-022's draped top became a plain cami in 6 frames; canon won).
- **Tops whose canon is worn-alone need the wear_note** or every spin frame
  layers the gray base tank under them (11/12/13/16/19 re-spun; 23/24 caught
  earlier). Canon front render = the reference for every spin QA call.
- **fal balance flapping:** two mid-batch "Exhausted balance" locks; top-ups
  take minutes to unlock submits, and a 202 from a status endpoint does NOT
  prove the account can spend — only a real submit does. The retry loop
  (probe with a needed frame every 10 min) is the right resume shape.
- 07-suit-vest was silently missing from the tranche lists (my count error) —
  caught by the final completeness sweep; sweep by enumerating garments/ and
  looks.json, never by trusting the plan's arithmetic.
Invented rears flagged for Janice's scrub-through; known aesthetic leftovers:
26 drape wobble, 31 long laces, 48 bare back, look-010 a180 rear print.

## 2026-07-22 — Full spin batch: garments done + QA'd; halted on fal balance

Back-photo drop ingested (24 files → per-garment raw/, avif→png via sips;
47/48 higher-res upgrades demote old shots to `_back2/_side2`). All 41
back-covered garment spins rendered and QA'd on contact sheets + full-size
profile checks. **What QA taught (now encoded in spin_frame):**
- **Base-outfit keep anchor:** a lone bottom garment with no mention of the
  tank read as undress to nb2's content checker (47's 422); prompts now state
  what the base outfit keeps, mirroring the 07-16 SLOT_NOTES lesson.
- **Legwear rulings:** silent prompts flickered between bare legs and kept
  leggings across frames. Default: bottoms replace leggings, dresses replace
  tank+leggings; a garment `wear_note` overrides (47 keeps leggings — its
  canon front render wears the skirt over them; 41 keeps the tank visible
  through its open back).
- **Meta text can poison turn-base frames:** 36-liv's color field said
  "violet-blue leopard" (wrong vision tag) — five frames followed the text
  while the canon front render followed the photos (black, red roses). Owner
  photos > auto-tags, again. Also: spin details carry only the top 3
  `details_to_preserve` — promote construction-critical notes (03's
  "sleeveless" was #4 and a270 invented a sleeve).
- **Model-back photos leak companions** (24's black under-sleeves) —
  exclude_from_photo applies to back refs too.
- Left as canon: 30 sheer-over-tank, 48 bare back (matches product photo),
  26 drape wobble, 31 long corset laces (Janice to judge in the scrub).
`fal_generate` polls 15 min now — the old ~4-min window abandoned ~5 billed
jobs when the queue slowed; timeouts also log the request_id.
**Outfits 7/18 done** (006/013/014/005/008/017 + 023's pilot; 009 at 6/7).
**HALT: fal 403 "User is locked. Exhausted balance"** — genlog ($28.33/$45)
tracks Janice's cap, not the fal account balance (shared with older
projects). Resume after top-up: 12-look rerun (skip-safe) + tranche 3
(15 no-back basics + 43/44 with `back_note`). Tag `pre-spin-full-batch`.

## 2026-07-19 (later) — Index lens SHIPPED; looks renumbered 001–019

The grid/index view (queued since the look-cards spec, trigger long passed)
is live: a **Carousel / Index toggle** in carousel.html's nav-left — the index
is a hairline-ruled SYVE grid over the carousel (z-6, native scroll; wheel/
touch handlers and the hero morph name are guarded while it's up; #info/
#controls hidden — they're z-10). Cells reuse ALL_ITEMS and open the same
detail overlay; `?view=index` deep-links it. CARD-PIPELINE's transferable
polish kept (one figure height, bottom baseline, min-height captions); the
Holo Mirror skin deliberately not carried over — SYVE only. **All look titles
renumbered to start at 001** (shift −3; 001–019, hoodie look = 019). Note
title ≠ id: landing hero look-006 is now titled "look 002" (START_LOOK
unchanged — it pins the plissé look itself, flagged to Janice).

## 2026-07-19 (later) — 360 spin BUILT ($0, awaiting avatar bases); cap → $45

Janice approved +$20 (genlog cap 25→45; $33.22 headroom) and full pre-generation
scope. Real per-spin cost is **$0.313** (2 faced frames × $0.059 + 5 unfaced ×
$0.039 — no face to swap on rear/profile frames), so everything ≈ $24: 58
garments ~$18.15 + 19 outfits ~$5.95, comfortably inside cap with fix margin.
Built and CDP-tested (11/11, stub frames, $0): `tryon.py` ANGLES/spin_frame
(back photos auto-attached as ground truth on rear frames; `--spin` CLI),
`/api/spin` (probe = frames/cost/no-back warnings; per-angle generate so
progress is visible and an aborted batch resumes), angle stems filtered like
pose tags, mirror scrub viewer (40px/frame, ESC exits, crossfade suppressed
while scrubbing), billed-batch confirm modal, spinToFront "she turns to face
you" on drag-hover (front-receive untouched, still the only receive frame).
Feedback bar hides during spin (correctives stay front-only). Run batches as
`tryon.py <gid> --spin` / `--outfit ... --spin` once bases land. **Janice's
running server needs a restart to pick up /api/spin.** Stub frames deleted
after testing (they would have made real batches skip generation).

## 2026-07-19 — 360 spin: PLANNED, fitting-room only (rule amendment)

**Decision (user):** the 360 turntable lives in the FITTING ROOM, not the
archive — this amends the 07-14 "poses/angles are archive-only" rule for
angle frames specifically (the posed-look system in the archive is unchanged;
correctives stay front-frame-only). Design: 8-frame spin at 45° steps, scrub
the mirror to rotate; "360" control beside RENDER OUTFIT with a billed-batch
confirm (~$0.42/spin: 7 new frames, face-swap only on the two front-quarter
frames); frames persist (re-spin = $0); angle-tagged stems (`_a045` etc.)
filtered from normal render lists like pose tags. **Receive gesture kept:**
dragging a garment over a mid-spin mirror eases the viewer back to the front
frame first, THEN the front-receive swap plays ("she turns to face you to
take it") — front-receive.png stays the single UI-only frame, no per-angle
receive variants (rejected same grounds as per-render hovers). **Scope
(user):** ALL outfits get full-rendering spins AND every individual garment
gets its own spin — architecturally same pipeline (garment spin = 1-item
compose per angle), but pre-generating everything ≈ $32 (19 outfits ~$8 +
58 garments ~$24) vs $13.22 left under the $25 cap → default is lazy
on-demand generation with per-spin confirm; full pre-generation needs a cap
decision. **Coverage gap: 38/58 garments (all 10 shoes) have NO back view**
— rear frames would be invented; spin-enable back-covered items first,
source backs via /sourcing. **Blocked on assets from Janice:** 7 avatar
angle bases (turn-045…turn-315, nano-banana single edits of front.png,
prompts delivered 07-19 in-session) + mizuno side/heel photos for the pilot.

## 2026-07-19 — Ingest: 59-el-hoodie (Eckhaus Latta)

Janice staged 4 webp views ("EL-hoodie") via the sourcing flow; ingested as
**59-el-hoodie**. "EL" resolved to **Eckhaus Latta** from the baked-in shoulder
print (the uniqlo→Aritzia lesson paying off). Primary = flat-lay on beige
(1080px — under the ≥1500px preferred bar but above the re-source threshold);
extras `_model-front/_model-alt/_model-back` (back view banked for the
turntable idea). Difficulty 3: the painted band must wrap chest→sleeves
continuously. Dragcut done (general model, 512×447). **size_owned NOT logged —
ask Janice.** No render yet ($0.059 when approved); it lives on the racks only.
README gained the sourcing screenshot + a note that the demo excludes
/sourcing (needs the live server to fetch/rank remote pages).

**Rendered same day** (size M logged; Janice approved render + corrective,
$0.118 total): `_1` invented a full-zip worn open — new failure flavor:
**nb2 can invent garment construction, not just leak clothing**; `_2` fixed
via one "wrong fit" corrective ("closed pullover, no zipper"). `_1` hidden.
meta's `exclude_from_photo` now carries "any zipper or open front" so future
re-renders anchor against it.

**Root cause found via look-023 (Janice's hoodie+sagittarius+mizuno look
rendered zip-up AGAIN + cropped pants):** the zip invention wasn't random —
BOTH prompt paths hard-code outer layers "worn OPEN" (single: `layer_note`,
outfit: `LAYER_HINTS`), which for a pullover means inventing a front opening.
Fix: per-garment **`wear_note` meta override** honored by both paths (59 says
"worn CLOSED as a pullover"); the outfit path also now carries each item's
`exclude_from_photo` (it never did — the 07-16 fix only reached the single
path). The cropped pants were a WRONG VISION TAG: 42-sagittarius meta said
"tapered cropped ankle" but Janice's pair is full length (product photo
agrees) — meta corrected; trust the owner over the auto-tag. look-023
corrected in ONE batched call ($0.059: pullover + full-length together,
3-image edit: render + both garment ground truths), `_1` hidden, looks.json
repointed at `_2`.

## 2026-07-19 — Carousel shows outfits only

**Decision (user, triggering the 07-16 queued item):** with 19 looks published, the
archive carousel now displays ONLY created outfits — no single-garment figures.
`buildItems()` in `carousel.html` drops the garment loop (published looks only, as
before); the category filter nav (All/Tops/…/Outfits) is removed since every entry
is an outfit — nav-left keeps just the Fitting room / Sourcing links. Single
garments remain fully browsable in the fitting room racks, and the look detail
overlay / re-render / OPEN IN FITTING ROOM handoff are unchanged. Garment cutouts
stay on disk (fitting room hover previews still use them). Revert = restore the
garment loop + filter spans from git history.

**Same-day follow-ups (user):** duplicate "look 017" titles fixed (look-019 →
"look 018", everything after shifted down one — titles only, ids/filenames
untouched; note title ≠ id number now, and the server's default title for the next
new look is keyed to the id, so it'll suggest "look 024"). look-023 (coucou tank +
vortex boots + liniss pants) unpublished to draft ("look 022") — Janice confirmed
the pre-renumber reading of "look 021"; entry + renders kept, republish restores
it. Carousel lands centered on look 005 (`START_LOOK = 'look-006'` in
carousel.html, falls back to first item if missing).

**README demo GIF (user, 07-19):** the README's fitting-room visual is now
`docs/screenshots/fitting-room-drag.gif` (800px, ~5MB, per-frame palettes —
shared/128-color palettes speckle the face): a CDP-driven drag of 03-plissé
from the rack to the mirror — receive frame, drop, render lands. Captured $0
(all renders pre-existing) via Page.screencast + synthetic pointer events;
capture script kept in the session scratchpad (`capture_drag_gif.py` pattern —
rebuildable from decisions here if needed). `fitting-room.png` stays on disk,
now unreferenced. A look-preview frame for the looks index was built, shown,
and REJECTED by Janice same day — do not rebuild.

**Looks index scrolls (user, 07-19):** the fitting room's Looks list now scrolls
on its own with the racks' discipline — outfit slots + action buttons pinned,
`#saved-outfits` gets `flex: 1` + the same 6px black scrollbar (`#outfit-panel`
became the same flex column as `#closet-panel`). The repeated "in archive" badge
is gone — a publish button marks the draft rows, published rows are the quiet
default. Saving a look scrolls the new draft into view at the foot of the index.

## 2026-07-17 — The mirror reacts: avatar "receive" frame on drag-hover

**Decision (user, photo supplied):** the ISC demo's ModelHover mechanic, done our way.
Janice generated `avatar-v3-front-receive.png` externally (nano banana edit of
front.png per our prompt spec: same stance/framing/outfit, arms lifting to receive);
aligned locally via human-seg figure bboxes (scale 0.817, ±1px shift — blink-strip
verified) → canonical `avatar/avatar-v3/front-receive.png`; her original kept at
`avatar/avatar-v3-front-receive.png`. Behavior: while a dragged garment hovers the
mirror AND the stage shows the base avatar, the stage crossfades to the receive
frame; leaving reverts; a successful drop holds the receiving frame ~220ms before
the render lands ("she takes it"). Renders on stage keep the CSS breath only —
per-render hover variants were rejected (≈$0.06 × catalog + face risk).
**front-receive.png is a UI frame only, never a render base** (renders stay on
front.png). $0 total. CDP suite: 11 checks, all pass.

## 2026-07-17 — Drag-to-dress v3: bare garment silhouettes (the missing dimension)

**Why v2 still felt flat (user question):** the physics were already the demo's —
but the demo drags transparent garment PNGs, and a bordered rectangle under the same
rotateY reads as a playing card, not fabric. Fix: `scripts/dragcut.py` ($0, local
rembg) writes `clean/<id>_dragcut.png` transparent silhouettes — **only** dragcuts,
never `_onwhite`/`_extracted`, so try-on inputs are untouched (server also excludes
them from `photos[]`; manifest gains a `dragcut` field). Routing lesson from the
first pass: **on-model photos → cloth-seg only, NEVER the general model as fallback**
(it keeps the whole person: a model-shaped drag ghost); product/ghost/extracted
shots → general model (cloth-seg rags/truncates them). Result: 50/57 bare
silhouettes (shadow hugs the alpha); 7 items fly as the framed card (5 weak
cloth-seg on-model + bunnyhill ×2 demoted after QA). Also: the mirror now "notices"
— avatar scales 1.015 + brightens 5% while a garment hovers it ($0 stand-in for the
demo's pre-made hover images, which would cost renders + face risk). CDP suite
extended (bare vs framed) — all pass. Run dragcut.py at every future ingest.

## 2026-07-17 — Drag-to-dress v2: the Interactive-Styling-Canvas physics

**Decision (user):** the drag should look like kaberikram/Interactive-Styling-Canvas.
Cloned the repo (MIT, scratchpad only) and ported its mechanics: native HTML5 DnD
replaced with **pointer-driven drag** — a hairline-framed garment card (the item's
photo; our sources aren't transparent PNGs like the demo's shirts) rides the cursor,
with the demo's exact physics: `.grabbed` scale-1.05 lift + soft shadow, directional
perspective tilt while moving (rotateY ∓15° + skew, spring curve
cubic-bezier(.68,-.55,.265,1.55)), settle-to-flat on pause (60ms), **fly-back to the
rack row on a missed drop**, shrink-into-the-mirror on a hit. 6px threshold keeps
click-to-try-on intact. Targets/slot rules unchanged from v1 (below). CDP-verified:
click-not-drag, pickup+tilt, mirror arm+drop, slot mismatch fly-home, slot match,
no leftover cards.

## 2026-07-16 — Drag-to-dress ships in the fitting room (v1, superseded same week)

**Decision (user, vetted 07-15):** garments can be dragged from the racks onto the
mirror (auto-slot via the category map) or onto a specific manifest slot (only the
matching slot arms; a mismatch drop toasts the right destination). Drop = slot
assignment + the existing tryOn flow — instant render swap since every garment now
has a front render; **drop position carries no pixel-placement meaning** (nb2 slots
by category). Affordances in the SYVE language: grab cursor on rows, mirror hairline
doubles while dragging (inset shadow, no layout shift), triples on hover, caption
becomes "drop to wear — {name}", matching slot inverts; the rack preview image rides
as the drag ghost. Verified via CDP-driven Chrome (synthetic DragEvents): mirror
drop, slot mismatch rejection, slot match equip — all pass. Rollback point: tag
`pre-drag-to-dress`. Inspiration: kaberikram/Interactive-Styling-Canvas (whose
"instant" trick is pre-rendered assets — exactly our render library).
Same day, sundae shirt corrective ($0.06): pasted-on look improved but the ghost
photo's propped-open collar + inner brand tag survived (Janice caught the tag —
the true "sitting on top" tell). 07-17: fresh render ($0.06) with the tag in
`exclude_from_photo` + "collar worn naturally closed" in details → clean, lives at
`_3` (both earlier takes hidden; the original _1 was accidentally overwritten by
the CLI's default suffix — lesson: pass explicit --suffix when re-rendering).
Drag-to-dress discovery copy: idle-mirror caption now reads "click a garment, or
drag one onto the mirror"; rack rows carry a hover tooltip. Spend $10.25/$25.

## 2026-07-16 — Batch ingest: 53 items (06–58), shoes category goes live

**The July sourcing haul is in.** Janice gathered ~120 ecomm photos via `/sourcing`;
QA pass flagged 18 files (thumbnails/dupes/screenshots/an info-strip collage) which
she chose to discard rather than re-source (all in `garments/raw/_discarded/` — four
items dropped entirely: bitter-cells jacket, realisation scarlet, the aritzia-tooltip
"uniqlo" parka, reformation leather dress). The remaining 101 files became **53 items
(06–58): 43 clothing + 10 shoes**, sizes/brands from Janice's worksheet
(`docs/ingest-worksheet.md`, kept as the ingest record). Conventions established:
- **raw/ naming:** primary view = plain slug ('.' sorts before '_' so
  `tryon.garment_asset` picks it); extra views `_back/_side/_alt/_model-*/_detail`.
- **avif → png at ingest** (pipeline IMG_EXT excludes avif).
- Fixups: liv-dress black pillarbox bars cropped; gnur hoodie (grey terry shot on
  black at 800px) got a cloth-seg `_onwhite` extraction; entire-studios alpha
  composited on white.
- **Sets:** subtle-mermaid top (43) + skirt (44) are separate garments cross-noted as
  a set (Janice: wearable separately); set-reference photo lives in 43's raw/.
- **Shoes:** fitting room needed zero changes (SLOTS/category-map/filters already
  handled it); carousel got a Shoes filter + a guard so unrendered garments stay out
  of the parade (they live in the racks until rendered).
- Difficulty 4/5 assigned (front-pose rule applies): issey tanks ×2, nin pleated top,
  liniss dune pants, realisation sheer top, subtle-mermaid top + skirt.
**Render batch (approved, $3.25 actual):** 53/53 rendered clean on the pipeline side,
45 min. QA found **10 failures with one root cause: the prompt never carried the
"NOT part of this garment" notes and never anchored what the base outfit keeps** —
companion garments leaked (09/25/26/27/29/31), and three items mis-slotted (18 white
skirt → shirt-dress, 44 mermaid skirt → gown, 52 flats → a printed dress).
**Prompt fix shipped:** `SLOT_NOTES` category anchor (top/bottom/dress/outerwear/shoes
— what changes, what stays) + `exclude_from_photo` meta field (populated on 15
on-model items) → exclusion clause in the prompt. Fix round (approved, $0.53): 9/9
re-rendered clean as `*_nb2_v3_2`; the bad `*_nb2_v3_1` stems live in hidden.json
(files kept). 30-off-shoulder kept as-is (borderline: model's trousers instead of
leggings; garment itself correct). Spend after both rounds: **$10.13 / $25**.
Next build: drag-to-dress in the fitting room (agreed 07-15).

**Post-QA amendments (Janice, same day):** 22-gnur-hoodie ARCHIVED (strange render,
weakest source) — garment folder → `garments/archive/`, renders → `renders/archive/`;
`garments/archive/` joins `renders/archive/` as app-invisible. 45-sundae-gorum-shirt
flagged: reads as pasted-on rather than worn (corrective candidate). **Standing
intent: the archive carousel eventually shows ONLY created outfits** (single garments
stay in the fitting room racks) — build when looks exist in volume.

## 2026-07-15 — /sourcing: photo-sourcing gets a page (URL → ranked images → raw/)

**Decision (user):** garment photo sourcing moves from CLI-only to a friendly UI.
Janice is gathering closet photos (clothing, shoes, accessories) from ecomm sites;
`scripts/ingest_fetch.py` (built same day) pulls a page's declared images at full
resolution, and `/sourcing` is the SYVE-styled page over it: paste URL → scan →
ranked candidate grid (browser measures true dims; server python lacks PIL) →
click-select → save to `garments/raw/<slug>.<ext>` with a page-title-derived slug.
A "staged in garments/raw." strip shows what awaits ingest, flags anything under
1000px long side ("thumb — re-source"), and × moves files to
`garments/raw/_discarded/` (never deletes). Routes: `/api/source/{scan,img,save,
staged,discard}`; scan is the server's one `requests`-dependent route (lazy import,
graceful error). $0 — no fal involvement; works without ENABLE_GENERATION.
Source-photo bar stated on the page: ≥1500px long side, ghost-mannequin/flat-lay >
on-model studio > editorial, true color.

## 2026-07-15 — ASCII entrance shipped (handoff algorithm, SYVE skin, pulse-fade)

**Decision (user, after three live previews):** the archive's entrance is the
design-handoff effect (`design-inspo/design_handoff_ascii_entrance/` — Sobel edge-trace,
chars drawn sequentially from the Wild Woman passage, 4-layer twinkle) translated to the
SYVE language, not the handoff's warm-putty look. Final form, iterated in
`design-inspo/entrance-previews/option3-interior-syve.html` (options 1/2 retained there):
- **Image:** the handoff interior photo, grayscaled, Instagram UI (arrows / profile icon /
  dots) inpainted out (cv2 + clone patches; handoff original untouched) →
  `app/entrance-bg.jpg`. Full-bleed: runtime center-crop to the viewport aspect, canvas
  pinned to 100vw/100vh (!important over the module's inline sizing).
- **Glyphs:** black on the white void, charSize 12 (handoff's 7 too tiny), quote text;
  "enter the archive." italic label kept (white backdrop pill).
- **Shimmer:** new `shimmerDepth` knob = 0.9 (alpha 10–100%, speed 3) — the handoff's
  50–100% twinkle is invisible in black-on-white.
- **Dispel (replaces scatter/rise):** glyphs pulse in and out under a ~2.6s decaying
  envelope — each reappearance weaker until they stop coming back — while the photo fades
  fully out from 0.9s (NO ghost); the overlay bg goes transparent on click so the fade
  reveals the live carousel directly. ~3.3s total.
- **Integration** (inside `carousel.html`, single-file): shows once per browser session
  (`sessionStorage.archiveEntered`, set on dispel completion), skipped under
  prefers-reduced-motion, `?entrance=1` forces / `?entrance=0` suppresses (QA),
  image-load failure dismisses the cover (never trap the site), carousel wheel/touch
  scroll blocked while the cover is up. Verified end-to-end via CDP-driven Chrome:
  idle cover → click → mid-dispel reveal → clean carousel → same-session reload skips.

## 2026-07-14 — Fitting room "prettier pass" (mirror / index / manifest)

**Decision (user):** art-direct the fitting room within the SYVE language, keeping the
three-zone layout. Stage = a hairline-framed **mirror** with a gallery label (tracked
9px caps under a rule). Racks = a **text-first index** — number, brand eyebrow, name,
difficulty dots; row hover inverts and fills a framed square **preview** below (never
empty; defaults to the first garment). Outfit rail = a **manifest** — hairline rows,
slot label + "Brand · name", strike-through on hover as the remove affordance, empty
slots read "—". Looks list restyled to the same hairline rows. Previous design remains
at tag `fitting-room-syve-v1` (revert: `git checkout fitting-room-syve-v1 -- virtual-closet/app/`).

## 2026-07-14 — Two-view architecture decided and built: the look is the atom

**Decision (user, after talking through options):** home stays the archive (`/`); the
fitting room moves to `/fitting-room` (`/classic` kept as alias). The **look** is the
canonical object: `looks.json` stores id/title/items/pose/state/render/cutout/created
with a **draft → published lifecycle** (manifest's filename-derived outfit list removed).
Doors between the views:
- **Archive → fitting room:** clicking the centered hero opens a detail overlay
  (items + sizes, pose, RE-RENDER LOOK / OPEN IN FITTING ROOM / CLOSE); "open" hands the
  look's items to the fitting room via localStorage and loads them into the slots.
- **Fitting room → archive:** SAVE LOOK saves a free draft (`POST /api/looks`);
  PUBLISH opens a pose-picker dialog (front pre-selected when the look contains a
  difficulty-4+ garment) → `POST /api/publish` renders via tryon_outfit with that pose,
  runs the cutout pass (liminal venv subprocess), and the look appears in the carousel.
- Re-rendering a published look (carousel CTA / detail) also goes through `/api/publish`
  with its stored pose, keeping looks.json current.
- Cross-document **view transitions**: the hero figure morphs into/out of the stage
  (`view-transition-name: figure`; only the centered carousel element carries it).
- Legacy localStorage `savedOutfits` migrate to server drafts on first fitting-room load.
Seeded: look-001 (01+02, 34turn) + look-002 (01+02+04, hand-on-hip) published;
look-003 (02+04+05) draft. Also fixed en route: `/api/generate`'s suffix counter
scanned `_v1_` stems (could overwrite v3 renders); now scans v3 front stems.

## 2026-07-14 — avatar-v3 is the new canon; pose library live (user gate passed)

**Decision (user):** Janice supplied her own externally-generated pose set and chose it as
the **new avatar lineage over avatar-v1**: `avatar/avatar-v3/` = front.png, contrapposto.png,
hand-on-hip.png, 34turn.png (canonical copies; her originals remain `avatar/avatar-v3*.png`;
`avatar_v2.png` was a superseded iteration — Janice trashed it 07-14).
The v3 face/hair (curtain bangs, long waves) visibly differs from v1 —
**face-swap identity source is now `avatar/avatar-v3/front.png`** (tryon.py + server
updated). Per plan §5.4 the seven v1 renders are legacy: they keep their `_v1_` tags and
remain in the app until re-rendered on v3 (~$0.41 for the full set — NOT yet approved).

**Amendment 2 (same day): poses are archive-only (user).** The fitting room (`/classic`)
shows front-facing renders exclusively: the manifest's per-garment `renders` list filters
out pose-tagged stems (`is_posed()` in closet_server.py), and tryon.py's corrective
default targets the newest FRONT render. Both generate paths already default to front.
Consequence: 01–04's stage renders fall back to the legacy v1 (old face) front renders
until front v3 renders exist (~$0.06 each, not approved). 05 already has a front v3.

**Amendment (same day): full catalog re-rendered on v3 (approved batch, $0.295).** Pose
map: 01 contrapposto · 02 hand-on-hip · 03 contrapposto · 04 34turn · 05 front ·
look 01+02 34turn · look 01+02+04 hand-on-hip. Outfit compose got `--pose` too (slug
carries the pose: `outfit_01+02_34turn_1`). The three v1 look renders joined
`outfit_02+04+05_1` in hidden.json (files kept). Two honest notes: (a) 03 is the
difficulty-4 plissé and should have stayed on front per the standing rule — the folder
name "05-hardest-item" misled; garment fidelity held but the pose drifted to a
hand-to-hair gesture (kept pending Janice's verdict; re-render on front is one $0.06
call). (b) 05's difficulty-5 drape rendered clean on the front pose. Spend $5.82/$25.

**Approved test envelope ($0.118, passed):** `tryon.py --pose` wired (pose base as Image 1,
prompt made pose-aware — "same stance and camera angle as Image 1" replaces "front-facing"
for non-front poses; hair description updated to v3). 01 mock-neck on contrapposto and
04 blazer on 34turn both held pose, garment, and identity; cutouts clean (hand-on-hip
arm-triangle QA'd separately, $0); carousel picks v3 cutouts automatically (`v3` sorts
after `v1` in the server's `cuts[-1]`). Render naming: `<gid>_<arm>_v3[_<pose>]_<n>.png`.
Standing rules otherwise unchanged (budget gate, no NB edits on the head region, one pose
per saved look — variance across looks, not within; difficulty-4/5 garments stay on front).

**Decision (user):** an ambient auto-scroll for the archive carousel (drift at 0.18
items/s, easing to a 0.015 items/s crawl while the cursor is over a figure, smoothstep
on the thumb→hero growth) was built, tuned once, and then shelved — not the browsing
effect Janice wants. Reverted to the manual-scroll carousel; the auto-drift version is
archived at tag `auto-drift-v1`
(restore: `git checkout auto-drift-v1 -- virtual-closet/app/carousel.html`).

## 2026-07-13 (night) — Archive page becomes a runway procession

**Decision (user):** rework the archive carousel into a static single-file procession per
`design-inspo/runway-inspo.avif` — white background kept (no crowd/set), figures static
(no walk animation: per-frame/video generation rejected for cost + identity risk; fake
CSS limb motion rejected as less sophisticated). Implementation is a parametric
perspective path in `carousel.html` (scale ~ 1/z, vanishing point just above the hero's
head like the inspo's raised camera, alternating lateral stagger, contact shadows, depth
blur, passed figure exits by scaling through the camera). Scroll/click/filters/TRY ON
mechanics unchanged. Previous side-by-side SYVE layout preserved at tag
`syve-carousel-v1`.

**Amendment (user, same night):** after seeing it live, Janice reverted the archive page
back to the side-by-side SYVE carousel. The procession is saved at tag
`runway-procession-v1` (restore: `git checkout runway-procession-v1 -- virtual-closet/app/carousel.html`)
should we want to revisit it.

## 2026-07-13 (late) — Site brand "the archive."; SYVE language goes site-wide

**Decision (user):** The header/brand is **"the archive."** (lowercase, with period), and
the `/classic` fitting room is restyled to the same SYVE white-void language as the
carousel (white bg, black 1px hairlines, uppercase Helvetica, black-fill CTAs, italic
lowercase wordmark). Layout of the fitting room (outfit rail | stage | racks) is unchanged.
This supersedes the Boutique/313NY visual direction; Boutique v3 remains recoverable at
git tag `boutique-v3` (`git checkout boutique-v3 -- virtual-closet/app/`). The two-view
architecture (carousel = archive, /classic = fitting room) still stands.

Same batch: carousel responds to horizontal (x-axis) scroll and click-to-center on any
figure; `renders/hidden.json` lists render stems the server keeps out of the app
(currently the two `outfit_01+02+04` renders — files stay on disk); the size row now
reflects each garment's `size_owned` from `meta.json` (no highlight when unset — sizes
must be logged per item at ingest, everything is NOT small).

## 2026-07-13 — Phase 3 verdict: nb2/edit + face-swap is the default try-on pipeline

Benchmark (docs/phase3-benchmark.md): `fal-ai/nano-banana-2/edit` + face-swap finish swept
5/5 garments at $0.059/render. NB Pro is *worse* at try-on despite 3.4x the price — it
re-stages the scene (collages, removes base clothing, drifts colors) where nb2/edit behaves
like an editor. IDM-VTON needs its `category` param wired before it's a fair arm (3/5
failures were ours). nb2 caveats: slight garment slimming; stricter content checker —
try-on prompts must stay neutrally worded ("virtual try-on: show the person wearing…",
never "dress the woman…", no body-size adjectives). Live generation wired: app
`/api/generate` → tryon.py → render + swap + budget log.

## 2026-07-13 — avatar-v1 LOCKED (user gate 2 passed)

**Decision (user):** `avatar/avatar-v1/` is the locked character sheet: front.png (the
user-supplied `avatar-draft-2.png`), 34left.png / 34right.png (NB Pro turnaround views with
the face identity-swapped back via `fal-ai/face-swap`), back.png. All try-on renders
reference avatar-v1 only.

**Pipeline learning that got us here (the identity bridge):** prompt-only generation tops
out at "close cousin" likeness — NB Pro re-imagines faces rather than copying them, and a
full-body frame gives the face too few pixels for identity anyway. The working recipe:
(1) generate base/view with the right framing, hair, lighting; (2) finish with an
embedding-based face swap (`fal-ai/face-swap`, ~$0.02: `base_image_url` = image to fix,
`swap_image_url` = identity source). **Standing rule: every render where the avatar's face
is visible gets a face-swap finishing pass** (source: avatar-v1/front.png). User-tuned face
notes: soft OVAL chin (never sharp), visible winged eyeliner, wispy sheer bangs, straight
hair, slim nose.

## 2026-07-13 — Face-exact avatar round + generative garment extraction (approved batch)

**User requirement:** avatar face must match the persona reference photos EXACTLY.

**Learned (the hard way, 4 failed edits):** NB Pro *edits* on the avatar are unreliable —
three face edits returned before/after collages despite explicit single-figure instructions,
and a "bangs only" edit rebuilt the whole head and regressed the face. Rule: **do not edit
the avatar's head region; regenerate instead.** Fresh generation with reference roles
explicitly decoupled ("Images 1–3 define ONLY the face; Image 4 defines ONLY the body; her
body is slender even though her face has soft cheeks") produced the best result:
`avatar/versions/r3_faceexact_2.png` — face close-match, correct petite body, single figure.
Known deviation: bangs render wispy/parted vs the reference's full straight bangs.
Also: face-softness adjectives leak into body build unless explicitly firewalled.

**Garments:** 01 + 04 re-extracted generatively (NB Pro ghost-mannequin on white) →
`garments/{01-plain-tee,04-structured-blazer}/clean/*_extracted.png`; superseded rembg
cutouts deleted (regenerable via scripts/extract_garment.py). Segmentation cutouts kept
for 02/03/05 where they were clean.

**Status:** avatar lock (user gate 2) PENDING — user to judge r3_faceexact_2 before the
4-view character sheet is generated. Batch spend ≈ $1.21 (one blazer extraction was billed
but lost to a transient download failure before logging; fal_generate.py now retries
downloads and logs the result URL on failure).

## 2026-07-12 — App design direction: "The Boutique" (313NY)

**Decision (user):** The closet app follows the locked design direction from
`~/liminal-wardrobe/spec/design/design-tokens.md` and its moodboard (313NY archival store):
cool industrial bones + warm directional light + sparing amber/green accents, gallery restraint.
Fonts: Bodoni Moda (display) / Spline Sans Mono (technical labels, the only uppercase voice) /
Archivo (body). Zone mapping: stage = fitting room (dim, backlit-mirror glow);
closet panel = the racks (tile-white, grout grid); outfit rail = charcoal instrument panel.
A first pass in feminine violet/rose ("dressing room at night") was rejected — wrong universe.

**Accent amendment (user, same day):** amber reads too masculine. The active/selected voice is
**soft chrome** (brushed-silver gradients, cool mirror-white LED light — the galvanized-steel /
light-wall side of 313NY), not the warm amber lamp side. Oxblood stays as the rare alert voice.
Warm-light tokens are reserved for photo content, not UI chrome.

## 2026-07-12 — Benchmark garments are on-model photos

All 5 raw photos show garments worn by models (not flat-lays). Try-on prompts must extract
the garment from a worn photo and ignore the model's other clothing (noted per item in each
`meta.json`). Two slots differ from their folder names: 01 is a draped mock-neck top (not a
plain tee), 02 is black wide-leg suiting trousers (not jeans). Folder ids kept; `name` fields
carry the real descriptions.

## 2026-07-11 — Avatar lock DEFERRED; flow-first, credit-conscious

**Decision (user):** Stop spending fal credits on avatar perfection for now. Build the closet app flow (Phase 4, $0) first; lock avatar-v1 later. Round-2 candidates (`avatar/versions/r2_candidate_*.png`) are all QA-clean and retained; `r2_candidate_2` (best persona face) serves as **provisional draft avatar** for UI development — it is NOT locked, and no renders against it are canon.

**Standing rule from this decision:** API-spending actions (any fal call) happen only in explicit, user-approved batches. The app's generate path ships **disabled by default** (`ENABLE_GENERATION` env flag) with copy-prompt mode as the $0 fallback.

## 2026-07-11 — Avatar identity: AI persona face + real body proportions

**Decision (user):** The three face reference photos are AI-generated persona images (not photos of Janice, not a real third party). Build the avatar **as-is** on this persona face, combined with Janice's real measurements and full-body proportions reference.

**Implications:**
- The Phase 2 exit gate changes from "feels like me" to **"matches the persona consistently + my real proportions."**
- Auto-QA identity scoring is against the persona face refs, exactly as the pipeline already works — no mechanical change.
- Renders are *styling visualization on a persona with my body*, not "how clothes look on my face." Fit/proportion signal is still real; face is fictional.
- If Janice later wants a true-likeness avatar, that's a new lineage (`avatar-v2`) from real unfiltered selfies — per plan §5.4, old renders keep their version tag.

## 2026-07-11 — Clean-skin avatar

**Decision (user):** Exclude the tattoos/markings visible in the real full-body photo. Every avatar and try-on prompt specifies clean, unmarked skin. `distinctive_features` stays empty by design.

## Reference photo inventory

| File | Role | Notes |
|---|---|---|
| `front face.png` (1536×1024) | persona face, front | AI-generated, warm indoor lighting |
| `left face.jpeg` (766×1024) | persona face, 3/4 | below 1024px spec — acceptable |
| `right face.jpeg` (778×1024) | persona face, 3/4 | below 1024px spec — acceptable |
| `full-body-upright.jpeg` (4284×5712) | body proportions only | real photo, rotated from `full-body.jpeg`; face/tattoos in it are NOT avatar canon |

**Prompt consequence:** face refs and body ref are different people, so avatar prompts must bind face to Images 1–3 and take only proportions from Image 4 (see `prompts/v1/avatar.md`). Skin tone follows measurements.json ("pale"), not the warm-lit persona photos.
