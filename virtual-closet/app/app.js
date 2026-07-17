let M = null;                 // manifest
let currentGarment = null;    // garment shown on stage
let currentRender = null;     // render path shown on stage
let filter = "all";
const POSES = ["front", "contrapposto", "hand-on-hip", "34turn"];
const SLOTS = ["top", "bottom", "layer", "shoes"];
const outfit = JSON.parse(localStorage.getItem("outfit") || "{}");

const $ = (s) => document.querySelector(s);

// crossfade the mirror whenever its image changes
window.addEventListener("DOMContentLoaded", () => {
  const img = $("#stage-img");
  new MutationObserver(() => img.classList.add("loading"))
    .observe(img, { attributes: true, attributeFilter: ["src"] });
  img.addEventListener("load", () => img.classList.remove("loading"));
});

async function refreshManifest() {
  M = await (await fetch("/api/manifest")).json();
  $("#cost-meter").textContent = `$${M.spend.spent_usd.toFixed(2)} / $${M.spend.cap_usd.toFixed(0)}`;
}

async function boot() {
  await refreshManifest();
  $("#avatar-status").textContent = "avatar: " + (M.avatar.locked_version || "draft (unlocked)");
  $("#gen-mode").textContent = M.generation_enabled ? "generation: LIVE" : "generation: copy-prompt mode";
  await migrateLegacySaves();
  showAvatar();
  renderFilters();
  renderGrid();
  renderSlots();
  renderSaved();
  setupDropZones();
  consumeIncomingLook();
  const first = M.garments.find((g) => g.photos[0]);
  if (first) previewGarment(first.id);   // the preview frame is never empty
}

// pre-looks.json saves lived in localStorage; move them to server drafts once
async function migrateLegacySaves() {
  const legacy = JSON.parse(localStorage.getItem("savedOutfits") || "[]");
  if (!legacy.length) return;
  for (const o of legacy) {
    const items = [...new Set(Object.values(o.slots || {}))].filter(Boolean);
    if (!items.length) continue;
    await fetch("/api/looks", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: o.name, items }),
    });
  }
  localStorage.removeItem("savedOutfits");
  await refreshManifest();
  toast(`migrated ${legacy.length} saved outfit(s) to looks`);
}

// plain header navigation gets a quiet crossfade, not a figure-to-figure morph
document.querySelector('.strip-left a[href="/"]').addEventListener("click", () => {
  $("#stage-img").style.viewTransitionName = "none";
});

// the archive's "open in fitting room" door
function consumeIncomingLook() {
  const raw = localStorage.getItem("incomingLook");
  if (!raw) return;
  localStorage.removeItem("incomingLook");
  try {
    const { title, items, kind } = JSON.parse(raw);
    SLOTS.forEach((s) => delete outfit[s]);
    items.forEach((gid) => {
      const g = M.garments.find((x) => x.id === gid);
      if (g) equip(g);
    });
    localStorage.setItem("outfit", JSON.stringify(outfit));
    renderSlots();
    if (kind === "garment" && items.length === 1) {
      tryOn(items[0]);   // its newest front render goes on stage
    }                    // looks arrive as loaded slots + base avatar (front-only stage)
    toast(`from the archive: ${title}`);
  } catch { /* stale handoff — ignore */ }
}

function showAvatar() {
  currentRender = null;
  currentGarment = null;
  if (M.avatar.draft) {
    $("#stage-img").src = M.avatar.draft;
    const v = M.avatar.locked_version || "draft";
    $("#stage-caption").textContent = `base avatar (${v}) — click a garment to try on`;
  } else {
    $("#stage-caption").textContent = "no avatar yet — Phase 2 pending";
  }
  $("#feedback-bar").hidden = true;
}

function renderFilters() {
  const cats = ["all", ...new Set(M.garments.map((g) => g.category))];
  $("#filters").innerHTML = cats
    .map((c) => `<button class="filter ${c === filter ? "on" : ""}" data-c="${c}">${c}</button>`)
    .join("");
  document.querySelectorAll(".filter").forEach((b) =>
    b.addEventListener("click", () => { filter = b.dataset.c; renderFilters(); renderGrid(); }));
}

