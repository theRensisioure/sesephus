# Plan — praxis frame repo · cherry-pick scanner QOL · Sesefus inherits

> **For implementers:** phase-by-phase; zero-context safe. Prefer **copy + thin package** over “move the scanner.”  
> **New repo:** `praxis` (does not exist yet on disk or GitHub under Zychs).  
> **Consumers:** Sesefus first (inherit frame). Artifact Scanner later may **also** depend or stay a fat host until migrated.

**Goal:** Extract **frame QOL** (window · serve · launch · single-instance · reading face helpers) from Artifact Scanner into a **new repo `praxis`**, initial-commit that surface only, then **Sesefus inherits** that frame instead of re-implementing half of it in `apps/journal-daemon/ui_host.py`.

**Architecture:**
- **praxis** = product-agnostic **frame kit** (library + tiny templates). Not a second scanner. Not Sesefus product modules.
- **Sesefus** = product modules (record · alarms · speech-display later) **on top of** praxis frame.
- **Artifact Scanner** = finder/board product; remains SSOT for **scan/board/archive** logic. It is the **donor** of QOL code, not the long-term home of shared frame.

**Tech stack:** Python 3.11+ · Windows-first (mutex, detached spawn, Brave/Edge/WebView2 patterns) · optional pywebview · static CSS/JS snippets for dyslexia scale · git (new public/private repo under Zychs).

**Inheritance (recommended default):**
1. `praxis` as its own git remote (`github.com/Zychs/praxis` or local `C:\dev\praxis` first).
2. Sesefus consumes via **git submodule** or **path install** (`pip install -e ../praxis`) — pick one in Phase 1; default **editable path install** for speed, submodule when multi-machine.
3. Do **not** vendor a full copy of `window_host.py` into sesefus forever.

**Anti-goal / anti-dogfood:** This plan is **frame extraction**, not journal dogfood, not suite glue, not loading Sesefus into scanner `:8765`.

---

## Phase 0 — Documentation discovery (done in this plan; re-verify before code)

### Sources consulted

| Source | What it establishes |
|--------|---------------------|
| `C:\Users\bardw\artifact-scanner\SEED.md` | Serve failsafe, single-instance laws, host≠serve, dyslexia UI, native window vs app-mode |
| `C:\Users\bardw\artifact-scanner\window_host.py` (~1635 lines) | Host seat, layout geometry, open_window, ensure server, browser fallbacks, mutex |
| `C:\Users\bardw\artifact-scanner\scripts\ensure_serve.py` (~85 lines) | Idempotent serve-only; imports from `window_host` |
| `ArtifactScanner.bat` / `.vbs` | Desktop launch; VBS style `1` (not SW_HIDE) |
| `C:\dev\sesefus\apps\journal-daemon\ui_host.py` (~161 lines) | **Already partial mirror:** ensure_serve, Brave/Edge app-mode, port 8777, detached Popen |
| `ui_serve.py` · `ui.html` · `README.md` | Product UI + port family; not frame kit |
| `C:\dev\sesefus\plans\2026-08-11-journal-alarm-daemon.md` | Scanner is **not** Sesefus host |
| `C:\Users\bardw\jwrangle\YOU-AGENT.md` | you/ vs agent/ if praxis docs split |
| GitHub `Zychs/*` | **No `praxis` repo yet** |

### Frame vs product (cherry-pick law)

