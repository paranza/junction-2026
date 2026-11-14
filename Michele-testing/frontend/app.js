// Blueprint Takeoff frontend: vanilla JS, SVG overlays on the analysed drawing.
const $ = (s) => document.querySelector(s);
const NS = "http://www.w3.org/2000/svg";
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const CAT = {
  bedroom: ["#7c6cff", "Bedroom"], living: ["#ff8a3d", "Living / dining"], kitchen: ["#ffc53d", "Kitchen"],
  bathroom: ["#22b8cf", "Bathroom"], wc_room: ["#15aabf", "WC"], corridor: ["#adb5bd", "Corridor"],
  storage: ["#a9773b", "Storage"], stair: ["#868e96", "Stairs"], elevator: ["#495057", "Lift"],
  balcony: ["#51cf66", "Balcony / outdoor"], sauna: ["#e8590c", "Sauna"], room: ["#4dabf7", "Room"],
  office: ["#9775fa", "Office"], other: ["#ced4da", "Other"], shaft: ["#343a40", "Shaft / void"], unlabelled: ["#74c0fc", "Unlabelled room"],
};
const OBJ = {
  door: ["#e8590c", "Doors", "D"], window: ["#1c7ed6", "Windows", "W"], wc: ["#0ca678", "WC / toilets", "T"],
  washbasin: ["#3bc9db", "Washbasins", "B"], sink: ["#3bc9db", "Sinks", "S"], bathtub: ["#4263eb", "Bathtubs", "Ba"],
  shower: ["#7048e8", "Showers", "Sh"], stove: ["#f03e3e", "Stoves", "St"], washing_machine: ["#868e96", "Washing machines", "WM"],
  kitchen: ["#fab005", "Kitchen runs", "K"], sauna_stove: ["#d9480f", "Sauna stoves", "SS"],
  opening: ["#e8590c", "Openings (doors / gaps)", "O"],
};

let F = null;                 // current facts
let view = { s: 1, x: 0, y: 0 };
let layers = { rooms: true, labels: true, walls: false, units: true };
let objOn = {};
let chatHistory = [];

// ------------------------------------------------------------- status + samples
fetch("/api/health").then((r) => r.json()).then((h) => {
  $("#status").innerHTML = [
    ["PlanNet", h.plannet], ["GlyphNet", h.glyphnet], ["Gemini", h.gemini],
  ].map(([k, v]) => `<span class="pill ${v ? "ok" : "no"}">${k}</span>`).join("");
}).catch(() => {});
fetch("/api/samples").then((r) => r.json()).then((list) => {
  const sel = $("#samples");
  for (const s of list) sel.insertAdjacentHTML("beforeend", `<option value="${esc(s.path)}">${esc(s.name)}</option>`);
  if (!list.length) sel.parentElement.classList.add("hidden");
});
$("#samples").onchange = async (e) => {
  if (!e.target.value) return;
  const r = await fetch("/api/samples/" + e.target.value);
  const b = await r.blob();
  upload(new File([b], e.target.value.split("/").pop()));
};

// ------------------------------------------------------------- upload
$("#file").onchange = (e) => e.target.files[0] && upload(e.target.files[0]);
const drop = $("#drop");
["dragenter", "dragover"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.add("over"); }));
["dragleave", "drop"].forEach((t) => drop.addEventListener(t, (e) => { e.preventDefault(); drop.classList.remove("over"); }));
drop.addEventListener("drop", (e) => e.dataTransfer.files[0] && upload(e.dataTransfer.files[0]));
$("#newfile").onclick = () => { ["#stage", "#toolbar", "#panel"].forEach((s) => $(s).classList.add("hidden")); $("#drop").classList.remove("hidden"); $("#file").value = ""; };

async function upload(file) {
  $("#drop").classList.add("hidden");
  $("#busy").classList.remove("hidden");
  const steps = [...document.querySelectorAll("#steps li")];
  steps.forEach((li) => (li.className = ""));
  let i = 0;
  steps[0].className = "on";
  const timer = setInterval(() => { if (i < steps.length - 1) { steps[i].className = "done"; steps[++i].className = "on"; } }, 900);
  const fd = new FormData();
  fd.append("file", file);
  try {
    const r = await fetch("/api/analyze", { method: "POST", body: fd });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail || r.statusText);
    steps.forEach((li) => (li.className = "done"));
    await new Promise((res) => setTimeout(res, 250));
    show(j);
  } catch (err) {
    alert("Analysis failed: " + err.message);
    $("#drop").classList.remove("hidden");
  } finally {
    clearInterval(timer);
    $("#busy").classList.add("hidden");
  }
}

