# Your story in Lorekeeper

Lorekeeper helps you keep track of what happened, when it happened, and who was there. Your writing stays in files you can open without Lorekeeper. You can use the browser editor without an AI assistant.

## Start a world

Follow the [installation and quickstart](../README.md) once. Choose an empty folder for each story. The novel template gives you a small example world to explore. Series adds books with a series order; campaign adds a faction, a quest, sessions and session notes. These are examples, not facts about your story.

For daily work, open a terminal in your story folder and enter `lore serve`. Open the local address it prints in your browser. Leave the terminal running while you work; press Ctrl+C there when you are finished. If your terminal opens elsewhere, use `lore serve --root "C:/Stories/My Novel"`, with your own folder path.

The editor saves directly to your story files. Keep backups of the folder as you would for a manuscript.

## Create, connect and revise

Choose a **New item type**, enter a **New item name**, and press **Create**. Select the item in a view or the **Selected item** list. Its fields appear in the inspector on the right. Add dates, then press **Save**. Characters use `born` and `died`; other items normally use `date` and `end`.

To connect an event to a character, select the event, choose **Participants** as the link role, choose the character, and press **Add link**. Use **Location** for its place. **Backlinks** show items that point to the selected item. A location holds one link; remove an existing location link before adding another.

Fields that contain several values appear as lists, for example `["travel", "opening"]`. Keep the brackets and the double quotes when editing a list. The link controls save you from typing these lists yourself. The inspector edits fields and links; write longer prose in the Markdown file with your usual editor or Obsidian. Adding new kinds of fields or changing project settings also requires editing files or using the command line.

Changing a canonical name does not rewrite existing links or rename its file. If you rename an item, update links that use the old name, or keep the old name in its `aliases` list.

If another editor changes the same item, Lorekeeper can merge changes to different fields. If the same field has changed, it refuses your save and shows the current values. Your input stays visible. Copy any draft text you want to keep, reload to read the latest item, and reconcile the changes before saving again. Saved edits from other programs normally appear within a few seconds.

## The five views

**Timeline** places dated items on a time axis. Use its zoom and pan controls, then select a mark to inspect it. An exact Gregorian date can be dragged to a different position while keeping its precision. Dragging changes the start only; an explicit end date stays where it was. Approximate dates, ranges and custom-calendar dates must be changed in the inspector. Undated items remain available in the item selector and Spreadsheet.

**Subway** gives people separate lanes, with stops at their participating events. Shared events connect the lanes. It initially shows the twelve people with the most events. Use **Filter people** to find others. Participation comes from an event's `participants` links.

**Relationships** is a table of people against dated, non-person items. Where a person participates, the cell shows their age. It is useful for spotting a child who has become an adult too soon. This view is an age grid, not a general family-tree diagram. Other relationships are available in the inspector's links and backlinks.

**Spreadsheet** lists items with name, type, date or birth, end or death, and location. Press Enter or leave a cell to save it. **Inspect** opens the other fields. A failed save leaves the cell available for correction.

**Narrative** lists `chapter` and `card` items. It sorts by the numeric `chapter`, `order`, or `number` field, in that priority; otherwise it uses numbers in names and then name order. It flags a move backwards in time, which may be an intentional flashback. It does not read `narrative.md` or display book and session items. Campaign sessions can be edited in Spreadsheet or the inspector; read their outline in `narrative.md` and their index in `sessions.md`.

The browser has no check-results panel or import/export buttons. Those tasks use the short commands below; someone helping you set up the project can run them too.

## Files you can keep

Each item is one Markdown file, usually inside a folder such as `Characters`, `Locations` or `Events`. At the top is a small block of fields between `---` lines, called frontmatter. Below it is ordinary writing:

```markdown
---
id: EVENT-THE-LETTER
type: event
canonical_name: The Letter
date: 2025-04-01 09:00
location: "[[Lantern Harbour]]"
participants: ["[[Mira Vale]]"]
tags: [opening, mystery]
---

# The Letter

Mira recognises her sister's handwriting.
```

Keep frontmatter flat: one field per line, with a single value or an inline list. Field keys use lowercase letters and underscores. Quoted `"[[Name]]"` links connect items by name; bracketed links in the prose are useful for reading but are not continuity relationships. Use distinct canonical names and IDs. Notes without a frontmatter `type` are not loaded as items.

