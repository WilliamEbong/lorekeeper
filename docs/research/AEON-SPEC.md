# Aeon Timeline 3 file format and behaviour: clean-room notes for Lorekeeper interop

**Status:** research notes, written in our own words. Sources:
- static analysis of Aeon Timeline 3.5.123 (exe SHA-256 `d985701d…`) with REA
- the files bundled inside the exe, inspected in a scratch folder outside this repository
- arithmetic checks against the 19 bundled template files

No Aeon code or template content is copied here. Facts are stated only as precisely as interop needs. "Verified" means checked against real files; "observed" means read from the app's code but not tested.

---

## 1. Container (`.aeon`)

All integers are little-endian. A file is a tree of **archives**. Each archive is laid out as:

```
[payload bytes][index][40-byte header]
```

and is read **from its end**: the header sits in the last 40 bytes and says how large the index in front of it is.

### 1.1 Header (40 bytes)
| Offset | Type | Meaning |
|---|---|---|
| 0 | u32 | archive format version: 1 or 2 |
| 4 | u32 | header size, always `0x28` |
| 8 | u64 | index size in bytes |
| 16 | u32 | number of entries |
| 20 | 20 bytes | type marker: `33 33 33 33`, then eight `11` bytes, then eight `22` bytes (v1) or the ASCII bytes `HDJDJZWQ` (v2) |

The marker is constant per version. It is not a hash, MAC or signature. **Verified:** every bundled template carries one of the two markers, and no file has a checksum anywhere.

### 1.2 Root archive
The file itself is the root archive. It has exactly two entries, `attachments` and `timeline`. Each is a child archive stored inside the root's payload area. Root index entry:

```
u64 offset   u64 size   u64 0   u64 0   u32 name_len   name (UTF-8)
```

`offset` is from the start of the file; `size` covers the whole child archive, including its own index and header.

### 1.3 Leaf archives (`attachments`, `timeline`)
Index entry:

```
u64 offset   u64 size   28 extra bytes   u32 id_len   u32 name_len   id   name
```

- `offset` is relative to the start of the child archive.
- **Extra bytes in v1:** all zero.
- **Extra bytes in v2:** a u64 at extra+12 holds the stored size again. (Everywhere it was checked, it equals `size`. It is probably an "uncompressed size" field that is unused because nothing is compressed.) The other extra bytes are zero.
- **`timeline` archive:** exactly one entry, id `timeline3.json`, empty name. Its payload is UTF-8 JSON followed by one `\n`.
- **`attachments` archive:** one entry per attached file. The id is a GUID or short id, the name is the original filename, and the payload is the raw file bytes. An empty attachments archive is just a 40-byte header with an empty index.

### 1.4 Writing
A writer that produces format **v1** with an empty attachments archive needs only the layout above. The bundled "Story Planning" template is laid out exactly that way:

```
offset 0x00   attachments header (40 bytes, 0 entries)
offset 0x28   timeline3.json bytes
              timeline index (one entry) + timeline header
              root index (two entries) + root header
```

Aeon itself ships both v1 and v2 templates, so it reads both. **Verified** by parsing all 19 bundled files.

---

## 2. Top-level JSON
```
{ fileVersion, core, collection, sync, appState, printOptions, activeTutorialPath }
core = { coreFileVersion, definitions, data, templateDetails, projectId }
```

- **Bundled templates** are `fileVersion` **14**. The app itself writes the current version, **27** (embedded app metadata: `appVersion 3.5.123, fileVersion 27`).
- **`collection` is derived.** It holds indexes such as relationships by item, items by type, children by id, and topological order. The loader **rebuilds it from `core` after migration**, so a writer can omit it.
- **`appState`, `sync`, `printOptions`** hold UI, Scrivener/Ulysses sync and print state. The loader fills defaults when they are missing.

### 2.1 Shapes the loader accepts (observed)
The loader checks the parsed JSON in this order:
1. An object with `definitions` but no `coreFileVersion` or `templateFileVersion` creates a new timeline from definitions only.
2. A template record (`isTemplate` + `templateFileVersion`).
3. **A bare core object** (`coreFileVersion` present). It is wrapped as `{fileVersion: coreFileVersion, core: <object>}`, and every other part gets defaults.
4. A full file (`core` present).

