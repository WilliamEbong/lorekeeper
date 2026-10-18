# Feature 003: Checks (Aeon's checks plus the ones Aeon lacks)

## Overview
`lore check` finds continuity errors from the data alone: an event before its prerequisite, a dead character taking part, someone in two places at once, a parent younger than their child, a "duel" that lasts three days, a story rail whose dates run backwards.

Dates are intervals (feature 002), so every check knows how certain it is:
- **FAIL** means the error is definite whatever the true dates within their stated precision.
- **WARN** means the error is possible.

An item with `status: provisional` (or a date marked provisional) can only produce WARN.

## Definitions
- **Item interval.** From 002 `item_dates(item)`: the start (`When`) and the end (`When`). The **hull** of an item is `[start.lo, end.hi)`. The **core** is `[start.hi-1, end.lo]`, the time that is certainly covered; it is empty when that range is inverted.
- **Point comparison.** For a constraint `X ≥ Y + lag`, where X and Y are `When`s with possible minutes `[lo, hi-1]`:
  - definitely violated when `X.hi-1 < Y.lo + lag`
  - possibly violated when `X.lo < Y.hi-1 + lag`
- **Same place.** Two location items are the same place when they are equal or one is reached from the other through `located_in` links (transitively, in either direction).

## Functional requirements
- **FR-1 Dependencies** (Aeon FS/SS/FF/SF). These come from role values on the subject, with an optional lag (`"[[Y]] +2d"`):
  - `after` (finish→start): subject start ≥ Y end + lag
  - `same_start`: subject start = Y start + lag
  - `same_end`: subject end = Y end + lag
  - `sf` (start→finish): subject end ≥ Y start + lag

  Equality is definitely violated when the two possible ranges are disjoint, and possibly violated when either is not a single minute. Code `DEPENDENCY`. Missing dates on either side mean the check is skipped, and a `WARN DEPENDENCY_UNDATED` is given.
- **FR-2 Dead or unborn participant.**
  - For each event and each `participants` target of type person (category `person`): the event start is compared with the person's death (`DEAD_PARTICIPANT`) and the event end with the person's birth (`UNBORN_PARTICIPANT`).
  - The same check applies to `learns` targets that are people: an item that learns something after its death.
- **FR-3 Two places at once** (`TWO_PLACES`). For each person, take every pair of events they take part in whose locations are known and not the same place:
  - FAIL if the two cores overlap.
  - WARN if only the hulls overlap and both events have hour or minute precision. Day-level coincidences are too common to flag.
- **FR-4 Age sanity.**
  - `PARENT_AGE`: a `parent` must be at least `min_parent_age` years older than the child (default 12, set via `checks.min_parent_age`).
  - `AGE_LIMIT`: no person may be older than `max_age` at an event they take part in (default 130).
- **FR-5 Declarative rules** (`lore.json` `rules`, a list). Each rule has `rule`, a match `select` (`{type, tag, field: value}`, all optional), an optional `code` (overrides the default code) and an optional `severity` cap (`"warn"`).
  - `{"rule": "max_duration", "max": "1d"}`: the item's span must not exceed max. FAIL if the core length > max; WARN if only the hull length > max. Default code `MAX_DURATION`.
  - `{"rule": "gap", "role": "R", "exactly"|"min"|"max": "7d", "from": "start"|"end"}`: for each selected item with role R linking to Y, measure from Y's start (or end) to the item's start. Default code `GAP`.
  - `{"rule": "monotonic", "order": "chapter", "group": "rail"}`: among selected items that share a `group` value, sorted by the numeric `order` field, the start dates must not decrease. FAIL if a later item's start is definitely before an earlier item's start. Default code `ORDER_REGRESSION`. Saga rails use `code: "RAIL_REGRESSION"`.
- **FR-6 Story order versus chronology** (`STORY_ORDER`, always WARN). If `narrative.md` exists, its wikilinks in document order form the story order. An item whose start is definitely before the start of an item that comes earlier in the story is reported as a flashback, at info level as WARN. This is off by default; enable it with `checks.story_order: true`, because flashbacks are often intended.
- **FR-7 Findings.** Each finding is `{severity, code, detail, path, line}`. `line` points at the frontmatter key that carries the problem (the role, or the date key). `detail` names the other item and shows both dates formatted in their calendars.
- **FR-8 In-memory items.** Checks run on any list of `Item`s, including items built in memory, which the saga integration uses for chapter cards. `store.Item.from_fields(path, fields, line_map=None)` builds one without a file.
- **FR-9 New ops.**
  - `where PERSON --at DATE`: the latest event at or before DATE with a known location that PERSON took part in, plus `uncertain: true` when the order is not definite.
  - `knows PERSON --at DATE`: every item that PERSON learned (via the `learns` roles of events they took part in) by DATE.

## Success criteria
- **SC-1** Fixture world: `PARENT_AGE` FAIL for Ivo Brandt and Mara Quell. The dependency `after [[The flood at Saltmarsh]] +2d` is satisfied.
- **SC-2** A unit vector for each check gives FAIL in the definite case, WARN in the possible case, and nothing when it is satisfied.
- **SC-3** `provisional` caps the severity at WARN.
- **SC-4** A 3,000-item synthetic project checks in under 2 s.
- **SC-5** `check` exits 1 on any FAIL (already true from 001).
