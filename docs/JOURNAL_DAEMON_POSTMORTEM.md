# Why `Sesefus.lnk` sucked

**Date:** 2026-08-22
**Scope:** the Desktop shortcut `C:\Users\bardw\Desktop\Sesefus.lnk`, and the
app it launches, `apps/journal-daemon`.

## What the shortcut actually does

Resolved directly from the `.lnk`:

```
Target:  C:\Windows\system32\wscript.exe
Args:    "C:\dev\sesefus\apps\journal-daemon\Sesefus.vbs"
Start in: C:\dev\sesefus\apps\journal-daemon
```

It runs `Sesefus.vbs`, which silently launches `ui_host.py` under
`pythonw.exe` and opens a browser tab against it. `ui_host.py` +
`ui_serve.py` (161 + 507 lines) serve a local page at
`http://127.0.0.1:8777/`.

Note the path: `C:\dev\sesefus` (the retired private-tree identity), not
`C:\dev\sesephus` (this public lineage/reference repo — see
`docs/CANON.md` §1). The in-repo `apps/journal-daemon` removal is committed
on the reconciliation review branch and preserved in Git history plus the
dated vault package. The shortcut is retired as a supported door; its
physical removal remains gated to destructive reconciliation Phase 2.

## The complaint, verbatim

> too many demands for user interaction

## Why that's true, architecturally

`journal-daemon` is not one program, it's eight separate entry points a
user has to know about and move between:

| File | Job |
|---|---|
| `daemon.py` | poll for a due alarm, fire a cue |
| `hop.py` | fire one window manually |
| `hop_to_array.py` | cook a take into text after the fact |
| `record_launch.py` | resolve + launch the *designated external* recorder |
| `ui_serve.py` + `ui.html` | the compact UI — record / probe / filter / designate / alarms / land |
| `capture_config.py` | config + filter/designate logic |
| `launcher.py` | spawn the designated app |
| `inbox.py` | detect + land inbox takes |

Capture itself isn't even self-contained: per `schema.md`, recording means
launching a **separate, user-designated** app (default: Windows Sound
Recorder), then coming back to `journal-daemon` to "probe/filter/designate"
that other app's output, then a *third* manual step — `land` — to copy the
capture into durable-archive:

```
python %USERPROFILE%\artifact-scanner\scripts\durable_land.py land --src <capture-dir>
```

None of that is automatic. Every stage — fire the alarm, launch the outside
recorder, come back, designate/probe, land — is a decision the user has to
make and a command the user has to issue. Compare external Desktop Clippers,
its supported successor: one compact capture tree with numbered click-to-record
(1=30s/2=60s/3=90s/4=120s), transcribes in-window, done. journal-clip has no
external app to launch, no probe/designate step, and no separate land
command — the friction `journal-daemon` had is exactly what got cut. The
canonical tree is `C:\Users\bardw\Desktop\corection-goald\journal-clip`.

## Why the screenshot is the proof

The last screenshot (`Screenshot 2026-08-22 163628.png`) is a session graph
dominated by one repeating shape: a tall spine of items fanning out into
node after node labeled some variant of **"/prompts Command"** —
Deploying, Executing, Investigating, Transcribing, Analyzing,
Renaming — the same demand for a manual command, over and over, instead of
one action completing on its own. That's the same failure mode as the
eight-entry-point list above, just visualized: the system's default
response to "do the next thing" is *ask the user to issue another command*,
not *do it*. journal-daemon's UX and this session's own interaction shape
have the identical defect.

## Disposition

- `apps/journal-daemon` is retired from this repo. It remains recoverable
  through Git history and the dated vault preserve; revival requires a new
  named plan.
- `Sesefus.lnk` is retired as an operator door. It is not redirected to a
  second recorder under the old name; destructive Phase 2 removes it after
  the reconciliation gates pass.
- **Desktop Clippers** at
  `C:\Users\bardw\Desktop\corection-goald\journal-clip` is the sole supported
  Voice door.
- See [`docs/JOURNAL_CLIP_BOUNDARY.md`](JOURNAL_CLIP_BOUNDARY.md) §5 for how
  journal-daemon's land wiring relates to journal-clip's (still-missing)
  handoff.
