# HANDOFF — Lorekeeper

Final state after run 4 (2026-10-19). Authoritative, including over memory and older summaries. History: SESSION-LOG.md (the "Run 4" entries), BUILD-PLAN.md ("Run 4" section), specs/010-progressive-wiki (spec with Clarifications, plan.md, tasks.md).

## 1. Snapshot

Lorekeeper (command `lore`) is a standalone, stdlib-only story-world engine: Markdown files, one per item; dates, ages and continuity checks; one operations table driving a CLI (`--json`), an MCP server (`lore mcp`) and a local browser editor (`lore serve`). Feature 010 adds the **progressive story wiki**: chapter stamps on facts (`[ch 7]`, `[ch 2-5]`), an index and cards as the reader knows them after chapter N, and a complete mode.

## 2. Current state

- **Lorekeeper:** branch `feat/010-progressive-wiki`, local commits only. **Not pushed and not merged into `main`**; both wait for the owner. `main` = `origin/main` = d0b564a.
  - Run 4 commits: 8b4ea81, 21c5931 (spec work), 25cd2aa (engine, ops, CLI, MCP), 66b3d95 (Wiki tab), 8ea9023 (templates, docs), 0f6aaaa (reveal as a section), 73bd8a1, 9364e92 (editor polish), 88d131c (review fixes), 64d84c8 and this handoff (docs).
  - Suite: 312 OK (1 POSIX-only skip). Impeccable detector on editor.html: `[]`.
- **Sagas (landed fast-forward, 2026-10-19):**

  | Saga | Live HEAD | Vendored engine | Story Wiki | In progress (untouched) |
  |---|---|---|---|---|
  | Realm | `bbf9b36` | `88d131c` | CH001–003, 29 entries | CH004 at READY_FOR_HUMAN |
  | Space | `1390389` | `88d131c` | CH001–004, 24 entries | CH005 at READY_FOR_HUMAN |
  | Zombies | `5821c8f` | `88d131c` | CH001–003, 21 entries | CH004 at READY_FOR_HUMAN |

  Each saga has: the `story_wiki` key in `_system/lorekeeper.json`, a `Story Wiki/` folder, the shared skill `_system/skills/story_wiki_update.md` with its README row and one paragraph in PIPELINE §6 (after `freeze N`, before `cleanup N`), and `.mcp.json` running `lore mcp --saga`.
- **In flight:** nothing. Resume cron deleted.

## 3. What feature 010 does (for the owner)

- **Progressive mode:** pick chapter N and the wiki lists only what the reader has met, under the names the reader knows; each entry opens a card with its own chapter control. Someone seen before being named is listed under the reader's description. A secret identity is its own card until the reveal chapter, then folded in ("as Lord Vane").
- **Complete mode:** everything as of the latest chapter, all identities on one card, ended facts marked "no longer current", page fields and the working page shown.
- **Spoiler guard:** at chapter N no answer (editor, CLI, MCP JSON) contains a hidden name, a later chapter's title, a page path or a fact from later.
- **AI use:** operations `wiki`, `fact-add`, `fact-end`, `fact-remove` (CLI with `--json`, MCP tools, editor API) with guides written for AI readers; facts are written only through them.

## 4. Decisions the owner may want to change (each logged with how to undo it)

1. `--config FILE` for worlds whose settings are not in `lore.json`; `lore mcp --saga` offers only reading tools and the three fact tools, and refuses them without a story folder.
2. Undo uses a fourth operation, `fact-remove`, and `fact-end --reopen`.
3. Companion pages are named `<Name> (story).md` under `Story Wiki/<Type plural>/`.
4. Chapters, books, sessions and saga chapter cards are never wiki entries; they only label the chapter list.
5. A reveal can be written as a `## Revealed to be` section (so AI can record it with fact-add).
6. Entry keys are opaque (`id:…`); in progressive mode the editor's Edit button and page paths appear only in Complete.
7. The saga after-freeze update runs between `freeze N` and `cleanup N` (cleanup deletes the approved deltas it reads). It is outside the stage machine; skipping it only leaves the Story Wiki behind.
8. Backfill scope: standalone story pages only for named people who matter; e.g. no page for Zombies' Sarkis Accord or Realm's machine Mapping One (recorded in each saga's agent_decisions.md).

## 5. Next actions

1. **Owner:** review, then approve merging `feat/010-progressive-wiki` into `main` and pushing to the private repo.
2. **Owner, in Claude Code inside a saga:** approve the project MCP server `lorekeeper` once when asked.
3. After each future chapter freeze, run `_system/skills/story_wiki_update.md` before `cleanup` (the PIPELINE paragraph points there).
4. Feature 011, the planning wiki (BUILD-PLAN "Planning wiki"), is next to specify. Not started.
5. Carried over: Space chronology report (cards 051/052, four impossible SRD days); deferred saga keys in `chronology_deferred.md`.

## 6. Gotchas

- Several engine and test files are CRLF (checks, dates, fm, interop, mcp, ops, serve, store, timeinfo, editor.js, some tests). `sed -i` in Git Bash turns CRLF into LF, and Python heredocs through the shell tool lose backslashes: edit with the Edit tool or script files, then check line endings against `main`.
- Playwright writes screenshots only inside the Lorekeeper folder (`.playwright-mcp/`, gitignored).
- Saga Lorekeeper projects are rooted at `Wiki/` with settings from `_system/lorekeeper.json`; the Story Wiki is `../Story Wiki` from there. Saga shared files must stay identical across the three sagas and must not mention any Wiki page title, saga name or HO id.
- Scratch: `C:\Users\Owner\lk-scratch` (clones `sagas/`, probes `probe6/`, baselines `run4-before/`, `run4-after/`, tools in `snap/`). Old run-3 clones are in `sagas-run3/`.

## 7. How to verify

- `python -m unittest discover -s tests` in this repo: 312 OK, 1 skipped.
- `lore init --template novel` in an empty folder, then `lore wiki --as-of 1` and `lore wiki "Ash" --as-of 2`; or `lore serve` and open the Wiki tab.
- In a saga: `python _system/scripts/saga.py timeline`, Wiki tab; or `python _system/vendor/lorekeeper --root Wiki --config _system/lorekeeper.json wiki --as-of 2`.
- In each saga: `python -m unittest discover -s _system/tests` (Realm 219, Space 216, Zombies 211).
- MCP: `python C:\Users\Owner\lk-scratch\snap\handshake.py "<saga folder>"`.
