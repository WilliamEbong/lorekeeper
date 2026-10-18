"""Date arithmetic and grammar vectors; no external saga files are needed."""

import unittest
from unittest.mock import patch

from lorekeeper import dates


# Copied configuration, rather than importing the parked test: importing it
# scans external saga paths, which this task explicitly forbids.
SRD = {"id": "srd", "type": "days", "year_days": 365, "epoch": "6842-01-01", "epoch_year": 0,
       "display_year_offset": 6842, "display": "{display_year} CE, Day {day:03}",
       "formats": [r"SRD Y(?P<year>-?\d+) D(?P<day>\d+)",
                   r"(?P<display_year>-?\d+) CE, Day (?P<day>\d+)(?:, (?P<hour>\d\d):(?P<minute>\d\d))?",
                   r"SRD Y(?P<year>-?\d+)"]}
FANTASY = {"id": "fantasy", "type": "months", "epoch": "2000-03-01", "epoch_year": 7,
           "months": [{"name": f"Moon{i}", "days": 28} for i in range(1, 13)]
                     + [{"name": "Last", "days": 29, "leap_days": 30}],
           "leap_cycles": [4, 100, 400],
           "formats": [r"F(?P<year>-?\d+)(?:/(?P<month>\d+|Moon\d+|Last)(?:/(?P<day>\d+))?)?(?: (?P<hour>\d+):(?P<minute>\d+))?"]}


class Decades(unittest.TestCase):
    def test_decade_and_leading_label(self):
        cals = dates.calendars(None)
        w = dates.parse("African Collapse Wars, 2040s", cals)
        self.assertEqual((w.lo, w.hi, w.note), (cals[0].to_axis(2040, 1, 1), cals[0].to_axis(2050, 1, 1),
                                                "African Collapse Wars"))
        self.assertIsNone(dates.parse("Wars, sometime", cals))


