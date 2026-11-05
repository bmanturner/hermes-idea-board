"""Pure text helpers shared by the pipeline. No Hermes imports, so tests run under any Python."""
from __future__ import annotations

import re

STOPWORDS = frozenset("""
a about above after again all also am an and any are as at be because been before being below
between both but by can could did do does doing down during each few for from further had has have
having he her here hers herself him himself his how i if in into is it its itself just let me more
most my myself no nor not now of off on once only or other our ours ourselves out over own please
same she should so some such than that the their theirs them themselves then there these they this
those through to too under until up us very was we were what when where which while who whom why will
with would you your yours yourself yourselves ok okay yes yeah thanks thank hi hey hello sure right
like get got make want need one two use using via into onto
""".split())

# Blocks Hermes (or a user's own hooks) append to what the user typed. Everything from the
# first marker on is context the user did not write, often fetched web or mail content.
INJECTED_MARKERS = (
    "--- Attached Context ---",
    "Notes that may be relevant (",
    "Map of open work (",
    "[Context from the interrupted assistant response]",
)
_SYSTEM_LINE = re.compile(r"^\[(System|IMPORTANT|ASYNC DELEGATION)[^\]]*\].*$", re.MULTILINE)
_OOB = re.compile(r"\[/?OUT-OF-BAND USER MESSAGE[^\]]*\]")
_WS = re.compile(r"\s+")
_TOKEN = re.compile(r"[a-z0-9][a-z0-9'+#.-]*")


def clean_user_text(text: str) -> str:
    """Keep only what the user typed: cut injected context blocks and system notices."""
    if not isinstance(text, str):
        text = str(text or "")
    cut = len(text)
    for marker in INJECTED_MARKERS:
        idx = text.find(marker)
        if idx != -1:
            cut = min(cut, idx)
    text = text[:cut]
    text = _OOB.sub("", text)
    text = _SYSTEM_LINE.sub("", text)
    return text.strip()


def squash(text: str) -> str:
    return _WS.sub(" ", text or "").strip()


def clip(text: str, limit: int) -> str:
    text = squash(text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def tokens(text: str) -> list[str]:
    return [t.strip(".'-") for t in _TOKEN.findall((text or "").lower())]


def content_tokens(text: str) -> set[str]:
    return {t for t in tokens(text) if len(t) > 2 and t not in STOPWORDS and not t.isdigit()}


def jaccard(a: "set[str] | frozenset[str]", b: "set[str] | frozenset[str]") -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def topic_match(a: str, b: str, threshold: float = 0.5) -> bool:
    """Loose match for short topic labels ("weekly invoices" vs "invoices")."""
    ta, tb = content_tokens(a), content_tokens(b)
    if not ta or not tb:
        return False
    return ta <= tb or tb <= ta or jaccard(ta, tb) >= threshold
