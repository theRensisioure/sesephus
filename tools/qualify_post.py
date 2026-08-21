#!/usr/bin/env python3
"""Single-post Systems Peer qualification via vLLM OpenAI API (LeadLogic PR2 wire)."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request

DEFAULT_URL = os.environ.get("LOCAL_LLM_URL", "http://localhost:8000/v1/chat/completions")
DEFAULT_MODEL = os.environ.get("LOCAL_LLM_MODEL", "Crownelius/Crow-9B-HERETIC-4.6")
DEFAULT_SERVICE = os.environ.get("SALES_INTENT", "developers and founders discussing technical pain points")


def extract_system_block(prompt_md: str) -> str:
    m = re.search(
        r"## System instruction\s+```\s*(.*?)```",
        prompt_md,
        re.DOTALL | re.IGNORECASE,
    )
    if not m:
        raise ValueError("Could not find system instruction code block in prompt file")
    return m.group(1).strip()


def apply_service_type(system: str, service_type: str) -> str:
    focus = f'indicating an active or implicit pain point/problem space related to "{service_type}"'
    return (
        system.replace("{{focusInstruction}}", focus)
        .replace("{{serviceType}}", service_type)
    )


def build_user_message(post: str, handle: str | None, did: str | None) -> str:
    if handle or did:
        h = handle or did or "unknown"
        did_val = did or h
        profile = f"https://bsky.app/profile/{h}"
        return (
            f"Analyze this Bluesky post:\n"
            f"Author DID: {did_val}\n"
            f"Handle: {h}\n"
            f"Profile: {profile}\n"
            f"Post: {post}\n\n"
            "Return a valid JSON object matching the schema, or return an empty object {} if irrelevant."
        )
    return (
        f"Analyze this post:\n"
        f"Title: (cli)\n"
        f"Content: {post}\n"
        f"Author: unknown\n"
        f"Url: \n"
        f"Platform: cli\n\n"
        "Return a valid JSON object matching the schema, or return null if irrelevant."
    )


def call_vllm(system: str, user: str, url: str, model: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.0,
        "max_tokens": 450,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        print(
            f"[LeadLogic] vLLM unreachable at {url}: {e}\n"
            "Start vLLM (e.g. .\\run_vllm.ps1 in LeadLogic-Engine) or set LOCAL_LLM_URL.",
            file=sys.stderr,
        )
        sys.exit(2)
    return data.get("choices", [{}])[0].get("message", {}).get("content", "")


def parse_lead(raw: str) -> dict | None:
    trimmed = raw.strip()
    if not trimmed or trimmed == "{}" or trimmed.lower() == "null":
        return None
    start = trimmed.find("{")
    end = trimmed.rfind("}") + 1
    if start == -1 or end == 0:
        return None
    try:
        lead = json.loads(trimmed[start:end])
        if not lead or not lead.get("name"):
            return None
        return lead
    except json.JSONDecodeError:
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description="Qualify one post via Systems Peer + vLLM")
    ap.add_argument("--prompt-path", required=True, help="Resolved path to qualify-post.md")
    ap.add_argument("--post", required=True, help="Post text to qualify")
    ap.add_argument("--handle", default=None, help="Bluesky handle (optional)")
    ap.add_argument("--did", default=None, help="Bluesky DID (optional)")
    ap.add_argument("--service-type", default=DEFAULT_SERVICE)
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    args = ap.parse_args()

    prompt_md = open(args.prompt_path, encoding="utf-8").read()
    system = apply_service_type(extract_system_block(prompt_md), args.service_type)
    user = build_user_message(args.post, args.handle, args.did)

    raw = call_vllm(system, user, args.url, args.model)
    lead = parse_lead(raw)
    if lead is None:
        print(json.dumps({"qualified": False, "raw": raw[:500]}))
        sys.exit(0)
    lead["qualification"] = "vllm-systems-peer"
    lead["prompt_path"] = args.prompt_path
    print(json.dumps(lead, ensure_ascii=False))


if __name__ == "__main__":
    main()