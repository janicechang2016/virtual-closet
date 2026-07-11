# Virtual Closet — Autonomous Execution Plan

**Project:** Photorealistic virtual try-on closet with a persistent personal avatar, built to feel like a video game fitting room.
**Execution model:** Claude executes phases autonomously inside its sandbox; the user unblocks permissions, uploads assets, and approves quality gates. Every phase has explicit entry criteria, exit criteria, and a fallback if blocked.
**Last updated:** 2026-07-11

---

## 0. Ground truth about the execution environment (verified, not assumed)

These were empirically tested on 2026-07-11 from Claude's sandbox:

| Capability | Status | Evidence |
|---|---|---|
| `api.anthropic.com` (Claude API, incl. vision) | ✅ Reachable | HTTP response received |
| `fal.ai` (image gen aggregator) | ❌ **Blocked** | 403 from egress proxy |
| `generativelanguage.googleapis.com` (Gemini / Nano Banana) | ❌ **Blocked** | 403 from egress proxy |
| `replicate.com` | ❌ Assumed blocked (same allowlist) | Not on allowlist |
| GitHub, npm, PyPI | ✅ Reachable | On allowlist |
| Python/Node in sandbox | ✅ Available | Standard container |
| Filesystem persistence between sessions | ❌ **Resets** | Container is ephemeral |
| Artifacts calling `api.anthropic.com` (no key needed) | ✅ Available | "Claude-in-Claude" supported in artifacts |
| Artifact persistent key-value storage (`window.storage`) | ✅ Available | Survives sessions; per-user |
| Artifacts calling arbitrary external APIs (fal, Gemini) | ⚠️ Unverified | Must be tested in Phase 0 (CSP may block) |

**Implication:** Claude can autonomously build the entire app, the prompt system, the QA harness, and the data layer *today*. Claude **cannot generate a single image** until at least one image-generation route is unblocked (Section 2).

---

## 1. Architecture (decided)

Three independent asset pipelines + one app:

```
┌─────────────────┐   ┌──────────────────┐   ┌─────────────────────┐
│ AVATAR PIPELINE │   │ GARMENT PIPELINE │   │  TRY-ON PIPELINE     │
│ (slow, careful, │   │ (once per item)  │   │  (fast, cheap,       │
│  run ~once)     │   │                  │   │   run constantly)    │
│                 │   │ garment photo →  │   │                      │
│ face photos +   │   │ cleanup → bg     │   │ avatar sheet +       │
│ measurements →  │   │ removal → meta   │   │ garment asset →      │
│ candidate gen → │   │ tagging          │   │ composed render →    │
│ structured      │   │                  │   │ auto-QA → user       │
│ feedback loop → │   │                  │   │ feedback → edit loop │
│ LOCKED CHARACTER│   │                  │   │                      │
│ SHEET (4 views) │   │                  │   │                      │
└────────┬────────┘   └────────┬─────────┘   └──────────┬──────────┘
         │                     │                        │
         └─────────────────────┴────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │  CLOSET APP (React) │
                    │  game-like UI,      │
                    │  outfit saves,      │
                    │  feedback buttons,  │
                    │  window.storage     │
                    └─────────────────────┘
```

**Key principles:**
1. **The avatar is a locked, versioned asset.** Never regenerate it casually. All try-ons reference the same character sheet → identity consistency.
2. **Edit, don't regenerate.** Feedback is applied as image *edits* on the previous best output, preserving what already works.
3. **Every generation is logged** (model, prompt, refs, seed if available, cost) so wins are reproducible.
4. **Auto-QA before human review.** Claude vision inspects each render for artifacts before the user ever sees it.

---

## 2. Permission & access derisking (USER ACTION CHECKLIST)

This is everything Claude needs to run independently. Do these once; Claude verifies each in Phase 0.

### 2.1 Network allowlist (required for image generation)
In Claude's settings, add these domains to the sandbox network allowlist:

- [ ] `fal.run` and `fal.ai` and `queue.fal.run` (primary route — fal.ai REST API)
- [ ] `generativelanguage.googleapis.com` (direct Gemini/Nano Banana route)
- [ ] `v3.fal.media` / `fal.media` (fal-hosted output images)
- [ ] *(optional)* `api.replicate.com` (backup aggregator)
- [ ] *(optional)* `api.fashn.ai` (fashion-specific try-on API for benchmarking)

