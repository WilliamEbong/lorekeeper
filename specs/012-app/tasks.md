# Tasks 012: The Lorekeeper app

- [x] T1 `serve.py`: extract `LocalHandler`; `make_server(home=None)` fills `__LORE_HOME__`; editor **All worlds** link (html, js, css). Existing serve tests stay green.
- [x] T2 Move `docs/agent-skill.md` to `lorekeeper/agent-skill.md`, leave a pointer, update links and `test_readme`.
- [x] T3 Tests first: `tests/test_app.py` for the world list, kinds, create, AI files and guide.
- [x] T4 `app.py`: world list, kinds, default place, create, AI files and guide.
- [x] T5 Tests first: app API (hello, token, Host, worlds, open, forget, quit), saga launch command, install arguments, MCP handshake from `.mcp.json`.
- [x] T6 `app.py`: server, sagas, picker, show, quit, `run()`, `install()`; `cli.py` `app` adapter.
- [x] T7 Start screen: `app.html`, `app.js`, `app.css`.
- [x] T8 `lorekeeper.ico`; `Set up Lorekeeper.bat`; `pyproject.toml` package data.
- [x] T9 Docs: README and user guide ("Getting started without a terminal", "Working with an AI assistant").
- [x] T10 Verify: suite, Playwright (light, dark, 390 px, console), real launch and second launch, shortcuts, detector; converge.
