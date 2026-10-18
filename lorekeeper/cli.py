"""`lore` command line, generated from the operations table."""
import argparse
import sys

from . import __version__, fm, ops, store
from .store import LoreError

ADAPTERS = {"mcp": "Run the MCP server on stdin/stdout for AI agents."}


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
    sub = ap.add_subparsers(dest="op", required=True, metavar="command")
    for op in ops.OPS:
        sp = sub.add_parser(op.name, parents=[common], help=op.summary, description=op.summary)
        for p in op.params:
            flag = "--" + p.name.replace("_", "-")
            if p.kind == "str" and p.required:
                sp.add_argument(p.name, help=p.help)
            elif p.kind == "bool":
                sp.add_argument(flag, dest=p.name, action="store_true", default=None, help=p.help)
            elif p.kind == "list":
                sp.add_argument(flag, dest=p.name, action="append", metavar="VALUE", help=p.help)
            elif p.kind == "dict":
                sp.add_argument(flag, dest=p.name, action="append", type=key_value, metavar="KEY=VALUE", help=p.help)
            else:
                sp.add_argument(flag, dest=p.name, type=int if p.kind == "int" else str, help=p.help)
    for name, summary in ADAPTERS.items():
        sub.add_parser(name, parents=[common], help=summary, description=summary)
    return ap


def human(result):
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
        root = ns.root
        if ns.op == "mcp":
            from . import mcp
            return mcp.serve(root or store.find_root("."))
        op = ops.BY_NAME[ns.op]
        args = {p.name: getattr(ns, p.name, None) for p in op.params}
        for p in op.params:
            if p.kind == "dict" and args[p.name] is not None:
                args[p.name] = dict(args[p.name])
        result = ops.run(ns.op, args, root=root or ("." if ns.op == "init" else store.find_root(".")))
    except LoreError as exc:
        if ns.json:
            print(ops.to_json(exc.as_dict()))
        print(f"ERROR {exc.code} {exc.message}", file=sys.stderr)
        return 2
    print(ops.to_json(result) if ns.json else human(result))
    return 1 if result.get("fail") else 0
