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

This is that harness, in git, with the 07-27 figures as its acceptance test
(`--check`). If a change to the engine moves these numbers, that is a finding,
not a nuisance — but it must be SEEN.

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

from engine import colour, constraints, gaps, preference  # noqa: E402

SNAPSHOT = os.path.join(HERE, "closet_snapshot.json")

# What TRAINS affinity. Not what counts as worn — that distinction cost a day on
# 07-27 and is why /stylist and /insights once disagreed 23 vs 13.
PRIOR = ("manual",)

# The 07-27 results, as the acceptance test. Tolerance is deliberately loose on
# the LOO figures: they were computed before 59-el-hoodie gained its `top` alt
# role (space 2220), and the snapshot now carries it (2320). The DIRECTION is
# what was established and what must not silently flip.
EXPECTED = {
    "heldout_affinity_whole": 0.652,     # 0.660 pre-hoodie, restated 0.652 after
    "heldout_affinity_rotation": 0.548,  # 0.555 pre-hoodie
    "heldout_colour_whole": 0.360,
    "insample_published_whole": 0.939,
}
TOLERANCE = 0.03

# The LOO deltas are the finding that sets `PRIOR = ("manual",)` everywhere:
# adding worn outfits to the training set COSTS accuracy. Pinned separately
# because a sign flip here would mean the standing rule is wrong, which is a
# much bigger deal than a third-decimal wobble.
EXPECTED_LOO_DELTA = {"whole": -0.120, "rotation": -0.172}
LOO_TOLERANCE = 0.05


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

def held_out(d):
    print("\nHELD OUT — the %d worn outfits as a test set the model never saw"
          % len(d["positives"]))
    print("%-34s %-24s %s" % ("model", "vs whole valid space", "vs in-rotation only"))
    rows = {}
    for label, score in (
        ("learned affinity (published)", affinity_model(d["garments"], d["published"])),
        ("colour + constraints", colour_model(d["by_id"])),
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
    """Acceptance: do we still reproduce 07-27?"""
    got = {
        "heldout_affinity_whole": rows[("learned affinity (published)", False)],
        "heldout_affinity_rotation": rows[("learned affinity (published)", True)],
        "heldout_colour_whole": rows[("colour + constraints", False)],
        "insample_published_whole": sanity,
    }
    print("\nACCEPTANCE vs the 07-27 figures (tolerance ±%.2f)" % TOLERANCE)
    bad = 0
    for k, want in EXPECTED.items():
        have = got[k]
        ok = abs(have - want) <= TOLERANCE
        bad += not ok
        print("  %-30s expected %.3f  got %.3f   %s"
              % (k, want, have, "ok" if ok else "*** DRIFTED ***"))
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

    rows = held_out(d)
    sanity = in_sample_sanity(d)
    loo_drift = []
    if not args.check:
        by_occasion(d)
        if not args.skip_loo:
            _, _, loo_drift = leave_one_out(d)
    bad = check(d, rows, sanity) + len(loo_drift)
    if bad and not args.rules:
        print("\n%d figure(s) drifted. That is a FINDING — investigate before "
              "trusting anything downstream." % bad)
    return 1 if (bad and not args.rules) else 0


if __name__ == "__main__":
    raise SystemExit(main())
