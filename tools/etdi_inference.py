"""Emotion inference for voice memos: transcript + metadata -> structured JSON -> ETDI.

Locked system prompt and JSON schema; backend is Ollama (local-first, default)
or the xAI Grok API. Both are called over plain HTTP with schema-enforced
output, so the parse step is deterministic.

ETDI = sqrt(v^2 + a^2 + s^2) / (sqrt(3) * duration_minutes)

The Euclidean norm of the emotion vector, normalized so a one-minute memo
tops out at 1.0 — distance from neutral, per minute. Entries with unknown
duration are NOT scored (compute_etdi returns None) rather than silently
inflated through a duration floor.
"""
from __future__ import annotations

import json
import math
import os
import urllib.request

OLLAMA_URL = os.environ.get("SESEFUS_OLLAMA_URL", "http://localhost:11434/api/chat")
OLLAMA_MODEL = os.environ.get("SESEFUS_OLLAMA_MODEL", "qwen2.5:7b-instruct")
XAI_URL = os.environ.get("SESEFUS_XAI_URL", "https://api.x.ai/v1/chat/completions")
XAI_MODEL = os.environ.get("SESEFUS_XAI_MODEL", "grok-3-mini")

MIN_DURATION_MINUTES = 0.05  # 3s floor so micro-memos don't blow up the ratio
PAUSE_GAP_SECONDS = 0.5

SYSTEM_PROMPT = """You are a deterministic emotion inference engine for personal voice journaling and time-perception research.

Analyze ONLY the provided transcript and metadata. Infer the speaker's emotional state during the recording.

Output EXACTLY one valid JSON object matching the schema below. No other text, no explanations, no markdown.

Schema fields:
- valence: float, -1.0 to 1.0 (negative to positive emotional tone)
- arousal: float, 0.0 to 1.0 (low to high activation/energy)
- salience: float, 0.0 to 1.0 (how emotionally charged or personally significant this moment feels)
- primary_emotion: string (joy, sadness, anger, fear, anxiety, neutral, or short compound like "anxious_excitement")
- time_distortion_likelihood: float, 0.0 to 1.0 (how likely this emotional charge distorted perceived time)
- rationale: string, max 18 words
- confidence: float, 0.0 to 1.0

Rules:
- Be conservative on high salience and arousal.
- Use both semantic content and implied prosody from wording/pacing.
- If transcript is ambiguous or low-signal, lower salience and confidence."""

EMOTION_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "valence": {"type": "number", "minimum": -1.0, "maximum": 1.0},
        "arousal": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "salience": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "primary_emotion": {"type": "string"},
        "time_distortion_likelihood": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "rationale": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": [
        "valence", "arousal", "salience", "primary_emotion",
        "time_distortion_likelihood", "rationale", "confidence",
    ],
}


def audio_stats_from_segments(segments: list[dict], duration_seconds: float | None) -> dict:
    """Basic prosody proxies from Whisper segment timestamps."""
    word_count = 0
    pause_count = 0
    pause_total = 0.0
    prev_end = None
    last_end = 0.0
    for seg in segments or []:
        text = (seg.get("text") or "").strip()
        word_count += len(text.split())
        start = seg.get("start")
        end = seg.get("end")
        if start is not None and prev_end is not None and start - prev_end > PAUSE_GAP_SECONDS:
            pause_count += 1
            pause_total += start - prev_end
        if end is not None:
            prev_end = end
            last_end = max(last_end, end)
    duration = duration_seconds if duration_seconds else last_end
    wps = round(word_count / duration, 2) if duration else None
    return {
        "duration_seconds": round(duration, 2) if duration else None,
        "word_count": word_count,
        "words_per_second": wps,
        "pause_count": pause_count,
        "pause_total_seconds": round(pause_total, 2),
    }


def build_user_message(transcript: str, stats: dict) -> str:
    lines = [f"TRANSCRIPT: {transcript.strip()}"]
    if stats.get("duration_seconds") is not None:
        lines.append(f"DURATION_SECONDS: {stats['duration_seconds']}")
    if stats.get("words_per_second") is not None:
        lines.append(f"WORDS_PER_SECOND: {stats['words_per_second']}")
    if stats.get("pause_count") is not None:
        lines.append(f"PAUSE_COUNT: {stats['pause_count']}")
    if stats.get("pause_total_seconds") is not None:
        lines.append(f"PAUSE_TOTAL_SECONDS: {stats['pause_total_seconds']}")
    return "\n".join(lines)


def _post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 120) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _clamp(value, lo: float, hi: float, default: float = 0.0) -> float:
    try:
        return max(lo, min(hi, float(value)))
    except (TypeError, ValueError):
        return default


def validate_emotion(raw: dict) -> dict:
    return {
        "valence": _clamp(raw.get("valence"), -1.0, 1.0),
        "arousal": _clamp(raw.get("arousal"), 0.0, 1.0),
        "salience": _clamp(raw.get("salience"), 0.0, 1.0),
        "primary_emotion": str(raw.get("primary_emotion") or "neutral")[:40],
        "time_distortion_likelihood": _clamp(raw.get("time_distortion_likelihood"), 0.0, 1.0),
        "rationale": str(raw.get("rationale") or "")[:200],
        "confidence": _clamp(raw.get("confidence"), 0.0, 1.0),
    }


def infer_emotion(transcript: str, stats: dict, backend: str = "ollama", model: str | None = None) -> dict:
    """Run the locked prompt against the chosen backend; return validated emotion dict."""
    user_message = build_user_message(transcript, stats)
    if backend == "grok":
        api_key = os.environ.get("XAI_API_KEY")
        if not api_key:
            raise RuntimeError("XAI_API_KEY not set; required for --backend grok")
        payload = {
            "model": model or XAI_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "emotion", "schema": EMOTION_JSON_SCHEMA, "strict": True},
            },
            "temperature": 0,
        }
        data = _post_json(XAI_URL, payload, headers={"Authorization": f"Bearer {api_key}"})
        content = data["choices"][0]["message"]["content"]
    else:
        payload = {
            "model": model or OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            "format": EMOTION_JSON_SCHEMA,
            "stream": False,
            "options": {"temperature": 0},
        }
        data = _post_json(OLLAMA_URL, payload)
        content = data["message"]["content"]
    return validate_emotion(json.loads(content))


def compute_etdi(valence: float, arousal: float, salience: float, duration_seconds: float | None) -> float | None:
    """None when duration is unknown — an unscorable entry, not an inflated one."""
    if not duration_seconds or duration_seconds <= 0:
        return None
    duration_minutes = max(duration_seconds / 60.0, MIN_DURATION_MINUTES)
    magnitude = math.sqrt((valence * valence + arousal * arousal + salience * salience) / 3.0)
    return round(magnitude / duration_minutes, 4)
