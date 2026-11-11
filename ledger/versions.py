"""Fold decision state-changes in transcript order."""

from __future__ import annotations


def resolve_state(ledger: dict, uid: str) -> dict[str, str]:
    state: dict[str, str] = {}
    found = False
    for decision in ledger["decisions"]:
        state[decision["key"]] = decision["value"]
        if decision["uid"] == uid:
            found = True
            break
    if not found:
        raise KeyError(uid)
    return state