`lore.json` contains project settings. Its `types` describe kinds of items; `roles` describe connections; `properties` describe fields. `calendars` defines date systems, `rules` holds story-specific checks, and `checks` adjusts built-in checks. Default types, roles and properties still apply when those sections are empty. A custom entry with the same key replaces that default entry, so include the settings you need. You do not need to change this file for ordinary editing.

`narrative.md` is a separate outline of wikilinks. When the story-order check is enabled, it reads these links in file order. Aeon export also uses that outline. The browser's Narrative view instead uses the chapter fields described above; maintain the outline separately when you change reading order.

## Dates and uncertainty

Use the detail you know: `2025`, `2025-04`, `2025-04-02`, or `2025-04-02 09:30`. `April 2, 2025` works too. A day without a time means any time during that day, not a promise that something happened at midnight.

Write `~2025` or `circa 2025` for an approximate year. Circa expands a year by one year on either side, a month by one month, a day by one day, and a minute-precision time by fifteen minutes. `2040s` covers the whole decade. `44 BC` and `2025 AD` work, as do BCE and CE suffixes.

Write `2025-04-01..2025-04-10` when an event's date is somewhere in that range. Both endpoints are included. For an event that actually lasts that long, put its beginning in `date` and its ending in `end`. A `duration` such as `2d` or `1h 30m` can supply the end when there is no explicit end. Durations also accept years (`y`), months (`mo`), weeks (`w`) and minutes (`m`).

Keep sources with the date: `2025-04-02 (letter)` or `2025-04-02, outline note`. To mark a working assumption, use `2025-04-02 (provisional)` or the separate field `status: provisional`. Relevant continuity findings are then warnings, even if the assumed dates would otherwise prove a conflict. A provisional date still needs valid date syntax.

`date_min` and `date_max` can narrow the possibilities or supply bounds when no start date is stated. Contradictory bounds are reported. An unparseable date stays in the file and produces a warning; Lorekeeper does not quietly replace it.

Gregorian dates work without configuration. Custom calendars need definitions in `lore.json`; arbitrary invented month names are not understood automatically. `lore convert "2025-04-02"` displays a date in the project's configured calendars. The `age` command returns possible year bounds alongside an age description. Relationships shows the description, so check the underlying date precision before treating it as exact. For an immortal or other ageless character, add `max_age: none` to that person's frontmatter; birth and death consistency checks still apply.

## Read a continuity report

Run `lore check` from your story folder. Each finding includes a code, an explanation and a file with a line number. **FAIL** means the data establishes a problem. **WARN** means a possible problem, unreadable or incomplete information, or a rule deliberately set to warn. A clean report says `0 FAIL, 0 WARN`. Checks never move dates or repair files for you.

| Code | What to look at |
| --- | --- |
| `BAD_ENCODING` | A file is not UTF-8. Save it as UTF-8 in your text editor. |
| `BAD_FRONTMATTER` | The opening fields cannot be read. Check delimiters and syntax. |
| `UNSUPPORTED_FRONTMATTER` | A line was preserved but not understood; use flat fields and inline lists. |
| `DUPLICATE_ID` | Two items share an ID. Give each item its own ID. |
| `DUPLICATE_NAME` | Two items share a canonical name. Make their names distinct. |
| `UNKNOWN_TYPE` | A type is missing from the schema. Correct its spelling or define it in `lore.json`. |
| `BROKEN_LINK` | A field links to a name that cannot be found. |
| `ROLE_TYPE` | A link reaches the wrong kind of item, such as a location used as a participant. |
| `DATE_UNPARSED` | A date, bound or duration cannot be understood, or bounds contradict the stated date. |
| `DEPENDENCY_UNDATED` | A timing relationship lacks a date needed for comparison. |
| `DEPENDENCY` | A timing relationship is violated or uncertain, or its lag cannot be read. |
| `DEAD_PARTICIPANT` | A person is involved after their death. |
| `UNBORN_PARTICIPANT` | A person's involvement ends before their birth. |
| `AGE_LIMIT` | A participant exceeds the allowed age: 130 years by default, adjustable per project or person. |
| `PARENT_AGE` | A parent is younger than the minimum at the child's birth: 12 years by default. |
| `TWO_PLACES` | A person has overlapping appearances in different places. A place nested inside another via `located_in` is compatible with it. Broad dates alone do not always establish a collision. |
| `ORDER_REGRESSION` | Dates move backwards through a configured numeric order. Series uses this for books. |
| `MAX_DURATION` | An item may exceed a configured maximum duration. |
| `GAP` | The time between linked items does not meet a configured exact, minimum or maximum gap. |
| `STORY_ORDER` | The `narrative.md` outline definitely moves backwards in time. This is a warning, since flashbacks can be intentional. |

