# HANDOFF — Lorekeeper (run 4 in progress)

Written mid-run, 2026-10-19, while three backfill agents work. Authoritative over memory. History: SESSION-LOG.md (the "Run 4" entries), BUILD-PLAN.md ("Run 4" section and its checklist), specs/010-progressive-wiki (spec with Clarifications, plan.md, tasks.md).

## 1. Where things stand
- **Lorekeeper** (branch `feat/010-progressive-wiki`, local commits only, never pushed or merged): feature 010 is built and green.
  - Commits: 21c5931 (clarify/plan/tasks), 25cd2aa (engine, ops, CLI, MCP), 66b3d95 (Wiki tab), 8ea9023 (templates and docs), 0f6aaaa ("Revealed to be" section). Suite: 297 OK, 1 POSIX-only skip.
  - Playwright evidence on lk-scratch/ui-wiki is in SESSION-LOG; screenshots in `.playwright-mcp/` (gitignored).
- **Sagas** (work only under `C:\Users\Owner\lk-scratch`):
  - Fresh clones: `lk-scratch/sagas/<saga>`; each has one new commit "system: Story Wiki layer (vendored Lorekeeper 0f6aaaa, ...)" (Realm 9d5a021, Space 26e123e, Zombies cef47a6). Clone suites: 219 / 216 / 211 OK with parity.
  - Probes (full copies of the live repos): `lk-scratch/probe6`. Before-baseline: `lk-scratch/run4-before` (suites OK, health, status and validate per chapter, `trees.txt` with git tree ids of Wiki, roles, skills, templates, workflow). In-progress packets verify (`snap/verify_packets.py`).
  - SC-7 handshake passes on all three clones (`snap/handshake.py <clone>` and `... dot`).
  - **In flight:** three backfill agents writing `Story Wiki/` in the clones, following `snap/story_backfill_brief.md`. A Lorekeeper reviewer agent is reviewing `main...feat/010-progressive-wiki`.
- Live saga HEADs at the start: Realm 6ee4816, Space 87db843, Zombies 89095c4. Re-check before landing.

## 2. Exact next steps
1. When each backfill agent reports: inspect its Story Wiki (check, index per chapter, spot-check), then commit in the clone: `git add -- "Story Wiki" _system/knowledge/agent_decisions.md` as two commits (`wiki: Story Wiki backfill through CH00k`; decisions `knowledge: Story Wiki backfill decisions`). Never stage anything else.
2. Fix confirmed reviewer findings in Lorekeeper (TDD), commit, re-vendor (`snap/vendor4.sh`), commit `system:` in the clones, rerun clone suites.
3. Replay on probes: `git -C probe6/<saga> fetch <clone> main && git -C probe6/<saga> merge --ff-only FETCH_HEAD`; run `snap/baseline.sh /c/Users/Owner/lk-scratch/probe6 /c/Users/Owner/lk-scratch/run4-after`; require identical status/validate files and health; Wiki/roles/templates tree ids unchanged (skills tree changes only by the new skill and README row); `verify_packets.py` OK.
4. After-freeze proof on a probe copy: `snap/reset_chapter.py <saga> <last frozen>` then a fresh agent runs `_system/skills/story_wiki_update.md` for that chapter; compare with the backfill.
5. Saga reviewer (fresh context): three characters per saga against each chapter's CURRENT_WORLD_BIBLE_OUT.md.
6. Playwright on `saga.py timeline` in a clone: Wiki tab, Propose a fact queues a request, screenshots.
7. Land with `lk-scratch/snap/land.sh "<saga>" <expected live HEAD>` (fast-forward only). If a live repo moved, re-clone and redo.
8. Finish: full checks, docs, final HANDOFF, memory, delete cron `6ae28ced`, PushNotification, SendUserFile screenshots, report.

## 3. Gotchas
- Python heredocs through the shell tool lose backslashes; use the Edit tool or script files. Several engine files are CRLF (checks, dates, fm, interop, mcp, ops, serve, store, timeinfo, editor.js, tests/test_mcp, tests/test_cli); check with `file` and `git diff --stat`.
- Playwright may only write screenshots inside the Lorekeeper folder (`.playwright-mcp/`).
- `saga.py cleanup` deletes approved deltas, so the after-freeze routine runs between freeze and cleanup.
- Saga Lorekeeper project root is `Wiki/`; settings come from `_system/lorekeeper.json` (`--config`); the Story Wiki is `../Story Wiki` from there.
- Saga shared files (skills, roles, templates, PIPELINE, vendored engine) must be identical in all three sagas and must not mention any Wiki page title, saga name or HO id.

## 4. Decisions to surface to the owner
In SESSION-LOG with undo notes: `--config` and `mcp --saga`; `fact-remove` and `fact-end --reopen` for Undo; companion naming `<Name> (story).md`; narrative items never wiki entries; names resolve links late; `kind`/`revealed_as` accept any type; reveal also as a "Revealed to be" section; the after-freeze routine sits between freeze and cleanup.
