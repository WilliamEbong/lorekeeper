# HANDOFF — Lorekeeper

Written 2026-10-19, at the end of run 5. **Feature 011, the planning wiki, is built, reviewed and landed in the three sagas.** The Lorekeeper branch `feat/011-planning-wiki` is local only and waits for the owner's approval to merge and push. This document is authoritative, including over memory and older summaries. History is in SESSION-LOG.md and BUILD-PLAN.md ("Run 5").

## 1. Snapshot

Lorekeeper (command `lore`) is a standalone, stdlib-only story-world engine.
- **Storage:** plain Markdown files, one per item, with flat frontmatter and Obsidian wikilinks.
- **Interfaces:** one operations table (`lorekeeper/ops.py`) drives a CLI (`--json` everywhere), an MCP server (`lore mcp`) and a local browser editor (`lore serve`).
- **Three wikis:**
  - the story wiki (feature 010): what a reader knows after chapter N, plus a Complete mode;
  - the planning wiki (feature 011): the author's intended end state.

**The planning wiki (011).**
- **Pages:** one per entity in a planning folder. Every decided fact cites its source section, e.g. `[src: World Bible §82.2]`.
- **Link lists:** computed by Lorekeeper: notable members, dialogues, the chapters an entity appears in, and idea sections.
- **Ideas:** kept apart under `## Ideas`, never canon.
- **Recording a change:** `planning-change` records an author's change as a HUMAN OVERRIDE, writes a dated "Amended by HO-NNN" line into the cited source section, updates the page and returns an impact review. In the review, frozen chapters are only flagged; current and planned material is listed.
- **Ops:** `planning`, `planning-source`, `planning-fact`, `planning-impact`, `planning-change`. Spec and plan are in `specs/011-planning-wiki/`.
- **Editor:** the Wiki tab's picker is now Planning | Complete | Chapter N.

## 2. Current state

