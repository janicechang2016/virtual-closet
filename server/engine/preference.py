"""Learned per-garment preference. Pure functions, deterministic, no I/O.

Colour theory ranked her blind verdicts at AUC 0.42 — worse than a coin flip,
because it was measuring the wrong thing. What actually separated "would wear"
from "would not" was WHICH GARMENTS were in the outfit, footwear above all:
camper flats 92% accepted, weejuns loafers 0%, on outfits whose colour logic was
otherwise identical. No colour rule can express that, and no amount of retuning
one will.

So preference is learned rather than legislated. Evidence:
  * her published looks — she assembled and published them, which is a strong
    positive signal per garment
  * explicit verdicts from the calibration set — positive and negative

Smoothed so a garment seen twice cannot outrank one seen twenty times, and so
garments with no evidence sit at neutral instead of zero.
"""

PRIOR_STRENGTH = 2.0   # Beta(a,a): how much evidence before affinity moves off 0.5
LOOK_WEIGHT = 1.0      # a published look is one positive observation per garment
VERDICT_WEIGHT = 1.5   # an explicit yes is worth slightly more — it is direct

# Negatives are COLLECTED but not applied. Measured twice, on independent data:
# the 42-outfit blind calibration (unattributed) and 70 stylist judgements (all
# attributed). Both say rejections hurt, and the stylist sweep is monotone —
# ignore 0.638, 1x 0.605, 2x 0.577.
#
# The likely reason is that a rejection is contextual, not absolute. She blamed
# the keen sandals six times, but that means "wrong shoe for THIS outfit", not
# "I dislike these sandals" — and a per-garment scalar cannot hold the
# difference, so the model concludes she hates most of her shoes. Attribution
# was still worth building: it lifted rejections from actively inverted (0.386)
# to roughly neutral. The blame data is the raw material for a pairwise
# compatibility model, which is what it actually encodes.
NEGATIVE_WEIGHT = 0.0

# A single disliked garment sinks an outfit; a good average does not rescue it.
# This is the loafer case: everything else fine, still would not wear it.
MIN_WEIGHT = 0.5


def affinity(garments, looks=(), verdicts=(), negative_weight=None):
    """Per-garment affinity in 0..1. 0.5 = no evidence either way.

    `looks`    : iterable of {"garment_ids": [...]} she published
    `verdicts` : iterable of ({"ids": [...]}, "yes"/"no")
    `negative_weight` : multiplier on rejections; defaults to NEGATIVE_WEIGHT
                        (0.0 — see the note there, this is measured, not a guess)
    """
    negative_weight = (NEGATIVE_WEIGHT if negative_weight is None
                       else negative_weight)
    pos = {g["id"]: 0.0 for g in garments}
    neg = {g["id"]: 0.0 for g in garments}

    for lk in looks:
        for gid in (lk.get("garment_ids") or []):
            if gid in pos:
                pos[gid] += LOOK_WEIGHT

    for entry, verdict in verdicts:
        weight = VERDICT_WEIGHT if verdict == "yes" else VERDICT_WEIGHT * negative_weight
        if not weight:
            continue
        bucket = pos if verdict == "yes" else neg
        for gid in (entry.get("ids") or []):
            if gid in bucket:
                bucket[gid] += weight

    out = {}
    for gid in pos:
        a, b = pos[gid], neg[gid]
        out[gid] = (a + PRIOR_STRENGTH / 2.0) / (a + b + PRIOR_STRENGTH)
    return out


def outfit_preference(garment_ids, aff):
    """Blend of mean and minimum affinity.

    Mean alone lets three loved garments carry one she will not wear; minimum
    alone makes every outfit hostage to its weakest item. The blend reproduces
    what her verdicts actually show.
    """
    vals = [aff.get(gid, 0.5) for gid in garment_ids]
    if not vals:
        return 0.5
    mean = sum(vals) / len(vals)
    return (1.0 - MIN_WEIGHT) * mean + MIN_WEIGHT * min(vals)


def evidence_counts(garments, looks=(), verdicts=()):
    """How much evidence backs each garment — affinity without it is a guess."""
    n = {g["id"]: 0 for g in garments}
    for lk in looks:
        for gid in (lk.get("garment_ids") or []):
            if gid in n:
                n[gid] += 1
    for entry, _ in verdicts:
        for gid in (entry.get("ids") or []):
            if gid in n:
                n[gid] += 1
    return n
