"""Dates of items: which keys mean start and end, narrowing, durations, display."""
from . import dates
from .store import LoreError

START_KEYS, END_KEYS = ("born", "date", "start"), ("died", "end")


def _first(fields, keys):
    for key in keys:
        value = fields.get(key)
        if value not in (None, "", []):
            return key, value if isinstance(value, str) else ", ".join(value)
    return None, None


def calendar_of(p, when):
    return next((c for c in p.calendars if c.id == when.calendar), p.calendars[0])


def item_dates(p, item):
    """(start When|None, end When|None, [(key, unparsed value)]); cached per project."""
    cache = p.__dict__.setdefault("_dates", {})
    if id(item) not in cache:
        f, cals, bad = item.fields, p.calendars, []

        def read(key, value):
            when = dates.parse(value, cals) if value else None
            if value and when is None:
                bad.append((key, value))
            return when
        start = read(*_first(f, START_KEYS))
        end = read(*_first(f, END_KEYS))
        lo_w = read("date_min", f.get("date_min") or None)
        hi_w = read("date_max", f.get("date_max") or None)
        if start is None and (lo_w or hi_w):          # only bounds known: they are the interval
            start = (lo_w or hi_w)._replace(lo=(lo_w or hi_w).lo, hi=(hi_w or lo_w).hi)
        elif start is not None:                        # bounds narrow a stated date
            lo = max(start.lo, lo_w.lo) if lo_w else start.lo
            hi = min(start.hi, hi_w.hi) if hi_w else start.hi
            start = start._replace(lo=lo, hi=max(hi, lo + 1))
        category = p.schema["types"].get(item.type, {}).get("category")
        if start and end is None and category != "person":
            raw = f.get("duration")
            duration = dates.parse_duration(str(raw)) if raw else None
            if raw and duration is None:
                bad.append(("duration", raw))
            cal = calendar_of(p, start)
            end = start._replace(lo=dates.add(start.lo, duration, cal), hi=dates.add(start.hi, duration, cal)) \
                if duration else start
        cache[id(item)] = (start, end, bad)
    return cache[id(item)]


def show_when(p, when):
    if when is None:
        return None
    cal = calendar_of(p, when)
    out = {"text": when.text, "from": cal.format(when.lo, when.precision),
           "to": cal.format(when.hi - 1, when.precision), "precision": when.precision}
    out.update({k: v for k, v in (("circa", when.circa), ("provisional", when.provisional), ("note", when.note)) if v})
    return out


def parse_at(p, at):
    """A date string, or an item name meaning that item's start."""
    when = dates.parse(at, p.calendars)
    if when is None:
        when = item_dates(p, p.find(at))[0]
        if when is None:
            raise LoreError("INVALID", f"{at!r} is neither a date nor a dated item")
    return when
