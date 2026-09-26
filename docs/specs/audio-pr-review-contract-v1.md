# Audio-Connected Pull-Request Review Contract v1

This document freezes the intended boundary for a future open-source,
model-neutral pull-request review system connected to the planned audio
engine. It is a design contract, not an implementation claim.

## Purpose

The system shall provide a CodeRabbit-like pull-request review surface while
allowing the operator to choose the language model and inference location.
Review results shall be useful in two synchronized forms:

- durable review summaries and inline findings on the pull request; and
- conversational audio input and output through the audio engine.

The audio engine is an interface to review events. It is not itself the review
policy, model provider, or GitHub integration.

## Frozen principles

1. **Model neutrality.** The review layer must not require one model vendor.
   Providers may be hosted, local, self-hosted, or OpenAI-compatible. Provider
   selection belongs behind an adapter boundary.
2. **Human-controlled action.** A finding may be narrated, displayed, or
   queued without authorizing a code change, merge, dismissal, or approval.
   Mutating actions require an explicit operator decision and a separate
   authorization path.
3. **Structured findings.** The review engine produces structured findings
   before rendering them as GitHub comments, dashboard records, or speech.
   Renderers must not be the source of truth.
4. **Evidence before assertion.** A finding must identify the relevant pull
   request, changed file or diff region when available, category, severity,
   explanation, and confidence or uncertainty. A model's lack of context must
   be disclosed rather than silently converted into certainty.
5. **Asynchronous operation.** Short audio acknowledgements and long-running
   review jobs are separate paths. A queued review must be observable as
   queued, running, completed, failed, or cancelled.
6. **Repository contracts travel with the review.** Repository-local
   instructions, such as `AGENTS.md`, may inform review context. They must not
   be replaced by a generic prompt or treated as permission to change code.
7. **Product boundaries remain explicit.** This contract does not make
   Sesephus the supported Voice capture product, does not absorb Desktop
   Clippers, and does not vendor or launch the external Clippers tree.

## Conceptual flow

```text
pull-request event
    -> collect diff, changed files, CI state, and permitted repository context
    -> review orchestration
    -> selected model provider
    -> structured findings and review status
       -> GitHub summary and inline comments
       -> audio narration and spoken queries
       -> durable local review record
```

The flow describes ownership and sequencing only. It does not establish that
any of these adapters or runtimes currently exist.

## Review event minimum shape

The eventual implementation shall be able to represent, at minimum:

- `review_id` and pull-request identity;
- repository and source revision identifiers;
- review state: `queued`, `running`, `completed`, `failed`, or `cancelled`;
- finding identity and stable location where one exists;
- severity and category;
- concise summary and supporting explanation;
- confidence or an explicit uncertainty marker;
- source evidence or context boundary;
- operator disposition: `unreviewed`, `accepted`, `dismissed`, `deferred`,
  or `needs-human-decision`;
- model/provider metadata sufficient to explain which route produced the
  result, without storing secrets.

The exact serialization format is deferred to a separately versioned data
schema. This contract does not authorize inventing a JSONL, database, or API
format prematurely.

## Audio boundary

The audio engine may provide:

- speech-to-text for review questions and navigation commands;
- text-to-speech for summaries, findings, status, and completion notices;
- streaming acknowledgement and progress events;
- interruption, replay, and verbosity controls;
- a route from spoken input to an explicitly identified review operation.

The audio engine shall not infer approval, merge authority, dismissal, or code
execution from ambiguous speech. Commands with external or repository effects
must be confirmed through an explicit interaction appropriate to the action.

The system shall preserve the difference between:

- a transcript;
- an interpreted review question;
- a finding returned by the reviewer; and
- an authorized action.

## Model/provider boundary

The review orchestrator owns context assembly, review stages, retries,
timeouts, and structured-output validation. A provider adapter owns transport
and model-specific request details. The orchestrator must be able to route
different work to different models, for example:

- a fast model for changed-file summaries;
- a stronger reasoning model for architectural or security findings;
- a local model for sensitive source;
- a second model or deterministic tool for verification.

No model may be described as authoritative merely because it produced a
finding. Static analysis, tests, CI results, repository rules, and human review
remain distinct evidence sources.

## GitHub boundary

The future GitHub adapter may read pull-request metadata, diffs, changed
files, comments, review state, and CI results according to configured
permissions. It may publish summaries and inline findings.

It shall not automatically:

- merge a pull request;
- approve on behalf of the operator;
- push code changes;
- dismiss human review;
- expose secrets or private audio/journal material in a review comment.

Any future write action requires its own explicit contract and authorization
gate.

## Sesephus relationship

This contract is compatible with Sesephus as a public lineage/reference
repository, but it does not assert that the feature belongs in the current
runtime. A future implementation must decide separately whether the review
orchestrator, audio adapter, GitHub adapter, or review ledger lives in this
repository, an external sibling, or a new repository.

The current supported Voice boundary remains Desktop Clippers at
`C:\dev\journal-clippers\audio-journal-system`. The historical
`tools/voice.py` path remains historical and unsupported. Connecting a future
review system to an audio engine must not be represented as making either path
the supported PR-review implementation.

## Explicit non-goals for v1

- No GitHub App, webhook, or GitHub Action implementation
- No provider credentials or model default
- No requirement for Ollama, OpenRouter, OpenAI, Anthropic, or another vendor
- No fixed audio device, speech model, transport, or latency target
- No automatic code editing, commit creation, approval, or merge
- No claim that the current Sesephus runtime exposes review events
- No migration of Desktop Clippers into this repository
- No public release of private audio, journal, raw-chat, or research-corpus data

## Future implementation gates

Before calling an implementation complete, it must separately demonstrate:

1. provider-adapter configuration with secrets kept out of logs and comments;
2. diff/context collection against a real pull request fixture or controlled
   test repository;
3. structured finding validation and deterministic rendering;
4. duplicate-safe comment updates after a pull request changes;
5. audio interruption, retry, timeout, and transcript/error behavior;
6. explicit authorization tests for every mutating action;
7. privacy review for source, audio, transcripts, prompts, and model telemetry;
8. repository-local compile, test, and integration evidence for each adapter.

Until those gates are met, this document is a contract for intent and
boundaries only, not evidence that the system is wired.
