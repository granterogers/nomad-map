
/* ---------- rail: rankings derived from current data ---------- */
const TABS = [
  ["hot","Hot now"],["rising","Rising"],["hoods","Neighbourhoods"],
  ["density","Social density"],["small","Small cities"],["coast","Coast & peaks"],
  ["regions","Regions"],["sources","Sources"],
];
const TAB_NOTE = {
  hot:"Ranked by Nomad Live Score from current evidence only. Reputation contributes nothing.",
  rising:"Attention in the last 14 days against the previous 14, from Wikipedia pageview dumps.",
  hoods:"Contiguous clusters of hot H3 cells — where inside a city the evidence actually concentrates.",
  density:"Active Community Density: how easy it looks to enter a real social ecosystem alone.",
  small:"Places under 250,000 people that still show real ecosystem evidence.",
  coast:"Coastal places and places above 700 m, classified from open geographic data.",
  regions:"Administrative roll-ups keep the maximum, not just the mean, so a hot city is never averaged away.",
  sources:"Every source tested, and what it currently contributes. Missing data is shown, not hidden.",
};

function trendChip(L){
  const cls = /RISING|HOT/.test(L.trend) ? "rise" : /COOL|QUIET/.test(L.trend) ? "cool" : "";
  return `<span class="chip ${cls}">${esc(L.trend)}</span>`;
}
function rowHTML(rank, name, sub, score, gid, extraCls=""){
  return `<button class="row ${extraCls}" data-gid="${gid}">
    <span class="rank num">${rank}</span>
    <span><span class="rname">${esc(name)}</span><span class="rsub">${sub}</span></span>
    <span class="score num" style="color:${heatCss(score,1)}">${score}</span></button>`;
}

function renderRail(){
  const body = document.getElementById("railbody");
  const list = filtered();
  let html = "", note = TAB_NOTE[S.tab] || "";
  const head = (t, n) => `<div class="listhead"><h3>${t}</h3><span class="n num">${n}</span></div>
    <div class="listnote">${note}</div>`;

  if (S.tab === "hot"){
    const rows = list.slice().sort((a,b) => b.live_score-a.live_score).slice(0,120);
    html = head("Hottest right now", rows.length) + rows.map((L,i) =>
      rowHTML(i+1, L.name, `<span class="chip">${esc(L.cc)}</span>${trendChip(L)}<span>${L.confidence}% conf</span>`,
              L.live_score, L.gid, S.sel && S.sel.gid===L.gid ? "active":"")).join("");
  } else if (S.tab === "rising"){
    const rows = list.filter(L => L.momentum_ratio != null && L.evidence_count >= 4)
      .sort((a,b) => b.momentum_ratio-a.momentum_ratio).slice(0,90);
    html = head("Fastest rising", rows.length) + rows.map((L,i) =>
      rowHTML(i+1, L.name, `<span class="chip">${esc(L.cc)}</span><span class="chip rise">×${L.momentum_ratio.toFixed(2)}</span><span>score ${L.live_score}</span>`,
              Math.round(L.momentum_ratio*100)/1|0 ? L.live_score : L.live_score, L.gid)).join("");
    const cooling = list.filter(L => L.momentum_ratio != null && L.momentum_ratio < 0.85 && L.evidence_count >= 6)
      .sort((a,b) => a.momentum_ratio-b.momentum_ratio).slice(0,25);
    if (cooling.length) html += `<div class="listhead"><h3>Fastest cooling</h3><span class="n num">${cooling.length}</span></div>` +
      cooling.map((L,i) => rowHTML(i+1, L.name, `<span class="chip">${esc(L.cc)}</span><span class="chip cool">×${L.momentum_ratio.toFixed(2)}</span>`, L.live_score, L.gid)).join("");
  } else if (S.tab === "hoods"){
    const allow = new Set(list.map(L => L.gid));
    const rows = CLUSTERS.filter(c => allow.has(Number(c.gid))).slice(0,110);
    html = head("Hotspot clusters", rows.length) + rows.map((c,i) =>
      `<button class="row" data-cluster="${c.id}">
        <span class="rank num">${i+1}</span>
        <span><span class="rname">${esc(c.place)} — ${c.n_cells} cells</span>
        <span class="rsub"><span class="chip">${esc(c.cc)}</span><span>${c.evidence} items · ${c.area_km2} km²</span></span></span>
        <span class="score num" style="color:${heatCss(c.score,1)}">${c.score}</span></button>`).join("");
  } else if (S.tab === "density"){
    const rows = list.slice().sort((a,b) => b.active_community_density-a.active_community_density).slice(0,90);
    html = head("Active community density", rows.length) + rows.map((L,i) =>
      rowHTML(i+1, L.name, `<span class="chip">${esc(L.cc)}</span><span>${L.organizers} organisers · ${L.events_upcoming} events</span>`,
              L.active_community_density, L.gid)).join("");
  } else if (S.tab === "small"){
    const rows = list.filter(L => L.pop < 250000).sort((a,b) => b.live_score-a.live_score).slice(0,90);
    html = head("Best small cities", rows.length) + rows.map((L,i) =>
      rowHTML(i+1, L.name, `<span class="chip">${esc(L.cc)}</span><span>${(L.pop/1000).toFixed(0)}k people</span>${trendChip(L)}`,
              L.live_score, L.gid)).join("");
  } else if (S.tab === "coast"){
    const beach = list.filter(L => L.coastal).sort((a,b) => b.live_score-a.live_score).slice(0,55);
    const mtn = list.filter(L => (L.elev||0) >= 700).sort((a,b) => b.live_score-a.live_score).slice(0,45);
    html = head("Best coastal", beach.length) + beach.map((L,i) =>
      rowHTML(i+1, L.name, `<span class="chip">${esc(L.cc)}</span><span>${L.elev} m</span>`, L.live_score, L.gid)).join("")
      + `<div class="listhead"><h3>Best high-altitude</h3><span class="n num">${mtn.length}</span></div>`
      + mtn.map((L,i) => rowHTML(i+1, L.name, `<span class="chip">${esc(L.cc)}</span><span>${L.elev} m</span>`, L.live_score, L.gid)).join("");
  } else if (S.tab === "regions"){
    const cs = D.country_rollup.slice(0,70);
    html = head("Countries by hottest locality", cs.length) + cs.map((r,i) =>
      `<button class="row" data-gid="${r.top_locality.gid}">
        <span class="rank num">${i+1}</span>
        <span><span class="rname">${esc(r.label)}</span>
        <span class="rsub"><span>top: ${esc(r.top_locality.name)}</span><span class="chip">mean ${r.mean}</span><span class="chip">${r.hot_localities} hot</span></span></span>
        <span class="score num" style="color:${heatCss(r.max,1)}">${r.max}</span></button>`).join("")
      + `<div class="listhead"><h3>Regions</h3><span class="n num">${D.region_rollup.length}</span></div>`
      + D.region_rollup.slice(0,60).map((r,i) =>
      `<button class="row" data-gid="${r.top_locality.gid}">
        <span class="rank num">${i+1}</span>
        <span><span class="rname">${esc(r.label)}</span>
        <span class="rsub"><span>${r.n_localities} localities</span><span class="chip">conc ×${r.concentration}</span></span></span>
        <span class="score num" style="color:${heatCss(r.max,1)}">${r.max}</span></button>`).join("");
  } else if (S.tab === "sources"){
    html = head("Source health", D.sources.audit.length) + sourceHTML();
  }
  body.innerHTML = html;
  body.querySelectorAll("[data-gid]").forEach(b =>
    b.onclick = () => selectLocality(Number(b.dataset.gid)));
  body.querySelectorAll("[data-cluster]").forEach(b =>
    b.onclick = () => selectCluster(b.dataset.cluster));
}

