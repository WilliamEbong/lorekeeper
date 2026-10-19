"""Project loading, link resolution and safe writes for a folder of Markdown items."""
import copy
import hashlib
import json
import os
import re
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from . import dates, fm

CONFIG = "lore.json"
SKIP_DIRS = {".git", ".obsidian", "_TEMPLATES", "node_modules", "__pycache__"}
RESERVED = {"id", "type", "canonical_name", "name", "aliases", "tags", "status"}
KEY = re.compile(r"[a-z_]+\Z")   # keys we write: exactly what the saga regex reads
LINK = re.compile(r"\s*(\[\[[^\]]+\]\])\s*(.*)\Z", re.S)   # "[[X]] +2h" -> ("[[X]]", "+2h")
BAD_NAME = re.compile(r"[\[\]|#^/\\\x00-\x1f]")   # cannot appear inside a wikilink
BAD_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
DEVICE = re.compile(r"\A(con|prn|aux|nul|com[1-9\xb9\xb2\xb3]|lpt[1-9\xb9\xb2\xb3])(?= *(?:\.|\Z))", re.I)

DEFAULT_SCHEMA = {
    "types": {
        "character": {"label": "Character", "plural": "Characters", "id_prefix": "CHAR", "category": "person",
                      "sections": ["Names", "Current state", "Where", "Beliefs", "Knows", "Wants", "Relationships", "Important events"]},
        "location": {"label": "Location", "plural": "Locations", "id_prefix": "LOC", "category": "place",
                      "sections": ["Names", "Controlled by", "Who is here", "Condition", "Important events"]},
        "event": {"label": "Event", "plural": "Events", "id_prefix": "EVENT", "category": "event"},
        "organization": {"label": "Organization", "plural": "Organizations", "id_prefix": "ORG", "category": "group",
                      "sections": ["Names", "Leaders", "Members", "Goals", "Territory", "Allies and enemies", "Standing", "Important events"]},
        "technology": {"label": "Technology", "plural": "Technology", "id_prefix": "TECH", "category": "thing",
                      "sections": ["Names", "Kind", "Held by", "Where", "Condition", "What it does", "Important events"]},
        "item": {"label": "Item", "plural": "Items", "id_prefix": "ITEM", "category": "thing",
                      "sections": ["Names", "Kind", "Held by", "Where", "Condition", "What it does", "Important events"]},
        "chapter": {"label": "Chapter", "plural": "Chapters", "id_prefix": "CH", "category": "narrative"},
    },
    "roles": {
        "participants": {"label": "Participants", "inverse": "Took part in", "to": ["character", "organization"]},
        "location": {"label": "Location", "inverse": "Events here", "to": ["location"], "single": True},
        "member_of": {"label": "Member of", "inverse": "Members", "to": ["organization"]},
        "parent": {"label": "Parent", "inverse": "Children", "to": ["character"]},
        "spouse": {"label": "Spouse", "inverse": "Spouse of", "to": ["character"]},
        "located_in": {"label": "Located in", "inverse": "Contains", "to": ["location"], "single": True},
        "after": {"label": "After (finish-to-start)", "inverse": "Followed by", "to": []},
        "same_start": {"label": "Starts with", "inverse": "Starts with", "to": []},
        "same_end": {"label": "Ends with", "inverse": "Ends with", "to": []},
        "sf": {"label": "Starts before end of", "inverse": "Ends after start of", "to": []},
        "learns": {"label": "Reveals", "inverse": "Learned in", "to": []},
        "revealed_as": {"label": "Revealed to be", "inverse": "Also known as", "to": [], "single": True},
        "kind": {"label": "Kind", "inverse": "Examples", "to": [], "single": True},
    },
    "properties": {
        "born": {"label": "Born", "format": "date"},
        "died": {"label": "Died", "format": "date"},
        "date": {"label": "Date", "format": "date"},
        "end": {"label": "End", "format": "date"},
        "date_min": {"label": "Earliest date", "format": "date"},
        "date_max": {"label": "Latest date", "format": "date"},
        "status": {"label": "Status", "format": "text"},
    },
}


class LoreError(Exception):
    def __init__(self, code, message, data=None):
        super().__init__(message)
        self.code, self.message, self.data = code, message, data or {}

    def as_dict(self):
        return {"error": {"code": self.code, "message": self.message, **({"data": self.data} if self.data else {})}}


