# Feature 001: Core model, storage, operations, CLI and MCP

## Overview
Lorekeeper keeps a story world as plain Markdown files: one file per character, place, event, organisation or other item. Facts live in flat frontmatter, and links are Obsidian wikilinks. Feature 001 delivers:
- the on-disk format and a project file (`lore.json`)
- loading and link resolution
- safe concurrent writes
- one operations table
- the two adapters that come first: the `lore` command line and an MCP server

Later features plug into the same table: time (002), checks (003), the editor's HTTP API (005) and interop (006).

The format is deliberately the one the user's three saga Wikis already use, so a saga Wiki is a Lorekeeper project with no conversion.

## User scenarios
1. **A novelist starts a world.** `lore init` creates `lore.json`. `lore create character "Darius Cole" --field born=2001-03-14` writes `Characters/Darius Cole.md`. `lore show "Darius Cole"` prints the fields, links and backlinks.
2. **An AI agent works through MCP.** It calls `query`, `show`, `create`, `set`, `link` and `check` as MCP tools. Each tool returns exactly the JSON the CLI prints with `--json`.
3. **A human and an agent edit the same file at once.** If they change different keys, both edits survive (merge). If they change the same key, the second writer gets a conflict (409) with the current values, and nothing is lost.
4. **A saga.** Lorekeeper pointed at `Realm Saga/Wiki` loads every page. Reading and re-writing a page without changes reproduces it byte for byte. `check` reports structural problems in saga style (`FAIL <CODE> …`).
5. **Obsidian.** Files Lorekeeper writes open in Obsidian with working Properties and links.

## Functional requirements

### Format
- **FR-1 Item file.** An item is any `.md` file whose frontmatter has a non-empty `type`. The frontmatter is the first block, delimited by lines that are exactly `---` (CRLF tolerated).
  - **Recognised keys:** `id`, `type`, `canonical_name` (with fallbacks `name`, then the file stem), `aliases` (list), `tags` (list), `status` (`locked|committed|provisional|open`).
  - **Other keys:** anything else is a property or a role.
  - **Not items:** files without frontmatter, or without `type`, are notes. They are ignored without error.
- **FR-2 Restricted frontmatter.** Each line in the frontmatter block is one of:
  - `key: value`, where the key matches `[a-z_][a-z0-9_]*`
  - a comment (`# …`)
  - blank
  - anything else, which is kept verbatim but reported as `WARN UNSUPPORTED_FRONTMATTER <path>:<line>`

  Values are a scalar (bare, `"double"` or `'single'` quoted), an inline list `[a, "b", "[[X]]"]`, or empty.
- **FR-3 Byte-stable round trip.** Parsing a file and writing it back with no changes reproduces the exact bytes, including line endings, comments, key order, quoting and spacing. An edit rewrites only the lines of the keys it changes:
  - new keys are appended before the closing `---`
  - a removed key's line is deleted
  - the file's own line-ending style is kept
