"""Protocol coverage and golden parity with the real CLI."""
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from lorekeeper import __version__, mcp, ops
from lorekeeper.store import LoreError

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURE = os.path.join(REPO, "tests", "fixtures", "world")
VERSIONS = ["2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]
VERSION_KEY = "io.modelcontextprotocol/protocolVersion"


def meta(version):
    return {VERSION_KEY: version, "io.modelcontextprotocol/clientCapabilities": {}}


class McpTests(unittest.TestCase):
    def request(self, method, params=None, root=FIXTURE):  # noqa: D401
        return mcp.handle({"jsonrpc": "2.0", "id": 1, "method": method,
                           "params": {} if params is None else params}, root)

    def call(self, name, arguments=None, root=FIXTURE):
        return self.request("tools/call", {"name": name, "arguments": arguments}, root)["result"]

    def test_initialize(self):
        for version in VERSIONS[1:] + ["unknown", "2026-07-28", None]:
            with self.subTest(version=version):
                response = self.request("initialize", {"protocolVersion": version})
                self.assertEqual(response, {"jsonrpc": "2.0", "id": 1, "result": {
                    "protocolVersion": version if version in VERSIONS[1:] else "2025-11-25",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "lorekeeper", "version": __version__},
                    "instructions": mcp.INSTRUCTIONS}})
        self.assertEqual(self.request("initialize")["result"]["protocolVersion"], "2025-11-25")
        self.assertIsInstance(mcp.INSTRUCTIONS, str)
        self.assertTrue(mcp.INSTRUCTIONS)

    def test_notifications_are_ignored_without_running_tools(self):
        with patch.object(ops, "run") as run:
            for method in ("notifications/initialized", "notifications/cancelled", "tools/call"):
                self.assertIsNone(mcp.handle({"jsonrpc": "2.0", "method": method,
                                             "params": {"name": "create"}}, FIXTURE))
            run.assert_not_called()

    def test_discover(self):
        self.assertEqual(self.request("server/discover")["result"], {
            "resultType": "complete", "supportedVersions": VERSIONS,
            "capabilities": {"tools": {}},
            "_meta": {"io.modelcontextprotocol/serverInfo": {"name": "lorekeeper", "version": __version__}},
            "instructions": mcp.INSTRUCTIONS})

    def test_unsupported_version_precedes_any_dispatch(self):
        with patch.object(ops, "run") as run:
            for method in ("initialize", "server/discover", "ping", "tools/list", "tools/call", "missing"):
                for version in ("2099-01-01", None):
                    with self.subTest(method=method, version=version):
                        self.assertEqual(self.request(method, {"_meta": meta(version)}), {
                            "jsonrpc": "2.0", "id": 1, "error": {
                                "code": -32022, "message": "Unsupported protocol version",
                                "data": {"supported": VERSIONS, "requested": version}}})
            run.assert_not_called()

    def test_modern_results_and_legacy_ping(self):
        self.assertEqual(self.request("ping")["result"], {})
        for method, params in (("ping", {}), ("tools/list", {}),
                               ("tools/call", {"name": "query"}),
                               ("tools/call", {"name": "show", "arguments": {"item": "Nobody"}})):
            legacy = self.request(method, params)["result"]
            self.assertNotIn("resultType", legacy)
            for version in VERSIONS:
                with self.subTest(method=method, version=version):
                    modern = self.request(method, {**params, "_meta": meta(version)})["result"]
                    self.assertEqual(modern, {**legacy, "resultType": "complete"})

    def test_tools_list(self):
        tools = self.request("tools/list")["result"]["tools"]
        self.assertEqual([t["name"] for t in tools], [op.name for op in ops.OPS])
        for tool, op in zip(tools, ops.OPS):
            self.assertEqual(tool["description"], op.summary)
            self.assertEqual(tool["annotations"], {"readOnlyHint": not op.writes})
            self.assertFalse(tool["inputSchema"]["additionalProperties"])
        by_name = {t["name"]: t for t in tools}
        self.assertEqual(by_name["show"]["inputSchema"], {
            "type": "object", "properties": {"item": {
                "type": "string", "description": "item name or id"}},
            "required": ["item"], "additionalProperties": False})
        self.assertNotIn("required", by_name["query"]["inputSchema"])

    def test_all_parameter_kinds(self):
        # Synthetic int/bool parameters cover kinds not yet used by the real table.
        kinds = ("str", "int", "bool", "list", "dict")
        op = ops.Op("sample", "Sample", [ops.Param(k, k, False, k) for k in kinds], False, None)
        with patch.object(ops, "OPS", [op]):
            schema = self.request("tools/list")["result"]["tools"][0]["inputSchema"]
        self.assertEqual(schema["properties"], {
            "str": {"type": "string", "description": "str"},
            "int": {"type": "integer", "description": "int"},
            "bool": {"type": "boolean", "description": "bool"},
            "list": {"type": "array", "items": {"type": "string"}, "description": "list"},
            "dict": {"type": "object", "description": "dict", "additionalProperties": {
                "anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "string"}}]}}})
        self.assertNotIn("required", schema)

    def test_golden_cli_parity(self):
        cases = [("query", {}, []), ("query", {"type": "character"}, ["--type", "character"]),
                 ("show", {"item": "Mara Quell"}, ["Mara Quell"]), ("check", {}, []), ("schema", {}, [])]
        env = dict(os.environ, PYTHONPATH=REPO, PYTHONDONTWRITEBYTECODE="1")
        for name, arguments, cli_args in cases:
            with self.subTest(name=name, arguments=arguments):
                cli = subprocess.run([sys.executable, "-m", "lorekeeper", "--root", FIXTURE,
                                      "--json", name, *cli_args], cwd=REPO, env=env,
                                     capture_output=True, encoding="utf-8")
                self.assertEqual(cli.returncode, 0, cli.stderr)
                self.assertTrue(cli.stdout.endswith("\n"))
                result = self.call(name, arguments)
                self.assertEqual(result["content"], [{"type": "text", "text": cli.stdout[:-1]}])
                self.assertEqual(result["structuredContent"], json.loads(cli.stdout))
                self.assertIs(result["isError"], False)

    def test_tool_and_method_errors(self):
        result = self.call("show", {"item": "Nobody"})
        self.assertIs(result["isError"], True)
        self.assertEqual(result["structuredContent"]["error"]["code"], "NOT_FOUND")
        self.assertEqual(result["content"][0]["text"], ops.to_json(result["structuredContent"]))
        self.assertEqual(self.request("tools/call", {"name": "missing"})["error"],
                         {"code": -32602, "message": "Unknown tool: missing"})
        self.assertEqual(self.request("missing")["error"],
                         {"code": -32601, "message": "Method not found: missing"})

    def test_tool_exceptions(self):
        for exc, expected in ((RuntimeError("broken"), {"error": {"code": "INTERNAL", "message": "broken"}}),
                              (LoreError("CONFLICT", "changed", {"version": "new"}),
                               {"error": {"code": "CONFLICT", "message": "changed", "data": {"version": "new"}}})):
            with self.subTest(exc=exc), patch.object(ops, "run", side_effect=exc):
                result = self.call("query")
                self.assertEqual(result, {"content": [{"type": "text", "text": ops.to_json(expected)}],
                                          "structuredContent": expected, "isError": True})

    def test_serve_lines_and_flush(self):
        messages = [{"id": 1, "method": "initialize"}, {"method": "notifications/initialized"},
                    {"id": 2, "method": "tools/list"}]
        inp = io.BytesIO(("\n".join(json.dumps(m) for m in messages) + "\nnot json\n").encode("utf-8"))
        out = io.BytesIO()
        with patch.object(out, "flush", wraps=out.flush) as flush:
            self.assertEqual(mcp.serve(FIXTURE, inp, out), 0)
            self.assertEqual(flush.call_count, 3)
        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), 3)
        responses = [json.loads(line) for line in lines]
        self.assertEqual(responses[:2], [mcp.handle(messages[i], FIXTURE) for i in (0, 2)])
        self.assertEqual(responses[2], {"jsonrpc": "2.0", "id": None,
                                        "error": {"code": -32700, "message": "Parse error"}})
        for line, response in zip(lines, responses):
            self.assertEqual(line, json.dumps(response, separators=(",", ":")).encode("ascii"))

    def test_serve_utf8_and_unterminated_last_line(self):
        message = {"jsonrpc": "2.0", "id": "é", "method": "tools/call", "params": {"name": "query"}}
        value = {"body": "café\nnext line"}
        out = io.BytesIO()
        with patch.object(ops, "run", return_value=value):
            self.assertEqual(mcp.serve(FIXTURE, io.BytesIO(json.dumps(message).encode("utf-8")), out), 0)
        self.assertEqual(len(out.getvalue().splitlines()), 1)
        self.assertTrue(out.getvalue().isascii())   # non-ASCII travels as JSON escapes
        self.assertEqual(json.loads(out.getvalue())["result"]["structuredContent"], value)

    def test_invalid_messages_do_not_stop_stream(self):
        out = io.BytesIO()
        self.assertEqual(mcp.serve(FIXTURE, io.BytesIO(b'\xff\n[]\n{"jsonrpc":"2.0","id":null,"method":"ping"}\n'), out), 0)
        responses = [json.loads(line) for line in out.getvalue().splitlines()]
        self.assertEqual([r["error"]["code"] for r in responses[:2]], [-32700, -32600])
        self.assertEqual(responses[2]["error"]["code"], -32600)   # a null id is not a valid request id
        for params in ([], None, {"_meta": []}):
            message = {"jsonrpc": "2.0", "id": 0, "method": "ping", "params": params}
            self.assertEqual(mcp.handle(message, FIXTURE)["error"]["code"], -32602)

    def test_handle_preserves_request(self):
        message = {"jsonrpc": "2.0", "id": "request", "method": "tools/call", "params": {
            "name": "query", "arguments": {"type": "character"}, "_meta": meta(VERSIONS[0])}}
        before = copy.deepcopy(message)
        self.assertEqual(mcp.handle(message, FIXTURE)["id"], "request")
        self.assertEqual(message, before)

    def test_create_then_show(self):
        # Keep temporary writes inside the repository; the source fixture stays read-only.
        with tempfile.TemporaryDirectory(dir=REPO) as tmp:
            root = os.path.join(tmp, "world")
            shutil.copytree(FIXTURE, root)
            made = self.call("create", {"type": "character", "name": "Renée Vale",
                                       "field": {"tags": ["traveler"]}, "body": "A traveler.\n"}, root)
            self.assertIs(made["isError"], False)
            shown = self.call("show", {"item": "Renée Vale"}, root)
            self.assertIs(shown["isError"], False)
            self.assertEqual(shown["structuredContent"]["name"], "Renée Vale")
            self.assertEqual(shown["structuredContent"]["fields"]["tags"], ["traveler"])
            self.assertEqual(shown["structuredContent"]["body"], "A traveler.\n")
            self.assertEqual(shown["structuredContent"]["version"], made["structuredContent"]["version"])


if __name__ == "__main__":
    unittest.main()
