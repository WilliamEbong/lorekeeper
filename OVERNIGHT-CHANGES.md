# Overnight changes (2026-11-22 to 23)

This was a maintenance pass on branch `claude/overnight-fixes-77b916`, taken from main at `bec45dd`. Nothing was pushed or merged, and the sagas were not touched.

The pass fixed defects and added no features. Each fix began with a test that failed and passed once the fix was in. The full suite passed before every commit. Three read-only Opus agents audited the codebase in parallel; every lead they raised was confirmed in the code before it was acted on. Codex then reviewed the branch diff twice. Its confirmed findings are fixed below; the rest are listed under "Found, not changed".

## Tests

- **Before:** `python -m unittest discover -s tests` gave 376 OK (1 skipped, POSIX-only).
- **After:** 383 OK (1 skipped).
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

## Found, not changed

Each of these is below the confidence bar, needs your decision, or needs a browser.

- **Export can still replace some project files.**
  - Codex pass 2 found two cases the guard misses:
    - planning sources such as `World Bible.md`, or prose chapter files, can live outside the planning folder, even outside the project root;
    - a `--config` file named with an `.md` extension.
  - Both need an explicit export path from the CLI (saga mode blocks export over HTTP and MCP).
  - Recommendation: decide whether export should only ever write a new file, or replace one it wrote itself. That is a behaviour choice, so it was left for you.
- **A refused import can still leave a changed `lore.json`.** If folder creation fails for a reason the preflight doesn't check, the new type is already saved. Examples are a type name longer than 255 characters (Codex) or a path over the Windows length limit. Recommendation: restore the original `lore.json` bytes when `create` fails during import.
- **Export can write anywhere.** Over HTTP and MCP, `export` writes to any absolute or working-directory path, and `import` reads any path. This is documented ("relative to the process working directory unless absolute"). The HTTP route needs the editor's token. Recommendation: if AI clients should be confined, restrict `out` to the world folder in MCP and HTTP.
- **Oversized HTTP bodies reset the connection.** A body over the limit (serve and app) gets a connection reset on Windows instead of a readable 400. Memory stays bounded. Recommendation: send `Connection: close` and drain up to a cap.
- **MCP replies to responses.** The MCP server answers a JSON-RPC response object (`{"id":1,"result":{}}`) with an error. Harmless in practice, since the server never sends requests.
- **Round trips lose some date detail.**
  - A date known only by `date_min`/`date_max` narrows to its lower bound after CSV or Aeon export and import.
  - CSV re-import adds `end` equal to `date` and `tags: []`.
  - A CSV text value that looks like a JSON list comes back as a list.
  - Aeon export drops century, decade and week precision, and writes a born-only person with a null end.
  - Recommendation: a spec decision about how bounds-only dates export.
- **`lore app --install` prints a traceback before the friendly message** if PowerShell fails (code reading only; the exit code is still 1, so `Set up Lorekeeper.bat` reports the failure).
- **`--config` input that is deeply nested** raises a RecursionError traceback. The same applies to app reads of a person's own `.mcp.json`.
- **`cli.main` with a non-console stdout:** calling it in-process with stdout redirected to a `StringIO` fails on `reconfigure`. Only in-process callers are affected.
- **`link` accepts an undeclared role,** and `check` doesn't flag it. This may be intended.
- **`Open Lorekeeper.bat` doesn't check the Python version.** `Set up Lorekeeper.bat` does. With Python 3.10 or older, the window-less app fails silently. Otherwise the quoting is sound.
- **`tools/aeon_extract.py`** prints a raw traceback if the exe is missing. It is a developer tool.
- **`app.open_saga`** holds the app lock for up to 20 s while a saga starts (code reading only). Other open actions wait.
- **A flaky performance test:** `test_perf` (1.5 s load limit) failed twice at about 9 s, when other overnight sessions loaded the machine, and passed on rerun. Not changed.
- **Needs a browser check:** none of the changes touch the UI. #9 changes which message the app shows for a corrupt `lore.json`, from the generic one to "settings file can't be read". I checked it by test, not in a browser.

## Other branches

`feat/008-editor-ux`, `feat/009-editor-followups`, `feat/010-progressive-wiki`, `feat/011-planning-wiki`, `fix/lives-flashbacks-overflow` and `fix/mcp-cache-hints` are all fully merged into main (0 commits ahead). They hold no unmerged work.

## How to merge and re-vendor

1. From the main checkout, run `git merge --ff-only claude/overnight-fixes-77b916`. main has not moved since `bec45dd`, so this fast-forwards.
2. Run `python -m unittest discover -s tests`. Expect 383 OK, 1 skipped.
3. Push to the private repo, if you approve.
4. Re-vendoring into the sagas follows the run-7 method in `docs/build/SESSION-LOG.md`:
   1. Copy every tracked file of `lorekeeper/` into each saga's `_system/vendor/lorekeeper/` in a clone, and set `VERSION`.
   2. Run each saga's own suite (`python -m unittest discover -s _system/tests`) and replay its status and validate outputs.
   3. Land by fast-forward.

   One change affects sagas: `lore mcp --saga` documentation now names `planning-fact`. The behaviour is unchanged.
