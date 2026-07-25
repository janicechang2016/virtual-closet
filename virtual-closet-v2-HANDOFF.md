# Virtual Closet v2 — Handoff / Resume Point

**Date:** 2026-07-25 · **Branch:** `2d-reboot` · **Status:** Phase 0 scaffold built, nothing provisioned.

Read this to resume the v2 pivot cold. Source-of-truth docs: `CLAUDE.md` (2D app),
`virtual-closet-plan-v2.md` (full v2 spec, tracks A–F), `virtual-closet-v2-foundation-plan.md`
(scope-reconciled Phases 0–2), `virtual-closet/docs/decisions.md` (07-25 entries).

## What this is
The app is pivoting from an aesthetic lookbook ("the archive") to a **utility wardrobe
tool** (stylist, sustainability, gap analysis, constellation dashboard). This iteration
builds the **foundation only** (Phases 0–2), then stops to pick the first user-facing feature.

## Decisions locked (2026-07-25) — do not re-litigate
1. **Hosted Postgres** — deliberately reverses the 07-20 "no live endpoint" rule. → auth +
   server-side budget gate are load-bearing (both already built).
2. **Host = Railway + Vercel + Cloudflare R2.** Railway (Postgres + API + worker), Vercel
   (frontend; archive stays put), R2 (object storage — Railway has no native blob).
3. **Scope = foundation only** (Phases 0–2). ~$0 on API calls. Stop and reassess.
4. **Additive identity** — archive carousel stays home; `/stylist` `/insights` `/galaxy` added later.
5. **Glassmorphism re-homed** — off the archive, onto `/galaxy` (primary) + stylist cards
   (secondary); resolve at Phase 5. Archive stays glass-free.

## Safety nets (rollback points)
- `2d-final-pre-v2` — tag at `3b069e0`, pushed to origin. The complete pre-pivot 2D app.
  Restore: `git checkout 2d-final-pre-v2`.
- `archive/360-avatar-v4-20260724` — the 3D/360 exploration.
- `~/wardrobe-v3-360-local-assets-20260724/` — 2.1 GB of parked 360 assets.

## What's built (Phase 0 scaffold, `server/`)
FastAPI backend, compiles on Python 3.9. **The two reversal guardrails are real, not stubbed:**
- `app/auth.py` — shared-secret bearer token; every route except `/health` requires it.
- `app/budget.py` — Postgres-backed port of `genlog.py` (COST_TABLE + `check_budget()`);
  raises **before** any paid call. The worker is the only place paid calls happen.
- `app/queue.py` + `app/worker.py` — Postgres job queue (SKIP LOCKED) + async worker.
- `app/main.py` — `/health` (open), `/budget` (auth), `/jobs/*` (auth) demonstrating the
  enqueue→poll async pattern all future generation endpoints follow.
- `migrations/0001_init.sql` — full v2 §6 data model + infra tables. `garment.id` = existing
  slug (preserves render-matching). Colours as LAB. Job queue + generation_log + budget.
- `engine/` — Phase 2 placeholder (constraints / colour / gaps), do not build yet.
- `README.md` — exact provisioning commands.

## RESUME HERE — next actions in order
1. **Provision (user does — interactive logins).** From `server/README.md`:
   `railway login` → `railway init` → `railway add` (PostgreSQL) → set variables
   (`APP_SECRET`, `BUDGET_CAP_USD=45`, `FAL_KEY`, `ANTHROPIC_API_KEY`) → create R2 bucket
   `virtual-closet` in Cloudflare + set `R2_*` vars.
2. **Apply schema + first deploy.** `railway run psql "$DATABASE_URL" -f migrations/0001_init.sql`
   then `railway up`. Verify `/health` and authed `/budget`.
3. **Phase 1 — backfill (not written yet).** Migrate 58 garments from the file store →
   `garment` rows (carry size + brand); programmatic LAB colours ($0, white-balance first);
   seed the 18 published looks as `outfit` rows (source='manual') = cold-start prior;
   subjective attributes (formality/warmth/fabric/fit) via a $0 confirmation grid (she
   decides aesthetics) — Anthropic auto-extraction only as an approved batch.
4. **Phase 2 — constraint engine.** `engine/constraints.py` + `colour.py` + `gaps.py`, pure
   functions, unit-tested against the real closet. Acceptance: enumerate valid outfits,
   orphans obvious, harmony scores rank sane. → STOP, pick first UI (stylist / insights / galaxy).

## Standing rules that still apply
- Spending gated: fal/Anthropic only in approved batches; every paid call through the budget
  gate. Foundation is $0.
- She decides aesthetics — build, show, expect rejection sometimes.
- v2's "Track A first" is wrong for this closet (already tagged) — backfill + engine is the
  real critical path.
