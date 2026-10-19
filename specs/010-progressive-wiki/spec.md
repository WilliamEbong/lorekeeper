# Feature 010: Progressive story wiki

## Overview
The owner asked on 2026-10-18 for a story wiki tied to where the reader is in the story. Pick chapter 3 and the wiki shows only what a reader who has finished chapter 3 knows. Pick chapter 10 and it shows the story as of chapter 10. A second, **complete** mode shows everything, for the author.

The only new idea is a **chapter stamp**: a short marker such as `[ch 7]` at the end of a fact, saying from which chapter the reader knows it. Everything works by hand. AI only makes it faster.
- **Hand-written worlds** keep their stamped facts in their own pages.
- **The owner's three sagas** keep them in a separate Story Wiki layer on top of the saga. The saga's own Wiki, templates, profile packets, pipeline stages, gates and commands keep working exactly as they do now. After a chapter is frozen, the AI uses that chapter's approved outputs to add its facts to the Story Wiki.

Why sagas need the separate layer: a saga's profile packet puts each character's whole Wiki page into the drafting AI's context, with a 60 KB cap. Facts that are no longer true, left in those pages, would mislead drafting and could overflow the cap.

Constraints are unchanged:
- The engine is standard-library Python. The editor is vanilla JavaScript with no build step and its strict Content-Security-Policy.
- The CLI, the MCP server and the editor share one operations table, so every new operation is also an MCP tool.
- Frontmatter stays flat (`key: value`, lists inline).
- In a saga, nothing is ever taken from a draft.

## Terms
- **Chapter number:** a position in reading order.
  - In a saga, the number in `CH004`.
  - In other worlds, a narrative item's `order` field, else the number in its id or name ("Chapter 4").
  - Prologues may use 0.
  - Numbers are continuous across a whole story. Lorekeeper never renumbers stamps when chapters move.
- **Fact:** one list item (with its continuation lines) or one paragraph. Headings, frontmatter and HTML comments are not facts.
- **Appears:** a page appears in the chapter named by its `first_appearance` field (`CH003` or `3`). A page without one is always visible.
- **Story page:** where a world keeps its stamped facts.
  - In a world without a story-wiki folder, the story page is the item's own page.
  - In a world with one, the story page is a companion page in that folder. It is linked to the item's page, or it stands alone, for example for someone the reader has seen but who has no Wiki page yet.
- **Progressive mode:** the wiki as of chapter N. **Complete mode:** the wiki with no cut-off.

## User scenarios
- **A novelist who writes by hand.** They add "Lost his left hand at the Gate. [ch 4]" and "Believes the far side is unarmed. [ch 2-5]". In the editor's Wiki tab they pick chapter 3: Darius's card shows the belief but not the lost hand. At chapter 6 the belief is gone and the hand is lost. In complete mode both show, the belief marked "ch 2–5".
- **The saga author after a chapter is frozen.**
  - The saga works as it always has.
  - After `freeze 5`, the AI reads CH005's approved outputs and adds the chapter's facts to the Story Wiki with Lorekeeper's fact commands.
  - In the Wiki tab, chapter 5 shows them and chapter 4 does not. Nothing from CH006, still a draft, exists anywhere.
  - The Wiki pages and the next chapter's profile packet are untouched.
- **A character seen before being named.** The hooded rider appears in chapter 2 and is named Kresh in chapter 6. At chapter 4 the index lists "the hooded rider". From chapter 6 it lists "Kresh". It is one card throughout.
- **A secret identity.** Lord Vane, met in chapter 3, is revealed in chapter 9 to be Kresh. Before chapter 9, Lord Vane and Kresh are two cards. From chapter 9 they are one card, "Kresh (also Lord Vane)". In complete mode there is only ever the one card, holding both identities.
- **Things and kinds of things.** "Standard alien battle tank" has a page, and so does a named tank that links to it. Each has a progressive card: what is known about the kind, and who holds the named tank, as of chapter N.
- **An AI agent in a saga session** calls Lorekeeper's MCP tools (`wiki`, `fact-add`, `fact-end`) directly, because the saga registers Lorekeeper's MCP server. A scripted pipeline step uses the same operations through the CLI with `--json`.
- **A game master** numbers sessions as chapters and checks what the players have learned by session 5.

## Functional requirements

