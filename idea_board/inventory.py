"""What this Hermes profile can do, built in code so the model can't invent capabilities.

Hermes adapter. Public APIs first (tool registry, ``find_all_skills``, ``gateway.config``, tool
dispatch for connectors and cron jobs); a few private helpers (platform toolsets, MCP server list,
suggested jobs, live connector catalog) are used inside ``try`` blocks and fall back cleanly.

Each capability row: {"id", "kind", "name", "status", "can_do", "tools"}.
status: "ready" (usable now), "available" (a connector the user could connect), "disabled".
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Callable

from .text import clip

log = logging.getLogger("plugins.idea-board")
DATA = Path(__file__).resolve().parent.parent / "data"
SKIP_TOOLSETS = {"idea_board", "onboarding", "todo", "clarify"}
MAX_SKILLS = 150
Dispatch = Callable[[str, dict], str]


def _first_sentence(text: str, limit: int = 150) -> str:
    text = " ".join((text or "").split())
    cut = text.find(". ")
    return clip(text[: cut + 1] if 0 < cut < limit else text, limit)


def _connector_catalog() -> dict[str, dict[str, str]]:
    """Names and one-line descriptions for Portal connectors, from the snapshot shipped in data/."""
    return {c["slug"]: c for c in json.loads((DATA / "connectors.json").read_text())["connectors"]}


def connectors(dispatch: Dispatch) -> tuple[list[dict[str, Any]], str | None]:
    try:
        data = json.loads(dispatch("manage_connections", {"action": "status"}))
    except Exception as exc:
        return [], f"connector status failed: {exc}"
    rows = data.get("connectors") if isinstance(data, dict) else None
    if not rows:
        return [], "connectors unavailable for this account" if isinstance(data, dict) else "bad connector status"
    catalog = _connector_catalog()
    out = []
    for r in rows:
        slug = r.get("connector")
        if not slug:
            continue
        meta = catalog.get(slug, {})
        status = "ready" if r.get("connected") else "available" if r.get("enabled", True) else "disabled"
        out.append({"id": f"connector:{slug}", "kind": "connector", "name": meta.get("name") or slug,
                    "status": status, "category": meta.get("category") or "",
                    "can_do": meta.get("description") or "", "tools": []})
    return out, None


def _disabled_toolsets(cfg: dict[str, Any]) -> set[str]:
    """``agent.disabled_toolsets`` from the public config (a list, or a JSON-array string)."""
    raw = (cfg.get("agent") or {}).get("disabled_toolsets") or []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw.replace("'", '"'))
        except ValueError:
            raw = [p.strip() for p in raw.strip("[]").split(",")]
    return {str(x).strip() for x in raw if str(x).strip()} if isinstance(raw, list) else set()


def _mcp_enabled(cfg: dict[str, Any], name: str) -> bool:
    entry = (cfg.get("mcp_servers") or {}).get(name)
    return not (isinstance(entry, dict) and entry.get("enabled") is False)


def toolsets(platform: str = "cli") -> list[dict[str, Any]]:
    """Toolsets enabled where cards run. Desktop chats use the ``cli`` platform's selection
    (``tui_gateway/agent_factory.py``), so that is the default.

    Hermes has no public API for "which toolsets are on for this platform" yet, so this uses two
    core internals (``hermes_cli.tools_config._get_platform_tools`` and ``toolsets.resolve_toolset``;
    see README, Compatibility). If either moves, it falls back to every available toolset minus the
    ones disabled globally in config (``agent.disabled_toolsets``), and keeps working."""
    from tools.registry import registry

    tool_to_ts = registry.get_tool_to_toolset_map()
    cfg: dict[str, Any] = {}
    mcp_names: set[str] = set()
    try:  # public: the profile config
        from hermes_cli.config import load_config

        cfg = load_config() or {}
        mcp_names = {str(k) for k in (cfg.get("mcp_servers") or {})}
    except Exception as exc:
        log.debug("idea-board: config unavailable: %s", exc)
    enabled_tools: set[str] | None = None
    enabled_names: set[str] = set()
    try:  # private: the per-platform toolset selection and composite resolution
        from hermes_cli.tools_config import _get_platform_tools
        from toolsets import resolve_toolset

        picked: set[str] = set()
        names: set[str] = set()
        for ts in _get_platform_tools(cfg, platform):
            names.add(str(ts))
            picked.update(resolve_toolset(ts))
        enabled_tools, enabled_names = picked, names
    except Exception as exc:
        log.debug("idea-board: platform toolsets unavailable, using registry availability: %s", exc)
    disabled = _disabled_toolsets(cfg) if enabled_tools is None else set()
    available = registry.get_available_toolsets()
    groups: dict[str, list[str]] = {}
    for tool, ts in tool_to_ts.items():
        if ts in SKIP_TOOLSETS or ts in disabled:
            continue
        if enabled_tools is not None and tool not in enabled_tools:
            continue
        if enabled_tools is None and not (available.get(ts) or {}).get("available", True):
            continue
        groups.setdefault(ts, []).append(tool)
    out = []
    for ts, tools in sorted(groups.items()):
        schema = registry.get_schema(sorted(tools)[0]) or {}
        kind = "mcp" if ts in mcp_names else "toolset"
        out.append({"id": f"{kind}:{ts}", "kind": kind, "name": ts, "status": "ready",
                    "can_do": _first_sentence(schema.get("description") or ""), "tools": sorted(tools)[:12]})
    # MCP servers enabled for chats whose tools aren't loaded in this process (they connect lazily
    # in some processes): list them so ideas can use them, with what we know.
    # Without the private platform selection, every enabled MCP server in config counts.
    lazy = mcp_names & enabled_names if enabled_tools is not None else {
        n for n in mcp_names if _mcp_enabled(cfg, n) and n not in disabled}
    for name in sorted(lazy - set(groups)):
        out.append({"id": f"mcp:{name}", "kind": "mcp", "name": name, "status": "ready",
                    "can_do": f"MCP server {name} (tools load when a chat connects to it)", "tools": []})
    return out


def skills() -> list[dict[str, Any]]:
    try:
        from tools.skills_tool import find_all_skills

        rows = find_all_skills()
    except Exception as exc:
        log.debug("idea-board: skills unavailable: %s", exc)
        return []
    return [{"id": f"skill:{s['name']}", "kind": "skill", "name": s["name"], "status": "ready",
             "can_do": _first_sentence(s.get("description") or "", 140), "tools": []}
            for s in rows[:MAX_SKILLS] if s.get("name")]


def platforms() -> list[dict[str, Any]]:
    try:
        from gateway.config import load_gateway_config

        names = [getattr(p, "value", str(p)) for p in load_gateway_config().get_connected_platforms()]
    except Exception as exc:
        log.debug("idea-board: platforms unavailable: %s", exc)
        return []
    return [{"id": f"platform:{n}", "kind": "platform", "name": n, "status": "ready",
             "can_do": f"Deliver messages and scheduled-job results to {n}", "tools": []} for n in sorted(set(names))]


def automations(dispatch: Dispatch, notes: list[str] | None = None) -> dict[str, Any]:
    jobs: list[dict[str, Any]] = []
    try:
        data = json.loads(dispatch("cronjob_manage", {"action": "list"}))
        for j in data.get("jobs") or []:
            jobs.append({"name": clip(j.get("name") or "", 80), "schedule": j.get("schedule"),
                         "state": j.get("state") or ("enabled" if j.get("enabled") else "paused"),
                         "last_status": j.get("last_status"), "failing": bool(j.get("last_error")),
                         "deliver": j.get("deliver"), "what": clip(j.get("prompt_preview") or "", 160)})
    except Exception as exc:
        log.debug("idea-board: cron list unavailable: %s", exc)
    suggested: list[dict[str, Any]] = []
    try:  # private: core "Suggested cron jobs"; Idea Board must not duplicate them
        from cron.suggestions import load_suggestions

        suggested = [{"title": s.get("title"), "status": s.get("status")} for s in load_suggestions()
                     if s.get("status") in ("pending", "dismissed")]
    except Exception as exc:  # fallback: skip the duplicate check against Hermes's suggestions
        log.debug("idea-board: suggestions unavailable: %s", exc)
        if notes is not None:
            notes.append("Hermes suggested jobs unavailable; duplicate check against them skipped")
    return {"jobs": jobs, "suggested": suggested}


def profile_text(limit: int = 1500) -> str:
    try:
        from hermes_constants import get_hermes_home

        path = get_hermes_home() / "memories" / "USER.md"
        return clip(path.read_text(encoding="utf-8"), limit) if path.exists() else ""
    except Exception:
        return ""


def build(dispatch: Dispatch) -> dict[str, Any]:
    conns, conn_note = connectors(dispatch)
    notes = [n for n in (conn_note,) if n]
    caps = toolsets() + conns + skills() + platforms()
    tool_to_cap = {t: c["id"] for c in caps for t in c.get("tools") or []}
    return {"capabilities": caps, "tool_to_cap": tool_to_cap, "automations": automations(dispatch, notes),
            "profile": profile_text(), "notes": notes}
