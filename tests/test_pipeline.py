"""Nomad Radar test suite (spec §58).

Covers geospatial/H3 behaviour, scoring monotonicity, dedup, degraded-source
handling, empty/stale data, roll-up correctness and the shipped bundle's
integrity. Run: python3 tests/test_pipeline.py
"""
import json, math, os, sys, unittest
from collections import defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))
import h3
import common
import step6_h3 as S6
import step7_artifacts as S7

DATA = os.path.join(ROOT, "data")


def load(name, default=None):
    p = os.path.join(DATA, name)
    return json.load(open(p)) if os.path.exists(p) else default


def decode_localities(bundle):
    """Mirror of the client-side decoder: localities ship as keyless rows."""
    S, PK, SK, WC = (bundle["loc_schema"], bundle["part_keys"],
                     bundle["source_keys"], bundle["warn_codes"])
    out = []
    for row in bundle["localities"]:
        L = {S[i]: (row[i] if i < len(row) else None) for i in range(len(S))}
        parts = L.get("parts") or []
        L["parts"] = {k: (parts[i] if i < len(parts) else 0) for i, k in enumerate(PK)}
        mask = L.get("sources") or 0
        L["sources"] = [s for i, s in enumerate(SK) if mask & (1 << i)]
        L["warnings"] = [{"code": WC[c] if 0 <= c < len(WC) else "NOTE", "detail": d}
                         for c, d in (L.get("warnings") or [])]
        for k in ("live_score", "confidence", "evidence_count", "unique_sources",
                  "n_clusters", "n_cells", "pop"):
            L[k] = L.get(k) or 0
        L["band"] = S6.band(L["live_score"])
        L["presence"] = S6.presence_band(L["parts"]["nomad_presence"])
        L["momentum"] = S6.momentum_label(L.get("momentum_ratio"))
        L["freshness"] = S6.freshness_label(L.get("freshest_hours"))
        out.append(L)
    return out


def decode_evidence(bundle, items):
    K, SRC, T = bundle["ev_keys"], bundle["ev_sources"], bundle["ev_types"]
    out = []
    for e in items:
        o = {K[k]: v for k, v in e.items() if k in K}
        o["type"] = T[o.get("type", 0)]
        o["precision"] = "point" if e.get("p") else "locality"
        out.append(o)
    return out


class TestH3Model(unittest.TestCase):
    def test_parent_child_consistency(self):
        cell = h3.latlng_to_cell(38.7139, -9.1394, 8)
        for res in (7, 6, 5, 4, 3, 2):
            parent = h3.cell_to_parent(cell, res)
            self.assertEqual(h3.get_resolution(parent), res)
            self.assertIn(cell, h3.cell_to_children(parent, 8))

    def test_rollup_preserves_evidence_counts(self):
        cells = {}
        for lat, lon in [(38.71, -9.14), (38.715, -9.142), (38.72, -9.15), (41.39, 2.16)]:
            c = h3.latlng_to_cell(lat, lon, 8)
            cells[c] = {"h3": c, "res": 8, "gid": "1", "w": defaultdict(float, {"coworking": 2.0}),
                        "n": 3, "sources": {"osm"}, "kinds": __import__("collections").Counter({"cafe": 1}),
                        "titles": [], "min_age": 5.0}
        levels = S6.rollup(cells)
        total_fine = sum(c["n"] for c in cells.values())
        for res in (7, 6, 5, 4, 3, 2):
            self.assertEqual(sum(c["n"] for c in levels[res].values()), total_fine,
                             f"evidence lost at res {res}")
        self.assertLessEqual(len(levels[2]), len(levels[8]))

    def test_rollup_weights_sum(self):
        cells = {}
        for lat, lon in [(35.68, 139.69), (35.70, 139.72), (35.66, 139.75)]:
            c = h3.latlng_to_cell(lat, lon, 8)
            cells[c] = {"h3": c, "res": 8, "gid": "9", "w": defaultdict(float, {"event": 1.5}),
                        "n": 1, "sources": {"meetup"}, "kinds": __import__("collections").Counter(),
                        "titles": [], "min_age": 1.0}
        levels = S6.rollup(cells)
        self.assertAlmostEqual(sum(sum(c["w"].values()) for c in levels[4].values()),
                               3 * 1.5, places=6)

    def test_cell_scoring_is_monotonic(self):
        def mk(w):
            return {"w": defaultdict(float, w), "n": 5, "sources": {"a", "b"},
                    "kinds": __import__("collections").Counter()}
        _, low, _, _ = S6.score_cell(mk({"coworking": 1.0}))
        _, high, _, _ = S6.score_cell(mk({"coworking": 8.0}))
        self.assertGreater(high, low)

    def test_confidence_rises_with_independent_sources(self):
        base = {"w": defaultdict(float, {"coworking": 3.0}), "n": 6,
                "kinds": __import__("collections").Counter()}
        _, _, c1, _ = S6.score_cell({**base, "sources": {"a"}})
        _, _, c3, _ = S6.score_cell({**base, "sources": {"a", "b", "c"}})
        self.assertGreater(c3, c1)


