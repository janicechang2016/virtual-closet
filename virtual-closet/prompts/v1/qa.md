# Auto-QA judge — v1

**Model:** Claude vision (via API or this Claude Code session). **Attachments:** render R, garment photo G, avatar sheet front view A.

## Template

> Compare render R against garment photo G and avatar sheet A. Score 1–10 with one-line justification each: (a) identity match to A, (b) garment fidelity to G — color, pattern, construction, (c) anatomical correctness — hands, feet, joints, hairline, (d) lighting/composite coherence. List every visible artifact with location. Verdict: PASS / REGENERATE / EDIT with suggested edit instruction. Respond as JSON: {"identity": n, "garment": n, "anatomy": n, "coherence": n, "artifacts": [{"location": "", "description": ""}], "verdict": "", "edit_instruction": ""}

## Thresholds (v1, tune in Phase 3)

- PASS: all scores ≥ 7 and no artifact in face/hands
- REGENERATE: identity < 6, or ≥ 3 artifacts (stochastic retry, max 2)
- EDIT: everything else (single targeted correction via `edit.md`)

Avatar-candidate QA (Phase 2) additionally scores proportion plausibility against `measurements.json`.
