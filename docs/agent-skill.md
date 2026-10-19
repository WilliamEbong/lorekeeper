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

## The story wiki: what the reader knows by a chapter

A **chapter stamp** at the end of a fact says from which chapter the reader knows it: `[ch 7]`, or `[ch 2-5]` for something true from chapter 2 until chapter 5 (a belief, a place, a state, a relationship). A fact is one list item or one paragraph inside a section (a `##` heading). An unstamped fact is known from its page's `first_appearance` (`CH003`, `ch 3` or `3`); a page without one is always known. Chapter numbers follow reading order, not in-world dates.

- **Story page.** Where an entry's stamped facts live. Normally that is the item's own page. When the settings name a `story_wiki` folder, it is a companion page in that folder instead (`<folder>/<Type plural>/<Name> (story).md`, with `type`, `page: "[[Name]]"` and optional `first_appearance`). Companions are never items, so they never appear in `query`, `graph` or other views. In such a world never put stamps in the working pages: they are written for the present and would leak.
- **Names.** A `## Names` section lists the names the reader knows the entry by, each stamped: `- the hooded rider [ch 2-5]`, `- Kresh [ch 6]`. The index shows the latest name that covers the chapter. These names also resolve references.
- **Secret identities.** `revealed_as: "[[Kresh]] [ch 9]"` in a story page's frontmatter keeps Lord Vane a separate card until chapter 9; from then on, and always in complete mode, Lord Vane is folded into Kresh's card, each folded fact marked with `as`. Agents record a reveal with `fact-add` instead: item `Lord Vane`, section `Revealed to be`, text `[[Kresh]]`, from `9`.
- **Kinds of things.** `kind: "[[Standard alien battle tank]]"` links a thing to the page for its kind; a kind page is an ordinary entry with its own card.
- **Worked-out facts.** When a card's Where, Knows or Relationships section has no written fact at that chapter, `wiki` fills it from the links (located events, `learns` links, role links) and marks each one `worked_out`. Do not copy them back as written facts.

**When to read it.** Before drafting or reviewing chapter N+1, call `wiki` with `as_of` N for the index of what the reader has met, then `wiki` with `item` for each entry on the page. Call it without `as_of` for the author's complete view, with frontmatter fields and every ended fact. A progressive answer never contains anything later than N: an entry the reader has not met yet returns NOT_FOUND, exactly like a name that does not exist.

**How to record facts.** Only with the fact tools. Never type or edit `[ch …]` stamps by hand.
1. Read the card (`wiki`, `item`, `as_of`) and keep its `version`.
2. `fact-add` each new fact: `section`, one-line `text` without a stamp, and `from` = the chapter that reveals it. Add a new name to section `Names`.
3. When a belief, place, state or relationship changes, `fact-end` the old fact with `after` = the last chapter it was true in, then `fact-add` the new one.
4. Someone the reader has met who has no page yet (story-wiki worlds only): `fact-add` with `type`, which starts a standalone story page.
5. To take back your own mistake, `fact-remove` (undo an add) or `fact-end` with `reopen` (undo an end).
6. Run `check` and fix any `STAMP_UNREADABLE` or `STAMP_RANGE` finding.

On CONFLICT, read the card again and retry with its new version. Every refusal says what to change.

Each written fact on a card has an `id` (`fact:…`), and `fact-add` returns the new fact's `id`. Pass an id as `fact` to `fact-end` or `fact-remove` to name exactly that fact; text works too (an exact match first, then the facts that start with it), but text that matches several facts is refused. Entry keys (`id:…`) and fact ids are opaque on purpose: a progressive answer never contains a page path, a later name or a planning-only full name, and an entry opens at chapter N only under a name the reader knows by then (or by its key).

Starter sections, used for new story pages (other headings work too, shown in page order):
- character: Names, Current state, Where, Beliefs, Knows, Wants, Relationships, Important events;
- organization: Names, Leaders, Members, Goals, Territory, Allies and enemies, Standing, Important events;
- location: Names, Controlled by, Who is here, Condition, Important events;
- item and technology: Names, Kind, Held by, Where, Condition, What it does, Important events.

### Sagas: the after-freeze routine

