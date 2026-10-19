# Feature 011: Planning wiki

## Overview
The owner asked on 2026-10-19 for a third wiki, the **planning wiki**: the intended end state of the story, everything the author has designed, including what no reader knows yet, as browsable, well-linked pages. It is a back-end reference for the author and the AI. Information flows one way: planning wiki → chapter cards → drafting → the complete and progressive wikis (feature 010).

Locked owner decisions (2026-10-19), which this spec does not change:
1. The planning documents stay the master; in the sagas the World Bible stays first. The planning wiki is a **derived, per-entity view** of every planning document (bibles, Conversations, card libraries, tech ledgers, rulings, overrides, mystery and setup/payoff ledgers). Every planning fact cites its source document and section. The world's authority ranking decides conflicts.
2. A change to a planning fact, made by the author or by the AI on the author's word, is recorded as a **HUMAN OVERRIDE** in the override register and **written back** into the master document. An **impact review** then covers the matching planning pages, source sections, unwritten chapter cards and the in-progress chapter. Anything that contradicts a written (frozen) chapter is **flagged** to the author, never applied to approved prose.
3. Pages are well linked. Kind pages list notable members, characters list the saved dialogues that feature them, things list the chapters they appear in. **Lorekeeper computes these lists mechanically** (tags and links, Conversations headings and speakers, a whole-word name and alias search over the chapter cards, with an exclusion list for names that are ordinary words). The AI never writes them.
4. **Undecided material** (plot ideas, opportunities, unapproved-decision reports) is shown, labelled as ideas and kept apart from decided facts. It is never canon: not for cards, impact reviews or link lists.
5. The Wiki tab's picker becomes **Planning | Complete | Chapter N**. Planning facts never appear in Complete or Chapter N, and never in a profile packet or drafting context.
6. The saga systems keep working exactly as they do now. The planning wiki is added on top.

Constraints are unchanged: standard-library Python, vanilla JavaScript editor with its strict Content-Security-Policy, one operations table that drives the CLI (`--json`), the MCP server and the editor API; flat frontmatter; every `open()` with `encoding="utf-8"`; line endings preserved.

## Clarifications

### Session 2026-10-19
Answered by the build agent with the recommended option (run 5, owner away; each is logged in SESSION-LOG with how to undo it).
- Q: How does a world declare its planning layer? → A: One settings key, `planning_wiki`, an object: `folder` (where planning pages live, relative to the project root, may sit beside it), `sources` (an ordered list; order is the authority ranking, first wins), and `exclude_names`. Each source has a `name` (used in citations), a `file`, and at most one role flag: `dialogues`, `chapters` (with optional `skip` line prefixes), `ideas`, `overrides`, or `prose` (a pattern such as `../Chapters/CH{n:03d}/CHAPTER.md`). A world without the key has no planning layer and nothing changes.
- Q: How is "kept apart" enforced for ideas? → A: Ideas live only in a page's `## Ideas` section, and Lorekeeper also lists, mechanically, the idea-source sections whose heading names the entry. Both come back in the card under `ideas`, never under `sections`. A decided fact that cites only idea sources is reported as PLAN_IDEA_AS_FACT. Impact reviews and link lists never read idea sources or `## Ideas` sections.
- Q: Who writes the master document during a planning change, Lorekeeper or the AI? → A: Both, in order. `planning-change` appends the override and a dated amendment line at the end of the cited section of the highest-ranked source the fact cites, then updates the planning fact and returns the impact review. The AI then reconciles the surrounding prose that the review lists, following the world's own human-change route (in the sagas, `impact_analyze_human_change`). `lore mcp --saga` never offers `planning-change`, so no MCP tool writes an authority; in a saga the change runs through the CLI under the saga skill.
- Q: How are written chapters told apart from planned ones in an impact review? → A: A `written` number (the last written or frozen chapter) given by the caller; without it, the last chapter used by the Story Wiki's stamps, else 0. Chapters up to `written` are frozen (flag only), `written + 1` is current, later ones are planned.
- Q: Do planning problems join `check`? → A: No. `check` feeds the sagas' status, validate and health output, which must stay byte-identical, and reading every source on each check would slow every saga command. The planning index returns its own `problems`.

