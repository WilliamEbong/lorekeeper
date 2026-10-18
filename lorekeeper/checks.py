"""Read-only, uncertainty-aware continuity checks over stored or in-memory items."""
import math
import os
import re
from heapq import heappop, heappush
from itertools import groupby

from . import dates
from .store import finding, link_parts
from .timeinfo import START_KEYS, calendar_of, item_dates, shift, show_when


def possible(x):
    """Inclusive possible minutes (the stored upper bound is exclusive)."""
    return x.lo, x.hi - 1


def compare_ge(x, y, lag_minutes=0):
    a, b = possible(x)
    c, d = possible(y)
    return "FAIL" if b < c + lag_minutes else "WARN" if a < d + lag_minutes else None


def compare_eq(x, y, lag_minutes=0):
    a, b = possible(x)
    c, d = (n + lag_minutes for n in possible(y))
    return "FAIL" if b < c or d < a else "WARN" if a != b or c != d else None


def same_place(project, a, b):
    if a is None or b is None:
        return False

    def reaches(start, target):
        pending, seen = [start], set()
        while pending:
            item = pending.pop()
            if item is target:
                return True
            if item in seen:
                continue
            seen.add(item)
            pending.extend(other for _, other, _ in project.links(item).get("located_in", []) if other)
        return False

    # Follow ancestry in either direction, not an undirected graph: siblings differ.
    return reaches(a, b) or reaches(b, a)