### Recording
- **FR-1 Stamps.**
  - A fact ending in `[ch 7]` is known from chapter 7 on.
  - A fact ending in `[ch 2-5]` (an en dash also works) is known from chapter 2 and stops being current after chapter 5. Use this for beliefs, states and relationships that change.
  - Matching ignores case and spaces (`[CH 7]`, `[ch7]`).
  - An unstamped fact is known from its story page's first appearance. On a page with no `first_appearance`, it is always known.
  - A link value in frontmatter may carry a stamp after the link (`parent: "[[Mr Earnshaw]] [ch 4]"`), in the same place an offset like `+2h` goes today.
- **FR-2 Story-wiki folder.**
  - `lore.json` may name a `story_wiki` folder. Each companion page in it has `type` and `first_appearance` in its frontmatter, an optional `page` link to the item it describes, and a body of sections holding stamped facts.
  - When a world has this folder:
    - progressive cards use companion facts only, because the working pages are written for the present and would leak;
    - complete cards show the working page's body followed by the companion's facts and their ranges;
    - a page with no companion still appears in the index from its first appearance, and its card says no story facts are recorded yet.
  - Companion pages are never separate items in other views or checks, and never make a name ambiguous. Their file names never clash with page names, so Obsidian links stay unambiguous.
- **FR-3 Names.**
  - A story page may have a `## Names` section. Each fact in it is a name the reader knows the item by, with its stamp (`- the hooded rider [ch 2-5]`, `- Kresh [ch 6]`).
  - The shown name at chapter N is the latest-starting name whose range covers N. If no name covers N, it is the item's own name.
  - These names also resolve links, as `aliases` do.
- **FR-4 Secret identities.**
  - A new default role, `revealed_as` (label "Revealed to be", inverse "Also known as", single), links a story page to the one it turns out to be. Its stamp is the reveal chapter: `revealed_as: "[[Kresh]] [ch 9]"`.
  - From the reveal chapter on, and always in complete mode, the revealed page is folded into its target:
    - The index lists only the target, with "also Lord Vane".
    - The target's card merges the folded facts under matching headings, each marked "as Lord Vane".
    - Opening the folded page opens the target's card.
- **FR-5 Sections.**
  - A type in the schema may list starter `sections`. New story pages (from `create`, New item, or the first fact added to a companion) get them as empty headings.
  - Defaults:
    - **character:** Names, Current state, Where, Beliefs, Knows, Wants, Relationships, Important events
    - **organization:** Names, Leaders, Members, Goals, Territory, Allies and enemies, Standing, Important events
    - **location:** Names, Controlled by, Who is here, Condition, Important events
    - **item** and **technology:** Names, Kind, Held by, Where, Condition, What it does, Important events
  - Cards show a story page's own headings in page order. Pages with other headings work unchanged.
- **FR-6 Kinds of things.**
  - A new default role, `kind` (label "Kind", inverse "Examples", single, to thing types), links an individual thing to the page for its kind.
  - A kind is an ordinary thing page with its own progressive card.
  - Worlds may add thing types such as `vehicle` in `lore.json`. Nothing about them is special.
- **FR-7 Fact operations (CLI, MCP and editor API).**
  - `lore fact-add NAME --section S --text T --from N [--to M]` appends a stamped fact to the end of section S of NAME's story page. It creates the companion page, with its starter sections, when the world has a story-wiki folder and none exists yet.
  - `lore fact-end NAME --section S --fact TEXT --after M` closes the range of the first fact in S that starts with TEXT.
  - Both check versions like `set` does (CONFLICT on a clashing edit), refuse unreadable chapters and ranges, and return the new version.
  - These operations are how AI updates the wiki. Agents never hand-edit stamps.

### Reading
- **FR-8 The `wiki` operation (CLI, MCP and editor API).**
  - `lore wiki [--as-of N]` returns the index:
    - entries grouped by type (plural label), sorted by shown name;
    - each entry with its shown name, type, page and the chapter it appears in;
    - pages that have not appeared by N, and pages folded into another, are left out.
  - `lore wiki NAME [--as-of N]` returns the card:
    - the shown name, type and appearance chapter;
    - the other names known by N;
    - the sections in page order, each with its visible facts, and each fact with its from and to chapters;
    - the worked-out facts (FR-11).
  - Both also return the chapter list (FR-12).
  - Without `--as-of`, both are in complete mode. `--json` works as everywhere else.
  - In progressive mode, a name that has not appeared by N gives the same NOT_FOUND as a name that does not exist.
