# HANDOFF — Lorekeeper

Transferred from: Lorekeeper run 3 (editor UX overhaul and whole-app audit), 2026-10-18.
This document is authoritative, including over memory and older summaries. The previous handoff's history is in SESSION-LOG.md and BUILD-NOTES.md.

## 1. Snapshot

Lorekeeper (command `lore`) is a self-sufficient, standalone story-world engine, inspired by Aeon Timeline but in no way dependent on it.
- **Storage:** a world is plain Markdown files, one per character, place or event, with flat frontmatter and Obsidian wikilinks.
- **What it does:** reads dates at whatever precision they are written, computes ages and timelines, and checks continuity (FAIL means a definite error, WARN a possible one).
- **Interfaces:** a CLI, an MCP server for AI agents, and a local browser editor (`lore serve`).
- **Interop:** imports and exports Aeon `.aeon`, CSV and Markdown.

Audiences: writers who draft with AI agents, novelists who don't use AI, and worldbuilders/GMs. First clients: the owner's three sagas (Realm, Space, Zombies), in warn mode.

## 2. Current state

**Run 3 is done, on branch `feat/008-editor-ux`** (local commits only; not merged into `main`, not pushed). HEAD is the final docs commit after `d1d3468`. 240 tests pass (1 POSIX-only skip). `main` is still `adc9c41` and matches the private GitHub repo.

What the branch adds:
- **Editor (feature 008, specs/008-editor-ux):** rebuilt for novelists.
  - Shell: a top bar with live save status, a find box (`/`), and a New item form.
  - Inspector: plain labels, dates read back in words, one-per-line lists, a type picker, grouped connections, and Undo after every save. Conflicts offer "Load their version" or "Keep my text".
  - Timeline: round axis dates that stay in view, packed rows, a colour per type, approximate dates drawn dashed, type filters, and safe dragging (a 6 px threshold, a live date, the whole span moves, Undo).
  - Other views: Subway lines run from birth to death. Ages (renamed from Relationships) keeps its names in view and tints children and impossible ages. Spreadsheet sorts, filters and pages its rows.
  - New Continuity tab: shows `lore check` results in plain words, with a count badge.
  - Works in light and dark, at phone width, and at 3,000 items.
- **Audit fixes (about 50 findings from three read-only audits, fixed in four parallel worktrees, then two fresh-context reviews):**
  - Aeon import no longer invents deaths; dependencies are no longer reversed; SS/FF import as `starts_after_start`/`ends_after_end`.
  - Obsidian block-style lists are read and edited safely.
  - A mistyped `--root` errors instead of giving a false all-clear.
  - "May 5, 1990" no longer reads as the year 5.
  - New checks: `END_BEFORE_START` and `AMBIGUOUS_NAME` (WARN).
  - TWO_PLACES: back-to-back scenes no longer clash, and the check went from 21 s to 0.3 s on coarse worlds.
  - Parameter types are checked once for all three interfaces.
  - The CLI prints plain sentences for timeline, age, when, where and knows.
  - Live-reload polling went from 0.7 s to 0.05 s at 3,000 files.
- **Wuthering Heights sample (re-imported):** 2 FAIL and 2 WARN, all genuine. It reported 23 FAIL and 7 WARN before.

**In flight:** nothing.

## 3. Decision log (this run; earlier decisions are in SESSION-LOG and BUILD-NOTES)

| # | Decision | Rationale | Status |
|---|----------|-----------|--------|
| 14 | Refine the editor's look; don't redesign it | The paper-and-ink identity works; the problems were usability | settled |
| 15 | The Relationships tab is labelled **Ages** | It is an age grid; element ids are unchanged | owner may revert |
| 16 | In local mode, link fields are edited only through Connections, not as raw `[[Name]]` text | Raw link syntax is error-prone for novelists; saga mode keeps the text | owner may revert |
| 17 | A timeline drag moves the whole written span | Moving only the start could put it after its end | settled |
| 18 | Continuity re-runs `check` after every reload (0.5 s debounce) | Keeps the badge honest; `check` takes about 1 s at 3,000 items | settled |
| 19 | An event dated exactly like a birth or death is not a DEAD/UNBORN finding | Birth and death events were flagged against the same person | settled |
| 20 | `create()` keeps the index current; callers no longer re-index | Imports were quadratic | settled |
| 21 | Aeon SS/FF import as unchecked roles | Lorekeeper's `same_start`/`same_end` mean "equal", which is wrong for Aeon | settled; checking them is on the Later list |

