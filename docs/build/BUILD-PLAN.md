# Plan: Lorekeeper (`lore`), an AI-native story-world engine inspired by Aeon, built autonomously and integrated into 3 sagas

> **Consolidated 2026-10-18 (session 2).** The 14 design-review amendments from session 1 are now merged into the body below; nothing supersedes anything else any more. The re-validation fixes are marked "(re-validated)". The amendments are kept, numbered, at the end as a record. The progress checklist is at the bottom.

## Context
- **The problem.** The user writes three 500-chapter sagas: Realm, Space and Zombies.
  - An autonomous AI pipeline, `saga.py`, produces them. It is a stdlib engine that is byte-identical across three git repos under `Documents\Creative writing\`.
  - Chronology, people, places and relationships live only in prose and Markdown tables. Nothing computes ages, checks who was where, or validates dates.
- **What REA established about Aeon Timeline 3.5.123** is in HANDOFF §2. In short:
  - It is a CEF launcher around a React/Redux app.
  - The data model is typed items with reference-role triples, typed properties, calendars with eras, months and leap cycles, precision levels, item dates, a narrative tree, dependencies, constraints, and an age rule.
  - The `.aeon` container is little-endian, with nested archives and no encryption or checksum.
  - Aeon has no "one person in two places" check, no multiple calendars, no plain-text storage and no API.
- **The goal.** Build **Lorekeeper** (CLI `lore`), a standalone product for writers drafting with AI agents, novelists who don't use AI, and worldbuilders/GMs. It provides:
  - plain-text storage that humans, Obsidian and agents can all read
  - a CLI and an MCP server
  - checks that Aeon lacks
  - an interactive editor in v1
  - `.aeon`, CSV and Markdown interop

  Then integrate it into all three sagas.

## Locked user decisions
| Topic | Decision |
|---|---|
| Name | Lorekeeper, CLI `lore` |
| v1 human UI | Interactive editor: create, edit, link, drag |
| Audience | AI-agent writers, novelists without AI, worldbuilders/GMs |
| Human edits in a saga | Become a **change request**, applied by agents through the pipeline with impact checks. They never mutate canon directly. |
| Canon gaps (e.g. birthdates) | Agents **decide and record** them in `agent_decisions.md`. The user can override. |
| Publishing | **Private GitHub repo** at the end, via `gh`. Nothing public. |
| Aeon EULA | The user is allowed to reverse engineer it. Do not raise it again. |
| Process | Spec Kit + Ponytail + REA + Codex + computer use + Playwright. Autonomous: Claude makes judgement calls and stops only when done. |

## Architecture decisions (from the design review)
- **Storage = the saga Wiki convention.**
  - One Markdown file per item (events included), with frontmatter `id`, `type`, `canonical_name` and flat `[a-z_]+` keys.
  - Values are scalars or inline lists only. Links are quoted: `"[[X]]"`.
  - A saga Wiki is therefore a Lorekeeper store natively, with no translation layer.
  - The saga parser (`profiles.profile_metadata`) depends on this flat shape, so no nested YAML.
- **Dates** are written the way they are known, and precision comes from how they are written (`2036-11` means the whole month).
  - Optional `date_min` / `date_max`.
  - Dependencies: `after` (FS), `same_start` (SS), `same_end` (FF), `sf`, each with an optional lag (`"[[X]] +2h"`).
  - `status`: locked | committed | provisional | open. Provisional items produce WARN only.
  - A reference is stored once, on its subject. Inverses are computed at load time.
  - Narrative order lives in `narrative.md`, a nested outline of wikilinks. Saga mode uses chapter numbers instead.
  - Knowledge state: `learns: ["[[A]]"]` on events, plus `lore knows A --at DATE`.
- **Project config = `lore.json`**, not TOML. `tomllib` can't write, and the editor edits the schema. This matches `PROJECT_MANIFEST.json`.
- **One ops table** drives the CLI, the MCP server and the HTTP API. Every capability is reachable from all three.
- **Time: no `datetime`.**
  - Integer minutes on one shared axis. Gregorian conversion uses Hinnant's days-from-civil.
  - Each calendar is either months/eras or day-count years, plus an epoch offset and format regexes with named groups.
  - Parsing tries the project's calendars in order.
- **Checks are uncertainty-aware.** A definite violation is FAIL; a merely possible one is WARN.
  - Output lines follow saga style, `FAIL <CODE> <detail>` / `WARN ...`, and the exit code is 1 on any FAIL.
  - v1 has no travel-time model and no auto-rescheduling solver: checks only.
- **Stdlib-only everywhere in Lorekeeper:**
  - argparse; no typer, rich or click.
  - Every `open()` passes `encoding="utf-8"` (a test greps for bare `open(` calls).
  - Read with `newline=""` and keep each file's own line-ending style.
  - Atomic writes with one OneDrive retry, like saga `fsio.atomic_write`.
  - Skip `~$*` and `*.tmp`. Report OneDrive conflict copies as `FAIL DUPLICATE_ID`.
  - Slugs are short and unique case-insensitively.
- **Concurrent edits.**
  - Every read returns the file's sha256 as its version; every write carries the version it was based on.
  - If the file changed and the edited keys don't overlap, three-way merge the flat dicts. Otherwise return 409; the browser keeps the user's form. Nothing is ever lost.
  - Live reload polls mtimes every 2 s with `os.scandir`.
- **Editor.**
  - Vanilla ES modules + SVG. No Preact, no CDN, no Node build step.
  - `lore serve` binds to 127.0.0.1 only and checks the Host header. Mutating requests need a per-run token header plus a JSON content type.
  - The spreadsheet is a real `<table>` with native inputs, and doubles as the accessible fallback.
  - Subway shows the top 12 lanes by default and is filterable.
  - Saga mode refuses writes (403) except change requests.
  - Mindmap is cut from v1.
- **Aeon interop scope.** Import the current fileVersion (27) and fail clearly on others. Skip the migration chain, the solver internals and the Subway layout algorithm.

## Phase 0: repo, Spec Kit, continuity kit
- **Repo.** `git init -b main` in `Documents\Lorekeeper`, then the user's Spec Kit sequence exactly:
  1. `specify init . --integration claude --script ps --force`
  2. `specify preset add lean`
  3. `specify integration install codex --script ps`
  4. `specify integration use codex`
  5. `specify integration use claude`

  (re-validated) If init prompts or hangs, re-run it with `--non-interactive` and log that. Confirm `.specify/integration.json` has `default_integration: claude`, and that `.claude/settings.json` keeps its additionalDirectories.
- **CLAUDE.md and AGENTS.md** are written *after* init, because init may overwrite them. Each gets:
  - the user's Spec Kit note, verbatim
  - "Before anything, read docs/build/HANDOFF.md, BUILD-PLAN.md and the SESSION-LOG tail."

  AGENTS.md also carries the Codex rules: work in this repo only; no commits, pushes or installs; stdlib only; `encoding="utf-8"`; run unittest.
- **Constitution** (speckit-constitution). (re-validated: no `tomllib`)
  - The core is stdlib-only and vendorable, on Python ≥3.11, with `lore.json` config.
  - Storage is plain text following the saga Wiki convention, Obsidian-compatible.
  - One ops table drives the CLI, MCP and HTTP.
  - Ponytail ladder.
  - Tests use stdlib `unittest`, with one runnable check per piece of non-trivial logic.
  - Never publish or push, except the approved private repo at the end.
- **(re-validated) Spec Kit skills.** `.claude/skills/` didn't exist at session start, so the new skills may not be invocable via the Skill tool (that would need `/reload-skills`). Fallback: Read `.claude/skills/speckit-<x>/SKILL.md` and follow it by hand. Log which path was used.
- **Continuity kit: project-scoped hooks.** They live in `Documents\Lorekeeper\.claude\settings.json`, which hot-reloads.
  - One script, `tools/build-hooks/guard.py`, run as `python -I`, with four modes.
  - Each mode is a no-op without `docs/build/ACTIVE` and exits 0 on any internal error. The only exception is the deliberate exit 2 in `pre`.
  - State lives in `docs/build/.hookstate.json`.
  - **`post`** (PostToolUse):
    - Read the transcript tail. Usage = the last assistant message's (input + cache_creation + cache_read), plus the bytes written since that line ÷ 4. The window comes from `ECC_CONTEXT_WINDOW_TOKENS` (default 1,000,000).
    - (re-validated) Warn at **86%** (advisory), **90%** (mandatory: finish the atomic step, rewrite HANDOFF, append SESSION-LOG, tick boxes, commit) and **92%** (repeat until HANDOFF is newer than the warning). The reason: observed auto-compactions on this machine fired at 922,763–973,192 tokens, and the lowest was 92.3%.
    - Re-arm when usage drops below 80%.
    - Nudge a HANDOFF refresh after each `git commit`.
    - Track `Read` calls on the three docs.
  - **`pre`** (PreToolUse, matcher `Edit|Write|NotebookEdit`): block with exit 2 until all three docs have been read since this session's latest SessionStart.
  - **`compact`** (PreCompact, never blocks):
    - Log the trigger, the token percentage and the handoff age to SESSION-LOG.
    - Record the observed pre-compaction tokens. If they are below 92% of the window, scale the effective window down so the tiers fire in time.
    - Copy HANDOFF to `docs/build/handoff-history/`.
    - Write `docs/build/AUTO-SNAPSHOT.md`: `git log -5`, porcelain status, the current `specs/NNN`, its first five unchecked tasks, and the last user message (truncated).
  - **`start`** (SessionStart, every source): print HANDOFF (≤8,000 chars), plus AUTO-SNAPSHOT if it is newer, plus the instruction to read the other two docs. Reset read-tracking.
  - (re-validated) The hooks are registered mid-session, so re-read the three docs once after registration so the tracker records them.
  - **Discipline:** HANDOFF is rewritten and SESSION-LOG appended at every Spec Kit step and feature boundary, so a surprise compaction loses at most one task.
  - **At the end:** delete ACTIVE, then remove the hook entries.

## Phase 1: REA close-out
- **Extract.** Re-extract the Aeon bundle into scratch: `python -I tools/aeon_extract.py "<exe>" C:\Users\Owner\lk-scratch\aeon_extract`. Never into the repo. The exe hash was re-checked on 2026-10-18 and still matches.
- **Sample fixtures.** While the Aeon trial is still valid, create and save about 5 sample `.aeon` files via computer use: a custom calendar, dependencies, narrative folders, relationships. Save them to `C:\Users\Owner\lk-scratch\aeon_fixtures\` as round-trip fixtures, kept out of git. Never enter licence or account details; a licence or registration prompt means stop.
- **`docs/research/AEON-SPEC.md`**, clean-room, in our own words: container, calendar maths, age rule, solver summary, narrative numbering, CSV columns, migration notes (current fileVersion only).
- **REA/Ghidra** only if round-trip testing needs the meaning of the 28 extra index bytes. **If the trailer turns out to be cryptographic: stop and ask.**

## Phase 2: Spec Kit features
Each feature runs speckit-specify → plan → tasks → implement → converge, then `ponytail-review`, then a read-only Codex adversarial review, then fixes, and is committed as its own commit series.

1. **001 core:** model, storage, `lore.json` schema, ONE ops table driving the argparse CLI (`--json` everywhere), the MCP server and (later) HTTP.
   - Subcommands: `lore init|check|age|where|when|knows|timeline|query|serve|import|export` (later features fill in some of them).
   - MCP: a stdlib JSON-RPC stdio server exposing tools only (initialize, tools/list, tools/call, ping). Verify the protocol version through context7 first.
   - The restricted-frontmatter reader/writer round-trips byte-stably.
   - sha256-versioned writes, with a three-way merge or 409.
2. **002 time.**
   - Multiple calendars per project: Gregorian with leap rules [4,100,400]; custom eras, months and leap cycles; day-count years.
   - (re-validated) Space SRD: **365-day years** (`DARK_SPACE_OPERA_500_CHAPTER_BRAIDED_ARCHITECTURE_V2.md:52`), `Y0 = 6842 CE` (HO-079). Dateline format `6842 CE, Day 004, 20:05` (`_system/workflow/STANDING_RULES.md:27`).
   - Date strings carry precision (`2036`, `2036-11`, `2036-11-21 21:28`), circa (`~2004`), uncertain ranges (`2004..2006`) and durations.
   - Ages follow Aeon's rule, plus explicit uncertainty.
3. **003 checks.**
   - Aeon's checks: dependencies FS/SS/FF/SF and constraints.
   - Aeon-plus checks: one person in two places (overlapping events at different locations); a dead character participating; age sanity; rail regression; story order versus chronology.
   - Declarative rules in `lore.json`: max duration ("a duel ≤ 1 day") and exact gap ("death→Return = 7 days").
   - Every finding carries a code, a severity and file:line. The exit code is non-zero on FAIL.
4. **004 saga integration.** Specifics below.
5. **005 interactive editor.**
   - `lore serve` with a JSON API (architecture above).
   - Views: Timeline (drag to re-date), Subway lanes, a relationship grid with ages, a spreadsheet, narrative, and an inspector.
   - Users can create, edit and link items, and the page live-reloads when agents edit the files.
   - In saga mode, edits go to the change-request queue.
   - Accessibility basics: keyboard navigation, labels, and contrast in both themes.
6. **006 interop.**
   - `.aeon` import of all 19 bundled template files (fileVersion 14) and app-saved v27 files, and a v1 writer that emits the v14 core shape (AEON-SPEC §2.1).
   - Round trip: our writer → open in the Aeon desktop app via computer use → a screenshot shows the items, dates and relationships.
   - CSV import/export with Aeon's column IDs, and Markdown export.
7. **007 templates, onboarding, packaging.**
   - Templates: Novel, Series, and Worldbuilding/Campaign (GM).
   - `pyproject.toml`, so `uv tool install .` works.
   - README with a scripted quickstart, a user guide, and an agent skill file for Claude Code/Codex.
   - `gh repo create lorekeeper --private --source . --push`, then confirm `gh repo view --json visibility` returns PRIVATE.

## Codex split and guardrails
- **Hand-off.** Self-contained briefs go through `Agent(subagent_type:"codex:codex-rescue")` with `--write`. Each brief gives the paths, the spec excerpt and the acceptance tests, plus: "work only in Documents\Lorekeeper; no commit, push or install; stdlib only; run `python -m unittest`; list changed files".
  - Codex gets plain briefs, never `/speckit` commands. Keep `claude` as the active Spec Kit integration.
- **Codex builds:**
  - the frontmatter parser/writer
  - the calendar and date maths with test vectors
  - the MCP server
  - the `.aeon` reader/writer and CSV
  - the saga card-date parsers and tests
  - read-only adversarial reviews of each feature
- **Claude keeps:** specs and plans, architecture, editor UX, saga integration (it is governance-sensitive), reviews, verification and all commits.
- **After every Codex run:** compare `git status --porcelain` in Lorekeeper, the three live sagas and the three clones against the last snapshot. Any stray change means stop, revert it and log it.

## Saga integration (feature 004): specifics
Paths are relative to each saga root and identical in all three repos.
- **Work in clones only.**
  - Clone to `C:\Users\Owner\lk-scratch\sagas\{Realm Saga,Space saga,Zombies saga}`, outside OneDrive. The parity test compares siblings in its parent folder, so it still works there.
  - Baseline each clone: unittest, `saga.py status`, `health`, and `validate` on frozen chapters. Save the results to `docs/build/baselines/<saga>/`. **If a baseline is red: stop and report.**
- **Vendor and parity.**
  - Vendor flat into `_system/vendor/lorekeeper/*.py` (the parity glob doesn't recurse), with a `VERSION` file holding the source commit.
  - Add `_system/vendor/lorekeeper/*` to `SHARED_GLOBS`, and `_system/scripts/chrono.py` + `_system/tests/test_chrono.py` to `SHARED_FILES`.
- **`chrono.py`** is modelled on `profiles.py` (`enabled`/`applies`/`assemble`/`verify`/`gate` at profiles.py:20–427) and reuses `cards.py`, `fsio` and `refs`.
  - `enabled()`: the manifest has a `lorekeeper` key.
  - `applies(n)`: the chapter state has `"chrono": 1`. `init-chapter` sets it only once chronology is enabled, so chapters already in progress are never gated.
  - `assemble(n)` at SOURCE_ASSEMBLY writes `RT/context/chronology.md`: roster ages at the chapter date, each person's last known place and time, time elapsed since their last appearance, and constraints coming due. Plus a sha256 receipt.
  - `gate(..., completing)` at WIKI_AND_LEDGER_UPDATE: the Wiki pages touched in this chapter must carry structured fields. Hook it in next to `profiles.gate` at state.py:346/383.
  - (re-validated) Zombies has no `card_schema` or `refs` manifest keys (default schema, field `Date/era`), so `chrono.py` must work without them.
- **`saga.py` changes:**
  - `cmd_validate` gets `FAIL CHRONO_*` lines, for applicable chapters only.
  - `cmd_health` gets an advisory chronology summary.
  - New subcommands:
    - `chrono N`
    - `chrono-report`, which writes `_system/knowledge/chronology_report.md`, a 500-card planning and canon audit
    - `timeline`, which runs `lore serve` on the saga
    - `timeline-requests`, which lists and applies queued edits
- **Manifest key:** `"lorekeeper": {"mode": "warn", "calendars": {...}, "rules": [...]}`. Warn mode first; switching to fail mode is a later user decision.
  - Realm and Zombies use Gregorian. Space uses SRD with a CE display.
  - Realm rules: a duel ≤ 1 day; death→Return = exactly 7 days; paired cards 7 days apart.
  - Space rule: no rail regression on `Primary allocation`.
- **Shared docs:**
  - Wiki `_TEMPLATES` gain optional `born`/`died`/`date`/`end` keys.
  - Add a generic `_system/skills/chronology.md`, and list it in the skills README, since `test_docs` checks that every skill is listed.
  - Update the PIPELINE notes and add a START_HERE intent per saga ("Show me the timeline" / "Check chronology").
- **Backfill.** An agent pass over the frozen chapters' Wiki pages adds structured fields from canon, citing chapters. Invented values go to `agent_decisions.md`. Commit as `wiki:`/`knowledge:`.
- **Safety:**
  - Commit `system: lorekeeper chronology (warn mode)` in the clones.
  - Never `git add -A`. Check `git diff --cached --name-only` against an allowlist before every commit.
  - **Never stage:** in-progress `Chapters/CH00N/`, `_system/state/CH00N.json`, (re-validated) `_system/state/provenance/CH00N.json`, or `_system/logs/saga.log`.
  - Authorities stay read-only, and planning findings go into the report, not into edits.
  - Snapshot `saga.py status N` and `validate N` for each in-progress chapter before and after; they must be identical.
- **Landing.**
  - (re-validated) Recompute the in-progress set at landing time; the user may have moved on.
  - Snapshot each live repo's porcelain status plus the hashes of its in-progress files.
  - If live `main` moved past the clone base, rebase the clone's commits onto it and re-run that clone's suite.
  - Land with `git fetch <clone> main` then `git merge --ff-only FETCH_HEAD`.
  - (re-validated) **Land all three back to back.** The live parity test compares every sibling under `Creative writing\`, so it is expected to be red until the third landing.
  - Then re-verify the porcelain status and hashes, and run all three suites, parity and `chrono-report`.

## Verification
- **Lorekeeper:**
  - `python -m unittest discover` is green.
  - `lore check` is clean on the 3 templates.
  - An import scan finds stdlib modules only, and there are no bare `open(` calls.
  - A 3,000-item synthetic project loads in under 1.5 s and checks in under 2 s.
  - The MCP output matches the `--json` output (golden test).
  - The `.md` files of all three saga Wikis, copied to temp, round-trip byte-identical.
  - All three architectures' card dates parse at 100%, or land in an unparsed report.
  - The README quickstart runs verbatim (scripted).
- **Editor (Playwright MCP):**
  - Create an event, link a character, drag to re-date, and see the age update.
  - A keyboard-only create/date/link flow.
  - A simultaneous CLI and browser edit ends in a merge or 409, never lost data.
  - In saga mode, hand edits reach the queue.
- **`.aeon`:** all 19 bundled Aeon template files import, and an exported file opens in Aeon (computer use, screenshot).
- **Sagas:**
  - All three suites green, parity green, `health` clean.
  - In-progress chapters unchanged.
  - `chrono-report` generated.
  - `timeline` serves (Playwright).

## Stop conditions and definition of done
- **Stop only for:**
  - anything that would be public
  - a cryptographic `.aeon` trailer
  - an Aeon licence or registration prompt (never enter credentials)
  - a saga baseline that is already red
  - a destructive or outward action not covered above
- **Done when:**
  - features 001–007 have converged
  - all the verification above passes
  - the three sagas are integrated in warn mode and backfilled, with chronology reports generated
  - the docs are written and the private GitHub repo is pushed
  - HANDOFF is final, ACTIVE is removed and the hooks are unregistered
  - memory is updated and a final report goes to the user

---

## Record: design-review amendments (session 1; now merged above)
1. Features renumbered 001–007, with the CLI + MCP folded into core.
2. Storage follows the saga Wiki convention.
3. `lore.json` replaces TOML.
4. No `datetime`; integer minutes; SRD year length taken from the World Bible (settled: 365).
5. Uncertainty-aware FAIL/WARN; no solver in v1.
6. Stdlib only; utf-8; line endings; OneDrive.
7. sha256 versions plus merge/409.
8. Editor: vanilla JS and security.
9. REA scope cut; sample fixtures created via computer use.
10. Saga work in clones; ff-only landing.
11. Vendor layout and manifest key.
12. Project-scoped `guard.py` hooks.
13. Codex guardrails.
14. Acceptance additions.

---

# Progress checklist (tick as you go; HANDOFF.md says which box is current)

## Phase H — session-limit handoff (session 1, 2026-10-17)
- [x] BUILD-PLAN.md, HANDOFF.md, SESSION-LOG.md, KICKOFF-PROMPT.md written
- [x] tools/aeon_extract.py saved; .gitignore excludes extracted Aeon files

## Phase R — re-validation (session 2, 2026-10-18)
- [x] Plan re-validated against the folder, the sagas and the tools; BUILD-PLAN consolidated; changes logged in SESSION-LOG

## Phase 0 — repo, Spec Kit, continuity kit
- [x] `git init`; Spec Kit 5-command sequence run exactly; Spec Kit note + "read HANDOFF/BUILD-PLAN/SESSION-LOG first" in CLAUDE.md and AGENTS.md
- [x] Constitution written (speckit-constitution): stdlib core, plain-text storage, CLI+MCP+editor parity, ponytail, unittest, no publish except private repo at end
- [x] tools/build-hooks/guard.py (modes start/post/pre/compact) + unittest self-check per mode
- [x] Hooks registered in PROJECT .claude/settings.json; `docs/build/ACTIVE` created; verified live; three docs re-read
- [x] Guard thresholds set from the measured compaction point (86/90/92%) and logged
- [x] Commit `chore: bootstrap Lorekeeper with Spec Kit and continuity kit`

## Phase 1 — REA close-out
- [x] Re-extract Aeon bundle with tools/aeon_extract.py into scratch (not repo)
- [ ] ~5 sample .aeon fixtures created in Aeon via computer use (scratch, not git) — DEFERRED: app access declined 2026-10-18; the 19 bundled templates (v14) are the fixtures; retry once at 006
- [x] docs/research/AEON-SPEC.md (clean-room, our words): container, calendar math, age rule, solver, numbering, CSV columns, migration notes
- [x] (only if needed) REA/Ghidra pass — not needed: trailer is plain (no checksum); v2 extra = size copy to settle the 28 extra index bytes

## Phase 2 — features (each: specify → plan → tasks → implement → converge → ponytail-review → Codex read-only adversarial review → commit)
- [x] 001 core (model + storage + ops table + CLI + MCP) — accept: all subcommands with --json; MCP golden test vs --json; saga Wikis round-trip byte-identical; round-trip byte-stable frontmatter on fixtures; types/roles/properties from lore.json; concurrent-edit sha256 version + merge/409 test; Obsidian-compatible keys; stdlib-only import scan; no bare open(); 3,000 items load <1.5 s
- [x] 002 time — accept: Gregorian incl. leap rules [4,100,400]; custom calendar; day-count years (SRD Y0 D004 ↔ 6842 CE Day 004); precision/circa/range parsing; durations; ages match Aeon rule on test vectors; all three sagas' card dates parse or land in an unparsed report
- [x] 003 checks — accept: FS/SS/FF/SF + constraints; two-places; dead-participant; age sanity; rail regression; story-vs-chronology; declarative max-duration + exact-gap rules; findings carry code/severity/file:line; non-zero exit on FAIL; FAIL vs WARN by certainty; 3,000 items check <2 s
- [x] 004 saga integration — accept: baselines green; vendored + parity green in all 3; chrono.py gated (in-progress chapters byte-identical status/validate before/after); chrono-report for 500 cards ×3; Wiki templates/skills/PIPELINE updated; START_HERE intent; backfill of frozen-chapter Wiki pages; suites green; `system:` commits explicit paths only; landed by ff-only back to back
- [x] 005 interactive editor — accept (Playwright): create event, link character, drag re-date, age updates, subway lanes, relationship grid, spreadsheet, narrative, live reload on agent edit, saga-mode edits land in change-request queue; keyboard-only flow; simultaneous CLI+browser edit merges or 409s; labels + contrast
- [x] 006 interop (Aeon open-in-app UNVERIFIED: access declined twice) — accept: all 19 bundled Aeon template files import; exported v1 .aeon opens in Aeon desktop (computer-use screenshot); CSV in/out with Aeon column ids; Markdown export
- [x] 007 templates + onboarding + packaging (private repo pushed: github.com/WilliamEbong/lorekeeper, PRIVATE) — accept: Novel / Series / Worldbuilding-Campaign templates pass `lore check`; pyproject + `uv tool install .` works; README quickstart runs verbatim; user guide, agent skill; private GitHub repo created + pushed, visibility PRIVATE

## Phase 9 — close-out
- [x] Final HANDOFF; ACTIVE removed; hooks unregistered; memory updated; final report to user

# Run 3: editor UX overhaul and whole-app audit (2026-10-18)

**Goal.** Make the browser editor excellent and easy for novelists, then fix what a whole-app audit finds. Spec Kit feature: [specs/008-editor-ux](../../specs/008-editor-ux/spec.md) ([plan](../../specs/008-editor-ux/plan.md), [tasks](../../specs/008-editor-ux/tasks.md)). Branch `feat/008-editor-ux`, local commits only.

**Deepened brief.**
1. A professional would add: undo after every save, protection against accidental drags, plain-language errors with a way out, continuity results inside the editor (the product's core promise was missing from it), empty states, phone layout, and a test that pins the editor's date maths to the engine's.
2. Rawest material: the running editor on a 116-item imported world (Wuthering Heights), the fixture world, an empty world and saga mode; the code; the user guide.
3. Methods: Impeccable critique (independent design review scored the old editor 18/40) and detector; Spec Kit; Playwright; three read-only audit agents (dates/checks, store/fm/ops/cli, interop/mcp/serve), then fixes in parallel worktrees.
4. Independent proof: the unit suite; Playwright on real pages (light, dark, 390 px, saga mode); the Impeccable detector; a fresh-context reviewer on the final diff.

**Acceptance checks.** Spec 008 SC-1 to SC-7; detector clean; every confirmed audit finding fixed with a test or listed under Later; full suite green; reviewer findings fixed.

- [x] Editor rewritten (shell, find, inspector, six views, toasts with undo, conflict actions, drag safety) and verified in Playwright
- [x] Docs (user guide, README) updated for the editor
- [x] Audit fixes: interop; frontmatter and store; ops, CLI, MCP and server; dates and checks (four worktrees, merged)
- [x] Large-world performance: spreadsheet paging and shared place list, capped Ages and Continuity, stamp polling 0.7 s to 0.05 s
- [x] User guide, agent skill, Aeon notes and spec 006 updated; full suite 240 OK; two fresh-context reviews (engine, editor) and all their findings fixed; final handoff
- [x] Run 3b (owner review, spec 009):
  - drag handles for start, end and the whole block;
  - a real Relationships view, separate from Ages;
  - BC era dates, centuries, Aeon nesting, Aeon type names and multitext;
  - a fresh review, with its findings fixed;
  - the engine re-vendored into all three sagas (probes identical, landed fast-forward only).

**Later (not built).** ~~BC dates finer than a year display as astronomical years~~; ~~"1800s" means the decade~~; ~~Aeon nesting is dropped on import~~; ~~dated Aeon types all become `event`~~; ~~Aeon multitext exports as JSON text~~ (all done in run 3b, spec 009); re-vendor the engine into the three sagas (run 3b).

# Run 4: progressive story wiki, built and applied to the sagas (2026-10-19)

**Goal.** Build feature 010 into Lorekeeper (engine, CLI, MCP, editor) and add a Story Wiki layer to Realm, Space and Zombies without changing how the sagas work. Spec: [specs/010-progressive-wiki](../../specs/010-progressive-wiki/spec.md) ([plan](../../specs/010-progressive-wiki/plan.md), [tasks](../../specs/010-progressive-wiki/tasks.md)). Branch `feat/010-progressive-wiki`, local commits only.

**Deepened brief.**
1. A professional would add: errors that say how to fix them (every refusal names the fix); a `check` warning for bad stamps; Undo for facts in the editor; MCP writes in a saga limited to the Story Wiki, so no tool can touch canon; a spoiler guard (hidden pages become plain text, frontmatter hidden in progressive mode); live reload for the Story Wiki folder; the 3,000-item timing test.
2. Rawest material: the code; the saga repos as they are (Wiki pages, `CURRENT_WORLD_BIBLE_OUT.md`, approved deltas, git history of the Wiki between freezes); the saga test suites; the running editor; Claude Code's MCP docs.
3. Methods: Spec Kit (clarify, plan, tasks, analyze, implement, converge); TDD for stamps, visibility, names and folding; Playwright; the Impeccable detector; three parallel backfill subagents (one per saga); the run-3b clone, probe and land method; two fresh-context reviewers.
4. Independent proof: the unit suite; the MCP golden test (MCP equals `--json`); an MCP handshake against each saga clone; saga suites with parity; byte-identical `status`/`validate` before and after; Playwright screenshots; reviewer subagents.

**Acceptance checks.**
- Spec SC-1 to SC-8.
- AI use: every new capability (`wiki`, `fact-add`, `fact-end`, `fact-remove`) is one op, so it is a CLI command with `--json`, an MCP tool and an editor API; tool descriptions say what, when, returns and an example; errors say what went wrong and how to fix it; the MCP golden test covers the new tools; `docs/agent-skill.md` is enough on its own to use the wikis; each saga's `.mcp.json` passes a handshake that lists the tools and calls `wiki` on a clone; the README shows the MCP setup for any world.
- Sagas: re-vendored engine, `story_wiki` key, backfilled `Story Wiki/`, shared `story_wiki_update` skill with one pointer, `.mcp.json`, the Wiki tab in `saga.py timeline` (Playwright); the after-freeze routine re-run from scratch on a probe matches the backfill; landed fast-forward only.

**Steps.**
- [x] Set up: cron, keep-awake, branch, live state re-checked
- [x] Clarify (5 answers in the spec)
- [x] Plan, tasks, analyze
- [x] Engine: stamps, story pages, names, folding, visibility, worked-out facts, chapter list (TDD)
- [x] Ops: `wiki`, `fact-add`, `fact-end`, `fact-remove`; `--config`; `mcp --saga`; check codes; schema defaults; MCP golden
- [x] Editor: Wiki tab, picker, card toggle, Add a fact with Undo, saga requests; Playwright; detector
- [x] Templates, user guide, agent skill, README
- [x] Sagas: baseline, clones, vendor and config, skill and pointer, `.mcp.json`, handshake test
- [x] Sagas: backfill (three parallel agents), probe replay, after-freeze proof, reviewer
- [x] Land the three sagas (fast-forward only)
- [x] Finish: all checks, two reviewers, docs, handoff, memory, cron deleted, notification

# Run 5: planning wiki, built and applied to the sagas (2026-10-19)

**Goal.** Build feature 011 into Lorekeeper (engine, CLI, MCP, editor) and add a Planning Wiki to Realm, Space and Zombies without changing how the sagas work. Spec: [specs/011-planning-wiki](../../specs/011-planning-wiki/spec.md) ([plan](../../specs/011-planning-wiki/plan.md), [tasks](../../specs/011-planning-wiki/tasks.md)). Branch `feat/011-planning-wiki`, local commits only.

**Deepened brief.**
1. A professional would add: errors that name the settings key or source to fix; a `problems` list on the planning index (uncited facts, unknown sources, missing sections, ideas used as facts) so the build can prove every citation resolves; a change that checks everything before writing and says what was written if it fails part-way; version checks on planning pages; a leak test with a unique marker; live reload for the planning folder; a timing check on Realm's real documents.
2. Rawest material: the code; the sagas' planning documents as they are (headings, Conversations entries, cards, registers); the saga AUTHORITY.md, impact skill and override register; the 2026-07-28 MCP schema; the running editor.
3. Methods: Spec Kit (clarify answered in the spec, plan, tasks, analyze, implement, converge); TDD for the source reader, link lists, ideas, change and write-back, impact search and leak rule; Playwright; the Impeccable detector; three parallel build agents (one per saga); the run-4 clone, probe and land method; two fresh-context reviewers.
4. Independent proof: the unit suite; the MCP golden test; MCP handshakes against the clones; saga suites with parity; byte-identical status/validate/health; `lore planning` problems = 0 in each saga; the change-flow proof's impact report; Playwright screenshots; reviewer subagents.

**Acceptance checks.**
- Spec SC-1 to SC-9.
- AI use: the five capabilities are ops (CLI `--json`, MCP tool, editor API); guides say what, when, returns, example; errors say how to fix; MCP golden covers them; `lore mcp --saga` never writes an authority or a Wiki page; `docs/agent-skill.md` alone is enough to use the planning wiki (when to read it, the change flow, the saga routines); README and user guide explain it for any world.
- Sagas: re-vendored engine, `planning_wiki` key, Planning Wiki with cited facts and labelled ideas, computed link lists, shared `planning_wiki_change` skill with one pointer, Planning in `saga.py timeline` (Playwright); landed fast-forward only.

**Steps.**
- [x] Set up: cron, keep-awake, branch, live state re-checked
- [x] Owner's mid-run MCP fix (68b63e5, branch fix/mcp-cache-hints)
- [x] Specify and clarify (5 answers in the spec)
- [x] Plan, tasks, analyze
- [x] Engine: settings, source reader, citations, pages, matcher, link lists, views, fact, impact, change, leak tests (TDD)
- [x] Faces: ops, MCP, CLI, serve, editor; timing; Playwright (fixture and saga mode); detector
- [x] Docs: README, user guide, agent skill
- [x] Sagas: baseline, clones, vendor, key, skill and pointer
- [x] Sagas: three build agents; probe replay; change-flow proof
- [x] Reviewers and fixes
- [x] Land the three sagas (fast-forward only)
- [x] Finish: all checks, docs, handoff, memory, cron deleted, notification

# Run 6: the Lorekeeper app and a plain-language editor (2026-10-19)

**Goal.** Make Lorekeeper usable by creative people who are not programmers, with no terminal at any point (feature 012: setup, a double-click launcher, a start screen, an AI guide inside each world), then a plain-language pass over the editor (feature 013). Spec: [specs/012-app](../../specs/012-app/spec.md) ([plan](../../specs/012-app/plan.md), [tasks](../../specs/012-app/tasks.md)); 013 to be specified after 012 lands on the branch. Branch `feat/012-app` (worktree `lk-scratch/lk-app`), local commits only.

**Deepened brief.**
1. A professional would add: friendly errors for every start-screen action (folder exists, no permission, Python missing); an empty state that leads with "Start a new world"; a missing-folder state; keyboard and screen-reader basics; a second-launch check so two copies never fight over a port; AI files that never overwrite a person's own; a handshake test proving an AI can connect from a new world's `.mcp.json`.
2. Rawest material: serve.py, cli.py, ops.op_init, templates.py, editor.html/css/js, the saga launchers (`Open * Lorekeeper.bat`, `chrono.serve`), docs/agent-skill.md, the running pages.
3. Methods: Spec Kit (spec, plan, tasks, implement, converge); TDD for the world list, folder kinds, AI files and the app API; Playwright through isolated Chromium (the MCP profile is shared); the Impeccable detector; a fresh-context reviewer.
4. Independent proof: the unit suite; an MCP handshake on a world the app created; Playwright screenshots (light, dark, 390 px) and console; a real `pythonw` launch and a second launch; the shortcut files on disk; the detector; the reviewer.

**Acceptance checks.** Spec 012 success criteria; for 013, every editor screen reviewed for programmer language, with fixes verified in Playwright and the suite green.

**Steps.**
- [x] Set up: cron, keep-awake, worktree, spec 012
- [x] 012 plan and tasks
- [x] 012 engine: world list, folder kinds, AI guide files, app server and API (TDD)
- [x] 012 start screen page, editor "All worlds" link, icon
- [x] 012 setup batch file, shortcuts, launch and second launch
- [x] 012 docs (README, user guide, agent skill move), Playwright, detector, suite
- [x] 013 specify, plan, tasks, implement, verify
- [ ] Reviewer and fixes; finish (handoff, cron deleted, notification)

**Later.** An installer that brings its own Python; macOS and Linux shortcuts; stopping automatically when the browser closes; check the `sf` connection label ("Starts before end of" on an item whose end must come after the other's start); an editor that skips the planning request in worlds without a planning wiki (a handled 404 in the console).

# Feature requests from the owner

## Chapter-scoped story wiki (requested 2026-10-18; specified 2026-10-19 as [specs/010-progressive-wiki](../../specs/010-progressive-wiki/spec.md), which settles the questions below; to be built in run 4)
**The request, in the owner's terms:** a story wiki tied to where the story is. Selecting chapter 3 shows only what is known by chapter 3; selecting chapter 10 shows the story state as of chapter 10, and so on.
- **AI optional.** Everything must be possible by hand, with AI making it much faster.
- **An upgrade to the saga system, not a replacement.** Each chapter drafting session in the owner's saga system already produces a current-state snapshot. This feature should be a more mature layer on top of that. Once the built-in chapter wrap-up has run, the AI uses its output to update that story's Lorekeeper profile.

**Grounding for whoever designs it (from reading the Realm saga, 2026-10-18):**
- In the saga pipeline (`_system/workflow/PIPELINE.md` §6), post-approval finalization already runs:
  - one extraction pass, `extract_approved_chapter_changes`, which writes `RT/approved_deltas.md`;
  - then the updates: `update_current_world_bible`, which writes `CURRENT_WORLD_BIBLE_OUT.md`, and `update_obsidian_wiki`;
  - then a `finalization_auditor`, then `saga.py finalize N` and `freeze N`.
  
  The new step would read those approved outputs after the wrap-up and write chapter-stamped facts into Lorekeeper. Nothing may run on drafts: the pipeline forbids draft-derived facts leaving the chapter workspace.
- The saga already keeps per-chapter state in `_system/state/CH###.json` and runtime context in `_system/runtime/CH###/` (profile packets), plus knowledge ledgers in `_system/knowledge/` (mystery ledger, setup/payoff ledger, character cards).
- Lorekeeper already has building blocks:
  - `knows` (what a person has learned by a date, from `learns` links);
  - `where` (a person's last place by a date);
  - ages at events;
  - Narrative order for chapters and cards.
  
  The missing idea is a *story position* (the chapter a fact was established in, or revealed to the reader), which differs from the in-world date.

**Scope and answers the owner added the same day (2026-10-18, before any spec):**
- It is a *progressive wiki*. Each type has an index page (Characters, Factions, Locations, and possibly items, objects and vehicles) listing only the entries named by the chosen chapter.
- Clicking an entry opens its *progressive card*, which has its own chapter toggle.
- Character cards hold the critical things as of that chapter: core beliefs, what they know, where they are, relationships, and the like.
- Factions, locations, items, objects and vehicles get the same kind of progressive card.
- **Unnamed characters.** A character seen but not yet named is listed under the description the reader has ("the hooded rider") from their first appearance, and switches to their name in the chapter that names them.
- **Identity reveals.** In the progressive view, a secret identity is its own card until the reveal chapter; then the cards merge. A **complete** view, with everything, shows one card holding all of a character's identities.
- **Things.** Only important individual items get cards, plus category pages for kinds of things (for example, "standard alien battle tank").
- **Defaults accepted.** The cut-off follows reading order; facts are stamped per line, plus `first_appearance`; one chapter picker filters every editor view; hand-written worlds use the same stamps.

**Questions that remain for the spec (some are answered above):**
- Is the cut-off the reading order or the in-world chronology? (Flashbacks make these differ.)
- Should the cut-off cover what the reader knows, what each character knows, or both?
- How is a fact stamped with the chapter that establishes it: per field, per link, per page section?
- Does the editor get a chapter picker that filters every view?
- How does a hand-written world, with no saga pipeline, record the same stamps?

## Planning wiki (requested 2026-10-19; shape confirmed; to be specified and built as feature 011 in run 5, prompt in KICKOFF-PROMPT.md)
**The request, in the owner's terms:** a third wiki, the planning wiki: the intended end state of the story, everything the author has designed, including what no reader knows yet. Today the bibles and some other documents together play this role.
- **Flow of information:** design happens in the planning wiki → it is used to create the chapter cards → the cards are used to draft → the full and progressive wikis are updated from the written story.
- **Audience:** a back-end reference for the author and the AI, to plan and keep continuity.
- **Editing:** the author changes a planning fact (example: "the fighter jet's top speed is Mach 30"), or tells the AI to. The AI then reviews and updates everything linked to it.
- **Constraint:** the existing saga systems keep working exactly as they do now; the wikis are added on top.

**Grounding (read 2026-10-19):**
- Realm's `_system/workflow/AUTHORITY.md` ranks the sources:
  1. The Master World Bible is binding for setting canon and "may contain facts the audience and the characters do not yet know".
  2. Chapter Cards (extracted from the story architecture) and the Conversations document are binding per chapter.
  3. The Style Bible.
  4. Approved prose.
  5. Derived systems (Current World Bible, Obsidian Wiki, ledgers, the agent-decisions register), which never overrule anything above. When they conflict, the derived data is repaired.
- A decision that supersedes an authority is a HUMAN OVERRIDE and goes to the override register (`_system/knowledge/overrides.md`).
- Plot ideas, the tech ledger and the review reports are reconciling context, not authorities.
- Sizes in Realm: World Bible 387 KB, story architecture 712 KB, plot ideas 898 KB. Building a planning wiki means reading the World Bible once, split by section. Impact reviews should use a mechanical search (names and aliases across the bible, the cards, the chapters and the wikis) so the AI reads only the passages that match.

**Shape (confirmed by the owner, 2026-10-19):**
- The World Bible stays the authority, so the saga works unchanged. The planning wiki is a derived, per-entity view of it, each fact citing its section.
- An author's edit in the planning wiki is recorded as a HUMAN OVERRIDE and written back into the World Bible by the AI.
- An impact review then covers the matching planning pages, bible sections, unwritten chapter cards and the in-progress chapter.
- A change that contradicts frozen chapters is flagged for the author, never applied to approved prose.
- It is a separate feature (011), built after 010, reusing its Wiki tab, cards and fact operations. The Wiki tab's toggle becomes Planning | Full | Chapter N.

**Owner decisions (2026-10-19):** the World Bible stays the master; any conflict with written (frozen) chapters is flagged to the author, never applied to approved prose; build 010 first, then specify this as feature 011.

**Sources (owner, 2026-10-19):** every planning document, not just the World Bible. Examples:
- Space's Military Systems Bible;
- the Conversations documents (saved dialogues);
- the character, species, faction and combatant card libraries;
- tech ledgers, author rulings and overrides;
- mystery and setup/payoff ledgers.

The saga's `AUTHORITY.md` ranking still decides which document wins a conflict.

**Linking (owner, 2026-10-19):** pages are well linked. For example, the Vampire page has a "Notable vampires" section linking each vampire's card, such as Sava's. Sava's card lists the saved dialogues that feature her, each linked. Characters, items and places have an "Appears in" section listing their chapters, kept current from the chapter cards.

**Token-efficient design for links (proposed):** link lists are computed by Lorekeeper, never written by the AI, so they cost no tokens and never go stale:
- **Notable X:** pages tagged or linked to the kind. Saga Wiki pages already carry tags such as `species-heavenian`.
- **Dialogues:** Conversations entries (each is a heading, such as `### §A.252 — The Bound`) whose speaker lines (`Name:`) or text name the character, plus the entries a chapter card points to.
- **Appears in:** a whole-word search for each page's names and aliases across the parsed chapter cards (the `**POV:**`, `**Location:**` and summary text of every card; the saga's `cards.py` already parses them). Planned chapters come from the cards; written chapters come from approved chapters.
- **Limits:** a card that only says "the vampire captain" is missed unless that phrase is one of her names. Names that are ordinary words need an exclusion list.

**Undecided material (owner, 2026-10-19):** plot ideas, opportunities portfolios and unapproved-decisions reports are shown in the planning wiki, clearly labelled as ideas. They are kept visibly apart from decided facts, and are never used as decided canon (for chapter cards, impact reviews or link lists).