// ------------------------------------------------------------- render
function show(facts) {
  window.history.replaceState(null, "", "?id=" + facts.id);
  F = facts;
  chatHistory = [];
  $("#chat").innerHTML = "";
  objOn = Object.fromEntries(Object.keys(facts.summary.objects).map((k) => [k, k !== "opening"]));  // gap candidates are noisy: opt-in
  const img = $("#img");
  img.onload = () => { fit(); };
  img.src = `/api/analysis/${facts.id}/image?${Date.now()}`;
  $("#walls").src = facts.has_walls ? `/api/analysis/${facts.id}/walls` : "";
  $("#svg").setAttribute("viewBox", `0 0 ${facts.width} ${facts.height}`);
  $("#svg").setAttribute("width", facts.width);
  $("#svg").setAttribute("height", facts.height);
  ["#stage", "#toolbar", "#panel"].forEach((s) => $(s).classList.remove("hidden"));
  const src = facts.style === "geometry" ? "Image (wall geometry, no learned model)" :
    facts.style === "cubicasa" ? "Image (PlanNet residential)" :
    { dxf: "Vector DXF (exact geometry)", pdf: "PDF (text layer + PlanNet)", raster: "Image (PlanNet + GlyphNet)" }[facts.source];
  $("#fileinfo").innerHTML = `<div class="name">${esc(facts.filename)}</div>
    <div class="meta">${src} · ${facts.cached ? "cached" : facts.seconds + " s"} · ${facts.scale.m_per_px ? `scale ${(facts.scale.m_per_px * 100).toFixed(2)} cm/px (${esc(facts.scale.method)})` : `<b style="color:var(--accent)">scale not set</b>`}</div>`;
  buildLayers();
  draw();
  overview();
  roomsTab();
  takeoffTab(facts.takeoff);
  chips();
  tab("overview");
}

function el(tag, attrs, parent) {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs) e.setAttribute(k, attrs[k]);
  parent && parent.appendChild(e);
  return e;
}

function centroid(p) {
  // area-weighted polygon centroid; falls back to mean
  let a = 0, cx = 0, cy = 0;
  for (let i = 0; i < p.length; i++) {
    const [x1, y1] = p[i], [x2, y2] = p[(i + 1) % p.length];
    const f = x1 * y2 - x2 * y1; a += f; cx += (x1 + x2) * f; cy += (y1 + y2) * f;
  }
  if (Math.abs(a) < 1e-6) return p.reduce((s, q) => [s[0] + q[0] / p.length, s[1] + q[1] / p.length], [0, 0]);
  return [cx / (3 * a), cy / (3 * a)];
}

