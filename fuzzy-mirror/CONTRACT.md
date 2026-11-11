# Fuzzy Mirror Contract v1.0p

| Field | Value |
|---|---|
| **Date** | 2026-09-18 |
| **Status** | Frozen v1.0p (docs). Runtime **absent**. |
| **Home** | `C:\dev\sesephus\fuzzy-mirror\` |
| **Engineering form** | [DESIGN.md](DESIGN.md) |
| **Schema** | [schema/v1.0p.json](schema/v1.0p.json) |
| **Normative** | This file (C0–C9) plus Key Decisions. If DESIGN.md hats and this file disagree, **this file wins** or this file is wrong and must be patched first. |

Version string: `1.0p`. Protocol field: `"v": "1.0p"`.

---

## Identity

**Fuzzy Mirror** isolates fuzzy-find. The operator runs CLI `fm`. Local pick walks in-process and never opens a port. Listen sockets refuse to start without a pairing token, require `PairHello` first, and require a `PairOk` session before any walk. The host walks a tree once and ships a snapshot. The client filters locally. The v1.0p UI generator is `fm schema` JSON → stock `fzf` argv. Pairing is Syncthing-shaped (token file + host approve). The interface reports **corrections**. It does not praise.

**Not this product:** `fuzzy-dow`, AyTree, Artifact Scanner, sesefus host:client (`RegisterClient`, ports 3000/5000/3001/5173), grok-launcher, Clippers, Method Cards as runtime, private `C:\dev\sesefus`. Scanner may read a handoff token. Fuzzy Mirror does not launch Scanner.

**Two nouns.** FZD (primary) = filesystem descendant directories; never file titles. Rule-directory (later) = finite named set of rule files; print strikes; do not execute them.

Picker is stock `fzf` (do not source-fork). First code PR freezes **Python** for ignore / walk / host.

---

## Key Decisions (condensed)

1. Isolate the finder. FZD chooses host + abs dir. Scanner gets a handoff token only.
2. Primary noun is FZD. `--root` itself is not a hit. Nested dirs independently selectable. Files never enter the FZD hit set.
3. Rule-directory is binder-consumer, not v1.0p primary. Print, do not execute. Never kill `ollama serve`.
4. Wrap stock fzf. First code PR freezes Python. Do not extend `core/sesephus`.
5. Walk on the host; filter on the client. Snapshot once or on explicit refresh.
6. Ignore algebra lives only in C3: `I = B + file.baseline + (file.advanced if advanced)`. `A` names the stanza, not a second list. Staged is candidate OR (ancestor closure). `R` is a pre-walk predicate.
7. Pairing gates every listen socket, including loopback. Empty token refuses listen. `device_id` is public; token is the secret.
8. v1.0p derived UI is fzf argv from `fm schema`. Not REST GUI. Not the three dashboards.
9. One fzf key per schema object. Ctrl-h backspace. Ctrl-a toggle-advanced. Ctrl-d no-op. Reload via Python `fm-internal`.
10. Closed error classes. One class, one meaning. Never coerce failed-walk into empty.
11. Handoff, not merge. `last-handoff.json`. Do not launch Scanner.
12. Dual-host: drive letters kept in JSON `abs_dir`. Snapshot body relative, `/` only. `lstat`. Owner-only ACL.
13. v1.0p is the contract release, not a binary.
14. Local pick never opens a port.
15. PairHello-first on any listen socket.
16. Generator scope is fzf argv only.
17. `R` is refuse-to-walk. `--allow-root-ignore` **strips** those patterns, banners, then walks.

---

## C0 Identity and files

- Product name: **Fuzzy Mirror**.
- CLI: `fm` (long form `fuzzy-mirror` as argv0 alias).
- Config dir: `$FM_HOME` else `~/.fuzzy-mirror/` (Windows: `%USERPROFILE%\.fuzzy-mirror\`).
- **Copies:** Windows public-lineage copy is `C:\dev\sesephus\fuzzy-mirror`. An SPN copy is for local-model review (phi); **do not overwrite live `fzd-*`**. This sitting does not scp.
- Neighbor: `C:\dev\sesephus\fuzzy-dow\` is out of scope.
- Snapshot kind default: `fzd-dirs`.
- Language freeze (first code PR): **Python** for ignore / walk / host. Picker: stock `fzf`.

Config dir mode: Unix `0700`; Windows owner-only ACL (no other users). Every file under it inherits owner-only (Unix `0600` / equivalent ACL), including `approved-devices`, `pending-devices`, snapshots, logs, pid.

```
~/.fuzzy-mirror/
  device-id                 # 32 hex, public identity
  pairing-token             # 32 hex, secret
  approved-devices          # one device-id per line
  pending-devices
  profile                   # "baseline" | "advanced" (Ctrl-a / --profile)
  host.pid
  host.sock                 # Linux/macOS unix listen, if endpoint is unix://
  host.log
  last-snapshot.meta.json
  last-snapshot.paths       # NUL-separated; ≤ max_entries
  last-handoff.json
  config.toml