## Terms
- **Planning page:** a Markdown file in the planning folder, at `<folder>/<type plural>/<name> (plan).md`, with flat frontmatter (`type`, `canonical_name`, optional `page` link to a Wiki item, `aliases`, `tags`, `member_tags`, `kind`, `member_of`) and a body of sections of facts.
- **Planning entry:** a planning page, merged with the item its `page` link (or name) resolves to, so the item's names, aliases and tags count too.
- **Citation:** a trailing `[src: World Bible §23.4]` on a fact; several refs are separated by `;`. A ref is a source name (matched case-insensitively, longest name first) and a section.
- **Section reference:** in a source document, a heading's leading number (`23`, `0.8.4`, `A.252`, `B.2A`; a leading `§` is ignored), or else its title text (case and punctuation ignored; exact title first, then a title that starts with it). In an overrides register, an entry id (`HO-031`). A section runs from its heading to the next heading of the same or a higher level.
- **Decided fact:** a fact in any section except `## Ideas`.

## User scenarios
- **The author browses the plan.** In the Wiki tab they pick Planning. The index lists every planning entry by type. Sava's card shows her decided facts, each with a citation chip ("World Bible §31.2"); a chip opens that section's text. Below are her dialogues (Conversations §A.252, §A.278), the chapters she appears in (from the chapter cards), and an Ideas block, visibly labelled, listing plot-idea sections about her. The Vampires page lists "Notable members" with Sava in it.
- **The author changes a fact.** On the fighter jet's card they choose Change on "Top speed Mach 20", type "Top speed Mach 30" and their reason. In a saga this queues a change request, like every editor edit in a saga. The AI then runs the saga's planning-change routine: HUMAN OVERRIDE recorded, World Bible amended, planning page updated, impact review produced, unfrozen material updated, the in-progress chapter refreshed, frozen chapters flagged. In a world without a pipeline the change is recorded at once and the impact review appears on screen.
- **An AI agent plans a chapter.** It reads `planning` cards for the chapter's cast through MCP, and their citations point it to the exact source sections (`planning-source`), so it never pastes a whole bible.
- **A novelist without a saga** keeps planning pages by hand (no sources needed), sees the same link lists computed from their chapter pages, and edits facts in place.

## Functional requirements

### Settings and pages
- **FR-1 Settings.** `planning_wiki` as in the Clarifications. Errors name the key to fix: an unknown flag, two `overrides` sources, a missing `file` (reported when the source is read: "source 'World Bible' file not found: …; update planning_wiki.sources in the settings file").
- **FR-2 Planning pages are a separate layer.** They are never items: not in `query`, `show`, `graph`, `timeline`, `export`, `check`, the story `wiki` (either mode) or the timeline views, and their names never resolve item links. The project scan skips the planning folder when it lies inside the project.
- **FR-3 Facts and citations.** Facts are list items or paragraphs, as in feature 010. A trailing `[src: …]` is the fact's citation. A planning page with `## Ideas` keeps its ideas there.