class TestClustering(unittest.TestCase):
    def _cells(self, coords, weight=3.0):
        out = {}
        for lat, lon in coords:
            c = h3.latlng_to_cell(lat, lon, 8)
            out[c] = {"h3": c, "res": 8, "gid": "1", "w": defaultdict(float, {"coworking": weight}),
                      "n": 4, "sources": {"osm", "meetup"},
                      "kinds": __import__("collections").Counter({"coworking": 2}),
                      "titles": ["A"], "min_age": 3.0}
        return out

    def test_adjacent_cells_form_one_cluster(self):
        seed = h3.latlng_to_cell(38.7139, -9.1394, 8)
        ring = list(h3.grid_disk(seed, 1))
        cells = {}
        for c in ring:
            cells[c] = {"h3": c, "res": 8, "gid": "1", "w": defaultdict(float, {"coworking": 3.0}),
                        "n": 4, "sources": {"osm"}, "kinds": __import__("collections").Counter(),
                        "titles": [], "min_age": 2.0}
        cl = S6.cluster(cells, {"1": {"name": "X", "cc": "PT", "country": "Portugal"}})
        self.assertEqual(len(cl), 1)
        self.assertEqual(cl[0]["n_cells"], len(ring))

    def test_distant_cells_do_not_merge(self):
        # two adjacent cells in Lisbon, two adjacent cells in Barcelona
        a = h3.latlng_to_cell(38.7139, -9.1394, 8)
        b = h3.latlng_to_cell(41.3874, 2.1686, 8)
        coords = [h3.cell_to_latlng(a), h3.cell_to_latlng(list(h3.grid_disk(a, 1))[1]),
                  h3.cell_to_latlng(b), h3.cell_to_latlng(list(h3.grid_disk(b, 1))[1])]
        cells = self._cells(coords)
        cl = S6.cluster(cells, {"1": {"name": "X", "cc": "PT", "country": "Portugal"}})
        self.assertEqual(len(cl), 2)

    def test_single_cell_is_not_a_cluster(self):
        cells = self._cells([(1.29, 103.85)])
        self.assertEqual(len(S6.cluster(cells, {})), 0)

    def test_weak_cells_excluded(self):
        a = h3.latlng_to_cell(38.7139, -9.1394, 8)
        coords = [h3.cell_to_latlng(c) for c in list(h3.grid_disk(a, 1))[:4]]
        cells = self._cells(coords, weight=0.1)
        self.assertEqual(len(S6.cluster(cells, {})), 0)


