/**
 * ASCII Entrance — edge-trace shimmer + two-phase dispel
 * Framework-agnostic vanilla module. No dependencies.
 *
 * Usage:
 *   import { createAsciiEntrance } from './ascii-entrance.js';
 *   const entrance = createAsciiEntrance(canvasEl, {
 *     src: '/images/interior.jpeg',
 *     onDispelled: () => revealSite(),
 *   });
 *   // entrance.dispel() / entrance.reset() / entrance.destroy()
 *
 * The canvas height is set automatically from the image aspect ratio.
 * Rendering is done at 2x internal resolution for crispness.
 */

const DEFAULT_TEXT =
  'We are all filled with a longing for the wild. There are few culturally sanctioned antidotes for this yearning. We were taught to feel shame for this desire. We grew our hair long and used it to hide our feelings. But the shadow of the Wild Woman still lurks behind us during our days and in our nights. No matter where we are, the shadow that trots behind is definitely four-footed. ';

export function createAsciiEntrance(canvas, options = {}) {
  const opts = {
    src: options.src,
    text: options.text ?? DEFAULT_TEXT,
    charSize: options.charSize ?? 7,        // character size in CSS px (design default: 7)
    shimmerSpeed: options.shimmerSpeed ?? 2.2, // twinkle speed multiplier (design default: 2.2)
    intensity: options.intensity ?? 0.5,    // 0.15–1: edge density + char brightness (design default: 0.5)
    width: options.width ?? null,           // CSS px; defaults to canvas.clientWidth or 420
    veil: options.veil ?? 'rgba(242,239,230,0.30)', // wash over the photo
    charColor: options.charColor ?? '#fffdf4',
    ghostAlpha: options.ghostAlpha ?? 0.12, // photo opacity left after dispel
    clickToDispel: options.clickToDispel ?? true,
    onDispelled: options.onDispelled ?? null,
    fontFamily: options.fontFamily ?? "'IBM Plex Mono', monospace",
  };

  let api = { dispel: () => {}, reset: () => {}, destroy: () => {} };
  let destroyed = false;

  const img = new Image();
  img.onload = () => {
    const fontsReady = document.fonts && document.fonts.ready ? document.fonts.ready : Promise.resolve();
    fontsReady.then(() => { if (!destroyed) boot(img); });
  };
  img.src = opts.src;

  function boot(img) {
    const cssW = opts.width || canvas.clientWidth || 420;
    const W = cssW * 2;
    const H = Math.round(W * (img.height / img.width));
    canvas.width = W; canvas.height = H;
    canvas.style.width = cssW + 'px';
    canvas.style.height = (H / 2) + 'px';
    canvas.style.pointerEvents = 'auto';
    const ctx = canvas.getContext('2d');

    const fs = opts.charSize * 2;
    const font = fs + 'px ' + opts.fontFamily;
    const cellW = Math.max(4, Math.round(fs * 0.6));
    const cellH = Math.max(6, Math.round(fs * 1.02));
    const cols = Math.ceil(W / cellW), rows = Math.ceil(H / cellH);

    // --- sample image at grid resolution
    const sc = document.createElement('canvas'); sc.width = cols; sc.height = rows;
    const sx = sc.getContext('2d', { willReadFrequently: true });
    sx.drawImage(img, 0, 0, cols, rows);
    const px = sx.getImageData(0, 0, cols, rows).data;
    const lum = new Float32Array(cols * rows);
    for (let i = 0; i < cols * rows; i++)
      lum[i] = (0.299 * px[i * 4] + 0.587 * px[i * 4 + 1] + 0.114 * px[i * 4 + 2]) / 255;

    // --- per-image contrast normalization (2nd–98th percentile stretch)
    const sorted = Float32Array.from(lum).sort();
    const lo = sorted[Math.floor(sorted.length * 0.02)];
    const hi = sorted[Math.floor(sorted.length * 0.98)];
    const rng = Math.max(0.05, hi - lo);
    for (let i = 0; i < lum.length; i++) lum[i] = Math.min(1, Math.max(0, (lum[i] - lo) / rng));

    // --- Sobel edge magnitude
    const mag = new Float32Array(cols * rows);
    for (let r = 1; r < rows - 1; r++) for (let c = 1; c < cols - 1; c++) {
      const i = r * cols + c;
      const gx = (lum[i - cols + 1] + 2 * lum[i + 1] + lum[i + cols + 1]) - (lum[i - cols - 1] + 2 * lum[i - 1] + lum[i + cols - 1]);
      const gy = (lum[i + cols - 1] + 2 * lum[i + cols] + lum[i + cols + 1]) - (lum[i - cols - 1] + 2 * lum[i - cols] + lum[i - cols + 1]);
      mag[i] = Math.sqrt(gx * gx + gy * gy);
    }

    const mk = () => { const c = document.createElement('canvas'); c.width = W; c.height = H; return c; };

    // --- base layer: photo + veil
    const base = mk(), bx = base.getContext('2d');
    bx.drawImage(img, 0, 0, W, H);
    bx.fillStyle = opts.veil;
    bx.fillRect(0, 0, W, H);

    // --- character layers (4 twinkle groups) + particle list
    const inten = opts.intensity;
    const eThresh = 0.3 + (1 - inten) * 0.45;
    const eAlpha = 0.3 + 0.7 * inten;
    const q = opts.text.replace(/\s+/g, ' ');
    const layers = [mk(), mk(), mk(), mk()];
    const xs = layers.map(L => {
      const x = L.getContext('2d');
      x.font = font; x.textBaseline = 'top';
      x.globalAlpha = eAlpha; x.fillStyle = opts.charColor;
      x.shadowColor = opts.charColor; x.shadowBlur = 3 * inten;
      return x;
    });
    const parts = [];
    let qi = 0;
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const i = r * cols + c;
      if (!mag[i] || mag[i] < eThresh) continue;
      let ch = q[qi++ % q.length]; while (ch === ' ') ch = q[qi++ % q.length];
      const k = (Math.random() * 4) | 0;
      xs[k].fillText(ch, c * cellW, r * cellH);
      parts.push({ x: c * cellW, y: r * cellH, ch, a: eAlpha });
    }

    const state = { mode: 'idle', t0: 0, raf: 0 };

    // --- idle: photo + twinkling character layers
    const drawIdle = (t) => {
      ctx.clearRect(0, 0, W, H);
      ctx.drawImage(base, 0, 0);
      for (let k = 0; k < layers.length; k++) {
        ctx.globalAlpha = 0.5 + 0.5 * (0.5 + 0.5 * Math.sin(t * 0.0016 * opts.shimmerSpeed + k * 1.7));
        ctx.drawImage(layers[k], 0, 0);
      }
      ctx.globalAlpha = 1;
    };

    // --- dispel: 1.2s haphazard scatter, then collective upward sweep
    const startDispel = () => {
      if (state.mode !== 'idle') return;
      for (const p of parts) {
        const ang = Math.random() * Math.PI * 2;
        const sp = 30 + Math.random() * Math.random() * 320;
        p.vx = Math.cos(ang) * sp;
        p.vy = Math.sin(ang) * sp - 40;
        p.g = (Math.random() - 0.5) * 400;
        p.dl = (0.5 + 0.5 * Math.sin(p.x * 0.011 + p.y * 0.017)) * 0.4 + Math.random() * 0.3;
        p.fl = 8 + Math.random() * 26;    // flicker rate
        p.rv = 500 + Math.random() * 700; // rise speed
      }
      state.mode = 'dispel';
      state.t0 = performance.now();
    };

    const drawDispel = (t) => {
      const u = (t - state.t0) / 1000;
      ctx.clearRect(0, 0, W, H);
      // photo fades slowly to a faint ghost
      const bgA = Math.max(opts.ghostAlpha, 1 - u / 2.4);
      ctx.globalAlpha = bgA; ctx.drawImage(base, 0, 0); ctx.globalAlpha = 1;
      ctx.font = font; ctx.textBaseline = 'top'; ctx.fillStyle = opts.charColor;
      let alive = false;
      for (const p of parts) {
        const tt = u - p.dl;
        let x = p.x, y = p.y, a = p.a;
        if (tt > 0) {
          x += p.vx * tt; y += p.vy * tt + 0.5 * p.g * tt * tt;
          a = p.a * (0.7 + 0.3 * Math.sin(tt * p.fl));
        }
        const tr = Math.max(0, u - 1.2); // upward phase starts at 1.2s
        if (tr > 0) {
          y -= p.rv * tr * tr;
          a *= Math.max(0, 1 - tr / 1.1);
        }
        if (a <= 0.01) continue;
        alive = true;
        ctx.globalAlpha = a;
        ctx.fillText(p.ch, x, y);
      }
      ctx.globalAlpha = 1;
      if (!alive && u > 2.4) {
        state.mode = 'done';
        ctx.clearRect(0, 0, W, H);
        ctx.globalAlpha = opts.ghostAlpha; ctx.drawImage(base, 0, 0); ctx.globalAlpha = 1;
        canvas.style.pointerEvents = 'none';
        if (opts.onDispelled) opts.onDispelled();
      }
    };

    let last = 0;
    const loop = (t) => {
      if (destroyed) return;
      state.raf = requestAnimationFrame(loop);
      if (state.mode === 'idle') { if (t - last < 33) return; last = t; drawIdle(t); }
      else if (state.mode === 'dispel') drawDispel(t);
    };
    state.raf = requestAnimationFrame(loop);

    const onClick = () => startDispel();
    if (opts.clickToDispel) canvas.addEventListener('click', onClick);

    api = {
      dispel: startDispel,
      reset: () => { state.mode = 'idle'; canvas.style.pointerEvents = 'auto'; },
      destroy: () => {
        destroyed = true;
        cancelAnimationFrame(state.raf);
        canvas.removeEventListener('click', onClick);
      },
    };
  }

  return {
    dispel: (...a) => api.dispel(...a),
    reset: () => api.reset(),
    destroy: () => { destroyed = true; api.destroy(); },
  };
}
