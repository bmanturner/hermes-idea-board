"""Find evidence for ideas in code, before any model runs.

Input is a list of normalized sessions (built by ``transcripts.py`` or by test fixtures):

    {"id": str, "source": str, "title": str, "started_at": float, "last_active": float,
     "end_reason": str | None,
     "turns": [{"role": "user" | "assistant" | "tool", "ts": float, "text": str,
                "tool_name": str | None, "tool_error": bool}]}

``user`` turns hold only what the user typed (see ``text.clean_user_text``). ``assistant`` text is
used for fixed-phrase detection only and never leaves this module. ``tool`` turns carry a name and
an error flag, no content.

Output: evidence items the model may cite by id. Every ``quote`` is either the user's own words or a
sentence this module wrote, so nothing fetched from mail or the web can reach the ideation prompt
through a quote.
"""
from __future__ import annotations

import datetime as dt
import math
import re
from collections import defaultdict
from typing import Any

from .text import clip, content_tokens, jaccard, squash

KIND_WEIGHT = {
    "repeat": 3.0,
    "open_loop": 2.5,
    "dated": 2.5,
    "wish": 2.5,
    "manual_relay": 2.0,
    "tool_friction": 2.0,
    "correction": 1.5,
}

_OPEN_LOOP_USER = re.compile(
    r"\b(remind me|don'?t let me forget|follow up|later today|tomorrow|next week|next month|"
    r"when i get a chance|circle back|to-?do)\b", re.I)
_OFFER_ASSISTANT = re.compile(r"\b(want me to|shall i|should i|i can also|would you like me to)\b", re.I)
_CORRECTION = re.compile(
    r"^\s*(no[,.! ]|nope\b|not that\b|that'?s (wrong|not)|i meant\b|wrong\b|again[,.! ]|still (wrong|not)\b|"
    r"use .{1,40} (not|instead)\b|instead[,.! ])", re.I)
_WISH_USER = re.compile(
    r"\b(i wish|is there a way|can you (check|read|look|access|see|pull|get)|could you (check|read|access|pull))\b",
    re.I)
_CANT_ASSISTANT = re.compile(
    r"\b(i can'?t|i cannot|i don'?t have access|i'?m not able to|no access to|not connected|isn'?t connected|"
    r"unable to access)\b", re.I)
_RELAY_VERB = re.compile(
    r"\b(summari[sz]e|reformat|extract|turn (this|it) into|convert|clean (this|it) up|rewrite|translate|"
    r"draft|make (a|this) (table|list)|pull out)\b", re.I)
_EMOTION = re.compile(r"\b(ugh|annoying|hate|tedious|every (single )?time|again and again|so tired of|sick of)\b",
                      re.I)
_MONTHS = ("january february march april may june july august september october november december").split()
_DATE_ISO = re.compile(r"\b(20\d\d)-(\d\d)-(\d\d)\b")
_DATE_MD = re.compile(r"\b(" + "|".join(m[:3] for m in _MONTHS) + r")[a-z]*\.? (\d{1,2})(st|nd|rd|th)?\b", re.I)
_DATE_WORDS = re.compile(
    r"\b(next (monday|tuesday|wednesday|thursday|friday|saturday|sunday|week)|this (friday|weekend)|"
    r"due|deadline|appointment|renewal|expires?|flight|trip|birthday|anniversary)\b", re.I)

RELAY_MIN_CHARS = 800
REPEAT_THRESHOLD = 0.5
MAX_EVIDENCE = 40


def _day(ts: float) -> str:
    return dt.datetime.fromtimestamp(ts).date().isoformat()


def _parse_date(text: str, now: dt.datetime) -> str | None:
    m = _DATE_ISO.search(text)
    if m:
        try:
            return dt.date(int(m[1]), int(m[2]), int(m[3])).isoformat()
        except ValueError:
            return None
    m = _DATE_MD.search(text)
    if m:
        month = [x[:3] for x in _MONTHS].index(m[1][:3].lower()) + 1
        try:
            day = dt.date(now.year, month, int(m[2]))
        except ValueError:
            return None
        if day < now.date() - dt.timedelta(days=60):
            day = day.replace(year=now.year + 1)
        return day.isoformat()
    return None


def _user_quote(text: str, limit: int = 200) -> str:
    """A quote from a user turn. Long pastes are summarized by shape, not quoted."""
    text = squash(text)
    if len(text) < RELAY_MIN_CHARS:
        return clip(text, limit)
    lines = [squash(x) for x in re.split(r"[\n.?!]", text) if squash(x)]
    ask = next((x for x in reversed(lines) if _RELAY_VERB.search(x) and len(x) < 160), "")
    return clip(f"[pasted ~{len(text)} chars] {ask}".strip(), limit)