class TestScoring(unittest.TestCase):
    place = {"gid": 1, "name": "T", "pop": 500000, "cc": "PT"}

    def test_empty_evidence_is_low_and_unconfident(self):
        m = S6.score_locality(self.place, [], [], [], {}, {}, {})
        self.assertLess(m["live_score"], 40)
        self.assertLess(m["confidence"], 55)
        self.assertEqual(m["evidence_count"], 0)
        self.assertEqual(m["momentum"], "UNKNOWN")

    def test_more_evidence_scores_higher(self):
        few = [{"type": "venue", "family": "coworking", "kind": "coworking", "weight": 3.0,
                "source_id": "osm", "age_hours": 0}]
        many = few * 1 + [{"type": "venue", "family": "coworking", "kind": "coworking",
                           "weight": 3.0, "source_id": "osm", "age_hours": 0} for _ in range(20)]
        a = S6.score_locality(self.place, few, [], [], {}, {}, {})
        b = S6.score_locality(self.place, many, [], [], {}, {}, {})
        self.assertGreater(b["live_score"], a["live_score"])

    def test_stale_events_are_excluded_from_upcoming(self):
        ev = [{"type": "event", "family": "event", "kind": "digital nomad", "weight": 1.0,
               "source_id": "meetup_public", "age_hours": 5000, "organizer": "O", "venue": "V"}]
        m = S6.score_locality(self.place, ev, [], [], {}, {}, {})
        self.assertEqual(m["events_upcoming"], 0)

    def test_single_organizer_warning(self):
        ev = [{"type": "event", "family": "event", "kind": "networking", "weight": 1.0,
               "source_id": "meetup_public", "age_hours": 10, "organizer": "Solo", "venue": f"V{i}"}
              for i in range(5)]
        m = S6.score_locality(self.place, ev, [], [], {}, {}, {})
        self.assertIn("EVENT ACTIVITY DOMINATED BY ONE ORGANIZER",
                      [w["code"] for w in m["warnings"]])

    def test_reputation_without_activity_is_flagged(self):
        att = {"daily_avg": 900.0, "recent_days_covered": 14, "momentum_ratio": 1.0}
        m = S6.score_locality(self.place, [], [], [], att, {}, {})
        self.assertIn("HISTORICALLY POPULAR, CURRENTLY QUIET",
                      [w["code"] for w in m["warnings"]])

    def test_cooling_is_detected(self):
        att = {"daily_avg": 100.0, "recent_days_covered": 14, "momentum_ratio": 0.6}
        m = S6.score_locality(self.place, [], [], [], att, {}, {})
        self.assertEqual(m["momentum"], "STRONGLY COOLING")

    def test_population_does_not_dominate_density(self):
        ev = [{"type": "event", "family": "event", "kind": "digital nomad", "weight": 1.0,
               "source_id": "meetup_public", "age_hours": 20, "organizer": f"O{i%4}",
               "venue": f"V{i}"} for i in range(12)]
        small = S6.score_locality({"gid": 1, "name": "S", "pop": 60000, "cc": "PT"}, ev, [], [], {}, {}, {})
        big = S6.score_locality({"gid": 2, "name": "B", "pop": 9000000, "cc": "PT"}, ev, [], [], {}, {}, {})
        self.assertGreaterEqual(small["active_community_density"],
                                big["active_community_density"] - 2)

    def test_weights_sum_to_one(self):
        self.assertAlmostEqual(sum(S6.WEIGHTS.values()), 1.0, places=6)

    def test_bands_and_labels(self):
        self.assertEqual(S6.band(95), "EXTREMELY HOT")
        self.assertEqual(S6.band(10), "LOW ACTIVITY")
        self.assertEqual(S6.presence_band(90), "VERY HIGH")
        self.assertEqual(S6.momentum_label(None), "UNKNOWN")
        self.assertEqual(S6.freshness_label(2), "LIVE")
        self.assertEqual(S6.freshness_label(None), "NO LIVE SIGNAL")
        self.assertEqual(S6.freshness_label(9999), "STALE")


class TestRollup(unittest.TestCase):
    def test_max_is_not_averaged_away(self):
        ls = [{"live_score": 95, "pop": 500000, "evidence_count": 90, "gid": 1, "name": "Hot",
               "lat": 1, "lon": 1, "n_clusters": 3, "confidence": 90, "cc": "PT", "country": "P"}]
        ls += [{"live_score": 12, "pop": 20000, "evidence_count": 2, "gid": i, "name": f"Q{i}",
                "lat": 1, "lon": 1, "n_clusters": 0, "confidence": 30, "cc": "PT", "country": "P"}
               for i in range(2, 40)]
        r = S6.admin_rollup(ls, lambda l: l["cc"], lambda l: l["country"])[0]
        self.assertEqual(r["max"], 95)
        self.assertLess(r["mean"], 30)
        self.assertEqual(r["top_locality"]["name"], "Hot")
        self.assertGreater(r["concentration"], 3)


class TestProjection(unittest.TestCase):
    def test_projection_bounds_and_direction(self):
        x0, y0 = S7.project(0, -180)
        x1, y1 = S7.project(0, 180)
        self.assertAlmostEqual(x0, 0, places=3)
        self.assertAlmostEqual(x1, S7.W, places=3)
        self.assertLess(S7.project(60, 0)[1], S7.project(-60, 0)[1])  # north is up

    def test_latitude_clamped(self):
        self.assertGreater(S7.project(-89.9, 0)[1], 0)
        self.assertLess(S7.project(89.9, 0)[1], S7.H + 1)

    def test_cell_encoding_roundtrip(self):
        cells = [{"h": h3.latlng_to_cell(38.71, -9.14, 8)},
                 {"h": h3.latlng_to_cell(-33.92, 18.42, 8)},
                 {"h": h3.latlng_to_cell(64.14, -21.94, 8)}]
        flat, meta = S7.encode_cells(cells)
        self.assertEqual(len(meta), 3)
        px = py = 0; p = 0
        for i in range(3):
            px += flat[p]; py += flat[p+1]; p += 2
            n = flat[p]; p += 1
            self.assertGreaterEqual(n, 5)
            cx, cy = px/4, py/4
            exp = S7.project(*h3.cell_to_latlng(meta[i]["h"]))
            self.assertLess(abs(cx - exp[0]), 3.0)
            self.assertLess(abs(cy - exp[1]), 3.0)
            p += n*2

    def test_antimeridian_cell_is_not_smeared(self):
        c = h3.latlng_to_cell(0.0, 179.99, 6)
        flat, meta = S7.encode_cells([{"h": c}])
        n = flat[2]
        xs = [flat[3 + 2*i] for i in range(n)]
        self.assertLess(max(xs) - min(xs), S7.W * 0.2)