function draw() {
  const svg = $("#svg");
  svg.innerHTML = "";
  $("#walls").classList.toggle("hidden", !layers.walls || !F.has_walls);
  const unitColor = ["#e03131", "#1971c2", "#2f9e44", "#f08c00", "#9c36b5", "#0c8599", "#c2255c", "#5c940d"];
  const gR = el("g", {}, svg), gU = el("g", {}, svg), gL = el("g", {}, svg), gO = el("g", {}, svg);
  const fontBase = Math.max(10, Math.min(F.width, F.height) / 110);
  if (layers.units) F.units.forEach((u, i) => {
    if (u.polygon.length > 2) el("polygon", { class: "unit", points: u.polygon.join(" "), stroke: unitColor[i % unitColor.length], "stroke-width": 3 }, gU);
  });
  if (layers.rooms) for (const r of F.rooms) {
    if (r.polygon.length < 3) continue;
    const [col] = CAT[r.category] || CAT.other;
    const p = el("polygon", { class: "room", points: r.polygon.join(" "), fill: col, "fill-opacity": r.shaft ? 0.08 : 0.2, stroke: col, "stroke-width": 4, "stroke-linejoin": "round", "data-id": r.id }, gR);
    p.onclick = (e) => { e.stopPropagation(); select(r.id); };
    p.onmousemove = (e) => tip(e, `<b>${esc(r.name || r.category)}</b> ${r.number ? esc(r.number) : ""} · ${r.area_m2 ?? "?"} m²`);
    p.onmouseleave = () => tip();
    if (layers.labels && !r.shaft) {
      const [cx, cy] = centroid(r.polygon);
      const xs = r.polygon.map((q) => q[0]), w = Math.max(...xs) - Math.min(...xs);
      const fs = Math.max(8, Math.min(fontBase * 1.25, w / 6));
      const t = el("text", { x: cx, y: cy - fs * 0.15, "text-anchor": "middle", class: "rlabel", "font-size": fs, fill: "#111" }, gL);
      t.textContent = r.area_m2 != null ? `${(+r.area_m2).toFixed(2)} m²` : (r.name || `Room ${r.number || ""}`);
      if (r.name && w > fs * 4) {
        const t2 = el("text", { x: cx, y: cy + fs * 0.95, "text-anchor": "middle", class: "rlabel", "font-size": fs * 0.72, fill: col, style: "font-weight:600" }, gL);
        t2.textContent = r.name;
      }
    }
  }
  const rad = Math.max(7, fontBase * 0.75);
  for (const o of F.objects) {
    if (!objOn[o.type]) continue;
    const [col, , ab] = OBJ[o.type] || ["#000", o.type, "?"];
    const g = el("g", { class: "obj", "data-id": o.id, transform: `translate(${o.x},${o.y})` }, gO);
    el("circle", { class: "dot", r: rad, fill: col, "fill-opacity": 0.9, stroke: "#fff", "stroke-width": 2 }, g);
    const t = el("text", { "text-anchor": "middle", dy: rad * 0.35, "font-size": rad * (ab.length > 1 ? 0.8 : 1.05), fill: "#fff", style: "font-weight:700;pointer-events:none;font-family:Inter" }, g);
    t.textContent = ab;
    g.onclick = (e) => { e.stopPropagation(); select(o.id); };
    g.onmousemove = (e) => tip(e, `${esc((OBJ[o.type] || [0, o.type])[1])} · confidence ${(o.score * 100).toFixed(0)}%`);
    g.onmouseleave = () => tip();
  }
}

function tip(e, html) {
  const t = $("#tip");
  if (!e) return t.classList.add("hidden");
  const b = $("#viewer").getBoundingClientRect();
  t.innerHTML = html;
  t.style.left = e.clientX - b.left + 14 + "px";
  t.style.top = e.clientY - b.top + 14 + "px";
  t.classList.remove("hidden");
}

function buildLayers() {
  const L = $("#layers");
  const items = [["rooms", "Rooms", "#4dabf7"], ["labels", "Areas", "#111"], ["units", "Apartments", "#e03131"]];
  if (F.has_walls) items.push(["walls", "Walls", "#2828dc"]);
  L.innerHTML = items.map(([k, n, c]) => `<button data-l="${k}" class="${layers[k] ? "on" : ""}"><span class="sw" style="background:${c}"></span>${n}</button>`).join("") +
    Object.keys(objOn).map((k) => `<button data-o="${k}" class="${objOn[k] ? "on" : ""}"><span class="sw" style="background:${(OBJ[k] || ["#999"])[0]}"></span>${(OBJ[k] || [0, k])[1]} ${F.summary.objects[k]}</button>`).join("");
  L.querySelectorAll("button").forEach((b) => (b.onclick = () => {
    if (b.dataset.l) layers[b.dataset.l] = !layers[b.dataset.l];
    else objOn[b.dataset.o] = !objOn[b.dataset.o];
    b.classList.toggle("on");
    draw();
  }));
}

