# ideas — the unified graveyard/nursery

One place for concepts that are **not plans and not apps**. A `plans/` file is
ready to hand an implementer. An `ideas/` file is a napkin: it may die here,
or it may graduate into a `plans/YYYY-MM-DD-*.md` once something forces it to
get real. Nothing in this folder should be assumed to run.

## Why this exists now (2026-08-22)

Six app surfaces left `apps/` in the reconciliation: `goal-minter`,
`journal-clip`, `journal-daemon`, `record-widget`, `skills-window`, and
`tangent-analyzer`. Each started as exactly this kind of napkin idea, skipped
straight to `apps/`, and stalled without ever being pressure-tested on paper
first. This folder is the corrective: one unified spot to draft the idea
*before* it earns a folder under `apps/`, so the next stall is visible as an
unfinished `.md` here instead of a half-built app there.

This is not a restoration of those six surfaces' code as *apps* — the intent
is for their successors to get written down here first, not to just re-open
the old folders. The retirement is committed on the reconciliation review
branch. The old code remains available through Git history and the dated vault
preserve, but none of the six is a current app or a one-command restoration
target. Any revival requires its own named plan.

## Rules for anything filed here

- One idea, one file: `YYYY-MM-DD-slug.md`.
- Must open with a one-line **Status** (`draft` / `graduated → plans/...` /
  `dead — why`).
- Must have a **Not this** section — what the idea is deliberately not, so it
  doesn't quietly re-grow into another `apps/tangent-analyzer`.
- No code, no daemons, no new `apps/*` folder from anything filed here without
  first passing through `plans/`.

## Index

| File | Status |
|---|---|
| [2026-08-22-state-of-the-weave.md](2026-08-22-state-of-the-weave.md) | draft |
| [2026-08-22-clip-pipeline-roles.md](2026-08-22-clip-pipeline-roles.md) | graduated → [docs/JOURNAL_CLIP_BOUNDARY.md](../docs/JOURNAL_CLIP_BOUNDARY.md) |