It then runs the **migration chain** for every step with `fileVersion < N`, rebuilds `collection`, and stamps the current version.

**Consequence for Lorekeeper's writer:** emit `{"fileVersion": 14, "core": {...}}` with `core` in the **v14 shape**, the same shape as the bundled templates. Aeon's own migrations then upgrade it exactly as they upgrade its templates. This avoids guessing the v27 shape.

### 2.2 v14 → v27 differences that matter to a reader
A reader must accept both versions:

| Data | v14 (templates) | v27 (app-saved) |
|---|---|---|
| per-type manual order | `data.itemOrderByType` | `data.customOrder` (one flat order) |
| item nesting | `data.superAndChildOrderById{id:{super, childOrder}}` | `data.superById{id: superId}` |
| view range | `data.timelineRange` | moved into `appState` (removed from data) |

Disabled types, properties and references are deleted by the v17 step. The other steps (18–27) touch only views and app state, or clean up dangling ids. Everything else the reader uses has the same name in both: `itemsById`, `itemDatesById`, `relationshipsById`, `dependenciesById`, `dateConstraintsById`, `narrative.sacOrderById`, `sequenceOrder`, `tags`, and the `definitions` blocks.

---

## 3. Definitions
- **`calendar`:** `eras[]`, `months[]`, `weekdays[]`, `leapCycles`, `hoursInDay`, `weekdayIndexAtZero`, `zeroDateTimestamp`, `calendarType`, `maxPrecision`, plus display options (`dateFormat`, `timeFormat`, `dateOrder`, …).
  - Each era is `{name, shortName, isBackwards, hasLeapYears, leapOffset, duration}`.
  - Each month is `{name, shortName, normalDuration, leapDuration}`.
- **`types`:** `{byId, sortOrder}`. Each type has `id`, `label`, `pluralLabel`, `identifierPrefix`, `references{roleId:true}`, `properties{propId:true}`, `superTypes`, `canHaveDate`, `canIncludeInNarrative`, `isNarrativeFolder`, `category` (PERSON / LOCATION / OTHER), `icon`, `defaultItemColor`, `enabled`.
- **`properties`:** `{byId, sortOrder}`. Each is `{id, label, format, allowed?, multiple?, …}`. `format` is one of text, multitext, list, percentage, number, checkbox or date.
- **`references`** (relationship roles): `{byId, sortOrder}`. Each is `{id, label, types{allowed}, bidirectional, inverseLabel, showInverse, color, lineStyle, enabled}`.
- **`colors`:** `{byId, sortOrder}`.
- **`narrativeSettings`:** `labels{id:{label, autoForFolder, autoForOther, sortOrder}}`, plus the numbering style.
- **Other keys:** `includeNarrative`, `autoAdjustLevel` (0 off … 3 resolve constraints), `autoAdjustBackwardsLimit`, `storeRelativePaths`, `defaultColumns`.

## 4. Data
- **`itemsById[id]`:** `{id, type, label, summary, color, tags{}, propertyValues{}, links{}, attachments{}, image, displayId, internalId, narrativeLabel?}`.
- **`itemDatesById[id]`:** `{startDate, endDate, duration, ongoing, isDateLocked, preferred*, latestStartDate, earliestEndDate, preferredPrecision}`.
  - Each date is `{era, year, month, day, hour, minute, second, timestamp, weekday, precision}`.
  - **Month and day are 1-based** (verified: 1,006 dates).
  - `duration` is `{years, months, weeks, days, hours, minutes, seconds}`.
- **`relationshipsById[id]`:** `{id, subject, reference, object}`, i.e. "subject *role* object".
- **`dependenciesById[id]`:** `{id, subject, object, dependencyType}`, with type FS, SS, FF or SF.
- **`dateConstraintsById[id]`:** `{constraintType: Relative|Date|DatePart, subject, subjectTarget: Start|End, object, objectTarget, comparison: Before|After|Equal, date, offset, partPrecision, partValue}`.
- **`narrative.sacOrderById`:** the narrative tree, `{id: {super, childOrder{childId: rank}}}`.
- **`sequenceOrder`:** chronological tie-break order.
- **Also:** `tags`, `calendarMarkers` (recurring anniversaries), `savedFiltersById`, `attachmentsById`, `mindmaps`, `lastTodayDate`.

