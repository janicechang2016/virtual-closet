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
VERDICT_WEIGHT = 1.5   # an explicit yes/no is worth slightly more — it is direct

# A single disliked garment sinks an outfit; a good average does not rescue it.
# This is the loafer case: everything else fine, still would not wear it.
MIN_WEIGHT = 0.5


def affinity(garments, looks=(), verdicts=()):
    """Per-garment affinity in 0..1. 0.5 = no evidence either way.

    `looks`    : iterable of {"garment_ids": [...]} she published
    `verdicts` : iterable of ({"ids": [...]}, "yes"/"no")
    """
    pos = {g["id"]: 0.0 for g in garments}
    neg = {g["id"]: 0.0 for g in garments}

    for lk in looks:
        for gid in (lk.get("garment_ids") or []):
            if gid in pos:
                pos[gid] += LOOK_WEIGHT

    for entry, verdict in verdicts:
        bucket = pos if verdict == "yes" else neg
        for gid in (entry.get("ids") or []):
            if gid in bucket:
                bucket[gid] += VERDICT_WEIGHT

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
