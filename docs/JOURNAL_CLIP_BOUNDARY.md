# Journal-clip boundary — SSOT

> Single source of truth for where the external Desktop Clippers tree ends
> and who owns a take after that. The canonical implementation is
> `C:\Users\bardw\Desktop\corection-goald\journal-clip`; this repository
> records a pointer only. Ranks as a scoped sibling to `docs/CANON.md`, same
> arbitration rule.

## 1 · The three owners

| Owner | Job | Touches |
|---|---|---|
| **Clipper** | Voice | mic → capture → Whisper → tape → shred → cue projection. Ends at the Voice boundary. |
| **Archiver** | Read, post-handoff | view a single note; mass-note functions across many landed notes. |
| **Schemer** | Edit, post-handoff | edits the archive itself, not the raw take. |

A take crossing the handoff stops being the clipper's concern. Archiver and
schemer both pick it up after that line, for different jobs — read vs.
write. Nothing owns more than one of these three jobs.

## 2 · Clipper — external Desktop tree

Canonical path:

```text
C:\Users\bardw\Desktop\corection-goald\journal-clip
```

Owns: record → transcribe (Whisper, in-window) → append to `takes.jsonl` →
shred the wav → project cues. That's the whole Voice job. Nothing past the
Voice boundary is this Sesephus repository's to own.

The external tree's `clip_store.py` `append()`, `harvest()`, and `purge()`
remain capture-side. Sesephus does not import, vendor, submodule, or launch
that tree.

## 3 · Archiver — read, post-handoff

Owns two surfaces: viewing a single landed note, and mass-note functions
(operating across many landed notes at once).

The historical implementation was split across two places, not one file:

- The optional Artifact Scanner `durable_land.py` API lives outside this
  repo at `%USERPROFILE%\artifact-scanner\scripts\durable_land.py`. Voice
  does not require it; this repo does not version or control it.
- The retired `apps/journal-daemon/land_durable.py` — note the reversed
  filename — was a thin journal-specific wrapper. It imported the external
  `durable_land` module and called `durable_land.land(...)`; its local surface was
  `pending_stamps()` / `landed_sources()` / `land_one()` / `main()`, not
  `land()`/`status()`/`list_lands()` themselves.
- Retired `apps/journal-daemon/review.py` (`collect_rows()` / `format_row()` /
  `main()`) was the listing half — one row per landed item, closer to
  "list many" than strictly "single-note."

Neither is named "archiver" in code, and mass-note functions don't exist
yet anywhere. "Archiver" is not one component today — it is one external
module the repo depends on, plus one thin repo-local wrapper around it.

**Status: optional, partial, unnamed, and outside the Voice requirement.**
Treat "archiver" as a boundary name, not as a claim that Artifact Scanner
is required or that a current implementation lives here.

## 4 · Schemer — edit, post-handoff

Owns: editing the archive after a take has landed. Never the raw take
itself — once something is a take (pre-handoff), clipper's the only writer.

**External-tree drift (flagged, not fixed here):** `Clip-edit.bat` /
`clip_edit_ui.py` and `clip_store.update_text()` already edit
**journal-clip's own `takes.jsonl`** — that's editing *before* handoff, done
by the clipper itself. Per this boundary, that's the clipper doing
schemer's job on its own turf. This file does not resolve that; it names
the drift so nobody mistakes `Clip-edit.bat` for "the schemer."

## 5 · The handoff itself (currently missing)

No code in this repository moves a take from Clippers to an archiver. The
canonical external Clippers tree does not depend on Artifact Scanner. The
old `apps/journal-daemon` had optional landing wiring —
`record.py` printed a land hint that fed `land_durable.py` — but
the canonical external Clippers tree does not carry that dependency.

`apps/journal-daemon` and the embedded `apps/journal-clip` are committed
retirements on the reconciliation review branch. Their code remains
available through Git history and the dated vault preserve; neither is a
current app or a restoration target.

Until a handoff exists, **archiver and schemer are owners with nothing
crossing to them yet.** Building either further without first wiring the
handoff would repeat the shape that stalled the six surfaces retired from
`apps/` this session (see `ideas/README.md`).

## 6 · Stale spots (checklist)

- [ ] External `Clip-edit.bat` / `clip_edit_ui.py` edit the clipper's own tape
      directly — should become schemer's job once a handoff exists.
- [ ] No required handoff from external Clippers into Artifact Scanner;
      Artifact Scanner remains optional.
- [ ] "archiver" / "schemer" are not used as names anywhere in code; this
      file is the first place they're defined. Don't assume other docs
      already use them.
- [x] The duplicate in-repo `journal-daemon` and `journal-clip` surfaces are
      committed retirements, preserved in Git history and the vault package.

## Not this

- Not a plan to build the handoff, the mass-note functions, or a schemer
  tool. This is the boundary/identity declaration only — see
  [`ideas/2026-08-22-clip-pipeline-roles.md`](../ideas/2026-08-22-clip-pipeline-roles.md)
  for the draft this graduated from, and `plans/` for where the build
  itself would eventually get specced.
