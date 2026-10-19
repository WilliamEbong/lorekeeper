"""Flashbacks in ordered rules, day counts past a year's end, and second lives (reborn)."""
import unittest

from lorekeeper import checks, dates, ops
from lorekeeper.store import Item, Project

SRD = {"id": "srd", "type": "days", "year_days": 365, "epoch": "6842-01-01", "epoch_year": 0,
       "formats": [r"SRD Y(?P<year>-?\d+) D(?P<day>\d+)"]}
RAIL = {"rule": "monotonic", "select": {"type": "card"}, "order": "chapter", "group": "rail", "code": "RAIL_REGRESSION"}


def card(n, date, **extra):
    return Item.from_fields(f"arch#CH{n:03d}", {"id": f"CARD-{n:03d}", "type": "card", "canonical_name": f"Card {n:03d}",
                                                "chapter": str(n), "rail": "A", "date": date, **extra})


def codes(items, **config):
    config = {"types": {"card": {"label": "Card", "plural": "Cards", "category": "narrative"}}, **config}
    return [f["code"] for f in checks.run(Project.from_items(".", config, items))]


class Flashbacks(unittest.TestCase):
    def test_marked_flashback_and_its_continuation_are_not_regressions(self):
        cards = [card(50, "SRD Y0 D164"),
                 card(51, "SRD Y-2 D168 (sanctioned prelude; presented out of chronological order)"),
                 card(52, "SRD Y-2 D168 (seconds after Ch 051)"),
                 card(53, "SRD Y0 D170")]
        self.assertEqual(codes(cards, calendars=[SRD], rules=[RAIL]), [])

    def test_unmarked_regressions_still_fail(self):
        plain = [card(50, "SRD Y0 D164"), card(51, "SRD Y-2 D168"), card(52, "SRD Y0 D170")]
        self.assertEqual(codes(plain, calendars=[SRD], rules=[RAIL]), ["RAIL_REGRESSION"])
        after = [card(50, "SRD Y0 D164"), card(51, "SRD Y-2 D168 (flashback)"), card(52, "SRD Y0 D100")]
        self.assertEqual(codes(after, calendars=[SRD], rules=[RAIL]), ["RAIL_REGRESSION"])   # back on the main line

    def test_flashback_field(self):
        cards = [card(50, "SRD Y0 D164"), card(51, "SRD Y-2 D168", flashback="yes"), card(52, "SRD Y0 D170")]
        self.assertEqual(codes(cards, calendars=[SRD], rules=[RAIL]), [])


class DayOverflow(unittest.TestCase):
    def test_overflow_reads_into_the_next_year(self):
        strict = dates.calendars([SRD])
        loose = dates.calendars([{**SRD, "overflow": True}])
        self.assertIsNone(dates.parse("SRD Y0 D367", strict))
        self.assertEqual(dates.parse("SRD Y0 D367", loose).lo, dates.parse("SRD Y1 D002", loose).lo)
        self.assertEqual(dates.parse("SRD Y1 D378", loose).lo, dates.parse("SRD Y2 D013", loose).lo)
        self.assertIsNone(dates.parse("SRD Y0 D000", loose))


class SecondLives(unittest.TestCase):
    def world(self, event_date):
        person = Item.from_fields("P.md", {"id": "P", "type": "character", "canonical_name": "Ada", "born": "2000",
                                           "died": "2030-03-01", "reborn": "2031-01-01"})
        event = Item.from_fields("E.md", {"id": "E", "type": "event", "canonical_name": "Scene",
                                          "date": event_date, "participants": ["[[Ada]]"]})
        return Project.from_items(".", {}, [person, event])

    def test_second_life_appearances_are_not_after_death(self):
        self.assertNotIn("DEAD_PARTICIPANT", [f["code"] for f in checks.run(self.world("2040-05-05"))])
        self.assertIn("DEAD_PARTICIPANT", [f["code"] for f in checks.run(self.world("2030-06-01"))])   # between lives

    def test_graph_carries_the_second_life(self):
        ada = next(i for i in ops.run("graph", {}, project=self.world("2040-05-05"))["items"] if i["name"] == "Ada")
        self.assertEqual(ada["reborn"]["text"], "2031-01-01")
        self.assertIsInstance(ada["rlo"], int)
        self.assertIn("reborn", ops.run("schema", {}, project=self.world("2040-05-05"))["properties"])


if __name__ == "__main__":
    unittest.main()
