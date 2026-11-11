# Spike 004a: Zig 0.16 std-only card server

## Question

Given Zig 0.16 std only, when a program serves one HTML page on 127.0.0.1 and accepts
POST /label, does each posted JSON object land as exactly one appended line in a JSONL
file, with bad input refused?

Fences kept: no network except 127.0.0.1; journal-clip not touched; nothing outside this
folder written except a temp folder for labels; nothing git-added or committed.

## What was built

- `build.zig` - one executable, `card-serve`.
- `src/main.zig` - about 210 lines, `std` only (std.Io.net, std.http.Server, std.json).
- Env: `CARD_PORT` (default 8765), `CARD_LABELS` (default `.\labels.jsonl` in the cwd).
  Everything else is hardcoded.
- `GET /` returns an inline page (2043 bytes): a card with a front and back face, a Flip
  button, Yes/No buttons, Left/Right arrow keys post yes/no, Up/Down flip. Three hardcoded
  cards (c1..c3). No external requests.
- `POST /label`: body must be a JSON object, at most 8192 bytes, optional `id` must be a
  non-empty string. The object is re-serialized compactly and appended as one line
  ending in `\n`. A repeated `id` returns 409 and writes nothing. Known ids are reloaded
  from the file at startup.
- One connection at a time, every reply sends `connection: close`.

## What was run

```
cd C:\dev\sesephus\spikes\004-card-surface\zig-serve
zig build            # 0.16.0, exit 0, no output
bash <scratchpad>/run004a.sh     # starts card-serve.exe in the background, drives it with curl.exe
```

The driver script lived in the session scratchpad (not in this folder). It created a temp
folder with `mktemp -d` and pointed `CARD_LABELS` at `labels.jsonl` inside it. Nothing was
written to `~/.claude/work/clivor`. Temp folder for the final run:
`C:\Users\bardw\AppData\Local\Temp\tmp.0inyyvjoHm`.

### Real output, final run (trimmed only of the netstat TIME_WAIT noise)

```
listening on 127.0.0.1:8765 labels=C:\Users\bardw\AppData\Local\Temp\tmp.0inyyvjoHm\labels.jsonl known_ids=0

== (1) GET /
status=200 type=text/html; charset=utf-8 bytes=2043
ArrowLeft occurrences: 1
external URL occurrences: 0

== (2) POST valid JSON, lines before=0
{"ok":true}
 status=200
lines after=1
{"id":"c1","label":"yes"}

== (3) two POSTs in a row, lines before=1
{"ok":true}
 status=200
{"ok":true}
 status=200
lines after=3
{"id":"c1","label":"yes"}$
{"id":"c2","label":"no"}$
{"id":"c3","label":"yes"}$

== (3b) pretty-printed multi-line JSON body becomes one line
 status=200
lines after=4
{"id":"c4","label":"no"}

== (4) malformed JSON, lines before=4
malformed JSON                          status=400   (body: {"id":"bad", oops)
JSON must be an object                  status=400   (body: [1,2])
malformed JSON                          status=400   (empty body)
id must be a non-empty string           status=400   (body: {"id":5})
lines after=4

== (5) body over 8 KiB, lines before=4
big body bytes: 9021
body over 8 KiB   status=413
chunked, no content-length:
body over 8 KiB   status=413
lines after=4

== (5b) boundary
edge body bytes: 8192   -> status=200
edge+1 body bytes: 8194 -> status=413
lines after=5

== (6) duplicate id, lines before=5
duplicate card id   status=409
lines after=5

== other routes
GET /nope status=404
GET /label status=405

== restart: duplicates survive a restart
listening on 127.0.0.1:8765 ... known_ids=5
duplicate card id   status=409
lines after=5
```

Final file had 5 lines: c1, c2, c3, c4, edge (the 8192-byte one).

Stop check: server killed with `kill`; `taskkill /IM card-serve.exe` reported "process not
found" (already gone); afterwards `netstat -ano | grep ":8765 " | grep -c LISTENING`
printed `0` and `tasklist | grep -ci card-serve` printed `0`. Only TIME_WAIT rows from
closed curl connections remained. The restart in the middle of the run rebound 8765 while
those TIME_WAIT rows existed, so a rebind works.

### Run 1 (failed, kept for the record)

The first run, before the fixes below, showed:

- (1), (4), (5) passed; (2), (3), (3b), (6) returned `could not write` with `status=500`
  and the file stayed empty. Server log: `append failed: AccessDenied`.
- (5b) a valid body of exactly 8192 bytes returned 413.

Fixes: `createFile(..., .{ .truncate = false, .read = true })`, and read the body with
`.limited(max_body + 1)` then compare the length. I did not isolate which call raised
AccessDenied; I only observed that adding `.read = true` made it go away. My guess is that
`file.length()` needs read-attribute rights that a write-only Windows handle lacks. That
guess is not verified.

## What was not done

- No browser was opened. The page's key handling and flip logic were never executed; only
  its bytes were fetched. The "Left/Right post, Up/Down flip" behavior is untested.
- No concurrent-client test. The server handles one connection at a time.
- No crash-mid-write test and no check of a file that lacks a trailing newline.
- Not tested with Windows CRLF or non-ASCII JSON.
- The server was killed, not shut down gracefully, so the leak-check at exit never ran.

## Verdict: VALIDATED

### What worked
- `zig build` passed on the first compile with Zig 0.16.0, `std` only. No compiler errors
  to report.
- (1) GET / returned 200 with the page, 0 external URLs.
- (2) One valid POST appended exactly one line.
- (3) Two POSTs appended two lines in order (c2 then c3), each ending in `\n`.
- (4) Malformed JSON, non-object JSON, empty body and a non-string id all returned 400 and
  appended nothing.
- (5) A 9021-byte body returned 413 with Content-Length and with chunked encoding; nothing
  appended. Exactly 8192 bytes was accepted; 8194 was refused.
- (6) A duplicate id returned 409 and appended nothing, including after a restart.
- A pretty-printed multi-line body was stored as a single line.
- The port was not listening after the server was stopped.

### What didn't
- First run: every append failed with AccessDenied until `.read = true` was added to the
  file open. Off-by-one at the 8192 boundary until the limit was raised by one.
- The browser side (arrow keys, flip) was not exercised, so the page is only
  half-evidenced.

### Surprises
- `std.Io.Dir.CreateFileOptions` has no append flag. Append is done by `file.length()` then
  `writePositionalAll` at that offset. That is fine for a single writer and not safe for
  two writers.
- On Windows a write-only handle was not enough for `length()` (suspected, not isolated).
- `Reader.allocRemaining(.limited(n))` raised `StreamTooLong` at a body of exactly n bytes
  in my run, so the limit has to be n + 1 for an inclusive cap.
- `std.http.Server` did the request parsing, `Content-Length` and chunked decoding with
  no extra code, and `respond` with `.keep_alive = false` closed cleanly each time.

### Recommendation for the real build
- Zig std is enough for this surface. Keep the one-connection-at-a-time loop with
  `connection: close`; it avoids idle browser keep-alive connections blocking the server.
- Keep the 8 KiB cap, the object-only check, the compact re-serialization and the id
  dedupe; all four held up in the run.
- Before trusting it with real labels: run the page in an actual browser once, add a
  crash-mid-write and trailing-newline check, and decide whether fsync per append is
  wanted (not added here).
- Keep the single-writer assumption written down; there is no locking.
- `zig-out` and `.zig-cache` in this folder are build output and should not be kept.
