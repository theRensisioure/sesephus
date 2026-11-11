# Changelog

## 1.0p — 2026-09-18

Contract freeze. **No runtime.** No `fm` binary. Directory `fuzzy-mirror/` holds docs + `schema/v1.0p.json` only.

### Key decisions (human)

1. Isolate the finder. FZD picks a place (host + abs dir). Scanner only gets a handoff token.
2. Primary noun is descendant filesystem directories. Root is not a hit. Never file titles.
3. Rule-directory is a later binder-consumer. Print the strike. Do not execute it.
4. Wrap stock fzf. First code PR freezes Python for ignore / walk / host. Do not source-fork fzf. Do not extend `core/sesephus`.
5. Walk on the host. Filter on the client. Snapshot once (or explicit refresh). Not per keystroke.
6. Ignore compile is `I = B + file.baseline + (file.advanced if advanced)`. `A` names the stanza, not a second list. Deleting `Documents/` unhides it. Staged is ancestor-closure **OR** into the candidate set, not an ignore file. `R` is refuse-to-walk.
7. Pairing gates **every** listen socket, including loopback and SSH-forward. Empty token refuses listen. PairHello first. WalkStart needs session.
8. Local `fm pick` / `fm walk` without `--endpoint` never open a port.
9. v1.0p UI is fzf argv from `fm schema`. Not a REST GUI. Not Tk. Not the three dashboards.
10. One fzf key per schema object. Ctrl-h is backspace. Ctrl-a toggles advanced. Ctrl-d is a no-op. Reload via Python `fm-internal`, not POSIX `cat`.
11. Closed error classes. One class, one meaning. Never coerce a failed walk into “no directories.”
12. Dual-host: drive letters stay in JSON `abs_dir`. `lstat`. Owner-only ACL on `~/.fuzzy-mirror/`.
13. v1.0p is the contract release, not a binary gate.
14. `device_id` is public. The token is the secret.
15. LAN later (PR10) cannot merge without TLS or `listen.trust=trusted-l2`.
16. Generator skips empty/`(default)` keymap rows. Query-mismatch uses `FZF_TOTAL_COUNT` + `FM_SNAP_N`, not `{+n}`.
17. `--allow-root-ignore` **strips** hide-everything patterns, then banners, then walks. It does not return an empty tree.

### Fences

- No unauthenticated HTTP/TCP (including SSH-forwarded loopback without PairHello).
- Forbidden ports: 3000, 5000, 3001, 5173, 8000.
- Forbidden wire types: `RegisterClient`, alarm JSON, `audio_data_base64`.
- Not fuzzy-dow, Clippers, AyTree, Artifact Scanner, grok-launcher, private `C:\dev\sesefus`.
- Corrections, not praise.
- Do not kill `ollama serve`.

### Closed after freeze (same day)

- **OQ2:** Linux default listen is `unix://$FM_HOME/host.sock`. Windows stays loopback TCP `127.0.0.1:18733`.
- **OQ15:** Operator confirmed candidate-OR + baseline vs `# --- ADVANCED` stanza. PR5 is later-sitting runtime, not gated on that confirm.

### Still open for later PRs

Per-device tokens (4), snapshot invalidation (5), symlink follow confirm (6), gitignore `[]` / nested `.gitignore` (7), untracked vs staged (8), shell `cd` (10), rule-directory home via a future `/constrain` skill not born this sitting (11), port 18733 on SPN for Windows-listen / SSH-forward TCP (12), ranking beyond fzf default (13), SSH-only vs token-LAN UX (14).
