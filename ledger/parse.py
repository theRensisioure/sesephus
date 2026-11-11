"""Parse explicit EVENT, REASON, and DECISION markers into a flat ledger."""

from __future__ import annotations

import hashlib
import re

_MARKERS = {
    "EVENT": re.compile(r"^EVENT (\S+)$"),
    "REASON": re.compile(r"^REASON (\S+) (\S+)$"),
    "DECISION": re.compile(r"^DECISION (\S+) (\S+) (\S+)$"),
}
_ENDS = {
    "EVENT": "END EVENT",
    "REASON": "END REASON",
    "DECISION": "END DECISION",
}


def _lines(text: str) -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    i = 0
    while i <= len(text):
        j = text.find("\n", i)
        if j < 0:
            rows.append((i, len(text), text[i:]))
            break
        rows.append((i, j, text[i:j]))
        i = j + 1
        if i == len(text):
            break
    return rows


def _uid(decision_id: str, key: str, value: str, start: int) -> str:
    raw = f"{decision_id}\n{key}\n{value}\n{start}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _acyclic(nodes: list[str], edges: list[dict[str, str]]) -> bool:
    incoming = {node: 0 for node in nodes}
    outbound: dict[str, list[str]] = {node: [] for node in nodes}
    for edge in edges:
        src, dst = edge["from"], edge["to"]
        if src not in incoming or dst not in incoming:
            return False
        outbound[src].append(dst)
        incoming[dst] += 1
    ready = [node for node, count in incoming.items() if count == 0]
    seen = 0
    while ready:
        node = ready.pop()
        seen += 1
        for nxt in outbound[node]:
            incoming[nxt] -= 1
            if incoming[nxt] == 0:
                ready.append(nxt)
    return seen == len(nodes)


def build_ledger(text: str) -> dict:
    rows = _lines(text)
    events: list[dict] = []
    decisions: list[dict] = []
    pending_edges: list[tuple[str, str]] = []
    i = 0
    while i < len(rows):
        _start, end, line = rows[i]
        kind = None
        match = None
        for name, pattern in _MARKERS.items():
            match = pattern.match(line)
            if match:
                kind = name
                break
        if kind is None or match is None:
            i += 1
            continue
        body_start = end + 1 if end < len(text) and text[end:end + 1] == "\n" else end
        j = i + 1
        while j < len(rows) and rows[j][2] != _ENDS[kind]:
            j += 1
        if j >= len(rows):
            raise ValueError(f"unclosed {kind}")
        body_end = rows[j][0]
        body = text[body_start:body_end]
        if kind == "EVENT":
            events.append({
                "id": match.group(1),
                "kind": "event",
                "text": body,
                "span": {"start": body_start, "end": body_end},
            })
        elif kind == "DECISION":
            decision_id, key, value = match.group(1), match.group(2), match.group(3)
            uid = _uid(decision_id, key, value, body_start)
            record = {
                "id": decision_id,
                "kind": "decision",
                "text": body,
                "span": {"start": body_start, "end": body_end},
                "uid": uid,
                "change": {"key": key, "value": value},
            }
            events.append(record)
            decisions.append({
                "id": decision_id,
                "uid": uid,
                "key": key,
                "value": value,
                "span": {"start": body_start, "end": body_end},
            })
        else:
            pending_edges.append((match.group(1), match.group(2)))
        i = j + 1

    ids = [event["id"] for event in events]
    if len(ids) != len(set(ids)):
        raise ValueError("event ids must be unique")
    uids = [item["uid"] for item in decisions]
    if len(uids) != len(set(uids)):
        raise ValueError("decision uids must be unique")
    known = set(ids)
    edges = [{"from": src, "to": dst} for src, dst in pending_edges if src in known and dst in known]
    if not _acyclic(ids, edges):
        raise ValueError("reason curve is cyclic")
    return {
        "events": events,
        "decisions": decisions,
        "curve": {"nodes": ids, "edges": edges},
    }
