"""Idea Board REST backend, mounted by Hermes at /api/plugins/idea-board/ (desktop: ctx.rest).

Reads and writes only Idea Board's own store (<HERMES_HOME>/plugin-data/idea-board/data.db). It
never calls a model or a tool: generating ideas happens in the agent half (the nightly job, or the
/idea-board generate command the user sends from a chat).
"""
from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

try:
    from fastapi import APIRouter, HTTPException
    from pydantic import BaseModel
except Exception:  # lets the module import (and be tested) without FastAPI
    class APIRouter:  # type: ignore[no-redef]
        def get(self, *_a, **_k): return lambda fn: fn
        def post(self, *_a, **_k): return lambda fn: fn
        def patch(self, *_a, **_k): return lambda fn: fn
        def delete(self, *_a, **_k): return lambda fn: fn

    class HTTPException(Exception):  # type: ignore[no-redef]
        def __init__(self, status_code: int, detail: str):
            super().__init__(detail)
            self.status_code, self.detail = status_code, detail

    class BaseModel:  # type: ignore[no-redef]
        def __init__(self, **kw: Any):
            for k, v in kw.items():
                setattr(self, k, v)

router = APIRouter()
_CORE = "idea_board_core_dashboard"
_STORE_OVERRIDE: Any = None  # tests inject a Store


def _core(name: str):
    """Load idea_board/<name>.py as a package module (this file is imported standalone)."""
    if _CORE not in sys.modules:
        root = Path(__file__).resolve().parent.parent / "idea_board"
        spec = importlib.util.spec_from_file_location(_CORE, root / "__init__.py",
                                                      submodule_search_locations=[str(root)])
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        sys.modules[_CORE] = mod
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return importlib.import_module(f"{_CORE}.{name}")


def _store():
    if _STORE_OVERRIDE is not None:
        return _STORE_OVERRIDE
    from plugins.plugin_storage import plugin_db

    return _core("store").Store(plugin_db("idea-board"))


def _label(cap_id: str) -> dict[str, str]:
    kind, _, name = cap_id.partition(":")
    return {"id": cap_id, "kind": kind, "name": name or cap_id}


def _card_out(c: dict[str, Any]) -> dict[str, Any]:
    keys = ("id", "status", "kind", "lens", "topic", "title", "why", "prompt", "schedule", "expires", "risk",
            "value_note", "value_min", "score", "then_recurring", "created_at", "started_at", "session_id",
            "outcome", "snooze_until")
    out = {k: c.get(k) for k in keys}
    out["stretch"] = bool(c.get("stretch"))
    out["uses"] = [_label(u) for u in c.get("uses") or []]
    out["evidence"] = [{"kind": e.get("kind"), "quote": e.get("quote"), "days": e.get("days") or [],
                        "count": e.get("count") or 1, "session_ids": (e.get("session_ids") or [])[:5]}
                       for e in c.get("evidence") or []]
    return out


def _run_out(r: dict[str, Any] | None) -> dict[str, Any] | None:
    if not r:
        return None
    keys = ("id", "status", "trigger", "started_at", "finished_at", "sessions_read", "evidence", "candidates",
            "kept", "input_tokens", "output_tokens", "cost_usd", "model", "error")
    return {k: r.get(k) for k in keys}


class DismissInput(BaseModel):
    reason: str
    note: str = ""


class SnoozeInput(BaseModel):
    days: int = 7


class RuleInput(BaseModel):
    text: str


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/board")
def board():
    s = _store()
    store_mod = _core("store")
    started = [c for c in s.cards(("started", "done")) if c.get("started_at")]
    started.sort(key=lambda c: -(c.get("started_at") or 0))
    return {
        "cards": [_card_out(c) for c in s.board()],
        "started": [_card_out(c) for c in started[:10]],
        "snoozed": [_card_out(c) for c in s.cards(("snoozed",))],
        "rules": [{"id": r["id"], "text": r["text"], "scope": r["scope"], "hits": r["hits"],
                   "created_at": r["created_at"]} for r in s.rules()],
        "last_run": _run_out(s.last_run()),
        "reasons": [{"code": k, "label": v} for k, v in store_mod.REASONS.items()],
    }


def _require(s, card_id: str) -> dict[str, Any]:
    card = s.card(card_id)
    if not card:
        raise HTTPException(status_code=404, detail="card not found")
    return card


@router.post("/cards/{card_id}/started")
def started(card_id: str):
    s = _store()
    card = _require(s, card_id)
    if card["status"] in ("open", "snoozed"):
        s.mark_started(card_id)
    return {"ok": True}


@router.post("/cards/{card_id}/dismiss")
def dismiss(card_id: str, body: DismissInput):
    s = _store()
    _require(s, card_id)
    try:
        result = s.dismiss(card_id, body.reason, body.note or "")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    rule = None
    if result.get("rule"):
        rule = next((r["text"] for r in s.rules() if r["id"] == result["rule"]), None)
    return {"ok": True, "action": result["action"], "rule": rule, "widened": bool(result.get("widened"))}


@router.post("/cards/{card_id}/snooze")
def snooze(card_id: str, body: SnoozeInput):
    s = _store()
    _require(s, card_id)
    s.snooze(card_id, max(1, min(90, int(body.days or 7))))
    return {"ok": True}


@router.post("/cards/{card_id}/undo")
def undo(card_id: str):
    s = _store()
    _require(s, card_id)
    return {"ok": s.undo_dismiss(card_id)}


@router.patch("/rules/{rule_id}")
def edit_rule(rule_id: int, body: RuleInput):
    text = (body.text or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="rule text is empty")
    _store().edit_rule(rule_id, text)
    return {"ok": True}


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int):
    _store().delete_rule(rule_id)
    return {"ok": True}