class TestDedup(unittest.TestCase):
    def test_duplicate_events_counted_once(self):
        eco, evs = {}, {"1": {"scanned_at": common.iso(), "events": [
            {"title": "Nomad Coffee Meetup", "url": "https://a/1", "start": "", "status": "scheduled",
             "venue": "V", "street": "", "locality": "", "organizer": "O", "organizer_url": "",
             "category": "digital nomad", "online": False, "lat": None, "lon": None,
             "source": "meetup_public"},
            {"title": "Nomad  Coffee  Meetup!", "url": "https://b/1", "start": "", "status": "scheduled",
             "venue": "V", "street": "", "locality": "", "organizer": "O", "organizer_url": "",
             "category": "digital nomad", "online": False, "lat": None, "lon": None,
             "source": "luma_public"}]}}
        per = S6.build_evidence({"places": []}, eco, evs, {}, {})
        self.assertEqual(len(per["1"]), 1)

    def test_cancelled_and_online_events_ignored(self):
        evs = {"1": {"scanned_at": common.iso(), "events": [
            {"title": "X", "url": "u1", "start": "", "status": "cancelled", "venue": "", "street": "",
             "locality": "", "organizer": "", "organizer_url": "", "category": "social",
             "online": False, "lat": None, "lon": None, "source": "meetup_public"},
            {"title": "Y", "url": "u2", "start": "", "status": "scheduled", "venue": "", "street": "",
             "locality": "", "organizer": "", "organizer_url": "", "category": "social",
             "online": True, "lat": None, "lon": None, "source": "meetup_public"}]}}
        self.assertEqual(len(S6.build_evidence({"places": []}, {}, evs, {}, {}).get("1", [])), 0)

    def test_city_precision_evidence_gets_no_cell(self):
        comm = {"1": {"mentions": 1, "unique_sources": 1, "sources": ["reddit_rss"],
                      "samples": [{"source": "reddit_rss", "channel": "r/x", "title": "t",
                                   "url": "u", "at": "", "matched": "x", "precision": "locality"}]}}
        per = S6.build_evidence({"places": []}, {}, {}, comm, {})
        self.assertIsNone(per["1"][0]["h3"])
        self.assertEqual(per["1"][0]["precision"], "locality")
        self.assertEqual(len(S6.build_cells(per)), 0)


class TestResilience(unittest.TestCase):
    def test_circuit_breaker_opens_and_recovers(self):
        b = common.CircuitBreaker(threshold=3, cooldown=0)
        for _ in range(3):
            self.assertTrue(b.allow()); b.fail()
        self.assertTrue(b.allow())          # cooldown 0 -> half-open probe
        b2 = common.CircuitBreaker(threshold=2, cooldown=999)
        b2.fail(); b2.fail()
        self.assertFalse(b2.allow())
        b2.ok()
        self.assertTrue(b2.allow())

    def test_failed_source_does_not_break_scoring(self):
        # every optional layer missing
        m = S6.score_locality({"gid": 1, "name": "T", "pop": 100000, "cc": "XX"},
                              [], [], [], None or {}, {}, {})
        self.assertIsInstance(m["live_score"], int)
        self.assertEqual(m["sources"], [])

    def test_rate_limiter_enforces_gap(self):
        import time as _t
        r = common.RateLimiter(0.25)
        r.wait(); t0 = _t.time(); r.wait()
        self.assertGreaterEqual(_t.time() - t0, 0.2)


