#!/usr/bin/env python3
"""Artifact Sieve: comb Google Gemini / chat dump trees into DebrisChunks.

A branch of sieve.py's DebrisChunk pipeline (sibling to image_sieve.py).
Where the text sieve shreds loose files by paragraph, and the image sieve
reads screenshots, this sieve opens a *directory of export artifacts* —
Google Takeout Gemini JSON/HTML, My Activity dumps, AI Studio history,
and related chat export shapes — linearizes conversation DAGs, and ships
embeddable chunks to the same ingest/debris_shards.jsonl Forge path.

Scan mode (no shred) invents the "artifact scanner" inventory for the
dashboard: for a particular opened directory, list dump files, detect
format, estimate conversation/message counts.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

_here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _here)
sys.path.insert(0, os.path.join(os.path.dirname(_here), "tools"))
from sieve import DebrisChunk  # noqa: E402 — exact chunk shape sieve.py ships
from sesefus_config import load_config  # noqa: E402

_cfg = load_config()

# Files / extensions that look like chat-export artifacts
DUMP_NAMES = {
    "conversations.json",
    "myactivity.json",
    "my_activity.json",
    "activity.json",
    "full_chat_export.json",
    "applet_access_history.json",
}
DUMP_EXT = {".json", ".html", ".htm", ".md", ".txt", ".jsonl"}
SKIP_DIR_NAMES = {
    "node_modules", "__pycache__", ".git", "venv", ".venv",
    "libraries", "versions", "mods",
}

# Read a bounded prefix of document-shaped dumps: the output is capped at
# 100k chars anyway, so slurping a multi-hundred-MB MyActivity.html and then
# running six whole-content regexes over it was pure waste on a thin host.
DOC_READ_CAP_BYTES = 2_000_000
# Files above this are inventoried but not deep-parsed.
MAX_DEEP_PARSE_BYTES = 64 * 1024 * 1024

ROLE_ALIASES = {
    "user": "user",
    "human": "user",
    "model": "model",
    "assistant": "model",
    "bot": "model",
    "system": "system",
    "gemini": "model",
    "bard": "model",
}


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def default_roots() -> list[Path]:
    configured = [Path(r) for r in _cfg.get("artifact_roots", [])]
    if configured:
        return configured
    home = Path.home()
    candidates = [
        home / "Downloads",
        home / "Documents" / "Takeout",
        home / "Documents" / "Gemini",
        Path(__file__).resolve().parent.parent / "export" / "gemini",
    ]
    return [p for p in candidates if p.exists()] or [home / "Downloads"]


def _norm_role(raw: Any) -> str:
    if raw is None:
        return "unknown"
    if isinstance(raw, dict):
        raw = raw.get("role") or raw.get("name") or raw.get("type") or "unknown"
    key = str(raw).strip().lower()
    return ROLE_ALIASES.get(key, key or "unknown")


def _parts_to_text(parts: Any) -> str:
    """Flatten Gemini/ChatGPT-style content parts to plain text."""
    if parts is None:
        return ""
    if isinstance(parts, str):
        return parts
    if isinstance(parts, dict):
        if "text" in parts:
            return str(parts["text"])
        if "parts" in parts:
            return _parts_to_text(parts["parts"])
        # multimodal stub — keep structure, drop binary
        if parts.get("inline_data") or parts.get("inlineData"):
            return "[image]"
        if parts.get("file_data") or parts.get("fileData"):
            return "[file]"
        return ""
    if isinstance(parts, list):
        bits = []
        for p in parts:
            t = _parts_to_text(p)
            if t:
                bits.append(t)
        return "\n".join(bits)
    return str(parts)


def _strip_html(raw: str) -> str:
    text = re.sub(r"(?is)<script[^>]*>.*?</script>", " ", raw)
    text = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", text)
    text = re.sub(r"(?is)<br\s*/?>", "\n", text)
    text = re.sub(r"(?is)</p>", "\n\n", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def _decode_bytes(raw: bytes) -> str:
    """Decode export bytes, tolerating the BOMs this machine actually produces."""
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="ignore")
    # utf-8-sig strips a UTF-8 BOM and is a no-op when there isn't one.
    return raw.decode("utf-8-sig", errors="ignore")


def _read_text(path: Path, max_bytes: int = 0) -> str:
    """Read (optionally a bounded prefix of) a file as text."""
    with path.open("rb") as f:
        raw = f.read(max_bytes) if max_bytes > 0 else f.read()
    return _decode_bytes(raw)


# ---------------------------------------------------------------------------
# Conversation linearization (mapping DAG + flat list shapes)
# ---------------------------------------------------------------------------

def _walk_mapping_messages(mapping: dict) -> list[dict]:
    """Leaf-to-root linearization of a ChatGPT/Gemini-style mapping DAG.

    Picks the leaf with the deepest path (final branch) so regenerated
    forks don't duplicate the whole tree.
    """
    if not isinstance(mapping, dict) or not mapping:
        return []

    # Iterative + memoized. A recursive walk cost one interpreter frame per
    # ancestor, so a chain of ~1000 nodes raised RecursionError and took down
    # the parse of every other conversation in the same file.
    depths: dict[str, int] = {}

    def depth(node_id: str) -> int:
        chain: list[str] = []
        seen: set[str] = set()
        cur: Any = node_id
        while isinstance(cur, str) and cur in mapping and cur not in depths and cur not in seen:
            seen.add(cur)
            chain.append(cur)
            cur = (mapping[cur] or {}).get("parent")
        base = depths.get(cur, 0) if isinstance(cur, str) else 0
        for nid in reversed(chain):
            base += 1
            depths[nid] = base
        return depths.get(node_id, 0)

    leaves = [
        nid for nid, node in mapping.items()
        if isinstance(node, dict) and not (node.get("children") or [])
    ]
    if not leaves:
        leaves = list(mapping.keys())

    best = max(leaves, key=depth)
    chain: list[dict] = []
    current: Any = best
    # A visited set, not a counter: cyclic parent pointers used to emit the
    # same messages 50_000 times instead of terminating at the cycle.
    visited: set[str] = set()
    while isinstance(current, str) and current not in visited:
        visited.add(current)
        node = mapping.get(current) or {}
        msg = node.get("message")
        if msg:
            author = msg.get("author") or msg.get("role")
            content = msg.get("content")
            text = ""
            if isinstance(content, dict):
                text = _parts_to_text(content.get("parts", content))
            else:
                text = _parts_to_text(content)
            text = (text or "").strip()
            if text:
                chain.append({
                    "role": _norm_role(author),
                    "text": text,
                    "node_id": current,
                })
        current = node.get("parent")
    chain.reverse()
    return chain


def _extract_messages_from_obj(obj: Any) -> list[dict]:
    """Best-effort message list from one conversation-like object."""
    if not isinstance(obj, dict):
        return []

    mapping = obj.get("mapping")
    if isinstance(mapping, dict) and mapping:
        return _walk_mapping_messages(mapping)

    for key in ("messages", "entries", "turns", "conversation", "chat"):
        items = obj.get(key)
        if not isinstance(items, list):
            continue
        out = []
        for item in items:
            if not isinstance(item, dict):
                continue
            # nested message wrapper
            msg = item.get("message") if isinstance(item.get("message"), dict) else item
            role = (
                msg.get("role")
                or msg.get("author")
                or msg.get("type")
                or item.get("role")
                or item.get("type")
            )
            text = (
                msg.get("text")
                or msg.get("content")
                or msg.get("message")
                or item.get("text")
                or item.get("content")
            )
            text = _parts_to_text(text).strip()
            if text:
                out.append({"role": _norm_role(role), "text": text})
        if out:
            return out

    # single-turn activity style (My Activity)
    title = obj.get("title") or obj.get("header")
    if isinstance(title, str) and title.strip() and (
        "gemini" in str(obj.get("products") or obj.get("header") or "").lower()
        or "bard" in str(obj.get("header") or "").lower()
        or obj.get("titleUrl")
    ):
        return [{"role": "activity", "text": title.strip()}]

    return []


def _conversation_meta(obj: dict, fallback_title: str) -> dict:
    title = (
        obj.get("title")
        or obj.get("name")
        or obj.get("conversation_title")
        or fallback_title
    )
    cid = (
        obj.get("conversation_id")
        or obj.get("id")
        or obj.get("conversationId")
        or ""
    )
    created = (
        obj.get("create_time")
        or obj.get("createTime")
        or obj.get("created_at")
        or obj.get("time")
        or obj.get("timestamp")
    )
    return {
        "title": str(title)[:200] if title else fallback_title,
        "conversation_id": str(cid)[:80] if cid else "",
        "created": created,
    }


def iter_conversations_from_json(data: Any, source_name: str) -> Iterator[dict]:
    """Yield {title, conversation_id, created, messages, format} from loaded JSON."""
    # Top-level list of conversations or activities
    if isinstance(data, list):
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            # prune_chat / Mongo-style $set wrapper
            if "$set" in item and isinstance(item["$set"], dict):
                inner = item["$set"]
                messages = _extract_messages_from_obj(inner)
                if not messages and "messages" in inner:
                    messages = _extract_messages_from_obj({"messages": inner["messages"]})
                meta = _conversation_meta(inner, f"{source_name}#{i}")
                if messages:
                    yield {**meta, "messages": messages, "format": "mongo_export"}
                continue
            messages = _extract_messages_from_obj(item)
            meta = _conversation_meta(item, f"{source_name}#{i}")
            if messages:
                # My Activity singles often have one "activity" message
                fmt = "my_activity" if messages[0].get("role") == "activity" else "conversation_list"
                yield {**meta, "messages": messages, "format": fmt}
        return

    if not isinstance(data, dict):
        return

    # Takeout bundle: { conversations: [ ... ] }
    if isinstance(data.get("conversations"), list):
        for i, item in enumerate(data["conversations"]):
            if not isinstance(item, dict):
                continue
            messages = _extract_messages_from_obj(item)
            meta = _conversation_meta(item, f"{source_name}#{i}")
            if messages:
                yield {**meta, "messages": messages, "format": "takeout_conversations"}
        return

    # AI Studio applet history
    if isinstance(data.get("applets"), list):
        for i, item in enumerate(data["applets"]):
            if not isinstance(item, dict):
                continue
            name = item.get("name") or f"applet-{i}"
            desc = item.get("description") or ""
            text = f"{name}\n\n{desc}".strip()
            if text:
                yield {
                    "title": str(name)[:200],
                    "conversation_id": str(
                        (item.get("source") or {}).get("spanner", {}).get("id")
                        or item.get("id")
                        or ""
                    ),
                    "created": item.get("firstAccessTime") or item.get("lastAccessTime"),
                    "messages": [{"role": "artifact", "text": text}],
                    "format": "ai_studio_applet",
                }
        return

    # Single conversation object (per-file Takeout Gemini Apps/*.json).
    # This also covers a bare root-level `mapping`, which
    # _extract_messages_from_obj consumes first.
    messages = _extract_messages_from_obj(data)
    if messages:
        meta = _conversation_meta(data, source_name)
        yield {**meta, "messages": messages, "format": "single_conversation"}


def detect_format(path: Path) -> str:
    name = path.name.lower()
    if name in DUMP_NAMES:
        return name.replace(".json", "")
    if name.endswith(".html") or name.endswith(".htm"):
        return "html_export"
    if name.endswith(".jsonl"):
        return "jsonl"
    if name.endswith(".md") or name.endswith(".txt"):
        return "plaintext"
    if name.endswith(".json"):
        return "json_unknown"
    if name.endswith(".zip"):
        return "zip_bundle"
    return "other"


def classify_path(path: Path) -> bool:
    """True if this file looks like a chat/export artifact worth scanning."""
    if not path.is_file():
        return False
    name = path.name.lower()
    if name in DUMP_NAMES:
        return True
    if path.suffix.lower() not in DUMP_EXT and path.suffix.lower() != ".zip":
        return False
    # Prefer Gemini / Takeout / Activity / chat-ish names
    markers = (
        "gemini", "bard", "takeout", "activity", "conversation",
        "chat", "export", "applet", "myactivity", "messages",
    )
    joined = f"{name} {path.parent.name.lower()}"
    if any(m in joined for m in markers):
        return True
    # Loose .json under a Takeout/Gemini tree
    parts = {p.lower() for p in path.parts}
    if "takeout" in parts or "gemini" in parts or "my activity" in parts:
        return path.suffix.lower() in {".json", ".html", ".htm", ".zip"}
    return False


# ---------------------------------------------------------------------------
# Parse one file → conversations
# ---------------------------------------------------------------------------

def parse_artifact_file(path: Path, errors: list[str] | None = None) -> list[dict]:
    """Parse a dump file into conversation dicts. Empty list on hard failure.

    Pass `errors` to receive the failure reason — otherwise a skipped file is
    indistinguishable from one that genuinely holds no conversations.
    """
    fmt = detect_format(path)
    try:
        if fmt == "zip_bundle":
            return _parse_zip(path)
        if fmt == "html_export":
            raw = _read_text(path, max_bytes=DOC_READ_CAP_BYTES)
            text = _strip_html(raw)
            if not text:
                return []
            return [{
                "title": path.stem,
                "conversation_id": "",
                "created": None,
                "messages": [{"role": "document", "text": text[:100_000]}],
                "format": "html_export",
            }]
        if fmt == "plaintext":
            text = _read_text(path, max_bytes=DOC_READ_CAP_BYTES).strip()
            if not text:
                return []
            return [{
                "title": path.stem,
                "conversation_id": "",
                "created": None,
                "messages": [{"role": "document", "text": text[:100_000]}],
                "format": "plaintext",
            }]
        if fmt == "jsonl":
            convs = []
            with path.open("r", encoding="utf-8-sig", errors="ignore") as f:
                for i, line in enumerate(f):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    for conv in iter_conversations_from_json(obj, f"{path.name}:L{i}"):
                        convs.append(conv)
            return convs

        # JSON
        data = json.loads(_read_text(path))
        return list(iter_conversations_from_json(data, path.name))
    # RecursionError is caught deliberately: a single pathological conversation
    # must degrade to skipping this file, never take down the whole scan.
    except (OSError, ValueError, UnicodeError, zipfile.BadZipFile, RecursionError) as exc:
        msg = f"{type(exc).__name__}: {exc}"
        if errors is not None:
            errors.append(msg)
        print(f"[artifact_sieve] parse skip {path}: {msg}")
        return []


def _parse_zip(path: Path) -> list[dict]:
    convs: list[dict] = []
    with zipfile.ZipFile(path, "r") as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            inner = Path(info.filename)
            if inner.suffix.lower() not in {".json", ".html", ".htm", ".md", ".txt", ".jsonl"}:
                continue
            # only chat-ish members to avoid reading whole Drive dumps
            low = info.filename.lower()
            if not any(m in low for m in (
                "gemini", "bard", "conversation", "activity", "chat", "applet", "my activity"
            )):
                continue
            try:
                raw = zf.read(info)
            except Exception:
                continue
            try:
                if inner.suffix.lower() in {".html", ".htm"}:
                    text = _strip_html(raw.decode("utf-8", errors="ignore"))
                    if text:
                        convs.append({
                            "title": inner.stem,
                            "conversation_id": "",
                            "created": None,
                            "messages": [{"role": "document", "text": text[:100_000]}],
                            "format": "zip_html",
                        })
                    continue
                if inner.suffix.lower() == ".jsonl":
                    for i, line in enumerate(raw.decode("utf-8", errors="ignore").splitlines()):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            obj = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        for conv in iter_conversations_from_json(obj, f"{path.name}:{inner.name}:L{i}"):
                            convs.append(conv)
                    continue
                if inner.suffix.lower() in {".md", ".txt"}:
                    text = raw.decode("utf-8", errors="ignore").strip()
                    if text:
                        convs.append({
                            "title": inner.stem,
                            "conversation_id": "",
                            "created": None,
                            "messages": [{"role": "document", "text": text[:100_000]}],
                            "format": "zip_text",
                        })
                    continue
                data = json.loads(raw.decode("utf-8", errors="ignore"))
                for conv in iter_conversations_from_json(data, f"{path.name}:{inner.name}"):
                    convs.append(conv)
            except Exception as exc:  # noqa: BLE001
                print(f"[artifact_sieve] zip member skip {info.filename}: {exc}")
    return convs


def linearize_conversation(conv: dict) -> str:
    lines = []
    title = conv.get("title") or "Untitled"
    lines.append(f"# {title}")
    created = conv.get("created")
    if created is not None:
        lines.append(f"(created: {created})")
    lines.append("")
    for msg in conv.get("messages") or []:
        role = msg.get("role") or "unknown"
        text = (msg.get("text") or "").strip()
        if not text:
            continue
        lines.append(f"--- {role.upper()} ---")
        lines.append(text)
        lines.append("")
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Scanner inventory (for UI)
# ---------------------------------------------------------------------------

def collect_artifact_files(
    roots: list[Path], problems: list[dict] | None = None
) -> list[Path]:
    """Collect artifact-shaped files under roots.

    Unreachable roots and unreadable subtrees are recorded in `problems`
    rather than dropped: a Windows path evaluated under WSL (or the reverse)
    used to be indistinguishable from "this directory has no artifacts".
    """
    def note(target: Any, error: str) -> None:
        print(f"[artifact_sieve] {error}: {target}", file=sys.stderr)
        if problems is not None:
            problems.append({"path": str(target), "error": error})

    seen: set[str] = set()
    files: list[Path] = []
    for root in roots:
        try:
            exists = root.exists()
        except OSError as exc:
            note(root, f"root not reachable from this environment ({exc})")
            continue
        if not exists:
            note(root, "root not found")
            continue
        if root.is_file():
            candidates = [root]
        else:
            candidates = []
            for dirpath, dirnames, filenames in os.walk(
                root, onerror=lambda exc: note(getattr(exc, "filename", root), f"walk failed ({exc})")
            ):
                dirnames[:] = [
                    d for d in dirnames
                    if d.lower() not in SKIP_DIR_NAMES and not d.startswith(".")
                ]
                for name in filenames:
                    candidates.append(Path(dirpath) / name)
        for path in candidates:
            if not path.is_file():
                continue
            if not classify_path(path):
                continue
            try:
                key = str(path.resolve())
            except OSError:
                key = str(path)
            if key not in seen:
                seen.add(key)
                files.append(path)
    return files


def scan_directory(roots: list[Path], deep_parse: bool = True, limit: int = 0) -> dict:
    """Inventory dump files under roots for the artifact scanner view."""
    problems: list[dict] = []
    files = collect_artifact_files(roots, problems=problems)
    if limit > 0:
        files = files[:limit]

    entries = []
    total_conversations = 0
    total_messages = 0
    for path in files:
        error = None
        try:
            st = path.stat()
            size = st.st_size
            mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat()
        except OSError as exc:
            # None, not 0 — an unreadable file must not read as an empty one.
            size = None
            mtime = None
            error = f"stat failed: {exc}"

        fmt = detect_format(path)
        conv_count = 0
        msg_count = 0
        titles: list[str] = []
        skipped_reason = None
        if deep_parse and size is not None and size > MAX_DEEP_PARSE_BYTES:
            skipped_reason = f"file over {MAX_DEEP_PARSE_BYTES // (1024 * 1024)} MB — not deep-parsed"
        elif deep_parse:
            parse_errors: list[str] = []
            try:
                convs = parse_artifact_file(path, errors=parse_errors)
                conv_count = len(convs)
                for c in convs:
                    msg_count += len(c.get("messages") or [])
                    t = c.get("title")
                    if t and len(titles) < 5:
                        titles.append(str(t)[:80])
            except Exception as exc:  # noqa: BLE001
                parse_errors.append(str(exc))
            if parse_errors and not error:
                error = "; ".join(parse_errors)
        total_conversations += conv_count
        total_messages += msg_count
        # Tri-state: True = conversations found, False = parsed and empty,
        # None = not determined (shallow scan, oversize, or unreadable).
        if conv_count > 0:
            sievable = True
        elif deep_parse and not error and not skipped_reason:
            sievable = False
        else:
            sievable = None
        entries.append({
            "path": str(path),
            "name": path.name,
            "parent": str(path.parent),
            "format": fmt,
            "size_bytes": size,
            "mtime": mtime,
            "conversation_count": conv_count,
            "message_count": msg_count,
            "sample_titles": titles,
            "error": error,
            "deep_parse_skipped": skipped_reason,
            "sievable": sievable,
        })

    return {
        "roots": [str(r) for r in roots],
        "root_problems": problems,
        "file_count": len(entries),
        "conversation_count": total_conversations,
        "message_count": total_messages,
        "files": entries,
        "scanned_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Shred → DebrisChunks
# ---------------------------------------------------------------------------

class ArtifactSieve:
    def __init__(
        self,
        output_path: Path,
        state_path: Path,
        source_node: str = "GeminiTakeout",
    ):
        self.output_path = output_path
        self.state_path = state_path
        self.source_node = source_node
        self.state = self._load_state()
        self.chunks: list[DebrisChunk] = []

    def _load_state(self) -> dict:
        if not self.state_path.exists():
            return {}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8-sig"))
        except (json.JSONDecodeError, OSError) as exc:
            # Do not silently return {} — that is indistinguishable from a first
            # run and quietly re-ships every file ever processed. Preserve the
            # damaged file and say so.
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
            quarantine = self.state_path.with_suffix(f".corrupt-{stamp}.json")
            try:
                os.replace(self.state_path, quarantine)
            except OSError:
                quarantine = None
            print(
                f"[artifact_sieve] WARNING: dedup state unreadable ({exc}); "
                f"dedup history reset"
                + (f", damaged file kept at {quarantine}" if quarantine else ""),
                file=sys.stderr,
            )
            return {}

    def _save_state(self) -> None:
        """Atomically replace the dedup state file.

        A truncating in-place write left a window in which a kill wiped the
        whole dedup index; _load_state then read it as a first run.
        """
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(self.state, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.state_path)

    def _append(self, chunk: DebrisChunk) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with self.output_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(chunk.to_dict()) + "\n")

    def shred_file(
        self,
        path: Path,
        dry_run: bool = False,
        force: bool = False,
        unit: str = "conversation",
    ) -> list[DebrisChunk]:
        """Shred one dump file. unit: 'conversation' | 'turn'."""
        try:
            file_hash = file_sha256(path)
        except OSError as exc:
            print(f"[error] hash {path}: {exc}")
            return []

        state_key = f"{file_hash}:{unit}"
        if not force and state_key in self.state:
            return []

        convs = parse_artifact_file(path)
        if not convs:
            return []

        if dry_run:
            print(f"[dry-run] would shred {path} ({len(convs)} conversation(s)) via unit={unit}")
        else:
            # Record the marker BEFORE the first append. Writing it only after
            # the whole file finished meant an interrupted run left already-
            # appended chunks unrecorded, and the next run appended them again
            # into the append-only ledger.
            self.state[state_key] = {
                "chunk_ids": [],
                "conversation_count": len(convs),
                "path": str(path),
                "started_at": datetime.now(timezone.utc).isoformat(),
                "complete": False,
            }
            self._save_state()

        produced: list[DebrisChunk] = []
        for conv in convs:
            if unit == "turn":
                for i, msg in enumerate(conv.get("messages") or []):
                    text = (msg.get("text") or "").strip()
                    if not text:
                        continue
                    content = f"{msg.get('role', 'unknown').upper()}: {text}"
                    if len(content) > 30_000:
                        content = content[:30_000]
                    chunk = DebrisChunk(
                        content=content,
                        source_node=self.source_node,
                        source_path=str(path),
                        file_type=path.suffix.lower() or ".json",
                        metadata={
                            "shred_method": "gemini-turn",
                            "artifact_format": conv.get("format"),
                            "conversation_title": conv.get("title"),
                            "conversation_id": conv.get("conversation_id"),
                            "turn_index": i,
                            "role": msg.get("role"),
                            "file_sha256": file_hash,
                            "created": conv.get("created"),
                        },
                    )
                    produced.append(chunk)
                    if not dry_run:
                        self.chunks.append(chunk)
                        self.state[state_key]["chunk_ids"].append(chunk.id)
                        self._append(chunk)
            else:
                body = linearize_conversation(conv)
                if not body:
                    continue
                if len(body) > 30_000:
                    body = body[:30_000]
                chunk = DebrisChunk(
                    content=body,
                    source_node=self.source_node,
                    source_path=str(path),
                    file_type=path.suffix.lower() or ".json",
                    metadata={
                        "shred_method": "gemini-conversation",
                        "artifact_format": conv.get("format"),
                        "conversation_title": conv.get("title"),
                        "conversation_id": conv.get("conversation_id"),
                        "message_count": len(conv.get("messages") or []),
                        "file_sha256": file_hash,
                        "created": conv.get("created"),
                    },
                )
                produced.append(chunk)
                if not dry_run:
                    self.chunks.append(chunk)
                    self.state[state_key]["chunk_ids"].append(chunk.id)
                    self._append(chunk)

            # Checkpoint once per conversation rather than once per chunk:
            # resumable, and O(conversations) state rewrites instead of
            # O(chunks) full-file serializations.
            if not dry_run:
                self._save_state()

        if not dry_run:
            self.state[state_key]["shipped_at"] = datetime.now(timezone.utc).isoformat()
            self.state[state_key]["complete"] = True
            self._save_state()
        return produced


def shred_roots(
    roots: list[Path],
    output: Path,
    state: Path,
    source_node: str = "GeminiTakeout",
    unit: str = "conversation",
    limit: int = 0,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    sieve = ArtifactSieve(output, state, source_node=source_node)
    problems: list[dict] = []
    files = collect_artifact_files(roots, problems=problems)
    if limit > 0:
        files = files[:limit]

    read_count = 0
    chunk_count = 0
    errors = list(problems)
    for path in files:
        try:
            produced = sieve.shred_file(path, dry_run=dry_run, force=force, unit=unit)
            if produced:
                read_count += 1
                chunk_count += len(produced)
                print(f"[shred] {path.name} -> {len(produced)} chunk(s)")
        except Exception as exc:  # noqa: BLE001
            errors.append({"path": str(path), "error": str(exc)})
            print(f"[error] {path}: {exc}")

    return {
        "files_seen": len(files),
        # A dry run ships nothing, so the shipped counters stay zero — the
        # would_* pair carries the preview the UI actually needs.
        "files_shredded": 0 if dry_run else read_count,
        "chunks_shipped": 0 if dry_run else chunk_count,
        "would_shred": read_count if dry_run else 0,
        "would_ship": chunk_count if dry_run else 0,
        "output": str(output),
        "dry_run": dry_run,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Artifact Sieve: Gemini/Takeout chat dumps → DebrisChunks"
    )
    parser.add_argument(
        "--root", action="append", default=[],
        help="export directory or dump file (repeatable). Default: artifact_roots / Downloads",
    )
    parser.add_argument(
        "--scan-only", action="store_true",
        help="inventory only — print scanner JSON, do not shred",
    )
    parser.add_argument(
        "--unit", choices=("conversation", "turn"), default="conversation",
        help="shred grain: whole conversation (default) or each turn",
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).resolve().parent.parent / "ingest" / "debris_shards.jsonl",
    )
    parser.add_argument(
        "--state", type=Path,
        default=Path(__file__).resolve().parent.parent / "ingest" / "artifact_sieve_state.json",
    )
    parser.add_argument("--source-node", default="GeminiTakeout")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", "-n", action="store_true")
    parser.add_argument(
        "--yes", action="store_true",
        help="actually ship when no --root was given (default is dry-run then)",
    )
    parser.add_argument(
        "--shallow", action="store_true",
        help="with --scan-only: skip deep parse (format/size only)",
    )
    args = parser.parse_args()

    roots = [Path(r) for r in args.root] if args.root else default_roots()
    if not roots:
        print("No roots to scan. Pass --root PATH to a Takeout/Gemini export folder.")
        return 1

    print(f"Artifact sieve roots: {', '.join(str(r) for r in roots)}")

    if args.scan_only:
        inv = scan_directory(roots, deep_parse=not args.shallow, limit=args.limit)
        print(json.dumps(inv, indent=2))
        print(
            f"Scan: {inv['file_count']} file(s), "
            f"{inv['conversation_count']} conversation(s), "
            f"{inv['message_count']} message(s)"
        )
        if inv["root_problems"] and not inv["file_count"]:
            print("No root was reachable — nothing was scanned.", file=sys.stderr)
            return 1
        return 0

    dry_run = args.dry_run
    if not args.root and not dry_run and not args.yes:
        # Without an explicit root this walks ~/Downloads and ships anything
        # merely named export/chat/messages/activity into the vault ledger.
        # Preview by default; --yes to mean it.
        dry_run = True
        print(
            "No --root given: defaulting to a dry run over the fallback roots. "
            "Re-run with --yes (or an explicit --root) to actually ship.",
            file=sys.stderr,
        )

    result = shred_roots(
        roots=roots,
        output=args.output,
        state=args.state,
        source_node=args.source_node,
        unit=args.unit,
        limit=args.limit,
        force=args.force,
        dry_run=dry_run,
    )
    if dry_run:
        print(
            f"Done (dry run). files_seen={result['files_seen']} "
            f"would_shred={result['would_shred']} "
            f"would_ship={result['would_ship']} chunk(s)"
        )
    else:
        print(
            f"Done. files_seen={result['files_seen']} "
            f"shredded={result['files_shredded']} "
            f"chunks={result['chunks_shipped']}"
        )
    if result["chunks_shipped"] and not dry_run:
        print(f"Shipped to {result['output']}")
        print("Next: python utils/forge.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
