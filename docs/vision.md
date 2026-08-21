> **Dated vision (2026-06).** Brand here is Sesephus (old name). Live tree: `C:\dev\sesefus`.
> This is direction, not a ship checklist. Circadia status: [../core/sesephus/README.md](../core/sesephus/README.md).

# Vision: Sovereign Personal AI & Alarm Ecosystem (Sesephus)

This vision document defines the architectural paradigm for **Sesephus**—a local-first, highly secure, and adaptive personal assistant. Sesephus integrates low-level daemon execution, secure cryptographic storage, and edge-native AI modeling to create a fully private, voice-tuned virtual companion.

---

## 1. Core Architectural Pillars

```mermaid
graph TD
    A["Voice Input (Microphone)"] ──► B["Zig Client (Native WaveIn Capture)"]
    B ──► C["Encrypted TCP Sync (ChaCha20-Poly1305)"]
    C ──► D["Zig Host (Encrypted Vault Database)"]
    D ──► E["Semantic Router Traffic Cop"]
    E ──►|Command / Status| F["Direct SQL Query (<100ms)"]
    E ──►|Voice / Text Query| G["On-Device Local AI Engine"]
    G ──►|Personalized Hearing| H["Custom Voice LoRA Adapter"]
    H ──►|Self-Healing Corrections| I["Client-Side Voice Fine-Tuning Loop"]
```

### 🕰️ Sovereign Edge Mesh
The system operates entirely offline, distributed across a personal mesh network:
* **The High-Compute Core**: Your desktop computer runs the database host daemon, handles continuous AI model quantization, and manages encrypted synchronization.
* **The Edge Clients**: Surface tablets, laptops, and mobile devices record journals and trigger alarms natively, utilizing secure TCP socket streams over private networks.
* **Open Source Foundations**: Built with pure Zig, Rust (Tauri), and Python with zero external cloud dependencies.

### 🎙️ Adaptive Voice LoRA Tuning (Trial-and-Error Personalization)
Standard Speech-to-Text models fail when encountering morning raspy voices, accents, or custom coding acronyms. Sesephus resolves this by training a personalized, lightweight voice adapter through on-device trial-and-error:
* **Correction Loop**: When the AI transcribes a voice log incorrectly, you edit the text directly in the dashboard UI.
* **Local Fine-Tuning**: A client-side training agent updates a low-rank (LoRA) adapter of rank $r=8$ (typically under 20MB) in seconds on your GPU/NPU.
* **Accented Recognition**: Future transcriptions are modified by this custom adapter, dynamically correcting the base model's hearing to match your voice.

### 🚦 Semantic Routing (The Traffic Cop)
Bypasses slow, expensive Large Language Model (LLM) calls for simple, structured tasks to keep execution latency under 100 milliseconds:
* **Predefined Routes**: Simple questions like *"What alarms are set?"* or *"Record for 5 seconds"* are routed directly to the database or system controllers.
* **Sovereignty Boundaries**: Privacy policies route PII (Personally Identifiable Information) queries strictly to local nodes, while escalations to secure cloud clusters are handled transparently.

---

## 2. Dynamic Hardware-Aware Execution

To prevent running heavy models from draining mobile batteries or causing thermal throttling, the runtime utilizes telemetry-driven mixed-precision:

### ⚙️ The Calmîc On-Device Controller
A closed-loop system that monitors battery level, GPU temperature, and request queues:
* **Low Battery / High Heat**: Automatically hot-swaps the active model to compressed INT4 or INT2 quantization weights.
* **AC Power / Cool Temps**: Instantly restores the model to high-fidelity INT8 or FP16 formats for max accuracy.

### 🎯 APreQEL Quantization
Rather than compressing all model layers uniformly, **APreQEL** calculates each layer's contribution to text generation (using cosine similarity of hidden layers). Critical layers are protected at high-precision (INT8), while redundant layers are compressed aggressively.

---

## 3. CONF-KV Memory Management

Managing the context window of local LLMs is critical for maintaining fast execution speeds. Sesephus deploys an adaptive key-value cache controller:

### 🧠 Step-Level Confidence Eviction
If the AI model is highly confident about its output words, **CONF-KV** prunes older, unimportant words from its active short-term memory cache. If it is uncertain, the budget expands to protect context.

### 🛡️ Bilateral Structural Protection
Standard compression algorithms lose track of the original system prompt or your last sentence. Sesephus locks down exactly 10% of the cache capacity at the beginning (prefix) and end (suffix) of the thread. This bilateral guard preserves model coherence and instructions.

---

## 4. Operational Pipeline Flow

1. **Scheduling**: The Zig [host.zig](file:///C:/Users/bardw/arcadium-circadia/core/sesephus/src/host.zig) schedules and triggers an alarm command.
2. **Recording**: The client captures native audio via Win32 waveIn and writes the WAV file to local memory.
3. **Piping**: The WAV file is streamed over TCP to the host, encrypted with **ChaCha20-Poly1305**, and saved to [sesephus_vault.db](file:///C:/Users/bardw/arcadium-circadia/core/sesephus/sesephus_vault.db).
4. **Transcription**: The local AI engine (Whisper.cpp) transcribes the recording using the personalized **Voice LoRA** adapter.
5. **Shredding & Ingesting**: The transcribed text is chunked using the Sieve shredder [sieve.py](file:///C:/Users/bardw/arcadium-circadia/shredder/sieve.py), tagged with semantic vectors, and stored in [ingest/debris_shards.jsonl](file:///C:/Users/bardw/arcadium-circadia/ingest/debris_shards.jsonl).
6. **Querying**: The Tauri dashboard UI sends user search queries through the **Semantic Router**, pulling the relevant journal facts instantly.
