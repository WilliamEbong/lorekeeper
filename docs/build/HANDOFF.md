# HANDOFF — Lorekeeper

Transferred from: the feature 010 specification session, 2026-10-19. Next: run 4, which builds feature 010 (the progressive story wiki) and applies it to the three sagas.
This document is authoritative, including over memory and older summaries. History is in SESSION-LOG.md, BUILD-NOTES.md and BUILD-PLAN.md.

## 1. Snapshot

Lorekeeper (command `lore`) is a self-sufficient, standalone story-world engine, inspired by Aeon Timeline but in no way dependent on it.
- **Storage:** a world is plain Markdown files, one per character, place or event, with flat frontmatter and Obsidian wikilinks.
- **What it does:** reads dates at whatever precision they are written, computes ages and timelines, and checks continuity (FAIL means a definite error, WARN a possible one).
- **Interfaces:** one operations table (`lorekeeper/ops.py`) drives three interfaces:
  - a CLI (`--json` everywhere);
  - a built-in MCP server for AI agents (`lore mcp`, stdio; each op's name is its MCP tool name);
  - a local browser editor (`lore serve`).
- **Interop:** imports and exports Aeon `.aeon`, CSV and Markdown.

Audiences: writers who draft with AI agents, novelists who don't use AI, and worldbuilders/GMs. First clients: the owner's three sagas (Realm, Space, Zombies), in warn mode.

## 2. Current state

- **Lorekeeper:**
  - `main` = `origin/main` = `d0b564a` (private repo). It holds feature 008 (editor UX and audit fixes) and 009 (drag handles, a real Relationships view, BC dates, centuries, Aeon nesting).
  - 247 tests pass (1 POSIX-only skip).
- **Feature 010 is specified, not built:**
  - Spec: [specs/010-progressive-wiki/spec.md](../../specs/010-progressive-wiki/spec.md).
  - Branch: `feat/010-progressive-wiki`, from `main`.
  - The spec, this handoff, the new KICKOFF-PROMPT, a BUILD-PLAN status line and a SESSION-LOG entry may still be uncommitted. If so, commit them first (`docs: specify the progressive story wiki`).
- **Sagas, checked 2026-10-19:**

  | Saga | Live HEAD | Vendored engine | Complete | In progress |
  |---|---|---|---|---|
  | Realm | `6ee4816` | `2de4351` | CH001–003 | CH004 at READY_FOR_HUMAN |
  | Space | `87db843` | `2de4351` | CH001–004 | CH005 at READY_FOR_HUMAN |
  | Zombies | `89095c4` | `2de4351` | CH001–003 | CH004 at READY_FOR_HUMAN |

  The owner may advance chapters during the run, so re-check this at the start and before landing.
- **In flight:** nothing.

## 3. Feature 010 in one paragraph

A chapter stamp (`[ch 7]`, or `[ch 2-5]` for a range) on each fact says from which chapter the reader knows it.
- **Progressive mode** shows the wiki as of chapter N: an index per type of what the reader has met, under the names the reader knows, and a card per entry with its own chapter toggle.
- **Complete mode** shows everything, ended facts with their ranges, and one card holding all of a character's identities.
- **Where facts live:**
  - Hand-written worlds keep stamped facts in their own pages.
  - Sagas keep them in a separate `Story Wiki/` folder of companion pages, so the saga's Wiki, templates, profile packets, stages, gates and commands are untouched.
- **How AI writes them:** through new `fact-add`/`fact-end` operations (CLI, MCP, editor). A new shared saga skill runs the update after `freeze N`, from approved sources only.
- **MCP:** each saga gets a project `.mcp.json` running the vendored `lore mcp`.

The spec's FRs and SCs are the definition of done.

## 4. Decision log (earlier decisions are in SESSION-LOG and BUILD-NOTES)

| # | Decision | Rationale | Status |
|---|----------|-----------|--------|
| 14 | Refine the editor's look; don't redesign it | The paper-and-ink identity works | settled |
| 16 | In local mode, link fields are edited only through Connections | Raw link syntax is error-prone for novelists | owner may revert |
| 18 | Continuity re-runs `check` after every reload (0.5 s debounce) | Keeps the badge honest | settled |
| 19 | An event dated exactly like a birth or death is not a DEAD/UNBORN finding | It is that birth or death | settled |
| 20 | `create()` keeps the index current | Imports were quadratic | settled |
| 21 | Aeon SS/FF import as unchecked roles | Lorekeeper's `same_start`/`same_end` mean "equal" | settled; checking them is Later |
| 22 | Relationships tab = actual relationships; Ages tab = the age grid | Owner request | settled |
| 23 | Bar ends are drag handles; the middle moves the whole item | Owner request | settled |
| 24 | "N00s" is a century; BC finer than a year is written `0044-03-15 BC` | How writers use it | settled |
| 25 | The sagas stay in warn mode; Space's chronology findings stay with the author | Fail mode would block the pipeline on canon decisions | settled |
| 26 | Cut-off is reading order (chapter numbers), not in-world dates | Flashbacks; the timeline already covers in-world time | owner-approved |
| 27 | Stamps go on each fact (list item or paragraph); untagged facts inherit the page's `first_appearance` | Plain text, typeable by hand, Obsidian-friendly | owner-approved |
| 28 | Someone seen before being named is listed under the reader's description (`## Names` with stamps) | Owner's choice | owner decision |
| 29 | A secret identity is its own card until the reveal (`revealed_as` role with a stamp); complete mode holds all identities on one card | Owner's choice | owner decision |
| 30 | Only important things get cards, plus pages for kinds of things (`kind` role) | Owner's choice | owner decision |
| 31 | Sagas: stamped facts live in `Story Wiki/` companion pages, never in Wiki pages | Profile packets embed whole Wiki pages (60 KB cap); the owner wants the saga system unchanged | settled |
| 32 | The chapter picker filters only the Wiki tab; progressive cards hide frontmatter fields | Dates give deaths away; per-field stamps are Later | settled |
| 33 | AI writes facts only through `fact-add`/`fact-end`; sagas register `lore mcp` in `.mcp.json`; scripted steps use the CLI with `--json` | Validated writes; easy AI use | settled |
| 34 | The saga update runs after `freeze N` (a new skill plus one pointer), outside the stage machine | No existing stage, gate or instruction changes | settled |

## 5. Open questions (owner's call; none blocks run 4)

- Should the sagas switch from warn to fail mode? (Carried over; decision 25 says no for now.)

## 6. Next actions

1. **Run 4: build feature 010 with build-continuously.** Use the prompt in [KICKOFF-PROMPT.md](KICKOFF-PROMPT.md). **← NEXT**
2. **After run 4: specify feature 011, the planning wiki.** The owner's request and decisions are in BUILD-PLAN.md under "Planning wiki". The World Bible stays the master, and conflicts with written chapters are flagged, never applied. It is not part of run 4.
3. Space chronology report: cards 051/052 (RAIL_REGRESSION) and four impossible SRD days (the author's call, carried over).
4. Apply the deferred saga keys in each saga's `chronology_deferred.md` as chapters freeze (carried over).

## 7. Constraints & preferences

- The owner directs in plain language and does not read code, JSON or git. Persisted docs and commits use normal prose.
- Ponytail (the simplest correct design) and stdlib only. Spec Kit for features. Playwright for any UI check.
- Every `open()` passes `encoding="utf-8"`. Tests use `unittest`.
- Line endings: most `.py` files and `editor.js` are CRLF; `editor.css`, `editor.html` and the docs are LF. Preserve them, and check with `git diff --stat` before committing.
- Lorekeeper git: work on `feat/010-progressive-wiki`, with local commits only. Never push, and never merge into `main`; both wait for the owner. The private repo is the only remote. Nothing public.
- **Sagas:**
  - All work happens in clones under `C:\Users\Owner\lk-scratch\sagas`, with fresh full copies as probes (as in run 3b: `lk-scratch/probe5`).
  - Land by fast-forward only with `lk-scratch\snap\land.sh`. If a live repo moved, re-clone and redo; never force.
  - Never stage in-progress chapters, `_system/state`, provenance or `saga.log`.
  - Commit prefixes: engine and config `system:`, Story Wiki content `wiki:`.
  - Run `status` and `validate` only on copies.
  - The owner authorized applying feature 010 to the three sagas (2026-10-19), on the condition that their systems keep working exactly as before.

## 8. Gotchas for run 4

- **Profile packets** (`_system/scripts/profiles.py`):
  - `assemble` puts each participant's whole Wiki page text into `RT/context/profiles.md`, and fails above 60 KB.
  - Roster Wiki pages and `PROJECT_MANIFEST.json` are fingerprinted, so editing them stales an in-progress chapter's packet.
  - `_system/lorekeeper.json` is not fingerprinted; put the `story_wiki` key there.
- **Saga parity:**
  - `_system/tests/test_engine_parity.py` has a `SHARED_FILES` list and `SHARED_GLOBS` (`_system/roles/*.md`, `_system/skills/*.md`, `Wiki/_TEMPLATES/*.md`). A new skill must be identical in all three sagas.
  - `test_docs.py` requires `_system/skills/README.md` to list every skill, and forbids saga-specific terms (`HO-\d+`, saga names, word-cap literals) in shared files.
- **Saga Wiki layouts differ:** Realm uses subfolders (Characters, Events, Locations, Organizations, Chapters). Space and Zombies are flat. Space already has kind pages ("Human Assault battlesuit", "Imperial Warform").
- **Saga page facts:** character pages carry `first_appearance`, `last_updated_after_chapter`, an `## Important events` list with `**CHnnn**` markers, and `## Appearances`. Use these with each chapter's `Chapters/CHnnn/CURRENT_WORLD_BIBLE_OUT.md` ("Current World Bible — after CHnnn") for the backfill.
- **`freeze`** refuses staged paths outside its scope, so the Story Wiki gets its own commit after the freeze.
- **Lorekeeper code:**
  - `store.RESERVED` already includes `aliases`, and alias resolution is in `store.py` around line 294.
  - Link values already take a suffix (`LINK` regex: `"[[X]] +2h"`).
  - `op.name` is both the CLI subcommand and the MCP tool name, hence `fact-add`.
- **Editor:** nothing renders page bodies today. The Wiki tab is the first body renderer. Render a small Markdown subset (headings, lists, paragraphs, bold and italic, wikilinks) as DOM text nodes, never `innerHTML`, to keep the CSP and stay safe from XSS.
- **Realm's editor title** reads "Wiki" because the saga config has no `name` (cosmetic, Later).

## 9. Artifact manifest

| Artifact | Purpose | Status | Location |
|----------|---------|--------|----------|
| Lorekeeper source + tests | The app | final for 008/009 | repo, `main` |
| specs/010-progressive-wiki/spec.md | The feature 010 spec (plan and tasks come in run 4) | ready | repo, `feat/010-progressive-wiki` |
| docs/build/KICKOFF-PROMPT.md | Run 4 kickoff and resume prompts | ready | repo |
| README.md, docs/user-guide.md, docs/agent-skill.md | Guides; run 4 extends them (FR-26) | current for 009 | repo |
| docs/build/BUILD-PLAN.md, SESSION-LOG.md, BUILD-NOTES.md | Plan and full history; run 4 adds its own section | current | repo |
| Saga clones and probes | Saga work area | recreate fresh for run 4 | `C:\Users\Owner\lk-scratch` |

## 10. Glossary

- **Card (saga architecture):** an architecture chapter card (in-memory item of type `card`, path `<architecture>#CHnnn`). Not the same as a wiki card.
- **Wiki card:** the progressive or complete view of one entry in the Wiki tab.
- **Stamp:** `[ch N]` or `[ch N-M]` at the end of a fact.
- **Story page:** where an item's stamped facts live. That is the item's own page, or a companion page in the world's `story_wiki` folder (`Story Wiki/` in the sagas).
- **Progressive / complete:** the wiki as of chapter N, or with no cut-off.
- **Rail:** a Space story strand. **SRD:** Space's 365-day production calendar.
- **Warn mode:** chronology findings are printed but never block a stage.
- **FAIL / WARN:** a definite or possible continuity error.

## 11. How to verify (today)

- `python -m unittest discover -s tests` from the repo root: 247 tests, OK (1 skipped).
- `lore serve --root <a world>` and open the printed address.
- `"C:/Users/Owner/.claude/skills/impeccable/scripts/impeccable" detect --json lorekeeper/editor.html` should print `[]`.
- In each saga: `python -m unittest discover -s _system/tests`.