> If the settings UI doesn't allow adding domains, Fallback B in §2.5 applies.

### 2.2 API keys (required)
Provide via a pasted message or an uploaded `.env` file at the start of a working session (the sandbox resets, so Claude will ask for it each session unless stored in the app — see §2.4):

- [ ] `FAL_KEY` — create at fal.ai dashboard. **Recommended primary** (one key → Nano Banana 2/Pro, FLUX.2, Seedream, IDM-VTON, upscalers).
- [ ] *(optional)* `GEMINI_API_KEY` — Google AI Studio, for direct Nano Banana access.
- [ ] *(optional)* `FASHN_API_KEY` — for the dedicated try-on benchmark arm.
- [ ] Confirm a **budget cap**: suggested **$25 for Phases 1–3** (≈ 150–250 generations mixing $0.039 Nano Banana 2 and $0.134 NB Pro images). Claude tracks estimated spend in the generation log and stops at the cap.

### 2.3 Personal assets (required, privacy-sensitive)
- [ ] **Face photos:** 3–6 photos, ≥1024px on the short side, even lighting, no heavy filters: front-facing, 3/4 left, 3/4 right; face filling ~30–50% of frame. Optional: one full-body photo in fitted clothing (best single input for proportions).
- [ ] **Body measurements** (fill into `avatar/measurements.json`, template created in Phase 1): height, weight (optional), bust/chest, waist, hip, shoulder width, inseam, usual sizes (tops/bottoms/dress), body-shape self-description.
- [ ] **Garment photos:** start with **5 benchmark items** of increasing difficulty: (1) plain solid tee, (2) jeans or solid trousers, (3) patterned dress, (4) structured blazer, (5) hardest item you own (sheer/lace/heavy print/layered). Flat-lay or on-hanger, plain background, minimal wrinkles, whole garment in frame.
- [ ] **Privacy acknowledgment:** face photos will be sent to third-party image APIs (fal/Google). fal offers privacy modes; Gemini API data handling per Google's API terms. Confirm you're OK with this before Phase 2.

### 2.4 Persistence strategy (required — sandbox resets between sessions)
Pick one:
- [ ] **Option A (recommended): private GitHub repo.** Provide a repo (e.g. `virtual-closet`) + a fine-grained PAT with `contents:rw` scoped to that repo. Claude pushes all code, prompts, generation logs, and approved assets each session and pulls at session start. GitHub is already network-allowed — this works today.
- [ ] **Option B: artifact `window.storage`.** The closet app stores garment metadata, avatar refs (as URLs or base64), outfit saves, and feedback logs in artifact persistent storage. Good for the app itself; clunky for code iteration.
- [ ] **Option C: manual.** Claude presents a zip at the end of each session; you re-upload it next session. Zero setup, most friction.

### 2.5 Fallback ladder if a permission can't be granted
- **Fallback A — keys but no allowlist change:** if artifacts *can* reach fal.ai from the browser (tested in Phase 0.4), the app itself makes generation calls client-side with your key; Claude builds/QAs around it. Key lives in `window.storage` (personal use; acceptable risk for a single-user app).
- **Fallback B — no network route at all:** Claude builds everything (app, prompt packs, QA harness, benchmark protocol) and produces a **copy-paste operator manual**: you run each prompt in Google AI Studio / fal playground manually, upload results, Claude QAs and iterates. Slower but fully functional.
- **Fallback C — hand off heavy build:** move the codebase to Claude Code on your machine where network is unrestricted; this chat remains the design/QA brain.

---

## 3. Phase plan

### Phase 0 — Environment verification (Claude autonomous, ~15 min, $0)
**Entry:** user has attempted checklist §2.
**Steps:**
1. `curl` probe every domain in §2.1; record HTTP status in `docs/phase0-report.md`.
2. If `FAL_KEY` provided: 1 cheapest-possible test generation ($0.04) to verify auth + output download.
3. Verify Anthropic API from sandbox and from a test artifact (for QA judge).
4. **Test artifact→fal.ai CORS/CSP** with a minimal artifact that attempts a fetch; record result (decides Fallback A viability).
5. If GitHub repo provided: init repo structure, push, pull-verify.
**Exit criteria:** written report stating which of routes {sandbox-direct, artifact-client-side, manual-operator} is live. **No image work proceeds without at least one live route.**

