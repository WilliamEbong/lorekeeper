# Tasks 008: Editor UX overhaul

- [ ] T1 `serve.py`: serve `/favicon.svg` (image/svg+xml) and a `lore-name` meta tag; add `favicon.svg`; package data; test the route.
- [ ] T2 `editor.html`: new shell (top bar with wordmark, world name, mode, find box, status; tabs including Continuity; work area; inspector; alert).
- [ ] T3 `editor.css`: tokens for light and dark, category and rail colours, app layout, sticky inspector and headers, grid-style spreadsheet, states (hover, focus, disabled, saved, failed), reduced motion, mobile fallback.
- [ ] T4 `editor.js` shell: status states, alert with actions, find box, `/` and `Ctrl+S` shortcuts, create form, welcome state, Continuity badge.
- [ ] T5 Inspector: labels from schema, type select, read-only id, list textareas, date read-back, add-field select, dirty tracking, discard, grouped links and backlinks, filtered link targets, conflict actions, saga variant.
- [ ] T6 Timeline: real-width rendering, round ticks, sticky axis, type bands with counts, lane packing, category colours, uncertainty style, legend, type filters, undated note, wheel and keyboard zoom/pan, hit areas; keep drag re-date.
- [ ] T7 Subway: per-person colours, lifespan rails, selected stops.
- [ ] T8 Relationships: sticky column and header, no request without a birth date, hidden empty rows and columns, child tint.
- [ ] T9 Spreadsheet: filter, type filter, sortable headers, grid cells, type select, saved flash, row count.
- [ ] T10 Narrative: narrative-category types, backwards badge.
- [ ] T11 Continuity view: totals, grouped findings with plain titles, select item, clean state.
- [ ] T12 Update `docs/user-guide.md` and README editor paragraphs to match.
- [ ] T13 Verify SC-1…SC-7 with Playwright and the unit suite.
