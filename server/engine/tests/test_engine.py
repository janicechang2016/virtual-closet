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


@unittest.skipUnless(os.path.exists(SNAPSHOT), "closet snapshot not dumped")
class TestRealCloset(unittest.TestCase):
    """Assertions against the actual 58-garment closet."""

    @classmethod
    def setUpClass(cls):
        with open(SNAPSHOT) as fh:
            data = json.load(fh)
        cls.garments = data["garments"]
        cls.outfits = data["outfits"]

    def test_every_garment_attributed(self):
        for field in ("formality", "warmth", "volume", "subcategory"):
            missing = [g_["id"] for g_ in self.garments if g_.get(field) is None]
            self.assertEqual(missing, [], "%s missing on %s" % (field, missing))

    def test_every_garment_has_colour(self):
        self.assertEqual([g_["id"] for g_ in self.garments if not g_.get("colors")], [])

    def test_enumeration_matches_arithmetic(self):
        n = {c: len([x for x in self.garments if x["category"] == c])
             for c in ("top", "bottom", "dress", "shoes")}
        expected = (n["top"] * n["bottom"] + n["dress"]) * n["shoes"]
        self.assertEqual(len(gaps.enumerate_outfits(self.garments)), expected)

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

    def test_rejection_lowers_affinity(self):
        aff = preference.affinity(self.closet, [], [({"ids": ["disliked"]}, "no")] * 3)
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
