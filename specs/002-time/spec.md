# Feature 002: Time (calendars, dates with uncertainty, durations, ages)

## Overview
Dates in a story world are written at whatever precision the author knows: "2036", "November 2036", "November 20, 2036", "approximately 5:40 a.m.", "SRD Y0 D004", "2045-2047". Lorekeeper reads each date as an **interval on one shared time axis**: integer minutes from 0001-01-01 00:00, proleptic Gregorian. It does the arithmetic and computes ages, and it never invents precision. A project can hold several calendars (Gregorian, a custom month calendar, a year/day production calendar), and they all convert through the axis.

## User scenarios
1. **Saga cards parse.** The Realm card "November 20, 2036", the Zombies card "March 3, 2071, approximately 5:40 a.m." and the Space card "SRD Y0 D004 (PROVISIONAL production calendar)" all parse. The Space date also displays as `6842 CE, Day 004`.
2. **Ages.** `lore age "Darius Cole" --at "First crossing"` prints "35 years, 8 months". For someone born "~1951", it gives a range of years.
3. **Timeline.** `lore timeline` lists dated items in chronological order, each shown in its own calendar.
4. **Conversion.** `lore convert "SRD Y-6 D204"` shows the date on every calendar in the project.

## Functional requirements
- **FR-1 Axis.** Every date is a half-open interval `[lo, hi)` of integer axis minutes. Gregorian conversion uses Hinnant's days-from-civil. No `datetime`.
- **FR-2 Precision.** A date written to year, month, day, hour or minute covers exactly that unit: "2036-11" is the whole of November.
- **FR-3 Gregorian formats.** Case-insensitive, whitespace-tolerant.
  - **ISO:** `YYYY`, `YYYY-MM`, `YYYY-MM-DD`, `YYYY-MM-DD HH:MM` (also with `T`). Negative ISO years are astronomical (`-0043` = 44 BC).
  - **Written out:** `Month D, YYYY`, `D Month YYYY`, `Month YYYY`. Full or 3-letter month names.
  - **Era suffix:** `YYYY BC|BCE|AD|CE`.
  - **Time** after a date: `, H:MM a.m.|p.m.|am|pm`, `, HH:MM`, or ` HH:MM`.
  - **Circa markers:** `~`, `c.`, `ca.`, `circa`, `about`, `approximately`. A marker may sit before the date or before the time.
  - **Ranges:** `A..B`, and the year ranges `YYYY-YYYY` and `YYYY–YYYY`. A range runs from the start of A to the end of B.
- **FR-4 Notes.** Trailing text the grammar doesn't consume (after a comma, or in parentheses) is kept as `note`, not rejected: "framed in 2071", "(continuous action)". A note containing "provisional" sets `provisional: true`.
- **FR-5 Circa.** A circa date widens by one unit of its precision on each side (minute precision: ±15 minutes) and carries `circa: true`.
- **FR-6 Calendars.** The `lore.json` key `calendars` lists calendars, tried in order. Default: `[{"id":"gregorian","type":"gregorian"}]`. Three types:
  - **`gregorian`:** built in.
  - **`days`:** years of `year_days` numbered days. Year `epoch_year` (default 0), day 1, begins at `epoch` (a Gregorian date). Each calendar also has:
    - `formats`: regexes whose named groups are among `year`, `display_year`, `day`, `hour`, `minute`. A `display_year` is converted back by subtracting `display_year_offset`.
    - `display`: a format string over `year`, `display_year`, `day`, `hour`, `minute`.
    - **SRD example:** `year_days` 365; `display_year_offset` 6842; formats `SRD Y(?P<year>-?\d+) D(?P<day>\d+)` and `(?P<display_year>-?\d+) CE, Day (?P<day>\d+)(?:, (?P<hour>\d\d):(?P<minute>\d\d))?`; display `{display_year} CE, Day {day:03}`.
  - **`months`:** `months: [{name, days, leap_days?}]`, with optional Aeon-style leap years (`leap_cycles`, `leap_offset`), plus `epoch`, `epoch_year` (default 1), `formats` and `display`.
- **FR-7 Durations.** `"2h"`, `"45m"`, `"3d"`, `"2w"`, `"1y 2mo"`, `"7 days"`, `"+2d"` and `"-1h"` all parse to `(months, minutes)`. To add a duration, add the months first (clamping the day to the month's length), then the minutes.
- **FR-8 Formatting.** Show an axis minute in any calendar at a given precision. Gregorian output is ISO-like `YYYY-MM-DD HH:MM`, cut to the precision.
- **FR-9 Ages (Aeon rule).** An age is the span from the subject's start to the event's start, broken down greedily (years, months, weeks, days, hours, minutes) and shown as its two largest non-zero units ("32 years, 4 months").
  - If the event ends before the subject's start, it reads "N before birth".
  - If the subject has ended, and that end is at or before the event's start, it reads "N after death".
  - The start is each interval's `lo`, so a year-only birth counts from 1 January.
  - It also reports `years: [min, max]`, in whole years: min runs from the latest possible birth to the earliest possible event start; max from the earliest birth to the latest event start.
- **FR-10 Item dates.**
  - **Start** is the first present of `born`, `date` or `start`. **End** is `died` or `end`.
  - **No end:** an event lasts its own precision interval, or `duration` from its start if that is set.
  - **Narrowing:** `date_min` / `date_max` narrow the interval.
  - **Bad values:** an unparseable value gives `WARN DATE_UNPARSED <key> <value>` in `check`.
- **FR-11 New ops.**
  - `when ITEM`: start and end intervals, formatted.
  - `age ITEM --at DATE_OR_ITEM`: the age result.
  - `timeline [--type T] [--from D] [--to D]`: dated items sorted by start, then end.
  - `convert DATE`: the date on every project calendar.

## Success criteria
- **SC-1** Every card date in the three saga architectures parses with that saga's calendars, or is listed in an unparsed report. The target is 100% parsed.
- **SC-2** The [4,100,400] leap rule holds (1900 is not a leap year, 2000 is), and days-from-civil round-trips every day from year -1000 to 3000.
- **SC-3** `SRD Y0 D004` ↔ `6842 CE, Day 004` both ways, and `Y-6 D204` displays as `6836 CE, Day 204`.
- **SC-4** Age test vectors match the Aeon rule, including "before birth", "after death" and year-precision births.
- **SC-5** Circa, range and precision intervals are exact on the test vectors.
