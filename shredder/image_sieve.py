#!/usr/bin/env python3
"""Image Sieve: abstract-notion comprehension of Windows screenshots.

A branch of sieve.py's DebrisChunk pipeline. Instead of shredding text files
into paragraphs, this shreds *screenshots* by asking a vision-capable model
to comprehend what's on screen -- the app/window context and the abstract
idea or task the screen represents, not a literal OCR transcript.

Each screenshot produces one DebrisChunk whose `content` is a natural
language synthesis (embeddable by the existing Forge / nomic-embed-text
pipeline) and whose `metadata` carries the full structured reading. Chunks
ship to the same ingest/debris_shards.jsonl that sieve.py writes to, so
utils/forge.py and docs/GUIDE_Vector_Engagement.md need no changes to pick
up screenshots alongside text and code shards.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
sys.path.insert(0, os.path.join(os.path.dirname(_here), "tools"))
from sieve import DebrisChunk  # reuse the exact chunk shape sieve.py ships
from sesefus_config import load_config

_cfg = load_config()

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}

def default_roots() -> list[Path]:
    configured = [Path(r) for r in _cfg.get("screenshot_roots", [])]
    if configured:
        return configured
    home = Path.home()
    return [
        home / "Pictures" / "Screenshots",
        home / "OneDrive" / "Pictures" / "Screenshots",
        home / "OneDrive" / "Desktop",
        home / "Desktop",
    ]

OLLAMA_URL = os.environ.get("SESEFUS_OLLAMA_URL", _cfg["ollama_url"])
OLLAMA_VISION_MODEL = os.environ.get("SESEFUS_OLLAMA_VISION_MODEL", _cfg["ollama_vision_model"])
XAI_URL = os.environ.get("SESEFUS_XAI_URL", "https://api.x.ai/v1/chat/completions")
XAI_VISION_MODEL = os.environ.get("SESEFUS_XAI_VISION_MODEL", "grok-2-vision-1212")

SYSTEM_PROMPT = """You are a deterministic screen-comprehension engine reading a single Windows screenshot for a personal knowledge archive.

Look past the literal pixels. Identify the app/window context, then infer the abstract notion, idea, or task the screen represents -- what the person was thinking about or working toward, not just what widgets are visible.

Output EXACTLY one valid JSON object matching the schema below. No other text, no markdown.

Schema fields:
- app_context: string, short (e.g. "VS Code editing a Zig file", "browser tab on a forum thread")
- visible_text_summary: string, max 40 words, gist of any on-screen text (not a transcript)
- abstract_notion: string, max 25 words, the underlying idea/task/concept the screen embodies
- concepts: array of 2-6 short lowercase tags
- synthesis: string, one paragraph (40-80 words), natural language combining the above for search/embedding
- confidence: float, 0.0 to 1.0

