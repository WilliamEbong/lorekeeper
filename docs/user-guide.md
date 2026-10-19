# Your story in Lorekeeper

Lorekeeper helps you keep track of what happened, when it happened, and who was there. Your writing stays in files you can open without Lorekeeper. You can use the browser editor without an AI assistant.

## Start a world

Follow the [installation and quickstart](../README.md) once. Choose an empty folder for each story. The novel template gives you a small example world to explore. Series adds books with a series order; campaign adds a faction, a quest, sessions and session notes. These are examples, not facts about your story.

For daily work, open a terminal in your story folder and enter `lore serve`. Open the local address it prints in your browser. Leave the terminal running while you work; press Ctrl+C there when you are finished. If your terminal opens elsewhere, use `lore serve --root "C:/Stories/My Novel"`, with your own folder path.

The editor saves directly to your story files. Keep backups of the folder as you would for a manuscript.

## Create, connect and revise

Press **New item**, choose a type, enter a name and press **Create**. The new item opens in the inspector on the right, with its first date field ready for typing. To open an existing item, select it in any view, or press `/` and start typing its name in the **Find an item** box.

The inspector shows the item's fields with plain labels. Characters use **Born** and **Died**; other items normally use **Date** and **End**. Under each date field the editor says how it reads the date, for example "Reads as July 1764", or warns you when it cannot read it. Fields that hold several values, such as **Tags** and **Aliases**, take one value per line. **Add a field** adds one of the project's fields, or a new one of your own. Press **Save** or Ctrl+S to save; **Discard changes** puts the fields back. A field you have changed but not saved is marked "changed", and the status at the top right says "Unsaved changes" until you save. After each save, a message offers **Undo**.

**Connections** lists the item's links, grouped by kind, such as Participants and Location. Select a name to open that item, or press the cross beside it to remove the link. To add a link, choose the kind of connection under **Add a connection**, start typing a name, choose it from the list, and press **Add** (or Enter). The list offers only items of the right kind: Participants accepts characters and organizations, and Location accepts places. A location holds one link; remove the existing one before adding another. **Linked from** shows the items that point to this one.

The inspector edits fields and links; write longer prose in the Markdown file with your usual editor or Obsidian. Changing project settings, such as new types or calendars, still means editing `lore.json` or using the command line.

Changing a name does not rewrite existing links or rename its file. If you rename an item, update links that use the old name, or keep the old name in its **Aliases**.

If another program changes the same item while you are editing it, Lorekeeper merges changes to different fields. If the same field has changed, it refuses your save and tells you the new value. Your text stays in the inspector. Choose **Load their version** to drop your edit, or **Keep my text** to keep it on top of the latest version and then save again on purpose. Saved edits from other programs normally appear within a few seconds, and the editor keeps your place while it updates.

## The eight views

**Timeline** places dated items on a time axis, grouped by type, each type in its own colour. The dates along the top stay in view while you scroll. Solid marks are exact dates; pale, dashed marks are approximate or uncertain ones, such as circa dates, ranges, or a month or year with no end. A person runs from birth to death; someone with no recorded death is alive, so a thin life line carries on to the latest date in the story. Use the buttons to zoom and move along the axis, or Ctrl and the mouse wheel to zoom, and Shift and the wheel to move. The `+`, `−` and `0` keys zoom in, zoom out and fit everything. Tick or untick a type to hide or show it. Drag an exactly dated item sideways to move it, start and end together. On a bar that has a written end, drag either end of the bar instead to change just its start or just its end; the pointer becomes a resize arrow there. The new date shows as you drag, and a message offers **Undo**. Very short bars have no ends to grab until you zoom in. Approximate dates, ranges and custom-calendar dates are changed in the inspector instead. Undated items are listed in Spreadsheet.

**Subway** gives each person a coloured line, solid between their birth and death, with stops at the events they take part in. Shared events connect the lines. It first shows the twelve people with the most events; use **Filter people by name** to find others. Participation comes from an event's Participants links.

**Relationships** shows who is related to whom: a card for each person or group, listing their parents, children, spouses, siblings, groups and members, and any other connection between people or groups. A connection someone else makes to them appears under its reverse name, such as Children for Parent; where the project gives no reverse name, it reads "Sibling of". Select a name to open it. Add a relationship in the inspector under **Add a connection**.

**Ages** is a table of people against the dated events they take part in. Each cell shows the person's age at that event. Yellow cells show someone under 18; red cells show an appearance before birth or after death. The person and event names stay in view while you scroll. A person without a birth date shows "No birth date". For who is related to whom, use Relationships.

