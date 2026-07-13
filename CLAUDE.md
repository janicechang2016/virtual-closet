# Virtual Closet (wardrobe-v3)

Photorealistic virtual try-on with a persistent personal avatar. Single-user, local-first.
Working code in `virtual-closet/`; plan in `virtual-closet-execution-plan.md`; running
decisions in `virtual-closet/docs/decisions.md` (read it — it carries the standing rules).

## Current state (2026-07-13)

- Phases 0–4 complete. **avatar-v1 LOCKED**: 4-view sheet in `avatar/avatar-v1/`.
- Phase 3 benchmark done (`docs/phase3-benchmark.md`): default try-on pipeline is
  **fal-ai/nano-banana-2/edit + fal-ai/face-swap finish** ($0.059/render). NB Pro is worse
  at try-on (re-stages scenes); IDM-VTON needs its `category` param wired.
- App: server `scripts/closet_server.py` → http://localhost:8765 (run with
  `ENABLE_GENERATION=1` for live spending). Single-item try-on, multi-item outfit compose,
  feedback→corrective-edit loop, clear-to-base — all working from the UI.
- Design: "The Boutique" v3 (git tag `boutique-v3`) — 313NY tokens from
  `~/liminal-wardrobe/spec/design/design-tokens.md`, soft-chrome accent variant
  (amber rejected as masculine; violet/rose rejected outright).
- Spend: ~$5.41 of $25 cap (`python3 scripts/genlog.py summary`).

## Standing rules

1. **Spending:** fal calls only in user-approved batches/envelopes. All calls go through
   `scripts/genlog.py` budget gate; never bypass it.
2. **Identity:** every render with a visible avatar face gets a `fal-ai/face-swap`
   finishing pass, source `avatar/avatar-v1/front.png`. Never edit the avatar's head
   region with NB models (edits collage or regress the face — regenerate instead).
3. **Prompts for nb2/edit must be neutrally worded** ("virtual try-on: show the person
   wearing…", never "dress the woman", no body-size adjectives) — its content checker is
   strict. Anti-collage phrasing ("one single figure, not a collage…") in every prompt.
4. **Renders:** `renders/<garment>_<arm>_v1_<n>.png`; `_raw` = pre-swap intermediate
   (excluded from the app). Garment-id prefix is how the app matches renders.

## Key commands

```bash
ENABLE_GENERATION=1 python3 scripts/closet_server.py     # app (from virtual-closet/)
python3 scripts/tryon.py <garment-id>                    # one try-on render
python3 scripts/tryon.py --outfit 01-plain-tee 02-jeans  # multi-item compose
python3 scripts/tryon.py <gid> --correct "wrong fit" --note "…"  # corrective edit
python3 scripts/genlog.py summary                        # spend vs cap
/Users/janice.chang/liminal-wardrobe/.venv/bin/python scripts/extract_garment.py  # cloth-seg cutouts
```

The liminal-wardrobe venv (Python 3.9) has rembg/cv2/PIL; system python3 is 3.9 (no
`str | None` syntax). Headless design QA: Chrome `--headless=new --screenshot=…` then
actually look at the PNG.

## Queued next (do not build until asked)

Saved outfits as **look cards** — port `~/liminal-wardrobe-v2/spec/design/CARD-PIPELINE.md`
(rembg u2net_human_seg cutout → largest-component cleanup → crop → coverflow lookbook).
