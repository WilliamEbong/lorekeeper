# BUILD NOTES — Lorekeeper (research and saga seams; superseded as a handoff by HANDOFF.md)

**Last updated:** 2026-10-18, end of session 2. **The build is complete.**
**Where things are:**
- **Code:** `Documents\Lorekeeper`. Private repo: https://github.com/WilliamEbong/lorekeeper (visibility PRIVATE). Install with `uv tool install .`, which gives `lore`.
- **Sagas:** chronology is integrated in warn mode. Live HEADs: Realm efd585f, Space ffedb64, Zombies 82a1536.
  - Config: `_system/lorekeeper.json`.
  - Engine: `_system/vendor/lorekeeper/` (VERSION eb20b30; Lorekeeper dc9207a differs only by a load-speed change).
  - Reports: `_system/knowledge/chronology_report.md`.
  - Deferred roster keys: `_system/knowledge/chronology_deferred.md`.
  - Commands: `saga.py chrono N`, `chrono-report`, `timeline`, `timeline-requests`.
- **Verification evidence:** see SESSION-LOG.
  - Lorekeeper: 190 tests OK.
  - Saga suites green (219/216/211, parity included).
  - All 26 status/validate outputs are identical to the pre-integration baseline.
  - The Playwright editor flows passed (SC-1..SC-4).
  - `uv tool install` works.
  - MCP golden test passes.
  - All 19 Aeon templates import.
**Not done or unverified:**
- Opening a Lorekeeper-written .aeon file in the Aeon desktop app: access was declined twice. The sample is at `C:\Users\Owner\lk-scratch\aeon_out`.
**Later list:**
- Re-vendor the engine into the sagas at the next update (perf only).
- Apply `chronology_deferred.md` as each in-progress chapter freezes.
- The user decides on fail mode.
- Optional saga rules: Realm's "paired cards 7 days apart" has no structured pairing data yet.
**Continuity kit:** retired. `docs/build/ACTIVE` is removed and the hooks are unregistered from `.claude/settings.json`. `tools/build-hooks/guard.py` is kept for reuse.
**Read order for any new or resumed session:** this file → `BUILD-PLAN.md` (plan + checklist) → the tail of `SESSION-LOG.md`.

---

## 1. What we are building and why

**Lorekeeper** (CLI `lore`) is a standalone, AI-native story-world engine inspired by Aeon Timeline. It has two jobs:

1. **Product.** It is usable by three groups:
   - writers who draft with AI agents (Claude Code, Codex)
   - novelists who don't use AI
   - worldbuilders and game masters

   It provides:
   - plain-text storage (Markdown + frontmatter, Obsidian-compatible)
   - a CLI and an MCP server
   - consistency checks Aeon lacks
   - an interactive local editor
   - `.aeon`, CSV and Markdown interop
2. **First clients: the user's three sagas** in `C:\Users\Owner\OneDrive\Documents\Creative writing\` (Realm Saga, Space saga, Zombies saga). Today their chronology lives only in prose: no ages, no who-was-where, no date validation. The integration has to improve their AI-driven chapter pipeline.

### Locked user decisions

| Topic | Decision |
|---|---|
| Name | Lorekeeper, with the CLI command `lore`. |
| v1 human UI | An interactive editor: create, edit, link and drag, Aeon-like. Read-only views are not enough. |
| Audience | All three groups above. |
| Hand edits inside a saga | They become a **change request**: queued, then applied by agents through the pipeline with impact checks. They never mutate canon directly. |
| Canon gaps (e.g. a birthdate canon never states) | Agents **decide and record** the value in the saga's `_system/knowledge/agent_decisions.md`, the same rule as invented names. The user can override. |
| Publishing | A **private GitHub repo** at the end, created with `gh repo create --private` and pushed. Nothing public. No other pushes. |
| Aeon EULA | The user stated they are allowed to reverse engineer Aeon. Do not raise the EULA again. |
| Process | Build autonomously and make the judgement calls yourself. Use Spec Kit, Ponytail, the REA MCP/CLI, Codex (it can take many tasks), computer use and Playwright. Stop only when done. |
| Continuity | Keep BUILD-PLAN, SESSION-LOG and HANDOFF current. Write the handoff at 94% context. All three are read after a compaction or any restart. |

