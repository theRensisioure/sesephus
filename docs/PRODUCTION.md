# Sesephus Production Guidelines & Guardrails

This document outlines the deployment checklist and safety guardrails enforced by the Sesephus host daemon when running in production mode.

## 1. The Single Source of Truth

The Zig Host Daemon (`sesephus host`) is the absolute single source of truth for all alarm state, cryptography, and persistence.
- **UI Architecture**: The React Dashboard **must never** attempt to execute low-level system commands directly. It must communicate exclusively through the FastAPI sidecar.
- **Sidecar Role**: The Python sidecar translates UI requests into either HTTP API calls against the Host Daemon or sanitized CLI executions via `sesephus <command> --json`.

## 2. Global Guardrails

When the daemon or CLI is started with the `--production` flag, several safety mechanisms are activated:

### Destructive Operation Confirmation
Any CLI command classified as destructive (e.g., `group delete`, `vault refactor`, `vault shuffle`) will trigger an interactive `(y/N)` prompt. This prevents accidental data loss or disruption to scheduled alarms.

### Dry-Run Simulation
Administrators can append `-n` or `--dry-run` to any command. The system will process the parameters, validate the logic, and emit the expected side-effects to the console without actually mutating the database or vault.

### Strict API Rate Limiting (Upcoming)
In production, the host daemon enforces stricter rate limits on incoming HTTP requests from the proxy sidecar to mitigate looping errors in the UI.

## 3. Deployment Checklist

Before deploying Sesephus to a production device, ensure the following:
- [ ] `SESAPHUS_PRODUCTION=1` environment variable is set.
- [ ] The CLI entrypoint `sesephus` is available in the system PATH.
- [ ] The `sesephus_vault.db` file is backed up.
- [ ] The FastAPI proxy is configured to use the correct Host Daemon port (default 3000).
- [ ] All automated scripts invoking `sesephus` append the `--production` flag and handle interactive prompts appropriately, or use predefined API endpoints.

## 4. Audit Logging

Every interaction with the Host Daemon, whether via HTTP API or standard CLI execution, is recorded. Destructive actions trigger high-visibility logs detailing the exact timestamp, the command issued, and the resulting state change.

## 5. SSFS Drive Lettering & Resilience (CRITICAL — prevents data loss scares)

**Single source of truth:** `ssfs/drive-mapping.json`

- V: (label SSFS_VAULT) — Primary vault (audio + state). **Required**. All code derives paths via the engine/resolver.
- E: (label SESEFUS-STAGING) — Cold archive (enclosure). High priority, optional in some contexts.
- T: (future worktrees) — optional.

**Rules that stop disasters from repeating:**
- NEVER hard-code V:, E:, T: or any drive letter in source, scripts, or commands (except this file and the verified receipts).
- Run `node ssfs/storage/config-engine.js` **manually** whenever you want (before big ops, after hardware changes, on new boots, etc.). It does existence + **label match** checks, **fails loud**, and writes a receipt to `V:\ssfs-vault\state\ssfs-verified.json`.
- (Autostart in the Zig host is intentionally paused for now — per preference.)
- Live git checkouts live **only** at `C:\dev\sesefus`. Nowhere else (Desktop, OneDrive, Favorites, etc. caused the original sync corruption + sprawl).
- Cold archive (E:) is read-only history. Never work directly in it. The 7z split for cloud is the offsite third copy path.
- Before any destructive disk/partition action: re-verify with the engine + confirm you have 2+ independent copies of irreplaceable data.

**Usage from JS tools:**
```js
const { getVaultPath, getAudioJournalPath, getMainVaultDbPath } = require('./ssfs/storage/paths');
const vaultAudio = getVaultPath('audio');   // V:\ssfs-vault\audio
const journal = getAudioJournalPath(new Date());
const db = getMainVaultDbPath();            // V:\sesephus_vault.db (unified)
```

Run the guard often. It is the thing that would have made the unallocated-disk day a non-event.

See also: ssfs/ , drive-mapping.json , vault_security.md (migrate hardcodes toward this over time).
