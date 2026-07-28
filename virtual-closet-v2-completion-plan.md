# Virtual Closet v2 — Completion Plan (Phases 4–6)

> Written 2026-07-27. Covers everything left between today's state and "finished."
> Successor to `virtual-closet-v2-foundation-plan.md` (Phases 0–2, done) and the Phase 3
> wear-logging work (done). Full track spec is `virtual-closet-plan-v2.md`; `CLAUDE.md`
> remains source of truth for what is actually built.

## Locked decisions (2026-07-27)

| Decision | Choice | Consequence |
|---|---|---|
| Definition of finished | **Both, showpiece first** | The five public pages get presentable before the modelling work resumes. Utility gaps are not abandoned — they move behind the surfaces. |
| Budget posture | **fal + Anthropic, gated** | Track A's paid half and Track D's style profile are back on the table. Standing rule #1 still holds: approved batches only, every call through `genlog.py`. |
| Stylist accuracy | **Wait for ~50 wears** | The 0.555 problem is not attacked now. It is calendar-gated, so it goes last and everything else fills the wait. |

**The shape this produces:** the one item that cannot be hurried (wear data) is the one item
scheduled last. Phases 4 and 5 are the work that fits inside the waiting period.

---

## Phase 4 — Showpiece (the next 1–2 sessions)

Goal: an interviewer opening the site sees five finished pages, not four finished ones and
a rendering pass in progress.

### 4.0 Unblock spend — do this first, everything paid waits on it

- Top up fal. The balance is **-$0.08**, which is why the last batch "kept exhausting."
- Recover the **$0 pilot segment** already paid for: request_id
  `019f8b35-0d15-7f41-99fa-2556b24f03fd`. Free, and it is the evidence for whether hero-look
  video is worth $3.20 a look.
- Confirm the genlog cap before approving anything — the two docs disagree ($25 vs $45).
  `python3 scripts/genlog.py summary` is authoritative. Raise it deliberately if Phase 4+5
  needs more headroom than it has.

**Cost:** the top-up itself. Everything below is priced against it.

### 4.1 Render coverage — **SCOPED 07-27 by audit, not by assumption**

Her chosen reading of "fitting-room rendering updates." Audited with
`virtual-closet/scripts/render_coverage.py` (re-runnable, $0, no deps — the acceptance check
for this section), which mirrors `closet_server.garment_list()`'s visibility rules exactly
(hidden.json + `is_posed` + `_raw`), so "visible" means visible in the app.

**The result inverts the premise: garment-level coverage is already complete.**

| Check | Result |
|---|---|
| Garments with no visible render | **0 of 58** |
| Garments still on legacy avatar-v1 only | **0 of 58** |
| Garments with no render cutout | **0 of 58** |
| Published looks missing a render or cutout file | **0 of 18** |

Nothing is invisible in the fitting room and there is no stale-lineage backlog — the 07-16
batch and the 07-14 v3 re-render did their job. **So this is not a "fill in the missing
renders" job**, and a batch proposed on that premise would have spent against a gap that does
not exist.

The four coverage gaps that *are* real differ in kind:

#### A. Opening a look in the fitting room does not try it on — **her diagnosis 07-27, and the priority**

**The renders exist and are already served.** `looks_list()` resolves each look's render to an
asset URL, and all 18 published looks have both a render and a cutout file on disk. **The stage
simply never displays them.** Two code paths, one behaviour:

- `app.js:84` — a look arriving from the carousel: `if (kind === "garment" && items.length === 1)
  tryOn(...)`. A look fails that condition, so it loads slots and shows the **base avatar**. The
  comment records it as intentional: *"looks arrive as loaded slots + base avatar (front-only
  stage)."*
- `app.js:loadLook()` — clicking a look in the fitting room's own rail: sets slots, calls
  `renderSlots()`, toasts. **Never touches `#stage-img` either.**

So it is not a missing-asset problem and not a spend problem — it is four lines of wiring. But
the reason it was written this way is real, and it is why this needs her call rather than a fix:

**The archive-only pose rule (07-14) says the fitting room shows front renders exclusively**,
and `is_posed()` enforces it server-side for garments. Only **7 of 18 looks are front pose**;
the other 11 are 34turn (5), contrapposto (3) or hand-on-hip (3).

