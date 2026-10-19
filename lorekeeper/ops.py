"""The one operations table. The CLI, MCP server and HTTP API are generated from OPS."""
import json
import os
import secrets
import time
from collections import namedtuple

from . import checks, dates, store, wiki
from .timeinfo import calendar_of, item_dates, parse_at, show_when
from .store import LoreError, Project

Param = namedtuple("Param", "name kind required help")   # kind: str | int | bool | list | dict
Op = namedtuple("Op", "name summary params writes handler guide", defaults=("",))   # guide: for AI readers


def to_json(result):
    return json.dumps(result, ensure_ascii=False, indent=2)


# ---- handlers: (project, **args) -> JSON-able dict ---------------------------
def op_init(root, name=None, template=None):
    from .templates import TEMPLATES

    path = os.path.join(root, store.CONFIG)
    if os.path.exists(path):
        raise LoreError("CONFLICT", f"{store.CONFIG} already exists in {root}")
    if template is not None and template not in TEMPLATES:
        raise LoreError("INVALID", "template must be novel, series or campaign")
    config = {"lorekeeper": 1, "name": name or os.path.basename(os.path.abspath(root)),
              "types": {}, "roles": {}, "properties": {}}
    starter = TEMPLATES.get(template)
    if starter:
        config.update(starter["config"])
        p = Project(root, config)
        # Check all destinations before creating lore.json; existing writing wins.
        targets = [p.path_for(item["type"], item["name"]) for item in starter["items"]]
        targets += [os.path.join(root, filename) for filename in starter["files"]]
        for target in targets:
            if not store.inside(root, target):
                raise LoreError("INVALID", "template destination is outside the project folder")
            folder = os.path.dirname(target)
            if os.path.lexists(target) or (os.path.isdir(folder) and
                    os.path.basename(target).lower() in {n.lower() for n in os.listdir(folder)}):
                raise LoreError("CONFLICT", f"template file already exists: {p.rel(target)}")
            while not os.path.exists(folder):
                folder = os.path.dirname(folder) or "."
            if not os.path.isdir(folder):
                raise LoreError("CONFLICT", f"template folder is a file: {folder}")
        for item in starter["items"]:
            if p.resolve(item["name"]):
                raise LoreError("CONFLICT", f"an item named {item['name']!r} already exists")
    store.atomic_write(path, to_json(config) + "\n", create=True)
    if starter:
        for item in starter["items"]:
            p.create(item["type"], item["name"], item["fields"], item["body"])
        for filename, text in starter["files"].items():
            store.atomic_write(os.path.join(root, filename), text, create=True)
    return {"created": store.CONFIG, "root": os.path.abspath(root)}


def op_schema(p):
    return p.schema


def op_query(p, type=None, tag=None, text=None, links_to=None):
    target = p.find(links_to) if links_to else None
    out = []
    for item in p.items:
        if type and item.type != type:
            continue
        tags = item.fields.get("tags", [])
        if tag and tag not in (tags if isinstance(tags, list) else [tags]):
            continue
        if text and text.lower() not in item.text.lower():
            continue
        if target and not any(o is target for links in p.links(item).values() for _, o, _ in links):
            continue
        out.append(item)
    out.sort(key=lambda i: (i.type, i.name.lower()))
    return {"items": [i.summary() for i in out], "count": len(out)}


def op_show(p, item):
    it = p.find(item)
    roles = p.schema["roles"]
    links = {role: [o.name if o else t for t, o, _ in ls] for role, ls in p.links(it).items()}
    back = {}
    for role, src in p.backlinks(it).items():   # roles may share an inverse label
        back.setdefault(roles.get(role, {}).get("inverse", f"{role} (from)"), []).extend(i.name for i in src)
    return {**it.summary(), "version": it.version, "fields": it.fields, "links": links,
            "backlinks": back, "body": it.body}


def op_create(p, type, name, field=None, body=None):
    it = p.create(type, name, field or {}, body)
    return {**it.summary(), "version": it.version}


