"""The nightly run: packet → ideate → validate in code → critique → rank in code → store.

``llm`` is a callable ``llm(stage, instructions, body, schema, max_tokens) -> LlmResult`` so tests can
script the model. In Hermes it wraps ``ctx.llm.complete_structured(task="idea_board", ...)``.
"""
from __future__ import annotations

import datetime as dt
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from . import prompts, safety
from .store import Store, title_key
from .text import clip, jaccard, topic_match

NEEDS_EVIDENCE = {"repeated", "open_loop", "coming_up", "teach_once", "connector"}
DEFAULT_MAX_CARDS = 6
P_START_PRIOR = 0.3


@dataclass
class LlmResult:
    parsed: Any
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None
    model: str = ""


LlmFn = Callable[[str, str, str, dict, int], LlmResult]

# Provider hiccups worth another try: overloaded, rate limited, server errors, timeouts, dropped links.
_TRANSIENT = re.compile(r"overloaded|rate.?limit|\b(429|529)\b|(status|http|code)\D{0,6}(500|502|503|504)\b|"
                        r"internal server error|bad gateway|service unavailable|time(d)? ?out|temporarily|"
                        r"connection (reset|error|aborted)", re.I)
RETRY_WAITS = (15, 45)


def is_transient(exc: BaseException) -> bool:
    return bool(_TRANSIENT.search(f"{type(exc).__name__} {exc}"))


def retrying(call: Callable[[], Any], *, waits: tuple[float, ...] = RETRY_WAITS,
             sleep: Callable[[float], None] = time.sleep) -> Any:
    """Run ``call``; on a transient provider error wait and try again (len(waits) retries). Anything else,
    or the last failure, raises, and the run records it."""
    for wait in (*waits, None):
        try:
            return call()
        except Exception as exc:
            if wait is None or not is_transient(exc):
                raise
            sleep(wait)


@dataclass
class RunReport:
    run_id: int
    status: str
    kept: list[dict[str, Any]] = field(default_factory=list)
    rejected: list[dict[str, str]] = field(default_factory=list)
    candidates: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float | None = None
    model: str = ""
    error: str | None = None

    def summary(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id, "status": self.status, "candidates": self.candidates,
            "kept": [{"id": c["id"], "title": c["title"], "kind": c["kind"], "value": c["value_note"]}
                     for c in self.kept],
            "rejected": self.rejected[:20], "tokens": self.input_tokens + self.output_tokens,
            "cost_usd": self.cost_usd, "model": self.model, "error": self.error,
        }


def run(packet: dict[str, Any], llm: LlmFn, store: Store, *, trigger: str = "manual",
        max_cards: int = DEFAULT_MAX_CARDS, now: dt.datetime | None = None) -> RunReport:
    now = now or dt.datetime.now()
    run_id = store.start_run(trigger)
    rep = RunReport(run_id=run_id, status="running")
    try:
        _run(packet, llm, store, rep, max_cards, now)
        rep.status = "ok"
    except Exception as exc:  # recorded on the run; the board shows it
        rep.status, rep.error = "error", f"{type(exc).__name__}: {exc}"
    store.finish_run(run_id, rep.status, sessions_read=len(packet.get("chats") or []),
                     evidence=len(packet.get("evidence") or []), candidates=rep.candidates, kept=len(rep.kept),
                     rejected=rep.rejected[:50], input_tokens=rep.input_tokens, output_tokens=rep.output_tokens,
                     cost_usd=rep.cost_usd, model=rep.model, error=rep.error)
    return rep


def _account(rep: RunReport, res: LlmResult) -> None:
    rep.input_tokens += res.input_tokens
    rep.output_tokens += res.output_tokens
    if res.cost_usd is not None:
        rep.cost_usd = (rep.cost_usd or 0.0) + res.cost_usd
    rep.model = res.model or rep.model


