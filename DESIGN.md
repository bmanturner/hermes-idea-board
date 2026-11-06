---
name: Idea Board
description: A field notebook inside Hermes Desktop; dated notes in your own words, each with a ready-to-run offer.
colors:
  accent: "#0053fd"
  on-accent: "#ffffff"
  ink: "#1f2328"
  page: "#fbfbfc"
  text-primary: "#1f2328f0"
  text-secondary: "#1f2328bd"
  text-tertiary: "#1f23288a"
  hairline: "#0a44bb25"
  ring: "#0846c438"
  fill-soft: "#0d3ea116"
  fill-quiet: "#0f3b940f"
  row-hover: "#0d3fa412"
  row-active: "#0b41af20"
  alert: "#cf2d56"
typography:
  overline:
    fontFamily: "Segoe WPC, Segoe UI, -apple-system, BlinkMacSystemFont, SF Pro Text, system-ui, sans-serif"
    fontSize: "0.6rem"
    fontWeight: 500
    lineHeight: 1.5
    letterSpacing: "0.05em"
  meta:
    fontFamily: "Segoe WPC, Segoe UI, -apple-system, BlinkMacSystemFont, SF Pro Text, system-ui, sans-serif"
    fontSize: "0.7rem"
    fontWeight: 400
    lineHeight: 1.5
  control:
    fontFamily: "Segoe WPC, Segoe UI, -apple-system, BlinkMacSystemFont, SF Pro Text, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.33
  row:
    fontFamily: "Segoe WPC, Segoe UI, -apple-system, BlinkMacSystemFont, SF Pro Text, system-ui, sans-serif"
    fontSize: "0.78rem"
    fontWeight: 500
    lineHeight: 1.5
  body:
    fontFamily: "Segoe WPC, Segoe UI, -apple-system, BlinkMacSystemFont, SF Pro Text, system-ui, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 400
    lineHeight: 1.5
  title:
    fontFamily: "Segoe WPC, Segoe UI, -apple-system, BlinkMacSystemFont, SF Pro Text, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 600
    lineHeight: 1.43
  quote:
    fontFamily: "Segoe WPC, Segoe UI, -apple-system, BlinkMacSystemFont, SF Pro Text, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 400
    lineHeight: 1.5
  idea-title:
    fontFamily: "Segoe WPC, Segoe UI, -apple-system, BlinkMacSystemFont, SF Pro Text, system-ui, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.01em"
rounded:
  row: "2px"
  control: "2.5px"
  block: "4px"
  full: "9999px"
spacing:
  hair: "2px"
  xs: "4px"
  icon: "6px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "4px 10px"
  button-secondary:
    backgroundColor: "{colors.fill-soft}"
    textColor: "{colors.text-primary}"
    typography: "{typography.control}"
    rounded: "{rounded.control}"
    padding: "4px 10px"
  button-text:
    textColor: "{colors.text-tertiary}"
    typography: "{typography.control}"
  list-row:
    textColor: "{colors.text-primary}"
    typography: "{typography.row}"
    rounded: "{rounded.row}"
    padding: "6px 8px"
  list-row-hover:
    backgroundColor: "{colors.row-hover}"
  list-row-selected:
    backgroundColor: "{colors.row-active}"
  group-overline:
    textColor: "{colors.text-tertiary}"
    typography: "{typography.overline}"
  idea-title:
    textColor: "{colors.text-primary}"
    typography: "{typography.idea-title}"
  quote:
    textColor: "{colors.text-primary}"
    typography: "{typography.quote}"
  day-dot:
    backgroundColor: "{colors.accent}"
    rounded: "{rounded.full}"
    size: "6px"
  day-dot-empty:
    rounded: "{rounded.full}"
    size: "6px"
  prompt-block:
    backgroundColor: "{colors.fill-quiet}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.body}"
    rounded: "{rounded.block}"
    padding: "10px"
  undo-bar:
    backgroundColor: "{colors.fill-soft}"
    textColor: "{colors.text-secondary}"
    typography: "{typography.body}"
    rounded: "{rounded.block}"
    padding: "8px 12px"
  step-marker:
    textColor: "{colors.text-tertiary}"
    typography: "{typography.meta}"
    rounded: "{rounded.full}"
    size: "18px"
  step-marker-done:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.full}"
    size: "18px"