| **FRAME (praxis candidate)** | **PRODUCT (leave in scanner / sesefus)** |
|------------------------------|------------------------------------------|
| Port probe · HTTP ok · ensure serve detached | Session index · board cards · agent tabs |
| Single-instance host mutex + pid file | Archive browser · segregate · session-map |
| Host ≠ serve | Reconstruct · durable land API (scanner routes) |
| Work-area geometry / companion layout helpers | AyTree module · suite flip cards |
| Chromium app-mode + WebView2 open helpers | Scanner-specific titles (Live / Archival / rails) |
| Launchers template (.bat/.vbs style-1, Start Menu install) | win_serve routes (~45 product APIs) |
| Dyslexia face: font serve pattern · Ctrl± scale ladder snippet | Card kind taxonomy · preview map law |
| Structured launch log under `%LOCALAPPDATA%\<App>\` | Product config (scan roots, notes DB) |
| Optional `open_path` editor bridge (thin) | GitHub compare / branch peek |

### Allowed APIs / patterns to **copy** (not invent)

From **`window_host.py`** (names as of today — re-grep before extract):

- `port_open(host, port)` · `http_ok(url)`
- `_popen_detached(cmd, cwd=…)`
- `acquire_host_instance` / `release_host_instance` (generalize mutex name)
- `_work_area()` · `_layout(...)` (parameterize product panes; don’t hardcode scanner suite)
- `_brave_candidates` / `_edge_candidates` / `_open_chromium_app`
- `_webview_importable` + native window path
- `EditorApi.open_window` **shape** (url, title) — not board-specific suite_hotswap/zip as required frame API

From **`ensure_serve.py`:**

- CLI: `python -m praxis.ensure_serve --port N` (rename after extract)
- Exit 0 = listening, 1 = failed

From **Sesefus `ui_host.py`:**

- Smaller Brave-first path already working for journal — **prefer as slim template** for praxis v0 host if full `window_host` is too fat for first commit

### Anti-patterns (Phase 0 guards)

- Do **not** copy `win_serve.py` wholesale into praxis  
- Do **not** make praxis depend on board.html or session trees  
- Do **not** “inherit” by symlink to entire artifact-scanner  
- Do **not** require pywebview for Sesefus if browser app-mode is enough (praxis: optional extra)  
- Do **not** put speech-rules / will-sieve / LM Studio in praxis  
- Do **not** move durable-archive product into praxis unless explicitly reframed as generic land kit later  

### Phase 0 exit checklist

- [x] Frame vs product table written  
- [ ] Re-grep `window_host.py` def list on extract day (file drifts)  
- [ ] Confirm mutex string becomes **parameterized** (`Local\Praxis.Host.<app_id>.v1`)

---

## Phase 1 — Name the frame contract (docs only in praxis)

**Objective:** One page that every consumer implements against.

**Create (in new repo after scaffold):**
- `README.md` — what praxis is / is not  
- `FRAME.md` — contract  
- `CHERRY_PICK.md` — donor map (scanner path → praxis path)

### FRAME.md contract (v0)

```text
App provides:
  - app_id: str          # "sesefus" | "artifact-scanner" | …
  - port: int
  - serve_cmd: list[str] # how to start THIS app's HTTP server
  - home_url: str        # http://127.0.0.1:{port}/
  - data_dir: Path       # %LOCALAPPDATA%/<AppName>
  - window_title: str

Praxis provides:
  - ensure_serve(app) -> None
  - open_window(app, url, title=None) -> None
  - acquire_host(app) / release_host(app)
  - port_open / http_ok
  - install_shortcuts(app)  # optional helper
  - dyslexia_css_url or static mount recipe
```

**Verify:**
- [ ] Sesefus journal-daemon can be described in 10 lines as an `App` config without scanner fields  
- [ ] Scanner board can be described without journal fields  

**Anti-pattern:** one god config that requires both products’ env.

---

## Phase 2 — Create `praxis` repo · initial commit = frame only

**Objective:** Empty product surface; only frame QOL.

### Task 2.1 — Create local tree

```text
C:\dev\praxis\
  README.md
  FRAME.md
  CHERRY_PICK.md
  LICENSE          # match house preference (sesefus LICENSE or MIT)
  pyproject.toml   # package name: praxis  (or praxis-frame)
  src/praxis/
    __init__.py
    ports.py       # port_open, http_ok
    process.py     # popen_detached
    host_instance.py  # mutex + pid
    serve.py       # ensure_serve(app)
    browser.py     # brave/edge/chrome app-mode
    window.py      # open_window orchestration
    layout.py      # work_area + optional multi-window layout (v0.1+)
    launch_log.py
  templates/
    windows/
      App.bat.j2 or App.bat.template
      App.vbs.template   # Run style 1
  static/
    dyslexia/
      README.md    # how to serve OpenDyslexic; fonts optional submodule or download note
  tests/
    test_ports.py
    test_structure_import.py
