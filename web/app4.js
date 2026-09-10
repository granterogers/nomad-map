
/* ---------- detail drawer ---------- */
const app = document.getElementById("app");
const drawer = document.getElementById("drawer");
function closeDrawer(){ S.sel = null; app.classList.remove("drawer-open"); renderRail(); draw(); }
document.getElementById("dclose").onclick = closeDrawer;

function metric(label, v, tone){
  return `<div class="metric"><span class="lb">${label}</span><span class="vl num">${v}</span>
    <span class="track"><span class="fill" style="width:${Math.max(2,v)}%;background:${tone || heatCss(v,1)}"></span></span></div>`;
}
function pill(text, kind){
  const col = kind === "rise" ? "var(--rise)" : kind === "cool" ? "var(--cool)" : "var(--accent)";
  return `<span class="pill" style="background:color-mix(in srgb,${col} 16%,transparent);color:${col}">${esc(text)}</span>`;
}
function ago(h){
  if (h == null) return "—";
  if (h < 1) return "just now";
  if (h < 48) return `${Math.round(h)}h`;
  return `${Math.round(h/24)}d`;
}

function sparkline(series){
  if (!series || series.length < 4) return "";
  const vals = series.map(s => s[1]);
  const max = Math.max(...vals), min = Math.min(...vals);
  const w = 340, h = 38, n = vals.length;
  const X = i => (i/(n-1))*w, Y = v => h-3 - ((v-min)/Math.max(max-min,1))*(h-8);
  const d = vals.map((v,i) => `${i?"L":"M"}${X(i).toFixed(1)},${Y(v).toFixed(1)}`).join("");
  const area = `${d}L${w},${h}L0,${h}Z`;
  const half = Math.floor(n/2);
  return `<svg class="spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" role="img"
     aria-label="Daily Wikipedia views, ${series[0][0]} to ${series[n-1][0]}, peak ${max}">
    <path d="${area}" fill="${heatCss(60,.16)}"></path>
    <path d="${d}" fill="none" stroke="${heatCss(72,1)}" stroke-width="1.4"></path>
    <line x1="${X(half)}" y1="0" x2="${X(half)}" y2="${h}" stroke="var(--line)" stroke-width="1" stroke-dasharray="2 2"></line>
    <circle cx="${X(n-1)}" cy="${Y(vals[n-1])}" r="2.6" fill="${heatCss(88,1)}"></circle>
  </svg>
  <div class="tiny" style="display:flex;justify-content:space-between">
    <span>${esc(series[0][0])}</span><span>previous 14d | last 14d</span><span>peak ${max}</span></div>`;
}

function selectLocality(gid){
  const L = byGid.get(gid);
  if (!L) return;
  S.sel = {kind:"locality", gid};
  app.classList.add("drawer-open");
  app.classList.remove("rail-open");
  drawer.scrollTop = 0;
  const z = zoomLevel();
  if (z < 10.2) flyTo(L.px, L.py, Math.max(view.k, 256*Math.pow(2,10.4)/WORLD_W));
  else draw();
  renderLocality(L);
  renderRail();
  setTimeout(resize, 30);
}

