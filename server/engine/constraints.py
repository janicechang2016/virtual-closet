"""Outfit validity rules. Pure functions, deterministic, no I/O, no API calls.

Three tiers, kept strictly apart:

  HARD  — structural. An outfit that fails is not an outfit (no shoes; two
          bottoms; a dress worn with a skirt). These filter.
  USER  — her own directives, from `server/scripts/style_rules.txt`. These
          filter too, but only what the stylist SUGGESTS. See below.
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


# ---------------------------------------------------------------- user rules

# Her rules live in prose in `server/scripts/style_rules.txt`, which is the
# source of truth and which NOTHING regenerates. The two that are executable are
# hand-translated here, with her sentence quoted verbatim so any drift between
# the two is visible on sight. This file deliberately does NOT parse that one:
# it is her authored document, and the D.1 lesson was that round-tripping a
# user's words through a parser eats them.
#
# WHY THIS IS A SEPARATE TIER AND NOT A HARD RULE — measured 07-28, not assumed.
# Checked against all 57 outfits in the closet: zero WORN outfits break either
# rule, but TWO PUBLISHED LOOKS do (both `32-personal-language-skirt` with
# `53-keen-sandals`), and neither of those two was ever worn. Folding these into
# `hard_violations` would retroactively declare two of her own published looks
# structurally invalid — the exact failure this module's header warns about, and
# the one that already bit look-023. Published-but-never-worn is precisely the
# gap the 07-27 pivot identified, so her rule is a correction to what gets
# SUGGESTED, not a claim that those looks were never outfits.
#
# Consequence, stated so it is not read as an oversight: the affinity prior is
# untouched. Those two looks still train `preference.affinity()` — they are real
# evidence about tops and skirts, and the rule is about the shoe.

# Keyed by ID, not by `subcategory == "sandal"`, because her rule names this
# specific shoe. It is the only sandal in the closet today, so the two are
# indistinguishable now — but a future sandal must not silently inherit a rule
# she wrote about her Keens.
KEEN_SANDALS = "53-keen-sandals"

#: Rules take (garments, occasion). `occasion` is an OCCASION SLUG from
#: `app.wear_rules.OCCASIONS`, or None when the caller has no context — and None
#: must mean "cannot violate an occasion rule", never "assume the worst".
#: Suggestions are made for a specific occasion or for none at all, and
#: silently applying a dinner rule to an unspecified request would filter the
#: general pool on a premise nobody stated.
USER_RULES = (
    # "Never suggest a sneaker with a skirt or dress."
    ("sneaker with a skirt or dress",
     lambda gs, occ: (_any_sub(gs, "sneaker") and _any_skirt_or_dress(gs))),
    # "Keen sandals are for extremely casual and walking days only. Never
    #  suggest them with a skirt or dress."
    ("keen sandals with a skirt or dress",
     lambda gs, occ: (any(g.get("id") == KEEN_SANDALS for g in gs)
                      and _any_skirt_or_dress(gs))),
    # "Never suggest a sneaker for dinner." — added 07-28 from the wear data,
    # confirmed by her. Of her 6 logged dinners, 5 were the yello-heels and one
    # was flats; sneakers were worn 5 times and NEVER to dinner. This is the
    # first rule derived from what she DID rather than from what she said, which
    # is exactly the target the stylist was re-pointed at on 07-27.
    # CAVEAT, recorded so it can be undone honestly: n=6 dinners. It is enforced
    # because she confirmed it, not because 6 is a sample. Delete this tuple and
    # its test to remove it — nothing else references it.
    ("sneaker for dinner",
     lambda gs, occ: occ == "dinner" and _any_sub(gs, "sneaker")),
)


def _any_sub(garments, sub):
    return any(g.get("subcategory") == sub for g in garments)


def _any_skirt_or_dress(garments):
    # A skirt is a `bottom` with subcategory "skirt"; a dress is its own
    # category. Both halves are needed — neither field alone finds both.
    return any(g.get("category") == "dress" or g.get("subcategory") == "skirt"
               for g in garments)


#: The stylist's occasion tabs come from the PUBLISHED LOOKS' free-text
#: vocabulary; wear logging uses the 0006 slugs. They are two vocabularies for
#: one idea, and `dinner` happens to be spelled identically in both — relying on
#: that coincidence is how the live route and the deployed pool drifted apart on
#: 07-27, so the mapping is written down instead.
#:
#: `work` maps to NOTHING on purpose: a look tagged "work" does not say whether
#: it was worn from home or in an office, and 0006 split those precisely because
#: the difference matters. Guessing would put a rule on a premise she never
#: stated.
OCCASION_ALIASES = {
    "day out": "day_out",
    "dinner": "dinner",
    "event / formal": "event",
    "home / lounge": "home",
}


def normalise_occasion(value):
    """Display label or slug -> slug, or None if it cannot be resolved."""
    if not value:
        return None
    if value in OCCASION_ALIASES:
        return OCCASION_ALIASES[value]
    # already a slug? only accept ones a rule could reference
    known = {slug for _, slug in OCCASION_ALIASES.items()} | {"work_home", "work_out"}
    return value if value in known else None


def user_rule_violations(garments, occasion=None):
    """Her directives. Empty list means the stylist may suggest this outfit.

    Filters suggestions only. Never call this to decide whether something IS an
    outfit — that is `hard_violations`.

    `occasion` is optional and defaults to None, which cannot violate an
    occasion-scoped rule. A caller with no occasion is asking a general
    question, and answering it with dinner's constraints would filter the pool
    on a premise nobody stated.
    """
    return [name for name, breaks in USER_RULES if breaks(garments, occasion)]


def allowed_by_user_rules(garments, occasion=None):
    return not user_rule_violations(garments, occasion)


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
