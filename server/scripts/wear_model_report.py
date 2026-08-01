#!/usr/bin/env python3
"""Can anything predict what she actually WEARS? $0, no API calls, no database.

    python3 scripts/wear_model_report.py            # the full report
    python3 scripts/wear_model_report.py --check     # just the regression check

WHY THIS FILE EXISTS AT ALL. The 07-27 measurements — the ones every later
decision rests on (0.660 held out, 0.555 controlling for rotation, and the
leave-one-out table that killed feeding wears into affinity) — were produced by
`scratchpad/heldout_wear_test.py` and `scratchpad/loo_wear_test.py`. Neither was
ever tracked and the scratchpad is gone. So the headline numbers could not be
reproduced or extended, and Phase 6's "re-measure at ~50 wears" had no harness:
a rebuild that differs from the original method in how negatives are drawn or
folds are cut yields a number that LOOKS comparable and is not.

This is that harness, in git, with a pinned data state as its acceptance test
(`--check`). If a change to the engine moves these numbers, that is a finding,
not a nuisance — but it must be SEEN.

THE PIN IS A DATA STATE, NOT A CONSTANT, and it moves when the DATA does. It
was the 07-27 figures at 15 wears; it is the 07-31 figures at 18. Growing the
test set changes every held-out statistic by definition, so those old values
became permanently unreproducible the moment the 16th wear was logged — and a
check that can only ever report red is a check nobody reads. **Repin when the
data grew; investigate when it did not.** Each repin keeps the superseded value
inline, because the direction it established is what must not silently flip.

THE ONE THING MOST EASILY GOT WRONG: the 07-27 space was the STRUCTURAL one,
before her style rules filtered it (2320 outfits). Her rules landed 07-28 and
cut the suggestable space to 1600. Every measurement here therefore runs with
`apply_user_rules=False`, or it is not comparable to the numbers it claims to
reproduce. `--rules` runs the same measurement on the filtered space for
contrast; it answers a different question.

TARGET, per her call 07-27: outfits she would WEAR, not outfits she would
publish. Published looks are training data that happened to exist first.
"""
import argparse
import json
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))

from engine import colour, constraints, gaps, pairwise, preference  # noqa: E402

SNAPSHOT = os.path.join(HERE, "closet_snapshot.json")
STYLIST_SCRIPTS = os.path.normpath(
    os.path.join(HERE, "..", "..", "virtual-closet", "scripts"))

# What TRAINS affinity. Not what counts as worn — that distinction cost a day on
# 07-27 and is why /stylist and /insights once disagreed 23 vs 13.
PRIOR = ("manual",)

# REPINNED 07-31 AT 18 WEARS. These were the 07-27 figures, measured on 15; the
# test set has since grown by three and THE OLD VALUES CAN NEVER BE REPRODUCED
# FROM THIS SNAPSHOT AGAIN — adding positives changes the statistic by
# definition. Leaving them pinned would have meant a harness that reports red
# forever and so stops being read, which is the failure mode it exists to
# prevent. The 15-wear values are kept inline as history, because the DIRECTION
# they established is the thing that must not silently flip.
#
# All three moved UP and in the same direction as the added positives, which is
# what makes this a repin rather than a finding. Nothing here changed model,
# code or training set: `PRIOR` is unchanged and was re-verified the same day
# (LOO -0.118 / -0.170 against the pinned -0.120 / -0.172).
EXPECTED = {
    "heldout_affinity_whole": 0.682,     # 15 wears: 0.652 (0.660 pre-hoodie)
    "heldout_affinity_rotation": 0.583,  # 15 wears: 0.548 (0.555 pre-hoodie)
    # 15 wears: 0.360, whose CI EXCLUDED 0.5 — colour was called "not merely
    # uninformative but inverted". At 18 the CI is [0.294, 0.506] and no longer
    # excludes chance, so state the weaker claim from here: colour does not
    # predict her wears. It is not established that it predicts them backwards.
    # The standing rule is untouched either way — it rests on colour failing to
    # beat chance, never on it losing to chance.
    "heldout_colour_whole": 0.399,
    # NOT wear-dependent (published looks vs the whole space), so it is not part
    # of this repin. Reads 0.940 today against 0.939 pinned; left alone rather
    # than churned for a rounding-level move on a figure that never drifted.
    "insample_published_whole": 0.939,
}
TOLERANCE = 0.03