function renderLocality(L){
  const P = L.parts;
  const clusters = CLUSTERS.filter(c => Number(c.gid) === L.gid).slice(0,6);
  const ev = decodeEvidence(D.evidence[String(L.gid)]);
  const events = ev.filter(e => e.type === "event").sort((a,b) => (a.age_hours??999)-(b.age_hours??999));
  const venues = ev.filter(e => e.type === "venue");
  const posts = ev.filter(e => e.type === "community_post");
  const famCount = {};
  for (const v of venues) famCount[v.kind] = (famCount[v.kind]||0)+1;

  document.querySelector(".dhead .eyebrow").textContent = `${L.band} · ${L.presence} NOMAD PRESENCE`;
  document.querySelector(".dhead h2").textContent = L.name;
  document.querySelector(".dhead .where").textContent =
    `${L.admin1 ? L.admin1 + ", " : ""}${L.country} · ${L.pop.toLocaleString()} people · ${L.tz}`;

  drawer.querySelector(".dbody").innerHTML = `
  <div class="bigrow">
    <div class="bigscore num" style="color:${heatCss(L.live_score,1)}">${L.live_score}</div>
    <div class="bigmeta">
      <div>Nomad Live Score</div>
      <div>Confidence <b class="num">${L.confidence}%</b> · Freshness <b>${L.freshness}</b></div>
      <div>${pill(L.momentum, /RISING/.test(L.momentum) ? "rise" : /COOL/.test(L.momentum) ? "cool" : "")}</div>
    </div>
  </div>

  ${L.warnings.length ? `<div class="sec"><h4>Read this first</h4>
    ${L.warnings.map(w => `<div class="warnbox"><div class="wt">${esc(w.code)}</div>
      <div class="wd">${esc(w.detail)}</div></div>`).join("")}</div>` : ""}

  <div class="sec"><h4>Score components</h4>
    ${metric("Nomad presence", P.nomad_presence)}
    ${metric("Event activity", P.event_activity)}
    ${metric("Community activity", P.community_activity)}
    ${metric("Coworking infrastructure", P.coworking_infra)}
    ${metric("International / social", P.international_social)}
    ${metric("Momentum", P.momentum)}
    ${metric("Active community density", L.active_community_density, "var(--accent)")}
    <div class="tiny" style="margin-top:7px">Weights: presence 25 · events 25 · community 20 ·
      coworking 10 · international 10 · momentum 5 · confidence 5.</div>
  </div>

  <div class="sec"><h4>Where inside ${esc(L.name)} the activity is</h4>
    ${clusters.length ? clusters.map(c => `<button class="hotrow" data-cluster="${c.id}">
        <span><b>${c.n_cells} contiguous cells · ${c.area_km2} km²</b>
        <span class="em" style="display:block;color:var(--muted);font-size:11px">
          ${esc(c.landmarks.slice(0,2).join(" · ") || c.dominant.slice(0,3).join(" · "))}</span></span>
        <span class="num" style="color:${heatCss(c.score,1)};font-weight:600">${c.score}</span></button>`).join("")
      : `<div class="tiny">No contiguous hotspot cluster emerged here. Evidence is either
         too thin or too dispersed to name a neighbourhood honestly — the map still shows
         every individual cell that does have evidence.</div>`}
    <div class="tiny" style="margin-top:8px">${L.n_cells} H3 cells at resolution ${D.meta.fine_res}
      carry evidence; top-5 cells hold ${Math.round(L.concentration*100)}% of the weight.</div>
  </div>

  <div class="sec"><h4>Live evidence · ${L.evidence_count} items from ${L.unique_sources} sources</h4>
    <dl class="kv">
      <dt>Events in window</dt><dd class="num">${L.events_upcoming} (${L.events_per_week}/wk)</dd>
      <dt>Distinct organisers</dt><dd class="num">${L.organizers}</dd>
      <dt>Event categories</dt><dd class="num">${L.event_categories.length}</dd>
      <dt>Community posts</dt><dd class="num">${L.community_posts}</dd>
      <dt>Mapped venues</dt><dd class="num">${L.venues}</dd>
      <dt>Freshest signal</dt><dd class="num">${ago(L.freshest_hours)}</dd>
    </dl>
    ${L.event_categories.length ? `<div class="rsub" style="margin-top:8px">
      ${L.event_categories.slice(0,10).map(c => `<span class="chip">${esc(c)}</span>`).join("")}</div>` : ""}
  </div>

  ${L.att_series && L.att_series.length ? `<div class="sec"><h4>Attention, last 28 days</h4>
    ${sparkline(L.att_series)}
    <div class="tiny" style="margin-top:6px">Daily English Wikipedia article views for
      <span class="mono">${esc((L.wiki||L.name))}</span>, from Wikimedia's public dumps
      (4 sampled hours/day). Last 14 days: <b>${L.att_recent_views.toLocaleString()}</b> ·
      previous 14: <b>${L.att_prior_views.toLocaleString()}</b>.</div></div>` : ""}

  ${events.length ? `<div class="sec"><h4>Events found (${events.length})</h4>
    ${events.slice(0,14).map(e => `<div class="evrow">
      <span><span class="et"><a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.title)}</a></span>
      <span class="em"><span class="chip">${esc(e.kind)}</span>
        ${e.venue ? `<span>${esc(e.venue)}</span>` : ""}
        ${e.organizer ? `<span>by ${esc(e.organizer)}</span>` : ""}
        <span>${esc(e.source_id.replace("_public",""))}</span>
        <span>${e.precision === "point" ? "point precision" : "city precision"}</span></span></span>
      <span class="ea">${esc((e.event_date||"").slice(0,10))}</span></div>`).join("")}
    </div>` : `<div class="sec"><h4>Events</h4><div class="tiny">
      No current public event listings were found for this place. That is a statement about
      the sources reachable without credentials, not proof that nothing is happening.</div></div>`}

  ${venues.length ? `<div class="sec"><h4>Mapped ecosystem (${venues.length})</h4>
    <div class="rsub" style="margin-bottom:8px">${Object.entries(famCount).sort((a,b)=>b[1]-a[1])
      .slice(0,9).map(([k,v]) => `<span class="chip">${esc(k)} ${v}</span>`).join("")}</div>
    ${venues.filter(v=>v.title).slice(0,10).map(v => `<div class="evrow">
      <span><span class="et">${esc(v.title)}</span><span class="em">
        <span class="chip">${esc(v.kind)}</span><span>OpenStreetMap</span></span></span>
      <span class="ea"><a href="${esc(v.url)}" target="_blank" rel="noopener">map</a></span></div>`).join("")}
    </div>` : ""}

  ${posts.length ? `<div class="sec"><h4>Community mentions (${L.community_posts})</h4>
    ${posts.slice(0,8).map(p => `<div class="evrow">
      <span><span class="et"><a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.title)}</a></span>
      <span class="em"><span class="chip">${esc(p.kind)}</span><span>city precision</span></span></span>
      <span class="ea">${ago(p.age_hours)}</span></div>`).join("")}
    </div>` : ""}

  <div class="sec"><h4>Source coverage here</h4>
    <div class="srcgrid">
      ${["osm_overpass","meetup_public","luma_public","reddit_rss","mastodon_public",
         "hn_algolia","lemmy_public","wikimedia_pageview_dumps"].map(s => {
        const on = L.sources.includes(s) || (s === "wikimedia_pageview_dumps" && L.daily_attention > 0);
        return `<div class="srcrow"><span class="dot" style="background:${on?"var(--rise)":"var(--line)"}"></span>
          <span>${esc(s.replace(/_/g," "))}</span>
          <span class="tiny">${on ? "contributing" : "no signal here"}</span></div>`;
      }).join("")}
      <div class="srcrow"><span class="dot" style="background:var(--cool)"></span>
        <span>Instagram · Facebook · Google Places</span><span class="tiny">credential-walled · 0</span></div>
    </div>
  </div>`;

  drawer.querySelectorAll("[data-cluster]").forEach(b =>
    b.onclick = () => selectCluster(b.dataset.cluster));
}