function renderGrid() {
  const items = M.garments.filter((g) => filter === "all" || g.category === filter);
  $("#garment-grid").innerHTML = items.map((g) => {
    const num = /^\d+/.exec(g.id)?.[0] ?? "";
    return `<div class="row" data-id="${g.id}">
      <span class="row-num">${num}</span>
      <span class="row-name">${g.brand ? `<span class="row-brand">${g.brand}</span>` : ""}${g.name}</span>
      <span class="row-diff">${"◆".repeat(g.difficulty)}</span>
    </div>`;
  }).join("");
  document.querySelectorAll("#garment-grid .row").forEach((r) => {
    r.addEventListener("click", () => tryOn(r.dataset.id));
    r.addEventListener("mouseenter", () => previewGarment(r.dataset.id));
    // drag-to-dress: rows can be dragged onto the mirror or a manifest slot
    r.draggable = true;
    r.addEventListener("dragstart", (e) => {
      draggedId = r.dataset.id;
      e.dataTransfer.setData("text/plain", r.dataset.id);
      e.dataTransfer.effectAllowed = "copy";
      previewGarment(r.dataset.id);
      const ghost = $("#rack-preview-img");
      if (ghost && ghost.complete && ghost.naturalWidth) {
        e.dataTransfer.setDragImage(ghost, 48, 64);
      }
      document.body.classList.add("dragging");
    });
    r.addEventListener("dragend", endDrag);
  });
}

function previewGarment(id) {
  const g = M.garments.find((x) => x.id === id);
  if (g && g.photos[0]) $("#rack-preview-img").src = g.photos[0];
}

function tryOn(id) {
  const g = M.garments.find((x) => x.id === id);
  currentGarment = g;
  if (g.renders.length) {
    // newest render for this garment goes on stage
    currentRender = g.renders[g.renders.length - 1];
    $("#stage-img").src = currentRender;
    $("#stage-caption").textContent = `${g.name} — render ${g.renders.length}/${g.renders.length}`;
    $("#feedback-bar").hidden = false;
    equip(g);
  } else if (!g.photos.length) {
    toast(`add a photo first: garments/${g.id}/raw/`);
  } else if (M.generation_enabled) {
    generateRender(g);
    equip(g);
  } else {
    // no render yet -> copy-prompt mode
    openPromptModal(g);
    equip(g);
  }
}

async function generateRender(g) {
  $("#stage-caption").textContent = `rendering ${g.name}… (~1 min, billed)`;
  $("#feedback-bar").hidden = true;
  try {
    const r = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ garment: g.id }),
    });
    const j = await r.json();
    if (!r.ok) { toast(j.error || "generation failed"); showAvatar(); return; }
    M = await (await fetch("/api/manifest")).json();
    $("#cost-meter").textContent = `$${M.spend.spent_usd.toFixed(2)} / $${M.spend.cap_usd.toFixed(0)}`;
    renderGrid();
    currentGarment = M.garments.find((x) => x.id === g.id);
    currentRender = j.render;
    $("#stage-img").src = j.render;
    $("#stage-caption").textContent = `${g.name} — fresh render`;
    $("#feedback-bar").hidden = false;
  } catch (e) {
    toast("generation failed: " + e.message);
    showAvatar();
  }
}

function naturalSlot(g) {
  return g.category === "dress" ? "top" : SLOTS.includes(g.category) ? g.category
    : g.category === "outerwear" ? "layer" : null;
}

function equip(g) {
  const slot = naturalSlot(g);
  if (slot) { outfit[slot] = g.id; localStorage.setItem("outfit", JSON.stringify(outfit)); renderSlots(); }
}

/* ── drag-to-dress: drop a rack item on the mirror (auto-slot) or a manifest
   slot (must match). Drop position carries no other meaning — nb2 places
   garments by category; the drop is slot assignment, nothing else. ── */
let draggedId = null;
let savedCaption = null;

function endDrag() {
  draggedId = null;
  document.body.classList.remove("dragging");
  document.querySelectorAll(".drop-hot").forEach((el) => el.classList.remove("drop-hot"));
  restoreCaption();
}

function restoreCaption() {
  if (savedCaption !== null) { $("#stage-caption").textContent = savedCaption; savedCaption = null; }
}

