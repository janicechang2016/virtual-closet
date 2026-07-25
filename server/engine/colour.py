"""Colour reasoning in LAB. Pure functions, deterministic, no I/O, no API calls.

Everything downstream consumes LAB because that is what the closet stores
(invariant #6) and because perceptual distance is meaningful there in a way it
is not in RGB. Colour NAMES are never used for reasoning — they are UI labels
and have already proved unreliable (a garment black measures L*~15-22, and
naming it correctly took two rounds of anchor calibration).
"""
import math

# Below this chroma a colour reads as neutral. Black, white, grey, greige,
# oatmeal and most of this closet's palette sit here — which matters, because
# neutrals combine with everything and dominate the wardrobe.
NEUTRAL_CHROMA = 14.0

# Hue windows, degrees. Deliberately wide: garment colour is not a paint chip,
# and the measured hue of a shadowed fabric wanders several degrees.
MONOCHROME_DH = 20.0
ANALOGOUS_DH = 55.0
COMPLEMENTARY_LO = 150.0
COMPLEMENTARY_HI = 210.0

# The awkward zone: far enough apart to read as a mismatch, not far enough to
# read as contrast. Starts where analogous ends — the branches are checked in
# order, so a lower bound below ANALOGOUS_DH would simply never be reached.
DISCORD_LO = ANALOGOUS_DH
DISCORD_HI = 90.0


def chroma(lab):
    """Distance from the neutral axis. 0 = pure grey."""
    return math.hypot(lab[1], lab[2])


def hue_angle(lab):
    """Hue in degrees, 0-360. Meaningless for near-neutrals — guard with is_neutral."""
    return math.degrees(math.atan2(lab[2], lab[1])) % 360.0


def is_neutral(lab):
    return chroma(lab) < NEUTRAL_CHROMA


def delta_e(a, b):
    """CIE76. Crude next to CIEDE2000, but adequate and cheap for ranking."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def hue_delta(a, b):
    """Smallest angle between two hues, 0-180."""
    d = abs(hue_angle(a) - hue_angle(b)) % 360.0
    return 360.0 - d if d > 180.0 else d


def lightness_delta(a, b):
    return abs(a[0] - b[0])


def pair_harmony(lab_a, lab_b):
    """Score a colour pair in 0..1 with the reason. Deterministic.

    Neutrals score high on purpose: this closet is overwhelmingly black, greige
    and oatmeal, so a rule that penalised them would reject most of the wardrobe.
    """
    na, nb = is_neutral(lab_a), is_neutral(lab_b)

    if na and nb:
        # Two neutrals. Separation in lightness is what makes it read as
        # deliberate rather than a near-miss — black with cream, not black with
        # charcoal-that-was-meant-to-match.
        dl = lightness_delta(lab_a, lab_b)
        if dl < 8:
            return 0.82, "neutral, matched"
        if dl < 25:
            return 0.74, "neutral, slight mismatch"
        return 0.90, "neutral contrast"

    if na or nb:
        # One neutral anchoring one colour is the safest combination there is.
        return 0.88, "neutral-anchored"

    dh = hue_delta(lab_a, lab_b)
    if dh <= MONOCHROME_DH:
        return 0.86, "monochrome"
    if dh <= ANALOGOUS_DH:
        return 0.80, "analogous"
    if COMPLEMENTARY_LO <= dh <= COMPLEMENTARY_HI:
        return 0.72, "complementary"
    if DISCORD_LO < dh < DISCORD_HI:
        return 0.38, "discordant"
    return 0.55, "unrelated"


def dominant(colors, min_coverage=0.0):
    """The LAB entries of a garment's palette, most-covering first."""
    out = [c for c in (colors or []) if c.get("coverage", 0) >= min_coverage]
    out.sort(key=lambda c: -c.get("coverage", 0))
    return [c["lab"] for c in out]


def garment_harmony(colors_a, colors_b):
    """Harmony between two garments, weighted by how much of each colour shows.

    Only the top two colours per garment participate: a 4% print accent should
    tint the judgement, not decide it.
    """
    a = (colors_a or [])[:2]
    b = (colors_b or [])[:2]
    if not a or not b:
        return 0.5, "unknown"

    total, acc, best_reason, best = 0.0, 0.0, "unknown", -1.0
    for ca in a:
        for cb in b:
            w = ca.get("coverage", 0) * cb.get("coverage", 0)
            s, reason = pair_harmony(ca["lab"], cb["lab"])
            acc += s * w
            total += w
            if s > best:
                best, best_reason = s, reason
    return (acc / total if total else 0.5), best_reason


def outfit_harmony(garments):
    """Mean pairwise harmony across an outfit. Returns (score, worst_pair).

    The mean is what ranks; the worst pair is what explains. Shoes are included —
    they are a colour decision like any other.
    """
    pairs = []
    for i in range(len(garments)):
        for j in range(i + 1, len(garments)):
            s, reason = garment_harmony(garments[i].get("colors"),
                                        garments[j].get("colors"))
            pairs.append((s, reason, garments[i]["id"], garments[j]["id"]))
    if not pairs:
        return 1.0, None
    score = sum(p[0] for p in pairs) / len(pairs)
    return score, min(pairs, key=lambda p: p[0])