function selectCluster(id){
  const c = CLUSTERS.find(x => x.id === id);
  if (!c) return;
  S.sel = {kind:"cluster", gid: Number(c.gid), id};
  app.classList.add("drawer-open"); app.classList.remove("rail-open");
  flyTo(c.px, c.py, 256*Math.pow(2,11.6)/WORLD_W);
  drawer.scrollTop = 0;
  const L = byGid.get(Number(c.gid));
  document.querySelector(".dhead .eyebrow").textContent = "H3 HOTSPOT CLUSTER";
  document.querySelector(".dhead h2").textContent = `${c.place} — ${c.n_cells}-cell cluster`;
  document.querySelector(".dhead .where").textContent =
    `${c.country} · ${c.area_km2} km² · centre ${c.lat.toFixed(4)}, ${c.lon.toFixed(4)}`;
  drawer.querySelector(".dbody").innerHTML = `
    <div class="bigrow"><div class="bigscore num" style="color:${heatCss(c.score,1)}">${c.score}</div>
      <div class="bigmeta"><div>Cluster score</div>
        <div>Confidence <b class="num">${c.confidence}%</b></div>
        <div>Freshest signal <b>${ago(c.min_age_hours)}</b></div></div></div>
    <div class="sec"><h4>What is in this cluster</h4>
      <dl class="kv">
        <dt>H3 cells (res ${D.meta.fine_res})</dt><dd class="num">${c.n_cells}</dd>
        <dt>Evidence items</dt><dd class="num">${c.evidence}</dd>
        <dt>Independent sources</dt><dd class="num">${c.sources.length}</dd>
        ${Object.entries(c.families).map(([k,v]) => `<dt>${esc(k)} weight</dt><dd class="num">${v}</dd>`).join("")}
      </dl></div>
    <div class="sec"><h4>Dominant venue types</h4>
      <div class="rsub">${c.dominant.map(d => `<span class="chip">${esc(d)}</span>`).join("")}</div></div>
    ${c.landmarks.length ? `<div class="sec"><h4>Named places inside it</h4>
      <div class="tiny" style="margin-bottom:6px">The cluster is not given an invented neighbourhood
      name. These are the actual mapped objects it contains.</div>
      ${c.landmarks.map(t => `<div class="evrow"><span class="et">${esc(t)}</span></div>`).join("")}</div>` : ""}
    ${L ? `<div class="sec"><h4>Its city</h4>
      <button class="hotrow" data-gid="${L.gid}"><span><b>${esc(L.name)}</b>
        <span class="em" style="display:block;color:var(--muted);font-size:11px">Open the full locality report</span></span>
        <span class="num" style="color:${heatCss(L.live_score,1)};font-weight:600">${L.live_score}</span></button></div>` : ""}`;
  drawer.querySelectorAll("[data-gid]").forEach(b =>
    b.onclick = () => selectLocality(Number(b.dataset.gid)));
  renderRail(); setTimeout(resize, 30);
}

