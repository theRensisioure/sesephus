#!/usr/bin/env python3
"""Multimedia hop — a condition on fire → designated recorder.

Sound or picture may ride. Not a third app. Not embed. Not curation-retrieval.
"""
from __future__ import annotations

import argparse
import html
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

from capture_config import expand_path

SpawnFn = Callable[[list[str]], Any]


def resolve_media(window: dict[str, Any]) -> dict[str, Any]:
    """Optional sound/picture on the window. Missing file = absent, not a lie."""
    sound_raw = str(window.get("sound") or "").strip()
    picture_raw = str(window.get("picture") or "").strip()
    sound = Path(expand_path(sound_raw)) if sound_raw else None
    picture = Path(expand_path(picture_raw)) if picture_raw else None
    sound_ok = bool(sound and sound.is_file())
    picture_ok = bool(picture and picture.is_file())
    return {
        "sound": str(sound) if sound_ok else "",
        "picture": str(picture) if picture_ok else "",
        "sound_asked": sound_raw,
        "picture_asked": picture_raw,
        "sound_missing": bool(sound_raw) and not sound_ok,
        "picture_missing": bool(picture_raw) and not picture_ok,
    }


def cue_page_html(window: dict[str, Any], media: dict[str, Any]) -> str:
    label = html.escape(str(window.get("label") or window.get("id") or "cue"))
    aid = html.escape(str(window.get("id") or ""))
    when = html.escape(str(window.get("time") or ""))
    prompt = html.escape(str(window.get("prompt") or ""))
    pic = media.get("picture") or ""
    img = ""
    if pic:
        img = f'<img src="{html.escape(Path(pic).as_uri())}" alt="">'
    prompt_block = f"<p class='prompt'>{prompt}</p>" if prompt else ""
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>cue · {label}</title>
<style>
  html, body {{ margin: 0; background: #050509; color: #e7e7f2;
    font: 16px/1.4 "Segoe UI", system-ui, sans-serif; }}
  main {{ max-width: 28rem; margin: 12vh auto; padding: 1.4rem; }}
  .k {{ color: #7cf7ff; letter-spacing: 0.12em; text-transform: uppercase;
    font: 700 11px/1 ui-monospace, Consolas, monospace; }}
  h1 {{ margin: 0.4rem 0 0.6rem; font-size: 1.4rem; }}
  .prompt {{ color: #a7a7bd; }}
  img {{ display: block; max-width: 100%; max-height: 42vh; margin: 1rem 0;
    border-radius: 10px; }}
  .next {{ color: #6c6c83; font-size: 0.9rem; }}
</style>
<main>
  <div class="k">cue · {when} · {aid}</div>
  <h1>{label}</h1>
  {prompt_block}
  {img}
  <p class="next">Sound Recorder is opening. Take. This is not a third app.</p>
</main>
</html>
"""


def write_cue_page(
    cue_dir: Path,
    window: dict[str, Any],
    *,
    stem: str,
    media: dict[str, Any] | None = None,
) -> Path:
    cue_dir.mkdir(parents=True, exist_ok=True)
    media = media if media is not None else resolve_media(window)
    path = cue_dir / f"{stem}.html"
    path.write_text(cue_page_html(window, media), encoding="utf-8")
    return path


def build_open_argv(target: str | Path) -> list[str]:
    s = str(target)
    if os.name == "nt":
        return ["cmd", "/c", "start", "", s]
    return ["xdg-open", s]


def ride_hop(
    window: dict[str, Any],
    *,
    page_path: Path,
    dry_run: bool = False,
    show_page: bool = False,
    spawn: SpawnFn | None = None,
    media: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Write-side hop. Default: do not open a browser. Sound rides if present."""
    media = media if media is not None else resolve_media(window)
    opened: list[str] = []
    result: dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "page": str(page_path),
        "sound": media.get("sound") or "",
        "picture": media.get("picture") or "",
        "sound_missing": bool(media.get("sound_missing")),
        "picture_missing": bool(media.get("picture_missing")),
        "show_page": show_page,
        "opened": opened,
    }
    if dry_run:
        return result

    def _default_spawn(argv: list[str]) -> None:
        kwargs: dict[str, Any] = {}
        if os.name == "nt":
            kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
        else:
            kwargs["start_new_session"] = True
        subprocess.Popen(argv, **kwargs)

    sp = spawn or _default_spawn
    # Default hop is recorder + optional sound. The cue page stays on disk.
    # Opening it would dump Chrome/Brave as a third window.
    if show_page and page_path.is_file():
        sp(build_open_argv(page_path))
        opened.append("page")
    sound = media.get("sound") or ""
    if sound:
        sp(build_open_argv(sound))
        opened.append("sound")
    return result


def main() -> int:
    from daemon import run_once

    ap = argparse.ArgumentParser(description="Fire one alarm hop (cue + recorder)")
    ap.add_argument("--fire", required=True, help="window id (e.g. morning)")
    ap.add_argument("--dry-run", action="store_true", help="write cue, do not open GUI")
    ap.add_argument(
        "--show-page",
        action="store_true",
        help="also open the cue HTML (default off — dumps a browser)",
    )
    args = ap.parse_args()
    summary = run_once(
        force_due_id=args.fire,
        dry_run_launch=args.dry_run,
        show_page=args.show_page,
    )
    if not summary.get("ok"):
        print(summary)
        return 1
    print(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
