#!/usr/bin/env python3
"""Phase 2 acceptance evidence. $0, offline, reads closet_snapshot.json only.

    python3 scripts/dump_closet.py       # refresh the snapshot first
    python3 scripts/engine_report.py

Prints what the foundation plan asks to see before Phase 2 can be called done:
  1. all valid outfits enumerated, count is sane
  2. orphans identified and match intuition on inspection
  3. harmony scores rank hand-picked good/bad pairings correctly
"""
import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from engine import colour, constraints, gaps  # noqa: E402

SNAPSHOT = os.path.join(HERE, "closet_snapshot.json")


def rule(title):
    print("\n" + title)
    print("-" * len(title))


def main():
    if not os.path.exists(SNAPSHOT):
        print("no snapshot — run scripts/dump_closet.py first", file=sys.stderr)
        return 1
    with open(SNAPSHOT) as fh:
        data = json.load(fh)
    G, O = data["garments"], data["outfits"]
    by_id = {g["id"]: g for g in G}

    def dom(gid):
        c = by_id[gid].get("colors") or []
        return c[0]["name"] if c else "?"

    def label(gid):
        return "%s (%s)" % (gid, dom(gid))

    # ---------------------------------------------------------------- 1. count
    rule("1. ENUMERATION")
    n = {c: len([x for x in G if x["category"] == c])
         for c in ("top", "bottom", "dress", "outerwear", "shoes")}
    structural_space = gaps.enumerate_outfits(G, apply_user_rules=False)
    base = gaps.enumerate_outfits(G)
    with_ow = gaps.enumerate_outfits(G, with_outerwear=True)
    print("closet: " + " · ".join("%s %d" % (k, v) for k, v in n.items()))
    print("structurally valid      %5d   = (%d x %d + %d) x %d"
          % (len(structural_space), n["top"], n["bottom"], n["dress"], n["shoes"]))
    # Her rules are a filter on what may be SUGGESTED, so the gap between these
    # two lines is the price of style_rules.txt — printed rather than buried,
    # because it is the number to look at if suggestions ever feel thin.
    removed = len(structural_space) - len(base)
    print("suggestable (her rules) %5d   -%d (%.0f%%) by %d user rule(s)"
          % (len(base), removed, 100.0 * removed / max(len(structural_space), 1),
             len(constraints.USER_RULES)))
    for name, _ in constraints.USER_RULES:
        n_hit = sum(1 for c in structural_space
                    if name in constraints.user_rule_violations(c))
        print("    %-40s -%d" % (name, n_hit))
    print("with outerwear          %5d" % len(with_ow))

    ranked = gaps.ranked_outfits(G)
    scores = [o["score"] for o in ranked]
    print("score  min %.3f · median %.3f · max %.3f"
          % (min(scores), statistics.median(scores), max(scores)))

    # ---------------------------------------------------------------- 2. gaps
    rule("2. GAPS")
    part = gaps.participation(G)
    print("structural participation: min %d · median %d · max %d"
          % (min(part.values()), statistics.median(part.values()), max(part.values())))
    structural = gaps.orphans(G)
    print("structural orphans (<=2): %d %s"
          % (len(structural), "— everything pairs; see quality orphans below"
             if not structural else ""))

    cutoff = statistics.median(scores)
    qcount, qbest = gaps.quality_participation(G, cutoff)
    stranded = sorted(((qcount[g["id"]], qbest[g["id"]], g["id"]) for g in G))[:8]
    print("\ngarments with fewest ABOVE-MEDIAN outfits (cutoff %.3f):" % cutoff)
    for cnt, best, gid in stranded:
        print("   %-34s %4d good outfits · best %.3f · %s"
              % (gid, cnt, best, by_id[gid].get("category")))

    # Published looks + logged wears — NOT the raw outfit list, which also holds
    # stylist suggestions. Passing all 57 counted a garment as worn because the
    # engine once proposed it, which is how this printed 9 never-worn against
    # /insights' 13 and quietly deflated every cost-per-wear.
    WORN = gaps.worn_outfits(O)
    never = gaps.unworn(G, WORN)
    print("\nnever worn (published looks + logged wears): %d of %d"
          % (len(never), len(G)))

    cpw = [r for r in gaps.cost_per_wear(G, WORN) if r["wears"] == 0]
    print("value sitting unworn: ${:,.0f} across {} garments".format(
        sum(r["price_usd"] for r in cpw), len(cpw)))
    for r in sorted(cpw, key=lambda r: -r["price_usd"])[:5]:
        print("   %-34s $%.0f" % (r["id"], r["price_usd"]))

    worn = [r for r in gaps.cost_per_wear(G, WORN) if r["wears"] > 0]
    if worn:
        print("\nbest cost-per-wear so far:")
        for r in sorted(worn, key=lambda r: r["cost_per_wear"])[:5]:
            print("   %-34s $%.2f  (%d wears, $%.0f)"
                  % (r["id"], r["cost_per_wear"], r["wears"], r["price_usd"]))

    # ------------------------------------------------------------- 3. ranking
    rule("3. RANKING")
    print("best 5:")
    for o in ranked[:5]:
        print("   %.3f  %s" % (o["score"], ", ".join(label(i) for i in o["garment_ids"])))
    print("worst 5:")
    for o in ranked[-5:]:
        print("   %.3f  %s   [%s]" % (o["score"],
                                      ", ".join(label(i) for i in o["garment_ids"]),
                                      "; ".join(o["notes"]) or o["worst_reason"]))

    # Her own looks are the ground truth available: if the ranking is sane they
    # should sit high in the space they were drawn from.
    #
    # PUBLISHED ONLY. This iterated over every outfit row — all 57, including the
    # 24 the STYLIST itself proposed and the 15 logged wears — while printing the
    # header "her 18 published looks". Scoring the engine's own suggestions and
    # calling the result her taste is circular, and it is the same confusion that
    # made this file report 9 never-worn against /insights' 13 on 07-28.
    pcts = []
    for o in [x for x in O if x.get("source") == "manual"]:
        combo = [by_id[i] for i in o["garment_ids"] if i in by_id]
        if not combo:
            continue
        h, _ = colour.outfit_harmony(combo)
        s, _ = constraints.score(combo, h)
        pct = 100.0 * sum(1 for x in scores if x < s) / len(scores)
        pcts.append((pct, s, o.get("render_cache_key"),
                     (o.get("context") or {}).get("occasion")))
    # Sort on the NUMBERS only. A plain sort() falls through to the 3rd and 4th
    # tuple fields whenever two looks tie on (pct, score), and `render_cache_key`
    # can be None — which raises on py3 comparing None to str. It crashed here.
    pcts.sort(key=lambda p: (p[0], p[1]))
    print("\nher %d published looks, scored against all %d outfits:"
          % (len(pcts), len(ranked)))
    print("   mean percentile %.0f · median %.0f"
          % (sum(p[0] for p in pcts) / len(pcts),
             statistics.median([p[0] for p in pcts])))
    print("   weakest 3:")
    for pct, s, lid, occ in pcts[:3]:
        print("      %-10s %.3f  p%.0f  (%s)" % (lid, s, pct, occ or "—"))
    print("   strongest 3:")
    for pct, s, lid, occ in pcts[-3:]:
        print("      %-10s %.3f  p%.0f  (%s)" % (lid, s, pct, occ or "—"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