```

**Fonts:** do **not** bulk-commit large TTFs unless license is clear; document “copy from scanner `fonts/OpenDyslexic3-*.ttf`” or package separately.

### Task 2.2 — Git init + first commit

```bash
cd /c/dev/praxis
git init
git add .
git commit -m "feat: initial praxis frame kit (ports, serve ensure, host seat, browser open)"
```

**Initial commit contents must NOT include:**
- board.html · win_serve product routes · experimental/aytree · session scanners  
- sesefus record/alarm modules  

### Task 2.3 — Optional remote

```bash
gh repo create Zychs/praxis --private --source=. --remote=origin
# or public if frame is meant to be shareable
git push -u origin HEAD
```

**Verify:**
- [ ] `git ls-files` shows no `board.html`, no `win_serve.py`  
- [ ] `python -c "import praxis"` works after `pip install -e .`  
- [ ] Clone is &lt; small; no session data  

**Anti-pattern:** monorepo dump of three products “for convenience.”

---

## Phase 3 — Cherry-pick implementation (ordered, thin first)

Copy **behavior** from donor files; re-home under `src/praxis/`. Parameterize app_id/port/serve_cmd.

### Task 3.1 — ports + process (from scanner + sesefus)

**Donor:**
- `window_host.port_open` · `http_ok`  
- `ui_host.port_open` · `url_ok` (sesefus — simpler timeouts)  
- `_popen_detached` from `window_host`

**Verify:** unit tests with free high port; mock socket if needed.

### Task 3.2 — ensure_serve(app)

**Donor:** `scripts/ensure_serve.py` + sesefus `ui_host.ensure_serve`

**Shape:**

```python
@dataclass
class AppSpec:
    app_id: str
    port: int
    serve_argv: list[str]
    cwd: Path
    data_dir: Path
    ready_url: str | None = None  # default http://127.0.0.1:{port}/

def ensure_serve(app: AppSpec, *, timeout_s: float = 6.0) -> bool:
    ...
