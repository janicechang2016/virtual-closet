"""Outfit enumeration and wardrobe gap analysis. Pure functions, no I/O, no API calls.

Enumeration is exhaustive over the structural shapes, not sampled: at this
closet's size the full space is small enough to walk, and an exact participation
count is what makes orphan detection trustworthy.
"""
import itertools

from . import colour, constraints, preference

# A garment appearing in this few valid outfits is functionally stranded.
ORPHAN_PARTICIPATION = 2


def _cat(garments, name):
    """Garments that can fill this slot.

    `category` is the garment's primary identity; `alt_categories` (migration
    0005) lists additional slots it may fill. 59-el-hoodie is outerwear she wears
    AS THE TOP: 3 of her first 15 logged wears were bottom + shoes + hoodie — a
    shape `hard_violations` already permits ("outerwear worn on its own IS the
    top layer") but that this enumerator never generated, so the stylist could
    never suggest one of her most-worn garments.
    """
    return [g for g in garments
            if g.get("category") == name
            or name in (g.get("alt_categories") or ())]


def enumerate_outfits(garments, with_outerwear=False):
    """Every structurally valid outfit shape: (top+bottom | dress) + shoes.

    Outerwear is off by default — including it multiplies the space by the
    number of coats and tells you little that the base outfit did not.
    """
    tops, bottoms = _cat(garments, "top"), _cat(garments, "bottom")
    dresses, shoes = _cat(garments, "dress"), _cat(garments, "shoes")
    outers = _cat(garments, "outerwear") if with_outerwear else []

    bases = [list(c) for c in itertools.product(tops, bottoms)]
    bases += [[d] for d in dresses]

    out = []
    for base in bases:
        for sh in shoes:
            combo = base + [sh]
            if constraints.is_valid(combo):
                out.append(combo)
            for ow in outers:
                # a dual-role garment cannot be its own outer layer
                if any(x["id"] == ow["id"] for x in combo):
                    continue
                combo2 = base + [sh, ow]
                if constraints.is_valid(combo2):
                    out.append(combo2)
    return out


def ranked_outfits(garments, limit=None, with_outerwear=False, affinity=None,
                   affinity_weight=0.75):
    """Valid outfits ordered best-first.

    With an `affinity` map (see engine.preference) that signal leads, because it
    is the only one measured to predict her judgement: on outfits it had never
    seen, learned affinity scored AUC 0.824 while colour harmony scored 0.491 —
    chance. Colour is kept at a small weight as a tiebreak, not a ranker.
    """
    scored = []
    for combo in enumerate_outfits(garments, with_outerwear):
        ids = [g["id"] for g in combo]
        h, worst = colour.outfit_harmony(combo)
        s, notes = constraints.score(combo, h)
        pref = None
        if affinity:
            pref = preference.outfit_preference(ids, affinity)
            s = max(0.0, affinity_weight * pref + (1.0 - affinity_weight) * s
                    - constraints.soft_notes(combo)[0] * (1.0 - affinity_weight))
        scored.append({
            "garment_ids": ids,
            "score": round(s, 4),
            "harmony": round(h, 4),
            "preference": None if pref is None else round(pref, 4),
            "notes": notes,
            "worst_pair": worst[2:] if worst else None,
            "worst_reason": worst[1] if worst else None,
        })
    scored.sort(key=lambda o: -o["score"])
    return scored[:limit] if limit else scored


def participation(garments, outfits=None):
    """How many valid outfits each garment can appear in.

    Enumerates WITH outerwear: excluding it gives every coat a participation of
    zero and reports the entire outerwear rail as orphaned, which is an artifact
    of the enumeration rather than anything true about the closet.
    """
    outfits = enumerate_outfits(garments, with_outerwear=True) if outfits is None else outfits
    counts = {g["id"]: 0 for g in garments}
    for combo in outfits:
        for g in combo:
            counts[g["id"]] += 1
    return counts


