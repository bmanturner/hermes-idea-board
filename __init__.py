"""Idea Board: a nightly board of things your Hermes can do for you.

Registers:
* an auxiliary model slot ``idea_board`` (Settings → Models → Auxiliary) used for both model passes;
* the ``idea_board_run`` tool, which the nightly job calls;
* the ``/idea-board`` command (``generate`` | ``status``);
* an Automation Blueprint ``idea-board:nightly`` the user schedules with one click;
* a ``pre_llm_call`` hook that links a chat started from a card back to that card (no injection).
"""
from __future__ import annotations

import json
import logging
import threading
from typing import Any

import time

from .idea_board import inventory, packet, pipeline, safety, seeds, transcripts
from .idea_board.store import Store

log = logging.getLogger("plugins.idea-board")
PLUGIN = "idea-board"
TASK = "idea_board"
_CTX: Any = None
_RUN_LOCK = threading.Lock()


def _store() -> Store:
    from plugins.plugin_storage import plugin_db

    return Store(plugin_db(PLUGIN))


def _setting(key: str, default: int) -> int:
    """The user's choice from the board's setup (plugin data) wins, then plugin config, then default."""
    try:
        chosen = _store().get_meta(key)
        if chosen is not None:
            return int(chosen)
    except Exception:
        pass
    try:
        value = (_CTX.get_config() or {}).get(key, default)
        return int(value)
    except Exception:
        return default


def _llm(stage: str, instructions: str, body: str, schema: dict, max_tokens: int) -> pipeline.LlmResult:
    res = _CTX.llm.complete_structured(
        instructions=instructions, input=[{"type": "text", "text": body}], json_schema=schema,
        schema_name=f"idea_board_{stage}", task=TASK, purpose=f"idea_board.{stage}", max_tokens=max_tokens,
        timeout=300)
    usage = getattr(res, "usage", None)
    return pipeline.LlmResult(parsed=res.parsed, input_tokens=getattr(usage, "input_tokens", 0) or 0,
                              output_tokens=getattr(usage, "output_tokens", 0) or 0,
                              cost_usd=getattr(usage, "cost_usd", None), model=res.model or "")


def run_once(trigger: str) -> dict[str, Any]:
    if not _RUN_LOCK.acquire(blocking=False):
        return {"status": "busy", "message": "An Idea Board run is already in progress."}
    try:
        store = _store()
        inv = inventory.build(_CTX.dispatch_tool)
        sessions = transcripts.load_sessions(history_days=_setting("history_days", 14))
        library = seeds.load_seeds()
        try:
            _rank_connectors(store, inv, sessions, library)
        except Exception:
            log.exception("idea-board: connector ranking failed")
        have = seeds.classes_ready(inv["capabilities"])
        pkt = packet.build(inv, sessions, store,
                           seeds=seeds.available_now(library, have, seeds.chat_topics(sessions)))
        report = pipeline.run(pkt, _llm, store, trigger=trigger, max_cards=_setting("max_cards", 6))
        out = report.summary()
        out["notes"] = pkt.get("notes") or []
        return out
    finally:
        _RUN_LOCK.release()


