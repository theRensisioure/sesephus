# Sesephus Project & Agentic Optimization Guide

This document serves as a persistent global resource for Gemini agents operating in this environment. It outlines the architectural intentions of the **Sesephus** system, along with optimized guidelines for tool usage, compiler management, and token conservation.

---

## 1. System Vision & Intended Architecture (Sesephus Suite)

The end-goal of the suite is **Sesephus**: a unified local-first self-help dashboard comprising several modular sub-systems:

### 🕰️ Circadia (The Alarm Engine)
* **Role**: Alarm management daemon for mass administration of alarms across client devices.
* **Mechanism**: Handled via a Zig TCP server/client connection architecture using length-prefixed protocol frames.
* **Triggers**: Alarms prompt client-side actions, which are dynamically definable (e.g., `play_sound`, `run_command`, `record_audio`).

### 🎙️ Arcadium (Audio Journaling Engine)
* **Role**: Client-side audio recording and encrypted host ingestion.
* **Client side**: Records audio natively using Win32 multimedia APIs (`winmm.dll` waveIn interface), with a synthetic sine-wave generator fallback for headless or restricted hardware.
* **Piping**: The client pipes WAV files over TCP to the host daemon.
* **Ingestion**: The host ingests incoming WAV data into an encrypted local database vault (`sesephus_vault.db`) using **ChaCha20-Poly1305** authenticated encryption (AEAD) with key derivation via **PBKDF2-HMAC-SHA256**.

### 🎡 SaturnNav (Preferential Navigation)
* **Role**: A low-stimulus nav speaker layer for riders who don't need more noise on the road. Preferential routing for bikers, lithium-ion e-assist, gas two-wheelers, acoustic legs, and especially unicyclers. Limited understanding is intentional — short phrases, long quiet stretches, no stacked alerts — so nav doesn't compete with road stimuli for processing bandwidth.
* **Processing model**: Nav benefits most from **preflight** — graph ingest, DEM, wind snapshot, Pareto candidates, and speaker script baked into a local session bundle. **In-ride edits** are lightweight patches against cached alternates inside the preflight corridor; no live cellular reroute, no routing loss on failed patch. Cellular optional after bundle write.

---

## 2. Technical Stack Constraints
- **Language**: Pure Zig (v0.16.0).
- **External Dependencies**: Zero external runtime dependencies. Integrations with Win32 APIs must use native standard library extern declarations or direct DLL imports.
- **Scheduling**: Built on the Zig `std.Io` async/threaded scheduling framework.

---

## 3. Agentic Execution & Token Optimization Guidelines

Future agents working on this project should adhere to the following rules to conserve token budgets, minimize system runtime, and prevent redundant iterations:

### 🔍 A. Python-Based Search & Discovery (Stdlib, Workspace, & Context footprint)
* **Context**: Inspecting namespaces, finding symbols, or locating code blocks without causing token bloat, compilation delays, or failing due to missing environment binaries (like `grep` or `ripgrep`).
* **Anti-Patterns**:
  1. *Incremental Compilation Probe*: Creating small test files (e.g., `probe.zig`) and running `zig run` to check if standard library classes or functions exist.
  2. *Large File View Bloat*: Running `view_file` on entire files or massive line ranges, flooding context window.
  3. *Unverified Grep Dependency*: Relying on built-in search tools when system paths lack binary dependencies.
* **Optimized Approach**: Use Python CLI scripts or custom Python walks. They run instantaneously, have no dependencies, and allow precise extraction of small line slices (e.g., 20–50 lines).
  * *Stdlib symbol lookup:*
    ```powershell
    python -c "import sys; print([line for line in open('C:/Users/bardw/AppData/Local/.../lib/std/Thread.zig') if 'Mutex' in line])"
    ```
  * *Workspace file search:*
    ```powershell
    python -c "import os; print([os.path.join(r, f) for r, d, fs in os.walk('.') for f in fs if 'client' in f])"
    ```

