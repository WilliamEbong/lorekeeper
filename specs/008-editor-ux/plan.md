# Plan 008: Editor UX overhaul

## Technical context
- **Files:** `lorekeeper/editor.html`, `editor.css` and `editor.js` are rewritten in place. `lorekeeper/favicon.svg` is new. `serve.py` gains the favicon route and a world-name meta tag. No other engine change is needed: every view uses ops that already exist (`graph`, `set`, `create`, `link`, `unlink`, `request`, `convert`, `age`, `check`).
- **Stack:** one vanilla ES module, inline SVG, native controls (`<input list>`, `<details>`, `<select>`, `<textarea>`). No build step, no CDN, CSP unchanged (`default-src 'self'`). The favicon is a file served by the same allowlist as the other assets, because the CSP blocks `data:` images.
- **Packaging:** `pyproject.toml` package data gains `favicon.svg`.

## Design decisions
1. **Keep the identity, fix the experience.** Paper-and-ink palette, deep green accent, Georgia only for the wordmark and the inspector's item heading; system UI font elsewhere, tabular figures for dates and ages. This is a refinement, so no new visual world.
2. **App layout.** On wide screens the page is a fixed-height app: top bar, tabs, then a two-column work area in which the view and the inspector scroll independently. This removes the old double scroll and keeps the inspector in view. Below 900px it falls back to normal document flow with the inspector under the view.
3. **Charts render at real pixel width.** Each chart measures its container and redraws on resize, instead of scaling a 1000-unit viewBox, so text never shrinks on small screens and label widths can be estimated for packing.
4. **Axis ticks.** Pick the smallest step from a fixed ladder (1, 5, 15, 30 min; 1, 3, 6, 12 h; 1, 2, 7 d; 1, 3, 6 months; 1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000… years) that gives at least ~110 px per tick. Month and year ticks are aligned with a Gregorian `days_from_civil` (the inverse of the existing `civil_from_days` port), so ticks land on 1 January or the first of a month. Labels follow the step: `1760`, `44 BC`, `Jul 1764`, `12 Jul 1764`, `12 Jul 09:30`. The axis is its own SVG inside a sticky header of the chart's scroll box.
5. **Lane packing.** Within each type band, items sorted by start take the first row whose last occupant ends before them; an item occupies its bar plus its estimated label width (`ponytail:` character-count estimate; measure with `getComputedTextLength` if labels collide in practice).
6. **Uncertainty is a style, not a shape.** Circa, provisional, range dates, `date_min`/`date_max`, and year- or month-precision dates without an explicit end are drawn with a soft fill and dashed outline; a legend explains it.
7. **Role fields live in Links.** In local mode, fields that are schema roles are edited through the Links section, not as raw `[[Name]]` text. In saga mode they stay in the field list, because proposing a link means proposing field text.
8. **Lists one per line.** A list field is a textarea with one value per line; that avoids JSON and survives names containing commas.
9. **Date read-back** calls `convert` 350 ms after typing stops and words the result (`July 1764`, `between 1763 and 1765`); unreadable text is reported but still saveable, matching the engine's rule that unparsed dates stay and warn.
10. **Conflicts.** A 409 keeps the draft and offers "Load their version" (drop the draft) or "Keep my text" (rebase the draft onto the latest version so the next Save is a deliberate overwrite of those fields).
11. **Continuity tab** calls `check` once at start (to show the FAIL count on the tab) and again after each reload while the tab is open. Codes get plain titles from a small table in the page; unknown codes fall back to the code in words.
12. **Relationships** skips people without a birth date (no request), drops events with no participating person and people with no events (with a count), and keeps the 4-request pool.
13. **Narrative** takes every type whose category is `narrative`, plus `card`.
14. **Icons** are a handful of authored stroke SVGs (plus, minus, fit, search, close), one weight, `currentColor`.

## Verification
Playwright MCP on scratch copies (a 116-item imported world, the fixture world, an empty world, and saga mode), desktop 1440×900 and mobile 390×844, light and dark, against SC-1…SC-7. The Python suite covers the new route.