function setupDropZones() {
  const frame = $("#stage-frame");
  frame.addEventListener("dragover", (e) => {
    if (!draggedId) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    frame.classList.add("drop-hot");
    if (savedCaption === null) savedCaption = $("#stage-caption").textContent;
    const g = M.garments.find((x) => x.id === draggedId);
    $("#stage-caption").textContent = g ? `drop to wear — ${g.name}` : "drop to wear";
  });
  frame.addEventListener("dragleave", (e) => {
    if (frame.contains(e.relatedTarget)) return;
    frame.classList.remove("drop-hot");
    restoreCaption();
  });
  frame.addEventListener("drop", (e) => {
    e.preventDefault();
    const gid = draggedId || e.dataTransfer.getData("text/plain");
    savedCaption = null;   // tryOn writes the real caption
    endDrag();
    if (gid) tryOn(gid);
  });

  // manifest rail: only the matching slot lights up / accepts
  const rail = $("#outfit-slots");
  rail.addEventListener("dragover", (e) => {
    const slotEl = e.target.closest(".slot");
    if (!slotEl || !draggedId) return;
    const g = M.garments.find((x) => x.id === draggedId);
    if (!g || naturalSlot(g) !== slotEl.dataset.s) return;   // incompatible: not a target
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    slotEl.classList.add("drop-hot");
  });
  rail.addEventListener("dragleave", (e) => {
    const slotEl = e.target.closest(".slot");
    if (slotEl && !slotEl.contains(e.relatedTarget)) slotEl.classList.remove("drop-hot");
  });
  rail.addEventListener("drop", (e) => {
    const slotEl = e.target.closest(".slot");
    if (!slotEl) return;
    e.preventDefault();
    const gid = draggedId || e.dataTransfer.getData("text/plain");
    endDrag();
    const g = M.garments.find((x) => x.id === gid);
    if (!g) return;
    if (naturalSlot(g) !== slotEl.dataset.s) {
      toast(`${g.name} wears as ${naturalSlot(g) || "…"} — drop it there or on the mirror`);
      return;
    }
    tryOn(gid);
  });
}

function renderSlots() {
  $("#outfit-slots").innerHTML = SLOTS.map((s) => {
    const gid = outfit[s];
    const g = gid && M ? M.garments.find((x) => x.id === gid) : null;
    const val = g ? `${g.brand ? g.brand + " · " : ""}${g.name}` : (gid || "—");
    return `<div class="slot ${gid ? "filled" : ""}" data-s="${s}">
      <span class="slot-name">${s}</span><span class="slot-val">${val}</span></div>`;
  }).join("");
  document.querySelectorAll(".slot.filled").forEach((el) =>
    el.addEventListener("click", () => {
      delete outfit[el.dataset.s];
      localStorage.setItem("outfit", JSON.stringify(outfit));
      renderSlots();
    }));
}

function renderSaved() {
  const looks = M.looks || [];
  $("#saved-outfits").innerHTML = looks.map((l) => `
    <div class="saved" data-id="${l.id}">
      <span class="saved-title">${l.title}</span>
      <span class="saved-tags">
        ${l.state === "draft"
          ? `<button class="pub" data-id="${l.id}">publish</button>`
          : `<span class="badge">in archive</span>`}
        <button class="del" data-id="${l.id}" title="remove look">×</button>
      </span>
    </div>`).join("");
  document.querySelectorAll(".saved").forEach((el) =>
    el.addEventListener("click", () => loadLook(el.dataset.id)));
  document.querySelectorAll(".pub").forEach((b) =>
    b.addEventListener("click", (e) => { e.stopPropagation(); openPublishModal(b.dataset.id); }));
  document.querySelectorAll(".del").forEach((b) =>
    b.addEventListener("click", async (e) => {
      e.stopPropagation();
      const l = (M.looks || []).find((x) => x.id === b.dataset.id);
      if (!l || !confirm(`remove "${l.title}"? (render files stay on disk)`)) return;
      await fetch("/api/looks/delete", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: l.id }),
      });
      await refreshManifest();
      renderSaved();
      toast("look removed");
    }));
}

function loadLook(id) {
  const l = (M.looks || []).find((x) => x.id === id);
  if (!l) return;
  SLOTS.forEach((s) => delete outfit[s]);
  l.items.forEach((gid) => {
    const g = M.garments.find((x) => x.id === gid);
    if (g) equip(g);
  });
  localStorage.setItem("outfit", JSON.stringify(outfit));
  renderSlots();
  toast(`look loaded: ${l.title}`);
}

