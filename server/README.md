# Virtual Closet v2 — Backend (Phase 0)

Hosted backend for the v2 pivot. FastAPI + Postgres on **Railway**; frontend stays on
**Vercel**; closet images in **Cloudflare R2**. See
`../virtual-closet-v2-foundation-plan.md` for scope (foundation only, Phases 0–2).

## Why this exists / the reversal
The 07-20 "no live endpoint in front of the fal budget" rule is deliberately reversed for
v2. Because the budget now sits behind a public URL, **two guardrails are load-bearing and
already live in this scaffold:**
- **Auth** — every non-health route requires the shared secret (`app/auth.py`). No open
  endpoints.
- **Server-side budget hard-stop** — `app/budget.py` is the Postgres-backed port of
  `virtual-closet/scripts/genlog.py`; `check_budget()` raises *before* any paid call. The
  worker calls it on every generation. Client-side gating is not trusted.

## Layout
```
server/
  app/
    config.py     env loading (fail-fast on missing secrets)
    db.py         asyncpg pool
    auth.py       shared-secret dependency (the reversal guardrail)
    budget.py     Postgres-backed budget gate — ported from genlog.py
    queue.py      Postgres job queue (SKIP LOCKED)
    main.py       FastAPI app: /health (open), /budget (auth), enqueue stub
    worker.py     async job worker; budget-gated before any paid call
  engine/         Phase 2 placeholder (constraints / colour / gaps)
  migrations/
    0001_init.sql v2 data model DDL + infra tables
  .env.example    copy to .env for local; set the same as Railway variables
  requirements.txt
  Procfile        web + worker process definitions for Railway
  railway.json
```

## Setup — commands to run yourself
Run these with the `! ` prefix in the Claude Code prompt so output lands here.

**1. Railway project + Postgres**
```
! cd ~/wardrobe-v3/server && railway login
! railway init                 # create/select the project
! railway add                  # choose PostgreSQL plugin
```

**2. Secrets** (Railway → Variables, or CLI). `APP_SECRET` = any long random string you
keep; it's the auth token the frontend will send.
```
! railway variables --set "APP_SECRET=$(openssl rand -hex 24)" \
    --set "BUDGET_CAP_USD=45" \
    --set "FAL_KEY=<your fal key>" \
    --set "ANTHROPIC_API_KEY=<your anthropic key>"
```
`DATABASE_URL` is injected by the Postgres plugin automatically.

**3. Cloudflare R2** (object storage — the one thing Railway doesn't give natively)
- Cloudflare dashboard → R2 → create bucket `virtual-closet`.
- Create an R2 API token (S3-compatible). Then:
```
! railway variables --set "R2_ACCOUNT_ID=..." --set "R2_ACCESS_KEY_ID=..." \
    --set "R2_SECRET_ACCESS_KEY=..." --set "R2_BUCKET=virtual-closet"
```

**4. Migrate + deploy**
```
! railway run psql "$DATABASE_URL" -f migrations/0001_init.sql   # apply schema
! railway up                                                     # deploy web + worker
```

**5. Frontend (Vercel)** — the archive stays where it is. When Phase 3 UI arrives, point
the Vercel app at the Railway URL and have it send `Authorization: Bearer $APP_SECRET`.

## Local dev
```
! cp .env.example .env    # fill it in
! pip install -r requirements.txt
! uvicorn app.main:app --reload           # API on :8000
! python -m app.worker                     # worker in a second terminal
```
Health check (no auth): `GET /health`. Everything else needs the bearer token.

## Not built yet (honest scope)
- Phase 1 backfill scripts (migrate 58 garments, LAB colours, seed 18 looks) — next.
- Phase 2 engine (`engine/`) — placeholder only.
- No paid calls wired. Foundation is $0 on API spend.
