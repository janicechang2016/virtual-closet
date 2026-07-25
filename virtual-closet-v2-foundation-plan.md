# Virtual Closet v2 — Foundation Execution Plan (Phases 0–2)

> Scope-reconciled slice of `virtual-closet-plan-v2.md`. Decisions locked 2026-07-25.
> This iteration builds the **foundation only** — data model + backfill + constraint
> engine — then STOPS so the first user-facing feature (stylist / insights / galaxy)
> is chosen with real data in hand. Full track spec (A–F) lives in the v2 plan; do
> not build past Phase 2 without a fresh go.

## Locked decisions (2026-07-25)

| Decision | Choice | Consequence |
|---|---|---|
| Persistence / hosting | **Hosted Postgres** (v2 §3 as written) | Reverses the 07-20 "no live endpoint in front of fal" call — *deliberately*. Auth + server-side budget gate become load-bearing (Phase 0). |
| Iteration scope | **Foundation only** (Phases 0–2) | ~$0 on API calls if subjective attributes are hand-filled. Stop and reassess before any UI track. |
| Product identity | **Additive layer** | `carousel.html` ("the archive.") stays the front door; `/stylist` `/insights` `/galaxy` added later under the same SYVE language. Nothing about the current gallery changes now. |

## Why this ordering (differs from v2's "Track A first")

Track A is bulk ingestion of *new* photos. The closet already has **58 tagged garments
+ 18 published looks**. The real critical path is therefore a **schema migration +
attribute backfill of the existing closet** — because B/C/D/E all consume that data and
none of it exists yet (`meta.json` today holds size + brand only). The 18 curated looks
are a ready-made outfit seed and preference prior, which also blunts the wear-logging
cold-start risk. So: backfill + constraint engine first; ingestion (A) and spin (F) stay
deferred.

---

## Phase 0 — Infra + the reversal guardrails

The hosting reversal lands here. Nothing that can call fal ships until the guardrails do.

- **Pick host** (needs: Postgres, object storage, secrets, async job queue, public URL).
  Recommend **Supabase + Vercel** (Postgres + storage + auth in one, generous free tier)
  or **Railway** (queue + Postgres + storage, simplest single-service). Janice's account /
  billing — her call.
- **Provision:** Postgres DB, object-storage bucket, secrets:
  `DATABASE_URL`, `FAL_KEY`, `ANTHROPIC_API_KEY`, `STORAGE_BUCKET_URL`, `BUDGET_CAP_USD`.
- **Guardrails (load-bearing because of the reversal):**
  - **Auth in front of the public URL.** Single-user → simplest sufficient: shared-secret /
    basic auth, or platform deployment protection. No open endpoints.
  - **Server-enforced budget gate.** Port `scripts/genlog.py` into the backend as a
    hard-stop that every generation path (fal try-on, SAM 3, Anthropic) must pass through.
    Client-side gating is not enough once the endpoint is public.
  - **Rate-limit** the generation endpoints.
- **Privacy note (v2 checklist):** closet photos + wear history are personal — exportable,
  deletable; document the stance.

Phase 0 has a small monthly infra cost (free tiers likely cover it) but **$0 in API calls.**

## Phase 1 — Schema + backfill (mostly $0)

- **Stand up the v2 data model** (v2 §6): `garment`, `outfit`, `wear_log`,
  `interaction_log`, `style_profile`. Colours as LAB; formality/warmth as int 1–5;
  timestamps UTC ISO-8601; cache key `avatar_version + sorted(garment_ids)`.
- **Migrate 58 garments** from the file store → `garment` rows, carrying existing size +
  brand. Set `asset_tier`: currently render-ready garments → `render_ready`, the rest →
  `catalog`.
- **$0 programmatic backfill:** dominant + secondary colour via k-means in **LAB**
  (white-balance normalise first — invariant #6, risk: indoor light reads navy as black);
  garment embedding (for future dedup).
- **Seed the 18 published looks as `outfit` rows** (`source: 'manual'`) — instant
  preference prior + gives the gap/constellation engines real edges from day one.
- **Subjective attributes** (formality, warmth, fabric, fit, season): keep this $0 via a
  **confirmation grid** — pre-fill programmatic guesses, Janice taps to correct
  (~5s/item, v2 §A.5). She decides aesthetics anyway; this honours that standing rule.
  *Optional:* Anthropic auto-extraction as a small **approved** batch if she'd rather not
  hand-fill 58 (gated per the conserve-credits rule).

## Phase 2 — Constraint engine ($0, pure code)

The keystone: unlocks B, C, D, and E at once. All pure functions, unit-tested against the
real 58-garment / 18-look data.

- `/engine/constraints` — completeness rules `valid = (top+bottom | dress) + shoes
  [+ outerwear if required]`; warmth + formality banding.
- `/engine/colour` — LAB conversion, neutral detection, analogous / complementary /
  monochrome harmony scoring (deterministic).
- `/engine/gaps` — outfit-combination enumeration, per-garment participation count,
  orphan detection (participation ≤ 2).

**Foundation acceptance:**
- Enumerate all valid outfits from the real closet; count is sane.
- Orphans identified and match intuition on inspection.
- Harmony scores rank hand-picked good/bad pairings correctly.

→ **STOP.** With data + engine proven, pick the first UI (stylist B / sustainability C /
constellation E) — that's the next iteration's decision.

---

## Parked design study — glassmorphism (re-homed 07-25)
The 07-23 "carousel detail glassmorphism" idea is **re-homed off the archive**. Glass
fights SYVE's white-void austerity and has no backdrop to work over there. It belongs on
**`/galaxy`** (Track E — dark field + glow makes frosted glass native) as the primary case,
with **stylist cards** (Track B) as a restrained secondary; the archive stays glass-free by
design. Resolve when `/galaxy` is designed (Phase 5) — do not build now. See
`virtual-closet/docs/decisions.md` (2026-07-25).

## Not in this iteration
- Track A bulk ingestion (SAM 3) — only matters when adding many new items; closet is
  already tagged.
- Track F 360 spin — just rolled back from it; stays on `archive/360-avatar-v4-20260724`.
- Any paid render batch — foundation is $0; on-demand try-on arrives with the stylist.