# The LOO deltas are the finding that sets `PRIOR = ("manual",)` everywhere:
# adding worn outfits to the training set COSTS accuracy. Pinned separately
# because a sign flip here would mean the standing rule is wrong, which is a
# much bigger deal than a third-decimal wobble.
EXPECTED_LOO_DELTA = {"whole": -0.120, "rotation": -0.172}
LOO_TOLERANCE = 0.05

# PAIRWISE. Repinned 07-31 on 18 wears / 140 verdicts (75 yes, 65 blamed no) /
# 18 published looks; was 07-29 on 15 wears / 82 verdicts.
# Unlike the block above these are NOT historic reproductions — they are this
# model's measurement, and they WILL move as she logs more. The durable claim is
# the relational one below; these floats only say "the data state that produced
# the write-up".
#
# THESE MOVE ON TWO INPUTS, NOT ONE. Wears grow the test set (as above), but her
# VERDICTS grow the training set, and judging a few cards shifts the third
# decimal immediately: six verdicts landed mid-measurement on 07-31 and made two
# consecutive runs disagree. **Repin pairwise only BETWEEN stylist sessions**,
# and check the verdict count in the report header is the one recorded here —
# otherwise the pin describes a data state that changed while it was being
# written down.
EXPECTED_PAIRWISE = {"whole": 0.803, "rotation": 0.802}  # 07-29: 0.768 / 0.774

# THE FINDING, pinned as a relation because that is what has to survive more
# data: against the in-rotation pool — the one that strips the model's ability
# to win by scoring dead stock low, and where affinity collapses to 0.543 —
# pair structure must stay decisively ahead. If this margin ever closes, the
# argument for ranking on pairs has gone with it.
PAIRWISE_MARGIN = 0.15


def auc(scored):
    """Mann-Whitney, ties at 0.5 — byte-identical to
    `analyse_stylist_feedback.auc`, so these numbers sit on the same scale as
    the blind 24-outfit calibration. Do not 'improve' it."""
    yes = [s for s, v in scored if v == "yes"]
    no = [s for s, v in scored if v == "no"]
    if not yes or not no:
        return float("nan")
    wins = ties = 0
    for a in yes:
        for b in no:
            if a > b:
                wins += 1
            elif a == b:
                ties += 1
    return (wins + 0.5 * ties) / (len(yes) * len(no))


def bootstrap_ci(pos, neg, n=2000, seed=17):
    """Percentile CI by resampling the POSITIVES — 15 wears is what is scarce
    here; the negative pool is thousands and contributes almost no variance."""
    rng = random.Random(seed)
    if not pos or not neg:
        return (float("nan"), float("nan"))
    stats = []
    for _ in range(n):
        sample = [rng.choice(pos) for _ in pos]
        stats.append(auc([(s, "yes") for s in sample] + [(s, "no") for s in neg]))
    stats.sort()
    return (stats[int(0.025 * len(stats))], stats[int(0.975 * len(stats))])


# ---------------------------------------------------------------- the models

def affinity_model(garments, looks):
    aff = preference.affinity(garments, looks=looks)
    return lambda ids: preference.outfit_preference(ids, aff)


def pairwise_model(garments, looks, verdicts):
    m = pairwise.compatibility(garments, looks=looks, verdicts=verdicts)
    return lambda ids: pairwise.outfit_compatibility(ids, m)


def calibrated_pairwise_model(d, verdicts, space=None):
    """The shipping candidate: pairs learned from published looks + her BLAME
    negatives, ranked within pair-count class. Positive verdicts are left out
    deliberately — measured, they cost 0.15 (see `pairwise_report`)."""
    neg = [e for e in verdicts if e.get("verdict") == "no" and e.get("blame")]
    m = pairwise.compatibility(d["garments"], looks=d["published"], verdicts=neg)
    return pairwise.rank_calibrator(m, space if space is not None else d["space"])