- **FR-9 Progressive rules.**
  - A fact is visible at N when its start is ≤ N and it has no end or its end is ≥ N.
  - A page is visible at N when it appears at or before N.
  - In visible text, a link to a page that is not visible at N is shown as plain text.
  - Frontmatter fields (dates, tags, status and the rest) are not shown on progressive cards, because a death date is a spoiler. Per-field stamps are Later.
- **FR-10 Complete rules.**
  - Every fact is shown, ended ones with their range ("ch 2–5").
  - Frontmatter fields are shown.
  - All names are listed with their chapters.
  - Folded identities are merged as in FR-4.
- **FR-11 Worked-out facts.** When a card's section has no written fact visible at N, Lorekeeper fills it from the world's links, marked "worked out":
  - **Where:** the place of the latest-dated (in-world time) located event the person took part in, among events visible at N.
  - **Knows:** what Reveals (`learns`) links on events visible at N teach the person, from events they took part in.
  - **Relationships:** role links between person and group pages (parent, spouse, member of, and the like) whose stamp, or else their page's appearance, is ≤ N, when both ends are visible.
- **FR-12 Chapter list.** Chapters 1 up to the highest chapter number used by any stamp or `first_appearance`, each labelled with its narrative item's name when one has that number.

### Editor
- **FR-13 Wiki tab.**
  - A new tab with the index on the left (type groups with counts, and a filter box) and a card on the right.
  - A picker above the index offers "Complete" and "Chapter N — name". It starts on Complete and remembers the last choice in the browser.
  - The picker changes only the Wiki tab. Other views stay complete, because their dates would give deaths away (Later).
- **FR-14 Cards.**
  - Each card has its own toggle (previous and next buttons plus a select, including Complete). It starts at the picker's value and changes only that card.
  - The card shows the shown name, "Appears in chapter K", other names, sections and facts.
  - Each fact carries a quiet chapter marker. In complete mode, ended facts are visibly marked as no longer current.
  - Linked names of visible pages open their card at the same chapter. "Edit" selects the item in the inspector.
