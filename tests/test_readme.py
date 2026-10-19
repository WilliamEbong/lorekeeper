"""Execute the published quickstart in a fresh, empty story folder."""
import json
from pathlib import Path
import re
import shlex
import tempfile
import unittest

from lorekeeper import ops
from tests.test_cli import REPO, lore


class Readme(unittest.TestCase):
    def test_quickstart_verbatim(self):
        readme = Path(REPO, "README.md").read_text(encoding="utf-8")
        section = re.search(r"(?m)^## Quickstart\s*\n([\s\S]*?)(?=^## |\Z)", readme)
        self.assertIsNotNone(section, "README needs a Quickstart section")
        blocks = re.findall(r"```bash\n(.*?)\n```", section[1], re.S)
        self.assertEqual(len(blocks), 1, "Quickstart needs one executable bash block")
        lines = blocks[0].splitlines()
        self.assertEqual(lines[0], "lore init --template novel")
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(list(Path(root).iterdir()), [])
            for line in lines:
                with self.subTest(command=line):
                    self.assertTrue(line.startswith("lore "), "Only lore commands belong in the block")
                    args = shlex.split(line)
                    result = lore(*args[1:], cwd=root)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            result = lore("check", "--json", cwd=root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout), {"findings": [], "fail": 0, "warn": 0})

    def test_agent_reference_covers_the_operations_and_parameters(self):
        guide = Path(REPO, "lorekeeper", "agent-skill.md").read_text(encoding="utf-8")
        rows = re.findall(r"(?m)^\| `([^`]+)` \| ([^|]+) \| ([^|]+) \| (.+) \|$", guide)
        reference = {name: (required, optional, example) for name, required, optional, example in rows}
        self.assertEqual(set(reference), {op.name for op in ops.OPS})
        for op in ops.OPS:
            required, optional, example = reference[op.name]
            self.assertEqual(re.findall(r"`([^`]+)`", required), [p.name for p in op.params if p.required])
            self.assertEqual(re.findall(r"`([^`]+)`", optional), [p.name for p in op.params if not p.required])
            self.assertIn("lore " + op.name, example)


if __name__ == "__main__":
    unittest.main()