## 4. Open questions (owner's call)

- Merge `feat/008-editor-ux` into `main` and push to the private repo? (Not done: pushing needs the owner's go-ahead.)
- Should the sagas switch from warn to fail mode? (Carried over.)
- Keep the tab name "Ages", or go back to "Relationships"?

## 5. Next actions

## 5. Next actions

0. **Owner feature request (2026-10-18), not started:** a chapter-scoped story wiki that shows only what is known by a chosen chapter. It is AI-optional, and it builds on the saga's chapter wrap-up rather than replacing it. The full brief and its grounding are in BUILD-PLAN.md under "Feature requests from the owner". Start it with speckit-specify.
1. Owner reviews the editor (`lore serve` in a world folder), then approves merging and pushing the branch. **← NEXT**
2. Re-vendor the engine into the three sagas. They carry `eb20b30`; the branch changes check results: TWO_PLACES, END_BEFORE_START, AMBIGUOUS_NAME (cards are exempt) and `learns`. Use clones and `land.sh`, as in run 2, and compare saga reports before landing. The dates agent checked read-only that saga card dates and findings are unchanged.
3. Space chronology report: cards 051/052 (RAIL_REGRESSION) and four impossible SRD days (carried over).
4. Apply the deferred saga keys in `chronology_deferred.md` as chapters freeze (carried over).

## 6. Constraints & preferences

- The owner directs in plain language and does not read code, JSON or git. Persisted docs and commits use normal prose.
- Ponytail (the simplest correct design) and stdlib only. Spec Kit for features. Playwright for any UI check.
- Line endings: most `.py` files and `editor.js` are CRLF; `editor.css`, `editor.html` and the docs are LF. Preserve them, and check with `git diff --stat` before committing.
- **Sagas:**
  - Never stage in-progress chapters, `_system/state`, provenance or `saga.log`.
  - Engine commits are prefixed `system:`.
  - Run status and validate only on copies.
- Nothing public. The only remote is the private repo.

## 7. Artifact manifest

| Artifact | Purpose | Status | Location |
|----------|---------|--------|----------|
| Lorekeeper source + tests | The app | final on branch | repo, `feat/008-editor-ux` |
| specs/008-editor-ux | Spec, plan, tasks for the editor | final | repo |
| README.md, docs/user-guide.md, docs/agent-skill.md | Guides (updated this run) | final | repo |
| docs/research/AEON-SPEC.md | Clean-room `.aeon` notes (dependency direction and zero-length ends added) | final | repo |
| docs/build/BUILD-PLAN.md, SESSION-LOG.md | Plan with run-3 section; full history | final | repo |
| tests/test_editor_dates.py | Runs the editor's own date and tick code in Node against the engine (skips without Node) | final | repo |
| Scratch test worlds (Wuthering Heights import, fixture copy, empty world, 3,000-item world) | Verification only | disposable | session scratchpad (not in the repo) |

## 8. Glossary

- **Card:** an architecture chapter card (in-memory item of type `card`, path `<architecture>#CHnnn`).
- **Rail:** a Space story strand. **SRD:** Space's 365-day production calendar.
- **Warn mode:** chronology findings are printed but never block a stage.
- **FAIL / WARN:** a definite or possible continuity error.
- **Approximate (editor):** circa, provisional, ranges, `date_min`/`date_max`, or month or year precision without a written end. Drawn pale and dashed.

## 9. How to verify

- `python -m unittest discover -s tests` from the repo root: 240 tests, OK (1 skipped).
- `lore serve --root <a world>` and open the printed address:
  1. Press `/`, find a character, edit Born, and check that it reads back.
  2. Press Ctrl+S, then Undo.
  3. Open the Continuity tab.
  4. Drag an event and watch the date shown live.
- `"C:/Users/Owner/.claude/skills/impeccable/scripts/impeccable" detect --json lorekeeper/editor.html` should print `[]`.

## 10. Appendix

None.
