import os
import tempfile
import time
import unittest

from lorekeeper import ops
from lorekeeper.store import Project


def synthetic(root, n=3000):
    """n items: a third characters, a third places, a third events linking both."""
    for i in range(n):
        kind = ("character", "location", "event")[i % 3]
        folder = os.path.join(root, kind)
        os.makedirs(folder, exist_ok=True)
        extra = ""
        if kind == "event":
            extra = (f'date: {1900 + i % 120}-{1 + i % 12:02d}-{1 + i % 28:02d}\n'
                     f'location: "[[Place {i - 2}]]"\nparticipants: ["[[Person {i - 1}]]", "[[Person {i - 4}]]"]\n')
        name = {"character": "Person", "location": "Place", "event": "Event"}[kind]
        with open(os.path.join(folder, f"{name} {i}.md"), "w", encoding="utf-8") as fh:
            fh.write(f"---\nid: X-{i}\ntype: {kind}\ncanonical_name: {name} {i}\n{extra}---\n\n# {name} {i}\n\nText.\n")


class Perf(unittest.TestCase):
    def test_3000_items_load_under_1_5s(self):
        with tempfile.TemporaryDirectory() as root:
            synthetic(root)
            start = time.perf_counter()
            p = Project(root)
            elapsed = time.perf_counter() - start
            self.assertEqual(len(p.items), 3000)
            self.assertLess(elapsed, 1.5, f"load took {elapsed:.2f}s")

    def test_3000_items_check_under_2s(self):
        with tempfile.TemporaryDirectory() as root:
            synthetic(root)
            p = Project(root)
            start = time.perf_counter()
            ops.run("check", {}, project=p)
            elapsed = time.perf_counter() - start
            self.assertLess(elapsed, 2.0, f"check took {elapsed:.2f}s")


if __name__ == "__main__":
    unittest.main()
