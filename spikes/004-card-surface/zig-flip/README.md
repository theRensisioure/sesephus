# Spike 004b: zig-flip

Question: given Zig 0.16 std only, can the flip and deck rules of the existing
two-face cards be expressed as pure Zig functions that pass tests copied from
the Python originals?

Zig: 0.16.0 (`zig version`). Std only, no dependencies, no build.zig.zon.
Run: `zig build test --summary all` from this folder.

## Files

- `build.zig` - one test step, two test modules (flip, deck).
- `src/flip.zig` - `flipWidthScale`, `flipSwapStep`, `portraitBox`, the
  constants (`FLIP_STEPS`, `FLIP_MS`, `PORTRAIT`), and a pure `Flip` state
  machine (the FlipFaces logic minus the tkinter widgets). 13 tests.
- `src/deck.zig` - `Deck` (cards, append-only ledger, current face, skip
  counters), `renderLine` (one ledger line as a JSON string into a caller
  buffer). 31 tests.
- `src/xdump.zig` + `xcheck.py` - cross-check harness, not part of the build
  (see "Checks beyond the tests").

## What was ported, and from where

Read-only sources (nothing copied into this repo, ported by hand):

- `clip_flip.py`: `flip_width_scale`, `flip_swap_step`, `portrait_box`,
  `FLIP_STEPS`, `FLIP_MS`, `PORTRAIT`, and the state transitions of
  `FlipFaces.flip/_tick/cancel`.
- `tests/test_flip.py`: `TestFlipMath` (3 tests) ported assertion by assertion.
  `TestFlipFaces` needs tkinter and a display, so it was NOT ported; the
  `Flip` state-machine tests stand in for its non-widget parts.
- `card-interface.md`: the deck rules (flip is the only way between faces; face
  2 is read-only; left/right on face 1 only; append-only answers; an answered id
  is dropped). No Python test exists for these, so the deck tests are written
  fresh from the rules. They are not copies of anything. The skip-bad-lines rule (a bad
  ledger line is skipped, never fatal) is from the card surface spec.

## The ledger line

`renderLine` writes the six keys of the real Clivor label row, in the order the
reader report gave for `append_label` in `clivor_card.py`:

`ts`, `card`, `id`, `question`, `answer`, `disk`

- `ts` is a string such as `2026-10-06T12:00:00`. The caller supplies it. It was
  an integer in the earlier version of this spike.
- `card` is `Card.slug`, default `clivor`. `disk` is `Card.disk`, default empty.
- Separators are `", "` and `": "` and non-ASCII is written as `\uXXXX` with
  lowercase hex and surrogate pairs, because that is what Python `json.dumps`
  does by default and the real card uses it.
- Proof: the test "golden lines" compares two lines byte for byte with the output
  of `python -I` running stdlib `json.dumps` on the same six keys (backslash,
  quote, 0x7f, 0x01, backspace, form feed, newline, tab, e-acute, a check mark
  and an astral emoji included). No journal-clip or Clivor code was run.
- Not proven: the real `labels.jsonl` does not exist, so no real row was read. The
  shape is the reader report's reading of the source.

What zig-serve (not edited) would also need to match this one shape:

- It writes whatever the page POSTs, re-serialised compactly:
  `{id, label, t}` today (page script, `main.zig` line 28). The real row needs
  `ts` (string, local time), `card`, `id`, `question`, `answer` (`yes` or `no`,
  not `label`) and `disk`, in that order, with `", "` and `": "` separators and
  `\u` escapes. Its `std.json.Stringify.valueAlloc(.., .{})` call gives none of that.
- It stamps nothing: `t` is the browser's `Date.now()` integer. The server would
  have to format a local-time string.
- `id` is optional in `postLabel`; a row without an id is accepted and can never
  be deduplicated. The deck skips such a row on read.
- `loadSeen` skips bad lines silently and counts nothing; it swallows
  `OutOfMemory` in `catch continue`; it accepts an empty id that `postLabel`
  refuses; it does not look at the final byte of the file, and `appendLine`
  writes at the end of the file without checking for a newline, so a torn tail
  glues to the next row (the case `needs_newline` covers here).
- The page binds ArrowLeft to yes and ArrowRight to no. That is the reverse of
  the deck and of the Clivor rule.

## Real output

`zig build test --summary all`, exit 0 (run after the last edit):

```
Build Summary: 5/5 steps succeeded; 44/44 tests passed
test success
+- run test 13 pass (13 total) 18ms MaxRSS:3M
|  +- compile test Debug native cached 40ms MaxRSS:18M
+- run test 31 pass (31 total) 17ms MaxRSS:6M
   +- compile test Debug native cached 40ms MaxRSS:18M
```

Per-test names for the deck (`zig test src/deck.zig`):