def _compare_shifted_eq(x, y, duration, cal):
    target = shift(y, duration, cal)
    # Bound exact month-shift work to two days of source minutes; wider
    # intervals use the hull. Within each source day the shift is continuous.
    if duration[0] and y.hi - y.lo <= 2 * 1440:
        lo = y.lo
        while lo < y.hi:
            hi = min(y.hi, (lo // 1440 + 1) * 1440)
            segment = shift(y._replace(lo=lo, hi=hi), duration, cal)
            if x.lo < segment.hi and segment.lo < x.hi:
                return compare_eq(x, target)
            lo = hi
        return "FAIL"
    return compare_eq(x, target)


def _date_key(item):
    return next((k for k in (*START_KEYS, "date_min", "date_max") if item.fields.get(k)), "date")


def _selected(item, select):
    tags = item.fields.get("tags", [])
    tags = tags if isinstance(tags, list) else [tags]
    return all(value in tags if key == "tag" else item.fields.get(key) == value
               for key, value in select.items())


def run(project):
    p, out = project, []
    settings = p.config.get("checks", {})
    times = {item: item_dates(p, item)[:2] for item in p.items}
    people = {item for item in p.items if p.schema["types"].get(item.type, {}).get("category") == "person"}
    appearances = {}
    provisional = {i for i in p.items if i.fields.get("status") == "provisional" or
                   any(w and w.provisional for w in times[i])}

    def emit(severity, code, item, key, other, x, y, detail, rule=None, extra=()):
        if not severity:
            return
        involved = (item, other, *extra)
        if any(i in provisional for i in involved) or (rule or {}).get("severity", "").lower() == "warn":
            severity = "WARN"
        shown = lambda w: show_when(p, w)["from"] if w else "undated"
        text = f"{item.name} ({shown(x)}): {detail}; {other.name} ({shown(y)})"
        out.append(finding(severity, (rule or {}).get("code", code), text, item.path, item.line(key)))

    for item in p.items:
        start, end = times[item]
        links = p.links(item)
        for role, ix, iy, compare in (("after", 0, 1, compare_ge), ("same_start", 0, 0, compare_eq),
                                     ("same_end", 1, 1, compare_eq), ("sf", 1, 0, compare_ge)):
            for _, other, lag in links.get(role, []):
                if other is None:     # Broken links are already reported by Project.findings().
                    continue
                x, y = times[item][ix], times[other][iy]
                if x is None or y is None:
                    emit("WARN", "DEPENDENCY_UNDATED", item, role, other, x, y, role)
                    continue
                duration = dates.parse_duration(lag) if lag else (0, 0)
                # A malformed lag must never silently become a satisfied zero-lag link.
                cal = calendar_of(p, start or end)
                severity = (_compare_shifted_eq(x, y, duration, cal) if compare is compare_eq else
                            compare(x, shift(y, duration, cal))) if duration else "WARN"
                emit(severity, "DEPENDENCY", item, role, other, x, y, f"{role} {lag}".strip())

        for role in ("participants", "learns"):
            for _, person, _ in links.get(role, []):
                if person not in people:
                    continue
                birth, death = times[person]
                # Birth/death minutes are inclusive; strictly outside is a violation.
                if start and death:
                    emit(compare_ge(death, start), "DEAD_PARTICIPANT", item, role, person,
                         start, death, "after death")
                if end and birth:
                    emit(compare_ge(end, birth), "UNBORN_PARTICIPANT", item, role, person,
                         end, birth, "before birth")
                if role == "participants":
                    appearances.setdefault(person, set()).add(item)
                    if start and birth:
                        cal = calendar_of(p, birth)
                        count = len(cal.months) if cal.type == "months" else 12
                        limit = (count * int(settings.get("max_age", 130)), 0)
                        emit(compare_ge(shift(birth, limit, cal), start),
                             "AGE_LIMIT", item, role, person, start, birth, "exceeds maximum age")
        if item in people and start:
            for _, parent, _ in links.get("parent", []):
                if parent in people and times[parent][0]:
                    birth = times[parent][0]
                    cal = calendar_of(p, start)
                    count = len(cal.months) if cal.type == "months" else 12
                    minimum = (count * int(settings.get("min_parent_age", 12)), 0)
                    emit(compare_ge(start, shift(birth, minimum, cal)),
                         "PARENT_AGE", item, "parent", parent, start, birth, "parent too young")

    if settings.get("two_places", "on") != "off":
        places = {i: frozenset(o for _, o, _ in p.links(i).get("location", []) if o) for i in p.items}
        place_cache = {}

        def compatible(xs, ys):
            if xs & ys:
                return True
            for x in xs:
                for y in ys:
                    pair = frozenset((x, y))
                    if pair not in place_cache:
                        place_cache[pair] = same_place(p, x, y)
                    if place_cache[pair]:
                        return True
            return False

        for person, events in appearances.items():
            events = sorted((i for i in events if all(times[i]) and places[i]),
                            key=lambda i: (times[i][0].lo, i.path))
            active, expiry = {}, []
            for index, item in enumerate(events):
                start, end = times[item]
                while expiry and expiry[0][0] <= start.lo:
                    _, _, expired = heappop(expiry)
                    bucket = active[places[expired]]
                    del bucket[expired]
                    if not bucket:
                        del active[places[expired]]
                for locations, bucket in active.items():
                    if compatible(places[item], locations):
                        continue
                    for other in bucket:
                        a, b = times[other]
                        core = max(start.hi - 1, a.hi - 1) <= min(end.lo, b.lo)
                        hull = max(start.lo, a.lo) < min(end.hi, b.hi)
                        fine = all(w.precision in ("hour", "minute") for w in (start, end, a, b))
                        severity = "FAIL" if core else "WARN" if hull and fine else None
                        emit(severity, "TWO_PLACES", item, "participants", other, start, a,
                             f"{person.name} in different places", extra=(person,))
                active.setdefault(places[item], {})[item] = None
                heappush(expiry, (end.hi, index, item))

    def ordered(items, code, rule=None, definite_only=False):
        # Extremal prior bounds catch regressions hidden by an uncertain neighbour.
        prior, committed = [None, None], [None, None]
        for batch in items:
            for item in batch:
                start = times[item][0]
                severity, other = None, None
                # Prefer committed evidence for FAIL before applying severity caps.
                for candidate in (committed[0], prior[0], committed[1], prior[1]):
                    if candidate:
                        other = candidate
                        severity = compare_ge(start, times[other][0])
                        if severity == "FAIL":
                            break
                if severity and (not definite_only or severity == "FAIL"):
                    emit("WARN" if definite_only else severity, code, item, _date_key(item),
                         other, start, times[other][0], "chronology runs backwards", rule)
            for item in batch:
                for extrema in (prior,) if item in provisional else (prior, committed):
                    if extrema[0] is None or times[item][0].lo > times[extrema[0]][0].lo:
                        extrema[0] = item
                    if extrema[1] is None or times[item][0].hi > times[extrema[1]][0].hi:
                        extrema[1] = item

    for rule in p.config.get("rules", []):
        selected = [i for i in p.items if _selected(i, rule.get("select", {}))]
        kind = rule.get("rule")
        if kind == "monotonic":
            groups = {}
            for item in selected:
                try:
                    order = float(item.fields[rule["order"]])
                except (KeyError, TypeError, ValueError):
                    continue
                if not math.isfinite(order) or not times[item][0]:
                    continue
                group = item.fields.get(rule.get("group"))
                if isinstance(group, list):
                    group = tuple(group)
                groups.setdefault(group, []).append((order, item))
            for group in groups.values():
                # Equal numeric order values are peers, with no order between them.
                batches = [[i for _, i in batch] for _, batch in
                           groupby(sorted(group, key=lambda pair: pair[0]), key=lambda pair: pair[0])]
                ordered(batches, "ORDER_REGRESSION", rule)
        elif kind == "max_duration":
            duration = dates.parse_duration(rule.get("max"))
            if duration is None:
                continue
            for item in selected:
                start, end = times[item]
                if start and end:
                    cal = calendar_of(p, start)
                    # Use the spec's literal core/hull lengths, including hull's exclusive end.
                    limit = shift(start, duration, cal)
                    severity = ("FAIL" if end.lo > limit.hi - 1 else
                                "WARN" if end.hi > limit.lo else None)
                    key = "end" if item.fields.get("end") else "duration" if item.fields.get("duration") else _date_key(item)
                    emit(severity, "MAX_DURATION", item, key, item, start, end,
                         f"span exceeds {rule['max']}", rule)
        elif kind == "gap":
            for item in selected:
                start = times[item][0]
                if start is None:
                    continue
                for _, other, _ in p.links(item).get(rule.get("role"), []):
                    # With no 'from', a gap begins at the linked item's end (like FS).
                    origin = times[other][0 if rule.get("from", "end") == "start" else 1] if other else None
                    if origin is None:
                        continue
                    for bound in ("exactly", "min", "max"):
                        duration = dates.parse_duration(rule.get(bound))
                        if duration is None:
                            continue
                        cal = calendar_of(p, start)
                        target = shift(origin, duration, cal)
                        severity = (_compare_shifted_eq(start, origin, duration, cal) if bound == "exactly" else
                                    compare_ge(start, target) if bound == "min" else compare_ge(target, start))
                        emit(severity, "GAP", item, rule["role"], other, start, origin,
                             f"gap {bound} {rule[bound]}", rule)

    if settings.get("story_order", False):
        try:
            with open(os.path.join(p.root, "narrative.md"), encoding="utf-8") as fh:
                narrative = fh.read()
        except FileNotFoundError:
            narrative = ""
        links = (link_parts(link) for link in re.findall(r"\[\[[^\[\]\r\n]+\]\]", narrative))
        story = [p.resolve(parts[0]) for parts in links if parts]
        ordered([[i] for i in story if i and times[i][0]], "STORY_ORDER", definite_only=True)
    return out
