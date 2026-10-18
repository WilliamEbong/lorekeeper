# Lorekeeper

Lorekeeper keeps the people, places and events of your story in ordinary Markdown files. It connects those notes to a timeline and checks for continuity problems: someone appearing after their death, a journey happening before its cause, or a character being in two places at once.

- **Novelists:** explore and edit your world in a local browser editor. No AI account is needed.
- **Writers working with agents:** use the same world through the `lore` command or an MCP server, with version checks for shared edits.
- **Worldbuilders and game masters:** start with factions, quests and sessions, and keep your notes in an Obsidian vault if you like.

There is no database. One Markdown file holds each item; `lore.json` holds the project's settings. The runtime uses only Python's standard library.

## Install

You need Python 3.11 or later and either uv or pipx. From a local checkout of this repository, run one of:

```text
uv tool install .
```

```text
pipx install .
```

Then `lore --version` should print the version. These instructions install from the checkout; they do not assume a package published on PyPI. For work directly from source, `python -m lorekeeper` accepts the same arguments when this repository is on Python's import path.

## Quickstart

Open a terminal in an empty folder for your story, then run these commands in order. The novel template supplies Mira Vale, Lantern Harbour, two events and two chapters. The commands add a new event, connect it, and check the resulting world.

```bash
lore init --template novel
lore query
lore create event "Homecoming" --field "date=2025-04-10 18:00"
lore link "Homecoming" participants "Mira Vale"
lore link "Homecoming" location "Lantern Harbour"
lore link "Homecoming" after "Departure"
lore when "Homecoming"
lore age "Mira Vale" "Homecoming"
lore timeline --type event
lore check
```

The final command should say `0 FAIL, 0 WARN`. All starter names and dates are examples for you to replace.

For a different new project, use `lore init --template series` or `lore init --template campaign`. Series adds books, a `series_order` property and a rule checking that their dates move forward in that order. Campaign adds factions, members, quests, sessions and a session outline. Plain `lore init` creates only `lore.json`. Initialization refuses an existing `lore.json`; template initialization also refuses collisions with starter files or names.

## Open the editor

From your story folder, run `lore serve`. Open the printed `http://127.0.0.1:…/` address in your browser and leave the terminal running. Ctrl+C stops the server. It serves only on your own computer and loads no CDN assets.

Use Timeline to explore dates, Subway to follow people through events, Ages to see how old everyone is at each event, Spreadsheet for quick edits, Narrative for the story in reading order, and Continuity for the problems `lore check` finds. Press `/` to find an item; its fields and connections open in the inspector, and every save can be undone. Disk edits appear automatically. The [user guide](docs/user-guide.md) explains each view, uncertainty and conflict messages.

`lore serve --saga` queues proposed changes for a host writing pipeline instead of editing canon. This restriction belongs to the editor; CLI and MCP callers must follow the host's own canon rules.

## Connect an agent

For a client that reads `.mcp.json`, add this configuration, replacing the path with your story folder:

```json
{
  "mcpServers": {
    "lorekeeper": {
      "command": "lore",
      "args": ["mcp", "--root", "/absolute/path/to/story"]
    }
  }
}
```

On Windows, a JSON path can use forward slashes, such as `C:/Stories/My Novel`. For clients with another configuration format, register the same stdio command: `lore mcp --root <project>`. The server supports both legacy `initialize` and modern per-request discovery/version metadata; it exposes the operations as tools. The [agent skill](docs/agent-skill.md) documents every operation and safe editing rules.

## Date cheat sheet

| Write | Meaning |
| --- | --- |
| `2025` | Somewhere in that year |
| `2025-04` | Somewhere in April |
| `2025-04-02` | That day, without a known time |
| `2025-04-02 09:30` | Minute precision |
| `April 2, 2025` | The same day in words |
| `~2025` or `circa 2025` | Approximate year; the bounds widen |
| `2025-04-01..2025-04-10` | A possible date anywhere in that inclusive range |
| `2040s` | 2040 through 2049 |
| `44 BC`, `2025 AD` | Era suffixes; BCE and CE also work |
| `2025-04-02 (letter)` | Date with a source note |
| `2025-04-02, tentative outline` | Date with a trailing note |
| `2025-04-02 (provisional)` | Provisional date; relevant continuity findings become warnings |

A range expresses uncertainty about a date. To describe an event lasting several days, use `date` and `end`. Keep the precision you actually know. Custom calendars can be configured in `lore.json`; Gregorian is the default.

## Bring notes in or share them

`lore import story.aeon` and `lore import story.csv` bring items into an initialized project. Existing names are skipped, not replaced. Export with `lore export aeon story.aeon`, `lore export csv story.csv`, or `lore export md story.md`. Markdown export is a readable report; there is no matching report-import command.

Aeon interchange has limits: attachments are not imported, dependency lag text is not exported, and export uses Gregorian dates. Opening an exported file in the Aeon desktop app remains unverified. See the [interchange guidance](docs/user-guide.md#import-and-export) before moving a whole project.

For everyday writing, start with the [user guide](docs/user-guide.md). For command arguments, use `lore --help` or `lore <command> --help`. Add `--json` for structured results or `--root <project>` to address a story folder from elsewhere.
