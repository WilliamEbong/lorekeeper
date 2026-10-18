# Feature 007: Templates, onboarding, packaging

## Functional requirements
- **FR-1 Templates.** `lore init --template novel|series|campaign` (an optional `template` param on the `init` op) writes `lore.json` plus a handful of starter items.
  - **novel:** characters, locations, events, chapters, and a `narrative.md`.
  - **series:** adds a `book` type, a `series_order` property and a monotonic rule over books.
  - **campaign** (worldbuilding / game master): adds `faction`, `session` and `quest` types, a `members` role, and a `sessions` narrative.
  - Every template's starter world passes `lore check` with 0 FAIL and 0 WARN. With no template, `init` behaves as before.
- **FR-2 Packaging.** `pyproject.toml` (setuptools) declares package `lorekeeper` with `editor.html`, `editor.js` and `editor.css` as package data, the console script `lore = lorekeeper.cli:main`, `requires-python >= 3.11` and no dependencies. `uv tool install .` gives a working `lore` command.
- **FR-3 README.md.** What Lorekeeper is, for the three audiences; install (`uv tool install .` or `pipx install .`); a **Quickstart** fenced `bash` block of `lore …` commands; the editor; MCP setup; the date syntax cheat sheet; links to the guides. A test runs the quickstart block verbatim in a temp folder (each `lore` line through `python -m lorekeeper`), and every command must exit 0, or 1 where it is a `check` that is meant to find something.
- **FR-4 `docs/user-guide.md`.** A plain-language guide for novelists who never use AI or a terminal beyond `lore serve`. It covers the file format, dates and uncertainty, each view in the editor, each check and what FAIL and WARN mean, import and export, and working alongside Obsidian.
- **FR-5 `docs/agent-skill.md`.** A skill file for Claude Code or Codex: when to use Lorekeeper, the MCP setup (`.mcp.json` snippet using `lore mcp --root <project>`), every op with an example, the version and expect rules for safe edits, and the conventions (flat keys, quoted wikilinks, never invent precision, decide-and-record).

## Success criteria
- **SC-1** Each of the three templates passes `lore check` clean, which a test asserts.
- **SC-2** The README quickstart test passes.
- **SC-3** `uv tool install .` installs, then `lore --version` and `lore --root <fixture> check` work from the installed tool. This is verified by Claude.
