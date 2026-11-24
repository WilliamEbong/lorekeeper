# Overnight changes (2026-11-22 to 23)

## What changed for you, in plain words

**This is merged and pushed.** On 2026-11-23 `main` was fast-forwarded to `99b13f1` and pushed to the private repo, and all three sagas were upgraded to engine `99b13f1`, changing only `_system/vendor/` in each. A later interface-only design pass (`f080dca`) also landed on `main`; the sagas were not re-vendored for it, which is optional (see "Merge and upgrade" below).

**In the editor you will notice:**
- It is calmer to read. Section headings are small Georgia titles instead of grey capitals, wiki and notes text keeps a comfortable line length, chart labels are a little larger and no longer crossed by gridlines, and dark mode shows its card edges.
- It tells you more plainly what is going on. The top bar says "All changes saved" or "Unsaved changes in Heathcliff". If you save a date Lorekeeper can't read, it says the item is left off the Timeline until the date can be read. A selected item is outlined in ink, not an orange that looked like an error.
- Continuity problems read as sentences: "Hareton Earnshaw died June 1778, but takes part here (1 January 1803)."
- The inspector no longer says "No connections yet" for someone that others link to, and "Linked from" comes before the form for adding a connection.
- On a phone, Continuity and its count are visible, and "Open" takes you straight to the item.
- Ages shows one card per person, listing only the events they are in. A birth reads "newborn", and a card with impossible ages says so in one line.
- Narrative lists story parts the same way in every world. In an imported world you click the dash beside a part to give it a chapter number, and parts without one sit under "Not placed yet".
- Dates read in words ("July 1764") in the Spreadsheet and the Inspector until you click into the field to change them.
- On the Subway, stops crowded into one year merge into a numbered circle. Click it to zoom in; events on the very same day are listed under the chart.
- File names and line numbers are out of sight: hover over "Open Hindley Earnshaw" or the item's kind to see them.
- On a phone, one View menu replaces the two rows of tabs, the Spreadsheet shows names and dates, and long Subway names wrap.

**Behind the scenes:**
- Export never overwrites one of your own files: it writes a new file, or replaces only a file it wrote itself that nobody has changed since.
- AI assistants (through MCP) and the editor can only import and export inside the world's folder.
- Importing from Aeon or CSV keeps more: no stray end dates or empty tags, Aeon's decade and century dates, Aeon "Narrative Folder" types, and a warning when a CSV has columns your world doesn't know (before, those links were silently lost).
- Answers an AI gets are more trustworthy. "Where was she in 1780?" now says it isn't sure when she moved that year, and a misspelled connection kind gets a warning.
- `Open Lorekeeper.bat` checks your Python version instead of failing silently.
- The repository is about 3,800 lines lighter: an old copy of the program that was committed by mistake is gone.
- There is a map of the code in `graphify-out/` that AI tools can search.

**Design scores:** after this pass, fresh reviewers score the screens between 6.5 and 8 out of 10, with no screen at 9. The Subway and the phone layout are lowest (6.5), and the reasons are listed under "Design pass 3". Nothing found should stop the merge: the full suite passes (397 tests), and the final Codex review's confirmed findings are fixed.

**What you might decide:** three of the choices above were yours to make, and each is one commit you can undo: the export rule, keeping AI tools inside the world folder, and the import round-trip rules (see Round 2). The merge and the saga upgrade are done (see above).


This was a maintenance pass on branch `claude/overnight-fixes-77b916`, taken from main at `bec45dd`. At the time of writing nothing was pushed or merged and the sagas were untouched; both happened later the same day (see the top of this file).

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

## Design pass 3: acting on the reviewers' list

The reviewers' reasons said what a 9 would need, so this pass made those changes, including small features and layout changes where they asked for one. Lowest screens first. One commit per item, each tested in the browser, the full suite green at each commit.

**Round A (from the S6 list):**
- Ages: one card per person instead of a mostly blank grid (`7f0619d`).
- Phone: one View menu in place of two rows of tabs, and no scroll areas inside the scrolling page except the charts (`e1ccde0`).
- Narrative: a chapter number can be set in place (`90b0d09`).
- Spreadsheet: dates read in words until a cell is edited (`45b3d90`).
- Subway: crowded stops merge into numbered stops that zoom in (`a5fe0eb`).

