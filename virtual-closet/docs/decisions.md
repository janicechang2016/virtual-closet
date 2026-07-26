# Decision log

## 2026-07-26 — The mirror is a constant box; `production` branch deleted

**Mirror.** Dropping a garment visibly resized the frame. Cause: `#stage-img` was only
`max-height` constrained, so displayed width = height × aspect — and **42 of the 126 visible
renders are not square** (aspect 0.513–1.833) while the avatar is 1.0. Swapping the square
avatar for a 0.665 render made the image a third narrower and the frame, which hugged its
content, shrank with it. The caption was suspected first and measured innocent: all three
caption states render at 27px.

Fixed with the pattern the spin viewer already needed — **lock the box, letterbox the
frame**: a square `height`/`width` on the image plus `object-fit: contain`. Verified across
aspect 1.000 / 0.665 / 0.800 / 1.000: frame constant at 657×642, image undistorted.

**Reported still moving after that fix, and it was — two other things changed size, both
deliberate:** the `drop-hot` state scaled the image `1.015` (measured 738 → 749 → 738px
mid-drag) and the drop affordance stacked a 1px then 3px inset shadow on top of the frame's
existing 1px border, so the edge read as 1 → 2 → 4px. Locking the box only fixed the
aspect-ratio cause; these two were separate.

Both removed. Hover now signals with brightness alone, and the drop target uses the
chrome-silver wash already used by the index lens and stylist cards — same signal, zero
geometry. Traced through a real drag: frame 852×837 and image 738×738 constant at every
phase.

**Reported STILL shifting after both fixes.** The approach was wrong, not just incomplete:
the frame sized itself to its contents, so every fix chased one more thing that could push
the border — aspect ratio, hover scale, shadow weight, caption wrapping. Four causes, three
rounds, and no guarantee a fifth did not exist.

**The frame now has explicit dimensions** (`width: min(760px,100%)`, `height: min(78vh,860px)`,
`flex: none`); the image fills what is left with `object-fit: contain`, and the caption
reserves two lines. Content adapts to the border, never the reverse. Measured 760×860
identically at 1440/1700/1999/2400px, across four caption strings, 14 garments, and every
phase of a real drag.

