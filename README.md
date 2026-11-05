# Idea Board

I'm your Hermes agent's idea board. Each night I read your chats and what this profile can do (its tools, connectors and skills), and I post a short board of things I could take off your plate, each tied to your own words.

Each night I go through the day's conversations and find signals in code: things you asked for on several days, "remind me" loops, dates coming up, corrections, tools that keep failing, things I said I couldn't reach. A model turns them into a short list of ideas, a second pass critiques them, and code checks every idea before it reaches the board. Click an idea and I open a new chat with the prompt already in the composer; you read it and press send. Dismiss an idea with a reason, and the reason becomes a rule I follow on every later run.

## What makes an idea

- **Grounded or gone.** Every idea cites evidence found by code: your own words, the days you said them, or a usage count. The model can only cite evidence ids that exist.
- **Real capabilities only.** The capability list (toolsets, MCP servers, Portal connectors, skills, messaging platforms) is built in code. An idea that names a capability this profile doesn't have is dropped.
- **Three kinds.** *Do once* (close a loop, prep for a date), *Put on autopilot* (a scheduled job or standing skill), and *Connect next* (one connector that would unlock something you asked for).
- **No repeats.** Ideas are checked against the board, your scheduled jobs, Hermes' own suggested jobs, and your dismissal rules.

## Which connector to add next

Every run, I also work out which connectors would open up the most new ideas for you, in code, with no model call:

1. **Seed ideas.** `data/seeds.json` holds 128 generic ideas distilled once from the [Hermes user stories](https://hermes-agent.nousresearch.com/docs/user-stories), each linked to its stories and tagged with the kinds of tool it needs (email, calendar, notes, tasks, team chat, payments, and so on; the full list is `CLASSES` in `idea_board/seeds.py`).
2. **What you have.** Your toolsets, MCP servers, skills, messaging platforms and connected Portal connectors are mapped to those same kinds.
3. **What each connector adds.** Each Portal connector in `data/connectors.json` is tagged with the kinds it adds. For every connector you could still connect, I count the seed ideas you can't do today but could with it, and how many of those match what you've talked about: two of the idea's topic words came up together in one of your recent chats, and the topic came up in at least two.
4. **Grounded or gone.** A connector is suggested only if at least one idea it opens up matches your chats. One that merely opens up many generic ideas (a sales tool for someone who isn't selling) is not. If nothing qualifies, the group doesn't appear.
5. **The board.** The top three appear under *Connect next*: "Connect Todoist · 9 new ideas · 3 match your chats". Connectors that open up exactly the same ideas are folded together ("or Linear, Asana, Jira"). Pick one to see the ideas it would make possible and a ready message; *Connect in a new chat* places it in the composer for you to send, and *Not interested* stops suggesting it (with Undo).

Ideas you can already do from the seed list are also given to the nightly run as starting points, adapted to your own tools and topics. After you connect something, send `/idea-board connectors` to recheck right away; otherwise the next run notices.

## Safety

The prompt on a card was written by a model that read your chats, and you send it with your full tool access. So code, not the model, controls what a card can carry:

- Only text you typed is quoted. Long pastes, attached context, fetched web or mail content and other people's messages in group chats are never quoted into the ideation prompt, and chat data is wrapped as untrusted.
- Every prompt starts with a fixed header asking the agent to show a plan and wait for your yes before anything that sends, posts, pays, books, deletes, shares or schedules.
- Links and email addresses you never typed are rejected. `@file:`/`@url:` references are defused so the composer can't attach or fetch anything. A small set of injection patterns is rejected.
- The risk badge is computed in code and can only go up from what the model claimed.
- Nothing is ever sent for you. The board places text in a new chat; you press send.

## What I read, store and cost

- **Reads:** your chats from the last 14 days (scheduled-job runs, subagents, hidden and group chats are skipped), this profile's tools, skills, connectors, platforms and scheduled jobs, and `memories/USER.md`.
- **Stores:** ideas, dismissals, rules and run history in `<HERMES_HOME>/plugin-data/idea-board/data.db`. Nothing leaves your machine except the two model calls per run.
- **Costs:** two model calls per run (ideation and critique). A run over two weeks of heavy use was about 70k tokens. The board shows the model and tokens for every run. Pick a cheaper model in **Settings → Models → Auxiliary → Idea Board** (or `auxiliary.idea_board` in `config.yaml`); until you do, it uses your main model.
- **Runs:** only when you schedule it in setup, or when you ask (*Make my first ideas* in setup, *Make ideas now* on an empty board, or `/idea-board generate`).

## Install

```bash
hermes plugins install bmanturner/hermes-idea-board --enable
```

Then in Hermes Desktop, turn on **Idea Board** in **Settings → Plugins**. It appears in the sidebar.

**Desktop connected to a remote Hermes** (e.g. a laptop talking to a home server): install the agent half on the server as above, then on the laptop use **Settings → Plugins → Install from Git** with `https://github.com/bmanturner/hermes-idea-board` and the **Desktop** target checked. The desktop half of a plugin installed on a remote server can't be read from another machine.

### First run: setup

Open **Idea Board** in the sidebar. Until you finish setup, the page shows a short setup instead of the board, and nothing runs. Steps are on the left with your current choice under each; the step you pick opens on the right:

1. **What I read**: how many days of chats each run reads (7, 14 or 30) and how many new ideas a run may add (up to 3, 6 or 10), with one of your ideas (or an example) to show what the board makes.
2. **Which model I use**: shows the model in use and its token cost on your last run, with a link to choose a smaller one for Idea Board alone.
3. **When I run**: *Every night* at a time you pick (creates a scheduled job only when you press *Schedule it*), or *Only when you ask*.
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

- `/idea-board generate` runs once in the background; `/idea-board connectors` rechecks which connectors would help (no model call); `/idea-board status` shows the last run.
- `idea_board_run` (tool) runs once; the nightly job calls it.

## Compatibility

I use public plugin APIs everywhere except three Hermes internals that have no public equivalent yet. `hermes plugins validate` lists them as warnings (catalog rule 9: public surfaces only):

| Internal | What I use it for | If a Hermes release moves it |
|---|---|---|
| `hermes_cli.tools_config._get_platform_tools` and `toolsets.resolve_toolset` | Which toolsets are on for chats, so ideas only use tools you can actually call | I fall back to every installed toolset minus `agent.disabled_toolsets`; lazily loaded MCP servers stay listed |
| `cron.suggestions.load_suggestions` | Hermes's own suggested jobs, so I don't suggest them again | I skip that duplicate check and say so in the run's notes |

`tests/test_compat.py` breaks each one on purpose and checks the board keeps working. A request for public versions is open upstream (link added when filed).

## Development

```bash
python3 -m unittest tests.test_core tests.test_api tests.test_seeds tests.test_compat   # core, backend, connector ranking, fallbacks; on a made-up user
hermes plugins validate .                            # catalog checks
```

Layout: `idea_board/` is the core (evidence, safety, prompts, pipeline, store, and `seeds.py` for seed ideas and connector ranking). `inventory.py` and `transcripts.py` are the only modules that read Hermes. `dashboard/plugin_api.py` is the board's REST backend, `desktop/plugin.js` the page. `docs/nightly-run.md` describes the pipeline.

## License

MIT
