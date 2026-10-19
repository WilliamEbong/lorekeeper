"""`lore` command line, generated from the operations table."""
import argparse
import json
import os
import sys

from . import __version__, fm, ops, store
from .store import LoreError

ADAPTERS = {"mcp": "Run the MCP server on stdin/stdout for AI agents.",
            "serve": "Open the local interactive editor."}


def key_value(text):
    key, sep, value = text.partition("=")
    if not sep or not key:
        raise argparse.ArgumentTypeError(f"expected KEY=VALUE, got {text!r}")
    return key.strip(), fm.parse_value(value.strip())


def build_parser():
    ap = argparse.ArgumentParser(prog="lore", description="Lorekeeper: a plain-text story-world engine.")
    ap.add_argument("--version", action="version", version=f"lore {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    for parser, default in ((ap, None), (common, argparse.SUPPRESS)):
        parser.add_argument("--root", default=default, help="project folder (default: nearest folder with lore.json)")
        parser.add_argument("--json", action="store_true", default=default or False, help="print JSON")
        parser.add_argument("--config", default=default, metavar="FILE",
                            help="settings file to use instead of lore.json (then --root is the project folder)")
    sub = ap.add_subparsers(dest="op", required=True, metavar="command")
    for op in ops.OPS:
        sp = sub.add_parser(op.name, parents=[common], help=op.summary,
                            description=f"{op.summary} {op.guide}".strip())
        for p in op.params:
            flag = "--" + p.name.replace("_", "-")
            if p.kind == "str" and p.required:
                sp.add_argument(p.name, help=p.help)
            elif p.kind == "str" and p.name == "item":   # lore wiki [NAME]
                sp.add_argument(p.name, nargs="?", help=p.help)
            elif p.kind == "bool":
                sp.add_argument(flag, dest=p.name, action="store_true", default=None, help=p.help)
            elif p.kind == "list":
                sp.add_argument(flag, dest=p.name, action="append", metavar="VALUE", help=p.help)
            elif p.kind == "dict":
                sp.add_argument(flag, dest=p.name, action="append", type=key_value, metavar="KEY=VALUE", help=p.help)
            else:
                sp.add_argument(flag, dest=p.name, type=int if p.kind == "int" else str, help=p.help)
    for name, summary in ADAPTERS.items():
        sp = sub.add_parser(name, parents=[common], help=summary, description=summary)
        if name == "serve":
            sp.add_argument("--port", type=int, default=0, help="local port (default: choose a free port)")
            sp.add_argument("--saga", action="store_true", help="queue change requests instead of editing canon")
        else:
            sp.add_argument("--saga", action="store_true",
                            help="offer only reading and the story-wiki fact tools (Wiki pages stay with the pipeline)")
    return ap


def span(start, end):
    return start["text"] + (f" to {end['text']}" if end and end["text"] != start["text"] else "")


def interval(when):
    """The written date, plus the range it was read as when that is wider."""
    if when is None:
        return "none"
    return when["text"] + (f" ({when['from']} to {when['to']})" if when["from"] != when["to"] else "")


def chapters(start, end):
    return "" if start is None else f"[ch {start}]" if end is None else f"[ch {start}-{end}]"


def wiki_text(result):
    when = "complete" if result["as_of"] is None else f"as of chapter {result['as_of']}"
    if "groups" in result:
        lines = [f"Story wiki, {when}: {result['count']} entries"]
        for group in result["groups"]:
            lines.append(f"{group['label']} ({group['count']})")
            lines += [f"  {e['name']}" + (f"  (also {', '.join(e['also'])})" if e["also"] else "")
                      + ("" if e["appears"] is None else f"  ch {e['appears']}") for e in group["entries"]]
        return "\n".join(lines)
    lines = [f"{result['name']} ({result['type']}), {when}"]
    if result["appears"] is not None:
        lines.append(f"Appears in chapter {result['appears']}")
    if result["also"]:
        lines.append(f"Also: {', '.join(result['also'])}")
    if result["names"]:
        lines.append("Names: " + ", ".join(f"{n['name']} {chapters(n['from'], n['to'])}".strip() for n in result["names"]))
    for section in result["sections"]:
        lines += ["", f"## {section['heading'] or '(untitled)'}"]
        for f in section["facts"]:
            tags = [chapters(f["from"], f["to"])] + ([f"as {f['as']}"] if f.get("as") else []) \
                + (["worked out"] if f.get("worked_out") else [])
            lines.append(f"- {f['text']}  " + " ".join(t for t in tags if t))
        if not section["facts"]:
            lines.append("  (nothing yet)")
    if not result["sections"]:
        lines.append("No story facts recorded yet.")
    return "\n".join(lines)


def human(op, args, result):
    """Plain text for people; --json prints the data unchanged."""
    at = args.get("at")
    if op == "wiki":
        return wiki_text(result)
    if op == "fact-add":
        return f"Added to {result['item']} › {result['section']}: {result['text']} {chapters(result['from'], result['to'])}" \
            + (f" (new story page {result['path']})" if result["created"] else "")
    if op == "fact-end":
        return f"{result['item']} › {result['section']}: {result['text']} {chapters(result['from'], result['to'])}"
    if op == "fact-remove":
        return f"Removed from {result['item']} › {result['section']}: {result['removed']}"
    if op == "timeline":
        rows = [(span(i["start"], i["end"]), i) for i in result["items"]]
        width = max((len(d) for d, _ in rows), default=0)
        return "\n".join(f"{d:<{width}}  {i['type']:<13} {i['name']}" for d, i in rows) or "(no items)"
    if op == "age":
        return f"{result['item']} at {at}: {result['text']}"
    if op == "when":
        lines = [result["name"], f"start: {interval(result['start'])}", f"end: {interval(result['end'])}"]
        return "\n".join(lines + [f"unreadable {u['key']}: {u['value']}" for u in result["unparsed"]])
    if op == "where":
        if not result["location"]:
            return f"By {at}, {result['item']} has no recorded location."
        doubt = " Some dates overlap, so this may not be the latest." if result["uncertain"] else ""
        return (f"By {at}, {result['item']} was last at {result['location']} "
                f"({result['event']}, {result['since']['text']}).{doubt}")
    if op == "knows":
        def names(rows):
            return ", ".join(f"{k['item']} (from {k['learned_in']})" for k in rows)
        parts = [f"knows {names(result['knows'])}"] if result["knows"] else []
        if result["may_know"]:
            parts.append(f"may know {names(result['may_know'])}")
        return f"By {at}, {result['item']} " + ("; ".join(parts) or "has learned nothing on record") + "."
    if "findings" in result:
        lines = [f"{f['severity']} {f['code']} {f['detail']} {f['path']}:{f['line']}" for f in result["findings"]]
        return "\n".join(lines + [f"{result['fail']} FAIL, {result['warn']} WARN"])
    if "items" in result:
        return "\n".join(f"{i['type']:<13} {i['name']}  ({i['path']})" for i in result["items"]) or "(no items)"
    return ops.to_json(result)


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")
    ns = build_parser().parse_args(argv)
    try:
        config = None
        if ns.config and ns.op != "init":   # settings kept elsewhere (a saga's _system/lorekeeper.json)
            root = os.path.abspath(ns.root or ".")
            if not os.path.isdir(root):
                raise LoreError("NOT_FOUND", f"--root {root} is not a folder")
            try:
                with open(ns.config, encoding="utf-8") as fh:
                    config = json.load(fh)
            except OSError as exc:
                raise LoreError("NOT_FOUND", f"cannot read --config {ns.config}: {exc.strerror}") from exc
            except ValueError as exc:
                raise LoreError("INVALID", f"--config {ns.config} is not valid JSON: {exc}") from exc
            if not isinstance(config, dict):
                raise LoreError("INVALID", f"--config {ns.config} must hold a JSON object")
        else:
            # --root names the project or a folder inside it; a mistyped one must not read as an empty world
            root = (ns.root or ".") if ns.op == "init" else store.find_root(ns.root or ".")
        if ns.op == "mcp":
            from . import mcp
            return mcp.serve(root, config=config, saga=ns.saga)
        if ns.op == "serve":
            from . import serve
            return serve.serve(root, port=ns.port, saga=ns.saga, config=config)
        op = ops.BY_NAME[ns.op]
        args = {p.name: getattr(ns, p.name, None) for p in op.params}
        for p in op.params:
            if p.kind == "dict" and args[p.name] is not None:
                args[p.name] = dict(args[p.name])
        result = ops.run(ns.op, args, root=root, config=config)
    except LoreError as exc:
        if ns.json:
            print(ops.to_json(exc.as_dict()))
        print(f"ERROR {exc.code} {exc.message}", file=sys.stderr)
        return 2
    print(ops.to_json(result) if ns.json else human(ns.op, args, result))
    return 1 if result.get("fail") else 0
