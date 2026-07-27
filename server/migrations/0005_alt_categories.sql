-- Garments that legitimately play more than one role.
--
-- `category` stays exactly as it is: a single NOT NULL text read in ~55 places
-- across ~20 files (insights grouping, the /wear grid, tryon, dragcut, the
-- ingest forms). Widening it to a list would touch all of them for the sake of
-- one garment, so this is ADDITIVE and only the outfit enumerator reads it.
--
-- The case that forced it, measured 07-27: 3 of her first 15 logged wears were
-- `bottom + shoes + 59-el-hoodie`. The hoodie is outerwear by category but she
-- wears it AS THE TOP, so those outfits have no `top`, fall outside
-- gaps.enumerate_outfits(), and the stylist can never suggest one of her
-- most-worn garments.
--
-- Semantics: `category` remains the garment's primary identity. `alt_categories`
-- lists ADDITIONAL slots it may fill when composing an outfit. Null/empty means
-- "primary only", which is every other garment.

ALTER TABLE garment ADD COLUMN IF NOT EXISTS alt_categories text[];

UPDATE garment SET alt_categories = ARRAY['top']
 WHERE id = '59-el-hoodie';

-- acceptance: exactly one garment carries an alt role, and it is the hoodie
SELECT id, category, alt_categories
  FROM garment
 WHERE alt_categories IS NOT NULL AND cardinality(alt_categories) > 0
 ORDER BY id;
