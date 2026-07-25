# Virtual Closet — Implementation Plan

> **For agent use.** This is the working spec for the virtual closet app. Read §2 (Invariants) before writing any code — those rules are non-negotiable and several of them contradict the obvious implementation. Each track in §5 is independently implementable; check `Status` before starting. Suggested drop-in location: repo root as `PLAN.md`, or reference from `CLAUDE.md`.

---

## 1. Project state

**Built and working:**
- 2D closet (garment library with images)
- 2D fitting room (avatar + single-garment try-on rendering)
- Avatar generation from face photos + body measurements

**This plan covers (in priority order):**
| Track | Feature | Status |
|---|---|---|
| A | Bulk garment ingestion (auto-identify from photos) | Not started |
| B | Occasion stylist (quiz → 3 outfits) | Not started |
| C | Sustainability metrics | Not started |
| D | Style learning + gap analysis | Not started |
| E | Constellation analytics dashboard | Not started |
| F | 360 spin view | Not started — lowest priority |

Tracks A→D have forced dependencies (each consumes the previous one's data). E depends on C/D data but can prototype early. F is fully independent and should not block anything.

---

## 2. Invariants — do not violate

These exist because the naive implementation is wrong in each case.

1. **Never pass the full closet into an LLM prompt and ask for outfits.** Filter deterministically first (§5.B.2), then let the LLM rank a small candidate pool. Full-closet prompting hallucinates garments and degrades as inventory grows.
2. **Always validate returned garment IDs against the candidate pool.** If the LLM returns an ID not in the pool, reject the response and retry. No exceptions.
3. **Do not train a model.** Single-user scale (hundreds of interactions) is wrong for ML. Use counters, embeddings, and an LLM-maintained profile document (§5.D.1).
4. **Never render try-on images speculatively.** Suggestions display as flat-lay thumbnail composites (free). Avatar renders are generated on demand only, and cached by `avatar_version + sorted(garment_ids)`.
5. **Two asset tiers are mandatory** (§5.A.1). A garment can exist as catalog-only. Do not require a render-ready asset for a garment to participate in outfit planning.
6. **Store colour as LAB, not names.** The styling engine needs numeric distance. Names are for display only.
7. **No affiliate links, ever.** Gap analysis recommends purchases; monetising that recommendation invalidates the sustainability premise.
8. **Design every usage-dependent feature to work at 30% wear-logging compliance.** If it only works at 90%, it does not work.
9. **GPU inference never runs on the app server.** Segmentation, generation, and 3D reconstruction are hosted API calls. The backend orchestrates only.
10. **The style profile must be user-visible and user-editable.** Non-negotiable for trust and for correcting bad inferences.

---

## 3. Stack

| Layer | Choice | Notes |
|---|---|---|
| Backend / hosting | Replit, Railway, Render, or Vercel+Supabase | Needs: secrets, async job queue, Postgres, object storage, public URL |
| Database | Postgres | |
| Segmentation | **SAM 3** (text-prompted, native) via hosted API | Not Grounded SAM — SAM 3 removes the DINO+SAM chaining and its error propagation |
| Segmentation fallback | Grounded SAM (Grounding DINO + SAM2), Apache 2.0 | Only if licensing or self-hosting demands it |
| Clothing-specific alt | Human-parsing model (collar/sleeve/skirt classes) | Benchmark against SAM 3 on real garment photos before committing |
| Image generation / try-on | fal.ai (model-agnostic aggregator) | Swap models via config, not code |
| Vision + reasoning | Anthropic API | Attribute extraction, outfit composition, style profile, cluster labelling |
| Weather | Open-Meteo | Free, no API key |
| Graph rendering | d3-force on canvas | 2D only — see §5.E.3 |

**Do not use an AI agent to build the hard parts unsupervised.** Prior attempts at the 360 spin failed this way: the agent produced a viewer while the actual blocker was asset generation quality.

### Environment variables
```
DATABASE_URL
FAL_KEY                 # generation, SAM 3, image-to-3D
ANTHROPIC_API_KEY       # attribute extraction, stylist, style profile
STORAGE_BUCKET_URL
BUDGET_CAP_USD          # enforced in the generation logger; hard-stop
```

### Repo structure
```
/api            # endpoints (§4)
/engine
  /constraints  # deterministic outfit filtering + validity rules
  /colour       # LAB conversion, harmony scoring, palette extraction
  /gaps         # participation counting, orphan detection
  /profile      # style profile generation
/ingest         # detection, attribute extraction, dedup
/render         # try-on job orchestration, cache keys
/web            # frontend
/prompts        # versioned LLM prompt templates
/logs           # generation log schema + cost meter
```

---

## 4. API surface

```
POST /ingest              # batch photo upload → detection job
GET  /ingest/:jobId       # poll → proposed garment list for confirmation
POST /garments/:id        # confirm/edit auto-tags
POST /garments/merge      # duplicate resolution
POST /stylist             # quiz answers → 3 outfit proposals (flat-lay, no render)
POST /tryon               # garment_ids + avatar_version → render job
GET  /tryon/:jobId        # poll → image URLs
POST /wear                # log a worn outfit
GET  /insights            # utilization, cost-per-wear, gap analysis
GET  /graph               # nodes + edges for constellation view
```

All generation endpoints are async. Nothing blocks a request for 20s–4min.

---

## 5. Tracks

### 5.A — Bulk garment ingestion

**Goal:** user uploads photos in bulk; app produces a tagged closet without manual cropping.

#### A.1 Two asset tiers (invariant #5)
- **`catalog`** — recognised and tagged; participates in outfit planning. Partial visibility is sufficient.
- **`render_ready`** — clean, unoccluded, background-removed; suitable for try-on generation.

Prompt for a better photo only when the user attempts to render a catalog-tier item.

#### A.2 Pipeline
```
batch upload
  → SAM 3 detection, prompt: "shirt. dress. trousers. jacket. shoes. skirt. sweater. coat."
  → per-instance crop + mask
  → quality gate: occlusion %, resolution, aspect ratio, blur score
      pass → render_ready (bg removed, normalised)
      fail → catalog
  → attribute extraction (A.3)
  → duplicate check: embedding similarity vs existing closet
  → confirmation grid (A.5)
  → commit
```

#### A.3 Attribute extraction — split by method
| Attribute | Method | Reliability |
|---|---|---|
| Category / subcategory | Vision LLM | High |
| Dominant + secondary colour | k-means in LAB space (programmatic); LLM names it only | High / Medium |
| Pattern | Vision LLM | High |
| Formality 1–5 | Vision LLM with explicit rubric in prompt | Medium — expect correction |
| Warmth 1–5 | Vision LLM + fabric heuristic | Medium |
| Season tags | Derived from warmth + fabric | Medium |
| Fabric / material | Vision LLM | **Low — models guess.** User-confirmed or from purchase data |
| Fit | Vision LLM | Medium |

Normalise white balance before colour extraction. Warm indoor light reads cream as beige and navy as black.

#### A.4 Input types and expected quality
| Input | Result |
|---|---|
| Flat lay, items separated | Best case — near-perfect. **Document this as the preferred format.** |
| Single garment, plain background | Excellent |
| Worn outfit photo | Tops usable, bottoms poor (occlusion, pose distortion, tucked hems) → catalog |
| Closet rail | 10–20% visibility per item → catalog only |

Surface expectations in the UI: *"48 items found — 12 ready to try on, 36 need a solo photo."*

#### A.5 Confirmation grid
Target **~5 seconds per item**, not zero-touch. Grid of detected items, pre-filled tags, tap to correct, swipe to delete, long-press to merge duplicates. This beats manual cropping and is honest about detection limits.

**Acceptance:** 10 mixed photos → ≥80% of garments correctly detected and tagged after one confirmation pass.

---

### 5.B — Occasion stylist

**Goal:** short quiz → 3 outfits built from owned items.

#### B.1 Quiz — 4 taps maximum
1. Occasion (work / casual / dinner / event / active / travel)
2. Time (day / evening)
3. Venue (indoors / outdoors / mixed)
4. Location — defaults to saved home location

**Do not ask for weather.** Fetch it from location + date via Open-Meteo. Removes a tap and yields better data (temperature, precipitation, wind) than a user's subjective "cold."

Optional freeform context field ("meeting my partner's parents") passed to the LLM as extra signal.

#### B.2 Architecture — constraints first, LLM second
```
quiz answers + fetched weather
  → CONSTRAINT FILTER (deterministic)
      · warmth band from temperature
      · formality band from occasion
      · precipitation → require outerwear / appropriate footwear
      · exclude in-laundry / recently-worn (configurable)
  → candidate pool (typically 15–40 items)
  → COMPLETENESS RULES
      valid = (top + bottom | dress) + shoes [+ outerwear if required]
  → COLOUR HARMONY SCORING (deterministic, LAB distance:
      neutral detection, analogous / complementary / monochrome)
  → top ~20 valid combinations
  → LLM RANKS & COMPOSES: selects 3, writes rationale, applies style profile
  → VALIDATE every returned garment_id against the pool; reject + retry on miss
```

Deterministic layer guarantees *wearable*. LLM layer provides *taste*. Neither does the other's job.

#### B.3 Presentation and cost
1. Render each suggestion as a **flat-lay composite of existing garment thumbnails** — instant, zero generation cost.
2. `Try it on` triggers avatar rendering for that one outfit only.
3. Cache on `avatar_version + sorted(garment_ids)`.

Per-suggestion actions: `Try on` / `Wear today` / `Not this` (+ optional one-tap reason).

**Acceptance:** 3 valid weather-appropriate outfits returned in <5s at flat-lay stage; zero hallucinated garments across 50 runs.

---

### 5.C — Sustainability metrics

Low effort, high differentiation. Logging plus arithmetic — no models involved.

- Cost per wear (requires optional purchase price at ingestion)
- Wear count leaderboard; "not worn in 90 days" list
- Closet utilization rate (% worn in last season)
- **Outfits-available count** as the headline number — it rises when new combinations are found, not when items are bought
- Rediscovery prompts: deliberately surface an orphan item in a suggestion

#### C.1 Wear logging is the fragile link
Everything downstream depends on it and users log unreliably. In order of preference:
1. One-tap `Wear today` directly from a suggestion (zero added friction)
2. Single daily notification at a user-chosen time, last suggestions pre-loaded
3. Fall back to `selected + tried on` as a proxy signal

See invariant #8.

---

### 5.D — Style learning + gap analysis

#### D.1 Style profile (no model training — invariant #3)
A maintained document, regenerated weekly by an LLM reading the interaction log:

```json
{
  "version": 7,
  "updated": "2026-07-24",
  "summary": "Gravitates to high-contrast neutrals with one saturated accent. Prefers structured silhouettes over flowy. Denim appears in 62% of chosen casual outfits. Consistently rejects busy patterns.",
  "confirmed_preferences": ["no floral", "always flats for work"],
  "confidence": "medium (48 logged outfits)",
  "user_editable": true
}
```

#### D.2 Cold start
- **The existing closet is already a preference dataset.** 70% neutral tops is a strong prior before any interaction.
- Onboarding quiz: 8–10 generated outfit images across archetypes, user picks favourites.
- Explicit user rules ("never suggest heels", "I don't wear yellow").

#### D.3 Signal weights
| Signal | Weight | Note |
|---|---|---|
| Marked worn | Strongest | Requires user action — see §5.C.1 |
| Favourited | Strong | |
| Tried on | Medium | Interest, not approval |
| Rejected | **Weak** | Ambiguous cause. Occasionally ask one-tap "why not?" |
| Time on screen | Discard | Noise |

#### D.4 Gap analysis — combinatorics, not AI
1. Enumerate all valid outfit combinations (rules from §5.B.2)
2. For each garment, count outfit participation
3. **Orphans** = participation ≤2 → dead assets
4. For each orphan, compute which hypothetical item (category + colour band + formality) unlocks the most new combinations
5. Report with the math: *"Your 4 dressy tops pair with only one bottom. A mid-grey tailored trouser would create 11 new outfits."*

Specific, verifiable, immune to hallucination.

#### D.5 Sustainability tension — resolve explicitly
- **Default to unlock, not acquire.** Lead with unworn combinations from owned items.
- **Gate purchase suggestions behind a threshold** (e.g. ≥8 new outfits unlocked). Otherwise stay silent.
- **Always show the math.** Never "this completes your wardrobe."
- Invariant #7: no affiliate links.

#### D.6 Filter bubble guard
Optimising purely on past picks calcifies style and makes the app boring. **One of the three suggestions must be a deliberate wildcard**, flagged as such. Track wildcard acceptance rate separately.

---

### 5.E — Constellation analytics dashboard

**Goal:** "second brain / galaxy" view — force-directed graph, dark field, glowing nodes, emergent clusters.

#### E.1 Why this shape fits
The closet is natively a graph. Nodes = garments, edges = pairings, clusters = emergent style groups. Critically, **isolated peripheral nodes are the §5.D.4 orphan analysis made visible** — three lonely dressy tops drifting at the edge communicate "dead assets" better than a participation count.

#### E.2 Encodings — each must drive a decision
| Property | Encodes | Decision supported |
|---|---|---|
| Node size | Wear count | What am I actually using? |
| Node colour | **Actual garment colour** (LAB → hex) | Reveals real palette; exposes repeat-buying |
| Node brightness | Recency of wear (decays) | Neglected items at a glance |
| Edge solid/bright | Actually worn together | Real combinations |
| Edge dim/dashed | Could pair (constraint engine) | Unexplored potential |
| Edge thickness | Co-wear count | Habits and ruts |
| Cluster | Emergent style group | LLM-labelled: "work uniform", "weekend casual" |
| Isolated node | Orphan | Link to rediscover or resell |
| **Ghost node** (hollow, dotted) | Hypothetical gap item | Shows the constellation that *would* form |

Ghost nodes are the strongest element: render a proposed missing item with dotted edges to every orphan it would connect, so a dark region visibly lights up.

#### E.3 Technical constraints
- **2D, not 3D.** 3D screenshots well and uses badly — occlusion, ambiguous depth, awkward navigation. Achieve the nebula feel in 2D via glow, additive edge blending, depth-of-field blur on de-emphasised nodes.
- **Canvas, not SVG.** SVG degrades past ~500 nodes.
- **Performance is not a concern.** Personal closets are 50–300 nodes. No WebGL, no clustering-for-performance.
- Palette derives from the garments, not from neon. Restraint.
- Interaction: click node → detail + containing outfits; hover → highlight neighbourhood, dim rest; filter chips (season/formality/category); 12-month time scrubber.

#### E.4 Time scrubber
Replaying 12 months of wear history makes this more than decoration: clusters ignite and fade, seasonal groups appear and vanish, and a March purchase that never lit up becomes obvious. Built on `wear_log`.

#### E.5 Anti-pattern guard
Obsidian's graph view is the cautionary case — admired, rarely acted on.
- **Ship plain panels alongside the graph.** Graph = explorer, charts = answers.
- **Every node click leads to an action.**
- **Cut any encoding that doesn't drive a decision.**

Supporting panels: colour palette wheel (LAB values plotted — reveals seven near-identical navy tops), utilization sunburst by category, cost-per-wear ranked list, wear-frequency calendar heatmap.

#### E.6 Cold start
An empty graph reads as broken. **Draw could-pair edges from day one** — they come from the constraint engine and need no wear history. Actual-wear edges brighten over them as data accrues. Below ~20 garments, gate behind a "your galaxy is still forming" state.

#### E.7 Data
No new tables. Nodes ← `garment`. Actual edges ← `outfit` + `wear_log` co-occurrence. Potential edges ← constraint engine. Clusters ← community detection, LLM-labelled. Ghost nodes ← gap analysis.

**Acceptance:** renders real closet; orphans visually obvious without explanation; every node click leads to an action.

---

### 5.F — 360 spin (lowest priority)

Do not let this block other tracks.

- **Not video.** Video models warp past ~30° of orbit and offer no random access to specific angles.
- **Discrete views + drag-to-scrub.** Generate 8–12 fixed angles, interpolate (RIFE/FILM) to 32–48 frames.
- **Generate as a single contact sheet**, not N separate calls — a grid-layout prompt produces one self-consistent artifact. Slice programmatically.
- **Register every frame** — normalise scale and centre on a consistent pivot (pelvis, not bbox centre) or it jitters. Generate on plain background, matte, composite the room behind.
- **Photograph garments from the back.** Rear views are hallucinated without a back reference. Data fix, not a prompt fix.
- **Build the viewer against a placeholder turntable first**, then swap in real frames. Debugging asset quality and interaction quality simultaneously is what sank prior attempts.
- **Upgrade path:** turnaround sheet → image-to-3D → GLB in Three.js at 60fps. Hitem3D strongest on multi-view input; TRELLIS strong on mesh accuracy from a T-pose reference; Rodin on photorealism. Expect waxy faces — use 3D for full-body rotation, 2D renders for close-ups.
- **Scaling wall:** cost is `outfits × angles`. 200 combos × 24 angles = 4,800 images. Generate spins only for favourited outfits.

---

## 6. Data model

```
garment
  id, category, subcategory,
  colors[{lab, name, coverage}], pattern,
  formality(1-5), warmth(1-5), season_tags[], fabric, fit,
  asset_tier: 'catalog' | 'render_ready',
  images: {raw[], clean, back?}, embedding[],
  purchase: {price?, date?, source?},
  wear_count, last_worn, created_at

outfit
  id, garment_ids[], source: 'stylist'|'manual'|'wildcard',
  context: {occasion, time, venue, weather_snapshot},
  render_cache_key, rationale, created_at

wear_log
  id, outfit_id, date, confirmed_by: 'user'|'inferred'

interaction_log
  id, type: 'suggested'|'favourited'|'tried_on'|'rejected'|'worn',
  outfit_id, reason_code?, timestamp

style_profile
  version, summary, structured_prefs{}, user_edits[], confidence, updated_at
```

**Conventions:** colours stored as LAB; formality and warmth as integers 1–5; all timestamps UTC ISO-8601; cache keys as `avatar_version + sorted(garment_ids)`.

---

## 7. Risk register

| Risk | Severity | Mitigation |
|---|---|---|
| Wear-logging compliance collapses | **High** | Design for 30%; use proxy signals |
| Gap analysis drifts into a shopping app | **High (mission)** | Threshold gating, unlock-first framing, no affiliate links |
| Ingestion yields junk assets from rail photos | Medium | Two-tier model + explicit UI expectations |
| Colour extraction wrong under indoor light | Medium | White-balance normalisation; store LAB; user correction |
| Stylist hallucinates garments | Medium | Hard validation against candidate pool; reject + retry |
| Try-on render cost spirals | Medium | Flat-lay first, on-demand rendering, aggressive caching |
| Style profile calcifies into a filter bubble | Medium | Mandatory wildcard slot |
| Dashboard admired but never acted on | Medium | Plain panels alongside; every node click leads to an action |
| Empty graph on cold start reads as broken | Low | Could-pair edges from day one; gate below ~20 garments |
| Closet too small for meaningful combinatorics | Low | Degrade gracefully; gap analysis needs ~20+ items |

---

## 8. Setup checklist

- [ ] Hosting account + deployment access
- [ ] Postgres + object storage provisioned
- [ ] `FAL_KEY` (generation, SAM 3, image-to-3D)
- [ ] `ANTHROPIC_API_KEY` (attribute extraction, stylist, style profile)
- [ ] Open-Meteo integration (no key required)
- [ ] `BUDGET_CAP_USD` set and enforced in the generation logger
- [ ] Privacy decision documented — closet photos and wear history are highly personal. Local-first where possible; exportable; deletable.

---

## 9. Definition of done for this iteration

- [ ] 10 mixed photos → ≥80% garments correctly detected and tagged after one confirmation pass
- [ ] Quiz returns 3 valid, weather-appropriate outfits from real inventory in <5s (flat-lay stage)
- [ ] Zero hallucinated garments across 50 stylist runs
- [ ] Wear logging functional; utilization dashboard shows real numbers
- [ ] Gap analysis produces at least one specific, math-backed recommendation
- [ ] Style profile visible and editable by the user
- [ ] Constellation view renders real closet; orphans visually obvious; every node click leads to an action
