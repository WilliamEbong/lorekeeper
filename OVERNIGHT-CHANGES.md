# Overnight changes (2026-11-22 to 23)

This was a maintenance pass on branch `claude/overnight-fixes-77b916`, taken from main at `bec45dd`. Nothing was pushed or merged, and the sagas were not touched.

The pass fixed defects and added no features. Each fix began with a test that failed and passed once the fix was in. The full suite passed before every commit. Three read-only Opus agents audited the codebase in parallel; every lead they raised was confirmed in the code before it was acted on. Codex then reviewed the branch diff twice. Its confirmed findings are fixed below; the rest are listed under "Found, not changed".

## Tests

- **Before:** `python -m unittest discover -s tests` gave 376 OK (1 skipped, POSIX-only).
- **After round 1:** 383 OK (1 skipped).
- **Now:** 395 OK (1 skipped).
- **No lint or typecheck:** the project has no lint or typecheck configuration, so neither was run.

## Changes

Undo any single change with `git revert <hash>`.

| # | Commit | What | Why, and the evidence |
|---|---|---|---|
| 1 | `8a48774` | The MCP server answers a very deeply nested JSON line with a `-32700` parse error. | 200,000 `[` characters made `json.loads` raise `RecursionError`, and the whole stdio server exited. Test: `test_deeply_nested_line_is_a_parse_error_not_a_crash`. |
| 2 | `821bd86` | `export` refuses to overwrite `lore.json`, `narrative.md` or an item file. | `POST /api/export {"format":"md","out":"<world>\\lore.json"}` replaced the settings with a report and broke the world. Aimed at an item, it replaced the item. The CLI and MCP had the same hole. Test: `test_export_never_overwrites_the_projects_own_files`. |
| 3 | `a8fe827` | Malformed `.aeon` and CSV files are refused as INVALID. | Several inputs crashed `lore import` with a traceback: a year of `Infinity` (OverflowError), deeply nested JSON (RecursionError), and records of the wrong shape (AttributeError or TypeError). `read_aeon` now checks the shapes the importer relies on. A CSV cell nested too deeply is kept as text. Tests: `test_hostile_numbers_and_nesting_are_invalid_not_crashes` and `test_wrongly_shaped_aeon_records_are_invalid_and_write_nothing`. |
| 4 | `f74b534` | Import refuses a new type whose name cannot be a folder (`CON`, `x?`, `a*`), before anything is written. | `lore.json` was rewritten with the new type, and only then did creating the folder fail. The importer's own comment promises "a refused import writes nothing". Test: `test_csv_type_that_cannot_be_a_folder_is_refused_before_writing`. |
| 5 | `eff826e` | The quit test waits up to 5 s for the servers to stop. | Quit stops the servers on a background thread. The test failed once under load and passed on rerun. |
| 6 | `d3ef91a` | `lore check` no longer crashes on a `max_age` such as `²`. | `isdigit()` accepts `²`, but `int()` cannot read it, so the check raised `ValueError`. Now `isdecimal()`. Test added to `test_max_age_override`. |
| 7 | `2f5296f` | Fixed two broken links in `lorekeeper/agent-skill.md` (they pointed to `user-guide.md`; the file is `../docs/user-guide.md`). | A new test checks every relative link in README, AGENTS, `docs/*.md` and the agent skill. It failed on these two. |
| 8 | `d54f65e` | Corrected four statements in the docs that the code contradicts. | (1) `mcp --saga` also offers `planning-fact`: fixed in the README, the agent skill and the `--saga` help. (2) Books and sessions do appear in the Narrative view. (3) On the CLI, argparse rejects a non-integer flag with exit 2 and no JSON, not INVALID. (4) The `planning-fact` example needs `--type`. Each was checked against `mcp.offered`, `editor.js narrative()` and a CLI run. |
| 9 | `7dc6530` | A `lore.json` that is not a single JSON object is now INVALID. | `[]` gave an AttributeError traceback from every CLI command. `lore serve` crashed even on plainly invalid JSON. The new `store.load_config` serves both, and the app shows its "settings file can't be read" message. Test: `test_settings_that_are_not_an_object_are_invalid`. |
| 10 | `393b14a` | Build-plan and session-log entries for this pass. | |
| 11 | `c6d2080` | The quit test polls a URL each server really answers: `/api/hello` on the start screen, `/api/stamp` on the world. | Codex found that the old test passed vacuously: the start screen's 404 counted as "stopped". This predates this pass. I proved the new test by making quit a no-op, and the test then fails. |
| 12 | `c598bbc` | An Aeon type whose `category` is not text is INVALID. | Codex found a gap in #3: `"category": []` still raised a TypeError. Test case added. |
| 13 | `863298b` | Import refuses a type whose folder would be an existing file. | Codex found a gap in #4: a CSV type named `lore.json` planned items under `lore.json/`, then wrote the schema, then failed. Test case added. |
| 14 | `bf8d6d3` | Export also refuses wiki pages and any existing file with another format's extension. | Codex found that #2 missed story and planning wiki pages and a settings file kept elsewhere (`--config`). Re-exporting over an earlier export of the same format still works. The agent skill now says so. |
| 15 | `b5584c9` | Export compares the extension case-insensitively on every platform. | Codex found that on POSIX `report.CSV` worked once and was then refused. The test simulates POSIX case handling. |

