-- Wear logging (Phase 3).
--
-- wear_log references outfit_id and nothing else, so an ad-hoc combination has
-- to become an outfit row before it can be logged. That is not a workaround: it
-- is why wear logging compounds — every wear grows the outfit corpus the
-- stylist learns from, where a garment-level wear table would have grown
-- nothing but a counter.
--
-- 'worn' distinguishes an outfit that exists because it HAPPENED from one that
-- was published ('manual') or proposed ('stylist' / 'wildcard'). The stylist
-- filters on source, so keeping them distinguishable is load-bearing: it lets
-- us decide later whether lived outfits should carry the same weight as
-- published ones, and measure it, rather than silently blending them.

ALTER TABLE outfit DROP CONSTRAINT IF EXISTS outfit_source_check;
ALTER TABLE outfit ADD CONSTRAINT outfit_source_check
    CHECK (source IN ('stylist', 'manual', 'wildcard', 'worn'));

-- The two access patterns: "what did I wear recently" and "how often was this
-- outfit worn". Both are tiny today and will not stay tiny.
CREATE INDEX IF NOT EXISTS wear_log_worn_on_idx ON wear_log (worn_on DESC);
CREATE INDEX IF NOT EXISTS wear_log_outfit_idx ON wear_log (outfit_id);
