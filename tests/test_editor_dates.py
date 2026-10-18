"""The editor's date maths must agree with the engine. Needs Node.js; skipped without it."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from lorekeeper import dates

JS = Path(__file__).resolve().parents[1] / "lorekeeper" / "editor.js"


@unittest.skipUnless(shutil.which("node"), "Node.js is not installed")
class EditorDateMathsTests(unittest.TestCase):
    def run_js(self, body):
        # Run the editor's own date and tick sections, unchanged, with a small test body.
        source = JS.read_text(encoding="utf-8")
        months = source[source.index("const MONTHS"):source.index("const CATEGORIES")]
        maths = source[source.index("// ---- dates"):source.index("// ---- find")]
        out = subprocess.run(["node", "--input-type=module", "-e", months + maths + body],
                             capture_output=True, text=True, encoding="utf-8", check=True, timeout=60)
        return json.loads(out.stdout)

    def test_formats_match_the_gregorian_calendar(self):
        cal = dates.Calendar({"type": "gregorian"})
        samples = [m * 9973 * 1440 + m * 37 for m in range(-120, 121)] + [0, -1, 1440 * 366]
        js = self.run_js(f"const s = {json.dumps(samples)}; console.log(JSON.stringify(s.map(m => "
                         "['year', 'month', 'day', 'minute'].map(p => [gregorian(m, p), minuteOf(gregorian(m, p))]))));")
        for minute, row in zip(samples, js):
            for precision, (text, first) in zip(("year", "month", "day", "minute"), row):
                with self.subTest(minute=minute, precision=precision):
                    self.assertEqual(text, cal.format(minute, precision))
                    self.assertEqual(first, dates.parse(text, [cal]).lo)

    def test_ticks_fall_on_round_dates(self):
        cals = dates.calendars(None)
        decade = dates.parse("1750", cals).lo, dates.parse("1810", cals).lo
        bc = dates.parse("60 BC", cals).lo, dates.parse("40 AD", cals).lo
        js = self.run_js(f"console.log(JSON.stringify([ticks({list(decade)}, 800).map(t => t.label), "
                         f"ticks({list(bc)}, 800).map(t => t.label)]));")
        self.assertEqual(js[0], ["1750", "1760", "1770", "1780", "1790", "1800", "1810"])
        self.assertEqual(js[1], ["60 BC", "40 BC", "20 BC", "20", "40"])

    def test_drag_shifts_an_end_by_the_same_amount(self):
        js = self.run_js("const d = minuteOf('1784-03-26') - minuteOf('1784-03-21'); console.log(JSON.stringify(["
                         "shiftDate('1784-04-02', 'day', d), shiftDate('1784-11', 'month', minuteOf('1785-01') - minuteOf('1784-11')),"
                         "shiftDate('44 BC', 'year', minuteOf('1 BC') - minuteOf('44 BC')), dateWords('-0043-03-15')]));")
        self.assertEqual(js, ["1784-04-07", "1785-01", "1 BC", "15 March 44 BC"])


if __name__ == "__main__":
    unittest.main()
