"""The user's three saga Wikis are Lorekeeper projects as they stand (skipped where absent).

Reads only; every write goes to a temp copy.
"""
import glob
import os
import shutil
import tempfile
import unittest

from lorekeeper import fm
from lorekeeper.store import Project

SAGAS = os.environ.get("LORE_SAGAS", r"C:\Users\Owner\OneDrive\Documents\Creative writing")
WIKIS = sorted(glob.glob(os.path.join(SAGAS, "*", "Wiki")))


@unittest.skipUnless(WIKIS, "saga Wikis not present on this machine")
class SagaWikis(unittest.TestCase):
    def test_every_page_round_trips_byte_identical(self):
        with tempfile.TemporaryDirectory() as tmp:
            for wiki in WIKIS:
                copy = os.path.join(tmp, os.path.basename(os.path.dirname(wiki)))
                shutil.copytree(wiki, copy)
                for path in glob.glob(os.path.join(copy, "**", "*.md"), recursive=True):
                    with open(path, "rb") as fh:
                        data = fh.read()
                    text = data.decode("utf-8")
                    self.assertEqual(fm.update(text).encode("utf-8"), data, path)
                    front = fm.parse(text)
                    if front and front.fields:
                        key = next(iter(front.fields))
                        edited = fm.update(text, set={key: front.fields[key]})
                        self.assertEqual(edited, text, f"no-op set changed {path}")

    def test_every_wiki_loads_without_parser_failures(self):
        for wiki in WIKIS:
            p = Project(wiki, {})
            self.assertGreater(len(p.items), 10, wiki)
            parser = [f for f in p.findings()
                      if f["code"] in ("BAD_FRONTMATTER", "BAD_ENCODING", "UNSUPPORTED_FRONTMATTER")]
            self.assertEqual(parser, [], wiki)


if __name__ == "__main__":
    unittest.main()