## Round 2: the items round 1 found (owner approved)

The owner then set a bar: only tangible improvements, nothing for fringe cases. Every change below says who notices. Three round-2 fixes failed that bar and were reverted (`5fb746b`), and three more were trimmed (`b3a33b6`).

| Commit | Change | Who notices |
|---|---|---|
| `e68d5a5`, `45ab600` | The editor and start screen read and drop a request body before replying with an error. | The test suite: a bad-Host test failed once with a connection reset under load. An oversized body (over 1 MiB) gets the same readable error. |
| `4521fd5` | `lore app --install` prints one line instead of a traceback when PowerShell can't make a shortcut. | The owner, running Set up Lorekeeper. |
| `b7859c4` | `Open Lorekeeper.bat` checks for Python 3.11 first. | Anyone with an older Python: the app used to fail silently. A test runs the real `.bat` with stand-in programs. |
| `0b9a34c` | The speed tests take the best of three runs (budgets unchanged). | The test suite: they failed while other work loaded the machine. |
| `2e7b960`, `d47bb62` | **Owner default:** export writes a new file, or replaces only a file it wrote itself that nobody changed since. It keeps a record in `.lore/exports.json`. | A writer exporting over a file of the same name: a planning document, a chapter, or their own `.aeon` timeline could be overwritten. Revert `2e7b960` to undo. |
| `0efad5b` | **Owner default:** AI tools (MCP) and the editor import and export only inside the world folder. The command line is unchanged. | Anyone running an AI assistant on a world: it could read or write any file the user can. Revert `0efad5b` to undo. |
| `52444a3` | **Owner default:** CSV and Aeon round trips keep dates and fields (spec 006 FR-6). | A writer importing from Aeon: every event gained a redundant `end` and every item an empty `tags: []`; Aeon lost decade and century precision. Losses the formats can't avoid are listed in the spec. |
| `48a173c` | `planning-change --remove` without a fact id is INVALID, not a crash. Two agent-skill examples fixed. | An AI client naming a fact by section and text (found by the round-3 audit). |
| `28ab884` | Aeon narrative-folder types (Book, Narrative Folder) import as narrative types. | A writer importing from Aeon: the Narrative view said "No chapters yet". |