**S7 scores** (three fresh Opus reviewers; median of each reviewer's lowest axis): Start 7.5, Timeline 7.5, Subway 7, Relationships 8, Ages 7, Spreadsheet 7.5, Narrative 6.5, Wiki card 7.5, Planning card 7.5, Continuity 7.5, Inspector 7, New item 7.5, Phone 6.5, Dark 7.5. These reviewers were stricter than S6's: they marked down things S6 had passed. All three named the same next changes, which Round B makes.

**Round B (what all three S7 reviewers named):**
- Ages: "newborn", not "0 minutes"; the death date beside the birth date; one plain line on a card with impossible ages (`832a247`).
- Narrative: one list design in both worlds, with unnumbered parts under "Not placed yet" (`e2ab100`).
- Codex review of rounds A and B: seven findings, all confirmed and fixed (`c081bc8`).
- File paths and line numbers moved into tooltips (`b03b13e`).
- Inspector: date fields read in words until focused, and Save always looks like a button (`0bc931f`).
- Subway: names wrap on a phone, with quieter connector lines and a plainer key (`7022c74`).
- Phone Spreadsheet: the name and dates are in view, with the name held in place (`390f52a`).
- Dark mode: the main button is deep green instead of a glaring pale mint (`95af289`).

**Not done, and why:**
- The header says "imp2" while the start screen says "Wuthering Heights (imported)". This comes from my test copy: its settings file names it imp2, and I gave it a different name in the test list of worlds.
- "Narrative Folder" shows as a type name in the imported world. That is the import's own type name, part of the data, so renaming it is your decision about your world.
- Raised but not attempted:
  - Relationships cards of equal height;
  - Wiki chapter stepper wording;
  - a planning world opening on Wiki when nothing is dated;
  - grouping repeated Continuity problems.

**S8 scores (final)**, from three fresh Opus reviewers after Round B, scored the same way as S7:

| Screen | S7 | S8 |
|---|---|---|
| Start | 7.5 | 8 |
| Timeline | 7.5 | 7.5 |
| Subway | 7 | 6.5 |
| Relationships | 8 | 8 |
| Ages | 7 | 7.5 |
| Spreadsheet | 7.5 | 7.5 |
| Narrative | 6.5 | 7 |
| Wiki card | 7.5 | 7.5 |
| Planning card | 7.5 | 7.5 |
| Continuity | 7.5 | 7.5 |
| Inspector | 7 | 7.5 |
| New item form | 7.5 | 7.5 |
| Phone overall | 6.5 | 6.5 |
| Dark overall | 7.5 | 7.5 |

Ages, Narrative, Inspector and Start rose, and nothing fell beyond the ±0.5 noise between reviewers. No screen reached 9. The reasons the S8 reviewers still give, which are what remains:
- **Subway (6.5):**
  - the axis starts at the earliest birth, so the left of the chart is empty while stops crowd the right;
  - hollow, filled and numbered circles need a drawn legend, not a sentence.
- **Phone (6.5):**
  - the Timeline and Subway squeeze 60 years into 300 px with one or two year labels, and need a readable zoom with sideways scrolling;
  - the right gutter is wider than the left;
  - the inspector stacks under the view instead of opening as a sheet.
- **Narrative (7):**
  - the dash does not read as a control, and needs a visible "Set chapter" button;
  - reviewers also asked for drag-to-reorder.
- **Ages and Inspector (7.5):**
  - "adult" and "under 18" tints are too close;
  - an empty Connections line sits above a filled "Linked from";
  - the inspector's width changes when an item is selected.

Each of these is a further layout or interaction change, not a fix. They are listed here for a later pass.

**Final Codex review** (whole branch against main, at wrap-up): five findings. Four were confirmed and fixed in `90ce814`:
- chapter 0 (a prologue) can be set;
- a fresh Aeon import's unnumbered story parts get the chapter control;
- a long run of evenly spaced Subway stops lists its events instead of zooming in place for ever;
- "newborn" appears only for an exact birth day.

The fifth was not changed, as a fringe case. Exporting from a read-only world to a writable folder writes the file, then reports that the export ledger couldn't be saved, and a retry to the same path is refused. Nothing is lost, and you can export to a new name.

**What this pass taught.** Changes in presentation alone stopped moving the scores after S3. The rises came from changes in structure, such as Ages as cards and one Narrative design. A fresh set of reviewers marks harder than the last, so compare rounds only within one reviewer brief: S1 to S6, then S7 to S8.

Screenshots: `.playwright-mcp\design\s7` and `s8` in the worktree; reviewer tables in `C:\Users\Owner\lk-scratch\r4-design\s7-*.md` and `s8-*.md`.

## Design root-cause pass

Branch `claude/design-root-cause`, from `origin/main` at `7bb82a0`.


William asked what actually keeps the screens under 9, and for those causes to be fixed directly instead of running more rounds of fixes and rescoring. This table merges every reason the three S8 reviewers gave (S7's were the same in substance). "Said by" counts the S8 reviewers who named it. The table is the plan, biggest first.

| # | Screen(s) | Why it is under 9 | Said by | Root cause |
|---|---|---|---|---|
| 1 | Narrative, Subway, Wiki, Timeline | A control or mark whose meaning you have to guess: the clickable dash, unexplained hollow, filled and numbered circles, the "‹ Showing All chapters ›" stepper, the "Exact / Approximate / Alive" legend | 3 | Meaning is carried by bare glyphs and arrows, with no words on the control itself |
| 2 | Phone | Timeline and Subway squeeze 60 years into 300 px with one or two year labels; the right gutter is wider than the left; the inspector stacks under the view | 3 | The charts are drawn to the screen's width, not to a readable scale; the phone layout reserves a permanent scrollbar gutter |
| 3 | Ages, Continuity | One wrong death date shows as ten red pills on one card, and as 24 near-identical cards in Continuity | 3 | Errors are reported once per affected row, not once at their source |
| 4 | All (trust) | The Continuity badge says 24 while the phone menu says 26; the Timeline says 14 characters while the Wiki says 15 | 3 | The counts use different rules (definite only vs all; dated only vs all) without saying so. The 24 vs 26 gap is a regression from this pass's own Codex fix |
| 5 | Inspector | "Connections: None yet" sits above a filled "Linked from", which reads as a contradiction; the hint says "further down"; the panel changes width when an item is selected | 3 | Links are split by direction into two sections; the inspector has no fixed width |
| 6 | Start, Wiki, Spreadsheet | System words: "Folder: big", raw Windows paths, "Notes from the item's page", "species-human" tags, "Wiki as of" vs "Wiki" | 3 | Internal names and raw values are shown as they are stored |
| 7 | Narrative, Continuity, Relationships | Wide screens use only the left half; Relationships cards have ragged heights | 3 | Lists are capped at 80 characters with no layout for the remaining width; the card grid stretches to the tallest card |
| 8 | Planning card, Timeline | Zoom, scale and legend stay live over an empty canvas | 3 | Controls are drawn whether or not there is anything to control |
| 9 | New item form | A popover with no title, covering the toolbar | 3 | A floating form with no heading or anchor |
| 10 | All | Important instructions are in 12–13 px grey | 2 | Helper text is used for instructions as well as asides |

**Tactics, with their sources.** An Opus researcher read the William Web Design kit (`rules\` 00-HARD-RULES, COPY, CRAFT, PREFERENCES, MOTION; `templates\docs\DESIGN.md`) and the impeccable, frontend-design, minimalist-ui, design-critique and ux-copy skills. It also looked at how Aeon Timeline, World Anvil, Plottr and Scrivener solve the same problems. The kit is written for marketing sites, so only its rules on type, copy, glyphs and lists apply here.
1. **Words on the control, not a glyph.** "Set chapter" in place of the dash; a legend that draws the real marks beside plain words; a labelled "Show the wiki as of" menu in place of the arrows. Sources: CRAFT.md §1 ("never a Unicode glyph standing in"); PREFERENCES.md ("no stepper circles"); impeccable clarify; Plottr and Scrivener, where order comes from position.
2. **A chart at a readable scale on a phone, not a squeezed one.** A minimum width per year, scrolling sideways with the names held in place; no reserved scrollbar gutter. Sources: impeccable adapt ("don't squeeze"); World Anvil's list and timescale modes.
3. **Say an error once, at its source.** One line on the person's card and calm pills on the rows; Continuity problems grouped by the item they come from. Sources: impeccable distill ("if it's said elsewhere, don't repeat it"); CRAFT.md §2 ("Say it once"); Aeon's one warning on the broken constraint.
4. **One rule per count.** Done: the counts now say which rule they use.
5. **Group by meaning, hide what is empty.** One Connections section with "Links to" and "Linked from"; a fixed inspector width. Source: impeccable layout and clarify.
6. **Show the name, not the storage.** Folder names and paths on hover only; tags and headings in words. Source: COPY.md §5 ("say what they do").
7. **Prose has a measure; records use the width.** The 70-character limit applies to running text, while lists of records lay out as grids. Source: impeccable operate ("data can run denser").
8. **Controls only when there is something to control.** Source: design:ux-copy (what this is, why it is empty, how to start).
9. **A titled form anchored to its button.** Source: MOTION.md §10; impeccable operate.
10. **Instructions at reading size.** Helper text at 14 px in the muted token at 4.5:1 or better. Sources: COPY.md §5; impeccable craft-floor.

**Fixed, one commit per cause**, each tested in a clean browser context, with the full suite green (397 OK) at every commit. Branch `claude/design-root-cause`.
- **Cause 4, counts** (`e764713`):
  - The phone menu says "Continuity (24 definite, 2 possible)", as the Continuity screen does.
  - The Timeline's chips say "14 dated".
- **Cause 1, words on controls** (`67697de`):
  - "Set chapter" replaces the dash.
  - The Subway has a key that draws its marks.
  - The wiki card has a "This card as of" menu, and the toolbar says "Wiki as of" in every world.
  - The Timeline legend reads "Exact date / Approximate date / Lifetime".
- **Causes 2 and 8, phone and empty states** (`37d72cc`):
  - Below 600 px the Timeline is a list of cards by year, and the Subway is a card per person with their events in order.
  - No scrollbar gutter is reserved on the phone page.
  - A world with nothing dated shows its message without chart controls.
- **Causes 3 and 7, said once; records use the width** (`064bfee`):
  - Continuity groups problems that come from one person's date ("Cathy Linton: 13 events after they died"), with the events folded underneath. The imported world's 24 cards become 7.
  - The cards lay out in a grid.
  - The Ages row pills go quiet once the card has said why.
- **Cause 5, inspector** (`633030f`):
  - One 340 px width, selected or not.
  - Only sections with something in them are shown.
- **Causes 6 and 10, names and reading size** (`7d62ccc`):
  - No "Folder: big"; "Kept in" is a folder trail with the full path on hover.
  - The wiki card says "Notes", and its tags read as words.
  - Helper text is 14 px.
- **Cause 9, New item** (`657d048`): a "New item" heading, and a line on what happens next.
- **Cause 7, Relationships** (`41760c3`): the cards flow in columns with no ragged gaps, and the names look like links.

**Check of each cause.** A fresh Opus reviewer compared the S8 and S9 screenshots, asking one question per cause. It answered "gone" for all ten (`C:\Users\Owner\lk-scratch\r4-design\s9-causes.md`).

**S9 scores**, from three fresh Opus reviewers on the same brief as S7 and S8, with screenshots from a clean browser:

| Screen | S8 | S9 |
|---|---|---|
| Start | 8 | 8 |
| Timeline | 7.5 | 7.5 |
| Subway | 6.5 | 7 |
| Relationships | 8 | 8.5 |
| Ages | 7.5 | 7.5 |
| Spreadsheet | 7.5 | 7 |
| Narrative | 7 | 7 |
| Wiki card | 7.5 | 7.5 |
| Planning card | 7.5 | 8 |
| Continuity | 7.5 | 8 |
| Inspector | 7.5 | 8 |
| New item form | 7.5 | 7.5 |
| Phone overall | 6.5 | 7.5 |
| Dark overall | 7.5 | 8 |

Phone rose a full point, and Subway, Relationships, Planning, Continuity, Inspector and Dark rose half a point each. Spreadsheet fell half a point, which is within the noise. No screen reached 9.

**What the S9 reviewers name now.** All three agree on each item. These are the causes for the next pass:
- **Narrative:**
  - A world with 40 unnumbered parts shows 40 identical "Set chapter" buttons.
  - The fix is one "Number these in this order" action, with the per-row control shown on hover.
- **Spreadsheet:**
  - Location is cut off ("Wuthering Heig…") while other columns have room.
  - The phone cuts names short.
  - Column widths need to follow their content.
- **New item:** the popover covers the Inspector heading. It should open below its button, clear of the panel.
- **Timeline:**
  - Event labels crowd and are clipped at the bottom of the chart.
  - A person with only a birth date shows as a bare dot.
- **Subway:** the hairlines between shared events still bunch up near 1800, and half the chart below the lanes is empty.

**How each fix was verified:**
- In the browser, by checking the specific thing each cause names, in a clean Playwright context, at 1440 px and at 390 px or 360 px. For example: the counts read 24 in both places; the inspector is the same width selected and unselected; no sideways scroll at 360 px.
- By the full suite, green (397 OK) at every commit.
- Then by a fresh reviewer, asked one question per cause about the before (S8) and after (S9) screenshots.

**Final Codex review** of the branch against `origin/main`: seven findings, six confirmed and fixed in `3166b30`:
- a date with a time is grouped under its year on the phone Timeline;
- list and chart swap when the window crosses 600 px;
- Continuity cards fit a 360 px screen;
- possible problems are worded as uncertain;
- the phone lists keep the undated-items and top-8 notices.

The seventh, two characters with the same name grouped together, is a fringe case; Continuity already flags duplicate names.

**How reliable the scores are.**
- Each score is the median of three reviewers, and each reviewer's score is the weakest of three aspects. Different reviewers on the same screenshots differ by about ±0.5 to 1 point, so a half-point move, up or down, is noise.
- S8 fell from S6 mostly because the brief changed: from S7 on, a 9 meant "ship it in a commercial writing app without changes", and the reviewers saw the phone, the planning world and dark mode as well. One real regression (cause 4) added to it, and so did test data being read as design.
- Scores move only about half a point when a cause is confirmed gone because each fresh reviewer finds the next weakest thing on the screen. Removing the worst problem exposes the second, and the score is set by whatever is now weakest.
- So the per-cause check ("is this gone?") is the reliable measure. The 1–10 score is a rough guide to how much is left.

**Does this branch affect the sagas?**
- It changes only the editor's interface: `editor.js`, `editor.css`, `editor.html` and `app.js`. No Python engine file changes, so no data, check, MCP or command-line behaviour changes.
- The sagas vendor the whole `lorekeeper/` folder, editor included, so they get the new interface only after a re-vendor.
- A re-vendor is optional. Their tests, `saga.py` tooling, MCP and skills don't depend on these files.

**Not design causes** (so not fixed here):
- "imp2" in the header comes from the test copy's settings file.
- Cathy Linton dying on her birth day, and the "Narrative Folder" type name, are the imported data.
- They still show the need for cause 3: a data error should be said once.

**Why S7 and S8 scored lower than S6**, a mix of three things:
- Stricter reviewers. From S7 the brief said a 9 means "ship it in a commercial writing app without changes", and it gave the reviewers more screens: the planning world, every phone screen, dark mode.
- One real regression: the 24 vs 26 count (cause 4).
- Data shown as design: Cathy's dates and "imp2", above.

A capture problem was ruled out: each journey clears the browser's remembered settings before the planning world.

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

**How to check each saga still works on the new engine.** Run these in each saga folder (Realm Saga, Space saga, Zombies saga), after the vendor commit:
1. Version: `type _system\vendor\lorekeeper\VERSION` shows the merged main's short hash, no longer `456bfe9`.
2. The saga's own tests: `python -m unittest discover -s _system/tests`. Expect 312 (Realm), 309 (Space) and 304 (Zombies) OK, as in the rehearsal.
3. Saga health: `python _system\scripts\saga.py health` reports no new problems compared with before, and `python _system\scripts\saga.py status` matches.
4. Lore check: `python _system\vendor\lorekeeper --root Wiki --config _system\lorekeeper.json check`. Expect the same findings as before the upgrade (same count, same items).
5. Launcher: double-click `Open Realm Lorekeeper.bat` (or Space, Zombies) in `Creative writing`. The editor opens at `http://127.0.0.1:8701/` (8702, 8703 for the others) and shows the saga's items. The inspector's button reads "Propose change", and the new design is visible: the View menu on a narrow window, and Ages as cards.
6. MCP: in a Claude Code session opened in the saga folder, `/mcp` lists `lorekeeper` as connected. Asking "what does Lorekeeper know about <a character>" returns that character. The server runs the command in the saga's `.mcp.json`: the vendored engine with `--root Wiki --config _system/lorekeeper.json mcp --saga`.
7. Skills: `_system/skills/story_wiki_update.md` and `planning_wiki_change.md` name Lorekeeper tools. Check those tool names still appear in the tool list the MCP server reports (step 6). This release renames no tools.

What the sagas will notice: the editor (`saga.py timeline`) gets the design changes; `lore mcp --saga` import and export stay inside the saga folder; a command-line export records itself in `<saga>/.lore/exports.json`; `where`, `link` and CSV import messages are clearer. Their own saga tooling output is unchanged (byte-identical in the rehearsal).

## Saga upgrade (2026-11-23, landing)

**2026-11-23: design root-cause pass landed.** `main` fast-forwarded `7bb82a0` → `f080dca` and pushed; suite 397 OK (1 skipped). The three sagas stay on engine `99b13f1`: only the editor interface changed, so a re-vendor is optional and was not done.

**Merged and pushed:** `main` fast-forwarded `bec45dd` → `99b13f1` and pushed to the private repo. Suite: 397 OK (1 skipped).

**The live sagas had uncommitted work that is not the engine's:**
- Realm Saga and Zombies saga: `_system/logs/saga.log` has one uncommitted line each ("CH004 runtime scratch removed", 31 Oct).
- Space saga: untracked `Chapters/CH005/` (chapter, READY_FOR_HUMAN, 30 Oct) and `_system/state/CH005.json`, `_system/state/provenance/CH005.json`.

The landing first held the sagas because of this. The orchestrator then decided, under the judgment William had delegated, to upgrade all three with the vendor folder only and leave that work exactly as it was. Each saga's parity test needs all three engines to match, so all three were done back to back.

**Landed in the live sagas** (script `C:\Users\Owner\lk-scratch\snap\r9_land.sh`, checks `r9_live_check.sh`, logs `snap/r9-land.log` and `snap/r9-live.log`, before/after files in `lk-scratch\r9-live`). Every tracked file of `lorekeeper/` at `99b13f1` was copied into `_system/vendor/lorekeeper/`, with `VERSION` set to `99b13f1`. Only `git add -- _system/vendor` was staged. There was no stash, checkout or clean.

| Saga | Commit | Engine | Tests (incl. parity) | `lore check` | `saga.py health` | MCP handshake, both launch forms | Launcher (`saga.py timeline`) |
|---|---|---|---|---|---|---|---|
| Realm | `6ef5c4c` → `4194bd5` | `456bfe9` → `99b13f1` | 312 OK | 0 FAIL, 0 WARN | identical to the `456bfe9` baseline | OK / OK | port 8701 served `/` (200), then stopped |
| Space | `778af5a` → `f5147cf` | `456bfe9` → `99b13f1` | 309 OK | 0 FAIL, 0 WARN | identical | OK / OK | port 8702, 200, stopped |
| Zombies | `ff7aaef` → `ebac53d` | `456bfe9` → `99b13f1` | 304 OK | 0 FAIL, 0 WARN | identical | OK / OK | port 8703, 200, stopped |

Each commit, `chore: re-vendor lorekeeper 99b13f1`, touches 17 files, all under `_system/vendor/`. They match `main` byte for byte. `git status --porcelain` is the same before the commit, after it and after every check. The SHA-256 hashes of the owner's uncommitted files match before and after: 1 file in Realm, 11 in Space, 1 in Zombies. None of the sagas has a remote, so nothing was pushed.

Rollback for a saga: `git revert <its re-vendor commit>`. Revert all three together, because of the parity test.

**Dry run on merged main, before landing (throwaway probes `C:\Users\Owner\lk-scratch\r8-probe`, script `snap/r9_main.sh`, log `snap/r9-main.log`):** every tracked file of `lorekeeper/` at `99b13f1` copied in and `VERSION` set, by the run-7 method.

| Saga | Engine before → after | Tests before / after | `lore check` before / after | `saga.py health` | MCP handshake (`handshake5.py`) |
|---|---|---|---|---|---|
| Realm | `c8c3e40` → `99b13f1` | 312 OK / 312 OK | 0 FAIL, 0 WARN / same | identical | OK / OK |
| Space | `c8c3e40` → `99b13f1` | 309 OK / 309 OK | 0 FAIL, 0 WARN / same | identical | OK / OK |
| Zombies | `c8c3e40` → `99b13f1` | 304 OK / 304 OK | 0 FAIL, 0 WARN / same | identical | OK / OK |

Vendored files byte-identical to `main`. Between `c8c3e40` and `99b13f1` only editor files changed (`app.css`, `app.js`, `editor.css`, `editor.html`, `editor.js`).
