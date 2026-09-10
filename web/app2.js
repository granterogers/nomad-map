
/* ---------- filtering ---------- */
const LOC = decodeLocalities();
const byGid = new Map(LOC.map(L => [L.gid, L]));
const CLUSTERS = D.clusters;
let filterCache = null, filterKey = "", rankedCache = null;
function invalidateScale(){ filterCache = null; filterKey = ""; rankedCache = null; allCache = null; }
function filtered(){
  const f = S.filters;
  const key = JSON.stringify(f) + S.scale;
  if (key === filterKey && filterCache) return filterCache;
  filterKey = key; rankedCache = null;
  filterCache = LOC.filter(L => {
    if (!L.ranked) return false;
    if (f.continent && L.continent !== f.continent) return false;
    if (f.minConf && L.confidence < f.minConf) return false;
    if (f.trend && L.trend !== f.trend) return false;
    if (f.presence && L.presence !== f.presence) return false;
    if (f.size === "small" && L.pop >= 250000) return false;
    if (f.size === "mid" && (L.pop < 250000 || L.pop >= 1200000)) return false;
    if (f.size === "large" && L.pop < 1200000) return false;
    if (f.terrain === "coast" && !L.coastal) return false;
    if (f.terrain === "mountain" && (L.elev || 0) < 700) return false;
    return true;
  });
  return filterCache;
}
/* Everything observed, ranked or not - the map still shows infrastructure-only
   places, the rankings do not. */
let allCache = null;
function allLocalities(){
  if (!allCache) allCache = LOC.slice().sort((a,b) => scoreOf(b) - scoreOf(a));
  return allCache;
}
/* pins are drawn strongest-first so the cap keeps the most useful ones */
function rankedLocalities(){
  if (!rankedCache) rankedCache = filtered().slice().sort((a,b) => scoreOf(b) - scoreOf(a));
  return rankedCache;
}

/* ---------- interaction ---------- */
let drag = null, moved = 0;
cv.addEventListener("pointerdown", e => {
  cv.setPointerCapture(e.pointerId);
  drag = {x: e.clientX, y: e.clientY, cx: view.cx, cy: view.cy};
  moved = 0; cv.classList.add("drag");
});
cv.addEventListener("pointermove", e => {
  if (drag){
    const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
    moved = Math.max(moved, Math.abs(dx)+Math.abs(dy));
    view.cx = drag.cx - dx/view.k; view.cy = drag.cy - dy/view.k;
    clampView(); draw();
  } else {
    hoverAt(e);
  }
});
function endDrag(e){
  if (drag && moved < 5) clickAt(e);
  drag = null; cv.classList.remove("drag");
}
cv.addEventListener("pointerup", endDrag);
cv.addEventListener("pointercancel", () => { drag = null; cv.classList.remove("drag"); });
cv.addEventListener("pointerleave", () => { hideTip(); });
cv.addEventListener("wheel", e => {
  e.preventDefault();
  const r = cv.getBoundingClientRect();
  zoomAbout(e.clientX - r.left, e.clientY - r.top, Math.exp(-e.deltaY * 0.0022));
}, {passive:false});

let pinch = null;
cv.addEventListener("touchstart", e => {
  if (e.touches.length === 2){
    const [a,b] = e.touches;
    pinch = {d: Math.hypot(a.clientX-b.clientX, a.clientY-b.clientY), k: view.k};
  }
}, {passive:true});
cv.addEventListener("touchmove", e => {
  if (pinch && e.touches.length === 2){
    e.preventDefault();
    const [a,b] = e.touches;
    const d = Math.hypot(a.clientX-b.clientX, a.clientY-b.clientY);
    view.k = pinch.k * (d/pinch.d); clampView(); draw();
  }
}, {passive:false});
cv.addEventListener("touchend", () => { pinch = null; });

function zoomAbout(sx, sy, factor){
  const wx = toWorldX(sx), wy = toWorldY(sy);
  view.k = Math.max(minK*0.85, Math.min(view.k * factor, MAX_K));
  view.cx = wx - (sx - VW/2)/view.k;
  view.cy = wy - (sy - VH/2)/view.k;
  clampView(); draw();
}
document.getElementById("zin").onclick = () => zoomAbout(VW/2, VH/2, 1.55);
document.getElementById("zout").onclick = () => zoomAbout(VW/2, VH/2, 1/1.55);
document.getElementById("zworld").onclick = () => {
  view.cx = WORLD_W*0.5; view.cy = WORLD_H*0.46; view.k = minK; clampView(); draw();
};
cv.tabIndex = 0;
cv.addEventListener("keydown", e => {
  const step = 90/view.k;
  if (e.key === "ArrowLeft") view.cx -= step; else if (e.key === "ArrowRight") view.cx += step;
  else if (e.key === "ArrowUp") view.cy -= step; else if (e.key === "ArrowDown") view.cy += step;
  else if (e.key === "+" || e.key === "=") view.k *= 1.4;
  else if (e.key === "-") view.k /= 1.4;
  else return;
  e.preventDefault(); clampView(); draw();
});