// ------------------------------------------------------------- pan / zoom
const stage = $("#stage"), canvas = $("#canvas");
function apply() { canvas.style.transform = `translate(${view.x}px,${view.y}px) scale(${view.s})`; }
function fit() {
  const b = stage.getBoundingClientRect();
  const s = Math.min((b.width - 40) / F.width, (b.height - 90) / F.height);
  view = { s, x: (b.width - F.width * s) / 2, y: (b.height - 60 - F.height * s) / 2 };
  apply();
}
function zoomAt(f, cx, cy) {
  const ns = Math.min(8, Math.max(0.05, view.s * f));
  view.x = cx - (cx - view.x) * (ns / view.s);
  view.y = cy - (cy - view.y) * (ns / view.s);
  view.s = ns; apply();
}
stage.addEventListener("wheel", (e) => {
  e.preventDefault();
  const b = stage.getBoundingClientRect();
  zoomAt(e.deltaY < 0 ? 1.15 : 1 / 1.15, e.clientX - b.left, e.clientY - b.top);
}, { passive: false });
let drag = null;
stage.addEventListener("mousedown", (e) => { drag = { x: e.clientX - view.x, y: e.clientY - view.y, moved: false }; stage.classList.add("drag"); });
window.addEventListener("mousemove", (e) => { if (!drag) return; view.x = e.clientX - drag.x; view.y = e.clientY - drag.y; drag.moved = true; apply(); });
window.addEventListener("mouseup", () => { drag = null; stage.classList.remove("drag"); });
stage.addEventListener("click", (e) => { if (e.target === stage || e.target.id === "img") select(null); });
$("#zin").onclick = () => { const b = stage.getBoundingClientRect(); zoomAt(1.3, b.width / 2, b.height / 2); };
$("#zout").onclick = () => { const b = stage.getBoundingClientRect(); zoomAt(1 / 1.3, b.width / 2, b.height / 2); };
$("#zfit").onclick = fit;
window.addEventListener("resize", () => F && fit());

function focusOn(ids) {
  const pts = [];
  for (const id of ids) {
    const r = F.rooms.find((x) => x.id === id);
    if (r) pts.push(...r.polygon);
    const o = F.objects.find((x) => x.id === id);
    if (o) pts.push([o.x - 30, o.y - 30], [o.x + 30, o.y + 30]);
  }
  if (!pts.length) return;
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  const b = stage.getBoundingClientRect();
  const s = Math.min(3, (b.width - 120) / (x1 - x0 + 1), (b.height - 180) / (y1 - y0 + 1));
  view = { s, x: b.width / 2 - ((x0 + x1) / 2) * s, y: (b.height - 60) / 2 - ((y0 + y1) / 2) * s };
  canvas.style.transition = "transform .35s ease"; apply();
  setTimeout(() => (canvas.style.transition = ""), 400);
}

function highlight(ids) {
  const set = new Set(ids);
  document.querySelectorAll("#svg .room, #svg .obj").forEach((n) => {
    n.classList.toggle("dim", set.size > 0 && !set.has(n.dataset.id));
    n.classList.toggle("sel", set.has(n.dataset.id));
  });
}

// ------------------------------------------------------------- selection detail
function select(id) {
  const d = $("#detail");
  if (!id) { highlight([]); d.classList.add("hidden"); return; }
  highlight([id]);
  const r = F.rooms.find((x) => x.id === id);
  const o = F.objects.find((x) => x.id === id);
  let html = `<button class="x" onclick="select(null)">×</button>`;
  if (r) {
    const t = (F.takeoff.rooms || []).find((x) => x.id === id) || {};
    const objs = F.objects.filter((x) => x.room === id);
    const cnt = {};
    objs.forEach((x) => (cnt[x.type] = (cnt[x.type] || 0) + 1));
    html += `<h4>${esc(r.name || (CAT[r.category] || CAT.other)[1])} ${r.number ? `<span style="color:var(--muted)">${esc(r.number)}</span>` : ""}</h4>
      <div class="src">${esc((CAT[r.category] || CAT.other)[1])}${r.unit ? " · apartment " + esc(r.unit) : ""}${r.outdoor ? " · outdoor" : ""}</div>
      <div class="kv">
        <span>Net area</span><b>${r.area_m2 ?? "?"} m²</b>
        <span>Source</span><span>${esc(r.area_source)}</span>
        ${r.area_geom_m2 != null ? `<span>Geometry check</span><span>${r.area_geom_m2} m² ${r.area_m2 ? `(${(((r.area_geom_m2 / r.area_m2) - 1) * 100).toFixed(1)}%)` : ""}</span>` : ""}
        <span>Perimeter</span><span>${t.perimeter_m ?? "?"} m</span>
        <span>Wall surface</span><span>${t.wall_m2 ?? "?"} m² at ${F.takeoff.assumptions.ceiling_height_m} m</span>
        <span>Contains</span><span>${Object.entries(cnt).map(([k, v]) => `${v} ${(OBJ[k] || [0, k])[1].toLowerCase()}`).join(", ") || "no detected objects"}</span>
        <span>Confidence</span><span>${(r.confidence * 100).toFixed(0)}%</span>
      </div>`;
  } else if (o) {
    const room = F.rooms.find((x) => x.id === o.room);
    html += `<h4>${esc((OBJ[o.type] || [0, o.type])[1].replace(/s$/, ""))}</h4>
      <div class="kv"><span>Position</span><span>${o.x}, ${o.y} px</span><span>In room</span><span>${room ? esc(room.name || room.category) + " " + esc(room.number || "") : "none"}</span>
      <span>Confidence</span><span>${(o.score * 100).toFixed(0)}%</span><span>Method</span><span>${F.source === "dxf" ? "DXF entity (exact)" : "PlanNet heatmap peak"}</span></div>`;
  }
  d.innerHTML = html;
  d.classList.remove("hidden");
}
window.select = select;