/* ── publish: draft -> rendered look in the archive (billed, pose-aware) ── */
let publishId = null;
function openPublishModal(id) {
  const l = (M.looks || []).find((x) => x.id === id);
  if (!l) return;
  if (!M.generation_enabled) { toast("generation is gated off (ENABLE_GENERATION=1)"); return; }
  publishId = id;
  const hard = l.items.some((gid) =>
    (M.garments.find((x) => x.id === gid)?.difficulty ?? 0) >= 4);
  $("#publish-note").textContent =
    `"${l.title}" gets one render in the chosen pose + a cutout, then appears in the archive.` +
    (hard ? " contains a difficulty-4+ garment — front pose recommended." : "");
  $("#pose-picker").innerHTML = POSES.map((p, i) => `
    <label class="pose-opt"><input type="radio" name="pose" value="${p}"
      ${(hard ? p === "front" : i === 0) ? "checked" : ""}> ${p}</label>`).join("");
  $("#publish-modal").showModal();
}
$("#publish-cancel").addEventListener("click", () => $("#publish-modal").close());
$("#publish-go").addEventListener("click", async () => {
  const pose = document.querySelector('input[name="pose"]:checked')?.value || "front";
  const l = (M.looks || []).find((x) => x.id === publishId);
  $("#publish-modal").close();
  if (!l) return;
  $("#stage-caption").textContent = `publishing "${l.title}"… (~1 min, billed)`;
  try {
    const r = await fetch("/api/publish", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id: l.id, pose }),
    });
    const j = await r.json();
    if (!r.ok) { toast(j.error || "publish failed"); return; }
    await refreshManifest();
    renderSaved();
    toast(`published to the archive: ${l.title} (${pose})`);
  } catch (e) {
    toast("publish failed: " + e.message);
  } finally {
    if (!currentRender) showAvatar();   // stage stays front-only; posed render lives in the archive
  }
});

$("#clear-outfit").addEventListener("click", () => {
  SLOTS.forEach((s) => delete outfit[s]);
  localStorage.setItem("outfit", JSON.stringify(outfit));
  renderSlots();
  showAvatar(); // undressed base avatar back on the stage
  toast("cleared — base avatar");
});

$("#save-outfit").addEventListener("click", async () => {
  const items = [...new Set(Object.values(outfit))].filter(Boolean);
  if (!items.length) { toast("equip at least one item first"); return; }
  const n = (M.looks || []).length + 1;
  const name = prompt("name this look:", `look ${String(n).padStart(3, "0")}`);
  if (!name) return;
  const r = await fetch("/api/looks", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: name, items }),
  });
  if (!r.ok) { toast("save failed"); return; }
  await refreshManifest();
  renderSaved();
  toast(`saved as a draft — publish it to appear in the archive`);
});

async function openPromptModal(g) {
  const r = await (await fetch(`/api/prompt?g=${encodeURIComponent(g.id)}`)).json();
  $("#prompt-text").value = r.prompt;
  $("#prompt-modal").showModal();
}
$("#copy-prompt").addEventListener("click", () => {
  navigator.clipboard.writeText($("#prompt-text").value);
  toast("prompt copied");
});
$("#close-modal").addEventListener("click", () => $("#prompt-modal").close());

document.querySelectorAll(".fb").forEach((b) =>
  b.addEventListener("click", async () => {
    const note = prompt(`"${b.dataset.b}" — optional note:`, "") ?? "";
    const live = M.generation_enabled && currentGarment;
    if (live) $("#stage-caption").textContent = `applying correction… (~1 min, billed)`;
    const r = await fetch("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        render: currentRender, garment: currentGarment?.id, button: b.dataset.b, note,
        regenerate: live,
      }),
    });
    const j = await r.json();
    if (j.render) {
      M = await (await fetch("/api/manifest")).json();
      $("#cost-meter").textContent = `$${M.spend.spent_usd.toFixed(2)} / $${M.spend.cap_usd.toFixed(0)}`;
      currentRender = j.render;
      $("#stage-img").src = j.render;
      $("#stage-caption").textContent = `${currentGarment.name} — corrected (${b.dataset.b})`;
    } else {
      if (j.error) toast(j.error);
      else toast(`logged: ${b.dataset.b}`);
      if (live) $("#stage-caption").textContent = `${currentGarment.name}`;
    }
  }));

$("#render-outfit").addEventListener("click", async () => {
  const ids = [...new Set(Object.values(outfit))].filter(Boolean);
  if (ids.length < 2) { toast("equip at least 2 items first"); return; }
  $("#stage-caption").textContent = `rendering outfit (${ids.length} items)… (~1 min, billed)`;
  $("#feedback-bar").hidden = true;
  try {
    const r = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ outfit: ids }),
    });
    const j = await r.json();
    if (!r.ok) { toast(j.error || "generation failed"); showAvatar(); return; }
    M = await (await fetch("/api/manifest")).json();
    $("#cost-meter").textContent = `$${M.spend.spent_usd.toFixed(2)} / $${M.spend.cap_usd.toFixed(0)}`;
    currentRender = j.render;
    currentGarment = null;
    $("#stage-img").src = j.render;
    $("#stage-caption").textContent = `outfit — ${ids.join(" + ")}`;
    $("#feedback-bar").hidden = false;
  } catch (e) {
    toast("generation failed: " + e.message);
    showAvatar();
  }
});

function toast(msg) {
  const t = document.createElement("div");
  t.className = "toast";
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 2200);
}

boot();
