# HANDOFF — Lorekeeper

Written 2026-10-19, after run 4. Next: **run 5, which builds feature 011 (the planning wiki) and applies it to the three sagas.** This document is authoritative, including over memory and older summaries. History is in SESSION-LOG.md, BUILD-NOTES.md and BUILD-PLAN.md.

## 1. Snapshot

Lorekeeper (command `lore`) is a standalone, stdlib-only story-world engine.
- **Storage:** plain Markdown files, one per item, with flat frontmatter and Obsidian wikilinks.
- **What it does:** dates at any precision, ages, timelines and continuity checks (FAIL means definite, WARN means possible).
- **Interfaces:** one operations table (`lorekeeper/ops.py`) drives a CLI (`--json` everywhere), an MCP server (`lore mcp`) and a local browser editor (`lore serve`).
- **Interop:** imports and exports Aeon `.aeon`, CSV and Markdown.

**Feature 010, the progressive story wiki, is done** (run 4).
- Chapter stamps on facts: `[ch 7]`, or `[ch 2-5]` for a range.
- A Wiki tab with a chapter picker and cards, each card with its own chapter control.
- Progressive mode (what a reader knows after chapter N) and complete mode (everything to date).
- Operations `wiki`, `fact-add`, `fact-end` and `fact-remove`.
- In the sagas, a `Story Wiki/` layer written after each freeze.

## 2. Current state

- **Lorekeeper:**
  - Feature 010 is merged into `main` and pushed to the private repository (`origin/main` = 781f461), with the owner's approval on 2026-10-19.
  - Local `main` may hold one docs commit with this handoff and the run 5 kickoff prompt; the repo shows it.
  - Suite: 312 OK (1 POSIX-only skip). Impeccable detector on `editor.html`: `[]`.
- **Sagas** (landed 2026-10-19; re-check at the start and before landing):

  | Saga | Live HEAD | Vendored engine | Story Wiki | In progress |
  |---|---|---|---|---|
  | Realm | `bbf9b36` | `88d131c` | CH001–003 | CH004 at READY_FOR_HUMAN |
  | Space | `1390389` | `88d131c` | CH001–004 | CH005 at READY_FOR_HUMAN |
  | Zombies | `5821c8f` | `88d131c` | CH001–003 | CH004 at READY_FOR_HUMAN |

  Each saga has the `story_wiki` key in `_system/lorekeeper.json`, the shared skill `_system/skills/story_wiki_update.md` (run between `freeze N` and `cleanup N`), one pointer in PIPELINE §6, and `.mcp.json` running `lore mcp --saga`.
- **In flight:** nothing.

## 3. Feature 011, the planning wiki (to build in run 5)

The full request and the owner's decisions are in BUILD-PLAN.md, "Feature requests from the owner" → "Planning wiki". No spec exists yet: run 5 writes it first. In short:

- **What it is:** the author's intended end state. Everything designed, including what no reader knows yet, as browsable, well-linked pages. It is a back-end reference for the author and the AI.
- **Where it sits:**
  - The flow is planning wiki → chapter cards → drafting → the full and progressive wikis.
  - The Wiki tab's picker becomes **Planning | Complete | Chapter N**.
  - It reuses 010's Wiki tab, cards and fact operations.
