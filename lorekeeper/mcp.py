"""Small, stateless MCP adapter over the operations table (JSON lines on stdio)."""
import json
import sys

from . import __version__, ops
from .store import LoreError

SUPPORTED = ["2026-07-28", "2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"]
VERSION_KEY = "io.modelcontextprotocol/protocolVersion"
INSTRUCTIONS = (
    "Lorekeeper stores a story world as Markdown files, one per item. "
    "Use query/show to read and create/set/link to write. "
    "set merges or returns CONFLICT; pass the version and expect values you read. "
    "Run check after edits."
)


def _error(id_, code, message, data=None):
    error = {"code": code, "message": message}
    if data is not None:
        error["data"] = data
    return {"jsonrpc": "2.0", "id": id_, "error": error}


def _tool(op):
    properties = {}
    for p in op.params:
        prop = {"type": {"str": "string", "int": "integer", "bool": "boolean",
                         "list": "array", "dict": "object"}[p.kind], "description": p.help}
        if p.kind == "list":
            prop["items"] = {"type": "string"}
        elif p.kind == "dict":
            prop["additionalProperties"] = {"anyOf": [
                {"type": "string"}, {"type": "array", "items": {"type": "string"}}]}
        properties[p.name] = prop
    schema = {"type": "object", "properties": properties, "additionalProperties": False}
    required = [p.name for p in op.params if p.required]
    if required:
        schema["required"] = required
    return {"name": op.name, "description": op.summary, "inputSchema": schema,
            "annotations": {"readOnlyHint": not op.writes}}


def handle(message: dict, root: str) -> dict | None:
    """Return a response without transport I/O; tools delegate their effects to ops."""
    # Only individual JSON-RPC objects are supported; batches are invalid requests.
    if not isinstance(message, dict):
        return _error(None, -32600, "Invalid Request")
    # Notifications never execute operations, including accidental tools/call notifications.
    if "id" not in message:
        return None
    id_ = message["id"]
    if message.get("jsonrpc") != "2.0" or isinstance(id_, bool) or not isinstance(id_, (str, int)) \
            or not isinstance(message.get("method"), str):
        return _error(id_ if isinstance(id_, (str, int)) and not isinstance(id_, bool) else None,
                      -32600, "Invalid Request")
    method = message.get("method")
    params = message.get("params", {})
    if not isinstance(params, dict):
        return _error(id_, -32602, "Invalid params")
    meta = params.get("_meta", {})
    if not isinstance(meta, dict):
        return _error(id_, -32602, "Invalid params")
    modern = VERSION_KEY in meta
    if modern and meta[VERSION_KEY] in SUPPORTED and "io.modelcontextprotocol/clientCapabilities" not in meta:
        return _error(id_, -32602, "Invalid params: _meta needs io.modelcontextprotocol/clientCapabilities")
    if modern and meta[VERSION_KEY] not in SUPPORTED:
        return _error(id_, -32022, "Unsupported protocol version",
                      {"supported": list(SUPPORTED), "requested": meta[VERSION_KEY]})
    info = {"name": "lorekeeper", "version": __version__}
    if method == "initialize":
        version = params.get("protocolVersion")
        result = {"protocolVersion": version if version in SUPPORTED[1:] else SUPPORTED[1],
                  "capabilities": {"tools": {}}, "serverInfo": info, "instructions": INSTRUCTIONS}
    elif method == "server/discover":
        result = {"resultType": "complete", "supportedVersions": list(SUPPORTED),
                  "capabilities": {"tools": {}},
                  "_meta": {"io.modelcontextprotocol/serverInfo": info}, "instructions": INSTRUCTIONS}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": [_tool(op) for op in ops.OPS]}
    elif method == "tools/call":
        name = params.get("name")
        if not isinstance(name, str) or name not in ops.BY_NAME:
            return _error(id_, -32602, f"Unknown tool: {name}")
        arguments = params.get("arguments")
        if arguments is not None and not isinstance(arguments, dict):
            return _error(id_, -32602, "Invalid params: arguments must be an object")
        is_error = False
        try:   # bad argument values come back from ops.run as INVALID tool errors
            value = ops.run(name, arguments, root=root)
        except LoreError as exc:
            value, is_error = exc.as_dict(), True
        except Exception as exc:
            value, is_error = LoreError("INTERNAL", str(exc)).as_dict(), True
        result = {"content": [{"type": "text", "text": ops.to_json(value)}],
                  "structuredContent": value, "isError": is_error}
    else:
        return _error(id_, -32601, f"Method not found: {method}")
    # A supported per-request version selects modern framing, with no session state.
    if modern:
        result["resultType"] = "complete"
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def serve(root, inp=None, out=None) -> int:
    """Serve UTF-8 JSON lines on binary streams until EOF."""
    inp = sys.stdin.buffer if inp is None else inp
    out = sys.stdout.buffer if out is None else out
    for line in inp:
        if not line.strip():
            continue
        try:
            message = json.loads(line.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            response = _error(None, -32700, "Parse error")
        else:
            response = handle(message, root)
        if response is not None:
            # ASCII escapes keep lone surrogates and any other odd text valid on the wire
            out.write((json.dumps(response, separators=(",", ":")) + "\n").encode("ascii"))
            out.flush()
    return 0
