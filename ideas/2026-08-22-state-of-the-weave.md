# State of the Weave

**Status:** draft — idea only. Not a plan. Do not implement.
**Date:** 2026-08-22
**Filed under:** [ideas/](README.md)

## One sentence

Give continuous context a physical shape borrowed from tape overdubbing: a
**wave** is one take (one session's burst of work), **the commit for a wave**
is the print that seals it, and **the weave** is the master thread those
prints drape across — so the next session can punch in without re-listening
to the whole reel.

## The gap this is pointing at

Git history is *code state*, not *why*. Every new session — a new chat, a new
agent, a new sitting at the keyboard — starts context-cold and has to
re-derive intention from diffs, or from whatever a summarizer kept. The
groksights timeline already draws this after the fact (cyan = spine work kept,
rose = invalidated branches abandoned) but it's a read-only mirror. Nothing
today answers, *at the start of a session*, "which take am I on, what was the
last print, what's still hot from last time."

## The metaphor, mapped

| Sequencer term | Weave term | Meaning here |
|---|---|---|
| A take | **wave** | One bounded session of work — opens when the session starts, closes when it prints. |
| Punching in | opening a wave | Picking up mid-thread on an existing track, not starting a blank one. |
| Bouncing / printing the take | **the commit for a wave** | The single commit a session ends on, carrying a structured trailer: what continued from the prior wave, what's newly laid down, what's still open for the next wave. |
| The master tape | **the weave** | A thin, append-only ledger of wave prints — not git log, not the full journal, just "where the tape heads are." That thinness is the point: cheap to read, expensive to reconstruct without it. |
| A muted/bad take | invalidated wave | A session that crashed, went sideways, or got abandoned mid-take. It never prints, so it never joins the weave — same way groksights already colors abandoned branches rose instead of erasing them. |

## Why overdubbing and not just "better commit messages"

A commit message describes a diff. An overdub describes a *relationship to
the prior layer* — it only makes sense next to what's already on the tape.
The weave's unit is that relationship, not the diff: each wave's print should
say what it's continuing, not just what it changed.

## Open questions (deliberately unresolved)

- **Where does the ledger live?** Repo-local drapes context only within one
  repo. User-global (closer to how `dev-watcher` already tracks file lineage
  across all of `C:/dev`) drapes across every project at once. Unclear which
  is actually load-bearing versus just bigger.
- **Who prints?** An agent auto-closing a wave at end-of-session risks
  printing noise every time. A deliberate act (closer to how `git commit`
  itself is deliberate) risks never getting used. Needs a real forcing
  moment, not a guess.
- **Overlap risk.** This must describe *intent lineage*, not re-implement
  something that already exists:
  - `dev-watcher` already ledgers *where files moved*.
  - the groksights timeline already visualizes *spine vs. invalidated* after
    the fact.
  - `plans/YYYY-MM-DD-*.md` already carries structured intent for anything
    big enough to plan.
  The weave only earns its own file if none of those three actually cover
  "what should the next session know before it does anything."

## Not this

- Not a daemon. Not a new `apps/*` folder.
- Not a replacement for `dev-watcher` (file-location lineage), the groksights
  timeline (visualization), or external Desktop Clippers (voice capture).
- Not a rewrite of git history — the weave sits *beside* git, never inside it,
  and never replaces a commit.
- Not, yet, a schema. The table above is vocabulary, not a file format.

## Why this is filed in `ideas/` and not `plans/`

Because it hasn't been forced yet. `goal-minter`, `journal-clip`,
`journal-daemon`, `record-widget`, `skills-window`, and `tangent-analyzer`
all skipped this step
— each went straight from metaphor to `apps/` folder and stalled. This one
waits here until a specific cross-session pain moment demands the ledger
exist, at which point it graduates into a dated `plans/` file that names the
forcing moment directly.