def _run(packet: dict[str, Any], llm: LlmFn, store: Store, rep: RunReport, max_cards: int,
         now: dt.datetime) -> None:
    instructions, body = prompts.ideate_input(packet)
    res = llm("ideate", instructions, body, prompts.IDEATE_SCHEMA, 12000)
    _account(rep, res)
    cands = list((res.parsed or {}).get("candidates") or [])
    rep.candidates = len(cands)

    survivors = []
    for c in cands:
        why_not = validate(c, packet, store)
        if why_not:
            rep.rejected.append({"title": clip(str(c.get("title")), 80), "why": why_not})
        else:
            survivors.append(c)
    if not survivors:
        return

    instructions, body = prompts.critique_input(packet, survivors)
    res = llm("critique", instructions, body, prompts.CRITIQUE_SCHEMA, 6000)
    _account(rep, res)
    reviews = {r["index"]: r for r in (res.parsed or {}).get("reviews") or [] if isinstance(r.get("index"), int)}

    scored = []
    p_start = lens_priors(store)
    friction = {e.get("tool") for e in packet["evidence"] if e["kind"] == "tool_friction"}
    for i, c in enumerate(survivors):
        r = reviews.get(i)
        if not r or not r.get("keep") or _band(r.get("feasibility")) <= 1 or _band(r.get("novelty")) <= 1:
            rep.rejected.append({"title": clip(str(c.get("title")), 80),
                                 "why": "critic: " + clip(str((r or {}).get("reason") or "no review"), 160)})
            continue
        c = dict(c, title=clip(r.get("title") or c["title"], 70), why=clip(r.get("why") or c["why"], 240))
        c["_critic"] = r
        scored.append(score(c, r, packet, p_start.get(c["lens"], P_START_PRIOR), friction, now))

    for c in select(scored, max_cards):
        rep.kept.append(_store_card(c, packet, store, rep.run_id))


def _band(v: Any) -> int:
    try:
        return max(1, min(5, int(v)))
    except (TypeError, ValueError):
        return 1


def validate(c: dict[str, Any], packet: dict[str, Any], store: Store) -> str | None:
    """Why a candidate fails code checks, or None."""
    caps = {cap["id"]: cap for cap in packet["capabilities"]}
    evidence = {e["id"]: e for e in packet["evidence"]}
    kind, lens = c.get("kind"), c.get("lens")
    if kind not in prompts.KINDS or lens not in prompts.LENSES:
        return "bad kind or lens"
    if not str(c.get("prompt") or "").strip() or not str(c.get("title") or "").strip():
        return "empty title or prompt"
    cited = [evidence[e] for e in c.get("evidence_ids") or [] if e in evidence]
    if len(cited) != len(c.get("evidence_ids") or []):
        return "cites evidence that doesn't exist"
    consumed = store.consumed_quotes()
    if any(e["quote"].lower() in consumed for e in cited):
        return "evidence already handled"
    if lens in NEEDS_EVIDENCE and not cited:
        return f"lens {lens} needs evidence"
    uses = c.get("uses") or []
    if not uses:
        return "names no capability"
    unknown = [u for u in uses if u not in caps]
    if unknown:
        return "unknown capability: " + ", ".join(unknown[:3])
    not_ready = [u for u in uses if caps[u]["status"] != "ready"]
    if kind == "connector":
        avail = [u for u in not_ready if caps[u]["kind"] == "connector" and caps[u]["status"] == "available"]
        if len(avail) != 1 or len(not_ready) != 1:
            return "a connector card needs exactly one not-connected connector"
    elif not_ready:
        return "uses capabilities that aren't ready: " + ", ".join(not_ready[:3])
    if kind == "recurring" and not str(c.get("schedule") or "").strip():
        return "recurring without a schedule"
    problems = safety.check_card(c, packet["user_corpus"] + "\n" + "\n".join(e["quote"] for e in cited))
    if problems:
        return problems[0]
    c["risk"] = safety.risk_level(c.get("risk"), kind, str(c.get("prompt")))
    rule = store.blocking_rule(c)
    if rule:
        store.hit_rule(rule["id"])
        return f"blocked by your rule: {rule['text']}"
    dup = duplicate_of(c, store)
    if dup:
        return f"repeats {dup}"
    if kind == "recurring":
        for job in packet["automations"].get("jobs") or []:
            if topic_match(c.get("topic") or "", job.get("name") or "") or topic_match(
                    c.get("title") or "", job.get("name") or ""):
                return f"already scheduled: {job.get('name')}"
        for sug in packet["automations"].get("suggested") or []:
            if topic_match(c.get("title") or "", sug.get("title") or ""):
                return f"already a suggested job: {sug.get('title')}"
    return None


def duplicate_of(c: dict[str, Any], store: Store) -> str | None:
    """The same idea again. Any earlier card with a near-identical title counts. A same-topic card counts
    only while it is still on the board or snoozed: once dismissed, the dismissal's rule decides what stays
    off (a "wrong tool" dismissal must not block a different idea on the same topic)."""
    key = title_key(c.get("title") or "")
    for old in store.cards(("open", "snoozed", "started", "done", "dismissed")):
        if jaccard(key, title_key(old["title"] or "")) >= 0.6:
            return old["id"]
        if old["kind"] == c.get("kind") and old.get("topic") and topic_match(old["topic"], c.get("topic") or "") \
                and old["status"] in ("open", "snoozed"):
            return old["id"]
    return None


