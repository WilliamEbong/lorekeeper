"""The one operations table. The CLI, MCP server and HTTP API are generated from OPS."""
import json
import os
from collections import namedtuple

from . import store
from .store import LoreError, Project

Param = namedtuple("Param", "name kind required help")   # kind: str | int | bool | list | dict
Op = namedtuple("Op", "name summary params writes handler")


def to_json(result):
    return json.dumps(result, ensure_ascii=False, indent=2)


# ---- handlers: (project, **args) -> JSON-able dict ---------------------------
def op_init(root, name=None):
    path = os.path.join(root, store.CONFIG)
    if os.path.exists(path):
        raise LoreError("CONFLICT", f"{store.CONFIG} already exists in {root}")
    config = {"lorekeeper": 1, "name": name or os.path.basename(os.path.abspath(root)),
              "types": {}, "roles": {}, "properties": {}}
    store.atomic_write(path, to_json(config) + "\n", create=True)
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
    back = {roles.get(role, {}).get("inverse", f"{role} (from)"): [i.name for i in src]
            for role, src in p.backlinks(it).items()}
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


def op_link(p, item, role, target):
    it, other = p.find(item), p.find(target)
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
    version, merged = p.update(it, {role: value}, (), None, it.version, {role: it.fields.get(role)})
    return {"path": it.path, "version": version, "merged": merged}


def op_unlink(p, item, role, target):
    it = p.find(item)
    other = p.resolve(store.fm.link_target(target) or target)   # None: the link may point nowhere
    current = _role_values(it, role)
    wanted = (store.fm.link_target(target) or target).strip().lower()
    keep = [v for v, t in zip(current, _targets(p, current))
            if not (t is other if other else (store.link_parts(v) or ("",))[0].lower() == wanted)]
    if len(keep) == len(current):
        raise LoreError("NOT_FOUND", f"{it.name} has no {role} link to {target}")
    single = p.schema["roles"].get(role, {}).get("single") or not isinstance(it.fields.get(role), list)
    sets, unsets = ({}, [role]) if not keep else ({role: keep[0] if single and len(keep) == 1 else keep}, [])
    version, merged = p.update(it, sets, unsets, None, it.version, {role: it.fields.get(role)})
    return {"path": it.path, "version": version, "merged": merged}


def op_check(p):
    found = p.findings()
    found.sort(key=lambda f: (f["severity"] != "FAIL", f["path"], f["line"], f["code"]))
    fails = sum(f["severity"] == "FAIL" for f in found)
    return {"findings": found, "fail": fails, "warn": len(found) - fails}


S, I, B, L, D = "str", "int", "bool", "list", "dict"
OPS = [
    Op("init", "Create lore.json (default schema) in the project folder.",
       [Param("name", S, False, "project name")], True, op_init),
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
        Param("target", S, True, "target item")], True, op_link),
    Op("unlink", "Remove a role link.",
       [Param("item", S, True, "subject item"), Param("role", S, True, "role key"),
        Param("target", S, True, "target item")], True, op_unlink),
    Op("check", "Check the project; FAIL lines are definite problems, WARN lines possible ones.",
       [], False, op_check),
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
