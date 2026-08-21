# Journal daemon · data shape

## Capture
Default inbox: `%USERPROFILE%\test-write\journal\<stamp>\`
- **`audio.webm` / `audio.wav`** — the journal (required)
- `meta.json` — BA dimensions sidecar
- optional caption in `meta.note` — never a stand-in for audio

## meta.json
- audio, audio_bytes, mime, duration_sec
- activity, context
- mood, pleasure, mastery (0–10 or null)
- sampled_by: alarm | freeform
- alarm_id optional
- transcription: parked

## Alarm window (alarms.json)
- id, time (HH:MM local), label, prompt
- optional **sound** — file path; rides the hop if the file exists
- optional **picture** — file path; shown on the cue page if the file exists
Missing file is skipped (no fake media). Not a third app.

## Hop
On fire: write cue JSON + cue HTML, open the cue page, start sound if present, open the designated recorder.

## Land
`python %USERPROFILE%\artifact-scanner\scripts\durable_land.py land --src <capture-dir>`
Copies the stamp folder (audio + meta) into durable-archive.
