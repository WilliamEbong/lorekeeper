"""Certainty vectors for the public checks API; synthetic worlds stay in memory."""
import os
import shutil
import tempfile
import time
import unittest
from unittest.mock import mock_open, patch

from lorekeeper import checks, dates
from lorekeeper.store import Item, Project
from lorekeeper.timeinfo import item_dates, show_when

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(ROOT, "tests", "fixtures", "world")


def item(name, type="event", **fields):
    return Item.from_fields(f"{name}.md", {"type": type, "canonical_name": name, **fields})


def project(*items, **config):
    return Project.from_items(ROOT, config, items)


def findings(p, code):
    return [f for f in checks.run(p) if f["code"] == code]


class Comparisons(unittest.TestCase):
    def test_possible_and_comparisons(self):
        def w(lo, hi):
            return dates.When(lo, hi, "minute", False, False, "", "gregorian", "")
        self.assertEqual(checks.possible(w(-3, 2)), (-3, 1))
        for compare, vectors in (
            (checks.compare_ge, [(0, 1, 2, 3, 0, "FAIL"), (0, 3, 2, 4, 0, "WARN"),
                                 (3, 4, 0, 4, 0, None), (3, 4, 0, 1, 3, None),
                                 (0, 1, 3, 4, -3, None)]),
            (checks.compare_eq, [(0, 1, 1, 2, 0, "FAIL"), (0, 2, 1, 2, 0, "WARN"),
                                 (0, 1, 0, 2, 0, "WARN"), (3, 4, 1, 2, 2, None),
                                 (0, 1, 1, 2, -1, None)])):
            for a, b, c, d, lag, expected in vectors:
                with self.subTest(compare=compare.__name__, vector=(a, b, c, d, lag)):
                    self.assertEqual(compare(w(a, b), w(c, d), lag), expected)

    def test_same_place_ancestry_siblings_and_cycles(self):
        town = item("Town", "location")
        inn = item("Inn", "location", located_in="[[Town]]")
        room = item("Room", "location", located_in="[[Inn]]")
        dock = item("Dock", "location", located_in="[[Town]]")
        a = item("A", "location", located_in="[[B]]")
        b = item("B", "location", located_in="[[A]]")
        p = project(town, inn, room, dock, a, b)
        for x, y in ((town, town), (town, room), (room, town), (a, b)):
            self.assertTrue(checks.same_place(p, x, y))
        for x, y in ((room, dock), (a, town), (None, None)):
            self.assertFalse(checks.same_place(p, x, y))