function selectCell(c){
  const lv = level(c.res), raw = lv.raw, i = c.i;
  const L = byGid.get(raw.g[i]);
  S.sel = {kind:"cell", res:c.res, i, gid: raw.g[i]};
  app.classList.add("drawer-open"); app.classList.remove("rail-open");
  drawer.scrollTop = 0;
  const sub = raw.sub[i];
  document.querySelector(".dhead .eyebrow").textContent = `H3 CELL · RESOLUTION ${c.res}`;
  document.querySelector(".dhead h2").textContent = L ? L.name : "H3 cell";
  document.querySelector(".dhead .where").textContent =
    `${L ? L.country + " · " : ""}cell edge ${RES_KM[c.res]} · ${raw.n[i]} evidence items`;
  drawer.querySelector(".dbody").innerHTML = `
    <div class="bigrow"><div class="bigscore num" style="color:${heatCss(raw.s[i],1)}">${raw.s[i]}</div>
      <div class="bigmeta"><div>${bandOf(raw.s[i])}</div>
        <div>Confidence <b class="num">${raw.c[i]}%</b></div>
        <div>Freshest signal <b>${ago(raw.a[i])}</b></div></div></div>
    <div class="sec"><h4>Cell breakdown</h4>
      ${metric("Coworking", sub[0])}${metric("Community", sub[1])}
      ${metric("International", sub[2])}${metric("Social", sub[3])}${metric("Events", sub[4])}</div>
    <div class="sec"><h4>Evidence</h4><dl class="kv">
      <dt>Items in cell</dt><dd class="num">${raw.n[i]}</dd>
      <dt>Independent sources</dt><dd class="num">${raw.u[i]}</dd>
      <dt>Dominant types</dt><dd>${esc(((raw.k[i]||0)||[]).length ? raw.k[i].join(", ") : "—")}</dd></dl>
      ${((raw.ti[i]||0)||[]).length ? `<div style="margin-top:8px">${raw.ti[i].map(t =>
        `<div class="evrow"><span class="et">${esc(t)}</span></div>`).join("")}</div>` : ""}
      <div class="tiny" style="margin-top:8px">Only point-precision evidence is placed in cells.
        City-precision evidence (community posts, events without a mapped venue) is counted for the
        locality but never assigned to a neighbourhood.</div></div>
    ${L ? `<div class="sec"><h4>Its city</h4><button class="hotrow" data-gid="${L.gid}">
      <span><b>${esc(L.name)}</b><span class="em" style="display:block;color:var(--muted);font-size:11px">
      Open the full locality report</span></span>
      <span class="num" style="color:${heatCss(L.live_score,1)};font-weight:600">${L.live_score}</span></button></div>` : ""}`;
  drawer.querySelectorAll("[data-gid]").forEach(b =>
    b.onclick = () => selectLocality(Number(b.dataset.gid)));
  draw(); setTimeout(resize, 30);
}
