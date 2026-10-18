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
            lo, hi = (lo_w or hi_w).lo, (hi_w or lo_w).hi
            if lo < hi:
                start = (lo_w or hi_w)._replace(lo=lo, hi=hi)
            else:
                bad.append(("date_max", f"{f.get('date_max')} is before date_min {f.get('date_min')}"))
        elif start is not None and (lo_w or hi_w):     # bounds narrow a stated date, never move it
            lo = max(start.lo, lo_w.lo) if lo_w else start.lo
            hi = min(start.hi, hi_w.hi) if hi_w else start.hi
            if lo < hi:
                start = start._replace(lo=lo, hi=hi)
            else:
                bad.append(("date_min" if lo_w else "date_max", "contradicts the stated date"))
        raw = f.get("duration")
        duration = dates.parse_duration(str(raw)) if raw else None
        if raw and duration is None:
            bad.append(("duration", raw))
        category = p.schema["types"].get(item.type, {}).get("category")
        if start and end is None and category != "person":
            cal = calendar_of(p, start)
            # possible ends are start instants plus the duration; add() never decreases, so the
            # bounds come from the first and last possible start minute
            end = start._replace(lo=dates.add(start.lo, duration, cal),
                                 hi=dates.add(start.hi - 1, duration, cal) + 1) if duration else start
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
    """A date string, or an item name meaning that item's whole span (start to end)."""
    when = dates.parse(at, p.calendars)
    if when is None:
        start, end, _ = item_dates(p, p.find(at))
        if start is None:
            raise LoreError("INVALID", f"{at!r} is neither a date nor a dated item")
        when = start._replace(hi=max(start.hi, (end or start).hi))
    return when