// ------------------------------------------------------------- tabs
document.querySelectorAll(".tabs button").forEach((b) => (b.onclick = () => tab(b.dataset.tab)));
function tab(name) {
  document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("on", b.dataset.tab === name));
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("on", t.id === "tab-" + name));
}

function overview() {
  const S = F.summary;
  const n = (k) => (F.style === "geometry" ? "—" : S.objects[k] || 0);
  let html = `<div class="cards">
    <div class="card big"><div class="k">Net indoor floor area</div><div class="v">${S.net_area_m2 != null ? S.net_area_m2.toFixed(2) + " <small>m²</small>" : `<button class="btn primary" onclick="startScale()">Set scale to measure</button>`}</div></div>
    <div class="card"><div class="k">Rooms</div><div class="v">${S.rooms}</div></div>
    <div class="card"><div class="k">Apartments</div><div class="v">${F.style === "geometry" || F.style === "cubicasa" ? "—" : S.apartments}</div></div>
    <div class="card"><div class="k">Doors</div><div class="v">${n("door")}</div></div>
    <div class="card"><div class="k">Windows</div><div class="v">${n("window")}</div></div>
  </div>`;
  // features appear grouped by category, each clickable
  const cats = {};
  F.rooms.forEach((r) => (cats[r.category] = cats[r.category] || []).push(r));
  html += `<h3>Rooms by type</h3>`;
  let d = 0;
  for (const [c, rs] of Object.entries(cats).sort((a, b) => b[1].length - a[1].length)) {
    const [col, name] = CAT[c] || CAT.other;
    const area = rs.reduce((s, r) => s + (r.area_m2 || 0), 0);
    const known = rs.every((r) => r.area_m2 != null);
    html += `<div class="feat" style="animation-delay:${(d++) * 40}ms" data-ids="${rs.map((r) => r.id).join(",")}"><span class="sw" style="background:${col}"></span><span class="n">${name}</span><span class="c">${rs.length}${known ? ` · ${area.toFixed(1)} m²` : ""}</span></div>`;
  }
  html += `<h3>Detected objects</h3>`;
  for (const [k, v] of Object.entries(S.objects).sort((a, b) => b[1] - a[1])) {
    const [col, name] = OBJ[k] || ["#999", k];
    const ids = F.objects.filter((o) => o.type === k).map((o) => o.id);
    html += `<div class="feat" style="animation-delay:${(d++) * 40}ms" data-ids="${ids.join(",")}"><span class="sw" style="background:${col};border-radius:50%"></span><span class="n">${name}</span><span class="c">${v}</span></div>`;
  }
  if (F.units.length) {
    html += `<h3>Apartments</h3>`;
    for (const u of F.units) {
      const ids = F.rooms.filter((r) => r.unit === u.id).map((r) => r.id);
      html += `<div class="feat" data-ids="${ids.join(",")}"><span class="sw" style="background:#e03131"></span><span class="n">Apartment ${esc(u.id)}</span><span class="c">${ids.length} rooms · ${u.area_m2} m²</span></div>`;
    }
  }
  if (F.warnings?.length) html += F.warnings.slice(0, 6).map((w) => `<div class="warn">${esc(w)}</div>`).join("");
  $("#tab-overview").innerHTML = html;
  bindFeat("#tab-overview");
}

function bindFeat(root) {
  document.querySelectorAll(root + " [data-ids]").forEach((n) => (n.onclick = () => {
    const ids = n.dataset.ids.split(",").filter(Boolean);
    highlight(ids); focusOn(ids);
  }));
}

