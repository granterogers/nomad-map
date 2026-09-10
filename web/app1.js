/* Nomad Radar - client. Everything below runs against precomputed artifacts
   embedded in the page: no tiles, no map library, no network calls. */
"use strict";
const D = JSON.parse(document.getElementById("bundle").textContent);
const WPX = D.world_px, WORLD_W = WPX.w, WORLD_H = WPX.h, GEO_SCALE = WORLD_W / WPX.ref;

/* ---------- wire decoding ----------
   Localities and evidence travel without repeated keys, and every string that
   is a pure function of a number (band, presence, momentum, freshness) is
   derived here rather than transmitted. */
function decodeLocalities(){
  const S = D.loc_schema, PK = D.part_keys, SK = D.source_keys, WC = D.warn_codes;
  return D.localities.map(row => {
    const L = {};
    for (let i = 0; i < S.length; i++) L[S[i]] = row[i] === undefined ? null : row[i];
    const p = L.parts || [];
    L.parts = {}; PK.forEach((k, i) => L.parts[k] = p[i] || 0);
    const mask = L.sources || 0;
    L.sources = SK.filter((_, i) => mask & (1 << i));
    L.warnings = (L.warnings || []).map(([code, detail]) =>
      ({code: WC[code] || "NOTE", detail}));
    L.event_categories = L.event_categories || [];
    L.venue_families = L.venue_families || {};
    L.pop = L.pop || 0;
    L.evidence_count = L.evidence_count || 0;
    L.n_clusters = L.n_clusters || 0;
    L.n_cells = L.n_cells || 0;
    L.daily_attention = L.daily_attention || 0;
    L.confidence = L.confidence || 0;
    L.live_score = L.live_score || 0;
    L.active_community_density = L.active_community_density || 0;
    L.band = bandOf(L.live_score);
    L.presence = presenceOf(L.parts.nomad_presence);
    L.momentum = momentumLabel(L.momentum_ratio);
    L.trend = trendOf(L.momentum_ratio);
    L.freshness = freshnessOf(L.freshest_hours);
    if (L.att_series && L.att_series.length === 2 && Array.isArray(L.att_series[1])){
      const [start, vals] = L.att_series;
      const d0 = new Date(start.slice(0,4)+"-"+start.slice(4,6)+"-"+start.slice(6,8)+"T00:00:00Z");
      L.att_series = vals.map((v, i) => {
        const d = new Date(d0.getTime() + i*86400000);
        return [d.toISOString().slice(0,10), v];
      });
    } else L.att_series = null;
    L.att_recent_views = L.att_recent_views || 0;
    L.att_prior_views = L.att_prior_views || 0;
    return L;
  });
}
function decodeEvidence(list){
  const K = D.ev_keys, SRC = D.ev_sources, T = D.ev_types, P = D.url_prefix;
  return (list || []).map(e => {
    const o = {};
    for (const k in e) if (K[k]) o[K[k]] = e[k];
    o.type = T[o.type] || "venue";
    o.source_id = SRC[o.source_id] || "unknown";
    o.precision = e.p ? "point" : "locality";
    o.title = o.title || "";
    if (o.url){
      for (const pre of Object.keys(P).sort((a,b) => b.length-a.length)){
        if (o.url.startsWith(pre)){ o.url = P[pre] + o.url.slice(pre.length); break; }
      }
    }
    return o;
  });
}

/* ---------- heat ramp: the data's colour, not the UI accent ---------- */
const RAMP = [[0,"#241a45"],[38,"#4a2270"],[55,"#7d2a72"],[70,"#b23566"],
              [80,"#d95f3c"],[90,"#f2952b"],[100,"#ffd469"]];
const hexToRgb = h => [parseInt(h.slice(1,3),16),parseInt(h.slice(3,5),16),parseInt(h.slice(5,7),16)];
const RAMP_RGB = RAMP.map(([s,h]) => [s, hexToRgb(h)]);
function heat(v){
  v = Math.max(0, Math.min(100, v));
  for (let i = 1; i < RAMP_RGB.length; i++){
    if (v <= RAMP_RGB[i][0]){
      const [a,ca] = RAMP_RGB[i-1], [b,cb] = RAMP_RGB[i];
      const t = (v-a)/(b-a || 1);
      return [Math.round(ca[0]+(cb[0]-ca[0])*t), Math.round(ca[1]+(cb[1]-ca[1])*t),
              Math.round(ca[2]+(cb[2]-ca[2])*t)];
    }
  }
  return RAMP_RGB[RAMP_RGB.length-1][1];
}
const heatCss = (v,a=1) => { const c = heat(v); return `rgba(${c[0]},${c[1]},${c[2]},${a})`; };

