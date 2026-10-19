"""The Lorekeeper app: world list, folder kinds, AI files and the start-screen server, on disposable folders."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from lorekeeper import app, ops

REPO = Path(__file__).resolve().parents[1]


class AppTestCase(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix=".app-test-", dir=REPO)
        self.addCleanup(temp.cleanup)
        self.tmp = Path(temp.name)
        patcher = patch("lorekeeper.app.data_dir", return_value=str(self.tmp / "data"))
        patcher.start()
        self.addCleanup(patcher.stop)


class WorldListTests(AppTestCase):
    def test_remember_orders_newest_first_and_forget_removes(self):
        app.remember(str(self.tmp / "a"), "A", "world", when="2026-10-01T10:00:00")
        app.remember(str(self.tmp / "b"), "B", "world", when="2026-10-02T10:00:00")
        app.remember(str(self.tmp / "a"), "A again", "world", when="2026-10-03T10:00:00")
        self.assertEqual([w["name"] for w in app.load_worlds()], ["A again", "B"])
        app.forget(str(self.tmp / "a"))
        self.assertEqual([w["name"] for w in app.load_worlds()], ["B"])

    def test_unreadable_list_is_empty_not_fatal(self):
        os.makedirs(self.tmp / "data")
        (self.tmp / "data" / "worlds.json").write_text("{not json", encoding="utf-8")
        self.assertEqual(app.load_worlds(), [])

    def test_folder_kinds(self):
        world, saga, plain = self.tmp / "w", self.tmp / "s", self.tmp / "p"
        world.mkdir(); (world / "lore.json").write_text("{}", encoding="utf-8")
        (saga / "_system" / "scripts").mkdir(parents=True)
        (saga / "_system" / "scripts" / "saga.py").write_text("", encoding="utf-8")
        (saga / "_system" / "lorekeeper.json").write_text("{}", encoding="utf-8")
        plain.mkdir()
        self.assertEqual([app.kind(str(f)) for f in (world, saga, plain, self.tmp / "gone")],
                         ["world", "saga", "folder", "missing"])

    def test_folder_name_drops_characters_windows_cannot_use(self):
        self.assertEqual(app.folder_name('  The: Glass/Orchard?. '), "The Glass Orchard")
        self.assertEqual(app.folder_name("???"), "My world")


class CreateAndAIFileTests(AppTestCase):
    def test_create_blank_and_template_worlds(self):
        blank = app.create_world("Quiet Hills", None, str(self.tmp / "Quiet Hills"))
        self.assertEqual(json.loads(Path(blank, "lore.json").read_text(encoding="utf-8"))["name"], "Quiet Hills")
        novel = app.create_world("The Glass Orchard", "novel", str(self.tmp / "nested" / "The Glass Orchard"))
        self.assertTrue(Path(novel, "Characters", "Mira Vale.md").is_file())
        with self.assertRaises(app.AppError) as caught:
            app.create_world("Again", None, blank)
        self.assertIn("already", str(caught.exception))

    def test_ai_files_are_written_and_never_overwrite_a_persons_files(self):
        root = Path(app.create_world("Salt", "novel", str(self.tmp / "Salt")))
        (root / "AGENTS.md").write_text("My own agent notes\n", encoding="utf-8")
        (root / ".mcp.json").write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}), encoding="utf-8")
        before = ops.run("check", {}, root=str(root))
        app.write_ai_files(str(root))
        self.assertEqual((root / "AGENTS.md").read_text(encoding="utf-8"), "My own agent notes\n")
        self.assertIn(".lore/AI-GUIDE.md", (root / "CLAUDE.md").read_text(encoding="utf-8"))
        servers = json.loads((root / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]
        self.assertEqual(servers["other"], {"command": "x"})
        self.assertEqual(servers["lorekeeper"]["args"][-3:], ["mcp", "--root", str(root)])
        guide = root / ".lore" / "AI-GUIDE.md"
        guide.write_text("stale", encoding="utf-8")
        app.write_ai_files(str(root))
        self.assertTrue(guide.read_text(encoding="utf-8").startswith("<!-- Written by Lorekeeper"))
        # The AI files are not items and add no findings.
        self.assertEqual(ops.run("check", {}, root=str(root)), before)

    def test_invalid_mcp_json_is_left_alone(self):
        root = Path(app.create_world("Salt", None, str(self.tmp / "Salt")))
        (root / ".mcp.json").write_text("{broken", encoding="utf-8")
        app.write_ai_files(str(root))
        self.assertEqual((root / ".mcp.json").read_text(encoding="utf-8"), "{broken")

    def test_guide_describes_this_world_and_every_operation(self):
        root = app.create_world("The Salt Road", "novel", str(self.tmp / "Salt Road"))
        guide = app.ai_guide(root)
        for text in ("The Salt Road", root, "schema", "Characters", "participants", "## Operation reference",
                     "## How everything connects", os.path.dirname(app.__file__)):
            self.assertIn(text, guide)


class ServerTests(AppTestCase):
    def setUp(self):
        super().setUp()
        self.server, self.url, self.token = app.make_app(0)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(lambda: (app.stop_all(self.server), self.server.server_close(), thread.join(timeout=5)))

    def call(self, path, args=None, token=True, host=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-Lore-Token"] = self.token
        if host:
            headers["Host"] = host
        data = json.dumps(args).encode("utf-8") if args is not None else None
        try:
            response = urlopen(Request(self.url.rstrip("/") + path, data=data, headers=headers), timeout=10)
        except HTTPError as exc:
            response = exc
        with response:
            body = response.read().decode("utf-8")
            kind = response.headers.get_content_type()
            return response.status, json.loads(body) if kind == "application/json" else body

    def test_page_hello_and_guards(self):
        status, page = self.call("/")
        self.assertEqual(status, 200)
        self.assertIn(self.token, page)
        self.assertEqual(self.call("/api/hello"), (200, {"app": "lorekeeper"}))
        self.assertEqual(self.call("/api/forget", {"folder": "x"}, token=False)[0], 403)
        self.assertEqual(self.call("/api/hello", host="evil.example")[0], 403)

    def test_create_open_reopen_offer_and_forget(self):
        place = str(self.tmp / "Orchard")
        status, created = self.call("/api/create", {"name": "Orchard", "template": "novel", "parent": str(self.tmp)})
        self.assertEqual(status, 200, created)
        page = urlopen(created["url"], timeout=10).read().decode("utf-8")
        self.assertIn(f'<meta name="lore-home" content="{self.url}">', page)
        self.assertTrue(Path(place, ".lore", "AI-GUIDE.md").is_file())
        self.assertEqual(self.call("/api/open", {"folder": place})[1]["url"], created["url"])
        worlds = self.call("/api/worlds")[1]
        self.assertEqual([(w["name"], w["kind"], w["open"]) for w in worlds["worlds"]], [("Orchard", "world", True)])
        self.assertTrue(worlds["parent"].endswith("Lorekeeper worlds"))
        plain = self.tmp / "notes"
        plain.mkdir()
        (plain / "idea.md").write_text("# An idea\n", encoding="utf-8")
        self.assertEqual(self.call("/api/open", {"folder": str(plain)})[1], {"offer": "make", "name": "notes"})
        self.assertIn("url", self.call("/api/open", {"folder": str(plain), "make": True})[1])
        self.assertEqual((plain / "idea.md").read_text(encoding="utf-8"), "# An idea\n")
        self.assertEqual(self.call("/api/forget", {"folder": place})[0], 200)
        self.assertEqual([w["name"] for w in self.call("/api/worlds")[1]["worlds"]], ["notes"])

    def test_errors_are_plain_sentences(self):
        status, reply = self.call("/api/open", {"folder": str(self.tmp / "nowhere")})
        self.assertEqual(status, 404)
        self.assertNotIn("_", reply["error"])
        status, reply = self.call("/api/create", {"name": "", "template": None, "parent": str(self.tmp)})
        self.assertEqual(status, 400)
        self.assertIn("name", reply["error"])

    def test_pick_uses_the_folder_picker(self):
        with patch("lorekeeper.app.pick_folder", return_value="C:/Stories"):
            self.assertEqual(self.call("/api/pick", {}), (200, {"folder": "C:/Stories"}))

    def test_quit_stops_worlds_and_the_start_screen(self):
        _, created = self.call("/api/create", {"name": "Brief", "template": None, "parent": str(self.tmp)})
        self.assertEqual(self.call("/api/quit", {}), (200, {"closed": True}))
        for url in (created["url"], self.url):
            with self.assertRaises((URLError, ConnectionError, OSError)):
                urlopen(url + "api/stamp", timeout=3)


class LaunchTests(AppTestCase):
    def test_saga_command_uses_the_sagas_own_launcher(self):
        command = app.saga_command(8711)
        self.assertEqual(command[1:], [os.path.join("_system", "scripts", "saga.py"), "timeline", "--port", "8711"])

    def test_shortcut_runs_the_package_folder_without_a_console(self):
        spec = app.shortcut_spec()
        self.assertEqual(spec["arguments"], f'"{os.path.dirname(app.__file__)}" app')
        self.assertTrue(spec["icon"].endswith("lorekeeper.ico") and os.path.isfile(spec["icon"]))
        if sys.platform == "win32" and os.path.isfile(os.path.join(os.path.dirname(sys.executable), "pythonw.exe")):
            self.assertTrue(spec["target"].lower().endswith("pythonw.exe"))

    def test_an_ai_can_connect_from_the_worlds_mcp_settings(self):
        root = app.create_world("Handshake", "novel", str(self.tmp / "Handshake"))
        app.write_ai_files(root)
        server = json.loads(Path(root, ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["lorekeeper"]
        lines = [{"jsonrpc": "2.0", "id": 1, "method": "initialize",
                  "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}},
                 {"jsonrpc": "2.0", "method": "notifications/initialized"},
                 {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "schema", "arguments": {}}}]
        done = subprocess.run([server["command"], *server["args"]], input="".join(json.dumps(m) + "\n" for m in lines),
                              capture_output=True, text=True, encoding="utf-8", timeout=60)
        replies = [json.loads(line) for line in done.stdout.splitlines() if line.strip()]
        self.assertEqual(replies[-1]["result"]["structuredContent"]["name"], "Handshake")


if __name__ == "__main__":
    unittest.main()
