# Graph Report - overnight-fixes-77b916  (2026-11-23)

## Corpus Check
- 159 files · ~152,132 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 1906 nodes · 3771 edges · 147 communities (111 shown, 36 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 183 edges (avg confidence: 0.62)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `ea902b2c`
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
- item_dates
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
- Tasks: [FEATURE NAME]
- SKILL.md
- SKILL.md
- spreadsheet
- Project
- ops.py
- atomic_write
- LoreError
- lore
- Aeon Timeline 3 file format and behaviour: clean-room notes for Lorekeeper interop
- Calendar
- Item
- app.js
- Execution Steps
- Execution Steps
- common.ps1
- Feature 010: Progressive story wiki
- store.py
- mcp.py
- Writing
- cli.py
- dates.py
- Feature 012: The Lorekeeper app
- inside
- Loading
- Core Principles
- Feature Specification: [FEATURE NAME]
- Design
- AuditFixes
- Core Principles
- Contracts
- Feature 001: Core model, storage, operations, CLI and MCP
- LocalHandler
- Implementation Plan: [FEATURE]
- conversations.md
- TimeOps
- SKILL.md
- SKILL.md
- relationships
- Lean Workflow
- Tasks 010: Progressive story wiki
- test_rules.py
- SKILL.md
- SKILL.md
- Overnight changes (2026-11-22 to 23)
- Feature 013: A plain-language editor
- Ivo Brandt.md
- EditorDateMathsTests
- fastest
- selectItem
- make_server
- _open
- create-new-feature.ps1
- Tasks 001: core
- Feature 002: Time (calendars, dates with uncertainty, durations, ages)
- Feature 003: Checks (Aeon's checks plus the ones Aeon lacks)
- Feature 004: Saga integration (Realm, Space, Zombies) in warn mode
- Feature 008: Editor UX overhaul
- 1. Peoples
- Rules
- test_saga_dates.py
- Speckit Constitution Skill
- SKILL.md
- Speckit Constitution Skill
- SKILL.md
- explain
- [CHECKLIST TYPE] Checklist: [FEATURE NAME]
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
- Speckit Implement Skill
- Speckit Plan Skill
- Speckit Specify Skill
- Speckit Tasks Skill
- speckit.constitution.md
- Feature 007: Templates, onboarding, packaging
- Plot ideas
- Human Override Register
- Sava
- Crossing Harrow Pass.md
- Lorekeeper — agent rules
- Lorekeeper
- speckit.implement.md
- speckit.plan.md
- speckit.specify.md
- speckit.tasks.md
- Tasks 003: checks
- Bo
- Edran
- Mirela
- Will Marsh
- Vampires
- Nightjar fighter
- Sava
- tasks.md
- tasks.md
- tasks.md
- tasks.md
- CH001.md
- CH002.md
- The Voyage.md
- Edran.md
- Sava.md
- Chapter 1.md
- Harrow Pass.md
- Saltmarsh.md
- Salt Road Guild.md
- lorekeeper

## God Nodes (most connected - your core abstractions)
1. `LoreError` - 157 edges
2. `Project` - 71 edges
3. `el()` - 45 edges
4. `InteropTests` - 42 edges
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

## Communities (147 total, 36 thin omitted)

### Community 0 - "planning.py"
Cohesion: 0.06
Nodes (43): op_planning_fact(), _amend(), change(), _check_refs(), _check_text(), cite(), _counts(), _done() (+35 more)

### Community 1 - "run"
Cohesion: 0.06
Nodes (23): build(), CliTests, CreateTests, FactOpTests, facts(), names(), Feature 010: chapter stamps, story pages and the progressive wiki., SC-2, run on both layouts. (+15 more)

### Community 2 - "wiki.py"
Cohesion: 0.06
Nodes (40): op_fact_add(), append_fact(), chapter(), _check_span(), _check_text(), companion_name(), covers(), Entry (+32 more)

### Community 3 - "app.py"
Cohesion: 0.07
Nodes (52): act_create(), act_forget(), act_open(), act_pick(), act_show(), ai_guide(), App, AppError (+44 more)

### Community 4 - "run"
Cohesion: 0.06
Nodes (17): ChangeTests, CitationTests, CliTests, copy_fixture(), FactTests, ImpactTests, LeakTests, Feature 011: the planning wiki (source reader, citations, link lists, ideas, imp (+9 more)

### Community 5 - "editor.js"
Cohesion: 0.05
Nodes (52): activateTab(), ages, ApiError, byPath, calendars, cells, civil(), conversions (+44 more)

### Community 6 - "update"
Cohesion: 0.09
Nodes (20): _block(), _format_string(), format_value(), Frontmatter, FrontmatterError, link_target(), _list_item(), parse() (+12 more)

### Community 7 - "InteropTests"
Cohesion: 0.11
Nodes (7): archive(), container(), InteropTests, Independent fixture encoder, including the v2 stored-size field., Independent test decoder: locate root timeline and its first leaf payload., sample(), timeline_json()

### Community 8 - "GregorianTests"
Cohesion: 0.05
Nodes (6): ArithmeticTests, CivilTests, CustomCalendarTests, Decades, GregorianTests, Date arithmetic and grammar vectors; no external saga files are needed.

### Community 9 - "Your story in Lorekeeper"
Cohesion: 0.05
Nodes (35): Lorekeeper agent skill, Create, connect and revise, Dates and uncertainty, Files you can keep, Import and export, Open Lorekeeper, Read a continuity report, Start a world from a terminal (+27 more)

### Community 10 - "item_dates"
Cohesion: 0.10
Nodes (34): compare_eq(), compare_ge(), _compare_shifted_eq(), _date_key(), flashback(), order_check(), possible(), Read-only, uncertainty-aware continuity checks over stored or in-memory items. (+26 more)

### Community 11 - "interop.py"
Cohesion: 0.09
Nodes (36): _aeon_date(), _ancestors(), _archive(), _calendar(), _check_shapes(), _collection(), _csv_date(), _csv_value() (+28 more)

### Community 12 - "timeline"
Cohesion: 0.13
Nodes (35): agesView(), byName(), chart(), dated(), events(), fit(), fitAll(), fuzzy() (+27 more)

### Community 14 - "ServerTests"
Cohesion: 0.08
Nodes (8): AppTestCase, CreateAndAIFileTests, LauncherTests, LaunchTests, The Lorekeeper app: world list, folder kinds, AI files and the start-screen serv, Run Open Lorekeeper.bat with a stand-in pyw/pythonw that records a launch instea, ServerTests, WorldListTests

### Community 15 - "Checks"
Cohesion: 0.20
Nodes (4): Checks, findings(), item(), project()

### Community 16 - "guard.py"
Cohesion: 0.13
Nodes (21): build(), do_compact(), do_post(), do_pre(), do_start(), emit(), git(), last_user_message() (+13 more)

### Community 17 - "el"
Cohesion: 0.23
Nodes (31): add(), addForm(), button(), chapterName(), chapterSelect(), chips(), chText(), citeBox() (+23 more)

### Community 18 - "McpTests"
Cohesion: 0.11
Nodes (6): McpTests, meta(), 2026-07-28 clients reject a tools/list result without ttlMs and cacheScope (0 to, The fact tools write the same bytes and return the same data through MCP and the, The planning tools return the same data through MCP and the CLI (reads on the fi, lore mcp --saga: planning-change is refused; planning-fact needs a planning fold

### Community 19 - "Feature 011: Planning wiki"
Cohesion: 0.07
Nodes (27): Design, Files, Plan: Feature 011, planning wiki, Risks, Saga integration (run-4 method), Technical context, AI use, Changing (+19 more)

### Community 20 - "enableRedate"
Cohesion: 0.21
Nodes (28): addFieldRow(), addLinkForm(), anyDirty(), api(), conflictActions(), convert(), dirty(), enableRedate() (+20 more)

### Community 21 - "Tasks: [FEATURE NAME]"
Cohesion: 0.07
Nodes (26): Dependencies & Execution Order, Format: `[ID] [P?] [Story] Description`, Implementation for User Story 1, Implementation for User Story 2, Implementation for User Story 3, Implementation Strategy, Incremental Delivery, MVP First (User Story 1 Only) (+18 more)

### Community 22 - "SKILL.md"
Cohesion: 0.08
Nodes (25): 1. Initialize Analysis Context, 2. Load Artifacts (Progressive Disclosure), 3. Build Semantic Models, 4. Detection Passes (Token-Efficient Analysis), 5. Severity Assignment, 6. Produce Compact Analysis Report, 7. Provide Next Actions, 8. Offer Remediation (+17 more)

### Community 23 - "SKILL.md"
Cohesion: 0.08
Nodes (25): 1. Initialize Analysis Context, 2. Load Artifacts (Progressive Disclosure), 3. Build Semantic Models, 4. Detection Passes (Token-Efficient Analysis), 5. Severity Assignment, 6. Produce Compact Analysis Report, 7. Provide Next Actions, 8. Offer Remediation (+17 more)

### Community 24 - "spreadsheet"
Cohesion: 0.14
Nodes (26): cellId(), changes(), display(), editableCell(), endKey(), fieldRow(), fieldsFor(), isDateKey() (+18 more)

### Community 25 - "Project"
Cohesion: 0.12
Nodes (6): Project, The story wiki and planning wiki folders, normcased: their pages are not items., A name, file stem or alias that two items claim: its links silently pick one of, _slurp(), The user's three saga Wikis are Lorekeeper projects as they stand (skipped where, SagaWikis

### Community 26 - "ops.py"
Cohesion: 0.12
Nodes (19): parse(), _check_link_version(), _events_of(), op_convert(), op_knows(), op_link(), op_planning_source(), op_requests() (+11 more)

### Community 27 - "atomic_write"
Cohesion: 0.15
Nodes (17): import_into(), Create new items only; skipped subjects and their existing files remain untouche, op_export(), op_request(), Queue a change request instead of editing (saga mode): the pipeline applies it l, Write the project as .aeon (Aeon Timeline), CSV (Aeon column ids) or one Markdow, atomic_write(), blank() (+9 more)

### Community 28 - "LoreError"
Cohesion: 0.15
Nodes (4): LoreError, Exception, SettingsTests, Review

### Community 29 - "lore"
Cohesion: 0.13
Nodes (6): CliFlows, InProcess, lore(), cli.main called directly, as the app and other Python callers do., Execute the published quickstart in a fresh, empty story folder., Readme

### Community 30 - "Aeon Timeline 3 file format and behaviour: clean-room notes for Lorekeeper interop"
Cohesion: 0.10
Nodes (20): 1.1 Header (40 bytes), 1.2 Root archive, 1.3 Leaf archives (`attachments`, `timeline`), 1.4 Writing, 1. Container (`.aeon`), 2.1 Shapes the loader accepts (observed), 2.2 v14 → v27 differences that matter to a reader, 2. Top-level JSON (+12 more)

### Community 31 - "Calendar"
Cohesion: 0.20
Nodes (10): add(), Calendar, calendars(), civil_from_days(), days_from_civil(), Hinnant's Gregorian day number, with 1970-01-01 at zero., span(), When (+2 more)

### Community 32 - "Item"
Cohesion: 0.16
Nodes (7): Item, AgelessPeople, Comparisons, OrderCheck, Certainty vectors for the public checks API; synthetic worlds stay in memory., No recorded death, yet older than anyone could be by the latest date in the stor, SecondLives

### Community 33 - "app.js"
Cohesion: 0.28
Nodes (16): aiNote(), ask(), busy(), button(), el(), folderName(), load(), opened() (+8 more)

### Community 34 - "Execution Steps"
Cohesion: 0.12
Nodes (15): 1. Initialize Convergence Context, 2. Load Artifacts (Progressive Disclosure), 3. Build the Intent Inventory, 4. Assess the Codebase and Classify Findings, 5. Assign Severity, 6. Present the In-Session Findings Summary, 7. Append Convergence Tasks (or report converged), 8. Provide Next Actions (Handoff) (+7 more)

### Community 35 - "Execution Steps"
Cohesion: 0.12
Nodes (15): 1. Initialize Convergence Context, 2. Load Artifacts (Progressive Disclosure), 3. Build the Intent Inventory, 4. Assess the Codebase and Classify Findings, 5. Assign Severity, 6. Present the In-Session Findings Summary, 7. Append Convergence Tasks (or report converged), 8. Provide Next Actions (Handoff) (+7 more)

### Community 36 - "common.ps1"
Cohesion: 0.23
Nodes (13): Find-SpecifyRoot(), Format-SpecKitCommand(), Get-CurrentBranch(), Get-FeaturePathsEnv(), Get-InvokeSeparator(), Get-NormalizedPriority(), Get-Python3Command(), Get-RepoRoot() (+5 more)

### Community 37 - "Feature 010: Progressive story wiki"
Cohesion: 0.12
Nodes (15): Checks, Clarifications, Editor, Feature 010: Progressive story wiki, Functional requirements, Later (not in this feature), Overview, Reading (+7 more)

### Community 38 - "store.py"
Cohesion: 0.15
Nodes (7): Lorekeeper: a plain-text story-world engine (CLI `lore`, MCP server, local edito, Loopback-only HTTP adapter over OPS and the bundled, build-free editor., Project loading, link resolution and safe writes for a folder of Markdown items., Small starter worlds as Python data, so vendoring needs no template directory., Regression checks for the feature-001 adversarial review findings., Real loopback requests against a disposable copy, never the fixture itself., Starter worlds, init compatibility, and packaging declarations.

### Community 39 - "mcp.py"
Cohesion: 0.21
Nodes (13): _error(), handle(), offered(), Small, stateless MCP adapter over the operations table (JSON lines on stdio)., Serve UTF-8 JSON lines on binary streams until EOF., In a saga, Wiki pages and authority documents change only through the saga's own, Return a response without transport I/O; tools delegate their effects to ops., serve() (+5 more)

### Community 41 - "cli.py"
Cohesion: 0.23
Nodes (12): build_parser(), chapters(), human(), interval(), key_value(), planning_text(), `lore` command line, generated from the operations table., Plain text for people; --json prints the data unchanged. (+4 more)

### Community 42 - "dates.py"
Cohesion: 0.22
Nodes (8): age(), Integer-minute dates, configured calendars, and uncertainty intervals., span_text(), card(), codes(), DayOverflow, Flashbacks, Flashbacks in ordered rules, day counts past a year's end, and second lives (reb

### Community 43 - "Feature 012: The Lorekeeper app"
Cohesion: 0.14
Nodes (13): AI instructions, Clarifications, Editor, Feature 012: The Lorekeeper app, Functional requirements, Out of scope, Overview, Safety (+5 more)

### Community 44 - "inside"
Cohesion: 0.18
Nodes (11): main(), op_init(), Run one operation. confine (MCP and the editor): import and export paths are rel, run(), to_json(), Hash metadata in configured roots, plus lore.json; skip excluded folders., serve(), stamp() (+3 more)

### Community 46 - "Core Principles"
Cohesion: 0.15
Nodes (12): Constraints, Core Principles, Development Workflow, Governance, I. Stdlib-only, vendorable core, II. Plain text is the source of truth, III. One operations table, three faces, IV. Never lose an edit (+4 more)

### Community 47 - "Feature Specification: [FEATURE NAME]"
Cohesion: 0.15
Nodes (12): Assumptions, Edge Cases, Feature Specification: [FEATURE NAME], Functional Requirements, Key Entities *(include if feature involves data)*, Measurable Outcomes, Requirements *(mandatory)*, Success Criteria *(mandatory)* (+4 more)

### Community 48 - "Design"
Cohesion: 0.15
Nodes (12): AI files, Constitution check, Design, Files, Folder kinds, Launch and install, Plan 012: The Lorekeeper app, Sagas (+4 more)

### Community 50 - "Core Principles"
Cohesion: 0.18
Nodes (10): Core Principles, Governance, [PRINCIPLE_1_NAME], [PRINCIPLE_2_NAME], [PRINCIPLE_3_NAME], [PRINCIPLE_4_NAME], [PRINCIPLE_5_NAME], [PROJECT_NAME] Constitution (+2 more)

### Community 51 - "Contracts"
Cohesion: 0.18
Nodes (10): cli.py, Contracts, Design decisions, File structure, fm.py, mcp.py, ops.py, Plan 001: core (+2 more)

### Community 52 - "Feature 001: Core model, storage, operations, CLI and MCP"
Cohesion: 0.18
Nodes (10): Defaults chosen (logged), Feature 001: Core model, storage, operations, CLI and MCP, Format, Functional requirements, Operations, Overview, Project, Safe writes (+2 more)

### Community 53 - "LocalHandler"
Cohesion: 0.28
Nodes (5): BaseHTTPRequestHandler, LocalHandler, The request body when it is 1 byte to `limit`; otherwise b"", after reading and, A loopback-only request handler: Host check, security headers and JSON error rep, read_body()

### Community 54 - "Implementation Plan: [FEATURE]"
Cohesion: 0.22
Nodes (8): Complexity Tracking, Constitution Check, Documentation (this feature), Implementation Plan: [FEATURE], Project Structure, Source Code (repository root), Summary, Technical Context

### Community 55 - "conversations.md"
Cohesion: 0.22
Nodes (8): A.1 Register schedule, §A.252 — The Bound (Dec 2048), §A.253 — Will Marsh Walks, §B.10 — Night Flight, Conversations, HOW TO DRAFT, PART A — SAVA AND EDRAN, PART B — NIGHT CREWS

### Community 57 - "SKILL.md"
Cohesion: 0.25
Nodes (7): Anti-Examples: What NOT To Do, Checklist Purpose: "Unit Tests for English", Example Checklist Types & Sample Items, Execution Steps, Post-Execution Checks, Pre-Execution Checks, User Input

### Community 58 - "SKILL.md"
Cohesion: 0.25
Nodes (7): Anti-Examples: What NOT To Do, Checklist Purpose: "Unit Tests for English", Example Checklist Types & Sample Items, Execution Steps, Post-Execution Checks, Pre-Execution Checks, User Input

### Community 59 - "relationships"
Cohesion: 0.39
Nodes (8): CATEGORIES, category(), relationships(), TIMING, typeChips(), typeInfo(), typePlural(), typeRank()

### Community 60 - "Lean Workflow"
Cohesion: 0.25
Nodes (7): Commands Included, Development, Installation, Lean Workflow, License, What It Replaces, When to Use

### Community 61 - "Tasks 010: Progressive story wiki"
Cohesion: 0.25
Nodes (7): Editor, Engine (TDD: test first, watch it fail, then code), Faces, Finish, Sagas (clones and probes under lk-scratch), Starter worlds and guides, Tasks 010: Progressive story wiki

### Community 62 - "test_rules.py"
Cohesion: 0.32
Nodes (3): Standing rules: stdlib only, explicit utf-8, one ops table behind every face., Rules, trees()

### Community 63 - "SKILL.md"
Cohesion: 0.29
Nodes (6): Completion Report, Done When, Mandatory Post-Execution Hooks, Outline, Pre-Execution Checks, User Input

### Community 64 - "SKILL.md"
Cohesion: 0.29
Nodes (6): Completion Report, Done When, Mandatory Post-Execution Hooks, Outline, Pre-Execution Checks, User Input

### Community 65 - "Overnight changes (2026-11-22 to 23)"
Cohesion: 0.29
Nodes (6): Changes, Found, not changed, How to merge and re-vendor, Other branches, Overnight changes (2026-11-22 to 23), Tests

### Community 66 - "Feature 013: A plain-language editor"
Cohesion: 0.29
Nodes (6): Clarifications, Feature 013: A plain-language editor, Functional requirements, Overview, Session 2026-10-19, Success criteria

### Community 67 - "Ivo Brandt.md"
Cohesion: 0.29
Nodes (4): born: circa only; no record survives, Ivo Brandt, Mara Quell, Tess Varga

### Community 69 - "fastest"
Cohesion: 0.38
Nodes (5): fastest(), Perf, n items: a third characters, a third places, a third events linking both., The best of a few timed runs: a busy machine slows one run, a real regression sl, synthetic()

### Community 70 - "selectItem"
Cohesion: 0.33
Nodes (6): markSelection(), narrow(), pickFind(), revealInView(), selectItem(), showStart()

### Community 71 - "make_server"
Cohesion: 0.33
Nodes (4): make_server(), load_config(), A project's lore.json, which must hold one JSON object., ThreadingHTTPServer

### Community 72 - "_open"
Cohesion: 0.40
Nodes (6): companion_path(), fact_end(), fact_remove(), _open(), (entry, path, text, sha) of an entry's story page; text is None when the page mu, _write()

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

### Community 79 - "1. Peoples"
Cohesion: 0.33
Nodes (5): 1.1 Vampires, 1.2 Humans, 1. Peoples, Canon inheritance rule, Fixture World Bible

### Community 80 - "Rules"
Cohesion: 0.33
Nodes (5): Chapter 1: Night Arrives, Chapter 2: The Scholar, Chapter 3: Sava Returns, Outline, Rules

### Community 81 - "test_saga_dates.py"
Cohesion: 0.40
Nodes (3): architecture(), Every chapter-card date in the three saga architectures parses (skipped where th, SagaCardDates

### Community 82 - "Speckit Constitution Skill"
Cohesion: 0.40
Nodes (4): Outline, Scope Guard, Speckit Constitution Skill, User Input

### Community 83 - "SKILL.md"
Cohesion: 0.40
Nodes (4): Outline, Post-Execution Checks, Pre-Execution Checks, User Input

### Community 84 - "Speckit Constitution Skill"
Cohesion: 0.40
Nodes (4): Outline, Scope Guard, Speckit Constitution Skill, User Input

### Community 85 - "SKILL.md"
Cohesion: 0.40
Nodes (4): Outline, Post-Execution Checks, Pre-Execution Checks, User Input

### Community 86 - "explain"
Cohesion: 0.50
Nodes (5): explain(), findingText(), lagWords(), plainText(), unlink()

### Community 87 - "[CHECKLIST TYPE] Checklist: [FEATURE NAME]"
Cohesion: 0.40
Nodes (4): [Category 1], [Category 2], [CHECKLIST TYPE] Checklist: [FEATURE NAME], Notes

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

### Community 100 - "Speckit Implement Skill"
Cohesion: 0.50
Nodes (3): Outline, Speckit Implement Skill, User Input

### Community 101 - "Speckit Plan Skill"
Cohesion: 0.50
Nodes (3): Outline, Speckit Plan Skill, User Input

### Community 102 - "Speckit Specify Skill"
Cohesion: 0.50
Nodes (3): Outline, Speckit Specify Skill, User Input

### Community 103 - "Speckit Tasks Skill"
Cohesion: 0.50
Nodes (3): Outline, Speckit Tasks Skill, User Input

### Community 104 - "speckit.constitution.md"
Cohesion: 0.50
Nodes (3): Outline, Scope Guard, User Input

### Community 105 - "Feature 007: Templates, onboarding, packaging"
Cohesion: 0.50
Nodes (3): Feature 007: Templates, onboarding, packaging, Functional requirements, Success criteria

### Community 106 - "Plot ideas"
Cohesion: 0.50
Nodes (3): 4.12 Sava betrays the Bound, 4.13 Weather, Plot ideas

### Community 107 - "Human Override Register"
Cohesion: 0.50
Nodes (3): EXAMPLE ENTRY — ILLUSTRATION ONLY, Human Override Register, Register

### Community 108 - "Sava"
Cohesion: 0.50
Nodes (3): Ideas, Identity, Sava

## Knowledge Gaps
- **441 isolated node(s):** `state`, `token`, `calendars`, `worldName`, `MONTHS` (+436 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **36 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `LoreError` connect `LoreError` to `planning.py`, `run`, `wiki.py`, `app.py`, `run`, `item_dates`, `interop.py`, `McpTests`, `Project`, `ops.py`, `atomic_write`, `store.py`, `mcp.py`, `Writing`, `cli.py`, `inside`, `Loading`, `AuditFixes`, `LocalHandler`, `TimeOps`, `make_server`, `_open`?**
  _High betweenness centrality (0.106) - this node is a cross-community bridge._
- **Why does `Project` connect `Project` to `Item`, `app.py`, `fastest`, `store.py`, `make_server`, `Writing`, `dates.py`, `inside`, `Loading`, `ServeTests`, `Checks`, `AuditFixes`, `ops.py`, `atomic_write`, `LoreError`?**
  _High betweenness centrality (0.047) - this node is a cross-community bridge._
- **Why does `run()` connect `item_dates` to `wiki.py`, `app.py`, `dates.py`, `Checks`, `guard.py`?**
  _High betweenness centrality (0.020) - this node is a cross-community bridge._
- **Are the 83 inferred relationships involving `LoreError` (e.g. with `App` and `.open_world()`) actually correct?**
  _`LoreError` has 83 INFERRED edges - model-reasoned connections that need verification._
- **Are the 15 inferred relationships involving `Project` (e.g. with `AgelessPeople` and `Checks`) actually correct?**
  _`Project` has 15 INFERRED edges - model-reasoned connections that need verification._
- **What connects `state`, `token`, `calendars` to the rest of the system?**
  _441 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `planning.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06468797564687975 - nodes in this community are weakly interconnected._