### The user (how to work with them)

- They direct creatively in natural language. They do not read or maintain code, JSON or git.
- Their standing rules are in `~/.claude/CLAUDE.md`:
  - **Playwright** for all browser verification.
  - **context7** before writing code against an external library.
  - **WebFetch** before fcrawl.
  - **Spec Kit** for new apps.
  - **Ponytail** outranks ECC.
  - Surface assumptions by logging them, then proceed.
- Persisted docs and commits use normal prose, not caveman style.

---

## 2. Aeon Timeline: what REA and static analysis established

- **Install:** `C:\Users\Owner\OneDrive\Documents\aeon timelin RE\Aeon Timeline\AeonTimeline.exe`
  - Version 3.5.123, released 16 Sep 2026; app fileVersion 27.
  - SHA-256 `d985701dd1dc49ea06eab3bd67c2f761de0641ec717fc1ef73aae3ccc72264e4`.
  - The installer is in the parent folder.
- **Architecture:** the exe is about 2 MB of native code (a CEF launcher; `libcef.dll`) wrapping a React/Redux web app.
  - The web app and its assets are stored in PE resources of **custom type 256**, as **concatenated zlib streams**, followed by a small index.
  - `tools/aeon_extract.py` re-extracts them. It hardcodes the resource offsets for this exe hash; if the hash differs, get fresh offsets from the REA tool `inspect_pe_resources`.
  - Resource 3000, stream 0003 = `main.js` (19 MB)
  - Resource 3000, stream 0002 = `ReducerWorker.worker.js`
  - Resource 3000, stream 0009 = English UI strings JSON (148 top-level keys)
  - Resource 3000, stream 0012 = `{appVersion 3.5.123, fileVersion 27}`
  - Resource 3001 = a near-duplicate of 3000
  - Resource 3002 = the licensing/trial/purchase window (FastSpring), not useful
  - Resource 3003 = 17 built-in templates as real `.aeon` files: Murder on the Orient Express, History of Inventions, Wuthering Heights, Story Planning, Project Planning, Historical Research, Case Documentation, Historic Timeline ×3, Legal Case ×2, Project Management ×3, Novel ×2, Science Fiction. Plus a .docx attachment sample.
  - Resource 3004 = a sample with a jpg and a pdf attachment, plus two template-definition JSONs
  - Resources 4000–4020 = fonts
- **Native/JS boundary:** the JS talks to native code through `window.CefContainerInterface` / `nativeBroadcast:*` messages, e.g. `PUSH_DATA_TO_NATIVE`, `EXPORT_DATA_DOCX`, `EXPORT_DATA_MARKDOWN`. **The `.aeon` container is read and written by native code** (exe strings near offset 1904392: `blockIdentifier`, `fileIdentifier`, `timeline3.json`, `aeonEmbedded://`). The JSON model lives in JS.

### `.aeon` container (decoded; checked arithmetically on 4 files)

All fields are little-endian.

- **Overall layout:** each archive is `[payloads][index][40-byte header]`, read from the **end** of the file.
- **Header fields:**

  | Offset | Type | Meaning |
  |---|---|---|
  | +0 | u32 | version: 1 or 2 |
  | +4 | u32 | header size (0x28) |
  | +8 | u64 | index size |
  | +16 | u32 | entry count |
  | +20 | 20 bytes | fixed signature: `33333333`, then `1111111111111111`, then `2222222222222222` (v1) or ASCII `HDJDJZWQ` (v2) |

  The signature is a type marker, not a hash.
- **Nesting:** a file is a root archive with two child archives, `attachments` and `timeline`.
- **Root index entry:** u64 offset, u64 size, u64 0, u64 0, u32 name length, name.
- **Leaf index entry:**
  - u64 offset (relative to its archive) and u64 size
  - 28 extra bytes: zero in v1; in v2 there is a u64 at entry+28 equal to the size, probably an uncompressed size
  - u32 id length, u32 name length, then the id and the name
  - The timeline leaf has id `timeline3.json` and an empty name. Attachments have a GUID/short id plus the original filename.
