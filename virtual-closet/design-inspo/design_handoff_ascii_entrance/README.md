# Handoff: ASCII Entrance (edge-trace cover page)

## Overview
A cover/entrance page for a portfolio site. A photograph is overlaid with ASCII characters (drawn from a text passage) that trace the photo's contours. The characters twinkle continuously ("shimmer"). On click, the characters scatter haphazardly for ~1.2 s, then all sweep upward together and fade, while the photo fades to a faint ghost — revealing the site beneath.

## About the Design Files
The files in this bundle are **design references created in HTML** — a working prototype showing the intended look and behavior, not production code to copy verbatim. The task is to **integrate/recreate this in the target codebase's existing environment** (React, Vue, plain JS, etc.) using its established patterns. That said, `ascii-entrance.js` is a clean, dependency-free ES module that can be used directly if the stack allows.

## Fidelity
**High-fidelity.** The prototype was iterated with the client to final values. All parameters below are the approved defaults — implement them exactly.

## Files
- `ascii-entrance.js` — dependency-free ES module containing the complete, final effect. **Start here.** Exports `createAsciiEntrance(canvas, options)`.
- `example.html` — minimal integration example: full-viewport stage, canvas cover, underlying site content that fades in via the `onDispelled` callback.
- `interior.jpeg` — the source photograph used in the design (790×994).
- `reference/ASCII Entrance.dc.html` — the original design-tool prototype (for reference only; the module above is the portable version).

## How It Works (algorithm)
1. Load the image and sample it at character-grid resolution (`cellW = round(fontPx*0.6)`, `cellH = round(fontPx*1.02)`).
2. Compute per-cell luminance, then **contrast-normalize** to the 2nd–98th percentile range (makes the effect work on dark or light photos).
3. Run a **Sobel** filter on the normalized luminance; cells with gradient magnitude ≥ threshold get a character.
4. Characters are taken **sequentially from the text passage** (spaces skipped), so the quote literally wraps the contours.
5. Characters are pre-rendered into **4 offscreen layers**; each layer's opacity oscillates sinusoidally at a phase offset → twinkle/shimmer at ~30 fps with only 5 drawImage calls per frame.
6. On dispel, each character becomes a particle (see Interactions).

## Interactions & Behavior
- **Idle**: photo + cream veil + twinkling characters. Cursor: pointer. Twinkle alpha per layer k: `0.5 + 0.5*(0.5 + 0.5*sin(t_ms * 0.0016 * shimmerSpeed + k*1.7))`.
- **Click → dispel**, two phases:
  - **Phase 1 — haphazard scatter (0 to 1.2 s)**: each particle launches after a patchy delay `dl = (0.5+0.5*sin(x*0.011 + y*0.017))*0.4 + rand()*0.3` (noise-clustered, 0–0.7 s), moves in a random direction (speed `30 + rand()*rand()*320` px/s, slight upward bias −40, random curvature g = ±200 px/s²), and flickers: `alpha *= 0.7 + 0.3*sin(tt * fl)` with `fl = 8 + rand()*26`.
  - **Phase 2 — collective rise (from 1.2 s)**: all particles accelerate upward together, `y -= rv * tr²` with per-particle `rv = 500 + rand()*700`, fading linearly over 1.1 s.
- **Photo fade**: during dispel the photo+veil fades from 1 → **0.12 opacity over 2.4 s** and stays as a permanent faint ghost (do NOT fade to blank).
- **End state**: canvas shows only the 12% ghost; `pointer-events: none` so the revealed site is interactive; `onDispelled` callback fires (use it to fade in / enable the site).
- **Reset** (optional dev affordance): re-enables pointer events and returns to idle.
- All coordinates/speeds above are in **internal canvas px** (2× CSS px — the canvas renders at 2x resolution).

## Approved Parameter Values (final)
- `charSize`: **7** (CSS px; 14 px internal at 2×)
- `shimmerSpeed`: **2.2**
- `intensity`: **0.5** → edge threshold `0.3 + (1-i)*0.45 = 0.525`, character alpha `0.3 + 0.7*i = 0.65`, glow blur `3*i = 1.5`
- Scatter phase length: **1.2 s**; photo fade: **2.4 s**; ghost: **0.12**

## Design Tokens
- Page background: `#e7e3d5` (warm putty)
- Paper / frame background: `#f2efe6`
- Veil over photo: `rgba(242, 239, 230, 0.30)`
- Character color: `#fffdf4` (warm white), glow: same color, shadowBlur 1.5
- Ink / text color (UI chrome): `#2f3a28`; muted: `#8a8676`
- Font: **IBM Plex Mono** (400/500/600), fallback `monospace` — used for both canvas characters and UI copy
- Frame shadow: `0 18px 50px rgba(47, 58, 40, 0.16)`

## Content
Character source text (repeats as needed; spaces skipped when placing characters):

> "We are all filled with a longing for the wild. There are few culturally sanctioned antidotes for this yearning. We were taught to feel shame for this desire. We grew our hair long and used it to hide our feelings. But the shadow of the Wild Woman still lurks behind us during our days and in our nights. No matter where we are, the shadow that trots behind is definitely four-footed."

There is **no visible text after dispel** — the client removed the "enter the archive" label; the entrance simply dissolves to reveal the site.

## State Management
- `mode`: `idle → dispel → done` (one-way per session; `reset()` returns to `idle`).
- No data fetching. Wait for **image load + `document.fonts.ready`** before building the grid (character metrics depend on the loaded font).

## Integration Notes
- The canvas height is derived from the image aspect ratio; the module sizes itself from `options.width` or `canvas.clientWidth`.
- For a **full-viewport** cover, either crop the photo to the viewport aspect beforehand, or center the canvas on a stage as in `example.html`.
- Performance: idle loop is throttled to ~30 fps and costs 5 `drawImage` calls; the dispel repaints ~1–3 k glyphs per frame for ~2.5 s only.
- Respect `prefers-reduced-motion` in production: consider skipping the scatter and using a simple crossfade.
- If the site uses a router, trigger navigation in `onDispelled` (or after a short delay) rather than on click, so the animation completes.

## Assets
- `interior.jpeg` — client-provided photograph. Any photo works; contrast normalization adapts automatically, but contour-rich subjects read best.
- IBM Plex Mono via Google Fonts (or self-host in production).