Rules:
- Be conservative: if the screen is ambiguous or mostly noise, lower confidence and keep abstract_notion generic.
- Do not invent specific numbers, names, or text you cannot actually read.
- synthesis must stand alone as a readable paragraph -- it is what gets embedded and searched later."""

SCREEN_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "app_context": {"type": "string"},
        "visible_text_summary": {"type": "string"},
        "abstract_notion": {"type": "string"},
        "concepts": {"type": "array", "items": {"type": "string"}},
        "synthesis": {"type": "string"},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": ["app_context", "visible_text_summary", "abstract_notion", "concepts", "synthesis", "confidence"],
}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 180) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _clamp01(value, default: float = 0.0) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def validate_reading(raw: dict) -> dict:
    concepts = raw.get("concepts")
    if not isinstance(concepts, list):
        concepts = []
    return {
        "app_context": str(raw.get("app_context") or "unknown")[:120],
        "visible_text_summary": str(raw.get("visible_text_summary") or "")[:400],
        "abstract_notion": str(raw.get("abstract_notion") or "")[:200],
        "concepts": [str(c)[:40] for c in concepts][:6],
        "synthesis": str(raw.get("synthesis") or "")[:900],
        "confidence": _clamp01(raw.get("confidence")),
    }


def stub_reading(path: Path) -> dict:
    """No-model smoke test: filename/size only, clearly zero-confidence."""
    return validate_reading({
        "app_context": "unknown (stub backend, no vision model called)",
        "visible_text_summary": "",
        "abstract_notion": f"unscored screenshot: {path.name}",
        "concepts": ["unscored"],
        "synthesis": (
            f"Screenshot {path.name} ({path.stat().st_size} bytes) was queued but not read "
            f"by a vision model -- run with --backend ollama or --backend grok for a real reading."
        ),
        "confidence": 0.0,
    })


def read_screenshot(path: Path, backend: str, model: str | None) -> dict:
    if backend == "stub":
        return stub_reading(path)

    image_b64 = base64.b64encode(path.read_bytes()).decode("ascii")

    if backend == "grok":
        api_key = os.environ.get("XAI_API_KEY")
        if not api_key:
            raise RuntimeError("XAI_API_KEY not set; required for --backend grok")
        ext = path.suffix.lstrip(".").lower()
        mime = "jpeg" if ext == "jpg" else ext
        payload = {
            "model": model or XAI_VISION_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": [
                    {"type": "text", "text": "Read this screenshot."},
                    {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{image_b64}"}},
                ]},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "screen_reading", "schema": SCREEN_JSON_SCHEMA, "strict": True},
            },
            "temperature": 0,
        }
        data = _post_json(XAI_URL, payload, headers={"Authorization": f"Bearer {api_key}"})
        content = data["choices"][0]["message"]["content"]
    else:
        payload = {
            "model": model or OLLAMA_VISION_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "Read this screenshot.", "images": [image_b64]},
            ],
            "format": SCREEN_JSON_SCHEMA,
            "stream": False,
            "options": {"temperature": 0},
        }
        data = _post_json(OLLAMA_URL, payload)
        content = data["message"]["content"]

    return validate_reading(json.loads(content))


class ImageSieve:
    def __init__(self, output_path: Path, state_path: Path, source_node: str = "VisionOxide"):
        self.output_path = output_path
        self.state_path = state_path
        self.source_node = source_node
        self.state = self._load_state()
        self.chunks: list[DebrisChunk] = []

    def _load_state(self) -> dict:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return {}
        return {}

    def _save_state(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def collect_images(self, roots: list[Path]) -> list[Path]:
        seen: set[str] = set()
        files: list[Path] = []
        for root in roots:
            if not root.exists():
                continue
            candidates = [root] if root.is_file() else sorted(root.rglob("*"))
            for path in candidates:
                if path.is_file() and path.suffix.lower() in IMAGE_EXT:
                    key = str(path.resolve())
                    if key not in seen:
                        seen.add(key)
                        files.append(path)
        return files

    def _append(self, chunk: DebrisChunk) -> None:
        """Ship immediately, forge.py-style: a crash never re-bills completed
        vision calls because every reading lands on disk (chunk + dedup state)
        the moment it finishes."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(chunk.to_dict()) + "\n")
        self._save_state()

    def shred_screenshot(self, path: Path, backend: str, model: str | None,
                          dry_run: bool = False, force: bool = False) -> DebrisChunk | None:
        image_hash = file_sha256(path)
        if not force and image_hash in self.state:
            return None  # already sieved this exact image; skip the (costly) vision call

        if dry_run:
            print(f"[dry-run] would read {path} via {backend}")
            return None

        reading = read_screenshot(path, backend, model)
        chunk = DebrisChunk(
            content=reading["synthesis"],
            source_node=self.source_node,
            source_path=str(path),
            file_type=path.suffix.lower(),
            metadata={
                "shred_method": "vision-abstract-notion",
                "backend": backend,
                "model": model or {"ollama": OLLAMA_VISION_MODEL, "grok": XAI_VISION_MODEL}.get(backend, "none"),
                "image_sha256": image_hash,
                "app_context": reading["app_context"],
                "visible_text_summary": reading["visible_text_summary"],
                "abstract_notion": reading["abstract_notion"],
                "concepts": reading["concepts"],
                "confidence": reading["confidence"],
            },
        )
        self.chunks.append(chunk)
        self.state[image_hash] = chunk.id
        self._append(chunk)
        return chunk


def main() -> int:
    parser = argparse.ArgumentParser(description="Sieve Windows screenshots into embeddable DebrisChunks")
    parser.add_argument("--root", action="append", default=[], help="screenshot file or directory (repeatable)")
    parser.add_argument("--backend", choices=("ollama", "grok", "stub"), default="ollama")
    parser.add_argument("--model", help="override vision model for the chosen backend")
    parser.add_argument("--output", type=Path,
                         default=Path(__file__).resolve().parent.parent / "ingest" / "debris_shards.jsonl")
    parser.add_argument("--state", type=Path,
                         default=Path(__file__).resolve().parent.parent / "ingest" / "image_sieve_state.json")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--force", action="store_true", help="re-read images already recorded in state")
    parser.add_argument("--dry-run", "-n", action="store_true")
    args = parser.parse_args()

    roots = [Path(r) for r in args.root] if args.root else default_roots()
    sieve = ImageSieve(args.output, args.state)
    images = sieve.collect_images(roots)
    if args.limit > 0:
        images = images[: args.limit]

    print(f"Found {len(images)} screenshot(s) across {len(roots)} root(s)")
    read_count = 0
    for path in images:
        try:
            chunk = sieve.shred_screenshot(path, args.backend, args.model, args.dry_run, args.force)
            if chunk is not None:
                read_count += 1
                print(f"[read] {path.name} -> {chunk.id[:12]} conf={chunk.metadata['confidence']}")
        except Exception as exc:  # noqa: BLE001 -- batch run reports per-file errors
            print(f"[error] {path}: {exc}")

    if not args.dry_run and read_count:
        print(f"Shipped {read_count} screenshot chunk(s) to {args.output}")
    print(f"Done. read={read_count} of {len(images)} dry_run={args.dry_run}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
