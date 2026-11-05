"""Read recent chats from the Hermes session store into the normalized shape ``signals`` expects.

Hermes adapter: imports ``hermes_state`` (public) lazily. Skips scheduled-job runs, subagents,
hidden and child sessions, and group chats (other people's words). Only user-typed turns keep their
text for quoting; assistant text is kept short for phrase checks; tool turns keep a name and an
error flag.
"""
from __future__ import annotations

import json
import time
from typing import Any

from .text import clean_user_text

EXCLUDED_SOURCES = ["cron", "subagent"]
GROUP_CHAT_TYPES = {"group", "supergroup", "channel", "thread", "guild"}
TYPED_KINDS = {None, "", "steer"}
ASSISTANT_KEEP = 400
MAX_TURNS_PER_SESSION = 120


def _tool_failed(content: Any) -> bool:
    if isinstance(content, str):
        head = content.lstrip()[:200].lower()
        if head.startswith(("error", "blocked", "traceback")):
            return True
        try:
            content = json.loads(content)
        except (ValueError, TypeError):
            return '"error":' in head and '"error": null' not in head
    if isinstance(content, dict):
        if content.get("success") is False or content.get("ok") is False:
            return True
        err = content.get("error")
        return bool(err) and err not in ("", None)
    return False


def load_sessions(*, history_days: int = 14, max_sessions: int = 150,
                  exclude_ids: set[str] | None = None, db: Any = None) -> list[dict[str, Any]]:
    from hermes_state import SessionDB

    own = db is None
    db = db or SessionDB()
    try:
        cutoff = time.time() - history_days * 86400
        rows = db.list_sessions_rich(exclude_sources=EXCLUDED_SOURCES, order_by_last_active=True,
                                     limit=max_sessions, min_message_count=2)
        out = []
        for r in rows:
            last = float(r.get("last_active") or r.get("started_at") or 0)
            if last < cutoff:
                break
            if r.get("parent_session_id") or r.get("hidden") or (exclude_ids and r["id"] in exclude_ids):
                continue
            info = db.get_session(r["id"]) or {}
            if str(info.get("chat_type") or "").lower() in GROUP_CHAT_TYPES:
                continue
            out.append(_normalize(r, db.get_messages(r["id"])))
        return out
    finally:
        if own:
            close = getattr(db, "close", None)
            if close:
                close()


def _normalize(row: dict[str, Any], messages: list[dict[str, Any]]) -> dict[str, Any]:
    turns = []
    for m in messages[-MAX_TURNS_PER_SESSION:]:
        role, ts = m.get("role"), float(m.get("timestamp") or 0)
        if role == "user":
            if m.get("display_kind") not in TYPED_KINDS:
                continue
            raw = m.get("content")
            text = clean_user_text(raw if isinstance(raw, str) else "")
            if text:
                turns.append({"role": "user", "ts": ts, "text": text})
        elif role == "assistant":
            if m.get("display_kind") == "hidden":
                continue
            text = m.get("content") if isinstance(m.get("content"), str) else ""
            if text:
                turns.append({"role": "assistant", "ts": ts,
                              "text": text[:ASSISTANT_KEEP] + ("\n" + text[-ASSISTANT_KEEP:] if len(text) > 2 * ASSISTANT_KEEP else "")})
        elif role == "tool":
            turns.append({"role": "tool", "ts": ts, "tool_name": m.get("tool_name"),
                          "tool_error": _tool_failed(m.get("content"))})
    return {
        "id": row["id"], "source": row.get("source") or "", "title": row.get("title") or "",
        "started_at": float(row.get("started_at") or 0), "last_active": float(row.get("last_active") or 0),
        "end_reason": row.get("end_reason"), "turns": turns,
    }