---

## 5. Time
### 5.1 Timestamps (verified)
- **Definition.** `timestamp` is a number of **seconds**. 0 is year 1, month 1, day 1, 00:00:00 of the **last** (forward) era.
- **Gregorian AD.** `timestamp = (days_from_civil(y, m, d) − days_from_civil(1, 1, 1)) × 86400 + h×3600 + min×60 + s`, using the proleptic Gregorian calendar. Verified exactly on 901 of 901 AD dates.
- **BC (backwards era).** Year *n* BC maps to astronomical year 1 − *n*. Aeon's stored value is then **one day (86,400 s) later** than proleptic Gregorian. Verified on 105 of 105 BC dates, all of them 1 January.
  - ponytail: the rule is only verified for 1 January BC dates. If BC interop matters, re-check it on a mid-year BC date from a real file.
- **Precision enum:** −1 Auto, 0 Century, 1 Decade, 2 Year, 3 Month, 4 Week, 5 Day, 6 Hour, 7 Minute, 8 Second.
- **calendarType:** 0 date and time; 1 week count; 2 day count; 3 plain timestamp. In types 1–3, dates are **still stored as full calendar dates**. `zeroDateTimestamp` marks Day 0 (or Week 0), and the relative number is only a display.

### 5.2 Leap years (observed)
Walk `leapCycles` (e.g. `[4, 100, 400]`) from the last entry to the first. At the first cycle where `year % cycle == leapOffset`, the year is a leap year if that cycle's index is even, and not one if it is odd. If no cycle matches, it is not a leap year. In the bundled Gregorian calendars, AD uses `leapOffset` 0 and BC uses 1.

### 5.3 Ages (observed)
Given a person with start date P (and possibly an end) and an event starting at E:
- If the person has ended and their end ≤ E, report the time **since end**.
- Otherwise, if E < P, report the time **before start**.
- Otherwise the age is the span from P to E. It is broken down greedily into years, months, weeks, days, hours, minutes, seconds, and shown as at most two units (for example "32 years, 4 months").

Precision is ignored: a person known only to the year counts from 1 January. Lorekeeper keeps this rule but also reports the uncertainty range.

### 5.4 Constraints and auto-adjust (observed; Lorekeeper only *checks*)
- **Violations.** Aeon collects bounds from Equal, Before/After and dependency rules. It tracks violated constraints, violated dependencies and violated items.
- **Auto-adjust.** It clamps each item to its bounds, propagates through a worklist, and repeats up to 5 passes while violations remain.
- **Lorekeeper.** It reports the same violations as FAIL or WARN findings and never moves anything.

---

## 6. Narrative numbering (observed)
- **Labels.** Each narrative node has a label (Part, Chapter, Scene, …). An "automatic" label is the next eligible label after the parent's label, in `sortOrder`.
- **Outline style.** Numbers are hierarchical ("Chapter 1.2.3").
- **Continuous style.** Each label keeps one counter across the whole depth-first walk.

## 7. CSV column ids (observed)
`label, type, color, startDate, endDate, duration, durationToStartOfEndDate, ongoing, summary, tags, super, internalId, compactDisplay, latestStartDate, earliestEndDate, links, image, displayId, initials, shortLabel, sequence, narrativePosition, narrativeSection, blockedBy, blocks, dateConstraints, attachments, mindmaps, dateLocked`

Lorekeeper's CSV import/export uses these ids as column headers.

## 8. Migration notes
- **The chain.** It runs from fileVersion 12 up to 27, one guarded step per version, followed by a dangling-reference cleanup on every load. See §2.2 for the steps that change data shape.
- **Lorekeeper's reader** accepts v14 and v27 directly (§2.2), and refuses anything else with a clear message.
- **Lorekeeper's writer** emits v14 and relies on Aeon's own migrations (§2.1).

## 9. Open items
- **Open-in-Aeon test.** No Lorekeeper-written file has been opened in Aeon yet. Feature 006 does this through computer use, if the user grants access to the app. Access was declined on 2026-10-18.
- **BC timestamp rule.** Only verified on 1 January dates (§5.1).