---

# Design System: Idea Board

## Overview

**Creative North Star: "The Field Notebook"**

Idea Board is a field notebook kept inside Hermes Desktop. Each entry is dated, quotes the user in their own words, names the tools it would use, and ends with an offer that is ready to run. The notebook is quiet and factual: it never sells, never decorates, and never claims anything it can't show the date and the words for.

The notebook is written on Hermes's own paper. Every color, font, control, dialog and shadow comes from the host app, so Idea Board follows every theme, skin and light or dark mode with no work of its own, and reads as a first-party Hermes page. The page chrome (titles, rows, meta lines, controls) is exactly Hermes-sized. One moment on any page is allowed to be larger: the idea itself, meaning its title and the user's quoted words. That contrast is the whole visual identity; nothing else needs to be loud.

Density follows Hermes's Scheduled jobs page: a 14px page title, 12.5px list rows, 11.2px meta, uppercase 9.6px group labels, flat rows with a tinted selection, and one blue action per view. Separation comes from whitespace and single hairlines, never from boxes.

**Key Characteristics:**
- Borrowed ink: host variables only; no literal colors, fonts or shadows in plugin code.
- Hermes-sized chrome with one larger reading moment (idea title 20px, quotes 15px).
- Every observation is dated (the 14-day ribbon, the run receipt).
- Flat and hairline-separated; tonal fills mark state, not structure.
- One filled blue action per view.

**Surfaces this covers:** the sidebar row, the board (header and receipt, idea list, idea detail, undo bar, started list), setup, the dismiss menu and dismiss-with-a-note dialog, the "What I've learned" dialog, pop-up notices, empty, loading, error and backend-off states, the command palette entries, the plugin's settings form, the scheduled-job and blueprint cards, chat replies to `/idea-board`, and README screenshots. Copy voice for all of them lives in PRODUCT.md (Brand Commitments).

## Colors

Hermes's own palette, borrowed whole: an ink neutral at stepped opacities, one signal blue, and blue-tinted transparent fills. Values below are light-theme samples from Hermes Desktop on 2026-11-05; the normative source is always the host CSS variable named in each entry.

### Primary
- **Hermes Signal Blue** (`--ui-accent`): the primary action of a view (Start in a new chat, Schedule it), filled day dots, and finished step markers. Nothing else.
- **On-Accent White** (`--dt-primary-foreground`): text and icons on Signal Blue (the primary button label, the check in a finished step marker).

### Neutral
- **Ink** (`--ui-base`): the root of every text tone. Never used directly.
- **Page** (`--ui-bg-editor`): the page background the board sits on. Plugin code never paints it.
- **Primary Text** (`--ui-text-primary`): page title, idea title, quotes, list row titles, rule text.
- **Secondary Text** (`--ui-text-secondary`): the "why" paragraph, prompt body, undo message.
- **Tertiary Text** (`--ui-text-tertiary`): receipts, meta lines, group overlines, row values, keyboard hints, the promise beside Start, text actions at rest. This is the faintest tone Idea Board uses; Hermes's quaternary tone is below a readable contrast at these sizes.
- **Hairline** (`--ui-stroke-tertiary`): the header rule, the list/detail divider, rows in the rules dialog.
- **Ring** (`--ui-stroke-secondary`): the 1px ring of empty day dots and unfinished step markers. One step stronger than Hairline so the fourteen-day scale stays visible in dark mode.
- **Soft Fill** (`--ui-bg-quaternary`): the undo bar and secondary buttons.
- **Quiet Fill** (`--ui-bg-quinary`): the prompt block.
- **Row Hover** (`--ui-row-hover-background`) and **Row Selected** (`--ui-row-active-background`): list row states, exactly as Hermes's own lists use them.
- **Alert Red** (`--ui-red`): run errors in the receipt and failed-state text. Hermes has no `--ui-text-danger`; don't reference it.

