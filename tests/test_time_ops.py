import os
import shutil
import tempfile
import unittest

from lorekeeper import ops
from lorekeeper.store import LoreError

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "world")


def run(name, **args):
    return ops.run(name, args, root=FIXTURE)


class TimeOps(unittest.TestCase):
    def test_when_shows_intervals(self):
        r = run("when", item="Crossing Harrow Pass")
        self.assertEqual((r["start"]["from"], r["start"]["to"], r["start"]["precision"]), ("2020-03", "2020-03", "month"))
        circa = run("when", item="Ivo Brandt")["start"]
        self.assertTrue(circa["circa"])
        self.assertEqual((circa["from"], circa["to"]), ("1950", "1952"))

    def test_ages_follow_the_aeon_rule(self):
        self.assertEqual(run("age", item="Mara Quell", at="The flood at Saltmarsh")["text"], "31 years, 7 months")
        self.assertEqual(run("age", item="Ivo Brandt", at="2020-01-01")["status"], "after_death")
        self.assertEqual(run("age", item="Mara Quell", at="1980")["status"], "before_birth")
        ivo = run("age", item="Ivo Brandt", at="The flood at Saltmarsh")
        self.assertEqual((ivo["status"], ivo["years"][1]), ("alive", 69))
        self.assertLess(ivo["years"][0], ivo["years"][1])        # ~1951 gives a range
        with self.assertRaises(LoreError):
            run("age", item="Saltmarsh", at="2020")

    def test_unreadable_at_is_invalid_not_a_missing_item(self):
        for op in ("age", "where", "knows"):
            with self.subTest(op=op), self.assertRaises(LoreError) as caught:
                run(op, item="Mara Quell", at="2025-02-30")
            self.assertEqual((caught.exception.code, caught.exception.message),
                             ("INVALID", "'2025-02-30' is neither a date Lorekeeper can read nor an item name"))
        with self.assertRaises(LoreError) as caught:
            run("timeline", since="next spring")
        self.assertEqual(caught.exception.code, "INVALID")

    def test_timeline_is_chronological(self):
        names = [i["name"] for i in run("timeline")["items"]]
        self.assertEqual(names, ["Ivo Brandt", "Mara Quell", "Tess Varga", "The flood at Saltmarsh",
                                 "Crossing Harrow Pass"])
        self.assertEqual([i["name"] for i in run("timeline", type="event", since="2020")["items"]],
                         ["Crossing Harrow Pass"])

    def test_where_and_knows(self):
        where = run("where", item="Mara Quell", at="2020-06-01")
        self.assertEqual((where["location"], where["event"]), ("Harrow Pass", "Crossing Harrow Pass"))
        self.assertEqual(run("where", item="Mara Quell", at="2019-11-02 22:00")["location"], "Saltmarsh")
        self.assertIsNone(run("where", item="Mara Quell", at="2000")["location"])
        self.assertEqual([k["item"] for k in run("knows", item="Tess Varga", at="2021")["knows"]], ["Ivo Brandt"])
        self.assertEqual(run("knows", item="Tess Varga", at="2019")["knows"], [])

    def test_convert_and_unparsed_dates(self):
        self.assertEqual(run("convert", date="November 2, 2019")["calendars"]["gregorian"]["from"], "2019-11-02")
        self.assertEqual(run("convert", date="March 15, 44 BC, 9:30")["calendars"]["gregorian"],
                         {"from": "0044-03-15 09:30 BC", "to": "0044-03-15 09:30 BC"})
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "w")
            shutil.copytree(FIXTURE, root)
            with open(os.path.join(root, "Events", "Odd.md"), "w", encoding="utf-8") as fh:
                fh.write("---\ntype: event\ncanonical_name: Odd\ndate: sometime soonish\n---\n")
            found = ops.run("check", {}, root=root)["findings"]
            self.assertIn(("DATE_UNPARSED", "Events/Odd.md", 4),
                          {(f["code"], f["path"], f["line"]) for f in found})


if __name__ == "__main__":
    unittest.main()
