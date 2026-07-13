# Phase 3 — Try-on benchmark (2026-07-13)

**Setup:** 5 benchmark garments × 3 arms, each render finished with the `fal-ai/face-swap`
identity pass (avatar-v1 standing policy). Inputs: `avatar/avatar-v1/front.png` + best clean
garment asset. One render per cell, first-shot quality (no retries), same prompt template
for both Nano Banana arms.

**Arms:**
- `nb-pro` — fal-ai/nano-banana-pro, $0.134/render (+$0.02 swap)
- `nb2` — fal-ai/nano-banana-2/edit, $0.039/render (+$0.02 swap)
- `idm-vton` — fal-ai/idm-vton specialist, $0.03/render (+$0.02 swap)

## Scores (garment fidelity / identity hold / outfit continuity / artifacts, 1–10)

| Garment | nb-pro | nb2 | idm-vton |
|---|---|---|---|
| 01 draped mock-neck top | 7 — garment excellent but **removed the leggings** (rendered underwear) | **9 — winner.** Washed-black cast correct, buttons present, leggings kept | 7 — good drape, side buttons faded |
| 02 wide-leg trousers | 1 — **two-panel collage**, hallucinated houndstooth outfit | **8 — winner.** Trousers correct, leg slightly slimmer than ref | 2 — draped trousers as a *top* (missing category param) |
| 03 printed plissé dress | 6 — print/pleats good but hallucinated a collar + button placket | **9 — winner.** Print placement, mock neck, side slits all correct | 3 — cropped dress into a top (category param) |
| 04 tailored blazer | 6 — tailoring good but grey instead of black, framing cropped to 3/4 | **9 — winner.** True black, worn open over tank, full body | 4 — closed with nothing underneath; hair turned into a bob |
| 05 draped jersey maxi | 7 — drape good, color drifted near-black, skirt too A-line | **9 — winner.** Slate-grey correct, hip-wrap drape, bias flow | 2 — mangled into a one-shoulder top (category param) |

## Verdict

**Default pipeline: `nb2` (fal-ai/nano-banana-2/edit) + face-swap finish — $0.059/render.**
A clean 5/5 sweep for the cheapest arm. NB2/edit behaves like an *editor* (it keeps the
base image and changes only the garment), which is exactly the try-on job. NB Pro behaves
like a *creative director* — better single-image quality ceiling, but it re-stages the
scene: collages (1/5), removed base clothing (1/5), color drift, framing changes. Identity
was a non-issue in all arms because the face-swap pass guarantees it by construction.

**IDM-VTON caveat:** 3 of its 5 failures are an integration gap, not a model gap — we never
passed its garment `category` (upper/lower/dresses; defaults to upper). Worth a $0.15
re-test someday, but with nb2 at $0.059 doing a 5/5 sweep there's no current need.

**Known nb2 weaknesses to watch:** slight garment slimming (02), content checker is
stricter than Pro's (prompt template must stay neutrally worded — see tryon.py).

## Cost

Benchmark round ≈ $1.42 (incl. swaps, one nb2 collage discard, one flagged-prompt retry).
Running total: see `python3 scripts/genlog.py summary`.

## Config

- App default arm: `nb2` (server env `TRYON_ARM`, default in `scripts/tryon.py`)
- Renders land as `renders/<garment>_<arm>_v1_<n>.png` (`_raw` = pre-swap intermediate)
