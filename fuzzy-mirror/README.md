# Fuzzy Mirror

v1.0p is the **contract**. There is no binary yet.

Windows public-lineage copy is `C:\dev\sesephus\fuzzy-mirror`. An SPN copy is for local-model review (phi). Do not overwrite live `fzd-*`. This sitting does not scp.

You will run a CLI named `fm`. The UI is derived from that CLI’s schema. The first paint is stock `fzf` argv, not a second hand-built dashboard. Pairing is Syncthing-shaped: a token file plus host **approve**. The job is isolated fuzzy-find.

## What it is not

Not `fuzzy-dow` (the Tk session-file keeper next door).

Not AyTree. Not Artifact Scanner. Not the sesefus alarm host:client (`RegisterClient`, ports 3000/5000). Not grok-launcher. Not Clippers.

Scanner may later read a handoff token (host + abs dir). Fuzzy Mirror does not launch Scanner.

## Two directory nouns

**FZD** (primary): filesystem directories only. Nested dirs. Never file titles. Query `notes` must not return `notes.txt`.

**Rule-directory** (later binder-consumer): a finite named set of **rule files**, not a filesystem browser. Same fzf wrap. Fuzzy Mirror **prints** a strike record. It does not execute it.

Do not collapse the nouns.

## How it runs (when a later sitting builds it)

**Local pick** (`fm pick` with no `--endpoint`): walk in-process. No listen socket. No pairing.

**Listen path** (`fm host start`): empty token **refuses to listen**, including loopback. First message must be `PairHello`. `WalkStart` needs a `PairOk` session. SSH-forward of loopback still pairs. It is not a skip.

The host walks once and ships a snapshot. The client filters locally. Keystrokes do not round-trip.

## Interface law

Corrections, not praise. Show ignore-hid-tree, failed walk, unpaired client, query mismatch. Do not toast “you did it.”

A failed scan must not say “no directories.”

User path completes without the three Sesephus dashboards.

## Forbidden ports

Do not bind **3000, 5000, 3001, 5173, or 8000**. Those are Fleet / AyTree / vLLM.

Linux default listen: `unix://$FM_HOME/host.sock`. Windows default listen: `127.0.0.1:18733`. A Windows client SSH-forwards the Linux unix socket onto local TCP (`ssh -L 18733:$FM_HOME/host.sock`).

## Docs

Normative contract: [CONTRACT.md](CONTRACT.md)

Approved design (full sitting): [DESIGN.md](DESIGN.md)

Schema fixture (machine-readable C1/C4/C6): [schema/v1.0p.json](schema/v1.0p.json)

This CHANGELOG: [CHANGELOG.md](CHANGELOG.md)

## Next sitting (implementation)

Start at **PR2**: schema fixture validator + `fm schema` that prints `schema/v1.0p.json`. Language freeze for first code is Python (PR3). Do not extend `core/sesephus`. Do not edit `fuzzy-dow`.