This is the third instance of the same standing rule ("appearing must never shift the
centred mirror", 07-15). Two lessons worth keeping: **an effect that is "just visual" still
counts as movement if it changes apparent size**, and **when a fix needs a third round,
stop fixing causes and remove the degree of freedom.**

**`production` deleted.** Vercel now builds from `main` (verified by pushing a commit to
`main` alone and watching the live build stamp change to it). A branch named `production`
that no longer deploys is the exact ambiguity that cost this session two rounds of
misdiagnosis.

## 2026-07-26 — Deploy source is `main`; the `production` branch retired

**Decision (user):** point Vercel at `main`. One branch means live; no promotion step.

**Why it came up:** the session's work was pushed to `main` and nothing appeared on the site.
Not a build failure — **Vercel's production branch was `production`**, 38 commits behind at a
07-20 commit, so every push was aimed at a branch nothing was watching. Diagnosed by hashing
the deployed `/app/carousel.html` against each candidate branch: it matched
`origin/production` byte for byte. Grepping for markers only established "old"; the hash
established *which*.

`production` was fast-forwarded (a clean ancestor, no force) to ship the phone-layout fix,
then the setting moved to `main`. Deploy verified live at a true 390px viewport: HUD stacked,
no overlap, both flanking figures legible, `nav.js` 200.

**`production` is now vestigial and should be deleted** — leaving a same-named branch that no
longer deploys is exactly the ambiguity that caused this.

## 2026-07-26 — Merge to `main` and deploy; Railway kept warm

**Decisions (user):** (1) get the session's work onto `main` so the branch stops diverging —
this is what Vercel builds, so it deploys the public site; (2) **keep Railway warm** rather
than pausing it, accepting the $5/mo while `/stylist` and `/insights` remain local-only and
snapshot-driven.

**A naive merge would have been destructive, and the check caught it.** `main` was not an
ancestor of `2d-reboot`: it carried **31 commits of the 360/spin work** — the full spin batch
(58 garments + 18 looks × 7 angle frames, ~1,300 files), `spin_smooth.py`, `spin_video.py`,
and the paid renders — none of which the 2D rollback has. Worse,
**`archive/360-avatar-v4-20260724` had never been pushed**, so `main` was the only remote
copy of roughly $23 of generated assets.

Sequence actually run: push the archive branch to origin → verify **every** commit on `main`
is reachable from it (`git rev-list --count archive..main` = 0, so `main` held nothing
unique) → tag `main-pre-v2-20260726` at the old tip → move `main` to the v2 line with
`--force-with-lease`.

`main` is now the current 2D + v2 line rather than a merge, because the 360 rollback was a
deliberate product decision and a merge would have resurrected the spin code paths and
conflicted in `closet_server.py`, `tryon.py`, `fal_generate.py` and `genlog.py` — all of
which would have been resolved in the 2D line's favour anyway.

**Recovery:** `git reset --hard main-pre-v2-20260726`, or the full 360 history on
`origin/archive/360-avatar-v4-20260724`.

**A real bug was caught by checking the built export before merging, not after.** `nav.js`
read `body.demo` when it built the menu — but that class is applied only *after* the
carousel's async manifest fetch, so the race lost and the static export offered **Stylist,
Insights and Sourcing: three links that 404 on the public site**. Fixed by marking those
items `data-local` and hiding them in CSS (`body.demo #navsheet li[data-local]`), which has
no timing to lose. Verified: the built export shows Archive + Fitting room only; the local
server still shows all five.

**`CLAUDE.md` queued list cleaned.** It still carried the render batch and drag-to-dress as
"do not build until asked" months after both shipped, which would mislead a cold read. The
durable constraints inside those entries (pose rules, sourcing quality bar) were kept and
relabelled as standing rules; the task framing was dropped.

## 2026-07-26 — Nav polish + insights made modular

**Hamburger:** box removed (three hairlines at the site's own weight). Placement is no longer
a floating overlay by default — it **mounts into each page's existing top-right cluster** so
it aligns with its neighbours instead of covering them. The mount is container-aware because
two real failures showed up: the carousel's `#nav-right` is a **column**, so mounting stacked
the button beneath the readout and over the figures; sourcing's strip is
**space-between**, so adding a third child shoved `$0 · local only` to the centre. Columns
now fall back to floating, and space-between rows pin the previous sibling with
`margin-left:auto`. **The wordmark links home from every page except the archive itself** —
a link to the page you are already on is a dead control.

**Insights, made modular for scanning.** Sections became modules on a 12-column field,
divided by hairlines rather than cards (SYVE has no shadows or radii to spend). Every module
carries the same head — ordinal number, title, one line of context — so the eye learns the
shape once and can then skim. Span follows the story, not the data: the two at-a-glance
reads sit 8/4, the two category comparisons 6/6, and the photographic evidence runs full
width. `auto-fill` was leaving dead space at the end of the picture rows; `auto-fit`
collapses the empty tracks so the cards stretch.

## 2026-07-26 — Navigation consolidated into a shared hamburger

**Decision (user):** one menu for every page, italic labels, inline nav retired with a
recoverable version. Tagged **`inline-nav-v1`** before removal.

**Placement — top-right, reasoned rather than defaulted.** The wordmark owns the left on
three of five pages and is the brand anchor; the archive's top-left holds the Carousel/Index
**lens toggle**, which is an in-page control and not navigation, so it stays. Top-right
carried only readouts (avatar, spend) and actions, both of which shift 46px without losing
meaning. Reading order also puts identity left and controls right.

**The reveal is the entrance run backwards.** The entrance dispels glyphs under a decaying
envelope with noise-clustered per-glyph delays; the menu resolves them under a settling one,
clustered by row so it materialises roughly downward while characters land out of order.

**Bug caught during removal:** the carousel bound its crossfade handler to
`#nav-left a[href="/fitting-room"]` — an anchor the consolidation deleted, so the query
returned null and the page script would have thrown on load, taking the whole carousel with
it. Now delegated at the document, which also survives the link living in the menu.

## 2026-07-26 — Insights: pictures and diagrams over number rows; stylist state line cut

**Stylist:** the ambient state line (garments / looks / never worn / idle value) is
**removed** — it duplicated `/insights`, which now owns those numbers. It was design option
6 from the 07-26 pass; superseded rather than wrong.

**Insights, made visual on her ask.** Order now tells a story rather than listing measures:
- **Unit chart first** — 58 marks, one per garment, ordered so the unworn block reads as a
  block. Four columns hid the population; this shows every garment and lets her hover any
  single one. Ramp steps encode wear count, oxblood is the reserved zero state, and a legend
  with counts is mandatory because identity must never rest on colour alone.
  The "1 wear" step was first `#c9c9c9` and measured **1.66:1** on white — invisible as a
  mark. Re-stepped to `#8f8f8f` (3.23:1), `#5c5c5c` (6.69:1), `#000`.
- **Meter** for the idle share — the skill's form for a single ratio against a limit, fill
  and track being steps of one ramp. Replaces a percentage buried in stat-tile subtext.
- **Photographs** for "most value never worn" and "earning their keep". The subject is
  clothes; numbers alone read as a spreadsheet about a wardrobe rather than a view of one.
  Cutouts already exist for 51 of 58 garments, so this cost nothing.

## 2026-07-26 — `/insights` shipped (Track C), $0

Second UI after the stylist. Same pattern: local-only, reads `closet_snapshot.json`,
no generation and no network.

**The honest-framing decision, and the one that mattered most.** Wear counts come from the
18 published looks — the only wear record that exists. A garment worn weekly but never
photographed reads as never worn. So every surface qualifies it ("no recorded wear", and a
standing caveat line under the KPI row). Shipping an unqualified "**$2,381 never worn**"
would have been an accusation the data cannot support, and the number is prominent enough
that the qualification has to travel with it.

**Form follows the dataviz method, not taste:**
- Headline numbers are **stat tiles**, not one-bar charts — closet value, value never worn,
  never-worn count, median cost per wear.
- Comparisons are thin horizontal bars (15px in a 28px band — air in the slot), 4px rounded
  data-end, square at the baseline, 2px surface gaps, recessive hairline baseline.
- Per-mark hover tooltips with the value leading and the label secondary; 37 marks are
  keyboard-reachable; a **58-row table view** means nothing is gated behind hover.
- **Not a categorical palette.** One ink (#000) for the single series, plus the brand's
  documented oxblood `#6F2B2B` alert token for the idle measure only. The validator's
  lightness/chroma checks are scoped to categorical palettes and do not apply; the checks
  that do — contrast vs surface — pass for all three inks, and oxblood separates from the
  greys at ΔE 24+ under deuteranopia. Status colour never appears without a written label.

**What the data says:** $6,298 closet · **$2,381 (38%) with no recorded wear** · 23 of 58
garments · median cost-per-wear $75, best is square-toe flats at $10.89 over 9 wears. Idle
value concentrates in dresses ($814) and tops ($791); shoes are only 3 garments but $578.

## 2026-07-26 — Phone layout fixed on the two public pages

**The bug (found 2026-07-21 in a portfolio sweep, never recorded in the repo until now —
it lived only in a memory note, which is why it sat for five days).** The live archive is
linked from her portfolio, so this was the only open defect strangers could see.

- **Archive carousel.** `#info` and `#controls` were fixed 350px panels pinned to opposite
  corners — 724px of chrome in a 390px window, so they overlapped and clipped each other's
  text. Slot geometry scaled a 1440px reference by `vw/REF_W`, rendering the flanking
  figures ~39px wide: smudges, not garments. There were **no media queries at all**; the
  page was built desktop-only.
  Fixed: below 760px the HUD stacks full-width (caption above controls, cleared by 98px for
  the two 40px control rows), and phones get their own slot geometry — hero at 70% of
  viewport height, neighbours peeking in at the edges to show the procession continues,
  ±2/±3 hidden. Verified at a true 390px viewport via CDP device emulation, not a resized
  window: `#info`/`#controls` 10–380, `#cta` 224–367, nothing clipped. Desktop geometry is
  untouched (regression-checked at 1440px).
- **Fitting room.** Also public (`vercel.json` rewrites `/fitting-room`) and worse: the
  three-column grid (240px | 1fr | 344px) squeezed the mirror to a ~50px strip with the
  caption running vertically. Below 760px the panels stack, mirror first. Sections size to
  content — the desktop layout pins them to a fixed-height column with nested scroll panes,
  which collapsed the outfit rail to one visible slot when stacked.

**Honest limitation, not papered over:** drag-to-dress is pointer-driven and does not work
by touch. Tapping a garment still equips it, which is the whole flow on a phone. The rack
hover-preview is hidden on narrow screens for the same reason.

**Not deployed.** The fix is on `2d-reboot`; the live site builds from `main`, which stays
untouched. Merging and redeploying is hers.

## 2026-07-26 — Stylist card hover reuses the index lens's chrome-silver

Hovering a suggestion now applies the **same gradient the carousel's index lens uses**
(`.gcell:hover`), so it is unambiguous which card a verdict will land on. Reused rather than
reinvented: the black invert was rejected there in 07-19 as too heavy at grid density, and
behind a glass panel it would be heavier still. Suppressed on cards already ruled on — they
are not inviting input. Incidental benefit: the glass panel finally has a tinted backdrop to
refract, which is the one thing the white void never gave it.

## 2026-07-26 — Suggestions fill exactly one row

**Her question: why 7?** No reason — `n=6` was an arbitrary default with the wildcard added
on top. Nothing was reasoned about it.

**Fixed 5 would not have worked either.** The grid is `auto-fill`, so the column count is a
property of the window (4 at ~1400px, 3 at ~1120px, 5 on a wide monitor) and any hard-coded
number wraps at some width. The count now follows the columns, with the wildcard taking the
last slot: 3 suggestions + wildcard at her width, 2 + wildcard when narrow. The client
over-fetches 8 and slices, so a resize re-lays out without asking the server for a different
set of clothes.

## 2026-07-26 — Flat-lay sizing is a fixed unit, not a percentage

Garment sizes were percentages of the card's height, so the hero — which is taller —
inflated everything inside it: the same tank rendered small in a grid card and enormous in
the lead. Sizes are now a fixed `--u` (236px; 290px in the hero), so proportion is identical
everywhere and the lead steps up by a bounded amount.

**Category turned out to be too coarse a scale key.** A mini skirt and a maxi skirt are both
`bottom`, so one height made the mini enormous and very wide. Scale is now computed
per garment server-side (`_draw_scale`) from its own name/fit text, which already carries
mini/midi/maxi: mini skirt 0.44, midi 0.76, trousers 0.88, maxi 0.98; tanks 0.52, sweaters
0.62; boots 0.46, other shoes 0.32. Width is capped alongside height, or a short wide
garment sprawls sideways when forced to a height. Reference photos are full-body shots and
take 0.86u — sized for the photo, not the garment inside it.

**Priority note (her question, agreed):** explore mode and pairwise compatibility are NOT
priorities. Both are reasonable ideas recorded for later; chasing them now would be
optimising a metric rather than serving the work. Revisit only if suggestions start feeling
stale in real use.

## 2026-07-26 — Rejections are COLLECTED but not applied (measured, twice)

**Question:** after 77 stylist judgements — all 42 rejections attributed to a garment —
does feedback improve prediction? Leave-one-out, so nothing scores its own verdict.

| model | AUC |
|---|---|
| published looks only | 0.572 |
| + feedback, rejections un-attributed | **0.420** (inverted) |
| + feedback, rejections attributed | 0.654 |
| + feedback, **positives only** | **0.668** ← shipped |

**Attribution was worth building** — it lifted rejections from actively inverted (0.420) to
roughly neutral. **But applying them still costs accuracy**, and a weight sweep is monotone:
ignore 0.638, 1× 0.605, 2× 0.577. Two independent datasets now agree (the 42-outfit blind
calibration and these 77), so `NEGATIVE_WEIGHT = 0.0`.

**Why, most likely: a rejection is contextual, not absolute.** 28 of 42 blames are shoes —
keen sandals six times, jil sander boots five. That means "wrong shoe for THIS outfit", not
"I dislike these sandals". A per-garment scalar cannot hold the difference, so the model
concludes she dislikes most of her shoes. **The blame data is still the right thing to
collect: it is the raw material for a pairwise compatibility model, which is what it
actually encodes.** Keep gathering it; do not feed it to the scalar.

**Second effect worth naming: range restriction.** Affinity scored 0.824 on the blind
calibration set but only ~0.67 here. The stylist now shows only what it already rates
highly, so the easy discrimination is gone and it is being graded on a narrow band of its
own choosing. An explore mode that samples across the range is the fix, and it is not built.

## 2026-07-26 — Stylist design pass: proportion, rationale, hierarchy, state

**Shipped (her picks 1/2/3/6 from the design options):**
1. **Flat-lay proportion.** Equal flex widths made a ballet flat the size of a pair of
   trousers — a row of product thumbnails. Garments now hang from a shared top line, scaled
   by category (dress 100% → shoes 26%), shoes bottom-aligned.
2. **Rationale.** Cards read "NO FLAGS", which is engine jargon. Now a sentence built from
   data already computed: "built around your samira draped tank", "first outing for the
   gorum wrap-collar shirt", with soft rules phrased as a caveat ("mixed warmth"). $0,
   deterministic templates, no LLM. Colliding garment names are disambiguated by measured
   dominant colour — three garments are called "scoop tank".
3. ~~**Hierarchy.** The lead suggestion spans two columns.~~ **REVERTED 07-26 (user):
   containers are uniform.** Built as designed, then rejected on sight — at this card size a
   double-width lead read as an inconsistency rather than as emphasis, and she wants one
   frame for every suggestion. (Spanning ROWS was also tried and was worse: the flat area
   grew unbounded and pushed the panel and actions off the card.) The rejected variant is in
   git history if hierarchy is ever wanted again.
6. **Ambient state line** — `garments 58 · published looks 18 · never worn 23 · idle value
   $2,381 · judgements 70`. Ties the stylist to the sustainability track in SYVE's own
   technical-label register.

**Deferred, her call: (4) vertical body-stacked outfits and (5) the wildcard styled as a
full-width interruption.** Both are good ideas; neither is a priority now.

**Attempted and REVERTED: cutouts for the 7 un-cut garments.** The `full`-mask + band
fallback that recovered them for colour extraction produces poor *silhouettes* — 09 and 47
came back with the model's hands and boots attached, 29 full of holes. A ragged silhouette
reads worse than the product photo, which is why dragcut fell back to framed cards in the
first place. `dragcut.py` left unchanged. Instead the stylist FRAMES those seven as
reference photographs at fixed size — a deliberate second register, matching the
silhouette-vs-framed-card distinction dragcut already makes.

## 2026-07-25 — Feedback is revisable everywhere (stylist + fitting room)

**Decision (user):** a judgement should never be final by accident. Applied first to the
stylist, then to the fitting room's feedback bar on her request.

**Pattern, both logs:** append-only. Re-judging appends a new verdict; undo appends a
tombstone (`retracted` for stylist outfits, `{"retracts": ts}` for feedback). A resolver
(`stylist_current()`, `feedback_current()`) takes newest-wins and only the surviving verdict
reaches the model. Changing your mind must not erase what you first thought, and a
retraction is itself a fact worth keeping.

**Fitting room specifics:**
- Undo lives in the **toast** and a **dialog**, never in the bar itself — the bar keeps its
  footprint so the centred mirror never shifts (standing rule, 07-15). The hidden bar
  already holds layout, so shown/hidden parity is structural.
- **Undo withdraws the record only.** A corrective render that already ran was billed and
  the file stays on disk; the UI says so plainly rather than implying the spend is reversed.
- `body.demo` already hides the whole bar, so the static Vercel export is unaffected.

## 2026-07-25 — `/stylist` v1 shipped (Track B), local-only, $0

**Decision (user):** first UI is the stylist, run **local-only**. Shipping it publicly would
put `APP_SECRET` in a public page, and that secret is what stands between the internet and
the fal budget — the exact guarantee the 07-25 hosted-Postgres reversal was granted on. A
Vercel serverless proxy holding the secret is the upgrade path when it earns it.

**Built:** `/stylist` route in `closet_server.py` + `app/stylist.html`. Reads
`server/scripts/closet_snapshot.json`, ranks with `engine.preference` (affinity), filters
with `engine.constraints`. Six suggestions + one wildcard. No generation, no LLM, no network.

**Three design calls worth keeping:**
1. **Diversity is enforced.** Pure ranking returned six variations of one favourite top,
   because affinity is a property of garments and the best garment wins every slot. A
   garment now cannot repeat until the pool is exhausted.
2. **The wildcard is deliberate.** Affinity ranks what she already wears, so the 23 unworn
   garments sit at neutral and lose forever — a filter bubble, and directly against Track C.
   One suggestion per load is the best outfit built around something never worn.
3. **Rejections ask which garment was wrong.** This is the fix for the attribution problem
   that made her calibration rejections *lower* prediction quality. Verified: blaming the
   loafers dropped them to 0.286 while the jeans in the same rejected outfit rose to 0.867.

**Occasion is an optional filter, not the primary input** — her occasion data is 12 "day
out" against 3 work / 1 dinner / 1 event / 1 home, so anything else is too thin to ground a
suggestion. Falls back to the full history when an occasion has fewer than 4 looks.

**Glassmorphism, honestly:** applied to the card info panel per the 07-25 re-homing, with
the flat-lay running behind it so it has a backdrop. It is still barely perceptible — the
same white-void problem that got it thrown off the archive. Kept because it is restrained
and SYVE-consistent, but it is doing very little work and dropping it would cost nothing.

## 2026-07-25 — Ranking calibrated: colour theory is chance, preference is learned

**Method:** blind set of 42 outfits — her 18 published looks (the control) mixed with 24
engine picks sampled across the score range, shuffled, **scores hidden** so they could not
anchor her answers. She judged all 42 "would wear / would not".

**Result, measured on the 24 engine picks the model never saw:**

| signal | AUC |
|---|---|
| colour harmony + constraints | **0.491** — chance |
| affinity learned from her 18 looks | **0.824** — predictive |
| looks + her negative verdicts | 0.583 — *worse* |

She would wear **18/18** of her own looks and **6/24** engine picks; of the 3 picks the
engine ranked in its top decile, 1.

**The finding: colour was not miscalibrated, it was the wrong signal.** What separates her
yes from her no is WHICH GARMENTS are in the outfit, footwear above all — camper flats 92%
accepted (11/12), weejuns loafers 0% (0/3), salomon sneakers 25%, vortex boots 17%, on
outfits whose colour logic is identical. All three rejected all-black outfits were
black-on-black with loafers or sneakers; the same colour logic with flats she accepts.

**Two wrong turns, caught by checking rather than reporting:**
1. Mean lightness spread looked decisive (would-wear ΔL* 40 vs would-not 63) and suggested
   "she dresses tonally". False — all-black outfits are accepted **12 to 3**. The means were
   driven by tails, not a tonal preference.
2. Affinity first measured AUC **0.928**. That was leakage: 18 of the 42 judged outfits ARE
   her looks and the affinity was built from those looks. Evaluated only on picks the model
   never saw, the honest figure is 0.824.

**Negative feedback is not yet usable.** An outfit-level "no" cannot be attributed — the
penalty smears across garments that were fine, which is why adding her rejections made
prediction worse. Capturing *which garment* killed an outfit is the fix; NOT built.

**Consequence for the architecture:** hard constraints filter (they work — all 18 looks
pass), learned preference ranks, colour is a tiebreak at low weight. `engine/preference.py`
learns smoothed per-garment affinity; `ranked_outfits(affinity=...)` leads with it. Her 42
verdicts persisted to `interaction_log` (24 favourited / 18 rejected); judged engine picks
stored as `outfit` rows with `source='stylist'`.

## 2026-07-25 — Phase 2 constraint engine built; its taste does NOT match hers

**Built ($0, offline, 26 unit tests passing):** `engine/colour.py` (LAB, neutral detection,
harmony), `engine/constraints.py` (hard structural rules vs soft judgement, kept strictly
apart), `engine/gaps.py` (enumeration, participation, orphans, cost-per-wear).
`scripts/dump_closet.py` snapshots Postgres to JSON so the engine stays a pure library.

**Acceptance met:** 2220 valid outfits = (21×10 + 12)×10, arithmetic confirmed; 13,320 with
outerwear. Scoring is instant. Her 18 published looks all pass the hard rules.

**THE FINDING — the engine's aesthetic prior disagrees with her.** Her 18 published looks
score at **mean percentile 39**, i.e. below the median outfit the engine would suggest.
Cause is measurable: **99.4% of all garment pairs in this closet are neutral-on-neutral**
(990 "neutral contrast", 392 "neutral-anchored", 176 "matched", 85 "slight mismatch" —
against just 10 chromatic pairs in the entire wardrobe). So colour harmony barely
discriminates, and what little it does comes from lightness separation: the rules reward
maximum contrast (white + greige + black = 0.900) and *penalise* tonal black-on-charcoal as
a near-miss (0.74). Tonal black is her signature. The rule encodes a generic styling
opinion that is demonstrably not hers.

**Not fixed unilaterally — she decides aesthetics** (standing rule). But there is now a
concrete calibration target: **tune until her own 18 looks rank high in the space they were
drawn from.** That is real ground truth, and it is the honest exit criterion for ranking.

**Rules corrected because her closet said so:**
- `look-023` (hoodie + trousers + sneakers) failed "no top". **Outerwear worn alone IS the
  top layer.** When the closet's own history fails a rule, the rule is wrong.
- Structural orphan detection returned **zero** orphans — with 21 tops and 10 bottoms
  everything pairs, so participation says nothing. Replaced by *quality* participation:
  how many ABOVE-MEDIAN outfits a garment can appear in. That list is all dresses.
- Outerwear was excluded from enumeration, which reported the entire outerwear rail as
  orphaned — an artifact of the enumeration, not a fact about the closet.

**Track C preview from real data:** 23 of 58 garments appear in no published look,
**$2,381 of value sitting unworn**; best cost-per-wear is 52-camper-flats at $10.89 over
9 wears.

**Data-loss bug found and fixed:** re-running `backfill.py` after the colour work **wiped
user-owned data** — `subcategory` reset to null and `occasion` was replaced out of
`outfit.context`. The garment upsert protected formality/warmth/season_tags but not
subcategory; the outfit upsert replaced `context` wholesale. Now: subcategory is never
written by backfill, and context MERGES (`outfit.context || EXCLUDED.context`). Verified by
re-running and confirming 58/58/18 survive.

## 2026-07-25 — Phase 1 backfill: objective half loaded, subjective half awaiting her

**Done ($0, no API calls):** 58 garments + 18 published looks are in Postgres. Garment ids
are the existing slugs, so render-id matching is preserved. Looks seed `outfit` as
`source='manual'` — the cold-start preference prior. `scripts/verify_backfill.sql` passes:
0 orphan references, 0 duplicates, 0 garments without colours, idempotent on re-run.

**Standing rule honoured — she decides aesthetics.** `formality` and `warmth` have no source
in `meta.json`, so they are NOT populated by the backfill and re-running never overwrites
them. They come from a $0 confirmation grid (`scripts/make_attr_grid.py` → `attr_grid.html`)
pre-filled with proposals derived from each garment's own text, so the job is confirming
rather than authoring 116 values. No Anthropic auto-extraction was run; it stays an
approved-batch item only.

**Colour extraction rulings (worth keeping):**
- On-model photos use **cloth-seg only, never the general model** — same rule as dragcut.py.
  The general model keeps the whole figure, so 26-liniss-dune-pants (sand) picked up a
  phantom 21% charcoal that was the *model's black halter top*.
- The 7 garments dragcut could never cut fail because cloth-seg files them under `full`
  and leaves upper/lower empty. Fallback: intersect `full` with a category-appropriate
  vertical band. Recovered all 7.
- **Colour-name anchors were recalibrated to how garments photograph, not to ideal
  swatches:** a real black top measures L*~15-22, so anchoring "black" at L*~7 sent every
  black item in the closet to "charcoal". 15 QA flags dropped to 6. LAB values were correct
  throughout — only the names were wrong, and LAB is what the engine consumes.
- Attribute proposals ignore `meta.notes`: it describes the *photo*, not the garment.
  04-structured-blazer's note "worn open over a white tee" was classifying a tailored
  blazer as casual.

**Finding for her verdict:** `36-realisation-liv-dress` has the wrong `meta.color` — recorded
as "violet-blue with dark leopard print", the garment is black with dark red spots. The
measurement caught a mislabelled garment. `meta.json` left unedited — her data, her call.

## 2026-07-25 — Phase 0 provisioned: Railway live, guardrails verified

**Decision (user):** subscribed to **Railway Hobby, $5/month** — the trial had expired and no
project could be created without it. A real recurring cost, distinct from the fal budget.
Alternatives were offered (free Neon Postgres with hosting deferred, or local Postgres) and
declined in favour of the plan of record: one vendor, no rework, worker support later.

**Live:** https://virtual-closet-api-production.up.railway.app · project `virtual-closet`
(Postgres 18 + `virtual-closet-api`, sfo), deployed from GitHub `2d-reboot`, root dir `server`.

**The reversal is now real and proven, not assumed.** Verified end to end: `/health` 200 open,
`/budget` **401 without the bearer token**, correct JSON with it — and that response is a
Postgres round-trip, so schema, connection, and the server-side budget gate are all confirmed
($0.00 of $45.00 spent, 0 generations). Auth + budget hard-stop stand between the public URL
and the fal budget, exactly as the 07-25 hosting reversal required.

**Scope held:** foundation only, $0 API spend. R2 credentials and the worker service are
deliberately deferred — neither is touched by Phases 1–2.

**Gotchas worth not re-deriving** (full list in `virtual-closet-v2-HANDOFF.md`): `railway up`
CLI upload 403s for reasons never established (GitHub deploy routes around it); `DATABASE_URL`
is per-service and must be a `${{Postgres.DATABASE_URL}}` reference; laptop-side migrations
need `DATABASE_PUBLIC_URL`; connecting the repo via the dashboard spawns a duplicate service.

**`main` stays untouched** — it is what Vercel builds the live archive from. The pivot lives on
`2d-reboot`; do not merge. This preserves the additive-identity decision.

## 2026-07-25 — v2 pivot: decisions locked + hosting reversal

**Context:** rolled back to the 2D app (branch `2d-reboot`, HEAD `3b069e0`); the 360/
avatar-v4 work is archived on `archive/360-avatar-v4-20260724`. New spec
`virtual-closet-plan-v2.md` reframes the app from an aesthetic lookbook to a utility
wardrobe tool (tracks A ingestion / B stylist / C sustainability / D style+gap /
E constellation / F spin). Reconciled foundation plan: `virtual-closet-v2-foundation-plan.md`.

**Decisions (user):**
1. **Persistence = hosted Postgres** — deliberately REVERSES the 07-20 "no live endpoint
   in front of the fal budget" rule. Consequence: auth + a server-side budget hard-stop are
   now load-bearing, and both ship in the Phase 0 scaffold (`server/app/auth.py`,
   `server/app/budget.py` — a Postgres port of genlog).
2. **Host = Railway + Vercel + Cloudflare R2.** Railway (Postgres + API + worker), Vercel
   (frontend; the archive stays put), R2 (object storage — Railway has no native blob).
   No strong reason for Supabase at single-user scale; R2 is the only added piece.
3. **Scope = foundation only** (Phases 0–2: infra+guardrails → schema+backfill → constraint
   engine). ~$0 on API calls. Stop and choose the first UI with real data in hand.
4. **Identity = additive.** The SYVE archive carousel stays the front door; `/stylist`
   `/insights` `/galaxy` are added later under the same language. The gallery is unchanged.

**Sequencing note:** v2's stated "Track A first" is wrong for this closet — it is already
tagged (58 garments, 18 looks), so bulk ingestion is not the bottleneck. The real critical
path is schema migration + attribute backfill + the constraint engine; the 18 looks seed
the outfit table as a cold-start preference prior.

## 2026-07-25 — Glassmorphism: re-home from the archive to `/galaxy`

**Decision (user, agreed):** The 07-23 "carousel detail glassmorphism exploration" is
**re-homed.** Do NOT apply glassmorphism to the archive carousel/detail overlay.

**Why:** SYVE's language is a white void + 1px black hairlines + hard edges. Frosted
translucency fights that austerity and has no rich backdrop to work over on a white void +
figure cutout — it reads as decoration and muddies the crispness that is the brand.

**Where it goes instead:**
- **Primary: the constellation dashboard (`/galaxy`, Track E).** Glass is native here — a
  dark field with glowing nodes and depth-of-field blur is exactly what glassmorphism is
  for (a HUD floating over a live nebula, glow bleeding through). The dark backdrop is what
  makes frosted glass legible.
- **Secondary, restrained: stylist suggestion cards (`/stylist`, Track B)** over the flat-lay
  composite — translucency signals "ephemeral suggestion, not yet committed."
- **The archive stays glass-free** on purpose. The crisp-archive ↔ atmospheric-galaxy
  contrast is a feature.

**Timing:** parked as a design study to resolve when `/galaxy` (Phase 5) is designed. It
does not block the foundation; building it against the archive now would solve it in the
wrong context.

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