def blended_model(garments, looks, verdicts, w=0.5):
    """Affinity and compatibility answer different questions — WHICH garments
    versus WHICH combinations — so the blend is worth measuring rather than
    assuming one supersedes the other. `w` is the weight on pairwise."""
    aff = preference.affinity(garments, looks=looks)
    m = pairwise.compatibility(garments, looks=looks, verdicts=verdicts)
    return lambda ids: ((1 - w) * preference.outfit_preference(ids, aff)
                        + w * pairwise.outfit_compatibility(ids, m))


def colour_model(by_id):
    """Colour harmony plus the soft constraint penalty — the pre-affinity
    ranker, kept as the baseline it was measured against."""
    def score(ids):
        combo = [by_id[i] for i in ids]
        h, _ = colour.outfit_harmony(combo)
        s, _ = constraints.score(combo, h)
        return s
    return score


# ------------------------------------------------------------------ the data

def load(apply_user_rules=False):
    with open(SNAPSHOT) as fh:
        snap = json.load(fh)
    G = snap["garments"]
    by_id = {g["id"]: g for g in G}
    outfits = snap["outfits"]
    by_oid = {o["id"]: o for o in outfits}

    # POSITIVES: outfits she actually put on, via the wear log. Deduplicated —
    # two wears of one outfit is one positive example, not two votes.
    worn_ids, worn_sets = [], set()
    for w in snap.get("wears") or []:
        o = by_oid.get(w.get("outfit_id"))
        if not o:
            continue
        key = tuple(sorted(o.get("garment_ids") or []))
        if key and key not in worn_sets:
            worn_sets.add(key)
            worn_ids.append(key)

    space = [tuple(sorted(g["id"] for g in combo))
             for combo in gaps.enumerate_outfits(G, apply_user_rules=apply_user_rules)]
    space_set = set(space)

    published = [o for o in outfits if o.get("source") in PRIOR]

    # IN-ROTATION: negatives built only from garments she has worn or published.
    # This removes the shortcut of scoring dead stock low, and it is the column
    # that collapsed the affinity model to a CI spanning chance.
    in_rotation = set()
    for o in gaps.worn_outfits(outfits):
        in_rotation.update(o.get("garment_ids") or [])

    return {
        "garments": G, "by_id": by_id, "outfits": outfits,
        "published": published, "positives": worn_ids,
        "space": space, "space_set": space_set, "in_rotation": in_rotation,
        "wears": snap.get("wears") or [], "by_oid": by_oid,
    }


def load_verdicts(d):
    """Her stylist judgements, resolved newest-wins. The pairwise model's only
    source of NEGATIVE evidence — the affinity model cannot use them at all.

    Imported from `closet_server.stylist_current()` rather than re-parsed here:
    the log is append-only with tombstones, and a second implementation of
    "which verdict is current" is exactly how two paths drift.

    LEAKAGE GUARD: any judged outfit that she has also WORN is dropped. It is 0
    today and will not stay 0 — the wears are the test set, and a judged copy of
    one would train the model on its own answer.
    """
    sys.path.insert(0, STYLIST_SCRIPTS)
    try:
        import closet_server as cs
    except Exception as exc:                                   # pragma: no cover
        print("  (no stylist verdicts: %s)" % exc)
        return [], 0
    worn = set(d["positives"])
    entries, dropped = [], 0
    for sig, e in cs.stylist_current().items():
        if e.get("verdict") not in ("yes", "no"):
            continue
        if sig in worn:
            dropped += 1
            continue
        entries.append(e)
    return entries, dropped


def negatives(d, positives, rotation_only=False):
    pos = set(positives)
    out = []
    for combo in d["space"]:
        if combo in pos:
            continue
        if rotation_only and not set(combo) <= d["in_rotation"]:
            continue
        out.append(combo)
    return out


