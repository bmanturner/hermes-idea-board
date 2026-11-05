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


class SetupInput(BaseModel):
    history_days: int | None = None
    max_cards: int | None = None
    schedule: str | None = None
    done: bool | None = None


SETUP_DEFAULTS = {"history_days": 14, "max_cards": 6}
ALLOWED = {"history_days": (7, 14, 30), "max_cards": (3, 6, 10)}


def _model_info() -> dict[str, Any]:
    """Which model writes the ideas: Idea Board's own slot if the user set one, else the main model."""
    try:
        from hermes_cli.config import load_config

        cfg = load_config() or {}
    except Exception:
        return {"name": None, "follows_main": True}
    aux = ((cfg.get("auxiliary") or {}).get("idea_board") or {})
    main = cfg.get("model")
    main_name = (main.get("default") or main.get("model")) if isinstance(main, dict) else main
    model = str(aux.get("model") or "").strip()
    if model:
        return {"name": model, "follows_main": False}
    return {"name": main_name or None, "follows_main": True}


def _setup(s) -> dict[str, Any]:
    return {
        "done": bool(s.get_meta("setup_done", False)),
        "history_days": int(s.get_meta("history_days", SETUP_DEFAULTS["history_days"])),
        "max_cards": int(s.get_meta("max_cards", SETUP_DEFAULTS["max_cards"])),
        "schedule": s.get_meta("schedule", None),
        "model": _model_info(),
    }


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
        "setup": _setup(s),
    }


@router.post("/setup")
def setup(body: SetupInput):
    s = _store()
    for key, allowed in ALLOWED.items():
        value = getattr(body, key, None)
        if value is not None:
            if int(value) not in allowed:
                raise HTTPException(status_code=400, detail=f"{key} must be one of {list(allowed)}")
            s.set_meta(key, int(value))
    if body.schedule is not None:
        s.set_meta("schedule", str(body.schedule)[:80] or None)
    if body.done is not None:
        s.set_meta("setup_done", bool(body.done))
    return {"ok": True, "setup": _setup(s)}


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
