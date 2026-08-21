"""Shared config loader: sesefus.config.json at the repo root.

De-personalizes the hardcoded paths (bardw, T:\\) so the alpha is shippable
to testers. Every consumer falls back to sane defaults when the file or a
key is absent — a fresh clone works with zero configuration.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = REPO_ROOT / "sesefus.config.json"

DEFAULTS = {
    # Where voice.py drops recordings and manifests
    "recordings_dir": str(REPO_ROOT / "aurgio" / "recordings"),
    "transcript_dir": str(REPO_ROOT / "aurgio" / "transcript"),
    # Extra folders ingress_memos.py / image_sieve.py should scan (absolute paths)
    "memo_roots": [],
    "screenshot_roots": [],
    # Gemini Takeout / chat-export folders for shredder/artifact_sieve.py
    "artifact_roots": [],
    # etdi.db location; null = platform default (see etdi_store.default_db_path)
    "etdi_db": None,
    # Inference
    "backend": "heuristic",  # heuristic | ollama | grok — heuristic needs no model
    "ollama_url": "http://localhost:11434/api/chat",
    "ollama_model": "qwen2.5:7b-instruct",
    "ollama_vision_model": "llama3.2-vision",
    "whisper_model": "base",
    # UI
    "dashboard_url": "http://localhost:5173",
    # AyTree (suite Version Control / derivation-map) — sibling checkout or absolute path.
    # Leave null to auto-discover ../AyTree or AYTREE_ROOT. Never a roster of projects.
    "aytree_root": None,
    "aytree_port": 8000,
}


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            user = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            for key, value in user.items():
                if value is not None or key == "etdi_db":
                    cfg[key] = value
        except (json.JSONDecodeError, OSError) as exc:
            print(f"[config] ignoring unreadable {CONFIG_PATH.name}: {exc}")
    return cfg


def write_default_config() -> Path:
    """Drop a commented starter config for testers (install.bat calls this)."""
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(json.dumps(DEFAULTS, indent=2) + "\n", encoding="utf-8")
    return CONFIG_PATH


if __name__ == "__main__":
    print(json.dumps(load_config(), indent=2))
