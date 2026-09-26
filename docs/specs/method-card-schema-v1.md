# Method Card Schema v1

This document freezes the first-pass contract for a methods database card.
It defines a durable record shape, not a runtime, sync protocol, or device
surface.

## Purpose

A method card is a reusable record that names a method, points at the tool or
function behind it, preserves the prompt used to change or refine it, and
stores an AyTree directory representation alongside the method data.

Manual prefabs are allowed to stand in for directory or workflow templates when
live state is not being modeled.

## Scope

In scope:

- Stable card identity
- Tool or function reference
- Change or refinement prompt
- AyTree directory representation
- Manual prefab references for prebuilt directory or workflow templates

Out of scope:

- Live filesystem watching
- Host/client messaging
- Android or Bluetooth transport
- Device pairing
- Encrypted update delivery
- Transcription behavior
- Alarm behavior
- Live state management of any kind

## Canonical record shape

Each method card is a JSON object with these fields:

The examples file wraps cards in a small illustrative collection envelope. That
envelope is not part of the card schema and does not claim a runtime store.

| Field | Required | Type | Contract |
|---|---:|---|---|
| `id` | Yes | string | Stable opaque card id. Never reuse an id for a different method card. |
| `method_ref` | Yes | object | Reference to the tool or function the card describes. |
| `change_prompt` | Yes | string | Prompt that would be used to change or refine the card. |
| `aytree_directory` | Yes | object | Manual AyTree directory representation stored with the card. |
| `prefabs` | Yes | array | Manual prefab references that can stand in for live directory or workflow state. |
| `title` | No | string | Human label for display only. |
| `tags` | No | array[string] | Optional index terms. |
| `notes` | No | string | Free-form remarks, if needed. |

### `method_ref`

The method reference is a small object with these fields:

| Field | Required | Type | Contract |
|---|---:|---|---|
| `type` | Yes | string | Either `tool` or `function`. |
| `name` | Yes | string | Human name for the tool or function. |
| `locator` | Yes | string | Exact reference used later by an implementation, such as a CLI token, module path, or function name. |

### `aytree_directory`

The AyTree directory representation is manual in v1:

| Field | Required | Type | Contract |
|---|---:|---|---|
| `mode` | Yes | string | Must be `manual` in v1. |
| `path` | Yes | string | Directory reference or equivalent durable pointer. |
| `snapshot` | Yes | string or array | Human-readable directory representation. This is descriptive, not watched state. |
| `notes` | No | string | Boundary notes about the directory representation. |

### `prefabs`

Each prefab reference should use this shape:

| Field | Required | Type | Contract |
|---|---:|---|---|
| `id` | Yes | string | Stable prefab id. |
| `label` | Yes | string | Short human label. |
| `path` | Yes | string | Path or durable reference to the prefab template. |
| `purpose` | Yes | string | What the prefab stands in for. |

## Validation rules

1. Card identity must be stable across edits.
2. The card must name exactly one method reference, either a tool or a function.
3. The change prompt must exist even when the card is otherwise frozen.
4. The AyTree directory representation must be stored with the card, not inferred
   from live filesystem watching.
5. Manual prefabs are allowed and may substitute for live directory state.
6. No field in this schema may require host/client transport, Android/Bluetooth
   pairing, device sync, transcription, or alarm execution.

## What this schema is not

- Not an executable database implementation
- Not a transport contract
- Not a live sync spec
- Not a device pairing design
- Not a runtime state machine
