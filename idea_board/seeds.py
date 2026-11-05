"""Seed ideas and "connect next" recommendations, computed in code (no model call).

Seeds (data/seeds.json) are generic ideas distilled once from the Hermes user stories, each tagged
with the capability classes it needs. This module works out which classes this profile already has
(toolsets, MCP servers, skills, messaging platforms and connected Portal connectors), then, for
every connector the user could still connect, counts the seeds it would make possible: seeds that
can't run today but could with that connector added. Seeds whose topic words show up in the user's
own recent messages count as matching their chats.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

DATA = Path(__file__).resolve().parent.parent / "data"

CLASSES = {
    "web": "search the web or read pages",
    "browser": "drive a real browser",
    "schedule": "run on a schedule",
    "terminal": "run commands or code",
    "memory": "remember facts across chats",
    "messaging": "message you on your phone or chat app",
    "media": "make images, video or voice",
    "home": "control smart-home devices",
    "email": "read and send your email",
    "calendar": "read and add calendar events",
    "scheduling_links": "booking links",
    "notes": "docs, wikis and notes",
    "meeting_notes": "meeting notes and transcripts",
    "tasks": "task and project trackers",
    "team_chat": "team chat",
    "files": "cloud files",
    "spreadsheet": "spreadsheets and tables",
    "crm": "sales contacts and outreach",
    "support": "customer support inboxes",
    "recruiting": "hiring pipelines",
    "payments": "payments and invoices",
    "banking": "bank accounts and spending",
    "crypto": "crypto wallets",
    "ecommerce": "online store",
    "monitoring": "errors, logs and uptime",
    "analytics": "analytics and dashboards",
    "seo": "search rankings",
    "hosting": "deploys, DNS and databases",
    "code": "code repositories and reviews",
    "design": "design tools",
    "bulk_email": "newsletters and email campaigns",
    "social": "social networks",
}

# Hermes toolsets -> classes.
TOOLSET_CLASSES = {
    "web": ["web"], "x_search": ["web", "social"], "browser": ["browser"], "computer_use": ["browser"],
    "cronjob": ["schedule"], "terminal": ["terminal"], "code_execution": ["terminal"], "memory": ["memory"],
    "image_gen": ["media"], "tts": ["media"], "video_gen": ["media"], "messaging": ["messaging"],
    "send_message": ["messaging"], "feishu_doc": ["notes"], "feishu_drive": ["files"],
    "google_meet": ["meeting_notes"], "homeassistant": ["home"],
}
PLATFORM_CLASSES = {"slack": ["messaging", "team_chat"], "discord": ["messaging", "team_chat"],
                    "mattermost": ["messaging", "team_chat"], "teams": ["messaging", "team_chat"]}

# Brand names are safe to read from any capability name, including skills.
_BRANDS: list[tuple[str, list[str]]] = [
    (r"fastmail", ["email", "calendar"]),
    (r"gmail|outlook|himalaya|protonmail", ["email"]),
    (r"google.?calendar|caldav|icloud.?calendar", ["calendar"]),
    (r"notion|obsidian|confluence|logseq|evernote", ["notes"]),
    (r"granola|circleback|otter|fireflies", ["meeting_notes"]),
    (r"todoist|asana|linear|jira|clickup|trello|things3", ["tasks"]),
    (r"slack|discord|mattermost", ["team_chat"]),
    (r"telegram|whatsapp|\bsignal\b|imessage|twilio", ["messaging"]),
    (r"github|gitlab|bitbucket|greptile", ["code"]),
    (r"dropbox|onedrive|google.?drive|\bbox\b", ["files"]),
    (r"airtable|google.?sheets|smartsheet", ["spreadsheet"]),
    (r"hubspot|salesforce|pipedrive|apollo", ["crm"]),
    (r"zendesk|intercom|freshdesk", ["support"]),
    (r"ashby|greenhouse|lever\b", ["recruiting"]),
    (r"stripe|paypal|cashfree|quickbooks|xero", ["payments"]),
    (r"plaid|ynab|\bramp\b|mercury|monarch", ["banking"]),
    (r"coinbase|metamask", ["crypto"]),
    (r"shopify|etsy|woocommerce", ["ecommerce"]),
    (r"sentry|datadog|better.?stack|pagerduty", ["monitoring"]),
    (r"posthog|amplitude|mixpanel|metabase|statsig|clickhouse", ["analytics"]),
    (r"ahrefs|semrush", ["seo"]),
    (r"vercel|cloudflare|railway|supabase|netlify|heroku|\bneon\b|turso", ["hosting"]),
    (r"canva|figma", ["design"]),
    (r"sendgrid|resend|mailchimp|customer.?io", ["bulk_email"]),
    (r"xurl|twitter|linkedin|reddit|youtube|bluesky|mastodon", ["social"]),
    (r"home.?assistant|philips.?hue", ["home"]),
]
# Generic words only count when read from tool names and MCP server names, never skill names
# (a skill called "competitor-news-monitor" doesn't give the profile production monitoring).
_TOOL_WORDS: list[tuple[str, list[str]]] = [
    (r"(read|send|search|draft|reply)_?e?mail|inbox", ["email"]),
    (r"calendar|_event", ["calendar"]),
    (r"(create|read|search|update)_note|notes?$", ["notes"]),
    (r"reminder|(create|add|complete|update|list)_(task|todo)s?\b", ["tasks"]),
    (r"spreadsheet|sheet|xlsx", ["spreadsheet"]),
    (r"invoice|payment", ["payments"]),
    (r"transaction|budget|account_balance", ["banking"]),
    (r"deploy|dns|serverless", ["hosting"]),
]

# Topic words too common, or too ambiguous, to say what a user cares about ("lead" is a sales lead
# in a seed but a tech lead in a job search). Matching ignores them.
_GENERIC = set("""daily weekly monthly yearly morning evening night today time date day week month year
report update summary digest news message alert reminder status track tracking log trend metric
work task data file list note email inbox chat agent tool app idea thing help question result project
team user people plan check change issue problem draft reply review request research approve approval
followup feedback decision knowledge priority schedule call post page site website online content build
search process service template guide procedure table pdf document doc docs text voice video lead job
market price cost free owner support audit triage quote order account record system setup add save get
set use make run new down link format personal""".split())
_WORD = re.compile(r"[a-z][a-z0-9'-]{2,}")


def _stem(w: str) -> str:
    w = w.strip("'-")
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 4 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        return w[:-1]
    return w


def load_seeds() -> list[dict[str, Any]]:
    path = DATA / "seeds.json"
    if not path.exists():
        return []
    seeds = json.loads(path.read_text(encoding="utf-8")).get("seeds") or []
    return [s for s in seeds if s.get("id") and s.get("title") and set(s.get("needs") or []) <= set(CLASSES)]


def load_catalog() -> list[dict[str, Any]]:
    return json.loads((DATA / "connectors.json").read_text(encoding="utf-8"))["connectors"]


def _match(text: str, rules: list[tuple[str, list[str]]]) -> set[str]:
    out: set[str] = set()
    low = text.lower()
    for pattern, classes in rules:
        if re.search(pattern, low):
            out.update(classes)
    return out


def classes_ready(capabilities: Iterable[dict[str, Any]], catalog: list[dict[str, Any]] | None = None) -> set[str]:
    """Capability classes this profile can use today."""
    by_slug = {c["slug"]: c for c in (catalog if catalog is not None else load_catalog())}
    have: set[str] = set()
    for cap in capabilities:
        if cap.get("status") != "ready":
            continue
        kind, name = cap.get("kind"), str(cap.get("name") or "")
        if kind == "toolset":
            have.update(TOOLSET_CLASSES.get(name, []))
            have |= _match(" ".join(cap.get("tools") or []), _TOOL_WORDS)
        elif kind == "mcp":
            have |= _match(name, _BRANDS) | _match(name, _TOOL_WORDS)
            for tool in cap.get("tools") or []:
                have |= _match(tool, _TOOL_WORDS) | _match(tool, _BRANDS)
        elif kind == "platform":
            have.update(PLATFORM_CLASSES.get(name, ["messaging"]))
        elif kind == "connector":
            slug = str(cap.get("id") or "").split(":", 1)[-1]
            have.update((by_slug.get(slug) or {}).get("classes") or [])
        elif kind == "skill":
            have |= _match(name, _BRANDS)
    return have


class Topics:
    """The words of each recent chat (the user's own messages and the chat title)."""

    def __init__(self, chats: list[set[str]]):
        self.chats = chats
        self.counts: Counter[str] = Counter(w for words in chats for w in words)


def chat_topics(sessions: Iterable[dict[str, Any]]) -> Topics:
    chats = []
    for s in sessions:
        words: set[str] = set()
        texts = [s.get("title") or ""] + [t.get("text") or "" for t in s.get("turns") or [] if t.get("role") == "user"]
        for text in texts:
            tokens = [_stem(w) for w in _WORD.findall(text.lower())]
            words.update(tokens)
            # two-word terms: "action items" also counts as the seed keyword "action-item"
            words.update(f"{a}-{b}" for a, b in zip(tokens, tokens[1:]) if "-" not in a + b)
        chats.append(words)
    return Topics(chats)


def topic_match(seed: dict[str, Any], topics: Topics) -> list[str]:
    """Seed topic words the user has talked about, most-used first. Precision over recall: a seed
    matches only when two of its specific words came up together in one chat, and its topic came up
    in at least two chats. One shared word ("invoice" once) is not enough."""
    words = {_stem(str(k).lower()) for k in seed.get("keywords") or []} - _GENERIC
    if len(words) < 2:
        return []
    per_chat = [chat & words for chat in topics.chats]
    if not any(len(found) >= 2 for found in per_chat) or sum(1 for found in per_chat if found) < 2:
        return []
    found = set().union(*per_chat)
    return sorted(found, key=lambda w: (-topics.counts[w], w))[:4]


def available_now(seeds: list[dict[str, Any]], have: set[str], topics: Topics, limit: int = 12) -> list[dict[str, Any]]:
    """Seeds this profile can already do, the ones matching the user's chats first, for the ideation prompt."""
    ok = [s for s in seeds if set(s.get("needs") or []) <= have]
    scored = sorted(ok, key=lambda s: (-len(topic_match(s, topics)), s["id"]))
    return [{k: s[k] for k in ("id", "title", "what", "kind", "needs") if k in s} for s in scored[:limit]]


def recommend(capabilities: list[dict[str, Any]], sessions: list[dict[str, Any]], *,
              seeds: list[dict[str, Any]] | None = None, catalog: list[dict[str, Any]] | None = None,
              hidden: Iterable[str] = (), limit: int = 6, examples: int = 8) -> list[dict[str, Any]]:
    """Connectors worth connecting next, ranked by the ideas they'd make possible.

    Only connectors the Portal reports as available (not connected, not disabled) are considered,
    and only ones that open up at least one idea matching the user's own chats ("grounded or gone":
    a connector that merely unlocks many generic ideas is not a recommendation). Connectors that make
    exactly the same ideas possible are folded into one, with the others listed as alternatives."""
    seeds = load_seeds() if seeds is None else seeds
    catalog = load_catalog() if catalog is None else catalog
    by_slug = {c["slug"]: c for c in catalog}
    have = classes_ready(capabilities, catalog)
    topics = chat_topics(sessions)
    hidden = set(hidden)
    available = [str(c["id"]).split(":", 1)[-1] for c in capabilities
                 if c.get("kind") == "connector" and c.get("status") == "available"]
    groups: dict[frozenset[str], list[dict[str, Any]]] = {}
    for slug in available:
        meta = by_slug.get(slug)
        if not meta or slug in hidden or not meta.get("classes"):
            continue
        adds = set(meta["classes"]) - have
        if not adds:
            continue
        unlocked = [s for s in seeds if (set(s.get("needs") or []) - have) and set(s.get("needs") or []) <= have | adds]
        if unlocked:
            groups.setdefault(frozenset(s["id"] for s in unlocked), []).append({"meta": meta, "seeds": unlocked})
    recs = []
    for members in groups.values():
        members.sort(key=lambda m: (m["meta"].get("rank", 50), m["meta"]["name"]))
        lead, unlocked = members[0]["meta"], members[0]["seeds"]
        matched = [(s, topic_match(s, topics)) for s in unlocked]
        matched_n = sum(1 for _, w in matched if w)
        if not matched_n:
            continue
        words = Counter(w for _, ws in matched for w in ws)
        ordered = sorted(matched, key=lambda p: (not p[1], p[0]["id"]))
        recs.append({
            "slug": lead["slug"], "name": lead["name"], "description": lead.get("description") or "",
            "classes": sorted(set(lead["classes"]) - have),
            "alternatives": [{"slug": m["meta"]["slug"], "name": m["meta"]["name"]} for m in members[1:]],
            "unlocked": len(unlocked), "matched": matched_n,
            "matched_words": [w for w, _ in words.most_common(5)],
            "examples": [{"id": s["id"], "title": s["title"], "what": s.get("what") or "", "kind": s.get("kind"),
                          "words": w} for s, w in ordered[:examples]],
        })
    recs.sort(key=lambda r: (-r["matched"], -r["unlocked"], r["name"]))
    return recs[:limit]


def connect_prompt(rec: dict[str, Any]) -> str:
    """The message placed in a new chat when the user picks a recommendation (the user's voice)."""
    picks = [e["title"].rstrip(".") for e in rec.get("examples") or []][:3]
    lines = [f"I'd like to connect {rec['name']}. Walk me through connecting it here, then suggest the first "
             "thing you could do with it for me."]
    if picks:
        lines.append("For example:")
        lines.extend(f"- {p}" for p in picks)
    lines.append("Don't start any of them until I say so.")
    return "\n".join(lines)
