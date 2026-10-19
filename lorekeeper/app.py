"""The Lorekeeper app: a start screen for people who never open a terminal.

`lore app` serves a page that lists the person's worlds, creates and opens worlds, opens sagas through
their own launcher, and writes instructions for AI assistants into every world it opens.
"""
import collections
import datetime
import importlib.util
import json
import os
import pathlib
import secrets
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import ThreadingHTTPServer
from urllib.parse import urlsplit
from urllib.request import urlopen

from . import ops, serve, store
from .store import LoreError

PORT = 8700   # the saga launchers use 8701-8703
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATES = ("novel", "series", "campaign")
GUIDE = os.path.join(".lore", "AI-GUIDE.md")
GUIDE_NOTE = "<!-- Written by Lorekeeper each time this world is opened from the Lorekeeper app. Edits here are replaced. -->"
POINTER = ("# Instructions for AI assistants\n\n"
           "This folder is a Lorekeeper story world. Before you read or change anything, read `.lore/AI-GUIDE.md`. "
           "It explains this world, how its parts connect, the exact commands to use, and the rules that keep "
           "the author's work safe.\n")
PAGES = {"/": ("app.html", "text/html"), "/app.js": ("app.js", "text/javascript"), "/app.css": ("app.css", "text/css"),
         "/editor.css": ("editor.css", "text/css"), "/favicon.svg": ("favicon.svg", "image/svg+xml")}


class AppError(Exception):
    """A problem to show a person, in plain words."""
    def __init__(self, message, status=400):
        super().__init__(message)
        self.status = status


# ---- places on this computer -----------------------------------------------------------------
def data_dir():
    base = os.environ.get("APPDATA")
    return os.path.join(base, "Lorekeeper") if base else os.path.join(os.path.expanduser("~"), ".lorekeeper")


def shell_folder(name):
    """A Windows shell folder (Personal = Documents, Desktop, Programs = Start menu), OneDrive-aware."""
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
            return os.path.expandvars(winreg.QueryValueEx(key, name)[0])
    except (ImportError, OSError):
        home = os.path.expanduser("~")
        return {"Personal": os.path.join(home, "Documents"), "Desktop": os.path.join(home, "Desktop")}.get(name, home)


def default_parent():
    return os.path.join(shell_folder("Personal"), "Lorekeeper worlds")


def console_python():
    """python.exe beside pythonw.exe: AI tools talk to Lorekeeper over a console's standard input and output."""
    folder, name = os.path.split(sys.executable)
    if name.lower() == "pythonw.exe" and os.path.isfile(os.path.join(folder, "python.exe")):
        return os.path.join(folder, "python.exe")
    return sys.executable


# ---- the list of worlds ------------------------------------------------------------------------
def worlds_file():
    return os.path.join(data_dir(), "worlds.json")


def load_worlds():
    try:
        with open(worlds_file(), encoding="utf-8") as fh:
            worlds = json.load(fh)
    except (OSError, ValueError):
        return []
    if not isinstance(worlds, list):
        return []
    worlds = [w for w in worlds if isinstance(w, dict) and isinstance(w.get("folder"), str)]
    return sorted(worlds, key=lambda w: str(w.get("opened", "")), reverse=True)


def save_worlds(worlds):
    store.atomic_write(worlds_file(), json.dumps(worlds, ensure_ascii=False, indent=2) + "\n")


