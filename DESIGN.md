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
  text-quaternary: "#1f23285c"
  hairline: "#0a44bb25"
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

Density follows Hermes's Scheduled jobs page: a 14px page title, 12.5px list rows, 11px meta, uppercase 10px group labels, flat rows with a tinted selection, and one blue action per view. Separation comes from whitespace and single hairlines, never from boxes.

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
- **On-Accent White** (`--color-primary-foreground`): text and icons on Signal Blue (the primary button label, the check in a finished step marker).

### Neutral
- **Ink** (`--ui-base`): the root of every text tone. Never used directly.
- **Page** (`--ui-bg-editor`): the page background the board sits on. Plugin code never paints it.
- **Primary Text** (`--ui-text-primary`): page title, idea title, quotes, list row titles, rule text.
- **Secondary Text** (`--ui-text-secondary`): the "why" paragraph, prompt body, undo message.
- **Tertiary Text** (`--ui-text-tertiary`): receipts, meta lines, group overlines, row values, text actions at rest.
- **Quaternary Text** (`--ui-text-quaternary`): keyboard hints and risk footnotes only.
- **Hairline** (`--ui-stroke-tertiary`): the header rule, the list/detail divider, rows in the rules dialog, empty day dots.
- **Soft Fill** (`--ui-bg-quaternary`): the undo bar and secondary buttons.
- **Quiet Fill** (`--ui-bg-quinary`): the prompt block.
- **Row Hover** (`--ui-row-hover-background`) and **Row Selected** (`--ui-row-active-background`): list row states, exactly as Hermes's own lists use them.
- **Alert Red** (`--ui-red`): run errors in the receipt and failed-state text. Hermes has no `--ui-text-danger`; don't reference it.

### Named Rules
**The Borrowed Ink Rule.** Every color in plugin code is `var(--ui-…)`. A hex, rgb or named color in `plugin.js` is a bug, because it breaks the user's theme.

**The One Blue Rule.** At most one filled blue control per view. Selection uses the row tint, not blue; links and text actions stay tertiary until hovered.

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
- **Meta** (400, 11px / 0.7rem, 1.5): receipt, meta line, row values, day counts, keyboard hints.
- **Overline** (500, 10px / 0.6rem, 0.05em, uppercase): group labels ("PUT ON AUTOPILOT · 2"), the "PROMPT" label, "STARTED". Always followed by `· count` when it heads a list.

### Named Rules
**The One Reading Moment Rule.** Only the idea title and quotes are larger than Hermes's 14px page title. If a new element wants to be big, it is the wrong element.

**The Eight Roles Rule.** Plugin code sets font sizes only from the roles above (0.6, 0.7, 0.75, 0.78, 0.8125, 0.875, 0.9375 and 1.25rem). No half-pixel one-offs.

## Layout

Every page-level surface uses one frame: page padding 24px top and 32px sides; a header row (title, then one meta line under it, actions right-aligned on the baseline); a single hairline; then the body filling the remaining height and scrolling inside itself, so primary actions are never clipped by the window.

The board body is master-detail: a 320px list column, a hairline, 32px of air, then the detail column. Detail prose caps at 68ch and the detail column at 720px; the extra width stays empty on the right rather than stretching text. Groups in the list are separated by 16px; rows within a group by 2px.

Rhythm is a 4px grid: 2 (inside a row), 4, 6 (icon to label, as in Hermes buttons), 8 (related items), 12 (within a block), 16 (between blocks), 24 (between sections), 32 (between regions). Setup and empty states use the same frame and the same left edge as the board, so moving between them never shifts the page.

Narrow windows (provisional, not built): below about 760px of page width the list stacks above the detail.

## Elevation & Depth

Flat. Idea Board defines no shadows. Depth comes from three things only: hairlines for structure, tonal fills (row tint, soft fill, quiet fill) for state, and the host's own popovers and dialogs, which bring their own elevation. The empty day dot is drawn as a 1px inset ring in the hairline color, not as a border or shadow.

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

### Evidence block and day ribbon (signature)
- **Quote:** Quote type, primary text, italic in curly quotes.
- **Ribbon:** fourteen 6px dots, 3px apart, oldest left; days the user said it are filled Signal Blue, the rest are hairline rings. It is never replaced by a number alone.
- **Line under the quote:** ribbon, then Meta text ("2 days in the last two weeks"), then the "Open chat" text action.

### Capability badges
Host `Badge`, muted variant, codicon leading at 4px. Deduplicated by name. They never take color.

### Prompt block
- **Style:** Quiet Fill, 4px radius, 10px padding, Body type in secondary text, clamped to 8 lines with "Show all".
- **Label:** a "PROMPT · GOES INTO A NEW CHAT" overline above it, matching the PROMPT label on Hermes's Scheduled jobs page.
- **Footer:** risk note in Meta quaternary, then "Show all" and "Copy prompt".

### Undo bar
Soft fill, 4px radius, 8px 12px padding, Body type; message left, "Undo" textStrong right. Appears at the top of the detail column for 10 seconds after a dismiss or snooze.

### Step marker (setup)
An 18px circle with a 1px hairline ring and the step number in Meta tertiary; when done, Signal Blue fill with a white check codicon. Step titles use Title type.

### Dialogs, menus and notices
Host `Dialog`, `DropdownMenu`, `Textarea` and `host.notify` exactly as shipped. Reason choices in the note dialog are host buttons (secondary, primary when chosen), never custom chips.

### Navigation
The sidebar row uses the host nav area with the `lightbulb` codicon and the label "Idea Board". Command palette entries: "Open Idea Board" and "Idea Board: generate ideas now".

### Empty, loading and error states
Host `EmptyState` (title plus one line) centered in the body, with at most one action button under it; host `Loader` while loading. Errors name what failed and the one thing to do next.

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
- **Don't** write a hex, rgb or named color, a font-family, or a box-shadow in `plugin.js`.
- **Don't** reference `--ui-text-danger`; it doesn't exist in Hermes. Use `--ui-red` for errors.
- **Don't** use font sizes outside the eight roles (no 11.5, 13.5 or 22px one-offs; 12.5px comes only from the Row role).
- **Don't** box sections, nest cards, or add colored side stripes; use a hairline or whitespace.
- **Don't** use the blue fill for selection or for more than one action in a view.
- **Don't** add icons, emoji or color to capability badges or chat replies for decoration.
- **Don't** let a primary action sit below the fold; the body scrolls, the frame doesn't.