def lens_priors(store: Store) -> dict[str, float]:
    """p(start) per lens from history, smoothed toward the prior."""
    rows = store.conn.execute("SELECT lens, status FROM cards WHERE status IN ('started','done','dismissed')")
    tally: dict[str, list[int]] = {}
    for r in rows:
        t = tally.setdefault(r["lens"], [0, 0])
        t[0 if r["status"] in ("started", "done") else 1] += 1
    return {lens: (s + P_START_PRIOR * 3) / (s + d + 3) for lens, (s, d) in tally.items()}


def score(c: dict[str, Any], review: dict[str, Any], packet: dict[str, Any], p_start: float,
          friction: set[Any], now: dt.datetime) -> dict[str, Any]:
    def num(key: str, lo: float, hi: float) -> float:
        try:
            return max(lo, min(hi, float(c.get(key) or 0)))
        except (TypeError, ValueError):
            return lo

    if c["kind"] == "recurring":
        per_run, per_month = num("minutes_per_run", 1, 120), num("runs_per_month", 0.25, 31)
        value = per_run * min(per_month * 3, 60)
        monthly = per_run * per_month
        note = f"≈ {monthly / 60:.1f} h/month" if monthly >= 60 else f"≈ {monthly:.0f} min/month"
    else:
        value = num("minutes_once", 1, 240)
        note = f"≈ {value:.0f} min once"
    urgency = 1.0
    if c.get("expires"):
        try:
            days = (dt.date.fromisoformat(str(c["expires"])) - now.date()).days
            urgency = 1.5 if days <= 3 else 1.2 if days <= 7 else 1.0
        except ValueError:
            c["expires"] = None
    p_success = _band(review.get("feasibility")) / 5
    if any(any(t and t in u for t in friction) for u in c.get("uses") or []):
        p_success *= 0.7
    s = p_start * p_success * value * urgency * (_band(review.get("novelty")) / 5) * (_band(review.get("specificity")) / 5)
    if c.get("risk") == "external-action":
        s *= 0.9
    return dict(c, value_min=round(value, 1), value_note=note, score=round(s, 3))


def select(scored: list[dict[str, Any]], max_cards: int) -> list[dict[str, Any]]:
    """Best first, with a mix: at least one recurring and one one-time when they exist, at most one
    connector card and one stretch idea."""
    ranked = sorted(scored, key=lambda c: -c["score"])
    picked: list[dict[str, Any]] = []
    for kind in ("recurring", "once"):
        best = next((c for c in ranked if c["kind"] == kind), None)
        if best:
            picked.append(best)
    for c in ranked:
        if len(picked) >= max_cards:
            break
        if c in picked:
            continue
        if c["kind"] == "connector" and any(p["kind"] == "connector" for p in picked):
            continue
        if c.get("stretch") and any(p.get("stretch") for p in picked):
            continue
        picked.append(c)
    return sorted(picked[:max_cards], key=lambda c: -c["score"])


def _store_card(c: dict[str, Any], packet: dict[str, Any], store: Store, run_id: int) -> dict[str, Any]:
    evidence = {e["id"]: e for e in packet["evidence"]}
    cited, seen = [], set()
    for e in c.get("evidence_ids") or []:
        if e in evidence and evidence[e]["quote"].lower() not in seen:
            seen.add(evidence[e]["quote"].lower())
            cited.append(e)
    card_id = store.next_card_id()
    card = {
        "id": card_id, "run_id": run_id, "kind": c["kind"], "lens": c["lens"], "topic": clip(c.get("topic") or "", 40),
        "title": c["title"], "why": c["why"],
        "prompt": safety.build_prompt(card_id, c["title"], c["prompt"]),
        "uses": c.get("uses") or [],
        "evidence": [{k: evidence[e][k] for k in ("kind", "quote", "session_ids", "days", "count") if k in evidence[e]}
                     for e in cited],
        "schedule": c.get("schedule"), "expires": c.get("expires"), "risk": c["risk"],
        "value_min": c["value_min"], "value_note": c["value_note"], "score": c["score"],
        "stretch": 1 if c.get("stretch") else 0, "seed_id": c.get("seed_id"),
        "then_recurring": safety.defuse_refs(c["then_recurring"]) if c.get("then_recurring") else None,
    }
    store.add_card(card)
    return card


def now_block(now: dt.datetime | None = None) -> str:
    now = (now or dt.datetime.now()).astimezone()
    return now.strftime("%A %Y-%m-%d %H:%M %Z")


def stamp() -> float:
    return time.time()
