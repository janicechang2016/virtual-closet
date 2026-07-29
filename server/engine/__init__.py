"""The engine — all pure functions, $0, no I/O, unit-tested against the real
58-garment / 18-look closet.

  constraints.py  completeness rules + warmth/formality banding, three tiers:
                  HARD (structural) · USER (her written rules) · SOFT (judgement)
  colour.py       LAB conversion, neutral detection, harmony scoring (invariant #6)
  gaps.py         outfit enumeration, participation counting, orphan detection
  preference.py   learned PER-GARMENT affinity — what ranks /stylist today
  pairwise.py     learned PER-PAIR compatibility — the shape a scalar cannot hold

Read `preference.py` and `pairwise.py` together: they are two answers to the same
question, and `server/scripts/wear_model_report.py` is what adjudicates between
them. Colour is a low-weight tiebreak in both worlds — measured at chance against
her stated verdicts and BELOW chance against her actual wears.
"""
