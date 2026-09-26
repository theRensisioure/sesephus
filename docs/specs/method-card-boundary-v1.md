# Method Card Boundary v1

This note fixes the boundary for the methods database schema lock.

## Frozen contract

The method card model in `method-card-schema-v1.md` is a frozen data model.
It preserves identity, method references, prompts, AyTree directory intent, and
manual prefab references.

It does not define an implementation.

## Explicit non-goals

- No transport layer
- No device sync
- No Android or Bluetooth receiver
- No live state management
- No filesystem watcher
- No encrypted update delivery
- No transcription behavior
- No alarm behavior

## Operational boundary

The directory information in this schema is manual and durable. It is allowed to
describe structure and intent, but it is not required to mirror real-time
filesystem state.

If a later implementation wants live directory state, transport, or sync, that
work must be specified separately and versioned independently of this frozen
contract.

## Repository boundary

This repo remains the public Sesephus lineage/reference tree. The schema here
must not imply that the supported Voice capture path, device sync path, or
runtime implementation already exists in this checkout.
