# Sesefus · alarm daemon (draft)

**Not Circadia.** This is a Python dogfood stand-in. The Zig daemon is `core/sesephus/` and is **not done**. See that README.

**Product:** audio journal that **schedules** and **files** takes.  
**Capture:** BYO designated recorder (default: Microsoft Sound Recorder).  
**Hop:** cue page + designated recorder. Sound or picture may ride. Not a third app.  
**Not:** virtual mixer · in-house mic graph · Artifact Scanner host · the finished Zig Circadia · curation-retrieval.

## Surfaces

| Entry | Role |
|-------|------|
| `daemon.py` | Alarm poll / fire → cue page + **same** designated recorder as Record |
| `hop.py` | Fire one window now (`--fire morning`) · multimedia condition |
| `hop_to_array.py` | Cook take → text → stamp `hop.audio_text`. End of hop: rename inbox file to `sesefus · hop · <meaning>.m4a` |
| `record_launch.py` | CLI Record / dry-run resolve |
| `ui_serve.py` + `ui.html` | Compact UI: Record · probe/filter/designate · alarms · land inbox |
| `capture_config.py` | Config + filter/designate pure logic |
| `launcher.py` | Spawn designated app |
| `inbox.py` | Detect inbox takes → land into `~/test-write/journal` |
| `alarm_core.py` | Once-per-day due/fire |

## Quick start

```bat
cd C:\dev\sesefus\apps\journal-daemon
python record_launch.py --dry-run
python daemon.py --once --dry-run-launch
python daemon.py --force-due morning --dry-run-launch
python hop.py --fire morning --dry-run
python hop.py --fire morning
python hop.py --fire morning --show-page
python ui_serve.py
```

UI: `http://127.0.0.1:8777/` — rule-of-thirds hop. Center is Record.  
`hop-prefs.json` is live: `auto_land` + `auto_cook` must be on for a take to transcribe itself. The alarm daemon polls the inbox each tick. The UI status poll does the same if the window is open.

## Config

`capture-config.json` — designated command/inbox/glob + last probe rows.  
`hop-prefs.json` — `auto_land` / `auto_cook` (a new Sound Recorder m4a should plate itself).  
After cook, the inbox file is renamed to `sesefus · hop · <centroid>`. Centroid is a full tract probe of every clause (whisper segments + split), nearest to the whole take — not the first three words. `--mass` force-renames the whole inbox.

Default designated: Windows Sound Recorder → `%USERPROFILE%\Documents\Sound Recordings\*.m4a`.

## Tests

```bat
python -m unittest discover -s tests -v
```
