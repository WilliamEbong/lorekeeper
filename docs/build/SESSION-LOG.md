# SESSION LOG — Lorekeeper build

Append-only. Newest entries at the bottom. Each entry gives: date/time (UTC if known), session, what was done, decisions, and what comes next.

---

## 2026-10-17 — Session 1 (research + planning), Claude Opus 5.5 in the Claude desktop Code tab

**Done**
- **Confirmed the tooling.** REA 6.5.0, Ghidra 12.1.4 and JDK 21 are installed, and the REA MCP is connected.
- **Statically analysed Aeon Timeline 3.5.123 with REA.**
  - Ran `inspect_pe_resources` and found custom resource type 256.
  - Inflated the concatenated zlib streams. They contain the web app (`main.js`, `ReducerWorker`), the UI strings and 17 `.aeon` templates.
  - Decoded the data model from the template JSON.
  - A recon subagent decoded the `.aeon` container and the main behaviours: calendar, age, solver, numbering, CSV columns and migrations.
  - The full findings are in HANDOFF §2.
- **Web research.** Aeon's feature inventory, pricing, community tools and what writers value. Summary in HANDOFF §2.
- **Surveyed the three sagas** (Realm, Space, Zombies).
  - They share one byte-identical stdlib engine, with a parity test enforcing it.
  - Chronology exists only as prose: no birthdates, no structured events.
  - Each saga has one in-progress chapter, which must not be disturbed.
  - Integration seams are in HANDOFF §3.
- **Brainstormed with the user**, who chose:
  - the name Lorekeeper / `lore`
  - an interactive editor in v1
  - an audience of AI writers, novelists without AI, and worldbuilders/GMs
  - saga hand edits become change requests
  - canon gaps are handled by "decide and record" in `agent_decisions`
  - a private GitHub repo at the end
  - authorisation to reverse engineer Aeon (do not raise the EULA again)
- **Plan approved.** A design-review subagent then supplied 14 amendments, now in BUILD-PLAN.md, which supersede the plan text.
- **Wrote:** BUILD-PLAN.md, HANDOFF.md, this log, KICKOFF-PROMPT.md, `tools/aeon_extract.py`, `.gitignore`.
- **Memory:** `aeon-timeline-re-project.md` now points here.

**Decisions made by Claude (judgement calls; the user can override)**
- **Location:** `Documents\Lorekeeper`, the same pattern as the other Spec Kit projects.
- **Language:** a stdlib-only Python core, so it can be vendored into the sagas.
- **Saga integration comes before the editor**, because it reaches the user's main goal sooner.
- **REA scope is limited** to what interop needs.

**Next**
- Start a new session with its working folder set to `C:\Users\Owner\OneDrive\Documents\Lorekeeper` and paste the prompt from `docs/build/KICKOFF-PROMPT.md`.
- Phase 0: git init, Spec Kit, constitution, continuity hooks.

---

## 2026-10-18: Session 2 (build), Claude Opus 5.5 in the Claude desktop Code tab

**Re-validation (plan mode, read-only)**
- **Confirmed unchanged:**
  - Folder contents.
  - Tool versions: Python 3.14.3, node 24.14.1, git 2.48.1, gh 2.93.0 (logged in as WilliamEbong, `repo` scope), uv 0.11.29, Claude Code 2.1.284, specify 1.0.13 (lean preset present), REA 6.5.0 (MCP connected), Codex CLI 0.160.0 with plugin 1.0.6.
  - The Aeon exe hash.
  - Saga engine byte-identity across all three, every seam line number in HANDOFF §3, and the in-progress chapters.
- **BUILD-PLAN.md rewritten as one consolidated plan.** The amendments are merged into the body. Changes:
  1. Constitution: `tomllib` replaced by `lore.json` config.
  2. Phase 0 hook text replaced with the single project-scoped `guard.py`. Matcher `Edit|Write|NotebookEdit`; MultiEdit is not a documented tool.
  3. Guard tiers changed from 90/94/97 to 86/90/92%. Observed auto-compactions in old transcripts fired at 922,763–973,192 of 1M tokens (lowest 92.3%). The compact mode self-calibrates the window from the observed point.
  4. Phase 2 body renumbered to features 001–007.
  5. `_system/state/provenance/CH00N.json` added to the never-stage list. It is untracked in all three sagas.
  6. Space SRD year = 365 days (architecture V2 line 52); dateline `6842 CE, Day 004, 20:05` (STANDING_RULES:27).
  7. The three live landings must happen back to back, because live parity compares every sibling.
  8. The in-progress set is recomputed at landing time; rebase the clone commits if live main moved.
  9. Zombies has no `card_schema`/`refs` keys, so `chrono.py` must not need them.
  10. Speckit skills may need `/reload-skills`; fallback is to read SKILL.md and follow it by hand.
  11. Re-read the three docs once after the hooks register mid-session.
  12. `.gitignore` gains AUTO-SNAPSHOT, handoff-history and raw baselines.
  13. The memory file's container description is stale; fix it at close-out.