const BANDS = [[90,"EXTREMELY HOT"],[80,"VERY ACTIVE"],[70,"ACTIVE"],[55,"MODERATE"],[40,"QUIET"],[0,"LOW ACTIVITY"]];
const bandOf = v => (BANDS.find(b => v >= b[0]) || BANDS[5])[1];
const presenceOf = v => v >= 82 ? "VERY HIGH" : v >= 66 ? "HIGH" : v >= 48 ? "MODERATE"
                       : v >= 28 ? "LOW" : "VERY LOW";
const momentumLabel = r => r == null ? "UNKNOWN" : r >= 1.35 ? "STRONGLY RISING"
  : r >= 1.10 ? "RISING" : r >= 0.92 ? "STABLE" : r >= 0.75 ? "COOLING" : "STRONGLY COOLING";
const trendOf = r => r == null ? "?" : r >= 1.5 ? "HOT" : r >= 1.1 ? "RISING"
  : r >= 0.92 ? "STABLE" : r >= 0.75 ? "COOLING" : "QUIET";
const freshnessOf = h => h == null ? "NO LIVE SIGNAL" : h <= 24 ? "LIVE" : h <= 168 ? "<7 DAYS"
  : h <= 720 ? "<30 DAYS" : "STALE";

/* ---------- level decoding (lazy: only what the viewport asks for) ---------- */
const RES_LIST = [8,7,6,5,4,3,2];
const levelCache = {};
function level(res){
  if (levelCache[res]) return levelCache[res];
  const raw = D.levels[String(res)];
  if (!raw){ return levelCache[res] = {n:0}; }
  const g = raw.geom, n = raw.s.length;
  const cx = new Float64Array(n), cy = new Float64Array(n);
  const vstart = new Int32Array(n+1), vcount = new Int32Array(n);
  let total = 0;
  for (let i = 0, p = 0; i < n; i++){ p += 2; const c = g[p++]; vcount[i] = c; total += c; p += c*2; }
  const vx = new Float32Array(total), vy = new Float32Array(total);
  let px = 0, py = 0, vi = 0, p = 0;
  for (let i = 0; i < n; i++){
    px += g[p++]; py += g[p++];
    const X = px/4, Y = py/4;
    cx[i] = X; cy[i] = Y;
    const c = g[p++]; vstart[i] = vi;
    for (let j = 0; j < c; j++){ vx[vi] = X + g[p++]/8; vy[vi] = Y + g[p++]/8; vi++; }
  }
  vstart[n] = vi;
  // sort index by x so viewport culling can binary-search a slice
  const order = Array.from({length:n}, (_,i) => i).sort((a,b) => cx[a]-cx[b]);
  const ox = new Float64Array(n);
  order.forEach((idx,k) => ox[k] = cx[idx]);
  return levelCache[res] = {n, cx, cy, vx, vy, vstart, vcount, order, ox, raw};
}

/* ---------- view ---------- */
const cv = document.getElementById("cv"), ctx = cv.getContext("2d", {alpha:false});
let VW = 0, VH = 0, DPR = 1;
const view = {cx: WORLD_W*0.5, cy: WORLD_H*0.46, k: 0.008};
let minK = 0.004;

function zoomLevel(){ return Math.log2(view.k * WORLD_W / 256); }
function resForZoom(z){
  return z < 2.6 ? 2 : z < 3.8 ? 3 : z < 5.0 ? 4 : z < 6.4 ? 5 : z < 7.8 ? 6 : z < 9.4 ? 7 : 8;
}
const RES_KM = {2:"~158 km",3:"~60 km",4:"~22.6 km",5:"~8.5 km",6:"~3.2 km",7:"~1.2 km",8:"~0.46 km"};

