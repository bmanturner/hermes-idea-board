"""Assemble the context packet for one run from the inventory, recent chats, evidence and the board."""
from __future__ import annotations

import datetime as dt
from collections import Counter
from typing import Any

from . import safety, signals
from .store import Store
from .text import clip

MAX_CHATS = 60
TODAY_HOURS = 24


def build(inventory: dict[str, Any], sessions: list[dict[str, Any]], store: Store, *,
          seeds: list[dict[str, Any]] | None = None, now: dt.datetime | None = None) -> dict[str, Any]:
    now = now or dt.datetime.now().astimezone()
    evidence = signals.extract(sessions, now=now.replace(tzinfo=None) if now.tzinfo else now,
                               today_hours=TODAY_HOURS)
    caps = inventory["capabilities"]
    tool_to_cap = inventory.get("tool_to_cap") or {}
    usage: Counter[str] = Counter()
    for tool, n in signals.capability_usage(sessions).items():
        cap = tool_to_cap.get(tool)
        if cap:
            usage[cap] += n
    ready = [c["id"] for c in caps if c["status"] == "ready" and c["kind"] in ("toolset", "mcp", "connector")]
    chats = []
    for s in sorted(sessions, key=lambda x: -x["last_active"])[:MAX_CHATS]:
        tools = Counter(t["tool_name"] for t in s["turns"] if t.get("role") == "tool" and t.get("tool_name"))
        title = clip(s.get("title") or "", 70)
        if safety.threats(title):
            title = "(title withheld)"
        chats.append({
            "id": s["id"], "day": dt.datetime.fromtimestamp(s["last_active"]).strftime("%a %Y-%m-%d"),
            "source": s.get("source"), "title": title,
            "user_turns": sum(1 for t in s["turns"] if t.get("role") == "user"),
            "top_tools": [t for t, _ in tools.most_common(5)],
        })
    # Links a card may carry must come from short messages the user typed, not from long pastes
    # (a pasted email is someone else's words and may carry a planted link).
    user_texts = [t["text"] for s in sessions for t in s["turns"]
                  if t.get("role") == "user" and len(t["text"]) < signals.RELAY_MIN_CHARS]
    return {
        "now": now.strftime("%A %Y-%m-%d %H:%M %Z"),
        "profile": inventory.get("profile") or "",
        "capabilities": [{k: c[k] for k in ("id", "kind", "name", "status", "can_do", "tools") if k in c}
                         for c in caps],
        "automations": inventory.get("automations") or {"jobs": [], "suggested": []},
        "usage": {cap: usage.get(cap, 0) for cap in ready},
        "chats": chats,
        "evidence": [{k: e[k] for k in ("id", "kind", "quote", "session_ids", "days", "count", "today", "note",
                                         "expires", "tool") if k in e} for e in evidence],
        "board": store.history_for_prompt(),
        "seeds": seeds or [],
        "user_corpus": safety.corpus(user_texts),
        "notes": inventory.get("notes") or [],
    }
