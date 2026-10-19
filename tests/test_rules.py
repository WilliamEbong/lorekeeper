"""Standing rules: stdlib only, explicit utf-8, one ops table behind every face."""
import ast
import glob
import os
import sys
import unittest

from lorekeeper import cli, ops

PKG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "lorekeeper")
SOURCES = sorted(glob.glob(os.path.join(PKG, "*.py")))


def trees():
    for path in SOURCES:
        with open(path, encoding="utf-8") as fh:
            yield path, ast.parse(fh.read(), path)


class Rules(unittest.TestCase):
    def test_imports_are_stdlib_or_relative(self):
        bad = []
        for path, tree in trees():
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    mods = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    mods = [node.module]
                else:
                    continue
                bad += [f"{os.path.basename(path)}: {m}" for m in mods
                        if m.split(".")[0] not in sys.stdlib_module_names
                        and not (m == "lorekeeper.cli" and path.endswith("__main__.py"))]   # run as a folder
        self.assertEqual(bad, [])

    def test_every_text_open_has_encoding(self):
        bad = []
        for path, tree in trees():
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open":
                    mode = node.args[1].value if len(node.args) > 1 and isinstance(node.args[1], ast.Constant) else "r"
                    for kw in node.keywords:
                        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                            mode = kw.value.value
                    if "b" not in mode and not any(kw.arg == "encoding" for kw in node.keywords):
                        bad.append(f"{os.path.basename(path)}:{node.lineno}")
        self.assertEqual(bad, [])

    def test_package_is_flat(self):
        self.assertEqual([d for d in os.listdir(PKG) if os.path.isdir(os.path.join(PKG, d)) and d != "__pycache__"], [])

    def test_cli_subcommands_are_exactly_the_ops_table(self):
        sub = next(a for a in cli.build_parser()._actions if a.dest == "op")
        self.assertEqual(set(sub.choices) - set(cli.ADAPTERS), {op.name for op in ops.OPS})


if __name__ == "__main__":
    unittest.main()