**And the poses are a different shape:** front look renders are **1024×1024**, posed ones are
**922×1152**. Putting a posed render on the stage changes the mirror's aspect ratio — which
collides with the standing rule that **the centred mirror must never shift** (the same rule that
shaped the feedback bar's hidden-but-footprint-preserving behaviour).

Three ways to resolve it:

| Option | Cost | Trade-off |
|---|---|---|
| **1. Show whatever render the look has** | **$0** | All 18 work immediately. Softens the archive-only pose rule and the stage changes aspect between looks. |
| **2. Show it only for the 7 front looks** | **$0** | Rule intact, but 11 of 18 looks still do nothing — inconsistent in use, arguably worse than today. |
| **3. Render front versions of the 11** | **~$0.65** | Every look tries on, rule intact, mirror never shifts. Costs a second render per look (archive keeps the pose, fitting room uses front). |

**RESOLVED 07-27: she chose Option 3, and it is DONE.** 18/18 looks now try on.

- **The aspect-ratio column above was wrong** and is left standing as the record of a bad
  argument. Front renders are *not* uniformly square (1024×1024, 922×1152, 896×1183, 843×1264
  all occur), and `#stage-frame` has been a fixed rectangle with `object-fit: contain` since
  July anyway — CDP-verified at 760×712 across both a square and a portrait render. **Option 3's
  only real justification is the archive-only pose rule.**
- **The batch was 9, not 11** — looks 004 and 006 already had clean front renders on disk.
  Pilot (look 018, the hoodie-as-top edge case) + 8: **$11.837 → $12.309, i.e. $0.53 total**,
  cap $25. All 9 QA'd on a paired contact sheet against their published counterparts; fidelity
  holds — same garments, colours and construction in every pair, including the difficulty-5
  draped maxi (look 012) and the 4-item stack (look 015).
- **CLOSED 07-27 (her call): the hood stays DOWN.** Look 018's published render is a deliberate
  hood-up variant and the fitting-room twin is hood-down; the two differ on purpose. Do not
  re-render it to match.
- Verified through the real door (CDP, localStorage handoff → `/fitting-room`), and the static
  export bundles all 9 (`asset_urls()` is generic, so `stage_render` is collected without
  changes — assets 303 → 353 files, 93 MB). 35 engine tests pass.

#### B. 23 garments appear in no published look — **DROPPED 07-27, her call. Do not re-propose.**

Kept below as the record of what was measured, not as pending work.

The carousel has been outfits-only since 07-19, so a garment in no published look **never
appears in the archive at all**. 23 of 58 are in that state — and 10 of them have logged wears,
i.e. she demonstrably wears them and the archive does not know:

- **Worn but unrepresented:** `54-salomon-sneakers` (2 wears); `04-structured-blazer`, `12`,
  `13`, `18`, `19`, `36`, `41`, `45`, `51` (1 each).
- **Never worn, unrepresented:** six maxi/slip dresses (`14`, `17`, `21`, `33`, `34`, `39`)
  plus `16`, `20`, `28`, `31`, `40`, `43`, `58`.

**Cost: ~$0.059 per look render**, cutout $0 local. Covering all 23 takes roughly 8–10 new
looks at 2–4 garments each → **under $1 for the whole batch**, retries included. By far the
highest visual return per dollar left in the project.

**Method — close the Track B ↔ archive loop instead of hand-picking.** The stylist engine
already ranks valid outfits; filter its candidates to those containing an unrepresented
garment, she approves what she likes, and they go through the *existing* publish pipeline
(SAVE LOOK → pose picker → render + cutout → carousel). No new code path, and it gives the
stylist a job it is already good at rather than one it measurably is not.

**Two cautions to raise before rendering:**
- **Three of the 23 are the footwear she rejects** — weejuns 0% accepted, vortex 17%, salomon
  25% in the blind calibration. Do not force looks around them just to complete a set.
- **Salomon is simultaneously the most-worn of the 23.** Stated preference and lived behaviour
  disagree on one garment — the 07-27 finding in miniature. Flag it; do not resolve it by fiat.

#### C. 7 garments have no transparent silhouette — a photo problem, not a render problem

`08, 09, 26, 29, 30, 47, 48` have no `_dragcut`, so they fly as framed cards in drag-to-dress
and are framed as reference photos in stylist flat-lays. Generating silhouettes was **tried and
reverted on 07-26** — band-mask output came back with the model's hands and boots attached,
worse than the photo. **No amount of try-on rendering fixes this.** The real routes are better
source photos (§5.3) or a proper segmentation pass (§5.1's SAM 3), so it belongs in Phase 5 —
stated here so it stops reading as a rendering backlog.

#### D. Pose coverage is 3/58 — by design, not a gap

Only `01`, `02` and `04` have non-front pose renders. Poses have been archive-only since 07-14:
the fitting room shows front renders exclusively and the server filters pose-tagged stems out.
Published looks carry the variety instead (7 front · 5 34turn · 3 hand-on-hip · 3 contrapposto).
**Rendering the other 55 on poses would cost ~$3.25 and change nothing any page displays.**
Not unless the archive-only rule is being deliberately revisited.

**Constraints on any render here:** face-swap finish on any visible face (rule #2), never edit
the avatar's head region with NB models, neutrally-worded prompts (rule #3), corrective notes
batched into one pass (chained correctives compound face drift), and difficulty-4/5 garments
stay on the front pose — which catches **40-realisation-sheer-top (4)** and
**43-subtle-mermaid-top (5)** in list A.

**Sequence:** pilot one look → she judges → approved batch → QA on contact sheets → commit.
Same loop as the 58-garment batch; the pilot is what caught the 10 prompt failures there.

### 4.2 Galaxy time scrubber (plan E.4) — **DONE 07-27, $0**

**Built on ACQUISITION, not wear — her call, after the data was checked.** The wear log turned
out to be 15 rows, exactly one per day across a single fortnight; replaying that is a ticker.
Purchase dates span 2018-10 → 2026-07 across 27 months and carry the shape worth watching:
27 garments over seven years, then **31 in 2026 alone**. E.4's own promise — *"a March purchase
that never lit up becomes obvious"* — describes acquisition, not wear.

- Presence composes into the existing `rv` reveal value, so nodes, edges, halos and plates gate
  together; edges needed no special case. Positions are not recomputed while scrubbing, so the
  field fills in rather than reflowing. Playback ~230ms/month (~6s), on the clamped delta.
- **Honesty constraints:** the oxblood ring is today's state, not that month's (said in a
  standing caveat line); the never-worn panel is scoped to garments owned at the cutoff; an
  empty panel says so rather than showing a bare header.
- Verified over CDP on a real clock (never `--virtual-time-budget`): monotonic 1 → 33 → 58,
  edges 0 → 26 → 102, future garments unclickable, playback terminates and resets its button.
  35 engine tests pass; the deployed payload carries all 27 months.

**The wear axis is not lost** — revisit it as a second mode at ~50 wears, when it can carry one.

### 4.3 Design decisions already queued — **DROPPED 07-27, her call. Do not re-propose.**

Galaxy title type, non-black galaxy ground and carousel glassmorphism were each raised, looked
at, and tabled — and are now closed rather than pending. The previews already built stay on
disk. Original notes kept below for context only:

- **Galaxy title type** — six treatments already previewed in
  `design-inspo/galaxy-title-previews/`. Pick one or close the topic.
- **Non-black galaxy ground** — her idea, and technically the strongest of the three: the
  glass has almost nothing to refract against near-black. Touches the Ink palette decision,
  so it is a discussion before it is a build.
- **Carousel detail glassmorphism** — the original 07-23 study, re-homed to galaxy and
  stylist. Decide whether the carousel half is genuinely dead or still wanted.

### 4.4 Hero-look video — only if 4.0's recovered segment is good

$0.40/segment at 720p = **$3.20 per look**, so this is 2–3 hero looks (look-023, look-014,
a dress), never catalogue-wide (~$243). Her judgement on the recovered pilot decides it.

**Phase 4 acceptance:** all five pages presentable at desktop *and* 390px; no queued design
question still open; fitting-room rendering shipped to whatever spec 4.1 lands on.

---

## Phase 5 — The two unbuilt tracks (paid, gated)

This is where the "fal + Anthropic, gated" decision actually gets spent. Both tracks were
specced in v2 and neither exists.

### 5.1 Track A, paid half — multi-garment detection + vision tagging

Structurally pre-built for: `/ingest`'s `stage` already takes one image and returns one
garment, so detection is **N calls into the same commit path, not a rewrite**.

- SAM 3 detection (fal) → per-instance crop, then the existing quality gate decides
  `render_ready` vs `catalog` — the two-tier model is already implemented and honest in the UI.
- Vision-LLM attribute extraction (Anthropic) for category/pattern/formality/warmth, pre-filling
  the confirmation grid she already prefers over TSV.
- **Keep the programmatic colour path.** `extract_colors.py` does LAB k-means with white-balance
  normalisation — invariant #6 says the LLM only *names* colours, never measures them. That rule
  survived a QA round against her own eyes and should not be relaxed.

**Build only if tagging, rather than photographing, turns out to be the bottleneck.** For one
to three items at a time the $0 path may simply win; the spec was written for a 0→58 cold start
this closet is long past.

**Acceptance (v2 §9):** 10 mixed photos → ≥80% correctly detected and tagged after one pass.

### 5.2 Track D — **D.4/D.5 DONE 07-27 ($0). D.1 style profile still open.**

Built: `hypothetical_unlocks()` + `rediscovery()` in `engine/gaps.py`, surfaced as `/insights`
sections 08–09, 41 engine tests. See the Track D section of `CLAUDE.md` for the measurements.

**The headline finding: D.4's purchase recommender has nothing true to say about this closet,
and waiting for wear data will not change that** — `hard_violations` is slot-counting, so
attributes cannot discriminate on validity; `orphans()` is empty; every never-worn garment
already sits in 60–2,220 valid outfits. Fixed by counting GOOD outfits against the closet's own
median instead of valid ones, which makes formality and warmth discriminate honestly.
**Colour is excluded and this is the proof of the standing rule:** held equal, black unlocks
101 good outfits to white's 208, so a colour-aware recommender would tell her to buy white and
avoid black — her signature — on a signal measured below chance against her wears.

**Still open: D.1 style profile** — LLM-maintained from `interaction_log`, and **invariant #10
requires it be user-visible and user-editable**. Needs Anthropic calls, so it is a gated spend.

*(Original scope note below.)*

### 5.2b Track D as originally scoped

The last fully untouched track, and materially better now that real wear data exists.

- **D.1 style profile** — an LLM-maintained document regenerated from `interaction_log`, not a
  trained model (invariant #3). **Invariant #10 is non-negotiable: it must be user-visible and
  user-editable.** Cheap — one Anthropic call per regeneration.
- **D.4 gap analysis, steps 4–5** — this half is **$0 combinatorics, not AI**, and it is the
  piece `/insights` is currently missing. Participation counts already ship; what does not is
  *"your 4 dressy tops pair with only one bottom — a mid-grey tailored trouser creates 11 new
  outfits."* Specific, verifiable, immune to hallucination.
- **D.5 guard rails, stated because this is where the project's premise is easiest to lose:**
  default to unlock rather than acquire, gate purchase suggestions behind a real threshold
  (≥8 new outfits), always show the math, and **never any affiliate link** (invariant #7).
- Feeds the **ghost nodes** on `/galaxy` (E.2) — a proposed missing item drawn with dotted
  edges to every orphan it would connect. That is the single strongest visual in the E spec
  and it has been unbuildable until now.

**Acceptance:** style profile visible and editable; at least one specific, math-backed gap
recommendation.

### 5.3 Find-a-better-photo search — stretch, build last or not at all

Reverse image search is blocked (Lens has no API, Bing Visual Search retired, TinEye matches
exact reuse). The workable route is **identify-then-text-search**, reusing `ingest_fetch.py`
and the `/sourcing` grid; only the identification call and the search API are new.

Be honest about its value: for ~10 items, searching the brand herself and pasting a URL is
faster and free. **It wins on garments she cannot identify** — a model reading a care label
beats her there — and does nothing for a plain black tank.

### 5.4 Renders for accepted stylist outfits — her note 07-27, LOW priority

**Ranked explicitly: below everything above it, above Track F 360 spin.** Recorded here so it
does not get lost and does not get pulled forward.

When she accepts a stylist suggestion, generate a real try-on render for it rather than leaving
it a flat-lay. Most of the machinery exists — an accepted suggestion is already an `outfit` row,
and `tryon.py --outfit` renders an arbitrary garment set — so the work is the *policy*, not the
pipeline:

- **Invariant #4 is the constraint: never render speculatively.** Only accepted suggestions, only
  on demand, never the whole ranked pool. At ~$0.059 each, rendering suggestions eagerly is how
  this becomes the runaway cost the risk register warns about.
- **Cache on `avatar_version + sorted(garment_ids)`** (§B.3) so re-accepting the same combination
  is free. This matters more here than anywhere else: the stylist re-rolls, so the same outfit
  will recur.
- Decide whether an accepted-and-rendered outfit is publishable to the archive. **Note the
  standing rule only bars *logged* outfits from the carousel**, so a stylist outfit she likes
  could legitimately go through the normal publish path — but that is a new decision, not an
  extension of an existing one, and it would blur "the archive is curated" if done automatically.
- Best built **after** §4.1 A resolves, since it inherits whatever that settles about poses and
  the stage.

---

## Phase 6 — The stylist model (calendar-gated, ~50 wears)

Deferred by decision, not by difficulty. Everything above is designed to fill this wait.

### 6.1 Keep logging

`/wear` is deployed and writing. **This is the only input Phase 6 needs, and it accrues for
free.** At 15 today, ~50 is the threshold where the CIs stop overlapping enough to choose
between candidate models.

### 6.2 Re-measure, then choose

The measurement harness already exists — `scratchpad/heldout_wear_test.py` and
`loo_wear_test.py`, using the same `auc` function as the original blind calibration, so the
numbers stay comparable across every decision this project has made. Re-run all three
candidates against the larger test set:

| Candidate | Why it might work | Already available |
|---|---|---|
| **Pairwise compatibility** | Her blame data encodes exactly this — which garment killed which outfit | `interaction_log.reason_code` |
| **Context / occasion** | A Tuesday is a context; wear prediction may be mostly situational | `outfit.context` populated |
| **Frequency-normalised affinity** | Down-weights defaults, so jeans stop dominating | trivial change to `preference.py` |

**Note pairwise was closed on 07-26 and that call predates the 07-27 finding that a
per-garment scalar cannot reach the wear target. It is reopened by evidence, not by whim.**

### 6.3 What is already settled — do not retry

Three negative results, each measured on independent data. They are the map of where not to go:

- **Colour theory does not predict her taste.** 0.491 on stated verdicts, **0.360 — below
  chance** — against real wears.
- **Rejections cost accuracy** even when correctly attributed. `NEGATIVE_WEIGHT = 0.0`.
- **Wears must not feed affinity.** Leave-one-out cost 0.120–0.172 AUC. `PRIOR = ("manual",)`.

Same root cause in all three: **a per-garment scalar cannot hold context.** Any candidate that
reduces to one is going to fail the same way.

**Acceptance:** a model that beats 0.660 / 0.555 held out against real wears — or a documented
finding that at this closet size nothing does, which is itself a legitimate result and should
be written up rather than buried.

---

## Formally out of scope — close these, don't leave them ambient

- **Weather / Open-Meteo and the 4-tap quiz** (§5.B.1). Specced, never built, and the stylist
  works without them. **Decide explicitly: build in Phase 6 alongside context, or strike from
  the definition of done.** Leaving it half-remembered is what makes a project feel unfinished.
- **Track F 360 spin.** Rolled back deliberately; lives on `archive/360-avatar-v4-20260724`
  plus 2.1 GB parked locally. Not returning this iteration.
- **Entrance passphrase gate.** Built, worked, reverted — the site stays public for
  interviewers. Vercel Deployment Protection is Pro-only; do not re-propose it.
- **Closed by her verdict:** stylist index/catalog numbering, explore mode, vertical
  body-stacked cards, wildcard-as-interruption.

## Definition of done for the whole project

- [ ] Five pages presentable, desktop and phone (Phase 4)
- [ ] **Opening a look in the fitting room actually tries it on** (4.1 A)
- [ ] The 23 unrepresented garments reach the archive (4.1 B)
- [ ] Galaxy time scrubber live (4.2)
- [ ] Every queued design question answered yes or no (4.3)
- [ ] 10 photos → ≥80% auto-tagged after one pass (5.1) *— or explicitly dropped*
- [ ] Style profile visible and editable (5.2)
- [ ] At least one math-backed gap recommendation, ghost nodes on galaxy (5.2)
- [ ] Stylist re-measured at ~50 wears; best candidate shipped or the null result documented (6.2)
- [ ] Weather/quiz built or struck from scope
- [ ] *(low, optional)* accepted stylist outfits can be rendered on demand (5.4)

## Standing rules that govern all of it

1. **Spending is gated** — approved batches, every call through `genlog.py`, never bypassed.
2. **She decides aesthetics** — build it, show it, expect rejection. Rejected variants get tags,
   never deletion.
3. **Both stores or neither** — a garment written to `meta.json` and not Postgres is invisible
   to every page that reads the snapshot.
4. **Re-dump the snapshot after any data change, then run the engine tests** — `TestRealCloset`
   reads it, and a suite that passes pre-dump can fail post-dump.
5. **A push to `main` redeploys both the site and the API.**
6. **Logged outfits never reach the archive carousel.**