function resize(){
  const r = cv.parentElement.getBoundingClientRect();
  DPR = Math.min(window.devicePixelRatio || 1, 2);
  VW = Math.max(1, Math.round(r.width)); VH = Math.max(1, Math.round(r.height));
  cv.width = VW*DPR; cv.height = VH*DPR;
  cv.style.width = VW+"px"; cv.style.height = VH+"px";
  minK = Math.max(VW/WORLD_W, VH/WORLD_H) * 0.92;
  if (view.k < minK) view.k = minK;
  clampView(); draw();
}
function clampView(){
  const hw = VW/(2*view.k), hh = VH/(2*view.k);
  view.cx = Math.max(Math.min(view.cx, WORLD_W-hw*0.15), hw*0.15);
  view.cy = Math.max(Math.min(view.cy, WORLD_H-hh*0.3), hh*0.3);
  view.k = Math.max(minK*0.85, Math.min(view.k, 0.9));
}
const toScreenX = wx => (wx - view.cx)*view.k + VW/2;
const toScreenY = wy => (wy - view.cy)*view.k + VH/2;
const toWorldX = sx => (sx - VW/2)/view.k + view.cx;
const toWorldY = sy => (sy - VH/2)/view.k + view.cy;

/* ---------- basemap ---------- */
let landPath = null;
function buildLand(){
  landPath = new Path2D();
  for (const c of D.countries_geo){ landPath.addPath(new Path2D(c.d)); }
}
buildLand();

/* ---------- state ---------- */
const S = {
  layer: "live",             // live | events | community | coworking | international | social | momentum | confidence
  tab: "hot",
  sel: null,                 // {kind:'locality'|'cluster'|'cell', ...}
  hover: null,
  filters: {continent:"", minConf:0, trend:"", size:"", terrain:"", presence:""},
  showPins: true,
};
const LAYERS = [["live","Live"],["events","Events"],["community","Community"],
                ["coworking","Coworking"],["international","Intl"],["social","Social"]];
const SUB_IX = {coworking:0, community:1, international:2, social:3, events:4};

function cellValue(lv, i){
  const raw = lv.raw;
  if (S.layer === "live") return raw.s[i];
  if (S.layer === "confidence") return raw.c[i];
  const ix = SUB_IX[S.layer];
  return ix === undefined ? raw.s[i] : raw.sub[i][ix];
}

/* ---------- draw ---------- */
let raf = 0;
function draw(){ if (!raf) raf = requestAnimationFrame(render); }