class CivilTests(unittest.TestCase):
    def test_every_day_minus_1000_through_3000(self):
        start = dates.days_from_civil(-1000, 1, 1)
        stop = dates.days_from_civil(3001, 1, 1)
        for n in range(start, stop):
            y, m, d = dates.civil_from_days(n)
            if dates.days_from_civil(y, m, d) != n:
                self.fail(f"round trip failed at day {n}: {(y, m, d)}")
        self.assertEqual(dates.civil_from_days(start), (-1000, 1, 1))
        self.assertEqual(dates.civil_from_days(stop - 1), (3000, 12, 31))

    def test_known_anchors_and_leaps(self):
        self.assertEqual(dates.days_from_civil(1970, 1, 1), 0)
        self.assertEqual(dates.days_from_civil(1, 1, 1), -719162)
        cal = dates.Calendar({})
        self.assertEqual(cal.to_axis(1, 1, 1), 0)
        self.assertEqual(cal.from_axis(-1), dict(year=0, month=12, day=31, hour=23, minute=59))
        for year, leap in ((1900, False), (2000, True), (2024, True), (2023, False), (0, True), (-100, False)):
            with self.subTest(year=year):
                self.assertEqual(cal.parse(f"{year}-02-29") is not None, leap)
                self.assertEqual((cal.to_axis(year, 3, 1) - cal.to_axis(year, 2, 28)) // 1440, 1 + leap)


class GregorianTests(unittest.TestCase):
    def setUp(self):
        self.cal = dates.Calendar({})

    def test_impossible_dates_stop_all_fallbacks(self):
        srd = dates.Calendar(SRD)
        permissive = dates.Calendar(dict(SRD, id="long", year_days=400))
        for text, cals in (("February 30, 2024", [self.cal]),
                           ("February 30, 2024 (provisional)", [self.cal]),
                           ("6842 CE, Day 366", [srd, self.cal]),
                           ("6842 CE, Day 366", [srd, permissive]),
                           ("2024-01-01..February 30, 2024", [self.cal])):
            with self.subTest(text=text, calendars=[c.id for c in cals]):
                self.assertIsNone(cals[0].parse(text))
                self.assertIsNone(dates.parse(text, cals))
        matched = dates.parse("African Collapse Wars, 2040s", [self.cal])
        self.assertEqual((matched.lo, matched.note),
                         (self.cal.to_axis(2040, 1, 1), "African Collapse Wars"))

    def test_written_date_without_space_after_comma(self):
        for parse in (self.cal.parse, lambda text: dates.parse(text, [self.cal])):
            w = parse("May 3,2071")
            self.assertEqual((w.lo, w.hi, w.precision, w.note),
                             (self.cal.to_axis(2071, 5, 3), self.cal.to_axis(2071, 5, 4), "day", ""))

    def test_invalid_clock_in_note_is_preserved(self):
        for note in ("note 13:00 pm", "note 24:00", "note 12:60"):
            w = dates.parse("March 3, 2071, " + note, [self.cal])
            self.assertEqual((w.lo, w.precision, w.note),
                             (self.cal.to_axis(2071, 3, 3), "day", note))
        self.assertIsNone(dates.parse("March 3, 2071, 13:00 pm", [self.cal]))

    def test_iso_and_written_forms(self):
        cases = (("2036", (2036, 1, 1), "year"),
                 ("2036-11", (2036, 11, 1), "month"),
                 ("2036-11-20", (2036, 11, 20), "day"),
                 ("November 20, 2036", (2036, 11, 20), "day"),
                 ("20 November 2036", (2036, 11, 20), "day"),
                 ("November 2036", (2036, 11, 1), "month"),
                 ("Nov 20, 2036", (2036, 11, 20), "day"),
                 ("Nov. 20, 2036", (2036, 11, 20), "day"),
                 ("Sept 20, 2036", (2036, 9, 20), "day"),
                 ("  sEpT. 20, 2036  ", (2036, 9, 20), "day"),
                 ("7-01-02", (7, 1, 2), "day"),
                 ("12345", (12345, 1, 1), "year"))
        for text, ymd, precision in cases:
            with self.subTest(text=text):
                w = self.cal.parse(text)
                self.assertIsNotNone(w)
                self.assertEqual(w.lo, self.cal.to_axis(*ymd))
                self.assertEqual(w.precision, precision)
                self.assertEqual(w.text, text)
                self.assertEqual(w.calendar, "gregorian")
                self.assertFalse(w.circa)

    def test_precision_bounds(self):
        cases = (("2036", (2036, 1, 1), (2037, 1, 1)),
                 ("2036-02", (2036, 2, 1), (2036, 3, 1)),
                 ("September 2064", (2064, 9, 1), (2064, 10, 1)),
                 ("2024-02-29", (2024, 2, 29), (2024, 3, 1)),
                 ("2024-12-31T23:59", (2024, 12, 31, 23, 59), (2025, 1, 1)))
        for text, lo, hi in cases:
            with self.subTest(text=text):
                w = self.cal.parse(text)
                self.assertEqual((w.lo, w.hi), (self.cal.to_axis(*lo), self.cal.to_axis(*hi)))
        # The supplied grammars have no hour-only form; the interval primitive
        # and formatter still support the public precision vocabulary.
        w = self.cal._interval(2024, 1, 1, 5, 0, "hour")
        self.assertEqual(w.hi - w.lo, 60)

    def test_eras(self):
        for text, ymd in (("44 BC", (-43, 1, 1)), ("44 BCE", (-43, 1, 1)),
                          ("44 AD", (44, 1, 1)), ("44 CE", (44, 1, 1)),
                          ("1 BC", (0, 1, 1)), ("-0043", (-43, 1, 1)),
                          ("March 15, 44 BC", (-43, 3, 15)),
                          ("15 March 44 BCE", (-43, 3, 15)),
                          ("March 15, 44 AD", (44, 3, 15))):
            with self.subTest(text=text):
                self.assertEqual(self.cal.parse(text).lo, self.cal.to_axis(*ymd))

    def test_times(self):
        for suffix, hour in ((" 05:40", 5), ("T05:40", 5), (", 5:40 a.m.", 5),
                             (", 5:40 p.m.", 17), (", 5:40 am", 5), (", 5:40 PM", 17),
                             (", 12:40 a.m.", 0), (", 12:40 p.m.", 12), (", 23:40", 23)):
            with self.subTest(suffix=suffix):
                w = self.cal.parse("2071-03-03" + suffix)
                self.assertEqual(w.lo, self.cal.to_axis(2071, 3, 3, hour, 40))
                self.assertEqual(w.hi - w.lo, 1)
                self.assertEqual(w.precision, "minute")
        w = self.cal.parse("March 15, 44 BC, 12:01 am")
        self.assertEqual(w.lo, self.cal.to_axis(-43, 3, 15, 0, 1))

    def test_circa(self):
        for marker in ("~", "c.", "ca.", "circa", "about", "approximately", "approx.", "around"):
            with self.subTest(marker=marker):
                w = self.cal.parse(marker + " 1951")
                self.assertTrue(w.circa)
                self.assertEqual((w.lo, w.hi), (self.cal.to_axis(1950, 1, 1), self.cal.to_axis(1953, 1, 1)))
                w = self.cal.parse("March 3, 2071, " + marker + " 5:40 a.m.")
                self.assertTrue(w.circa)
                self.assertEqual((w.lo, w.hi), (self.cal.to_axis(2071, 3, 3, 5, 25), self.cal.to_axis(2071, 3, 3, 5, 56)))
        for text, lo, hi in (("~2024-02", (2024, 1, 1), (2024, 4, 1)),
                             ("~2024-02-29", (2024, 2, 28), (2024, 3, 2))):
            w = self.cal.parse(text)
            self.assertEqual((w.lo, w.hi), (self.cal.to_axis(*lo), self.cal.to_axis(*hi)))

    def test_ranges(self):
        for sep in ("-", "\u2013", "\u2014", ".."):
            w = self.cal.parse(f"2045{sep}2047, Taiwan settlement")
            self.assertEqual((w.lo, w.hi), (self.cal.to_axis(2045, 1, 1), self.cal.to_axis(2048, 1, 1)))
            self.assertEqual(w.note, "Taiwan settlement")
            self.assertEqual(w.precision, "year")
        w = self.cal.parse("March 2000..2001-02-03")
        self.assertEqual((w.lo, w.hi), (self.cal.to_axis(2000, 3, 1), self.cal.to_axis(2001, 2, 4)))
        self.assertEqual(w.precision, "month")
        w = self.cal.parse("~2000..2002 (provisional)")
        self.assertTrue(w.circa)
        self.assertTrue(w.provisional)
        self.assertEqual((w.lo, w.hi), (self.cal.to_axis(1999, 1, 1), self.cal.to_axis(2003, 1, 1)))
        self.assertEqual(self.cal.parse("2045-2045").hi, self.cal.to_axis(2046, 1, 1))

    def test_notes(self):
        for text, note, provisional in (("March 2065, framed in 2071", "framed in 2071", False),
                                         ("September 14, 2071 (day-level provisional)", "day-level provisional", True),
                                         ("2045, Open Weights Crisis", "Open Weights Crisis", False),
                                         ("2045; PROVISIONAL", "PROVISIONAL", True),
                                         ("2045 (continuous action)", "continuous action", False),
                                         ("2045, around the world", "around the world", False),
                                         ("2045 (circa 5:40 tomorrow)", "circa 5:40 tomorrow", False)):
            with self.subTest(text=text):
                w = self.cal.parse(text)
                self.assertEqual((w.note, w.provisional), (note, provisional))
                self.assertFalse(w.circa)

    def test_format(self):
        n = self.cal.to_axis(2036, 11, 20, 21, 28)
        for precision, expected in zip(dates.UNITS, ("2036", "2036-11", "2036-11-20", "2036-11-20 21:00", "2036-11-20 21:28")):
            self.assertEqual(self.cal.format(n, precision), expected)
        self.assertEqual(self.cal.format(self.cal.to_axis(-43, 3, 15), "year"), "44 BC")
        self.assertEqual(self.cal.format(self.cal.to_axis(-43, 3, 15), "day"), "-0043-03-15")
        self.assertEqual(self.cal.format(-1), "0000-12-31 23:59")

    def test_unparseable(self):
        for text in (None, "", " ", "nonsense", "2045 garbage", "2045/01/01", "2000-13-01",
                     "2000-00-01", "2000-01-00", "2023-02-29", "February 30, 2024",
                     "2024-01-01 24:00", "2024-01-01 12:60", "2024-01-01 13:00 pm",
                     "2024-01-01, 13:00 pm", "February 30, 2024 (provisional)",
                     "2047-2045", "2045..2044", "2000..2001..2002", "0 BC", "-43 BCE",
                     "2000-123", "2045-1", "Janu 1, 2000"):
            with self.subTest(text=text):
                self.assertIsNone(self.cal.parse(text))

    def test_defaults_and_calendar_order(self):
        for config in (None, []):
            self.assertEqual([c.id for c in dates.calendars(config)], ["gregorian"])
        first, second = dates.Calendar({"id": "first"}), dates.Calendar({"id": "second"})
        self.assertEqual(dates.parse("2000", [first, second]).calendar, "first")
        self.assertIsNone(dates.parse("2000", []))
        cals = dates.calendars([SRD, {}])
        self.assertEqual(dates.parse("2000", cals).calendar, "gregorian")
        self.assertIsNone(cals[0].parse("2000"))


class ArithmeticTests(unittest.TestCase):
    def setUp(self):
        self.cal = dates.Calendar({})

    def test_signed_age_bounds_do_not_depend_on_status(self):
        birth = self.cal.parse("2000..2010")
        at = self.cal.parse("2005-01-01")
        for death, status in ((None, "alive"), (self.cal.parse("2004"), "after_death")):
            result = dates.age(birth, at, death, self.cal)
            self.assertEqual(result["status"], status)
            self.assertEqual(result["years"], [-5, 5])

    def test_durations(self):
        for text, expected in (("2h", (0, 120)), ("45m", (0, 45)), ("45min", (0, 45)),
                               ("3d", (0, 4320)), ("2w", (0, 20160)), ("1y", (12, 0)),
                               ("1y 2mo", (14, 0)), ("7 days", (0, 10080)), ("1 week", (0, 10080)),
                               ("+2d", (0, 2880)), ("-1h", (0, -60)), ("90 minutes", (0, 90)),
                               ("-1y 2mo 3d", (-14, -4320)), (" 2 HR ", (0, 120)), ("0m", (0, 0))):
            self.assertEqual(dates.parse_duration(text), expected, text)
        for aliases, value in (("y yr year years", (12, 0)), ("mo month months", (1, 0)),
                               ("w wk week weeks", (0, 10080)), ("d day days", (0, 1440)),
                               ("h hr hour hours", (0, 60)), ("m min minute minutes", (0, 1))):
            for unit in aliases.split():
                self.assertEqual(dates.parse_duration("1 " + unit), value)
        for text in (None, "", "-", "two days", "1.5h", "1h junk", "1h -2m", "1h +2m", "1x", "1", "1h, 2m"):
            self.assertIsNone(dates.parse_duration(text), text)

    def test_add_month_clamping_and_order(self):
        for year, last in ((2023, 28), (2024, 29)):
            start = self.cal.to_axis(year, 1, 31, 15, 20)
            self.assertEqual(dates.add(start, (1, 0), self.cal), self.cal.to_axis(year, 2, last, 15, 20))
            self.assertEqual(dates.add(start, (1, 1440), self.cal), self.cal.to_axis(year, 3, 1, 15, 20))
        self.assertEqual(self.cal.add_months(self.cal.to_axis(2024, 3, 31), -1), self.cal.to_axis(2024, 2, 29))
        self.assertEqual(self.cal.add_months(0, -1), self.cal.to_axis(0, 12, 1))
        self.assertEqual(self.cal.add_months(self.cal.to_axis(2024, 2, 29), 12), self.cal.to_axis(2025, 2, 28))

    def test_spans(self):
        lo = self.cal.to_axis(2000, 3, 15)
        hi = self.cal.to_axis(2032, 7, 20, 2, 3)
        p = dates.span(lo, hi, self.cal)
        self.assertEqual(p, dict(years=32, months=4, weeks=0, days=5, hours=2, minutes=3))
        self.assertEqual(dates.span_text(p), "32 years, 4 months")
        for delta, text in ((0, "0 minutes"), (1, "1 minute"), (60, "1 hour"),
                            (1440, "1 day"), (10080, "1 week"), (10080 + 1440, "1 week, 1 day")):
            self.assertEqual(dates.span_text(dates.span(lo, lo + delta, self.cal)), text)
        start = self.cal.to_axis(2023, 1, 31)
        self.assertEqual(dates.span(start, self.cal.to_axis(2023, 2, 28), self.cal)["months"], 1)
        self.assertEqual(dates.span(self.cal.to_axis(2020, 2, 29), self.cal.to_axis(2021, 2, 28), self.cal)["years"], 1)
        leap_span = dates.span(self.cal.to_axis(2020, 2, 29), self.cal.to_axis(2024, 2, 28), self.cal)
        self.assertEqual((leap_span["years"], leap_span["months"], leap_span["days"]), (3, 12, 0))
        with self.assertRaises(ValueError):
            dates.span(1, 0, self.cal)

    def test_age_statuses_and_bounds(self):
        birth = self.cal.parse("2000-03-15")
        at = self.cal.parse("2032-07-20")
        self.assertEqual(dates.age(birth, at, None, self.cal),
                         dict(text="32 years, 4 months", status="alive", years=[32, 32]))
        result = dates.age(birth, self.cal.parse("1990-03-15"), None, self.cal)
        self.assertEqual(result, dict(text="10 years before birth", status="before_birth", years=[-10, -9]))
        result = dates.age(birth, at, self.cal.parse("2030-07-20"), self.cal)
        self.assertEqual(result["text"], "2 years after death")
        self.assertEqual(result["status"], "after_death")
        result = dates.age(self.cal.parse("2000"), self.cal.parse("2032-05-01"), None, self.cal)
        self.assertEqual(result, dict(text="32 years, 4 months", status="alive", years=[31, 32]))
        result = dates.age(self.cal.parse("~1951"), self.cal.parse("2000-01-01"), None, self.cal)
        self.assertEqual(result["years"], [47, 50])
        overlap = dates.age(self.cal.parse("2000-06-01"), self.cal.parse("2000"), None, self.cal)
        self.assertEqual(overlap, dict(text="0 minutes", status="alive", years=[0, 0]))
        self.assertEqual(dates.age(birth, birth, birth, self.cal)["text"], "0 minutes after death")


class CustomCalendarTests(unittest.TestCase):
    def test_native_month_count_defines_span_and_age_years(self):
        cal = dates.Calendar(FANTASY)
        birth = cal.parse("F7/1/1 00:00")
        for text, expected, years in (("F7/13/1 00:00", "12 months", 0),
                                      ("F8/1/1 00:00", "1 year", 1)):
            at = cal.parse(text)
            self.assertEqual(dates.span_text(dates.span(birth.lo, at.lo, cal)), expected)
            self.assertEqual(dates.age(birth, at, None, cal),
                             dict(text=expected, status="alive", years=[years, years]))
        self.assertEqual(cal.add_months(birth.lo, 13), cal.to_axis(8, 1, 1))
        self.assertEqual(cal.add_months(birth.lo, -13), cal.to_axis(6, 1, 1))

    def test_custom_hour_without_minute_has_hour_precision(self):
        cal = dates.Calendar(dict(SRD, formats=[
            r"SRD Y(?P<year>-?\d+) D(?P<day>\d+) H(?P<hour>\d+)(?::(?P<minute>\d+))?"]))
        for suffix, precision, width in (("H5", "hour", 60), ("H5:00", "minute", 1)):
            w = cal.parse("SRD Y0 D004 " + suffix)
            self.assertEqual((w.lo, w.precision, w.hi - w.lo),
                             (cal.to_axis(0, 1, 4, 5), precision, width))

    def test_display_template_time_is_not_duplicated(self):
        for display, expected in (("{display_year} CE, Day {day:03}, {hour:02}:{minute:02}",
                                    "6842 CE, Day 004, 20:33"),
                                   ("{year}/{day} H{hour}", "0/4 H20"),
                                   ("{year}/{day} M{minute}", "0/4 M33")):
            cal = dates.Calendar(dict(SRD, display=display))
            self.assertEqual(cal.format(cal.to_axis(0, 1, 4, 20, 33)), expected)

    def test_distant_month_years_use_bounded_work_and_storage(self):
        for cycles, offset in (([4, 100, 400], 0), ([4, 100, 400], 1), ([], 0)):
            cal = dates.Calendar(dict(FANTASY, leap_cycles=cycles, leap_offset=offset))
            with patch.object(cal, "_lengths", wraps=cal._lengths) as lengths:
                for year in (-999993, 1000007):
                    w = cal.parse(f"F{year}/1/1")
                    elapsed = (dates.days_from_civil(year - offset, 1, 1)
                               - dates.days_from_civil(7 - offset, 1, 1)
                               if cycles else (year - 7) * 365)
                    self.assertEqual(w.lo, (cal.epoch_day + elapsed) * 1440)
                    self.assertEqual(cal.from_axis(w.lo)["year"], year)
                    self.assertEqual(cal.from_axis(w.lo - 1)["year"], year - 1)
                self.assertLess(lengths.call_count, 20)
            self.assertEqual(len(cal.year_starts), max(cycles, default=1) + 1)

    def test_srd_parked_vectors(self):
        cal = dates.calendars([SRD])[0]
        w = dates.parse("SRD Y0 D004 (PROVISIONAL production calendar)", [cal])
        self.assertTrue(w.provisional)
        self.assertEqual(cal.format(w.lo, "day"), "6842 CE, Day 004")
        self.assertEqual(dates.parse("6842 CE, Day 004", [cal]).lo, w.lo)
        self.assertEqual(cal.format(dates.parse("SRD Y-6 D204", [cal]).lo, "day"), "6836 CE, Day 204")
        self.assertEqual(dates.parse("SRD Y1 D001", [cal]).lo - dates.parse("SRD Y0 D365", [cal]).lo, 1440)

    def test_days_times_notes_and_bounds(self):
        cal = dates.Calendar(SRD)
        w = cal.parse("6842 CE, Day 004, 20:33 (continuous action)")
        self.assertEqual(w.note, "continuous action")
        self.assertEqual(w.hi - w.lo, 1)
        self.assertEqual(cal.format(w.lo), "6842 CE, Day 004, 20:33")
        self.assertEqual(cal.from_axis(w.lo), dict(year=0, display_year=6842, month=1, day=4, hour=20, minute=33))
        w = cal.parse("circa 6842 CE, Day 004, approximately 20:33")
        self.assertTrue(w.circa)
        self.assertEqual(w.hi - w.lo, 31)
        self.assertEqual(cal.parse("~SRD Y0 D004").hi - cal.parse("~SRD Y0 D004").lo, 3 * 1440)
        self.assertEqual(cal.parse("SRD Y0").hi - cal.parse("SRD Y0").lo, 365 * 1440)
        self.assertEqual(cal.parse("~SRD Y0").hi - cal.parse("~SRD Y0").lo, 3 * 365 * 1440)
        for text in ("SRD Y0 D000", "SRD Y0 D366", "SRD Y0 D004 junk", "6842 CE, Day 004 24:00"):
            self.assertIsNone(cal.parse(text), text)
        for year in (-100000, -6, -1, 0, 1, 100000):
            for day in (1, 204, 365):
                n = cal.to_axis(year, 1, day, 23, 59)
                self.assertEqual(cal.parse(cal.format(n)).lo, n)

    def test_days_month_convention(self):
        cal = dates.Calendar(SRD)
        n = cal.to_axis(0, 1, 365)
        for months, days in ((12, 365), (24, 730), (-12, -365), (1, 30), (-1, -30), (13, 390)):
            self.assertEqual(cal.add_months(n, months) - n, days * 1440)
        p = dates.span(n, n + (365 + 60 + 8) * 1440 + 61, cal)
        self.assertEqual(p, dict(years=1, months=2, weeks=1, days=1, hours=1, minutes=1))
        plain = dates.Calendar({"type": "days", "year_days": 360, "epoch": "0001-01-01"})
        self.assertEqual(plain.format(-1, "day"), "Y-1 D360")
        self.assertNotIn("display_year", plain.from_axis(0))
        long_year = dates.Calendar({"type": "days", "year_days": 1000, "epoch": "0001-01-01"})
        self.assertEqual(dates.span(0, 400 * 1440, long_year)["months"], 13)

    def test_thirteen_month_round_trips(self):
        cal = dates.Calendar(FANTASY)
        self.assertEqual(cal.to_axis(7, 1, 1), dates.Calendar({}).to_axis(2000, 3, 1))
        for n in range(cal.to_axis(-5, 1, 1) // 1440, cal.to_axis(12, 1, 1) // 1440):
            p = cal.from_axis(n * 1440 + 1439)
            self.assertEqual(cal.to_axis(**p), n * 1440 + 1439)
        for year in (-99993, 100007):
            n = cal.to_axis(year, 13, 29, 12, 34)
            self.assertEqual(cal.from_axis(n), dict(year=year, month=13, day=29, hour=12, minute=34))
        self.assertEqual(cal.parse("F8/Last/30").lo, cal.to_axis(8, 13, 30))
        self.assertEqual(cal.parse("F8/moon1/2").lo, cal.to_axis(8, 1, 2))
        self.assertEqual(cal.parse("F8/13/30 12:34").hi - cal.parse("F8/13/30 12:34").lo, 1)
        self.assertEqual(cal.format(cal.to_axis(8, 13, 30), "day"), "8-13-30")
        self.assertEqual(cal.parse("F8").hi - cal.parse("F8").lo, 366 * 1440)
        self.assertEqual(cal.parse("F8/13").hi - cal.parse("F8/13").lo, 30 * 1440)
        self.assertEqual(cal.add_months(cal.to_axis(8, 13, 30), 1), cal.to_axis(9, 1, 28))
        self.assertEqual(cal.add_months(cal.to_axis(8, 13, 30), 13), cal.to_axis(9, 13, 29))

    def test_custom_leap_rules(self):
        cal = dates.Calendar(FANTASY)
        for year, leap in ((1900, False), (2000, True), (2024, True), (2023, False), (-400, True)):
            self.assertEqual(cal.parse(f"F{year}/Last/30") is not None, leap)
        shifted = dates.Calendar(dict(FANTASY, leap_cycles=[4, 100, 400], leap_offset=1))
        for year, leap in ((1901, False), (2001, True), (2025, True), (2024, False)):
            self.assertEqual(shifted.parse(f"F{year}/Last/30") is not None, leap)
        for text in ("F7/Last/30", "F7/14/1", "F7/Unknown/1", "F7/1/0", "F7/1/1 24:00"):
            self.assertIsNone(cal.parse(text), text)


if __name__ == "__main__":
    unittest.main()