def op_set(p, item, field=None, unset=None, version=None, expect=None, body=None):
    it = p.find(item)
    exp = dict(expect or {})
    if body is not None and "body" not in exp and version:
        raise LoreError("INVALID", "editing body with --version needs --expect body=<old body>")
    new_version, merged = p.update(it, field or {}, unset or [], body, version, exp)
    return {"path": it.path, "version": new_version, "merged": merged}


def _targets(p, values):
    return [p.resolve(parts[0]) if (parts := store.link_parts(v)) else None for v in values]


def _role_values(it, role):
    value = it.fields.get(role)
    return [] if value in (None, "") else value if isinstance(value, list) else [value]


def _check_link_version(p, it, role, version):
    if version is not None:
        current = store.file_sha(os.path.join(p.root, it.path))
        if version != current or version != it.version:
            raise LoreError("CONFLICT", f"{it.path} changed since it was read",
                            {"path": it.path, "version": current,
                             "current": {role: it.fields.get(role)}})


def op_link(p, item, role, target, version=None):
    it, other = p.find(item), p.find(target)
    _check_link_version(p, it, role, version)
    if not store.KEY.match(role) or role in store.RESERVED:
        raise LoreError("INVALID", f"{role!r} cannot be used as a role")
    current = _role_values(it, role)
    if other in _targets(p, current):
        return {"path": it.path, "version": it.version, "merged": False}
    link = f"[[{other.name}]]"
    if p.resolve(other.name) is not other:
        raise LoreError("INVALID", f"[[{other.name}]] would not resolve to {other.path}; rename one of them")
    single = p.schema["roles"].get(role, {}).get("single")
    if single and current:
        raise LoreError("CONFLICT", f"{it.name} already has {role} {current[0]}; unlink it first")
    value = link if single else current + [link]
    version, merged = p.update(it, {role: value}, (), None,
                              version if version is not None else it.version,
                              None if version is not None else {role: it.fields.get(role)})
    return {"path": it.path, "version": version, "merged": merged}


def op_unlink(p, item, role, target, version=None):
    it = p.find(item)
    _check_link_version(p, it, role, version)
    try:
        other = p.find(target)
    except LoreError as exc:
        if exc.code != "NOT_FOUND":
            raise
        other = None   # The link may point nowhere.
    current = _role_values(it, role)
    wanted = (store.fm.link_target(target) or target).strip().lower()

    def gone(v, t):
        parts = store.link_parts(v)
        if parts is None:              # plain text, not a wikilink: match by its text
            return v.strip().lower() == wanted
        return t is other if other else parts[0].lower() == wanted
    keep = [v for v, t in zip(current, _targets(p, current)) if not gone(v, t)]
    if len(keep) == len(current):
        raise LoreError("NOT_FOUND", f"{it.name} has no {role} link to {target}")
    single = p.schema["roles"].get(role, {}).get("single") or not isinstance(it.fields.get(role), list)
    sets, unsets = ({}, [role]) if not keep else ({role: keep[0] if single and len(keep) == 1 else keep}, [])
    version, merged = p.update(it, sets, unsets, None,
                              version if version is not None else it.version,
                              None if version is not None else {role: it.fields.get(role)})
    return {"path": it.path, "version": version, "merged": merged}


def op_when(p, item):
    it = p.find(item)
    start, end, bad = item_dates(p, it)
    return {**it.summary(), "start": show_when(p, start), "end": show_when(p, end),
            "unparsed": [{"key": k, "value": v} for k, v in bad]}


def op_age(p, item, at):
    it = p.find(item)
    birth, death, _ = item_dates(p, it)
    if birth is None:
        raise LoreError("INVALID", f"{it.name} has no start date (born/date/start)")
    when = parse_at(p, at)
    if p.schema["types"].get(it.type, {}).get("category") != "person":
        death = None
    return {"item": it.name, "at": show_when(p, when), **dates.age(birth, when, death, calendar_of(p, birth))}


def op_timeline(p, type=None, since=None, until=None):
    lo = parse_at(p, since).lo if since else None
    hi = parse_at(p, until).hi if until else None
    rows = []
    for it in p.items:
        start, end, _ = item_dates(p, it)
        if start is None or (type and it.type != type):
            continue
        last = (end or start).hi
        if (lo is not None and last <= lo) or (hi is not None and start.lo >= hi):
            continue
        rows.append((start.lo, last, it.name.lower(), it, start, end))
    rows.sort(key=lambda r: r[:3])
    return {"items": [{**it.summary(), "start": show_when(p, s), "end": show_when(p, e)}
                      for *_, it, s, e in rows], "count": len(rows)}