def sha256(data):
    return hashlib.sha256(data).hexdigest()


_WRITE_LOCK = threading.Lock()


def file_sha(path):
    try:
        with open(path, "rb") as fh:
            return sha256(fh.read())
    except FileNotFoundError:
        return None


def atomic_write(path, text, expect=None, create=False):
    """Write via a unique temp file in the same folder, then swap it in.

    expect: the sha256 the file must still have at the moment of the swap (checked
    before every attempt). create: the file must not exist; never overwrites.
    One retry after 0.5 s for OneDrive locks.
    """
    # ponytail: a per-process lock; separate processes can still race in the microseconds
    # between the check and the swap. Use OS file locking if that ever matters.
    data = text.encode("utf-8")
    folder = os.path.dirname(path) or "."
    try:
        os.makedirs(folder, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix=".lk-", suffix=".tmp", dir=folder)
    except OSError as exc:
        raise LoreError("IO_ERROR", f"could not write {path}: {exc}") from exc
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        if not create and os.name != "nt" and os.path.exists(path):   # mkstemp made it owner-only
            os.chmod(tmp, os.stat(path).st_mode & 0o7777)
        for attempt in (1, 2):
            with _WRITE_LOCK:
                if expect is not None and file_sha(path) != expect:
                    raise LoreError("CONFLICT", f"{path} changed during the write; retry", {"version": file_sha(path)})
                try:
                    if not create:
                        os.replace(tmp, path)
                    elif os.name == "nt":
                        os.rename(tmp, path)          # Windows rename never overwrites
                    else:
                        os.link(tmp, path)            # fails if path exists
                    return sha256(data)
                except FileExistsError:
                    raise LoreError("CONFLICT", f"file already exists: {path}")
                except PermissionError:
                    if attempt == 2:
                        raise
            time.sleep(0.5)
    except OSError as exc:
        raise LoreError("IO_ERROR", f"could not write {path}: {exc}") from exc
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def inside(root, path):
    root, path = os.path.realpath(root), os.path.realpath(path)
    return path == root or path.startswith(root.rstrip(os.sep) + os.sep)


def _slurp(path):
    with open(path, "rb") as fh:
        return fh.read()


def find_root(start="."):
    """The nearest folder at or above start that holds lore.json."""
    here = os.path.abspath(start)
    while not os.path.isfile(os.path.join(here, CONFIG)):
        parent = os.path.dirname(here)
        if parent == here:
            raise LoreError("NOT_FOUND", f"no {CONFIG} in {os.path.abspath(start)} or its parents (run: lore init)")
        here = parent
    return here


def link_parts(value):
    """'[[A|b]] +2h' -> ('A', '+2h'); None when the value is not a link."""
    m = LINK.match(value) if isinstance(value, str) else None
    target = m and fm.link_target(m[1])
    return (target, m[2].strip()) if target else None


def slug(text):
    return re.sub(r"[^A-Z0-9]+", "-", text.upper()).strip("-")


def merged_schema(config):
    schema = copy.deepcopy(DEFAULT_SCHEMA)
    for section in ("types", "roles", "properties"):
        schema[section].update(config.get(section, {}))
    for key, value in config.items():
        if key not in schema:
            schema[key] = value
    return schema


def finding(severity, code, detail, path, line=1):
    return {"severity": severity, "code": code, "detail": detail, "path": path, "line": line}


class Item:
    def __init__(self, path, text, version, front):
        self.path, self.text, self.version, self.fm = path, text, version, front
        f = front.fields
        self.fields = f
        self.type = str(f.get("type", ""))
        self.stem = os.path.splitext(os.path.basename(path))[0]
        self.name = str(f.get("canonical_name") or f.get("name") or self.stem)
        self.id = str(f.get("id") or "")
        aliases = f.get("aliases", [])
        self.aliases = aliases if isinstance(aliases, list) else [aliases] if aliases else []

    @classmethod
    def from_fields(cls, path, fields, body=""):
        """An item that lives only in memory (e.g. a saga chapter card)."""
        text = fm.update("", set=clean_fields(fields), body=body)
        return cls(path, text, sha256(text.encode("utf-8")), fm.parse(text))

    @property
    def body(self):
        return self.fm.body

    def line(self, key):
        return self.fm.lines.get(key, 1)

    def summary(self):
        return {"id": self.id, "type": self.type, "name": self.name, "path": self.path}