- **Worked example (template "Story Planning", resource 3003, stream 0004):**
  - The empty attachments archive takes 40 bytes, so the JSON starts at 0x28.
  - The JSON length is 0x17d9d, including the final `\n`.
  - Then come the timeline index (66 bytes), timeline header, root index (91 bytes) and root header, for a 238-byte trailer in total.
- **Writability:** no encryption, checksum or signature was found. A third party should be able to write v1 files by copying the template layout. **Untested.** Phase 2, feature 007 must round-trip a file and open it in Aeon via computer use.

### Data model (the template JSON: `core.definitions` and `core.data`)

**Top level:** `fileVersion`, `core{coreFileVersion, definitions, data, templateDetails{category,name}, projectId}`, `collection`, `sync` (Scrivener/Ulysses state), `appState` (open views), `printOptions`, `activeTutorialPath`.

**`definitions`**

- **`calendar`:**
  - `eras[{name, shortName, isBackwards, hasLeapYears, leapOffset, duration}]`
  - `months[{name, shortName, normalDuration, leapDuration}]`
  - `weekdays[{name, shortName}]`
  - `leapCycles` (Gregorian `[4,100,400]`)
  - `hoursInDay`, `weekdayIndexAtZero`, `zeroDateTimestamp`
  - `dateFormat`, `timeFormat`, `dateOrder`, `calendarType`, `maxPrecision`
- **`types.byId[...]`:**
  - `id`, `label`, `pluralLabel`, `identifierPrefix` (EV, PER, LOC…)
  - `references{roleId:true}`, `properties{propId:true}`
  - `superTypes`, `canHaveDate`, `canIncludeInNarrative`, `isNarrativeFolder`
  - `showOnSidebar`, `showAsColumn`, `compactDisplay`, `category` (PERSON/LOCATION/OTHER), `icon`, `defaultItemColor`
  - Default types: defaultEvent, flashback, backstory, defaultPerson, characterGroup, defaultLocation, storyArc, defaultNarrative, genericNode (mindmap).
- **`properties.byId[...]`:** `{id, label, format: text|multitext|list|percentage|number|checkbox|date, allowed{...} for lists, multiple, autoCalculate, autoCalculateType, indicateItemCompletion}`
- **`references.byId[...]`:**
  - Fields: `{id, label, types{allowed}, icon, color, lineStyle, bidirectional, inverseLabel, showInverse, showInInspector}`.
  - Defaults: participant, causes / "Caused by", instigates / "Instigated by", storyArc, location, birthplace, home, family, friend, rival, parent / "Child", sibling, relatesTo.
- **`narrativeSettings`:** labels Part, Chapter, Prologue, Epilogue, Scene, Passage; `autoForFolder` / `autoForOther`; `numbering` is `OUTLINE_STYLE` or `CONTINUOUS_STYLE`.
- Also: `colors`, `autoAdjustLevel`, `autoAdjustBackwardsLimit`, `defaultColumns`.

**`data`**

- `itemsById{id, type, displayId, label, summary, color, tags, propertyValues, links, attachments, image, internalId}`
- `itemOrderByType`
- `itemDatesById{startDate, endDate, duration, preferred*, ongoing, isDateLocked, latestStartDate, earliestEndDate, preferredPrecision}`
  - Each date is `{era, year, month, day, hour, minute, second, timestamp, weekday, precision}`.
- `superAndChildOrderById` (nesting)
- `relationshipsById{id, subject, reference, object}` (the triples)
- `mindmaps`
- `narrative{sacOrderById: tree of super/childOrder}`
- `sequenceOrder` (chronological order)
- `tags`, `calendarMarkers` (recurring anniversaries), `savedFiltersById`
- `dependenciesById{id, subject, object, dependencyType: FS|SS|FF|SF}`
- `dateConstraintsById`, `attachmentsById`, `timelineRange`, `lastTodayDate`

