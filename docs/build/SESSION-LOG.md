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