class Project:
    def __init__(self, root, config=None):
        self.root = os.path.abspath(root)
        if config is None:
            cfg = os.path.join(self.root, CONFIG)
            config = {}
            if os.path.isfile(cfg):
                with open(cfg, encoding="utf-8") as fh:
                    try:
                        config = json.load(fh)
                    except ValueError as exc:
                        raise LoreError("INVALID", f"{CONFIG} is not valid JSON: {exc}") from exc
        if isinstance(config.get("paths"), str):   # "paths": "Wiki" means ["Wiki"]
            config["paths"] = [config["paths"]]
        self.config = config
        self.schema = merged_schema(config)
        self.calendars = dates.calendars(config.get("calendars"))
        self.problems = []
        self.items = []
        self._load()

    @classmethod
    def from_items(cls, root, config, items):
        """A project over given items, without scanning files."""
        p = cls.__new__(cls)
        p.root, p.config = os.path.abspath(root), config
        p.schema, p.calendars = merged_schema(config), dates.calendars(config.get("calendars"))
        p.problems, p.items = [], list(items)
        p._index()
        return p

    @classmethod
    def open(cls, start="."):
        return cls(find_root(start))

    # ---- loading -------------------------------------------------------
    def rel(self, path):
        prefix = self.root.rstrip(os.sep) + os.sep
        if path.startswith(prefix):          # the common case: a path os.walk built under root
            return path[len(prefix):].replace(os.sep, "/")
        return os.path.relpath(path, self.root).replace(os.sep, "/")

    def files(self):
        skip = SKIP_DIRS | set(self.config.get("exclude", []))
        story = self.config.get("story_wiki")
        plan = self.config.get("planning_wiki")
        plan = plan.get("folder") if isinstance(plan, dict) and isinstance(plan.get("folder"), str) else None
        layers = {os.path.normcase(os.path.normpath(os.path.join(self.root, f))) for f in (story, plan) if f}
        for base in self.config.get("paths", ["."]):
            top = os.path.normpath(os.path.join(self.root, base))
            if not inside(self.root, top):
                raise LoreError("INVALID", f"{CONFIG} path {base!r} is outside the project folder")
            for dirpath, dirnames, filenames in os.walk(top):
                if not inside(self.root, dirpath) or os.path.normcase(dirpath) in layers:   # elsewhere, story or planning
                    dirnames[:] = []
                    continue
                dirnames[:] = sorted(d for d in dirnames if d not in skip and not d.startswith("."))
                for name in sorted(filenames):
                    if name.endswith(".md") and not name.startswith("~$") and not name.endswith(".tmp"):
                        yield os.path.join(dirpath, name)

    def _load(self):
        paths = list(self.files())
        # file opens dominate on Windows (antivirus scans each one); overlap them, parse in order
        with ThreadPoolExecutor(max_workers=8) as pool:
            blobs = list(pool.map(_slurp, paths))
        for path, data in zip(paths, blobs):
            item = self.read(path, data)
            if item is not None:
                self.items.append(item)
        self._index()

    def _index(self):
        self.by_id, self.by_name, self.by_stem, self.by_alias = {}, {}, {}, {}
        self.by_path = {}
        self._linked = None
        for item in self.items:
            self._add(item)

    def _add(self, item):
        self.by_path[item.path] = item
        if item.id:
            if item.id.lower() in self.by_id:
                first = self.by_id[item.id.lower()]
                self.problems.append(finding("FAIL", "DUPLICATE_ID", f"{item.id} also in {first.path}",
                                             item.path, item.line("id")))
            else:
                self.by_id[item.id.lower()] = item
        key = item.name.lower()
        if key in self.by_name:
            self.problems.append(finding("FAIL", "DUPLICATE_NAME", f"{item.name} also in {self.by_name[key].path}",
                                         item.path, item.line("canonical_name")))
        else:
            self.by_name[key] = item
        self.by_stem.setdefault(item.stem.lower(), item)
        for alias in item.aliases:
            self.by_alias.setdefault(str(alias).lower(), item)
        self._linked = None   # links and backlinks are rebuilt on next use

    def _link_maps(self):
        if self._linked is None:
            links = {id(item): self._item_links(item) for item in self.items}
            back = {}
            for item in self.items:
                for role, found in links[id(item)].items():
                    for _, other, _ in found:
                        if other is not None:
                            back.setdefault(id(other), {}).setdefault(role, []).append(item)
            self._linked = links, back
        return self._linked

    def read(self, path, data=None):
        rel = self.rel(path)
        if data is None:
            data = _slurp(path)
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            self.problems.append(finding("FAIL", "BAD_ENCODING", f"not UTF-8: {exc.reason}", rel))
            return None
        try:
            front = fm.parse(text)
        except fm.FrontmatterError as exc:
            self.problems.append(finding("FAIL", "BAD_FRONTMATTER", str(exc), rel, exc.line))
            return None
        if front is None or not front.fields.get("type"):
            return None
        for line in front.unsupported:
            self.problems.append(finding("WARN", "UNSUPPORTED_FRONTMATTER", "line kept as-is, not read", rel, line))
        return Item(rel, text, sha256(data), front)

    def _item_links(self, item):
        out = {}
        for key, value in item.fields.items():
            if key in RESERVED:
                continue
            for v in value if isinstance(value, list) else [value]:
                parts = link_parts(v)
                if parts:
                    out.setdefault(key, []).append((parts[0], self.resolve(parts[0]), parts[1]))
        return out

    # ---- lookup --------------------------------------------------------
    def resolve(self, name):
        key = str(name).strip().lower()
        return self.by_name.get(key) or self.by_stem.get(key) or self.by_alias.get(key)

    def find(self, ref):
        if str(ref).startswith("path:"):
            item = self.by_path.get(ref[5:])
        else:
            item = self.by_id.get(str(ref).lower()) or self.resolve(fm.link_target(ref) or ref)
        if item is None:
            raise LoreError("NOT_FOUND", f"no item with reference {ref!r}")
        return item

    def links(self, item):
        return self._link_maps()[0][id(item)]

    def backlinks(self, item):
        return self._link_maps()[1].get(id(item), {})

    def findings(self):
        out = list(self.problems)
        types, roles = self.schema["types"], self.schema["roles"]
        for item in self.items:
            if item.type not in types:
                out.append(finding("WARN", "UNKNOWN_TYPE", f"type {item.type!r} is not in the schema",
                                   item.path, item.line("type")))
            for role, links in self.links(item).items():
                allowed = roles.get(role, {}).get("to") or []
                for target, other, _ in links:
                    if other is None:
                        out.append(finding("WARN", "BROKEN_LINK", f"{role} -> [[{target}]] matches no item",
                                           item.path, item.line(role)))
                    elif allowed and other.type not in allowed:
                        out.append(finding("WARN", "ROLE_TYPE", f"{role} -> [[{target}]] is a {other.type}, "
                                           f"expected {'/'.join(allowed)}", item.path, item.line(role)))
        return out + self._ambiguous()

    def _ambiguous(self):
        """A name, file stem or alias that two items claim: its links silently pick one of them."""
        out, claims = [], {}
        for item in self.items:
            name_line = item.line("canonical_name" if "canonical_name" in item.fields else "name")
            # Only real files claim a stem: saga cards share their architecture file's path.
            keys = [(item.name, "name", name_line)] + ([(item.stem, "stem", 1)] if item.path.endswith(".md") else [])
            keys += [(str(alias), "alias", item.line("aliases")) for alias in item.aliases]
            for label, kind, line in keys:
                first, first_kind = claims.setdefault(label.lower(), (item, kind))
                if label and first is not item and first.name.lower() != item.name.lower():   # that is DUPLICATE_NAME
                    out.append(finding("WARN", "AMBIGUOUS_NAME", f"[[{label}]] could mean {first.name} "
                                       f"({first.path}) or {item.name} ({item.path})", item.path, line))
        return out

    # ---- writes --------------------------------------------------------
    def make_id(self, type_, name):
        prefix = self.schema["types"].get(type_, {}).get("id_prefix") or type_.upper()
        return f"{prefix}-{slug(name)}"

    def path_for(self, type_, name):
        spec = self.schema["types"][type_]
        folder = spec.get("folder") or spec.get("plural") or type_
        base = self.config.get("paths", ["."])[0]
        stem = DEVICE.sub(r"\1_", BAD_FILENAME.sub("-", name).strip(" ."))   # Windows cannot hold Con.md
        path = os.path.normpath(os.path.join(self.root, base, folder, stem + ".md"))
        if not inside(self.root, path):
            raise LoreError("INVALID", f"type {type_!r} folder points outside the project folder")
        return path

    def check_name(self, name, item=None):
        """The stripped name, if it suits a wikilink and no other item answers to it."""
        name = name.strip() if isinstance(name, str) else ""
        if not name or BAD_NAME.search(name):
            raise LoreError("INVALID", "name must be one line without [ ] | # ^ / \\ (they break wikilinks)")
        other = self.resolve(name)
        if other is not None and (item is None or other.path != item.path):
            raise LoreError("CONFLICT", f"an item named {name!r} already exists: {other.path}")
        return name

    def create(self, type_, name, fields=None, body=None):
        fields = clean_fields(fields or {})
        if type_ not in self.schema["types"]:
            raise LoreError("INVALID", f"unknown type {type_!r}; add it to {CONFIG} types")
        if set(fields) & {"id", "type", "canonical_name", "name"}:
            raise LoreError("INVALID", "id, type and canonical_name are set by create, not by fields")
        name = self.check_name(str(name))
        path = self.path_for(type_, name)
        folder = os.path.dirname(path)
        if os.path.isdir(folder) and os.path.basename(path).lower() in {n.lower() for n in os.listdir(folder)}:
            raise LoreError("CONFLICT", f"file already exists: {self.rel(path)}")
        base_id, n = self.make_id(type_, name), 1
        while (base_id if n == 1 else f"{base_id}-{n}").lower() in self.by_id:
            n += 1
        values = {"id": base_id if n == 1 else f"{base_id}-{n}", "type": type_, "canonical_name": name, **fields}
        if body is None:   # a new story page starts with its type's sections (feature 010)
            starters = [] if self.config.get("story_wiki") else self.schema["types"][type_].get("sections") or []
            body = f"\n# {name}\n" + "".join(f"\n## {h}\n" for h in starters)
        text = fm.update("", set=values, body=str(body))
        version = atomic_write(path, text, create=True)
        item = self.read(path)
        item.version = version
        self.items.append(item)
        self._add(item)
        return item

    def update(self, item, set=None, unset=(), body=None, version=None, expect=None):
        """Apply an edit; merge onto a newer file when the edited keys are untouched, else CONFLICT."""
        set, unset = clean_fields(set or {}), list(unset or ())
        if "type" in unset or "type" in set and not "".join(set["type"]).strip():
            raise LoreError("INVALID", "type cannot be blank: an item without a type is no longer read")
        for key in ("canonical_name", "name"):
            if key in set and set[key] != item.fields.get(key):
                set[key] = self.check_name(set[key], item)
        path = os.path.join(self.root, item.path)
        with open(path, "rb") as fh:
            data = fh.read()
        current_version = sha256(data)
        text = data.decode("utf-8")
        merged = False
        if version and version != current_version:
            front = fm.parse(text)
            current = dict(front.fields) if front else {}
            current["body"] = front.body if front else text
            expect = expect or {}
            keys = list(set) + unset + (["body"] if body is not None else [])
            stale = [k for k in keys if k not in expect or blank(current.get(k)) != blank(expect[k])]
            if stale:
                raise LoreError("CONFLICT", f"{item.path} changed since it was read: {', '.join(stale)}",
                                {"version": current_version, "path": item.path,
                                 "current": {k: current.get(k) for k in stale}})
            merged = True
        new = fm.update(text, set=set, unset=unset, body=body)
        if new == text:
            return current_version, merged
        return atomic_write(path, new, expect=current_version), merged


def blank(value):
    return "" if value is None else value


def clean_fields(fields):
    out = {}
    for key, value in fields.items():
        if not KEY.match(key):
            raise LoreError("INVALID", f"bad key {key!r}: use lowercase letters and _")
        if isinstance(value, (list, tuple)):
            out[key] = [str(v) for v in value]
        else:
            out[key] = "" if value is None else str(value)
        if any("\n" in v or "\r" in v for v in (out[key] if isinstance(out[key], list) else [out[key]])):
            raise LoreError("INVALID", f"{key}: values must be a single line")
    return out