def measure(d, score, positives, rotation_only=False, ci=True):
    neg = negatives(d, positives, rotation_only)
    p = [score(list(c)) for c in positives]
    n = [score(list(c)) for c in neg]
    a = auc([(s, "yes") for s in p] + [(s, "no") for s in n])
    lo, hi = bootstrap_ci(p, n) if ci else (float("nan"), float("nan"))
    return a, lo, hi, len(neg)


# -------------------------------------------------------------------- report

def held_out(d, verdicts):
    print("\nHELD OUT — the %d worn outfits as a test set the model never saw"
          % len(d["positives"]))
    print("%-34s %-24s %s" % ("model", "vs whole valid space", "vs in-rotation only"))
    rows = {}
    for label, score in (
        ("learned affinity (published)", affinity_model(d["garments"], d["published"])),
        ("colour + constraints", colour_model(d["by_id"])),
        ("pairwise (published+verdicts)",
         pairwise_model(d["garments"], d["published"], verdicts)),
        ("affinity + pairwise, 50/50",
         blended_model(d["garments"], d["published"], verdicts)),
        ("pairwise, blame-neg + calibrated",
         calibrated_pairwise_model(d, verdicts)),
    ):
        cells = []
        for rot in (False, True):
            a, lo, hi, n = measure(d, score, d["positives"], rot)
            cells.append("%.3f [%.3f, %.3f]" % (a, lo, hi))
            rows[(label, rot)] = a
        print("%-34s %-24s %s" % (label, cells[0], cells[1]))
    return rows


def in_sample_sanity(d):
    """Published looks vs the whole space, in-sample. Should be ~0.939 — if this
    breaks, the pipeline is wrong and nothing below it means anything."""
    score = affinity_model(d["garments"], d["published"])
    pub = [tuple(sorted(o["garment_ids"])) for o in d["published"]]
    pub = [p for p in pub if p in d["space_set"]]
    a, _, _, n = measure(d, score, pub, False, ci=False)
    print("\nSANITY  published looks vs whole space, in-sample: %.3f "
          "(expect ~%.3f) over %d negatives" % (a, EXPECTED["insample_published_whole"], n))
    return a


def leave_one_out(d):
    """Does feeding WORN outfits into affinity help? Measured 07-27: no.

    Per-fold models, so pooling raw scores across folds would be invalid. For
    each held-out positive, take the fraction of negatives it beats UNDER ITS
    OWN FOLD'S MODEL, then average those fractions.
    """
    print("\nLEAVE-ONE-OUT — should wears train affinity?")
    print("%-34s %-16s %s" % ("training set", "vs whole space", "vs in-rotation"))
    pos = d["positives"]
    worn_as_looks = [{"garment_ids": list(c)} for c in pos]

    def fold_scores(build, rotation_only):
        fracs = []
        for i, held in enumerate(pos):
            others = [worn_as_looks[j] for j in range(len(pos)) if j != i]
            score = build(others)
            neg = negatives(d, [held], rotation_only)
            hs = score(list(held))
            ns = [score(list(c)) for c in neg]
            wins = sum(1 for s in ns if hs > s) + 0.5 * sum(1 for s in ns if hs == s)
            fracs.append(wins / len(ns))
        return statistics.fmean(fracs)

    out = {}
    for label, build in (
        ("published only (today)",
         lambda others: affinity_model(d["garments"], d["published"])),
        ("published + the other wears",
         lambda others: affinity_model(d["garments"], d["published"] + others)),
        ("the other wears only",
         lambda others: affinity_model(d["garments"], others)),
    ):
        a = fold_scores(build, False)
        b = fold_scores(build, True)
        out[label] = (a, b)
        print("%-34s %-16.3f %.3f" % (label, a, b))

    base = out["published only (today)"]
    plus = out["published + the other wears"]
    deltas = {"whole": plus[0] - base[0], "rotation": plus[1] - base[1]}
    print("\n  adding wears to the training set: %+.3f whole, %+.3f in-rotation"
          % (deltas["whole"], deltas["rotation"]))
    drift = []
    for k, want in EXPECTED_LOO_DELTA.items():
        if abs(deltas[k] - want) > LOO_TOLERANCE:
            drift.append("%s %+.3f (expected %+.3f)" % (k, deltas[k], want))
        if deltas[k] >= 0:
            drift.append("%s DELTA IS NO LONGER NEGATIVE — "
                         "PRIOR = ('manual',) may no longer be justified" % k)
    for line in drift:
        print("  *** %s" % line)
    return out, deltas, drift


