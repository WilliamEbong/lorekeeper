# Overnight changes (2026-11-22 to 23)

## What changed for you, in plain words

**Nothing is merged yet.** Everything is on one branch, waiting for you. Your sagas have not been touched. The upgrade was rehearsed on throwaway copies of them (see "Merge and upgrade" below).

**In the editor you will notice:**
- It is calmer to read. Section headings are small Georgia titles instead of grey capitals, wiki and notes text keeps a comfortable line length, chart labels are a little larger and no longer crossed by gridlines, and dark mode shows its card edges.
- It tells you more plainly what is going on. The top bar says "All changes saved" or "Unsaved changes in Heathcliff". If you save a date Lorekeeper can't read, it says the item is left off the Timeline until the date can be read. A selected item is outlined in ink, not an orange that looked like an error.
- Continuity problems read as sentences: "Hareton Earnshaw died June 1778, but takes part here (1 January 1803)."
- The inspector no longer says "No connections yet" for someone that others link to, and "Linked from" comes before the form for adding a connection.
- On a phone, Continuity and its count are visible, and "Open" takes you straight to the item.

**Behind the scenes:**
- Export never overwrites one of your own files: it writes a new file, or replaces only a file it wrote itself that nobody has changed since.
- AI assistants (through MCP) and the editor can only import and export inside the world's folder.
- Importing from Aeon or CSV keeps more: no stray end dates or empty tags, Aeon's decade and century dates, Aeon "Narrative Folder" types, and a warning when a CSV has columns your world doesn't know (before, those links were silently lost).
- Answers an AI gets are more trustworthy. "Where was she in 1780?" now says it isn't sure when she moved that year, and a misspelled connection kind gets a warning.
- `Open Lorekeeper.bat` checks your Python version instead of failing silently.
- The repository is about 3,800 lines lighter: an old copy of the program that was committed by mistake is gone.
- There is a map of the code in `graphify-out/` that AI tools can search.

**What you might decide:** three of the choices above were yours to make, and each is one commit you can undo: the export rule, keeping AI tools inside the world folder, and the import round-trip rules (see Round 2). Then merge, and upgrade the sagas if you want the new editor there.


This was a maintenance pass on branch `claude/overnight-fixes-77b916`, taken from main at `bec45dd`. Nothing was pushed or merged, and the sagas were not touched.

The pass fixed defects and added no features. Each fix began with a test that failed and passed once the fix was in. The full suite passed before every commit. Three read-only Opus agents audited the codebase in parallel; every lead they raised was confirmed in the code before it was acted on. Codex then reviewed the branch diff twice. Its confirmed findings are fixed below; the rest are listed under "Found, not changed".

## Tests

- **Before:** `python -m unittest discover -s tests` gave 376 OK (1 skipped, POSIX-only).
- **After round 1:** 383 OK (1 skipped).
- **Now:** 397 OK (1 skipped).
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

**Codex review of rounds 2, design and 3** (branch diff against `fc3055f`): 9 findings. Fixed 4 that real use reaches (`49885a5`): the save message said "left off the Timeline" when only an end date was unreadable; a `1990s` date narrowed by `date_min` was sent to Aeon as a whole decade; the check speed test timed a warm cache after the best-of-three change, which hid what a first check costs (the test now times a fresh project each run); export hashed any existing file even when its record ruled it out. Not changed, as nobody meets them: an edit landing during the milliseconds of an export, a `.lore` folder that is a symlink, two exports at the same instant, `.lore/exports.json` itself as an export target, and a client that declares a large body and then stalls.

Net since round 1: lorekeeper and tests +351 / −82 lines; whole repo −3,779 lines (excluding the graph).

Speed: not changed. The suite's own time swung from 2.5 to 19 minutes with other sessions' load, so no measurement this night is trustworthy enough to claim a gain.

Left on the audit's list: the retired continuity-kit hook script `tools/build-hooks/guard.py` (BUILD-NOTES says "kept for reuse"; your call), and three 2-line wrappers (`mcp.story_folder`, `app.world_name`, a duplicate lore.json read in `serve.stamp`) whose removal saves only a few lines each.

**graphify:** open `graphify-out/graph.html` in a browser, read `graphify-out/GRAPH_REPORT.md`, or ask `graphify query "how does export decide what it may overwrite"`, `graphify path "op_export" "atomic_write"`, `graphify explain "item_dates"`. Refresh after code changes with `graphify update .`. Semantic extraction of the docs (concepts across specs) was skipped; it would take subagent time for little gain over the structural graph.

## Round 4: independent acceptance, upgrade rehearsal, design cycle 2

**Acceptance.** Three fresh Opus agents used Lorekeeper end to end from the documentation alone, each on copies in `C:\Users\Owner\lk-scratch\r8-accept-*`: a novelist on the command line, an AI assistant over MCP, and a novelist in the editor and start screen. Fixed what they hit in real use:

