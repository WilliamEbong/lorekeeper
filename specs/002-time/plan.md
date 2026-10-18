# Plan 002: time

## Files
- `lorekeeper/dates.py` [Codex]: axis maths, calendars, parse/format, durations, ages. Pure functions with no project access.
- `lorekeeper/store.py`: `Project.calendars`, built from `config["calendars"]` or the default.
- `lorekeeper/ops.py`:
  - `item_dates(project, item)` (FR-10)
  - the ops `when`, `age`, `timeline` and `convert`
  - the `DATE_UNPARSED` finding in `check`
- Tests:
  - `tests/test_dates.py` [Codex]
  - `tests/test_time_ops.py`
  - `tests/test_saga_dates.py` (SC-1; skipped without the sagas)

## dates.py contract
```python
UNITS = ("year", "month", "day", "hour", "minute")
class When(NamedTuple): lo: int; hi: int; precision: str; circa: bool; provisional: bool; note: str; calendar: str; text: str
class Calendar:
    id: str
    def parse(self, text) -> When | None
    def to_axis(self, year, month, day, hour=0, minute=0) -> int
    def from_axis(self, minutes) -> dict            # {year, month, day, hour, minute, display_year?}
    def add_months(self, minutes, months) -> int
    def format(self, minutes, precision="minute") -> str
def calendars(config_list) -> list[Calendar]        # None/[] -> [gregorian]
def parse(text, cals) -> When | None                # first calendar that parses wins
def parse_duration(text) -> tuple[int, int] | None  # (months, minutes)
def add(minutes, duration, cal) -> int
def span(lo, hi, cal) -> dict                        # greedy {years, months, weeks, days, hours, minutes}
def span_text(parts) -> str                          # the two largest non-zero units, e.g. "32 years, 4 months"
def age(birth, at, death, cal) -> dict               # {text, status: alive|before_birth|after_death, years: [min, max]}
def days_from_civil(y, m, d) -> int                  # 1970-01-01 = 0
def civil_from_days(n) -> tuple[int, int, int]
```

## Decisions
- **Minutes, not seconds:** no story needs seconds, and minutes keep the numbers readable.
- **One shared axis:** every calendar anchors to the Gregorian axis through its `epoch`, so comparing dates across calendars is plain integer comparison.
- **Saga-specific formats** such as SRD live in each saga's config, never in code.
