-- Phase 1 acceptance checks. Read-only; safe to run any time.
--   railway run --service Postgres bash -c \
--     '/opt/homebrew/opt/libpq/bin/psql "$DATABASE_PUBLIC_URL" -X -f scripts/verify_backfill.sql'
\echo '== counts =='
SELECT (SELECT count(*) FROM garment)                                AS garments,
       (SELECT count(*) FROM outfit WHERE source = 'manual')         AS outfits_manual,
       (SELECT count(*) FROM garment WHERE colors = '[]'::jsonb)     AS garments_no_colors,
       (SELECT count(*) FROM garment WHERE formality IS NOT NULL)    AS formality_set,
       (SELECT count(*) FROM garment WHERE warmth   IS NOT NULL)     AS warmth_set;

\echo '== category mix =='
SELECT category, count(*) FROM garment GROUP BY 1 ORDER BY 2 DESC;

\echo '== outfits referencing a garment that does not exist (must be 0) =='
SELECT count(*) AS orphan_refs
FROM (SELECT unnest(garment_ids) AS gid FROM outfit) u
LEFT JOIN garment g ON g.id = u.gid
WHERE g.id IS NULL;

\echo '== duplicate outfits by look id (must be 0) =='
SELECT count(*) AS dupes FROM (
  SELECT render_cache_key FROM outfit GROUP BY 1 HAVING count(*) > 1
) d;

\echo '== garments never worn in any published look (cold-start orphans) =='
SELECT count(*) AS unworn_garments
FROM garment g
WHERE NOT EXISTS (SELECT 1 FROM outfit o WHERE g.id = ANY(o.garment_ids));

\echo '== user-confirmed attributes (from the grid) =='
SELECT count(*) FILTER (WHERE formality   IS NOT NULL) AS formality_set,
       count(*) FILTER (WHERE warmth      IS NOT NULL) AS warmth_set,
       count(*) FILTER (WHERE volume      IS NOT NULL) AS volume_set,
       count(*) FILTER (WHERE subcategory IS NOT NULL) AS subcat_set,
       count(*) FILTER (WHERE season_tags <> '{}')     AS seasons_set,
       count(*)                                        AS total
FROM garment;

\echo '== garments still awaiting confirmation =='
SELECT id, category, name_hint FROM (
  SELECT id, category, left(coalesce(fit, ''), 44) AS name_hint
  FROM garment WHERE formality IS NULL ORDER BY id
) q;

\echo '== looks by occasion =='
SELECT context->>'occasion' AS occasion,
       count(*)             AS looks
FROM outfit
WHERE context ? 'occasion'
GROUP BY 1 ORDER BY 2 DESC;

\echo '== context merge preserved backfill keys (title/pose must survive) =='
SELECT count(*) FILTER (WHERE context ? 'title')    AS has_title,
       count(*) FILTER (WHERE context ? 'pose')     AS has_pose,
       count(*) FILTER (WHERE context ? 'occasion') AS has_occasion
FROM outfit;

\echo '== purchase coverage + closet value =='
SELECT count(*) FILTER (WHERE purchase ? 'price_usd') AS priced,
       count(*) FILTER (WHERE purchase ? 'date')      AS dated,
       count(*)                                       AS total,
       to_char(sum((purchase->>'price_usd')::numeric), 'FM999,999.00') AS total_usd,
       to_char(avg((purchase->>'price_usd')::numeric), 'FM999.00')     AS avg_usd
FROM garment;

\echo '== spend by category =='
SELECT category, count(*) AS items,
       to_char(sum((purchase->>'price_usd')::numeric), 'FM999,999') AS spend
FROM garment WHERE purchase ? 'price_usd'
GROUP BY 1 ORDER BY sum((purchase->>'price_usd')::numeric) DESC;

\echo '== most expensive garments never worn in a published look =='
SELECT g.id, to_char((g.purchase->>'price_usd')::numeric, 'FM999,999') AS price,
       g.purchase->>'date' AS bought
FROM garment g
WHERE g.purchase ? 'price_usd'
  AND NOT EXISTS (SELECT 1 FROM outfit o WHERE g.id = ANY(o.garment_ids))
ORDER BY (g.purchase->>'price_usd')::numeric DESC LIMIT 8;

\echo '== sample: dominant colour per garment =='
SELECT id, size_owned, brand,
       colors->0->>'name'                       AS dominant,
       round((colors->0->>'coverage')::numeric, 2) AS coverage
FROM garment ORDER BY id LIMIT 8;
