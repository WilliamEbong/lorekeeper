# Feature 012: The Lorekeeper app

## Overview
The owner asked on 2026-10-19 for Lorekeeper to be easy, pleasant and mature for creative people who are not programmers: no terminal, ever. Today a writer must open a terminal, run `lore init` and `lore serve`, and copy an address into a browser. This feature makes Lorekeeper an app you double-click.

The owner also asked for two separate audiences inside the app:
- **People** get a plain-language interface: no commands, no file formats, no jargon.
- **AI assistants** get separate, detailed instructions written for an AI, so that an assistant opening a world understands exactly what it is, how its parts connect and how to work on it safely.

Owner decisions (2026-10-19):
1. Launcher and start screen first; a plain-language pass over the editor itself is the next, separate feature.
2. Setting Lorekeeper up on a computer must not need the terminal either.
3. AI instructions and the human interface are separate: the human screens never show AI material beyond a plain "use with an AI assistant" note.

Constraints are unchanged: standard-library Python ≥3.11, vanilla JavaScript with no build step, strict Content-Security-Policy, page text as DOM text nodes (never `innerHTML`), loopback only, a per-run token on every change, every `open()` with `encoding="utf-8"`, line endings preserved. `lore serve`, `lore mcp` and the saga launchers keep working unchanged.

## Clarifications

### Session 2026-10-19
Answered by the build agent with the recommended option; each can be changed later.
- Q: What do people call a project? → A: A **world**, as the editor already does ("Welcome to The Salt Road").
- Q: Where does the start screen run? → A: A small local server, `lore app`, on port 8700 when it is free (the saga launchers use 8701–8703), else on any free port. Opening a world starts that world's editor inside the same program on its own free port.
- Q: How does a second double-click avoid a second copy? → A: It asks port 8700 whether Lorekeeper's start screen is there (`GET /api/hello`). If so it only opens the browser at it and exits.
- Q: Where is the list of worlds kept? → A: In `%APPDATA%\Lorekeeper\worlds.json` on Windows, else `~/.lorekeeper/worlds.json`. It holds each world's folder, name, kind (world or saga) and when it was last opened. Removing a world from the list never touches its files.
- Q: How does a person choose a folder from a web page? → A: The program shows the normal system folder picker (Tk, part of the standard library) in front of the browser. If Tk is missing, a text box for the folder path appears instead.
- Q: Where do new worlds go by default? → A: In a `Lorekeeper worlds` folder inside the person's real Documents folder (read from Windows' shell-folder setting, so a Documents folder kept in OneDrive is found), named after the world.
- Q: How do the owner's sagas open? → A: A folder with `_system/scripts/saga.py` and `_system/lorekeeper.json` is a saga. It opens through the saga's own command (`saga.py timeline --port N`, run with the same Python), so it uses the saga's vendored engine and its proposals-only mode. Lorekeeper never writes AI files or settings into a saga: sagas already have their own AI pipeline.
- Q: Where do the AI instructions live, and how do assistants find them? → A: In each world (not saga) opened or created through the app:
  - `.lore/AI-GUIDE.md`: the full guide, written by Lorekeeper and refreshed whenever the world is opened (a first line says edits are replaced). Hidden folders are not part of the world, so it never shows up as an item.
  - `AGENTS.md` and `CLAUDE.md` at the world's top level, created only when missing: a few lines telling any assistant to read `.lore/AI-GUIDE.md` before doing anything. These are the files assistants such as Claude Code and Codex read first.
  - `.mcp.json`: a `lorekeeper` MCP server entry with the exact Python and Lorekeeper paths and this world's folder. Other entries in an existing file are kept.
- Q: What is in the AI guide? → A: Two parts. First, this world: name, folder, mode, the exact commands to run Lorekeeper here (absolute paths, so no `lore` on PATH is needed), its kinds of item with their folders and counts, its connection types (from which kind to which), its fields, and which wikis it has. Second, how everything connects and every operation: the existing agent skill, moved into the package (`lorekeeper/agent-skill.md`) so it ships with Lorekeeper and can be copied into worlds; `docs/agent-skill.md` becomes a pointer to it.
- Q: Does the setup need Python? → A: Yes. `Set up Lorekeeper.bat` in the Lorekeeper folder looks for Python 3.11 or newer. If it is missing it explains in plain words, opens the python.org download page and asks the person to run setup again afterwards. Otherwise it creates the shortcuts and opens Lorekeeper. Shortcuts run `pythonw` (no console window) on the Lorekeeper folder itself, so moving the folder means running setup again (setup says so).
- Q: How does a person stop Lorekeeper? → A: **Close Lorekeeper** on the start screen stops every open world and the start screen, then the page says the tab can be closed. Closing the browser alone leaves it running quietly; the next double-click reuses it.