- **Lorekeeper:**
  - **Branch:** `feat/011-planning-wiki` (local commits only; not pushed, not merged).
    - It contains main up to 65c93d8 (the other session's merged work).
    - HEAD is the docs commit after 12ef7b3. 12ef7b3 is the engine vendored into the sagas.
  - **Checks:** suite 358 OK (1 POSIX-only skip). Impeccable detector: editor.html clean; editor.css has one finding (tab underline) that main has too.
  - **Earlier fix branch:** `fix/mcp-cache-hints` (68b63e5, the 2026-07-28 MCP fix) was merged into main by the other session and pushed.
  - **Timeline branch:** `feat/timeline-scale` (a1fbd5d, worktree `lk-scratch/lk-timeline-scale`) holds the owner's mid-run timeline request: year scale, gridline toggle, side scroll. It was built by a separate session, is not merged, and its session reports it merges cleanly.
- **Sagas** (landed by fast-forward on 2026-10-19):

  | Saga | Live HEAD | Engine | Planning Wiki | In progress |
  |---|---|---|---|---|
  | Realm | `de4cee0` | `12ef7b3` | 150 pages, 952 facts | CH004 READY_FOR_HUMAN |
  | Space | `21364f4` | `12ef7b3` | 229 pages, 3,185 facts | CH005 READY_FOR_HUMAN |
  | Zombies | `b628d43` | `12ef7b3` | 209 pages, 1,093 facts | CH004 READY_FOR_HUMAN |

  Each saga has:
  - a `planning_wiki` key in `_system/lorekeeper.json`: folder `../Planning Wiki`, sources in AUTHORITY.md order, `exclude_names`;
  - a `Planning Wiki/` folder;
  - the shared skill `_system/skills/planning_wiki_change.md`, with its skills README row and one PIPELINE sentence (after "A creative change with no chapter named…");
  - decision rows of kind `planning-wiki` in `agent_decisions.md`.

  `lore planning` reports 0 problems in all three.
- **Another session** (the run-4 "Progressive story wiki" session) worked on Lorekeeper and the sagas in parallel this run: life lines, second lives, flashbacks and Realm ages. Its work is on main and in the sagas. Run 5 merged main twice and rebased onto both of its landings.
- **In flight:** nothing.

## 3. What the owner may want to decide

- **Merge and push** `feat/011-planning-wiki` into main (private repo). It merges cleanly with main as of 65c93d8. Then decide on `feat/timeline-scale`.
- **Review findings in the saga planning documents** (no change made):
  - Space WB §CI-4 names Mara Chen and Tiriq Sen near the Sable Five. It is a naming-collision list; the members follow §X.14.2 and ruling N-12.
  - Space HO-029 revised the demonologist staffing without stating it.
  - Space name register: Mira Quill is called human (the World Bible says digital person), and the Assault pilot is called "Mara Chen" (the mystery ledger keeps the pilot anonymous).
  - Realm: the Architecture's Ch 230 card names the Great Ship "the Long Detour", while the register keeps its name pending.
- **Planning wiki choices to confirm:**
  - Realm and Zombies record mystery answers as decided facts (it is the author's view).
  - Zombies uses the Arc summary, which is non-binding, for some spoilers no binding source states (João's death in Ch 5, Nneka, the Caliph's sequences).
  - Realm's planning wiki inherits R6c's unapproved choices that are still in the World Bible.
- **Optional:** the other session recorded decided born/died/reborn keys for 28 Realm characters without pages (`chronology_deferred.md`). They could become planning facts.
- Carried over: should the sagas switch from warn to fail mode? Space chronology cards 051/052.

## 4. Gotchas

- **Planning changes stale the chapter in progress.** The provenance and the profile packet fingerprint every authority and the override register. After a planning change in a saga, run:
  1. `saga.py refresh-sources N`
  2. `saga.py assemble-profiles N`
  3. `saga.py validate N` (proven on a Realm copy; see `lk-scratch/r5-proof-summary.md`)
- **Never edit live authorities during a build.** Prove flows on copies.
- **Source references:**
  - A section ref is a heading number (`23.4`, `A.252`, `HO-031`, `VIII.2`) or a title.
  - Duplicate numbers (Space repeats 17) need the number plus the start of the title: `§X.7 Fleet doctrine`.
  - Code fences are ignored on purpose: the sagas use bare ``` lines as separators.
- **Override registers differ.**
  - Space mixes `## HO-104 — title` headings with `**ID:**` lines.
  - Zombies ends with an EXAMPLE entry.
  - Realm has real entries after its example block.
  - An ID line counts as an example only if its own line says so.
- **Playwright's MCP browser profile is shared machine-wide.** If another session holds it, use playwright-core directly with an isolated Chromium (`lk-scratch/snap/saga_ui5.js` shows how). Never kill another session's browser.
- **Line endings:** several engine files are CRLF. The Edit tool keeps them; `sed -i` and Python text-mode writes on Windows do not. Check with `file`.
- **Scratch:** `lk-scratch` holds:
  - `r5-clones`, `r5-probe`, `r5-before` and `r5-after`, and `r5-proof` (the change-flow proof);
  - the scripts in `snap/`: `add_planning_key.py`, `r5_vendor.sh`, `commit_system5.sh`, `replay5.sh`, `land5.sh`, `handshake5.py`, `exclude5.py`, `saga_ui5.js`, `planning_build_brief.md`, `planning_wiki_change.md`.

  The other session uses `fix-sagas`, `probe7`, `probe8`, `run7-*`, `run8-*`, `lk-lifespan` and `lk-lives`.

## 5. Next actions

1. Owner: approve merging `feat/011-planning-wiki` (and, separately, `feat/timeline-scale`) into main and pushing to the private repo. **← NEXT**
2. In a saga, try the planning wiki: run `python _system/scripts/saga.py timeline`, open the Wiki tab and pick Planning.
3. For a planning change, tell the AI in plain words. It follows `_system/skills/planning_wiki_change.md`.
4. After each chapter freeze, keep running `story_wiki_update` (unchanged).

## 6. Constraints and preferences

- The owner directs in plain language and does not read code, JSON or git. Persisted docs and commits use normal prose.
- Ponytail and stdlib only. Spec Kit for features. Playwright for any UI check. Every `open()` passes `encoding="utf-8"`. Tests use `unittest`.
- **Lorekeeper git:** feature branches with local commits only; never push or merge into main without the owner's approval. The private repo is the only remote.
- **Sagas:**
  - Work in clones and probes, and land by fast-forward only.
  - Never stage in-progress chapters, `_system/state`, provenance or `saga.log`.
  - Commit prefixes: `system:` for engine and config, `wiki:` for wiki content, `knowledge:` for decision rows, `canon:` for authority write-backs.

## 7. How to verify

- From the repo root, `python -m unittest discover -s tests`: 358 OK (1 skipped).
- In a saga root:
  - `python _system/vendor/lorekeeper --root Wiki --config _system/lorekeeper.json planning` shows the index and must report 0 problems;
  - add `planning "<Name>"` for a card;
  - add `planning-source "World Bible" --section 82.2` to read a cited section.
- In each saga, `python -m unittest discover -s _system/tests` passes with parity.
- MCP: `python C:\Users\Owner\lk-scratch\snap\handshake5.py "<saga folder>"`.
