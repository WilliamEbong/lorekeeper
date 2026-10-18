---
name: lorekeeper
description: Read, edit and check a Markdown story world through Lorekeeper CLI or MCP, preserving canon, date uncertainty and concurrent edits.
---

# Lorekeeper agent skill

Use Lorekeeper when a project has `lore.json`, when the user requests structured chronology or continuity checks, or when a host writing pipeline delegates world-state work. Read the project's canon and approval rules first. Lorekeeper checks structured fields and links; it does not extract truth from prose automatically.

## Connect

For Claude Code or another client that reads `.mcp.json`, register this stdio server, substituting the absolute story folder:

```json
{
  "mcpServers": {
    "lorekeeper": {
      "command": "lore",
      "args": ["mcp", "--root", "/absolute/path/to/project"]
    }
  }
}
```

Windows paths may use forward slashes, for example `C:/Stories/My Novel`. For Codex or another client with different configuration storage, register the same command and arguments in that client's MCP settings; do not assume it reads `.mcp.json`. The `lore` executable must be on the client's PATH. The server reads one UTF-8 JSON-RPC object per line on stdin and writes responses on stdout. Do not send batches or Content-Length framing.

The implementation supports legacy `initialize` negotiation for `2025-11-25`, `2025-06-18`, `2025-03-26` and `2024-11-05`, plus modern `server/discover` and per-request metadata for `2026-07-28`. Modern requests supply `params._meta` with `io.modelcontextprotocol/protocolVersion` and `io.modelcontextprotocol/clientCapabilities`. Unsupported per-request versions return `-32022`. Tools are generated from the same operations table as the CLI. `tools/list` provides the current parameter schemas; `tools/call` returns both text and `structuredContent`. Notifications do not execute operations. Inspect a check result's `fail` and `warn` counts: findings do not by themselves set MCP `isError`.

## Read before writing

1. Call `schema` for effective types, roles, properties and settings. Use `query` to find relevant items, then `show` for the full fields, body and version. `graph` supplies all items, versions, dates and relationships in one call, plus the schema's types, roles and properties.
2. Preserve the exact version and original values for every field you will change or remove. `query` summaries do not include versions.
3. Use `set` with `version` and `expect`. On `CONFLICT`, reread and reconcile with the current file; never discard the version to force your old draft through.
4. Run `check` after edits. Read every finding, including WARNs. Report unresolved contradictions with their paths and line numbers; do not silently reschedule items to make the report clean.

References accept IDs, canonical names, filename stems and aliases. `path:Characters/Mira Vale.md` selects an exact project-relative path, useful when names are ambiguous. `at`, `since` and `until` accept a date or a reference to a dated item. An item reference covers its whole dated span, not just one instant. `where` reports the last recorded located participation at or before the query, with an uncertainty flag; it is not continuous location tracking. `knows` follows `learns` links on events the person participated in and separates definite knowledge from `may_know`; it does not infer secrets from prose.

## Operation reference

These are CLI examples. For MCP use the operation name as the tool name and an arguments object with the listed parameter names. Required string parameters are positional on the CLI. Optional parameters use flags; underscores become hyphens, for example `links_to` becomes `--links-to`. `field` and `expect` are objects in MCP and repeatable `--field key=value` / `--expect key=value` flags on the CLI. `unset` is an array in MCP and repeatable `--unset key` flags on the CLI. Values in MCP field objects should be strings or arrays of strings.

All examples below assume an initialized novel template unless stated otherwise. They illustrate individual operations, not a script to run from top to bottom. `<version>` and `<old body>` are placeholders for actual read values. Paths for import/export are relative to the process working directory unless absolute; `--root` selects the project but does not change that directory.

| Operation | Required parameters | Optional parameters | CLI example |
| --- | --- | --- | --- |
| `init` | none | `name`, `template` | `lore init --name "My Novel" --template novel` (new folder) |
| `schema` | none | none | `lore schema --json` |
| `query` | none | `type`, `tag`, `text`, `links_to` | `lore query --type event --text Letter --links-to "Mira Vale" --json` |
| `show` | `item` | none | `lore show "Mira Vale" --json` |
| `create` | `type`, `name` | `field`, `body` | `lore create event "Homecoming" --field "date=2025-04-10 18:00" --body "Mira returns."` |
| `set` | `item` | `field`, `unset`, `version`, `expect`, `body` | `lore set "The Letter" --field "date=2025-04-01 10:00" --version "<version>" --expect "date=2025-04-01 09:00"` |
| `link` | `item`, `role`, `target` | `version` | `lore link "Chapter 1" participants "Mira Vale" --version "<version>"` |
| `unlink` | `item`, `role`, `target` | `version` | `lore unlink "The Letter" participants "Mira Vale" --version "<version>"` |
| `when` | `item` | none | `lore when "The Letter" --json` |
| `age` | `item`, `at` | none | `lore age "Mira Vale" "The Letter" --json` |
| `timeline` | none | `type`, `since`, `until` | `lore timeline --type event --since 2025 --until 2026 --json` |
| `convert` | `date` | none | `lore convert "April 2, 2025" --json` |
| `where` | `item`, `at` | none | `lore where "Mira Vale" "2025-04-02 12:00" --json` |
| `knows` | `item`, `at` | none | `lore knows "Mira Vale" "2025-04-02 12:00" --json` |
| `graph` | none | none | `lore graph --json` |
| `request` | `item`, `note` | `field`, `unset`, `version`, `expect` | `lore request "The Letter" "Align with revised outline" --field "date=2025-04-01 10:00" --version "<version>" --expect "date=2025-04-01 09:00"` |
| `requests` | none | none | `lore requests --json` |
| `import` | `file` | `into` | `lore import notes.csv --into Imported` |
| `export` | `format`, `out` | none | `lore export md reading-copy.md` |
| `check` | none | none | `lore check --json` |

