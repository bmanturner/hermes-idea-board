# Nightly run: context packet and prompts (draft v0, 2026-11-04)

Three stages. Only stages 2 and 3 call a model.

## Stage 1: build the context packet (code, no LLM)

Facts about capabilities come from code, never from the model's self-report.

| Block | Source | Contents |
|---|---|---|
| PROFILE | `memories/USER.md`, `memories/MEMORY.md`, config timezone | who the user is, standing preferences, now (local time) |
| CAPABILITIES | `hermes tools list`, Portal connector status, `hermes mcp list`, gateway platforms, `hermes skills list`, `hermes plugins list` | one row per capability: `id`, kind (tool / connector / mcp / platform / skill / plugin), status (ready / available-not-connected / disabled), one-line "can do", tool names |
| AUTOMATIONS | `hermes cron list`, recent `cron runs`, blueprint catalog | existing jobs (name, schedule, what, last result), failing jobs, unused blueprints |
| TODAY | `state.db`, sessions active in the last 24 h | per session: id, title, source, user messages (trimmed), tools called with ok/error, unanswered questions, promises ("I'll…", "remind me…"), abandoned endings |
| HISTORY | `state.db`, last 14 days | per session: id, date, title, top tools, 1-line topic; per capability: times used |
| BOARD | plugin state | open ideas, started ideas (and whether the chat finished), dismissed ideas with reasons, dismissal rules |
| SEEDS | shipped seed library, pre-filtered in code | seeds whose required capabilities are ready or one connector away |
| UNLOCKS | code | per not-connected connector: seeds it unlocks, how many match HISTORY topics |

Excluded: hidden sessions, cron sessions (they feed AUTOMATIONS), and Idea Board's own runs.

## Stage 2: ideation prompt

```
You are Idea Board's nightly ideation pass for one Hermes user. Your job: find the
most valuable things this user's Hermes could do for them, using ONLY the
capabilities listed in CAPABILITIES. Each idea becomes a card; clicking it opens a
new chat with your prompt in the composer for the user to send.

<PROFILE>…</PROFILE>
<CAPABILITIES>…</CAPABILITIES>
<AUTOMATIONS>…</AUTOMATIONS>
<TODAY>…</TODAY>
<HISTORY>…</HISTORY>
<BOARD>…</BOARD>
<SEEDS>…</SEEDS>
<UNLOCKS>…</UNLOCKS>

Work through these lenses, in order. Note evidence before ideas.
1. Repeated by hand: a task the user did or asked for 2+ times in HISTORY/TODAY.
   → a recurring idea (a scheduled job) or a skill that makes it one step.
2. Open loops: promises, unanswered questions, failed tool calls, chats that
   ended mid-task. → a one-time idea that closes the loop.
3. Coming up: dates, deadlines, trips, meetings, purchases mentioned. → one-time
   prep, with an expiry date.
4. Underused power: ready capabilities used 0–1 times in 14 days that fit the
   user's actual topics. → an idea that puts them to work on those topics.
5. Combinations: chain 2+ ready capabilities (input from one, action in
   another, delivery through a messaging platform) in a way no seed covers.
6. Automation upgrades: existing jobs that fail, overlap, or could do more.
7. Missing capability: something the user wanted that no ready capability can
   do. → a connector suggestion only if UNLOCKS has a connector that does it.
8. Seeds: adapt matching SEEDS to this user's tools, people and topics. Never
   copy a seed verbatim.

Rules
- Grounded: every idea cites evidence (session ids + a short quote, or a
  capability usage count). No evidence, no idea.
- Specificity test: if the idea would read the same for a different user,
  rewrite it around this user's specifics or drop it.
- Real capabilities only: list every capability id the idea uses in `uses`.
  An id not in CAPABILITIES (status ready) disqualifies the idea, except a
  single not-connected connector on a `connector` card.
- Respect BOARD: no idea matching an open card or a dismissal rule. Read the
  dismissal reasons as rules about kinds of ideas, not single cards.
- The prompt you write runs in a fresh chat with none of this context. Make it
  self-contained: the goal, the specifics (names, dates, files, session ids to
  look at), the skills to load, the tools to use, and what "done" means.
- Safety in the prompt: anything that sends, posts, pays, books, deletes or
  shares is drafted and shown to the user for a yes first. A recurring idea's
  prompt sets up the scheduled job (schedule, delivery target from
  CAPABILITIES, skills to attach), runs it once as a test, and shows the result.
- Kinds: `once` (do it now), `recurring` (a scheduled job or standing skill),
  `connector` (add one connector; say what it unlocks for this user).

Return about 20 candidates as JSON:
[{ "title": "≤60 chars, verb first",
   "kind": "once|recurring|connector",
   "lens": 1-8,
   "why": "one sentence a user would nod at",
   "evidence": [{"session_id": "...", "quote": "..."}] | [{"capability": "...", "uses_14d": 0}],
   "uses": ["capability ids"],
   "schedule": "cron expr + timezone (recurring only)",
   "expires": "YYYY-MM-DD or null",
   "minutes_saved": {"per_run": n, "runs_per_month": n},
   "risk": "none|drafts-for-approval|external-action",
   "prompt": "the full prompt placed in the new chat",
   "seed_id": "seed id or null" }]
```

## Stage 3: critic prompt

```
You are Idea Board's critic. Below are tonight's candidates and the same BOARD.
Score each 1–5 on: value (minutes saved × runs, or stakes for one-time),
specificity (only fits this user), feasibility (uses only ready capabilities;
prompt is self-contained and would actually work), novelty (not on BOARD, not
covered by AUTOMATIONS, not matching a dismissal rule), urgency (expires soon).
Drop anything scoring 1 on feasibility or novelty.
Keep the best 5–7: at least one recurring and one one-time when they exist, at
most one connector card. Return the kept cards unchanged except for tightened
titles and "why" lines, plus your scores and one line on why each made the cut.
```

## After stage 3 (code)

- Validate every `uses` id against CAPABILITIES; drop cards that fail.
- Dedupe against BOARD by embedding or normalized title.
- Store cards; the Desktop board shows them grouped: Today (expiring), Recurring, One-time, Connect next.