def op_convert(p, date):
    when = dates.parse(date, p.calendars)
    if when is None:
        raise LoreError("INVALID", f"no calendar in this project can read {date!r}")
    return {"input": date, "parsed_by": when.calendar, "precision": when.precision,
            "calendars": {c.id: {"from": c.format(when.lo, when.precision), "to": c.format(when.hi - 1, when.precision)}
                          for c in p.calendars}}


def _events_of(p, person):
    """(start, item) for every dated item the person takes part in, earliest first."""
    out = []
    for it in p.backlinks(person).get("participants", []):
        start = item_dates(p, it)[0]
        if start is not None:
            out.append((start, it))
    return sorted(out, key=lambda pair: (pair[0].lo, pair[0].hi))


def op_where(p, item, at):
    who, when = p.find(item), parse_at(p, at)
    placed = [(s, it, place) for s, it in _events_of(p, who) if s.lo <= when.lo
              for place in [next((o for _, o, _ in p.links(it).get("location", []) if o), None)] if place]
    if not placed:
        return {"item": who.name, "at": show_when(p, when), "location": None, "event": None}
    start, event, place = placed[-1]
    # uncertain when the event may fall after the date, or any earlier event may in fact be later
    uncertain = start.hi - 1 > when.lo or any(s.hi - 1 > start.lo for s, _, _ in placed[:-1])
    return {"item": who.name, "at": show_when(p, when), "location": place.name,
            "event": event.name, "since": show_when(p, start), "uncertain": uncertain}


def op_knows(p, item, at):
    who, when = p.find(item), parse_at(p, at)
    known, maybe = {}, {}
    for start, event in _events_of(p, who):
        if start.lo >= when.hi:
            continue
        bucket = known if start.hi - 1 <= when.lo else maybe
        for target, other, _ in p.links(event).get("learns", []):
            bucket.setdefault(other.name if other else target, event.name)
    for name in known:
        maybe.pop(name, None)
    return {"item": who.name, "at": show_when(p, when),
            "knows": [{"item": k, "learned_in": v} for k, v in known.items()],
            "may_know": [{"item": k, "learned_in": v} for k, v in maybe.items()]}


def op_graph(p):
    """Everything an editor or agent needs in one call: items with dates and versions, and links."""
    items, links = [], []
    for it in p.items:
        start, end, _ = item_dates(p, it)
        items.append({**it.summary(), "version": it.version, "fields": it.fields,
                      "start": show_when(p, start), "end": show_when(p, end),
                      "lo": start.lo if start else None, "hi": (end or start).hi if start else None})
        for role, targets in p.links(it).items():
            links += [{"from": it.id or it.name, "role": role, "to": (o.id or o.name) if o else t,
                       "from_path": it.path, "to_path": o.path if o else None,
                       "resolved": o is not None, "lag": lag} for t, o, lag in targets]
    return {"items": items, "links": links, "roles": p.schema["roles"], "types": p.schema["types"],
            "properties": p.schema["properties"]}


def requests_dir(p):
    folder = p.config.get("requests_dir") or os.path.join(p.root, ".lore", "requests")
    return folder if os.path.isabs(folder) else os.path.join(p.root, folder)


def op_request(p, item, note, field=None, unset=None, version=None, expect=None):
    """Queue a change request instead of editing (saga mode): the pipeline applies it later."""
    it = p.find(item)
    stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    rid = f"{stamp}-{store.slug(it.name)[:40].lower()}-{secrets.token_hex(3)}"
    body = {"id": rid, "item": it.name, "path": it.path, "version": it.version, "note": note,
            "set": store.clean_fields(field or {}), "unset": list(unset or []),
            "current": {k: it.fields.get(k) for k in list(field or {}) + list(unset or [])},
            "created_utc": stamp, "status": "open"}
    body["base_version"] = it.version if version is None else version
    body["base"] = body["current"].copy() if expect is None else dict(expect)
    if body["base_version"] != it.version or any(
            store.blank(value) != store.blank(it.fields.get(key)) for key, value in body["base"].items()):
        body["stale"] = True
    store.atomic_write(os.path.join(requests_dir(p), rid + ".json"), to_json(body) + "\n", create=True)
    return {"request": rid, "queued": True}


