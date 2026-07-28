#!/usr/bin/env python3
"""Track D.1 — the style profile.

An LLM-maintained document read from her own record: published looks, logged
wears, and stylist verdicts. NOT a trained model (plan invariant #3) — one
Anthropic call per regeneration, no fine-tuning, no gradient anywhere.

$0 BY DEFAULT. Without `--generate` this builds the digest, counts its tokens
and prints the estimated cost, and stops. The paid call happens only when asked
for, per the standing spending rule.

INVARIANT #10 IS THE LOAD-BEARING PART: the profile must be user-visible and
user-EDITABLE. Her edits live in their own `user_edits` list, are passed back
into every regeneration as authoritative, and are re-attached to the output
afterwards — so a regeneration can never quietly overwrite a rule she set. The
model is told it may not contradict them.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SNAPSHOT = ROOT / "server/scripts/closet_snapshot.json"
PROFILE = ROOT / "server/scripts/style_profile.json"
FEEDBACK = ROOT / "virtual-closet/logs/stylist_feedback.jsonl"

MODEL = "claude-opus-5"
# Thinking is ON BY DEFAULT on Opus 5 and max_tokens caps thinking + response
# TOGETHER. Sized tight, the JSON truncates mid-object and the whole call is
# wasted. 8000 is deliberate headroom, not an estimate of the output length.
MAX_TOKENS = 20000
PRICE_IN, PRICE_OUT = 5.0 / 1e6, 25.0 / 1e6      # claude-opus-5, USD per token

SYSTEM = """\
You are maintaining a personal style profile for one person, from her own record.

You will receive her closet, the outfits she published, the outfits she actually
wore, and her verdicts on suggestions (including, on rejections, which single
garment she blamed).

Rules, in order of authority:

1. HER OWN RULES ARE ABSOLUTE. Any rule listed under HER RULES was written by her
   directly. Restate them unchanged in `confirmed_preferences`. Never contradict
   one, never soften one, never infer a preference that conflicts with one.
2. GROUND EVERY CLAIM IN THE RECORD. Cite what you are reading from — "appears in
   9 of 18 published looks", "blamed in 3 of 4 rejections". If you cannot point
   at evidence, do not write the claim.
3. PUBLISHING AND WEARING ARE DIFFERENT SIGNALS AND MUST NOT BE MERGED. Measured
   on this data: not one logged wear matched a published look, and 18 of the 35
   garments in her published looks have never been worn. Where the two disagree,
   say so plainly rather than averaging them into one taste.
4. DO NOT INFER FROM COLOUR. Colour has been measured against her behaviour on
   this exact wardrobe and scores below chance. Comment on colour only where she
   stated a colour preference herself.
5. SAY WHAT YOU DO NOT KNOW. 15 wears is thin. Where the record is too small to
   support a claim, the honest output is to leave it out and let `confidence`
   reflect that.

