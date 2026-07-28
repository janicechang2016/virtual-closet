"""Validation for wear context (migration 0006). Stdlib unittest, no database.

The pure functions in `app.wear` are tested here; the SQL round trip is covered
by the migration's own acceptance query and the end-to-end run against
production. What matters most is the SWAP DIRECTION: `instead_of` must be a
garment she wore and `nearly_wore` one she did not. Reversed, the pair teaches
the model the exact opposite of what happened, and reversing it is two taps on a
phone at the end of a day.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app import wear_rules as wear  # noqa: E402

WORN = ["25-kotn-samira-tank", "02-jeans", "52-camper-flats"]


class TestOccasion(unittest.TestCase):
    def test_known_slug_passes(self):
        self.assertEqual(wear.clean_occasion("work_home"), "work_home")

    def test_blank_is_none_not_an_error(self):
        """Context is optional — a wear must never be lost for want of it."""
        self.assertIsNone(wear.clean_occasion(""))
        self.assertIsNone(wear.clean_occasion(None))

    def test_unknown_slug_rejected(self):
        with self.assertRaises(wear.WearError):
            wear.clean_occasion("brunch")

    def test_display_text_is_not_a_slug(self):
        """The page sends slugs. If it ever sends a label, fail loudly."""
        with self.assertRaises(wear.WearError):
            wear.clean_occasion("work — from home")

    def test_vocabulary_matches_the_migration(self):
        self.assertEqual(
            set(wear.OCCASIONS),
            {"work_home", "work_out", "day_out", "dinner", "event", "home"})


class TestSwap(unittest.TestCase):
    def test_valid_swap(self):
        self.assertEqual(
            wear.clean_swap("54-salomon-sneakers", "52-camper-flats", WORN),
            ("54-salomon-sneakers", "52-camper-flats"))

    def test_absent_swap_is_fine(self):
        self.assertEqual(wear.clean_swap(None, None, WORN), (None, None))
        self.assertEqual(wear.clean_swap("", "", WORN), (None, None))

    def test_half_a_swap_is_rejected(self):
        """One half is not a comparison — the value is that the two are matched."""
        with self.assertRaises(wear.WearError):
            wear.clean_swap("54-salomon-sneakers", None, WORN)
        with self.assertRaises(wear.WearError):
            wear.clean_swap(None, "52-camper-flats", WORN)

    def test_reversed_swap_is_rejected(self):
        """THE failure mode this validation exists for.

        Sending the worn garment as `nearly_wore` would record a true negative
        with its sign flipped — worse than collecting nothing.
        """
        with self.assertRaises(wear.WearError):
            wear.clean_swap("52-camper-flats", "54-salomon-sneakers", WORN)

    def test_instead_of_must_have_been_worn(self):
        with self.assertRaises(wear.WearError):
            wear.clean_swap("54-salomon-sneakers", "49-jil-sander-boots", WORN)

    def test_nearly_wore_must_not_have_been_worn(self):
        with self.assertRaises(wear.WearError):
            wear.clean_swap("02-jeans", "52-camper-flats", WORN)

    def test_garment_cannot_be_its_own_alternative(self):
        with self.assertRaises(wear.WearError):
            wear.clean_swap("52-camper-flats", "52-camper-flats", WORN)


if __name__ == "__main__":
    unittest.main()