function roomsTab() {
  const rows = [...F.rooms].sort((a, b) => String(a.number || "zz").localeCompare(String(b.number || "zz"), undefined, { numeric: true }));
  $("#tab-rooms").innerHTML = `<table><thead><tr><th>No.</th><th>Name</th><th>Apt</th><th class="num">Area m²</th></tr></thead><tbody>
    ${rows.map((r) => `<tr class="click" data-ids="${r.id}"><td>${esc(r.number || "–")}</td><td><span class="sw" style="display:inline-block;width:8px;height:8px;border-radius:2px;background:${(CAT[r.category] || CAT.other)[0]};margin-right:6px"></span>${esc(r.name || (CAT[r.category] || CAT.other)[1])}<div class="src">${esc(r.area_source || "")}</div></td><td>${esc(r.unit || "")}</td><td class="num">${r.area_m2 ?? "?"}</td></tr>`).join("")}
    </tbody></table>`;
  document.querySelectorAll("#tab-rooms tr[data-ids]").forEach((n) => (n.onclick = () => { select(n.dataset.ids); focusOn([n.dataset.ids]); }));
}

function takeoffTab(T) {
  const t = T.totals, a = T.assumptions;
  $("#tab-takeoff").innerHTML = `
    <div class="controls">
      <label>Ceiling height (m)<input id="ch" type="number" step="0.05" min="1.8" max="6" value="${a.ceiling_height_m}"></label>
      <label>Waste (%)<input id="wf" type="number" step="1" min="0" max="50" value="${Math.round(a.waste_factor * 100)}"></label>
      <button class="btn" id="recalc">Recalculate</button><button class="btn" id="csv">CSV</button>
    </div>
    <div class="cards">
      <div class="card"><div class="k">Flooring to order</div><div class="v">${t.flooring_order_m2 ?? "?"} <small>m²</small></div></div>
      <div class="card"><div class="k">Skirting boards</div><div class="v">${t.skirting_m ?? "?"} <small>m</small></div></div>
      <div class="card"><div class="k">Wall paint</div><div class="v">${t.paint_m2 ?? "?"} <small>m²</small></div></div>
      <div class="card"><div class="k">Wet-room wall tiles</div><div class="v">${t.wall_tiles_m2 ?? "?"} <small>m²</small></div></div>
    </div>
    <div class="formula">${esc(a.formula)}</div>
    <table><thead><tr><th>Room</th><th class="num">Floor</th><th class="num">Perim.</th><th class="num">Walls</th><th class="num">D/W</th></tr></thead><tbody>
    ${T.rooms.filter((r) => !r.outdoor).map((r) => `<tr class="click" data-ids="${r.id}"><td>${esc(r.number || "")} ${esc(r.name || r.category)}</td><td class="num">${r.floor_m2}</td><td class="num">${r.perimeter_m}</td><td class="num">${r.wall_m2}</td><td class="num">${r.doors}/${r.windows}</td></tr>`).join("")}
    </tbody></table>`;
  document.querySelectorAll("#tab-takeoff tr[data-ids]").forEach((n) => (n.onclick = () => { select(n.dataset.ids); focusOn([n.dataset.ids]); }));
  $("#recalc").onclick = async () => {
    const r = await fetch(`/api/analysis/${F.id}/takeoff?ceiling_h=${$("#ch").value}&waste=${$("#wf").value / 100}`);
    const j = await r.json();
    if (!r.ok) return alert(j.detail);
    F.takeoff = j; takeoffTab(j);
  };
  $("#csv").onclick = () => {
    const cols = ["number", "name", "category", "floor_m2", "perimeter_m", "wall_m2", "doors", "windows", "flooring_order_m2", "skirting_m", "paint_m2", "wall_tiles_m2"];
    const csv = [cols.join(",")].concat(T.rooms.map((r) => cols.map((c) => `"${String(r[c] ?? "").replace(/"/g, '""')}"`).join(","))).join("\n");
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = (F.filename || "takeoff").replace(/\.[^.]+$/, "") + "_takeoff.csv";
    a.click();
  };
}

