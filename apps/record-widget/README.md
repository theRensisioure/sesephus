# sesefus-record (C++)

Minimal **record widget daemon**. No alarms. No scanner host.

## How much speed?

**Human scale.** Ten Voice Recorder `.m4a` files hash in well under a second with Windows BCrypt. You do **not** need Zig micro-opts for this. What you need:

- **Full SHA-256** — identity + dedupe  
- **Prefix fractions** (`sha8` / `sha16` / `sha32`) — expedited lookup on submit / search without retyping 64 hex chars  
- **Active index written immediately** on ingest — status `active` as soon as hashed  

## Source of truth (audio)

`%USERPROFILE%\Documents\Sound Recordings\`  
(Windows Voice Recorder drops files here — e.g. `Recording (10).m4a`)

## Build

```bat
cd C:\dev\sesefus\apps\record-widget
build.bat
```

## Run

```bat
out\sesefus-record.exe          :: scan + serve widget http://127.0.0.1:8778/
out\sesefus-record.exe scan
out\sesefus-record.exe lookup ab12cd34
out\sesefus-record.exe status
```

Index file: `%LOCALAPPDATA%\SesefusRecord\active-index.txt`

## UI

Matrix film register: black void, phosphor green, mono, compact. Ingest Sound Recordings into **active**; lookup by sha prefix.


## Not this binary

Alarms → next. Transcription → parked. Suite/scanner host → no.
