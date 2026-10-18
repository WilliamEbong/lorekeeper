"""Starter worlds, init compatibility, and packaging declarations."""
import copy
import json
from pathlib import Path
import tempfile
import tomllib
import unittest

from lorekeeper import mcp, ops, store, templates
from tests.test_cli import REPO, lore


class Templates(unittest.TestCase):
    def test_all_templates_pass_cli_check_and_have_resolved_links(self):
        for template in ("novel", "series", "campaign"):
            with self.subTest(template=template), tempfile.TemporaryDirectory() as root:
                result = lore("init", "--template", template, "--name", "My World", cwd=root)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                result = lore("check", "--json", cwd=root)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout), {"findings": [], "fail": 0, "warn": 0})
                p = store.Project(root)
                self.assertEqual(p.config["name"], "My World")
                self.assertGreaterEqual(len(p.items), 6)
                self.assertTrue(p.links(p.find("The Letter"))["participants"])
                for item in p.items:
                    for links in p.links(item).values():
                        self.assertTrue(all(other is not None for _, other, _ in links))
                narrative = Path(root, "narrative.md").read_text(encoding="utf-8")
                self.assertIn("[[Session 1]]" if template == "campaign" else "[[Chapter 1]]", narrative)
                if template == "campaign":
                    self.assertTrue({"faction", "session", "quest"} <= p.schema["types"].keys())
                    self.assertEqual(p.links(p.find("Harbour Guild"))["members"][0][1].name, "Mira Vale")
                    self.assertTrue(Path(root, "sessions.md").is_file())

    def test_series_rule_detects_reversed_books(self):
        with tempfile.TemporaryDirectory() as root:
            ops.run("init", {"template": "series"}, root=root)
            ops.run("set", {"item": "Book 2", "field": {"date": "2024"}}, root=root)
            found = ops.run("check", root=root)
            self.assertEqual(found["fail"], 1)
            self.assertEqual(found["findings"][0]["code"], "ORDER_REGRESSION")

    def test_plain_init_is_unchanged(self):
        with tempfile.TemporaryDirectory() as root:
            result = ops.run("init", root=root)
            self.assertEqual(result, {"created": "lore.json", "root": root})
            self.assertEqual([p.name for p in Path(root).iterdir()], ["lore.json"])
            self.assertEqual(json.loads(Path(root, "lore.json").read_text(encoding="utf-8")),
                             {"lorekeeper": 1, "name": Path(root).name,
                              "types": {}, "roles": {}, "properties": {}})

    def test_invalid_template_leaves_folder_empty(self):
        for name in ("unknown", "", "Novel", "../novel"):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as root:
                with self.assertRaises(store.LoreError) as error:
                    ops.run("init", {"template": name}, root=root)
                self.assertEqual(error.exception.code, "INVALID")
                self.assertEqual(list(Path(root).iterdir()), [])

    def test_existing_files_and_names_are_preserved_before_any_write(self):
        cases = {
            "lore.json": "{}\n",
            "narrative.md": "My outline\r\n",
            "Events/Departure.md": "My draft\n",
            "elsewhere.md": '---\ntype: character\ncanonical_name: Mira Vale\n---\nMine\n',
            "Events": "A file where the template needs a folder\n",
        }
        for filename, content in cases.items():
            with self.subTest(filename=filename), tempfile.TemporaryDirectory() as root:
                path = Path(root, filename)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8", newline="")
                before = {str(p.relative_to(root)): p.read_bytes() for p in Path(root).rglob("*") if p.is_file()}
                with self.assertRaises(store.LoreError) as error:
                    ops.run("init", {"template": "novel"}, root=root)
                self.assertEqual(error.exception.code, "CONFLICT")
                after = {str(p.relative_to(root)): p.read_bytes() for p in Path(root).rglob("*") if p.is_file()}
                self.assertEqual(after, before)

    def test_repeat_init_and_independent_projects(self):
        original = copy.deepcopy(templates.TEMPLATES)
        with tempfile.TemporaryDirectory() as root:
            ops.run("init", {"template": "novel"}, root=root)
            ops.run("set", {"item": "Mira Vale", "field": {"born": "1985"}}, root=root)
            before = {str(p.relative_to(root)): p.read_bytes() for p in Path(root).rglob("*") if p.is_file()}
            with self.assertRaises(store.LoreError) as error:
                ops.run("init", {"template": "campaign"}, root=root)
            self.assertEqual(error.exception.code, "CONFLICT")
            self.assertEqual(before, {str(p.relative_to(root)): p.read_bytes()
                                     for p in Path(root).rglob("*") if p.is_file()})
        with tempfile.TemporaryDirectory() as root:
            ops.run("init", {"template": "novel"}, root=root)
            self.assertEqual(store.Project(root).find("Mira Vale").fields["born"], "1990")
        self.assertEqual(templates.TEMPLATES, original)

    def test_mcp_can_initialize_a_template(self):
        with tempfile.TemporaryDirectory() as root:
            response = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
                "name": "init", "arguments": {"template": "campaign"}}}, root)
            self.assertFalse(response["result"]["isError"])
            self.assertEqual(ops.run("check", root=root)["findings"], [])

    def test_packaging_declares_entry_point_and_editor_assets(self):
        data = tomllib.loads(Path(REPO, "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(data["build-system"]["build-backend"], "setuptools.build_meta")
        project = data["project"]
        self.assertEqual(project["name"], "lorekeeper")
        self.assertEqual(project["requires-python"], ">=3.11")
        self.assertEqual(project["dependencies"], [])
        self.assertEqual(project["scripts"], {"lore": "lorekeeper.cli:main"})
        settings = data["tool"]["setuptools"]
        self.assertEqual(settings["packages"], ["lorekeeper"])
        self.assertEqual(settings["dynamic"]["version"]["attr"], "lorekeeper.__version__")
        assets = settings["package-data"]["lorekeeper"]
        self.assertEqual(set(assets), {"editor.html", "editor.js", "editor.css"})
        for asset in assets:
            self.assertTrue(Path(REPO, "lorekeeper", asset).is_file())


if __name__ == "__main__":
    unittest.main()
