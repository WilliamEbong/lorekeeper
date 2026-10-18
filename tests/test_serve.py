"""Real loopback requests against a disposable copy, never the fixture itself."""
import contextlib
from concurrent.futures import ThreadPoolExecutor
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
        self.assertIn('<meta name="lore-name" content="The Salt Road">', page)
        for path, mime in (("/editor.js", "text/javascript"), ("/editor.css", "text/css"),
                           ("/favicon.svg", "image/svg+xml")):
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

    def test_deep_json_and_oversized_integer_return_invalid(self):
        bodies = [b'{"text":' + b'[' * 100000 + b'0' + b']' * 100000 + b'}']
        import sys
        limit = sys.get_int_max_str_digits()
        if limit:
            bodies.append(b'{"text":' + b'9' * (limit + 1) + b'}')
        for body in bodies:
            with self.subTest(size=len(body)):
                status, result, _ = self.request("/api/query", raw=body)
                self.assertEqual(status, 400)
                self.assertEqual(result["error"]["code"], "INVALID")
        self.assertEqual(self.request("/api/graph", {})[0], 200)

    def test_path_operations_target_the_selected_item_despite_id_name_collision(self):
        first = ops.run("create", {"type": "event", "name": "Identity A"}, root=self.root)
        second = ops.run("create", {"type": "event", "name": first["id"]}, root=self.root)
        ref = "path:" + first["path"]
        self.assertEqual(self.request("/api/show", {"item": first["id"]})[1]["path"], first["path"])
        status, saved, _ = self.request("/api/set", {"item": ref, "field": {"date": "2071"},
                                                   "version": first["version"], "expect": {"date": None}})
        self.assertEqual(status, 200)
        self.assertNotIn("date", self.request("/api/show", {"item": "path:" + second["path"]})[1]["fields"])
        person = ops.run("show", {"item": "Mara Quell"}, root=self.root)
        args = {"item": ref, "target": "path:" + person["path"], "role": "participants", "version": saved["version"]}
        status, linked, _ = self.request("/api/link", args)
        self.assertEqual(status, 200)
        links = self.request("/api/graph", {})[1]["links"]
        self.assertTrue(any(l["from_path"] == first["path"] and l["to_path"] == person["path"] for l in links))
        self.assertIn("years", self.request("/api/age", {"item": args["target"], "at": ref})[1])
        self.assertEqual(self.request("/api/unlink", {**args, "version": linked["version"]})[0], 200)
        self.assertEqual(self.request("/api/request", {"item": ref, "note": "Correct date", "field": {"date": "2072"}})[0], 200)
        self.assertEqual(self.request("/api/requests", {})[1]["requests"][0]["path"], first["path"])

    def test_link_and_unlink_reject_stale_versions_even_for_noop(self):
        item = ops.run("show", {"item": "Crossing Harrow Pass"}, root=self.root)
        target = ops.run("show", {"item": "The flood at Saltmarsh"}, root=self.root)
        ref = "path:" + item["path"]
        changed = ops.run("set", {"item": ref, "field": {"after": "[[The flood at Saltmarsh]] +3d"}}, root=self.root)
        path = self.root / item["path"]
        before = path.read_bytes()
        args = {"item": ref, "target": "path:" + target["path"], "role": "after", "version": item["version"]}
        for name in ("link", "unlink"):
            status, result, _ = self.request("/api/" + name, args)
            self.assertEqual(status, 409)
            self.assertEqual(result["error"]["code"], "CONFLICT")
            self.assertEqual(result["error"]["data"]["version"], changed["version"])
            self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.request("/api/unlink", {**args, "version": changed["version"]})[0], 200)

    def test_requests_preserve_draft_baselines_and_mark_stale(self):
        item = ops.run("show", {"item": "Mara Quell"}, root=self.root)
        ref = "path:" + item["path"]
        base = {"born": item["fields"]["born"], "died": None}
        changed = ops.run("set", {"item": ref, "field": {"born": "2042"}}, root=self.root)
        before = (self.root / item["path"]).read_bytes()
        for supplied, stale in (({"version": item["version"], "expect": base}, True),
                                ({"version": item["version"]}, True), ({"expect": base}, True),
                                ({"version": changed["version"], "expect": {"born": "2042", "died": None}}, False),
                                ({}, False)):
            with self.subTest(supplied=supplied):
                status, result, _ = self.request("/api/request", {"item": ref, "note": "Correction",
                                                                "field": {"born": "2043"}, "unset": ["died"], **supplied})
                self.assertEqual(status, 200)
                queued = next(r for r in self.request("/api/requests", {})[1]["requests"] if r["id"] == result["request"])
                self.assertEqual(queued["current"], {"born": "2042", "died": None})
                self.assertEqual(queued["version"], changed["version"])
                self.assertEqual(queued["base_version"], supplied.get("version", changed["version"]))
                self.assertEqual(queued["base"], supplied.get("expect", queued["current"]))
                self.assertEqual(queued.get("stale", False), stale)
        self.assertEqual((self.root / item["path"]).read_bytes(), before)

    def test_concurrent_requests_have_unique_ids_and_creation_is_exclusive(self):
        args = {"item": "Mara Quell", "note": "Concurrent proposal", "field": {"born": "2042"}}
        with patch.object(ops.time, "strftime", return_value="20261017T120000"):
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda _: self.request("/api/request", args), range(8)))
            self.assertTrue(all(status == 200 for status, _, _ in results))
            ids = [result["request"] for _, result, _ in results]
            self.assertEqual(len(set(ids)), 8)
            for rid in ids:
                self.assertRegex(rid, r"^20261017T120000-mara-quell-[0-9a-f]{6}$")
            with patch.object(ops.secrets, "token_hex", return_value="abcdef") as random:
                self.assertEqual(self.request("/api/request", args)[0], 200)
                before = self.request("/api/requests", {})[1]
                self.assertEqual(self.request("/api/request", {**args, "note": "Must not overwrite"})[0], 409)
                self.assertEqual(self.request("/api/requests", {})[1], before)
                random.assert_called_with(3)

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

    def test_stamp_scopes_paths_excludes_folders_and_deduplicates_roots(self):
        config = {"paths": ["Characters"], "exclude": ["Archive"]}
        (self.root / "lore.json").write_text(json.dumps(config), encoding="utf-8")
        for name in ("Archive", "node_modules", "_TEMPLATES", "__pycache__", ".hidden"):
            folder = self.root / "Characters" / name
            folder.mkdir()
            (folder / "ignored.md").write_text("Ignored", encoding="utf-8")
        scanned = []
        real_scan = serve.os.scandir

        def scan(path):
            scanned.append(Path(path).relative_to(self.root).as_posix())
            return real_scan(path)

        with patch.object(serve.os, "scandir", side_effect=scan):
            before = serve.stamp(self.root)
        self.assertEqual(scanned, ["Characters"])
        for path in (self.root / "notes" / "Draft.md", self.root / "Characters" / "Archive" / "ignored.md",
                     self.root / "Characters" / "~$lock.md"):
            path.write_text("Unrelated change", encoding="utf-8")
        self.assertEqual(serve.stamp(self.root), before)
        self.assertEqual(serve.stamp(self.root, {**config, "paths": ["Characters", "Characters/."]}), before)
        person = self.root / "Characters" / "Mara Quell.md"
        person.write_text(person.read_text(encoding="utf-8") + "\nEdit", encoding="utf-8")
        self.assertNotEqual(serve.stamp(self.root), before)
        self.assertEqual(serve.stamp(self.root, {"paths": [".", "Characters"]}), serve.stamp(self.root, {"paths": ["."]}))
        before = serve.stamp(self.root)
        (self.root / "lore.json").write_text(json.dumps({**config, "name": "Changed"}), encoding="utf-8")
        self.assertNotEqual(serve.stamp(self.root), before)
        self.start(config=config)
        self.assertEqual(self.request("/api/stamp")[1]["stamp"], serve.stamp(self.root, config))

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