In the owner's sagas (a `_system/lorekeeper.json` with `"story_wiki": "../Story Wiki"`), the saga pipeline is unchanged and the Story Wiki is a layer on top, updated after each `python _system/scripts/saga.py freeze N`. Follow `_system/skills/story_wiki_update.md` in the saga. In short:
1. Read only approved sources for chapter N: the frozen chapter, `Chapters/CHnnn/CURRENT_WORLD_BIBLE_OUT.md`, the chapter's approved deltas, and the Wiki's changes in the freeze commit (`git diff <previous freeze>..<this freeze> -- Wiki`). Never read the chapter architecture (planned chapter cards) or plans for unwritten chapters. Search the chapter text only to settle a specific question, such as how the reader first saw someone.
2. Write chapter N's facts with `fact-add` and `fact-end`: through the MCP tools, or `python _system/vendor/lorekeeper --root Wiki --config _system/lorekeeper.json fact-add ...` from the saga root.
3. Run `check` the same way.
4. Commit only `Story Wiki/` paths, in their own commit: `wiki: story wiki after CHnnn`.
5. Record any value you had to decide (such as the reader's description of an unnamed character) in `_system/knowledge/agent_decisions.md`.

Each saga's `.mcp.json` runs the vendored server as `lore mcp --saga`, which offers the reading tools and the three fact tools only, so an MCP session can never write Wiki pages.

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
| `wiki` | none | `item`, `as_of` | `lore wiki "Mira Vale" --as-of 1 --json` (leave out the name for the index, `--as-of` for the complete wiki) |
| `fact-add` | `item`, `section`, `text`, `from` | `to`, `version`, `type` | `lore fact-add "Mira Vale" Beliefs "Believes her sister is alive." --from 1 --version "<version>" --json` |
| `fact-end` | `item`, `section`, `fact` | `after`, `reopen`, `version` | `lore fact-end "Mira Vale" Beliefs "Believes her sister" --after 2 --json` |
| `fact-remove` | `item`, `section`, `fact` | `version` | `lore fact-remove "Mira Vale" Wants "To go home" --json` |

Global CLI options are `--root <project>`, `--config <file>`, `--json`, `--version` and help. `--config` names a settings file to use instead of `lore.json` (a saga keeps its settings in `_system/lorekeeper.json`); `--root` is then the project folder exactly as given. A vendored copy runs without installing: `python <vendor>/lorekeeper --root <project> wiki`. `--root` may name the project folder or any folder inside it; with no `lore.json` there or above, the command stops with NOT_FOUND (exit 2), and `mcp` and `serve` refuse to start. Every face checks parameter types the same way: a wrong type is INVALID, MCP `arguments` that are not an object get JSON-RPC -32602, and an unexpected server failure returns HTTP 500 INTERNAL. Without `--json`, `timeline`, `age`, `when`, `where` and `knows` print plain sentences; use `--json` for data. `serve` and `mcp` are CLI adapters, not operations or MCP tools. Start the editor with `lore serve --root <project>`, optionally `--port 8765` or `--saga`; start MCP with `lore mcp --root <project>`. The editor prints its loopback URL; it does not automatically open a browser. CLI check exits 1 on any FAIL, 0 otherwise; operational errors exit 2. A `--json` operational error is printed as JSON on stdout and also described on stderr.

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

`link` and `unlink` accept `version` but not `expect`; a stale version is refused, so reread before retrying. Linking a role declared `single` refuses to replace an existing target. Unlink it explicitly first. Broken links can also be unlinked by their written target name, and a plain-text (unbracketed) value is unlinked by its text. Always use the latest returned version for the next mutation.

`create` supplies `id`, `type` and `canonical_name`; do not override them through `field`. Names cannot contain brackets, pipe, hash, caret, slash, backslash or control characters. `init` is create-only, with `novel`, `series` and `campaign` as the optional templates. It does not apply templates to existing projects. Import skips existing names instead of replacing them; inspect the returned warnings. Export accepts `aeon`, `csv` or `md` and replaces its output file. There is no delete or automatic request-application operation.

In saga workflows use `request`, not direct writes, unless the host explicitly authorizes canon changes. Requests store proposed fields, removals, notes, current values and a base version/expectation snapshot. A stale baseline is marked `stale` rather than rejected; request creation does not establish that the change is safe to apply. `requests` lists the queued JSON records. The default directory is `.lore/requests`; the host can configure `requests_dir`. The host must reread canon, check impacts and apply approved changes through its own pipeline. Saga mode blocks direct HTTP writes other than requests, but does not restrict the CLI. `lore mcp --saga` offers only the reading tools and `fact-add`, `fact-end` and `fact-remove`.

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
