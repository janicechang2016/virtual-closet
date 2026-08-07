"""The Stylist -> fitting-room cache path. Stdlib unittest, no API calls.

The paid route is intentionally outside these tests. These checks establish
that an exact prior front render can be found without a look record, that the
newest front wins, and that archive-only poses and hidden/raw files never reach
the fitting-room mirror.
"""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "virtual-closet", "scripts"))

import closet_server as closet  # noqa: E402


GARMENTS = [
    {"id": "01-plain-tee"},
    {"id": "02-jeans"},
    {"id": "52-camper-flats"},
]


class TestOutfitRenderCache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "renders").mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def render(self, name):
        (self.root / "renders" / name).write_bytes(b"fixture")

    def index(self):
        with patch.object(closet, "ROOT", self.root):
            return closet.outfit_render_index(GARMENTS)

    def test_unsaved_exact_set_is_indexed(self):
        self.render("outfit_01+02+52_1.png")
        self.assertEqual(
            self.index()["01-plain-tee,02-jeans,52-camper-flats"],
            "/assets/renders/outfit_01+02+52_1.png",
        )

    def test_newest_front_render_wins(self):
        self.render("outfit_01+02+52_2.png")
        self.render("outfit_01+02+52_10.png")
        self.assertEqual(
            self.index()["01-plain-tee,02-jeans,52-camper-flats"],
            "/assets/renders/outfit_01+02+52_10.png",
        )

    def test_pose_raw_hidden_and_unknown_families_are_excluded(self):
        self.render("outfit_01+02+52_1_raw.png")
        self.render("outfit_01+02+52_contrapposto_2.png")
        self.render("outfit_01+02+52_3.png")
        self.render("outfit_01+99_1.png")
        (self.root / "renders" / "hidden.json").write_text(
            json.dumps(["outfit_01+02+52_3"])
        )
        self.assertEqual(self.index(), {})

    def test_stage_render_and_index_choose_the_same_front(self):
        self.render("outfit_01+02+52_4.png")
        with patch.object(closet, "ROOT", self.root):
            staged = closet.stage_render(
                ["52-camper-flats", "01-plain-tee", "02-jeans"]
            )
            indexed = closet.outfit_render_index(GARMENTS)
        self.assertEqual(
            staged,
            indexed["01-plain-tee,02-jeans,52-camper-flats"],
        )


if __name__ == "__main__":
    unittest.main()