```
1/31 deck.test.left is no, right is yes, one appended line each...OK
2/31 deck.test.golden lines: byte for byte what Python json.dumps wrote for the real Clivor row...OK
3/31 deck.test.arrow on face 2 changes nothing...OK
4/31 deck.test.a card id already in the ledger is dropped from the deck...OK
5/31 deck.test.a repeated card id inside the input is dropped...OK
6/31 deck.test.an answered card is asked once: a rebuilt deck drops it...OK
7/31 deck.test.an empty deck answers nothing...OK
8/31 deck.test.ledger is append-only: earlier lines never change, line slices stay valid...OK
9/31 deck.test.an answer line with a quote and a newline in the card text parses back...OK
10/31 deck.test.the nasty line survives the full path: press, ledger, rebuild...OK
11/31 deck.test.non-ASCII text round-trips...OK
12/31 deck.test.a too-small buffer is an error and the deck is unchanged...OK
13/31 deck.test.a malformed history line in the middle is skipped, counted, and the rest loads...OK
14/31 deck.test.a history line with no id is skipped and counted, its card stays in the deck...OK
15/31 deck.test.valid JSON that is not an object is skipped and counted...OK
16/31 deck.test.two objects glued on one line (a merged append) is skipped and counted...OK
17/31 deck.test.a torn final line with no newline: skipped, counted, flagged, next append gets its own line...OK
18/31 deck.test.without the newline the next answer is glued to the torn line and lost...OK
19/31 deck.test.a final line that is whole but has no newline: kept, flagged, not torn...OK
20/31 deck.test.a file that ends in a newline needs none, and an empty file is empty...OK
21/31 deck.test.blank lines are skipped and counted apart from bad lines...OK
22/31 deck.test.CRLF lines load, and the kept line has no carriage return...OK
23/31 deck.test.duplicate ids: the first line wins, later ones are counted...OK
24/31 deck.test.a very long line of junk is skipped without parsing, a long valid line is kept...OK
25/31 deck.test.a valid row over the line cap is skipped, so its card would be asked again...OK
26/31 deck.test.non-UTF8 bytes: the line is skipped and counted, its id is not remembered...OK
27/31 deck.test.valid non-ASCII rows load, and U+2028 inside a row does not split it...OK
28/31 deck.test.reading history never changes the bytes it was given...OK
29/31 deck.test.out of memory while reading history is an error, never a skip, and leaks nothing...OK
30/31 deck.test.out of memory inside the parse of a bad line is not mistaken for a bad line...OK
31/31 deck.test.flip twice is a round trip and touches no data...OK
All 31 tests passed.
```

The flip module's 13 test names are unchanged from the earlier run (`zig test src/flip.zig`):

```
flip.test.flip scale is edge-on at midpoint...OK
flip.test.card box is portrait in any slot...OK
flip.test.the reference card is not trimmed...OK
flip.test.PORTRAIT is the same double as Python 4/5...OK
flip.test.wide slot gives 520 for height 650 (float product is exact)...OK
flip.test.zero-size slot gives a 1x1 box...OK
flip.test.negative slot gives a 1x1 box...OK
flip.test.scale curve over all 8 steps...OK
flip.test.scale clamps odd inputs like the Python...OK
flip.test.state machine: non-animated flip toggles at once...OK
flip.test.state machine: animated flip swaps at step 4 and ends at 1.0...OK
flip.test.state machine: a second flip during a flip is ignored...OK
flip.test.state machine: cancel leaves the face where the last swap put it...OK
All 13 tests passed.
```

`std.testing.allocator` is used throughout, so any leak would have failed a
test; none did.

## Bad ledger lines

`Deck.init` (lines already split) and `Deck.initFromBytes` (raw file bytes) never
fail on a bad line. The only error either returns is `error.OutOfMemory`. Every
skipped line is counted in a public field, so nothing is hidden:

| Case | What happens | Where it is counted |
|---|---|---|
| not JSON, torn, merged (two objects on one line), a non-object, an object with no string `id`, invalid UTF-8, or longer than `max_line_bytes` (1 MiB) | skipped, not in `ledger`, its id is not remembered | `bad_lines` |
| empty or only spaces and tabs (a lone CR counts as empty) | skipped | `blank_lines` |
| an id already seen | first line wins; later lines are not in `ledger` | `duplicate_ids` |
| final line has no newline | nothing is repaired; the flag tells the writer | `needs_newline`; also `torn_tail` when that last line was unreadable |

- `Deck` never touches the file. It has no file I/O. "Never rewrites" holds
  because the deck only reads a byte slice; a test checks that the slice is
  unchanged after a load.
- CRLF: LF is the only line break. Every trailing CR on a line is dropped (the code
  trims all of them; no test covers more than one), so a kept line in `ledger`
  has no CR.
