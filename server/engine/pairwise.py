"""Pairwise garment compatibility. Pure functions, deterministic, no I/O.

WHY THIS EXISTS, when `preference.affinity` already ranks. That model scores
each garment on its own and has now been measured to its ceiling: 0.824 against
her STATED verdicts but 0.652 against what she actually WEARS, and 0.548 once
garment rotation is controlled for — a CI spanning chance. The diagnosis has
been identical every time the question has been asked (unattributed rejections
07-25, attributed rejections 07-26, wear frequency 07-27): a per-garment scalar
cannot hold context. She blamed `53-keen-sandals` six times and accepted it
four. The sandals are not the problem; the PAIRING is.

The blame data is a pairwise record and has never been read as one. A rejection
naming the Keens in an outfit with a skirt is evidence about (Keens, skirt). It
says nothing bad about the skirt — which is exactly why crediting or penalising
either garment alone destroys the finding, and why `NEGATIVE_WEIGHT = 0.0` had
to be the answer for a scalar model. Here the negative finally has somewhere to
go.

TWO LEVELS, because garment pairs are sparse and honesty about that matters.
58 garments make 1653 pairs; the evidence covers ~180 of them, and 28 of the 46
pairs in the worn test set have NO garment-level evidence at all. A model that
returned neutral for those would be reporting mostly prior. So a pair falls back
to its TYPE pair (subcategory x subcategory) rather than to 0.5 — which is also
the level her own rules are written at ("never a sneaker with a skirt or
dress"), and the level D.1 found the signal at (29 of 44 rejections blame a
shoe, and sneakers were never worn with a skirt).

The backoff is hierarchical shrinkage, not a switch: the type score IS the prior
mean for the garment pair, so a pair with no evidence returns its type's score
and a pair with plenty overrides it. One formula, no threshold to tune.

WHAT THIS MODULE DOES NOT DO: rank on its own authority. It is a scorer;
`wear_model_report.py` is what says whether it earns a place in the stylist.
"""

PAIR_PRIOR = 2.0       # Beta(a,a) strength: evidence needed to leave the type prior
TYPE_PRIOR = 2.0       # same, for the type level backing onto 0.5
LOOK_WEIGHT = 1.0      # she assembled and published it — every pair in it held
VERDICT_WEIGHT = 1.5   # an explicit "would wear" is direct evidence about pairs
BLAME_WEIGHT = 1.5     # a blamed rejection is a real negative on the pairs it names

# One bad pair sinks an outfit; a good average does not rescue it. Same doctrine
# as `preference.outfit_preference`, and for the same reason — this is the
# loafer case restated at the pair level.
MIN_WEIGHT = 0.5


def pairs(ids):
    """Unordered pairs, each as a sorted tuple. Order in never matters."""
    s = sorted(set(ids))
    return [(s[i], s[j]) for i in range(len(s)) for j in range(i + 1, len(s))]


def type_of(garment):
    """The backoff key. `subcategory` where it exists, else `category`.

    Deliberately NOT colour: colour measures 0.360 against her real wears, below
    chance, and a backoff keyed on it would launder that failure into a model
    that looks new.
    """
    return (garment.get("subcategory") or garment.get("category") or "?")


