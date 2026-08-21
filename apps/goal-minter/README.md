# goal-minter — what this is

A **small** Sesefus command. Not the host. Not Circadia. Not journal-clip.

You paste **messy objective text**. It mints a **house 3-Q goal packet** (spine · outcome · surface · fence · done when) and writes `intent/interview.md`.

No microphone. No extra HTTP port.

---

## Dry entry (no window)

Open **PowerShell**. One folder:

```bat
cd C:\Users\bardw\dev\sesefus\apps\goal-minter
```

```bat
Mint.bat --say "I want a launchable app that mints a goal packet. It should live at apps/goal-minter. Don't grow journal-clip." --out C:\Users\bardw\test-write
```

Stdout is the packet. The file is `--out`\intent\interview.md.

Blank or whitespace-only text fails closed (non-zero). No fake packet file.

`--text-file path.md` injects from disk instead of `--say`.

---

## Window

Double-click `Mint-ui.bat` (or `Mint.bat` with no args).

That window is **goal minting**, not journal transcription. Paste text. **mint packet**.

---

## What you are not doing

- Not `apps/journal-clip` (no mic, no wav, no Whisper).
- Not starting `sesefus.exe --role host`.
- Not opening the React dashboard.
- Not Artifact Scanner.
- Not a paid API. Heuristic mint; optional local 7B is not required.
