# Spike 004: card surface

Question: can the four cards (journal-clip, Circadia, Clivor yes/no, Vej testing)
share one surface in Sesephus, built as a prerelease in Zig 0.16 std only?

Docs only at this level. The two folders below are throwaway spikes. Nothing here
is a product. Nothing was git-added or committed. Spec: `docs/specs/card-surface-prerelease-v0.md`.

## Files

- `README.md` - this overview.
- `cards.example.json` - example registry, four entries. Checked for JSON syntax
  only; no loader exists.
- `zig-serve/` - spike 004a.
- `zig-flip/` - spike 004b.
- `look.html` - look prototype. Prefer a local server so `deck.json` loads; `file://` uses an embedded fallback. Not the Zig draft.
- `flip.js` - shared flip math (lockstep with `core/sesephus/src/anim/flip.zig`)
- `colors.css` - token accents
- `deck.json` - sample Clivor deck + four-card registry

## The two spike folders

### zig-serve (004a)

Question: does a std-only Zig program serve one page on 127.0.0.1 and turn each
POST /label into exactly one appended JSONL line, refusing bad input?

Verdict copied from `zig-serve/README.md`: **VALIDATED**.

- Compiled first try on Zig 0.16.0. About 210 lines.
- GET / gave 200 and 2043 bytes, no external URLs. One POST gave one line; two
  gave two in order.
- Malformed JSON, non-object, empty body and non-string id gave 400 and appended
  nothing. A body over 8 KiB gave 413 (Content-Length and chunked). 8192 bytes
  was accepted, 8194 refused. A duplicate id gave 409, also after a restart.
- Port closed after the server stopped.
- Did not work at first: appends failed with AccessDenied until `.read = true`
  was set (cause not isolated); an 8192-byte body was refused until the limit was
  raised by one.
- Not done: no browser was opened, so the page's keys and flip never ran. No
  concurrency, crash-mid-write, CRLF, non-ASCII or fsync checks. Single writer,
  no locking.
- Left in the folder: `zig-out/` build output. Its README says it should not be kept.

### zig-flip (004b)

Question: can the flip and deck rules of the existing two-face cards be pure Zig
functions that pass tests copied from the Python originals?

Verdict copied from `zig-flip/README.md`: **VALIDATED**.

- `zig build test --summary all` exited 0: 44 of 44 tests (13 flip, 31 deck).
  Before the bad-line fix it was 27 of 27 (13 flip, 14 deck).
- The three `TestFlipMath` tests ported and pass. 186 values matched the Python
  math with 0 mismatches (not re-run after the deck change). One extra Zig dump
  line was not chased down.
- `Deck.init` no longer fails on a bad ledger line. It skips it, counts it in a
  public field and never rewrites the file. Covered on in-memory input: torn
  middle and torn final line (with the next append put on its own line), blank
  lines, CRLF, valid JSON with no id, duplicate ids, a 1 MiB line, invalid UTF-8,
  out of memory.
- The deck writes the real Clivor row shape (`ts`, `card`, `id`, `question`,
  `answer`, `disk`), byte for byte equal to Python `json.dumps` on two golden lines.
- Mutation checks caught every change tried, except one that the first test
  missed (a swallowed out of memory) and a second test then caught.
- Did not do: `TestFlipFaces` (tkinter) not ported; the Python tests were never
  run; deck and flip are not wired together; no file I/O; the real `labels.jsonl`
  was not read. Deck tests are the spike's own reading of the card interface.

## Conflicts between the spikes and the rules

Found while reading the sources. Details in the spec, section 3.

- zig-serve's page binds ArrowLeft to yes and ArrowRight to no. The Clivor rule
  and zig-flip use left = no, right = yes.
- Fixed: zig-flip's `Deck.init` used to error on a malformed history line. It now
  skips and counts, as the card rule says. zig-serve's loader skips too but
  counts nothing and does not start an append on a new line after a torn tail.
- Three ledger line shapes existed across the spikes and the real Clivor row.
  zig-flip now writes the real one. zig-serve still writes `{id, label, t}`; what
  it needs is listed in `zig-flip/README.md`.

## Summation results

Three read-only reader passes summarised the cards. None built, ran or scored
anything. Their unreadable items are kept.

- journal-clip: two faces (this tower, ledgar). Job: speak, keep text, destroy the
  wav. Controls are a mouse ladder and a flip button; no arrow keys were found.
  Read from a Desktop tree, not the path CLAUDE.md names; same app unknown.
  Source not run. Several files not read (clip_heavy.py, clip_contract.py, contract.zig).
- Circadia: unfinished by its own README. The alarm scheduler exists inside the
  Sesefus host; the product does not. Three design artifacts are mocks. Two
  scopes conflict (phone and desktop concept versus the Windows-only 0.1 mood
  cue). The recovered handoff document and `circadia-base-car.md` were not found.
  Nothing was built or run.
- Clivor yes/no: two faces (yes-no, ledger). Left = no, right = yes, up or down
  flips. Answers append to `labels.jsonl`, which did not exist when read. Card
  source read, not run.
- Vej testing: a five-view test bench plan, nothing built. Plan is stale (it says
  all sets spent; the ledger holds five spent, two fresh). No score for fresh-004
  or fresh-005. Jev never run. Plan example numbers were not verified.

## Not answered by this spike

- Whether one surface works in a real browser or window.
- Whether the registry loads and the switch cycles cards.
- Whether face 2 can show a ledger read back from the server.
- Whether the Zig deck can write the real Clivor ledger beside the Python card.

Overall verdict for the whole question: none given. Each spike earned VALIDATED
for its own narrow question only.
