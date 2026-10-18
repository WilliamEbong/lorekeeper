"""Loopback-only HTTP adapter over OPS and the bundled, build-free editor."""
import hashlib
import html
import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from . import ops, store
from .store import LoreError


def stamp(root, config=None):
    """Hash metadata in configured roots, plus lore.json; skip excluded folders."""
    root = os.path.abspath(root)
    config_path = os.path.join(root, store.CONFIG)
    if config is None:
        config = {}
        if os.path.isfile(config_path):
            with open(config_path, encoding="utf-8") as fh:
                try:
                    config = json.load(fh)
                except (ValueError, RecursionError) as exc:
                    raise LoreError("INVALID", f"{store.CONFIG} is not valid JSON: {exc}") from exc
    rows, visited = [], set()
    skip = store.SKIP_DIRS | set(config.get("exclude", []))

    def record(path):
        try:
            info = os.stat(path, follow_symlinks=False)
        except FileNotFoundError:  # A replacement or deletion can overlap a scan.
            return
        rows.append((os.path.relpath(path, root).replace(os.sep, "/"),
                     info.st_mtime_ns, info.st_size))

    def scan(folder):
        key = os.path.normcase(os.path.realpath(folder))
        if key in visited or os.path.islink(folder) or not store.inside(root, folder):
            return
        visited.add(key)
        if not os.path.isdir(folder):
            return
        with os.scandir(folder) as entries:
            for entry in entries:
                if entry.is_symlink():
                    continue
                if entry.is_dir(follow_symlinks=False):
                    if entry.name not in skip and not entry.name.startswith("."):
                        scan(entry.path)
                elif entry.name.endswith(".md") and not entry.name.startswith("~$"):
                    record(entry.path)

    for base in config.get("paths", ["."]):
        top = os.path.normpath(os.path.join(root, base))
        if not store.inside(root, top):
            raise LoreError("INVALID", f"{store.CONFIG} path {base!r} is outside the project folder")
        scan(top)
    record(config_path)
    return hashlib.sha256(ops.to_json(sorted(rows)).encode("utf-8")).hexdigest()


ASSETS = {"/": "text/html", "/editor.js": "text/javascript", "/editor.css": "text/css",
          "/favicon.svg": "image/svg+xml"}


def make_server(root, port=0, saga=False, config=None, factory=None):
    root = os.path.abspath(root)
    settings = config
    if settings is None:
        settings = {}
        path = os.path.join(root, "lore.json")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                settings = json.load(fh)
    saga_mode = bool(saga or settings.get("mode") == "saga")
    token = secrets.token_urlsafe(32)
    assets = os.path.dirname(__file__)
    statuses = {"NOT_FOUND": 404, "CONFLICT": 409, "INVALID": 400, "FORBIDDEN": 403, "IO_ERROR": 500}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Keep stdout usable by the saga host; the UI reports operation errors.

        def parse_request(self):
            if not super().parse_request():
                return False
            hosts = self.headers.get_all("Host", [])
            if len(hosts) != 1 or hosts[0] not in {f"127.0.0.1:{self.server.server_port}",
                                                 f"localhost:{self.server.server_port}"}:
                self.fail(LoreError("FORBIDDEN", "Host must be this local editor's address"))
                return False
            return True

        def send(self, status, body, content_type="application/json"):
            data = body.encode("utf-8", errors="backslashreplace")
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; "
                             "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def fail(self, error, status=None):
            self.send(status or statuses.get(error.code, 500), ops.to_json(error.as_dict()))

        def do_GET(self):
            path = urlsplit(self.path).path
            try:
                if path == "/api/ops":
                    result = {"ops": [{"name": op.name, "summary": op.summary, "writes": op.writes,
                                       "params": [p._asdict() for p in op.params]} for op in ops.OPS]}
                elif path == "/api/stamp":
                    result = {"stamp": stamp(root, config)}
                elif path in ASSETS:
                    name = "editor.html" if path == "/" else path[1:]
                    with open(os.path.join(assets, name), encoding="utf-8") as fh:
                        body = fh.read()
                    if path == "/":
                        body = body.replace("__LORE_TOKEN__", token).replace("__LORE_SAGA__", str(saga_mode).lower())
                        calendars = settings.get("calendars") or [{"id": "gregorian", "type": "gregorian"}]
                        body = body.replace("__LORE_CALENDARS__", html.escape(ops.to_json(calendars), quote=True))
                        body = body.replace("__LORE_NAME__", html.escape(str(settings.get("name") or os.path.basename(root)), quote=True))
                    self.send(200, body, ASSETS[path])
                    return
                else:
                    raise LoreError("NOT_FOUND", "No such editor resource")
                self.send(200, ops.to_json(result))
            except LoreError as exc:
                self.fail(exc)
            except OSError as exc:
                self.fail(LoreError("IO_ERROR", str(exc)))
            except Exception as exc:
                self.fail(LoreError("INTERNAL", str(exc)))

        def do_POST(self):
            try:
                # Read the (bounded) body before any early error reply: answering first and leaving
                # the body unread makes Windows reset the connection instead of delivering the error.
                try:
                    length = int(self.headers.get("Content-Length", "0") or 0)
                except ValueError:
                    length = -1
                body = self.rfile.read(length) if 0 < length <= 1024 * 1024 else b""
                # Require the token for every POST, including reads: one consistent client contract.
                if not secrets.compare_digest(self.headers.get("X-Lore-Token", ""), token):
                    raise LoreError("FORBIDDEN", "Missing or invalid editor token")
                if self.headers.get_content_type() != "application/json":
                    self.fail(LoreError("INVALID", "Content-Type must be application/json"), 415)
                    return
                path = urlsplit(self.path).path
                name = path[5:] if path.startswith("/api/") else ""
                op = ops.BY_NAME.get(name)
                if op is None:
                    raise LoreError("NOT_FOUND", "No such operation")
                if saga_mode and op.writes and name != "request":
                    raise LoreError("FORBIDDEN", "Saga edits must use change requests (request)")
                if self.headers.get("Transfer-Encoding"):
                    raise LoreError("INVALID", "Use Content-Length, not Transfer-Encoding")
                if not 0 < length <= 1024 * 1024:
                    raise LoreError("INVALID", "JSON body must be between 1 byte and 1 MiB")
                args = json.loads(body.decode("utf-8"))
                if not isinstance(args, dict):
                    raise LoreError("INVALID", "Arguments must be a JSON object")
                result = ops.run(name, args, root=root, config=config,   # ops.run checks parameter types
                                 **({"project": factory()} if factory else {}))
                self.send(200, ops.to_json(result))
            except LoreError as exc:
                self.fail(exc)
            except (ValueError, TypeError, UnicodeError, RecursionError) as exc:
                self.fail(LoreError("INVALID", str(exc)))
            except OSError as exc:
                self.fail(LoreError("IO_ERROR", str(exc)))
            except Exception as exc:   # a reply, never a dropped connection
                self.fail(LoreError("INTERNAL", str(exc)))

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    return server, f"http://127.0.0.1:{server.server_port}/", token


def serve(root, port=0, saga=False, config=None, factory=None):
    server, url, _ = make_server(root, port, saga, config, factory)
    print(f"Lorekeeper editor: {url}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0