def op_requests(p):
    folder = requests_dir(p)
    out = []
    for name in sorted(os.listdir(folder)) if os.path.isdir(folder) else []:
        if name.endswith(".json"):
            with open(os.path.join(folder, name), encoding="utf-8") as fh:
                out.append(json.load(fh))
    return {"requests": out, "count": len(out)}


def op_import(p, file, into=None):
    """Bring an Aeon Timeline (.aeon) or CSV file into this project; existing names are never overwritten."""
    from . import interop
    csv_file = os.path.splitext(file)[1].lower() == ".csv"
    data = interop.read_csv(file) if csv_file else interop.read_aeon(file)   # read_aeon refuses non-Aeon files
    return {"file": file, **interop.import_into(p, data, into)}


def op_export(p, format, out):
    """Write the project as .aeon (Aeon Timeline), CSV (Aeon column ids) or one Markdown document."""
    from . import interop
    writer = {"aeon": interop.write_aeon, "csv": interop.write_csv, "md": interop.write_markdown}.get(format)
    if writer is None:
        raise LoreError("INVALID", "format must be aeon, csv or md")
    writer(p, out)
    return {"written": os.path.abspath(out), "format": format, "count": len(p.items)}


def op_wiki(p, item=None, as_of=None):
    if as_of is not None and as_of < 0:
        raise LoreError("INVALID", "as_of must be a chapter number, 0 or more; leave it out for the complete wiki")
    s = wiki.story(p)
    return s.index(as_of) if item is None else s.card(item, as_of)


def op_fact_add(p, item, section, text, to=None, version=None, type=None, **span):
    return wiki.fact_add(p, item, section, text, span["from"], to, version, type)


def op_fact_end(p, item, section, fact, after=None, reopen=None, version=None):
    return wiki.fact_end(p, item, section, fact, after, bool(reopen), version)


def op_fact_remove(p, item, section, fact, version=None):
    return wiki.fact_remove(p, item, section, fact, version)


def op_check(p):
    story = wiki.story(p)   # first: story names resolve links
    found = p.findings() + story.findings()
    for it in p.items:
        for key, value in item_dates(p, it)[2]:
            found.append(store.finding("WARN", "DATE_UNPARSED", f"{key}: {value}", it.path, it.line(key)))
    found += checks.run(p)
    found.sort(key=lambda f: (f["severity"] != "FAIL", f["path"], f["line"], f["code"]))
    fails = sum(f["severity"] == "FAIL" for f in found)
    return {"findings": found, "fail": fails, "warn": len(found) - fails}


