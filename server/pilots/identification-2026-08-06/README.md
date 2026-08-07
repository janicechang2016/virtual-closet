# Three-garment identification pilot — 2026-08-06

Paid batch approved by Janice. The source images are the existing primary raw
photos and the ground truth is each garment's checked-in `meta.json`.

| Garment | Intended case | Result | Searches | Cost | Safety verdict |
|---|---|---:|---:|---:|---|
| `59-el-hoodie` | branded + distinctive | identified, medium confidence | 3 | $0.1468 | **fail** — brand right, exact product wrong |
| `23-issey-black-tank` | plain + dark | not identified | 0 | $0.0265 | pass — honest image-only fallback |
| `12-coucou-black-scoop-tank` | expected failure | not identified | 0 | $0.0219 | pass — honest image-only fallback |
| **Total** | | | **3** | **$0.1952** | |

## Finding

Graceful failure works. Both ambiguous garments declined to search or invent a
brand and returned nine candidate ingest fields from the image. Those fields
would reduce typing, although fabric remains inferred and the repository lacks
ground truth for formality, warmth, volume and seasons, so a defensible final
edit-count reduction requires Janice's review.

Exact-product matching is not safe yet. The hoodie image visibly says Eckhaus
Latta, but the model returned a reseller page for the **Sprayed Hoodie** rather
than the catalogued **painted band hoodie**. It then marked that mismatched
page's `fabric` and `fit` as page-derived. This is the precise plausible-wrong
failure the confirmation step was designed to contain.

The first call also invalidated the original cost model: three searches pulled
52,503 input tokens and cost $0.1468. Search is now capped at one, the estimator
budgets roughly 16k pulled-in tokens per search, and the shared hard budget gate
runs before every billable request.

## Decision

Do not enable paid identification from the public/local ingest button yet. The
button remains on its $0 stub path. The prompt now requires either a matching
product/model code or two independent matching visual details; a brand match or
unverifiable reseller result cannot unlock page provenance.

The next proof is one approved re-run of the distinctive control with the
one-search cap. Passing means either the exact product is verified or the model
honestly refuses it. Another plausible wrong product rejects the approach.