def compatibility(garments, looks=(), verdicts=()):
    """Learn pair compatibility. Returns a plain dict — data, not an object.

    `looks`    : iterable of {"garment_ids": [...]} — published looks, or worn
                 outfits if a caller decides those should train it. This module
                 takes no view on that; the harness measures it.
    `verdicts` : iterable of stylist log entries as `stylist_current()` yields
                 them — {"ids": [...], "verdict": "yes"/"no", "blame": id|None}.
                 A "no" WITHOUT a blame is dropped, not smeared: that is the
                 07-25 finding and it has not been repealed.

    Note what a rejection does NOT do. Only the pairs naming the blamed garment
    are penalised; the pairs among the OTHER garments get nothing at all —
    neither credit nor blame. Crediting them would invent a positive out of an
    outfit she turned down, and penalising them is the smearing that made
    prediction worse twice.
    """
    types = {g["id"]: type_of(g) for g in garments}
    known = set(types)
    pair_pos, pair_neg = {}, {}
    type_pos, type_neg = {}, {}

    def add(a, b, weight, positive):
        pbucket = pair_pos if positive else pair_neg
        tbucket = type_pos if positive else type_neg
        key = (a, b) if a < b else (b, a)
        pbucket[key] = pbucket.get(key, 0.0) + weight
        ta, tb = types[a], types[b]
        tkey = (ta, tb) if ta <= tb else (tb, ta)
        tbucket[tkey] = tbucket.get(tkey, 0.0) + weight

    for lk in looks:
        ids = [g for g in (lk.get("garment_ids") or []) if g in known]
        for a, b in pairs(ids):
            add(a, b, LOOK_WEIGHT, True)

    for e in verdicts:
        ids = [g for g in (e.get("ids") or []) if g in known]
        verdict = e.get("verdict")
        if verdict == "yes":
            for a, b in pairs(ids):
                add(a, b, VERDICT_WEIGHT, True)
        elif verdict == "no":
            blame = e.get("blame")
            if not blame or blame not in known:
                continue
            for other in ids:
                if other != blame:
                    add(blame, other, BLAME_WEIGHT, False)

    return {
        "types": types,
        "pair_pos": pair_pos, "pair_neg": pair_neg,
        "type_pos": type_pos, "type_neg": type_neg,
    }


def type_score(model, ta, tb):
    """Compatibility of two TYPES, shrunk toward 0.5."""
    key = (ta, tb) if ta <= tb else (tb, ta)
    p = model["type_pos"].get(key, 0.0)
    n = model["type_neg"].get(key, 0.0)
    return (p + TYPE_PRIOR / 2.0) / (p + n + TYPE_PRIOR)


def pair_score(model, a, b):
    """Compatibility of two GARMENTS, shrunk toward their type pair's score."""
    types = model["types"]
    if a not in types or b not in types:
        return 0.5
    prior = type_score(model, types[a], types[b])
    key = (a, b) if a < b else (b, a)
    p = model["pair_pos"].get(key, 0.0)
    n = model["pair_neg"].get(key, 0.0)
    return (p + PAIR_PRIOR * prior) / (p + n + PAIR_PRIOR)


def outfit_compatibility(garment_ids, model):
    """Blend of mean and worst pair. A single bad pairing is disqualifying."""
    ps = [pair_score(model, a, b) for a, b in pairs(garment_ids)]
    if not ps:
        return 0.5
    mean = sum(ps) / len(ps)
    return (1.0 - MIN_WEIGHT) * mean + MIN_WEIGHT * min(ps)


def rank_calibrator(model, space):
    """A scorer that ranks an outfit WITHIN ITS OWN pair-count class, 0..1.

    WHY THIS IS PART OF THE MODEL AND NOT A GARNISH. Outfits with different
    numbers of pairs are not comparable under a mean/min blend: a two-item
    outfit (dress + shoes) has exactly ONE pair, so its mean and its minimum are
    the same number and nothing can drag it down, while a three-item outfit is
    always judged by its weakest of three. Raw, the model therefore put a DRESS
    in 10 of the top 12 — and dresses are 5% of the space, appear in 1 of her 15
    wears, and are the garments her own rules call event pieces for events she
    has not had.

    AUC did not catch it, and could not: dress outfits are 120 of 2320, so
    floating all of them costs almost nothing on a rank statistic while the
    ordering that matters stays right. **A ranking model has to be looked at,
    not only scored** — the number was 0.809 while the top of the list was
    unusable.

    Percentile rank is monotone inside each class, so this changes no
    within-class ordering and no within-class AUC. It only makes the classes
    comparable to each other. Measured: top-12 dress share 10/12 -> 0/12, and
    AUC 0.809 -> 0.814 whole, 0.795 -> 0.794 in-rotation.

    `space` is the candidate pool to calibrate against — pass the same
    enumeration the suggestions are drawn from.
    """
    import bisect

    tables = {}
    for combo in space:
        ids = list(combo)
        tables.setdefault(len(ids), []).append(outfit_compatibility(ids, model))
    for key in tables:
        tables[key].sort()

    def score(garment_ids):
        ids = list(garment_ids)
        raw = outfit_compatibility(ids, model)
        table = tables.get(len(ids))
        if not table:                      # a size the pool never contained
            table = max(tables.values(), key=len) if tables else None
        if not table or len(table) < 2:
            return raw
        return bisect.bisect_left(table, raw) / float(len(table) - 1)

    return score


