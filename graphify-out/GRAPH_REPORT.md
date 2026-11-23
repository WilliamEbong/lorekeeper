# Graph Report - overnight-fixes-77b916  (2026-11-23)

## Corpus Check
- 90 files · ~132,015 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1617 nodes · 3530 edges · 86 communities (73 shown, 13 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 183 edges (avg confidence: 0.62)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `01b6b083`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- planning.py
- run
- wiki.py
- app.py
- run
- editor.js
- update
- InteropTests
- GregorianTests
- Your story in Lorekeeper
- Item
- interop.py
- timeline
- ServeTests
- ServerTests
- Checks
- guard.py
- el
- McpTests
- Feature 011: Planning wiki
- enableRedate
- renderView
- SKILL.md
- SKILL.md
- spreadsheet
- checks.py
- Loading
- atomic_write
- LoreError
- lore
- Aeon Timeline 3 file format and behaviour: clean-room notes for Lorekeeper interop
- Calendar
- AuditFixes
- app.js
- Execution Steps
- inside
- EditorDateMathsTests
- Feature 010: Progressive story wiki
- test_saga_dates.py
- mcp.py
- Writing
- cli.py
- op_link
- Feature 012: The Lorekeeper app
- Design
- Contracts
- Feature 001: Core model, storage, operations, CLI and MCP
- LocalHandler
- TimeOps
- SKILL.md
- relationships
- Tasks 010: Progressive story wiki
- SKILL.md
- Overnight changes (2026-11-22 to 23)
- Feature 013: A plain-language editor
- fastest
- Tasks 001: core
- Feature 002: Time (calendars, dates with uncertainty, durations, ages)
- Feature 003: Checks (Aeon's checks plus the ones Aeon lacks)
- Feature 004: Saga integration (Realm, Space, Zombies) in warn mode
- Feature 008: Editor UX overhaul
- Speckit Constitution Skill
- SKILL.md
- explain
- Plan 002: time
- Plan 003: checks
- Feature 005: Interactive editor (`lore serve`)
- Feature 006: Interop (Aeon Timeline `.aeon`, CSV, Markdown)
- Plan 008: Editor UX overhaul
- Feature 009: Editor follow-ups (owner review of 008)
- Plan 010: Progressive story wiki
- aeon_extract.py
- Speckit Implement Skill
- Speckit Plan Skill
- Speckit Specify Skill
- Speckit Tasks Skill
- Feature 007: Templates, onboarding, packaging
- Lorekeeper — agent rules
- Lorekeeper
- Tasks 003: checks
- tasks.md
- tasks.md
- tasks.md
- tasks.md
- lorekeeper

## God Nodes (most connected - your core abstractions)
1. `LoreError` - 157 edges
2. `Project` - 71 edges
3. `el()` - 45 edges
4. `InteropTests` - 43 edges
5. `run()` - 38 edges
6. `ServeTests` - 37 edges
7. `Checks` - 31 edges
8. `renderView()` - 30 edges
9. `timeline()` - 29 edges
10. `item_dates()` - 29 edges

## Surprising Connections (you probably didn't know these)
- `run()` --calls--> `emit()`  [INFERRED]
  lorekeeper/checks.py → tools/build-hooks/guard.py
- `human()` --calls--> `names()`  [INFERRED]
  lorekeeper/cli.py → tests/test_wiki.py
- `McpTests` --uses--> `LoreError`  [INFERRED]
  tests/test_mcp.py → lorekeeper/store.py
- `ChangeTests` --uses--> `LoreError`  [INFERRED]
  tests/test_planning.py → lorekeeper/store.py
- `CitationTests` --uses--> `LoreError`  [INFERRED]
  tests/test_planning.py → lorekeeper/store.py

## Import Cycles
- None detected.

## Communities (86 total, 13 thin omitted)

### Community 0 - "planning.py"
Cohesion: 0.07
Nodes (40): _amend(), change(), _check_refs(), _check_text(), cite(), _counts(), _done(), Entry (+32 more)

### Community 1 - "run"
Cohesion: 0.06
Nodes (23): build(), CliTests, CreateTests, FactOpTests, facts(), names(), Feature 010: chapter stamps, story pages and the progressive wiki., SC-2, run on both layouts. (+15 more)

### Community 2 - "wiki.py"
Cohesion: 0.06
Nodes (49): op_fact_add(), append_fact(), chapter(), _check_section(), _check_span(), _check_text(), companion_name(), companion_path() (+41 more)

### Community 3 - "app.py"
Cohesion: 0.06
Nodes (54): act_create(), act_forget(), act_open(), act_pick(), act_show(), ai_guide(), App, AppError (+46 more)

### Community 4 - "run"
Cohesion: 0.06
Nodes (18): ChangeTests, CitationTests, CliTests, copy_fixture(), FactTests, ImpactTests, LeakTests, Feature 011: the planning wiki (source reader, citations, link lists, ideas, imp (+10 more)

### Community 5 - "editor.js"
Cohesion: 0.06
Nodes (55): ages, ApiError, byPath, calendars, cellId(), cells, civil(), conversions (+47 more)

### Community 6 - "update"
Cohesion: 0.09
Nodes (21): _block(), _format_string(), format_value(), Frontmatter, FrontmatterError, link_target(), _list_item(), parse() (+13 more)

### Community 7 - "InteropTests"
Cohesion: 0.10
Nodes (8): archive(), container(), InteropTests, Interop acceptance tests. Proprietary templates are inspected only in memory., Independent fixture encoder, including the v2 stored-size field., Independent test decoder: locate root timeline and its first leaf payload., sample(), timeline_json()

### Community 8 - "GregorianTests"
Cohesion: 0.05
Nodes (6): ArithmeticTests, CivilTests, CustomCalendarTests, Decades, GregorianTests, Date arithmetic and grammar vectors; no external saga files are needed.

### Community 9 - "Your story in Lorekeeper"
Cohesion: 0.05
Nodes (35): Lorekeeper agent skill, Create, connect and revise, Dates and uncertainty, Files you can keep, Import and export, Open Lorekeeper, Read a continuity report, Start a world from a terminal (+27 more)

### Community 10 - "Item"
Cohesion: 0.13
Nodes (10): Item, AgelessPeople, OrderCheck, No recorded death, yet older than anyone could be by the latest date in the stor, card(), codes(), DayOverflow, Flashbacks (+2 more)

### Community 11 - "interop.py"
Cohesion: 0.10
Nodes (37): _aeon_date(), _ancestors(), _archive(), _calendar(), _check_shapes(), _collection(), _csv_date(), _csv_value() (+29 more)

### Community 12 - "timeline"
Cohesion: 0.13
Nodes (34): agesView(), byName(), chart(), dated(), endKey(), events(), fit(), fitAll() (+26 more)

### Community 14 - "ServerTests"
Cohesion: 0.08
Nodes (8): AppTestCase, CreateAndAIFileTests, LauncherTests, LaunchTests, The Lorekeeper app: world list, folder kinds, AI files and the start-screen serv, Run Open Lorekeeper.bat with a stand-in pyw/pythonw that records a launch instea, ServerTests, WorldListTests

### Community 15 - "Checks"
Cohesion: 0.18
Nodes (6): Checks, Comparisons, findings(), item(), project(), Certainty vectors for the public checks API; synthetic worlds stay in memory.

### Community 16 - "guard.py"
Cohesion: 0.13
Nodes (21): build(), do_compact(), do_post(), do_pre(), do_start(), emit(), git(), last_user_message() (+13 more)

### Community 17 - "el"
Cohesion: 0.29
Nodes (24): add(), button(), chapterName(), chapterSelect(), chips(), chText(), citeBox(), continuity() (+16 more)

### Community 18 - "McpTests"
Cohesion: 0.10
Nodes (7): McpTests, meta(), Protocol coverage and golden parity with the real CLI., 2026-07-28 clients reject a tools/list result without ttlMs and cacheScope (0 to, The fact tools write the same bytes and return the same data through MCP and the, The planning tools return the same data through MCP and the CLI (reads on the fi, lore mcp --saga: planning-change is refused; planning-fact needs a planning fold

### Community 19 - "Feature 011: Planning wiki"
Cohesion: 0.07
Nodes (27): Design, Files, Plan: Feature 011, planning wiki, Risks, Saga integration (run-4 method), Technical context, AI use, Changing (+19 more)

### Community 20 - "enableRedate"
Cohesion: 0.21
Nodes (24): addFieldRow(), addLinkForm(), anyDirty(), conflictActions(), dirty(), groupBy(), idle(), inspectorWelcome() (+16 more)

### Community 21 - "renderView"
Cohesion: 0.17
Nodes (21): activateTab(), addForm(), api(), endForm(), indexGraph(), lastChapter(), loadGraph(), numberField() (+13 more)

### Community 22 - "SKILL.md"
Cohesion: 0.08
Nodes (25): 1. Initialize Analysis Context, 2. Load Artifacts (Progressive Disclosure), 3. Build Semantic Models, 4. Detection Passes (Token-Efficient Analysis), 5. Severity Assignment, 6. Produce Compact Analysis Report, 7. Provide Next Actions, 8. Offer Remediation (+17 more)

### Community 23 - "SKILL.md"
Cohesion: 0.12
Nodes (25): Lorekeeper: a plain-text story-world engine (CLI `lore`, MCP server, local edito, _events_of(), op_age(), op_check(), op_graph(), op_knows(), op_planning_fact(), op_requests() (+17 more)

### Community 24 - "spreadsheet"
Cohesion: 0.16
Nodes (22): changes(), display(), editableCell(), fieldRow(), fieldsFor(), isDateKey(), isList(), isRole() (+14 more)

### Community 25 - "checks.py"
Cohesion: 0.18
Nodes (17): compare_eq(), compare_ge(), _compare_shifted_eq(), _date_key(), flashback(), order_check(), possible(), Read-only, uncertainty-aware continuity checks over stored or in-memory items. (+9 more)

### Community 26 - "Loading"
Cohesion: 0.15
Nodes (3): merged_schema(), A project over given items, without scanning files., Loading

### Community 27 - "atomic_write"
Cohesion: 0.14
Nodes (6): finding(), Project, The story wiki and planning wiki folders, normcased: their pages are not items., A name, file stem or alias that two items claim: its links silently pick one of, The user's three saga Wikis are Lorekeeper projects as they stand (skipped where, SagaWikis

### Community 28 - "LoreError"
Cohesion: 0.11
Nodes (7): op_planning_source(), op_set(), op_wiki(), LoreError, Exception, Regression checks for the feature-001 adversarial review findings., Review

### Community 29 - "lore"
Cohesion: 0.05
Nodes (35): build_parser(), chapters(), human(), interval(), key_value(), main(), planning_text(), `lore` command line, generated from the operations table. (+27 more)

### Community 30 - "Aeon Timeline 3 file format and behaviour: clean-room notes for Lorekeeper interop"
Cohesion: 0.10
Nodes (20): 1.1 Header (40 bytes), 1.2 Root archive, 1.3 Leaf archives (`attachments`, `timeline`), 1.4 Writing, 1. Container (`.aeon`), 2.1 Shapes the loader accepts (observed), 2.2 v14 → v27 differences that matter to a reader, 2. Top-level JSON (+12 more)

### Community 31 - "Calendar"
Cohesion: 0.17
Nodes (14): add(), age(), Calendar, calendars(), civil_from_days(), days_from_civil(), parse_duration(), Integer-minute dates, configured calendars, and uncertainty intervals. (+6 more)

### Community 33 - "app.js"
Cohesion: 0.28
Nodes (16): aiNote(), ask(), busy(), button(), el(), folderName(), load(), opened() (+8 more)

### Community 34 - "Execution Steps"
Cohesion: 0.12
Nodes (15): 1. Initialize Convergence Context, 2. Load Artifacts (Progressive Disclosure), 3. Build the Intent Inventory, 4. Assess the Codebase and Classify Findings, 5. Assign Severity, 6. Present the In-Session Findings Summary, 7. Append Convergence Tasks (or report converged), 8. Provide Next Actions (Handoff) (+7 more)

### Community 35 - "inside"
Cohesion: 0.29
Nodes (7): op_export(), op_init(), Write the project as .aeon (Aeon Timeline), CSV (Aeon column ids) or one Markdow, to_json(), Hash metadata in configured roots, plus lore.json; skip excluded folders., stamp(), inside()

### Community 37 - "Feature 010: Progressive story wiki"
Cohesion: 0.12
Nodes (15): Checks, Clarifications, Editor, Feature 010: Progressive story wiki, Functional requirements, Later (not in this feature), Overview, Reading (+7 more)

### Community 38 - "test_saga_dates.py"
Cohesion: 0.40
Nodes (3): architecture(), Every chapter-card date in the three saga architectures parses (skipped where th, SagaCardDates

### Community 39 - "mcp.py"
Cohesion: 0.50
Nodes (4): parse(), op_convert(), When a person's second life begins (the `reborn` field), or None., reborn()

### Community 41 - "cli.py"
Cohesion: 0.14
Nodes (15): _check_link_version(), op_request(), Queue a change request instead of editing (saga mode): the pipeline applies it l, blank(), clean_fields(), file_sha(), find_root(), Project loading, link resolution and safe writes for a folder of Markdown items. (+7 more)

### Community 42 - "op_link"
Cohesion: 0.67
Nodes (4): op_link(), op_unlink(), _role_values(), _targets()

### Community 43 - "Feature 012: The Lorekeeper app"
Cohesion: 0.14
Nodes (13): AI instructions, Clarifications, Editor, Feature 012: The Lorekeeper app, Functional requirements, Out of scope, Overview, Safety (+5 more)

### Community 48 - "Design"
Cohesion: 0.15
Nodes (12): AI files, Constitution check, Design, Files, Folder kinds, Launch and install, Plan 012: The Lorekeeper app, Sagas (+4 more)

### Community 51 - "Contracts"
Cohesion: 0.18
Nodes (10): cli.py, Contracts, Design decisions, File structure, fm.py, mcp.py, ops.py, Plan 001: core (+2 more)

### Community 52 - "Feature 001: Core model, storage, operations, CLI and MCP"
Cohesion: 0.18
Nodes (10): Defaults chosen (logged), Feature 001: Core model, storage, operations, CLI and MCP, Format, Functional requirements, Operations, Overview, Project, Safe writes (+2 more)

### Community 53 - "LocalHandler"
Cohesion: 0.14
Nodes (12): BaseHTTPRequestHandler, LocalHandler, make_server(), Loopback-only HTTP adapter over OPS and the bundled, build-free editor., The request body when it is 1 byte to `limit`; otherwise b"", after reading and, A loopback-only request handler: Host check, security headers and JSON error rep, read_body(), serve() (+4 more)

### Community 57 - "SKILL.md"
Cohesion: 0.25
Nodes (7): Anti-Examples: What NOT To Do, Checklist Purpose: "Unit Tests for English", Example Checklist Types & Sample Items, Execution Steps, Post-Execution Checks, Pre-Execution Checks, User Input

### Community 59 - "relationships"
Cohesion: 0.39
Nodes (8): CATEGORIES, category(), relationships(), TIMING, typeChips(), typeInfo(), typePlural(), typeRank()

### Community 61 - "Tasks 010: Progressive story wiki"
Cohesion: 0.25
Nodes (7): Editor, Engine (TDD: test first, watch it fail, then code), Faces, Finish, Sagas (clones and probes under lk-scratch), Starter worlds and guides, Tasks 010: Progressive story wiki

### Community 63 - "SKILL.md"
Cohesion: 0.29
Nodes (6): Completion Report, Done When, Mandatory Post-Execution Hooks, Outline, Pre-Execution Checks, User Input

### Community 65 - "Overnight changes (2026-11-22 to 23)"
Cohesion: 0.17
Nodes (11): Changes, Design pass: the editor, wiki and start screen, Design scoring: final scores, How to merge and re-vendor, Other branches, Overnight changes (2026-11-22 to 23), Round 2: the items round 1 found (owner approved), Round 3: tidy and graphify (+3 more)

### Community 66 - "Feature 013: A plain-language editor"
Cohesion: 0.29
Nodes (6): Clarifications, Feature 013: A plain-language editor, Functional requirements, Overview, Session 2026-10-19, Success criteria

### Community 69 - "fastest"
Cohesion: 0.39
Nodes (5): fastest(), Perf, n items: a third characters, a third places, a third events linking both., The best of a few timed runs: a busy machine slows one run, a real regression sl, synthetic()

### Community 74 - "Tasks 001: core"
Cohesion: 0.33
Nodes (5): Foundational, Polish, Setup, Tasks 001: core, User stories

### Community 75 - "Feature 002: Time (calendars, dates with uncertainty, durations, ages)"
Cohesion: 0.33
Nodes (5): Feature 002: Time (calendars, dates with uncertainty, durations, ages), Functional requirements, Overview, Success criteria, User scenarios

### Community 76 - "Feature 003: Checks (Aeon's checks plus the ones Aeon lacks)"
Cohesion: 0.33
Nodes (5): Definitions, Feature 003: Checks (Aeon's checks plus the ones Aeon lacks), Functional requirements, Overview, Success criteria

### Community 77 - "Feature 004: Saga integration (Realm, Space, Zombies) in warn mode"
Cohesion: 0.33
Nodes (5): Feature 004: Saga integration (Realm, Space, Zombies) in warn mode, Functional requirements, Overview, Success criteria, User scenarios

### Community 78 - "Feature 008: Editor UX overhaul"
Cohesion: 0.33
Nodes (5): Feature 008: Editor UX overhaul, Functional requirements, Overview, Success criteria (Playwright MCP, on a scratch copy of a 116-item imported world and on the fixture world), User scenarios

### Community 82 - "Speckit Constitution Skill"
Cohesion: 0.40
Nodes (4): Outline, Scope Guard, Speckit Constitution Skill, User Input

### Community 83 - "SKILL.md"
Cohesion: 0.40
Nodes (4): Outline, Post-Execution Checks, Pre-Execution Checks, User Input

### Community 86 - "explain"
Cohesion: 0.50
Nodes (5): explain(), findingText(), lagWords(), plainText(), unlink()

### Community 88 - "Plan 002: time"
Cohesion: 0.40
Nodes (4): dates.py contract, Decisions, Files, Plan 002: time

### Community 89 - "Plan 003: checks"
Cohesion: 0.40
Nodes (4): checks.py contract, Decisions, Files, Plan 003: checks

### Community 90 - "Feature 005: Interactive editor (`lore serve`)"
Cohesion: 0.40
Nodes (4): Feature 005: Interactive editor (`lore serve`), Functional requirements, Overview, Success criteria (verified with the Playwright MCP)

### Community 91 - "Feature 006: Interop (Aeon Timeline `.aeon`, CSV, Markdown)"
Cohesion: 0.40
Nodes (4): Feature 006: Interop (Aeon Timeline `.aeon`, CSV, Markdown), Functional requirements, Overview, Success criteria

### Community 92 - "Plan 008: Editor UX overhaul"
Cohesion: 0.40
Nodes (4): Design decisions, Plan 008: Editor UX overhaul, Technical context, Verification

### Community 93 - "Feature 009: Editor follow-ups (owner review of 008)"
Cohesion: 0.40
Nodes (4): Feature 009: Editor follow-ups (owner review of 008), Functional requirements, Overview, Success criteria

### Community 94 - "Plan 010: Progressive story wiki"
Cohesion: 0.40
Nodes (4): Design decisions, Plan 010: Progressive story wiki, Technical context, Verification

### Community 95 - "aeon_extract.py"
Cohesion: 0.50
Nodes (4): inflate_all(), main(), Re-extract the web app, templates and assets embedded in AeonTimeline.exe.  Aeon, Yield each zlib stream in buf; stop at the trailing index (non-zlib bytes).

### Community 96 - "Speckit Implement Skill"
Cohesion: 0.50
Nodes (3): Outline, Speckit Implement Skill, User Input

### Community 97 - "Speckit Plan Skill"
Cohesion: 0.50
Nodes (3): Outline, Speckit Plan Skill, User Input

### Community 98 - "Speckit Specify Skill"
Cohesion: 0.50
Nodes (3): Outline, Speckit Specify Skill, User Input

### Community 99 - "Speckit Tasks Skill"
Cohesion: 0.50
Nodes (3): Outline, Speckit Tasks Skill, User Input

### Community 105 - "Feature 007: Templates, onboarding, packaging"
Cohesion: 0.50
Nodes (3): Feature 007: Templates, onboarding, packaging, Functional requirements, Success criteria

## Knowledge Gaps
- **276 isolated node(s):** `state`, `token`, `calendars`, `worldName`, `MONTHS` (+271 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `LoreError` connect `LoreError` to `planning.py`, `run`, `wiki.py`, `app.py`, `run`, `interop.py`, `McpTests`, `SKILL.md`, `Loading`, `atomic_write`, `lore`, `AuditFixes`, `inside`, `mcp.py`, `Writing`, `cli.py`, `op_link`, `LocalHandler`, `TimeOps`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._
- **Why does `Project` connect `atomic_write` to `AuditFixes`, `inside`, `app.py`, `fastest`, `Writing`, `cli.py`, `Item`, `ServeTests`, `Checks`, `LocalHandler`, `SKILL.md`, `Loading`, `LoreError`?**
  _High betweenness centrality (0.049) - this node is a cross-community bridge._
- **Why does `McpTests` connect `McpTests` to `LoreError`?**
  _High betweenness centrality (0.027) - this node is a cross-community bridge._
- **Are the 83 inferred relationships involving `LoreError` (e.g. with `App` and `.open_world()`) actually correct?**
  _`LoreError` has 83 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `Project` (e.g. with `AgelessPeople` and `Checks`) actually correct?**
  _`Project` has 15 INFERRED edges - model-reasoned connections that need verification._
- **What connects `state`, `token`, `calendars` to the rest of the system?**
  _276 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `planning.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06873706004140787 - nodes in this community are weakly interconnected._