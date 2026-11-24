# Deployment

## What is deployed

A single self-contained HTML file, `dist/nomad-radar.html`. It contains the
page, its styles, its script and the entire precomputed dataset. Opening the
URL is the only thing a user has to do.

It is published to **two** targets, from the same file:

| Target | URL | Ceiling | Build |
|---|---|---|---|
| **GitHub Pages** (primary) | https://granterogers.github.io/nomad-map/ | 100 MB/file | `NOMAD_SHIP_SCALE=2 ./build.sh && ./deploy-pages.sh` |
| Claude Artifact | private link, see README | 16 MB/page | `./build.sh`, then publish the file |

Pages is the primary public URL: no login, nothing to authorise, and a ceiling
high enough that the payload budget stops being the thing that decides how much
of the model a visitor can see.

## Why this target

The build environment was inspected for already-authorised hosting before
anything else. The available options were:

| Option | Verdict |
|---|---|
| **Claude Artifacts** | **Chosen.** Already authorised in this session, public URL, no account, no key, no DNS, no cost. |
| **GitHub Pages** | **Now also chosen, and primary.** Rejected originally because enabling it needs a repository-settings change an agent cannot make unattended — which remains true, and is a genuine one-off cost, not an avoided one. The repository is public, so Pages is free. |
| Vercel / Netlify / Cloudflare | No existing authentication in this environment; all require the user to create an account and a token. |
| Any managed database | Requires a project the user must create. Rejected outright — this is exactly the intervention the brief forbids. |

Artifacts was the only option returning a live URL with *zero* user
intervention, so it decided the architecture: a static, fully self-contained
page rather than a server plus database. That architecture is why adding Pages
later cost almost nothing — the artifact of the build was already a single
static file with no runtime dependencies.

## Constraints the host imposes, and how they are met

**No external images.** The host's CSP blocks image requests to any origin, so
raster map tiles are impossible. Every country outline and every hexagon
boundary is therefore projected at build time and drawn on a canvas. The page
is a real map with no tile server.

**Page size limits.** Ship-time pruning drops cells below an evidence-weight
threshold, per-resolution caps bound each zoom level, localities are shipped
only where they carry real evidence, and the wire format carries no repeated
JSON keys — the client expands rows into objects at load. The full unpruned
model stays in `data/scored.json` in the repository.

The caps are a payload budget, not a limit on the model, and the two targets
have very different ceilings — 16 MB for the Artifact, 100 MB for Pages. Rather
than keep two forks of the numbers, `NOMAD_SHIP_SCALE` scales them:
`1` (the default) is the Artifact-safe build. It governs only how much of the
model reaches the browser and touches no scoring. `deploy-pages.sh` refuses to
publish above 50 MB, where GitHub starts warning about file size.

**Fonts.** Google Fonts is the one stylesheet host the CSP admits; IBM Plex
Sans / Sans Condensed / Mono load from there, each with a real fallback stack,
so the page is correct even if the request fails.

**No runtime network.** The page makes no fetch calls at all. It works offline
once loaded.

## Rebuilding and republishing

```bash
./build.sh                                   # Artifact-sized build
NOMAD_SHIP_SCALE=2 ./build.sh                # Pages-sized build
./deploy-pages.sh                            # push to gh-pages
```

Republishing the Artifact to the same file path updates the same URL. Cache
TTLs mean a rebuild only re-fetches what has expired, so a refresh is minutes
rather than the full build — **on a warm checkout**. A cold one re-fetches
everything, including the GeoNames dumps, which `step1_geobase.py` now
downloads itself.

### How Pages is served

`deploy-pages.sh` force-pushes an orphan `gh-pages` branch containing only
`index.html` and a `.nojekyll`. Orphan and force-pushed deliberately: the page
is a ~20 MB build artifact, so committing it to the source branch would add
another 20 MB blob to the history of every clone on every rebuild. An orphan
branch that is replaced each time keeps that out of the repository people
actually work in.

Enabling Pages is a one-off manual step: **Settings → Pages → Source: Deploy
from a branch → `gh-pages` / root**.

## Cost

€0/month. Every source is anonymous and free; both hosts are free (GitHub Pages
is free for public repositories); there is no server, database, queue or
scheduler to pay for.
