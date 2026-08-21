#!/usr/bin/env python3
"""SaturnNav spike: A→B request log + sane-route measure (S-curve stages).

Bare minimum input: address A + address B → geocode → JSONL.
No triangulation / multi-source derivation.

Stdlib only. Append-only logs/sane_routes.jsonl
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path

SPIKE_DIR = Path(__file__).resolve().parent
LOG_DIR = SPIKE_DIR / "logs"
LOG_PATH = LOG_DIR / "sane_routes.jsonl"
GEO_CACHE = LOG_DIR / "geocode_cache.json"

# Nominatim usage: identify app, ≤1 req/s, cache forever locally for spike.
NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "SaturnNav-spike-002/0.2 (research; local; contact: sesefus)"
_last_geo_ts = 0.0

# S-curve stages (ceiling is theoretical product scale, not this script alone)
STAGES = (
    "floor",      # addresses → lat/lng → log OD (this bare minimum)
    "synthetic",  # fake grid enumerate (algorithm lab)
    "osrm_hint",  # public engine alternative count (thin real-world signal)
    # later, not implemented: "corridor_graph", "dem_sane", "city_batch", "global"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# --- geocode (floor) ---------------------------------------------------------


def _load_geo_cache() -> dict:
    if not GEO_CACHE.exists():
        return {}
    try:
        return json.loads(GEO_CACHE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_geo_cache(cache: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    GEO_CACHE.write_text(json.dumps(cache, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def geocode_address(query: str, cache: dict | None = None) -> dict:
    """Resolve free-text address → one lat/lng. No triangulation, first hit."""
    global _last_geo_ts
    q = query.strip()
    if not q:
        raise SystemExit("empty address")

    own_cache = cache is None
    if cache is None:
        cache = _load_geo_cache()

    key = q.casefold()
    if key in cache:
        hit = dict(cache[key])
        hit["from_cache"] = True
        return hit

    # polite rate limit
    wait = 1.05 - (time.time() - _last_geo_ts)
    if wait > 0:
        time.sleep(wait)

    params = urllib.parse.urlencode(
        {
            "q": q,
            "format": "json",
            "limit": "1",
            "addressdetails": "0",
        }
    )
    url = f"{NOMINATIM}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"geocode HTTP {e.code} for {q!r}: {e.reason}") from e
    except urllib.error.URLError as e:
        raise SystemExit(f"geocode network error for {q!r}: {e.reason}") from e
    finally:
        _last_geo_ts = time.time()

    data = json.loads(body)
    if not data:
        raise SystemExit(f"geocode: no results for {q!r}")

    top = data[0]
    rec = {
        "query": q,
        "lat": float(top["lat"]),
        "lon": float(top["lon"]),
        "display_name": top.get("display_name"),
        "osm_type": top.get("osm_type"),
        "osm_id": top.get("osm_id"),
        "importance": top.get("importance"),
        "from_cache": False,
        "provider": "nominatim",
    }
    cache[key] = {k: v for k, v in rec.items() if k != "from_cache"}
    if own_cache:
        _save_geo_cache(cache)
    return rec


def stage_floor(addr_a: str, addr_b: str) -> dict:
    cache = _load_geo_cache()
    ga = geocode_address(addr_a, cache)
    gb = geocode_address(addr_b, cache)
    _save_geo_cache(cache)

    dist = haversine_km(ga["lat"], ga["lon"], gb["lat"], gb["lon"])
    return {
        "ts": utc_now(),
        "stage": "floor",
        "od": {
            "a": {
                "address": ga["query"],
                "lat": ga["lat"],
                "lon": ga["lon"],
                "display_name": ga.get("display_name"),
                "geocode_cached": ga.get("from_cache", False),
            },
            "b": {
                "address": gb["query"],
                "lat": gb["lat"],
                "lon": gb["lon"],
                "display_name": gb.get("display_name"),
                "geocode_cached": gb.get("from_cache", False),
            },
            "straight_line_km": round(dist, 4),
        },
        "graph": None,
        "sane_def": None,
        "n_sane": None,
        "n_raw_simple_under_stretch": None,
        "measure_status": "od_only",
        "note": (
            "Floor: addresses resolved. No route graph / sane count yet. "
            "Same log schema grows up the S-curve without re-keying OD."
        ),
    }


# --- optional thin mid-curve: OSRM public alternatives -----------------------


def stage_osrm_hint(floor_rec: dict, profile: str = "bike") -> dict:
    """How many alternatives a public router returns — not full sane-count."""
    a = floor_rec["od"]["a"]
    b = floor_rec["od"]["b"]
    # lon,lat;lon,lat
    path = f"{a['lon']},{a['lat']};{b['lon']},{b['lat']}"
    url = (
        f"https://router.project-osrm.org/route/v1/{profile}/{path}"
        f"?alternatives=true&overview=false&steps=false"
    )
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as e:
        rec = dict(floor_rec)
        rec["ts"] = utc_now()
        rec["stage"] = "osrm_hint"
        rec["measure_status"] = "osrm_failed"
        rec["osrm"] = {"error": str(e), "profile": profile}
        rec["n_sane"] = None
        rec["note"] = "OSRM hint failed; OD still logged."
        return rec

    routes = data.get("routes") or []
    distances = [round(r.get("distance", 0) / 1000.0, 4) for r in routes]
    durations = [round(r.get("duration", 0) / 60.0, 2) for r in routes]
    rec = dict(floor_rec)
    rec["ts"] = utc_now()
    rec["stage"] = "osrm_hint"
    rec["measure_status"] = "engine_alternatives"
    rec["graph"] = {"kind": "osrm_public", "profile": profile}
    rec["sane_def"] = {
        "kind": "engine_default",
        "note": "Not SaturnNav sane v0 — public OSRM alternatives only.",
    }
    rec["n_sane"] = len(routes)  # engine-offered, not full sane universe
    rec["n_raw_simple_under_stretch"] = None
    rec["osrm"] = {
        "code": data.get("code"),
        "profile": profile,
        "n_routes": len(routes),
        "distance_km": distances,
        "duration_min": durations,
    }
    rec["note"] = (
        "OSRM alternative count is a thin ceiling-signal, not full path enumeration. "
        "Public demo server is rate-limited and not a production dependency."
    )
    return rec


# --- synthetic stage (algorithm lab) -----------------------------------------


def node_id(r: int, c: int) -> str:
    return f"{r},{c}"


def build_grid(rows: int, cols: int, seed: int) -> tuple[dict, dict]:
    rng = random.Random(seed)
    elev: dict[str, float] = {}
    for r in range(rows):
        for c in range(cols):
            base = 10.0 * math.sin(r * 0.7) + 8.0 * math.cos(c * 0.5)
            elev[node_id(r, c)] = base + rng.uniform(0, 15)

    adj: dict[str, list[str]] = defaultdict(list)
    for r in range(rows):
        for c in range(cols):
            u = node_id(r, c)
            for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                rr, cc = r + dr, c + dc
                if 0 <= rr < rows and 0 <= cc < cols:
                    adj[u].append(node_id(rr, cc))
    return dict(adj), elev


def edge_len(_u: str, _v: str) -> float:
    return 1.0


def climb_gain(elev: dict[str, float], u: str, v: str) -> float:
    d = elev[v] - elev[u]
    return d if d > 0 else 0.0


def shortest_length(adj: dict, a: str, b: str) -> float | None:
    if a not in adj or b not in adj:
        return None
    q = deque([(a, 0.0)])
    seen = {a}
    while q:
        u, d = q.popleft()
        if u == b:
            return d
        for v in adj[u]:
            if v not in seen:
                seen.add(v)
                q.append((v, d + edge_len(u, v)))
    return None


def path_metrics(path: list[str], elev: dict[str, float]) -> dict:
    length = 0.0
    climb = 0.0
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        length += edge_len(u, v)
        climb += climb_gain(elev, u, v)
    net = elev[path[-1]] - elev[path[0]]
    min_possible_climb = max(0.0, net)
    alt_dev = climb - min_possible_climb
    return {
        "length": length,
        "climb_m": round(climb, 3),
        "net_elev_m": round(net, 3),
        "alt_dev_m": round(alt_dev, 3),
        "nodes": len(path),
    }


def enumerate_simple_paths(
    adj: dict, a: str, b: str, max_len: float, max_paths: int
) -> list[list[str]]:
    out: list[list[str]] = []

    def dfs(u: str, path: list[str], length: float) -> None:
        if len(out) >= max_paths:
            return
        if u == b:
            out.append(path.copy())
            return
        for v in adj[u]:
            if v in path:
                continue
            nl = length + edge_len(u, v)
            if nl > max_len + 1e-9:
                continue
            path.append(v)
            dfs(v, path, nl)
            path.pop()

    dfs(a, [a], 0.0)
    return out


def hist_bins(values: list[float], edges: list[float]) -> dict[str, int]:
    labels = []
    for i in range(len(edges) - 1):
        labels.append(f"{edges[i]:g}-{edges[i+1]:g}")
    labels.append(f"{edges[-1]:g}+")
    c = Counter()
    for x in values:
        placed = False
        for i in range(len(edges) - 1):
            if edges[i] <= x < edges[i + 1]:
                c[labels[i]] += 1
                placed = True
                break
        if not placed:
            c[labels[-1]] += 1
    return {lab: c.get(lab, 0) for lab in labels}


def _stats(xs: list[float]) -> dict | None:
    if not xs:
        return None
    s = sorted(xs)
    n = len(s)
    mid = n // 2
    med = s[mid] if n % 2 else 0.5 * (s[mid - 1] + s[mid])
    return {
        "n": n,
        "min": round(s[0], 3),
        "max": round(s[-1], 3),
        "mean": round(sum(s) / n, 3),
        "median": round(med, 3),
    }


def stage_synthetic(
    rows: int,
    cols: int,
    seed: int,
    stretch_max: float,
    climb_max_m: float,
    max_paths: int,
    a: str | None,
    b: str | None,
    od_overlay: dict | None = None,
) -> dict:
    adj, elev = build_grid(rows, cols, seed)
    a = a or node_id(0, 0)
    b = b or node_id(rows - 1, cols - 1)
    if a not in elev or b not in elev:
        raise SystemExit(f"OD out of grid: {a} -> {b}")

    sp = shortest_length(adj, a, b)
    if sp is None:
        raise SystemExit(f"No path {a} -> {b}")

    len_cap = stretch_max * sp
    raw_paths = enumerate_simple_paths(adj, a, b, len_cap, max_paths)
    n_raw = len(raw_paths)
    truncated = n_raw >= max_paths

    climbs: list[float] = []
    alt_devs: list[float] = []
    sane_sigs: list[str] = []
    for path in raw_paths:
        m = path_metrics(path, elev)
        if m["climb_m"] <= climb_max_m + 1e-9:
            climbs.append(m["climb_m"])
            alt_devs.append(m["alt_dev_m"])
            sane_sigs.append(">".join(path))

    n_sane = len(set(sane_sigs))
    climb_edges = [0, 20, 40, 80, 160]

    od = {"a": a, "b": b}
    if od_overlay:
        od = {**od_overlay, "grid_a": a, "grid_b": b}

    return {
        "ts": utc_now(),
        "stage": "synthetic",
        "od": od,
        "graph": {"kind": "grid4", "rows": rows, "cols": cols, "seed": seed},
        "sane_def": {
            "simple": True,
            "stretch_max": stretch_max,
            "climb_max_m": climb_max_m,
            "dedup": "exact_node_sequence",
        },
        "n_raw_simple_under_stretch": n_raw,
        "n_sane": n_sane,
        "enumeration_truncated": truncated,
        "max_paths_cap": max_paths,
        "shortest_len": sp,
        "length_cap": len_cap,
        "climb_m": climbs,
        "alt_dev_m": alt_devs,
        "climb_hist": hist_bins(climbs, climb_edges),
        "alt_dev_hist": hist_bins(alt_devs, climb_edges),
        "climb_m_stats": _stats(climbs),
        "alt_dev_m_stats": _stats(alt_devs),
        "measure_status": "synthetic_sane_v0",
        "note": "Synthetic grid only — not real streets. Use --from/--to for address floor.",
    }


# --- I/O ---------------------------------------------------------------------


def emit(rec: dict, write: bool) -> None:
    line = json.dumps(rec, separators=(",", ":"), ensure_ascii=False)
    stage = rec.get("stage", "?")
    n = rec.get("n_sane")
    status = rec.get("measure_status", "")
    od = rec.get("od") or {}

    if isinstance(od.get("a"), dict):
        a_lab = od["a"].get("address") or od["a"].get("display_name") or "?"
        b_lab = od["b"].get("address") or od["b"].get("display_name") or "?"
        km = od.get("straight_line_km")
        print(f"[{stage}] {a_lab!r} → {b_lab!r}  straight≈{km} km  n_sane={n}  ({status})")
    else:
        print(
            f"[{stage}] n_sane={n}  raw={rec.get('n_raw_simple_under_stretch')}  "
            f"stretch≤{(rec.get('sane_def') or {}).get('stretch_max')}  ({status})"
        )

    if write:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(f"appended {LOG_PATH}")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="SaturnNav spike 002: address A/B floor + sane-count stages"
    )
    p.add_argument("--from", dest="addr_from", default=None, help="Origin address (bare text)")
    p.add_argument("--to", dest="addr_to", default=None, help="Destination address (bare text)")
    p.add_argument(
        "--stage",
        choices=["floor", "synthetic", "osrm_hint", "auto"],
        default="auto",
        help="auto: addresses→floor (or +osrm if --osrm); else synthetic",
    )
    p.add_argument(
        "--osrm",
        action="store_true",
        help="After geocode, query public OSRM alternatives (thin mid-curve signal)",
    )
    p.add_argument("--osrm-profile", default="bike", help="OSRM profile: bike|driving|foot")
    # synthetic knobs
    p.add_argument("--rows", type=int, default=5)
    p.add_argument("--cols", type=int, default=5)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--stretch", type=float, default=1.4)
    p.add_argument("--climb-max", type=float, default=80.0, dest="climb_max")
    p.add_argument("--max-paths", type=int, default=50_000)
    p.add_argument("--a", default=None, help="synthetic grid origin e.g. 0,0")
    p.add_argument("--b", default=None, help="synthetic grid dest e.g. 4,4")
    p.add_argument("--no-write", action="store_true")
    p.add_argument("--sweep", action="store_true", help="synthetic stretch×climb sweep only")
    p.add_argument(
        "--print-stages",
        action="store_true",
        help="print S-curve stage names and exit",
    )
    args = p.parse_args(argv)

    if args.print_stages:
        print("S-curve stages (implemented *):")
        print("  * floor       — address A/B → lat/lng → log (bare minimum)")
        print("  * synthetic   — fake grid sane-count (algo lab)")
        print("  * osrm_hint   — public OSRM alternative count (thin real signal)")
        print("    corridor_graph — local OSM extract + enumerate under sane (next)")
        print("    dem_sane       — real climb/alt-dev histograms")
        print("    city_batch     — many ODs per city, same sane_def")
        print("    global         — multi-city packs (Tokyo, …) — ceiling")
        print("No triangulation derivation at any stage yet.")
        return 0

    write = not args.no_write

    # --- synthetic-only paths ---
    if args.sweep:
        for stretch in (1.1, 1.3, 1.5, 1.8):
            for climb in (40.0, 80.0, 160.0):
                rec = stage_synthetic(
                    args.rows, args.cols, args.seed, stretch, climb,
                    args.max_paths, args.a, args.b,
                )
                emit(rec, write=write)
        return 0

    has_addr = bool(args.addr_from or args.addr_to)
    if has_addr and not (args.addr_from and args.addr_to):
        raise SystemExit("need both --from and --to for address input")

    stage = args.stage
    if stage == "auto":
        if has_addr:
            stage = "osrm_hint" if args.osrm else "floor"
        else:
            stage = "synthetic"

    if stage == "synthetic":
        if has_addr:
            # still geocode so log can carry real OD + synthetic measure side-by-side
            floor = stage_floor(args.addr_from, args.addr_to)
            rec = stage_synthetic(
                args.rows, args.cols, args.seed, args.stretch, args.climb_max,
                args.max_paths, args.a, args.b, od_overlay=floor["od"],
            )
            rec["note"] = (
                "Addresses geocoded for OD identity; sane count is still synthetic grid. "
                "Not street-true."
            )
        else:
            rec = stage_synthetic(
                args.rows, args.cols, args.seed, args.stretch, args.climb_max,
                args.max_paths, args.a, args.b,
            )
        emit(rec, write=write)
        return 0

    if stage in ("floor", "osrm_hint"):
        if not has_addr:
            raise SystemExit(f"stage {stage} needs --from and --to addresses")
        floor = stage_floor(args.addr_from, args.addr_to)
        if stage == "floor" and not args.osrm:
            emit(floor, write=write)
            return 0
        rec = stage_osrm_hint(floor, profile=args.osrm_profile)
        emit(rec, write=write)
        return 0

    raise SystemExit(f"unknown stage {stage}")


if __name__ == "__main__":
    sys.exit(main())