```

**Verify:**
- [ ] Second call reuses port (no second process)  
- [ ] Detached: parent exit does not kill serve (manual smoke on Windows)

### Task 3.3 — host single-instance

**Donor:** `acquire_host_instance` / mutex `Local\ArtifactScanner.Host.v1`

**Change:** mutex = `Local\Praxis.Host.{app_id}.v1` · pid file under `app.data_dir`

**Verify:** second `open_window` focuses/exits 0 for same app_id; sesefus and scanner can run **side by side** (different app_id).

### Task 3.4 — browser / window open

**Donor:** sesefus `find_browser` + scanner WebView2 path as **optional**

**v0:** Brave → Edge → Chrome app-mode → `os.startfile`  
**v0.1:** pywebview if importable and `prefer_native=True`

**Verify:** Sesefus still opens on :8777 via praxis API.

### Task 3.5 — launcher templates

**Donor:** `ArtifactScanner.vbs` style `1` · `Sesefus.vbs` · `install-shortcuts.ps1`

**Verify:** generated VBS does not use window style `0` (SW_HIDE bug).

### Task 3.6 — dyslexia static recipe (optional in v0)

**Donor:** SEED dyslexia section · scanner `fonts/` + board scale behavior (document; don’t port full board JS)

**v0:** CSS variables + font-face snippet + “Ctrl± ladder” notes  
**Later:** shared `praxis-scale.js` if two UIs need identical ladders

### Task 3.7 — layout helpers (defer if fat)

**Donor:** `_work_area` · `_layout` in `window_host.py`

Only extract when a second product needs multi-window geometry. **Not required for Sesefus journal single window.**

**Anti-pattern:** dragging suite zip/hotswap into praxis as mandatory.

---

## Phase 4 — Sesefus inherits praxis

**Objective:** journal-daemon uses praxis; delete duplicated ensure/browser once stable.

### Task 4.1 — depend

```text
# sesefus pyproject or requirements-dev / apps/journal-daemon note
# path:
pip install -e C:\dev\praxis
```

Or submodule:

```bash
cd C:\dev\sesefus
git submodule add <praxis-url> vendor/praxis
pip install -e vendor/praxis
```

### Task 4.2 — wire AppSpec

**Modify:** `apps/journal-daemon/ui_host.py`

Replace local `ensure_serve` / `find_browser` / port helpers with:

```python
from praxis.serve import ensure_serve, AppSpec
from praxis.window import open_app_window
# ...
app = AppSpec(
    app_id="sesefus",
    port=8777,
    serve_argv=[sys.executable, str(HERE / "ui_serve.py"), "--port", "8777"],
    cwd=HERE,
    data_dir=Path(os.environ["LOCALAPPDATA"]) / "Sesefus",
)
ensure_serve(app)
open_app_window(app, title="Sesefus")
```

**Keep in Sesefus:** `ui_serve.py` product routes · `record.py` · `daemon.py` · `ui.html` modules.

### Task 4.3 — docs

**Modify:** `apps/journal-daemon/README.md` — “frame: praxis”  
**Modify:** `plans/2026-08-11-journal-alarm-daemon.md` one-line pointer (optional)

**Verify:**
- [ ] Start **Sesefus** still serves :8777 and opens window  
- [ ] `ui_host.py` line count drops (duplication gone)  
- [ ] Scanner still runs independently (no forced praxis yet)

**Anti-pattern:** Sesefus imports `artifact_scanner.window_host` as “inheritance.”

---

## Phase 5 — Scanner optional consumer (later)

**Not blocking Sesefus.** When ready:

1. Point `ensure_serve.py` at `praxis.serve`  
2. Thin `window_host.py` to product suite (hotswap/zip/board URLs) + praxis primitives  
3. Keep board/session code in scanner forever  

**Risk:** 1635-line host — migrate in slices (ports → serve → host seat → browser → layout).

---

## Phase 6 — Verification (whole program)

| Check | How |
|-------|-----|
| praxis purity | `git ls-files` / grep: no session paths, no board.html |
| Sesefus smoke | Launch Sesefus · record path · alarms list · UI loads |
| Side-by-side | Scanner :8765 + Sesefus :8777 both up |
| Single-instance | Double-click Sesefus twice → one host seat |
| Detached serve | Kill UI only → port still answers |
| you/agent | Any agent-only experiments in `praxis/agent/` or leave out of main package |
| No SW_HIDE | VBS templates use style 1 |

### Final anti-pattern grep (on implement day)

```bash
# inside praxis
rg -n "board\.html|session-map|win_serve|artifact-scanner" src/ || true
# sesefus should not import scanner host
rg -n "window_host|artifact.scanner" apps/journal-daemon/
```

---

## Cherry-pick priority (what lands in initial commit vs later)

| Priority | Item | Initial commit? |
|----------|------|-----------------|
| P0 | ports · http_ok · detached spawn | **Yes** |
| P0 | ensure_serve(AppSpec) | **Yes** |
| P0 | browser app-mode open | **Yes** |
| P0 | host mutex parameterized | **Yes** |
| P0 | FRAME.md · README · pyproject | **Yes** |
| P1 | bat/vbs templates · shortcut installer helpers | Yes if small |
| P1 | launch log helper | Yes |
| P2 | pywebview native path | No (optional follow-up) |
| P2 | work-area multi-window layout | No |
| P3 | shared dyslexia scale JS | No |
| Never | board · archive · aytree · session index | — |

---

## Requirements brief

**Goal:** New repo **praxis** holds the **frame QOL** cherry-picked from Artifact Scanner; **Sesefus inherits** that frame for its small-app window/serve life.

**In scope:** ports, ensure serve, host single-instance, browser/window open, launcher templates, frame contract docs, Sesefus wire-up.

**Out of scope:** Moving scanner product; suite cards as host; speech LLM module inside praxis; liquidating hardware; stream chat.

**Hard constraints:**
- Scanner stays finder/product SSOT for board  
- Sesefus modules stay in sesefus  
- praxis has no session scan dependency  
- Different `app_id` → simultaneous apps allowed  
- Host ≠ serve preserved  

**Open spikes:**
1. Inheritance vehicle: editable path vs submodule vs published package  
2. When/if scanner migrates to praxis (slice order)  
3. Fonts packaging license path  
4. Whether layout multi-window is frame or scanner-only forever  

**Sources / paths:**
- Donor: `C:\Users\bardw\artifact-scanner\` (`window_host.py`, `scripts/ensure_serve.py`, launchers, SEED)  
- Consumer: `C:\dev\sesefus\apps\journal-daemon\`  
- New: `C:\dev\praxis` (create) · GitHub `Zychs/praxis` (create)

**Done when:**
- [ ] `praxis` repo exists with initial frame-only commit  
- [ ] Sesefus journal-daemon launches via praxis ensure_serve + open_window  
- [ ] Scanner still launches without requiring praxis (until Phase 5)  
- [ ] Side-by-side ports work  
- [ ] CHERRY_PICK.md maps each extracted function to donor lines (updated on extract day)

---

## One-line thesis

**praxis = shared window/serve frame; Sesefus inherits the frame; scanner donates QOL and keeps the finder product.**
