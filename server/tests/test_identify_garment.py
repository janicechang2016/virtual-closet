"""The $0 half of find-a-better-photo. Stdlib unittest, no API calls, no network.

These lock in the promises the feature makes to her, because every one of them
is invisible at runtime until it has already gone wrong: a price quietly filled
from a retail listing looks exactly like a price she typed, and a confidently
misidentified garment produces a grid that is plausible in every cell.
"""
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "scripts"))

import identify_garment as ig  # noqa: E402

ATTRS = ig.SCHEMA["properties"]["attributes"]["properties"]
FIELDS = [k for k in ATTRS if k != "provenance"]


class TestSchemaRefusals(unittest.TestCase):
    """The four things the model must never be allowed to supply."""

    def test_colour_is_never_a_model_output(self):
        """Invariant #6: the model may NAME a colour, never MEASURE one.
        extract_colors.py does LAB k-means with white-balance normalisation, and
        that rule survived a QA round against her own eyes."""
        for banned in ("color", "colour", "colors", "colours"):
            self.assertNotIn(banned, ATTRS)

    def test_price_is_never_a_model_output(self):
        """A retail listing price is NOT what she paid. Closet value ($6,298) and
        every cost-per-wear figure in /insights rest on her real purchase data —
        a pre-filled listing price would corrupt the one hand-built dataset."""
        for banned in ("price", "price_usd", "purchase", "purchase_price",
                       "purchase_date", "date"):
            self.assertNotIn(banned, ATTRS)

    def test_size_is_never_a_model_output(self):
        """In no photo and on no page. Her standing ingest note: log real sizes,
        not everything is S."""
        for banned in ("size", "size_owned"):
            self.assertNotIn(banned, ATTRS)

    def test_schema_is_closed(self):
        """additionalProperties:false everywhere — otherwise the model can invent
        a `price` field the assertions above cannot see."""
        def closed(node):
            if isinstance(node, dict):
                if node.get("type") == "object":
                    self.assertIs(node.get("additionalProperties"), False,
                                  "open object in schema: %s" % sorted(node)[:4])
                for v in node.values():
                    closed(v)
            elif isinstance(node, list):
                for v in node:
                    closed(v)
        closed(ig.SCHEMA)


class TestProvenance(unittest.TestCase):
    def test_every_attribute_has_a_provenance_entry(self):
        """Provenance is what tells her which cells to scrutinise. A field
        without one is a value with no stated origin — the exact thing that
        makes a wrong pre-fill pass review."""
        prov = ATTRS["provenance"]["properties"]
        self.assertEqual(sorted(prov), sorted(FIELDS))

    def test_provenance_is_required_for_every_attribute(self):
        self.assertEqual(sorted(ATTRS["provenance"]["required"]), sorted(FIELDS))

    def test_provenance_values_are_constrained(self):
        for field, spec in ATTRS["provenance"]["properties"].items():
            self.assertEqual(spec["enum"], ["page", "image", "inferred"], field)


class TestRequestShape(unittest.TestCase):
    def setUp(self):
        # A tiny valid PNG — this never leaves the process.
        import base64
        import tempfile
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
        self.tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        self.tmp.write(png)
        self.tmp.close()
        self.req = ig.build_request(__import__("pathlib").Path(self.tmp.name))

    def tearDown(self):
        os.unlink(self.tmp.name)

    def test_effort_is_low(self):
        """Thinking is ON BY DEFAULT on Sonnet 5 and Opus 5 — that default is
        what made the D.1 profile cost 20x its estimate. Tagging is
        classification, so effort is pinned rather than left implicit."""
        self.assertEqual(self.req["output_config"]["effort"], "low")

    def test_structured_output_is_requested(self):
        fmt = self.req["output_config"]["format"]
        self.assertEqual(fmt["type"], "json_schema")
        self.assertIs(fmt["schema"], ig.SCHEMA)

    def test_web_search_is_capped(self):
        """Uncapped search is uncapped spend — each one bills at $0.01."""
        tool = self.req["tools"][0]
        self.assertEqual(tool["name"], "web_search")
        self.assertEqual(tool["max_uses"], ig.MAX_SEARCHES)

    def test_model_is_not_opus(self):
        """Sonnet 5 on purpose: this is classification, not reasoning, and Opus
        would pay frontier prices to decide whether a tank top is a tank top."""
        self.assertEqual(self.req["model"], "claude-sonnet-5")

    def test_system_prompt_forbids_guessing(self):
        sys_prompt = self.req["system"].lower()
        self.assertIn("do not guess", sys_prompt)
        self.assertIn("identified=false", sys_prompt)