### ⚙️ B. Reliable Subprocess Management (Deadlocks & Logging Buffering)
* **Context**: Orchestrating backend daemons or FastAPI sidecars inside python script managers.
* **Anti-Patterns**:
  1. *Stdout/Stderr Deadlocks*: Spawning a subprocess with `stdout=subprocess.PIPE` without consuming it in real-time, causing OS buffers to fill and processes to freeze.
  2. *Buffered Stream Loss*: Spawning Python sidecars without unbuffered IO, resulting in lost diagnostics if standard streams are terminated abruptly.
* **Optimized Approach**:
  1. Redirect child `stdout`/`stderr` outputs directly to disk log files (e.g., `host.log` or `client.log`) and read them after the process exits.
  2. Always execute Python subprocesses with the `-u` CLI flag (e.g., `python -u script.py`) to guarantee logs are flushed to disk immediately.

### 🪵 C. Run Diagnostic Integrity (Merge Stderr & Stdout)
* **Context**: Analyzing build or execution traces, particularly in Zig where standard errors are handled uniquely.
* **Anti-Pattern**: Ignored standard error streams in python subprocesses, causing panics, memory leak traces, or warnings to be invisible.
* **Optimized Approach**: Always merge standard error into standard output (`stderr=subprocess.STDOUT`) for any automated execution checks to expose failures on the first execution.

### 🧹 D. Native Windows Memory Leak Checking
* **Context**: Sesephus binaries use Zig's Debug General Purpose Allocator, which checks for memory leaks upon process exit.
* **Optimized Approach**: Ensure all dynamically allocated lists (`std.ArrayList`), strings (`allocator.dupe`), and structs (`allocator.create`) are explicitly cleaned up and destroyed before the `main` loop returns, avoiding leak warnings.

### ⏱️ E. Avoid Active Task Polling (Use Platform Reminders)
* **Context**: Long-running background commands or compilation checks.
* **Anti-Pattern**: Running `manage_task` or status commands in a tight loop to check if a task has finished, which consumes context tokens and clutters output logs.
* **Optimized Approach**: Initiate the background task, then set a single-shot timer using the `schedule` tool (e.g. `DurationSeconds=15`) and end the turn. The system will automatically wake up upon task completion or timer expiration, saving tokens.

### 🌐 F. Keep-Alive Socket Stream Read Hangs
* **Context**: Reading HTTP headers or network protocols in custom servers.
* **Anti-Pattern**: Using `readSliceShort` or blocking chunk-reads on a socket stream where the client does not close the connection (e.g. HTTP keep-alive). The stream reader blocks indefinitely waiting for the buffer to fill.
* **Optimized Approach**: Read headers or frames byte-by-byte using `readSliceAll(&[1]u8)` and parse them incrementally, breaking as soon as the delimiter (e.g. `\r\n\r\n`) is matched.

### 📜 G. Accessing Compilation/History logs via JSONL
* **Context**: Retrieving previous variables, options, or context after model compaction or resumes.
* **Anti-Pattern**: Prompting the user to re-provide parameters or making assumptions about historical project state.
* **Optimized Approach**: Write a lightweight temporary python script in the scratch directory to parse the chronological `transcript.jsonl` log file, filter by `USER_EXPLICIT` or target steps, and read exact history.

### 🐧 H. Zig v0.16.0 Cross-Platform POSIX Syscalls Compatibility
* **Context**: Accessing clock time, sleeping threads, and resolving environment variables on Linux/Android under Zig v0.16.0.
* **Anti-Patterns**:
  1. Attempting to use `std.posix.nanosleep` or `std.time.nanoTimestamp` which do not compile or exist directly.
  2. Resolving environment variables using the deprecated `std.process.getEnvVarOwned` which fails on non-Windows/POSIX platforms.
* **Optimized Approach**:
  1. Thread sleeps: Call standard `std.posix.system.nanosleep(&timespec, null)`.
  2. Time generation: Pass a `std.posix.timespec` pointer to `std.posix.system.clock_gettime(std.posix.CLOCK.REALTIME, &ts)` and compute nanosecond offset.
  3. Environment variables: Fetch values directly from the `init.environ_map.get("KEY")` hash map exposed by the `main(init: std.process.Init)` boot parameter.

