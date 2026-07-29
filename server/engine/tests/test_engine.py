"""Phase 2 engine tests. Stdlib unittest — no pytest, no network, no API calls.

    python3 -m unittest discover -s engine/tests -v

Two kinds of test, deliberately separated:

  Synthetic — colours and garments constructed so the right answer is known
              independently of this closet. These pin the rules.
  Real       — assertions against closet_snapshot.json (58 garments, 18 looks).
              These catch the case where a rule is defensible in the abstract
              and useless on the actual wardrobe.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from engine import colour, constraints, gaps, preference  # noqa: E402

SNAPSHOT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "..", "..", "scripts", "closet_snapshot.json")

BLACK = [15.0, 1.0, -1.0]
WHITE = [95.0, 0.0, 1.0]
GREY = [55.0, 0.5, 0.0]
RED = [45.0, 60.0, 35.0]
ORANGE = [60.0, 35.0, 50.0]
GREEN = [50.0, -45.0, 30.0]
BLUE = [40.0, 10.0, -50.0]


def g(gid, category, colors=None, **kw):
    labs = colors or [GREY]
    item = {"id": gid, "category": category,
            "colors": [{"lab": c, "coverage": 1.0 / len(labs), "name": "x"}
                       for c in labs]}
    item.update(kw)
    return item


class TestColour(unittest.TestCase):
    def test_neutral_detection(self):
        for lab in (BLACK, WHITE, GREY):
            self.assertTrue(colour.is_neutral(lab), lab)
        for lab in (RED, GREEN, BLUE):
            self.assertFalse(colour.is_neutral(lab), lab)

    def test_hue_delta_wraps(self):
        # 350 deg and 10 deg are 20 apart, not 340.
        a = [50.0, 30.0, -5.3]
        b = [50.0, 30.0, 5.3]
        self.assertLess(colour.hue_delta(a, b), 25.0)

    def test_neutral_beats_discord(self):
        neutral, _ = colour.pair_harmony(BLACK, RED)
        discord, _ = colour.pair_harmony(RED, [50.0, -9.5, 54.2])
        self.assertGreater(neutral, discord)

    def test_monochrome_beats_discord(self):
        mono, r1 = colour.pair_harmony(RED, [60.0, 55.0, 32.0])
        disc, r2 = colour.pair_harmony(RED, [50.0, -9.5, 54.2])
        self.assertEqual(r1, "monochrome")
        self.assertGreater(mono, disc)

    def test_complementary_beats_discord(self):
        # RED sits at hue ~30 deg; its complement is ~210 deg, not GREEN's ~146.
        complement_of_red = [45.0, -43.3, -25.0]
        comp, reason = colour.pair_harmony(RED, complement_of_red)
        # ~70 deg from red: past analogous, short of complementary.
        disc, _ = colour.pair_harmony(RED, [50.0, -9.5, 54.2])
        self.assertEqual(reason, "complementary")
        self.assertGreater(comp, disc)

    def test_accent_does_not_dominate(self):
        """A 5% print accent tints the judgement; it must not decide it."""
        base = {"colors": [{"lab": WHITE, "coverage": 0.95},
                           {"lab": RED, "coverage": 0.05}]}
        other = {"colors": [{"lab": BLACK, "coverage": 1.0}]}
        score, _ = colour.garment_harmony(base["colors"], other["colors"])
        self.assertGreater(score, 0.8)


class TestConstraints(unittest.TestCase):
    def test_top_bottom_shoes_valid(self):
        self.assertTrue(constraints.is_valid(
            [g("t", "top"), g("b", "bottom"), g("s", "shoes")]))

    def test_dress_shoes_valid(self):
        self.assertTrue(constraints.is_valid([g("d", "dress"), g("s", "shoes")]))

    def test_missing_shoes_invalid(self):
        self.assertIn("no shoes", constraints.hard_violations(
            [g("t", "top"), g("b", "bottom")]))

    def test_dress_with_bottom_invalid(self):
        self.assertIn("dress worn with a bottom", constraints.hard_violations(
            [g("d", "dress"), g("b", "bottom"), g("s", "shoes")]))

    def test_two_bottoms_invalid(self):
        self.assertIn("two bottoms", constraints.hard_violations(
            [g("t", "top"), g("b1", "bottom"), g("b2", "bottom"), g("s", "shoes")]))

    def test_top_over_dress_allowed(self):
        """A deliberate styling move, not a structural error."""
        self.assertTrue(constraints.is_valid(
            [g("d", "dress"), g("t", "top"), g("s", "shoes")]))

    def test_formality_spread_penalised(self):
        tight = [g("t", "top", formality=3), g("b", "bottom", formality=3),
                 g("s", "shoes", formality=3)]
        wide = [g("t", "top", formality=1), g("b", "bottom", formality=5),
                g("s", "shoes", formality=3)]
        self.assertEqual(constraints.soft_notes(tight)[0], 0.0)
        self.assertGreater(constraints.soft_notes(wide)[0], 0.0)

    def test_oversized_on_oversized_penalised(self):
        combo = [g("t", "top", volume="oversized"),
                 g("b", "bottom", volume="oversized"), g("s", "shoes")]
        penalty, notes = constraints.soft_notes(combo)
        self.assertGreater(penalty, 0.0)
        self.assertIn("oversized on oversized", notes)

    def test_soft_rules_never_invalidate(self):
        """The clash of the century is still structurally an outfit."""
        combo = [g("t", "top", formality=1, warmth=1, volume="oversized"),
                 g("b", "bottom", formality=5, warmth=5, volume="oversized"),
                 g("s", "shoes", formality=1)]
        self.assertTrue(constraints.is_valid(combo))
        self.assertGreater(constraints.soft_notes(combo)[0], 0.0)

    def test_shoes_excluded_from_warmth_spread(self):
        """Boots with a summer dress is a look, not an incoherent outfit."""
        combo = [g("d", "dress", warmth=1), g("s", "shoes", warmth=5)]
        self.assertEqual(constraints.soft_notes(combo)[0], 0.0)


class TestUserRules(unittest.TestCase):
    """Her rules from style_rules.txt. Synthetic garments — these pin the rule,
    not the closet."""

    SNEAK = dict(category="shoes", subcategory="sneaker")
    SKIRT = dict(category="bottom", subcategory="skirt")

    def test_sneaker_with_skirt_rejected(self):
        combo = [g("t", "top"), g("sk", **self.SKIRT), g("sn", **self.SNEAK)]
        self.assertIn("sneaker with a skirt or dress",
                      constraints.user_rule_violations(combo))

    def test_sneaker_with_dress_rejected(self):
        combo = [g("d", "dress"), g("sn", **self.SNEAK)]
        self.assertFalse(constraints.allowed_by_user_rules(combo))

    def test_sneaker_with_trousers_allowed(self):
        """The rule is about skirts and dresses, not about sneakers."""
        combo = [g("t", "top"), g("b", "bottom", subcategory="trousers"),
                 g("sn", **self.SNEAK)]
        self.assertTrue(constraints.allowed_by_user_rules(combo))

    def test_keen_sandals_with_skirt_rejected(self):
        combo = [g("t", "top"), g("sk", **self.SKIRT),
                 g(constraints.KEEN_SANDALS, "shoes", subcategory="sandal")]
        self.assertIn("keen sandals with a skirt or dress",
                      constraints.user_rule_violations(combo))

    def test_another_sandal_is_not_covered_by_the_keen_rule(self):
        """Her rule names her Keens. A future sandal must not inherit it silently."""
        combo = [g("t", "top"), g("sk", **self.SKIRT),
                 g("99-other-sandals", "shoes", subcategory="sandal")]
        self.assertTrue(constraints.allowed_by_user_rules(combo))

    def test_user_rules_are_not_hard_rules(self):
        """The tiers must stay separate.

        A sneaker with a skirt is still structurally an outfit — it is one she
        has told us not to SUGGEST. Collapsing this into hard_violations would
        retroactively invalidate two of her own published looks.
        """
        combo = [g("t", "top"), g("sk", **self.SKIRT), g("sn", **self.SNEAK)]
        self.assertTrue(constraints.is_valid(combo))
        self.assertFalse(constraints.allowed_by_user_rules(combo))


class TestGaps(unittest.TestCase):
    def setUp(self):
        self.closet = ([g("t%d" % i, "top") for i in range(3)]
                       + [g("b%d" % i, "bottom") for i in range(2)]
                       + [g("d%d" % i, "dress") for i in range(2)]
                       + [g("s%d" % i, "shoes") for i in range(2)])

    def test_enumeration_count(self):
        # (3 tops x 2 bottoms + 2 dresses) x 2 shoes = 16
        self.assertEqual(len(gaps.enumerate_outfits(self.closet)), 16)

    def test_outerwear_counts_toward_participation(self):
        """Excluding outerwear reported every coat as an orphan — an artifact."""
        closet = self.closet + [g("o1", "outerwear")]
        self.assertGreater(gaps.participation(closet)["o1"], 0)
        self.assertEqual([o["id"] for o in gaps.orphans(closet)], [])

    def test_orphan_with_no_partner(self):
        """A lone shoe-less closet strands everything."""
        closet = [g("t", "top"), g("b", "bottom")]      # no shoes at all
        self.assertEqual(len(gaps.enumerate_outfits(closet)), 0)
        self.assertEqual(len(gaps.orphans(closet)), 2)

    def test_cost_per_wear(self):
        closet = [g("a", "top", purchase={"price_usd": 100}),
                  g("b", "top", purchase={"price_usd": 50}),
                  g("c", "top", purchase={})]
        worn = [{"garment_ids": ["a"]}, {"garment_ids": ["a"]}]
        rows = {r["id"]: r for r in gaps.cost_per_wear(closet, worn)}
        self.assertEqual(rows["a"]["cost_per_wear"], 50.0)   # 100 / 2 wears
        self.assertIsNone(rows["b"]["cost_per_wear"])        # never worn
        self.assertNotIn("c", rows)                          # no price recorded

    def test_unworn(self):
        closet = [g("a", "top"), g("b", "top")]
        self.assertEqual(gaps.unworn(closet, [{"garment_ids": ["a"]}]), ["b"])

    def test_hypothetical_never_returns_the_ghost_as_a_garment(self):
        """The stand-in must not leak into anything the caller could display."""
        r = gaps.hypothetical_unlocks(self.closet, categories=("bottom",))
        for row in r["rows"]:
            self.assertNotIn("id", row)
            self.assertEqual(row["category"], "bottom")

    def test_hypothetical_valid_count_is_category_arithmetic(self):
        """Structural validity is slot-counting, so a new bottom pairs with every
        top and every shoe. If this ever stops holding, hard_violations changed."""
        r = gaps.hypothetical_unlocks(self.closet, categories=("bottom",))
        tops = sum(1 for x in self.closet if x["category"] == "top")
        shoes = sum(1 for x in self.closet if x["category"] == "shoes")
        for row in r["rows"]:
            self.assertEqual(row["valid"], tops * shoes)

    def test_hypothetical_discriminates_on_formality(self):
        """The whole point of scoring against a quality bar: a garment that
        suits nothing in the closet must not tie with one that suits everything."""
        closet = ([g("t%d" % i, "top", formality=2) for i in range(3)]
                  + [g("b", "bottom", formality=2), g("s", "shoes", formality=2)])
        r = gaps.hypothetical_unlocks(closet, categories=("bottom",))
        by_f = {}
        for row in r["rows"]:
            by_f.setdefault(row["formality"], 0)
            by_f[row["formality"]] = max(by_f[row["formality"]], row["unlocked"])
        self.assertGreater(by_f[2], by_f[5])

    def test_hypothetical_excludes_colour(self):
        """Colour is measured below chance against her wears; it must not be a
        swept dimension, or the report recommends white and penalises black."""
        self.assertNotIn("colour", gaps.HYPOTHETICAL_DIMS)
        self.assertNotIn("color", gaps.HYPOTHETICAL_DIMS)

    def test_rediscovery_covers_every_unworn_garment(self):
        closet = [g("t", "top"), g("b", "bottom"), g("s", "shoes")]
        rows = gaps.rediscovery(closet, [{"garment_ids": ["t", "b", "s"]}])
        self.assertEqual(rows, [])                     # nothing unworn
        rows = gaps.rediscovery(closet, [])
        self.assertEqual({r["id"] for r in rows}, {"t", "b", "s"})
        for r in rows:
            self.assertNotIn(r["id"], r["partners"])   # never suggests itself

    def test_rediscovery_reaches_a_never_worn_outerwear(self):
        """A coat appears in no outfit while with_outerwear is off, so without
        the fallback pass the one garment most likely to sit unworn gets no
        suggestion at all."""
        closet = [g("t", "top"), g("b", "bottom"), g("s", "shoes"),
                  g("coat", "outerwear")]
        rows = gaps.rediscovery(closet, [{"garment_ids": ["t", "b", "s"]}])
        self.assertEqual([r["id"] for r in rows], ["coat"])
        self.assertIn("coat", rows[0]["outfit"])


@unittest.skipUnless(os.path.exists(SNAPSHOT), "closet snapshot not dumped")
class TestRealCloset(unittest.TestCase):
    """Assertions against the actual 58-garment closet."""

    @classmethod
    def setUpClass(cls):
        with open(SNAPSHOT) as fh:
            data = json.load(fh)
        cls.garments = data["garments"]
        cls.outfits = data["outfits"]
        cls.wears = data.get("wears") or []

    def test_every_garment_attributed(self):
        for field in ("formality", "warmth", "volume", "subcategory"):
            missing = [g_["id"] for g_ in self.garments if g_.get(field) is None]
            self.assertEqual(missing, [], "%s missing on %s" % (field, missing))

    def test_every_garment_has_colour(self):
        self.assertEqual([g_["id"] for g_ in self.garments if not g_.get("colors")], [])

    def test_enumeration_matches_arithmetic(self):
        # Slot membership follows the same rule as gaps._cat: a garment fills its
        # primary `category` plus anything in `alt_categories` (migration 0005 —
        # 59-el-hoodie is outerwear she wears as a top). Spelled out here rather
        # than calling _cat, so this stays an INDEPENDENT check of the enumerator
        # instead of comparing it against itself.
        def fills(g_, c):
            return g_["category"] == c or c in (g_.get("alt_categories") or ())
        n = {c: len([x for x in self.garments if fills(x, c)])
             for c in ("top", "bottom", "dress", "shoes")}
        expected = (n["top"] * n["bottom"] + n["dress"]) * n["shoes"]
        # Unfiltered: this asserts on the STRUCTURAL space, so her user rules are
        # off. The filtered count is checked independently below.
        self.assertEqual(
            len(gaps.enumerate_outfits(self.garments, apply_user_rules=False)),
            expected)

    def test_user_rules_remove_exactly_the_skirt_and_dress_pairings(self):
        """The rules' cost, derived independently rather than pinned to a number.

        Her two executable rules both say the same thing about the same set of
        shoes, so what they remove is arithmetic: every (skirt|dress) outfit
        wearing a sneaker or the Keens. Computing it from slot counts rather than
        hard-coding 1600 means this test still means something after an ingest.
        """
        def fills(g_, c):
            return g_["category"] == c or c in (g_.get("alt_categories") or ())
        tops = [x for x in self.garments if fills(x, "top")]
        bottoms = [x for x in self.garments if fills(x, "bottom")]
        dresses = [x for x in self.garments if fills(x, "dress")]
        shoes = [x for x in self.garments if fills(x, "shoes")]

        banned = [s for s in shoes
                  if s.get("subcategory") == "sneaker"
                  or s["id"] == constraints.KEEN_SANDALS]
        skirts = [b for b in bottoms if b.get("subcategory") == "skirt"]
        # bases that a banned shoe may no longer finish
        lost = (len(tops) * len(skirts) + len(dresses)) * len(banned)

        full = len(gaps.enumerate_outfits(self.garments, apply_user_rules=False))
        filtered = len(gaps.enumerate_outfits(self.garments))
        self.assertEqual(full - filtered, lost)
        self.assertTrue(banned and skirts, "fixture lost its sneakers or skirts")

    def test_user_rules_strand_no_garment(self):
        """Filtering may shrink the space but must not remove anyone from it.

        A garment that appears in zero suggestable outfits is invisible to the
        stylist, the wildcard and the rediscovery leads at once — a rule that
        does that has stopped filtering and started deleting.
        """
        space = gaps.enumerate_outfits(self.garments)
        seen = {g_["id"] for combo in space for g_ in combo}
        wearable = [g_["id"] for g_ in self.garments
                    if g_["category"] in ("top", "bottom", "dress", "shoes")
                    or (g_.get("alt_categories") or ())]
        self.assertEqual([i for i in wearable if i not in seen], [])

    def test_user_rules_do_not_invalidate_worn_outfits(self):
        """The closet's own history is the check on any rule that filters.

        Measured 07-28: zero worn outfits break either rule. Two PUBLISHED looks
        do (both `32-personal-language-skirt` with the Keens) and neither was
        ever worn — which is why these are a separate tier and are not in
        `hard_violations`. If a future rule ever fails something she actually
        WORE, the rule is what is wrong.
        """
        by_id = {g_["id"]: g_ for g_ in self.garments}
        worn_ids = {o["id"] for o in self.outfits if o.get("source") == "worn"}
        bad = []
        for o in self.outfits:
            if o["id"] not in worn_ids:
                continue
            combo = [by_id[i] for i in o["garment_ids"] if i in by_id]
            v = constraints.user_rule_violations(combo)
            if v:
                bad.append((o["id"], v))
        self.assertEqual(bad, [], "a rule rejects an outfit she actually wore: %s" % bad)

    def test_dual_role_garment_is_enumerated_in_its_alt_slot(self):
        """A garment with an alt role must actually reach the outfit space.

        59-el-hoodie is outerwear she wears as the top: 3 of her first 15 logged
        wears were bottom + shoes + hoodie, a shape hard_violations already
        allowed but that the enumerator never generated, so one of her most-worn
        garments could never be suggested.
        """
        combos = gaps.enumerate_outfits(self.garments)
        with_hoodie = [c for c in combos
                       if any(g_["id"] == "59-el-hoodie" for g_ in c)]
        self.assertTrue(with_hoodie,
                        "dual-role garment never appears in the outfit space")

    def test_no_garment_appears_twice_in_one_outfit(self):
        """A dual-role garment must not become its own outer layer."""
        for combo in gaps.enumerate_outfits(self.garments, with_outerwear=True):
            ids = [g_["id"] for g_ in combo]
            self.assertEqual(len(ids), len(set(ids)),
                             "garment duplicated within an outfit: %s" % ids)

    def test_worn_means_the_same_thing_everywhere(self):
        """One definition of "worn", checked against /insights' own arithmetic.

        `engine_report.py` passed the RAW outfit list to unworn()/cost_per_wear()
        until 07-28, so a garment counted as worn because the stylist once
        suggested it: 9 never-worn reported against /insights' 13, and every
        cost-per-wear deflated by suggestions. This reproduces the /insights
        number independently — published appearances plus the wear log — and
        asserts gaps.worn_outfits() agrees with it.
        """
        self.assertTrue(self.wears, "fixture has no wear log to check against")
        wears = {w["outfit_id"] for w in self.wears}
        by_id = {o["id"]: o for o in self.outfits}
        seen = set()
        for o in self.outfits:
            if o.get("source") == "manual":
                seen.update(o.get("garment_ids") or [])
        for oid in wears:
            seen.update((by_id.get(oid) or {}).get("garment_ids") or [])
        expected = sorted(g["id"] for g in self.garments if g["id"] not in seen)

        got = sorted(gaps.unworn(self.garments, gaps.worn_outfits(self.outfits)))
        self.assertEqual(got, expected)

    def test_suggestions_are_not_evidence_of_wearing(self):
        """A stylist suggestion must never make a garment count as worn."""
        suggested = [o for o in self.outfits
                     if o.get("source") not in gaps.WORN_SOURCES]
        self.assertTrue(suggested, "fixture has no suggestions to exclude")
        kept = {o["id"] for o in gaps.worn_outfits(self.outfits)}
        self.assertFalse(kept & {o["id"] for o in suggested})

    def test_published_looks_are_structurally_valid(self):
        """Her own 18 looks must pass the rules. If they do not, the rules are wrong."""
        by_id = {g_["id"]: g_ for g_ in self.garments}
        bad = []
        for o in self.outfits:
            combo = [by_id[i] for i in o["garment_ids"] if i in by_id]
            v = constraints.hard_violations(combo)
            if v:
                bad.append((o.get("render_cache_key"), v))
        self.assertEqual(bad, [], "published looks failing hard rules: %s" % bad)

    def test_published_looks_score_above_median(self):
        """The prior should rank well against the space it was drawn from."""
        by_id = {g_["id"]: g_ for g_ in self.garments}
        ranked = gaps.ranked_outfits(self.garments)
        median = sorted(o["score"] for o in ranked)[len(ranked) // 2]
        scores = []
        for o in self.outfits:
            combo = [by_id[i] for i in o["garment_ids"] if i in by_id]
            h, _ = colour.outfit_harmony(combo)
            s, _ = constraints.score(combo, h)
            scores.append(s)
        mean = sum(scores) / len(scores)
        self.assertGreaterEqual(mean, median - 0.05,
                                "her own looks rank below the median outfit")


if __name__ == "__main__":
    unittest.main()


class TestPreference(unittest.TestCase):
    """Learned affinity — the only signal measured to predict her judgement."""

    def setUp(self):
        self.closet = [g("liked", "shoes"), g("disliked", "shoes"), g("unseen", "shoes"),
                       g("t", "top"), g("b", "bottom")]

    def test_no_evidence_is_neutral(self):
        aff = preference.affinity(self.closet)
        self.assertAlmostEqual(aff["unseen"], 0.5)

    def test_published_look_raises_affinity(self):
        aff = preference.affinity(self.closet, [{"garment_ids": ["liked"]}] * 3)
        self.assertGreater(aff["liked"], 0.5)
        self.assertAlmostEqual(aff["unseen"], 0.5)

    def test_rejections_ignored_by_default(self):
        """Measured twice: applying rejections makes prediction worse."""
        aff = preference.affinity(self.closet, [], [({"ids": ["disliked"]}, "no")] * 3)
        self.assertAlmostEqual(aff["disliked"], 0.5)

    def test_rejection_lowers_affinity_when_weighted(self):
        aff = preference.affinity(self.closet, [], [({"ids": ["disliked"]}, "no")] * 3,
                                  negative_weight=1.0)
        self.assertLess(aff["disliked"], 0.5)

    def test_smoothing_bounds_thin_evidence(self):
        """One observation must not produce certainty."""
        aff = preference.affinity(self.closet, [{"garment_ids": ["liked"]}])
        self.assertLess(aff["liked"], 0.8)

    def test_one_bad_garment_sinks_the_outfit(self):
        """The loafer case: everything else fine, still would not wear it."""
        aff = {"t": 0.9, "b": 0.9, "disliked": 0.1}
        blended = preference.outfit_preference(["t", "b", "disliked"], aff)
        all_good = preference.outfit_preference(["t", "b"], aff)
        self.assertLess(blended, all_good)
        self.assertLess(blended, 0.6)

    def test_ranking_uses_affinity_when_given(self):
        closet = [g("t", "top"), g("b", "bottom"),
                  g("good", "shoes"), g("bad", "shoes")]
        aff = {"t": 0.5, "b": 0.5, "good": 0.95, "bad": 0.05}
        ranked = gaps.ranked_outfits(closet, affinity=aff)
        self.assertIn("good", ranked[0]["garment_ids"])
        self.assertIn("bad", ranked[-1]["garment_ids"])
        self.assertIsNotNone(ranked[0]["preference"])