```

`config.toml` keys (v1.0p, all optional):

```toml
# Client default (Windows, or Linux talking over SSH-forwarded TCP):
endpoint = "tcp://127.0.0.1:18733"
# Host listen default is OS-specific (C5.10):
#   Linux:   unix://$FM_HOME/host.sock
#   Windows: tcp://127.0.0.1:18733
# listen = "unix://$FM_HOME/host.sock"
root     = ""                        # empty → $PWD / %CD%
# LAN only. Absent or "refuse" → non-loopback listen is a start error.
# "trusted-l2" = operator accepts cleartext token on L2 (C5.11).
# "tls" = PairHello wrapped (amendment; not implemented in v1.0p docs).
listen.trust = "refuse"
```

Ignore inputs (read, not owned exclusively): `~/.fzdignore`, `~/.fzfignore`.

---

## C1 Commands

Global flags (all commands):

| Flag | Effect |
|---|---|
| `--json` | **Emit JSON on stdout.** Live. Not inert. |
| `--help` / `-h` | Help derived from `fm schema`. |
| `--endpoint URL` | Talk to a listen socket. Absent on `walk`/`pick` → in-process, **no socket**. |
| `--token-file PATH` | Pairing token (client). Default `~/.fuzzy-mirror/pairing-token`. |
| `--dry-run` / `-n` | Print intended walk/approve/bind. **Never** binds, walks for real, or spawns fzf. |

Exit codes: `0` success (path printed or status ok); `1` usage; `2` error; `130` abort (fzf/SIGINT class).

Exit 2: if `--json`, stdout is `{ "v":"1.0p", "ok": false, "class": "..." }` (and optional `detail`, `pattern`, `walk_id`). Else one C6 banner line on **stderr** and no JSON. Exit 0 with `--json` prints `{ "v":"1.0p", "ok": true, "class": "...", ... }`. Abort 130: no JSON, no handoff rewrite.

```
fm schema
fm status
fm host start [--listen ENDPOINT] [--token-file PATH]
fm host stop
fm host pair-print
fm host pending
fm host approve <device-id>
fm host deny <device-id>
fm host rotate-token
fm walk [--root PATH] [--profile baseline|advanced] [--or-staged] [--refresh]
        [--allow-root-ignore] [--ignore-file PATH] [--max-entries N]
        [--timeout-sec N] [--max-depth N] [--endpoint URL]
fm pick  [same walk flags] [--no-walk]
fm handoff show
fm strikes --transcript FILE     # reserved; v1.0p prints class absent
```

There is **no** `fm connect` as a long-lived process in v1.0p. `--endpoint` on `walk`/`pick` is an ephemeral connect: PairHello, WalkStart, read snapshot, close.

`fm pick` without `--endpoint` = in-process `fm walk` then fzf argv. `--no-walk` with a snapshot file → class `cache`. `--no-walk` with no snapshot file → class `cache-miss`, no fzf.

`fm host stop` kills the pid in `host.pid` and unlinks `host.sock` if present. Missing pid file → exit 2 class `disconnected`.

`fm schema` stdout is the UI contract. On-disk [schema/v1.0p.json](schema/v1.0p.json) contains the **full** C4 keymap and C6 class list. A validator (PR2) fails if `.keymap` / `.error_classes` drift from the tables, or if any `.keymap[].chord` contains `/` or whitespace-separated alternatives.

---

## C2 Message types (host control protocol)

Used **only** when a listen socket exists. Local pick never speaks C2.

Framing: **newline-delimited JSON** (NDJSON), UTF-8. Max **1 MiB** per JSON line. `WalkSnapshot` **must not** inline paths.

`sha256` hex is **lowercase**. `byte_length` cap: **33554432** (32 MiB). Over cap → `failed-walk`, close. `WalkProgress` at most **2/s** or on 10% `seen/max_entries` boundaries, whichever is less chatty.

### C2.1 Normative read loop

```
session = None
state = NDJSON
on accept:
  first = read_json_line()
  if first.type != "PairHello" or first.v != "1.0p":
      write PairDenied class=unpaired; close   # includes RegisterClient, WalkStart, unknown
  result = handle_pair_hello(first)            # C5
  if result is PairDenied: write it; close
  session = result.session
  write PairOk
  loop:
    if state == NDJSON:
      msg = read_json_line()                   # 1 MiB cap
      if msg.v != "1.0p": write WalkError class=version-mismatch; close
      if msg.type == "WalkStart":
        if msg.session != session: write PairDenied class=unpaired; close
        begin_walk(msg)
      elif msg.type == "WalkSnapshot":         # host → client only
        if msg.byte_length > 33554432: WalkError failed-walk; close
        state = BODY; remaining = msg.byte_length; expect_id = msg.walk_id
      elif msg.type unknown:
        ignore line                            # forward-compat AFTER PairOk only
      else:
        handle other control types
    elif state == BODY:
      body = read_exact(remaining)
      end = read_json_line()
      if end.type != "WalkBodyEnd" or end.walk_id != expect_id:
          WalkError class=failed-walk; drop body; close
      if sha256_hex_lower(body) != end.sha256:
          WalkError class=failed-walk; drop body; close
      state = NDJSON
      deliver snapshot