### Named Rules
**The Borrowed Ink Rule.** Every color in plugin code is `var(--ui-…)`. A hex, rgb or named color in `plugin.js` is a bug, because it breaks the user's theme.

**The One Blue Rule.** At most one filled blue control per view, dialogs and setup steps included. Selection uses the row tint, not blue; links and text actions stay tertiary until hovered. Setup's Finish button turns blue only when the open step has no blue action of its own.

## Typography

**Body Font:** the host's sans stack (`--font-sans`: Segoe WPC, Segoe UI, -apple-system, SF Pro Text, system-ui)
**Label/Mono Font:** none. The prompt preview is a message the user will send, so it stays in the sans.

**Character:** one system sans at Hermes's own small sizes, with weight (500/600) doing the hierarchy work, and a single step up in size for the idea and the user's words.

### Hierarchy
- **Idea title** (600, 20px / 1.25rem, 1.25, -0.01em, balanced wrap): the selected idea's title in the detail pane. The reading moment. One per view.
- **Quote** (400 italic, 15px / 0.9375rem, 1.5): the user's own words in the evidence block. Curly quotes. Tool-friction evidence (not a quote) drops the italic and the quotes.
- **Title** (600, 14px / 0.875rem, 1.43): page title ("Idea Board"), setup step titles, dialog titles via the host Dialog.
- **Body** (400, 13px / 0.8125rem, 1.5, max 68ch): the "why" paragraph, setup explanations, prompt body, rule text, undo message.
- **Row** (500, 12.5px / 0.78rem, 1.5): list row titles; Hermes's own list size.
- **Control** (500, 12px / 0.75rem): set by host Button, SegmentedControl and Badge; listed so nothing else uses it by accident.
- **Meta** (400, 11.2px / 0.7rem, 1.5): receipt, meta line, row values, day counts, keyboard hints, the promise beside Start.
- **Overline** (500, 9.6px / 0.6rem, 0.05em, uppercase): group labels ("PUT ON AUTOPILOT · 2"), the "YOUR MESSAGE" label, "STARTED", "SETUP · 2 OF 4 DONE", "STEP 1 OF 4". Always followed by `· count` when it heads a list.

### Named Rules
**The One Reading Moment Rule.** Only the idea title and quotes are larger than Hermes's 14px page title. If a new element wants to be big, it is the wrong element.

**The Eight Roles Rule.** Plugin code sets font sizes only from the roles above (0.6, 0.7, 0.75, 0.78, 0.8125, 0.875, 0.9375 and 1.25rem). No half-pixel one-offs.

**The Real Heading Rule.** The page title is an `h1`, the selected idea's title and each setup step title are `h2`, and setup's sample idea is an `h3`, so screen readers can jump between them.

## Layout

Every page-level surface uses one frame: page padding 24px top and 32px sides; a header row (title, then one meta line under it, actions right-aligned on the baseline); a single hairline; then the body filling the remaining height and scrolling inside itself, so primary actions are never clipped by the window.

The board body is master-detail: a 320px list column, a hairline, 32px of air, then the detail column. Detail prose caps at 68ch and the detail column at 720px; the extra width stays empty on the right rather than stretching text. Groups in the list are separated by 16px; rows within a group by 2px.

Rhythm is a 4px grid: 2 (inside a row), 4, 6 (icon to label, as in Hermes buttons), 8 (related items), 12 (within a block), 16 (between blocks), 24 (between sections), 32 (between regions). Setup and empty states use the same frame and the same left edge as the board, so moving between them never shifts the page.

Narrow windows (provisional, not built): below about 760px of page width the list stacks above the detail.

## Elevation & Depth

Flat. Idea Board defines no shadows. Depth comes from three things only: hairlines for structure, tonal fills (row tint, soft fill, quiet fill) for state, and the host's own popovers and dialogs, which bring their own elevation. The empty day dot is drawn as a 1px inset ring in the Ring color, not as a border or shadow.

### Named Rules
**The Hairline Rule.** Sections are separated by whitespace or one 1px hairline. No boxes around sections, no card-in-card, no colored side stripes.

## Shapes

