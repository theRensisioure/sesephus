#!/usr/bin/env python3
"""Prompt + paste leftover rank. Voice transcript is the prompt. Paste is the corpus.

Compose leftover pass, shipped as a function tests can call:
extract open loops only (not live trunk, process chatter, or closed work);
cluster; score 1–5 on leverage · openness · actionability; rank descending;
each cluster: loop · origin · move (pursue now / prompt out / handoff / drop).

Heuristic is the dry path. Optional local 7B may refine wording later; this
module does not require it.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

MOVES = ("pursue now", "prompt out", "handoff", "drop")

_STOP = frozenset(
    {
        "a",
        "an",
        "the",
        "to",
        "of",
        "and",
        "or",
        "for",
        "in",
        "on",
        "is",
        "it",
        "we",
        "i",
        "you",
        "this",
        "that",
        "from",
        "with",
        "as",
        "be",
        "are",
        "was",
        "at",
        "by",
        "not",
        "do",
        "did",
        "has",
        "have",
        "also",
        "just",
        "still",
        "need",
        "rank",
        "drop",
        "skip",
        "focus",
        "only",
        "work",
        "chores",
        "leftovers",
        "leftover",
        "open",
        "loops",
        "loop",
        "please",
        "about",
        "into",
        "then",
    }
)

_HOUSEHOLD = frozenset(
    {
        "grocery",
        "groceries",
        "oat",
        "milk",
        "car",
        "inspection",
        "chore",
        "household",
        "shopping",
        "errand",
        "fridge",
        "laundry",
    }
)
_PRODUCT = frozenset(
    {
        "sesefus",
        "hop",
        "vault",
        "meter",
        "mixer",
        "zig",
        "daemon",
        "clip",
        "journal",
        "alarm",
        "recorder",
        "circadia",
        "ssfs",
        "backup",
        "ui",
    }
)

_CLOSED = re.compile(
    r"\b("
    r"already (shipped|did|done|landed|merged|finished)|"
    r"we (already )?(shipped|finished|closed|landed)|"
    r"completed|resolved|merged into|shipped the"
    r")\b",
    re.I,
)
_CHATTER = re.compile(
    r"\b("
    r"thanks|thank you|anyway|as i said|status dump|"
    r"tests passed|the agent |compileall|ok then|got it"
    r")\b",
    re.I,
)
_OPEN = re.compile(
    r"\b("
    r"still|need to|leftover|hanging|parked|should|"
    r"todo|unfinished|remaining|waiting|overdue|"
    r"deferred|open loop|not this sitting|wire|fix|"
    r"inspect|brief another"
    r")\b",
    re.I,
)
_TRUNK = re.compile(r"\b(currently doing|live trunk|in flight now|this sitting is)\b", re.I)


@dataclass
class Cluster:
    loop: str
    origin: str
    move: str
    score: int
    leverage: int
    openness: int
    actionability: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Analysis:
    ok: bool
    error: str | None
    prompt: str
    clusters: list[Cluster] = field(default_factory=list)
    dropped_closed: int = 0
    dropped_chatter: int = 0
    dropped_trunk: int = 0
    mouth: str = "heuristic"

    def render(self) -> str:
        if not self.ok:
            return f"tangent analysis failed.\n{self.error or 'unknown error'}"
        if not self.clusters:
            return (
                "tangent analysis\n"
                f"prompt: {self.prompt.strip() or '(empty)'}\n\n"
                "no open loops in the paste (closed/chatter/trunk stripped)."
            )
        lines = [
            "tangent analysis",
            f"prompt: {self.prompt.strip()}",
            f"mouth: {self.mouth}",
            "",
        ]
        for i, c in enumerate(self.clusters, 1):
            lines.append(f"{i}. [{c.score}] {c.loop}")
            lines.append(f"   loop · {c.loop}")
            lines.append(f"   origin · {c.origin}")
            lines.append(f"   move · {c.move}")
            lines.append(
                f"   leverage {c.leverage} · openness {c.openness} · actionability {c.actionability}"
            )
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "error": self.error,
            "prompt": self.prompt,
            "clusters": [c.as_dict() for c in self.clusters],
            "dropped_closed": self.dropped_closed,
            "dropped_chatter": self.dropped_chatter,
            "dropped_trunk": self.dropped_trunk,
            "mouth": self.mouth,
            "analysis": self.render() if self.ok else (self.error or ""),
        }


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if w not in _STOP and len(w) > 2}


def _split_items(paste: str) -> list[str]:
    items: list[str] = []
    for raw in (paste or "").splitlines():
        s = raw.strip()
        if not s:
            continue
        s = re.sub(r"^[-*•]+\s+", "", s)
        s = re.sub(r"^\d+[.)]\s+", "", s)
        parts = re.split(r"\s+and also\s+", s, flags=re.I)
        for p in parts:
            p = p.strip(" .;\t")
            if p:
                items.append(p)
    return items


def _classify(item: str) -> str:
    if _CLOSED.search(item):
        return "closed"
    if _CHATTER.search(item) and not _OPEN.search(item):
        return "chatter"
    if _TRUNK.search(item):
        return "trunk"
    if _OPEN.search(item):
        return "open"
    if len(item.split()) >= 8:
        return "open"
    return "chatter"


def _drop_domains(prompt: str) -> set[str]:
    low = (prompt or "").lower()
    dropped: set[str] = set()
    if re.search(r"\bdrop(?:ping)?\s+household\b", low) or re.search(
        r"\bskip household\b", low
    ):
        dropped |= _HOUSEHOLD
    if re.search(r"\bdrop(?:ping)?\s+product\b", low) or re.search(
        r"\bskip product\b", low
    ):
        dropped |= _PRODUCT
    m = re.search(r"\b(?:drop|skip)\s+([^,.]+)", low)
    if m:
        dropped |= _tokens(m.group(1))
    return dropped


def _keep_domains(prompt: str) -> set[str]:
    low = (prompt or "").lower()
    keep: set[str] = set()
    if re.search(r"\b(rank|focus|only)\s+household\b", low):
        keep |= _HOUSEHOLD
    if re.search(r"\b(rank|focus|only)\s+(sesefus\s+)?product\b", low):
        keep |= _PRODUCT
    m = re.search(r"\b(?:rank|focus|only)\s+([^,.]+)", low)
    if m:
        keep |= _tokens(m.group(1))
    keep -= {"household", "product", "sesefus"}
    return keep


def _origin(item: str) -> str:
    low = item.lower()
    for name in (
        "hop",
        "vault",
        "circadia",
        "journal-daemon",
        "clip",
        "sesefus",
        "grocery",
        "car",
        "household",
    ):
        if name in low:
            return name
    words = item.split()
    return " ".join(words[:6]).rstrip(",.;")


def _scores(item: str, prompt_tok: set[str], item_tok: set[str]) -> tuple[int, int, int, int]:
    overlap = len(prompt_tok & item_tok)
    lev = 2
    if overlap:
        lev += min(2, overlap)
    if re.search(r"\b(friday|blocker|overdue|before)\b", item, re.I):
        lev += 1
    if re.search(r"\b(vault|backup|inspect|wire)\b", item, re.I):
        lev += 1
    lev = max(1, min(5, lev))

    op = 3
    if re.search(r"\b(still|parked|unfinished|leftover|overdue)\b", item, re.I):
        op = 4
    if re.search(r"\balmost\b", item, re.I):
        op = 2
    op = max(1, min(5, op))

    act = 2
    if re.search(r"\b(wire|fix|inspect|buy|land|delete|rank|brief|open|file)\b", item, re.I):
        act = 4
    if re.search(r"\b(before friday|overdue)\b", item, re.I):
        act = 5
    act = max(1, min(5, act))

    composite = int(round((lev + op + act) / 3.0))
    composite = max(1, min(5, composite))
    if overlap >= 2:
        composite = max(composite, 4)
        composite = min(5, composite)
    return composite, lev, op, act


def _move(item: str, prompt: str, score: int, dropped: bool) -> str:
    low = (item + " " + prompt).lower()
    if dropped or score <= 2:
        return "drop"
    if re.search(r"\b(handoff|brief another|other agent)\b", low):
        return "handoff"
    if re.search(r"\b(later|defer|branch|prompt out)\b", low):
        return "prompt out"
    if score >= 4:
        return "pursue now"
    if score >= 3:
        return "pursue now"
    return "drop"


def _cluster_items(items: list[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    used = [False] * len(items)
    for i, a in enumerate(items):
        if used[i]:
            continue
        ta = _tokens(a)
        g = [a]
        used[i] = True
        for j, b in enumerate(items):
            if used[j] or i == j:
                continue
            tb = _tokens(b)
            if not ta or not tb:
                continue
            inter = len(ta & tb)
            union = len(ta | tb)
            if union and inter / union >= 0.45:
                g.append(b)
                used[j] = True
        groups.append(g)
    return groups


def analyze(prompt: str, paste: str, *, mouth: str = "heuristic") -> Analysis:
    """Shipped leftover transform. Prompt steers. Paste is the only corpus."""
    p = (prompt or "").strip()
    body = (paste or "").strip()
    if not p:
        return Analysis(ok=False, error="empty prompt", prompt=p, mouth=mouth)
    if not body:
        return Analysis(ok=False, error="empty paste", prompt=p, mouth=mouth)

    closed = chatter = trunk = 0
    kept: list[str] = []
    for item in _split_items(body):
        kind = _classify(item)
        if kind == "closed":
            closed += 1
            continue
        if kind == "chatter":
            chatter += 1
            continue
        if kind == "trunk":
            trunk += 1
            continue
        kept.append(item)

    prompt_tok = _tokens(p)
    drop_lex = _drop_domains(p)
    keep_lex = _keep_domains(p)

    steered: list[str] = []
    for item in kept:
        it = _tokens(item)
        if drop_lex and (it & drop_lex):
            continue
        steered.append(item)

    if keep_lex:
        focused = [item for item in steered if _tokens(item) & keep_lex]
        if focused:
            steered = focused

    groups = _cluster_items(steered)
    clusters: list[Cluster] = []
    for g in groups:
        loop = g[0]
        origin = _origin(loop)
        item_tok = _tokens(" ".join(g))
        dropped_flag = False
        score, lev, op, act = _scores(loop, prompt_tok, item_tok)
        move = _move(loop, p, score, dropped_flag)
        clusters.append(
            Cluster(
                loop=loop,
                origin=origin,
                move=move,
                score=score,
                leverage=lev,
                openness=op,
                actionability=act,
            )
        )

    clusters.sort(
        key=lambda c: (
            -c.score,
            -len(_tokens(c.loop) & prompt_tok),
            c.loop.lower(),
        )
    )
    return Analysis(
        ok=True,
        error=None,
        prompt=p,
        clusters=clusters,
        dropped_closed=closed,
        dropped_chatter=chatter,
        dropped_trunk=trunk,
        mouth=mouth,
    )
