# Sesephus tester guide — retired capture path

This file records the former Sesephus 0.1.0 push-to-talk test surface. It is
historical documentation, not current launch guidance.

Do not use `voice.bat` or `tools/voice.py` as a supported recorder. Those files
remain unchanged in this lineage/reference repository so the public history is
inspectable, but the in-repo capture product is retired.

## Current Voice door

The sole supported Voice implementation is **Desktop Clippers**:

```text
C:\dev\journal-clippers\audio-journal-system
```

Desktop Clippers owns the microphone, capture, Whisper transcription, tape,
shredding, and cue projection. It is an external tree; Sesephus only records
the pointer and does not import, vendor, submodule, or launch it.

Artifact Scanner is optional post-capture tooling. It is not required to use
Clippers and is not part of this retired tester path.

## Historical disposition

- `voice.bat` and `tools/voice.py` are historical and unsupported.
- The six duplicate or stalled `apps/` surfaces were removed on the
  reconciliation review branch; their code remains available in Git history
  and the dated vault preserve.
- This repository remains useful for lineage, contracts, architecture, and
  reference builds. It is not a second Voice recorder.
