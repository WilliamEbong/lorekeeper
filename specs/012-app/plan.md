# Plan 012: The Lorekeeper app

## Technical context
Python ≥3.11 standard library only (`http.server`, `json`, `tkinter` for the folder picker, `winreg` for shell folders, `subprocess` for sagas and shortcuts, `webbrowser`). Vanilla JavaScript ES module and CSS, no build step. Tests: `unittest`. Windows first; `lore app` also runs elsewhere.

## Constitution check
- I stdlib, vendorable: new module `lorekeeper/app.py`; page assets read beside it like `editor.html`. Pass.
- II plain text: the world list is a small JSON file outside every world; AI files are Markdown and JSON written atomically. Pass.
- III one operations table: the start screen is not a world operation, so it is an adapter of its own (like `serve` and `mcp`), not an op. `lore app` joins `ADAPTERS`. Pass.
- IV never lose an edit: AI files never overwrite a person's own files; `.mcp.json` is merged. Pass.
- VI ponytail: no idle shutdown, no installer, no own Python. Pass.
- Security: loopback, Host check, token and JSON content type on every POST, same headers as `lore serve`. Pass.

## Design

### Files
- `lorekeeper/app.py`: world list, folder kinds, AI files and guide, the start-screen server, launch, install.
- `lorekeeper/app.html`, `app.js`, `app.css`: the start screen. It also loads `editor.css` for the shared tokens, typefaces, controls and themes.
- `lorekeeper/agent-skill.md`: moved from `docs/` (which keeps a one-line pointer), so it ships with the package and feeds the AI guide.
- `lorekeeper/lorekeeper.ico`: the favicon mark as a PNG-in-ICO (made once from `favicon.svg`).
- `Set up Lorekeeper.bat` at the repository root.
- `serve.py`: a module-level `LocalHandler` base (Host check, headers, error replies) shared by the editor and the start screen; `make_server(..., home=None)` fills `__LORE_HOME__`.
- `editor.html` / `editor.js` / `editor.css`: the **All worlds** link.
- `cli.py`: the `app` adapter with `--install`.
- `pyproject.toml`: package data for the new files.

### The start-screen server
- `make_app(port)` returns `(server, url, token)`; `run()` binds 8700 or, if taken, asks it `GET /api/hello`: Lorekeeper there → open the browser and return; anything else → a free port.
- State on the server: open worlds `{folder: (server, url)}` (each `serve.make_server` on port 0 in a daemon thread) and sagas `{folder: (process, url)}`.
- GET `/`, `/app.js`, `/app.css`, `/editor.css`, `/favicon.svg`; GET `/api/hello`; GET `/api/worlds` → `{worlds: [...], place, picker}` where each world has `folder, name, kind, opened, open`.
- POST (token, JSON): `create {name, template, place}`, `open {folder, make}`, `pick {}`, `forget {folder}`, `show {folder}`, `quit {}`.
- Replies `{error: "plain sentence"}` with 400/404/409 for a person to read; codes never reach the page.

### Folder kinds
`missing` (no folder), `saga` (`_system/scripts/saga.py` and `_system/lorekeeper.json`), `world` (`lore.json`), else `folder`.

### Sagas
`[sys.executable, "_system/scripts/saga.py", "timeline", "--port", N]` in the saga folder, no window, output discarded; wait up to 20 s for the port; the URL is returned. Never writes into the saga.

### AI files
`write_ai_files(root)`:
- `.lore/AI-GUIDE.md` rewritten only when its text changes.
- `AGENTS.md`, `CLAUDE.md` created with `create=True` only when missing.
- `.mcp.json`: load if present (invalid JSON → leave the file alone), set `mcpServers.lorekeeper = {command: python, args: [package folder, "mcp", "--root", root]}`, write only on change.
The guide: a header (generated, do not edit), "Start here" steps, this world (name, folder, mode, exact CLI and MCP commands, kinds with folders and counts, connections, fields, wikis present), "How everything connects" (files → items → fields and links → dates → views → checks → wikis; the person in the editor at the same time), then the agent skill.

### Launch and install
- Shortcut target `pythonw.exe` beside `sys.executable` (else `python.exe` minimised), arguments `"<package folder>" app`, icon `lorekeeper.ico`. Created through PowerShell's `WScript.Shell`, with paths passed in environment variables (no quoting into the command).
- Desktop and Start menu folders from the `Shell Folders` registry key (OneDrive-aware).

### Start screen page
Two columns on wide screens, one at 390 px: "Your worlds" (cards) and "Start a new world" (form); "Open a folder…" and "Close Lorekeeper" in the header. Folder-not-a-world offer and errors in an inline message region with `role="status"`/`alert`. Text via `textContent` only. Templates described in plain words.

## Verification
TDD in `tests/test_app.py`: world list round trip and order; kinds; create (blank and template; refuses an existing world); AI files (created, refreshed, never overwriting a person's files, `.mcp.json` merge); guide contents; app API (hello, token, Host, content type, worlds, open returns a working editor URL with the home link, forget, quit stops servers); install builds the right shortcut arguments (PowerShell not run in tests); MCP handshake on a created world from its `.mcp.json`. Then Playwright (isolated Chromium) in light, dark and 390 px; a real `pythonw` launch and second launch; the detector; the suite.
