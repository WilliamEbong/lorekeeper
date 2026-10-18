# Plan 001: core

## Technical context
- **Language.** Python ≥3.11, standard library only (constitution I). On this machine it is 3.14.3.
- **Tests.** `unittest`, under `tests/`. Run with `python -m unittest discover -s tests -t .`.
- **Packaging.** The package is the flat folder `lorekeeper/`, with no subfolders, because the sagas vendor it flat into `_system/vendor/lorekeeper/`. It uses relative imports only. `pyproject.toml` comes in 007.

## File structure
```
lorekeeper/
  __init__.py     __version__ = "0.1.0"
  __main__.py     python -m lorekeeper  ->  cli.main()
  fm.py           restricted frontmatter: parse, values, minimal-line update   [Codex]
  store.py        Project/Item, schema defaults, scanning, links, ids/paths, versions, atomic write, merge/409
  ops.py          LoreError, Param, Op, OPS table, run(), to_json()
  cli.py          argparse adapter generated from OPS
  mcp.py          stdio JSON-RPC MCP adapter (dual-era) generated from OPS      [Codex]
tests/
  fixtures/world/ small project: lore.json plus a dozen items (CRLF and LF files, comments, quoted values, aliases)
  test_fm.py      [Codex]
  test_store.py
  test_cli.py
  test_mcp.py     [Codex]  includes the golden MCP-vs-CLI test
  test_rules.py   stdlib-only import scan; no bare open(); every op appears in CLI and MCP
  test_sagas.py   saga Wiki round trip + load (skipped if the sagas are absent)
  test_perf.py    3,000 synthetic items load in under 1.5 s
```

## Contracts

### fm.py
```python
class FrontmatterError(ValueError): line: int        # e.g. an unterminated block
class Frontmatter:
    fields: dict            # key -> str | list[str], in file order (first occurrence wins)
    lines: dict             # key -> 1-based line number in the file
    unsupported: list       # 1-based line numbers of non key/comment/blank lines (incl. duplicate keys)
    body: str               # everything after the closing '---' line
    newline: str            # '\n' or '\r\n'; the style of the opening line
def parse(text: str) -> Frontmatter | None   # None when the text does not start with a frontmatter block
def parse_value(raw: str) -> str | list[str]
def format_value(value: str | list[str]) -> str
def update(text, set=None, unset=(), body=None) -> str
    # Edit only the touched lines. A key whose parsed value is unchanged keeps its original bytes.
    # New keys go before the closing '---'. Text without frontmatter gets a new block at the top.
def link_target(value: str) -> str | None   # '[[A/B|c]]' -> 'B'; None if not a wikilink
```
A leading BOM is preserved. Line endings are preserved per line, and new lines use `Frontmatter.newline`.

### store.py
```python
DEFAULT_SCHEMA: dict                      # types / roles / properties (FR-6)
class Item: id, type, name, path (posix, relative to root), line_of(key), fields, body, version, aliases
class Project:
    @classmethod open(start_dir) -> Project            # find lore.json upward
    __init__(root, config: dict | None)                # config None -> read root/lore.json if present
    items: list[Item]; schema: dict (merged)
    find(name_or_id) -> Item                           # LoreError NOT_FOUND
    resolve(link_value) -> Item | None
    links(item) -> {role: [Item|str]}                  # str = unresolved target name
    backlinks(item) -> {role: [Item]}
    findings() -> list[dict]                           # structural (DUPLICATE_ID, DUPLICATE_NAME, BROKEN_LINK, UNSUPPORTED_FRONTMATTER, BAD_FRONTMATTER)
    create(type, name, fields, body) -> Item
    update(item, set, unset, body, version, expect) -> (version, merged)
def atomic_write(path, text)                           # temp file + os.replace; one retry on PermissionError
def sha256(bytes) -> str
```
The project is loaded fresh on every operation (stateless). This is fast enough at the required scale (SC-5).
- ponytail: per-operation full reload. If an editor session needs better, add an mtime-keyed cache in 005.

### ops.py
```python
class LoreError(Exception): code, message, data
Param = namedtuple("Param", "name kind required help")   # kind: str|int|bool|list|dict
Op = namedtuple("Op", "name summary params writes handler")   # handler(project, **args) -> dict
OPS: list[Op]                       # ordered; the single source for CLI, MCP and HTTP
def run(name, args: dict, root=None, config=None, project=None) -> dict
def to_json(result) -> str          # json.dumps(result, ensure_ascii=False, indent=2)
```
`init` is the one op that runs without an existing project.

### cli.py
- **Parser.** The argparse subparsers are generated from `OPS`. Required `str` params are positional, in table order. Other params become `--name`: `list` uses `action=append`, `dict` takes repeatable `k=v`, and `bool` is `store_true`.
- **Commands outside the table.** `mcp` and (from 005) `serve` are adapters, not ops.
- **Output.** `--json` prints `to_json(result) + "\n"`. Otherwise findings print as `FAIL|WARN CODE detail path:line`, lists print one line each, and anything else prints as JSON.

### mcp.py
- **Entry points.** `handle(msg, root) -> dict | None` is pure and testable; `serve(root, inp, out)` is the loop.
- **Tool schema.** Each `Param` maps to JSON Schema: str→string, int→integer, bool→boolean, list→array of strings, dict→object of strings. `required` comes from the required params.
- **Results.** Text = `to_json(result)`, and `structuredContent` = the result.

## Design decisions
- **Wikilinks** stay quoted in frontmatter, as Obsidian requires. Lists are inline, as the saga regex requires.
- **Merge.** It is per key ("compare-and-swap on the keys you edited") rather than a full three-way merge. Flat dicts make the two equivalent, and it needs no stored base copy.
- **Ids** follow the saga convention: `CHAR-…`, `EVENT-…`, `LOC-…`, `ORG-…`, `TECH-…`, `CH`.
- **Dates** are stored as written. Their meaning arrives in 002.