// ------------------------------------------------------------- ask
function chips() {
  const qs = ["How many doors are drawn on this floor plan?", "How many windows are drawn on this floor plan?",
    "How many washbasins are drawn on this floor plan?", "What is the total net floor area in m² of all numbered indoor rooms on this floor?"];
  if (F.units[0]) qs.push(`What is the net floor area of apartment ${F.units[0].id} in m²?`);
  qs.push("How many litres of paint do I need for all bedrooms at 10 m² per litre, two coats?");
  $("#chips").innerHTML = qs.map((q) => `<button>${esc(q.length > 46 ? q.slice(0, 44) + "…" : q)}</button>`).join("");
  $("#chips").querySelectorAll("button").forEach((b, i) => (b.onclick = () => ask(qs[i])));
}
$("#askform").onsubmit = (e) => { e.preventDefault(); const q = $("#q").value.trim(); if (q) ask(q); $("#q").value = ""; };

async function ask(q) {
  tab("ask");
  const chat = $("#chat");
  chat.insertAdjacentHTML("beforeend", `<div class="msg q">${esc(q)}</div>`);
  const pending = document.createElement("div");
  pending.className = "msg a"; pending.textContent = "…";
  chat.appendChild(pending); chat.scrollTop = chat.scrollHeight;
  try {
    const r = await fetch(`/api/analysis/${F.id}/ask`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ question: q, history: chatHistory }) });
    const j = await r.json();
    if (!r.ok) throw new Error(j.detail);
    const det = (j.method || "").startsWith("deterministic");
    const ev = (j.evidence || []).filter((id) => F.rooms.some((x) => x.id === id) || F.objects.some((x) => x.id === id));
    pending.innerHTML = `<div class="val">${esc(j.answer)}</div>${j.explanation ? `<div class="how">${esc(j.explanation)}</div>` : ""}
      ${ev.length ? `<div class="ev">Show ${ev.length} evidence item${ev.length > 1 ? "s" : ""} on the drawing →</div>` : ""}
      <span class="meth ${det ? "det" : ""}">${esc(j.method)}${j.tokens && j.tokens.in ? ` · ${j.tokens.in}+${j.tokens.out} tokens` : ""}</span>`;
    const evl = pending.querySelector(".ev");
    if (evl) { evl.onclick = () => { highlight(ev); focusOn(ev); }; highlight(ev); }
    chatHistory.push({ q, a: j.answer });
  } catch (err) {
    pending.textContent = "Error: " + err.message;
  }
  chat.scrollTop = chat.scrollHeight;
}

// ------------------------------------------------------------- shareable links: /?id=<analysis id>
(async () => {
  const id = new URLSearchParams(location.search).get("id");
  if (!id) return;
  const r = await fetch(`/api/analysis/${encodeURIComponent(id)}`);
  if (r.ok) { $("#drop").classList.add("hidden"); show(await r.json()); }
})();


// ------------------------------------------------------------- scale calibration: click two points of a known length
let scaleMode = null;
function toImg(e) {
  const b = stage.getBoundingClientRect();
  return [(e.clientX - b.left - view.x) / view.s, (e.clientY - b.top - view.y) / view.s];
}
function startScale() {
  scaleMode = { pts: [] };
  stage.style.cursor = "crosshair";
  tip({ clientX: stage.getBoundingClientRect().left + 20, clientY: stage.getBoundingClientRect().top + 20 },
      "Click both ends of a dimension you know (e.g. a wall with a written length)");
}
window.startScale = startScale;
stage.addEventListener("click", async (e) => {
  if (!scaleMode || (drag && drag.moved)) return;
  e.stopPropagation();
  scaleMode.pts.push(toImg(e));
  const svg = $("#svg");
  const [x, y] = scaleMode.pts[scaleMode.pts.length - 1];
  el("circle", { cx: x, cy: y, r: 6 / view.s + 2, fill: "#ffb020", stroke: "#000", "stroke-width": 1 }, svg);
  if (scaleMode.pts.length < 2) return;
  const [[x1, y1], [x2, y2]] = scaleMode.pts;
  el("line", { x1, y1, x2, y2, stroke: "#ffb020", "stroke-width": 3 / view.s + 1 }, svg);
  const px = Math.hypot(x2 - x1, y2 - y1);
  scaleMode = null; stage.style.cursor = ""; tip();
  const v = prompt(`Real length of this line in metres? (${px.toFixed(0)} px)`, "");
  const m = parseFloat((v || "").replace(",", "."));
  if (!m) return draw();
  const r = await fetch(`/api/analysis/${F.id}/scale`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ px_length: px, meters: m }) });
  const j = await r.json();
  if (!r.ok) { alert(j.detail); return draw(); }
  const keep = { ...view };
  show(j); view = keep; apply();
}, true);
