"""Integer-minute dates, configured calendars, and uncertainty intervals."""

import re
from bisect import bisect_right
from typing import NamedTuple

UNITS = ("year", "month", "day", "hour", "minute")


class When(NamedTuple):
    lo: int
    hi: int
    precision: str
    circa: bool
    provisional: bool
    note: str
    calendar: str
    text: str


def days_from_civil(y, m, d):
    """Hinnant's Gregorian day number, with 1970-01-01 at zero."""
    y -= m <= 2
    era = y // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    return era * 146097 + yoe * 365 + yoe // 4 - yoe // 100 + doy - 719468


def civil_from_days(n):
    n += 719468
    era = n // 146097
    doe = n - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    d = doy - (153 * mp + 2) // 5 + 1
    m = mp + (3 if mp < 10 else -9)
    return y + (m <= 2), m, d


_ORIGIN = days_from_civil(1, 1, 1)
_MONTH_NAMES = "January February March April May June July August September October November December".split()
_MONTHS = {name.lower(): i for i, name in enumerate(_MONTH_NAMES, 1)}
_MONTHS.update({name[:3].lower(): i for i, name in enumerate(_MONTH_NAMES, 1)})
_MONTHS["sept"] = 9
_MARKER = r"(?:~|c\.|ca\.|circa\b|about\b|approximately\b|approx\.|around\b)\s*"
_TIME = re.compile(r"(?:\s*,\s*|\s+|T)(\d{1,2}):(\d{2})(?:\s*([ap])\.?m\.?)?$", re.I)


