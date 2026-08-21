# Sesephus Help Documentation & Command Reference Guide

Welcome to the Sesephus Suite Help system. This guide provides detailed information on running, configuring, and engaging with the **Sesephus** application suite.

---

## 🚀 Runtime CLI Arguments

There is **one unified executable, `sesefus.exe`** (built by `build.zig`, launched
by `ssfs.bat`). The role is chosen at first run (stdin prompt → `runtime.json`)
and can be forced with `--role host|client`. There is no separate
`host.exe` / `client.exe`.

### 🕰️ Host Role (`ssfs.bat` / `sesefus.exe --role host`)

The host role manages the scheduler, handles connected client status, and manages the authenticated database vault.

**Usage:**
```bash
ssfs.bat [options]
sesefus.exe --role host [options]
sesefus.exe help | --help | -h
```

**Options:**
- `--vault <path>`
  Specify a custom path to the encrypted database vault file (e.g. `--vault D:\sesephus_vault.db`). 
  *Default:* `V:\sesephus_vault.db` (with local `./sesephus_vault.db` fallback).
- `--read-vault`
  Decrypts and dumps raw transaction metadata and logs from the vault database directly to stdout, then exits immediately.
- `--extract <index> <out_path.wav>`
  Extracts the raw WAV audio journal entry stored at the specified `<index>` inside the encrypted vault and saves it to `<out_path.wav>`.

---

### 🎙️ Client Role (`sesefus.exe --role client`)

The client role registers with the host to listen for alarm events and trigger local sound alerts, system commands, or audio recording journals.

**Usage:**
```bash
sesefus.exe --role client [options]
sesefus.exe help | --help | -h
```

**Options:**
- `--name <id>`
  Sets a unique client ID. If omitted, the client defaults to the Windows Computer Name, hostname environment variables, or fallback strings.
- `--host <ip>`
  Specifies the IP address of the running Sesephus host daemon. 
  *Default:* `127.0.0.1`.
- `--port <port>`
  Specifies the TCP port of the running Sesephus host daemon.
  *Default:* `5000`.
- `--non-interactive`
  Bypasses the `(y/N)` validation prompt on `record_audio` actions. The client will immediately capture raw microphone input for the requested duration.
- `--no-record`
  Disables microphone recording capabilities. Alarms requesting `record_audio` will play beeps/alerts but dismiss recording.

---

## 💬 Host Interactive CLI Shell Commands

Once the host role is running, it spawns an interactive command-line interface. Use these commands to schedule alarms, control subgroups, or perform cryptographic database checks.

### 1. Alarm Scheduling & Management

- `status`
  Prints active client connections, subgroup registrations, and the total count of pending/fired alarms.
Syntax is **space-separated** — first token is the module, second the subcommand
(underscore forms like `alarm_group` resolve to `Unknown module`).

- `alarm schedule <client_id> <sec_from_now> <action> <duration>`
  Schedules an alarm for a specific client.
  *Example:* `alarm schedule client-laptop 15 record_audio 10.0`
- `alarm group <group_id> <sec_from_now> <action> <duration>`
  Schedules an alarm for all devices registered in a client subgroup.
  *Example:* `alarm group study_room 30 play_sound 5.0`
- `alarm toggle <true|false>`
  Globally enables or disables all scheduled alarms in memory.
- `alarm bulk <action> <duration> <alarm_id1,alarm_id2,...>`
  Bulk-modifies the action and action duration for the specified comma-separated list of alarm IDs.
- `alarm interval <client_id1,client_id2,...> <dur_sec> <count> <action> <act_dur> [group_id]`
  Schedules a sequence of `<count>` alarms spaced evenly over `<dur_sec>` seconds.
  *Example:* `alarm interval client-01,client-02 60 5 record_audio 8.0`
- `alarm adjust <parent_id> <spacing_sec> <jitter_ms>`
  Recalculates the spacing between all pending interval alarms belonging to `<parent_id>` and adds a random offset up to `<jitter_ms>` milliseconds.
- `alarm list`
  Lists pending and fired alarms.

---

### 2. Subgroup Management

- `group create <name> <client_id1,client_id2,...>`
  Defines a new subgroup with a unique ID and registers the listed client devices.
  *Example:* `group create office_desk client-01,client-02`
