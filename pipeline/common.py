"""Nomad Radar - shared fetch infrastructure.

Implements the resilient adapter substrate required by the spec:
retries, exponential backoff, timeouts, on-disk caching, circuit breakers
and a persistent source-health registry. Adapters fail independently:
one dead source must never break the world scan.
"""
from __future__ import annotations
import gzip, hashlib, json, os, random, ssl, threading, time
import urllib.error, urllib.parse, urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
CACHE = os.path.join(DATA, "cache")
REGISTRY_PATH = os.path.join(DATA, "source_registry.json")
UA = "NomadRadar/1.0 (open-data research bot; +https://github.com/granterogers/nomad-map)"

os.makedirs(CACHE, exist_ok=True)

_lock = threading.Lock()
_registry: dict = {}
if os.path.exists(REGISTRY_PATH):
    try:
        _registry = json.load(open(REGISTRY_PATH))
    except Exception:
        _registry = {}


def _now() -> float:
    return time.time()


def iso(ts: float | None = None) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts if ts is not None else _now()))


def register(source_id: str, **fields):
    """Update the persistent source registry (spec §31)."""
    fields.setdefault("adapter_version", "1.0")
    with _lock:
        rec = _registry.setdefault(source_id, {
            "source_id": source_id, "success_count": 0, "failure_count": 0,
            "last_checked": None, "last_success": None, "last_failure": None,
        })
        rec.update(fields)


def note_result(source_id: str, ok: bool, detail: str = ""):
    with _lock:
        rec = _registry.setdefault(source_id, {
            "source_id": source_id, "success_count": 0, "failure_count": 0,
            "last_checked": None, "last_success": None, "last_failure": None,
        })
        rec["last_checked"] = iso()
        if ok:
            rec["success_count"] += 1
            rec["last_success"] = iso()
        else:
            rec["failure_count"] += 1
            rec["last_failure"] = iso()
            if detail:
                rec["last_error"] = detail[:200]
        tot = rec["success_count"] + rec["failure_count"]
        rec["reliability"] = round(rec["success_count"] / tot, 3) if tot else 0.0


def save_registry():
    """Merge-then-write. Pipeline steps run concurrently and each holds its own
    in-memory copy, so a plain overwrite loses whatever another step registered
    while this one was running."""
    with _lock:
        merged = {}
        if os.path.exists(REGISTRY_PATH):
            try:
                merged = json.load(open(REGISTRY_PATH))
            except Exception:
                merged = {}
        for k, v in _registry.items():
            cur = merged.get(k, {})
            cur.update({kk: vv for kk, vv in v.items() if vv is not None})
            if v.get("success_count", 0) or v.get("failure_count", 0):
                cur["success_count"] = max(cur.get("success_count", 0), v.get("success_count", 0))
                cur["failure_count"] = max(cur.get("failure_count", 0), v.get("failure_count", 0))
                tot = cur["success_count"] + cur["failure_count"]
                cur["reliability"] = round(cur["success_count"] / tot, 3) if tot else 0.0
            merged[k] = cur
        tmp = REGISTRY_PATH + ".tmp"
        json.dump(merged, open(tmp, "w"), indent=1, sort_keys=True)
        os.replace(tmp, REGISTRY_PATH)
        _registry.update(merged)


def registry_snapshot() -> dict:
    with _lock:
        return json.loads(json.dumps(_registry))


class CircuitBreaker:
    """Trip after N consecutive failures; recover after a cool-down."""

    def __init__(self, threshold=12, cooldown=90):
        self.threshold, self.cooldown = threshold, cooldown
        self.fails, self.opened_at = 0, 0.0
        self.lock = threading.Lock()

    def allow(self) -> bool:
        with self.lock:
            if self.fails < self.threshold:
                return True
            if _now() - self.opened_at > self.cooldown:
                self.fails = self.threshold - 1  # half-open: allow a probe
                return True
            return False

    def ok(self):
        with self.lock:
            self.fails = 0

    def fail(self):
        with self.lock:
            self.fails += 1
            if self.fails == self.threshold:
                self.opened_at = _now()


class RateLimiter:
    """Minimum wall-clock gap between requests to one host."""

    def __init__(self, min_gap: float):
        self.min_gap, self.last, self.lock = min_gap, 0.0, threading.Lock()

    def wait(self):
        with self.lock:
            gap = _now() - self.last
            if gap < self.min_gap:
                time.sleep(self.min_gap - gap)
            self.last = _now()


def cache_path(key: str) -> str:
    h = hashlib.sha1(key.encode()).hexdigest()
    return os.path.join(CACHE, h[:2], h + ".json.gz")


def cache_get(key: str, max_age: float):
    p = cache_path(key)
    if os.path.exists(p) and (_now() - os.path.getmtime(p)) < max_age:
        try:
            with gzip.open(p, "rt", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def cache_put(key: str, value):
    p = cache_path(key)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(value, f)
    os.replace(tmp, p)


def fetch(url: str, *, source_id: str, data: bytes | str | None = None,
          headers: dict | None = None, timeout: int = 45, retries: int = 4,
          backoff: float = 2.0, limiter: RateLimiter | None = None,
          breaker: CircuitBreaker | None = None, as_json: bool = False,
          cache_ttl: float = 0.0, cache_key: str | None = None,
          accept_status: tuple = (200,)):
    """Fetch with retries/backoff/caching. Returns bytes|dict, or None on failure."""
    key = cache_key or (url + "||" + (data if isinstance(data, str) else (data or b"").decode("utf-8", "replace")))
    if cache_ttl > 0:
        hit = cache_get(key, cache_ttl)
        if hit is not None:
            return hit.get("body") if as_json else (hit.get("body") or "").encode()

    if breaker and not breaker.allow():
        note_result(source_id, False, "circuit breaker open")
        return None

    body = data.encode() if isinstance(data, str) else data
    last_err = ""
    for attempt in range(retries + 1):
        if limiter:
            limiter.wait()
        try:
            req = urllib.request.Request(url, data=body, method="POST" if body else "GET")
            req.add_header("User-Agent", UA)
            req.add_header("Accept-Encoding", "gzip")
            if body and not (headers or {}).get("Content-Type"):
                req.add_header("Content-Type", "application/x-www-form-urlencoded")
            for k, v in (headers or {}).items():
                req.add_header(k, v)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
                if r.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                if r.status not in accept_status:
                    raise urllib.error.HTTPError(url, r.status, "unexpected status", r.headers, None)
                out = json.loads(raw.decode("utf-8")) if as_json else raw
                if breaker:
                    breaker.ok()
                note_result(source_id, True)
                if cache_ttl > 0:
                    cache_put(key, {"body": out if as_json else raw.decode("utf-8", "replace"),
                                    "fetched_at": iso()})
                return out
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            code = getattr(e, "code", None)
            if code in (401, 403, 404):     # hard denial: do not hammer
                break
            if attempt < retries:
                time.sleep(backoff * (2 ** attempt) * (0.6 + 0.8 * random.random()))
    if breaker:
        breaker.fail()
    note_result(source_id, False, last_err)
    return None


def write_json(relpath: str, obj, indent=None):
    p = os.path.join(DATA, relpath)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(obj, open(p, "w"), indent=indent, separators=(",", ":") if indent is None else None)
    return p


def read_json(relpath: str, default=None):
    p = os.path.join(DATA, relpath)
    if not os.path.exists(p):
        return default
    return json.load(open(p))
