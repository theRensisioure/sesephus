# Sesefus 0.9.3 alpha — tester guide

Sesefus is a voice journal that notices when you're drifting — from your
sleep, your mood, your own baseline — before you do. You're testing the
first loop: **talk to it for sixty seconds a day for two weeks and tell us
where it's annoying.**

## Setup (Windows, ~5 minutes + downloads)

1. Install [Python 3.10+](https://www.python.org/downloads/) — check
   "Add python.exe to PATH" during install.
2. Download/clone this folder anywhere. If you use git/gh:
   ```bash
   gh repo clone Zychs/sesefus
   cd sesefus
   ```
3. Double-click **`install.bat`** (grabs dependencies + the Whisper
   speech-to-text model; the first run downloads ~1–2 GB). It also arms the
   git guards that block committing vault data or API keys.
4. Double-click **`voice.bat`**.
5. Press Enter, talk, press Enter again. That's the whole interface.

## How to use it

- **Long sentences are journal entries.** Speak your mind for 30–90
  seconds. It transcribes locally, scores the emotional density (ETDI),
  and files it.
- **Short phrases are commands** (5 words or fewer):
  - "status" — is everything running, how many memos are vaulted
  - "review last" — read back your last entry's score
  - "score" — re-score everything
  - "dashboard" — open the web dashboard (needs the dev servers; optional)
  - "goodbye" — stop

## What we want to hear from you

Where it's annoying. Where it misheard you. Whether the score ever felt
*right*. Anything that made you not want to open it on day three.

## Privacy — read this once

**Everything stays on your machine.** Recording, transcription, and
scoring all run locally; nothing is uploaded anywhere by default. Your
recordings live in `aurgio/recordings/`, transcripts and scores in
`aurgio/`. Delete those folders and the data is gone. The optional
cloud-scoring mode (`"backend": "grok"`) sends transcript text — never
audio — to the xAI API, and it is OFF unless you turn it on. By testing
you're agreeing to record your own voice on your own computer — nothing
more.

**If you ever enable cloud scoring:** keep your API key in an environment
variable (`XAI_API_KEY` / `ANTHROPIC_API_KEY`) only — never in
`sesefus.config.json`, and never type it inline on a command line (shell
history keeps it). The commit guard will block a key that slips into a file.

## Known rough edges (0.9.3)

- Terminal window, not a pretty app. The dashboard is optional and needs
  `npm`/`python` dev servers (`docs/ETDI.md` has the commands).
- Default scoring is a crude offline gauge (confidence pinned low). With
  Ollama + `qwen2.5:7b-instruct` installed it gets real inference —
  `install.bat` prints the two commands.
- Whisper's first transcription after launch is slow (model load).