### Behaviours (from `main.js`; offsets are byte offsets into stream 3000/0003)

- **Precision enum:** −1 Auto, 0 Century, 1 Decade, 2 Year, 3 Month, 4 Week, 5 Day, 6 Hour, 7 Minute, 8 Second.
  - Default `maxPrecision` is Second; templates use 6.
- **calendarType:** 0 DateTime, 1 WeekdayTime ("Week count"), 2 DayTime ("Day count"), 3 HourTime ("Timestamp").
- **Leap test (@~4789956):** walk `leapCycles` from last to first. If `year % cycle == leapOffset`, the year is a leap year when the cycle index is even, and not one when it is odd.
  - BC uses `leapOffset` 1; AD uses 0.
- **Timestamp:**
  - Value is in seconds. 0 = year 1, month 1, day 1, 00:00 of the **last** era.
  - Earlier eras subtract `daysInEra`. Backwards eras count in reverse.
  - `zeroDateTimestamp` anchors Day 0 / Week 0 for relative calendars.
- **Age rule (@17462829):**
  - If the person has ended and their end ≤ the event start: "X since end".
  - Else if the event is before the person's start: "X before start".
  - Otherwise: the span from person start to event start, computed greedily as y, m, w, d, h, min, s and shown as at most 2 units ("32 years, 4 months").
  - Precision is ignored, so a year-only birth counts from 1 January.
  - Anniversaries are drawn yearly and stop at the end unless `extendAnniversaryBeyondEnd`.
- **Constraints:** `{constraintType Relative|Date|DatePart, subject, subjectTarget Start|End, object, objectTarget, comparison Before|After|Equal, date, offset, partPrecision, partValue}`.
  - Resolution is MoveSelf or MoveOther.
- **autoAdjustLevel:** 0 Off, 1 AdjustSelf, 2 MoveChildren, 3 ResolveConstraints (the default).
  - `autoAdjustBackwardsLimit` is Off, Today, Tomorrow, NextWeek or NextMonth, relative to `lastTodayDate`.
- **Solver:**
  - `f6` (@13542105) gathers bounds from Equal, Before/After and dependencies. On conflict it stays put; otherwise it clamps.
  - `L6` (@13550300) propagates through a worklist with a visited set.
  - Outer loop: at most 5 passes while violations remain.
  - The worker tracks `violatedDateConstraints`, `violatedDependencies` and `violatedItems`.
- **No "person in two places" check exists.** "conflict" refers only to sync and file conflicts.
- **Narrative numbering:**
  - "automatic" label = the next eligible label after the parent's in `sortOrder`.
  - Outline style is "Label 1.2.3"; continuous style keeps one depth-first counter per label.
- **Views:** TIMELINE, RELATIONSHIP, NARRATIVE, MINDMAP, SPREADSHEET, OUTLINE, SUBWAY (split / subway / showall), LIST, ENTITY_LIST. Each runs in Chronological or Narrative mode.
- **CSV column ids (@15028987):** label, type, color, startDate, endDate, duration, durationToStartOfEndDate, ongoing, summary, tags, super, internalId, compactDisplay, latestStartDate, earliestEndDate, links, image, displayId, initials, shortLabel, sequence, narrativePosition, narrativeSection, blockedBy, blocks, dateConstraints, attachments, mindmaps, dateLocked.
- **Migration chain:** v14 → v27 (`cX` @5230795). The <28 cleanup step runs on every load.
- **Public context (web research):**
  - Aeon has one calendar per file, and the calendar can't be edited once dated items exist.
  - There is no API or plugin system, and no Markdown round-trip.
  - Scrivener/Ulysses sync is metadata-only.
  - Price is $65 with 12 months of updates.
  - Writers value most: ages at events, narrative order separate from chronology, Subway view, dependency warnings.
  - Complaints: learning curve, single calendar, fiddly sync.
  - Community tools by peter88213 (aeon3yw, aeon3md, aeon3obsidian) once read v3 JSON.

