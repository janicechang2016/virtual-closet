# Virtual Closet (wardrobe-v3)

Photorealistic virtual try-on with a persistent personal avatar. Single-user, local-first.
Working code in `virtual-closet/`; plan in `virtual-closet-execution-plan.md`; running
decisions in `virtual-closet/docs/decisions.md` (read it — it carries the standing rules).

## Current state (2026-07-13, night)

- Phases 0–4 complete. **avatar-v1 LOCKED**: 4-view sheet in `avatar/avatar-v1/`.
- Phase 3 benchmark done (`docs/phase3-benchmark.md`): default try-on pipeline is
  **fal-ai/nano-banana-2/edit + fal-ai/face-swap finish** ($0.059/render). NB Pro is worse
  at try-on (re-stages scenes); IDM-VTON needs its `category` param wired.
- Server `scripts/closet_server.py` → http://localhost:8765 (run with
  `ENABLE_GENERATION=1` for live spending). Single-item try-on, multi-item outfit compose,
  feedback→corrective-edit loop, clear-to-base — all working from the UI.
- **One brand ("the archive."), two views, one SYVE language** (white void, black 1px
  hairlines, uppercase Helvetica, italic lowercase wordmark):
  - `/` — **SYVE-style carousel** (`app/carousel.html`, single-file): figure cutouts
    (from `scripts/cutout_render.py`, rembg u2net_human_seg), spec-faithful slot
    interpolation + infinite wrap + 80px snap/dwell, x-axis scroll + click-to-center,
    TRY ON wired to the live pipeline; hero slot at 85% of spec size (Janice: full size
    too big). Spec: `virtual-closet/design-inspo/` (docx + reel).
    A **runway-procession variant** (single-file line receding to a vanishing point, per
    `design-inspo/runway-inspo.avif`) was built and shelved same night — saved at tag
    `runway-procession-v1` (restore: `git checkout runway-procession-v1 -- virtual-closet/app/carousel.html`).
    An **auto-scroll variant** (ambient drift + hover slow-to-crawl) was built and shelved
    2026-07-14 — saved at tag `auto-drift-v1` (restore:
    `git checkout auto-drift-v1 -- virtual-closet/app/carousel.html`).
  - `/classic` — **fitting room** (outfit rail | stage | racks), restyled 07-13 late to
    the SYVE language. Old look "The Boutique" v3 (313NY tokens, soft chrome) preserved
    at git tag `boutique-v3` (revert: `git checkout boutique-v3 -- virtual-closet/app/`);
    amber rejected as masculine, violet/rose rejected outright.
  - `renders/hidden.json` — render stems the server keeps out of the app (files stay on
    disk). Size row reads `size_owned` from each garment's `meta.json`; unset = no
    highlight (log real sizes at ingest — not everything is S).
- **Janice's architectural intent (2026-07-13, to flesh out later — do not build yet):**
  the SYVE carousel likely becomes the **OUTFIT ARCHIVE** view (browsing saved looks),
  while the Boutique app remains the **FITTING ROOM** (composing/trying-on). How the two
  connect (navigation, shared state, which is home) is an open design question she wants
  to work through together. Dovetails with the queued look-cards feature.
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

- Saved outfits as **look cards** — port `~/liminal-wardrobe-v2/spec/design/CARD-PIPELINE.md`
  (rembg u2net_human_seg cutout → largest-component cleanup → crop → coverflow lookbook).
- **Avatar pose variants** (Janice, 2026-07-13 — feasibility agreed, wait for go): build a
  small **pose library** extending avatar-v1 (contrapposto, hand-on-hip, mid-stride, 3/4
  turn) via the proven turnaround recipe — generate pose base once + face-swap finish,
  ~$0.08/pose one-time. Do NOT re-pose via nb2/edit prompt language alone (it's an editor;
  re-posing fights it — benchmark first if tried). Assign **one pose per saved look** at
  creation — variance across looks, not within (multiple poses per look multiplies cost).
  Limits: keep difficulty-4/5 garments (plissé dress) on the standard front pose; stay
  within the validated 3/4 face-angle envelope for face-swap; unusual silhouettes may need
  cutout cleanup. First step when greenlit: user-approved test envelope (~$0.35 = 2 pose
  bases × 2 outfit renders). Goal: archive page reads as a varied, character-select-style
  lineup.
- **New garment ingest incoming:** Janice will provide new on-model photos at a later
  session. At ingest, fill `meta.json` per the schema **including `size_owned`** (sizes
  vary per item — never default to S) and the per-item note on what in the photo is NOT
  part of the garment.
