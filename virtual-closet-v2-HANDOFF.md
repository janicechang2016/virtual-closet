# Virtual Closet v2 — Handoff / Resume Point

**Date:** 2026-07-25 · **Branch:** `2d-reboot` (pushed) · **Status:** Phase 0 PROVISIONED + deployed
and verified. Phase 1 not started.

**Live:** https://virtual-closet-api-production.up.railway.app — Railway project `virtual-closet`
(`d8cf0dfa-1353-4f98-8c9a-cc7aab7dbced`), Postgres 18 + `virtual-closet-api`, region sfo,
deployed from GitHub `2d-reboot` / root dir `server`. Verified 07-25: `/health` 200 open,
`/budget` 401 without token, JSON with it (a real Postgres round-trip — schema + budget gate
proven, not assumed). Bearer token is in `server/.app_secret` (gitignored, never committed).

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

## Provisioning — DONE 2026-07-25 (recorded so it isn't re-derived)
- Railway **Hobby $5/mo** was required: the trial had expired and `railway init` refused
  without a plan. This is a new recurring cost, separate from the fal budget.
- **`railway up` (CLI upload) returns 403 Forbidden — unexplained, still unresolved.** Auth
  was fine (project create, DB provision, variable writes all succeeded on the same
  credentials). Routed around by deploying from GitHub instead; if CLI upload is ever needed,
  this is the known blocker.
- Deploying from GitHub required pushing `2d-reboot` (the scaffold was local-only). **Do not
  merge to `main`** — `main` is what Vercel builds the live archive from.
- Connecting the repo in the dashboard spawned a **stray duplicate service** named
  `virtual-closet`; deleted 07-25. The real service is `virtual-closet-api`.
- `DATABASE_URL` is **not** auto-injected — Railway variables are per-service. Set as a
  reference: `DATABASE_URL=${{Postgres.DATABASE_URL}}` (works via CLI with single quotes).
- Migrations run from a laptop need **`DATABASE_PUBLIC_URL`**, not `DATABASE_URL` (the latter
  is a `railway.internal` host, unreachable off-platform). `psql` came from `brew install
  libpq`, keg-only → `/opt/homebrew/opt/libpq/bin/psql`.
- `scripts/set_railway_vars.sh` pushes secrets from `virtual-closet/.env` without echoing them.

**Deferred on purpose:** the three `R2_*` credentials (Cloudflare dashboard task; nothing in
Phases 1–2 touches object storage) and the **worker service** (Railway runs one start command
per service; no paid jobs exist yet — add a service with `python -m app.worker` when
generation is wired).

## RESUME HERE — next actions in order
1. ~~Provision~~ **DONE** — see above.
2. ~~Apply schema + first deploy~~ **DONE** — all 8 tables live, `/health` + authed `/budget` verified.
3. **Phase 1 — backfill: OBJECTIVE HALF DONE 2026-07-25, $0.** In Postgres now:
   **58 garment rows** (slug ids, size + brand carried, LAB colours, images, asset_tier)
   and **18 outfit rows** (`source='manual'`, `render_cache_key` = look id) = the
   cold-start prior. Acceptance checks all pass and are re-runnable:
   `scripts/verify_backfill.sql` → 0 orphan refs, 0 dupes, 0 garments without colours,
   idempotent on re-run. Notable signal: **23 garments appear in no published look** —
   real input for Phase 2 gap analysis.
   - `scripts/extract_colors.py` (venv python) — LAB per garment, white-balanced,
     median-cut, $0. Follows dragcut.py's routing rule: on-model photos use cloth-seg,
     NEVER the general model (that keeps the whole figure, so a garment's palette picks
     up the model's skin and other clothes). For the 7 garments dragcut could never cut,
     cloth-seg files the outfit under `full` and leaves upper/lower empty — fallback
     intersects `full` with a category-appropriate vertical band. `--rename` re-names
     from stored LAB without a second rembg pass.
   - `scripts/backfill.py` → `backfill.sql`. Values reach Postgres via dollar-quoted
     `jsonb_to_recordset`, so nothing is hand-escaped. Idempotent.
   - **STILL OPEN — needs her:** formality + warmth have no source in meta.json.
     `scripts/make_attr_grid.py` builds `attr_grid.html` (open via file://), a SYVE-styled
     $0 grid pre-filled with proposals derived from each garment's own name/fabric/fit
     text. She confirms/overrides → DOWNLOAD JSON → `scripts/apply_attrs.py <file>` →
     `attrs.sql`. season_tags is derived from confirmed warmth, not asked separately.
     Verified by applying with COMMIT→ROLLBACK: valid SQL, `UPDATE 58`, nothing persisted.
   - **Metadata review (her call 07-25, all three accepted).** Three inputs, all $0:
     (a) `make_occasion_form.py` → `occasion_form.html` — occasion/time/venue for the 18
     looks. Highest leverage: without it the prior teaches only "these go together"; with
     it, "these go together FOR X". `apply_occasions.py` MERGES into `outfit.context` (`||`)
     so backfill's title/pose/render survive. (b) `make_purchase_tsv.py` → `purchase.tsv`
     (fill in an editor; TSV because brands contain commas; never overwritten once it
     exists) → `--apply` → `purchase.sql`. Unlocks Track C cost-per-wear, which is
     arithmetically impossible to reconstruct later. (c) volume + subcategory: DERIVED from
     each garment's own name/fit text and folded into the same grid as confirm rows, so she
     spot-checks rather than authors. New column via `migrations/0003_garment_volume.sql`
     (applied); subcategory uses the existing column with a closed per-category vocabulary.
   - **Colour QA: 6 of 58 flagged for her eye** (was 15; 9 were my naming anchors, since
     recalibrated — a real garment black measures L*~15-22, not L*~7). Genuine finding:
     **36-realisation-liv-dress meta.color is wrong** — says "violet-blue with dark leopard
     print", the garment is black with dark red spots. meta.json left unedited: her data.
4. **Phase 2 — constraint engine.** `engine/constraints.py` + `colour.py` + `gaps.py`, pure
   functions, unit-tested against the real closet. Acceptance: enumerate valid outfits,
   orphans obvious, harmony scores rank sane. → STOP, pick first UI (stylist / insights / galaxy).

## Standing rules that still apply
- Spending gated: fal/Anthropic only in approved batches; every paid call through the budget
  gate. Foundation is $0.
- She decides aesthetics — build, show, expect rejection sometimes.
- v2's "Track A first" is wrong for this closet (already tagged) — backfill + engine is the
  real critical path.