- **Decision:** no Plan subagent this time. The design was already independently reviewed in session 1; this pass only re-validated facts.
- **Next:** Phase 0, box 1.

### Phase 0 (2026-10-18)
- `git init -b main`. The 5-command Spec Kit sequence ran as written, with no prompts. `integration.json` shows claude and codex installed, default claude, and `.claude/settings.json` kept its additionalDirectories.
- Decision: the speckit skills are not visible to the Skill tool ("Unknown skill"), because `.claude/skills/` was created mid-session. Fallback in use: read `.claude/skills/speckit-<x>/SKILL.md` and follow it by hand. The lean preset makes them short.
- CLAUDE.md and AGENTS.md were written after init. Both carry the Spec Kit note and the read-the-docs-first line; AGENTS.md also carries the Codex rules.
- Constitution v1.0.0 written to `.specify/memory/constitution.md`: 7 principles (stdlib/vendorable; plain text; one ops table; never lose an edit; honest checks; ponytail; tests).
- `tools/build-hooks/guard.py` (modes start/post/pre/compact) and `test_guard.py` (5 checks, green).
- Hooks registered in the project `.claude/settings.json`, using exec form (`command: python`, `args`) to avoid shell quoting. They picked up live with no restart. Verified live: PostToolUse wrote `.hookstate.json` and recorded the 3 doc reads, and PreToolUse blocked an Edit while reads were cleared.
- Tiers 86/90/92% are in the code (calibrated from the observed compactions, lowest 92.3%).

### Phase 1 (2026-10-18)
- Re-extracted the Aeon bundle into `C:\Users\Owner\lk-scratch\aeon_extract`; the stream counts match session 1. The analysis scripts live in the session scratchpad, never in the repo.
- Decision: **computer-use access to Aeon Timeline was declined** in the approval dialog. I did not retry. The 19 bundled template files (all fileVersion 14; Story Planning is the v1 layout) serve as fixtures. I will ask once more at feature 006 for the open-in-Aeon check; if that is declined too, the item is reported as unverified.
- Finding: the container parses cleanly on all 19 files, with no checksum. In v2 the 28 extra bytes hold a copy of the size at +12. The REA/Ghidra pass is not needed.
- Finding: bundled templates are fileVersion 14, while the app writes 27. The loader accepts a bare core or a full file, runs the migration chain, then rebuilds `collection`. Decision: the writer emits `{fileVersion:14, core:<v14 shape>}` and lets Aeon migrate it; the reader accepts v14 and v27 (customOrder/superById vs itemOrderByType/superAndChildOrderById).
- Finding: month and day are 1-based. AD timestamps = proleptic Gregorian seconds since 0001-01-01 (901/901 exact). BC dates are +1 day versus proleptic (105/105, all 1 January).
- Wrote `docs/research/AEON-SPEC.md` (clean-room, our words).
- Plan text: "17 templates" corrected to "19 bundled template files".