- A line with two `id` keys is skipped as bad, because `std.json` rejects
  duplicate keys. Python `json.loads` would keep it with the last id.
- A card whose id sits only on a skipped line stays in the deck and is asked
  again. That includes a valid row over 1 MiB.
- `needs_newline`: the file layer, when it appends the first answer, writes a
  newline first, then the line, then a newline, then calls `newlineWritten()`.
  The test "a torn final line with no newline" does exactly that on an in-memory
  buffer, checks the old bytes are a prefix of the new bytes, and reads the
  result back. The test "without the newline the next answer is glued" shows
  what happens if the writer skips that step: one bad line, the new answer lost.
- `Deck.init` given already-split lines cannot know about a missing final
  newline, so `needs_newline` stays false there. Use `initFromBytes` for a file.
- The explicit UTF-8 check I first wrote was removed: `std.json` already rejects
  invalid UTF-8, and a mutation that deleted the check survived, so it was dead
  code. The test "non-UTF8 bytes" is what holds the behaviour.

### Where this departs from journal-clip, and why

Source for journal-clip's behaviour is the reader report (a static read of
`python/clip_store.py`, `src/store.zig` and `CONTRACT.md`). I did not re-read
journal-clip and ran none of it.

- Same: a bad line is skipped wherever it is, not only the last. Blank lines are
  skipped. No file is rewritten by the reader.
- Python keeps no count of skipped lines and the ledger face shows only the parsed
  rows. The deck counts every skip.
- Python raises on invalid UTF-8 (`UnicodeDecodeError` is not caught by its
  `except OSError`), so one bad byte loses the whole ledger view. The deck skips
  that line only.
- Python splits lines with `splitlines()`, so a U+2028, U+2029 or U+0085 inside
  a take splits it into unreadable pieces that are dropped, and the id can be
  reissued. The deck splits on LF only. A test holds this.
- Python does not repair a missing final newline, so the next take is glued to
  the torn tail and lost. Zig `store.zig` has the same gap. The deck flags it
  (`needs_newline`) so the writer repairs it by adding a newline, never by
  editing the old bytes.
- Python `update_text` rewrites the tape from parsed rows and so deletes every bad
  line for good. The deck has no rewrite at all; the ledger stays append-only.
- Python keeps all rows with a repeated id and its UI shows later ones with a
  suffix. The deck keeps the first and counts the rest. Nothing is lost on disk.
- Python skips a row whose `text` is empty and accepts a row without an id. The
  deck needs a string `id` and does not look at the question text.
- Clivor's `read_labels` (reader report) skips only JSON syntax errors and then
  indexes `r['id']`, `r['answer']`, `r['ts']` and `r['question']`. A row that is
  valid JSON but lacks one of those would raise in that Python UI. The deck keeps
  any row with a string `id`, so it keeps rows that the Python card would choke
  on. It does not check the other five keys.
- Python has no line-length cap. The deck skips lines over 1 MiB without parsing
  them, to bound memory.
- Not covered by the deck or tests: a UTF-8 BOM at the start of the file (the first
  line would be counted bad; not tested), fsync, any lock, a stale lock,
  concurrent writers, and a lock file left by a crash.

## Checks beyond the tests

Mutation check on the bad-line change (copies in a scratch folder, this folder
untouched). Each mutation was applied alone and `zig build test` was run:

- drop the CR trim: 2 tests failed (blank lines, CRLF)
- drop the duplicate-id check: 1 test failed
- never set `needs_newline`: 2 tests failed
- never set `torn_tail`: 2 tests failed
- count blank lines as bad: 2 tests failed
- turn the skip back into an error (the old behaviour): at least 4 tests failed (my script printed only the first 4 failures)
- keep duplicate lines in the ledger: 1 test failed
- remove the 1 MiB cap: 1 test failed
- stop escaping non-ASCII in the writer: 2 tests failed (golden and non-ASCII)
- let the parse swallow `OutOfMemory`: this SURVIVED the first OOM test (43 of 43
  passed). The failing allocator keeps failing at the chosen allocation (its
  index does not advance on a failure), so the swallowed failure was followed by
  a real `OutOfMemory` from a later allocation and hid it. A second test
  with a history that holds only a bad line and nothing after the parse was
  added; the same mutation then failed it (`SwallowedOutOfMemoryError`).
- remove the explicit UTF-8 check: survived, so the check was deleted (see above).

Earlier mutation check on the flip and deck rules (unchanged, run before this
change):

- remove the face check in `press`: "arrow on face 2 changes nothing" failed
- disable the duplicate/ledger-id drop: 4 deck tests failed
- remove the `max(1, ...)` on slot height: zero-size and negative box tests failed
- write card text without JSON escaping: quote/newline test and the full-path test failed
- change `flipSwapStep` to `+1`: 3 flip tests failed