```

Client that is about to read a body: after `WalkSnapshot` header, read **exactly** `byte_length` bytes, then one NDJSON line `WalkBodyEnd`. Then resume NDJSON.

### C2.2 Types

```json
{"v":"1.0p","type":"PairHello","device_id":"<32hex>","token":"<32hex>","client_name":"string"}
{"v":"1.0p","type":"PairOk","session":"<opaque>","host":{"os":"linux","user":"dev","hostname":"SPN"}}
{"v":"1.0p","type":"PairDenied","class":"pending-approval|bad-token|unpaired","device_id":"<32hex>"}
{"v":"1.0p","type":"WalkStart","session":"<opaque>","root":"C:/Users/foo","profile":"baseline|advanced","or_staged":false,"refresh":false,"allow_root_ignore":false,"max_entries":50000,"timeout_sec":30,"max_depth":null}
{"v":"1.0p","type":"WalkProgress","walk_id":"...","seen":0,"denied":0,"elapsed_ms":0}
{"v":"1.0p","type":"WalkError","walk_id":"...","class":"permission|failed-walk|ignore-hid-tree|disconnected|version-mismatch|not-a-git-work-tree","detail":"string","pattern":null}
{"v":"1.0p","type":"WalkSnapshot","walk_id":"...","kind":"fzd-dirs","host":{"os":"linux","user":"dev","hostname":"SPN"},"root":"/home/dev","status":"complete|partial","seen":0,"denied":0,"hidden_by_ignore":0,"or_staged_added":0,"cache":false,"elapsed_ms":0,"body":"nul-paths","byte_length":0}
{"v":"1.0p","type":"WalkBodyEnd","walk_id":"...","sha256":"<64 lowercase hex>"}
{"v":"1.0p","type":"HostStatus","listen":"tcp://127.0.0.1:18733","paired":true,"pending":0,"last_walk":{"class":"partial","walk_id":"...","ts":"2026-09-18T00:00:00Z"}}
```

`WalkStart` **without** `session` matching this connection’s `PairOk` → close `unpaired`.

**Forbidden on this socket:** `RegisterClient`, alarm types, `audio_data_base64`, HTTP dashboard payloads. Before PairOk they close the socket (`unpaired`). After PairOk they are unknown types and are ignored (do not start a walk).

---

## C3 Ignore algebra

One formula.

Named sets:

| Set | Id | Default | Contents |
|---|---|---|---|
| Baseline | `B` | always on | **Compile-time constant** gitignore lines: `node_modules/`, `venv/`, `.venv/`, `__pycache__/`, `.*` except `.` / `..` as walk artifacts. Punch through only via `!` in a file baseline stanza. |
| Advanced | `A` | off | **A name for the `# --- ADVANCED` stanza text in the ignore files.** Not a second list at compile time. |
| User files | `U` | on if files exist | `~/.fzdignore` then `~/.fzfignore` then `--ignore-file`. Each file splits on `# --- ADVANCED` into `file.baseline` (before) and `file.advanced` (after). |

If `~/.fzdignore` is missing, write it **once** with this default template, then compile from the file (never from the template in parallel):

```
node_modules/
venv/
.venv/
__pycache__/
.*

# --- ADVANCED
Templates/
Videos/
Desktop/
Music/
Pictures/
Documents/
Downloads/
Public/
```

After that write, **the file is the only Advanced source.** Deleting `Documents/` from the stanza unhides `Documents/`. There is no hardcoded basename matcher and no compile-time injection of those eight names.

### C3.1 Compile order (last-match-wins)

One compile string. After the missing-file write (if any), parse each U file into `(file.baseline, file.advanced)` at `# --- ADVANCED` (advanced empty if the marker is absent).

```
I = B + Σ file.baseline + (Σ file.advanced if profile=advanced else ∅)
```

- `B` is prepended every walk (always-on). Identical lines in `file.baseline` are redundant; `!node_modules` in `file.baseline` still last-match-wins through `B`.
- **Do not** concatenate a constant Advanced list. `A` is `Σ file.advanced`, nothing else. The formula is **not** `B + file.baseline + (A + file.advanced)`.
- Profile `baseline`: `file.advanced` is not compiled (off-by-default).

