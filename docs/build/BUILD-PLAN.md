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
- [ ] 002 time — accept: Gregorian incl. leap rules [4,100,400]; custom calendar; day-count years (SRD Y0 D004 ↔ 6842 CE Day 004); precision/circa/range parsing; durations; ages match Aeon rule on test vectors; all three sagas' card dates parse or land in an unparsed report
- [ ] 003 checks — accept: FS/SS/FF/SF + constraints; two-places; dead-participant; age sanity; rail regression; story-vs-chronology; declarative max-duration + exact-gap rules; findings carry code/severity/file:line; non-zero exit on FAIL; FAIL vs WARN by certainty; 3,000 items check <2 s
- [ ] 004 saga integration — accept: baselines green; vendored + parity green in all 3; chrono.py gated (in-progress chapters byte-identical status/validate before/after); chrono-report for 500 cards ×3; Wiki templates/skills/PIPELINE updated; START_HERE intent; backfill of frozen-chapter Wiki pages; suites green; `system:` commits explicit paths only; landed by ff-only back to back
- [ ] 005 interactive editor — accept (Playwright): create event, link character, drag re-date, age updates, subway lanes, relationship grid, spreadsheet, narrative, live reload on agent edit, saga-mode edits land in change-request queue; keyboard-only flow; simultaneous CLI+browser edit merges or 409s; labels + contrast
- [ ] 006 interop — accept: all 19 bundled Aeon template files import; exported v1 .aeon opens in Aeon desktop (computer-use screenshot); CSV in/out with Aeon column ids; Markdown export
- [ ] 007 templates + onboarding + packaging — accept: Novel / Series / Worldbuilding-Campaign templates pass `lore check`; pyproject + `uv tool install .` works; README quickstart runs verbatim; user guide, agent skill; private GitHub repo created + pushed, visibility PRIVATE

## Phase 9 — close-out
- [ ] Final HANDOFF; ACTIVE removed; hooks unregistered; memory updated; final report to user
