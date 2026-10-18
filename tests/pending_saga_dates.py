"""Every chapter-card date in the three saga architectures parses (skipped where the sagas are absent)."""
import glob
import json
import os
import re
import unittest

from lorekeeper import dates

SAGAS = os.environ.get("LORE_SAGAS", r"C:\Users\Owner\OneDrive\Documents\Creative writing")
SRD = {"id": "srd", "type": "days", "year_days": 365, "epoch": "6842-01-01", "epoch_year": 0,
       "display_year_offset": 6842, "display": "{display_year} CE, Day {day:03}",
       "formats": [r"SRD Y(?P<year>-?\d+) D(?P<day>\d+)",
                   r"(?P<display_year>-?\d+) CE, Day (?P<day>\d+)(?:, (?P<hour>\d\d):(?P<minute>\d\d))?"]}
CALENDARS = {"Space saga": [SRD]}
FIELD = re.compile(r"^\*\*Date(?:/era)?:\*\*[ \t]*(.+?)[ \t]*$", re.M)


def architecture(saga_dir):
    with open(os.path.join(saga_dir, "PROJECT_MANIFEST.json"), encoding="utf-8") as fh:
        auth = json.load(fh)["authorities"]
    rel = auth.get("architecture") or next(v for k, v in auth.items() if "arch" in k.lower())
    return os.path.join(saga_dir, rel)


SAGA_DIRS = sorted(d for d in glob.glob(os.path.join(SAGAS, "*")) if os.path.isfile(os.path.join(d, "PROJECT_MANIFEST.json")))


@unittest.skipUnless(SAGA_DIRS, "sagas not present on this machine")
class SagaCardDates(unittest.TestCase):
    def test_all_card_dates_parse(self):
        report = []
        total = 0
        for saga in SAGA_DIRS:
            cals = dates.calendars(CALENDARS.get(os.path.basename(saga)))
            with open(architecture(saga), encoding="utf-8") as fh:
                text = fh.read()
            for m in FIELD.finditer(text):
                total += 1
                if dates.parse(m[1], cals) is None:
                    report.append(f"{os.path.basename(saga)}: {m[1]}")
        self.assertGreater(total, 1400)
        self.assertEqual(report, [], f"{len(report)}/{total} unparsed")

    def test_srd_round_trip_and_display(self):
        cal = dates.calendars([SRD])[0]
        w = dates.parse("SRD Y0 D004 (PROVISIONAL production calendar)", [cal])
        self.assertTrue(w.provisional)
        self.assertEqual(cal.format(w.lo, "day"), "6842 CE, Day 004")
        self.assertEqual(dates.parse("6842 CE, Day 004", [cal]).lo, w.lo)
        self.assertEqual(cal.format(dates.parse("SRD Y-6 D204", [cal]).lo, "day"), "6836 CE, Day 204")
        self.assertEqual(dates.parse("SRD Y1 D001", [cal]).lo - dates.parse("SRD Y0 D365", [cal]).lo, 1440)


if __name__ == "__main__":
    unittest.main()
