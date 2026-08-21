#!/usr/bin/env python3
"""Hop a take into the raw-transcription ARRAY as a typed pair.

Audio → text (food-truck Whisper). Then stamp dtype hop.audio_text on the
same-index pair. ARRAY.json is the database. Not a second store.
Inbox original stays in Sound Recordings. End of hop: rename a generic
or CUT-only name to the house title `sesefus · hop · <meaning>`.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
HOME = Path(os.environ.get("USERPROFILE") or Path.home())
JWRANGLE = HOME / "jwrangle"
SINK = JWRANGLE / "tools" / "food_truck_sink.py"
VAULT = JWRANGLE / "durable-archive" / "you" / "raw-transcription"
ARRAY_PATH = VAULT / "ARRAY.json"
if str(JWRANGLE / "tools") not in sys.path:
    sys.path.insert(0, str(JWRANGLE / "tools"))
import tract  # noqa: E402  — protractor; full centroid, not cheap first-clause slug
JOURNAL = HOME / "test-write" / "journal"
DTYPE = "hop.audio_text"
DTYPE_WHY = (
    "one pair: audio[i] + text[i]. Came through a hop (alarm or freeform). "
    "Not a third app. Not a second database."
)
GENERIC_REC = re.compile(r"^Recording(?: \(\d+\))?$", re.IGNORECASE)
CUT_ONLY = re.compile(r"^\d{8}T\d{6}Z(?:-\d+)?$", re.IGNORECASE)
HOUSE_NAMED = re.compile(r"^sesefus · [^\u00b7]+ · .+$", re.IGNORECASE)
HOUSE_DOMAIN = "sesefus"
HOUSE_TOPIC = "hop"
SLUG_STOP = frozenset(
    {
        "a",
        "able",
        "also",
        "and",
        "be",
        "between",
        "bit",
        "but",
        "case",
        "could",
        "for",
        "from",
        "gonna",
        "had",
        "has",
        "have",
        "here",
        "i",
        "im",
        "in",
        "inside",
        "is",
        "it",
        "less",
        "just",
        "keep",
        "kinda",
        "like",
        "little",
        "me",
        "my",
        "need",
        "of",
        "on",
        "obviously",
        "probably",
        "really",
        "remember",
        "so",
        "that",
        "well",
        "the",
        "then",
        "there",
        "this",
        "to",
        "want",
        "wanted",
        "was",
        "we",
        "with",
        "would",
        "yeah",
        "you",
    }
)


def die(msg: str, code: int = 1) -> None:
    print(msg, file=sys.stderr)
    raise SystemExit(code)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def journal_meta(stamp: str) -> dict[str, Any]:
    p = JOURNAL / stamp / "meta.json"
    if not p.is_file():
        die(f"missing journal meta: {p}")
    return read_json(p)


def resolve_src(args: argparse.Namespace) -> tuple[Path, dict[str, Any]]:
    hop: dict[str, Any] = {"via": "alarm" if args.journal else "path", "dtype": DTYPE}
    if args.journal:
        meta = journal_meta(args.journal)
        src = Path(str(meta.get("source_path") or ""))
        if not src.is_file():
            # hardlink sibling in the journal folder
            alt = JOURNAL / args.journal / str(meta.get("audio") or "")
            src = alt if alt.is_file() else src
        if not src.is_file():
            die(f"journal take missing: {src}")
        hop.update(
            {
                "via": str(meta.get("sampled_by") or "alarm"),
                "alarm_id": meta.get("alarm_id"),
                "journal": args.journal,
            }
        )
        return src, hop
    src = Path(args.path or "")
    if not src.is_file():
        die(f"need --journal STAMP or a real audio path")
    return src, hop


def stamp_pair(cut: str, hop: dict[str, Any]) -> dict[str, Any]:
    """Mark the plated pair as hop.audio_text. ARRAY is the database."""
    dest = VAULT / cut
    meta_path = dest / "meta.json"
    if not meta_path.is_file():
        die(f"missing plated meta: {meta_path}")
    meta = read_json(meta_path)
    meta["dtype"] = DTYPE
    meta["hop"] = hop
    write_json(meta_path, meta)

    if not ARRAY_PATH.is_file():
        die(f"missing ARRAY: {ARRAY_PATH}")
    array = read_json(ARRAY_PATH)
    found = 0
    for key in ("audio", "text"):
        for row in array.get(key) or []:
            if row.get("id") == cut:
                row["dtype"] = DTYPE
                row["hop"] = hop
                found += 1
    array.setdefault("dtypes", {})[DTYPE] = DTYPE_WHY
    if found < 2:
        die(f"ARRAY pair incomplete for {cut} (stamped {found} sides)")
    write_json(ARRAY_PATH, array)

    journal = hop.get("journal")
    if journal:
        jp = JOURNAL / str(journal) / "meta.json"
        if jp.is_file():
            jm = read_json(jp)
            jm["transcription"] = cut
            jm["dtype"] = DTYPE
            write_json(jp, jm)
    return {"ok": True, "cut": cut, "dtype": DTYPE, "hop": hop, "count": array.get("count")}


def is_generic_recorder_name(name: str) -> bool:
    return bool(GENERIC_REC.match(Path(name).stem))


def is_house_recording_name(name: str) -> bool:
    return bool(HOUSE_NAMED.match(Path(name).stem))


def needs_house_rename(name: str) -> bool:
    stem = Path(name).stem
    if is_house_recording_name(name):
        return False
    return is_generic_recorder_name(name) or bool(CUT_ONLY.match(stem))


def _clean_part(raw: str) -> str:
    s = (raw or "").replace("·", "-")
    s = re.sub(r'[<>:"/\\|?*]', "", s)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:48]


def plate_text(cut: str) -> str:
    p = VAULT / cut / "raw.txt"
    if not p.is_file():
        return ""
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return ""


def _keeps(chunk: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", (chunk or "").lower())
    return [w for w in words if w not in SLUG_STOP and len(w) > 2]


def plate_segments(cut: str) -> list[dict[str, Any]]:
    p = VAULT / cut / "whisper.json"
    if not p.is_file():
        return []
    try:
        data = read_json(p)
    except (OSError, json.JSONDecodeError):
        return []
    segs = data.get("segments")
    return list(segs) if isinstance(segs, list) else []


def probe_chunks(text: str, segments: list | None = None) -> list[str]:
    """Every spoken clause. Whisper segments first. Then punctuation split."""
    chunks: list[str] = []
    seen: set[str] = set()

    def add(raw: str) -> None:
        t = (raw or "").strip()
        if len(t) < 3:
            return
        key = t.casefold()
        if key in seen:
            return
        seen.add(key)
        chunks.append(t)

    for s in segments or []:
        if isinstance(s, dict):
            add(str(s.get("text") or ""))
        else:
            add(str(s))
    for part in re.split(r"[,.!?;]+", text or ""):
        add(part)
    return chunks


def centroid_probe(
    text: str,
    segments: list | None = None,
) -> dict[str, Any]:
    """Full tract probe. Nearest clause to the whole take is the centroid.

    Not first-clause. Not first-three-words. Diameter is log1p(|tan θ|).
    """
    chunks = probe_chunks(text, segments)
    whole = (text or "").strip() or " ".join(chunks)
    if not chunks:
        return {"chunk": "", "d": None, "n": 0, "whole": whole}
    scored: list[tuple[float, str]] = []
    for c in chunks:
        d = float(tract.tangent_quotient(whole, c)["d"])
        scored.append((d, c))
    scored.sort(key=lambda row: row[0])
    rich = [(d, c) for d, c in scored if len(_keeps(c)) >= 3]
    d0, chunk = (rich[0] if rich else scored[0])
    return {
        "chunk": chunk,
        "d": d0,
        "n": len(chunks),
        "whole": whole,
        "ranked": [{"d": d, "chunk": c} for d, c in scored[:8]],
    }


def artifact_slug(
    text: str,
    hop: dict[str, Any] | None = None,
    segments: list | None = None,
) -> str:
    hop = hop or {}
    probe = centroid_probe(text, segments)
    picked = _keeps(probe.get("chunk") or "")
    if len(picked) < 2:
        picked = _keeps(text)
    if picked:
        return "-".join(picked[:8])
    aid = str(hop.get("alarm_id") or "").strip()
    if aid and aid.lower() not in {"none", "null"}:
        return _clean_part(aid) or "voice-log"
    return "voice-log"


def house_recording_stem(
    cut: str,
    hop: dict[str, Any] | None = None,
    text: str | None = None,
    segments: list | None = None,
) -> str:
    """House title: domain · topic · artifact. Artifact is the tract centroid."""
    if text is None:
        text = plate_text(cut)
    if segments is None:
        segments = plate_segments(cut)
    topic = _clean_part(HOUSE_TOPIC) or "hop"
    art = _clean_part(artifact_slug(text, hop, segments)) or "voice-log"
    return f"{HOUSE_DOMAIN} · {topic} · {art}"


def unique_inbox_name(
    folder: Path,
    stem: str,
    suffix: str,
    *,
    same: Path | None = None,
) -> Path:
    dest = folder / f"{stem}{suffix}"
    if not dest.exists():
        return dest
    if same is not None:
        try:
            if dest.resolve() == same.resolve():
                return dest
        except OSError:
            pass
    n = 2
    while (folder / f"{stem}-{n}{suffix}").exists():
        n += 1
    return folder / f"{stem}-{n}{suffix}"


def _retarget_seen(old: Path, new: Path) -> None:
    from inbox import _source_key, load_seen, save_seen

    seen = load_seen()
    drop = {str(old)}
    try:
        drop.add(str(old.resolve()))
    except OSError:
        pass
    seen -= drop
    seen.add(_source_key(new))
    save_seen(seen)


def _retarget_journal(journal: str, new: Path, old_name: str) -> None:
    jp = JOURNAL / str(journal) / "meta.json"
    if not jp.is_file():
        return
    jm = read_json(jp)
    jm["source_path"] = str(new)
    jm["source_renamed_from"] = old_name
    write_json(jp, jm)


def _retarget_plate(cut: str, new: Path, old_name: str) -> None:
    dest = VAULT / cut
    meta_path = dest / "meta.json"
    if meta_path.is_file():
        meta = read_json(meta_path)
        src = meta.get("source") if isinstance(meta.get("source"), dict) else {}
        src["path"] = str(new)
        src["os_name"] = new.name
        src["os_name_untouched"] = False
        src["os_name_was"] = old_name
        src["moved"] = False
        meta["source"] = src
        meta["title"] = Path(new).stem
        meta["title_source"] = "house-centroid"
        write_json(meta_path, meta)
    if not ARRAY_PATH.is_file():
        return
    array = read_json(ARRAY_PATH)
    for row in array.get("audio") or []:
        if row.get("id") == cut:
            row["src"] = str(new)
            row["os_name"] = new.name
    write_json(ARRAY_PATH, array)


def rename_inbox_recording(
    src: Path,
    cut: str,
    *,
    hop: dict[str, Any] | None = None,
    text: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """End of hop: Recording (N), bare CUT, or cheap house name → centroid title."""
    hop = hop or {}
    target = src
    journal = hop.get("journal")
    if journal:
        jp = JOURNAL / str(journal) / "meta.json"
        if jp.is_file():
            sp = Path(str(read_json(jp).get("source_path") or ""))
            if sp.is_file():
                target = sp
    if not target.is_file():
        return {"ok": False, "skipped": "missing", "path": str(target)}
    if not force and not needs_house_rename(target.name):
        return {"ok": True, "skipped": "already named", "path": str(target)}
    if text is None:
        text = plate_text(cut)
    segs = plate_segments(cut)
    probe = centroid_probe(text, segs)
    stem = house_recording_stem(cut, hop, text, segs)
    dest = unique_inbox_name(target.parent, stem, target.suffix, same=target)
    if dest.resolve() == target.resolve():
        return {
            "ok": True,
            "skipped": "already centroid",
            "path": str(target),
            "centroid": probe.get("chunk"),
            "d": probe.get("d"),
        }
    try:
        target.rename(dest)
    except OSError as e:
        return {"ok": False, "error": str(e), "path": str(target)}
    old_name = target.name
    _retarget_seen(target, dest)
    if journal:
        _retarget_journal(str(journal), dest, old_name)
    _retarget_plate(cut, dest, old_name)
    print(f"[hop-array] renamed {old_name} → {dest.name}", flush=True)
    dest_meta = VAULT / cut / "meta.json"
    if dest_meta.is_file():
        meta = read_json(dest_meta)
        meta["centroid"] = {
            "chunk": probe.get("chunk"),
            "d": probe.get("d"),
            "n": probe.get("n"),
        }
        write_json(dest_meta, meta)
    return {
        "ok": True,
        "from": old_name,
        "to": dest.name,
        "path": str(dest),
        "centroid": probe.get("chunk"),
        "d": probe.get("d"),
        "n": probe.get("n"),
    }


def resolve_inbox_cut(src: Path) -> tuple[str, dict[str, Any]] | None:
    """Match an inbox file to its ARRAY pair + hop. sha first, then path."""
    if not ARRAY_PATH.is_file() or not src.is_file():
        return None
    import hashlib

    h = hashlib.sha256()
    with src.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    digest = h.hexdigest()
    try:
        src_key = str(src.resolve())
    except OSError:
        src_key = str(src)
    array = read_json(ARRAY_PATH)
    hit = None
    for row in array.get("audio") or []:
        if (row.get("sha256") or "").lower() == digest:
            hit = row
            break
    if hit is None:
        for row in array.get("audio") or []:
            for cand in (row.get("src"), row.get("path")):
                if not cand:
                    continue
                try:
                    if str(Path(str(cand)).resolve()) == src_key:
                        hit = row
                        break
                except OSError:
                    if str(cand) == str(src):
                        hit = row
                        break
            if hit is not None:
                break
    if hit is None:
        return None
    cut = str(hit.get("id") or "")
    if not cut:
        return None
    hop = dict(hit.get("hop") or {})
    hop.setdefault("dtype", DTYPE)
    return cut, hop


def mass_rename_inbox() -> dict[str, Any]:
    """Rename every inbox take to its tract centroid. Force. No cheap skip."""
    from capture_config import designated_fields, load_config
    from inbox import list_inbox_files

    fields = designated_fields(load_config())
    inbox = fields.get("inbox") or ""
    files = list_inbox_files(inbox, fields.get("glob") or "*.m4a")
    out: list[dict[str, Any]] = []
    for f in files:
        found = resolve_inbox_cut(f)
        if not found:
            out.append({"ok": False, "file": f.name, "skipped": "no plate"})
            print(f"[hop-array] mass skip {f.name} — no plate", flush=True)
            continue
        cut, hop = found
        r = rename_inbox_recording(f, cut, hop=hop, force=True)
        r["file"] = f.name
        r["cut"] = cut
        out.append(r)
    return {"ok": True, "count": len(out), "renamed": out}


def cook(src: Path) -> str:
    if not SINK.is_file():
        die(f"missing truck: {SINK}")
    sys.path.insert(0, str(SINK.parent))
    import food_truck_sink as truck  # noqa: WPS433

    plan = truck.plan_for(src)
    already = plan.get("already")
    if already:
        print(f"[hop-array] already plated {already} — stamp only", flush=True)
        return str(already)

    code = truck.land(src)
    if code != 0:
        die(f"truck failed: {code}")
    array = read_json(ARRAY_PATH)
    audio = array.get("audio") or []
    if not audio:
        die("truck returned but ARRAY has no audio")
    return str(audio[-1]["id"])


def main() -> int:
    ap = argparse.ArgumentParser(description="Hop take → text → typed ARRAY pair")
    ap.add_argument("path", nargs="?", help="audio file (if not --journal)")
    ap.add_argument("--journal", default="", help="journal stamp, e.g. 20260816-003833")
    ap.add_argument(
        "--stamp-only",
        default="",
        help="CUT already plated; only stamp dtype (no whisper)",
    )
    ap.add_argument(
        "--mass",
        action="store_true",
        help="rename every inbox take to its tract centroid (force)",
    )
    args = ap.parse_args()

    if args.mass:
        out = mass_rename_inbox()
        print(json.dumps(out, indent=2, default=str))
        bad = [r for r in out.get("renamed") or [] if not r.get("ok")]
        return 1 if bad else 0

    if args.stamp_only:
        hop = {"via": "stamp-only", "dtype": DTYPE}
        src = Path()
        if args.journal:
            hop["journal"] = args.journal
            jm = journal_meta(args.journal)
            hop["via"] = str(jm.get("sampled_by") or "alarm")
            hop["alarm_id"] = jm.get("alarm_id")
            src = Path(str(jm.get("source_path") or ""))
        out = stamp_pair(args.stamp_only, hop)
        out["rename"] = rename_inbox_recording(src, args.stamp_only, hop=hop)
        print(json.dumps(out, indent=2))
        return 0

    src, hop = resolve_src(args)
    print(f"[hop-array] cook {src}", flush=True)
    cut = cook(src)
    out = stamp_pair(cut, hop)
    out["rename"] = rename_inbox_recording(src, cut, hop=hop)
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
