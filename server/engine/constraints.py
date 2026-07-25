"""Outfit validity rules. Pure functions, deterministic, no I/O, no API calls.

Two tiers, kept strictly apart:

  HARD  — structural. An outfit that fails is not an outfit (no shoes; two
          bottoms; a dress worn with a skirt). These filter.
  SOFT  — judgement. Formality spread, warmth coherence, proportion. These
          score, never filter, because they are exactly the calls the user
          overrules — and the standing rule is that she decides aesthetics.

Getting that boundary wrong is how a stylist ends up refusing to suggest the
outfit its owner actually wears.
"""

CATEGORIES = ("top", "bottom", "dress", "outerwear", "shoes")

# Warmth spread inside one outfit. A 1 with a 5 is a coat over a camisole —
# possible, but worth flagging rather than silently ranking as coherent.
WARMTH_SPREAD_OK = 2
FORMALITY_SPREAD_OK = 2


def by_category(garments):
    out = {c: [] for c in CATEGORIES}
    for g in garments:
        out.setdefault(g.get("category"), []).append(g)
    return out


def hard_violations(garments):
    """Structural failures. Empty list means it is a wearable outfit."""
    cats = by_category(garments)
    v = []

    n_top, n_bottom = len(cats["top"]), len(cats["bottom"])
    n_dress, n_shoes = len(cats["dress"]), len(cats["shoes"])

    if n_dress:
        if n_dress > 1:
            v.append("two dresses")
        if n_bottom:
            v.append("dress worn with a bottom")
        # A top over a dress is a real styling move, so it is NOT a violation.
    else:
        # Outerwear worn on its own IS the top layer — a zipped hoodie or a
        # jacket over nothing else. Her own look-023 (hoodie + trousers +
        # sneakers) is exactly this, and an earlier version of this rule
        # rejected it. When the closet's own history fails a rule, the rule is
        # what is wrong.
        if not n_top and not cats["outerwear"]:
            v.append("no top")
        if not n_bottom:
            v.append("no bottom")

    if n_bottom > 1:
        v.append("two bottoms")
    if not n_shoes:
        v.append("no shoes")
    if n_shoes > 1:
        v.append("two pairs of shoes")
    if len(cats["outerwear"]) > 1:
        v.append("two outerwear pieces")
    return v


def is_valid(garments):
    return not hard_violations(garments)


def _spread(values):
    vals = [v for v in values if v is not None]
    return (max(vals) - min(vals)) if vals else 0


def soft_notes(garments):
    """Judgement calls. Returns (penalty 0..1, notes). Never filters."""
    notes = []
    penalty = 0.0

    f_spread = _spread([g.get("formality") for g in garments])
    if f_spread > FORMALITY_SPREAD_OK:
        penalty += 0.12 * (f_spread - FORMALITY_SPREAD_OK)
        notes.append("formality spread %d" % f_spread)

    # Warmth is judged on the body layers only. Shoes have their own logic —
    # boots are warm, but a boot with a summer dress is a deliberate look, not
    # an incoherent one.
    body = [g for g in garments if g.get("category") != "shoes"]
    w_spread = _spread([g.get("warmth") for g in body])
    if w_spread > WARMTH_SPREAD_OK:
        penalty += 0.10 * (w_spread - WARMTH_SPREAD_OK)
        notes.append("warmth spread %d" % w_spread)

    # Proportion: volume on volume loses the silhouette. This is the softest
    # rule here and the one most likely to be overruled.
    volumes = [g.get("volume") for g in garments
               if g.get("category") in ("top", "bottom", "dress")]
    if volumes.count("oversized") >= 2:
        penalty += 0.15
        notes.append("oversized on oversized")

    return min(penalty, 1.0), notes


def season_of(garments):
    """Seasons every body layer agrees on — empty means the outfit spans none."""
    body = [g for g in garments if g.get("category") != "shoes"]
    sets = [set(g.get("season_tags") or []) for g in body if g.get("season_tags")]
    if not sets:
        return set()
    out = sets[0]
    for s in sets[1:]:
        out &= s
    return out


def score(garments, harmony_score):
    """Combine harmony with the soft rules into one ranking number, 0..1."""
    penalty, notes = soft_notes(garments)
    return max(0.0, harmony_score - penalty), notes
