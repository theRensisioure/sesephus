# Card Surface Prerelease v0

Status: DRAFT for the user to approve. Not frozen. Docs only. Nothing in this
file is built. Two spikes under `spikes/004-card-surface/` prove narrow parts.

Facts here come from three reader reports (journal-clip, Circadia, Clivor and Vej
test), two spike reports (zig-serve, zig-flip) and the spike folders, which the
integrator read directly. Anything not in them is marked unknown.

## 1. What this is and is not

This is one surface that shows four cards: journal-clip, Circadia, Clivor yes/no
and Vej testing. Each card has two faces. The surface is a prerelease written in
Zig.

The user's decision: all four cards get one surface in Sesephus. The whole thing
is summarised, then redesigned as a prerelease in Zig.

It is:

- A card surface. It shows cards and flips them.
- A small registry file that lists the cards and their runner kind.

It is not:

- Clippers. Capture stays external. The surface never records audio.
- Circadia. No alarm, no scheduler, no timekeeper.
- A database. The registry is one JSON file read at start. Ledgers are append-only files.
- A model router. It calls no model and picks none.
- Method Cards. See the collision note in section 4.
- The Clio labeling rig. That contract grades cluster summaries. Clivor asks
  yes/no questions about goal subgoals. They are different units.
- A host, a daemon, a sync system or a live watcher.

## 2. Summation table

One row per card. "Status" is what the card is in this surface at v0.