`!` is ordinary gitignore last-match-wins. `!node_modules` in `file.baseline` **can** punch through `B`. This is one matcher, not “union of sets that ignore `!`.”

### C3.2 Root-guard `R` (pre-walk predicate, not a set subtracted from `I`)

For each **raw pattern line** in the compiled text (after stripping `!` for this test, comments, blanks):

1. Let `P` be the pattern with trailing `/` removed.
2. If `P`, treated as an **absolute host path** (POSIX `/…` or Windows `X:/…`), equals `root` **or is a parent of `root`** → the line is an `R` hit. Parent means: `root` is `P` plus one or more extra path components (`/home` is parent of `/home/dev`; `C:/Users` is parent of `C:/Users/foo`).
3. Else the line is **not** `R`. If `P` starts with `/` but is not abs-equal/parent of `root`, it is gitignore-**anchored to `root`**: it matches `<root>/<P without leading slash>`, never the root itself, and **never** via prefix-match against absolute host strings.
4. **Never** prefix-match an ignore pattern against an absolute host string as a “starts with” hide. That is the SPN `/home/dev` defect.

`R` decision:

```
R_hits = { pattern lines that step 2 marks }
if R_hits nonempty and not allow_root_ignore:
    emit ignore-hid-tree (pattern = first hit); do not walk
if R_hits nonempty and allow_root_ignore:
    strip those lines from the compiled gitignore
    record correction (in-picker --header)
I = remaining compiled gitignore
C_walk = { d | d is a descendant directory of root, lstat says dir or symlink-to-dir,
           d does not match I }
# --root itself is not in C_walk
C = C_walk ∪ (staged_dirs if or_staged else ∅)
```

`--allow-root-ignore` **strips** the hide-everything rule so the tree is visible, and the pick surface **must** show the `ignore-hid-tree` banner via `--header`. It does not apply the pattern and then return an empty tree.

### C3.3 Worked fixtures (root-guard)

Assume Unix host. Matcher must produce these classes.

| Pattern line | `--root` | Flag | Result |
|---|---|---|---|
| `/home/dev` | `/home/dev` | no | `ignore-hid-tree` (abs equals root). **No walk.** |
| `/home/dev` | `/home/dev` | `--allow-root-ignore` | Strip pattern; walk; `--header` `ignore-hid-tree`; tree visible |
| `/home/dev` | `/home/dev/src` | no | `ignore-hid-tree` (`/home/dev` is **parent** of root) |
| `/home` | `/home/dev` | no | `ignore-hid-tree` (parent) |
| `/home/dev` | `/home/justadev` | no | Not `R`. Anchored child match only: hides `<root>/home/dev` i.e. `/home/justadev/home/dev`. Whole tree remains. |
| `home/dev` (no leading `/`) | `/home/dev` | no | Not `R`. Child/component match only. Root not hidden. |
| `/home/dev/` | `/home/dev` | no | Same as `/home/dev` (`R`) |

Windows analogue: pattern `C:/Users/bardw` + root `C:/Users/bardw` → `ignore-hid-tree`. Pattern `C:/Users` + root `C:/Users/bardw` → `R` (parent). Pattern `/Users/bardw` on a Windows root `C:/Users/bardw` is **not** abs-equal (missing drive); treat as gitignore-anchored to root (child `Users/bardw` under `C:/Users/bardw`), not `R`.

Advanced-stanza fixtures (PR3 must assert):

| `profile` | `# --- ADVANCED` stanza | Result for a dir named `Documents` under root |
|---|---|---|
| `advanced` | omits `Documents/` (user deleted it) | **visible** (not in `I`) |
| `advanced` | includes `Documents/` (default template) | hidden |
| `baseline` | includes `Documents/` | **visible** (stanza not compiled) |

### C3.4 `staged_dirs`

`--or-staged`:

- Run `git diff --cached --name-only` inside `--root` (git `-C root`).
- If `--root` is not a git work tree → class `not-a-git-work-tree`, do not walk.
- For each staged path `p`: include `p` if it is a directory; include the **immediate parent** and **every ancestor** of `p` that is still inside `--root`, excluding `--root` itself.
- Union those dirs into `C` even if `I` would have hidden them.

Candidate-OR is the freeze (OQ15 closed 2026-09-18: operator confirmed). PR5 is later-sitting runtime, not gated on that confirm.

### C3.5 Match rules (gitignore subset)

- `#` comments. `# --- ADVANCED` starts the advanced stanza.
- Blank lines ignored.
- `!` un-ignores (last-match-wins, C3.1).
- Trailing `/` = directories only (redundant for FZD, legal).
- `*` `?` `**` allowed. `[]` character classes: Open Question 7.
- `B` names match a **path component** (`venv/` hides `…/venv/` not `…/prevent/`).

