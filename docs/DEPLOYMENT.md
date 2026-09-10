# Deployment

## What is deployed

A single self-contained HTML file, `dist/nomad-radar.html` (~14 MB), published
as a Claude Artifact. It contains the page, its styles, its script and the
entire precomputed dataset. Opening the URL is the only thing a user has to do.

## Why this target

The build environment was inspected for already-authorised hosting before
anything else. The available options were:

| Option | Verdict |
|---|---|
| **Claude Artifacts** | **Chosen.** Already authorised in this session, public URL, no account, no key, no DNS, no cost. |
| GitHub Pages | The repository is reachable through the GitHub app, but enabling Pages needs a repository-settings change the agent cannot make without the user. |
| Vercel / Netlify / Cloudflare | No existing authentication in this environment; all require the user to create an account and a token. |
| Any managed database | Requires a project the user must create. Rejected outright — this is exactly the intervention the brief forbids. |

Artifacts is the only option that returns a live URL with zero user
intervention, so it decided the architecture: a static, fully self-contained
page rather than a server plus database.

## Constraints the host imposes, and how they are met

**No external images.** The host's CSP blocks image requests to any origin, so
raster map tiles are impossible. Every country outline and every hexagon
boundary is therefore projected at build time and drawn on a canvas. The page
is a real map with no tile server.

**16 MB page limit.** Ship-time pruning drops cells below an evidence-weight
threshold, per-resolution caps bound each zoom level, localities are shipped
only where they carry real evidence, and the wire format carries no repeated
JSON keys — the client expands rows into objects at load. The full unpruned
model stays in `data/scored.json` in the repository.

**Fonts.** Google Fonts is the one stylesheet host the CSP admits; IBM Plex
Sans / Sans Condensed / Mono load from there, each with a real fallback stack,
so the page is correct even if the request fails.

**No runtime network.** The page makes no fetch calls at all. It works offline
once loaded.

## Rebuilding and republishing

```bash
python3 pipeline/step1_geobase.py … step8_build.py   # see README
```

Republishing the same file path updates the same URL. Cache TTLs mean a rebuild
only re-fetches what has expired, so a refresh is minutes, not the full build.

## Cost

€0/month. Every source is anonymous and free; the host is already provisioned;
there is no server, database, queue or scheduler to pay for.