class Calendar:
    def __init__(self, config):
        self.type = config.get("type", "gregorian")
        self.id = config.get("id", self.type)
        if self.type not in ("gregorian", "days", "months"):
            raise ValueError("unknown calendar type")
        self.config = config
        self.formats = [re.compile(f, re.I) for f in config.get("formats", [])]
        self.epoch_year = config.get("epoch_year", 0 if self.type == "days" else 1)
        self.offset = config.get("display_year_offset", 0)
        if self.type != "gregorian":
            epoch = Calendar({}).parse(config["epoch"])
            if epoch is None or epoch.precision != "day" or epoch.circa or epoch.note:
                raise ValueError("epoch must be a Gregorian date")
            self.epoch_day = epoch.lo // 1440
        if self.type == "days":
            self.year_days = config["year_days"]
            if self.year_days <= 0:
                raise ValueError("year_days must be positive")
        if self.type == "months":
            self.months = config["months"]
            if not self.months or any(m["days"] <= 0 or m.get("leap_days", m["days"]) <= 0 for m in self.months):
                raise ValueError("months must have positive lengths")
            self.cycles = config.get("leap_cycles", [])
            if any(c <= 0 for c in self.cycles):
                raise ValueError("leap cycles must be positive")
            self.cycle_years = max(self.cycles, default=1)
            self.year_starts = [0]
            for year in range(self.cycle_years):
                self.year_starts.append(self.year_starts[-1] + sum(self._lengths(year)))
            self.cycle_days = self.year_starts[-1]

    def _lengths(self, year):
        if self.type == "gregorian":
            leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
            return [31, 28 + leap, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        leap = False
        for i in range(len(self.cycles) - 1, -1, -1):
            if year % self.cycles[i] == self.config.get("leap_offset", 0):
                leap = i % 2 == 0
                break
        return [m.get("leap_days", m["days"]) if leap else m["days"] for m in self.months]

    def _year_start(self, year):
        # Floor division also counts complete blocks before year zero.
        blocks, remainder = divmod(year, self.cycle_years)
        epoch_blocks, epoch_remainder = divmod(self.epoch_year, self.cycle_years)
        return (self.epoch_day + (blocks - epoch_blocks) * self.cycle_days
                + self.year_starts[remainder] - self.year_starts[epoch_remainder])

    def to_axis(self, year, month, day, hour=0, minute=0):
        if not 0 <= hour < 24 or not 0 <= minute < 60:
            raise ValueError("invalid time")
        if self.type == "days":
            if month != 1 or not 1 <= day <= self.year_days:
                raise ValueError("invalid day")
            n = self.epoch_day + (year - self.epoch_year) * self.year_days + day - 1
        else:
            lengths = self._lengths(year)
            if not 1 <= month <= len(lengths) or not 1 <= day <= lengths[month - 1]:
                raise ValueError("invalid date")
            n = (days_from_civil(year, month, day) - _ORIGIN if self.type == "gregorian"
                 else self._year_start(year) + sum(lengths[:month - 1]) + day - 1)
        return n * 1440 + hour * 60 + minute

    def from_axis(self, minutes):
        n, time = divmod(minutes, 1440)
        hour, minute = divmod(time, 60)
        if self.type == "gregorian":
            year, month, day = civil_from_days(n + _ORIGIN)
        elif self.type == "days":
            year, day = divmod(n - self.epoch_day, self.year_days)
            year += self.epoch_year
            month, day = 1, day + 1
        else:
            blocks, remainder = divmod(n - self._year_start(0), self.cycle_days)
            year_in_cycle = bisect_right(self.year_starts, remainder) - 1
            year, month = blocks * self.cycle_years + year_in_cycle, 1
            day = remainder - self.year_starts[year_in_cycle] + 1
            for length in self._lengths(year):
                if day <= length:
                    break
                day -= length
                month += 1
        result = dict(year=year, month=month, day=day, hour=hour, minute=minute)
        if self.type == "days" and "display_year_offset" in self.config:
            result["display_year"] = year + self.offset
        return result

    def add_months(self, minutes, months):
        if self.type == "days":
            # No native months: exact multiples of 12 mean years; all other
            # counts mean 30-day months (including negative counts).
            days = months // 12 * self.year_days if months % 12 == 0 else months * 30
            return minutes + days * 1440
        p = self.from_axis(minutes)
        count = 12 if self.type == "gregorian" else len(self.months)
        year, month = divmod(p["year"] * count + p["month"] - 1 + months, count)
        day = min(p["day"], self._lengths(year)[month])
        return self.to_axis(year, month + 1, day, p["hour"], p["minute"])

    def format(self, minutes, precision="minute"):
        if precision not in UNITS:
            raise ValueError("invalid precision")
        p = self.from_axis(minutes)
        template = ""
        if precision == "hour":
            p["minute"] = 0
        if self.type == "gregorian":
            y = p["year"]
            if precision == "year" and y < 1:
                return f"{1 - y} BC"
            result = f"{y:04}" if y >= 0 else f"-{abs(y):04}"
            if precision != "year":
                result += f'-{p["month"]:02}'
            if precision not in ("year", "month"):
                result += f'-{p["day"]:02}'
        else:
            if precision == "year":
                return str(p.get("display_year", p["year"]))
            default = "Y{year} D{day:03}" if self.type == "days" else "{year}-{month:02}-{day:02}"
            p.setdefault("display_year", p["year"] + self.offset)
            template = self.config.get("display", default)
            result = template.format(**p)
        if precision in ("hour", "minute") and "{hour" not in template and "{minute" not in template:
            result += (" " if self.type == "gregorian" else ", ") + f'{p["hour"]:02}:{p["minute"]:02}'
        return result

    def _interval(self, year, month, day, hour, minute, precision):
        lo = self.to_axis(year, month, day, hour, minute)
        if precision == "year":
            hi = self.to_axis(year + 1, 1, 1)
        elif precision == "month":
            hi = self.add_months(lo, 1)
        else:
            hi = lo + {"day": 1440, "hour": 60, "minute": 1}[precision]
        return When(lo, hi, precision, False, False, "", self.id, "")

    def _gregorian(self, text):
        hour = minute = 0
        time = _TIME.search(text)
        if time:
            text = text[:time.start()].strip()
        era = re.search(r"\s+(BC|BCE|AD|CE)$", text, re.I)
        if era:
            text = text[:era.start()].strip()
        decade = re.fullmatch(r"(\d{2,})0s", text)        # "2040s": the ten years 2040-2049
        if decade and not era and not time:
            year = int(decade[1]) * 10
            return self._interval(year, 1, 1, 0, 0, "year")._replace(hi=self.to_axis(year + 10, 1, 1))
        iso = re.fullmatch(r"(-?\d+)(?:-(\d{2})(?:-(\d{2}))?)?", text)
        if iso:
            year = int(iso[1])
            month, day = int(iso[2] or 1), int(iso[3] or 1)
            precision = "day" if iso[3] else "month" if iso[2] else "year"
        else:
            written = re.fullmatch(r"([A-Za-z]+\.?)\s+(?:(\d{1,2})\s*,\s*)?(-?\d+)", text)
            reverse = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+\.?)\s+(-?\d+)", text)
            if written:
                name, day, year = written.groups()
            elif reverse:
                day, name, year = reverse.groups()
            else:
                return None
            month = _MONTHS.get(name.lower().rstrip("."))
            if month is None:
                return None
            precision = "day" if day else "month"
            year, day = int(year), int(day or 1)
        if era:
            if year <= 0:
                return None
            if era[1].upper() in ("BC", "BCE"):
                year = 1 - year
        if time:
            if precision != "day":
                return None
            hour, minute = int(time[1]), int(time[2])
            if time[3]:
                if not 1 <= hour <= 12:
                    raise ValueError("invalid twelve-hour time")
                hour = hour % 12 + (12 if time[3].lower() == "p" else 0)
            precision = "minute"
        return self._interval(year, month, day, hour, minute, precision)

    def _expression(self, text):
        if self.type == "gregorian":
            year_range = re.fullmatch(r"(\d{3,})[-\u2013\u2014](\d{3,})", text)
            if ".." in text or year_range:
                ends = text.split("..") if ".." in text else year_range.groups()
                if len(ends) != 2:
                    return None
                a, b = (self._parse(end) for end in ends)
                if a is None or b is None or b.lo < a.lo:
                    return None
                return When(a.lo, b.hi, min((a.precision, b.precision), key=UNITS.index),
                            a.circa or b.circa, a.provisional or b.provisional,
                            "; ".join(n for n in (a.note, b.note) if n), self.id, "")
            return self._gregorian(text)
        for pattern in self.formats:
            match = pattern.fullmatch(text)
            if not match:
                continue
            p = match.groupdict()
            year = int(p["year"]) if p.get("year") is not None else int(p["display_year"]) - self.offset
            month = p.get("month") or "1"
            if self.type == "months" and not re.fullmatch(r"\d+", month):
                month = next((str(i) for i, m in enumerate(self.months, 1)
                              if m["name"].casefold() == month.casefold()), "0")
            precision = "day" if p.get("day") is not None else "month" if p.get("month") is not None else "year"
            if p.get("minute") is not None:
                precision = "minute"
            elif p.get("hour") is not None:
                precision = "hour"
            return self._interval(year, int(month), int(p.get("day") or 1),
                                  int(p.get("hour") or 0), int(p.get("minute") or 0), precision)
        return None

    def parse(self, text):
        try:
            return self._parse(text)
        except (ValueError, KeyError):
            return None

    def _parse(self, text):
        # None means unmatched; invalid recognized expressions raise so callers
        # can stop calendar and leading-label fallback as well as shorter cuts.
        if not isinstance(text, str) or not text.strip():
            return None
        source = text.strip()
        # Longest complete expression wins: commas inside dates/configured
        # formats belong to the grammar before they can introduce a note.
        cuts = [len(source)] + [m.start() for m in reversed(list(re.finditer(r"[,;(]", source)))]
        for cut in cuts:
            expression = source[:cut].strip()
            leading = timed = 0
            # In A..B, circa belongs to its endpoint, not the entire range.
            if ".." not in expression:
                expression, leading = re.subn(r"^" + _MARKER, "", expression, flags=re.I)
                expression, timed = re.subn(r"(?<=[\s,])" + _MARKER + r"(?=\d{1,2}:\d{2})",
                                           "", expression, flags=re.I)
            result = self._expression(expression)
            if result is None:
                continue
            note = source[cut:].strip()
            if note:
                note = note[1:].strip()
                if source[cut] == "(" and note.endswith(")"):
                    note = note[:-1].strip()
            note = "; ".join(n for n in (result.note, note) if n)
            lo, hi = result.lo, result.hi
            if leading or timed:
                if result.precision == "year":
                    # Calendar years can contain other than twelve months.
                    def shift_year(n, delta):
                        p = self.from_axis(n)
                        return self.to_axis(p["year"] + delta, 1, 1)
                    lo, hi = shift_year(lo, -1), shift_year(hi, 1)
                elif result.precision == "month":
                    lo, hi = self.add_months(lo, -1), self.add_months(hi, 1)
                else:
                    width = {"day": 1440, "hour": 60, "minute": 15}[result.precision]
                    lo, hi = lo - width, hi + width
            return result._replace(lo=lo, hi=hi, circa=result.circa or bool(leading or timed),
                                   provisional="provisional" in note.lower(), note=note, text=text)
        return None