### Feature 001 core: specify / plan / tasks / implement (2026-10-18)
- Decision: the feature folder is `specs/001-core` (the lean speckit-specify asks for one; chosen autonomously).
- Decision: context7 hit its monthly quota, so the MCP spec was checked with WebFetch on modelcontextprotocol.io. The current revision is 2026-07-28 ("modern": stateless, per-request `_meta`, `server/discover`, error -32022). Legacy (`initialize`) covers ≤2025-11-25. Lorekeeper's server is dual-era.
- Codex built `lorekeeper/fm.py` + `tests/test_fm.py` (20 tests). It asked one clarifying question first (body boundary), which I answered: the body excludes the closing delimiter's newline. Stray-change check: only expected Lorekeeper files changed; the sagas were untouched.
- I wrote store.py, ops.py, cli.py, the fixture world, and tests for store, CLI, rules, perf and sagas. Fixed one bug: an absent key now equals an expected empty value in a merge.
- 48 tests green: the three saga Wikis round-trip byte-identically and load with no parser findings; 3,000 items load in under 1.5 s.
- Decision: `.gitattributes` marks `tests/fixtures/**` as `-text` to keep the CRLF fixture intact.
- Codex built `lorekeeper/mcp.py` (112 lines) + `tests/test_mcp.py` (15 tests, including the golden MCP-vs-CLI test). Stray check clean. I added one line: blank input lines are skipped.
- **Converge 001** (followed SKILL.md by hand): FR-1..FR-17 and SC-1..SC-9 are met. The only open item is the `lore` console script, which is planned for 007. Outcome: converged, no tasks appended.
- **ponytail-review 001:** cut 2 findings, net -5 lines (a dead bool branch in clean_fields; a one-caller `names()` helper). 63 tests green.
- A Codex read-only adversarial review of 001 is running.
- **Codex adversarial review of 001:** 16 findings, all fixed, with regression tests in `tests/test_review_001.py` (13 tests).
  - Writes: unique `mkstemp` temp files; the version is rechecked under a lock before every swap, including the OneDrive retry; `create`/`init` never overwrite (Windows `os.rename`, POSIX `os.link`).
  - Paths: scan and write paths are checked to stay inside the project folder.
  - Links: `link` on a single-value role refuses to replace an existing link (CONFLICT); a generated link must resolve to its target; `unlink` works on broken links.
  - List values: items containing quotes or brackets are quoted, and quotes only open a token.
  - Create: names containing `[ ] | # ^ / \` are refused; fields cannot override id/type/canonical_name; ids are deduplicated with `-2` etc.; the body is passed through untouched.
  - Merge: empty-list expectations merge correctly, and body conflicts return the current body.
  - Errors: ValueError/OSError become LoreError INVALID/IO_ERROR at the ops boundary, and newlines in values are refused.
  - Written keys match `[a-z_]+` (spec FR-2a added).
  - MCP: the envelope is validated (`jsonrpc` "2.0", string/int id, method); modern requests need `clientCapabilities`; output is ASCII-escaped, so lone surrogates can't crash the server.
- Note: Codex's sandbox blocks temp-file writes in read-only mode, so its in-review test run is not meaningful. Claude runs the suite.
- **Feature 001 done:** 76 tests green.

### Feature 002 time (2026-10-18)
- The codex-rescue forwarder ran the dates job with `--background`: the 9 KB prompt broke single-quoted Bash, so it was passed via a file. I waited with a status poll loop, then fetched the result with `codex-companion.mjs result`. Codex delivered `dates.py` (419 lines, no datetime) + `tests/test_dates.py` (21 tests). Stray check clean.
- I wired `timeinfo.py` (item_dates, narrowing, durations, display), `Project.calendars`, the ops `when` / `age` / `timeline` / `convert`, and `DATE_UNPARSED` in check.
- Added decades ("2040s") and a leading label before the date ("African Collapse Wars, 2040s").
- **Saga finding:** 1,497 of 1,501 card dates parse. The other 4 are real architecture errors in Space: `SRD Y0 D367`, `Y0 D374`, `Y1 D366`, `Y1 D378`. SRD years have 365 days, so these days cannot exist. They are kept in `KNOWN_INVALID` for the chrono-report.
- Decision: Space projects list `[srd, gregorian]` calendars, because the architecture header carries an ISO date.
- **Converge 002:** FR-1..FR-11 met; converged. 104 tests green.

### Feature 003 checks + 002 review fixes (2026-10-18), cut off by the usage limit
- **Codex review of 002:** 12 findings.
  - I fixed timeinfo items: duration end bounds use the last possible start minute; contradictory date_min/date_max is reported, never invented; an item used as `at` means its whole span; an invalid duration is always DATE_UNPARSED.
  - Codex job `task-mvd5i960-f2envw` is fixing the dates.py items:
    1. Impossible dates (Feb 30, SRD day 366) must not fall back to another reading.
    2. "May 3,2071".
    5. Months calendars use the configured month count per year.
    7. Signed age-year bounds.
    8. Hour-only format precision.
    9. Clock text inside notes.
    10. No duplicate time when the display template has one.
    12. Arithmetic leap-cycle year starts, no per-year materialisation.
- Codex built `checks.py` + `tests/test_checks.py` (122 tests green before wiring). I wired `checks.run` into `check` and added the ops `where` and `knows`. On the fixture: FAIL PARENT_AGE (Ivo/Mara), FAIL DEAD_PARTICIPANT (Ivo on the crossing after his death), WARN BROKEN_LINK.
- **Saga engine seams for 004** (investigator report):
  - `profiles.applies` keys on `st.contract(record) >= 2`. chrono will set its own `"chrono": 1` in `saga.py cmd_init_chapter` (L202-267, after `st.new_state`).
  - Gates are called in `state.py` `_enter` L345 and `complete_stage` L382 (lazy `import profiles`).
  - `cmd_validate` builds `fails`, with feature blocks at L576-585. `cmd_health` collects oks/fails, gated at L1531. Subcommand pattern at L1612.
  - `cards.parse_cards` returns `{n: {number, title, fields{label: value}, raw}}`. The rail field: Realm none; Space `Primary allocation`; Zombies `Arc/thread`. The date field is `Date` or `Date/era`.
  - `fsio`: `atomic_write(path, text)`, `write_json`, `sha256_file`, `append_log`. `GateError(PermissionError)` is at state.py L198. Test fixture: `fixture.make_repo(rich)`.
  - `test_docs` genericity bans HO-numbers, word caps, saga terms (Mandate, Ilyra, 2071, "Realm saga"…) and Wiki titles in shared docs.
- Decision: status/validate/health can rewrite status files, so baselines run on full copies (`lk-scratch\probe`), never on the live repos.
- Decision: Realm rules are encoded as Wiki-event rules (`tag: duel` max 1d; `role: return_of` exactly 7d). "Paired cards 7 days apart" has no structured pairing data and is reported as not encoded.