def same(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


WORLDS_LOCK = threading.Lock()   # two tabs opening worlds at once must not lose an entry


def remember(folder, name, kind_, when=None):
    when = when or datetime.datetime.now().isoformat(timespec="seconds")
    with WORLDS_LOCK:
        worlds = [w for w in load_worlds() if not same(w["folder"], folder)]
        save_worlds([{"folder": os.path.abspath(folder), "name": name, "kind": kind_, "opened": when}] + worlds)


def forget(folder):
    with WORLDS_LOCK:
        save_worlds([w for w in load_worlds() if not same(w["folder"], folder)])


def kind(folder):
    if not os.path.isdir(folder):
        return "missing"
    if os.path.isfile(os.path.join(folder, "_system", "scripts", "saga.py")) and \
            os.path.isfile(os.path.join(folder, "_system", "lorekeeper.json")):
        return "saga"
    return "world" if os.path.isfile(os.path.join(folder, store.CONFIG)) else "folder"


def folder_name(name):
    """A world's name as a Windows folder name."""
    text = "".join(" " if c in '<>:"/\\|?*' or ord(c) < 32 else c for c in name)
    text = " ".join(text.split()).strip(" .")
    return text or "My world"


def world_settings(folder):
    try:
        with open(os.path.join(folder, store.CONFIG), encoding="utf-8") as fh:
            settings = json.load(fh)
    except (OSError, ValueError):
        return {}
    return settings if isinstance(settings, dict) else {}


def world_name(folder):
    return str(world_settings(folder).get("name") or os.path.basename(folder))


def create_world(name, template, folder):
    folder = os.path.abspath(folder)
    if kind(folder) == "saga":
        raise AppError(f"{folder} is a saga. Open it with Open a folder, or choose another name or place.", 409)
    if kind(folder) == "world":
        raise AppError(f"There is already a world in {folder}. Open it from Your worlds, or choose another name or place.", 409)
    made = not os.path.exists(folder)
    try:
        os.makedirs(folder, exist_ok=True)
        ops.run("init", {"name": name, "template": template}, root=folder)
    except LoreError as exc:
        if made and not os.listdir(folder):
            os.rmdir(folder)
        if exc.code == "CONFLICT":
            raise AppError(f"{folder} already holds files that this starting point would replace. "
                           "Choose another place, or start from Blank.", 409) from exc
        raise AppError(f"Lorekeeper could not set up the world: {exc.message}") from exc
    except OSError as exc:
        raise AppError(f"Lorekeeper could not create {folder}: {exc.strerror or exc}. "
                       "Choose a place you can save files in, such as Documents.") from exc
    return folder


# ---- instructions for AI assistants ----------------------------------------------------------
def cli_command(root):
    return f'"{console_python()}" "{HERE}" <operation> [arguments] --root "{root}" --json'


def ai_guide(root):
    root = os.path.abspath(root)
    p = store.Project(root)
    schema, config = p.schema, p.config
    counts = collections.Counter(item.type for item in p.items)
    run = f'"{console_python()}" "{HERE}"'
    lines = [GUIDE_NOTE, "", f"# AI guide: {config.get('name') or os.path.basename(root)}", "",
             "You are working in a **Lorekeeper story world**: an author's fictional world kept as plain Markdown files, "
             "one file per character, place, event, chapter or other item. Lorekeeper is the program that reads, edits "
             "and checks those files. The author is a writer, not a programmer: explain what you did in plain words, "
             "never in commands or file formats, unless they ask.", "",
             "## Start here", "",
             "1. **The author may be working at the same time** in the Lorekeeper editor, a page in their browser. "
             "It reloads within about two seconds of any file change, and every write is checked against the version "
             "it was based on, so neither of you overwrites the other.",
             "2. **Orient before acting.** Run `schema` (kinds of item, connections, fields), then `query` to find items "
             "and `show` to read one in full, including its `version`.",
             "3. **Change the world through Lorekeeper operations** (the command line below or the MCP tools), passing "
             "the `version` and the old values (`expect`) you read. On `CONFLICT`, read again and reconcile; never "
             "force an old draft through. If you edit a Markdown file directly, keep its frontmatter flat "
             "(`key: value`, lists inline) and change nothing else in it.",
             "4. **Check after every change.** Run `check` and report every FAIL and WARN with its file and line. "
             "Never move dates around just to make the report clean; contradictions are the author's call.",
             "5. **Never delete files**, never touch `.lore/` (Lorekeeper's own folder), and never rename items "
             "without being asked: links between items use their names.", "",
             "## This world", "",
             f"- **Folder:** `{root}`",
             f"- **Mode:** {'saga: edits become change requests for the host writing pipeline' if config.get('mode') == 'saga' else 'normal: operations edit the world directly'}",
             f"- **Run an operation:** `{run} <operation> [arguments] --root \"{root}\" --json`",
             f"  - for example `{run} schema --root \"{root}\" --json`, then `query --type character`, "
             "`show \"Name\"`, `check`. `--json` prints the same data the MCP tools return; leave it out for a short summary.",
             f"- **MCP:** `.mcp.json` in this folder registers a server named `lorekeeper` for clients that read it "
             f"(Claude Code does). For other clients, register the command `{console_python()}` with the arguments "
             f"`[\"{HERE}\", \"mcp\", \"--root\", \"{root}\"]`. The tools are the operations below.", "",
             "### Kinds of item", "", "| Kind (`type`) | Label | Folder | Items | Category |", "|---|---|---|---|---|"]
    for key, info in schema["types"].items():
        folder = os.path.dirname(p.rel(p.path_for(key, "x")))
        lines.append(f"| `{key}` | {info.get('label', key)} | `{folder}/` | {counts.get(key, 0)} | {info.get('category', '')} |")
    lines += ["", "### Connections", "",
              "A connection is a field whose value is a link such as `\"[[Mira Vale]]\"` (or a list of them). It is stored "
              "once, on the item it starts from; the other item shows it under the reverse label automatically.", "",
              "| Field | Label | Reverse label | Can point to |", "|---|---|---|---|"]
    for key, info in schema["roles"].items():
        targets = ", ".join(f"`{t}`" for t in info.get("to") or []) or "any kind"
        lines.append(f"| `{key}` | {info.get('label', key)} | {info.get('inverse', '')} | {targets} |")
    lines += ["", "### Fields", "", "| Field | Label | Format |", "|---|---|---|"]
    for key, info in schema["properties"].items():
        lines.append(f"| `{key}` | {info.get('label', key)} | {info.get('format', 'text')} |")
    wikis = [w for w, on in (("a story wiki (`story_wiki`: what a reader knows after each chapter)", config.get("story_wiki")),
                             ("a planning wiki (`planning_wiki`: the author's intended end state)", config.get("planning_wiki"))) if on]
    lines += ["", f"**Wikis:** this world has {' and '.join(wikis) if wikis else 'no story or planning wiki set up'}.", "",
              "## How everything connects", "",
              f"- **Settings.** `{store.CONFIG}` holds the world's name, its kinds of item, connections, fields, calendars, "
              "rules and checks. `schema` shows the effective result. Change settings only when the author asks.",
              "- **Items.** Each item is one Markdown file in its kind's folder. The frontmatter at the top holds `type`, "
              "`canonical_name`, an `id` and the fields; the prose below is the author's and is never rewritten by Lorekeeper. "
              "Items are found by ID, name, file name or alias.",
              "- **Connections** link items by name (above). A link to a name with no item is a `BROKEN_LINK` finding.",
              "- **Dates.** People have `born` and `died`; events and other items have `date` and `end`. Dates may be "
              "uncertain (`~1951`, `1990s`, ranges, `date_min`/`date_max`) or in a custom calendar. Lorekeeper keeps the "
              "uncertainty: a check that depends on it is a WARN, not a FAIL.",
              "- **Views.** The editor's Timeline, Subway, Relationships, Ages, Spreadsheet, Narrative and Wiki views are "
              "all drawn from the items and their fields. Nothing else is stored, so a correct item is a correct view.",
              "- **Checks.** `check` compares dates, connections and rules: someone taking part after their death, "
              "chapters out of order, links to the wrong kind of item. Each finding has a code, a severity and a file and line. "
              "The editor's Continuity tab shows the same findings.",
              "- **Wikis.** The story wiki records what a reader knows by each chapter, with chapter stamps such as `[ch 7]`. "
              "The planning wiki holds the author's plan, each fact citing its source document. Both are described in the "
              "reference below.",
              "- **Versions.** Every read returns a `version` (the file's sha256); every write states it. This is what "
              "keeps the author's editor and your changes from losing each other's work.", "",
              "---", ""]
    with open(os.path.join(HERE, "agent-skill.md"), encoding="utf-8") as fh:
        skill = fh.read()
    if skill.startswith("---"):   # drop the skill file's own frontmatter
        skill = skill.split("---", 2)[2].lstrip()
    return "\n".join(lines) + "\n" + skill.replace("# Lorekeeper agent skill", "# Lorekeeper reference", 1)


def write_if_changed(path, text):
    try:
        with open(path, encoding="utf-8", newline="") as fh:
            if fh.read() == text:
                return
    except OSError:
        pass
    store.atomic_write(path, text)


def write_ai_files(root):
    """The AI guide (refreshed), pointers for AGENTS.md and CLAUDE.md readers (only when missing), and MCP settings."""
    root = os.path.abspath(root)
    write_if_changed(os.path.join(root, GUIDE), ai_guide(root))
    for name, text in (("AGENTS.md", POINTER), ("CLAUDE.md", POINTER + "\n@.lore/AI-GUIDE.md\n")):
        if not os.path.lexists(os.path.join(root, name)):
            store.atomic_write(os.path.join(root, name), text, create=True)
    path = os.path.join(root, ".mcp.json")
    settings = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                settings = json.load(fh)
        except (OSError, ValueError):
            return   # a person's own file that Lorekeeper cannot read: leave it alone
        if not isinstance(settings, dict) or not isinstance(settings.get("mcpServers", {}), dict):
            return
    servers = settings.setdefault("mcpServers", {})
    old = servers.get("lorekeeper")
    # Lorekeeper's own entry ends with this world's folder (and --saga); anything else is the person's and stays.
    if old is not None and not (isinstance(old, dict) and isinstance(old.get("args"), list) and old["args"][1:4] == ["mcp", "--root", root]):
        return
    saga = world_settings(root).get("mode") == "saga"
    servers["lorekeeper"] = {"command": console_python(), "args": [HERE, "mcp", "--root", root] + (["--saga"] if saga else [])}
    write_if_changed(path, json.dumps(settings, ensure_ascii=False, indent=2) + "\n")


# ---- folder picker, file manager, sagas ------------------------------------------------------
PICKER = importlib.util.find_spec("_tkinter") is not None
PICK_LOCK = threading.Lock()
NO_PICKER = "The folder picker didn't open on this computer. Type the folder's location instead."


def pick_folder(title="Choose a folder", start=None):
    """The system folder picker, in front of the browser. None when the person cancels."""
    try:
        import tkinter
        from tkinter import filedialog
    except ImportError as exc:
        raise AppError(NO_PICKER, 503) from exc
    with PICK_LOCK:
        try:
            window = tkinter.Tk()
        except tkinter.TclError as exc:
            raise AppError(NO_PICKER, 503) from exc
        window.withdraw()
        window.attributes("-topmost", True)
        try:
            folder = filedialog.askdirectory(parent=window, title=title, mustexist=False,
                                             initialdir=start if start and os.path.isdir(start) else shell_folder("Personal"))
        finally:
            window.destroy()
    return os.path.normpath(folder) if folder else None


def show_folder(folder):
    if os.name == "nt":
        os.startfile(folder)
    else:
        webbrowser.open(pathlib.Path(folder).resolve().as_uri())


def saga_command(port):
    return [console_python(), os.path.join("_system", "scripts", "saga.py"), "timeline", "--port", str(port)]


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---- the start-screen server -----------------------------------------------------------------
class AppServer(ThreadingHTTPServer):
    allow_reuse_address = os.name != "nt"   # on Windows it would let a second copy share the port
    daemon_threads = True


class App:
    """What the start screen has opened: worlds served in this program, sagas in their own."""
    def __init__(self, url, token):
        self.url, self.token = url, token
        self.lock = threading.Lock()
        self.worlds, self.sagas = {}, {}

    def open_world(self, folder):
        folder = os.path.abspath(folder)
        key = os.path.normcase(folder)
        with self.lock:
            if key not in self.worlds:
                try:
                    server, url, _ = serve.make_server(folder, home=self.url)
                except ValueError as exc:
                    raise AppError(f"This world's settings file ({store.CONFIG}) can't be read, so it can't open. "
                                   "Restore it from a backup, or ask for help.") from exc
                threading.Thread(target=server.serve_forever, daemon=True).start()
                self.worlds[key] = (server, url)
            url = self.worlds[key][1]
        try:
            write_ai_files(folder)
        except (OSError, LoreError):
            pass   # the AI guide is a convenience; never stop a person opening their world over it
        remember(folder, world_name(folder), "world")
        return url

    def open_saga(self, folder):
        folder = os.path.abspath(folder)
        key = os.path.normcase(folder)
        with self.lock:
            running = self.sagas.get(key)
            if running and running[0].poll() is None:
                return running[1]
            port = free_port()
            process = subprocess.Popen(saga_command(port), cwd=folder, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            url = f"http://127.0.0.1:{port}/"
            for _ in range(200):   # up to 20 s while the saga loads its world
                if process.poll() is not None:
                    raise AppError("The saga's editor stopped while starting. Try the saga's own launcher.", 500)
                try:
                    socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                    break
                except OSError:
                    time.sleep(0.1)
            else:
                process.terminate()
                raise AppError("The saga's editor took too long to start. Try again, or use the saga's own launcher.", 500)
            self.sagas[key] = (process, url)
        remember(folder, os.path.basename(folder), "saga")
        return url

    def is_open(self, folder):
        key = os.path.normcase(os.path.abspath(folder))
        saga = self.sagas.get(key)
        return key in self.worlds or bool(saga and saga[0].poll() is None)

    def listing(self):
        worlds = [dict(w, kind=kind(w["folder"]), open=self.is_open(w["folder"])) for w in load_worlds()]
        return {"worlds": worlds, "parent": default_parent(), "picker": PICKER}


def text_arg(args, name, required=True):
    value = args.get(name)
    if value is None and not required:
        return None
    if not isinstance(value, str) or (required and not value.strip()):
        raise AppError({"name": "Give your world a name."}.get(name, f"Choose a {name}."))
    return value.strip()


def act_create(state, args):
    name = text_arg(args, "name")
    template = args.get("template") or None
    if template not in (None, *TEMPLATES):
        raise AppError("Choose one of the starting points.")
    parent = text_arg(args, "parent", required=False) or default_parent()
    folder = create_world(name, template, os.path.join(parent, folder_name(name)))
    return {"url": state.open_world(folder), "folder": folder}


def act_open(state, args):
    folder = os.path.abspath(text_arg(args, "folder"))
    found = kind(folder)
    if found == "missing":
        raise AppError("That folder can't be found. It may have been moved, renamed or deleted.", 404)
    if found == "saga":
        return {"url": state.open_saga(folder)}
    if found == "folder":
        if not args.get("make"):
            return {"offer": "make", "name": os.path.basename(folder)}
        create_world(os.path.basename(folder), None, folder)
    return {"url": state.open_world(folder)}


def act_pick(state, args):
    if not PICKER:
        raise AppError(NO_PICKER, 503)
    title = args.get("title") if isinstance(args.get("title"), str) else "Choose a folder"
    return {"folder": pick_folder(title[:80], args.get("start") if isinstance(args.get("start"), str) else None)}


def act_forget(state, args):
    forget(text_arg(args, "folder"))
    return {"forgotten": True}


def act_show(state, args):
    folder = text_arg(args, "folder")
    if not os.path.isdir(folder):
        raise AppError("That folder can't be found. It may have been moved, renamed or deleted.", 404)
    show_folder(folder)
    return {"shown": True}


def act_quit(state, args):
    return {"closed": True}


ACTIONS = {"create": act_create, "open": act_open, "pick": act_pick, "forget": act_forget, "show": act_show, "quit": act_quit}


class Handler(serve.LocalHandler):
    def reply(self, status, value):
        self.send(status, json.dumps(value, ensure_ascii=False))

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/hello":
            return self.reply(200, {"app": "lorekeeper"})
        if path == "/api/worlds":
            return self.reply(200, self.server.app.listing())
        if path not in PAGES:
            return self.reply(404, {"error": "There is nothing at this address."})
        name, content_type = PAGES[path]
        try:
            with open(os.path.join(HERE, name), encoding="utf-8") as fh:
                body = fh.read()
        except OSError:
            return self.reply(500, {"error": "Part of Lorekeeper is missing. Download Lorekeeper again."})
        self.send(200, body.replace("__LORE_TOKEN__", self.server.app.token) if path == "/" else body, content_type)

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            length = -1
        body = self.rfile.read(length) if 0 < length <= 64 * 1024 else b""
        if not secrets.compare_digest(self.headers.get("X-Lore-Token", ""), self.server.app.token):
            return self.reply(403, {"error": "This page is out of date. Reload it and try again."})
        action = ACTIONS.get(urlsplit(self.path).path.removeprefix("/api/"))
        if self.headers.get_content_type() != "application/json" or action is None or not body:
            return self.reply(400, {"error": "Lorekeeper didn't understand that request. Reload the page and try again."})
        try:
            args = json.loads(body.decode("utf-8"))
            if not isinstance(args, dict):
                raise ValueError("not an object")
            result = action(self.server.app, args)
        except AppError as exc:
            return self.reply(exc.status, {"error": str(exc)})
        except (ValueError, UnicodeError):
            return self.reply(400, {"error": "Lorekeeper didn't understand that request. Reload the page and try again."})
        except OSError as exc:
            return self.reply(500, {"error": f"Lorekeeper couldn't use that folder: {exc.strerror or exc}."})
        except Exception:   # a reply, never a dropped connection
            return self.reply(500, {"error": "Something went wrong in Lorekeeper. Close it and open it again."})
        self.reply(200, result)
        if action is act_quit:
            threading.Thread(target=stop_all, args=(self.server,), daemon=True).start()


def make_app(port=0):
    server = AppServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    server.app = App(url, secrets.token_urlsafe(32))
    return server, url, server.app.token


def stop_all(server):
    """Stop every open world and saga, then the start screen."""
    state = server.app
    with state.lock:
        for world, _ in state.worlds.values():
            world.shutdown()
            world.server_close()
        for process, _ in state.sagas.values():
            if process.poll() is None:
                process.terminate()
        state.worlds.clear()
        state.sagas.clear()
    server.shutdown()


def running(port):
    try:
        with urlopen(f"http://127.0.0.1:{port}/api/hello", timeout=1) as response:
            return json.loads(response.read().decode("utf-8")).get("app") == "lorekeeper"
    except (OSError, ValueError, AttributeError):
        return False


def run(port=PORT, browser=True):
    """Open the start screen; a second launch only brings it back up in the browser."""
    if running(port):
        webbrowser.open(f"http://127.0.0.1:{port}/")
        return 0
    try:
        server, url, _ = make_app(port)
    except OSError:   # a second double-click racing the first, or another program on the port
        time.sleep(1.5)
        if running(port):
            webbrowser.open(f"http://127.0.0.1:{port}/")
            return 0
        server, url, _ = make_app(0)
    print(f"Lorekeeper: {url}", flush=True)
    if browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop_all(server)   # serve_forever has ended, so its shutdown returns at once
        server.server_close()
    return 0


# ---- shortcuts ----------------------------------------------------------------------------------
def shortcut_spec():
    folder = os.path.dirname(sys.executable)
    windowless = os.path.join(folder, "pythonw.exe")
    return {"target": windowless if os.path.isfile(windowless) else sys.executable, "arguments": f'"{HERE}" app',
            "workdir": os.path.dirname(HERE), "icon": os.path.join(HERE, "lorekeeper.ico")}


def launch():
    """Start the app as the shortcut does: in the background, with no console window."""
    spec = shortcut_spec()
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen([spec["target"], HERE, "app"], cwd=spec["workdir"], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags, close_fds=True)


def install():
    """A Lorekeeper shortcut on the Desktop and in the Start menu (Windows)."""
    if os.name != "nt":
        print("Shortcuts are made on Windows only. Start Lorekeeper with: lore app")
        return []
    spec = shortcut_spec()
    script = ("$s = (New-Object -ComObject WScript.Shell).CreateShortcut($env:LK_LINK); $s.TargetPath = $env:LK_TARGET; "
              "$s.Arguments = $env:LK_ARGS; $s.WorkingDirectory = $env:LK_DIR; $s.IconLocation = $env:LK_ICON; "
              "$s.Description = 'Lorekeeper: your story worlds'; $s.Save()")
    links = []
    for place in (shell_folder("Desktop"), shell_folder("Programs")):
        link = os.path.join(place, "Lorekeeper.lnk")
        env = dict(os.environ, LK_LINK=link, LK_TARGET=spec["target"], LK_ARGS=spec["arguments"],
                   LK_DIR=spec["workdir"], LK_ICON=spec["icon"])
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", script],
                       env=env, check=True, capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        links.append(link)
    return links
