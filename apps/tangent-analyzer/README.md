# tangent-analyzer

A small Sesefus window that **looks like journal-clip** and **ranks leftovers**.

Paste is the corpus. Voice is the prompt (transcribed, then the wav is shredded). The lower plate is **tangent analysis**, not a transcription.

Not the host. Not Circadia. Not hop. Not clip. Not a journal take. No extra HTTP server.

---

## UI

Double-click `Ta-ui.bat`.

1. Folder row + **change**. Last folder in `%USERPROFILE%\.sesefus\ta-ui.json`.
2. Dropdown is WinMM capture devices. Default pick is the Maono USB mic if present.
3. **Record** clicks: 1=10s, 2=20s, 3=30s, 4=40s. Stop / send ends early.
4. Waveform while capturing. House **negentropic-blue**.
5. Paste the data first. Speak the lens. Whisper runs in-window. Analysis plates below.
6. Temp wav is shredded after transcription.

No dashboard. No extra server. Close the window to end the session.

---

## Dry entry (no mic)

```bat
cd C:\dev\sesefus\apps\tangent-analyzer
Ta.bat --prompt "rank Sesefus product leftovers, drop household" --paste-file paste.txt
```

Or:

```bat
..\..\venv\Scripts\python.exe python\ta_heavy.py --prompt "…" --paste "…"
```

Empty prompt or empty paste fails honestly. Prompt-only does not invent loops from the spoken/injected text.

---

## Tests

```bat
cd C:\dev\sesefus\apps\tangent-analyzer\python
..\..\..\venv\Scripts\python.exe -m unittest discover -s tests -v
```