function pickCell(sx, sy){
  const res = resForZoom(zoomLevel());
  const lv = level(res);
  if (!lv.n) return null;
  const wx = toWorldX(sx), wy = toWorldY(sy);
  const reach = 40/view.k;
  let lo = 0, hi = lv.n;
  while (lo < hi){ const m = (lo+hi)>>1; if (lv.ox[m] < wx-reach) lo = m+1; else hi = m; }
  let best = -1, bestD = Infinity;
  for (let k = lo; k < lv.n && lv.ox[k] <= wx+reach; k++){
    const i = lv.order[k];
    const d = (lv.cx[i]-wx)**2 + (lv.cy[i]-wy)**2;
    if (d < bestD){ bestD = d; best = i; }
  }
  if (best < 0) return null;
  // inside-radius test against the cell's own size
  const s = lv.vstart[best];
  const r2 = (lv.vx[s]-lv.cx[best])**2 + (lv.vy[s]-lv.cy[best])**2;
  return bestD <= r2*1.15 ? {kind:"cell", res, i: best} : null;
}
function pickPin(sx, sy){
  const z = zoomLevel();
  const pins = visiblePins(z, toWorldX(0)-99, toWorldX(VW)+99, toWorldY(0)-99, toWorldY(VH)+99);
  let best = null, bestD = 15*15;
  for (const L of pins){
    const d = (toScreenX(L.px)-sx)**2 + (toScreenY(L.py)-sy)**2;
    if (d < bestD){ bestD = d; best = L; }
  }
  return best;
}
function clickAt(e){
  const r = cv.getBoundingClientRect();
  const sx = e.clientX - r.left, sy = e.clientY - r.top;
  const pin = pickPin(sx, sy);
  if (pin){ selectLocality(pin.gid); return; }
  const cell = pickCell(sx, sy);
  if (cell){ selectCell(cell); return; }
  closeDrawer();
}

const tip = document.getElementById("tip");
function hideTip(){ tip.classList.remove("on"); S.hover = null; }
function hoverAt(e){
  const r = cv.getBoundingClientRect();
  const sx = e.clientX - r.left, sy = e.clientY - r.top;
  const pin = pickPin(sx, sy);
  if (pin){
    showTip(sx, sy, `<div class="tt">${esc(pin.name)}<span class="muted"> ${esc(pin.country)}</span></div>
      <div class="tr"><span>${S.scale === "pc" ? "Per-capita score" : "Live score"}</span><b>${scoreOf(pin)}</b></div>
      <div class="tr"><span>Confidence</span><b>${pin.confidence}%</b></div>
      <div class="tr"><span>Trend</span><b>${pin.momentum}</b></div>
      <div class="tr muted" style="margin-top:3px">Click for evidence</div>`);
    return;
  }
  const c = pickCell(sx, sy);
  if (!c){ hideTip(); return; }
  const lv = level(c.res), raw = lv.raw, i = c.i;
  const L = byGid.get(raw.g[i]);
  showTip(sx, sy, `<div class="tt">${esc(L ? L.name : "H3 cell")} <span class="muted">res ${c.res}</span></div>
    <div class="tr"><span>${labelFor(S.layer)}</span><b>${cellValue(lv,i)}</b></div>
    <div class="tr"><span>Evidence</span><b>${raw.n[i]} from ${raw.u[i]} src</b></div>
    ${raw.ti[i] && raw.ti[i].length ? `<div class="tr muted" style="margin-top:3px">${esc(raw.ti[i].slice(0,2).join(" · "))}</div>` : ""}`);
}
function showTip(sx, sy, html){
  tip.innerHTML = html; tip.classList.add("on");
  const w = tip.offsetWidth, h = tip.offsetHeight;
  tip.style.left = Math.min(Math.max(6, sx+14), VW-w-6) + "px";
  tip.style.top = Math.min(Math.max(6, sy-h-12), VH-h-6) + "px";
}
const labelFor = l => ({live:"Live score",events:"Event activity",community:"Community",
  coworking:"Coworking",international:"International",social:"Social",confidence:"Confidence"})[l] || l;

function esc(s){ return String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
function flyTo(px, py, k){
  const tx = view.cx, ty = view.cy, tk = view.k;
  const t0 = performance.now(), dur = 520;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduce){ view.cx=px; view.cy=py; view.k=k; clampView(); draw(); return; }
  (function step(t){
    const p = Math.min(1, (t-t0)/dur), e = 1-Math.pow(1-p,3);
    view.cx = tx+(px-tx)*e; view.cy = ty+(py-ty)*e;
    view.k = Math.exp(Math.log(tk)+(Math.log(k)-Math.log(tk))*e);
    clampView(); draw();
    if (p < 1) requestAnimationFrame(step);
  })(t0);
}