A sixth mutation I tried then (`self.cursor += 0` in `flip`) was a no-op by my
mistake and proves nothing; it is not counted. That earlier run was on the
previous 14-test deck, not re-run on this one.

Cross-check against the Python (`xcheck.py`, `src/xdump.zig`): `xcheck.py`
reads `clip_flip.py` as text, runs only lines 28-63 (the constants and the
three functions) in memory with `python -B -I`, and prints 186 values: the
scale for 8 step counts x 11 step values, the swap step for 8 step counts, and
`portrait_box` for 9 widths x 10 heights (including negatives and zero).
`zig test src/xdump.zig` printed the same grid from the Zig port. Result:
0 mismatches over the 186 lines compared (floats compared numerically, boxes
as exact integers). The Zig dump had one extra parsed line that I did not
chase down. The Python test file itself was never run, because it imports
tkinter and `clip_look`. This cross-check was not re-run after the deck change;
`flip.zig` was not edited.

## Not covered

- Deck and the `Flip` state machine are not wired together. In the Python,
  `is_back` changes at the midpoint of the animation, so for the first half of
  a flip the old face still owns the arrows. `Deck.flip` here is instant.
- Deck allocates (ledger lines, id set), so it is deterministic but not
  allocation-free. Only `renderLine` and the flip math are strictly pure.
- No file I/O: the deck takes history bytes or lines and returns lines. Appending
  to a real `labels.jsonl` is not exercised, nor is reading one from disk. The
  torn-tail test uses an in-memory buffer.
- The deck does not produce the timestamp string; the caller does.
- Whether an id is unique across cards or per card (spec question 13) is open.
  The dedupe here is by id alone.
- `portraitBox` with a NaN or huge `ratio` would hit `@intFromFloat` checks.
  Not tested.
- Windows only (this machine). Debug mode only.

## Verdict: VALIDATED

Zig 0.16 std alone was enough: all 44 tests pass, and the flip math matched
the Python on every value compared. The bad-line change is proven by deck
tests on in-memory input only (the deck went from 14 tests to 31; two old tests
that asserted an error were replaced).

### What worked

- The three Python functions port to about 30 lines of Zig and match the
  Python on 186 compared values (including negative and zero slots).
- The three `TestFlipMath` tests port one to one and pass. `PORTRAIT` is
  bit-identical to Python 4/5 (0x3FE999999999999A, asserted).
- The deck rules are small, testable functions on a plain struct. The face rule
  is one early return in `press`; the dedupe rule is one hash-set lookup at
  `init`.
- `std.json.Stringify.encodeJsonString` with `.escape_unicode = true` into
  `std.Io.Writer.fixed(buf)` matched Python `json.dumps` byte for byte on the
  golden lines, and gives a clean `NoSpaceLeft` path for a caller buffer;
  `std.json.parseFromSlice` parses the line back, quote, newline and all.
- `errdefer` plus `testing.allocator` and `checkAllAllocationFailures` made
  partial-failure paths checkable.

### What didn't

- The tkinter test (`TestFlipFaces`) cannot be ported; only its state logic
  was.
- Deck and Flip are not integrated, so the mid-flip arrow question is open.
- The real `labels.jsonl` does not exist; the row shape rests on the reader
  report of `clivor_card.py`, plus a Python `json.dumps` run on the same keys.
- Deck tests are my own reading of `card-interface.md`, not copies of Python
  tests, because no Python tests for the deck rules exist.
- The first OOM test could not see a swallowed `OutOfMemory`, because the
  failing allocator keeps failing at the chosen allocation.

### Surprises

- Struct fields are always public in Zig, so "the ledger is append-only" is a
  convention plus tests, not something the type system enforces. Only an
  `opaque` handle (PACK section 3.15) would hide `ledger.items`.
- `{d}` prints the float 1.0 as `1`, not `1.0`, so cross-checking against
  Python's `repr` needed numeric comparison, not text comparison.
- Concatenating a function's `[]const u8` result with `++` fails in a test
  (`slice being concatenated must be comptime-known`); the test helper returns a
  pointer to a fixed-size array instead.

### Recommendation for the real build

- Keep flip math and `renderLine` as the pure core: no allocator, no `Io`.
- Hide the ledger behind an opaque handle or accessor functions so append-only
  is enforced, and test that the only mutator is `press`.
- Decide, and test, who owns arrows during an animated flip: either derive the
  face from `Flip.is_back` (Python behavior) or block arrows while
  `flipping`.
- Add the file layer last, taking an `io: std.Io`: read the whole file into
  `initFromBytes`, append one line plus newline per answer (a newline first when
  `needs_newline`), and test it against a temp folder only.
- Have zig-serve share this one line shape and the same skip-and-count reader
  (list above) before the two are joined.