### 💾 I. Mutex-Free Database I/O via Positional File Operations
* **Context**: Accessing database files concurrently from multiple threads without race conditions.
* **Anti-Pattern**: Manually seeking to offsets (`seekTo`, `seekToEnd`) before writing/reading. Sequential stateful seeks are not threadsafe and require intensive mutex locking.
* **Optimized Approach**: Use Zig's positional file operations (`writePositionalAll`, `readPositionalAll`, and `length`) which specify absolute offsets directly in the parameters, eliminating seek state and reducing thread blocking.

### 🛡️ J. Windows Smart App Control (WDAC/SAC) Binary Blocks
* **Context**: Building and running user-compiled executable binaries on Windows 11 with Smart App Control (SAC) enabled.
* **Anti-Pattern**: Compiling custom code changes (including non-functional changes like warnings cleanup or style tweaks) that produce a new binary executable file. The new binary will change the cryptographic hash, which triggers a Smart App Control block (`[WinError 4551] An Application Control policy has blocked this file`).
* **Optimized Approach**:
  1. If a binary compiled by a previous agent runs successfully, do not make cosmetic modifications to the source code that trigger recompilation. Recompiling will generate a new hash and violate code integrity policies.
  2. To diagnose blocking events, query the Windows Code Integrity operational event log:
     ```powershell
     Get-WinEvent -LogName "Microsoft-Windows-CodeIntegrity/Operational" | Where-Object { $_.Message -like "*your_binary.exe*" }
     ```

### ⏱️ K. Avoid Recursive Wake-Up Loops during User Approval
* **Context**: Proposing commands that run in the background (asynchronous tasks) and require user approval.
* **Anti-Pattern**: Scheduling short, repeating timers (e.g. 5–15 seconds) immediately after proposing a command to check the log file or status. This wakes the agent context continuously, preventing the user from reviewing and approving the proposed command.
* **Optimized Approach**: Submit the command and end the turn without scheduling short timers. The system automatically sends a high-priority message to wake the agent up when the proposed background task completes.

### 🔍 L. Windows Search & Discovery and Grep Failures
* **Context**: Searching for strings or regex matches in the workspace.
* **Anti-Pattern**: Using `grep_search` directly in Windows environments without verifying if a `grep` or `ripgrep` executable is on the system PATH. This raises executable-not-found errors.
* **Optimized Approach**: Write a lightweight Python search script or command-line one-liner (e.g., `python -c "import os; ..."`) to recursively search files, avoiding external binary dependencies.

### ⏱️ M. Virtual Environment Setup Race Conditions
* **Context**: Setting up a Python virtual environment and running test suite / commands immediately.
* **Anti-Pattern**: Running execution checks (like tests or running a script) immediately after launching an asynchronous setup task (like `setup_venv.ps1`) before the task has finished installing all packages. This triggers `ModuleNotFoundError`.
* **Optimized Approach**: Let the background setup command complete and verify its execution logs before triggering dependent tasks.

### 🧪 N. Testing Async Components (Event Loop Closures)
* **Context**: Testing asynchronous servers (e.g., `websockets.serve`) or schedulers (e.g., `APScheduler`) within `unittest.TestCase`.
* **Anti-Pattern**: Starting/stopping async components in synchronous `setUp` and `tearDown` methods. Because `asyncio.run()` closes the event loop when the test completes, calling `shutdown` or `close` in `tearDown` raises `RuntimeError: Event loop is closed`.
* **Optimized Approach**: Initialize the objects in `setUp`, but call `.start()` and `.shutdown()` / `.close()` inside the async test runner method within a `try...finally` block.

### 📦 O. WebSocket Signature Portability Across Library Versions
* **Context**: Handling incoming WebSocket connections using the `websockets` library.
* **Anti-Pattern**: Defining a WebSocket handler with the signature `async def handler(websocket, path):`. In newer `websockets` versions (v14+), the handler function takes only one argument (`websocket`), causing `TypeError` on connection.
* **Optimized Approach**: Use optional or variable arguments to ensure compatibility across all versions: `async def handler(websocket, path=None):` or `async def handler(websocket, *args, **kwargs):`.