def extract(sessions: list[dict[str, Any]], *, now: dt.datetime | None = None,
            today_hours: int = 24) -> list[dict[str, Any]]:
    """Return ranked evidence items: id, kind, quote, session_ids, days, count, last_seen,
    strength, plus ``expires`` (dated) and ``tool`` (tool_friction)."""
    now = now or dt.datetime.now()
    today_cut = now.timestamp() - today_hours * 3600
    items: list[dict[str, Any]] = []
    user_msgs: list[tuple[str, float, str, set[str]]] = []  # (session_id, ts, text, tokens)
    tool_errors: dict[str, list[tuple[str, float]]] = defaultdict(list)
    emotional: set[str] = set()

    for s in sessions:
        sid = s["id"]
        turns = s.get("turns") or []
        last_assistant = ""
        for i, t in enumerate(turns):
            role, text, ts = t.get("role"), t.get("text") or "", float(t.get("ts") or s.get("last_active") or 0)
            if role == "tool":
                if t.get("tool_error") and t.get("tool_name"):
                    tool_errors[t["tool_name"]].append((sid, ts))
                continue
            if role == "assistant":
                last_assistant = text
                continue
            if role != "user" or not text.strip():
                continue
            user_msgs.append((sid, ts, text, content_tokens(text)))
            if _EMOTION.search(text):
                emotional.add(sid)
            if _OPEN_LOOP_USER.search(text):
                items.append(_item("open_loop", sid, ts, _user_quote(text)))
            if last_assistant and _CORRECTION.search(text):
                items.append(_item("correction", sid, ts, _user_quote(text)))
            if len(squash(text)) >= RELAY_MIN_CHARS:
                items.append(_item("manual_relay", sid, ts, _user_quote(text)))
            if _DATE_WORDS.search(text) or _DATE_ISO.search(text) or _DATE_MD.search(text):
                when = _parse_date(text, now)
                if when is None or when >= now.date().isoformat():
                    it = _item("dated", sid, ts, _user_quote(text))
                    it["expires"] = when
                    items.append(it)
            if _WISH_USER.search(text):
                nxt = next((u for u in turns[i + 1:] if u.get("role") == "assistant"), None)
                if nxt and _CANT_ASSISTANT.search(nxt.get("text") or ""):
                    items.append(_item("wish", sid, ts, _user_quote(text)))
        # The agent offered something and the user never answered.
        if turns and turns[-1].get("role") == "assistant" and _OFFER_ASSISTANT.search(turns[-1].get("text") or ""):
            last_user = next((t for t in reversed(turns) if t.get("role") == "user" and (t.get("text") or "").strip()),
                             None)
            if last_user:
                offer = _offer_sentence(turns[-1].get("text") or "")
                note = (f"the agent already answered this and offered a next step: \"{offer}\"; no reply"
                        if offer else "the agent offered a next step; no reply")
                items.append(_item("open_loop", sid, float(last_user.get("ts") or 0),
                                   _user_quote(last_user["text"]), note=note))

    items.extend(_repeats(user_msgs))
    for tool, hits in tool_errors.items():
        if len(hits) >= 2:
            sids = sorted({h[0] for h in hits})
            it = _item("tool_friction", sids[0], max(h[1] for h in hits),
                       f"The {tool} tool failed {len(hits)} times across {len(sids)} chat(s).")
            it.update(session_ids=sids, count=len(hits), tool=tool)
            items.append(it)

    for it in items:
        recency = 1.0 if it["last_seen"] >= today_cut else 0.6
        boost = 0.5 if any(s in emotional for s in it["session_ids"]) else 0.0
        it["strength"] = round(KIND_WEIGHT[it["kind"]] * math.log2(1 + it["count"]) * recency + boost, 3)
        it["today"] = it["last_seen"] >= today_cut

    items = _dedupe(items)
    items.sort(key=lambda x: (-x["strength"], -x["last_seen"]))
    items = items[:MAX_EVIDENCE]
    for n, it in enumerate(items, 1):
        it["id"] = f"E{n}"
        it["days"] = sorted({_day(ts) for ts in it.pop("_ts")})
        it["last_seen_day"] = _day(it["last_seen"])
    return items


def _offer_sentence(text: str, limit: int = 160) -> str:
    """The sentence in which the agent offered a next step, so ideas follow up on the offer instead of
    redoing work the agent already did. Model input only; cards quote the user, never this."""
    for sentence in reversed(re.split(r"(?<=[.?!])\s+", squash(text))):
        if _OFFER_ASSISTANT.search(sentence):
            return clip(sentence, limit)
    return ""


def _item(kind: str, sid: str, ts: float, quote: str, note: str | None = None) -> dict[str, Any]:
    it = {"kind": kind, "session_ids": [sid], "quote": quote, "count": 1, "last_seen": ts, "_ts": [ts]}
    if note:
        it["note"] = note
    return it


def _repeats(user_msgs: list[tuple[str, float, str, set[str]]]) -> list[dict[str, Any]]:
    """Cluster similar asks; keep clusters seen on 2+ different days."""
    clusters: list[list[tuple[str, float, str, set[str]]]] = []
    for msg in user_msgs:
        if len(msg[3]) < 3:
            continue
        for c in clusters:
            if jaccard(c[0][3], msg[3]) >= REPEAT_THRESHOLD:
                c.append(msg)
                break
        else:
            clusters.append([msg])
    out = []
    for c in clusters:
        days = {_day(m[1]) for m in c}
        if len(days) < 2:
            continue
        newest = max(c, key=lambda m: m[1])
        it = _item("repeat", newest[0], newest[1], _user_quote(newest[2]))
        it.update(session_ids=sorted({m[0] for m in c}), count=len(c), _ts=[m[1] for m in c],
                  note=f"asked on {len(days)} different days")
        out.append(it)
    return out


def _dedupe(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One item per (kind, quote); merge their sessions and counts."""
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for it in items:
        key = (it["kind"], it["quote"].lower())
        if key in merged:
            m = merged[key]
            m["session_ids"] = sorted(set(m["session_ids"]) | set(it["session_ids"]))
            m["count"] += it["count"]
            m["_ts"] += it["_ts"]
            m["last_seen"] = max(m["last_seen"], it["last_seen"])
            m["strength"] = max(m["strength"], it["strength"])
        else:
            merged[key] = it
    return list(merged.values())


def capability_usage(sessions: list[dict[str, Any]]) -> dict[str, int]:
    """Tool name → number of calls across the sessions (from tool turns)."""
    counts: dict[str, int] = defaultdict(int)
    for s in sessions:
        for t in s.get("turns") or []:
            if t.get("role") == "tool" and t.get("tool_name"):
                counts[t["tool_name"]] += 1
    return dict(counts)