def orphans(garments, threshold=ORPHAN_PARTICIPATION):
    """Garments that combine into almost nothing.

    Two very different causes, separated here because the answers differ: a
    garment with no structural partner (the only skirt in a closet of trousers)
    versus one that partners fine but clashes with everything.
    """
    outfits = enumerate_outfits(garments, with_outerwear=True)
    counts = participation(garments, outfits)
    out = []
    for g in garments:
        n = counts[g["id"]]
        if n > threshold:
            continue
        out.append({
            "id": g["id"],
            "category": g.get("category"),
            "participation": n,
            "reason": "no structural partner" if n == 0 else "few valid partners",
        })
    return sorted(out, key=lambda o: (o["participation"], o["id"]))


def quality_participation(garments, min_score, with_outerwear=True):
    """Per garment: how many outfits containing it score at or above min_score.

    Structural participation turned out to say nothing about this closet — with
    21 tops and 10 bottoms everything pairs with everything, and the orphan list
    came back empty. What actually distinguishes a stranded garment is having no
    GOOD home, not no home.
    """
    ranked = ranked_outfits(garments, with_outerwear=with_outerwear)
    counts = {g["id"]: 0 for g in garments}
    best = {g["id"]: 0.0 for g in garments}
    for o in ranked:
        for gid in o["garment_ids"]:
            if o["score"] >= min_score:
                counts[gid] += 1
            if o["score"] > best[gid]:
                best[gid] = o["score"]
    return counts, best


GHOST_ID = "__hypothetical__"
# Swept dimensions for a hypothetical garment. COLOUR IS DELIBERATELY ABSENT.
# The plan (D.4) says "category + colour band + formality", but measured on this
# closet colour does discriminate and discriminates WRONGLY: held otherwise
# equal, a black bottom unlocks 101 good outfits against white's 208, because
# the harmony scorer rewards lightness contrast and penalises the tonal
# black-on-black that is her signature. Recommending a purchase on a signal that
# scores 0.360 against her actual wear behaviour — below chance — would be
# confident and wrong. Formality and warmth carry the discrimination honestly:
# they drive soft_notes, which is judgement about coherence, not taste.
HYPOTHETICAL_DIMS = {"formality": (1, 2, 3, 4, 5), "warmth": (1, 2, 3, 4, 5)}


def _ghost(category, formality, warmth):
    """A neutral mid-grey stand-in. The colour is fixed and arbitrary precisely
    so it cannot influence the ranking — see HYPOTHETICAL_DIMS."""
    return {
        "id": GHOST_ID, "category": category, "subcategory": "hypothetical",
        "colors": [{"lab": [50.0, 0.0, 0.0], "rgb": [128, 128, 128],
                    "name": "neutral", "coverage": 1.0}],
        "formality": formality, "warmth": warmth, "volume": "regular",
        "season_tags": [], "wear_count": 0,
    }


