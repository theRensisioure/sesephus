# Clip pipeline roles: clipper, archiver, schemer

**Status:** graduated → [`docs/JOURNAL_CLIP_BOUNDARY.md`](../docs/JOURNAL_CLIP_BOUNDARY.md)
**Date:** 2026-08-22
**Filed under:** [ideas/](README.md)

## One sentence

External Desktop Clippers only clips. Everything that happens to a take after it hands
off belongs to two separate roles, not one: the **archiver** (read) and the
**schemer** (edit).

## The split

- **Clipper** — the external Desktop tree at
  `C:\Users\bardw\Desktop\corection-goald\journal-clip`. Records,
  transcribes, writes the tape, shreds audio, and projects cues. Owns
  nothing once it hands off. Its job ends at the handoff, full stop.
- **Archiver** — owns the clip for *reading*, post-handoff. Two surfaces:
  - view a single note
  - mass-note functions (operate across many landed notes at once)
- **Schemer** — owns the clip for *editing*, post-handoff. Edits the archive
  itself, not the raw take.

Clipper, archiver, and schemer are three distinct owners. A clip crossing
the handoff stops being the clipper's concern; archiver and schemer both
pick it up from there, but for different jobs (read vs. write).

## Mapping to what already exists (needs confirming, not assumed)

- **Archiver** may use the optional `durable-archive` pair — the real
  `land()`/`status()`/`list_lands()` API is `durable_land.py`, external to
  this repo (`%USERPROFILE%\artifact-scanner\scripts\`). Artifact Scanner is
  not required by Voice. Retired `land_durable.py` was journal-daemon's thin
  local wrapper around it, plus `review.py`, which listed landed rows.
  Nothing today does mass-note operations across lands.
- **Schemer** looks like it could be external Clippers' own `Clip-edit.bat`
  (its README calls it "Transcription editor (separate
  goal)") — but that edits a take *before* it's archived. Whether schemer is
  that same editor pointed at landed archive notes, or a distinct component,
  is open.

## Open questions

- Is schemer = `Clip-edit.bat` extended to operate on durable-archive lands,
  or a new, separate tool?
- What concretely are "mass note functions" — bulk relabel, bulk export,
  bulk prune, something else?
- Where does the read/edit boundary actually live — one tool with two modes,
  or two separate scripts/binaries that never share code?

## Not this

- Not an implementation plan.
- Not a claim that `review.py` / `land_durable.py` / the external
  `durable_land.py` already *are* "the archiver" by that name — this file
  is proposing the name split, not documenting shipped behavior.