def calendars(config_list):
    return [Calendar(c) for c in (config_list or [{"type": "gregorian"}])]


def parse(text, cals):
    for cal in cals:
        try:
            result = cal._parse(text)
        except (ValueError, KeyError):
            return None
        if result is not None:
            return result
    label, sep, rest = text.partition(", ") if isinstance(text, str) else ("", "", "")
    if sep:                       # "African Collapse Wars, 2040s": a label before the date
        result = parse(rest, cals)
        if result is not None:
            return result._replace(note="; ".join(n for n in (label.strip(), result.note) if n), text=text)
    return None


_DURATION_UNITS = {}
for _names, _value in (("y yr year years", (12, 0)), ("mo month months", (1, 0)),
                       ("w wk week weeks", (0, 10080)), ("d day days", (0, 1440)),
                       ("h hr hour hours", (0, 60)), ("m min minute minutes", (0, 1))):
    _DURATION_UNITS.update(dict.fromkeys(_names.split(), _value))


def parse_duration(text):
    if not isinstance(text, str):
        return None
    text = text.strip().lower()
    sign = -1 if text.startswith("-") else 1
    if text.startswith(("-", "+")):
        text = text[1:].lstrip()
    months = minutes = pos = 0
    for m in re.finditer(r"(\d+)\s*([a-z]+)", text):
        if text[pos:m.start()].strip() or m[2] not in _DURATION_UNITS:
            return None
        a, b = _DURATION_UNITS[m[2]]
        months += int(m[1]) * a
        minutes += int(m[1]) * b
        pos = m.end()
    if not pos or text[pos:].strip():
        return None
    return sign * months, sign * minutes