const STATUS_COLOR = {ACTIVE:"var(--rise)", OPTIONAL:"var(--warn)", BLOCKED:"var(--cool)", REJECTED:"var(--faint)"};
function sourceHTML(){
  const reg = D.sources.registry || {};
  const contributing = Object.values(reg).filter(r => r.success_count > 0);
  let h = `<div class="fgrid" style="padding-bottom:4px"><div class="tiny">
    <b style="color:var(--ink)">${contributing.length}</b> sources are currently contributing evidence.
    Sources that need credentials, or that block automated access, contribute exactly nothing —
    they are listed so the gaps are visible.</div></div>`;
  h += `<div class="listhead"><h3>Contributing now</h3></div><div class="fgrid" style="gap:6px">`;
  for (const r of contributing.sort((a,b) => (b.coverage||0)-(a.coverage||0))){
    h += `<div class="srcrow"><span class="dot" style="background:var(--rise)"></span>
      <span><b>${esc(r.source_name || r.source_id)}</b><br><span class="tiny">${esc(r.domain||"")} · ${esc(r.source_type||"")} · reliability ${Math.round((r.reliability||0)*100)}%</span></span>
      <span class="num tiny">${r.coverage != null ? r.coverage.toLocaleString() : ""}</span></div>`;
  }
  h += `</div>`;
  const byStatus = {};
  for (const a of D.sources.audit) (byStatus[a.status] = byStatus[a.status] || []).push(a);
  for (const st of ["ACTIVE","OPTIONAL","BLOCKED","REJECTED"]){
    const rows = byStatus[st] || [];
    if (!rows.length) continue;
    h += `<div class="listhead"><h3>${st}</h3><span class="n num">${rows.length}</span></div><div class="fgrid" style="gap:5px">`;
    for (const r of rows){
      h += `<div class="srcrow"><span class="dot" style="background:${STATUS_COLOR[st]}"></span>
        <span><b>${esc(r.source)}</b><br><span class="tiny">${esc(r.notes||"")}${r.credential_required ? " · credential required" : ""}</span></span>
        <span class="num tiny">${r.http || "—"}</span></div>`;
    }
    h += `</div>`;
  }
  return h;
}