- **FR-15 Adding by hand.**
  - Each section on a card has "Add a fact" (text plus a from-chapter that defaults to the card's chapter).
  - Each fact offers "No longer true after chapter…".
  - Both use the fact operations. In local mode they show the usual Undo message. In saga mode they queue a change request, like every other editor edit in a saga.
- **FR-16** The Wiki tab follows live reload like the other views.
- **FR-17** Keyboard use, WCAG AA contrast in both themes, reduced motion and the 390 px layout meet the standard set by feature 008.

### Checks
- **FR-18** `check` gains two WARN codes:
  - `STAMP_UNREADABLE`: a `[ch …]` marker that cannot be read.
  - `STAMP_RANGE`: a range that ends before it starts.

### The three sagas (added on top; the saga system is unchanged)
- **FR-19 Nothing existing changes.**
  - Wiki pages, Wiki templates, profile packets, pipeline stages, gates, `freeze` and every existing command and skill behave exactly as before.
  - The only edits to existing files are additive: the vendored engine, `_system/lorekeeper.json` (which profile packets do not fingerprint), the skills README listing, and one pointer that tells the AI to run the Story Wiki update after `freeze`.
- **FR-20 Story Wiki.** Each saga gets a `Story Wiki/` folder of companion pages, named as its `story_wiki` folder in `_system/lorekeeper.json`.
- **FR-21 After-freeze update.**
  - A new shared skill, `_system/skills/story_wiki_update.md`, is identical in all three sagas, worded generically so the saga docs test passes, and listed in the skills README.
  - It tells the AI, after `saga.py freeze N`, to:
    - read only approved sources: the frozen chapter, its `CURRENT_WORLD_BIBLE_OUT.md`, its approved deltas, and the Wiki as committed by the freeze;
    - write chapter N's facts with `fact-add` and `fact-end` through the vendored CLI;
    - run `check`;
    - commit only `Story Wiki/` paths in a separate `wiki:` commit.
  - If the step is skipped, the saga still works, and the Story Wiki is simply behind.
- **FR-22 Backfill.**
  - Every frozen chapter is written into the Story Wiki from the same approved sources, using the Wiki as committed at each chapter's freeze.
  - Any value the AI has to decide, such as the reader's description of an unnamed character, is recorded in the saga's `agent_decisions.md`, as with other agent decisions.
  - No live Wiki page is edited, so in-progress chapters are not touched.
- **FR-23 MCP in the sagas.**
  - Each saga gets a project `.mcp.json` that runs the vendored engine's MCP server (`lore mcp`) on that saga. Any Claude Code session opened in the saga then has Lorekeeper's tools, the new `wiki` and fact tools included. Claude Code asks once to approve it.
  - The README shows the same setup for any world.
- **FR-24 Landing.**
  - The saga work is done in clones under `lk-scratch` and landed by fast-forward only, together with re-vendoring the engine.
  - In-progress chapters, `_system/state`, provenance and `saga.log` are never staged.

### Starter worlds and guides
- **FR-25** The Novel, Series and Worldbuilding templates include a few stamped facts, a renamed character and a secret identity, so a new world shows the progressive wiki working.
- **FR-26** The user guide, the agent skill and the README explain stamps, story pages, the two modes, the `wiki` and fact operations, the Wiki tab and MCP setup.

## Later (not in this feature)
- Per-field stamps (for `born`, `died`, `status`), and the chapter picker filtering Timeline, Subway, Ages, Relationships and Spreadsheet.
- Age as of a chapter.
- Spoiler-safe export (`lore export md --as-of N`) for beta readers and players.
- Chapter numbers relative to a book in a series.
- Planned versus actual reveals, and showing what the reader knows that a character does not.
- A saga warning when the Story Wiki is behind the last frozen chapter.

## Success criteria
- **SC-1 Unit tests:**
  - every stamp form and ranges;
  - unstamped facts inheriting the appearance;
  - visibility at N;
  - shown names at N;
  - folding at the reveal chapter;
  - companion pages: used in progressive mode, appended in complete mode, never items, never ambiguous;
  - `fact-add` and `fact-end`, including CONFLICT and refused input;
  - worked-out facts limited to visible events and links;
  - links to hidden pages shown as plain text;
  - both new check codes.
- **SC-2 A fixture world** has a hooded rider named Kresh in chapter 6, Lord Vane revealed as Kresh in chapter 9, a belief stamped 2–5, and a battle-tank kind with one named tank. It is tested twice: facts in the pages, then the same facts in a story-wiki folder.
  - At chapter 5, the index lists "the hooded rider" and "Lord Vane", not "Kresh".
  - At chapter 6, it lists "Kresh" and "Lord Vane".
  - At chapter 9, it lists only "Kresh", with "also Lord Vane".
  - In complete mode, it lists only "Kresh", holding both identities.
  - Kresh's card at chapter 5 holds no fact stamped 6 or later.
  - The MCP output equals `lore wiki --json`.
- **SC-3 Editor, checked in Playwright on the fixture and on a saga clone:**
  - the picker, the index and the card toggle;
  - Add a fact, then Undo;
  - complete mode marks ended facts;
  - in saga mode, Add a fact queues a change request;
  - light, dark and 390 px screenshots with no overflow and no console errors;
  - the Impeccable detector prints `[]`.
- **SC-4** On a 3,000-item world, the index and a card each return in under 1 s.
- **SC-5 Sagas unchanged, on the clones before landing:**
  - Every saga suite passes, parity included.
  - `status` and `validate` output for every chapter is byte-identical before and after.
  - `Wiki/` and every existing skill, role and template are byte-identical. The only diffs are the additions listed in FR-19 to FR-23.
  - The in-progress chapters' profile packets still verify.
- **SC-6 Sagas have a working Story Wiki.** For every frozen chapter k:
  - the index at k holds every page that appears at or before k, and no later page;
  - every character who has a Wiki page and is named in the Characters part of `CURRENT_WORLD_BIBLE_OUT.md` after CHk has at least one fact visible at k;
  - a fresh-context reviewer compares three characters per saga against those snapshots.
- **SC-7** In a saga clone, the `.mcp.json` server starts and lists `wiki`, `fact-add` and `fact-end` (an MCP handshake test).
- **SC-8** The full unit suite passes, and so do the stdlib-only import scan and the no-bare-`open()` scan.