## User scenarios
- **First time.** A novelist downloads the Lorekeeper folder, double-clicks **Set up Lorekeeper**, installs Python when asked, runs setup again and sees "Lorekeeper is ready" with a new Lorekeeper icon on the Desktop. The start screen opens in their browser.
- **A new world.** On the start screen they type "The Glass Orchard", choose **Novel**, keep the suggested place (`Documents\Lorekeeper worlds\The Glass Orchard`) and choose **Create world**. The editor opens on the novel starter world. A link in the header, **All worlds**, returns to the start screen.
- **Coming back.** Next week they double-click the icon. "Your worlds" lists The Glass Orchard, "Opened 7 days ago". One click opens it.
- **An existing folder of notes.** They choose **Open a folder…** and pick their old notes folder. The start screen says it is not a Lorekeeper world yet and offers **Make it a world**, which keeps every file as it is.
- **A saga.** The owner picks the Space saga folder. It opens in proposals-only mode, as the saga's own launcher does.
- **With an AI assistant.** The writer opens their world folder in Claude. Claude reads `CLAUDE.md`, then `.lore/AI-GUIDE.md`, and already knows the world's kinds of item, folders and connections, how to run Lorekeeper here, and the safe-editing rules. On the start screen the writer saw only a short note: "Your world includes instructions for AI assistants…", with **Copy a message for your assistant** and **Show the folder**.
- **Done for the day.** They choose **Close Lorekeeper**; the page says "Lorekeeper is closed. You can close this tab."

## Functional requirements

### Setup and launch
- **FR-1 Setup.** `Set up Lorekeeper.bat` finds Python ≥3.11 (`py -3`, then `python`). Without it: a plain explanation, the python.org downloads page opens, and nothing else happens. With it: `lore app --install` creates a **Lorekeeper** shortcut on the Desktop and in the Start menu, with Lorekeeper's icon, running `pythonw` on the Lorekeeper package folder with `app`. Then the start screen opens. Running setup again replaces the shortcuts. Every message is plain words.
- **FR-2 Launch.** `lore app` serves the start screen on 127.0.0.1 (ports as in the Clarifications), opens it in the default browser, and keeps running until **Close Lorekeeper**. A second launch only reopens the browser.
- **FR-3 Icon.** `lorekeeper/lorekeeper.ico` is Lorekeeper's mark (the favicon) and ships in the package.

### Start screen
- **FR-4 Your worlds.** Recently opened worlds, newest first: name, folder, "Opened …" in words (today, yesterday, N days ago, or the date), a saga label for sagas. Each has **Open** and **Remove from list**. A world whose folder no longer exists is shown as "Folder not found" with only **Remove from list**. With no worlds yet, the screen leads with starting one.
- **FR-5 Start a new world.** A name (required; the folder name drops characters Windows cannot use), a starting point (**Blank**, **Novel**, **Series**, **Campaign**, each with one plain sentence of what it contains) and a place (the default, or **Choose…** with the folder picker). **Create world** refuses, in plain words, a place that already holds a world or files that the starting point would overwrite. On success the world opens.
- **FR-6 Open a folder.** **Open a folder…** shows the folder picker. A world opens; a saga opens as a saga; any other folder gets the offer **Make it a world** (no starting point, files kept, name from the folder) or **Cancel**.
- **FR-7 Close Lorekeeper.** Stops every world and the start screen; the page then says it is closed.
- **FR-8 Look.** The start screen uses the editor's typefaces, colours and light/dark themes, works at 390 px wide, is fully usable by keyboard, announces results to screen readers, and shows no technical text (no paths in JSON, no error codes). Errors say what happened and what to do.

### Editor
- **FR-9 All worlds.** An editor opened from the start screen shows **All worlds** in its header, linking back. `lore serve` alone shows no such link.

### AI instructions
- **FR-10 AI files.** Creating or opening a world (not a saga) through the app writes `.lore/AI-GUIDE.md`, creates `AGENTS.md` and `CLAUDE.md` when missing, and adds or updates the `lorekeeper` entry in `.mcp.json`, as in the Clarifications. A person's own `AGENTS.md`, `CLAUDE.md` or other `.mcp.json` entries are never changed. None of these files becomes an item or a check finding.
- **FR-11 AI guide content.** The guide is written for an AI reader: direct, complete, structured by task (orient, read, change, check), with this world's facts and exact commands first and the full operation reference after. It states how items, files, fields, links, dates, views, checks and wikis connect, and that the person works in the editor at the same time (the editor reloads changes within seconds; version checks protect both).
- **FR-12 Human note.** Each world on the start screen offers, folded away by default, a plain note about AI assistants with **Copy a message for your assistant** (a one-paragraph message pointing the assistant to `AGENTS.md`) and **Show the folder** (opens it in the file manager).

### Safety
- **FR-13** Every start-screen change (create, open, remove, pick a folder, close) is a POST with the per-run token and a JSON body; the Host check and security headers match `lore serve`. Folder paths come only from the person (typed or picked) or the saved list.

## Success criteria
- From a fresh start, a person can set up, create a world, close Lorekeeper and reopen the world without seeing a terminal or typing a command. Verified in a browser (Playwright) in light, dark and at 390 px, with a clean console.
- A second launch reopens the start screen and does not start a second server.
- The owner's three sagas open from **Open a folder…** in proposals-only mode.
- An AI given only a world folder created by the app can find the guide from `AGENTS.md` or `CLAUDE.md`, run `schema` with the guide's command, and connect over MCP from `.mcp.json` (handshake test).
- `python -m unittest discover -s tests` passes, with new tests for the world list, folder kinds, world creation, AI files (create, refresh, never overwrite a person's files), the token and Host checks, and close. The Impeccable detector finds nothing new.

## Out of scope
- An installer that brings its own Python, macOS or Linux shortcuts (`lore app` itself works there), and stopping automatically when the browser closes.
- The plain-language pass over the editor (next feature).