### C3.6 Directories, symlinks, junctions

- Enumerate with **`lstat`**, not `stat`. Do not follow.
- Include a symlink-to-dir iff the **link itself** is the candidate (`lstat` is `S_IFLNK` and the target would be a dir — one `stat` of the target for classification is allowed; do not recurse through it).
- v1.0p Windows: **treat junctions as dirs, do not follow** (same as symlink).
- Cycles: do not follow; the link/junction itself may still appear once.

---

## C4 Keymap table (frozen)

Action names are the contract. **One fzf key per schema object.** `fm schema` `.keymap[]` is JSON `{chord, action, fzf}` where `chord` is a single fzf key token (`down`, `ctrl-n`, not `down / ctrl-n / ctrl-j`). PR2 validator **fails** if `chord` contains `/` or whitespace-separated alternatives.

Documented fzf-default **overrides**: `ctrl-a` (bol → toggle-advanced), `ctrl-d` (delete-char/eof → ignore), `ctrl-y` (yank → unignore). `ctrl-h` matches fzf. Require **fzf ≥ 0.53** (`FZF_TOTAL_COUNT` for C7 query-mismatch).

`fzf` empty or `(default)` → C7.1 **does not emit** `--bind` for that row (printable typing and click-select are stock fzf).

| Chord | Action | fzf `--bind` RHS | Notes |
|---|---|---|---|
| printable | query insert | | not emitted |
| click | select row | | not emitted; keys remain active |
| `bspace` | delete char left | `backward-delete-char` | |
| `ctrl-h` | delete char left | `backward-delete-char` | **not** column-switch |
| `ctrl-w` | delete word left | `unix-word-rubout` | |
| `ctrl-u` | clear query line | `unix-line-discard` | |
| `ctrl-r` | clear query | `clear-query` | SPN |
| `home` | query bol | `beginning-of-line` | fzf `ctrl-a` moved off this |
| `end` | query eol | `end-of-line` | |
| `ctrl-a` | toggle advanced + reload | see appendix | SPN correction |
| `down` | next row | `down` | |
| `ctrl-n` | next row | `down` | |
| `ctrl-j` | next row | `down` | |
| `up` | prev row | `up` | |
| `ctrl-p` | prev row | `up` | |
| `ctrl-k` | prev row | `up` | |
| `pgdn` | page down | `page-down` | **not** `ctrl-d` |
| `pgup` | page up | `page-up` | |
| `enter` | accept | `accept` | prints selected record |
| `esc` | abort | `abort` | exit 130 |
| `ctrl-c` | abort | `abort` | |
| `ctrl-g` | abort | `abort` | |
| `ctrl-q` | abort | `abort` | |
| `ctrl-x` | ignore highlighted | see appendix | append to `~/.fzdignore` |
| `ctrl-y` | unignore last | see appendix | **overrides** fzf yank |
| `ctrl-d` | identity no-op | `ignore` | **overrides** fzf delete-char |
| `ctrl-f` | refuse files profile | `transform-header(fm-internal banner files-profile-not-fzd)` | no-op on the list |
| `ctrl-l` | redraw | `clear-screen` | **not** files column |

**Illegal:** Tk-only `e.state & 0x4`, binds that exist only on an Entry widget, two-column Left/Right as `Ctrl-h`/`Ctrl-l`, two actions on one chord, grouped chord cells.

### C4 appendix — custom `--bind` recipes

Pick starts with env: `FM_ROOT`, `FM_HOME`, `FM_PROFILE_FILE` (`$FM_HOME/profile`), `FM_SNAP` (`$FM_HOME/last-snapshot.paths`).

`fzf` is invoked `--read0` with stdin from the snapshot. Reload and header helpers are **Python `fm-internal`**, not POSIX `cat --`.

| argv | stdout |
|---|---|
| `fm-internal cat-snapshot` | raw bytes of `FM_SNAP` (NUL-separated paths) |
| `fm-internal toggle-advanced` | empty; toggles `FM_PROFILE_FILE` and runs `fm walk --refresh` |
| `fm-internal query-header {q}` | header line; see C7.1 |
| `fm-internal banner <class>` | C6 banner for that class |
| `fm-internal ignore-current` | empty; C4 `ctrl-x` steps |
| `fm-internal unignore-last` | empty; C4 `ctrl-y` steps |

**`ctrl-a`**

1. Read `FM_PROFILE_FILE` (`baseline` if missing).
2. Write the other value (`baseline` ↔ `advanced`).
3. Run `fm walk --root <FM_ROOT> --profile <new> --refresh`.
4. Reload via `fm-internal cat-snapshot`.