def add(minutes, duration, cal):
    months, rest = duration
    return cal.add_months(minutes, months) + rest


def span(lo, hi, cal):
    if lo > hi:
        raise ValueError("span requires lo <= hi")
    count = len(cal.months) if cal.type == "months" else 12
    low, high = 0, 1
    while cal.add_months(lo, count * high) <= hi:
        low, high = high, high * 2
    while low + 1 < high:
        mid = (low + high) // 2
        if cal.add_months(lo, count * mid) <= hi:
            low = mid
        else:
            high = mid
    result = {"years": low}
    start = cal.add_months(lo, count * low)
    if cal.type == "days":
        months = (hi - start) // (30 * 1440)
        # The remaining span is shorter than a year, so positive multiples
        # of 12 cannot fit, even when a very long year fits many 30-day months.
        if months and months % 12 == 0:
            months -= 1
    else:
        months = 0
        # Do not cap at 11: clamping a leap-day start can leave 12 whole
        # months after the greedy year step (2020-02-29 to 2024-02-28).
        while cal.add_months(start, months + 1) <= hi:
            months += 1
    result["months"] = months
    rest = hi - cal.add_months(start, months)
    for name, size in (("weeks", 10080), ("days", 1440), ("hours", 60), ("minutes", 1)):
        result[name], rest = divmod(rest, size)
    return result


def span_text(parts):
    units = ("years", "months", "weeks", "days", "hours", "minutes")
    values = [f"{parts.get(u, 0)} {u[:-1] if parts.get(u) == 1 else u}" for u in units if parts.get(u)]
    return ", ".join(values[:2]) or "0 minutes"


def age(birth, at, death, cal):
    if at.hi <= birth.lo:
        status, text = "before_birth", span_text(span(at.lo, birth.lo, cal)) + " before birth"
    elif death is not None and death.lo <= at.lo:
        status, text = "after_death", span_text(span(death.lo, at.lo, cal)) + " after death"
    else:
        # Overlapping uncertainty can put at.lo before birth.lo: use zero.
        status, text = "alive", span_text(span(birth.lo, max(birth.lo, at.lo), cal))

    def years(start, end):
        if start <= end:
            return span(start, end, cal)["years"]
        return -span(end, start, cal)["years"]

    return dict(text=text, status=status, years=[years(birth.hi - 1, at.lo), years(birth.lo, at.hi - 1)])