### Reading
- **FR-4 `planning` (index).** `lore planning` returns groups by type (plural label), each entry with name, type, key (`plan:` + hash), page (the Wiki item's name, when attached) and fact count; plus `problems`, WARN findings:
  - PLAN_UNCITED: a decided fact with no citation, in a world that has sources;
  - PLAN_SOURCE_UNKNOWN: a ref whose source name is not configured;
  - PLAN_SECTION_MISSING: a ref whose section is not in the source;
  - PLAN_IDEA_AS_FACT: a decided fact citing only idea sources;
  - PLAN_PAGE_UNREADABLE: a planning file without UTF-8 text and a `type:`;
  - PLAN_SOURCE_MISSING: a configured source file that does not exist.
  Each finding names the page and line and says how to fix it.
- **FR-5 `planning NAME` (card).** Returns name, type, key, version, aliases, fields, `sections` (decided facts only: text, sources, id) and `ideas` (the `## Ideas` facts plus the computed idea sections, each marked `idea: true`), and `links`:
  - `members`: entries whose `kind` or `member_of` links to this entry, or whose tags include one of this entry's `member_tags`;
  - `dialogues`: entries of `dialogues` sources (the deepest numbered headings, or the deepest headings when none is numbered) whose own heading or an enclosing heading names the entry (in any capitals), or that have a speaker label (`**Name:**` or `**Name (note):**` at a line start) or a position marker (`*Name* —`) naming it;
  - `appears_in`: chapters (number and title) of `chapters` sources, whose card text names the entry; card text is the heading to the next heading, minus lines that start with a `skip` prefix; plus narrative items of the project (chapter pages) whose text names it;
  - each source in a citation is returned as `{source, section, title, rank, found}`.
  "Names the entry": a whole-word, case-sensitive match of its name, aliases or the attached item's name and aliases; names in `exclude_names` (any case) never match; a name shorter than three letters never matches.
- **FR-6 `planning-source`.** `lore planning-source SOURCE` returns the outline (each section's ref, title, level, line and size). With `--section S` it returns that section's text and line range. Ambiguous or missing sections fail with the candidates. This is how an AI reads a large document one section at a time.

### Changing
- **FR-7 `planning-fact`.** Adds, replaces (`--fact ID`) or removes (`--fact ID --remove`) one fact on a planning page, with `--source` refs written as the citation; `--type` creates a page for a new entry. Checks versions like `set` (CONFLICT), refuses multi-line text, stamps and citations inside `text`, and unknown sources. It is the AI's tool for keeping the derived view in step with its sources; it never writes a source document.
- **FR-8 `planning-impact`.** Given `item` (its names and aliases) and/or `terms` (phrases), returns every whole-word, case-insensitive match, grouped:
  - `planning`: decided planning facts (entry, section, fact id, text);
  - `sources`: per non-idea source, by rank: section ref, title, line, the matching line;
  - `chapters`: per card of `chapters` sources and per written-prose file of a `prose` source, with status `frozen` (≤ written), `current` (written + 1) or `planned`;
  - `pages`: project items (Wiki pages) and story pages whose text matches; story facts carry their chapter stamps, and those that start at or before `written` are `frozen`;
  - `written` as used, and a `limit` per group (default 40) with a `more` count.
  Idea sources and `## Ideas` sections are never searched.
- **FR-9 `planning-change`.** Records an author's change to one planning fact (`--fact ID` with new `--text`, or `--remove`) or a new fact (`--section` and `--text`):
  1. appends a HUMAN OVERRIDE entry to the `overrides` source (next free `HO-NNN`; the human decision verbatim; supersedes = the fact's refs and old text; scope; date; implications = the impact counts; status ACTIVE), when the world has one;
  2. appends `> **Amended by HO-NNN (date):** <new text>` (or "No longer true: <old text>") at the end of the cited section of the highest-ranked non-idea, non-override source the fact cites (write-back), preserving the file's line endings;
  3. updates the planning fact, citing the override first;
  4. returns the override id, the write-back place, the new fact, the impact review (FR-8, for the entry's names plus `terms`) and a Markdown `report`.
  It reads and checks every file, version and section before writing anything, then writes the register, the source and the page in that order; if a later write fails, the error names what was already written. A world without sources or register simply edits the fact. `lore mcp --saga` does not offer it; `serve --saga` turns an editor change into a change request instead.
- **FR-10 Change requests.** `request` accepts a planning key, so a saga's editor queues planning changes like any other.

### Editor
- **FR-11 Picker.** The Wiki tab's picker offers Planning (when the world has a planning layer), Complete and Chapter N, and remembers the choice.
- **FR-12 Planning card.** Name, type, aliases; sections of facts with citation chips that open the cited section's text; an Ideas block visibly labelled as undecided; the link lists (Notable members, Dialogues, Appears in, Ideas in the sources) with counts. Members open their planning card; chapters show number and title.
- **FR-13 Change flow.** Each fact has Change (new text, or remove, plus "your decision"). Local mode runs `planning-change` and shows the review; saga mode queues a change request and says so. Add a fact works the same way.
- **FR-14** Keyboard use, WCAG AA contrast in both themes, reduced motion and the 390 px layout meet feature 008's standard; live reload covers the planning folder.

### Never leaking
- **FR-15** Planning facts never reach `wiki` (Complete or Chapter N), item views, `export`, a saga profile packet or a drafting context. Tests prove it on a fixture whose planning facts carry a unique marker.

### AI use
- **FR-16** Every capability is one op (`planning`, `planning-source`, `planning-fact`, `planning-impact`, `planning-change`), so a CLI command with `--json`, an MCP tool and an editor API. Each op's guide says what it does, when to use it, what it returns and one example. Errors say what went wrong and how to fix it. `lore mcp --saga` offers `planning`, `planning-source`, `planning-impact` and `planning-fact` (writes only the planning folder, and only when the settings name one) and never `planning-change`.
- **FR-17** The user guide, the agent skill and the README explain the planning layer for any world.

### The three sagas (added on top; the saga system is unchanged)
- **FR-18** Each saga gets the re-vendored engine, a `planning_wiki` key in `_system/lorekeeper.json` naming its folder (`../Planning Wiki`) and its planning documents in AUTHORITY.md order, and a `Planning Wiki/` built from them: every entity with its own World Bible section or card-library entry, and every Wiki page entity, each fact citing its source section; ideas only in `## Ideas` sections. Values the AI decides go to the saga's `agent_decisions.md`.
- **FR-19** A shared skill `_system/skills/planning_wiki_change.md` (identical in all three, generic wording, listed in the skills README, one pointer) runs the change flow through the saga's existing human-change route: `impact_analyze_human_change`, the override register, `planning-change` through the vendored CLI, `refresh-sources` for the in-progress chapter, frozen chapters flagged to the author, separate commits.
- **FR-20** During the build no live authority document is edited. The full change flow is proven on a probe copy and its impact report shown to the owner.
- **FR-21** Landing is by fast-forward only, with the run-4 checks; in-progress chapters, `_system/state`, provenance and `saga.log` are never staged.

## Later (not in this feature)
- Manifest indirection for source file names (today a renamed bible means updating the settings; the error says so).
- Dialogue lists from chapter cards' conversation pointers.
- Per-field citations in frontmatter.
- A planning check inside `check` once the sagas opt in.

## Success criteria
- **SC-1 Unit tests (TDD):** the section reader (numbers, titles, `§`, levels, override ids, ambiguity); citations; the link lists, including the exclusion list, the case rule and short names; ideas kept apart; planning-change's override, write-back (CRLF and LF) and fact update; planning-impact's groups and statuses; planning facts never leaking (FR-15).
- **SC-2 A fixture world** with sources (bible, conversations, chapter outline, plot ideas, register) and planning pages: the card for a character lists its dialogues and chapters, a kind lists members, an excluded ordinary-word name lists nothing, ideas are labelled, and a change produces the override, the amendment and a review with frozen, current and planned chapters.
- **SC-3** The MCP golden test covers the new tools (MCP output equals `--json`); `lore mcp --saga` lists the four safe planning tools, refuses `planning-change` and refuses every write to an authority or Wiki page.
- **SC-4 Editor in Playwright** on the fixture and a saga clone: Planning in the picker; a planning card with citations, link lists and labelled ideas; the change flow (local review shown; saga request queued); light, dark and 390 px; no console errors; the Impeccable detector prints `[]`.
- **SC-5** On Realm's real documents, the planning index and a card each return in under 2 s.
- **SC-6 Sagas unchanged,** on clones before landing: suites green with parity; status, validate and health byte-identical for every chapter; `Wiki/`, `Story Wiki/`, roles, templates and existing skills untouched; in-progress profile packets verify.
- **SC-7 Sagas have a working planning wiki:** zero planning problems; a fresh reviewer spot-checks facts against their cited sections and confirms no planning fact appears in Complete or Chapter N; the Planning choice works in `saga.py timeline` (Playwright); the MCP handshake lists the planning tools.
- **SC-8** The change flow, run on a probe copy, records the override, writes back, refreshes the in-progress chapter, flags frozen chapters, and its impact report is sent to the owner.
- **SC-9** The full unit suite passes, with the stdlib-only import scan and the no-bare-`open()` scan.