### 🔄 P. Staging mirror Sync Script (S: to F:)
* **Context**: Working inside the active development workspace while preparing commits for GitHub.
* **Optimized Approach**: Perform all coding, testing, and debugging inside the Staging workspace `S:\arcadium-circadia`. When ready to commit, mirror files to the Git repo on `F:\git\Arcadiumandcircadia` by executing:
  ```powershell
  python S:\arcadium-circadia\sync_to_git.py
  ```
  This script filters out local databases, log files, caches, and sync files automatically. Perform all git commands (status, add, commit) inside the `F:\git\Arcadiumandcircadia` directory.

### 📁 Q. Context Window Directory Map Pruning (Factor Shredding)
* **Context**: Analyzing massive workspace trees without flooding the context window.
* **Optimized Approach**: Use factor-based shredding to classify mapped files:
  1. *Factor 1 (Core)*: Active source files, configurations, markdown docs.
  2. *Factor 2 (Build/Deps)*: `venv/`, `node_modules/`, `.zig-cache/`, `zig-out/` (always filter these out).
  3. *Factor 3 (Data)*: SQLite database and logs (redirect these entirely to drive `V:`).
  4. *Factor 4 (Media/Synthesis)*: Voice synthesis outputs and WAV recordings (consolidate as folder file counts, never print individual paths).

---

## 4. Environment Directories & Structure Guide

### Environment Directories
* **Staging Workspace (Active Development)**: `S:\arcadium-circadia`
  * *Purpose*: This is the local working directory and system archive workspace containing domain-specific modules. It is *not* initialized with Git. Perform all active code changes and builds here.
* **Git Repository**: `F:\git\Arcadiumandcircadia`
  * *Purpose*: This is the active Git repository containing full commit history and remote sync configuration with GitHub. Mirror your changes here via `sync_to_git.py` to audit and commit them.
