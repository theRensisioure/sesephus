# Spike 002 — Route request log (address A/B floor → S-curve)

**Question:** For a request A→B, how many *different, sane* routes exist — and how does altitude cost distribute?

**Answer shape:** Not a closed formula. Measure under an explicit sane definition; log every request.

**Bare minimum input (now):** free-text **address A** + **address B**.  
No triangulation. No multi-source derivation. One geocoder hit per address (cached).

---

## S-curve (your ceiling, named)

Stages share one JSONL schema. OD identity (addresses + lat/lng) is stable from floor upward.

1. **floor** *implemented* — A/B addresses → lat/lng → log. `n_sane = null`.
2. **synthetic** *implemented* — fake grid enumerate under sane v0 (algo lab).
3. **osrm_hint** *implemented* — public OSRM “how many alternatives does *an* engine offer?” Thin real signal. Not full sane universe.
4. **corridor_graph** *not yet* — local OSM extract around A/B + enumerate/filter under *your* sane def.
5. **dem_sane** *not yet* — real climb + altitude-deviation histograms.
6. **city_batch** *not yet* — many ODs, same sane_def, per city pack.
7. **global** *ceiling* — Tokyo, Seattle, … same instrument, market comparison.

**Ceiling in theory:** any address pair on Earth → same log → comparable `n_sane` under one sane_def.  
**Ceiling is not free:** needs graph+DEM+enumerator that scales (not brute DFS on a city). Floor does not claim that.

---

## Math (still true)

- All simple paths A→B: **#P-complete** (Valiant). No plug-in formula for road nets.
- k-shortest / Pareto size: algorithms + data, not a universal equation.
- “Sane” count: **definition-dependent** — you invent the knobs; research measures them.

---

## Sane v0 (synthetic stage only)

1. Simple (no repeated nodes)
2. Length ≤ `stretch_max` × shortest
3. Climb ≤ `climb_max_m`

Dedup: exact node sequence. Later: corridor similarity.

---

## Run

```bash
# S-curve map
python count_sane_routes.py --print-stages

# FLOOR — bare minimum: two addresses
python count_sane_routes.py --from "Shibuya Station, Tokyo" --to "Shinjuku Station, Tokyo"

# Thin real signal — OSRM public alternatives after geocode
python count_sane_routes.py --from "Shibuya Station, Tokyo" --to "Shinjuku Station, Tokyo" --osrm

# Algo lab (no addresses)
python count_sane_routes.py --stage synthetic
python count_sane_routes.py --sweep
```

Append-only: `logs/sane_routes.jsonl`  
Geocode cache: `logs/geocode_cache.json` (Nominatim, 1 req/s, User-Agent set)

---

## Floor log shape

```json
{
  "ts": "...",
  "stage": "floor",
  "od": {
    "a": {"address": "...", "lat": ..., "lon": ..., "display_name": "..."},
    "b": {"address": "...", "lat": ..., "lon": ..., "display_name": "..."},
    "straight_line_km": 3.2
  },
  "graph": null,
  "sane_def": null,
  "n_sane": null,
  "measure_status": "od_only"
}
```

Higher stages **add** graph / sane_def / counts; they do not replace OD.

---

## Constraints (honest)

| Can | Cannot (yet) |
|-----|----------------|
| Type any two addresses | Guarantee geocode is the “right” building |
| Work Tokyo / anywhere Nominatim knows | Full street-true sane-count |
| Cache geocodes offline after first hit | Offline-first geocode with no first network hit |
| Optional OSRM alt count | Depend on OSRM as product (demo server only) |
| Scale *schema* to global | Brute-force path count on a metropolis |

No triangulation derivation. No speaker, wind, Zig, dashboard wiring.

---

## Next rung (when floor is boring)

`corridor_graph`: bbox around A/B → OSM bike edges → snap A/B → enumerate or k-paths under sane v0 → fill `n_sane` for real streets. Same addresses, same log file.
