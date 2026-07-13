# Virtual Closet

Photorealistic virtual try-on with a persistent personal avatar. Full plan: `docs/virtual-closet-execution-plan.md`. Environment verification: `docs/phase0-report.md`.

## Status

- ✅ Phase 0 — environment verified (local machine, all API routes open)
- ✅ Phase 1 — scaffold + data layer (this repo)
- ✅ Phase 2 — avatar calibration — **avatar-v1 LOCKED** (4-view sheet in `avatar/avatar-v1/`; face-swap finishing pass is standing policy, see docs/decisions.md)
- ⏸ Phase 3 — try-on benchmark — unblocked (avatar locked, garments clean), awaiting user-approved spend envelope
- ✅ Phase 4 — closet app — local server + fitting-room UI, "The Boutique" design (313NY tokens); generation gated behind `ENABLE_GENERATION=1`, copy-prompt mode default
- ⏸ Phase 5 — full closet ingestion

## Layout

```
avatar/            measurements.json, reference-photos/ (gitignored), character sheet, versions/
garments/          one folder per item: <slug>/{raw/, clean/, meta.json} — schema in meta.schema.json
renders/           try-on outputs + smoke tests
prompts/v1/        avatar.md, tryon.md, edit.md, qa.md (versioned; wins get promoted to v2+)
logs/              generations.jsonl (every API call), budget.json (hard spend cap)
scripts/           genlog.py (logger + cost meter), fal_generate.py (fal queue client)
app/               React closet app (Phase 4)
docs/              plan, phase reports
```

## Commands

```bash
python3 scripts/genlog.py summary          # spend vs cap
python3 scripts/genlog.py set-cap 25.00    # change budget cap (deliberate act)
python3 scripts/fal_generate.py --smoke-test   # Phase 0.2: verify FAL_KEY works (~$0.04)
```

## To unblock Phase 2 (user actions)

1. `cp .env.example .env` and paste your `FAL_KEY`.
2. Fill `avatar/measurements.json`.
3. Drop 3–6 face photos into `avatar/reference-photos/` (front, 3/4 left, 3/4 right; ≥1024px short side; even lighting). Optional: one full-body photo in fitted clothing.
4. Confirm budget cap (default $25) and privacy: face photos are sent to fal.ai (and Google if the Gemini arm is used).

## Privacy notes

- `.env` and `avatar/reference-photos/` are gitignored.
- This repo is **local-only**. If you add a GitHub remote, keep it private and note that `renders/` and the character sheet contain your likeness.
