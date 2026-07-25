-- Virtual Closet v2 — initial schema (Phase 1 foundation).
-- Idempotent-ish: safe to re-run in dev. Data model per virtual-closet-plan-v2.md §6.
-- Colours stored as LAB (invariant #6). Timestamps UTC. Runs on plain Postgres;
-- embeddings kept as float4[] for now — pgvector is the later upgrade.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";  -- gen_random_uuid()

-- ---------------------------------------------------------------------------
-- garment — id is the existing slug (e.g. '01-plain-tee') to preserve continuity
-- with the current garments/ folders and render-id matching.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS garment (
    id            text PRIMARY KEY,
    category      text NOT NULL,
    subcategory   text,
    -- colors: jsonb array of {lab:[L,a,b], name, coverage}
    colors        jsonb NOT NULL DEFAULT '[]'::jsonb,
    pattern       text,
    formality     int  CHECK (formality BETWEEN 1 AND 5),
    warmth        int  CHECK (warmth BETWEEN 1 AND 5),
    season_tags   text[] NOT NULL DEFAULT '{}',
    fabric        text,
    fit           text,
    asset_tier    text NOT NULL DEFAULT 'catalog'
                    CHECK (asset_tier IN ('catalog','render_ready')),
    -- images: {raw:[...], clean, back?}
    images        jsonb NOT NULL DEFAULT '{}'::jsonb,
    embedding     real[],
    -- carried over from the current meta.json
    size_owned    text,
    brand         text,
    -- purchase: {price?, date?, source?}
    purchase      jsonb NOT NULL DEFAULT '{}'::jsonb,
    wear_count    int  NOT NULL DEFAULT 0,
    last_worn     date,
    created_at    timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- outfit — the 18 published looks seed this table as source='manual'.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS outfit (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    garment_ids      text[] NOT NULL,
    source           text NOT NULL DEFAULT 'manual'
                       CHECK (source IN ('stylist','manual','wildcard')),
    -- context: {occasion, time, venue, weather_snapshot}
    context          jsonb NOT NULL DEFAULT '{}'::jsonb,
    render_cache_key text,
    rationale        text,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS wear_log (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    outfit_id    uuid REFERENCES outfit(id) ON DELETE CASCADE,
    worn_on      date NOT NULL DEFAULT CURRENT_DATE,
    confirmed_by text NOT NULL DEFAULT 'user'
                   CHECK (confirmed_by IN ('user','inferred'))
);

CREATE TABLE IF NOT EXISTS interaction_log (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    type        text NOT NULL
                  CHECK (type IN ('suggested','favourited','tried_on','rejected','worn')),
    outfit_id   uuid REFERENCES outfit(id) ON DELETE SET NULL,
    reason_code text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS style_profile (
    version         int PRIMARY KEY,
    summary         text,
    structured_prefs jsonb NOT NULL DEFAULT '{}'::jsonb,
    user_edits      jsonb NOT NULL DEFAULT '[]'::jsonb,
    confidence      text,
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- Infra: generation log + budget (ported from genlog.py) and the job queue.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS generation_log (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    model      text NOT NULL,
    n_images   int  NOT NULL DEFAULT 1,
    cost_usd   numeric(10,4) NOT NULL DEFAULT 0,
    request_id text,
    meta       jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Singleton budget row (id is always TRUE).
CREATE TABLE IF NOT EXISTS budget (
    id         boolean PRIMARY KEY DEFAULT TRUE CHECK (id),
    cap_usd    numeric(10,2) NOT NULL,
    phase      text NOT NULL DEFAULT 'v2-foundation',
    updated_at timestamptz NOT NULL DEFAULT now()
);

-- Postgres-backed job queue (async generation jobs). Worker claims with SKIP LOCKED.
CREATE TABLE IF NOT EXISTS job_queue (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    type       text NOT NULL,
    payload    jsonb NOT NULL DEFAULT '{}'::jsonb,
    status     text NOT NULL DEFAULT 'queued'
                 CHECK (status IN ('queued','running','done','error')),
    result     jsonb,
    error      text,
    attempts   int NOT NULL DEFAULT 0,
    locked_at  timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS job_queue_status_idx ON job_queue (status, created_at);