def pairwise_report(d, verdicts):
    """Ablations, because "pairwise works" is not a finding — WHICH PART works is.

    The one that matters is `positives only`: affinity structurally cannot use a
    rejection (measured twice, it costs accuracy), so if the blame negatives buy
    nothing here either, the pairwise argument is dead and the honest conclusion
    is that the dataset, not the model shape, is the constraint.
    """
    G, looks = d["garments"], d["published"]
    pos_only = [e for e in verdicts if e.get("verdict") == "yes"]
    neg_only = [e for e in verdicts if e.get("verdict") == "no" and e.get("blame")]

    full = pairwise.compatibility(G, looks=looks, verdicts=verdicts)
    ev, tot = pairwise.coverage(full, d["positives"])
    print("\nPAIRWISE — %d verdicts (%d yes, %d blamed no) · %d published looks"
          % (len(verdicts),
             sum(1 for e in verdicts if e.get("verdict") == "yes"),
             sum(1 for e in verdicts if e.get("verdict") == "no" and e.get("blame")),
             len(looks)))
    print("  garment-level evidence covers %d of %d pairs in the test set (%.0f%%) "
          "— the rest fall back to their type" % (ev, tot, 100.0 * ev / max(tot, 1)))

    def strip(m, level):
        m = dict(m)
        if level == "type":          # forget individual garments
            m["pair_pos"], m["pair_neg"] = {}, {}
        else:                        # forget the backoff
            m["type_pos"], m["type_neg"] = {}, {}
        return m

    print("%-38s %-16s %s" % ("variant", "vs whole space", "vs in-rotation"))
    out = {}
    for label, model in (
        ("full (pairs + type backoff)", full),
        ("positives only — no blame negatives",
         pairwise.compatibility(G, looks=looks, verdicts=pos_only)),
        ("published looks only — no verdicts",
         pairwise.compatibility(G, looks=looks)),
        ("published + blame negatives only",
         pairwise.compatibility(G, looks=looks, verdicts=neg_only)),
        ("type level only", strip(full, "type")),
        ("garment level only", strip(full, "garment")),
    ):
        score = (lambda m: lambda ids: pairwise.outfit_compatibility(ids, m))(model)
        a, _, _, _ = measure(d, score, d["positives"], False, ci=False)
        b, _, _, _ = measure(d, score, d["positives"], True, ci=False)
        out[label] = (a, b)
        print("  %-36s %-16.3f %.3f" % (label, a, b))

    print("\n  blend weight on pairwise (0 = affinity today, 1 = pairwise alone)")
    for w in (0.0, 0.25, 0.5, 0.75, 1.0):
        score = blended_model(G, looks, verdicts, w=w)
        a, _, _, _ = measure(d, score, d["positives"], False, ci=False)
        b, _, _, _ = measure(d, score, d["positives"], True, ci=False)
        print("    w=%.2f   whole %.3f   in-rotation %.3f" % (w, a, b))
    return out