- `group list`
  Lists defined subgroups.
- `group rename <group_id> <new_name>`
  Renames the subgroup.
- `group edit <group_id> <client_id1,client_id2,...>`
  Replaces the clients assigned to `<group_id>` with a new list.
- `group delete <group_id>`
  Deletes the subgroup definition (does not affect scheduled alarms already created).

---

### 3. Vault & Database Operations

- `backup [dest_path]`
  Replicates the database vault to a backup location. **Wired.**
- `vault ingest-archive [--dry-run] [--limit n]`
  Historical memo ingress via `tools/ingress_memos.py`. **Wired.**
- `vault status` / `vault backup` / `vault audit`
  Currently **stubs** — they print a line and do nothing (CANON §2; wiring is
  tracked in issue #70). Use `--read-vault` to inspect the vault.

---

## 🛠️ Troubleshooting & Core Settings

### Port Conflicts
- **Zig Host TCP Port:** Bindings run on port `5000` (TCP socket). Make sure no other local service is using port `5000`.
- **FastAPI Port:** The Python AI transcription server runs on port `3001` (HTTP). The React/Vite proxy forwards requests here.

### Vault Encryption Key
Sesephus utilizes a robust key derived via **PBKDF2-HMAC-SHA256** with **ChaCha20-Poly1305** authenticated encryption to prevent local database snooping. If you need to verify vault authorization, run:
```bash
sesefus.exe --read-vault
```
(`vault audit` inside the interactive shell is currently a stub — CANON §2; use `--read-vault` for inspection.)

## How we used derive lanes for strict-database-host + unified archive (Unit 3 prime ex, 2026-06-12)

**From transcript (relative .grok/memory/bardw-5d3d16c2/sessions/2026-06-12-sesefus-strict-main-layer-rebuild.md + unified-runtime-precompact.md) + LANE_AGENT_ARRAYS.md Lane 3 (Sesefus Strict-Main + derive-agent-array) Impl 3 (IMPL-3-3)**:

- strict-main: orphan foundation branch (layers: 0 scaffold, 1 database/vault from vault-security...@21daf17, 2 gemini prompts vendored from naissance per leadlogic rule + git/repo-libs-naissance/meta/INDEX.md, 3 curated CLI/alarm); rebuilt via tools/strict_main.ps1 (explicit staging, no venv debris); tip 20f3528; reproducible.
- Then feat/unified-runtime-archive (single sesefus.exe binary: host/client role at first-run persisted in runtime.json; 6GHz/LAN discovery stub; dual archive db + ingress_memos.py; zig build clean; stacked on strict-database-host 04b38fa; tip 2a310ab).
- Used derive-agent-array (per .grok/skills/derive-agent-array/SKILL.md + lane-recursion-abc.md): 4 units mapped (Unit 3 = this), lanes from PF-*, 3 impls/lane (C.3 hygiene+cherry for cli + manifest), winners → trunk/cherry manifests (not full merges; see GIT_HISTORY_RESOLUTION.md), T:\compose-staging first, individual remotes, promote.
- Vendoring: naissance prompts (qualify-post.md Systems Peer) into sesefus lead.zig / strict path.
- Post: cleaner + derive ps1 clean C: copies (git/Arcadiumandcircadia/core/sesephus + .grok/derive equivalents: zig-out, .zig-cache, debris), promote manifest/artifacts/LANE/GIT to T:\grok\meta\ ; snapshot mappers; credit in external view (HEAVY_TRANSCRIPTS_ONTOLOGY.md).
- 4 units recap: 1=Naissance PR (cherry discipline), 2=DIGEST/compaction, 3=Sesefus (this), 4=Clone+gh align (on-ramp to T: SSOT role-split).
- Self-ref: produced by IMPL-3-3 under T:\compose-staging\derivation-external-view-2026-06-12\implementations\3-3\ ; ties derive skill, T: first, unified runtime archive, strict-main foundation. See also LANE/GIT in staging root + promotion scripts there.

**Recipe tie-in**: run derive → lane winners → manifest/cherry/trunk integrate → staging promote (clean C: first) → mappers snapshot → credit view/blueprint/sesefus docs. (Full in derive skill Phase 9 + prompting-infrastructure §10.)
