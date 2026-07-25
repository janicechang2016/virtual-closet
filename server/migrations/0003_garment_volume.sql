-- Phase 1 — silhouette volume, confirmed via the attribute grid.
-- Feeds the Phase 2 constraint engine's proportion rules (e.g. how oversized
-- pairs with oversized). Free-text `fit` stays as the human description; this is
-- the closed-vocabulary version the engine can reason over.
ALTER TABLE garment ADD COLUMN IF NOT EXISTS volume text;

DO $$
BEGIN
    ALTER TABLE garment ADD CONSTRAINT garment_volume_chk
        CHECK (volume IN ('fitted', 'relaxed', 'oversized'));
EXCEPTION
    WHEN duplicate_object THEN NULL;  -- already applied
END $$;