def top_of_list(d, verdicts, n=12):
    """WHAT SHE WOULD ACTUALLY SEE — the check AUC cannot perform.

    A ranking model is judged on its top row, not on its average behaviour, and
    the two came apart badly here: raw pair scoring measured 0.809 while putting
    a DRESS in 10 of its top 12, on a closet where dresses are 5% of the space,
    appear in 1 of 15 wears, and are the pieces her own rules call event wear
    for events she has not had. AUC did not move because dress outfits are 120
    of 2320 negatives. This table is the standing guard against that class of
    failure — read it every time, and compare against the space's own shares.
    """
    two_share = 100.0 * sum(1 for c in d["space"] if len(c) == 2) / len(d["space"])
    dress_share = 100.0 * sum(
        1 for c in d["space"]
        if any(d["by_id"][g]["category"] == "dress" for g in c)) / len(d["space"])
    print("\nTOP OF THE LIST — what a stylist row would actually show (n=%d)" % n)
    print("  the space itself is %.0f%% two-item, %.0f%% dress"
          % (two_share, dress_share))
    print("  %-34s %-9s %-9s %s" % ("model", "two-item", "dress", "distinct garments"))
    for label, score in (
        ("affinity (shipped today)",
         affinity_model(d["garments"], d["published"])),
        ("pairwise, raw",
         pairwise_model(d["garments"], d["published"],
                        [e for e in verdicts
                         if e.get("verdict") == "no" and e.get("blame")])),
        ("pairwise, blame-neg + calibrated",
         calibrated_pairwise_model(d, verdicts)),
    ):
        top = sorted(d["space"], key=lambda c: -score(list(c)))[:n]
        two = sum(1 for c in top if len(c) == 2)
        dress = sum(1 for c in top
                    if any(d["by_id"][g]["category"] == "dress" for g in c))
        print("  %-34s %-9s %-9s %d"
              % (label, "%d/%d" % (two, n), "%d/%d" % (dress, n),
                 len({g for c in top for g in c})))


def pairwise_loo(d, verdicts):
    """Should WORN outfits train the pairwise model? For affinity the answer was
    a firm no (-0.120 / -0.172). It is a genuinely different question here: the
    objection was that wear FREQUENCY is not preference, and a pair either
    co-occurred or did not — repeats add far less than they do to a scalar.

    Per-fold models throughout, same discipline as `leave_one_out`.
    """
    print("\nPAIRWISE LEAVE-ONE-OUT — should wears train it?")
    print("%-34s %-16s %s" % ("training set", "vs whole space", "vs in-rotation"))
    pos = d["positives"]
    worn_as_looks = [{"garment_ids": list(c)} for c in pos]

    def fold_scores(build, rotation_only):
        fracs = []
        for i, held in enumerate(pos):
            others = [worn_as_looks[j] for j in range(len(pos)) if j != i]
            m = build(others)
            neg = negatives(d, [held], rotation_only)
            hs = pairwise.outfit_compatibility(list(held), m)
            ns = [pairwise.outfit_compatibility(list(c), m) for c in neg]
            wins = sum(1 for s in ns if hs > s) + 0.5 * sum(1 for s in ns if hs == s)
            fracs.append(wins / len(ns))
        return statistics.fmean(fracs)

    res = {}
    for label, build in (
        ("published + verdicts (today)",
         lambda others: pairwise.compatibility(d["garments"], looks=d["published"],
                                               verdicts=verdicts)),
        ("+ the other wears",
         lambda others: pairwise.compatibility(d["garments"],
                                               looks=d["published"] + others,
                                               verdicts=verdicts)),
    ):
        a = fold_scores(build, False)
        b = fold_scores(build, True)
        res[label] = (a, b)
        print("%-34s %-16.3f %.3f" % (label, a, b))
    base, plus = res["published + verdicts (today)"], res["+ the other wears"]
    print("\n  adding wears to the pairwise training set: %+.3f whole, %+.3f in-rotation"
          % (plus[0] - base[0], plus[1] - base[1]))
    return res


