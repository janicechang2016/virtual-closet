let M = null;                 // manifest
let currentGarment = null;    // garment shown on stage
let currentRender = null;     // render path shown on stage
let filter = "all";
const SLOTS = ["top", "bottom", "layer", "shoes"];
const outfit = JSON.parse(localStorage.getItem("outfit") || "{}");
const savedOutfits = JSON.parse(localStorage.getItem("savedOutfits") || "[]");

const $ = (s) => document.querySelector(s);

async function boot() {
  M = await (await fetch("/api/manifest")).json();
  $("#avatar-status").textContent = "avatar: " + (M.avatar.locked_version || "draft (unlocked)");
  $("#cost-meter").textContent = `$${M.spend.spent_usd.toFixed(2)} / $${M.spend.cap_usd.toFixed(0)}`;
  $("#gen-mode").textContent = M.generation_enabled ? "generation: LIVE" : "generation: copy-prompt mode";
  showAvatar();
  renderFilters();
  renderGrid();
  renderSlots();
  renderSaved();
}

function showAvatar() {
  currentRender = null;
  currentGarment = null;
  if (M.avatar.draft) {
    $("#stage-img").src = M.avatar.draft;
    $("#stage-caption").textContent = "base avatar (draft) — click a garment to try on";
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
    const img = g.photos[0]
      ? `<img class="thumb" src="${g.photos[0]}" alt="${g.name}">`
      : `<div class="thumb-empty">no photo yet<br>drop into<br>garments/${g.id}/raw/</div>`;
    return `<div class="card" data-id="${g.id}">${img}
      <div class="label">${g.name} <span class="diff">${"◆".repeat(g.difficulty)}</span></div></div>`;
  }).join("");
  document.querySelectorAll(".card").forEach((c) =>
    c.addEventListener("click", () => tryOn(c.dataset.id)));
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

function equip(g) {
  const slot = g.category === "dress" ? "top" : SLOTS.includes(g.category) ? g.category
    : g.category === "outerwear" ? "layer" : null;
  if (slot) { outfit[slot] = g.id; localStorage.setItem("outfit", JSON.stringify(outfit)); renderSlots(); }
}

function renderSlots() {
  $("#outfit-slots").innerHTML = SLOTS.map((s) => {
    const v = outfit[s];
    return `<div class="slot ${v ? "filled" : ""}" data-s="${s}">
      <span class="slot-name">${s}</span>${v || "empty"}</div>`;
  }).join("");
  document.querySelectorAll(".slot").forEach((el) =>
    el.addEventListener("click", () => {
      delete outfit[el.dataset.s];
      localStorage.setItem("outfit", JSON.stringify(outfit));
      renderSlots();
    }));
}

function renderSaved() {
  $("#saved-outfits").innerHTML = savedOutfits
    .map((o, i) => `<div class="saved" data-i="${i}">${o.name}</div>`).join("");
  document.querySelectorAll(".saved").forEach((el) =>
    el.addEventListener("click", () => {
      Object.assign(outfit, savedOutfits[el.dataset.i].slots);
      localStorage.setItem("outfit", JSON.stringify(outfit));
      renderSlots();
      toast("outfit loaded");
    }));
}

$("#save-outfit").addEventListener("click", () => {
  const name = prompt("name this outfit:", `outfit ${savedOutfits.length + 1}`);
  if (!name) return;
  savedOutfits.push({ name, slots: { ...outfit } });
  localStorage.setItem("savedOutfits", JSON.stringify(savedOutfits));
  renderSaved();
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
