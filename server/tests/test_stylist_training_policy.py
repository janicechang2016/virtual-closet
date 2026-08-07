"""Runtime pairwise training policy. Stdlib unittest, no API calls.

The measurement harness intentionally reports full-verdict and blame-only
ablations side by side. The shipped Stylist is the blame-only variant: positive
evidence comes from deliberately published looks, while self-selected "yes"
cards from the old affinity ranker do not train pairwise. These tests prevent a
report label from being mistaken for the production policy again.
"""
import os
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "virtual-closet", "scripts"))

import closet_server as closet  # noqa: E402


GARMENTS = [
    {"id": "top", "category": "top", "subcategory": "tank"},
    {"id": "bottom", "category": "bottom", "subcategory": "trousers"},
    {"id": "shoe", "category": "shoes", "subcategory": "flat"},
]

YES = {"ids": ["top", "bottom", "shoe"], "verdict": "yes", "blame": None}
BLAMED_NO = {
    "ids": ["top", "bottom", "shoe"],
    "verdict": "no",
    "blame": "shoe",
}
UNATTRIBUTED_NO = {
    "ids": ["top", "bottom", "shoe"],
    "verdict": "no",
    "blame": None,
}


class TestStylistTrainingPolicy(unittest.TestCase):
    def current(self):
        return {"yes": YES, "blamed": BLAMED_NO, "unattributed": UNATTRIBUTED_NO}

    def test_runtime_filter_keeps_only_blamed_rejections(self):
        with patch.object(closet, "stylist_current", return_value=self.current()):
            self.assertEqual(closet.blamed_rejections(), [BLAMED_NO])

    def test_yes_verdicts_do_not_create_runtime_pair_positives(self):
        with patch.object(closet, "stylist_current", return_value=self.current()):
            model = closet.stylist_compat(GARMENTS, prior=[])
        self.assertEqual(model["pair_pos"], {})
        self.assertEqual(model["type_pos"], {})
        self.assertGreater(model["pair_neg"][("shoe", "top")], 0)
        self.assertGreater(model["pair_neg"][("bottom", "shoe")], 0)

    def test_published_looks_remain_the_positive_pairwise_prior(self):
        prior = [{"garment_ids": ["top", "bottom", "shoe"]}]
        with patch.object(closet, "stylist_current", return_value=self.current()):
            model = closet.stylist_compat(GARMENTS, prior=prior)
        self.assertGreater(model["pair_pos"][("bottom", "top")], 0)
        self.assertGreater(model["pair_pos"][("shoe", "top")], 0)


if __name__ == "__main__":
    unittest.main()
