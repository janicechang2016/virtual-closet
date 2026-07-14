# Decision log

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
