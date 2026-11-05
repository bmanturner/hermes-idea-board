"""Idea Board reads three Hermes internals that have no public equivalent yet (README, Compatibility).
These tests break each one on purpose and check the plugin keeps working on its fallback."""
import json
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from idea_board import inventory, seeds  # noqa: E402

_MISSING = object()
CONFIG = {
    "mcp_servers": {"Fastmail": {}, "Lazy": {}, "Off": {"enabled": False}},
    "agent": {"disabled_toolsets": "['browser']"},  # the JSON-array string form `hermes config set` writes
}
TOOL_TO_TS = {"web_search": "web", "browser_navigate": "browser", "mcp__Fastmail__read_email": "Fastmail",
              "delegate_task": "delegation"}


@contextmanager
def modules(mapping):
    """Install fake modules; a None value makes that import raise ImportError."""
    saved = {name: sys.modules.get(name, _MISSING) for name in mapping}
    sys.modules.update(mapping)
    try:
        yield
    finally:
        for name, mod in saved.items():
            if mod is _MISSING:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = mod  # type: ignore[assignment]


def package(name, **attrs):
    mod = types.ModuleType(name)
    mod.__path__ = []  # mark as a package
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


def public_hermes():
    registry = types.SimpleNamespace(
        get_tool_to_toolset_map=lambda: dict(TOOL_TO_TS),
        get_available_toolsets=lambda: {ts: {"available": True} for ts in TOOL_TO_TS.values()},
        get_schema=lambda tool: {"description": f"{tool} does a thing. More detail."},
    )
    reg_mod = types.ModuleType("tools.registry")
    setattr(reg_mod, "registry", registry)
    cfg_mod = types.ModuleType("hermes_cli.config")
    setattr(cfg_mod, "load_config", lambda: json.loads(json.dumps(CONFIG)))
    return {"tools": package("tools", registry=reg_mod), "tools.registry": reg_mod,
            "hermes_cli": package("hermes_cli", config=cfg_mod), "hermes_cli.config": cfg_mod}


BROKEN_PRIVATE = {"hermes_cli.tools_config": None, "toolsets": None, "cron": None, "cron.suggestions": None}


def by_id(caps):
    return {c["id"]: c for c in caps}


class FallbackTests(unittest.TestCase):
    def test_platform_toolsets_fall_back_to_registry_minus_disabled(self):
        with modules({**public_hermes(), **BROKEN_PRIVATE}):
            caps = by_id(inventory.toolsets())
        self.assertIn("toolset:web", caps)
        self.assertIn("toolset:delegation", caps)
        self.assertNotIn("toolset:browser", caps)  # agent.disabled_toolsets is still honoured
        self.assertEqual(caps["mcp:Fastmail"]["kind"], "mcp")  # MCP detection survives (public config)
        self.assertIn("mcp:Lazy", caps)      # lazily loaded servers stay listed
        self.assertNotIn("mcp:Off", caps)    # disabled servers don't
        # Classes still come through, e.g. email from the Fastmail server
        self.assertIn("email", seeds.classes_ready(caps.values(), []))

    def test_private_path_used_when_present(self):
        tools_config = types.ModuleType("hermes_cli.tools_config")
        setattr(tools_config, "_get_platform_tools", lambda cfg, platform: {"web", "Fastmail"})
        toolsets_mod = types.ModuleType("toolsets")
        setattr(toolsets_mod, "resolve_toolset", lambda ts: {"web": ["web_search"], "Fastmail": ["mcp__Fastmail__read_email"]}[ts])
        with modules({**public_hermes(), "hermes_cli.tools_config": tools_config, "toolsets": toolsets_mod}):
            caps = by_id(inventory.toolsets())
        self.assertEqual(set(caps), {"toolset:web", "mcp:Fastmail"})  # only what's on for chats

    def test_private_call_failing_midway_falls_back_cleanly(self):
        tools_config = types.ModuleType("hermes_cli.tools_config")

        def boom(cfg, platform):
            raise TypeError("signature changed")
        setattr(tools_config, "_get_platform_tools", boom)
        with modules({**public_hermes(), "hermes_cli.tools_config": tools_config, "toolsets": types.ModuleType("toolsets")}):
            caps = by_id(inventory.toolsets())
        self.assertIn("toolset:web", caps)
        self.assertIn("mcp:Lazy", caps)

    def test_suggested_jobs_missing_skips_duplicate_check_with_a_note(self):
        jobs = {"jobs": [{"name": "Morning brief", "schedule": "30 7 * * 1-5", "enabled": True, "prompt_preview": "Brief me"}]}
        notes: list[str] = []
        with modules(BROKEN_PRIVATE):
            out = inventory.automations(lambda name, args: json.dumps(jobs), notes)
        self.assertEqual(out["suggested"], [])
        self.assertEqual([j["name"] for j in out["jobs"]], ["Morning brief"])
        self.assertTrue(any("duplicate check" in n for n in notes))

    def test_build_end_to_end_with_every_internal_missing(self):
        status = {"connectors": [{"connector": "notion", "connected": False}, {"connector": "slack", "connected": True}]}

        def dispatch(name, args):
            return json.dumps(status if name == "manage_connections" else {"jobs": []})
        with modules({**public_hermes(), **BROKEN_PRIVATE, "tools.skills_tool": None, "gateway": None,
                      "gateway.config": None, "hermes_constants": None}):
            inv = inventory.build(dispatch)
        ids = {c["id"] for c in inv["capabilities"]}
        self.assertTrue({"toolset:web", "mcp:Fastmail", "connector:notion", "connector:slack"} <= ids)
        self.assertIn("Hermes suggested jobs unavailable; duplicate check against them skipped", inv["notes"])


if __name__ == "__main__":
    unittest.main()