Reverted for failing the bar (`5fb746b`): the import rollback after a late failure (needs a type name over 255 characters), the nested-JSON guards in the app and MCP (only a hand-made file), and the saga start lock rework (25 lines for a few seconds' wait). Trimmed (`b3a33b6`): the bounds-only date special case, the nested `--config` guard, and a launcher test that timed out under load.

Not changed, and why:
- `link` accepting an undeclared role: `specs/001-core/spec.md` allows it.
- MCP answering a JSON-RPC response object, and `tools/aeon_extract.py`'s traceback: nobody meets them.
- Audit findings judged fringe: a hand-edited bad calendar or checks setting crashes with exit 1; `fact-add` above chapter 9999; `fact-end` on a fenced code block; names `CONIN$` or `...`; `<!--` in fact text; `planning-fact` ignoring a version on a new page.

## Design pass: the editor, wiki and start screen

Method: every journey a novelist takes was screenshotted with Playwright at 1440 px and 390 px, plus dark mode, on scratch copies of a 116-item world imported from Aeon and the planning fixture. Five fresh-context Opus reviewers each took one lens: hierarchy and layout, words, flow and friction, visual craft (taste-skill, frontend-design) and accessibility (design:accessibility-review). Then fixes, new screenshots, and a fresh reviewer each round until the remaining findings were data or taste. Four review rounds.

| Commit | What a writer now sees |
|---|---|
| `11c3ca7` | A selected item is marked in ink, not an orange outline that read as an error. Dates of a single moment read once, not "June 1778 to June 1778" (tooltips and screen readers). The status says "All changes saved" or "Unsaved changes in Heathcliff". Saving a date Lorekeeper can't read says the item is left off the Timeline. Focus stays in the inspector after Save. Save and Discard stay in reach. Ages headers show dates in words. "(or reborn)" appears only in worlds with rebirths. Continuity drops 24 repeated "Definite" pills. The "alive" line is visible (was 1.8:1 contrast). Wiki text has a reading width. |
| `709112f` | The inspector no longer says "No connections yet" for someone others link to, and "Linked from" comes before the add form. Continuity says "Hareton Earnshaw died June 1778, but takes part here (1 January 1803)." instead of a log line. The top bar no longer jumps as the status changes. The start screen no longer says "on the right" on a phone. |
| `ef01ba0` | "In two places at once" reads as a sentence. On a phone, Continuity and its problem count are visible and card lists scroll with the page. |
| `4f0479b` | The wiki card's own chapter picker is labelled "This card as of", so it isn't confused with the toolbar's. |

Left, with the reason: date fields show the file's form ("1764-07") with a "Reads as July 1764" line, because the spreadsheet cell is editable and rewriting it would change files; file paths stay as quiet secondary text (spec 013); a world imported before `28ab884` keeps its old type categories; a fresh history (Back button) after following a connection would be a new feature.

Screenshots: `C:\Users\Owner\lk-scratch\r4-design\shots\before\` and `...\after\` (`desk-*`, `phone-*`, `dark-*`; `r2-*` to `r4-*` are the later checks). The scripts are in `C:\Users\Owner\lk-scratch\r4-design\`.

## Round 3: tidy and graphify

| Commit | Change | Measured |
|---|---|---|
| `ec5e3ec` | Stopped tracking `build/lib/` and `lorekeeper.egg-info/`, a stale setuptools copy of the package from 17 October (no app, planning or wiki modules). `.gitignore` keeps them out. | −3,693 lines in git. |
| `ea902b2` | The ops table points at `wiki.fact_end`, `wiki.fact_remove`, `planning.impact` and `planning.change` directly; four pass-through wrappers and the unused `app.cli_command` are gone. | −23 lines. |
| `d93b509`, `d622d20` | graphify knowledge graph in `graphify-out/` (1,608 nodes, 3,516 edges, 95 communities). Built from code and Markdown structure with `graphify update .`: no LLM, no cost. Cache and dated backups are git-ignored; `.graphifyignore` leaves out `.claude/`, `.specify/` and the test fixture worlds. | |

**Codex review of rounds 2, design and 3** (branch diff against `fc3055f`): 9 findings. Fixed 4 that real use reaches (next commit): the save message said "left off the Timeline" when only an end date was unreadable; a `1990s` date narrowed by `date_min` was sent to Aeon as a whole decade; the check speed test timed a warm cache after the best-of-three change, which hid what a first check costs (the test now times a fresh project each run); export hashed any existing file even when its record ruled it out. Not changed, as nobody meets them: an edit landing during the milliseconds of an export, a `.lore` folder that is a symlink, two exports at the same instant, `.lore/exports.json` itself as an export target, and a client that declares a large body and then stalls.

Net since round 1: lorekeeper and tests +351 / −82 lines; whole repo −3,779 lines (excluding the graph).

Speed: not changed. The suite's own time swung from 2.5 to 19 minutes with other sessions' load, so no measurement this night is trustworthy enough to claim a gain.

Left on the audit's list: the retired continuity-kit hook script `tools/build-hooks/guard.py` (BUILD-NOTES says "kept for reuse"; your call), and three 2-line wrappers (`mcp.story_folder`, `app.world_name`, a duplicate lore.json read in `serve.stamp`) whose removal saves only a few lines each.

**graphify:** open `graphify-out/graph.html` in a browser, read `graphify-out/GRAPH_REPORT.md`, or ask `graphify query "how does export decide what it may overwrite"`, `graphify path "op_export" "atomic_write"`, `graphify explain "item_dates"`. Refresh after code changes with `graphify update .`. Semantic extraction of the docs (concepts across specs) was skipped; it would take subagent time for little gain over the structural graph.

## Other branches

`feat/008-editor-ux`, `feat/009-editor-followups`, `feat/010-progressive-wiki`, `feat/011-planning-wiki`, `fix/lives-flashbacks-overflow` and `fix/mcp-cache-hints` are all fully merged into main (0 commits ahead). They hold no unmerged work.

## How to merge and re-vendor

1. From the main checkout, run `git merge --ff-only claude/overnight-fixes-77b916`. main has not moved since `bec45dd`, so this fast-forwards.
2. Run `python -m unittest discover -s tests`. Expect 395 OK, 1 skipped.
3. Push to the private repo, if you approve.
4. Re-vendoring into the sagas follows the run-7 method in `docs/build/SESSION-LOG.md`:
   1. Copy every tracked file of `lorekeeper/` into each saga's `_system/vendor/lorekeeper/` in a clone, and set `VERSION`.
   2. Run each saga's own suite (`python -m unittest discover -s _system/tests`) and replay its status and validate outputs.
   3. Land by fast-forward.

   Changes that affect sagas: `lore mcp --saga` documentation now names `planning-fact`; a CLI export creates `<saga>/.lore/exports.json`; MCP import and export stay inside the saga folder; the editor design changes appear in `saga.py timeline`.