class Checks(unittest.TestCase):
    def assertSeverity(self, p, code, expected):
        found = findings(p, code)
        self.assertEqual([f["severity"] for f in found], [expected] if expected else [], found)
        return found

    def test_each_dependency(self):
        for role in ("after", "same_start", "same_end", "sf"):
            for value, expected in (("2020-01-01 00:00", "FAIL"), ("2020-01-03", "WARN"),
                                    ("2020-01-03 00:00", None)):
                with self.subTest(role=role, date=value):
                    if role in ("after", "sf") and expected == "WARN":
                        value = "~2020-01-03 00:00"  # Straddle the minimum threshold.
                    y = item("Y", date="2020-01-01 00:00", end="2020-01-01 00:00")
                    x = item("X", date=value, end=value, **{role: "[[Y]] +2d"})
                    self.assertSeverity(project(y, x), "DEPENDENCY", expected)
        # Distinct endpoints ensure FS, SS, FF and SF are not accidentally conflated.
        y = item("Y", date="2020-01-01 00:00", end="2020-01-03 00:00")
        for role, start, end in (("after", "05", "06"), ("same_start", "03", "06"),
                                 ("same_end", "03", "05"), ("sf", "01", "03")):
            x = item("X", date=f"2020-01-{start} 00:00", end=f"2020-01-{end} 00:00", **{role: "[[Y]] +2d"})
            self.assertSeverity(project(x, y), "DEPENDENCY", None)

    def test_missing_dates_and_broken_links(self):
        for xfields, yfields in (({}, {"date": "2020"}), ({"date": "2020"}, {}),
                                 ({"date": "nonsense"}, {"date": "2020"})):
            x, y = item("X", after="[[Y]]", **xfields), item("Y", **yfields)
            p = project(x, y)
            self.assertSeverity(p, "DEPENDENCY", None)
            f = self.assertSeverity(p, "DEPENDENCY_UNDATED", "WARN")[0]
            self.assertEqual(f["line"], x.line("after"))
        self.assertEqual(checks.run(project(item("X", after="[[Missing]]"))), [])
        x = item("X", date="2020", after="[[Y]] +nonsense")
        self.assertSeverity(project(x, item("Y", date="1900")), "DEPENDENCY", "WARN")

    def test_calendar_lags_and_gap(self):
        y = item("Y", date="2024-01-31 00:00")
        x = item("X", date="2024-03-01 00:00", same_start="[[Y]] +1mo 1d")
        self.assertSeverity(project(x, y), "DEPENDENCY", None)
        x = item("X", date="2024-01-30 00:00", same_start="[[Y]] -1d")
        self.assertSeverity(project(x, y), "DEPENDENCY", None)
        config = [{"type": "days", "id": "short", "epoch": "2000-01-01", "year_days": 360,
                   "formats": [r"Y(?P<year>\d+) D(?P<day>\d+) (?P<hour>\d+):(?P<minute>\d+)"]},
                  {"type": "gregorian"}]
        x = item("X", date="Y1 D001 00:00", same_start="[[Y]] +1y", paired="[[Y]]")
        y = item("Y", date="2000-01-01 00:00")
        p = project(x, y, calendars=config, rules=[{"rule": "gap", "role": "paired", "exactly": "1y", "from": "start"}])
        self.assertEqual(checks.run(p), [])  # A year is 360 days in the subject's calendar.

    def test_month_end_clamping_keeps_all_possible_minutes(self):
        y = item("Y", date="2023-01-30 23:00..2023-01-31 01:00")
        for value in ("2023-02-28 00:00", "2023-02-28 23:59"):
            x = item("X", date=value, same_start="[[Y]] +1mo")
            self.assertSeverity(project(x, y), "DEPENDENCY", "WARN")
        x = item("X", date="2023-03-01 00:00", same_start="[[Y]] +1mo")
        self.assertSeverity(project(x, y), "DEPENDENCY", "FAIL")

    def test_month_equality_preserves_disconnected_shifted_days(self):
        source = "2023-02-28 23:59..2023-03-01 00:00"
        for role in ("same_start", "same_end", "gap_start", "gap_end"):
            for value, expected in (("2023-03-30 00:00", "FAIL"),
                                    ("2023-03-28 23:59", "WARN"),
                                    ("2023-04-01 00:00", "WARN")):
                with self.subTest(role=role, value=value):
                    y = item("Y", date=source, end=source)
                    if role.startswith("gap_"):
                        x = item("X", date=value, paired="[[Y]]")
                        rules = [{"rule": "gap", "role": "paired", "exactly": "1mo",
                                  "from": role.removeprefix("gap_")}]
                        self.assertSeverity(project(x, y, rules=rules), "GAP", expected)
                    else:
                        x = item("X", date=value, end=value, **{role: "[[Y]] +1mo"})
                        self.assertSeverity(project(x, y), "DEPENDENCY", expected)
        # Clamping can also leave holes within a single target day.
        y = item("Y", date="2023-01-30 23:00..2023-01-31 01:00")
        x = item("X", date="2023-02-28 12:00", same_start="[[Y]] +1mo")
        self.assertSeverity(project(x, y), "DEPENDENCY", "FAIL")

    def test_provisional_caps_either_item_or_date(self):
        for side in ("X", "Y"):
            for mode in ("status", "date", "other_date"):
                with self.subTest(side=side, mode=mode):
                    fields = {"X": {"date": "2000-01-01 00:00", "after": "[[Y]]"},
                              "Y": {"date": "2020-01-01 00:00"}}
                    if mode == "status":
                        fields[side]["status"] = "provisional"
                    elif mode == "date":
                        fields[side]["date"] += " (PROVISIONAL)"
                    else:
                        fields[side]["end"] = "2021-01-01 (provisional)"
                    p = project(*(item(name, **f) for name, f in fields.items()))
                    self.assertSeverity(p, "DEPENDENCY", "WARN")

    def test_dead_and_unborn_participants_but_not_what_is_learned(self):
        for code, field, values in (
            ("DEAD_PARTICIPANT", "died", (("2019", "FAIL"), ("2020", "WARN"), ("2021", None))),
            ("UNBORN_PARTICIPANT", "born", (("2021", "FAIL"), ("2020", "WARN"), ("2019", None)))):
            for value, expected in values:
                with self.subTest(code=code, date=value):
                    person = item("Person", "hero", **{field: value})
                    event = item("Event", date="2020-06-01 00:00", end="2020-06-02 00:00", participants="[[Person]]")
                    self.assertSeverity(project(person, event, types={"hero": {"category": "person"}}), code, expected)
                    # A learns target is the thing learned (a dead victim, an unborn heir), not a learner.
                    event = item("Event", date="2020-06-01 00:00", end="2020-06-02 00:00", learns="[[Person]]")
                    self.assertSeverity(project(person, event, types={"hero": {"category": "person"}}), code, None)
        person = item("Person", "character", born="2020-01-01 00:00", died="2020-01-02 00:00")
        for value in ("2020-01-01 00:00", "2020-01-02 00:00"):
            self.assertEqual(checks.run(project(person, item("E", date=value, participants="[[Person]]"))), [])
        # An event dated exactly like the birth or death is that birth or death: no possible clash.
        for field in ("born", "died"):
            person = item("Person", "character", **{field: "1784-03"})
            self.assertEqual(checks.run(project(person, item("E", date="1784-03", participants="[[Person]]"))), [])
            self.assertSeverity(project(person, item("E", date="1784", participants="[[Person]]")),
                                "UNBORN_PARTICIPANT" if field == "born" else "DEAD_PARTICIPANT", "WARN")
        person = item("Person", "character", born="2020-01-01 00:00", died="2020-01-02 00:00")
        # Non-people are not subject to mortality checks; an event can span a birth.
        org = item("Guild", "organization", died="1900")
        event = item("E", date="2019", end="2021", participants=["[[Person]]", "[[Guild]]"])
        self.assertSeverity(project(person, org, event), "UNBORN_PARTICIPANT", None)

    def test_age_sanity_and_settings(self):
        for birth, expected in (("2010", "FAIL"), ("2008", "WARN"), ("2000", None)):
            parent = item("Parent", "character", born=birth)
            child = item("Child", "character", born="2020-06-01 00:00", parent="[[Parent]]")
            self.assertSeverity(project(parent, child), "PARENT_AGE", expected)
        for birth, expected in (("1800", "FAIL"), ("1890", "WARN"), ("1900", None)):
            person = item("Person", "character", born=birth)
            event = item("Event", date="2020-06-01 00:00", participants="[[Person]]")
            self.assertSeverity(project(person, event), "AGE_LIMIT", expected)
        parent = item("P", "character", born="2000-01-01 00:00")
        child = item("C", "character", born="2010-01-01 00:00", parent="[[P]]")
        event = item("E", date="2031", participants="[[P]]")
        p = project(parent, child, event, checks={"min_parent_age": 10, "max_age": 30})
        self.assertSeverity(p, "PARENT_AGE", None)
        self.assertSeverity(p, "AGE_LIMIT", "FAIL")

    def test_age_limits_use_native_month_count(self):
        config = {"type": "months", "epoch": "2000-01-01",
                  "months": [{"name": f"M{n}", "days": 30} for n in range(10)],
                  "formats": [r"Y(?P<year>\d+) M(?P<month>\d+) D(?P<day>\d+) (?P<hour>\d+):(?P<minute>\d+)"]}
        parent = item("Parent", "character", born="Y1 M1 D1 00:00")
        child = item("Child", "character", born="Y13 M1 D1 00:00", parent="[[Parent]]")
        event = item("Event", date="Y132 M1 D1 00:00", participants="[[Parent]]")
        p = project(parent, child, event, calendars=[config])
        with self.subTest(code="PARENT_AGE"):
            self.assertSeverity(p, "PARENT_AGE", None)
        with self.subTest(code="AGE_LIMIT"):
            self.assertSeverity(p, "AGE_LIMIT", "FAIL")
        p = project(parent, child, event, calendars=[config],
                    checks={"min_parent_age": 13, "max_age": 131})
        self.assertSeverity(p, "PARENT_AGE", "FAIL")
        self.assertSeverity(p, "AGE_LIMIT", None)

    def test_two_places_certainty_locations_and_switch(self):
        person, a, b = item("P", "character"), item("A", "location"), item("B", "location")
        for start, end, expected in (("2020-01-01 10:30", "2020-01-01 12:00", "FAIL"),
                                     ("~2020-01-01 11:00", "~2020-01-01 11:30", "WARN"),
                                     # Its earliest start (11:00) is X's latest end: touching, not overlapping.
                                     ("~2020-01-01 11:15", "~2020-01-01 11:30", None),
                                     ("2020-01-01 11:00", "2020-01-01 11:30", None),
                                     ("2020-01-01 12:00", "2020-01-01 13:00", None),
                                     ("2020-01-01", "2020-01-01", None)):
            x = item("X", date="2020-01-01 10:00", end="2020-01-01 11:00", participants="[[P]]", location="[[A]]")
            y = item("Y", date=start, end=end, participants="[[P]]", location="[[B]]")
            self.assertSeverity(project(person, a, b, x, y), "TWO_PLACES", expected)
            self.assertSeverity(project(person, a, b, x, y, checks={"two_places": "off"}), "TWO_PLACES", None)
        y = item("Y", date="2020-01-01 10:30", end="2020-01-01 12:00", participants="[[P]]", location="[[B]]")
        nested = item("B", "location", located_in="[[A]]")
        self.assertSeverity(project(person, a, nested, x, y), "TWO_PLACES", None)
        provisional = item("P", "character", status="provisional")
        self.assertSeverity(project(provisional, a, b, x, y), "TWO_PLACES", "WARN")
        # Day precision suppresses only possible clashes, not definite multi-day overlap.
        x = item("X", date="2020-01-01", end="2020-01-05", participants="[[P]]", location="[[A]]")
        y = item("Y", date="2020-01-03", end="2020-01-06", participants="[[P]]", location="[[B]]")
        self.assertSeverity(project(person, a, b, x, y), "TWO_PLACES", "FAIL")

    def test_two_places_back_to_back_stays_and_moments(self):
        person, inn, dock = item("P", "character"), item("Inn", "location"), item("Dock", "location")
        meeting = item("Meeting", date="2020-01-01 10:00", end="2020-01-01 11:00", participants="[[P]]", location="[[Inn]]")
        walk = item("Walk", date="2020-01-01 11:00", end="2020-01-01 11:30", participants="[[P]]",
                    location="[[Dock]]", after="[[Meeting]]")
        self.assertEqual(checks.run(project(person, inn, dock, meeting, walk)), [])
        # A moment (no end) lasts a minute: at the meeting's last minute it clashes, at its end it does not.
        for date, expected in (("2020-01-01 10:59", "FAIL"), ("2020-01-01 11:00", None), ("2020-01-01 10:00", "FAIL")):
            with self.subTest(moment=date):
                call = item("Call", date=date, participants="[[P]]", location="[[Dock]]")
                self.assertSeverity(project(person, inn, dock, meeting, call), "TWO_PLACES", expected)
        first = item("First", date="2020-01-01 10:00", participants="[[P]]", location="[[Inn]]")
        second = item("Second", date="2020-01-01 10:00", participants="[[P]]", location="[[Dock]]")
        self.assertSeverity(project(person, inn, dock, first, second), "TWO_PLACES", "FAIL")
        # A short event inside a stay elsewhere that is certain for days is a definite clash.
        siege = item("Siege", date="2020-01-01", end="2020-01-05", participants="[[P]]", location="[[Inn]]")
        for date in ("2020-01-03", "2020-01-03 12:00"):
            with self.subTest(wedding=date):
                wedding = item("Wedding", date=date, participants="[[P]]", location="[[Dock]]")
                found = self.assertSeverity(project(person, inn, dock, siege, wedding), "TWO_PLACES", "FAIL")
                self.assertIn("Dock", found[0]["detail"])
                self.assertIn("Inn", found[0]["detail"])
        wedding = item("Wedding", date="2020-01-05", participants="[[P]]", location="[[Dock]]")
        self.assertSeverity(project(person, inn, dock, siege, wedding), "TWO_PLACES", None)

    def test_two_places_sweep_is_fast_for_coarse_overlaps(self):
        # One hero in 3,000 scenes all dated "2036" across 30 places: no clash is certain, so no pairwise work.
        items = [item("Hero", "character", born="2000")] + [item(f"L{n}", "location") for n in range(30)]
        items += [item(f"E{n}", date="2036", participants="[[Hero]]", location=f"[[L{n % 30}]]") for n in range(3000)]
        p = project(*items)
        start = time.perf_counter()
        found = checks.run(p)
        elapsed = time.perf_counter() - start
        self.assertEqual(found, [])
        self.assertLess(elapsed, 2, f"3,000 coarse scenes checked in {elapsed:.3f}s")

    def test_end_before_start(self):
        for start, end, expected in (("2020-05-10", "2020-05-01", "FAIL"), ("2020-05-10", "2020-05", "WARN"),
                                     ("2020-05-10", "2020-05-10", None), ("2020-05", "2020-05-10", None),
                                     ("2020-05-10 10:00", "2020-05-10 09:59", "FAIL")):
            with self.subTest(start=start, end=end):
                event = item("Journey", date=start, end=end)
                found = self.assertSeverity(project(event), "END_BEFORE_START", expected)
                if found:
                    self.assertEqual((found[0]["path"], found[0]["line"]), (event.path, event.line("end")))
        ghost = item("Ghost", "character", born="1990", died="1980")
        f = self.assertSeverity(project(ghost), "END_BEFORE_START", "FAIL")[0]
        self.assertEqual(f["line"], ghost.line("died"))
        self.assertSeverity(project(item("Ghost", "character", born="1990", died="1980 (provisional)")),
                            "END_BEFORE_START", "WARN")
        # Ends that come from a duration or from the start itself are never reported.
        for fields in ({"date": "2020-05-10"}, {"date": "~2020", "duration": "1d"}, {"date": "2020-05-10", "duration": "-2d"},
                       {"born": "1990"}, {"date": "2020-05-10", "end": "nonsense"}):
            with self.subTest(fields=fields):
                self.assertSeverity(project(item("X", **fields)), "END_BEFORE_START", None)

    def test_lone_date_bound_leaves_an_item_undated(self):
        y = item("Y", date="2023")
        for bound in ("date_min", "date_max"):
            with self.subTest(bound=bound):
                x = item("X", after="[[Y]]", **{bound: "2020"})
                p = project(x, y)
                self.assertEqual(item_dates(p, x)[:2], (None, None))
                self.assertSeverity(p, "DEPENDENCY", None)
                self.assertSeverity(p, "DEPENDENCY_UNDATED", "WARN")
        # Both bounds still make the interval; a lone bound still narrows a stated date.
        x = item("X", date_min="2024", date_max="2025", after="[[Y]]")
        p = project(x, y)
        self.assertEqual(show_when(p, item_dates(p, x)[0])["from"], "2024")
        self.assertEqual(item_dates(p, x)[0].hi, dates.parse("2025", p.calendars).hi)
        self.assertSeverity(p, "DEPENDENCY", None)
        x = item("X", date="2020", date_min="2020-06")
        p = project(x)
        self.assertEqual(item_dates(p, x)[0].lo, dates.parse("2020-06", p.calendars).lo)
        x = item("X", date_min="2025", date_max="2024")
        self.assertEqual(item_dates(project(x), x)[2], [("date_max", "2024 is before date_min 2025")])

    def test_max_age_none_at_project_level(self):
        person = item("M", "character", born="1800")
        event = item("E", date="2025", participants="[[M]]")
        for setting in ("none", None, "unlimited"):
            with self.subTest(setting=setting):
                self.assertSeverity(project(person, event, checks={"max_age": setting}), "AGE_LIMIT", None)
        own = item("M", "character", born="1800", max_age="150")
        self.assertSeverity(project(own, event, checks={"max_age": "none"}), "AGE_LIMIT", "FAIL")

    def test_max_duration_vectors_and_selection(self):
        rule = {"rule": "max_duration", "max": "1d", "select": {"type": "event", "tag": "duel", "rail": "A"}}
        for end, expected in (("2020-01-03 00:00", "FAIL"), ("2020-01-02", "WARN"),
                              ("2020-01-01 23:59", None)):
            event = item("E", date="2020-01-01 00:00", end=end, tags=["duel"], rail="A")
            self.assertSeverity(project(event, rules=[rule]), "MAX_DURATION", expected)
        # Exactly the maximum is allowed; one possible minute more is a warning.
        for fields, expected in (({"duration": "1d"}, None), ({"end": "2020-01-02 00:00"}, None),
                                 ({"end": "2020-01-02 00:01"}, "FAIL"), ({"end": "~2020-01-02 00:00"}, "WARN")):
            with self.subTest(fields=fields):
                event = item("E", date="2020-01-01 00:00", **fields)
                self.assertSeverity(project(event, rules=[{"rule": "max_duration", "max": "1d"}]), "MAX_DURATION", expected)
        duel = item("Duel", date="2020-01-01 10:00", end="2020-01-02 10:00")
        self.assertSeverity(project(duel, rules=[{"rule": "max_duration", "max": "1d"}]), "MAX_DURATION", None)
        for fields in ({"tags": ["other"], "rail": "A"}, {"tags": "duel", "rail": "B"},
                       {"type": "chapter", "tags": "duel", "rail": "A"}):
            event = item("E", date="2020-01-01", end="2020-02-01", **fields)
            self.assertEqual(checks.run(project(event, rules=[rule])), [])

    def test_month_max_duration_uses_shifted_start_extrema(self):
        for end, expected in (("2023-02-28 12:00", "WARN"),
                              ("2023-03-01 00:00", "FAIL"),
                              ("2023-02-27 23:59", None)):
            with self.subTest(end=end):
                event = item("E", date="2023-01-30 23:00..2023-01-31 01:00", end=end)
                self.assertSeverity(project(event, rules=[{"rule": "max_duration", "max": "1mo"}]),
                                    "MAX_DURATION", expected)

    def test_gap_exact_min_max_from_start_and_end(self):
        y = item("Y", date="2020-01-01 00:00", end="2020-01-03 00:00")
        for origin, target in (("start", 8), ("end", 10)):
            for bound in ("exactly", "min", "max"):
                wrong = target + (1 if bound == "max" else -1)
                for value, expected in ((f"2020-01-{wrong:02} 00:00", "FAIL"),
                                        (f"2020-01-{target:02}", "WARN"),
                                        (f"2020-01-{target:02} 00:00", None)):
                    with self.subTest(origin=origin, bound=bound, date=value):
                        # For min, uncertainty must straddle the target, not start at it.
                        if bound == "min" and expected == "WARN":
                            value = f"~2020-01-{target:02} 00:00"
                        x = item("X", date=value, paired="[[Y]]")
                        rule = {"rule": "gap", "role": "paired", bound: "7d", "from": origin}
                        self.assertSeverity(project(x, y, rules=[rule]), "GAP", expected)

    def test_monotonic_numeric_order_groups_and_uncertainty(self):
        rule = {"rule": "monotonic", "order": "chapter", "group": "rail"}
        for date, expected in (("2019", "FAIL"), ("2020", "WARN"), ("2021", None)):
            a = item("A", date="2020-06-01 00:00", chapter="2", rail="main")
            b = item("B", date=date, chapter="10", rail="main")
            other = item("Other", date="1800", chapter="11", rail="side")
            bad = item("Bad", date="1800", chapter="invalid", rail="main")
            self.assertSeverity(project(b, other, bad, a, rules=[rule]), "ORDER_REGRESSION", expected)
        a = item("A", date="2020", chapter="1")
        b = item("B", date="1900..2100", chapter="2")
        c = item("C", date="2000", chapter="3")
        found = findings(project(a, b, c, rules=[rule]), "ORDER_REGRESSION")
        self.assertEqual([(f["path"], f["severity"]) for f in found], [("B.md", "WARN"), ("C.md", "FAIL")])
        c = item("C", date="1900", chapter="1.0")
        self.assertEqual(checks.run(project(a, c, rules=[rule])), [])

    def test_monotonic_keeps_the_worst_severity(self):
        # A wide peer (B, all of 2020) must not hide the regression against A (June 2020).
        rule = {"rule": "monotonic", "order": "n"}
        a, b = item("A", date="2020-06-01", n="1"), item("B", date="2020", n="1")
        c = item("C", date="2020-05-01..2020-07-31", n="2")
        for peers in ((a, c), (a, b, c), (b, a, c)):
            with self.subTest(peers=[i.name for i in peers]):
                found = self.assertSeverity(project(*peers, rules=[rule]), "ORDER_REGRESSION", "WARN")
                self.assertIn("; A (", found[0]["detail"])

    def test_monotonic_provisional_predecessor_keeps_committed_evidence(self):
        rule = {"rule": "monotonic", "order": "chapter"}
        for fields in ({"date": "2030", "status": "provisional"},
                       {"date": "2030 (provisional)"},
                       {"date": "2030", "end": "2031 (provisional)"}):
            with self.subTest(fields=fields):
                a = item("A", date="2020", chapter="1")
                b = item("B", chapter="2", **fields)
                c = item("C", date="2010", chapter="3")
                found = self.assertSeverity(project(a, b, c, rules=[rule]), "ORDER_REGRESSION", "FAIL")
                self.assertEqual(found[0]["path"], "C.md")
                self.assertIn("; A (", found[0]["detail"])

    def test_custom_codes_and_rule_severity_caps(self):
        a = item("A", date="2020", chapter="1")
        b = item("B", date="2000", end="2002", chapter="2", paired="[[A]]")
        rules = [{"rule": "monotonic", "order": "chapter", "code": "RAIL_REGRESSION"},
                 {"rule": "max_duration", "max": "1d", "select": {"canonical_name": "B"}, "code": "LONG"},
                 {"rule": "gap", "role": "paired", "min": "7d", "code": "SHORT"}]
        for rule in rules:
            self.assertSeverity(project(a, b, rules=[rule]), rule["code"], "FAIL")
            self.assertSeverity(project(a, b, rules=[{**rule, "severity": "warn"}]), rule["code"], "WARN")

    def test_story_order_counts_only_first_mentions_of_narrative_items(self):
        chapter1, chapter2 = item("Chapter 1", "chapter", date="2025-04-01"), item("Chapter 2", "chapter", date="2025-04-10")
        mira, harbour = item("Mira Vale", "character", born="1995-02-11"), item("Harbour", "location")
        flood = item("Flood", date="1990")
        text = ("- [[Chapter 1]]: [[Mira Vale]] arrives\n- [[Chapter 2]]: [[Mira Vale]] leaves [[Harbour]] "
                "after the [[Flood]]\n- back to [[Chapter 1]]")
        with patch("lorekeeper.checks.open", mock_open(read_data=text)):
            self.assertEqual(checks.run(project(chapter1, chapter2, mira, harbour, flood, checks={"story_order": True})), [])
        # Any type whose category is narrative takes part (a series' books, a campaign's sessions).
        book = item("Book", "book", date="2000")
        with patch("lorekeeper.checks.open", mock_open(read_data="[[Chapter 1]] [[Book]]")):
            found = self.assertSeverity(project(chapter1, book, checks={"story_order": True},
                                                types={"book": {"category": "narrative"}}), "STORY_ORDER", "WARN")
            self.assertEqual(found[0]["path"], "Book.md")

    def test_story_order_opt_in_definite_only_and_fileless_projects(self):
        a = item("A", "chapter", date="2020")
        b = item("B", "chapter", date="1900..2100")
        c = item("C", "chapter", date="2000")
        source = mock_open(read_data="[[A|First]]\n[[Unknown]] [[ ]] [[B]]\n[[C]]")
        with patch("lorekeeper.checks.open", source):
            self.assertEqual(checks.run(project(a, b, c)), [])
            source.assert_not_called()
            found = self.assertSeverity(project(a, b, c, checks={"story_order": True}), "STORY_ORDER", "WARN")
            self.assertEqual(found[0]["path"], "C.md")
            source.assert_called_once_with(os.path.join(ROOT, "narrative.md"), encoding="utf-8")
        with patch("lorekeeper.checks.open", side_effect=FileNotFoundError):
            self.assertEqual(checks.run(project(a, checks={"story_order": True})), [])

    def test_finding_schema_lines_and_formatted_dates(self):
        y = item("Other", date="2020-02-01 12:00")
        x = item("Subject", date="2020-01-01 12:00", after="[[Other]]")
        p = project(x, y)
        f = self.assertSeverity(p, "DEPENDENCY", "FAIL")[0]
        self.assertEqual(set(f), {"severity", "code", "detail", "path", "line"})
        self.assertEqual((f["path"], f["line"]), (x.path, x.line("after")))
        for i in (x, y):
            self.assertIn(i.name, f["detail"])
            self.assertIn(show_when(p, item_dates(p, i)[0])["from"], f["detail"])
        x = item("X", start="2020", chapter="1")
        y = item("Y", start="2000", chapter="2")
        p = project(x, y, rules=[{"rule": "monotonic", "order": "chapter"}])
        f = self.assertSeverity(p, "ORDER_REGRESSION", "FAIL")[0]
        self.assertEqual((f["path"], f["line"]), (y.path, y.line("start")))

    def test_3000_in_memory_items_check_under_two_seconds(self):
        items = []
        for n in range(1000):
            items.extend((item(f"P{n}", "character", born="1900"), item(f"L{n}", "location"),
                          item(f"E{n}", date=f"2020-{1 + n % 12:02}-{1 + n % 28:02} 12:00",
                               duration="1h", participants=f"[[P{n}]]", location=f"[[L{n}]]")))
        shared = [item("P", "character"), item("L", "location")]
        shared.extend(item(f"E{n}", date="2020-01-01", participants="[[P]]", location="[[L]]")
                      for n in range(2998))
        for name, case in (("separate people", items), ("shared person", shared)):
            with self.subTest(case=name):
                self.assertEqual(len(case), 3000)
                p = project(*case)
                start = time.perf_counter()
                found = checks.run(p)
                elapsed = time.perf_counter() - start
                self.assertEqual(found, [])
                self.assertLess(elapsed, 2, f"3,000 items ({name}) checked in {elapsed:.3f}s")

    def test_fixture_world(self):
        # Keep even the disposable fixture copy inside the authorized repository.
        with tempfile.TemporaryDirectory(dir=ROOT) as tmp:
            root = os.path.join(tmp, "world")
            shutil.copytree(FIXTURE, root)
            found = checks.run(Project(root))
        self.assertIn(("PARENT_AGE", "FAIL", "Characters/Ivo Brandt.md"),
                      {(f["code"], f["severity"], f["path"]) for f in found})
        self.assertFalse(any(f["code"] == "DEPENDENCY" and f["path"] == "Events/Crossing Harrow Pass.md" for f in found))