- **Locked owner decisions (2026-10-19):**
  1. The World Bible stays the master (the saga's `AUTHORITY.md` ranks it first). The planning wiki is a derived, per-entity view of it, and each fact cites its source section.
  2. An author's edit in the planning wiki is recorded as a HUMAN OVERRIDE in the override register (`_system/knowledge/overrides.md`) and written back into the World Bible by the AI.
  3. An impact review then covers the matching planning pages, bible sections, unwritten chapter cards and the in-progress chapter.
  4. A change that contradicts a frozen (written) chapter is flagged to the author, never applied to approved prose.
  5. Sources are every planning document, not just the World Bible:
     - the military bible and the Conversations (dialogue) documents;
     - the character, species, faction and combatant card libraries;
     - tech ledgers, author rulings and overrides;
     - the mystery and setup/payoff ledgers.

     `AUTHORITY.md` decides conflicts.
  6. Pages are well linked. A kind page lists its notable members ("Notable vampires"), a character lists the saved dialogues that feature them, and things have an "Appears in" list of chapters from the chapter cards.
  7. Link lists are computed mechanically by Lorekeeper and never written by the AI. They come from tags, Conversations headings and speaker lines, and a whole-word search of names and aliases over the parsed chapter cards. Names that are ordinary words need an exclusion list.
  8. Undecided material (plot ideas, opportunities portfolios, unapproved-decisions reports) is shown, clearly labelled as ideas and kept apart from decided facts. It is never used as canon: not for cards, impact reviews or link lists.
  9. The saga systems keep working exactly as they do now. The planning wiki is added on top.
- **Token budget:** the documents are large. For example, Realm has a 387 KB World Bible, a 712 KB architecture and 898 KB of plot ideas.
  - Read each source once, split by section.
  - Impact reviews use mechanical search, so the AI reads only the matching passages.
  - Use one subagent per saga.

## 4. Gotchas for run 5

- **Editing an authority stales in-progress chapters.**
  - `_system/state/provenance/CH###.json` records the sha256 of the World Bible, architecture, style bible and Conversations for every unfrozen chapter.
  - Writing back into the World Bible therefore changes `validate` for Realm CH004, Space CH005 and Zombies CH004. The saga's own fix is `saga.py refresh-sources N`, followed by revalidating the prose.
  - So, during the build, **never edit a live authority document.** Build and prove the edit → override → write-back → impact-review flow on probes only.
  - In normal use the write-back is an owner-initiated canon change. It must follow the saga's existing route: the `impact_analyze_human_change` skill, the override register, and `refresh-sources` for unfrozen chapters.
- **Never alter the existing pipeline.** Profile packets fingerprint `PROJECT_MANIFEST.json` and roster Wiki pages; `_system/lorekeeper.json` is not fingerprinted.
- **Keep the saga invariants of run 4.** Every saga suite must pass, parity included. Status, validate and health output must be byte-identical before and after (outside the write-back proof, which runs on a probe). `Wiki/`, roles, templates and existing skills stay untouched; `Story Wiki/` stays untouched.
- **Shared saga files** must be identical in all three sagas. Shared means skills, roles, templates, PIPELINE, CRAFT_RULES and the vendored engine. They must not name any Wiki page title, saga name or HO id (`test_docs.py`); list a new skill in the skills README.
- **Planning facts are spoilers.** They must never appear in progressive or complete mode, and never in a profile packet or drafting context.
- **Saga Lorekeeper root.** It is `Wiki/` with `--config _system/lorekeeper.json`. Planning pages need their own folder key, like `story_wiki`.
- **Line endings.**
  - Several engine and test files are CRLF: checks, dates, fm, interop, mcp, ops, serve, store, timeinfo, `editor.js` and some tests.
  - `sed -i` in Git Bash turns CRLF into LF, and Python heredocs sent through the shell tool lose their backslashes.
  - Edit with the Edit tool or with script files, then compare line endings against `main`.
- **Playwright** writes screenshots only inside the Lorekeeper folder (`.playwright-mcp/`, gitignored).
- **Scratch:** `C:\Users\Owner\lk-scratch`.
  - Tools from run 4 are in `snap/`: `baseline.sh`, `vendor4.sh`, `commit_system4.sh`, `land.sh`, `handshake.py`, `verify_packets.py` and `story_backfill_brief.md`.
  - Make fresh clones and probes for run 5. Run 4's are in `sagas/` and `probe6/`.

## 5. Open questions (owner's call; none blocks run 5)

- Should the sagas switch from warn to fail mode? Carried over; for now they stay in warn mode.
- Space chronology: cards 051/052 (RAIL_REGRESSION) and four impossible SRD days. The author's call, carried over.

## 6. Next actions

1. **Run 5: build feature 011 with build-continuously**, using the prompt in [KICKOFF-PROMPT.md](KICKOFF-PROMPT.md). **← NEXT**
2. After each future chapter freeze: run `_system/skills/story_wiki_update.md` before `cleanup` (already wired into PIPELINE §6).
3. Owner: in Claude Code inside a saga, approve the `lorekeeper` MCP server once when asked.

## 7. Constraints and preferences

- The owner directs in plain language and does not read code, JSON or git. Persisted docs and commits use normal prose.
- Ponytail (the simplest correct design) and stdlib only. Spec Kit for features. Playwright for any UI check. Every `open()` passes `encoding="utf-8"`. Tests use `unittest`.
- **Lorekeeper git:** work on a feature branch with local commits only. Never push, and never merge into `main`, without the owner's approval. The private repo is the only remote.
- **Sagas:**
  - Work in clones and probes under `lk-scratch`.
  - Land by fast-forward only with `land.sh`. If a live repo moved, re-clone and redo; never force.
  - Never stage in-progress chapters, `_system/state`, provenance or `saga.log`.
  - Commit prefixes: `system:` for engine and config, `wiki:` for wiki content, `knowledge:` for decision rows.

## 8. How to verify (today)

- `python -m unittest discover -s tests` from the repo root: 312 OK (1 skipped).
- In a saga, `python _system/scripts/saga.py timeline`, then the Wiki tab. From the command line: `python _system/vendor/lorekeeper --root Wiki --config _system/lorekeeper.json wiki --as-of 2`.
- In each saga, `python -m unittest discover -s _system/tests`: Realm 219, Space 216, Zombies 211.
- MCP: `python C:\Users\Owner\lk-scratch\snap\handshake.py "<saga folder>"`.
