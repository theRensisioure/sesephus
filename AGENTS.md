# AGENTS.md

## Cursor Cloud specific instructions

**Sesephus** (`theRensisioure/sesephus`) is a **Windows-first public
lineage/reference repository**, not the supported Voice capture product.
A Linux dev setup still works. The
`.bat` / `.ps1` wrappers (`install.bat`, legacy `voice.bat`, `ssfs.bat`, `fleet.bat`,
`run_demo.bat`) do **not** run on Linux — invoke the underlying commands
directly, as `.devcontainer/post-create.sh` does. Canonical service/port map:
`docs/CANON.md` §4.

### Services (dev)
Three runtimes make up the full stack (see `docs/CANON.md` §4 and the quick-start
block at the end of `.devcontainer/post-create.sh`):

| Service | Dir | Dev command | Port |
|---|---|---|---|
| Zig host daemon | `core/sesephus` | `./zig-out/bin/sesefus --role host` | HTTP 3000, TCP 5000 |
| Python FastAPI bridge | repo root | `.venv/bin/python dashboard/dashboard_server.py` | 3001 |
| React/Vite dashboard | `dashboard/ui` | `npm run dev` | 5173 (proxies `/api` → 3001) |

The sole supported Voice implementation is external Desktop Clippers at
`C:\dev\journal-clippers\audio-journal-system`. This repository points
to it only. `voice.bat` and `tools/voice.py` are retained historical code and
must not be presented as a supported recorder.

**AyTree** (suite derivation map / Version Control module) is an **external sibling**
repo. Launch via `python tools/aytree_launch.py open` or `aytree.bat`. Path
resolution: `AYTREE_ROOT` → config `aytree_root` → `../AyTree`. See `docs/CANON.md`
§7. Do not vendor AyTree into this tree.

### Non-obvious caveats
- **Vite binds to IPv6 `localhost` (`::1`) only** — open `http://localhost:5173`,
  not `http://127.0.0.1:5173` (the latter is connection-refused). The `/api/*`
  proxy to FastAPI only works through the `localhost` origin.
- **Default ETDI inference backend is `ollama`**, which is not running here. Use
  `--backend heuristic` for offline lexical scoring (confidence 0.2).
- **Historical `tools/voice.py` needs a microphone** (via
  `sounddevice`/PortAudio). For forensic/reference exercise of that retired
  capture → ETDI → vault pipeline, use the
  test hooks: `python tools/voice.py --say "text" --duration 30 --backend heuristic`
  (skips audio+Whisper) or `--file memo.wav`.
- **Zig host audio is Windows-only** (WinMM); on Linux it falls back to a
  synthetic generator but still serves HTTP 3000 + TCP 5000 and boots an embedded
  client, so `/api/status`, `/api/machine`, alarms, and the vault all work.
- **Whisper is optional and large (~1–2 GB)**; it is intentionally not installed.
  Without it, `/api/transcribe` returns a simulated transcript; the historical
  `tools/voice.py` reference path requires `--say`.
- **Build vs. run**: build the Zig binary with `zig build` run from
  `core/sesephus` (output at `core/sesephus/zig-out/bin/sesefus`). This is a
  build step, not part of dependency refresh.

### Lint / test / build gates
- Blocking in CI (`.github/workflows/ci.yml`): Python `compileall` syntax gate
  and `zig build` (built on Windows in CI, but builds on Linux too).
- Advisory / non-gating: `npm run lint` (eslint) and `zig fmt --check` both report
  pre-existing findings and are **not** required to pass; CI does not run
  `npm run lint` and treats `zig fmt` as advisory.

### System dependencies (baked into the VM, not the update script)
Installed once during environment setup (persisted via the VM snapshot), so the
startup update script does not reinstall them:
- **Zig 0.16.0** at `/usr/local/bin/zig` (required by `core/sesephus/build.zig`).
- **`python3.12-venv`** (Debian package required to create `.venv`).