if __name__ == "__main__":
    unittest.main()


class OrderCheck(unittest.TestCase):
    def test_same_day_is_not_a_regression_but_earlier_is(self):
        from lorekeeper import checks, dates
        cals = dates.calendars(None)
        day, year, before = (dates.parse(t, cals) for t in ("2036-11-20", "2036", "2036-11-19"))
        self.assertIsNone(checks.order_check(day, day))
        self.assertEqual(checks.order_check(year, day), "WARN")       # the later card might start in January
        self.assertEqual(checks.order_check(before, day), "FAIL")


class AgelessPeople(unittest.TestCase):
    def test_max_age_override(self):
        from lorekeeper import checks
        from lorekeeper.store import Item, Project
        def world(max_age):
            extra = {"max_age": max_age} if max_age else {}
            people = Item.from_fields("Elder.md", {"id": "E", "type": "character", "canonical_name": "Elder",
                                                   "born": "~3000 BC", **extra})
            event = Item.from_fields("Meet.md", {"id": "M", "type": "event", "canonical_name": "Meet",
                                                 "date": "2036-11-20", "participants": ["[[Elder]]"]})
            return [f["code"] for f in checks.run(Project.from_items(".", {}, [people, event]))]
        self.assertIn("AGE_LIMIT", world(None))
        self.assertNotIn("AGE_LIMIT", world("none"))
        self.assertNotIn("AGE_LIMIT", world("6000"))