```
ctrl-a:execute-silent(fm-internal toggle-advanced)+reload(fm-internal cat-snapshot)
```

**`ctrl-x`**

1. Take fzf `{}` (current relative path, snapshot body form).
2. Build a gitignore-**anchored** line: `/` + relative path + `/`.
3. Run C3.2 `R` test against `FM_ROOT`. If it would `R`, **do not append**; `transform-header` `ignore-hid-tree`.
4. Else append the line to **`~/.fzdignore`** (not `~/.fzfignore`).
5. `fm walk --refresh` + `reload(fm-internal cat-snapshot)`.

```
ctrl-x:execute-silent(fm-internal ignore-current)+reload(fm-internal cat-snapshot)
```

**`ctrl-y`**

1. If `~/.fzdignore` last non-comment line was appended by `ctrl-x` this session (or is a `/rel/` line), delete that line.
2. Walk + `reload(fm-internal cat-snapshot)`.
3. Documented override of fzf `yank`.

```
ctrl-y:execute-silent(fm-internal unignore-last)+reload(fm-internal cat-snapshot)
```

**`ctrl-d`:** `ctrl-d:ignore`

**`ctrl-f`:** `ctrl-f:transform-header(fm-internal banner files-profile-not-fzd)` — does not insert files.

---

## C5 Pairing

1. `fm host start` creates `device-id` and `pairing-token` if missing (32 hex each, CSPRNG). Prints both to stdout once (`fm host pair-print` reprints). Writes `host.pid`.
2. If after mint the token file is empty or missing → **refuse to listen**. Includes loopback and Unix socket. There is no “local listen without a token.”
3. Client `--token-file` copies the **token** (secret). `device_id` is a **public** identity. Spoofing an approved id with a stolen token is full compromise; rotate-token is the recovery.
4. First message on the socket **must** be `PairHello` (C2.1). Anything else closes `unpaired`.
5. Host: constant-time token compare. Fail → `PairDenied class=bad-token` (dummy compare if file missing so timing does not leak presence — but listen already refused if empty, so this is defense in depth).
6. Token ok, device in `approved-devices` → `PairOk` + session. `WalkStart` must carry that session.
7. Token ok, device unknown → append `pending-devices`, `PairDenied class=pending-approval`. No session. No walk.
8. Operator `fm host approve <device-id>` is required **before** the first session. No auto-approve, no subnet allow, no `RegisterClient`.
9. `fm host rotate-token` rewrites the token file; existing clients fail `bad-token` until they recopy; approved device-ids remain (they still need the new token).
10. Default bind is **OS-specific**. Linux: `unix://$FM_HOME/host.sock`. Windows: loopback TCP `127.0.0.1:18733`. Override `--listen` / `listen` in config. A Windows client talking to a Linux host SSH-forwards the unix socket onto local TCP (`ssh -L 18733:$FM_HOME/host.sock`) and uses `--endpoint tcp://127.0.0.1:18733`. **Forbidden ports:** 3000, 5000, 3001, 5173, 8000.
11. **Non-loopback listen (PR10).** Default `listen.trust = refuse` → start error. Merge of PR10 requires **one** of: (a) TLS wrapping `PairHello` (amendment, not v1.0p runtime), or (b) operator sets `listen.trust = trusted-l2`, which **writes the accepted risk**: token is cleartext NDJSON on that L2. SSH-forwarded loopback is **not** LAN; it is loopback + SSH confidentiality; token-in-NDJSON is accepted there without `trusted-l2`.
12. No subnet connect-probe. No mDNS in v1.0p.
13. Local `fm walk` / `fm pick` without `--endpoint` **do not pair and do not listen**.

---

## C6 Error classes

Closed enum. One class, one meaning. JSON field `class`. Banner text is the `banner` column, not “no directories” unless class is `empty`.

**Picker channel:** `none` = stderr banner, **do not spawn fzf**. `header` = fzf `--header`. `transform-header` = fzf `transform-header` (query-time). Those two are the **only** in-picker banner channels.

