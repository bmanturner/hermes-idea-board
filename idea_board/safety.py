"""Safety for model-written prompts. Code, not the model, decides what a card may carry.

The prompt a card places in the composer is written by a model that read the user's chats, and the
user sends it with full tool access. So:

* Every prompt starts with a fixed header (it can't be left out) that asks the agent to show its plan
  and wait for a yes before anything that sends, posts, pays, books, deletes, shares or schedules.
  Because the header comes first, a prompt can never start with a ``/command``.
* ``@kind:`` references are defused: the Desktop composer turns ``@file:``/``@url:`` into
  attachments and fetches.
* Links and email addresses must appear in what the user typed; anything else is rejected.
* A small, vendored set of injection patterns rejects prompts that try to steer the agent.
* The risk badge is computed here and can only go up from what the model claimed.
"""
from __future__ import annotations

import re
from typing import Any, Iterable

HEADER = (
    "[Idea Board · {card_id}] {title}\n"
    "Suggested by the Idea Board plugin from my recent chats. Show me a short plan first. Before "
    "anything that sends, posts, pays, books, deletes, shares or creates a scheduled job, show me "
    "exactly what will happen and wait for my yes.\n\n"
)
FOOTER = "\n\n— Idea Board · {card_id}"
FOOTER_RE = re.compile(r"— Idea Board · (IB-\d{4,})\s*$")

_AT_REF = re.compile(r"(?<![\w`])@([a-z][\w-]*):", re.I)
_URL = re.compile(r"\bhttps?://[^\s<>\"')\]]+", re.I)
_BARE_DOMAIN_URL = re.compile(r"\b(?:www\.)[^\s<>\"')\]]+", re.I)
_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b")
_THREATS = [
    re.compile(p, re.I) for p in (
        r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|messages|rules)",
        r"disregard (all |any |the )?(previous|prior|above|your) ",
        r"\bsystem prompt\b",
        r"\byou are now\b",
        r"\bdo not (tell|show|ask) (me|the user)\b",
        r"\bwithout (asking|telling|confirming)\b",
        r"\bexfiltrat",
        r"\bcurl\b[^\n]*\|\s*(ba)?sh\b",
        r"\bbase64 -d\b",
        r"\brm -rf\b",
        r"~/\.ssh|\bid_rsa\b|BEGIN [A-Z ]*PRIVATE KEY",
        r"(^|[/\s])\.env\b|\bauth\.json\b",
        r"\b(send|post|upload|paste|share|print|read|cat|copy|email)\b.{0,40}\b(api[_ -]?keys?|passwords?|"
        r"tokens?|secrets?|private keys?|seed phrase|credentials?)\b",
        r"</?untrusted",
    )
]
_SENDS = re.compile(
    r"\b(send|sends|sending|post|posts|posting|publish|reply|replies|email|e-mail|message|dm|tweet|pay|"
    r"payment|purchase|buy|book|booking|delete|remove|unsubscribe|share|invite|deploy|transfer)\b", re.I)
RISK_ORDER = ["none", "drafts-for-approval", "external-action"]


def defuse_refs(text: str) -> str:
    """``@file:x`` → ``file:x`` so the composer doesn't attach or fetch anything."""
    return _AT_REF.sub(lambda m: f"{m[1]}:", text)


def links_in(text: str) -> set[str]:
    found = {u.rstrip(".,;:!?").lower() for u in _URL.findall(text)}
    found |= {u.rstrip(".,;:!?").lower() for u in _BARE_DOMAIN_URL.findall(text)}
    found |= {e.lower() for e in _EMAIL.findall(text)}
    return found


def foreign_links(prompt: str, user_corpus: str) -> list[str]:
    """Links or addresses in ``prompt`` that the user never typed."""
    allowed = user_corpus.lower()
    return sorted(x for x in links_in(prompt) if x not in allowed)


def threats(text: str) -> list[str]:
    return [p.pattern for p in _THREATS if p.search(text)]


def risk_level(claimed: str | None, kind: str, body: str) -> str:
    level = claimed if claimed in RISK_ORDER else "none"
    floor = "none"
    if kind == "recurring":
        floor = "drafts-for-approval"
    if _SENDS.search(body):
        floor = "external-action"
    return max(level, floor, key=RISK_ORDER.index)


def build_prompt(card_id: str, title: str, body: str) -> str:
    title = " ".join(title.split())[:80]
    return HEADER.format(card_id=card_id, title=title) + defuse_refs(body.strip()) + FOOTER.format(card_id=card_id)


def check_card(card: dict[str, Any], user_corpus: str) -> list[str]:
    """Reasons to reject a candidate card. Empty list = passes."""
    problems = []
    text = " ".join(str(card.get(k) or "") for k in ("title", "why", "prompt", "then_recurring"))
    bad_links = foreign_links(text, user_corpus)
    if bad_links:
        problems.append("links the user never typed: " + ", ".join(bad_links[:3]))
    hits = threats(text)
    if hits:
        problems.append("injection pattern: " + hits[0])
    return problems


def card_id_from_prompt(text: str) -> str | None:
    m = FOOTER_RE.search((text or "").strip())
    return m[1] if m else None


def corpus(user_texts: Iterable[str]) -> str:
    return "\n".join(user_texts)