Write `summary` as plain prose a person would recognise as being about herself —
specific, not flattering, no marketing voice."""


def load_digest():
    """Compact her whole record. ~7KB — small enough that the entire history
    fits in one call with no retrieval, chunking or summarisation step."""
    data = json.loads(SNAPSHOT.read_text())
    garments = data["garments"]
    outfits = {o["id"]: o for o in data["outfits"]}
    looks = [o for o in data["outfits"] if o.get("source") == "manual"]

    L = ["CLOSET (%d garments) — id|category/subcategory|colour|formality|"
         "warmth|volume|seasons" % len(garments)]
    for g in garments:
        colour = (g.get("colors") or [{}])[0].get("name", "?")
        L.append("%s|%s/%s|%s|f%s|w%s|%s|%s" % (
            g["id"], g.get("category"), g.get("subcategory"), colour,
            g.get("formality"), g.get("warmth"), g.get("volume"),
            ",".join(g.get("season_tags") or [])))

    L += ["", "PUBLISHED LOOKS (%d) — outfits she curated and photographed"
          % len(looks)]
    L += ["+".join(o["garment_ids"]) for o in looks]

    L += ["", "LOGGED WEARS (%d) — outfits she actually put on" % len(data["wears"])]
    for w in data["wears"]:
        o = outfits.get(w["outfit_id"])
        if o:
            L.append("%s %s" % (w["worn_on"], "+".join(o["garment_ids"])))

    # The feedback log's fields are `ids` and `blame` — NOT `garment_ids` and
    # `reason_code`. Reading the wrong names does not raise: every row arrives
    # as "no||blame=", the blame data silently vanishes, and the model correctly
    # reports that no rejection names a garment. Assert the shape instead.
    if FEEDBACK.exists():
        raw = []
        for line in FEEDBACK.read_text().splitlines():
            if not line.strip():
                continue
            try:
                raw.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        # Append-only with tombstones (see stylist_current in closet_server):
        # a re-judgement appends, so resolve newest-wins per outfit and drop
        # anything whose surviving verdict is a retraction.
        latest = {}
        for r in sorted(raw, key=lambda r: r.get("ts") or ""):
            latest["+".join(sorted(r.get("ids") or []))] = r
        rows = []
        for key, r in latest.items():
            if r.get("verdict") == "retracted" or not key:
                continue
            rows.append("%s|%s|blame=%s%s" % (
                r.get("verdict"), key, r.get("blame") or "-",
                "|wildcard" if r.get("wildcard") else ""))
        if rows:
            blamed = sum(1 for _, r in latest.items() if r.get("blame"))
            if not blamed:
                print("WARNING: no blame values parsed — check the log's field "
                      "names before spending on a generation.", file=sys.stderr)
            L += ["", "STYLIST VERDICTS (%d, newest-wins, retractions dropped) — "
                  "`blame` names the ONE garment she said killed a rejected "
                  "outfit; '-' means she rejected it without attributing"
                  % len(rows)] + rows
    return "\n".join(L)


def load_profile():
    return json.loads(PROFILE.read_text()) if PROFILE.exists() else {}


def load_key():
    """Same convention as fal_generate.load_key: environment, then the app's
    .env. The key is never written anywhere this script controls."""
    key = (os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        env = ROOT / "virtual-closet/.env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.strip().startswith("ANTHROPIC_API_KEY="):
                    raw = line.split("=", 1)[1]
                    # The .env ships this as a commented-out PLACEHOLDER
                    # ("ANTHROPIC_API_KEY=  # optional — ..."), so a naive
                    # split hands back the comment text and the SDK dies on a
                    # non-ascii header rather than on a missing key. Strip the
                    # comment, then require the real prefix.
                    key = raw.split("#", 1)[0].strip().strip("'\"")
                    break
    if not key.startswith("sk-ant-"):
        sys.exit("No Anthropic API key. virtual-closet/.env has an empty "
                 "ANTHROPIC_API_KEY placeholder, not a key.\n"
                 "Set ANTHROPIC_API_KEY in the environment, or fill that line in.")
    return key


SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "confirmed_preferences": {"type": "array", "items": {"type": "string"}},
        "observations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "evidence": {"type": "string"},
                },
                "required": ["claim", "evidence"],
                "additionalProperties": False,
            },
        },
        "confidence": {"type": "string"},
        "not_enough_data_for": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "confirmed_preferences", "observations",
                 "confidence", "not_enough_data_for"],
    "additionalProperties": False,
}


def build_prompt(digest, user_edits):
    rules = "\n".join("- %s" % e for e in user_edits) or "(none set yet)"
    return "HER RULES (written by her; authoritative)\n%s\n\n%s" % (rules, digest)


def record_spend(model, spent, usage, outcome):
    """Standing rule #1: every paid call reaches genlog — including the ones
    that fail. A refusal or a truncation is billed just like a success."""
    try:
        sys.path.insert(0, str(ROOT / "virtual-closet/scripts"))
        from genlog import log_generation
        log_generation(
            model=model,
            prompt="Track D.1 style profile from closet + looks + wears + verdicts",
            purpose="style-profile",
            cost_usd=round(spent, 4),
            outcome=outcome,
            extra={"input_tokens": usage.input_tokens,
                   "output_tokens": usage.output_tokens},
        )
    except Exception as exc:
        print("WARNING: genlog write failed (%s)" % exc, file=sys.stderr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true",
                    help="make the billed Anthropic call (otherwise $0 dry run)")
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args()

    prev = load_profile()
    # Single source of truth: her rules file, not the profile JSON (which this
    # script rewrites) and not the rendered .txt (which profile_view rewrites).
    # A rule must live somewhere nothing regenerates, or it gets clobbered.
    rules_file = ROOT / "server/scripts/style_rules.txt"
    user_edits = [" ".join(b.split()) for b in rules_file.read_text().split("\n\n")
                  if b.strip() and not b.strip().startswith("#")] \
        if rules_file.exists() else prev.get("user_edits", [])
    digest = load_digest()
    prompt = build_prompt(digest, user_edits)

    print("digest: %d chars | user rules carried forward: %d"
          % (len(digest), len(user_edits)))

    try:
        import anthropic
    except ImportError:
        print("\nanthropic SDK not installed — `pip install anthropic`.")
        print("Dry run only; cannot count tokens without it.")
        return 0

    client = anthropic.Anthropic(api_key=load_key())

    # Never estimate Claude tokens with tiktoken — it is OpenAI's tokenizer and
    # undercounts Claude badly. count_tokens is the only correct source.
    counted = client.messages.count_tokens(
        model=args.model,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    ).input_tokens
    # ~3700 output tokens measured on v1, not the 1000 first assumed: thinking
    # is on by default on Opus 5 and thinking bills as OUTPUT, which is most of
    # the response. Assuming a short answer under-quotes the call ~2.4x.
    est = counted * PRICE_IN + 3700 * PRICE_OUT
    print("input tokens: %d (measured) | est. cost/regeneration: $%.4f"
          % (counted, est))

    if not args.generate:
        print("\ndry run — pass --generate to make the billed call.")
        return 0

    resp = client.messages.create(
        model=args.model,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        messages=[{"role": "user", "content": prompt}],
        output_config={"format": {"type": "json_schema", "schema": SCHEMA}},
    )
    spent = (resp.usage.input_tokens * PRICE_IN
             + resp.usage.output_tokens * PRICE_OUT)
    ok = resp.stop_reason not in ("refusal", "max_tokens")
    record_spend(args.model, spent, resp.usage, "pass" if ok else resp.stop_reason)

    if resp.stop_reason == "refusal":
        print("refused (%s) — billed $%.4f" % (resp.stop_details, spent))
        return 1
    if resp.stop_reason == "max_tokens":
        print("TRUNCATED at max_tokens=%d — billed $%.4f. Thinking and output "
              "share the cap; raise MAX_TOKENS." % (MAX_TOKENS, spent))
        return 1

    body = json.loads(next(b.text for b in resp.content if b.type == "text"))

    # Standing rule #1: every paid call goes through genlog. Anthropic spend
    # belongs in the same ledger as fal — v1 and v2 were logged retroactively
    # after being run outside it, which is exactly what this prevents.
    try:
        sys.path.insert(0, str(ROOT / "virtual-closet/scripts"))
        from genlog import log_generation
        log_generation(
            model=args.model,
            prompt="Track D.1 style profile from closet + looks + wears + verdicts",
            purpose="style-profile",
            cost_usd=round(spent, 4),
            outcome="pass",
            extra={"input_tokens": resp.usage.input_tokens,
                   "output_tokens": resp.usage.output_tokens},
        )
    except Exception as exc:                       # never lose the profile to a
        print("WARNING: genlog write failed (%s)" % exc, file=sys.stderr)

    data = json.loads(SNAPSHOT.read_text())
    profile = dict(body)
    profile.update({
        "version": prev.get("version", 0) + 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "user_edits": user_edits,        # re-attached: never model-authored
        "model": args.model,
        "cost_usd": round(spent, 4),
        # what the profile was read FROM, so a stale one is obvious on sight
        "evidence": {
            "published_looks": sum(1 for o in data["outfits"]
                                   if o.get("source") == "manual"),
            "logged_wears": len(data["wears"]),
            "garments": len(data["garments"]),
        },
    })
    PROFILE.write_text(json.dumps(profile, indent=2) + "\n")

    print("\nv%d written to %s  (actual cost $%.4f: %d in / %d out)"
          % (profile["version"], PROFILE.name, spent,
             resp.usage.input_tokens, resp.usage.output_tokens))
    print("\n" + profile["summary"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