| Card | Job | Face 1 | Face 2 | Controls | Data file | Source of truth | Status |
|---|---|---|---|---|---|---|---|
| journal-clip | You speak. It keeps text. It destroys the wav. | this tower: record and plate a take | ledgar: tape list, five profile dots, refresh | Mouse ladder (left click 30/60/90/120 s, right click 7.5/15/22.5/30 min) and a flip button. No arrow keys found in its python files. | takes.jsonl in the vault folder .ssfs (external) | takes.jsonl, owned by the external app | pointer only |
| Circadia | A timekeeper. The scheduler exists; the product does not. | status: NOT DONE chip, one yes/no question | evidence: read-only rows of wired, stub, mock, design, plan, not built, open | Flip only. The mock writes nothing. | none | C:\dev\circadia\README.md and PREAMBLE.md | mock only |
| Clivor yes/no | One done/not-done question at a time, kept as a Vej training label. | yes-no: question, done-when line, cards left | ledger: read-only, grouped by day | Left = no, right = yes, up or down = flip, corner flip button | in: ~/.claude/work/clivor/cards/*.json. out: ~/.claude/work/clivor/labels.jsonl | labels.jsonl (absent when read) | runs here (target) |
| Vej testing | Read-only test bench: which set, which engine, right or wrong, sure but wrong. | scores (proposal) | sets: spent or fresh (proposal) | Flip only at v0 | none at v0 | data/fresh/ledger.json for set status; C:\dev\vej-lab\REPORT.md and C:\Users\bardw\durable\vej\spikes\VEJ-VS-JEV.md for results | mock only |

Notes on the table:

- Clivor "runs here" is the target. No spike ran the real Clivor files. Section 5
  says what is proven.
- Vej testing is "mock only" at v0 because the plan is unbuilt, has five views
  rather than two faces, and the harness saves no per-question rows. The two
  faces above are this document's proposal.
- Circadia faces are the reader's proposed card, not an existing screen.

### What each reader could not read or run

- journal-clip: read from `C:\Users\bardw\Desktop\journal-clip-streamlined\apps\journal-clip`,
  not from the path in CLAUDE.md. Whether they are the same app is unknown. The
  reader ran no code and no tests. Not read: clip_heavy.py, clip_contract.py,
  src/contract.zig, docs/CANON.md. Meaning of `kind`, `score`, `structured`,
  `extra` in the tape is unknown beyond types and defaults.
- Circadia: three design artifacts were read, all mocks. The recovered handoff
  document that the clause ids point to was not found. `C:\Users\bardw\dev\you\circadia-base-car.md`
  does not exist. Nothing was built or tested. INVENTORY.md says Circadia.jsx is
  795 lines; the file on disk is 736. `C:\dev\circadia` had uncommitted edits.
- Clivor: `clivor_card.py` was read, not run (its selftest writes labels). The
  real `labels.jsonl` does not exist yet, so its real rows have never been seen.
- Vej: nothing was run. The test UI plan is stale (it says all four sets are
  spent; the ledger holds five spent and two fresh). Its example numbers from
  `runs-compare.jsonl` and two spikes were not verified. No score exists for
  fresh-004 or fresh-005. Jev was never run.

## 3. Unified rules

The deck rules come from the Clivor card interface and the two spikes. The
reader report does not name them as a list, so this list is the integrator's
reading. The user should confirm it (section 7). The rules have names and no
numbers; the order does not matter.

- **Flip only.** Flip is the only way between faces. No tabs, no second window.
- **Read-only back.** Face 2 is read-only. It shows no decision control.
- **Arrows on the front.** Left and right decide on face 1 only. Left = no.
  Right = yes. They do nothing on face 2.
- **Append only.** Every answer is one appended line. Nothing is rewritten.
- **Ask once.** A card id already in the ledger is dropped from the deck.
- **Skip bad lines.** A ledger line that cannot be read (torn, not JSON, no
  string id, invalid UTF-8, too long) is skipped, counted and never rewritten.
  It never stops the deck from loading. Blank lines are skipped, and for a
  repeated id the first line wins. If the file does not end in a newline, the
  next appended line starts on its own line. A card whose id appears only on a
  skipped line stays in the deck and is asked again.

Arrows on the front, Append only and Ask once apply to a card that has
decisions. Cards with no decisions in v0 (journal-clip, Circadia, Vej testing)
treat left and right as inert.

Two agent rules from the Clivor skill stay: never pre-answer a card, and never
auto-yes a pass.

### The switch (new)

The header shows the card name. Choosing the name cycles to the next registered
card, in registry order. The new card always lands on face 1. The ledger of the
card being left is not changed by the switch.

This evolves an existing fence. The Clivor card interface says clicking the card
name is not built. No spike tested the switch.

### Conflicts found in the spikes

- Arrow direction. The zig-serve page binds ArrowLeft to yes and ArrowRight to
  no. The Clivor rule is left = no, right = yes. Zig-flip follows the Clivor
  rule. The serve page must be changed before it is used.
- Bad ledger lines. FIXED in zig-flip (tests pass, see section 5). `Deck.init`
  used to return an error on a malformed history line. It now skips the line,
  counts it in a public field and never fails except on out of memory.
  Zig-serve's loader also skips bad lines, but counts nothing, swallows out of
  memory and does not start an append on a new line after a torn tail.
- Ledger line shape. Three shapes existed: zig-serve `{id, label, t, ...}`, zig-flip
  `{id, text, answer, ts}` (its own choice), and the real Clivor row
  `{ts, card, id, question, answer, disk}` as reported. Only the last is real.
  Zig-flip's writer now emits the real row, with a golden-line test against
  Python `json.dumps`. Zig-serve was not changed and still writes the page's
  `{id, label, t}`. The real `labels.jsonl` has still never been read.
- Zig-flip dedupes by id within one deck. The real Clivor ledger holds rows from
  many cards. Whether an id is unique across cards is unknown.

## 4. Registry

The registry is a JSON file listing cards. The example is
`spikes/004-card-surface/cards.example.json`. It has an envelope with `schema`
and `cards`. Array order is switch order.

Fields of one entry:

| Field | Type | Meaning |
|---|---|---|
| `slug` | string | Stable short id. Never reused. |
| `label` | string | Name shown in the header. |
| `runner` | string | `native`, `pointer` or `mock`. See below. |
| `status` | string | `runs here`, `pointer only` or `mock only`. Matches the summation table. |
| `status_remark` | string | Why this status, and what is proven. |
| `job` | string | One sentence. |
| `faces` | object | `front` and `back`, each with `name` and `shows`. |
| `controls` | object | What left, right, up/down, the flip button and the header name do. |
| `data` | object | `reads` and `writes` lists. Pointer and mock cards write nothing. |
| `source_of_truth` | string | The one file or document that wins. |
| `pointer` | object | `paths`: where the real thing lives. |
| `proof` | array | Spikes that back this card. Empty if none. |
| `fences` | array | What this card must not do. |
| `unknowns` | array | What nobody has read or run. |

Runner kinds:

- `native`: runs inside this surface. Only Clivor yes/no at v0.
- `pointer`: shows a summary and a path to something external. It does not
  launch it, copy it or read its data at v0. journal-clip is this kind. The
  surface prints the path as a command the user can copy; it starts no process.
- `mock`: shows labelled status with no working behavior. Circadia and Vej
  testing at v0. A mock writes no file. A mock promotes to `native` only by a
  separate bounded task.

Collision note with Method Cards. A Method Card (`method-card-schema-v1.md`) is
a frozen record with `id`, `method_ref`, `change_prompt`, `aytree_directory`,
`prefabs`. A registry entry shares none of those names. It uses `slug` rather than
`id` and avoids `tags` and `notes`. A registry entry is not a Method Card, a
Method Card is not a registry entry, and neither file claims to be a database.
Do not rename either to Skill Warehouse.

## 5. Zig architecture

Zig 0.16.0, std only. One executable. Binds 127.0.0.1 only. One connection at a
time.

Intended pieces:

- Pure core: flip math (`flipWidthScale`, `flipSwapStep`, `portraitBox`) and one
  ledger-line renderer. No allocator, no Io.
- Deck: cards, append-only ledger, current face, the deck rules, and the counters
  of lines it skipped.
- Registry loader: reads the JSON file, builds the card list.
- Ledger file layer: read the whole file into the deck, then append one line plus
  newline per answer, with a newline first when the deck says the file did not
  end in one.
- HTTP layer: serve one page, one POST route per native card.
- One HTML page with inline script. No external requests.

### What spike 004b (zig-flip) proved. Verdict: VALIDATED.

- `zig build test --summary all` exited 0 with 44 of 44 tests passing (13 flip, 31 deck).
  It was 27 of 27 (13 flip, 14 deck) before the bad-line fix.
- The three `TestFlipMath` tests from `test_flip.py` ported one to one and pass.
- 186 values from the Python flip math matched the Zig port with 0 mismatches.
  One extra parsed line in the Zig dump was not chased down. This was not re-run
  after the deck change; `flip.zig` was not edited.
- Edge cases pass: arrow on face 2 changes nothing; repeated ids drop; a zero-size
  slot gives a 1x1 box; a line with quote, newline, backslash, tab and a control
  byte stays one physical line and parses back.
- Bad ledger lines, on in-memory input: a torn line in the middle, a torn final
  line with no newline (the next append is put on its own line), blank lines,
  CRLF, valid JSON with no id, non-objects, two objects glued on one line,
  repeated ids (first wins), a line over 1 MiB (a line of exactly 1 MiB is kept),
  invalid UTF-8 and out of memory all load without an error. Each skip is counted. The input bytes are unchanged.
- The written line matches Python `json.dumps` of the real Clivor row byte for
  byte on two golden lines.
- 5 of 5 effective mutations were caught on the earlier code. On the bad-line
  change, 10 mutations were tried: 9 were caught by the tests. One (swallowing
  out of memory in the parse) survived the first test, a second test was added,
  and it then failed; the explicit UTF-8 check was deleted because deleting it
  changed nothing.

Not proven by 004b:

- `TestFlipFaces` (tkinter) was not ported. The Python test file was never run.
- Deck and the flip state machine are not wired. Which face owns the arrows during
  an animated flip is open.
- No file I/O. The real `labels.jsonl` was not read. The deck tests are the
  spike's own reading of the card interface, not copies of Python tests. The
  torn-tail case is tested on an in-memory buffer, not on a file. A UTF-8 BOM at
  the start of a file, locking and fsync are not covered.
- Append-only is convention plus tests. Zig struct fields are public.
- Windows and Debug mode only.

### What spike 004a (zig-serve) proved. Verdict: VALIDATED.

- `zig build` compiled first try, std only. About 210 lines.
- GET / returned 200 with a 2043-byte page and 0 external URLs.
- A valid POST appended one line. Two POSTs appended two lines in order. A
  pretty-printed body became one line.
- Malformed JSON, a non-object, an empty body and a non-string id returned 400 and
  appended nothing.
- A body over 8 KiB returned 413, with Content-Length and with chunked encoding.
  Exactly 8192 bytes was accepted; 8194 was refused.
- A duplicate id returned 409 and appended nothing, also after a restart.
- After the server was killed, nothing listened on the port.

Not proven by 004a:

- No browser was opened. The page's arrow-key and flip script never ran. The
  page is half-evidenced.
- The first run failed: every append returned 500 (AccessDenied) until
  `.read = true` was added to the file open. The cause was not isolated. The
  spike's guess (length needs read rights) is unverified.
- The first run also refused a valid 8192-byte body. Fixed by reading limit + 1.
- Append is `length()` then a positional write. Single writer only. No locking.
- Not tested: concurrent clients, crash mid-write, a file with no trailing
  newline, CRLF, non-ASCII JSON, fsync, graceful shutdown.

### Not covered by either spike

- Loading and parsing the registry. Only a JSON syntax check was run on the example.
- Routing more than one card, and the switch.
- Serving ledger content to face 2. No spike has a read route.
- Reading Clivor input cards from `~/.claude/work/clivor/cards`.
- Reading any Vej or Circadia file.
- The flip animation. The flip math is Zig; a browser page would animate. Whether
  the page duplicates the math in script, or the server supplies it, is undecided.
- Unicode, Windows path edge cases, and a second writer such as the real Clivor
  Python card appending to the same `labels.jsonl`.

## 6. Prerelease boundary

v0 ships:

- One Zig executable on 127.0.0.1 and one page.
- The registry file with four entries and the switch.
- Clivor yes/no as the only native card: read input cards, answer with left and
  right, flip to the ledger, append one line per answer.
- journal-clip as a pointer card: job line, path, fence notes. No launch.
- Circadia and Vej testing as mock cards with labelled status and No data yet boxes.
- Tests: the flip and deck tests from 004b, adapted to the deck rules; the HTTP
  cases from 004a as a repeatable script. Labels in tests go to a temp folder.

v0 refuses:

- Launching, copying, vendoring or submoduling journal-clip, or recording audio.
- Reading or writing journal-clip's `takes.jsonl`.
- Any alarm, scheduler, timer or notification, and any claim that Circadia runs.
- Running any `vej` command, marking a set spent, scoring fresh-004 or fresh-005,
  or showing a Jev number.
- Any network except 127.0.0.1. No accounts, no auth.
- A database, a watcher, sync, a model call, a router.
- Writing anywhere from a mock card.
- Presenting the surface as Clippers, Circadia, Artifact Scanner, a warehouse
  or a Clio implementation.
- Keeping `zig-out` and `.zig-cache` in the repo.

## 7. Open questions for the user

1. Are the deck rules in section 3 the ones you meant? "Skip bad lines" is my
   addition to the rules the spikes first tested. It is now tested in zig-flip.
2. Browser page or native window? The only proven path is a local page served by
   Zig, and no browser has run it. Is a page acceptable?
3. Your Clivor skill says never put this runtime in `C:\dev\sesephus`. The surface
   decision seems to lift that. Do you lift it, and for which files?
4. Should the native Clivor runner write the real `~/.claude/work/clivor/labels.jsonl`,
   or a surface-owned file? A second writer (the Python card) has no locking.
5. Circadia scope: the phone and desktop concept, or the Windows-only 0.1 mood
   cue? They disagree about microphones and Android.
6. Vej testing: are the proposed two faces (scores, sets) right? The plan has
   five views. The plan also needs updating for the five spent and two fresh sets.
7. journal-clip path: CLAUDE.md names `C:\dev\journal-clippers\audio-journal-system`.
   The reader read a Desktop tree. Which is current? `docs/CANON.md` owns the pointer.
8. Should "pointer" ever launch the external app, or only show the path? v0 shows only.
9. May a pointer card read the external app's data file (read-only) on face 2?
   v0 does not.
10. The switch: click only, or a key too? No key is chosen.
11. Arrow direction for the page: confirm left = no, right = yes.
12. Which face owns the arrows during an animated flip: the old face, or none?
13. The real ledger row for Clivor: is an id unique across cards or only per card?
14. Should the registry stay a file in this repo, or live beside the card data?

## 8. Proposed CLAUDE.md wording

For the user to approve. CLAUDE.md is not edited by this task. Tags follow the
file's own style. The runtime is absent today, so the new lines say so.

Add a section after "Clio labeling rig":

```
## Card surface

- **[Known]** `docs/specs/card-surface-prerelease-v0.md` is a draft contract for one Zig surface that shows four two-face cards: journal-clip, Circadia, Clivor yes/no and Vej testing.
- **[Known]** Runner kinds are native (runs in the surface), pointer (shows an external path, never launches or copies it) and mock (labelled status only). journal-clip is pointer. Circadia and Vej testing are mock until a bounded task promotes them.
- **[Known]** The registry is a JSON file. It is not a Method Card, not a database and not Skill Warehouse.
- **[Absent]** No surface runtime is built. Spikes under `spikes/004-card-surface/` prove only the flip math, the deck rules and a local append-one-line server.
- **[Pointer-only]** Clivor yes/no data lives under `~/.claude/work/clivor`. Clivor's unit is a goal subgoal, not a cluster summary.
```

Change these existing lines:

- Voice boundary, last bullet: keep as is. Add: "A pointer card may show the external path. It does not launch it."
- Method Cards, last bullet: add "The card-surface registry does not copy it either."
- Clio labeling rig, last sentence of "Working rule": add "The Clivor native runner is authorized only by the card-surface contract, only as its v0 yes/no card, and not as a Clio labeling runtime."
- Boundaries, third bullet: keep. Circadia, Clippers and Clio stay on the do-not-present list.
- Working rule: add "The card surface is a separate return from documentation contracts, Clippers pointer repair and Circadia work."

Also needed outside CLAUDE.md, if you agree: the Clivor skill rule that keeps its runtime out of this repo.
