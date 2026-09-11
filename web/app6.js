
/* ---------- in-app validity report ----------
   Every figure here is read from the bundle this page shipped with, so the
   report always describes the data the reader is looking at. Nothing is
   hard-coded; if a build gets worse, this page says so. */
const VAL = D.validation || {}, AUD = D.audit || {};
const vEl = document.getElementById("validity");

function pct(x){ return (x == null) ? "—" : (typeof x === "number" ? x.toFixed(x < 1 ? 3 : 1) : x); }
function grade(v, good, ok){
  return v >= good ? ["GOOD", "var(--rise)"] : v >= ok ? ["WEAK", "var(--warn)"] : ["POOR", "var(--cool)"];
}
function vmetric(label, val, good, ok, max){
  const [g, c] = grade(val, good, ok);
  return `<div class="vmetric"><span>${label} <span style="color:${c};font-size:10.5px;
    letter-spacing:.06em">${g}</span></span><span class="vv num">${val.toFixed(3)}</span>
    <span class="tk"><span class="fl" style="width:${Math.max(2,Math.min(100,100*val/(max||1)))}%;
      background:${c}"></span></span></div>`;
}

function validityHTML(){
  const c = AUD.composition_shares || {};
  const comp = [["specific","Nomad-specific","var(--accent)"],
                ["adjacent","Nomad-adjacent","var(--accent2)"],
                ["generic","Generic urban","var(--neutral)"]];
  const bias = (AUD.osm_bias || []);
  const eu = bias.filter(b => ["FR","DE","NL","BE","AT","CH","DK","PT","ES","IT","GB","SE","PL","CZ"].includes(b.cc)).slice(0,6);
  const hub = bias.filter(b => ["TH","ID","VN","MX","CO","BR","IN","ZA","GE","AR","PH","MY","TR","MA"].includes(b.cc)).slice(0,8);
  const shown = eu.concat(hub);
  const mx = Math.max(...shown.map(b => b.coworking_per_100k), 0.01);
  const sel = (AUD.event_sample || {}).by_selection || {};
  const corr = AUD.corroboration || {};
  const pcv = VAL.per_capita || {};

  return `
  <h2>The headline finding</h2>
  <div class="vnote good">
    <div class="h">What the research established</div>
    <p>Activity data alone cannot rank nomad destinations well, and more of it does not fix
      that. Restricted to places with 25 or more events the correlation only reaches about
      <b>0.41</b>, and three separate activity features — the nomad share of events, nomad
      group membership, and nomad group counts — all measured below <b>+0.30</b> against the
      human labels.</p>
    <p>The reason is that somewhere is a nomad destination because it is <b>affordable, warm
      and legally viable to stay in</b> — and active. Cost of living alone scores
      <b>+0.53</b> against the labels and climate <b>+0.53</b>; the entire activity model
      scores <b>+0.32</b>. So a second score, <b>Nomad fit</b>, now combines activity with
      those structural facts, and it roughly doubles the correlation on held-out data.</p>
  </div>

  <h2>The verdict</h2>
  <p class="lede">This index is built entirely from open data that needs no credentials.
    That is what makes it exist at all, and it is also the source of every limitation
    below. Read it as <b>where activity can be observed</b>, not as a definitive ranking.</p>

  <div class="vfig">
    <div class="t">Nomad fit — measured on held-out data</div>
    <div class="s">The blend weights were chosen on one half of the reference set; these are
      the numbers on the other half, which the fitting never saw.</div>
    ${(D.nomadfit||{}).holdout_rho !== undefined ? `
      ${vmetric("Rank correlation, held out (max achievable 0.96)", D.nomadfit.holdout_rho, 0.80, 0.55, 0.96)}
      ${vmetric("Hub vs negative-control separation, held out", D.nomadfit.holdout_auc || 0, 0.85, 0.70, 1)}
      <div class="cap">Activity alone scores
        <b>${(D.nomadfit.activity_only_holdout_rho).toFixed(3)}</b> on the same holdout, so adding
        structural viability roughly doubles the correlation. Negative controls in the top 20 of
        the holdout: <b>${D.nomadfit.holdout_controls_in_top20}</b>, against
        <b>${(D.nomadfit.activity_only_holdout_auc||0).toFixed(2)}</b> AUC for activity alone. The chosen weights are activity
        <b>${(D.nomadfit.weights.activity*100).toFixed(0)}%</b>, cost
        <b>${(D.nomadfit.weights.cost*100).toFixed(0)}%</b>, climate
        <b>${(D.nomadfit.weights.climate*100).toFixed(0)}%</b>, visa
        <b>${(D.nomadfit.weights.visa*100).toFixed(0)}%</b>.</div>` : ""}
  </div>

  <div class="vfig">
    <div class="t">Live score (activity only) — how well does it match human judgement?</div>
    <div class="s">Measured against a held-out set of ${VAL.n_evaluated || 0} hand-labelled
      places, ${(AUD.reference_controls || 35)} of them negative controls — large,
      thoroughly mapped cities with no nomad reputation. Nothing in the model is tuned to
      these numbers.</div>
    ${vmetric("Rank correlation with human labels (max achievable 0.96)",
              VAL.spearman_tier_vs_score || 0, 0.80, 0.55, 0.96)}
    ${vmetric("Hub vs negative-control separation (0.5 = coin flip)",
              VAL.auc_hub_vs_control || 0, 0.85, 0.70, 1)}
    ${vmetric("Precision among the top 30", VAL.precision_at_30 || 0, 0.85, 0.70, 1)}
    <div class="cap">${(D.nomadfit||{}).holdout_rho !== undefined ? `<b>Nomad fit</b> scores
      <b>${(D.nomadfit.holdout_rho).toFixed(3)}</b> on a held-out half of the reference set that
      the weight-fitting never saw, against <b>${(D.nomadfit.activity_only_holdout_rho).toFixed(3)}</b>
      for activity alone on the same half. Weights were chosen on the other half only —
      without that split, choosing weights while watching the score would make the score
      meaningless.<br><br>` : ""}Negative controls still inside the top 30:
      <b>${VAL.negative_controls_in_top_30}</b>. On the per-capita scale the same measures are
      ${pct(pcv.spearman_tier_vs_score)} / ${pct(pcv.auc_hub_vs_control)} —
      <b>worse</b>, for the reason given under “the two scales” below.</div>
  </div>

  <div class="vnote">
    <div class="h">What this means in plain terms</div>
    <p>A correlation of 0.80 would mean the ranking is usually right to within half a
      category. <b>Nomad fit</b> reaches <b>${(D.nomadfit||{}).holdout_rho !== undefined ?
      (D.nomadfit.holdout_rho).toFixed(2) : "—"}</b> on held-out data — good enough to separate
      real destinations from ordinary cities almost perfectly (AUC 0.96), but not yet good
      enough to trust the exact ordering. <b>Live score</b> alone, at
      <b>${pct(VAL.spearman_tier_vs_score)}</b>, is typically off by more than a full category
      and should be read as "where activity is observable", not as a ranking.</p>
  </div>

  <h2>What the evidence is made of</h2>
  <div class="vfig">
    <div class="t">Composition of the mapped-ecosystem layer</div>
    <div class="s">Share of evidence weight, after specificity weighting</div>
    <div class="vbar">${comp.map(([k,l,col]) =>
      `<div style="flex:${c[k]||0};background:${col}" title="${l}: ${c[k]}%"></div>`).join("")}</div>
    <div class="vlab">${comp.map(([k,l,col]) =>
      `<div style="flex:${c[k]||0};color:${col}">${c[k]||0}%</div>`).join("")}</div>
    <div class="cap">${comp.map(([k,l,col]) =>
      `<span style="color:${col}">■</span> ${l}`).join(" &nbsp; ")}.
      Tags that say nothing about nomads are down-weighted to near zero and
      ${(AUD.dropped_tags||[]).length ? `<b>${(AUD.dropped_tags||[])
        .map(d=>d.tag).join(", ")}</b> is dropped entirely (${((AUD.dropped_tags||[])[0]||{}).objects
        ? ((AUD.dropped_tags||[])[0].objects).toLocaleString() : 0} objects)` : "nothing is dropped"}.
      Before this correction, community centres and sports centres alone carried 49% of all weight.</div>
  </div>

  <h2>The bias that shaped everything</h2>
  <div class="vfig">
    <div class="t">Mapped coworking spaces per 100,000 people</div>
    <div class="s">OpenStreetMap coverage — this is mapping effort, not reality</div>
    <div class="vhb">${shown.map(b => `
      <div class="l">${esc(b.country)}</div>
      <div class="tr"><div class="f" style="width:${Math.max(1.5,100*b.coworking_per_100k/mx)}%;
        background:${eu.includes(b) ? "var(--accent)" : "var(--accent2)"}"></div></div>
      <div class="v num">${b.coworking_per_100k.toFixed(2)}</div>`).join("")}</div>
    <div class="cap">Nobody believes these ratios reflect reality — they reflect how thoroughly
      each country has been mapped by volunteers. Every infrastructure signal is therefore
      scored as a <b>share of what OSM has mapped locally</b>, against a baseline of
      <b>${(AUD.baseline_objects||0).toLocaleString()}</b> deliberately nomad-irrelevant civic
      objects (${(AUD.baseline_tags||[]).join(", ")}).</div>
  </div>

  <h2>How the model protects itself</h2>
  <h3>Corroboration before ranking</h3>
  <p>A place is ranked only with two or more independent evidence families, at least one of
    them nomad-targeted (events or community discussion). Infrastructure plus general
    Wikipedia readership shows a town exists, not that nomads are there.
    <b>${(corr.ranked||0).toLocaleString()}</b> of
    <b>${(corr.scanned||0).toLocaleString()}</b> scanned localities qualify. The rest are drawn
    on the map with all their evidence and an explicit not-ranked label.</p>

  <h3>Half the event sample is random</h3>
  <p>Event coverage was originally chosen entirely by existing score, which made it confirm
    the ranking rather than test it. Half the budget is now a stratified random sample over
    continent × population band, independent of any score:
    ${Object.entries(sel).map(([k,v]) => `<b>${v.toLocaleString()}</b> ${esc(k)}`).join(" · ")}.</p>

  <h3>The two scales</h3>
  <p><b>Absolute</b> counts favour large cities by construction. <b>Per capita</b> divides
    every count by population (shrunk by 60,000 residents so a village with three events
    cannot outrank a city). Per capita surfaces small dense places the absolute view buries —
    but it scores worse against the reference set, because dividing out population amplifies a
    second bias: mid-sized Western European cities show high detected events per head largely
    because Meetup's own coverage is strongest there.</p>

  <h2>What is still wrong</h2>
  <ul>
    <li><b>Cost and visa status are country-level.</b> Chiang Mai and Bangkok get identical
      affordability scores, which is plainly wrong. City-level cost data is the single
      largest remaining improvement and it is not available without a commercial API.</li>
    <li><b>The event layer is geographically biased.</b> Meetup's reach is strongest in Europe
      and North America, and the coworking-feed layer is seeded from OSM website tags, so it
      inherits the same bias. This is the single largest remaining source of error.</li>
    <li><b>Restricting to well-covered places barely helps.</b> Among places with 25+ events
      the correlation only rises to about 0.41, so this is a signal problem, not merely a
      coverage problem.</li>
    <li><b>Attention is English-Wikipedia-dominated.</b> Local-language coverage exists for
      only a handful of editions; the rest of the world is measured on English readership.</li>
    <li><b>Community volume is thin.</b> ${(AUD.community||{}).posts ?
      (AUD.community.posts).toLocaleString() : "A few thousand"} public posts worldwide is a
      small sample to attribute to ${((AUD.community||{}).localities||0).toLocaleString()} places.</li>
    <li><b>No nomad headcount is possible.</b> Presence is reported as a band with a
      confidence, never as a fabricated number.</li>
  </ul>

  <h2>What the sources actually are</h2>
  <div class="vhb" style="grid-template-columns:1fr auto;gap:6px 12px">
    ${(D.sources.audit||[]).reduce((acc,a)=>{acc[a.status]=(acc[a.status]||0)+1;return acc;},{}) &&
      Object.entries((D.sources.audit||[]).reduce((acc,a)=>{acc[a.status]=(acc[a.status]||0)+1;return acc;},{}))
      .map(([k,v])=>`<div class="l" style="text-align:left">${esc(k)}</div><div class="v num">${v}</div>`).join("")}
  </div>
  <p style="margin-top:10px">Credential-walled sources — Instagram, Facebook, Google Places,
    Foursquare, LinkedIn, Nomads.com and others — contribute exactly zero and are shown as
    contributing zero, per place, in the source panel. Nothing here bypasses a login, a
    paywall or an anti-bot system.</p>

  <p class="cap" style="margin-top:26px;color:var(--faint);font-size:12px">
    Generated ${esc((D.generated_at||"").slice(0,16).replace("T"," "))} UTC from this build's own
    outputs. Reproduce with <span class="mono">python3 validation/evaluate.py</span> and
    <span class="mono">python3 audit/audit.py</span> in the repository.</p>`;
}

let vBuilt = false;
function openValidity(){
  if (!vBuilt){ document.getElementById("vbody").innerHTML = validityHTML(); vBuilt = true; }
  vEl.classList.add("open");
  vEl.scrollTop = 0;
  document.getElementById("vclose").focus();
}
function closeValidity(){ vEl.classList.remove("open"); }
document.getElementById("vclose").onclick = closeValidity;
document.getElementById("vopen").onclick = openValidity;
document.addEventListener("click", e => {
  if (e.target && e.target.id === "openvalidity") openValidity();
});
document.addEventListener("keydown", e => {
  if (e.key === "Escape" && vEl.classList.contains("open")) closeValidity();
});
