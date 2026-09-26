# Sesephus public-lineage working context

This is the public Sesephus lineage/reference repository. It is not the private daily Sesefus tree and not the supported capture product. Coverage-state definitions live at `C:\Users\bardw\jwrangle\you\architecture-context\COVERAGE.md`.

## Identity and ownership

- **[Known]** Public name: **Sesephus**. Repository identity: `theRensisioure/sesephus`.
- **[Pointer-only]** Canonical local checkout for this machine: `C:\dev\sesephus`; verify the active checkout with `git rev-parse --show-toplevel`.
- **[Pointer-only]** Read release state from Git tags and the current branch rather than duplicating a version string here.
- **[Known]** The Windows binary remains `sesefus.exe`; this does not rename the public repository.
- **[Known]** `docs/CANON.md`, `README.md`, and `AGENTS.md` govern public-lineage claims in this tree.

## Voice boundary

- **[Known]** Supported capture is external Clippers at `C:\dev\journal-clippers\audio-journal-system`.
- **[Pointer-only]** Older archival material may name retired Desktop Clippers paths; `docs/CANON.md` owns the current pointer.
- **[Known]** Treat `voice.bat` and `tools/voice.py` here as historical/reference code unless a specifically bounded task establishes otherwise.
- **[Known]** Do not recreate, vendor, submodule, or launch a replacement Clippers tree from this repository.

## Method Cards

- **[Known]** Method Card v1 lives at `docs/specs/method-card-schema-v1.md`, `docs/specs/method-card-boundary-v1.md`, and `docs/specs/method-card-examples-v1.json`.
- **[Known]** Method Cards are a frozen documentation schema: stable id, one tool-or-function reference, change prompt, manual AyTree directory representation, and optional prefabs.
- **[Known]** Method Cards are not a database, runtime, transport, live watcher, sync system, transcription system, alarm system, or model-capability router.
- **[Absent]** **Skill Warehouse** has no live product tree or runtime. Do not rename Method Cards to Skill Warehouse.
- **[Absent]** A retrieve/apply runtime for Method Cards has not been established.
- **[Known]** Do not copy the schema into private `C:\dev\sesefus` merely to make it appear shared.

## Audio PR review

- **[Known]** `docs/specs/audio-pr-review-contract-v1.md` is a frozen, docs-only contract for a future model-neutral review surface connected to an audio engine.
- **[Absent]** No GitHub adapter, model adapter, audio adapter, review ledger, or mutating review action is implemented by that contract.

## Boundaries

- **[Known]** Keep public Sesephus and private Sesefus as separate repositories with separate canonical prose.
- **[Known]** Preserve load-bearing `sesephus` tokens and historical records.
- **[Known]** Do not present this repository as Clippers, Artifact Scanner, Locality, Plan Atlas, Circadia, or a warehouse.
- **[Known]** AyTree remains an external sibling.

## Verification

- **[Known]** Read `AGENTS.md` for build and test gates; build Zig from `core\sesephus`.
- **[Pointer-only]** Do not infer current runtime behavior from a path or document mention alone.
- **[Unknown]** Git remote parity, live services, and historical Voice behavior require sitting-specific checks.

## Working rule

Keep documentation contracts, public release work, historical runtime inspection, and cross-product pointer repair as separate returns. Adding a Method Card example does not authorize building a methods database.