| class | Emitter | When | Banner | Hit list | Picker |
|---|---|---|---|---|---|
| `empty` | snapshot | walk **complete**, denied=0, `C` empty | walk complete; zero directories after ignores | empty, honest | header |
| `partial` | snapshot | timeout and/or max-entries and/or max-depth and/or denied>0 | partial walk: denied=N seen=M entries_cap=… timeout=…; refresh to retry | whatever was seen | header |
| `permission` | walk | root unreadable | permission denied at root PATH | none | none |
| `cache` | snapshot | `--no-walk` or serving last snapshot file that exists | cached snapshot from TIME; not a live walk | cached paths | header |
| `cache-miss` | walk | `--no-walk` and no snapshot file | no snapshot; run walk | none | none |
| `disconnected` | pair / client | no host / SSH drop / `fm host stop` with nothing to stop | host disconnected; last snapshot not this walk | no fresh list | none |
| `failed-walk` | walk / framing | walker crash, IO after start, `WalkBodyEnd` sha mismatch, `byte_length` cap, framing desync | walk failed: DETAIL | **must not** say no directories | none |
| `unpaired` | pair | first message not PairHello; missing session on WalkStart; no token on a listen path | client unpaired; copy token and connect | none | none |
| `pending-approval` | pair | waiting `fm host approve` | device DEVICE waiting host approve | none | none |
| `bad-token` | pair | compare failed | pairing token rejected; rotate or recopy | none | none |
| `ignore-hid-tree` | walk | `R` tripped, no `--allow-root-ignore` | ignore pattern P would hide root PATH; refused | none | none |
| `ignore-hid-tree` | snapshot | `R` tripped, **with** `--allow-root-ignore` (stripped, tree visible) | ignore pattern P would have hidden root PATH; allowed | C after strip | header |
| `query-mismatch` | picker | query hits=0 but snapshot nonempty | query matched nothing in N dirs | snapshot still there | transform-header |
| `not-a-git-work-tree` | walk | `--or-staged` outside git | not a git work tree | none | none |
| `version-mismatch` | pair / framing | `v` ≠ `1.0p` | protocol version mismatch | none | none |
| `files-profile-not-fzd` | picker | `Ctrl-f` in v1.0p | files profile is not FZD; dirs only | unchanged | transform-header |
| `absent` | CLI | reserved command (`fm strikes`) | strikes enumerator is absent | none | none |

`denied>0` ⇒ class is `partial`, never `empty`, never `complete`. Two bounds firing stay `partial` with both counts in `detail`.

Never coerce `failed-walk` / `disconnected` / `permission` / `cache-miss` into `empty`.

---

## C7 UI-derivation rules (the generator)

v1.0p generator is **`fm schema` JSON → fzf argv**. Not a REST GUI. Not a Tk card. Not Glass.

### C7.1 Algorithm

```
schema = fm schema
walk_result = in-process walk OR C2 WalkSnapshot/WalkError

PRE_PICKER = {
  permission, failed-walk, disconnected, unpaired, pending-approval,
  bad-token, ignore-hid-tree,   # the refuse-to-walk flavor (picker=none)
  cache-miss, version-mismatch, not-a-git-work-tree, absent
}

if walk_result.class in PRE_PICKER:
    print C6 banner on stderr
    if --json: stdout {v,ok:false,class}
    exit 2
    # do not spawn fzf

argv = ["fzf", "--read0", "--print0", "--no-multi"]
for row in schema.keymap:
    if row.fzf in ("", None, "(default)"):
        continue                          # printable / click: stock fzf
    argv += ["--bind", row.chord + ":" + row.fzf]
    # row.chord is one fzf key. "down / ctrl-n" is illegal (PR2 fails).

setenv FM_SNAP_N = count of NUL paths in last-snapshot.paths   # N in the banner
setenv FM_HEADER = C6 banner for walk_result.class, or ""
if walk_result.class in {partial, cache, empty} or (ignore-hid-tree and allow_root_ignore):
    argv += ["--header", FM_HEADER]

# query-mismatch is inside fzf. {+n} is selected indices — do not use it.
# FZF_TOTAL_COUNT (fzf ≥ 0.53) is the filtered list length.
argv += ["--bind", "change:transform-header(fm-internal query-header {q})"]

spawn argv with stdin = last-snapshot.paths
```

`fm-internal query-header`:

```
# stdin unused. env: FM_SNAP_N, FM_HEADER, FZF_TOTAL_COUNT (from fzf), argv {q}
if int(FZF_TOTAL_COUNT or -1) == 0 and int(FM_SNAP_N) > 0:
    print("query matched nothing in %s dirs" % FM_SNAP_N)
else:
    print(FM_HEADER)   # restore walk-time header; transform-header replaces it
```

Boolean schema flags become CLI flags, not fzf widgets, in v1.0p (`--or-staged`, `--allow-root-ignore`). Enum `profile` is `--profile` plus `Ctrl-a`. Path `root` is `--root` plus `FM_ROOT`.

### C7.2 Worked examples

Schema `{"chord":"ctrl-h","fzf":"backward-delete-char"}` → `--bind=ctrl-h:backward-delete-char`.

Three next-row chords are three objects, three `--bind`s: `--bind=down:down --bind=ctrl-n:down --bind=ctrl-j:down`. A single chord `"down / ctrl-n / ctrl-j"` is a PR2 fail.

Walk-time: `fm pick --root /home/dev` with ignore line `/home/dev` → class `ignore-hid-tree`, stderr banner, exit 2, fzf not started.