| Commit | Who notices, and what changed |
|---|---|
| `3545a41` | An AI assistant. `where` at a year in which the person moves said "certain"; it now flags uncertainty, and asked at an event the person attends it is sure. `link` with a misspelled role warns. A stale-version CONFLICT says what to do. `show` no longer lists backlinks under "null". The agent guide explains chapter marks and that `mcp --saga` has no `request`. |
| `56fe4cd` | A novelist on the command line. A CSV import lost 103 of 259 links silently; it now warns which columns were skipped. The user guide gains a working custom-calendar example (checked by running it). `lore age` says when dates allow a range. |
| `d1de0d8` | A novelist in the editor. On a phone, Continuity's "Open" left the screen where it was; a merge message suggested someone else had edited the file. (Clearing a stale error on the next success was reverted after Codex showed it could hide an unrelated failed save.) |

Not changed, as nobody meets them in normal use or they are new features: a "who is at this place" query, a browser Back history in the editor, connection kinds filtered by item type, undo for spreadsheet cells (the README no longer promises it), the start screen's folder picker behaviour (could not be judged in a hidden test browser).

**Codex review of round 4** (branch diff against `2313013`): 5 findings, 4 fixed in `c8c3e40`: `where` treated a matching month as the event itself; the CSV warning advised re-importing, which skips existing items (it now says to import into a new world with the schema in place); `age` printed a negative lower bound ("-1 to 1"); and the error auto-clear was reverted. Not changed: the typo warning on a repeated identical `link` call.

**Design cycle 2** (`e092c7e`, `931036c`). Two fresh reviewers scored nine screens out of 10 for clarity, craft and reading comfort; after the changes a third scored them again.

| Screen | Before (lowest of two) | After |
|---|---|---|
| Start screen | 6–8 | 9 |
| Timeline | 7–8 | 8, then labels clear of gridlines (`931036c`) |
| Inspector | 7.5 | 9 |
| Wiki card | 7–7.5 | 9 |
| Continuity | 7–8 | 8, then text in ink (`931036c`) |
| Spreadsheet | 7–7.5 | 8.5, then a green "Open" (`931036c`) |
| Relationships | 8 | 9 |
| Phone | 7 | 8 |
| Dark | 8 | 9 |

