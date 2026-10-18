# Feature 008: Editor UX overhaul

## Overview
Feature 005 made the browser editor work. This feature makes it pleasant and easy to use for its main audience: novelists who never open a terminal beyond `lore serve`. The editor keeps its paper-and-ink identity, its five views and every existing behaviour (saga mode, conflict handling, live reload, keyboard access). What changes is how clearly it shows the world, how plainly it speaks, and how little the writer has to remember.

Constraints are unchanged: the server uses only the standard library, the page is vanilla JavaScript and SVG with no build step and nothing fetched from the internet, and the strict Content-Security-Policy stays.

## User scenarios
- **A novelist opens their world for the first time.** They see the world's name, how many items it holds, and the timeline. They find "Heathcliff" by typing part of the name, and the inspector shows his fields with plain labels (Name, Born, Died), not `canonical_name`.
- **They fix a date.** They type `1764-07` in Born. Under the field the editor reads it back ("July 1764"). If they type something Lorekeeper cannot read, it says so before they save. A status in the top bar says "Unsaved changes", then "Saved".
- **They want to know if the story holds together.** The Continuity tab lists every FAIL and WARN in plain words, grouped by severity, each naming the item; clicking one opens that item.
- **A game master with 500 items** scrolls a timeline whose axis shows round dates (1760, 1770, …) that stay visible while scrolling, with items packed into as few rows as possible and coloured by kind.
- **A keyboard user** presses `/` to find an item, `Ctrl+S` to save, `Esc` to leave a field, and `+`/`-`/`0` to zoom the timeline.

## Functional requirements
- **FR-1 App shell.** A compact top bar shows the Lorekeeper wordmark, the world's name, the mode, a find box, and one live status message (loading, saved, unsaved, error). Tabs sit under it. Errors appear in one dismissible alert that names the problem and the way out; a CONFLICT also offers "Load their version". The page has a favicon (served from the package, so the CSP still holds).
- **FR-2 Find.** A find box (native `<input list>`) matches items by name and type; choosing one selects it in the inspector and on the current view. `/` focuses it from anywhere outside a text field.
- **FR-3 Create.** "New item" opens a small inline form (type select, name, Create). After creating, the new item is selected and its first date field is focused.
- **FR-4 Inspector.**
  - It stays in view while the page scrolls (sticky, scrolling on its own when tall).
  - It shows the item's name as a heading, its type and its file path.
  - Field labels come from the schema's property labels, else the key in plain words (`canonical_name` → Name, `date_min` → Date min).
  - `type` is a select of the project's types; `id` is shown read-only.
  - List fields are edited one value per line in a textarea; they are saved as lists.
  - Each date field reads its value back in words, using the `convert` op after typing pauses, or says it cannot be read.
  - Save is enabled only when something changed; "Discard changes" reverts; `Ctrl+S` saves.
  - Links are grouped by role, each target a button that selects it, with a labelled remove button. Backlinks are grouped by role with counts; long groups are collapsible.
  - Add link: the target box lists only items whose type the chosen role accepts (the role's `to` list), and is searchable.
- **FR-5 Timeline.**
  - Axis ticks fall on round dates whose step follows the zoom (minutes, hours, days, months, years, decades, centuries, millennia), labelled at that precision. The axis stays visible while the chart scrolls vertically.
  - Items are grouped by type under a labelled band with a count, and packed so that items whose bar and label do not overlap share a row.
  - Each type category (person, place, event, group, thing, narrative) has its own colour, readable in both themes.
  - Uncertain dates (circa, provisional, ranges, `date_min`/`date_max`, and month or year precision without an explicit end) are drawn visibly softer than exact ones, and the legend says so.
  - Type filter checkboxes hide or show types. A note counts undated items and points to the Spreadsheet.
  - Wheel scrolls the page; Shift+wheel or a horizontal wheel pans; Ctrl+wheel zooms at the pointer; `+`, `-`, `0` zoom in, out and fit.
  - Every mark has a hit area covering its label, so it is easy to click.
- **FR-6 Subway.** Each person's rail has its own colour and runs from birth to death where known. The selected event's stops are highlighted.
- **FR-7 Relationships.** The person column and the event header stay in view while scrolling. A person without a birth date shows "No birth date" without any server request. Ages use tabular figures; ages under 18 are tinted so a child is easy to spot.
- **FR-8 Spreadsheet.** A filter box and a type filter narrow the rows; column headers sort (dates sort chronologically). Cells look like a grid until hovered or focused. `type` is a select. A saved cell briefly shows that it saved. The row count is shown.
- **FR-9 Narrative.** Lists items of any type whose category is `narrative` (chapter, card, book, session…), as before, and shows a backwards move in time as a marked badge.
- **FR-10 Continuity.** A sixth tab runs `check` when opened and again after each reload while it is open. It shows totals, then findings grouped FAIL before WARN, each with a plain-language title for its code, the detail, and a button that selects the item. A clean world says so. The tab label shows the FAIL count once known.
- **FR-11 Empty and first-run states.** An empty world shows a welcome panel with the create form. Each view's empty state says what to do next.
- **FR-12 Accessibility and responsiveness.** All existing keyboard behaviour stays. Contrast meets WCAG AA in light and dark themes. `prefers-reduced-motion` turns off transitions. Below 900px the inspector stacks under the view and selecting an item scrolls it into view; nothing overflows horizontally except the charts' own scroll areas.

## Success criteria (Playwright MCP, on a scratch copy of a 116-item imported world and on the fixture world)
- **SC-1** Find "Heathcliff" with `/`, edit Born, see the read-back, save with `Ctrl+S`, and see "Saved".
- **SC-2** The timeline axis shows round dates; the axis stays visible after scrolling the chart; the item rows are fewer than the items.
- **SC-3** The Continuity tab lists the world's findings with plain titles and opens an item from a finding.
- **SC-4** Relationships makes no request for people without a birth date (no console errors).
- **SC-5** Light, dark and 390px-wide screenshots show no overflow and readable contrast.
- **SC-6** Saga mode still only proposes changes; a CLI edit during an unsaved inspector edit still yields a merge or a visible conflict with the input kept.
- **SC-7** The full unit suite passes.
