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
    return [g for g in garments if g.get("category") == name]


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


def unworn(garments, worn_outfits):
    """Garments in the closet that appear in no recorded outfit.

    Distinct from an orphan: these combine fine in theory and simply have not
    been worn — the honest input to a "why is this sitting there" question.
    """
    seen = set()
    for o in worn_outfits:
        seen.update(o.get("garment_ids") or [])
    return [g["id"] for g in garments if g["id"] not in seen]


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