S, I, B, L, D = "str", "int", "bool", "list", "dict"
KINDS = {S: str, I: int, B: bool, L: list, D: dict}
OPS = [
    Op("init", "Create lore.json, optionally with a starter world, in the project folder.",
       [Param("name", S, False, "project name"),
        Param("template", S, False, "starter world: novel | series | campaign")], True, op_init),
    Op("schema", "Show the effective schema: types, roles, properties and settings.", [], False, op_schema),
    Op("query", "List items, optionally filtered by type, tag, text or a link target.",
       [Param("type", S, False, "item type, e.g. character"), Param("tag", S, False, "tag to match"),
        Param("text", S, False, "case-insensitive text to find in the file"),
        Param("links_to", S, False, "only items that link to this item")], False, op_query),
    Op("show", "Show one item: fields, links, backlinks, body and version.",
       [Param("item", S, True, "item name or id")], False, op_show),
    Op("create", "Create an item file.",
       [Param("type", S, True, "item type"), Param("name", S, True, "canonical name"),
        Param("field", D, False, "frontmatter fields key=value"), Param("body", S, False, "Markdown body")],
       True, op_create),
    Op("set", "Set or remove fields; merges onto newer edits of other keys, else CONFLICT.",
       [Param("item", S, True, "item name or id"), Param("field", D, False, "fields to set, key=value"),
        Param("unset", L, False, "fields to remove"), Param("version", S, False, "version you read"),
        Param("expect", D, False, "values you read for the keys you edit"), Param("body", S, False, "new body")],
       True, op_set),
    Op("link", "Link an item to another under a role (e.g. participants, location).",
       [Param("item", S, True, "subject item"), Param("role", S, True, "role key"),
        Param("target", S, True, "target item"), Param("version", S, False, "version you read")], True, op_link),
    Op("unlink", "Remove a role link.",
       [Param("item", S, True, "subject item"), Param("role", S, True, "role key"),
        Param("target", S, True, "target item"), Param("version", S, False, "version you read")], True, op_unlink),
    Op("when", "Show an item's start and end as date intervals.",
       [Param("item", S, True, "item name or id")], False, op_when),
    Op("age", "Age of a person (or any dated item) at a date or at another item's start.",
       [Param("item", S, True, "person or item"), Param("at", S, True, "a date, or an item name")], False, op_age),
    Op("timeline", "Dated items in chronological order.",
       [Param("type", S, False, "only this type"), Param("since", S, False, "date or item: from"),
        Param("until", S, False, "date or item: until")], False, op_timeline),
    Op("convert", "Show a date in every calendar of the project.",
       [Param("date", S, True, "date text")], False, op_convert),
    Op("where", "Where a person last was at a date: their latest located event by then.",
       [Param("item", S, True, "person"), Param("at", S, True, "a date, or an item name")], False, op_where),
    Op("knows", "What a person has learned by a date (learns links on events they took part in).",
       [Param("item", S, True, "person"), Param("at", S, True, "a date, or an item name")], False, op_knows),
    Op("graph", "All items with dates, versions and fields, plus every link (for editors and agents).",
       [], False, op_graph),
    Op("request", "Queue a change request for an item instead of editing it (saga mode).",
       [Param("item", S, True, "item name or id"), Param("note", S, True, "what should change and why"),
        Param("field", D, False, "proposed values key=value"), Param("unset", L, False, "fields to remove"),
        Param("version", S, False, "version you read"), Param("expect", D, False, "draft baseline values")],
       True, op_request),
    Op("requests", "List queued change requests.", [], False, op_requests),
    Op("import", "Import an Aeon Timeline .aeon or a CSV file into this project (never overwrites).",
       [Param("file", S, True, "path to a .aeon or .csv file"),
        Param("into", S, False, "folder for the new items")], True, op_import),
    Op("export", "Export the project as aeon, csv or md.",
       [Param("format", S, True, "aeon | csv | md"), Param("out", S, True, "output file path")], True, op_export),
    Op("check", "Check the project; FAIL lines are definite problems, WARN lines possible ones.",
       [], False, op_check),
    Op("wiki", "Read the story wiki: the index of entries, or one entry's card, as the reader knows it by a chapter.",
       [Param("item", S, False, "entry name, alias, a name the reader knows it by, or key (path:...); "
                                "leave out for the index"),
        Param("as_of", I, False, "chapter number the reader has finished; leave out for the complete wiki")],
       False, op_wiki,
       "Use it before writing about the story at a given chapter, or to see what the reader already knows. "
       "Without item it returns the index: groups by type, each entry with name (the name the reader knows at "
       "as_of), type, key, page and appears (its first chapter), plus chapters (the chapter list). With item it "
       "returns the card: name, appears, names, also (identities folded into it), sections with facts (each with "
       "text, from, to, and as or worked_out when they apply), version (pass it to fact-add) and, in complete mode, "
       "fields and body. Progressive mode (as_of given) shows only facts true at that chapter and hides later pages "
       "(NOT_FOUND, like a page that does not exist). Example: {\"item\": \"Kresh\", \"as_of\": 5}."),
    Op("fact-add", "Add one chapter-stamped fact to an entry's story page (the only way AI should write wiki facts).",
       [Param("item", S, True, "entry name (or a name the reader knows it by)"),
        Param("section", S, True, "section heading, e.g. Beliefs, Where, Knows, Wants, Relationships, "
                                  "Important events, Names; created if missing"),
        Param("text", S, True, "the fact as one line, without a [ch …] stamp"),
        Param("from", I, True, "chapter from which the reader knows it"),
        Param("to", I, False, "last chapter it is still true in, for states that change (beliefs, places)"),
        Param("version", S, False, "the card's version you read; CONFLICT if the page changed since"),
        Param("type", S, False, "only when no entry has this name: create a standalone story page of this "
                                "type (story-wiki worlds)")],
       True, op_fact_add,
       "Use it after a chapter is written (in a saga, after it is frozen) to record what the reader learns. "
       "It appends '- text [ch from]' (or [ch from-to]) to the end of the section; in a world with a story_wiki "
       "folder it writes the entry's companion page there, creating it with the type's starter sections, and "
       "never touches the working page. Record a new name under section Names. Returns item, path, version, "
       "created, section, text, from and to. Example: {\"item\": \"Darius\", \"section\": \"Beliefs\", "
       "\"text\": \"Believes the far side is unarmed.\", \"from\": 2}."),
    Op("fact-end", "Mark a fact as no longer true after a chapter (or, with reopen, as current again).",
       [Param("item", S, True, "entry name"), Param("section", S, True, "section heading"),
        Param("fact", S, True, "the start of the fact's text (case and spacing ignored)"),
        Param("after", I, False, "last chapter the fact is true in"),
        Param("reopen", B, False, "clear the end instead (undo a fact-end)"),
        Param("version", S, False, "the card's version you read")],
       True, op_fact_end,
       "Use it when a belief, place, state or relationship changes: end the old fact, then fact-add the new one. "
       "It rewrites only that fact's stamp, so [ch 2] becomes [ch 2-5]; an unstamped fact starts at the page's "
       "first appearance. Returns item, path, version, text, from and to. Example: {\"item\": \"Darius\", "
       "\"section\": \"Beliefs\", \"fact\": \"Believes the far side\", \"after\": 5}."),
    Op("fact-remove", "Remove one fact from an entry's story page (to undo a mistaken fact-add).",
       [Param("item", S, True, "entry name"), Param("section", S, True, "section heading"),
        Param("fact", S, True, "the start of the fact's text (case and spacing ignored)"),
        Param("version", S, False, "the card's version you read")],
       True, op_fact_remove,
       "Use it only to take back a fact that was added by mistake; when something stops being true, use fact-end, "
       "because the reader still knew it until then. Returns item, path, version and the removed text. "
       "Example: {\"item\": \"Darius\", \"section\": \"Wants\", \"fact\": \"To go home\"}."),
]
BY_NAME = {op.name: op for op in OPS}


