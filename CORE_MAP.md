# CORE_MAP: Agentic Directory Consolidation

This document serves as the unified map for the agentic pipeline, tracing the lifecycle of the Anchor Task: **Recursive Intent Resolution**.

## Pipeline Overview
`Interface` $\rightarrow$ `Core` $\rightarrow$ `Engine` $\rightarrow$ `Prototype` $\rightarrow$ `Feedback`

---

### 1. Interface Layer (`interface/`)
*Doctrine: Emergent Context*
- **Primary Component**: `dashboard/dashboard_server.py` (FastAPI Bridge)
- **Secondary Component**: `core/sesephus/src/cli.zig` (CLI Parser)
- **Role**: Captures `UserIntent` via HTTP/CLI and serves as the entry point for the "Sieve" (artifact ingestion).

### 2. Core Schema (`core/`)
*Schema: AGPIAI-3.0 / Centroidal Design*
- **Primary Component**: `core/sesephus/src/host.zig` (State & Vault logic)
- **Supporting Files**: `runtime_config.zig`, `database.zig`
- **Role**: Decomposes intent into `SemanticQuanta`, manages thread-safe state (clients, alarms), and handles vault encryption.

### 3. Engine Execution (`engine/`)
*Logic: Neuronal Quanta / Sovereignty*
- **Primary Component**: `core/sesephus/src/commands/router.zig` (Routing logic)
- **Supporting Files**: `main.zig`, `client.zig`
- **Role**: Executes the decomposed quanta, manages network protocols, and routes commands to specific modules.

### 4. Prototype Implementation (`prototypes/`)
*Laborer: Active Prototype*
- **Primary Component**: `tools/` (Python scripts: `qualify_post.py`, `ingress_memos.py`)
- **Secondary Component**: `work/` (Experimental logic)
- **Role**: Performs the actual work (e.g., file operations, scoring) and generates `fidelity_score`.

---

## Dependency Graph


## Directory Index (Sibling Repositories)

**Interface**
- `neurialab-web`
- `zychs.github.io`
- `sideboard`

**Core**
- `semantic-core`
- `durable`
- `almanack`

**Engine**
- `sky-lane`
- `route-frame`
- `stratabasor`
- `unlosth-dev`
- `sesefus`

**Prototype**
- `vej-lab`
- `bas-coop`
- `scavenge-mill`
- `artifact-scanner`
- `voice`
- `script-launch`
- `journal-clip`

## Scaffolding Registry

**Interface**
- `neurialab-web` (React/Vite)
- `zychs.github.io` (Static/Web)
- `sideboard` (UI)

**Core**
- `semantic-core` (Zig/Logic)
- `durable` (Persistence)
- `almanack` (Scheduler)

**Engine**
- `sky-lane` (Routing)
- `route-frame` (Execution)
- `stratabasor` (Processing)
- `unlosth-dev` (Engine)
- `sesefus` (Host)

**Prototype**
- `vej-lab` (Experimental)
- `bas-coop` (Simulation)
- `scavenge-mill` (Data)
- `artifact-scanner` (Card Tools)
- `voice` (Historical)
- `script-launch` (Launch)
- `journal-clip` (Capture)
