# Feature 005: Interactive editor (`lore serve`)

## Overview
A local, dependency-free web editor over the same operations table. A novelist who never touches a terminal or an agent opens it and sees the world on a timeline. They can create items, edit fields, link people to events, and drag an event to re-date it. When an agent edits files, the page updates within seconds. In saga mode the editor never writes canon: every edit becomes a change request.

## Functional requirements
- **FR-1 Server.** `lore serve [--port N] [--saga]` starts a `ThreadingHTTPServer` on 127.0.0.1 only (port 0 picks a free one). It prints `Lorekeeper editor: http://127.0.0.1:PORT/`. It stops on Ctrl+C. Only the standard library is used.
- **FR-2 Security.**
  - Every request's `Host` header must be `127.0.0.1:PORT` or `localhost:PORT`, otherwise 403.
  - Mutating requests are POSTs to an op with `writes=True`. They need a per-run random token in the `X-Lore-Token` header and `Content-Type: application/json`, otherwise 403 or 415.
  - The token is embedded in the served HTML (`<meta name="lore-token">`). The same-origin policy keeps it from other sites.
  - No CORS headers are sent, and nothing is fetched from the internet.
- **FR-3 API.**
  - `GET /` serves the editor page; `GET /editor.js` and `GET /editor.css` serve the assets. All three are flat files in the package.
  - `GET /api/ops` returns the operations table (names, params, writes).
  - `POST /api/<op>` takes a JSON body of args and calls `ops.run`.
  - Results come back as JSON. Errors are `{"error": {...}}` with a status code: NOT_FOUND 404, CONFLICT 409, INVALID 400, FORBIDDEN 403, IO_ERROR 500.
  - `GET /api/stamp` returns `{"stamp": s}`, where s changes whenever any project Markdown file or `lore.json` changes. It is computed with `os.scandir` over the scanned folders (mtime and size).
- **FR-4 Saga mode** (`--saga`, or config `"mode": "saga"`). A writing op other than `request` returns 403 `FORBIDDEN` with a message pointing to change requests. The UI hides direct editing and shows "Propose change" instead.
- **FR-5 Views** (tabs; every view keyboard-reachable):
  - **Timeline.** An SVG time axis. Dated items appear as bars, or as points when their span is under a pixel, grouped in lanes by type. Zooming with buttons or Ctrl+wheel and panning both work. Dragging an item horizontally re-dates it: the new date keeps the item's precision, and the edit goes through `set` with `version` and `expect`.
  - **Subway.** One lane per person: the 12 people with the most events by default, plus a filter box. Each event is a stop drawn on every participating person's lane, and the stops are joined vertically.
  - **Relationships.** A grid with people as rows and dated events as columns, in chronological order. Each cell shows the person's age at that event (Aeon rule) when they took part, or "·".
  - **Spreadsheet.** A real `<table>` with columns name, type, date or born, end or died, and location, each a native `<input>`. Edits save on blur or Enter. This is also the accessible fallback for everything the timeline does.
  - **Narrative.** Chapters (type `chapter` or `card`) in chapter order, with their dates and a story-vs-chronology marker.
  - **Inspector** (side panel, for the selected item):
    - fields as labelled inputs
    - links and backlinks
    - "Add link" (role select plus target select)
    - "Remove link"
    - "Save"
    - In saga mode, "Propose change" (`request`) takes a note.
  - **Create.** A form with a type select and a name. It calls `create`.
- **FR-6 Live reload.** The page polls `/api/stamp` every 2 s. When the stamp changes, it refreshes the data while keeping unsaved inspector edits. A 409 on save shows the conflict (the current values) and keeps the user's input, so nothing is lost.
- **FR-7 Accessibility.**
  - All controls are buttons or inputs with labels, and there is a visible focus ring.
  - Arrow keys move the timeline selection; Enter opens the inspector.
  - The palette meets WCAG AA contrast in both `prefers-color-scheme` themes.
  - Dragging always has a keyboard alternative (the date input).
- **FR-8 Saga hook.** `saga.py timeline [--port N]` starts the server in saga mode on the Wiki with chrono's config and chapter cards. `saga.py timeline-requests [--done ID]` lists the queue in `_system/runtime/timeline_requests/`, or moves one request to `done/`.

## Success criteria (verified with the Playwright MCP)
- **SC-1** Create an event, link a character, drag-redate the event, and see the age in the Relationships grid update.
- **SC-2** Create, date and link using the keyboard only.
- **SC-3** A CLI edit while the browser holds the item gives either a merge (different key) or a visible 409 with the input kept (same key).
- **SC-4** In saga mode, an edit lands in the request queue and the file is unchanged.
- **SC-5** Bad Host, a missing token, or a wrong content type → 403/415 (unit test).
