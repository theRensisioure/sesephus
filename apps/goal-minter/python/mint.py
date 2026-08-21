#!/usr/bin/env python3
"""Messy objective text → house 3-Q goal packet. No mic. No window."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

PACKET_REL = Path("intent") / "interview.md"

Q1_QUESTION = "What exists when this is done?"
Q2_QUESTION = "Where does it live (repo, skill, doc, path)?"
Q3_QUESTION = "What is explicitly out of scope?"

_NOT_NAMED = "not named in the objective"

_KEY_LINE = re.compile(
    r"^(spine|outcome|surface|fence|done\s*when)\s*[:·]\s*(.*)$",
    re.I,
)
_CHECK_LINE = re.compile(r"^-\s*\[[ xX]\]\s*(.+)$")
_BARE_CHECK = re.compile(r"^-\s+(.+)$")
_LIVE_AT = re.compile(
    r"(?:should\s+live|lives?)\s+(?:at|in|under|on)\s+(?P<s>.+?)(?=\.\s|\.$|$)",
    re.I,
)
_PATH = re.compile(
    r"(?:apps[/\\][A-Za-z0-9._-]+"
    r"|[A-Za-z]:[\\/][^\s,;]+"
    r"|~[/\\][^\s,;]+)"
)
_FENCE_SPAN = re.compile(
    r"(?P<a>(?:don't|do not)\s+.+?)(?=\.|$)"
    r"|out of scope[:\s]+(?P<b>.+?)(?=\.|$)"
    r"|(?P<c>leave\s+.+?\s+(?:untouched|unchanged|alone))"
    r"|without\s+(?P<d>(?:growing|adding|touching)\s+.+?)(?=\.|$)"
    r"|(?:^|\.\s+)no\s+(?P<e>extra\s+.+?)(?=\.|$)",
    re.I,
)
_WANT = re.compile(
    r"(?:^|\.\s+)(?:i want|i need|wanted result is|the outcome is)\s+(?P<o>.+?)(?=\.|$)",
    re.I,
)
_HEADING = re.compile(r"^(#{1,3})\s+(.*\S)\s*$")


class EmptyInputError(ValueError):
    """Blank or whitespace-only objective; no packet is minted."""


@dataclass(frozen=True)
class Packet:
    spine: str
    outcome: str
    surface: str
    fence: str
    done_when: tuple[str, ...]

    def fields(self) -> dict[str, Any]:
        return {
            "spine": self.spine,
            "outcome": self.outcome,
            "surface": self.surface,
            "fence": self.fence,
            "done_when": list(self.done_when),
        }


def mint(text: str) -> Packet:
    """Shipped text→packet. Raises EmptyInputError on blank input."""
    if text is None or not str(text).strip():
        raise EmptyInputError("empty objective — no packet")
    raw = str(text)
    found = _fields_from_markdown(raw)
    _merge_key_lines(raw, found)
    _fill_heuristic(raw, found)
    spine = _one_line(found.get("spine") or "")
    outcome = _clean_block(found.get("outcome") or "")
    surface = _clean_block(found.get("surface") or "")
    fence = _clean_block(found.get("fence") or "")
    checks = _clean_checks(found.get("done_when") or [])
    if not outcome:
        outcome = _clean_block(raw)
    if not spine:
        spine = _spine_from(outcome or raw)
    if not surface:
        surface = _NOT_NAMED
    if not fence:
        fence = _NOT_NAMED
    if not checks:
        checks = _derive_done_when(outcome)
    if not (spine and outcome and surface and fence and checks):
        raise EmptyInputError("empty objective — no packet")
    return Packet(
        spine=spine,
        outcome=outcome,
        surface=surface,
        fence=fence,
        done_when=tuple(checks),
    )


def render_packet(packet: Packet, *, time_started: str | None = None) -> str:
    started = time_started or datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    checks = "\n".join(f"- [ ] {item}" for item in packet.done_when)
    return (
        f"# Goal packet\n"
        f"time_started: {started}\n"
        f"status: open\n"
        f"\n"
        f"## Spine\n"
        f"{packet.spine}\n"
        f"\n"
        f"## Done when\n"
        f"{checks}\n"
        f"\n"
        f"## Fence\n"
        f"{packet.fence}\n"
        f"\n"
        f"## Interview (max 3)\n"
        f"### Q1\n"
        f"{Q1_QUESTION}\n"
        f"**A:** {packet.outcome}\n"
        f"\n"
        f"### Q2\n"
        f"{Q2_QUESTION}\n"
        f"**A:** {packet.surface}\n"
        f"\n"
        f"### Q3\n"
        f"{Q3_QUESTION}\n"
        f"**A:** {packet.fence}\n"
    )


def write_packet(
    packet: Packet,
    out_dir: Path,
    *,
    time_started: str | None = None,
) -> Path:
    dest = Path(out_dir) / PACKET_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        render_packet(packet, time_started=time_started),
        encoding="utf-8",
    )
    return dest


def _fields_from_markdown(text: str) -> dict[str, Any]:
    found: dict[str, Any] = {}
    sections = _section_map(text)
    if "spine" in sections:
        found["spine"] = _one_line(sections["spine"])
    if "fence" in sections:
        found["fence"] = _clean_block(sections["fence"])
    if "done when" in sections:
        found["done_when"] = _checks_from(sections["done when"])
    qmap = {
        "q1": "outcome",
        "q1 · outcome": "outcome",
        "q2": "surface",
        "q2 · surface": "surface",
        "q3": "fence",
        "q3 · fence": "fence",
    }
    for heading, key in qmap.items():
        if heading in sections:
            ans = _answer_from(sections[heading])
            if ans:
                found[key] = ans
    interview = sections.get("interview") or sections.get("interview (max 3)") or ""
    if interview:
        for q_head, body in _section_map(interview).items():
            qn = _norm_heading(q_head)
            key = qmap.get(qn)
            if key and key not in found:
                ans = _answer_from(body)
                if ans:
                    found[key] = ans
    return found


def _section_map(text: str) -> dict[str, str]:
    lines = str(text).splitlines()
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []

    def flush() -> None:
        if current is None:
            return
        body = "\n".join(buf).strip()
        if current not in sections:
            sections[current] = body

    for line in lines:
        m = _HEADING.match(line)
        if m:
            flush()
            current = _norm_heading(m.group(2))
            buf = []
            continue
        if current is not None:
            buf.append(line)
    flush()
    return sections


def _norm_heading(title: str) -> str:
    t = title.strip().lower()
    t = re.sub(r"^#+\s*", "", t)
    return re.sub(r"\s+", " ", t)


def _answer_from(body: str) -> str:
    m = re.search(r"\*\*A:\*\*\s*(.*)", body, re.S)
    if m:
        return _clean_block(m.group(1))
    lines: list[str] = []
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        low = s.lower()
        if s.endswith("?") or low.startswith("what exists") or low.startswith("where does"):
            continue
        if low.startswith("what is explicitly"):
            continue
        lines.append(s)
    return _clean_block("\n".join(lines))


def _merge_key_lines(text: str, found: dict[str, Any]) -> None:
    lines = str(text).splitlines()
    i = 0
    while i < len(lines):
        m = _KEY_LINE.match(lines[i].strip())
        if not m:
            i += 1
            continue
        key = re.sub(r"\s+", " ", m.group(1).strip().lower())
        first = m.group(2).strip()
        block = [first] if first else []
        i += 1
        while i < len(lines):
            nxt = lines[i]
            stripped = nxt.strip()
            if not stripped:
                if block:
                    break
                i += 1
                continue
            if _KEY_LINE.match(stripped) or _HEADING.match(stripped):
                break
            if key != "done when" and stripped.startswith("#"):
                break
            block.append(stripped)
            i += 1
        body = "\n".join(block).strip()
        if key == "done when":
            if "done_when" not in found or not found["done_when"]:
                found["done_when"] = _checks_from(body)
        elif key not in found or not found.get(key):
            if key == "spine":
                found[key] = _one_line(body)
            else:
                found[key] = _clean_block(body)


def _fill_heuristic(raw: str, found: dict[str, Any]) -> None:
    if not found.get("surface"):
        live = _LIVE_AT.search(raw)
        if live:
            found["surface"] = _strip_sentence_tail(live.group("s"))
    fence_spans: list[tuple[int, int]] = []
    fence_bits: list[str] = []
    for m in _FENCE_SPAN.finditer(raw):
        bit = next((g for g in m.groups() if g), "")
        bit = _strip_sentence_tail(bit)
        if bit:
            fence_bits.append(bit)
            fence_spans.append((m.start(), m.end()))
    if not found.get("fence") and fence_bits:
        found["fence"] = "; ".join(fence_bits)
    if not found.get("surface"):
        for m in _PATH.finditer(raw):
            if any(m.start() >= a and m.end() <= b for a, b in fence_spans):
                continue
            found["surface"] = m.group(0).rstrip(".,;:")
            break
    if not found.get("outcome"):
        want = _WANT.search(raw)
        if want:
            found["outcome"] = _strip_sentence_tail(want.group("o"))
            low = found["outcome"].lower()
            if low.startswith("a "):
                found["outcome"] = found["outcome"][0].upper() + found["outcome"][1:]
            elif found["outcome"] and found["outcome"][0].islower():
                found["outcome"] = found["outcome"][0].upper() + found["outcome"][1:]
        else:
            remainder = _remainder_outcome(raw, found)
            if remainder:
                found["outcome"] = remainder


def _remainder_outcome(raw: str, found: dict[str, Any]) -> str:
    text = raw
    live = _LIVE_AT.search(text)
    if live:
        text = text[: live.start()] + text[live.end() :]
    for m in list(_FENCE_SPAN.finditer(text))[::-1]:
        text = text[: m.start()] + text[m.end() :]
    surface = found.get("surface") or ""
    if surface and surface != _NOT_NAMED:
        text = text.replace(surface, " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[.;,]+\s*$", "", text).strip(" .;,-")
    return _clean_block(text)


def _checks_from(body: str) -> list[str]:
    items: list[str] = []
    for line in str(body).splitlines():
        s = line.strip()
        if not s:
            continue
        m = _CHECK_LINE.match(s) or _BARE_CHECK.match(s)
        if m:
            items.append(_one_line(m.group(1)))
        elif not items:
            items.append(_one_line(s))
    return [x for x in items if x]


def _clean_checks(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        line = _one_line(item)
        key = line.lower()
        if not line or key in seen:
            continue
        seen.add(key)
        out.append(line)
    return out


def _derive_done_when(outcome: str) -> list[str]:
    line = _one_line(outcome)
    if not line:
        return ["Packet has spine, outcome, surface, fence, and a done-when check"]
    if line[-1] in ".!?":
        line = line[:-1]
    return [line]


def _spine_from(text: str) -> str:
    line = _one_line(text)
    if len(line) > 160:
        line = line[:157].rstrip() + "..."
    return line


def _one_line(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _clean_block(text: str) -> str:
    lines = [ln.rstrip() for ln in str(text or "").splitlines()]
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines).strip()


def _strip_sentence_tail(text: str) -> str:
    s = _one_line(text)
    s = s.strip(" \t\"'")
    if s.endswith(".") and not re.search(r"\.[A-Za-z0-9]{1,4}$", s[:-1]):
        s = s[:-1].rstrip()
    return s
