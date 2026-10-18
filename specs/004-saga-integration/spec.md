# Feature 004: Saga integration (Realm, Space, Zombies) in warn mode

## Overview
The three sagas run one byte-identical stdlib engine (`saga.py`). Lorekeeper is vendored into each and wired in as a feature-gated module, `chrono.py`, modelled on `profiles.py`, so the pipeline gains:
- chronology context while a chapter is drafted
- structural Wiki dates once a chapter is approved
- a 500-card chronology audit
- the timeline editor for the human, added in 005

Everything starts in **warn mode**: findings are reported and nothing blocks. Chapters already in progress are never gated.

## User scenarios
1. **Context while drafting.** The pipeline assembles chapter N. `RT/context/chronology.md` tells the drafting agents:
   - the chapter date
   - each roster character's age that day
   - where each character was last seen, and how long ago
   - which date rules apply
2. **Updates after approval.** After a chapter is approved, the Wiki update stage reminds the agent to keep `born`, `died`, `date`, `location` and `participants` current on touched pages. It WARNs when they are missing.
3. **Saga-wide audit.** The user says "Check chronology". `saga.py chrono-report` writes `_system/knowledge/chronology_report.md`, covering:
   - card-date parse status
   - impossible dates
   - rail regressions (Space)
   - Lorekeeper check findings on the Wiki
   - age spot-checks for characters with known birthdates
4. **Timeline view.** The user says "Show me the timeline". `saga.py timeline` starts `lore serve` on the Wiki in saga mode (005). Edits become change requests, which `saga.py timeline-requests` lists.

## Functional requirements
- **FR-1 Vendoring.**
  - `_system/vendor/lorekeeper/*.py` is a flat copy of `lorekeeper/` (no tests), plus `VERSION` holding the Lorekeeper commit.
  - Parity: `SHARED_GLOBS` gains `_system/vendor/lorekeeper/*.py`; `SHARED_FILES` gains `_system/vendor/lorekeeper/VERSION`, `_system/scripts/chrono.py`, `_system/tests/test_chrono.py` and `_system/skills/chronology.md`.
  - No saga script reads outside its repository.
- **FR-2 Manifest.** The key `"lorekeeper": {"mode": "warn", "calendars": [...], "rules": [...], "types": {...}}`. Without the key, chronology is off and every command is a no-op with a message.
  - Realm and Zombies: Gregorian.
  - Space: `[srd, gregorian]`, with SRD `Y0 = 6842 CE` (365-day years).
  - Rules:
    - Realm: a duel lasts at most 1 day (`tag: duel`); a Return comes exactly 7 days after the death it follows (`role: return_of`).
    - Space: `monotonic` over chapter cards, grouped by rail (`Primary allocation`) and ordered by chapter number, code `RAIL_REGRESSION`.
- **FR-3 Gating** follows the profiles pattern.
  - **Scope.** `enabled()` is true when the manifest has the key. `applies(n)` is true when the chapter state has `"chrono": 1`. `init-chapter` sets that flag only when the feature is enabled, so CH004/CH005 are never gated.
  - **SOURCE_ASSEMBLY.** `assemble(n)` writes `RT/context/chronology.md` plus a sha256 receipt.
  - **WIKI_AND_LEDGER_UPDATE (completing).** `gate` checks touched Wiki pages. In warn mode it prints `WARN CHRONO_*` lines; in fail mode it raises.
- **FR-4 `saga.py` commands.**
  - `chrono N` prints chapter N's chronology context.
  - `chrono-report` writes the report.
  - `timeline [--port P]` starts the editor (005).
  - `timeline-requests [--apply ID]`.
  - `validate N` gains `WARN|FAIL CHRONO_*` lines for applicable chapters.
  - `health` gains one advisory line.
- **FR-5 Cards as items.** Each chapter card becomes an in-memory Lorekeeper item: type `chapter`, `chapter: N`, `date`, `rail` (Space Primary allocation), `pov` and `location` text. Lorekeeper checks and rules run over Wiki items and card items together.
- **FR-6 Docs.**
  - Wiki templates gain optional frontmatter keys: character `born`, `died`; event `date`, `end`, `location`, `participants`.
  - A new skill, `_system/skills/chronology.md`, is listed in the skills README.
  - PIPELINE notes are updated, and a START_HERE intent is added for "Show me the timeline" / "Check chronology".
- **FR-7 Backfill.** For every frozen chapter, the Wiki pages it touched gain structured dates and links taken from canon (chapter prose, World Bible, cards), each with a cited source. A value with no source is decided and recorded in `_system/knowledge/agent_decisions.md`. Commits are prefixed `wiki:` and `knowledge:`.
- **FR-8 Safety.**
  - All work happens in clones under `C:\Users\Owner\lk-scratch\sagas`.
  - Baselines are green before any change.
  - Landing is fast-forward only, all three back to back.
  - Nothing in progress is staged: in-progress chapters, state, provenance and saga.log stay out.
  - `status` and `validate` output for in-progress chapters is byte-identical before and after.

## Success criteria
- **SC-1** All three suites and parity are green, in the clones and live.
- **SC-2** `chrono-report` is generated for all three sagas. Space lists the 4 impossible SRD day numbers.
- **SC-3** In-progress chapter status and validate output is unchanged (diff empty).
- **SC-4** Backfilled Wiki pages pass `lore check` with no FAIL from missing structure.
