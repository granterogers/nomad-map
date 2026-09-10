
/* ---------- search: navigation only, never the intelligence ---------- */
const searchEl = document.getElementById("search"), resEl = document.getElementById("results");
const SEARCH_IDX = LOC.map(L => ({L, k: (L.name + " " + L.country + " " + L.admin1).toLowerCase()}));
let searchSel = -1;
function runSearch(){
  const q = searchEl.value.trim().toLowerCase();
  if (q.length < 2){ resEl.innerHTML = ""; resEl.style.display = "none"; return; }
  const hits = SEARCH_IDX.filter(x => x.k.includes(q))
    .sort((a,b) => (a.L.name.toLowerCase().indexOf(q) - b.L.name.toLowerCase().indexOf(q))
                   || b.L.live_score - a.L.live_score).slice(0,9);
  searchSel = -1;
  resEl.style.display = hits.length ? "block" : "none";
  resEl.innerHTML = hits.map(({L}) => `<button data-gid="${L.gid}">
    <span>${esc(L.name)}</span> <span class="num" style="color:${heatCss(L.live_score,1)}">${L.live_score}</span>
    <div class="sub">${esc(L.admin1 ? L.admin1+", " : "")}${esc(L.country)} · ${L.band}</div></button>`).join("");
  resEl.querySelectorAll("button").forEach(b => b.onclick = () => {
    selectLocality(Number(b.dataset.gid)); resEl.style.display = "none"; searchEl.blur();
  });
}
searchEl.addEventListener("input", runSearch);
searchEl.addEventListener("keydown", e => {
  const btns = [...resEl.querySelectorAll("button")];
  if (e.key === "ArrowDown" || e.key === "ArrowUp"){
    e.preventDefault();
    searchSel = Math.max(0, Math.min(btns.length-1, searchSel + (e.key === "ArrowDown" ? 1 : -1)));
    btns.forEach((b,i) => b.classList.toggle("sel", i === searchSel));
  } else if (e.key === "Enter" && btns.length){
    (btns[Math.max(0,searchSel)]).click();
  } else if (e.key === "Escape"){ resEl.style.display = "none"; searchEl.blur(); }
});
document.addEventListener("click", e => {
  if (!e.target.closest("#searchwrap")) resEl.style.display = "none";
});

/* ---------- layer + tab + filter wiring ---------- */
const layerbar = document.getElementById("layerbar");
layerbar.innerHTML = LAYERS.map(([k,l]) =>
  `<button data-layer="${k}" aria-pressed="${k===S.layer}">${l}</button>`).join("");
layerbar.querySelectorAll("button").forEach(b => b.onclick = () => {
  S.layer = b.dataset.layer;
  layerbar.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b));
  document.getElementById("ramplabel").textContent = labelFor(S.layer);
  draw();
});

const scalebar = document.getElementById("scalebar");
scalebar.querySelectorAll("button").forEach(b => b.onclick = () => {
  if (S.scale === b.dataset.scale) return;
  S.scale = b.dataset.scale;
  scalebar.querySelectorAll("button").forEach(x => x.setAttribute("aria-pressed", x === b));
  invalidateScale();
  document.getElementById("ramplabel").textContent = labelFor(S.layer);
  document.getElementById("scalenote").textContent = S.scale === "pc"
    ? "· rankings and pins per head; hexes unchanged (they measure concentration, not population)"
    : "";
  if (S.sel && S.sel.kind === "locality") selectLocality(S.sel.gid);
  renderRail(); draw();
});

const tabsEl = document.getElementById("tabs");
tabsEl.innerHTML = TABS.map(([k,l]) =>
  `<button role="tab" data-tab="${k}" aria-selected="${k===S.tab}">${l}</button>`).join("");
tabsEl.querySelectorAll("button").forEach(b => b.onclick = () => {
  S.tab = b.dataset.tab;
  tabsEl.querySelectorAll("button").forEach(x => x.setAttribute("aria-selected", x === b));
  document.getElementById("railbody").scrollTop = 0;
  renderRail();
});

const CONTS = {EU:"Europe", AS:"Asia", NA:"North America", SA:"South America",
               AF:"Africa", OC:"Oceania"};
const contSel = document.getElementById("f-cont");
contSel.innerHTML = `<option value="">All continents</option>` +
  Object.entries(CONTS).map(([k,v]) => `<option value="${k}">${v}</option>`).join("");
function bindFilter(id, key, transform = v => v){
  const el = document.getElementById(id);
  el.addEventListener("input", () => {
    S.filters[key] = transform(el.value);
    if (id === "f-conf") document.getElementById("f-conf-v").textContent = el.value + "%";
    renderRail(); draw();
  });
}
bindFilter("f-cont","continent"); bindFilter("f-trend","trend");
bindFilter("f-size","size"); bindFilter("f-terrain","terrain");
bindFilter("f-presence","presence");
bindFilter("f-conf","minConf", v => Number(v));
document.getElementById("reset").onclick = () => {
  S.filters = {continent:"", minConf:0, trend:"", size:"", terrain:"", presence:""};
  ["f-cont","f-trend","f-size","f-terrain","f-presence"].forEach(i => document.getElementById(i).value = "");
  document.getElementById("f-conf").value = 0;
  document.getElementById("f-conf-v").textContent = "0%";
  renderRail(); draw();
};

/* mobile sheet toggles */
document.getElementById("mrail").onclick = () => {
  app.classList.toggle("rail-open"); app.classList.remove("drawer-open");
};

/* theme toggle: overrides the host theme for this page only */
const themeBtn = document.getElementById("theme");
themeBtn.onclick = () => {
  const cur = document.documentElement.getAttribute("data-theme");
  const next = cur === "dark" ? "light" : cur === "light" ? "" : "dark";
  if (next) document.documentElement.setAttribute("data-theme", next);
  else document.documentElement.removeAttribute("data-theme");
  themeBtn.setAttribute("aria-pressed", next === "dark");
  themeBtn.title = next ? `Theme: ${next}` : "Theme: follow system";
  draw();
};
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => draw());

/* ---------- boot ---------- */
const gen = new Date(D.generated_at.replace(" ", "T"));
document.getElementById("stamp").textContent =
  `${D.meta.scanned_localities.toLocaleString()} localities scanned of ${D.meta.universe_places.toLocaleString()} · ` +
  `${D.meta.universe_countries} countries · built ${D.generated_at.slice(0,16).replace("T"," ")} UTC`;
document.getElementById("ramplabel").textContent = labelFor(S.layer);

new ResizeObserver(() => resize()).observe(cv.parentElement);
window.addEventListener("resize", resize);
resize();
renderRail();

/* open on the world with the hottest place already framed, so the first frame
   is a working map rather than an empty one */
(function firstFrame(){
  const top = LOC.slice().sort((a,b) => b.live_score - a.live_score)[0];
  if (!top) return;
  view.cx = WORLD_W*0.5; view.cy = WORLD_H*0.44; view.k = minK;
  clampView(); draw();
})();