class TestStubs(unittest.TestCase):
    """The stubs are the $0 fixtures the UI is built against — if they drift from
    the schema, the UI gets built against a shape the API will never send."""

    def test_stubs_match_the_schema_fields(self):
        for name, stub in ig.STUBS.items():
            self.assertEqual(sorted(stub["attributes"]) , sorted(ATTRS), name)
            self.assertEqual(sorted(stub["attributes"]["provenance"]),
                             sorted(FIELDS), name)

    def test_stub_enums_are_legal(self):
        for name, stub in ig.STUBS.items():
            a = stub["attributes"]
            self.assertIn(a["category"], ATTRS["category"]["enum"], name)
            self.assertIn(a["volume"], ATTRS["volume"]["enum"], name)
            self.assertIn(a["formality"], ATTRS["formality"]["enum"], name)
            self.assertIn(a["warmth"], ATTRS["warmth"]["enum"], name)
            for s in a["seasons"]:
                self.assertIn(s, ATTRS["seasons"]["items"]["enum"], name)
            for v in a["provenance"].values():
                self.assertIn(v, ["page", "image", "inferred"], name)

    def test_hard_stub_claims_nothing(self):
        """The unidentifiable case must not leak a brand or a URL. ~60% of this
        closet is below L*25 — plain dark garments are the common case, not the
        edge case, so the honest-failure path is the one that gets exercised."""
        ident = ig.STUBS["hard"]["identification"]
        self.assertFalse(ident["identified"])
        self.assertEqual(ident["brand"], "")
        self.assertEqual(ident["product_url"], "")
        self.assertTrue(ident["evidence"], "a refusal still owes her a reason")
        prov = ig.STUBS["hard"]["attributes"]["provenance"]
        self.assertNotIn("page", prov.values(),
                         "nothing can come from a page that was never found")

    def test_easy_stub_sources_fabric_from_the_page(self):
        """The whole argument for finding the page: fabric and brand are the
        fields a photograph cannot supply, and fabric is the one her own ingest
        form gives up on."""
        a = ig.STUBS["easy"]["attributes"]
        self.assertEqual(a["provenance"]["fabric"], "page")
        self.assertTrue(a["fabric"])

    def test_render_handles_both_paths(self):
        for name, stub in ig.STUBS.items():
            out = ig.render(dict(stub))
            self.assertIn("NOT FILLED, by design", out, name)
            self.assertIn("colour (measured)", out, name)
        self.assertIn("NOT IDENTIFIED", ig.render(dict(ig.STUBS["hard"])))
        self.assertIn("IDENTIFIED (high", ig.render(dict(ig.STUBS["easy"])))


class TestCost(unittest.TestCase):
    def test_estimate_is_bounded_and_declared(self):
        import pathlib
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as fh:
            fh.write(b"x" * 200_000)
            p = pathlib.Path(fh.name)
        try:
            est = ig.estimate(p)
            # Sanity, not a pin: a per-garment call must stay in cents.
            self.assertLess(est["total_max"], 0.15)
            self.assertGreater(est["total_max"], 0.0)
            self.assertEqual(est["search_cost_max"],
                             round(ig.MAX_SEARCHES * ig.SEARCH_PRICE, 4))
        finally:
            os.unlink(p)

    def test_search_price_matches_published_rate(self):
        """$10 per 1,000 searches, checked against the docs 2026-07-28."""
        self.assertEqual(ig.SEARCH_PRICE, 0.010)


if __name__ == "__main__":
    unittest.main()
