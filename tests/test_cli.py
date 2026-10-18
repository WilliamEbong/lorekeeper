import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(REPO, "tests", "fixtures", "world")


def lore(*args, cwd, **kw):
    env = dict(os.environ, PYTHONPATH=REPO)
    return subprocess.run([sys.executable, "-m", "lorekeeper", *args], cwd=cwd, env=env,
                          capture_output=True, encoding="utf-8", stdin=subprocess.DEVNULL, **kw)


class CliFlows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def test_new_world_end_to_end(self):
        self.assertEqual(lore("init", "--name", "Test", cwd=self.root).returncode, 0)
        self.assertEqual(lore("init", cwd=self.root).returncode, 2)   # refuses to overwrite
        r = lore("--json", "create", "character", "Darius Cole", "--field", "born=2001-03-14",
                 "--field", "tags=[sergeant, crossing]", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        made = json.loads(r.stdout)
        self.assertEqual(made["path"], "Characters/Darius Cole.md")
        self.assertEqual(lore("create", "location", "Nullarbor Plain", cwd=self.root).returncode, 0)
        self.assertEqual(lore("create", "event", "First crossing", "--field", "date=2036-11-21 21:28",
                              cwd=self.root).returncode, 0)
        for role, target in (("participants", "Darius Cole"), ("location", "Nullarbor Plain")):
            r = lore("link", "First crossing", role, target, cwd=self.root)
            self.assertEqual(r.returncode, 0, r.stderr)
        shown = json.loads(lore("show", "Darius Cole", "--json", cwd=os.path.join(self.root, "Characters")).stdout)
        self.assertEqual(shown["fields"]["tags"], ["sergeant", "crossing"])
        self.assertEqual(shown["backlinks"], {"Took part in": ["First crossing"]})
        event = json.loads(lore("--json", "show", "First crossing", cwd=self.root).stdout)
        self.assertEqual(event["links"], {"participants": ["Darius Cole"], "location": ["Nullarbor Plain"]})
        with open(os.path.join(self.root, "Events", "First crossing.md"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn('participants: ["[[Darius Cole]]"]\n', text)
        self.assertIn('location: "[[Nullarbor Plain]]"\n', text)
        r = lore("unlink", "First crossing", "participants", "Darius Cole", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("participants", json.loads(lore("--json", "show", "First crossing", cwd=self.root).stdout)["fields"])

    def test_set_with_stale_version_conflict_exit_code(self):
        root = os.path.join(self.root, "w")
        shutil.copytree(FIXTURE, root)
        old = json.loads(lore("--json", "show", "Mara Quell", cwd=root).stdout)["version"]
        self.assertEqual(lore("set", "Mara Quell", "--field", "born=1987", cwd=root).returncode, 0)
        r = lore("--json", "set", "Mara Quell", "--field", "born=1990", "--version", old,
                 "--expect", "born=1988-04-02", cwd=root)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(json.loads(r.stdout)["error"]["code"], "CONFLICT")
        r = lore("--json", "set", "Mara Quell", "--field", "status=locked", "--version", old,
                 "--expect", "status=", cwd=root)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_check_human_output_and_exit_codes(self):
        root = os.path.join(self.root, "w")
        shutil.copytree(FIXTURE, root)
        r = lore("check", cwd=root)
        self.assertEqual(r.returncode, 1)          # the fixture world carries deliberate FAILs
        self.assertIn("FAIL PARENT_AGE", r.stdout)
        self.assertIn("WARN BROKEN_LINK located_in -> [[The Coast]] matches no item Locations/Saltmarsh.md:5", r.stdout)
        shutil.copy(os.path.join(root, "Characters", "Mara Quell.md"), os.path.join(root, "Characters", "Copy.md"))
        r = lore("check", cwd=root)
        self.assertEqual(r.returncode, 1)
        self.assertIn("FAIL DUPLICATE_ID", r.stdout)

    def test_errors_and_usage(self):
        self.assertEqual(lore("show", "x", cwd=self.root).returncode, 2)          # no lore.json
        self.assertIn("ERROR NOT_FOUND", lore("show", "x", cwd=self.root).stderr)
        self.assertEqual(lore("bogus", cwd=self.root).returncode, 2)

    def test_root_must_lead_to_a_project(self):
        root = os.path.join(self.root, "w")
        shutil.copytree(FIXTURE, root)
        missing = os.path.join(self.root, "Mistyped")
        for args in (["check"], ["--json", "check"], ["mcp"], ["serve"]):   # no false all-clear, no idle server
            with self.subTest(args=args):
                r = lore("--root", missing, *args, cwd=root, timeout=30)
                self.assertEqual(r.returncode, 2, r.stdout)
                self.assertIn(f"no lore.json in {missing}", r.stderr)
        self.assertEqual(json.loads(lore("--json", "--root", missing, "check", cwd=root).stdout)["error"]["code"],
                         "NOT_FOUND")
        r = lore("--root", os.path.join(root, "Characters"), "create", "character", "Ghost", cwd=self.root)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(root, "Characters", "Ghost.md")))
        self.assertFalse(os.path.exists(os.path.join(root, "Characters", "Characters")))

    def test_human_output_reads_as_text(self):
        root = os.path.join(self.root, "w")
        shutil.copytree(FIXTURE, root)
        out = lore("timeline", cwd=root).stdout.splitlines()
        self.assertEqual(out[0], "~1951 to 2019-11-03                   character     Ivo Brandt")
        self.assertEqual(out[3], "2019-11-02 21:00 to 2019-11-03 06:00  event         The flood at Saltmarsh")
        self.assertEqual(out[4], "2020-03                               event         Crossing Harrow Pass")
        self.assertEqual(lore("age", "Mara Quell", "Crossing Harrow Pass", cwd=root).stdout,
                         "Mara Quell at Crossing Harrow Pass: 31 years, 10 months\n")
        self.assertEqual(lore("when", "Ivo Brandt", cwd=root).stdout,
                         "Ivo Brandt\nstart: ~1951 (1950 to 1952)\nend: 2019-11-03\n")
        self.assertEqual(lore("where", "Mara Quell", "2021", cwd=root).stdout,
                         "By 2021, Mara Quell was last at Harrow Pass (Crossing Harrow Pass, 2020-03).\n")
        self.assertEqual(lore("where", "Mara Quell", "1990", cwd=root).stdout,
                         "By 1990, Mara Quell has no recorded location.\n")
        self.assertEqual(lore("knows", "Mara Quell", "2021", cwd=root).stdout,
                         "By 2021, Mara Quell knows Ivo Brandt (from Crossing Harrow Pass).\n")
        self.assertEqual(lore("knows", "Tess Varga", "2020-03-15", cwd=root).stdout,
                         "By 2020-03-15, Tess Varga may know Ivo Brandt (from Crossing Harrow Pass).\n")
        self.assertEqual(lore("knows", "Tess Varga", "2000", cwd=root).stdout,
                         "By 2000, Tess Varga has learned nothing on record.\n")
        self.assertEqual(json.loads(lore("show", "Mara Quell", cwd=root).stdout)["name"], "Mara Quell")   # still JSON


if __name__ == "__main__":
    unittest.main()