Hermes's small-radius geometry: 2px on list rows, 2.5px on controls (from the host Button), 4px on blocks (prompt block, undo bar), and full circles only for the 6px day dots and 18px step markers. Nothing in Idea Board uses Hermes's large 12px card radius, because nothing in Idea Board is a card.

## Components

### Buttons
Host `Button` only; never a hand-styled `<button>` that looks like one.
- **Shape:** gently squared (2.5px), 4px 10px padding at default size.
- **Primary:** Signal Blue fill, white 12px/500 text, optional leading codicon at 6px gap. One per view: "Start in a new chat" on the board, "Schedule it for 3:30 AM" in setup.
- **Secondary:** soft fill, primary text: "Not now", "Done", "What I've learned (n)".
- **Text actions:** host `text` and `textStrong` variants, inline size: "Open chat", "Show all", "Copy prompt", "Undo", "Change model".
- **Ghost with caret:** the Dismiss menu trigger.

### Idea list row (signature)
- **Shape:** flat, 2px radius, 6px 8px padding, no border.
- **Content:** title in Row type (primary text), value line under it in Meta (tertiary), 2px apart.
- **States:** hover takes Row Hover; selected takes Row Selected and stays 500 weight (no weight jump, so rows don't reflow). Keyboard ↑/↓ moves the selection; the focused page owns the keys.
- **Groups:** an overline with the kind's codicon and count heads each group.
- **Older:** last in the list, under an overline "Older · n" with a Show/Hide text action (no toggle when nothing else is on the board, where it opens by itself). Its rows carry "Set aside <day time>" as the value line. The detail adds one Meta line saying why it was set aside, and "Back on the board" (secondary) takes the place of "Not now".

### Evidence block and day ribbon (signature)
- **Quote:** Quote type, primary text, italic in curly quotes.
- **Ribbon:** fourteen 6px dots, 3px apart, oldest left; days the user said it are filled Signal Blue, the rest are 1px Ring-colored rings. It is never replaced by a number alone.
- **Line under the quote:** ribbon, then Meta text ("2 days in the last two weeks"), then the "Open chat" text action.

### Badges
Host `Badge`, muted variant only, codicon leading at 4px: capabilities (deduplicated by name), the due date (`calendar` codicon, "by Nov 29") and "Stretch". Badges never take color; each carries a tooltip saying what it means.

### Message block (the prompt)
- **Style:** Quiet Fill, 4px radius, 10px padding, Body type in secondary text. The text inside is clamped to 8 lines with "Show all"; the clamp sits on an inner element so the padding never shows a half line.
- **Label:** a "YOUR MESSAGE · GOES INTO A NEW CHAT" overline above it, in the place of the PROMPT label on Hermes's Scheduled jobs page. The block is the user's own words, so its "I" is the user.
- **Footer:** "Show all" (only when the clamp can cut something off) and "Copy prompt".
- **The promise:** the agent's promise sits under the Start row in Meta tertiary, never inside or under the user's message: "You read it and press send. I'll show you a plan first and act only after your yes." 

### Connector recommendation
Ranked in code and shown in the *Connect next* group, after the model's own connect ideas, as ordinary list rows: "Connect Todoist" over "9 new ideas · 3 match your chats". Its detail follows the idea detail exactly:
- **Title:** "Connect {Name}" in the idea-title role; meta line with the `plug` codicon, "Connect next", "adds {what it adds}" and "or {alternatives}".
- **Why:** the agent's sentence: "With Todoist connected, I could take on 9 new ideas. 3 of them match what you've talked about lately (deadline, todo, priority)."
- **Ideas it would make possible · N:** up to eight rows, Row title over a Meta line ("Matches your chats: todo" first, otherwise what the idea does), then "and N more". Not clickable.
- **Message block, actions and promise** as for ideas: "Connect in a new chat" (primary, `plug` codicon) and "Not interested" (secondary; undo bar "I won't suggest Todoist again."), then "You read it and press send. Nothing connects until you approve it in the connect step." Keyboard: Enter connects, N or D hides.

### Undo bar
Soft fill, 4px radius, 8px 12px padding, Body type; message left, then "Edit rules" (text action, only when the dismissal made a rule) and "Undo" (textStrong). It appears at the top of the detail column after a dismiss or snooze and stays until the next action (another dismiss or snooze, picking another idea, or Start). No timer. A new rule is shown as the agent's own sentence: "Dismissed. I'll stay off the topic "job search"." 

### Step marker (setup)
An 18px circle with a 1px Ring-colored ring and the step number in Meta tertiary; when done, Signal Blue fill with a white check codicon. Step titles use Title type.

### Dialogs, menus and notices
Host `Dialog`, `DropdownMenu`, `Textarea` and `host.notify` exactly as shipped.
- **Reason choice** (dismiss-with-a-note dialog): a single-select list of idea-list rows (`role="radiogroup"` / `radio`), the chosen row tinted Row Selected with a blue check. The dialog's Dismiss button is its only blue.
- **Deleting a rule** asks inline first ("Delete this rule? I may suggest these ideas again." Delete · Keep).
- **Notices** say what failed in the agent's voice, with a short reason and the next step: "I couldn't dismiss it (404 Not Found). Try again in a moment." 

### Navigation
The sidebar row uses the host nav area with the `lightbulb` codicon and the label "Idea Board". Command palette entries: "Open Idea Board" and "Idea Board: generate ideas now".

### Header and receipt
Title, then one Meta line that starts with the schedule ("I run nightly at 3:30 AM", "I run when you ask", or a "Not scheduled · Schedule" link into setup step 3), then the last run ("Last run Wed 5:41 PM", "I read 60 chats and kept 6 of 18 ideas", model and tokens) and "Change model". When the scheduled-jobs list can't be read, the schedule part is left out rather than guessed. Header actions right-align, including when they wrap in a narrow window.

### Empty, loading and error states
Host `EmptyState` (title plus one line) centered in the body, an optional Meta line under it, and at most one action button; host `Loader` while loading. Buttons that open a chat say so ("Make ideas in a new chat"). Commands appear in host inline-code style, never loose in a sentence. Errors name what failed and the one thing to do next.

### Keyboard
↑/↓ move the selection, Enter starts (from the page or a row), N hides for a week (not on Older ideas), D opens dismiss-with-a-note. Keys work anywhere on the page except text fields, ignore case, and do nothing with Ctrl, Alt or Cmd held. After a dismiss or snooze, focus moves to the idea that took its place.

## Do's and Don'ts

### Do:
- **Do** write every color as a host variable (`var(--ui-text-tertiary)`, `var(--ui-row-active-background)`).
- **Do** use Row Hover and Row Selected for list states, exactly as Hermes's own lists do.
- **Do** keep the idea title (20px) and quotes (15px) as the only text larger than 14px.
- **Do** date every observation: the ribbon for quotes, the receipt for runs ("Last run Wed 5:41 PM · read 60 chats").
- **Do** keep one filled blue button per view and put it first in its row.
- **Do** keep the page frame (24px/32px padding, header, hairline, self-scrolling body) on every surface, including setup and empty states.
- **Do** take README and demo screenshots in Hermes's default light theme at 1280×800, with real ideas, never invented ones.

### Don't:
- **Don't** write a hex, rgb or named color, a font-family other than the host's `var(--font-mono)` for inline code, or a box-shadow other than the 1px inset Ring on empty day dots and step markers, in `plugin.js`.
- **Don't** reference `--ui-text-danger`; it doesn't exist in Hermes. Use `--ui-red` for errors.
- **Don't** use font sizes outside the eight roles (no 11.5, 13.5 or 22px one-offs; 12.5px comes only from the Row role).
- **Don't** box sections, nest cards, or add colored side stripes; use a hairline or whitespace.
- **Don't** use the blue fill for selection or for more than one action in a view, dialogs included.
- **Don't** use Hermes's quaternary text tone; Tertiary is the faintest.
- **Don't** put the agent's "I" next to the user's "I": the promise goes beside Start, not under the user's message.
- **Don't** add icons, emoji or color to capability badges or chat replies for decoration.
- **Don't** let a primary action sit below the fold; the body scrolls, the frame doesn't.