**Spreadsheet** lists every item with its name, type, date or birth, end or death, and location. Filter it by name or type, and sort it by pressing a column heading. Press Enter or leave a cell to save it; Esc puts back what was there. Type and Location are chosen from lists. **Open** shows the item in the inspector. A cell that could not be saved is marked in red and keeps your text.

**Narrative** lists the parts of the story in reading order: chapters, and any other type marked as narrative, such as the series template's books and the campaign template's sessions. It sorts by the numeric `chapter`, `order` or `number` field, in that priority; otherwise it uses numbers in names, then name order. It flags a part that is earlier in time than the part before it, which may be an intentional flashback. It does not read `narrative.md`.

**Wiki** shows your story as a reader knows it. Pick **Complete** for everything, or **Chapter N** for only what a reader knows after chapter N; the editor remembers your choice. The list on the left groups what the reader has met by type, under the names the reader knows. Select an entry to open its card, which has its own chapter control, so you can step one card through the story without changing the rest. Each fact carries a quiet chapter marker; in Complete, a fact that stopped being true is marked "no longer current". **Add a fact** adds one to a section, and **No longer true after…** ends one; both offer **Undo**. Only the Wiki tab follows the chapter picker: the other views always show everything, because their dates would give away deaths and other surprises. See [The story wiki](#the-story-wiki).

**Continuity** runs the same check as `lore check` and lists the problems in plain words: definite problems first, then possible ones. Each problem names its file and line, and **Open** shows the item concerned. The tab shows the number of definite problems (or possible ones, when there are none) and refreshes after every change. Lorekeeper never changes your files to fix a problem.

Import and export still use the short commands below; someone helping you set up the project can run them too.

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

## The story wiki

The story wiki shows what a reader knows after any chapter. It needs only one habit: end a fact with a **chapter stamp** saying from which chapter the reader knows it.

```markdown
## Beliefs
- Believes the far side is unarmed. [ch 2-5]

## Important events
- Lost his left hand at the Gate. [ch 4]
```

- A fact is one list item or one paragraph under a `##` heading. `[ch 4]` means "known from chapter 4". `[ch 2-5]` means "true from chapter 2 until chapter 5", for beliefs, places, states and relationships that change. Capitals and spaces don't matter: `[CH 4]` and `[ch4]` work too.
- A fact without a stamp is known from the page's `first_appearance` (`3` or `CH003`). A page without one is always known, and pages with a later `first_appearance` stay out of the wiki until that chapter.
- Chapter numbers follow reading order, so flashbacks are no problem. Number them through the whole story; a prologue can be chapter 0, and a game master can number sessions.
- **Names the reader knows.** A `## Names` section lists them with stamps: `- the hooded rider [ch 2-5]` and `- Kresh [ch 6]`. Until chapter 6 the wiki lists "the hooded rider"; from chapter 6, "Kresh". It is one card throughout.
- **Secret identities.** `revealed_as: "[[Kresh]] [ch 9]"` on Lord Vane's page keeps Lord Vane a card of his own until chapter 9. From then on his facts appear on Kresh's card, marked "as Lord Vane". In Complete there is only ever the one card.
- **Kinds of things.** Give a thing a `kind` link to a page for its kind, such as `kind: "[[Standard alien battle tank]]"`. The kind is an ordinary page with its own card.
- **Starter sections.** New characters start with Names, Current state, Where, Beliefs, Knows, Wants, Relationships and Important events; groups, places, items and technology have their own. Any heading you write works and keeps its place.
- **Worked out for you.** When a card's Where, Knows or Relationships section has nothing written for that chapter, Lorekeeper fills it from your links (the place of the latest event someone took part in, what events reveal to them, their relationships) and marks it "worked out".
- **Spoilers stay hidden.** At chapter N a card hides facts that start later or ended earlier, page fields (a death date is a spoiler), and links to pages the reader has not met, which read as plain text.

From the command line, `lore wiki --as-of 5` lists the index at chapter 5, `lore wiki "Kresh" --as-of 5` shows one card, and leaving out `--as-of` gives the complete wiki. `lore fact-add "Darius" Beliefs "Believes the far side is unarmed." --from 2 --to 5` adds a stamped fact; `lore fact-end "Darius" Beliefs "Believes the far" --after 5` ends one; `lore fact-remove` takes one back. AI agents use the same operations through MCP.

**Keeping the stamps somewhere else.** If your pages describe the present and you'd rather keep the reader's view apart, add `"story_wiki": "Story Wiki"` to `lore.json`. Each entry's stamped facts then live in a companion page in that folder, such as `Story Wiki/Characters/Kresh (story).md`, with `type`, `page: "[[Kresh]]"` and the stamped sections. The wiki at a chapter uses only the companion pages; the complete card shows your page first, then the companion's facts. Companions are never items of their own, so they don't appear in other views or confuse links. Add a fact creates a companion when an entry has none. Someone the reader has met but who has no page yet gets a companion on its own with `lore fact-add "The Stranger" Where "At the inn." --from 5 --type character`. The owner's sagas work this way: their Wiki stays exactly as the saga pipeline writes it.

`lore check` reports a marker it cannot read as `STAMP_UNREADABLE` and a range that ends before it starts as `STAMP_RANGE`.

## Dates and uncertainty

Use the detail you know: `2025`, `2025-04`, `2025-04-02`, or `2025-04-02 09:30`. `April 2, 2025` works too. A day without a time means any time during that day, not a promise that something happened at midnight.

Write `~2025` or `circa 2025` for an approximate year. Circa expands a year by one year on either side, a month by one month, a day by one day, and a minute-precision time by fifteen minutes. `2040s` covers the whole decade, and a year ending in 00s covers the whole century, so `1800s` means 1800 to 1899. `44 BC` and `2025 AD` work, as do BCE and CE suffixes. A BC date finer than a year, such as `March 15, 44 BC`, is shown as `0044-03-15 BC`, and the editor reads it out as "15 March 44 BC".

Write `2025-04-01..2025-04-10` when an event's date is somewhere in that range. Both endpoints are included. For an event that actually lasts that long, put its beginning in `date` and its ending in `end`. A `duration` such as `2d` or `1h 30m` can supply the end when there is no explicit end. Durations also accept years (`y`), months (`mo`), weeks (`w`) and minutes (`m`).

Keep sources with the date: `2025-04-02 (letter)` or `2025-04-02, outline note`. To mark a working assumption, use `2025-04-02 (provisional)` or the separate field `status: provisional`. Relevant continuity findings are then warnings, even if the assumed dates would otherwise prove a conflict. A provisional date still needs valid date syntax.

`date_min` and `date_max` can narrow the possibilities of a stated date. Without a stated date, they date an item only when both are given; a lone bound leaves it undated. Contradictory bounds are reported. An unparseable date stays in the file and produces a warning; Lorekeeper does not quietly replace it.

Gregorian dates work without configuration. Custom calendars need definitions in `lore.json`; arbitrary invented month names are not understood automatically. `lore convert "2025-04-02"` displays a date in the project's configured calendars. The `age` command returns possible year bounds alongside an age description. The Ages view shows the description, so check the underlying date precision before treating it as exact. For an immortal or other ageless character, add `max_age: none` to that person's frontmatter (or `"checks": {"max_age": "none"}` in `lore.json` for a whole world); birth and death consistency checks still apply.

**Second lives.** In a world where people come back, record the end of a person's first life in `died` and the start of the second in `reborn`. The timeline draws the first life as a bar and the second as a line running on to the latest date in the story, and appearances after the rebirth are not reported as after death (only those between the two dates are).

**Flashbacks.** A chapter or event told out of order on purpose is not a mistake: give it `flashback: yes`, or say so in its date's note, such as `SRD Y-2 D168 (flashback)` or "(presented out of chronological order)". Order checks skip it, and the items right after it that continue the flashback, while still catching a real step back in time.

**Running day counts.** A day-count calendar can set `"overflow": true`, so a day past the end of the year carries into the next one: in a 365-day year, `Y0 D367` is read as `Y1 D002`.

## Read a continuity report

The editor's Continuity tab shows the same report. To run it in a terminal, enter `lore check` in your story folder (or any folder inside it). Each finding includes a code, an explanation and a file with a line number. **FAIL** means the data establishes a problem. **WARN** means a possible problem, unreadable or incomplete information, or a rule deliberately set to warn. A clean report says `0 FAIL, 0 WARN`. Checks never move dates or repair files for you.

| Code | What to look at |
| --- | --- |
| `BAD_ENCODING` | A file is not UTF-8. Save it as UTF-8 in your text editor. |
| `BAD_FRONTMATTER` | The opening fields cannot be read. Check delimiters and syntax. |
| `UNSUPPORTED_FRONTMATTER` | A line was preserved but not understood; use flat fields and inline lists. |
| `DUPLICATE_ID` | Two items share an ID. Give each item its own ID. |
| `DUPLICATE_NAME` | Two items share a canonical name. Make their names distinct. |
| `AMBIGUOUS_NAME` | An alias or file name belongs to two items, so a link using it could mean either. Give each item its own aliases. |
| `UNKNOWN_TYPE` | A type is missing from the schema. Correct its spelling or define it in `lore.json`. |
| `BROKEN_LINK` | A field links to a name that cannot be found. |
| `ROLE_TYPE` | A link reaches the wrong kind of item, such as a location used as a participant. |
| `DATE_UNPARSED` | A date, bound or duration cannot be understood, or bounds contradict the stated date. |
| `END_BEFORE_START` | A written end (`end` or `died`) comes before the start. FAIL when even the latest possible end is before the earliest possible start; WARN when the end may begin earlier, such as an end of `2020-05` for a start of `2020-05-10`. Ends worked out from a `duration` are not checked. |
| `DEPENDENCY_UNDATED` | A timing relationship lacks a date needed for comparison. |
| `DEPENDENCY` | A timing relationship is violated or uncertain, or its lag cannot be read. |
| `DEAD_PARTICIPANT` | A person is involved after their death (and before their rebirth, when `reborn` is recorded). |
| `UNBORN_PARTICIPANT` | A person's involvement ends before their birth. |
| `AGE_LIMIT` | A participant exceeds the allowed age: 130 years by default, adjustable per project or person. |
| `PROBABLY_DEAD` | A person has no recorded death but would be older than the age limit by the latest date in the story. Record `died`, or set `max_age` (`none` for the ageless). Always a warning. |
| `PARENT_AGE` | A parent is younger than the minimum at the child's birth: 12 years by default. |
| `TWO_PLACES` | A person has overlapping appearances in different places; the message names both places. A place nested inside another via `located_in` is compatible with it. Back-to-back scenes (one ends as the next begins) do not clash. Broad dates alone do not always establish a collision. |
| `ORDER_REGRESSION` | Dates move backwards through a configured numeric order. Series uses this for books. Items marked as flashbacks are skipped. |
| `MAX_DURATION` | An item may exceed a configured maximum duration. Lasting exactly the maximum is allowed. |
| `GAP` | The time between linked items does not meet a configured exact, minimum or maximum gap. |
| `STORY_ORDER` | The `narrative.md` outline definitely moves backwards in time. This is a warning, since flashbacks can be intentional. |
| `STAMP_UNREADABLE` | A chapter stamp cannot be read, such as `[ch x]`, or is not at the end of its fact. Write `[ch 7]` or `[ch 2-5]` at the end. |
| `STAMP_RANGE` | A chapter range ends before it starts, such as `[ch 5-2]`. |
| `STORY_PAGE_UNREADABLE` | A file in the story-wiki folder is not used: it needs UTF-8 text and frontmatter with `type:` (and `page: "[[Name]]"` when it describes a page). |

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

Open the story folder as an Obsidian vault. The Markdown files, flat properties and quoted wikilinks are designed to be usable there. Lists that Obsidian's Properties panel writes one item per line are read too; when Lorekeeper changes such a field, it rewrites it as a one-line list. A field Lorekeeper cannot read is left exactly as it is, reported as a warning, and refused for editing until you fix it by hand. Keep relationship links in frontmatter when you want Lorekeeper to check them. Ordinary prose links can point to any note, including the narrative outline.

Lorekeeper skips `.obsidian`, hidden folders and `_TEMPLATES`. It normally scans Markdown throughout the story folder; `paths` and `exclude` in `lore.json` can narrow that scope. Keep unrelated manuscripts outside the folder or outside the configured scan paths. Save changes in Obsidian and the browser will pick them up. Avoid editing the same field in both places at once; browser conflict messages protect pending edits.

## When a saga pipeline owns canon

With `lore serve --saga`, or a project whose `mode` is `"saga"`, the editor shows **Propose change**. Enter the proposed values and a change note. This queues a request, normally in `.lore/requests`, for the host pipeline to review and apply. It does not change the canon item. Creating items, direct link controls and spreadsheet edits are disabled in this mode. In the Wiki tab, **Propose a fact** and **Propose an end** queue the same kind of request.

Lorekeeper does not provide a standalone approval or apply-request operation. The host decides how requests become canon. The saga restriction is enforced by the editor's HTTP interface; people or agents using CLI/MCP must also respect that workflow.