---

## 3. The three sagas: integration seams

Each saga is its own git repo (`main`, no remote) and runs a **byte-identical** stdlib-Python engine. `R` = `...\Creative writing\Realm Saga\`. The facts below were verified in Realm and hold for all three.

### Hard constraints

- Stdlib only.
- **No script reads anything outside its own repo root**, so Lorekeeper must be **vendored** into each repo (`maintenance_agents.md:60`).
- No vector, embedding or graph databases (`PIPELINE.md:372`).
- Engine changes are committed as **`system:`** and never ride along with chapter freezes.
- Never delete; archive instead.
- Authorities (bibles, the 500-card architecture) are read-only.
- No draft-derived fact reaches the Wiki or ledgers before approval.

### Parity

- `_system/tests/test_engine_parity.py:15` has an explicit `SHARED_FILES` list:
  - scripts: `fsio, wb, cards, refs, state, profiles, saga`
  - tests: `__init__, fixture, test_pipeline, test_integration, test_profiles, test_scoped_freeze, test_source_refresh, test_refs, test_docs, test_engine_parity`
  - plus `PIPELINE.md` and `CRAFT_RULES.md`
- `SHARED_GLOBS` (`:27`) covers `_system/roles/*.md`, `_system/skills/*.md` and `Wiki/_TEMPLATES/*.md`.
- New scripts or vendored files must be added to `SHARED_FILES` and copied identically into all three repos.
- `test_docs.py` enforces genericity in shared files (no `HO-\d+`, no saga-specific terms, no word-cap literals) and requires `skills/README.md` to list every skill.

### Running tests

From the repo root: `python -m unittest discover -s _system/tests` (pytest also works). Python is 3.14.3.

### Pipeline stages

Defined in `state.py:41` `STAGES`:

NOT_STARTED → **SOURCE_ASSEMBLY** → MAJOR_BEATS → DETAILED_PLOT → DESCRIPTION → CHARACTERIZATION → DIALOGUE → BASIC_SYNTHESIS → BASIC_REVIEW → BASIC_REPAIR → **BASIC_VERIFICATION** → WORD_TARGET → PROSE_DRAFT → PROSE_REVIEW → PROSE_REVISION → FIDELITY_CHECK → FIDELITY_REPAIR → **FINAL_CONSISTENCY** (canon, chronology, knowledge…) → FINAL_REPAIR → READY_FOR_HUMAN → HUMAN_REVIEW → HUMAN_REVISION → **FINAL_REVALIDATION** → FINALIZATION → CURRENT_WB_UPDATE → **WIKI_AND_LEDGER_UPDATE** → GIT_COMMIT → FROZEN → COMPLETE.

### `saga.py` seams

- `build_parser()` at `:1599`, using the pattern `p = sub.add_parser("x"); p.add_argument(...); p.set_defaults(func=cmd_x)`.
- `cmd_validate` (`:533–635`) emits `FAIL <CODE> <detail>` lines; exit code is 1 on any FAIL.
- `cmd_health` is at `:1501`.
- `READY_CONTRACT` is at `:667`.
- `REQUIRED_SECTIONS_V2` is at `:739`.
- `freeze` (`:1018`) does `git add` + `git commit -m "chapter: …"` and refuses staged paths outside its scope.
- `_git()` is at `:191`.
- Manifest helpers live in `fsio.py`: `repo_root` `:27`, `load_manifest` `:49`, `rpath` `:61`, `atomic_write` `:66` (with an OneDrive retry), `read_json`/`write_json`, `sha256_file`, `append_log`.

### Template for a feature-gated module: `profiles.py`

- `enabled()` `:20` — true when the manifest has the key.
- `applies(n)` `:25`.
- `assemble(n)` `:270` — writes `RT/context/profiles.md` plus a sha256 receipt `RT/profile_packet.json`.
- `verify(n)` `:279`.
- `gate(n, stage, completing)` `:410` — called from `state.py:346` (`_enter`) and `state.py:383` (`complete_stage`).
- `verify_updates(n)` `:350` — at WIKI_AND_LEDGER_UPDATE, requires each touched Wiki page to have `last_updated_after_chapter == CH###` and a non-empty `## Current state`.
- `profile_metadata()` `:69` parses frontmatter with a regex: flat `key: value` lines only, and `tags` must be an inline `[a, b]` list. Keep any new frontmatter keys flat and inline-list, or the saga parser breaks.
- `wiki_characters()` `:138` walks `dirs.wiki` recursively.

### Existing chronology data

- **Card `Date` fields:** `cards.py:90` stores them as raw strings, and nothing parses dates anywhere today. Formats:
  - Realm: `**Date:** November 20, 2036`
  - Space: `**Date:** SRD Y0 D004 (PROVISIONAL production calendar)` / `SRD Y-6 D204 (sanctioned prelude…)`. The SRD is a naive 365-day year; HO-079 fixes `Y0 = 6842 CE`; datelines read `6842 CE, Day 004, 20:33`. Rails are the `Primary allocation` field and must never regress.
  - Zombies: `**Date/era:** March 3, 2071, approximately 5:40 a.m.` (default schema, no `card_schema` in its manifest).
- **`refs.pointers_document`** (`:394–415`) already emits `## Chronology anchor`: the raw card date plus `refs.anchors` table rows. Realm uses §73, a year/chapter anchor table.
- **`signatures.json`** holds `{chapter, title, date, pov[], location, …}` per approved chapter. Date formats are inconsistent across sagas.
- **Wiki** (Obsidian-style; Realm uses subfolders, Space and Zombies are flat):
  - Character pages have frontmatter `id/type/canonical_name/first_appearance/last_updated_after_chapter/tags` and **no birthdate**.
  - Event pages keep the date only in the filename and prose (e.g. `Events/First contact, 20 November 2036.md`, with timestamped bullets).
- **Rules to encode:**
  - Realm (World Bible §0.9): a duel never spans more than one day; death→Return is exactly 7 days; paired cards sit 7 days apart.
  - Space archived validator (`Space saga/_archive/_tools/validate_architecture.py`): regex `SRD Y(-?\d+) D(\d{3})`, ordinal `year*365+day`, `FAIL DATE_UNPARSED`, `FAIL RAIL_REGRESSION`.
- **Prior unbuilt design** worth reusing: `Zombies saga/_archive/old/Worldbuilding_Management_System_Design_Architecture_v1.1.md`. It covers typed entity IDs, atomic Fact IDs with effective date ranges, a Historical Event Ledger, reveal plan/actual, knowledge-state per POV, and mutability (LOCKED/COMMITTED/PROVISIONAL/OPEN).

### Live state on 2026-10-17 (do not disturb)

| Saga | Frozen | In progress |
|---|---|---|
| Realm | CH001–003 | CH004 at READY_FOR_HUMAN |
| Space | CH001–004 | CH005 at READY_FOR_HUMAN |
| Zombies | CH001–003 | CH004 mid-pipeline |

- Each repo has untracked `Chapters/CH00N/` and `_system/state/CH00N.json` files, plus a modified `_system/logs/saga.log`. **Never stage these.**
- Commit prefixes in use: `chapter:` / `canon:` / `wiki:` / `knowledge:` / `system:` / `fix:` / `chore:`.

---

## 4. Tools and environment

| Tool | Version / location | Notes |
|---|---|---|
| OS | Windows 10 | Bash (Git Bash) and PowerShell both available. CLIs start slowly under Git Bash (`rea` can take 60 s+), so give generous timeouts. |
| Python | 3.14.3 (only interpreter) | |
| node / npm | 24.14.1 / 11.11.0 | |
| git / gh | 2.48.1 / 2.93.0 | |
| uv | 0.11.29 | |
| claude | 2.1.284 | Model `claude-opus-5[1m]` (1M window). `ECC_CONTEXT_WINDOW_TOKENS=1000000` is in `~/.claude/settings.json` env. |
| Spec Kit | `specify` 1.0.13 at `~\.local\bin\specify.exe` | `lean` preset available. Skills after init: speckit-constitution / specify / plan / tasks / implement / converge / analyze / clarify / checklist / taskstoissues. Example projects: `Documents\VisualAtlas`, `Documents\The Autodidacts Eye`. |
| REA | 6.5.0 (`rea` CLI + `mcp__rea__*` tools) | Ghidra 12.1.4 at `C:\Users\Owner\tools\ghidra_12.1.4_PUBLIC`, JDK 21. Also registered for Codex. |
| Codex | CLI 0.160.0, model `gpt-6-astra` | Claude plugin `codex@openai-codex` 1.0.6, locally patched. Hand off with `Agent(subagent_type: "codex:codex-rescue")`; its Bash runs `codex-companion.mjs task [--background] [--write] -- '<prompt>'`. `--write` = danger-full-access, which the user approved by asking to loop Codex in. Briefs must be self-contained. Codex auto-reads `AGENTS.md`. |
| Playwright MCP | | Use for all browser verification (user rule). |
| Computer-use MCP | | Use for the Aeon desktop app (CEF window). |
| context7 MCP | | Library docs. |
| Installed pip packages | click, PyYAML, pytest, rich, typer, httpx | No mcp, jinja2 or pydantic. Lorekeeper core stays stdlib-only anyway. |
| Existing user hooks | `~/.claude/settings.json` | ECC SessionStart / PreCompact / Stop / SessionEnd, plus a codex-patch SessionStart. **Add, don't replace.** |

### Claude Code hook facts (from the docs)

- **PreCompact** (matchers `manual`/`auto`): can block (exit 2), but **cannot add context**.
- **SessionStart** (matchers `startup`/`resume`/`clear`/`compact`/`fork`): injects stdout or `additionalContext`, capped at 10,000 chars.
- **PostToolUse** and **Stop** support `additionalContext`.
- The transcript JSONL carries per-message `usage` (input + cache_creation + cache_read).
- `CLAUDE_AUTOCOMPACT_PCT_OVERRIDE` can only **lower** the threshold.
- The statusline JSON has `context_window.used_percentage`.

---

## 5. Next steps (in order)

1. Run the KICKOFF-PROMPT flow. Read the three docs and re-validate the plan against the actual repo state.
2. Phase 0: git init, Spec Kit, constitution, continuity hooks, the ACTIVE marker.
3. Phase 1: write AEON-SPEC.md. The scratch extraction from session 1 is gone, so re-run `tools/aeon_extract.py`.
4. Phase 2: features 001 → 008, in this order: 001 core, 002 time, 003 checks, 004 CLI + MCP, 005 saga integration, 006 editor, 007 interop, 008 packaging + private repo.

## 6. Open items / risks

- **`.aeon` writer is unproven.** It must be validated by opening our output in Aeon (computer use). Aeon may show a trial or registration screen: never enter credentials, and use read-only or trial mode.
- **Default auto-compact threshold is unknown.** Measure it in Phase 0 and set the guard below it if needed.
- **The design review did report in, at the very end of session 1.** Its 14 amendments are in BUILD-PLAN.md under "Design-review amendments", and **they supersede the plan text**. They cover:
  - feature renumbering 001–007, with the CLI and MCP folded into core
  - storage that follows the saga Wiki convention
  - `lore.json` instead of TOML
  - no `datetime`; integer minutes on a shared axis
  - uncertainty-aware FAIL/WARN
  - editor security and plain vanilla JS
  - saga work done in clones under `C:\Users\Owner\lk-scratch`, landed with a fast-forward merge
  - project-scoped hooks driven by one `guard.py`
  - Codex guardrails

  Locked user decisions still win where they conflict: backfill runs autonomously, and the run ends with a private GitHub push.
- **Start the build session with `Documents\Lorekeeper` as its working folder** so the project-scoped hooks load. The KICKOFF-PROMPT says this too.
- **OneDrive sync.** The repo lives under OneDrive, and `fsio.atomic_write` in the sagas retries once for OneDrive locks. Do the same in Lorekeeper.