* **Database & Telemetry Vault**: `V:\`
  * *Purpose*: Holds all persistent databases (`V:\sesephus_vault.db`) and runtime logs (`V:\host.log`, `V:\client.log`, `V:\dashboard.log`). Kept isolated from your staging and git paths.

### Directory Structure (Staging Workspace / Git Repo)
The staging workspace (`S:\arcadium-circadia`) and Git repo are organized into domain-specific modules to enforce separation of concerns:

* **`core/sesephus/`**: Low-level Zig system daemons (Host & Client). Handles TCP networking, database client calls, and raw alarm triggers.
* **`dashboard/`**: User interfaces and sidecar servers. Contains the FastAPI sidecar (`dashboard_server.py`) and the unified Vite + React frontend (`dashboard/ui`).
* **`ingest/`**: Ingestion shards (telemetry data).
* **`aurgio/`**: Local voice journals, transcript metadata, and raw audio files.
* **`audio/`**: Edge capturing scripts, FFT analyzers, and audio processing tools.
* **`shredder/`**: Sieve text-shredding and redaction modules.
* **`simulator/`**: Agentic conversation emulators and broker simulators for testing.
* **`client/`**: Standalone audio capturer experiments (`recorder.zig`).
* **`tools/`**: Support utilities and system scripts (e.g., `compress_archive.zig`).
* **`utils/`**: Chat pruners, latent space noise filters (`spiffy_prune.py`), and prompt compression scripts.
* **`docs/`**: Reference guides, backups, and agent guidelines ([gemini.md](file:///S:/arcadium-circadia/docs/gemini.md)).

---

## 5. Repository Version Sequence

To ensure coordination across Zig, Python, and React modules, the Sesephus project uses a synchronized versioning matrix.

### 5.1 Sesephus Suite Release Matrix
The overall suite version represents the collective milestones of all sub-systems.

| Suite Version | Git Branch / Milestone | Key Features & Architecture Changes | Released Component Alignment |
| :--- | :--- | :--- | :--- |
| **v1.0.0** | `Decision,-rust,-python,-or-zig` | Exploration of multi-language options. Selection of Zig (v0.16.0) as the core host daemon language. | Circadia v1.0.0, Arcadium v1.0.0 |
| **v2.0.0** | `main` (baseline) | Initial codebase structure, multi-drive orchestration (`S:\`, `V:\`, `F:\`), text ingestion foundations. | Circadia v1.0.1, Ingest v1.0.0 |
| **v3.0.0** | `main` (expanded) | Circumstance alarm engine extensions (Circadia subgroups, bulk edits, interval sequences, precision tuning). | Circadia v2.0.0, Ingest v1.1.0 |
| **v3.1.0** | `feat/telemetry-lighthouse-ui` | Added client telemetry, panic logging, crash recovery, and integrated the glassmorphic Lighthouse Portal design theme. | Circadia v2.1.0, Dashboard v3.C.5.1 |
| **v3.2.0** | `feat/embed-client` | Embedded local client thread inside `host.zig` to facilitate zero-config development and edge testing. | Circadia v2.2.0, Dashboard v3.C.5.2 |
| **v3.3.0** | `feat/orchestrated-inference` | Added `build_client.ps1` for targeting multiple client devices (Pixel, Surface, etc.) and prepared frontend for orchestrated inference selectors. Note: `build_client.ps1` was subsequently removed for stability. | Circadia v2.3.0, Dashboard v3.C.5.3 |
| **v3.4.0** | `main` | Added robust runtime CLI help features (`help`/`--help`/`-h`) and interactive command shell documentation references. | Circadia v2.4.0, Dashboard v3.C.5.3 (Current) |

---

### 5.2 Component-Specific Version Registries

#### 🕰️ Circadia (Alarm TCP Daemon & Client)
* **v1.0.0**: Initial TCP packet architecture, client handshake, and base action execution hooks.
* **v1.0.1**: Stabilized TCP read/write buffer handling and fixed potential memory leaks on socket close.
* **v2.0.0**: Multi-target sequence queuing, support for subgroups, mass alarm administration, and interval schedules.
* **v2.1.0**: Win32 multimedia capturing and telemetry logging (`client.log` in `V:\`), integration of Windows-native panic handler overrides to write to disk.
* **v2.2.0**: Exposed client runtime programmatic interfaces; embedded thread invocation support inside host process.
* **v2.3.0**: Target duplication capabilities via `build_client.ps1`, enabling optimized target builds for device-specific runs (Surface, Pixel, Debian, etc.).
* **v2.4.0** *(Current)*: Integrated runtime CLI help (`help`/`--help`/`-h`) and interactive command-line shell documentation.

#### 🎙️ Arcadium (Audio Journaling & Cryptographic Vault)
* **v1.0.0**: Win32 native voice capture (`winmm.dll`) and fallback sine-wave generator.
* **v1.1.0**: Authenticated Encryption with Associated Data (AEAD) via ChaCha20-Poly1305 and PBKDF2 key derivation.
* **v1.2.0** *(Current)*: Whisper ingestion backend, local audio segment processing, and database schema extensions.

#### 🎡 SaturnNav (Preferential Navigation)
* **v0.1.0** *(Current)*: Low-stimulus speaker layer with stimulus budget, sparse phrasing, preferential routing, rider profiles (unicycle especially), concurrent optimization stack, attractor basins, and Route Lab integration.

#### 🖥️ Dashboard Console (Server & UI)
* **v1.0.0**: Simple static landing page and FastAPI status endpoints.
* **v2.0.0**: Migration to Vite + React frontend dashboard framework (`dashboard/ui`).
* **v3.C.5.1**: Consolidated unified frontend design using the premium glassmorphic dark-mode Lighthouse UI reference (rotating beam accent, Outfits/Mono fonts).
* **v3.C.5.2**: Integrated device list panel, live status badge glows, and real-time client telemetry log stream window.
* **v3.C.5.3** *(Current)*: Added orchestrated node selector dropdown and edge-case execution controls.

---

### 5.3 Versioning & Release Guidelines for Agents
When making changes to the codebase, follow these versioning increment rules:
1. **Host Daemon Core Changes (Zig)**: Increment the second digit (minor version) of Sesephus Suite and Circadia (e.g., `v3.3.0` -> `v3.4.0`) if new protocols, capabilities, or embedded features are added.
2. **Dashboard UI Refinement (HTML/CSS/JS)**: Increment the patch digit of the Dashboard Console (e.g., `v3.C.5.2` -> `v3.C.5.3`).
3. **Smart App Control (SAC) Risk**: Avoid source version string modifications in Zig/HTML code files unless explicitly instructed by the user, to prevent changing the cryptographic binary hashes and triggering Windows SAC blocks.