Screenshots: `C:\Users\Owner\lk-scratch\r4-design\shots\c2-before\` and `...\c2-after\`.

**Merge and upgrade rehearsal.** The branch still fast-forwards `main` (`bec45dd`). In throwaway copies under `C:\Users\Owner\lk-scratch\r8-clones` and `r8-probe` (the real sagas were only read), the engine was re-vendored by the run-7 method and each saga checked before and after:
- **Saga suites:** Realm 312, Space 309 and Zombies 304 tests, all OK before and after.
- **Outputs:** `saga.py health` and every chapter's `status` and `validate` output (13 chapters) are byte-identical before and after.
- **Engine:** the full comparison ran on `931036c`; the last code commit, `c8c3e40` (four small Codex fixes), was then re-vendored into the same copies and the three suites and `health` rerun: all OK (312, 309, 304) and `health` identical. Upgrade all three sagas together: each saga's own parity test checks that the three vendored engines match, so a saga upgraded alone fails it until the others follow.
- **Scripts:** `C:\Users\Owner\lk-scratch\snap\r8_rehearse.sh` and `r8_final.sh`; logs `r8-rehearse.log` and `r8-final.log` beside them.

## Design scoring: final scores

**Final scores** (S6; each is the lowest of clarity, craft and reading comfort for that screen, as the median of three fresh Opus reviewers who had not seen earlier versions): Start 8.5, Timeline 8, Subway 7.5, Relationships 8.5, Ages 7, Spreadsheet 8, Narrative 7, Wiki card 8, Planning card 8, Continuity 8.5, Inspector 8, New item form 8.5, Phone 7, Dark 8.5. No main screen reached 9 with all three reviewers. Several reached 9 with one or two of them: Start, New item, Dark, Relationships and Continuity.

**Method.** Six scoring rounds (S1 to S6), 18 reviewers in all, on Playwright screenshots of the running app: a copy of the 116-item Aeon import and the planning fixture, at 1440 px, 390 px and in dark mode. Each round, fixes went in for the causes at least two reviewers agreed on, structural ones first. No round was reverted as a whole. Within rounds, two changes that made things worse were undone or fixed straight away: a tint that hid the Ages warning colours, and a header reflow that made the phone header taller.

| Screen | S1 | S2 | S3 | S4 | S5 | S6 |
|---|---|---|---|---|---|---|
| Start (with worlds) | 8 | 8 | 8.5 | 9 | 8.5 | 8.5 |
| Timeline | 8 | 8 | 8.5 | 8.5 | 8.5 | 8 |
| Subway | 7 | 7 | 8 | 8 | 8 | 7.5 |
| Relationships | 8.5 | 8 | 8.5 | 8.5 | 8.5 | 8.5 |
| Ages | 6 | 7 | 7 | 7 (regression, fixed) | 7.5 | 7 |
| Spreadsheet | 8 | 7 | 8.5 | 8 | 8 | 8 |
| Narrative | 8 | 6 | 6 | 7 | 7 | 7 |
| Wiki card | 7.5 | 7 (not captured) | 8.5 | 8 | 8 | 8 |
| Planning card | 7 | 7 | 8 | 7.5 (regression, fixed) | 7.5 | 8 |
| Continuity | 8 | 8 | 8.5 | 8.5 | 8.5 | 8.5 |
| Inspector | 8 | 8 | 8 | 8.5 | 8 | 8 |
| New item form | 7.5 | 8 | 9 | 9 | 9 | 8.5 |
| Phone overall | 6.5 | 6 | 7.5 | 7.5 | 7 | 7 |
| Dark overall | 8.5 | 8 | 8.5 | 9 | 8.5 | 8.5 |

S1 is before this cycle; S2 is affected by a capture fault (the wiki card wasn't captured). Reviewer-to-reviewer spread is about ±1 point, so changes of 0.5 between rounds are noise.

**Rounds and commits:** S2 and S3 in `e7d5939`; S4 and S5 in `7cec7ba`; S6 in `d6427d0`.
- **Structural changes in these rounds:**
  - the empty inspector narrows, and is hidden on a phone;
  - card lists sit on the page, not in frames inside frames;
  - an imported world's story parts are listed;
  - one chapter control on the wiki card;
  - on a phone, tapping a wiki entry shows the card;
  - the phone tabs fit in two rows.
- **Wording and craft:** listed in each commit message.

**Codex review of the scoring rounds** (branch diff against `8f6a17a`): 6 findings, all fixed in `3f96750`. A long wiki card overflowed the wiki area. "part" matched "apartment" and "participant" in the Narrative fallback. Ages shaded undetermined cells green. The spreadsheet's Open was invisible on touch screens. A failed age kept "working out…". "Childs" was shown instead of "Children".

**Why the scores stopped at 7 to 8.5, and what a 9 would need.** Scores stopped rising after S3, through four rounds of changes. What the reviewers still name are structural changes that amount to new layouts or features:
- **Phone (7):** a layout built for a phone rather than the desktop layout squeezed down. That means a tab menu, a per-person list for Ages, stacked rows for the Spreadsheet, and no scroll areas inside the scrolling page.
- **Ages (7):** a person-by-event grid is mostly blank by nature, so it needs a different view, such as a list per person. Swatches in the key would help a little.
- **Narrative (7):** this imported world's story parts have no chapter numbers. That is data, and it is fixed by giving them numbers (or a feature to set the order in place). A world with chapters (the planning fixture) shows them in order.
- **Subway (7.5):** crowded years need clustering, or zooming to a period.
- **Spreadsheet and Inspector (8):** to show dates in words in fields you can edit, those fields need a display mode separate from editing. That is a change of behaviour; the decision so far has been to show the date as written, with "Reads as …".
- **All screens:** the Inspector column is always reserved, and several views scroll inside the page. Changing either is a layout redesign, not a fix.

Screenshots for every round: `C:\Users\Owner\lk-scratch\r4-design\shots\s1` to `s6`.

## Other branches

`feat/008-editor-ux`, `feat/009-editor-followups`, `feat/010-progressive-wiki`, `feat/011-planning-wiki`, `fix/lives-flashbacks-overflow` and `fix/mcp-cache-hints` are all fully merged into main (0 commits ahead). They hold no unmerged work.

## How to merge and re-vendor

**Merge** (from the main checkout, `C:\Users\Owner\OneDrive\Documents\Lorekeeper`):
1. `git merge --ff-only claude/overnight-fixes-77b916` (main has not moved since `bec45dd`, so this fast-forwards).
2. `python -m unittest discover -s tests`: expect 397 OK, 1 skipped.
3. Push to the private repo, if you approve.

Rollback for the merge: `git reset --hard bec45dd` on main, before pushing. After pushing, revert instead of resetting.

**Upgrade the sagas** (optional; rehearsed above). For each of Realm Saga, Space saga and Zombies saga, in a clone, as in run 7:
1. Replace the files in `_system/vendor/lorekeeper/` with every tracked file of `lorekeeper/` from the merged main, and write the main commit's short hash into `_system/vendor/lorekeeper/VERSION`.
2. `python -m unittest discover -s _system/tests` (expect 312, 309 and 304 OK), `python _system/scripts/saga.py health`, and `status`/`validate` for the chapters in progress: the outputs should match the ones from before.
3. Commit as `system: vendor Lorekeeper <hash>` and land by fast-forward.

Rollback for a saga: `git revert <that system commit>` in the saga (it touches only `_system/vendor/lorekeeper/`). The engine they run today is `456bfe9`.

What the sagas will notice: the editor (`saga.py timeline`) gets the design changes; `lore mcp --saga` import and export stay inside the saga folder; a command-line export records itself in `<saga>/.lore/exports.json`; `where`, `link` and CSV import messages are clearer. Their own saga tooling output is unchanged (byte-identical in the rehearsal).
