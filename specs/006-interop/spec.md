# Feature 006: Interop (Aeon Timeline `.aeon`, CSV, Markdown)

## Overview
Writers come to Lorekeeper with existing Aeon Timeline files and spreadsheets, and they leave with things to share. This feature covers:
- reading Aeon's `.aeon` files (its bundled fileVersion 14 templates and the fileVersion 27 files the app saves)
- writing `.aeon` files that Aeon can open
- CSV in and out, using Aeon's column ids
- a Markdown export

`docs/research/AEON-SPEC.md` is the clean-room reference. No Aeon content enters the repository.

## Functional requirements
- **FR-1 `.aeon` reader** (`lorekeeper/aeon.py`, `read(path) -> dict`).
  - **Container.** Parse it as in AEON-SPEC §1, versions 1 and 2. Anything that is not a valid container gives `LoreError INVALID` with a clear reason.
  - **JSON version.** Accept fileVersion 14 or 27 (AEON-SPEC §2.2). Others are refused clearly.
  - **Output dict.** `{calendar, types, roles, properties, items:[{id, type, name, summary, tags, fields, start, end}], relationships:[{subject, role, object}], dependencies:[{subject, object, kind}], narrative:[ids in order], attachments:[names]}`.
  - **Dates.** Read from the date fields (era/year/month/day/hour/minute + precision), never from timestamps.
- **FR-2 Import op** `import FILE [--into DIR]`. Converts an `.aeon` or `.csv` into the current project as Lorekeeper items.
  - **Types and roles.** Aeon types map to Lorekeeper types by category: PERSON→character, LOCATION→location, and event-like types (`canHaveDate`)→event. Other types keep a slugged form of their own label, and missing types/roles are added to `lore.json`.
  - **Relationships.** Each becomes a role link on the subject.
  - **Dependencies.** On the successor (Aeon's object), pointing at the predecessor (the subject): FS→`after`, SS→`starts_after_start`, FF→`ends_after_end`, SF→`sf`. Amended 2026-10-18: the first version put them on the subject and mapped SS/FF to the equality roles.
  - **Dates.** Written at their Aeon precision.
  - **Summary and body.** The summary becomes the body.
  - **Narrative.** Its order is written to `narrative.md`.
  - **Name collisions.** An existing item name is skipped with a WARN line, never overwritten.
  - **Result.** It returns counts.
- **FR-3 `.aeon` writer.** `write(project, path)` emits a v1 container with an empty attachments archive and a timeline JSON of `{"fileVersion": 14, "core": <v14-shaped core>}`, as AEON-SPEC §2.1 recommends.
  - **Definitions.** A Gregorian calendar (BC/AD eras), plus types, references and properties.
  - **Data.** `itemsById`, `itemDatesById` (AD timestamps by the verified formula), `relationshipsById`, `dependenciesById`, a narrative tree from `narrative.md` when it exists, and the remaining required empty collections. The required set is taken from the shape of the bundled templates, without copying their content.
  - **Ids.** Generated with a stdlib random token (alphanumeric, 21 characters, like Aeon's).
- **FR-4 Export op** `export FORMAT --out PATH`, where FORMAT is `aeon`, `csv` or `md`.
  - **CSV.** UTF-8 with a BOM (for Excel). The header uses Aeon column ids: `label, type, startDate, endDate, summary, tags, displayId`, then one column per role (participants etc.) and per property.
  - **Markdown.** One document: the timeline in chronological order (date, name, type, location, participants), followed by every item's fields.
- **FR-5 CSV import.** It reads the same columns, plus any columns that match lore.json properties. It creates items and skips existing names, as FR-2 does.

- **FR-6 Round-trip fidelity** (added 2026-11-23 by the overnight maintenance pass, as a safe default the owner may revise). Exporting a world to CSV or `.aeon` and importing the file into an empty world gives the same items, dates and fields.
  - **Kept.** Every date field (`born`, `died`, `date`, `end`, `date_min`, `date_max`) travels as its own property beside Aeon's start and end, so the original text, circa marks and narrowing survive.
  - **Bounds-only dates.** A date known only by `date_min` and `date_max` is exported as its earliest date in Aeon's start (and CSV `startDate`). On import, a start equal to `date_min` beside both bounds and no stated date is left out, so the range is not narrowed to its first year.
  - **Ends.** An event's end defaults to its start, so an imported end equal to the start is not written. A person's `died` is always written.
  - **Tags.** An item without tags gets no `tags: []` line.
  - **Aeon precision.** A year range that is exactly an aligned decade (`1990s`) or century (`1800s`) is written at Aeon's decade or century precision.
  - **Recorded losses, where the formats cannot carry the detail.**
    - In Aeon itself (not on re-import): circa dates show their stated date; a bounds-only date shows only its earliest date; Lorekeeper's text forms ("1990s", "~1951") appear only as property values; a born-only person has no end date.
    - In a CSV, a text value that looks like a JSON list or object (`["a", "b"]`) comes back as a list or object, because lists are written that way.
    - Week precision: Lorekeeper has no week dates, so none are written; an imported Aeon week becomes a seven-day range.

## Success criteria
- **SC-1 Templates read.** All 19 bundled template files, extracted to `C:\Users\Owner\lk-scratch\aeon_extract\3003` (the test skips when they are absent), read without error. Their item counts match the JSON, and every dated item gets a parseable Lorekeeper date.
- **SC-2 Round trip.** fixture world → `.aeon` → read gives the same items, dates (at their precision), relationships and dependencies. Our own exported files may live in `tests/fixtures/ours/`.
- **SC-3 CSV round trip.** fixture → CSV → import into an empty project gives the same names, types and dates.
- **SC-4 Aeon opens the file.** A Lorekeeper-written `.aeon` file opens in the Aeon Timeline desktop app (computer use, screenshot). If the user declines app access, this is reported as unverified.
