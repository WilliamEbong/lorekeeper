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
- Baselines GREEN (2026-10-18): all three suites and health exit 0, on the probes and the clones. Output in docs/build/baselines/{probe,clone}-before/. No stop condition.
- (resumed after the usage reset) Codex job `task-mvd5i960-f2envw` finished: dates.py has 8 review fixes and 8 regression tests (30 date tests). Stray check: only dates.py and test_dates.py changed. Two tests (CLI check exit code, MCP golden check) now expect exit 1, because the fixture world carries deliberate FAILs. Added the perf check: 3,000 items checked in under 2 s. 131 tests green.
- The speckit skills are now visible to the Skill tool (they loaded after the restart), so they can be invoked directly from here on.
- 003 converged (one convergence task: where/knows tests). ponytail-review of checks.py: lean already, nothing to cut.
- **Codex review of 003:** 10 findings. Claude fixed 1, 4, 8, 9 and 10 (`2f3ca19`). Codex is fixing 2, 3, 5, 6 and 7 in checks.py.
- **004 started in the Realm clone:** vendored engine, chrono.py, state/saga wiring, test_chrono (4 green), shared docs, parity lists. Realm manifest rules: max_duration 1d on `{type: event, tag: duel}` (code DUEL_TOO_LONG); gap exactly 7d from start, `role: return_of`, on `{type: event, tag: return}` (code RETURN_GAP).
- Decision: card items get their own type `card` (category narrative), with path `<architecture>#CHnnn`, so card findings point at the architecture.
- Decision: the Wiki templates gain the optional keys as `#` comment lines, like the existing `voice:` comment, so no parser sees an empty key.
- Decision: START_HERE is per-saga, not shared. The new intent is inserted before "## 2." and "These are the six intents" becomes "These are the intents".
- Codex fixed checks.py items 2, 3, 5, 6 and 7. The shared-person two-places benchmark went from 10.4 s to 0.16 s. Stray check clean. **Feature 003 done.**
- Decision: for story/rail order, `order_check` gives WARN only when the later item can start before the earlier one starts (`x.lo < y.lo`). Same-day chapters are no longer flagged (Space went from 45 to fewer WARNs). FAIL is unchanged.
- 004 integration propagated to all three clones (shared files byte-identical; manifest keys added). Space report: 2 FAIL RAIL_REGRESSION (Cards 051/052 dated 6840 CE, after Card 050 at 6842 CE on the same rail) plus 4 impossible SRD days. Realm and Zombies show 0 findings until the backfill.
- Backfill: 3 parallel general-purpose agents (brief `lk-scratch/snap/backfill_brief.md`), one per clone, editing only frontmatter, Provenance bullets and agent_decisions rows.
- 005: added ops `graph`, `request`, `requests` (change-request queue, default `.lore/requests`, host may pass an absolute `requests_dir`). Codex is building serve.py and the editor UI.
- Perf note: the load test hit 1.93 s while 3 suites and 6 agents were running; re-check when idle.
- Clone suites green (Realm 219, Space 216, Zombies 211; parity included). Committed `system: lorekeeper chronology (warn mode)` in each clone (Realm 1bd7f16, Space a5799be, Zombies dd98943) with an explicit allowlist (`lk-scratch/snap/commit_system.sh`), so nothing protected was staged.
- build-continuously skill adopted: keep-awake requested; a PushNotification goes out at the end. Decisions: Lorekeeper stays on `main` (fresh repo; the kickoff names the private push as the end state, which outranks the skill's no-push default).
- **Backfill Zombies** (committed in the clone as 7415b05 wiki + ab9a6df knowledge): 19 pages, all 18 people now have a birthdate. 11 values sourced, 9 decided and logged. chrono-report: 0 FAIL / 0 WARN.
- **Backfill Space** (224e56e wiki + b8a213e knowledge): 15 people. 15 birthdates decided (canon gives no ages; the android counts from commissioning; the ancient being got a placeholder of ~2 millennia) and 3 deaths sourced from the CH001 datelines. Findings unchanged: 2 rail regressions + 4 impossible SRD days.
- To fold into the 005 system commit:
  - the Space calendar gets a year-only SRD format `(?P<display_year>-?\d+) CE`, because circa birth years were falling back to Gregorian
  - the chrono report shows born as written, and ages as a range when uncertain (it showed the high end)
- Later list: AGE_LIMIT will FAIL for ageless beings (Space's ancient being) once they take part in dated events. Fix: a per-item `max_age` override, or a manifest `checks.max_age` per type.

### Feature 005 editor (2026-10-18)
- Codex built serve.py (161 lines), editor.html/js/css (vanilla ES module + SVG) and test_serve.py; 157 tests green. Stray check clean (the repo-local Codex temp dirs were removed; `.playwright-mcp/` gitignored).
- **Playwright MCP verification on a temp copy of the fixture world:**
  - SC-1: created an event, set a date, linked Mara Quell, and drag-redated it on the timeline (2021-06-15 became 2003-04-19, day precision kept). The Relationships grid updated Mara's age from 33 y 2 mo to 15 y 2 wk.
  - SC-2: keyboard-only create and date (focus, type, Enter, Tab, Save).
  - SC-3: a CLI same-key edit while the browser held unsaved input gave a 409 shown with the current values; the input was kept and the file held the CLI value. Fixed one wart: the status line now says "Not saved" instead of a stale "Saved.".
  - SC-4 (real Realm clone, `saga.py timeline`): 532 items; the inspector shows only "Propose change"; a proposal was queued in `_system/runtime/timeline_requests/` and the page was unchanged. The test request was closed with `--done`.
- Added `saga.py timeline` / `timeline-requests` and the report fixes (born shown as written; uncertain ages as "a to b years") via `lk-scratch/snap/patch_saga2.py`. Space manifest: year-only SRD format added.
- Engine: a per-person `max_age` override (`none` for the ageless). Realm's five immortal far-side beings and Space's ancient being are marked `max_age: none`, citing canon.
- **Backfill Realm** (a7e4358 wiki + 84d8299 knowledge): 24 pages, 12 values sourced, 18 decided (the far-side immortals get a decided era of ~3000 BC); the 2 events got date/end/location/participants.
- **Codex review of 005:** 8 findings, security category clean (Host, token, content type, static allowlist, safe DOM). A Codex fix job is running for: path-based identity refs, no drag on uncertain dates, version on link/unlink/request, unique request ids, catching RecursionError, focus restore, stamp scope.
- Clone suites hit 1 failure (test_chrono expected "30 years"; the report now showed "29 to 30"). Decision: the report shows a range only when the birthdate is itself uncertain (year/month precision, or circa). `lk-scratch/snap/patch_saga3.py`.
- **Guard bug:** parallel Reads of the 3 docs raced in the hook state file and lost one read, which blocked an edit. Fixed: reads are tracked per session, and enforcement applies only to sessions with a SessionStart, i.e. after a restart or compaction. Read the docs one at a time.
- Decision: land the saga integration now at engine c71ec9c, plus the clone fixes. The 005 review fixes and 006/007 reach the sagas in one more landing at the end, so the live repos are touched twice in total.

### Landing + 006 (2026-10-18)
- **LANDED** all three sagas by ff-only, back to back, with the working tree untouched (`lk-scratch/snap/land.sh`: porcelain status and the hashes of every untracked or modified file were identical before and after). Live HEADs: Realm 7737f58, Space 75bd3ee, Zombies f1b4e1c.
  - Each received: system #1 (chronology), the backfill wiki + knowledge commits, system #2 (timeline editor, report fixes), and `knowledge: chronology report`.
  - Report results: Realm 0 FAIL / 0 WARN; Space 2 FAIL (RAIL_REGRESSION: cards 051/052) + 4 WARN (impossible SRD days); Zombies 0 / 0.
- After-landing probe: the live repos were copied to `lk-scratch/probe2` and `baseline.sh` writes to `docs/build/baselines/probe-after` (running). The in-progress status/validate diffs are to be checked.
- Aeon desktop access was declined a second time (the planned single retry). 006 SC-4 (opening in Aeon) stays **unverified**. Our export is at `lk-scratch\aeon_out\Salt Road (Lorekeeper).aeon` for the user to open.
- Codex built interop.py (637 lines; 15 tests; all 19 templates read). I wired the ops `import`/`export`: CSV by extension, anything else goes through `read_aeon`, which refuses non-Aeon files. Fixed type mapping: old templates leave category OTHER, so people and places are now matched by name. Wuthering Heights imports 116 items, and Lorekeeper finds 22 DEAD_PARTICIPANT FAILs in it (the dead listed at later events).
- Codex fixed the 8 findings from the 005 review. Committed `bd8fdfd`.
- Perf: the 3,000-item load test fails only under heavy parallel load (1.57–2.31 s while 3 saga suites run); re-verify when idle before close-out.
