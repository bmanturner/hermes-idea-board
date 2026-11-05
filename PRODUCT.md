# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

The board renders inside the Hermes Desktop app (Electron), using the app's own component library and theme variables. Desktop only for v1.

## Stack

Dictated by the Hermes plugin system, not a free choice:

- Desktop half: one uncompiled ESM `plugin.js` that imports only `@hermes/plugin-sdk`, `react` and `react/jsx-runtime` (UI written with `jsx()` calls, no JSX syntax, no build step). Registers a route page plus a sidebar nav row.
- Agent half: a Python Hermes plugin (`plugin.yaml` + `__init__.py`) with a `dashboard/plugin_api.py` backend reached from the desktop via `ctx.rest` (polling, since `ctx.socket` is a no-op on OAuth remotes).
- Shipped as one unified package folder: `plugins/<id>/` carrying the Python half and `desktop/plugin.js`.

## Users

Every Hermes Agent user who installs it from the Hermes Marketplace. Brendan is the first tester and dogfoods it on his own profile. Defaults are tuned for a stranger's install, not for Brendan's setup.

## Product Purpose

Idea Board turns what a user's Hermes already knows into a board of concrete things the agent can offer to do for them. Each night it reviews the day's conversations and the profile's capabilities (connected apps, messaging platforms, toolsets, MCP servers, installed plugins and skills) and posts a short set of ideas. Clicking an idea starts a new chat with a prompt that has the agent do it. Dismissing an idea records a reason, and future runs stop offering that idea, or anything matching that reason.

Success means the user starts ideas from the board, and the dismiss rate falls over time as the board learns what they don't want.

## Positioning

"Superpowers you aren't using." Every card is grounded in two things a generic suggestion engine can't see: a moment from the user's own conversations, and a capability this profile actually has (or could gain). Neighbouring catalog plugins suggest the next message in a chat (next-prompt, next-steps), check in when a chat is idle (alans-way), or run a broad proactive companion with goals and feeds (hermes-muse). Idea Board alone ties ideas to the capability inventory, recommends which connector to add next by how many new ideas it would unlock, and learns from dismissal reasons.

## Operating Context

- A nightly scheduled job, plus a "generate now" action for first run and demos.
- Ideas come from three sources, newest kind first:
  1. The user's conversations: work done by hand or topics revisited that the agent could take over.
  2. Capability combinations: two tools or connectors the user already has, paired in a way no seed covers.
  3. Seed use cases: about 100 generic ideas distilled once (light model) from the Hermes user-stories collection, each tagged with the capabilities it needs and linked to its source story. Shipped pinned in the package; nothing is fetched at runtime. Seeds are adapted to the user's own tools and topics, not shown verbatim.
- Generation is two-pass: draft about 20 candidates, then a critic keeps the best 5 or so, dropping anything not doable with current capabilities, near-duplicates of board items, and anything matching a dismissal reason.
- Connector suggestions: for each unconnected connector, count the ideas it would unlock and how many of those match the user's recent topics ("Connect Notion: 12 new ideas, 4 match your chats").
- Every card states where it came from (which conversation, which capabilities).
- Started and dismissed ideas steer the next run.
- The user reviews the board in the Desktop app; Desktop is the only surface in v1.

## Capabilities and Constraints

- Hackathon entry: Hermes Agent Plugin Hackathon, submissions due 2026-11-11 17:00 EST (16:00 CT). Entry = a PR adding the plugin to the Hermes plugin catalog, a demo video under 90 seconds on X tagging @NousResearch, and the submission form. Judged on usefulness, reliability, polish and creativity; judges favor plugins that do more than a prompt or a skill could.
- Catalog admission rules apply: pinned full commit SHA, no self-updating code, declared capabilities that match reality, credentials only through Hermes, approvals and unattended runs respected, risky behaviour disclosed (it reads conversation history and spends model tokens nightly).
- Must be profile-safe (`get_hermes_home()`), generic for any user, and independent of any personal vault or ledger.
- Starting an idea opens a new chat with the prompt placed in the composer; the user presses send (Brendan, 2026-11-04). The plugin never auto-sends.
- Tested 2026-11-04 (spike notes kept outside the repo):
  - Starting a new chat with a prompt: `host.newChat()` then `host.composer.setDraft('new', …)` retried every 100 ms; second try succeeds, 275–460 ms.
  - Reading connector status from plugin code via `ctx.dispatch_tool("manage_connections", {"action": "status"})`.
  - `ctx.llm.complete_structured` through the plugin's own model slot; schemas must set `additionalProperties: false` on every object.
- Still unverified: the plugin tool running inside a scheduled job end to end.
- The nightly job's model is user-configurable (Brendan, 2026-11-04): the plugin registers its own auxiliary model slot (`ctx.register_auxiliary_task("idea_board", …)`), which users set in Settings → Models → Auxiliary or `auxiliary.idea_board` in config. Hermes has no provider-neutral "cheap model" default, so until the user picks one it follows the main model; the board must show the model and token use per run and link to the setting.
- Model-written prompts must have `@…:` references and a leading `/command` neutralized: the composer turns them into attachments and commands.
- Users whose Desktop app connects to a remote backend must install the desktop half on the Desktop machine (Install from Git, Desktop target).
- The Python backend loads only when the plugin is in `plugins.enabled`; the desktop half is opt-in via Settings → Plugins. Install docs must say so.

## Brand Commitments

- Name: Idea Board (Brendan, 2026-11-04).

## Evidence on Hand

- Seed source: `website/src/data/userStories.json` in the hermes-agent repo (MIT), 395 stories with category, headline, quote and URL. Categories: dev-workflow 82, business-ops 57, personal-assistant 55, integrations 35, creative 28, enterprise 23, meta 23, cost-optimization 20, privacy 13, messaging 12, content-creation 12, research 12, marketing 9, general 9, trading 5. About a quarter (meta, cost, privacy) are not offerable tasks. Few name a Portal connector (Gmail 3, Notion 5, Slack 15, GitHub 12); many lean on messaging (Telegram 46, Discord 16), the browser (12) or schedules (about 60).
- Portal connector catalog: 54 services, status readable via `manage_connections`.
- Built-in automation blueprints: 16 in `cron/blueprint_catalog.py`.
- Prior art for the package shape: the `session-learning-inspector` plugin (hook + `dashboard/plugin_api.py` + sidebar page).
- No users, testimonials, metrics or screenshots exist yet. Do not fabricate any.

## Product Principles

1. Grounded or gone: every idea cites the conversation moment and the capability behind it; no generic filler.
2. A dismissal is a rule, not a delete: the reason shapes every future run.
3. One click to done: an idea is a ready-to-run prompt, not a suggestion to think about.
4. Few and good: a short nightly set beats a long feed.
5. Nothing leaves without the user: the board proposes and the user starts; the plugin never sends, posts or connects anything on its own.