def run(name, args=None, root=None, config=None, project=None):
    op = BY_NAME.get(name)
    if op is None:
        raise LoreError("INVALID", f"unknown operation {name!r}")
    args = {k: v for k, v in (args or {}).items() if v is not None}
    known = {p.name for p in op.params}
    unknown = set(args) - known
    if unknown:
        raise LoreError("INVALID", f"unknown parameter(s) for {name}: {', '.join(sorted(unknown))}")
    missing = [p.name for p in op.params if p.required and p.name not in args]
    if missing:
        raise LoreError("INVALID", f"missing parameter(s) for {name}: {', '.join(missing)}")
    for p in op.params:   # JSON callers (MCP, HTTP) can send any type
        value = args.get(p.name)
        if value is not None and type(value) is not KINDS[p.kind]:
            raise LoreError("INVALID", f"{p.name} must be {p.kind}")
        if p.kind == L and value is not None and not all(isinstance(v, str) for v in value):
            raise LoreError("INVALID", f"{p.name} must be a list of strings")
    try:
        if name == "init":
            return op.handler(root or ".", **args)
        if project is None:
            project = Project(root, config) if root else Project.open(".")
        return op.handler(project, **args)
    except ValueError as exc:          # bad input caught deep down (e.g. the frontmatter writer)
        raise LoreError("INVALID", str(exc)) from exc
    except OSError as exc:
        raise LoreError("IO_ERROR", str(exc)) from exc
