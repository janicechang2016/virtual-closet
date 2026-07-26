#!/usr/bin/env python3
"""Does accumulated stylist feedback actually improve prediction? $0, offline.

    python3 scripts/analyse_stylist_feedback.py

The calibration set answered this once and the answer was NO — unattributed
rejections made prediction worse (AUC 0.583 against 0.824 from her published
looks alone), because an outfit-level "no" smears blame across garments that
were fine. The stylist now captures WHICH garment was wrong, so the question is
open again and worth measuring rather than assuming.

Leave-one-out throughout: every judgement is scored by a model that never saw
it. Anything else measures memorisation.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..",
                                                 "virtual-closet", "scripts")))

from engine import preference  # noqa: E402

SNAPSHOT = os.path.join(HERE, "closet_snapshot.json")


def auc(scored):
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


def as_verdicts(entries, attributed=True, positives_only=False):
    """Shape log entries for engine.preference."""
    out = []
    for e in entries:
        if e.get("verdict") == "yes":
            out.append(({"ids": e.get("ids") or []}, "yes"))
        elif e.get("verdict") == "no" and not positives_only:
            if attributed and e.get("blame"):
                out.append(({"ids": [e["blame"]]}, "no"))
            elif not attributed:
                out.append(({"ids": e.get("ids") or []}, "no"))
    return out


def main():
    import closet_server as cs

    with open(SNAPSHOT) as fh:
        data = json.load(fh)
    garments = data["garments"]
    looks = [o for o in data["outfits"] if o.get("source") == "manual"]

    entries = list(cs.stylist_current().values())
    entries = [e for e in entries if e.get("verdict") in ("yes", "no")]
    if len(entries) < 12:
        print("only %d judgements — too few to measure" % len(entries))
        return 1

    yes_n = sum(1 for e in entries if e["verdict"] == "yes")
    print("judgements %d  (%d would wear, %d would not, %d attributed)"
          % (len(entries), yes_n, len(entries) - yes_n,
             sum(1 for e in entries if e.get("blame"))))
    print("published looks used as prior: %d\n" % len(looks))

    def evaluate(label, negw=1.0, **kw):
        # negative_weight is passed explicitly: the shipped default is 0.0, so
        # without an override every variant here would collapse to the same
        # number and the diagnostic would silently stop comparing anything.
        scored = []
        for i, e in enumerate(entries):
            others = [entries[j] for j in range(len(entries)) if j != i]
            aff = preference.affinity(garments, looks, as_verdicts(others, **kw),
                                      negative_weight=negw)
            scored.append((preference.outfit_preference(e["ids"], aff), e["verdict"]))
        print("  %-42s AUC %.3f" % (label, auc(scored)))
        return auc(scored)

    print("leave-one-out over the %d judgements:" % len(entries))
    base = []
    aff0 = preference.affinity(garments, looks, [])
    for e in entries:
        base.append((preference.outfit_preference(e["ids"], aff0), e["verdict"]))
    print("  %-42s AUC %.3f" % ("published looks only (no feedback)", auc(base)))
    a = evaluate("+ feedback, rejections ATTRIBUTED", negw=1.0, attributed=True)
    b = evaluate("+ feedback, rejections un-attributed", negw=1.0, attributed=False)
    c = evaluate("+ feedback, positives only  [SHIPPED]", negw=0.0, positives_only=True)

    print("\nwhat changed:")
    print("  attribution vs un-attributed  %+.3f" % (a - b))
    print("  attribution vs positives only %+.3f" % (a - c))
    print("  feedback vs none              %+.3f" % (a - auc(base)))

    # Where the evidence actually landed.
    from collections import Counter
    blame = Counter(e["blame"] for e in entries if e.get("blame"))
    print("\nrejections blame, by category:")
    cat = {g["id"]: g.get("category") for g in garments}
    print("  " + str(dict(Counter(cat.get(g, "?") for g in blame.elements()))))
    print("  most blamed: %s" % blame.most_common(5))

    print("\nCaveat: these outfits were chosen BY the model, so the evaluation set is")
    print("not independent of it. A rising AUC means the model predicts her judgement")
    print("on what it chooses to show — not on the closet as a whole.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
