# CLI surface ledger

**What:** One place to find **how to run** Sesefus creations from the shell.  
**Machine SSOT:** [`cli_surface.jsonl`](cli_surface.jsonl) — append-only.  
**Tool:** `python tools/cli_surface_ledger.py list`

Not a full repo inventory (see `INVENTORY.md`). Only **operator CLI surfaces** you actually invoke.

---

## Quick list (human)

### SaturnNav

- **route sane-count** (spike 002)  
  `cd spikes/002-route-sane-count`  
  `python count_sane_routes.py --from "ADDR_A" --to "ADDR_B"`  
  Optional: `--osrm` · stages: `--print-stages`  
  Log: `logs/sane_routes.jsonl`

### Spikes

- **suite card rack** (001)  
  `spikes/001-suite-card-rack/open.bat`  
  → `http://127.0.0.1:8791/rack.html`

### Suite launchers (root .bat)

- `voice.bat` — push-to-talk voice loop  
- `aytree.bat open` — AyTree  
- `ssfs.bat` — Zig host build/run  
- `fleet.bat` — fleet (venv)

### Python tools (common)

- `python tools/voice.py` — voice loop (flags: `--file` `--say` `--backend`)  
- `python tools/etdi_pipeline.py --scan` — ETDI score  
- `python tools/aytree_launch.py open` — AyTree  
- `python shredder/artifact_sieve.py --scan-only` — chat dump sieve  
- `python tools/cli_surface_ledger.py list` — this ledger

---

## Ledger rules

1. **Append only** to `cli_surface.jsonl` (never truncate — see ledger-safe-mutate).  
2. New spike / product CLI → `register` (or hand-append one JSON line).  
3. Refresh this `.md` when the **quick list** gets stale (human face, not the SSOT).  
4. `status`: `active` | `parked` | `dead` — prefer new row with new status over rewrite history.

---

## Register a new surface

```bash
python tools/cli_surface_ledger.py register \
  --id "spike-003-example" \
  --product saturnnav \
  --name "example surface" \
  --kind python \
  --path spikes/003-example/run.py \
  --invoke "python run.py --help" \
  --purpose "one line why" \
  --maturity spike
```

```bash
python tools/cli_surface_ledger.py list
python tools/cli_surface_ledger.py list --product saturnnav
python tools/cli_surface_ledger.py show spike-002-route-sane
```

---

## Schema (one JSONL line)

- `id` — stable slug  
- `ts` — ISO when registered  
- `product` — saturnnav | circadia | arcadium | aytree | sieve | sesefus-suite | meta  
- `name` — short human label  
- `kind` — python | bat | ps1 | zig | other  
- `path` — repo-relative entry file  
- `cwd` — where to run from (`.` = repo root)  
- `invoke` — copy-paste command (relative to cwd)  
- `purpose` — one line  
- `maturity` — spike | alpha | active | tooling | parked  
- `stage` — optional (e.g. SaturnNav S-curve stage)  
- `flags` — main CLI flags/subcommands  
- `outputs` — logs, URLs, dbs  
- `status` — active | parked | dead
