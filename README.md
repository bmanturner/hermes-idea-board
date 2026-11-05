# Idea Board

A nightly board of things your Hermes could do for you, grounded in your own chats and in the tools, connectors and skills this profile actually has.

Each night Idea Board reads the day's conversations, finds signals in code (things you asked for on several days, "remind me" loops, dates coming up, corrections, tools that keep failing, things Hermes said it couldn't reach), and asks a model to turn them into a short list of ideas. A second pass critiques them, and code checks every idea before it reaches the board. Click an idea to start it in a new chat, with the prompt already in the composer. You read it and press send. Dismiss an idea with a reason, and the reason becomes a rule that later runs follow.

## What makes an idea

- **Grounded or gone.** Every idea cites evidence found by code: your own words, the days you said them, or a usage count. The model can only cite evidence ids that exist.
- **Real capabilities only.** The capability list (toolsets, MCP servers, Portal connectors, skills, messaging platforms) is built in code. An idea that names a capability this profile doesn't have is dropped.
- **Three kinds.** *Do once* (close a loop, prep for a date), *Put on autopilot* (a scheduled job or standing skill), and *Connect next* (one connector that would unlock something you asked for).
- **No repeats.** Ideas are checked against the board, your scheduled jobs, Hermes' own suggested jobs, and your dismissal rules.

## Safety

The prompt on a card was written by a model that read your chats, and you send it with your full tool access. So code, not the model, controls what a card can carry:

- Only text you typed is quoted. Long pastes, attached context, fetched web or mail content and other people's messages in group chats are never quoted into the ideation prompt, and chat data is wrapped as untrusted.
- Every prompt starts with a fixed header asking the agent to show a plan and wait for your yes before anything that sends, posts, pays, books, deletes, shares or schedules.
- Links and email addresses you never typed are rejected. `@file:`/`@url:` references are defused so the composer can't attach or fetch anything. A small set of injection patterns is rejected.
- The risk badge is computed in code and can only go up from what the model claimed.
- Nothing is ever sent for you. The board places text in a new chat; you press send.

## What it reads, stores and costs

- **Reads:** your chats from the last 14 days (scheduled-job runs, subagents, hidden and group chats are skipped), this profile's tools, skills, connectors, platforms and scheduled jobs, and `memories/USER.md`.
- **Stores:** ideas, dismissals, rules and run history in `<HERMES_HOME>/plugin-data/idea-board/data.db`. Nothing leaves your machine except the two model calls per run.
- **Costs:** two model calls per run (ideation and critique). A run over two weeks of heavy use was about 70k tokens. The board shows the model and tokens for every run. Pick a cheaper model in **Settings → Models → Auxiliary → Idea Board** (or `auxiliary.idea_board` in `config.yaml`); until you do, it uses your main model.
- **Runs:** only when you schedule it in setup, or when you ask (the board's *Make my first ideas* / *Generate ideas now*, or `/idea-board generate`).

## Install

```bash
hermes plugins install bmanturner/hermes-idea-board --enable
```

Then in Hermes Desktop, turn on **Idea Board** in **Settings → Plugins**. It appears in the sidebar.

**Desktop connected to a remote Hermes** (e.g. a laptop talking to a home server): install the agent half on the server as above, then on the laptop use **Settings → Plugins → Install from Git** with `https://github.com/bmanturner/hermes-idea-board` and the **Desktop** target checked. The desktop half of a plugin installed on a remote server can't be read from another machine.

### First run: setup

Open **Idea Board** in the sidebar. Until you finish setup, the page shows a short setup instead of the board, and nothing runs:

1. **What it reads**: how many days of chats each run reads (7, 14 or 30) and how many new ideas a run may add (3, 6 or 10).
2. **Which model writes the ideas**: shows the model in use and its token cost on your last run, with a link to choose a smaller one for Idea Board alone.
3. **When it runs**: *Every night* at a time you pick (creates a scheduled job only when you press *Schedule it*), or *Only when I ask*.
4. **Your first ideas**: opens a new chat with `/idea-board generate` ready; you press send.

Reopen it any time with **Setup** at the top of the board. The *Idea Board nightly ideas* blueprint (Desktop Cron page, `/blueprint idea-board:nightly`) schedules the same job from outside the board.

### Settings

Setup stores your choices in the plugin's own data. Without setup, these keys in `plugins.entries.idea-board.settings` (or the form in Settings → Plugins) apply:

| Key | Default | Meaning |
|---|---|---|
| `max_cards` | 6 | Most new ideas per run |
| `history_days` | 14 | Days of chat history each run reads |

## Using the board

- `↑`/`↓` move, `Enter` starts, `N` hides an idea for a week, `D` dismisses with a reason.
- **Dismiss reasons:** *Not relevant to me*, *Not this topic*, *Don't automate this*, *Too risky* and *Wrong tool for this* become rules. *Already handled* marks the evidence as done. A rule starts narrow (this topic) and widens only when a second dismissal agrees. **What I've learned** lists every rule; edit or delete them there.
- **Started** lists ideas you've started, linked to their chats.

## Commands and tools

- `/idea-board generate` runs once in the background; `/idea-board status` shows the last run.
- `idea_board_run` (tool) runs once; the nightly job calls it.

## Development

```bash
python3 -m unittest tests.test_core tests.test_api   # core and backend, on a made-up user
hermes plugins validate .                            # catalog checks
```

Layout: `idea_board/` is the core (evidence, safety, prompts, pipeline, store). `inventory.py` and `transcripts.py` are the only modules that read Hermes. `dashboard/plugin_api.py` is the board's REST backend, `desktop/plugin.js` the page. `docs/nightly-run.md` describes the pipeline.

## License

MIT
