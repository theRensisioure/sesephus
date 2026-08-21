#!/usr/bin/env python3
"""Dry and live entry for tangent-analyzer.

Injected prompt + paste is the shipped dry path (no mic).
A wav, if present, is transcribed then shredded. Transcript becomes the prompt.
Never writes hop inbox or clip CSVs.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from ta_analyze import Analysis, analyze  # noqa: E402

OLLAMA = os.environ.get("SESEFUS_TA_OLLAMA", "http://127.0.0.1:11434").rstrip("/")


def shred_temp(path: Path) -> None:
    try:
        n = path.stat().st_size
        with open(path, "r+b") as f:
            f.write(b"\x00" * max(n, 0))
        path.unlink()
    except OSError:
        try:
            path.unlink()
        except OSError:
            pass


def transcribe_wav(wav_path: Path, whisper_model: str = "base") -> str:
    import whisper

    model = whisper.load_model(whisper_model)
    result = model.transcribe(str(wav_path))
    return str(result.get("text") or "").strip()


def run(
    *,
    prompt: str = "",
    paste: str = "",
    wav: Path | None = None,
    whisper_model: str = "base",
    transcribe: Callable[[Path], str] | None = None,
) -> dict[str, Any]:
    """Shipped entry: prompt+paste analysis. Wav optional; always shredded if given."""
    prompt_text = (prompt or "").strip()
    paste_text = (paste or "").strip()
    degraded: list[str] = []
    wav_path = Path(wav) if wav else None

    if wav_path is not None:
        try:
            if wav_path.is_file():
                try:
                    fn = transcribe or (lambda p: transcribe_wav(p, whisper_model))
                    spoken = fn(wav_path).strip()
                    if spoken:
                        prompt_text = spoken
                    else:
                        degraded.append("empty-transcript")
                except Exception as e:
                    degraded.append(f"transcribe:{e}")
        finally:
            if wav_path.is_file():
                shred_temp(wav_path)

    result: Analysis = analyze(prompt_text, paste_text, mouth="heuristic")
    out = result.as_dict()
    out["degraded"] = degraded
    out["wav_shredded"] = bool(wav_path is not None and not wav_path.is_file())
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="tangent-analyzer dry/live entry")
    ap.add_argument("--prompt", default="", help="injected voice-prompt text (dry)")
    ap.add_argument("--paste", default="", help="pasted corpus")
    ap.add_argument("--paste-file", type=Path, default=None)
    ap.add_argument("--wav", type=Path, default=None)
    ap.add_argument("--whisper-model", default="base")
    args = ap.parse_args(argv)

    paste = args.paste
    if args.paste_file is not None:
        paste = args.paste_file.read_text(encoding="utf-8")

    out = run(
        prompt=args.prompt,
        paste=paste,
        wav=args.wav,
        whisper_model=args.whisper_model,
    )
    print(json.dumps(out, ensure_ascii=False, indent=2))
    if out.get("ok") and out.get("analysis"):
        print("\n--- analysis ---\n", file=sys.stderr)
        print(out["analysis"], file=sys.stderr)
    return 0 if out.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
