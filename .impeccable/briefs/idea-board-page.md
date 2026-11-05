# Idea Board page: surface brief

Mode: operate. Route: `/idea-board` (Desktop plugin page + sidebar row "Idea Board").
Seed: seed:cdd7d278fb124a6c. Chosen structure: list + detail (Brendan, 2026-11-04, option 1 of three sketches).

THESIS
The ideas Hermes thinks it could do for you, each one backed by your own words and the tools this profile really has, ready to start in one click.

OWN-WORLD
Hermes Desktop's established world, inherited, not reinvented: the app's own components (`Button`, `Badge`, `Codicon`, `Kbd`, `DropdownMenu`, `Textarea`, `EmptyState`, `Loader`), its theme variables (`--ui-text-*`, `--ui-stroke-tertiary`, `--ui-bg-quaternary`, `--ui-accent`), its font. Flat, not boxed: no card-in-card, group with whitespace and single hairlines. Follows every theme, skin and light/dark mode automatically. No colours, fonts or shadows of our own.

STORY
Open the page → read the receipt (what last night's run read and kept) → scan the list grouped by kind → pick an idea → see why (the user's own words, the days they said them, the tools it uses) and the exact prompt that will go into the chat → Start (new chat, prompt in the composer, user presses send), Not now (snooze 7 days), or Dismiss with a reason that becomes a visible rule.

FIRST VIEWPORT
Header: title "Idea Board", the run receipt (when, chats read, signals, drafted/kept, model + tokens, "Change model"), and "What I've learned (n)". Body: left column (~340px) list grouped "Put on autopilot", "Do once", "Connect next", each row title + value; right detail of the selected idea: title, one meta line (kind · schedule · value · due date), why, evidence, capabilities, prompt preview, actions.

FORM
Signature move: the evidence day ribbon. Fourteen small dots for the last two weeks; the days the user said the quoted thing are filled with the accent. It shows "you keep asking for this" without a number to read. Everything else is the app's standard controls.

FINISH
- The meta line sits under the title (no eyebrow above a heading).
- Prompt preview: a quiet-fill block with a "PROMPT · GOES INTO A NEW CHAT" overline, matching Hermes's Scheduled jobs prompt block (DESIGN.md, 2026-11-05; supersedes the hairline treatment).
- Type, color, spacing and voice follow DESIGN.md and PRODUCT.md Brand Commitments (2026-11-05).
- States: loading (`Loader`), backend off (explains both switches: Settings → Plugins and `plugins.enabled`), never run (Generate now), empty board after a run, error from last run (shown in the receipt), dismiss menu with reason chips + optional note, undo after dismiss, rules drawer (edit, delete), start failure (prompt copied to clipboard instead).
- Keyboard: ↑/↓ moves the selection, Enter or S starts, D opens dismiss, N snoozes.
- Rejected looks: one-idea-at-a-time deck (option 2) and kind columns (option 3).