In-picker `query-mismatch`: snapshot 3497 paths (`FM_SNAP_N=3497`), query `zzzz`, `FZF_TOTAL_COUNT=0` → `query matched nothing in 3497 dirs`. `{+n}` is not consulted.

### C7.3 Other rules

1. One view per command (`picker` | `status` | `host` | `plain`).
2. No second hand-built surface is required. A Tk card or dashboard that does not consume `fm schema` is out of contract.
3. User path without dashboards: must not start ports 3000/3001/5173.
4. Corrections only. Forbidden: praise, points, “nice!”, confetti, streaks.
5. `--json` live. Shape `{ "v":"1.0p", "ok": bool, "class": ... }`.
6. Accept stdout: native OS path. `--json` accept: `{v,ok,class,host,abs_dir}` with C9 encoding. Also write `last-handoff.json`.
7. Abort: no path, exit 130, no handoff rewrite, `--dry-run` never reaches fzf.
8. Shell cd: not v1.0p.

---

## C8 Handoff token (Scanner, not merge)

`~/.fuzzy-mirror/last-handoff.json`:

```json
{
  "v": "1.0p",
  "kind": "fuzzy-mirror-handoff",
  "host": {"os": "linux", "user": "dev", "hostname": "SPN"},
  "abs_dir": "/home/justadev/journal-clip",
  "walk_id": "…",
  "ts": "2026-09-18T00:00:00Z"
}
```

Windows example `abs_dir`: `"C:/Users/bardw/dev"`. Scanner may read this. Fuzzy Mirror does not spawn Scanner, AyTree, or Clippers.

---

## C9 Dual-host

- JSON `root` / `abs_dir`: UTF-8; convert `\` → `/`; **keep drive letters** (`C:/Users/foo`). No trailing slash except Unix `/` or Windows `C:/`.
- Snapshot body: paths **relative to root**, `/` separators, no drive letter, no leading `/` except the meaningless empty root case (which is not a hit anyway).
- Stdout accept (no `--json`): host-native separators (`C:\Users\foo` on Windows, `/home/dev` on POSIX).
- `host` object: `{ "os": "linux"|"windows"|"darwin", "user": "<string>", "hostname": "<string>" }`. Display form `user@hostname`. Windows user is the account name, not `user@hostname` guessed from `$USER`.
- Windows walker joins with OS APIs. The Unix-only `pre + "/"` test in `fzdow.py:246` is a defect if copied.
- Token and config dir: Unix `0700`/`0600`; Windows owner-only ACL.
- Client on Windows + host on Linux is a supported pair (SSH-forwarded loopback + PairHello).
- FZD live scripts on SPN (`~/.local/bin/fzd-*`) are **prior art**, not this binary. Exist-check on SPN at implementation time. Do not overwrite them from this contract.

---

## Open Questions

Closed (one-liners):

1. Host daemon language — **closed:** Python on PR3.
2. Linux listen default — **closed:** `unix://$FM_HOME/host.sock`. Windows stays `tcp://127.0.0.1:18733` (C5.10).
3. TLS on LAN — **closed as merge gate:** C5.11, TLS or `trusted-l2`, else refuse.
9. Windows walker if `fd` absent — **closed:** Python `os.walk` + `lstat`. `fd` may be a subprocess fast path.
15. `staged || profiling` — **closed:** operator confirmed 2026-09-18. Candidate-OR + baseline vs `# --- ADVANCED` stanza stands. PR5 is later-sitting runtime, not gated on that confirm.

Still open:

4. **Shared house token vs per-device token.** v1.0p is one host token + device allowlist. Per-device tokens would be an amendment.
5. **Snapshot invalidation.** v1.0p = explicit `--refresh` / `Ctrl-a`. No inotify.
6. **Symlink follow.** v1.0p = do not follow; list the link if it is a dir link. Confirm against SPN live at implementation.
7. **gitignore `[]` and nested `.gitignore` per subtree.** v1.0p = home-level `U` files only.
8. **`--or-staged` and untracked files.** v1.0p = `git diff --cached` only.
10. **Shell integration** (`cd` on accept). Named later.
11. **Rule-directory enumerator home.** `fm strikes` stays reserved print-only / class `absent`. Fuzzy Mirror still does not execute strikes. Constraint of the enumerator is a future `/constrain` skill, **not born this sitting** (ghost unless `/create-skill`).
12. **Port 18733 collision on SPN.** Check at implementation; `FM_ENDPOINT` is the escape. Linux host default is the unix socket, so this OQ is Windows-listen / SSH-forward TCP only.
13. **Ranking beyond fzf default.** Review proposals are not recovered decisions.
14. **Pairing UX: SSH-only vs token-LAN.** v1.0p prefers SSH forward; LAN is PR10 with C5.11. Tailscale-only is not required.