def worst_pair(garment_ids, model):
    """The pair dragging an outfit down, for explaining a ranking to her.

    Returns (a, b, score) or None. The stylist already says "built around your
    samira draped tank"; this is the material for the opposite sentence.
    """
    ps = [(pair_score(model, a, b), a, b) for a, b in pairs(garment_ids)]
    if not ps:
        return None
    s, a, b = min(ps)
    return (a, b, s)


def pair_evidence(model, a, b):
    """(positive, negative) weight recorded for this exact pair of garments.

    GARMENT LEVEL ONLY, deliberately — this answers "what have I seen HER do
    with these two", not "what do I infer". The type backoff is inference and
    belongs in the score, not in a sentence claiming she did something.
    """
    key = (a, b) if a < b else (b, a)
    return (model["pair_pos"].get(key, 0.0), model["pair_neg"].get(key, 0.0))


# What an outfit's evidence looks like. Ordered by how much it should be said:
# a pairing she has REJECTED outranks one she has never tried, which outranks
# an outfit made entirely of pairings she has already put together.
EVIDENCE_REJECTED = "rejected"
EVIDENCE_UNTRIED = "untried"
EVIDENCE_STYLED = "styled"


def outfit_evidence(garment_ids, model):
    """What the model actually KNOWS about this combination: (kind, a, b).

    `a`/`b` name the pair the kind refers to; both are None for STYLED, where
    the statement is about the whole outfit.

    THE POINT OF THIS FUNCTION IS HONESTY ABOUT THE COMMON CASE. Measured on the
    top 40 suggestions: no weakest pair scores below 0.41 and the median is 0.50
    — which is exactly the no-evidence value. The ranker has already removed the
    bad pairings, so on a card good enough to show her, the weak link is almost
    never "this is bad" and almost always "I have never seen these two
    together". A UI that phrased that as a flaw would be quietly lying, and one
    that phrased it as a gap is both true and useful: the pair it knows least
    about is the pair her verdict would teach it the most from.

    STYLED says styled, not WORN. Positive evidence here comes from her
    published looks, and published is not worn — 18 of the 35 garments in her
    published looks have never appeared in the wear log. Claiming she wore
    something she only photographed is the kind of small false note that makes a
    whole feature untrustworthy.
    """
    ps = pairs(garment_ids)
    if not ps:
        return (EVIDENCE_STYLED, None, None)

    rejected, untried = [], []
    for a, b in ps:
        pos, neg = pair_evidence(model, a, b)
        if neg > 0:
            rejected.append((neg, -pos, a, b))
        elif pos <= 0:
            untried.append((pair_score(model, a, b), a, b))

    if rejected:                       # most negative evidence speaks first
        rejected.sort(reverse=True)
        return (EVIDENCE_REJECTED, rejected[0][2], rejected[0][3])
    if untried:                        # of the unknowns, the least promising
        untried.sort()
        return (EVIDENCE_UNTRIED, untried[0][1], untried[0][2])
    return (EVIDENCE_STYLED, None, None)


def coverage(model, outfits):
    """How much of a set of outfits the GARMENT level actually speaks to.

    Reported rather than assumed: if most pairs fall back to their type, the
    model is a type model wearing a garment model's name, and any result has to
    be read that way.
    """
    seen = set(model["pair_pos"]) | set(model["pair_neg"])
    total = evidenced = 0
    for ids in outfits:
        for key in pairs(ids):
            total += 1
            evidenced += key in seen
    return evidenced, total
