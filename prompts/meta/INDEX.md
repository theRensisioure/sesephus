# Context Load Index

Load **only** what the immediate task requires. See [agents/priorities.md](../agents/priorities.md) for the sharding rationale.

## Temperature Key

| Tier | When to load | Directory |
|------|--------------|-----------|
| **Hot** | Active coding, runtime wiring, prompt porting | `prompts/`, `architecture/hot-mvp-blueprint.md` |
| **Warm** | Database layer, embeddings, ingestion plumbing | `architecture/warm-data-ml.md`, `architecture/dual-source-sieve.md` |
| **Cold** | Onboarding, pipeline redesign, theory | `architecture/cold-ingestion-core.md` |
| **Agent** | Operator persona, speech parsing, engineering bootstrap | `agents/` |
| **Data** | Injected at runtime (anchors, profile bias) | `data/` |

---

## Task → Files

### Runtime inference (Hot)

| Task | Files |
|------|-------|
| Qualify forum/Bluesky post | `prompts/qualify-post.md` |
| Jetstream live sort | `prompts/jetstream-sort.md` → port to `prompts/qualify-post.md` Bluesky variant |
| General web lead search | `prompts/general-leads.md` + `data/skills-injection.md` |
| Gold buyers / Agent 3 | `prompts/gold-speculator.md` |
| Extract skills from profile | `prompts/skills-derive.md` |
| Jetstream profile alignment rollup | `prompts/jetstream-profile-align.md` + `architecture/dual-source-sieve.md` |

### Ingestion & triage (Warm)

| Task | Files |
|------|-------|
| CPU triage gates (0.55/0.78) | `architecture/dual-source-sieve.md` |
| Semantic instant-hit bypass | `data/symptom-library.json` |
| Jetstream backpressure theory | `architecture/cold-ingestion-core.md` |
| SQLite-vec + FTS5 hybrid search | `architecture/warm-data-ml.md`, `architecture/docs/hybrid-search.md` |
| SQLite tuning | `architecture/docs/sqlite-optimization.md` |
| Resilience / failure modes | `architecture/docs/resilience.md` |

### Implementation contracts (Hot)

| Task | Files |
|------|-------|
| gRPC daemon MVP | `architecture/hot-mvp-blueprint.md` |
| Docker + GPU passthrough | `architecture/hot-mvp-blueprint.md` |
| Wire prompts into server.ts | `meta/vllm-porting-notes.md` |

### Agent operator context

| Task | Files |
|------|-------|
| Onboard to LeadLogic | `agents/operator-guide.md` |
| Parse ambiguous user speech | `agents/pseudo-lora.md` |
| Engineering bootstrap / API layout | `agents/engineering-bootstrap.md` |
| Major architectural pivot | `agents/tactical-edits.md` + `agents/priorities.md` |
| User stack bias injection | `data/my_profile.md` + `data/skills-injection.md` |

---

## Anti-patterns

- Do **not** load `agents/pseudo-lora.md` when wiring a vLLM batch prompt.
- Do **not** load `architecture/cold-ingestion-core.md` when fixing a TypeScript triage bug.
- Do **not** inline prompts from memory — always read from `prompts/`.
- Do **not** treat `antigravity/LeadLogic-Engine/gemini.md` as canonical; this repo is.

---

## Legacy path map

| Old path | New path |
|----------|----------|
| `leadlogic/qualify-post.md` | `prompts/qualify-post.md` |
| `leadlogic/triage-architecture.md` | `architecture/dual-source-sieve.md` |
| `anchors/symptom-library.json` | `data/symptom-library.json` |
| `context/my_profile.md` | `data/my_profile.md` |
| `context/skills-injection.md` | `data/skills-injection.md` |
| `meta/gemini-agent-guide.md` | `agents/operator-guide.md` + `agents/pseudo-lora.md` |
| `meta/it-gemini.md` | `agents/engineering-bootstrap.md` |