- **FR-4 Value writing.** Lists are written inline: `[a, b]`. A value is double-quoted when it is a wikilink, when it would otherwise parse differently (it starts with one of `[ { " ' # & * ! | > % @ `` ` ``, contains `: ` or ` #`, has leading or trailing spaces, or is empty inside a list), or when it contains a comma inside a list. Inside double quotes, `"` and `\` are backslash-escaped.
- **FR-5 Links.** A frontmatter value of the form `[[Target]]`, `[[Target|shown text]]` or `[[folder/Target]]` is a link.
  - **Resolution** (case-insensitive): an item whose `canonical_name` is `Target`, then whose file stem is `Target`, then whose `aliases` contain `Target`.
  - **Roles.** A key holding links is a *role*. Roles declared in `lore.json` carry labels, an inverse label and allowed types. Undeclared roles still work; their label is the key.
  - **Storage.** A link is stored once, on its subject. Backlinks (inverses) are computed at load time.
  - **Unresolved links** are reported as `WARN BROKEN_LINK`.

### Project
- **FR-6 `lore.json`.** It holds:
  - `"lorekeeper": 1` and `name`
  - `paths` (folders to scan; default `["."]`) and `exclude` (folder names; defaults always skipped: `.git`, `.obsidian`, `_TEMPLATES`, `node_modules`, and dot-folders)
  - `types` (`{key: {label, plural, folder, id_prefix, category}}`)
  - `roles` (`{key: {label, inverse, to: [types]}}`)
  - `properties` (`{key: {label, format}}`, with format one of `text|number|date|list|checkbox`)
  - keys reserved for later features: `calendars`, `rules`, `mode`

  A missing key falls back to the default schema. Its types are character, location, event, organization, item and chapter. Its roles are participants, location, member_of, parent, spouse, located_in, after, same_start, same_end, sf and learns.
- **FR-7 Root discovery.** The CLI looks for `lore.json` in `--root` or in the working folder and its parents. A host program (the saga engine) can also pass a config dict and a root directly, with no `lore.json`.
- **FR-8 Scanning.** Read every `*.md` under `paths`, skipping excluded folders and files named `~$*` or `*.tmp`. Read text as UTF-8 with `newline=""`.
  - **Duplicates.** Two items with the same `id`, for example an OneDrive conflict copy, give `FAIL DUPLICATE_ID`.
  - **Name collisions.** Two items whose names collide case-insensitively give `FAIL DUPLICATE_NAME`, since links to them would be ambiguous.
- **FR-9 Ids and paths for new items.**
  - **Id:** `id_prefix` (default: the type upper-cased) + `-` + the name upper-cased with runs of non-alphanumerics turned into `-`, for example `CHAR-DARIUS-COLE`.
  - **Path:** the type's `folder` (default: the plural label, e.g. `Characters/`) + `<Name>.md`, with characters invalid in Windows filenames replaced by `-`.
  - **Refusals:** an existing name (case-insensitive) or path is refused with `CONFLICT`.

### Safe writes
- **FR-10 Versions.** Every item read returns `version`, the sha256 of the file bytes.
- **FR-11 Atomic writes.** Write a temp file in the same folder, then `os.replace` it. Retry once after 0.5 s on `PermissionError` (OneDrive lock), then fail with `IO_ERROR`. Never leave a partial file.
- **FR-12 Merge or conflict.** An update carries `version` (optional) and `expect` (`{key: value the caller last saw}`, including `body` when the body is edited).
  - **Current version** (or no version given): apply the update.
  - **Stale version:** if every edited key's current value equals `expect`, apply the edit to the current file. Keys others changed are preserved; the result reports `"merged": true`.
  - **Otherwise:** fail with `CONFLICT` (HTTP 409) carrying the current version and values. The file is not touched.

### Operations
- **FR-13 One table.** Each operation is defined once: name, one-line summary, parameters (name, kind `str|int|bool|list|dict`, required, help), and whether it writes. The CLI, MCP and HTTP adapters are generated from this table, with no per-operation adapter code.
- **FR-14 Operations in 001:**
  - `init [name]`: create `lore.json` with the default schema. Refuse if one exists.
  - `schema`: the effective config (defaults merged).
  - `query [--type T] [--tag G] [--text S] [--links-to X]`: matching items as `{id, type, name, path}`, sorted by type then name.
  - `show ITEM`: `{id, type, name, path, version, fields, links{role:[names]}, backlinks{role:[names]}, body}`.
  - `create TYPE NAME [--field k=v …] [--body TEXT]`: returns the new item summary with its version.
  - `set ITEM [--field k=v …] [--unset k …] [--version V] [--expect k=v …]`: returns `{version, merged}`.
  - `link ITEM ROLE TARGET` / `unlink ITEM ROLE TARGET`: add or remove `"[[TARGET]]"` in the role's list. The role becomes a list if it held a single link. Writing goes through FR-12.
  - `check`: findings `[{severity, code, detail, path, line}]` plus counts. Later features add more checks here.
- **FR-15 Errors.** Every failure is a `LoreError(code, message, data)`. Codes: `NOT_FOUND`, `CONFLICT`, `INVALID`, `IO_ERROR`, `FORBIDDEN`.
  - **CLI:** prints `ERROR <CODE> <message>` to stderr (with `--json`, `{"error": {...}}` to stdout) and exits 2.
  - **MCP:** returns `isError: true` with the same JSON.
- **FR-16 CLI.** `lore [--root DIR] [--json] <op> …`.
  - **Human output:** findings as `FAIL|WARN <CODE> <detail> <path>:<line>`; lists as one line per item; other results as JSON.
  - **`--json` output:** `json.dumps(result, ensure_ascii=False, indent=2)` plus a newline.
  - **Exit codes:** 0 success; 1 when `check` reports any FAIL; 2 for errors and usage.
  - **Entry points:** `python -m lorekeeper` and a `lore` console script (packaged in 007).
- **FR-17 MCP server** (`lore mcp`): newline-delimited JSON-RPC 2.0 over stdio, dual-era.
  - **Legacy:** answers `initialize`. It echoes the client's `protocolVersion` if it is one of `2025-11-25`, `2025-06-18`, `2025-03-26` or `2024-11-05`, otherwise sends `2025-11-25`. Capabilities `{tools:{}}`, plus `serverInfo` and `instructions`. It ignores `notifications/*`.
  - **Modern (2026-07-28):** answers `server/discover` with `supportedVersions`, `capabilities`, `_meta["io.modelcontextprotocol/serverInfo"]` and `instructions`. A request whose `_meta["io.modelcontextprotocol/protocolVersion"]` it does not support gets error `-32022` with `data.supported` and `data.requested`. Modern results include `"resultType": "complete"`.
  - **Both eras:**
    - `ping` returns `{}`.
    - `tools/list` returns one tool per operation, with a JSON Schema built from the parameters.
    - `tools/call` returns `content:[{type:"text", text:<CLI --json text without the trailing newline>}]` plus `structuredContent:<result>`. An operation error gives `isError:true`; an unknown tool gives JSON-RPC error `-32602`; an unknown method gives `-32601`.
  - **Output channel:** nothing but JSON-RPC goes to stdout. It exits on end of input.

## Success criteria
- **SC-1 Round trip.** Every `.md` file of all three saga Wikis, copied to a temp folder, parses and re-serialises byte-identically. The test skips when the sagas are absent.
- **SC-2 Wikis load.** All three Wikis load with no FAIL findings caused by the parser.
- **SC-3 Golden test.** For `query`, `show`, `check` and `schema`, MCP `tools/call` text equals CLI `--json` stdout (minus its final newline), on a fixture project.
- **SC-4 Merge and conflict.** A concurrent-edit test: disjoint keys merge with both edits present; same key gives `CONFLICT` with the file untouched; a stale write never loses data.
- **SC-5 Speed.** A 3,000-item synthetic project loads in under 1.5 s on this machine.
- **SC-6 Stdlib only.** An import scan of `lorekeeper/*.py` finds only stdlib modules and relative imports.
- **SC-7 Encoding.** No text-mode `open(` call without `encoding=` (test-enforced).
- **SC-8 Obsidian keys.** Files written by `create`/`set`/`link` use flat keys and inline lists, and the saga's own frontmatter regex (`^([a-z_]+):[ \t]*(.*?)[ \t]*$`) reads them.
- **SC-9 One table.** Every operation in the table appears as a CLI subcommand and an MCP tool, and nothing else does.

## Defaults chosen (logged)
- Unresolved links are WARN, not FAIL: Obsidian allows placeholder links, and saga prose links to pages not yet written.
- Undeclared roles are allowed, so the schema never blocks an author.
- An update without `version` applies directly. The CLI reads and writes in one process, which leaves a microsecond race window. This is documented as a ponytail ceiling.
