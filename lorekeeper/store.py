"""Project loading, link resolution and safe writes for a folder of Markdown items."""
import copy
import hashlib
import json
import os
import re
import time

from . import fm

CONFIG = "lore.json"
SKIP_DIRS = {".git", ".obsidian", "_TEMPLATES", "node_modules", "__pycache__"}
RESERVED = {"id", "type", "canonical_name", "name", "aliases", "tags", "status"}
KEY = re.compile(r"[a-z_][a-z0-9_]*\Z")
LINK = re.compile(r"\s*(\[\[[^\]]+\]\])\s*(.*)\Z", re.S)   # "[[X]] +2h" -> ("[[X]]", "+2h")
BAD_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

DEFAULT_SCHEMA = {
    "types": {
        "character": {"label": "Character", "plural": "Characters", "id_prefix": "CHAR", "category": "person"},
        "location": {"label": "Location", "plural": "Locations", "id_prefix": "LOC", "category": "place"},
        "event": {"label": "Event", "plural": "Events", "id_prefix": "EVENT", "category": "event"},
        "organization": {"label": "Organization", "plural": "Organizations", "id_prefix": "ORG", "category": "group"},
        "technology": {"label": "Technology", "plural": "Technology", "id_prefix": "TECH", "category": "thing"},
        "item": {"label": "Item", "plural": "Items", "id_prefix": "ITEM", "category": "thing"},
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


def atomic_write(path, text):
    """Write via a temp file in the same folder, then replace; one retry for OneDrive locks."""
    data = text.encode("utf-8")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
        for attempt in (1, 2):
            try:
                os.replace(tmp, path)
                return sha256(data)
            except PermissionError:
                if attempt == 2:
                    raise
                time.sleep(0.5)
    except OSError as exc:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise LoreError("IO_ERROR", f"could not write {path}: {exc}") from exc


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
        self.name = str(f.get("canonical_name") or f.get("name") or os.path.splitext(os.path.basename(path))[0])
        self.id = str(f.get("id") or "")
        aliases = f.get("aliases", [])
        self.aliases = aliases if isinstance(aliases, list) else [aliases] if aliases else []

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
        self.config = config
        self.schema = merged_schema(config)
        self.problems = []
        self.items = []
        self._load()

    @classmethod
    def open(cls, start="."):
        return cls(find_root(start))

    # ---- loading -------------------------------------------------------
    def rel(self, path):
        return os.path.relpath(path, self.root).replace(os.sep, "/")

    def files(self):
        skip = SKIP_DIRS | set(self.config.get("exclude", []))
        for base in self.config.get("paths", ["."]):
            top = os.path.normpath(os.path.join(self.root, base))
            for dirpath, dirnames, filenames in os.walk(top):
                dirnames[:] = sorted(d for d in dirnames if d not in skip and not d.startswith("."))
                for name in sorted(filenames):
                    if name.endswith(".md") and not name.startswith("~$") and not name.endswith(".tmp"):
                        yield os.path.join(dirpath, name)

    def _load(self):
        for path in self.files():
            item = self.read(path)
            if item is not None:
                self.items.append(item)
        self.by_id, self.by_name, self.by_stem, self.by_alias = {}, {}, {}, {}
        for item in self.items:
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
            self.by_stem.setdefault(os.path.splitext(os.path.basename(item.path))[0].lower(), item)
            for alias in item.aliases:
                self.by_alias.setdefault(str(alias).lower(), item)
        self._links = {id(item): self._item_links(item) for item in self.items}
        self._back = {}
        for item in self.items:
            for role, links in self._links[id(item)].items():
                for target, other, _ in links:
                    if other is not None:
                        self._back.setdefault(id(other), {}).setdefault(role, []).append(item)

    def read(self, path):
        rel = self.rel(path)
        with open(path, "rb") as fh:
            data = fh.read()
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
        item = self.resolve(fm.link_target(ref) or ref) or self.by_id.get(str(ref).lower())
        if item is None:
            raise LoreError("NOT_FOUND", f"no item named or with id {ref!r}")
        return item

    def links(self, item):
        return self._links[id(item)]

    def backlinks(self, item):
        return self._back.get(id(item), {})

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
        return out

    # ---- writes --------------------------------------------------------
    def make_id(self, type_, name):
        prefix = self.schema["types"].get(type_, {}).get("id_prefix") or type_.upper()
        return f"{prefix}-{slug(name)}"

    def path_for(self, type_, name):
        spec = self.schema["types"][type_]
        folder = spec.get("folder") or spec.get("plural") or type_
        base = self.config.get("paths", ["."])[0]
        return os.path.normpath(os.path.join(self.root, base, folder, BAD_FILENAME.sub("-", name).strip(" .") + ".md"))

    def create(self, type_, name, fields=None, body=None):
        name = str(name).strip()
        if type_ not in self.schema["types"]:
            raise LoreError("INVALID", f"unknown type {type_!r}; add it to {CONFIG} types")
        if not name or "\n" in name:
            raise LoreError("INVALID", "name must be a single non-empty line")
        if self.resolve(name):
            raise LoreError("CONFLICT", f"an item named {name!r} already exists: {self.resolve(name).path}")
        path = self.path_for(type_, name)
        folder = os.path.dirname(path)
        if os.path.isdir(folder) and os.path.basename(path).lower() in {n.lower() for n in os.listdir(folder)}:
            raise LoreError("CONFLICT", f"file already exists: {self.rel(path)}")
        values = {"id": self.make_id(type_, name), "type": type_, "canonical_name": name}
        values.update(clean_fields(fields or {}))
        text = fm.update(f"\n# {name}\n" if body is None else body, set=values)
        version = atomic_write(path, text)
        item = self.read(path)
        item.version = version
        return item

    def update(self, item, set=None, unset=(), body=None, version=None, expect=None):
        """Apply an edit; merge onto a newer file when the edited keys are untouched, else CONFLICT."""
        set, unset = clean_fields(set or {}), list(unset or ())
        path = os.path.join(self.root, item.path)
        with open(path, "rb") as fh:
            data = fh.read()
        current_version = sha256(data)
        text = data.decode("utf-8")
        merged = False
        if version and version != current_version:
            front = fm.parse(text)
            current = front.fields if front else {}
            expect = expect or {}
            stale = [k for k in list(set) + unset if k not in expect or current.get(k, "") != (expect[k] or "")]
            if body is not None and ("body" not in expect or (front.body if front else text) != expect["body"]):
                stale.append("body")
            if stale:
                raise LoreError("CONFLICT", f"{item.path} changed since it was read: {', '.join(stale)}",
                                {"version": current_version, "path": item.path,
                                 "current": {k: current.get(k) for k in stale if k != "body"}})
            merged = True
        new = fm.update(text, set=set, unset=unset, body=body)
        if new == text:
            return current_version, merged
        with open(path, "rb") as fh:  # ponytail: tiny race window between this check and replace
            if sha256(fh.read()) != current_version:
                raise LoreError("CONFLICT", f"{item.path} changed during the write; retry", {"path": item.path})
        return atomic_write(path, new), merged


def clean_fields(fields):
    out = {}
    for key, value in fields.items():
        if not KEY.match(key):
            raise LoreError("INVALID", f"bad key {key!r}: use lowercase letters, digits and _")
        if isinstance(value, (list, tuple)):
            out[key] = [str(v) for v in value]
        elif isinstance(value, bool):
            out[key] = "true" if value else "false"
        else:
            out[key] = "" if value is None else str(value)
    return out
