-- Wear context: the situation a wear happened in, not just what and when.
--
-- THE PROBLEM THIS FIXES, measured 07-28: `wear_log` carried `outfit_id` and
-- `worn_on` and nothing else — the thinnest record in the system, and the one
-- that is now the stylist's TARGET. With only "what" and "when", the only
-- pattern available to learn is which garments are in rotation, which is
-- exactly what the held-out test found (0.660 overall, 0.555 once rotation is
-- controlled for, a CI spanning chance).
--
-- Meanwhile all 18 PUBLISHED looks carry `context.occasion` — the field sits
-- entirely on the half of the data that is no longer the target.
--
-- Three additions, each answering a different failure:
--
--   occasion    Her own rules are context claims: "weekday wears are
--               work-from-home" and "the dresses are event pieces — I've had no
--               events". Neither is representable today, so the model cannot
--               tell comfort-first from taste. Note the vocabulary SPLITS work
--               into from-home and out (her call 07-28): under the published
--               looks' five values a WFH day is ambiguous between 'work' and
--               'home / lounge', and that is the majority of her logging.
--
--   weather     The only context field that costs her nothing — derived from
--               `worn_on` via Open-Meteo, never typed. See weather_backfill.py.
--
--   the swap    One garment she nearly wore INSTEAD of one she did. This is the
--               first TRUE NEGATIVE in the dataset. Every negative until now was
--               synthesised from the whole 1600-outfit space, which is precisely
--               why controlling for rotation collapses the score — the model
--               could win by scoring dead stock low. A swap is a negative drawn
--               from the same day, same weather, same occasion, and it is
--               pairwise, which is where the blame data already points (29 of 44
--               rejections blame a shoe).
--
-- NOTE THE SWAP CREATES NO OUTFIT ROW. Unlike a wear, a near-miss is a pair, not
-- a combination she put on. Minting a 'considered' outfit for it would grow the
-- corpus with clothes she did NOT wear, and `_resolve_outfit`'s matching would
-- then happily return that row the day she actually wears it.

-- Slugs, not display text. The UI renders the labels; the database stores stable
-- keys, so the wording can change without a migration and nothing depends on an
-- em dash surviving a round trip.
ALTER TABLE wear_log DROP CONSTRAINT IF EXISTS wear_log_occasion_check;
ALTER TABLE wear_log ADD COLUMN IF NOT EXISTS occasion text;
ALTER TABLE wear_log ADD CONSTRAINT wear_log_occasion_check
    CHECK (occasion IS NULL OR occasion IN
           ('work_home', 'work_out', 'day_out', 'dinner', 'event', 'home'));

-- {temp_max_c, temp_min_c, precip_mm, code, source, fetched_at} — jsonb because
-- it is derived data from one provider and should not spread across columns
-- until something actually reads a field.
ALTER TABLE wear_log ADD COLUMN IF NOT EXISTS weather jsonb NOT NULL DEFAULT '{}'::jsonb;

-- The swap. Both halves or neither — a "nearly wore" with nothing displaced is
-- not a comparison, and the whole value here is that the two are matched.
ALTER TABLE wear_log ADD COLUMN IF NOT EXISTS nearly_wore text REFERENCES garment(id);
ALTER TABLE wear_log ADD COLUMN IF NOT EXISTS instead_of  text REFERENCES garment(id);
ALTER TABLE wear_log DROP CONSTRAINT IF EXISTS wear_log_swap_check;
ALTER TABLE wear_log ADD CONSTRAINT wear_log_swap_check
    CHECK ((nearly_wore IS NULL) = (instead_of IS NULL));
-- A garment cannot be its own alternative.
ALTER TABLE wear_log DROP CONSTRAINT IF EXISTS wear_log_swap_distinct_check;
ALTER TABLE wear_log ADD CONSTRAINT wear_log_swap_distinct_check
    CHECK (nearly_wore IS DISTINCT FROM instead_of);

-- "Which occasions do I actually dress for" is the query this exists to answer.
CREATE INDEX IF NOT EXISTS wear_log_occasion_idx ON wear_log (occasion)
    WHERE occasion IS NOT NULL;
-- The swap is sparse and pairwise; the lookup is always "every near-miss".
CREATE INDEX IF NOT EXISTS wear_log_swap_idx ON wear_log (nearly_wore, instead_of)
    WHERE nearly_wore IS NOT NULL;

-- acceptance: the 15 existing wears survive untouched, with the new fields empty
SELECT count(*)                                   AS wears,
       count(occasion)                            AS with_occasion,
       count(*) FILTER (WHERE weather <> '{}')    AS with_weather,
       count(nearly_wore)                         AS with_swap
  FROM wear_log;