function render(){
  raf = 0;
  const css = getComputedStyle(document.documentElement);
  const sea = css.getPropertyValue("--sea").trim() || "#0b1017";
  const land = css.getPropertyValue("--land").trim() || "#1a2634";
  const landLine = css.getPropertyValue("--land-line").trim() || "#2c3d51";
  ctx.setTransform(DPR,0,0,DPR,0,0);
  ctx.fillStyle = sea; ctx.fillRect(0,0,VW,VH);

  // land
  ctx.save();
  ctx.setTransform(DPR*view.k*GEO_SCALE, 0, 0, DPR*view.k*GEO_SCALE,
                   DPR*(VW/2 - view.cx*view.k), DPR*(VH/2 - view.cy*view.k));
  ctx.fillStyle = land; ctx.fill(landPath);
  ctx.lineWidth = 0.7/(view.k*GEO_SCALE); ctx.strokeStyle = landLine; ctx.stroke(landPath);
  ctx.restore();

  const z = zoomLevel(), res = resForZoom(z);
  const lv = level(res);
  const pad = 60/view.k;
  const x0 = toWorldX(0)-pad, x1 = toWorldX(VW)+pad;
  const y0 = toWorldY(0)-pad, y1 = toWorldY(VH)+pad;

  let drawn = 0;
  if (lv.n){
    // binary search the x-sorted order
    let lo = 0, hi = lv.n;
    while (lo < hi){ const m = (lo+hi)>>1; if (lv.ox[m] < x0) lo = m+1; else hi = m; }
    ctx.setTransform(DPR,0,0,DPR,0,0);
    ctx.lineWidth = Math.min(1.1, Math.max(0.35, view.k*WORLD_W/20000));
    const strokeAlpha = z > 5 ? 0.5 : 0.22;
    const passes = [];
    for (let k = lo; k < lv.n && lv.ox[k] <= x1; k++){
      const i = lv.order[k];
      if (lv.cy[i] < y0 || lv.cy[i] > y1) continue;
      passes.push(i);
      if (passes.length > 9000) break;
    }
    passes.sort((a,b) => cellValue(lv,a) - cellValue(lv,b));  // hot cells paint last
    for (const i of passes){
      const v = cellValue(lv, i);
      const s = lv.vstart[i], c = lv.vcount[i];
      ctx.beginPath();
      for (let j = 0; j < c; j++){
        const X = toScreenX(lv.vx[s+j]), Y = toScreenY(lv.vy[s+j]);
        j ? ctx.lineTo(X,Y) : ctx.moveTo(X,Y);
      }
      ctx.closePath();
      const conf = lv.raw.c[i];
      ctx.fillStyle = heatCss(v, 0.34 + 0.54*(conf/100));
      ctx.fill();
      ctx.strokeStyle = heatCss(Math.min(100, v+10), strokeAlpha);
      ctx.stroke();
      drawn++;
    }
  }

  // selection halo
  if (S.sel && S.sel.kind === "cell" && S.sel.res === res){
    const i = S.sel.i, s = lv.vstart[i], c = lv.vcount[i];
    ctx.beginPath();
    for (let j = 0; j < c; j++){
      const X = toScreenX(lv.vx[s+j]), Y = toScreenY(lv.vy[s+j]);
      j ? ctx.lineTo(X,Y) : ctx.moveTo(X,Y);
    }
    ctx.closePath();
    ctx.lineWidth = 2.2; ctx.strokeStyle = css.getPropertyValue("--ink").trim(); ctx.stroke();
  }

  // locality pins
  const pins = visiblePins(z, x0, x1, y0, y1);
  const inkc = css.getPropertyValue("--ink").trim();
  const panel = css.getPropertyValue("--panel").trim();
  ctx.font = '600 11px "IBM Plex Sans Condensed", system-ui, sans-serif';
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  const taken = [];                       // occupied label boxes, for collision avoidance
  const fits = (x, y, w, h) => {
    for (const t of taken)
      if (x - w/2 < t[2] && x + w/2 > t[0] && y - h/2 < t[3] && y + h/2 > t[1]) return false;
    taken.push([x - w/2, y - h/2, x + w/2, y + h/2]);
    return true;
  };
  for (const L of pins){
    const X = toScreenX(L.px), Y = toScreenY(L.py);
    const r = z < 4 ? 3.4 : z < 6 ? 4.4 : 5.4;
    ctx.beginPath(); ctx.arc(X, Y, r, 0, 6.2832);
    ctx.fillStyle = heatCss(L.live_score, 0.98); ctx.fill();
    ctx.lineWidth = 1.4; ctx.strokeStyle = panel; ctx.stroke();
    const selected = S.sel && S.sel.gid === L.gid;
    if (z >= 4.2 || selected){
      const w = ctx.measureText(L.name).width + 8, ly = Y - r - 8;
      if (selected || fits(X, ly, w, 13)){
        ctx.lineWidth = 3; ctx.strokeStyle = panel;
        ctx.strokeText(L.name, X, ly);
        ctx.fillStyle = selected ? heatCss(L.live_score, 1) : inkc;
        ctx.fillText(L.name, X, ly);
      }
    }
  }
  document.getElementById("resbadge").innerHTML =
    `H3 RES <b>${res}</b> · edge ${RES_KM[res]} · <b>${drawn.toLocaleString()}</b> cells drawn · zoom ${z.toFixed(1)}`;
  const empty = document.getElementById("emptynote");
  empty.style.display = (drawn === 0 && pins.length === 0) ? "block" : "none";
  if (drawn === 0 && pins.length === 0)
    empty.textContent = "No evidence has been collected in this view yet. Scanning is adaptive — quiet regions are refreshed least often.";
}

function visiblePins(z, x0, x1, y0, y1){
  const out = [];
  const list = rankedLocalities();
  const cap = z < 3 ? 34 : z < 4.5 ? 90 : z < 6 ? 200 : z < 8 ? 380 : 700;
  const floor = z < 3 ? 46 : z < 4.5 ? 40 : z < 6 ? 32 : 0;
  for (const L of list){
    if (L.px < x0 || L.px > x1 || L.py < y0 || L.py > y1) continue;
    if (L.live_score < floor && !(S.sel && S.sel.gid === L.gid)) continue;
    out.push(L);
    if (out.length >= cap) break;
  }
  return out;
}