class TestBundle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = load("bundle.json")
        cls.locs = decode_localities(cls.b) if cls.b else []

    def setUp(self):
        if not self.b:
            self.skipTest("bundle.json not built yet")

    def test_structure(self):
        for k in ("world_px", "meta", "countries_geo", "levels", "localities",
                  "clusters", "country_rollup", "region_rollup", "evidence", "sources"):
            self.assertIn(k, self.b)

    def test_every_resolution_present(self):
        for r in ("2", "3", "4", "5", "6", "7", "8"):
            self.assertIn(r, self.b["levels"])

    def test_coarse_has_fewer_cells_than_fine(self):
        n = {r: len(self.b["levels"][r]["s"]) for r in ("2", "5", "8")}
        self.assertLessEqual(n["2"], n["5"])
        self.assertLessEqual(n["5"], n["8"])

    def test_scores_in_range(self):
        for r, lv in self.b["levels"].items():
            for arr in (lv["s"], lv["c"]):
                if arr:
                    self.assertGreaterEqual(min(arr), 0)
                    self.assertLessEqual(max(arr), 100)

    def test_localities_have_required_fields(self):
        for L in self.locs[:200]:
            for k in ("live_score", "confidence", "band", "presence", "momentum",
                      "freshness", "evidence_count", "unique_sources", "px", "py", "warnings"):
                self.assertIn(k, L, f'{L.get("name")} missing {k}')
            self.assertTrue(0 <= L["live_score"] <= 100)

    def test_geographic_diversity(self):
        conts = {L["continent"] for L in self.locs}
        self.assertGreaterEqual(len(conts), 5, f"only {conts} represented")
        ccs = {L["cc"] for L in self.locs}
        self.assertGreaterEqual(len(ccs), 40)

    def test_no_invented_precision(self):
        """Community posts must never carry coordinates or an H3 cell."""
        bad = 0
        for gid, items in list(self.b["evidence"].items())[:400]:
            for e in decode_evidence(self.b, items):
                if e["type"] == "community_post" and (e.get("h3") or e.get("lat")
                                                      or e["precision"] != "locality"):
                    bad += 1
        self.assertEqual(bad, 0)

    def test_clusters_reference_real_localities(self):
        gids = {L["gid"] for L in self.locs}
        for c in self.b["clusters"][:300]:
            self.assertIn(int(c["gid"]), gids)
            self.assertGreaterEqual(c["n_cells"], 2)

    def test_rollup_max_ge_mean(self):
        for r in self.b["country_rollup"]:
            self.assertGreaterEqual(r["max"], r["mean"])
            self.assertGreaterEqual(r["max"], r["median"])

    def test_pixel_coords_inside_world(self):
        W, H = self.b["world_px"]["w"], self.b["world_px"]["h"]
        for L in self.locs[:500]:
            self.assertTrue(0 <= L["px"] <= W)
            self.assertTrue(0 <= L["py"] <= H)

    def test_source_transparency(self):
        aud = self.b["sources"]["audit"]
        self.assertGreaterEqual(len(aud), 50, "spec requires 50-80 sources audited")
        self.assertTrue(any(a["status"] == "BLOCKED" for a in aud),
                        "blocked sources must be reported, not hidden")
        self.assertTrue(any(a["status"] == "ACTIVE" for a in aud))


class TestRegressionGeography(unittest.TestCase):
    """Spec §60: geographically diverse coverage, but NO hard-coded expected ranking."""

    @classmethod
    def setUpClass(cls):
        cls.b = load("bundle.json")
        cls.locs = decode_localities(cls.b) if cls.b else []

    def setUp(self):
        if not self.b:
            self.skipTest("bundle.json not built yet")

    def test_every_inhabited_continent_has_a_scored_locality(self):
        conts = defaultdict(int)
        for L in self.locs:
            conts[L["continent"]] += 1
        for c in ("EU", "AS", "NA", "SA", "AF", "OC"):
            self.assertGreater(conts[c], 0, f"no localities scored in {c}")

    def test_named_regression_places_are_present_and_scored(self):
        """These must exist in the output, but their scores are whatever the
        evidence says - no expected ordering is asserted."""
        want = ["Lisbon", "Barcelona", "Athens", "Bangkok", "Chiang Mai", "Cape Town",
                "Tbilisi", "Buenos Aires", "Medellín", "Mexico City", "Da Nang"]
        have = {L["name"] for L in self.locs}
        missing = [w for w in want if w not in have]
        self.assertLessEqual(len(missing), 2, f"discovery missed: {missing}")

    def test_sub_city_hotspots_exist_for_major_cities(self):
        multi = [c for c in self.b["clusters"] if c["n_cells"] >= 3]
        self.assertGreaterEqual(len(multi), 20,
                                "no meaningful sub-city clusters were discovered")


if __name__ == "__main__":
    unittest.main(verbosity=2)
