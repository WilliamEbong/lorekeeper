"""Real loopback requests against a disposable copy, never the fixture itself."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from lorekeeper import cli, ops, serve
from lorekeeper.store import Item, Project

REPO = Path(__file__).resolve().parents[1]
FIXTURE = REPO / "tests" / "fixtures" / "world"


class ServeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix=".editor-test-", dir=REPO)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "world"
        shutil.copytree(FIXTURE, self.root)
        self.start()

    def start(self, **kwargs):
        self.server, self.url, self.token = serve.make_server(self.root, **kwargs)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()

        # Capture each server independently: tests may also start a saga server.
        server = self.server

        def cleanup():
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

        self.addCleanup(cleanup)

    def request(self, path, args=None, headers=None, raw=None):
        data = (json.dumps(args).encode("utf-8") if args is not None else raw)
        hdr = {"X-Lore-Token": self.token, "Content-Type": "application/json"}
        hdr.update(headers or {})
        hdr = {key: value for key, value in hdr.items() if value is not None}
        req = Request(self.url.rstrip("/") + path, data=data, headers=hdr)
        try:
            response = urlopen(req, timeout=5)
        except HTTPError as exc:
            response = exc
        with response:
            body = response.read().decode("utf-8")
            value = json.loads(body) if response.headers.get_content_type() == "application/json" else body
            return response.status, value, response.headers

    def test_page_token_and_assets(self):
        status, page, headers = self.request("/")
        self.assertEqual(status, 200)
        self.assertIn(f'<meta name="lore-token" content="{self.token}">', page)
        self.assertIn('type="module"', page)
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        for path, mime in (("/editor.js", "text/javascript"), ("/editor.css", "text/css")):
            status, body, headers = self.request(path)
            self.assertEqual(status, 200)
            self.assertTrue(body)
            self.assertEqual(headers.get_content_type(), mime)

    def test_ops_are_generated_from_table(self):
        status, result, _ = self.request("/api/ops")
        self.assertEqual(status, 200)
        self.assertEqual(result["ops"], [{"name": op.name, "summary": op.summary,
                                         "params": [p._asdict() for p in op.params], "writes": op.writes}
                                        for op in ops.OPS])

    def test_query_and_graph_match_ops(self):
        for name, args in (("query", {"type": "character"}), ("graph", {})):
            with self.subTest(name=name):
                status, result, _ = self.request("/api/" + name, args)
                self.assertEqual(status, 200)
                self.assertEqual(result, ops.run(name, args, root=self.root))

    def test_missing_token(self):
        for name in ("query", "set"):
            status, result, _ = self.request("/api/" + name, {}, {"X-Lore-Token": None})
            self.assertEqual(status, 403)
            self.assertEqual(result["error"]["code"], "FORBIDDEN")

    def test_wrong_content_type(self):
        status, _, _ = self.request("/api/query", {}, {"Content-Type": "text/plain"})
        self.assertEqual(status, 415)

    def test_bad_host_on_get_and_post(self):
        for path, args in (("/", None), ("/editor.js", None), ("/api/ops", None), ("/api/query", {})):
            status, result, _ = self.request(path, args, {"Host": "evil.example:80"})
            self.assertEqual(status, 403)
            self.assertEqual(result["error"]["code"], "FORBIDDEN")

    def test_localhost_host_is_allowed(self):
        self.assertEqual(self.request("/", headers={"Host": f"localhost:{self.server.server_port}"})[0], 200)
        self.assertEqual(self.server.server_address[0], "127.0.0.1")

    def test_malformed_arguments_are_invalid(self):
        for data in (b"{", b"[]", b"null", b'{"text": []}', b'\xff'):
            with self.subTest(data=data):
                status, result, _ = self.request("/api/query", raw=data)
                self.assertEqual(status, 400)
                self.assertEqual(result["error"]["code"], "INVALID")
        self.assertEqual(self.request("/api/set", {"item": "Mara Quell", "unset": [{}]})[0], 400)

    def test_not_found_and_no_arbitrary_assets(self):
        for path, args in (("/api/nope", {}), ("/api/show", {"item": "Nobody"}),
                           ("/../lore.json", None), ("/lore.json", None), ("/api/set", None)):
            self.assertEqual(self.request(path, args)[0], 404)

    def test_create_set_link_unlink_and_age(self):
        status, item, _ = self.request("/api/create", {"type": "event", "name": "New crossing"})
        self.assertEqual(status, 200)
        self.assertEqual(self.request("/api/set", {"item": item["id"], "field": {"date": "2071-05-03"},
                                                 "version": item["version"], "expect": {"date": None}})[0], 200)
        args = {"item": item["id"], "role": "participants", "target": "Mara Quell"}
        self.assertEqual(self.request("/api/link", args)[0], 200)
        self.assertIn("years", self.request("/api/age", {"item": "Mara Quell", "at": item["id"]})[1])
        self.assertEqual(self.request("/api/unlink", args)[0], 200)

    def test_stale_version_conflict_returns_current(self):
        item = ops.run("show", {"item": "Mara Quell"}, root=self.root)
        ops.run("set", {"item": item["id"], "field": {"born": "2042"}}, root=self.root)
        status, result, _ = self.request("/api/set", {"item": item["id"], "field": {"born": "2043"},
                                                    "version": item["version"], "expect": {"born": item["fields"]["born"]}})
        self.assertEqual(status, 409)
        self.assertEqual(result["error"]["code"], "CONFLICT")
        self.assertEqual(result["error"]["data"]["current"], {"born": "2042"})

    def test_stale_version_different_field_merges(self):
        item = ops.run("show", {"item": "Mara Quell"}, root=self.root)
        ops.run("set", {"item": item["id"], "field": {"status": "updated"}}, root=self.root)
        status, result, _ = self.request("/api/set", {"item": item["id"], "field": {"born": "2043"},
                                                    "version": item["version"], "expect": {"born": item["fields"]["born"]}})
        self.assertEqual(status, 200)
        self.assertTrue(result["merged"])
        self.assertEqual(ops.run("show", {"item": item["id"]}, root=self.root)["fields"]["status"], "updated")

    def test_saga_flag_blocks_all_canon_writes_and_queues_request(self):
        self.start(saga=True)
        self.assert_saga()

    def test_saga_config_blocks_canon_writes(self):
        self.start(config={"mode": "saga"})
        self.assert_saga()

    def test_saga_config_from_disk(self):
        (self.root / "lore.json").write_text('{"mode": "saga"}', encoding="utf-8")
        self.start()
        self.assert_saga()

    def assert_saga(self):
        item = ops.run("show", {"item": "Mara Quell"}, root=self.root)
        path = self.root / item["path"]
        before = path.read_bytes()
        for op in ops.OPS:
            if op.writes and op.name != "request":
                status, result, _ = self.request("/api/" + op.name, {})
                self.assertEqual(status, 403)
                self.assertEqual(result["error"]["code"], "FORBIDDEN")
        self.assertIn('name="lore-saga" content="true"', self.request("/")[1])
        status, result, _ = self.request("/api/request", {"item": item["id"], "note": "Birthday correction", "field": {"born": "2042"}})
        self.assertEqual(status, 200)
        self.assertTrue(result["queued"])
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.request("/api/requests", {})[1]["requests"][0]["set"], {"born": "2042"})

    def test_stamp_tracks_edits_config_creation_deletion_and_ignores_hidden(self):
        def current():
            return self.request("/api/stamp")[1]["stamp"]
        before = current()
        path = self.root / "notes" / "Draft.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nEdit", encoding="utf-8")
        self.assertNotEqual(current(), before)
        before = current()
        config = self.root / "lore.json"
        config.write_text(config.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        self.assertNotEqual(current(), before)
        before = current()
        new = self.root / "new.md"
        new.write_text("New", encoding="utf-8")
        self.assertNotEqual(current(), before)
        with_new = current()
        new.unlink()
        self.assertNotEqual(current(), with_new)
        hidden = self.root / ".hidden"
        hidden.mkdir()
        (hidden / "ignored.md").write_text("Ignored", encoding="utf-8")
        self.assertEqual(current(), before)

    def test_factory_is_fresh_and_can_add_memory_cards(self):
        calls = []

        def factory():
            project = Project(self.root, {"mode": "saga"})
            card = Item.from_fields("architecture#CH002", {"id": "CH002", "type": "card", "canonical_name": "Card two", "date": "2071-05-03", "chapter": "2"})
            calls.append(project)
            return Project.from_items(self.root, project.config, project.items + [card])

        self.start(saga=True, factory=factory)
        for _ in range(2):
            result = self.request("/api/graph", {})[1]
            self.assertIn("CH002", [item["id"] for item in result["items"]])
        self.assertEqual(len(calls), 2)
        self.assertIsNot(calls[0], calls[1])

    def test_serve_closes_on_interrupt_and_prints_url(self):
        with patch.object(serve.ThreadingHTTPServer, "serve_forever", side_effect=KeyboardInterrupt), \
                patch.object(serve.ThreadingHTTPServer, "server_close", autospec=True,
                             side_effect=serve.ThreadingHTTPServer.server_close) as close, \
                contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(serve.serve(self.root), 0)
        self.assertRegex(out.getvalue(), r"Lorekeeper editor: http://127\.0\.0\.1:\d+/\n")
        close.assert_called_once()

    def test_cli_adapter_options(self):
        args = cli.build_parser().parse_args(["serve", "--port", "8123", "--saga", "--root", str(self.root)])
        self.assertEqual((args.port, args.saga, args.root), (8123, True, str(self.root)))


if __name__ == "__main__":
    unittest.main()
