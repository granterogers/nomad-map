"""Optional credential loading.

Nomad Radar's default build requires zero secrets and that stays true: every
adapter that needs a credential is OFF unless one is present, and a missing
credential degrades that source to "contributing zero" rather than failing the
build. See docs/CREDENTIALS_HOW_TO_GET.md for where each one comes from, and
docs/CREDENTIALS_TO_COLLECT.md for the sheet that gets filled in and returned.

Looks for, in order:
  $NOMAD_RADAR_ENV
  ./nomad-radar.env
  ./secrets/nomad-radar.env
  ~/.nomad-radar.env
"""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CANDIDATES = [
    os.environ.get("NOMAD_RADAR_ENV"),
    os.path.join(ROOT, "nomad-radar.env"),
    os.path.join(ROOT, "secrets", "nomad-radar.env"),
    os.path.expanduser("~/.nomad-radar.env"),
]

# key -> (env var names required, what it unlocks)
SERVICES = {
    "numbeo":     (["NUMBEO_API_KEY"], "city-level cost of living"),
    "eventbrite": (["EVENTBRITE_PRIVATE_TOKEN"], "events in Latin America and SE Asia"),
    "foursquare": (["FOURSQUARE_API_KEY"], "venues independent of OpenStreetMap"),
    "google_places": (["GOOGLE_MAPS_API_KEY"], "venues independent of OpenStreetMap"),
    "meetup":     (["MEETUP_CLIENT_ID", "MEETUP_CLIENT_SECRET"], "unbiased group and RSVP data"),
    "facebook":   (["FACEBOOK_ACCESS_TOKEN"], "communities outside Europe and North America"),
    "instagram":  (["INSTAGRAM_ACCESS_TOKEN"], "geotagged activity volume"),
    "cloudflare_radar": (["CLOUDFLARE_RADAR_API_TOKEN"], "internet quality per location"),
    "reddit":     (["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"], "community beyond the RSS cap"),
    "wikimedia":  (["WIKIMEDIA_ACCESS_TOKEN"], "live per-language attention"),
    "nomads":     (["NOMADS_API_KEY"], "calibration reference"),
}

_loaded = None


def load():
    """Parse the first credentials file found. Values already in the process
    environment win, so a single export can override the file."""
    global _loaded
    if _loaded is not None:
        return _loaded
    values, source = {}, None
    for path in CANDIDATES:
        if path and os.path.exists(path):
            source = path
            for line in open(path, encoding="utf-8"):
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                v = v.strip().strip('"').strip("'")
                if v:
                    values[k.strip()] = v
            break
    for k in list(values):
        values[k] = os.environ.get(k, values[k])
    for svc, (keys, _) in SERVICES.items():
        for k in keys:
            if k in os.environ and os.environ[k]:
                values[k] = os.environ[k]
    _loaded = {"values": values, "source": source}
    return _loaded


def get(name, default=None):
    return load()["values"].get(name, default)


def has(service):
    keys, _ = SERVICES[service]
    return all(get(k) for k in keys)


def status():
    st = load()
    lines = [f"credentials file: {st['source'] or 'none found (running credential-free)'}"]
    for svc, (keys, unlocks) in SERVICES.items():
        state = "ENABLED " if has(svc) else "disabled"
        lines.append(f"  {state}  {svc:18} {unlocks}")
    n = sum(1 for s in SERVICES if has(s))
    lines.append(f"{n} of {len(SERVICES)} optional sources enabled; "
                 f"the build works with none of them.")
    return "\n".join(lines)


if __name__ == "__main__":
    print(status())