Project rules may supply their own codes, such as `RAIL_REGRESSION`; that name is not a separate built-in check. The built-in controls include `checks.max_age`, `checks.min_parent_age`, `checks.two_places` (`"off"` disables it) and `checks.story_order` (a boolean). Templates enable story-order checking. Custom rules can select items for monotonic order, maximum duration or linked gaps, and can cap severity at WARN.

Timing links have specific meanings: `after` compares this item's start with the other item's end; `same_start` compares starts; `same_end` compares ends; `sf` requires this item's end to be at or after the other item's start. A quoted link can include a lag, such as `"[[The Letter]] +2h"`. Because dates can be uncertain, even matching day-only dates may produce a warning for an exact equality.

These checks work on recorded fields and links. They cannot find an unrecorded contradiction buried only in prose, and a clean report is not a complete proof of continuity. For command-line users, checks return exit code 1 when there are FAILs, 0 for clean reports or warnings only; command errors return 2.

## Import and export

Initialize a project first. From its folder, use these examples with your own filenames:

```text
lore import story.aeon
lore import notes.csv --into Imported
lore export aeon shared.aeon
lore export csv shared.csv
lore export md reading-copy.md
```

Import creates new items and may add schema entries. Existing names are skipped with warnings; it does not update those items. `--into` puts new files in a folder within the project. Export replaces the destination file, so choose an output filename you are happy to replace.

CSV needs `label` and `type` columns. Other standard columns are `startDate`, `endDate`, `summary`, `tags` and `displayId`. `summary` becomes the item's prose; dates become birth/death fields for people and date/end fields for other items. Extra columns are read only if their keys are already declared roles or properties in the destination schema. Export includes declared roles and properties. IDs are generated on import; `displayId` is not restored as the item ID.

Aeon import reads container versions 1 and 2 with file versions 14 and 27. It handles items, relationships, dependencies and narrative links, but does not import attachments. Date conversion assumes Gregorian-style dates; custom Aeon calendars should not be treated as a faithful transfer. Seconds are reduced to minutes. Export writes a version-1 container with file-version-14 data and Gregorian dates. It omits attachments and dependency lags, and cannot represent all uncertainty in Aeon's date slots. Original date text is retained where its field is a declared property. Opening exported files in the Aeon desktop app has not been verified.

Markdown export produces a timeline table followed by item fields and prose. It is a reading copy, not an editable backup format with a matching import command. Your original folder remains the complete working copy.

## Work alongside Obsidian

Open the story folder as an Obsidian vault. The Markdown files, flat properties and quoted wikilinks are designed to be usable there. Keep relationship links in frontmatter when you want Lorekeeper to check them. Ordinary prose links can point to any note, including the narrative outline.

Lorekeeper skips `.obsidian`, hidden folders and `_TEMPLATES`. It normally scans Markdown throughout the story folder; `paths` and `exclude` in `lore.json` can narrow that scope. Keep unrelated manuscripts outside the folder or outside the configured scan paths. Save changes in Obsidian and the browser will pick them up. Avoid editing the same field in both places at once; browser conflict messages protect pending edits.

## When a saga pipeline owns canon

With `lore serve --saga`, or a project whose `mode` is `"saga"`, the editor shows **Propose change**. Enter the proposed values and a change note. This queues a request, normally in `.lore/requests`, for the host pipeline to review and apply. It does not change the canon item. Creating items, direct link controls and spreadsheet edits are disabled in this mode.

Lorekeeper does not provide a standalone approval or apply-request operation. The host decides how requests become canon. The saga restriction is enforced by the editor's HTTP interface; people or agents using CLI/MCP must also respect that workflow.
