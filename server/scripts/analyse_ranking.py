#!/usr/bin/env python3
"""Measure the engine's ranking against her blind verdicts. $0, offline.

    python3 scripts/analyse_ranking.py ~/Downloads/ranking_verdicts.json

Answers three questions, in order of what actually matters:

  1. Does the score separate what she would wear from what she would not?
     If the two groups have the same mean, the ranking carries no signal at all
     and no amount of constant-twiddling will fix it.
  2. Where does it disagree, and what rule fired there? Disagreements are
     grouped by the notes and colour reasons involved, because a rule that only
     appears in the disagreements is the rule to change.
  3. Do her own looks score like the engine's picks? They are the ground truth.
"""
import argparse
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from engine import colour, constraints  # noqa: E402

SNAPSHOT = os.path.join(HERE, "closet_snapshot.json")


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("verdicts", help="ranking_verdicts.json from the review page")
    args = ap.parse_args()

    with open(os.path.expanduser(args.verdicts)) as fh:
        payload = json.load(fh)
    verdicts = payload.get("verdicts", {})
    items = {i["key"]: i for i in payload.get("items", [])}

    with open(SNAPSHOT) as fh:
        data = json.load(fh)
    by_id = {g["id"]: g for g in data["garments"]}

    judged = [(items[k], v) for k, v in verdicts.items() if k in items]
    if not judged:
        print("no judged outfits in that file", file=sys.stderr)
        return 1

    yes = [it for it, v in judged if v == "yes"]
    no = [it for it, v in judged if v == "no"]

    print("judged %d of %d  ·  would wear %d  ·  would not %d"
          % (len(judged), len(items), len(yes), len(no)))

    if not yes or not no:
        print("\nOnly one verdict used — nothing to separate. Judge a mix and re-export.")
        return 0

    # ------------------------------------------------------------ 1. signal
    my, mn = mean([i["score"] for i in yes]), mean([i["score"] for i in no])
    print("\n1. SEPARATION")
    print("   mean score, would wear     %.3f" % my)
    print("   mean score, would not      %.3f" % mn)
    print("   gap                        %+.3f" % (my - mn))

    # Rank-order agreement: over every yes/no pair, how often does the engine
    # put the one she likes higher? 0.5 is a coin flip.
    wins = ties = 0
    for a in yes:
        for b in no:
            if a["score"] > b["score"]:
                wins += 1
            elif a["score"] == b["score"]:
                ties += 1
    total = len(yes) * len(no)
    auc = (wins + 0.5 * ties) / total
    print("   pairwise agreement (AUC)   %.3f   %s" % (
        auc,
        "no better than chance" if 0.45 <= auc <= 0.55 else
        "inverted — the engine prefers what she rejects" if auc < 0.45 else
        "weak" if auc < 0.65 else "usable"))

    # ------------------------------------------------------------ 2. misfires
    print("\n2. WHERE IT DISAGREES")
    ranked_scores = sorted(i["score"] for i in items.values())
    cut = statistics.median(ranked_scores)
    false_low = [i for i in yes if i["score"] < cut]     # she likes, engine ranks low
    false_high = [i for i in no if i["score"] >= cut]    # engine likes, she rejects
    print("   she'd wear but engine ranked low:  %d" % len(false_low))
    print("   engine ranked high but she won't:  %d" % len(false_high))

    def reasons_for(entry):
        combo = [by_id[i] for i in entry["ids"] if i in by_id]
        if not combo:
            return [], []
        _, worst = colour.outfit_harmony(combo)
        _, notes = constraints.soft_notes(combo)
        return notes, ([worst[1]] if worst else [])

    from collections import Counter
    for label, group in (("she'd wear, ranked low", false_low),
                         ("ranked high, she won't", false_high)):
        notes_c, reason_c = Counter(), Counter()
        for e in group:
            n, r = reasons_for(e)
            notes_c.update(x.split()[0] for x in n)
            reason_c.update(r)
        if group:
            print("   %s:" % label)
            print("      soft rules firing : %s" % (dict(notes_c) or "none"))
            print("      worst-pair reasons: %s" % dict(reason_c))

    print("\n   individual misses (she'd wear, ranked low):")
    for e in sorted(false_low, key=lambda x: x["score"])[:8]:
        n, r = reasons_for(e)
        print("      %.3f p%-3d %-8s %s   [%s | %s]"
              % (e["score"], e["pct"], e["origin"], " + ".join(e["ids"]),
                 "; ".join(n) or "no penalty", "; ".join(r)))

    # ------------------------------------------------------- 3. her own looks
    print("\n3. HER OWN LOOKS AS GROUND TRUTH")
    hers = [(it, v) for it, v in judged if it["origin"] == "hers"]
    eng = [(it, v) for it, v in judged if it["origin"] == "engine"]
    if hers:
        kept = sum(1 for _, v in hers if v == "yes")
        print("   of her %d published looks, she'd still wear %d (%.0f%%)"
              % (len(hers), kept, 100.0 * kept / len(hers)))
        print("   their mean engine percentile: %.0f" % mean([i["pct"] for i, _ in hers]))
    if eng:
        kept = sum(1 for _, v in eng if v == "yes")
        print("   of %d engine picks, she'd wear %d (%.0f%%)"
              % (len(eng), kept, 100.0 * kept / len(eng)))
        top = [i for i, v in eng if i["pct"] >= 90]
        if top:
            kept_top = sum(1 for i, v in eng if i["pct"] >= 90 and v == "yes")
            print("   of %d picks the engine ranked in its top decile, she'd wear %d"
                  % (len(top), kept_top))

    print("\nRead the AUC first. Below ~0.55 the score is noise and the fix is a "
          "different signal, not different constants.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