Global CLI options are `--root <project>`, `--json`, `--version` and help. `serve` and `mcp` are CLI adapters, not operations or MCP tools. Start the editor with `lore serve --root <project>`, optionally `--port 8765` or `--saga`; start MCP with `lore mcp --root <project>`. The editor prints its loopback URL; it does not automatically open a browser. CLI check exits 1 on any FAIL, 0 otherwise; operational errors exit 2. A `--json` operational error is printed as JSON on stdout and also described on stderr.

## Safe mutation details

`version` is a SHA-256 of the file bytes. `set` with a matching version applies the edit. If the version is stale, each edited or removed key must have an `expect` value matching the current file. Only then can the operation merge onto the newer file. A missing field can be represented by `""` in CLI expectations; copy original strings and lists exactly. Expectations are a merge baseline, not a substitute for `version` or an independent precondition when the version matches.

For example, after reading `show`, an MCP call can be:

```json
{
  "name": "set",
  "arguments": {
    "item": "The Letter",
    "field": {"date": "2025-04-01 10:00"},
    "version": "<version from show>",
    "expect": {"date": "2025-04-01 09:00"}
  }
}
```

To remove a field, use `unset` and include its old value in `expect`. Replacing `body` while supplying `version` always requires `expect.body`, even when the version is current. Use MCP for multiline bodies so shell quoting cannot alter them. CLI supports `--body "<new body>" --expect "body=<old body>"` with the actual text.

`link` and `unlink` accept `version` but not `expect`; a stale version is refused, so reread before retrying. Linking a role declared `single` refuses to replace an existing target. Unlink it explicitly first. Broken links can also be unlinked by their written target name. Always use the latest returned version for the next mutation.

`create` supplies `id`, `type` and `canonical_name`; do not override them through `field`. Names cannot contain brackets, pipe, hash, caret, slash, backslash or control characters. `init` is create-only, with `novel`, `series` and `campaign` as the optional templates. It does not apply templates to existing projects. Import skips existing names instead of replacing them; inspect the returned warnings. Export accepts `aeon`, `csv` or `md` and replaces its output file. There is no delete or automatic request-application operation.

In saga workflows use `request`, not direct writes, unless the host explicitly authorizes canon changes. Requests store proposed fields, removals, notes, current values and a base version/expectation snapshot. A stale baseline is marked `stale` rather than rejected; request creation does not establish that the change is safe to apply. `requests` lists the queued JSON records. The default directory is `.lore/requests`; the host can configure `requests_dir`. The host must reread canon, check impacts and apply approved changes through its own pipeline. Saga mode blocks direct HTTP writes other than requests, but does not restrict CLI/MCP operations.

## Storage and chronology conventions

- Use UTF-8 Markdown, one item per file. Frontmatter keys match `[a-z_]+`: lowercase letters and underscores, without digits. Keep values scalar or inline lists, never nested YAML. Quote wikilinks, for example `location: "[[Lantern Harbour]]"` and `participants: ["[[Mira Vale]]"]`. Body links are not structured relationships.
- Read `lore.json` before extending types, roles or properties. Those entries merge by key with defaults; an entry replaces the whole corresponding default definition. `calendars`, `rules` and `checks` control time and validation. `paths` and `exclude` control scans. Use a person's `max_age: none` for ageless beings; it disables the age ceiling, not birth/death checks.
- Preserve uncertainty. Supported Gregorian examples include `2025`, `2025-04`, `2025-04-02`, `2025-04-02 09:30`, `April 2, 2025`, `~2025`, `2025..2027`, `2040s`, `44 BC`, `2025 AD`, and notes in parentheses or after a comma. BCE and CE are also accepted. Use `when` or `convert` to inspect parsing. An `A..B` range expresses a possible date, while `date` plus `end` expresses a span. Do not turn year-only evidence into a definite day or invent a clock time.
- Start keys are read in priority order: `born`, `date`, `start`; end keys are `died`, `end`. `date_min`/`date_max` narrow starts; `duration` supplies an absent end for non-person items. Missing dates are not automatically failures. Custom calendars require configuration; do not assume invented datelines parse.
- For a canon gap that the host authorizes you to decide, decide and record the choice, rationale and provenance in its designated decisions log. Mark uncertain working dates with `(provisional)` or `status: provisional` and tell the user what was assumed. Never label an invented value as sourced canon. In saga projects follow their decide-and-record conventions and approval gates.
- `after` is finish-to-start, `same_start` start-to-start equality, `same_end` end-to-end equality, and `sf` this item's end at or after the target's start. Link text can include a duration lag, such as `"[[Departure]] +2d"`. These relationships are checked; they never auto-reschedule items.
- Monotonic rules use `rule`, `select`, `order` and optional `group`; maximum-duration rules use `rule: "max_duration"` and `max`; gap rules use `rule: "gap"`, `role`, optional `from` (`"end"` by default), and `exactly`, `min` or `max`. Rules can override `code` and set `severity: "warn"`. A name such as `RAIL_REGRESSION` is a configured code, not another rule kind.
- `checks.story_order` reads `narrative.md` and warns on definite chronology reversals. The browser Narrative view instead sorts `chapter` and `card` items by chapter/order/number or name. Session and book items do not appear in that view. Do not promise synchronized outline reordering.
- CSV extra fields require destination schema definitions. Markdown export has no matching report import. Aeon conversion omits attachments and dependency lags and assumes Gregorian-style dates; exported files have not been verified in Aeon desktop. See the [user guide](user-guide.md#import-and-export) for limits.

Use the [finding-code reference](user-guide.md#read-a-continuity-report) when explaining checks. A clean report means no supported check found a recorded contradiction, not that the entire manuscript is consistent.