def hypothetical_unlocks(garments, min_score=None, categories=None,
                         with_outerwear=False):
    """D.4 steps 4-5: what a garment you do NOT own would add.

    Counted in GOOD outfits, not merely valid ones. Structural validity is
    category-only (`hard_violations` counts slots), so on validity alone every
    bottom scores identically at 220 and the recommendation collapses to "buy
    whichever category is scarcest" — arithmetic about the closet's shape, not
    advice. Scoring against a quality bar makes formality and warmth matter,
    which is the same move `quality_participation` made for stranded garments.

    `min_score` defaults to the median of the closet's own valid outfits, so the
    bar is "as good as a coin-flip outfit you could already make" rather than an
    invented constant.

    Returns rows sorted best-first. `unlocked` is the count clearing the bar;
    `valid` is the structural count, kept alongside so the difference between
    the two is visible rather than hidden.
    """
    base = ranked_outfits(garments, with_outerwear=with_outerwear)
    if min_score is None:
        scores = sorted(o["score"] for o in base)
        min_score = scores[len(scores) // 2] if scores else 0.0

    cats = categories or ("top", "bottom", "dress", "shoes")
    rows = []
    for cat in cats:
        for f in HYPOTHETICAL_DIMS["formality"]:
            for w in HYPOTHETICAL_DIMS["warmth"]:
                ranked = ranked_outfits(garments + [_ghost(cat, f, w)],
                                        with_outerwear=with_outerwear)
                mine = [o for o in ranked if GHOST_ID in o["garment_ids"]]
                if not mine:
                    continue
                rows.append({
                    "category": cat, "formality": f, "warmth": w,
                    "unlocked": sum(1 for o in mine if o["score"] >= min_score),
                    "valid": len(mine),
                    "best_score": round(max(o["score"] for o in mine), 3),
                })
    rows.sort(key=lambda r: (-r["unlocked"], r["category"], r["formality"]))
    return {"min_score": round(min_score, 3), "baseline": len(base),
            "rows": rows}


def unworn(garments, worn_outfits):
    """Garments in the closet that appear in no recorded outfit.

    Distinct from an orphan: these combine fine in theory and simply have not
    been worn — the honest input to a "why is this sitting there" question.
    """
    seen = set()
    for o in worn_outfits:
        seen.update(o.get("garment_ids") or [])
    return [g["id"] for g in garments if g["id"] not in seen]


def rediscovery(garments, worn_outfits, affinity=None, per_garment=1,
                with_outerwear=False):
    """D.5's "default to unlock, not acquire": the best outfit you already own
    for each garment you have never worn.

    This LEADS the gap report, and on this closet it is the only half with a
    true answer. Nothing here is structurally stranded — every never-worn
    garment already sits in 60 to 2,220 valid outfits — so the idle value is a
    wearing problem, not a combinatorics one, and a purchase recommendation
    would be answering a question the data never asked.

    Ranked by learned affinity when supplied, since that is what measured 0.824
    against her stated verdicts; colour harmony alone measured at chance.
    """
    unworn_ids = set(unworn(garments, worn_outfits))
    if not unworn_ids:
        return []
    out, seen = [], {}

    def collect(ranked):
        for o in ranked:                   # already best-first
            for gid in o["garment_ids"]:
                if gid not in unworn_ids or seen.get(gid, 0) >= per_garment:
                    continue
                seen[gid] = seen.get(gid, 0) + 1
                out.append({
                    "id": gid,
                    "outfit": list(o["garment_ids"]),
                    "score": round(o["score"], 3),
                    "partners": [x for x in o["garment_ids"] if x != gid],
                })

    collect(ranked_outfits(garments, affinity=affinity,
                           with_outerwear=with_outerwear))
    # A never-worn COAT would otherwise get no suggestion at all: the enumerator
    # omits outerwear by default, so an outerwear garment appears in no outfit
    # and silently drops out of the report — the one kind of garment most likely
    # to sit unworn. Retry just the ones still missing with the layer allowed.
    missing = unworn_ids - set(seen)
    if missing:
        collect(ranked_outfits(garments, affinity=affinity, with_outerwear=True))
    return sorted(out, key=lambda r: -r["score"])


def cost_per_wear(garments, worn_outfits):
    """Price divided by recorded appearances. None where price is unknown.

    Appearances come from published looks, so this is a floor, not the truth —
    it counts what was recorded, not what was worn.
    """
    counts = {}
    for o in worn_outfits:
        for gid in (o.get("garment_ids") or []):
            counts[gid] = counts.get(gid, 0) + 1
    out = []
    for g in garments:
        price = (g.get("purchase") or {}).get("price_usd")
        if price is None:
            continue
        n = counts.get(g["id"], 0)
        out.append({
            "id": g["id"],
            "price_usd": float(price),
            "wears": n,
            "cost_per_wear": None if n == 0 else round(float(price) / n, 2),
        })
    return sorted(out, key=lambda r: (r["wears"], -r["price_usd"]))