### Phase 1 — Scaffold + data layer (Claude autonomous, $0)
1. Repo structure:
```
virtual-closet/
├── avatar/            # measurements.json, reference photos, character sheet, versions/
├── garments/          # one folder per item: raw/, clean/, meta.json
├── renders/           # tryon outputs: {garment}_{avatar_ver}_{n}.png + sidecar log
├── prompts/           # versioned prompt templates (avatar, tryon, edit, qa)
├── logs/generations.jsonl   # every API call: model, prompt, refs, cost, outcome, feedback
├── app/               # React closet app
└── docs/              # this plan, phase reports, operator manual
```
2. `measurements.json` template + garment `meta.json` schema (category, color, fabric, fit, layer-order, difficulty score 1–5).
3. Generation logger + cost meter (hard-stops at budget cap from §2.2).
4. Prompt pack v1 (see §4).
**Exit:** structure pushed/persisted; user has filled `measurements.json` and uploaded the 5 benchmark garments + face photos.

### Phase 2 — Avatar calibration (Claude + user gates, est. $5–10)
1. **Candidate round (NB Pro, 4 candidates):** full-body, neutral gray base outfit, studio lighting, using face refs + measurement-derived body description.
2. **Auto-QA pass:** Claude vision scores each candidate on face likeness vs refs (1–10), proportion plausibility vs measurements, artifact scan (hands, hairline, feet, skin texture).
3. **User gate 1:** structured feedback form (not freeform): face likeness / body proportions / skin tone / hair — each "approve" or a specific correction.
4. **Edit loop:** corrections applied as *edits* to the best candidate, max 4 rounds (identity degrades past ~5 sequential edits — if not converged, restart candidates with learned prompt fixes).
5. **Character sheet generation:** from the approved avatar, generate front / 3/4-left / 3/4-right / back views + one seated pose, same base outfit and lighting. Auto-QA for cross-view identity match.
6. **User gate 2 (LOCK):** approve → tag `avatar-v1`, freeze. All Phase 3+ work references `avatar-v1` only.
**Exit:** locked, versioned 5-view character sheet the user says "feels like me."
**Known risks:** eye color drift (mitigation: name exact shade in every prompt), hand degradation (mitigation: describe hands explicitly, crop-and-fix edits), "prettified" averaging of features (mitigation: explicit "preserve asymmetries and distinctive features exactly as in reference" instruction).