def by_occasion(d):
    """NEW 07-28. Occasion was unrecorded until migration 0006; it is here
    because it removed 59% of the uncertainty about footwear.

    Reported as counts, NOT as a model: at 15 wears the largest occasion has 6
    examples, and an AUC per occasion would be a number with nothing behind it.
    """
    occ = {}
    for w in d["wears"]:
        o = d["by_oid"].get(w.get("outfit_id"))
        if not o or not w.get("occasion"):
            continue
        occ.setdefault(w["occasion"], []).append(o["garment_ids"])
    if not occ:
        print("\nBY OCCASION — no wear carries an occasion yet (migration 0006).")
        return
    print("\nBY OCCASION — descriptive only, n=%d" % sum(len(v) for v in occ.values()))
    for name, outs in sorted(occ.items(), key=lambda kv: -len(kv[1])):
        shoes = {}
        for ids in outs:
            for gid in ids:
                if d["by_id"][gid]["category"] == "shoes":
                    shoes[gid] = shoes.get(gid, 0) + 1
        top = sorted(shoes.items(), key=lambda kv: -kv[1])
        print("  %-11s n=%-2d  %s" % (name, len(outs),
              ", ".join("%s ×%d" % (g.split("-", 1)[1], c) for g, c in top)))


def check(d, rows, sanity):
    """Acceptance: do we still reproduce the pinned data state (18 wears, 07-31)?"""
    got = {
        "heldout_affinity_whole": rows[("learned affinity (published)", False)],
        "heldout_affinity_rotation": rows[("learned affinity (published)", True)],
        "heldout_colour_whole": rows[("colour + constraints", False)],
        "insample_published_whole": sanity,
    }
    print("\nACCEPTANCE vs the 18-wear pin, 07-31 (tolerance ±%.2f)" % TOLERANCE)
    bad = 0
    for k, want in EXPECTED.items():
        have = got[k]
        ok = abs(have - want) <= TOLERANCE
        bad += not ok
        print("  %-30s expected %.3f  got %.3f   %s"
              % (k, want, have, "ok" if ok else "*** DRIFTED ***"))

    pw = ("pairwise (published+verdicts)", True)
    if pw in rows:
        margin = rows[pw] - rows[("learned affinity (published)", True)]
        ok = margin >= PAIRWISE_MARGIN
        bad += not ok
        print("  %-30s pairwise beats affinity in-rotation by %+.3f "
              "(need >= %.2f)   %s"
              % ("pairwise_margin", margin, PAIRWISE_MARGIN,
                 "ok" if ok else "*** THE FINDING NO LONGER HOLDS ***"))
        for k, want in EXPECTED_PAIRWISE.items():
            have = rows[("pairwise (published+verdicts)", k == "rotation")]
            note = ("ok" if abs(have - want) <= TOLERANCE else
                    "moved (new wears AND/OR new verdicts — read it, do not just repin)")
            print("  %-30s pinned %.3f  got %.3f   %s"
                  % ("pairwise_" + k, want, have, note))
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rules", action="store_true",
                    help="measure on the rule-FILTERED space (a different question)")
    ap.add_argument("--check", action="store_true", help="acceptance only")
    ap.add_argument("--skip-loo", action="store_true", help="LOO is the slow part")
    args = ap.parse_args()

    d = load(apply_user_rules=args.rules)
    print("space %d outfits (%s) · %d positives · %d published · %d in rotation"
          % (len(d["space"]),
             "her rules APPLIED" if args.rules else "structural, rules off",
             len(d["positives"]), len(d["published"]), len(d["in_rotation"])))
    verdicts, leaked = load_verdicts(d)
    if leaked:
        print("  %d judged outfit(s) dropped as leakage — she has WORN them, and "
              "the wears are the test set" % leaked)

    rows = held_out(d, verdicts)
    sanity = in_sample_sanity(d)
    loo_drift = []
    if not args.check:
        if verdicts:
            pairwise_report(d, verdicts)
            top_of_list(d, verdicts)
        by_occasion(d)
        if not args.skip_loo:
            _, _, loo_drift = leave_one_out(d)
            if verdicts:
                pairwise_loo(d, verdicts)
    bad = check(d, rows, sanity) + len(loo_drift)
    if bad and not args.rules:
        print("\n%d figure(s) drifted. That is a FINDING — investigate before "
              "trusting anything downstream." % bad)
    return 1 if (bad and not args.rules) else 0


if __name__ == "__main__":
    raise SystemExit(main())