def _rank_connectors(store: Store, inv: dict[str, Any], sessions: list[dict[str, Any]],
                     library: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Connectors worth adding next, ranked in code by the seed ideas they'd make possible."""
    recs = seeds.recommend(inv["capabilities"], sessions, seeds=library)
    store.set_meta("connector_recs", {"as_of": time.time(), "items": recs})
    return recs


def refresh_connectors() -> str:
    """Recheck connectors now, without a model call (after the user connects one)."""
    store = _store()
    inv = inventory.build(_CTX.dispatch_tool)
    if not any(c["kind"] == "connector" for c in inv["capabilities"]):
        return "I can't see any connectors for this profile, so I have nothing to suggest."
    recs = _rank_connectors(store, inv, transcripts.load_sessions(history_days=_setting("history_days", 14)),
                            seeds.load_seeds())
    hidden = set(store.get_meta("hidden_connectors") or [])
    shown = [r for r in recs if r["slug"] not in hidden][:3]
    if not shown:
        return "I rechecked your connectors. None of the ones you could add would open up new ideas right now."
    parts = [f"{r['name']} ({r['unlocked']} new ideas" + (f", {r['matched']} matching your chats)" if r["matched"] else ")")
             for r in shown]
    return "I rechecked your connectors. Worth connecting next: " + "; ".join(parts) + ". They're on the Idea Board."


def _tool_run(args: dict, **_kw: Any) -> str:
    trigger = "nightly" if _CTX.current_cron_execution() else "manual"
    try:
        return json.dumps(run_once(trigger), default=str)
    except Exception as exc:
        log.exception("idea-board run failed")
        return json.dumps({"status": "error", "error": f"{type(exc).__name__}: {exc}"})


def _command(raw_args: str = "", **_kw: Any) -> str:
    arg = (raw_args or "").strip().lower() or "status"
    if arg == "generate":
        threading.Thread(target=_background_generate, name="idea-board-generate", daemon=True).start()
        return "I'm reading your recent chats and what this profile can do. New ideas land on the Idea Board in a minute or two."
    if arg == "status":
        last = _store().last_run()
        if not last:
            return "I haven't made any ideas yet. Send `/idea-board generate` and I'll make the first board."
        tokens = (last['input_tokens'] or 0) + (last['output_tokens'] or 0)
        if last.get("error") or last["status"] == "error":
            return (f"My last {last['trigger']} run failed: {last.get('error') or 'unknown error'}. "
                    "Send `/idea-board generate` to try again.")
        return (f"Last {last['trigger']} run: I read {last['sessions_read']} chats, drafted {last['candidates']} "
                f"ideas and kept {last['kept']}, using {tokens:,} tokens on {last['model'] or 'the default model'}.")
    if arg == "connectors":
        try:
            return refresh_connectors()
        except Exception as exc:
            log.exception("idea-board connector refresh failed")
            return f"I couldn't recheck your connectors ({type(exc).__name__}). Try again in a moment."
    return ("Send `/idea-board generate` to make new ideas, `/idea-board connectors` to recheck which "
            "connectors would help, or `/idea-board status` to see my last run.")


def _background_generate() -> None:
    try:
        run_once("manual")
    except Exception:
        log.exception("idea-board manual run failed")


def _on_pre_llm_call(session_id: str = "", user_message: Any = None, is_first_turn: bool = False, **_kw: Any):
    """Link a chat started from a card to that card. Never injects context."""
    if not is_first_turn or not isinstance(user_message, str):
        return None
    card_id = safety.card_id_from_prompt(user_message)
    if card_id and session_id:
        try:
            store = _store()
            if store.card(card_id):
                store.link_session(card_id, session_id)
                if (store.card(card_id) or {}).get("status") == "open":
                    store.mark_started(card_id)
        except Exception:
            log.debug("idea-board: link failed", exc_info=True)
    return None


def register(ctx) -> None:
    global _CTX
    _CTX = ctx
    ctx.register_auxiliary_task(
        TASK, display_name="Idea Board",
        description="Drafts and reviews the nightly ideas. A smaller, cheaper model works well here.")
    ctx.register_tool(
        name="idea_board_run", toolset="idea_board",
        schema={
            "name": "idea_board_run",
            "description": ("Run Idea Board once: read recent chats and this profile's capabilities, and "
                            "post new ideas to the Idea Board. Takes a minute or two. Call it only when "
                            "the user or the Idea Board nightly job asks."),
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
        handler=_tool_run)
    ctx.register_command("idea-board", _command, description="Idea Board: generate new ideas now, recheck connectors, or show the last run",
                         args_hint="generate|status")
    ctx.register_automation_blueprint(
        "nightly", title="Idea Board nightly ideas",
        description="Every night I read the day's chats and what this profile can do, and post new ideas to the Idea Board.",
        category="productivity", schedule_template="{minute} {hour} * * *",
        prompt_template="Call the idea_board_run tool once. Do nothing else, then reply [SILENT].",
        slots=[{"name": "time", "type": "time", "label": "What time?", "default": "03:30"}],
        deliver_default="local", tags=["ideas", "nightly"])
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