### Phase 3 — Try-on benchmark (Claude autonomous + 1 user gate, est. $8–12)
Run the 5 benchmark garments through **3 arms**:
- Arm 1: Nano Banana 2 (avatar sheet + garment photo, single-shot compose)
- Arm 2: FLUX.2 Pro (same inputs)
- Arm 3: fal-hosted try-on specialist (IDM-VTON or FASHN if key provided) applied to `avatar-v1` front view
2 renders per garment per arm = 30 renders. Auto-QA scores each on: garment fidelity (pattern/logo/neckline vs source photo), identity hold, artifact count, drape realism. Claude compiles a scored comparison report with a recommended default pipeline (possibly hybrid: specialist for garment, NB for scene/pose).
**User gate:** pick the winner (or accept Claude's recommendation).
**Exit:** `docs/phase3-benchmark.md` + a locked default try-on pipeline config.

### Phase 4 — Closet app (Claude autonomous, $0 API cost)
React artifact (frontend-design skill applied), game-fitting-room aesthetic:
- Garment grid (closet view) with difficulty/category filters; click-to-try-on
- Render viewer with the avatar; outfit slots (top/bottom/layer/shoes) and saved outfits
- **Feedback buttons per render:** `wrong fit` / `fabric off` / `face drifted` / `artifact` / `pattern wrong` — each maps to a canned corrective edit-prompt from the prompt pack, one tap = one targeted regeneration
- Generation history + cost meter surfaced in-app
- Persistence via `window.storage` (Option B) and/or export to repo
- Generation calls: direct from app (Fallback A) or "copy prompt" mode (Fallback B) or via sandbox batch (primary route)
**Exit:** user dresses the avatar in all 5 benchmark garments end-to-end inside the app.

### Phase 5 — Full closet ingestion (repeating, user-paced)
Batch pipeline: user uploads garment photos in bulk → Claude auto-cleans (bg removal via fal), auto-tags metadata with Claude vision, queues try-on renders overnight-style within budget, flags low-QA renders for feedback. Layered outfits composed sequentially (base garment render → edit to add layer).

### Phase 6 — Future: shop-the-web try-on (design only for now)
- Input problem: product pages usually show garments **on other models** — requires garment extraction (specialist try-on models handle model-to-model transfer better than general models; flat product images preferred when available).
- Add "paste product URL" → fetch image → extract garment → render on `avatar-v1`.
- **Explicit disclaimer baked into UI:** renders are *style visualization, not fit truth* — the model drapes everything flatteringly regardless of real sizing. Pair with a simple measurement-vs-size-chart checker for actual fit guidance.

---

## 4. Prompt pack v1 (starting templates — will be tuned in Phases 2–3)

**Avatar generation (NB Pro, with face refs attached):**
> Full-body studio photograph of the person in the reference images. Preserve facial features, asymmetries, and skin texture exactly as in Image 1–3 — do not beautify or average the face. Body: [height], [build description derived from measurements.json], natural posture, arms relaxed at sides, five visible fingers on each hand. Wearing a plain heather-gray fitted tank top and black leggings, barefoot. Plain light-gray seamless studio background, soft even lighting, 50mm lens, photorealistic, natural skin texture, no retouching look. Eyes: [exact shade].

**Try-on compose (NB2, avatar sheet + garment photo attached):**
> Dress the person from Images 1–4 (character reference — keep face, hair, body proportions identical) in the garment shown in Image 5. Reproduce the garment exactly: same color, pattern placement, neckline, sleeve length, buttons, and any text or logos. Natural fabric drape appropriate to [fabric type from meta.json]. Same studio background and lighting as the reference images. Full-body, front-facing.

**Corrective edit (applied to previous render):**
> Edit this image only as follows: [single specific correction, e.g. "the plaid pattern on the shirt should align at the front placket as in the garment reference"]. Keep the face, body, pose, lighting, and everything else exactly unchanged.

**Auto-QA judge (Claude vision, per render):**
> Compare render R against garment photo G and avatar sheet A. Score 1–10 with one-line justification each: (a) identity match to A, (b) garment fidelity to G — color, pattern, construction, (c) anatomical correctness — hands, feet, joints, hairline, (d) lighting/composite coherence. List every visible artifact with location. Verdict: PASS / REGENERATE / EDIT with suggested edit instruction.

---

## 5. Feedback & iteration protocol (the core product loop)

1. Every render enters state `pending-qa` → auto-QA → `pass` / `auto-retry` (max 2 stochastic retries for artifacts) / `needs-user`.
2. User feedback is **always structured** (button taxonomy in §Phase 4); freeform notes allowed as an addendum.
3. Each feedback event is appended to `logs/generations.jsonl` linked to the render; corrective prompts that *work* are promoted into the prompt pack (versioned `prompts/v{n}`).
4. Avatar itself is only ever revised via an explicit "re-open avatar" decision → produces `avatar-v2`; old renders keep their version tag.

## 6. Cost model (estimate, tracked live against cap)

| Item | Unit cost | Phase budget |
|---|---|---|
| NB Pro avatar candidates + edits + sheet | ~$0.134/img | ~$5–10 (Phase 2) |
| Benchmark renders (30 + retries) | $0.03–0.13/img | ~$8–12 (Phase 3) |
| Ongoing try-ons (NB2 default) | ~$0.04/img | ~$2 per 50 renders |
| Auto-QA (Claude vision) | ~fractions of a cent/check | negligible |

## 7. Definition of "done" for the independent-execution experiment
- [ ] Phase 0 report produced with zero unverified assumptions
- [ ] Avatar locked and user-approved as "feels like me"
- [ ] All 5 benchmark garments rendered on the avatar with QA PASS
- [ ] Closet app running with working feedback→edit loop and persistence
- [ ] Total spend ≤ cap; full generation log exported
- [ ] Honest writeup of where autonomy broke down and which permissions were the bottleneck
